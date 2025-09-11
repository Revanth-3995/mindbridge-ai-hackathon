"use client";

import React, {useCallback, useEffect, useMemo, useRef, useState} from "react";
import Webcam from "react-webcam";
import { motion, AnimatePresence } from "framer-motion";
import { Camera, CameraOff, Loader2, RefreshCw, AlertTriangle, PlayCircle, PauseCircle } from "lucide-react";
import apiClient from "@/lib/apiClient";
import { useRouter } from "next/navigation";
import socket from "@/lib/socket";

// Tailwind assumed available globally via app styles
// Icons from lucide-react

// Utility types
type EmotionPrediction = {
	emotion: string;
	confidence: number;
	bounding_box?: [number, number, number, number] | null;
	faces_detected?: number;
};

// Battery status minimal typing
interface NavigatorWithBattery extends Navigator {
	getBattery?: () => Promise<{ level: number; charging: boolean }>;
}

const captureIntervalMsDefault = 5000;

const videoConstraintsBase: MediaTrackConstraints = {
	width: { ideal: 640 },
	height: { ideal: 480 },
	frameRate: { ideal: 24 },
};

function useMediaDevices() {
	const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
	const [error, setError] = useState<string>("");

	const enumerate = useCallback(async () => {
		try {
			const list = await navigator.mediaDevices.enumerateDevices();
			setDevices(list.filter((d) => d.kind === "videoinput"));
		} catch (e: any) {
			setError(e?.message || "Failed to enumerate devices");
		}
	}, []);

	useEffect(() => {
		if (!navigator.mediaDevices?.enumerateDevices) return;
		enumerate();
		navigator.mediaDevices.addEventListener?.("devicechange", enumerate);
		return () => navigator.mediaDevices.removeEventListener?.("devicechange", enumerate);
	}, [enumerate]);

	return { devices, error };
}

function useBatteryAwareInterval(baseMs: number) {
	const [intervalMs, setIntervalMs] = useState(baseMs);
	useEffect(() => {
		const nav = navigator as NavigatorWithBattery;
		if (nav.getBattery) {
			nav.getBattery().then((batt) => {
				if (batt.level < 0.2 && !batt.charging) {
					setIntervalMs(baseMs * 2); // reduce frequency on low battery
				}
			});
		}
	}, [baseMs]);
	return intervalMs;
}

