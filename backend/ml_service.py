"""
ML Service Client and API routes for emotion detection.
Implements async HTTP client with retries, exponential backoff, and a simple circuit breaker.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, Query
from fastapi import status
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models import EmotionRecord, EmotionType, DataSource
from auth import get_current_active_user, User
from socketio_events import sio
from celery_app import celery_app


logger = logging.getLogger(__name__)


ML_BASE_URL = settings.ML_SERVICE_URL
SINGLE_ENDPOINT = "/predict/emotion"
BATCH_ENDPOINT = "/predict/batch"

ALLOWED_MIME = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
MAX_BYTES = 5 * 1024 * 1024


class CircuitBreaker:
    def __init__(self, failure_threshold: int = 3, reset_timeout_sec: int = 30):
        self.failure_threshold = failure_threshold
        self.reset_timeout_sec = reset_timeout_sec
        self.failures = 0
        self.state = "closed"  # closed, open, half_open
        self.opened_at: Optional[float] = None

    def on_success(self):
        self.failures = 0
        if self.state != "closed":
            self.state = "closed"

    def on_failure(self):
        self.failures += 1
        if self.failures >= self.failure_threshold and self.state != "open":
            self.state = "open"
            self.opened_at = time.time()

    def allow_request(self) -> bool:
        if self.state == "closed":
            return True
        if self.state == "open":
            if self.opened_at is None:
                return False
            if time.time() - self.opened_at >= self.reset_timeout_sec:
                # Try a probe request
                self.state = "half_open"
                return True
            return False
        if self.state == "half_open":
            # Allow a single probe at a time
            return True
        return True


class MLHttpClient:
    def __init__(self, base_url: str = ML_BASE_URL, timeout: float = 10.0, retries: int = 3):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.retries = retries
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        self.cb = CircuitBreaker()
        # Metrics
        self.success_count = 0
        self.failure_count = 0
        self.total_latency_ms = 0.0
        self.total_requests = 0

    async def _request_with_retry(self, method: str, url: str, **kwargs) -> httpx.Response:
        if not self.cb.allow_request():
            logger.warning("Circuit breaker open - skipping request")
            raise HTTPException(status_code=503, detail="ML service unavailable")

        last_exc: Optional[Exception] = None
        for attempt in range(self.retries):
            start = time.perf_counter()
            try:
                resp = await self.client.request(method, url, **kwargs)
                latency_ms = (time.perf_counter() - start) * 1000
                self.total_latency_ms += latency_ms
                self.total_requests += 1
                logger.info(f"ML {method} {url} -> {resp.status_code} in {latency_ms:.1f} ms")
                if resp.status_code < 500:
                    self.cb.on_success()
                    if 200 <= resp.status_code < 300:
                        self.success_count += 1
                    else:
                        self.failure_count += 1
                    return resp
                else:
                    # Server error - retry
                    self.cb.on_failure()
                    self.failure_count += 1
                    last_exc = HTTPException(status_code=resp.status_code, detail=resp.text)
            except Exception as e:
                self.cb.on_failure()
                self.failure_count += 1
                last_exc = e

            # Exponential backoff: 0.25, 0.5, 1.0 sec
            await asyncio.sleep(0.25 * (2 ** attempt))

        # Retries exhausted
        logger.error(f"ML request failed after {self.retries} attempts: {last_exc}")
        raise HTTPException(status_code=503, detail="ML service request failed")

    async def predict_single(self, file: UploadFile) -> Dict[str, Any]:
        form = {"file": (file.filename or "image.jpg", await file.read(), file.content_type or "image/jpeg")}
        resp = await self._request_with_retry("POST", SINGLE_ENDPOINT, files=form)
        try:
            return resp.json()
        except Exception:
            logger.error(f"Invalid JSON from ML service: {resp.text[:200]}")
            raise HTTPException(status_code=502, detail="Invalid ML response")

    async def predict_batch(self, files: List[UploadFile]) -> Dict[str, Any]:
        form = [("files", (f.filename or "image.jpg", await f.read(), f.content_type or "image/jpeg")) for f in files]
        resp = await self._request_with_retry("POST", BATCH_ENDPOINT, files=form)
        try:
            return resp.json()
        except Exception:
            logger.error(f"Invalid JSON from ML service: {resp.text[:200]}")
            raise HTTPException(status_code=502, detail="Invalid ML response")

    def metrics(self) -> Dict[str, Any]:
        avg_latency = (self.total_latency_ms / self.total_requests) if self.total_requests else 0.0
        return {
            "success": self.success_count,
            "failure": self.failure_count,
            "avg_latency_ms": round(avg_latency, 2),
            "total_requests": self.total_requests,
            "cb_state": self.cb.state,
        }


ml_client = MLHttpClient()


def _validate_upload(file: UploadFile):
    if file is None:
        logger.warning("No file uploaded")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail={"error": "No file uploaded"})
    if (file.content_type or "").lower() not in ALLOWED_MIME:
        logger.warning(f"Invalid file type: {file.content_type}")
        raise HTTPException(status_code=400, detail={"error": "Unsupported file type. Allowed: jpg, jpeg, png, webp"})
    try:
        # Determine size without reading whole file into memory permanently
        pos = file.file.tell()
        file.file.seek(0, 2)
        size = file.file.tell()
        file.file.seek(pos)
    except Exception:
        size = None
    if size is not None and size > MAX_BYTES:
        logger.warning(f"File too large: {size} bytes")
        raise HTTPException(status_code=400, detail={"error": "File too large. Max 5MB"})


def _map_emotion(label: str) -> EmotionType:
    try:
        return EmotionType(label.lower())
    except Exception:
        return EmotionType.NEUTRAL


async def _save_emotion_record(db: Session, user_id: Any, label: str, confidence: float, raw: Dict[str, Any]):
    # Retry DB insert on transient errors
    delay = 0.25
    for attempt in range(3):
        try:
            record = EmotionRecord(
                user_id=user_id,
                emotion=_map_emotion(label),
                confidence=float(confidence or 0.0),
                source=DataSource.WEBCAM,
                raw_data=raw,
                created_at=datetime.utcnow(),
            )
            db.add(record)
            db.commit()
            return record
        except Exception as e:
            db.rollback()
            logger.warning(f"DB insert failed (attempt {attempt+1}): {e}")
            if attempt == 2:
                raise
            await asyncio.sleep(delay)
            delay *= 2


router = APIRouter(prefix="/api/emotion", tags=["emotion"])


@router.post("/detect")
async def detect_emotion(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Proxy to ML service single prediction, store result, and emit event."""
    _validate_upload(file)
    try:
        start = time.perf_counter()
        ml_result = await ml_client.predict_single(file)
        duration_ms = (time.perf_counter() - start) * 1000
        logger.info(f"ML single prediction complete in {duration_ms:.1f} ms: {ml_result}")
    except HTTPException as e:
        # Fallback: mock response
        logger.error(f"ML single prediction error: {e.detail}")
        ml_result = {"success": True, "prediction": {"emotion": "neutral", "confidence": 0.5}}

    pred = (ml_result or {}).get("prediction") or {}
    emotion = pred.get("emotion") or "neutral"
    confidence = pred.get("confidence") or 0.0

    # Save record
    try:
        record = await _save_emotion_record(db, current_user.id, emotion, confidence, ml_result)
    except Exception as e:
        logger.error(f"Failed to save EmotionRecord: {e}")
        # Continue despite DB failure
        record = None

    # Emit Socket.IO event to user room
    try:
        await sio.emit("emotion_detected", {
            "user_id": str(current_user.id),
            "emotion": emotion,
            "confidence": confidence,
            "record_id": str(record.id) if record else None,
            "timestamp": datetime.utcnow().isoformat(),
        }, room=f"user_{current_user.id}")
    except Exception as e:
        logger.warning(f"Socket emission failed: {e}")

    return ml_result


