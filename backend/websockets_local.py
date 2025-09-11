import logging
from typing import Any, Dict, Optional
from datetime import datetime

import socketio
from redis.asyncio import Redis

from config import settings
from security import decode_token
from celery_app import check_user_crisis_indicators


logger = logging.getLogger(__name__)


# Redis manager for horizontal scaling
manager = socketio.AsyncRedisManager(settings.REDIS_URL)

# Async Socket.IO server
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins=settings.CORS_ORIGINS,
    client_manager=manager,
    logger=settings.DEBUG,
    engineio_logger=settings.DEBUG,
)


# Redis client for presence and rate limiting
redis_client: Optional[Redis] = None


async def get_redis() -> Redis:
    global redis_client
    if redis_client is None:
        redis_client = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    return redis_client


async def set_online(user_id: str):
    r = await get_redis()
    await r.set(f"online:{user_id}", "1", ex=120)
    await r.sadd("online_users", user_id)


async def set_offline(user_id: str):
    r = await get_redis()
    await r.delete(f"online:{user_id}")
    await r.srem("online_users", user_id)


async def check_rate_limit(sid: str, event: str, limit: int = 30, window_sec: int = 60) -> bool:
    r = await get_redis()
    key = f"ratelimit:{sid}:{event}:{int(datetime.utcnow().timestamp() // window_sec)}"
    current = await r.incr(key)
    if current == 1:
        await r.expire(key, window_sec)
    return current <= limit


async def _get_user_from_auth(auth: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    try:
        token = None
        if isinstance(auth, dict):
            token = auth.get("token") or auth.get("Authorization")
        if not token:
            return None
        if token.lower().startswith("bearer "):
            token = token.split(" ", 1)[1]
        payload = decode_token(token)
        if not payload:
            return None
        return {"user_id": str(payload.get("sub")), "email": payload.get("email")}
    except Exception as e:
        logger.warning(f"Auth parsing failed: {e}")
        return None


@sio.event
async def connect(sid: str, environ: Dict[str, Any], auth: Optional[Dict[str, Any]] = None):
    try:
        user = await _get_user_from_auth(auth)
        if not user or not user.get("user_id"):
            logger.warning("Socket connect rejected: invalid auth")
            return False

        await sio.save_session(sid, {
            "user_id": user["user_id"],
            "email": user.get("email"),
            "connected_at": datetime.utcnow().isoformat(),
        })

        # Join personal room
        await sio.enter_room(sid, f"user:{user['user_id']}")

        # Presence
        await set_online(user["user_id"])

        # Confirmation
        await sio.emit("connected", {
            "message": "Connected",
            "user": user,
            "timestamp": datetime.utcnow().isoformat(),
        }, room=sid)

        logger.info(f"Socket connected {sid} for user {user['user_id']}")
        return True
    except Exception as e:
        logger.error(f"Connect handler error: {e}")
        return False


@sio.event
async def disconnect(sid: str):
    try:
        session = await sio.get_session(sid)
        user_id = session.get("user_id") if session else None
        if user_id:
            await set_offline(user_id)
            await sio.leave_room(sid, f"user:{user_id}")
            logger.info(f"Socket disconnected {sid} for user {user_id}")
    except Exception as e:
        logger.error(f"Disconnect error: {e}")


@sio.event
async def emotion_update(sid: str, data: Dict[str, Any]):
    try:
        if not await check_rate_limit(sid, "emotion_update", limit=60, window_sec=60):
            logger.warning(f"Rate limited emotion_update for {sid}")
            return
        session = await sio.get_session(sid)
        if not session:
            return
        user_id = session.get("user_id")
        if not user_id:
            return
        # Broadcast to user's private room
        await sio.emit("emotion_update", {
            "data": data,
            "timestamp": datetime.utcnow().isoformat(),
        }, room=f"user:{user_id}")

        # Optionally trigger crisis detection in background
        try:
            check_user_crisis_indicators.delay(user_id)
        except Exception:
            pass
    except Exception as e:
        logger.error(f"emotion_update error: {e}")


@sio.event
async def peer_request(sid: str, data: Dict[str, Any]):
    try:
        if not await check_rate_limit(sid, "peer_request", limit=10, window_sec=60):
            logger.warning(f"Rate limited peer_request for {sid}")
            return
        session = await sio.get_session(sid)
        if not session:
            return
        user_id = session.get("user_id")
        target_id = data.get("target_user_id")
        if not user_id or not target_id:
            return
        # Notify target user
        await sio.emit("peer_request", {
            "from_user_id": user_id,
            "timestamp": datetime.utcnow().isoformat(),
        }, room=f"user:{target_id}")

        logger.info(f"Peer request from {user_id} -> {target_id}")
    except Exception as e:
        logger.error(f"peer_request error: {e}")


class EmotionNamespace(socketio.AsyncNamespace):
    def __init__(self):
        super().__init__(namespace="/emotion")


class ChatNamespace(socketio.AsyncNamespace):
    def __init__(self):
        super().__init__(namespace="/chat")


class AlertsNamespace(socketio.AsyncNamespace):
    def __init__(self):
        super().__init__(namespace="/alerts")


sio.register_namespace(EmotionNamespace())
sio.register_namespace(ChatNamespace())
sio.register_namespace(AlertsNamespace())

__all__ = ["sio", "get_redis"]