export default function EmotionMonitor() {
	const webcamRef = useRef<Webcam>(null);
	const canvasRef = useRef<HTMLCanvasElement>(null);
	const [hasPermission, setHasPermission] = useState<boolean | null>(null);
	const [selectedDeviceId, setSelectedDeviceId] = useState<string | undefined>(undefined);
	const { devices } = useMediaDevices();
	const [isCapturing, setIsCapturing] = useState(true);
	const [processing, setProcessing] = useState(false);
	const [error, setError] = useState<string>("");
	const [lastPrediction, setLastPrediction] = useState<EmotionPrediction | null>(null);
	const [queue, setQueue] = useState<string[]>([]); // offline queue of base64 images
	const [reducedMotion, setReducedMotion] = useState(false);
	const router = useRouter();

	useEffect(() => {
		const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
		setReducedMotion(mq.matches);
		const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
		mq.addEventListener("change", handler);
		return () => mq.removeEventListener("change", handler);
	}, []);

	// Socket.IO: listen for server-driven emotion updates (optional real-time overlay)
	useEffect(() => {
		if (!socket) return;
		socket.on("connect", () => {
			// eslint-disable-next-line no-console
			console.log("Connected to Socket.IO with ID:", socket.id);
		});
		socket.on("emotion_update", (data: any) => {
			// eslint-disable-next-line no-console
			console.log("Emotion update:", data);
		});
		return () => {
			socket.off("connect");
			socket.off("emotion_update");
		};
	}, []);

	const videoConstraints = useMemo<MediaTrackConstraints>(() => {
		const base: MediaTrackConstraints = { ...videoConstraintsBase };
		if (selectedDeviceId) base.deviceId = { exact: selectedDeviceId };
		return base;
	}, [selectedDeviceId]);

	// Request permission on mount
	useEffect(() => {
		(async () => {
			try {
				const stream = await navigator.mediaDevices.getUserMedia({ video: videoConstraintsBase, audio: false });
				stream.getTracks().forEach((t) => t.stop());
				setHasPermission(true);
			} catch (e) {
				setHasPermission(false);
			}
		})();
	}, []);

	const intervalMs = useBatteryAwareInterval(captureIntervalMsDefault);

	const getScreenshotBlob = useCallback(async () => {
		const webcam = webcamRef.current;
		if (!webcam) return null;
		const video = (webcam as any).video as HTMLVideoElement | undefined;
		if (!video) return null;

		const canvas = canvasRef.current ?? document.createElement("canvas");
		const ctx = canvas.getContext("2d");
		if (!ctx) return null;
		canvas.width = 640;
		canvas.height = 480;
		ctx.drawImage(video, 0, 0, 640, 480);

		// Face crop placeholder: in-browser simple center crop (simulate face region)
		// For actual face detection client-side, integrate MediaPipe or face-api.js
		const cropW = 320, cropH = 320;
		const sx = Math.max(0, (640 - cropW) / 2);
		const sy = Math.max(0, (480 - cropH) / 2);
		const cropCanvas = document.createElement("canvas");
		cropCanvas.width = cropW;
		cropCanvas.height = cropH;
		const cctx = cropCanvas.getContext("2d");
		if (!cctx) return null;
		cctx.drawImage(canvas, sx, sy, cropW, cropH, 0, 0, cropW, cropH);

		return await new Promise<Blob | null>((resolve) => {
			cropCanvas.toBlob((blob) => resolve(blob), "image/jpeg", 0.7); // compression
		});
	}, []);

	const uploadFrame = useCallback(async (blob: Blob) => {
		const form = new FormData();
		form.append("file", blob, "frame.jpg");
		const controller = new AbortController();
		try {
			setProcessing(true);
			const { data } = await apiClient.post("/api/emotion/detect", form, { signal: controller.signal, headers: { "Content-Type": "multipart/form-data" } });
			const pred = (data?.prediction || data?.data?.prediction || data) as any;
			if (pred?.emotion && typeof pred?.confidence === "number") {
				setLastPrediction({
					emotion: String(pred.emotion),
					confidence: Number(pred.confidence),
					bounding_box: pred.bounding_box || null,
					faces_detected: pred.faces_detected,
				});
			}
		} catch (e: any) {
			const status = e?.response?.status as number | undefined;
			const msg = status === 401 || status === 403 ? "Please log in to continue" : (e?.response?.data?.error || e?.message || "Upload error");
			setError(msg);
			if (status === 401 || status === 403) {
				setTimeout(() => router.replace("/login"), 200);
			}
			// Offline queueing: push base64 if failed
			try {
				const b64 = await blobToBase64(blob);
				setQueue((q) => [...q, b64]);
			} catch {}
		} finally {
			setProcessing(false);
		}
	}, []);

	// Retry queued frames when back online
	useEffect(() => {
		const handler = async () => {
			if (navigator.onLine && queue.length > 0) {
				const next = queue[0];
				try {
					const blob = base64ToBlob(next);
					await uploadFrame(blob);
					setQueue((q) => q.slice(1));
				} catch {}
			}
		};
		window.addEventListener("online", handler);
		return () => window.removeEventListener("online", handler);
	}, [queue, uploadFrame]);

	// Periodic capture
	useEffect(() => {
		if (!isCapturing) return;
		const id = setInterval(async () => {
			try {
				const blob = await getScreenshotBlob();
				if (blob) await uploadFrame(blob);
			} catch (e: any) {
				setError(e?.message || "Capture error");
			}
		}, intervalMs);
		return () => clearInterval(id);
	}, [getScreenshotBlob, uploadFrame, isCapturing, intervalMs]);

	const onManualCapture = useCallback(async () => {
		try {
			const blob = await getScreenshotBlob();
			if (blob) await uploadFrame(blob);
			if (navigator.vibrate) navigator.vibrate(10); // haptic feedback
		} catch (e: any) {
			setError(e?.message || "Manual capture error");
		}
	}, [getScreenshotBlob, uploadFrame]);

	const confidenceColor = useMemo(() => {
		const c = lastPrediction?.confidence ?? 0;
		if (c > 0.7) return "bg-green-500";
		if (c > 0.5) return "bg-yellow-500";
		return "bg-red-500";
	}, [lastPrediction]);

	return (
		<div className="w-full max-w-3xl mx-auto p-4">
			<div className="rounded-xl border border-neutral-200 dark:border-neutral-800 shadow-sm bg-white dark:bg-neutral-900 overflow-hidden">
				<div className="flex items-center justify-between px-4 py-2 border-b border-neutral-200 dark:border-neutral-800">
					<div className="flex items-center gap-2">
						<Camera className="w-5 h-5" aria-hidden />
						<h2 className="text-sm font-semibold">Emotion Monitor</h2>
					</div>
					<div className="flex items-center gap-2">
						<span className="sr-only">Privacy recording indicator</span>
						<span aria-live="polite" className={`inline-block w-2.5 h-2.5 rounded-full ${isCapturing ? "bg-red-500" : "bg-neutral-400"}`} />
					</div>
				</div>

				<div className="p-4 grid grid-cols-1 md:grid-cols-3 gap-4">
					<div className="md:col-span-2 relative">
						{hasPermission === false && (
							<div className="flex items-center justify-center aspect-video rounded-lg border border-dashed p-6 text-center">
								<div>
									<CameraOff className="w-10 h-10 mx-auto mb-2" />
									<p className="font-medium">Camera permission denied</p>
									<p className="text-sm text-neutral-500">Please enable camera access in your browser settings.</p>
								</div>
							</div>
						)}
						{hasPermission !== false && (
							<div className="relative">
								<Webcam
									ref={webcamRef}
									audio={false}
									videoConstraints={videoConstraints}
									className="w-full aspect-video rounded-lg bg-black object-cover"
								/>
								<canvas ref={canvasRef} className="hidden" />
								{lastPrediction && (
									<AnimatePresence>
										<motion.div
											initial={{ opacity: 0, y: -10 }}
											animate={{ opacity: 1, y: 0 }}
											exit={{ opacity: 0, y: -10 }}
											transition={{ duration: reducedMotion ? 0 : 0.25 }}
											className="absolute top-3 left-3 px-3 py-1 rounded-full bg-neutral-900/70 text-white text-xs backdrop-blur"
										>
											<span className="capitalize">{lastPrediction.emotion}</span>
										</motion.div>
									</AnimatePresence>
								)}
								{processing && (
									<div className="absolute inset-0 flex items-center justify-center">
										<Loader2 className="w-8 h-8 animate-spin" aria-label="Processing" />
									</div>
								)}
							</div>
						)}
					</div>

					<div className="space-y-3">
						<div>
							<label className="sr-only" htmlFor="camera">Camera</label>
							<select
								id="camera"
								className="w-full rounded-md border border-neutral-300 dark:border-neutral-700 bg-transparent p-2 text-sm"
								value={selectedDeviceId}
								onChange={(e) => setSelectedDeviceId(e.target.value)}
								aria-label="Select camera device"
							>
								<option value="">Default camera</option>
								{devices.map((d) => (
									<option key={d.deviceId} value={d.deviceId}>{d.label || `Camera ${d.deviceId.slice(-4)}`}</option>
								))}
							</select>
						</div>

						<div className="flex items-center gap-2">
							<button
								onClick={() => setIsCapturing((v) => !v)}
								className="inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm bg-neutral-900 text-white hover:bg-neutral-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-neutral-500"
								aria-pressed={isCapturing}
							>
								{isCapturing ? <PauseCircle className="w-4 h-4" /> : <PlayCircle className="w-4 h-4" />}
								{isCapturing ? "Pause" : "Resume"}
							</button>
							<button
								onClick={onManualCapture}
								className="inline-flex items-center gap-2 rounded-md px-3 py-2 text-sm border border-neutral-300 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-neutral-500"
								aria-label="Capture frame"
							>
								<Camera className="w-4 h-4" /> Capture
							</button>
							<button
								onClick={() => setError("")}
								className="ml-auto inline-flex items-center gap-2 text-xs text-neutral-600 hover:text-neutral-900"
								aria-label="Retry"
							>
								<RefreshCw className="w-4 h-4" /> Retry
							</button>
						</div>

						<div className="space-y-2" aria-live="polite">
							<div className="flex items-center justify-between text-sm">
								<span>Confidence</span>
								<span>{Math.round((lastPrediction?.confidence ?? 0) * 100)}%</span>
							</div>
							<div className="h-2 w-full rounded bg-neutral-200 dark:bg-neutral-800">
								<div className={`h-2 rounded ${confidenceColor}`} style={{ width: `${(lastPrediction?.confidence ?? 0) * 100}%` }} />
							</div>
							{error && (
								<div className="flex items-center gap-2 text-red-600 text-sm" role="alert">
									<AlertTriangle className="w-4 h-4" />
									<span>{error}</span>
								</div>
							)}
						</div>
					</div>
				</div>
			</div>
		</div>
	);
}

// Helpers
async function blobToBase64(blob: Blob): Promise<string> {
	return new Promise((resolve, reject) => {
		const reader = new FileReader();
		reader.onloadend = () => resolve(String(reader.result));
		reader.onerror = reject;
		reader.readAsDataURL(blob);
	});
}

function base64ToBlob(b64: string): Blob {
	const arr = b64.split(",");
	const mime = arr[0].match(/:(.*?);/)?.[1] || "image/jpeg";
	const bstr = atob(arr[1]);
	let n = bstr.length;
	const u8arr = new Uint8Array(n);
	while (n--) u8arr[n] = bstr.charCodeAt(n);
	return new Blob([u8arr], { type: mime });
}