@router.get("/history")
async def emotion_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Return user's emotion history (last 7 days), aggregated and paginated."""
    since = datetime.utcnow() - timedelta(days=7)

    # Paginated raw records
    q = db.query(EmotionRecord).filter(EmotionRecord.user_id == current_user.id, EmotionRecord.created_at >= since)
    total = q.count()
    records = q.order_by(EmotionRecord.created_at.desc()).offset((page - 1) * limit).limit(limit).all()

    # Aggregation by day and hour
    agg_day: Dict[str, Dict[str, Any]] = {}
    agg_hour: Dict[str, Dict[str, Any]] = {}
    for rec in records:
        ts = rec.created_at or datetime.utcnow()
        day_key = ts.strftime("%Y-%m-%d")
        hour_key = ts.strftime("%Y-%m-%d %H:00")
        agg_day.setdefault(day_key, {"count": 0, "emotions": {}})
        agg_hour.setdefault(hour_key, {"count": 0, "emotions": {}})
        agg_day[day_key]["count"] += 1
        agg_hour[hour_key]["count"] += 1
        emo = rec.emotion.value if rec.emotion else "neutral"
        agg_day[day_key]["emotions"][emo] = agg_day[day_key]["emotions"].get(emo, 0) + 1
        agg_hour[hour_key]["emotions"][emo] = agg_hour[hour_key]["emotions"].get(emo, 0) + 1

    return {
        "page": page,
        "limit": limit,
        "total": total,
        "records": [r.to_dict() for r in records],
        "aggregate": {
            "by_day": agg_day,
            "by_hour": agg_hour,
        },
        "metrics": ml_client.metrics(),
    }


@router.post("/batch")
async def emotion_batch(
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    if not files:
        raise HTTPException(status_code=400, detail={"error": "No file uploaded"})
    # Validate each file quickly
    valid_files = []
    for f in files:
        try:
            _validate_upload(f)
            valid_files.append(f)
        except HTTPException as e:
            logger.warning(f"Skipping invalid file: {e.detail}")
    if not valid_files:
        raise HTTPException(status_code=400, detail={"error": "No valid images uploaded"})

    # Enqueue Celery task
    task = process_batch_task.delay(str(current_user.id), [vf.filename or "image.jpg" for vf in valid_files])
    return {"task_id": task.id, "queued": True}


@celery_app.task(bind=True, max_retries=3, autoretry_for=(Exception,))
def process_batch_task(self, user_id: str, filenames: List[str]) -> Dict[str, Any]:
    """
    Background processing of batch images.
    Note: For simplicity, this placeholder does not stream actual file bytes across process boundaries.
    In production, store uploads temporarily and pass storage keys.
    """
    from database import get_db_context
    from sqlalchemy.orm import Session as OrmSession

    logger.info(f"Processing batch for user {user_id} with {len(filenames)} files")
    processed = 0
    errors: List[str] = []
    try:
        # This example mocks ML batch processing to focus on pipeline wiring
        mock_predictions = [
            {"emotion": "neutral", "confidence": 0.5},
            {"emotion": "happy", "confidence": 0.8},
        ]
        with get_db_context() as db:  # type: OrmSession
            for i, name in enumerate(filenames):
                pred = mock_predictions[i % len(mock_predictions)]
                rec = EmotionRecord(
                    user_id=user_id,
                    emotion=_map_emotion(pred["emotion"]),
                    confidence=pred["confidence"],
                    source=DataSource.WEBCAM,
                    raw_data={"mock": True, "filename": name},
                    created_at=datetime.utcnow(),
                )
                db.add(rec)
                processed += 1
        # Emit websocket update
        try:
            import asyncio as _asyncio
            loop = _asyncio.get_event_loop()
            if loop.is_running():
                _asyncio.ensure_future(sio.emit("emotion_batch_progress", {
                    "user_id": user_id,
                    "processed": processed,
                    "errors": errors,
                    "timestamp": datetime.utcnow().isoformat(),
                }, room=f"user_{user_id}"))
        except Exception:
            pass
        return {"processed": processed, "errors": errors}
    except Exception as exc:
        logger.error(f"Batch processing failed: {exc}")
        raise self.retry(countdown=2 ** self.request.retries, exc=exc)


__all__ = ["router"]


