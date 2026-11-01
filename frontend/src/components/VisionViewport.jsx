import { forwardRef, useEffect, useImperativeHandle, useRef, useState } from "react";

export const STATE_COLORS = {
  FREE: "#3ccf7a",
  OCCUPIED: "#4f7cff",
  NEEDS_CLEARING: "#ff9f43",
};
const BOX_COLOR = "#5ad1ff";
const DRAFT_COLOR = "#f5f7ff";
const MIN_FRAME_INTERVAL_MS = 100; // at most 10 FPS
const REPLY_TIMEOUT_MS = 5000; // resend if a reply never comes
const CAPTURE_WIDTH = 640; // the detector works at 640 px anyway

// Where the video picture sits inside its element (object-fit: contain).
function contentRect(video, width, height) {
  const videoWidth = video?.videoWidth;
  const videoHeight = video?.videoHeight;
  if (!videoWidth || !videoHeight) return { x: 0, y: 0, w: width, h: height };
  const scale = Math.min(width / videoWidth, height / videoHeight);
  const w = videoWidth * scale;
  const h = videoHeight * scale;
  return { x: (width - w) / 2, y: (height - h) / 2, w, h };
}

const clamp01 = (value) => Math.min(1, Math.max(0, value));

function drawLabel(ctx, text, x, y, color) {
  ctx.font = "600 13px system-ui, sans-serif";
  const width = ctx.measureText(text).width + 10;
  const top = Math.max(0, y - 20);
  ctx.fillStyle = color;
  ctx.fillRect(x, top, width, 20);
  ctx.fillStyle = "#080b12";
  ctx.fillText(text, x + 5, top + 14);
}

const VisionViewport = forwardRef(function VisionViewport(
  { zones, telemetry, drawing, onTelemetry, onStatus, onZoneDrawn, onDrawingDone },
  ref,
) {
  const videoRef = useRef(null);
  const overlayRef = useRef(null);
  const captureRef = useRef(null);
  const socketRef = useRef(null);
  const streamRef = useRef(null);
  const objectUrlRef = useRef(null);
  const timerRef = useRef(null);
  const awaitingRef = useRef(false);
  const lastSentRef = useRef(0);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const [hasVideo, setHasVideo] = useState(false);
  const [draft, setDraft] = useState([]);
  const [message, setMessage] = useState("");

  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => {
      setSize({ width: entry.contentRect.width, height: entry.contentRect.height });
    });
    observer.observe(videoRef.current);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!drawing) setDraft([]);
    if (!drawing) return undefined;
    const onKey = (event) => event.key === "Escape" && onDrawingDone();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [drawing, onDrawingDone]);

  useEffect(() => () => stop(), []); // eslint-disable-line react-hooks/exhaustive-deps

  // Overlay: zones coloured by state, detection boxes, the zone being drawn.
  useEffect(() => {
    const canvas = overlayRef.current;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(size.width * dpr);
    canvas.height = Math.round(size.height * dpr);
    const ctx = canvas.getContext("2d");
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, size.width, size.height);
    if (!hasVideo) return;

    const rect = contentRect(videoRef.current, size.width, size.height);
    const toPx = ([x, y]) => [rect.x + x * rect.w, rect.y + y * rect.h];
    const states = Object.fromEntries((telemetry?.zones ?? []).map((zone) => [zone.id, zone.state]));

    for (const zone of zones) {
      const state = states[zone.id] ?? "FREE";
      const color = STATE_COLORS[state];
      const points = zone.polygon.map(toPx);
      ctx.beginPath();
      points.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
      ctx.closePath();
      ctx.globalAlpha = 0.18;
      ctx.fillStyle = color;
      ctx.fill();
      ctx.globalAlpha = 1;
      ctx.lineWidth = 2;
      ctx.strokeStyle = color;
      ctx.stroke();
      const left = Math.min(...points.map(([x]) => x));
      const top = Math.min(...points.map(([, y]) => y));
      drawLabel(ctx, `${zone.name} - ${state}`, left, top, color);
    }

    for (const detection of telemetry?.detections ?? []) {
      const [x1, y1] = toPx([detection.box[0], detection.box[1]]);
      const [x2, y2] = toPx([detection.box[2], detection.box[3]]);
      ctx.lineWidth = 2;
      ctx.strokeStyle = BOX_COLOR;
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
      drawLabel(ctx, `${detection.label} ${Math.round(detection.confidence * 100)}%`, x1, y1, BOX_COLOR);
    }

    if (draft.length > 0) {
      const points = draft.map(toPx);
      ctx.beginPath();
      points.forEach(([x, y], i) => (i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y)));
      ctx.setLineDash([6, 4]);
      ctx.lineWidth = 2;
      ctx.strokeStyle = DRAFT_COLOR;
      ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = DRAFT_COLOR;
      for (const [x, y] of points) {
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, 2 * Math.PI);
        ctx.fill();
      }
    }
  }, [size, hasVideo, zones, telemetry, draft]);

  function scheduleSend(delay) {
    window.clearTimeout(timerRef.current);
    timerRef.current = window.setTimeout(sendFrame, delay);
  }

  // Backpressure: the next frame leaves only after the reply to this one.
  function sendFrame() {
    const socket = socketRef.current;
    const video = videoRef.current;
    if (!socket || socket.readyState !== WebSocket.OPEN) return;
    if (!video.videoWidth || video.readyState < 2) {
      scheduleSend(MIN_FRAME_INTERVAL_MS);
      return;
    }
    const scale = Math.min(1, CAPTURE_WIDTH / video.videoWidth);
    const canvas = captureRef.current;
    canvas.width = Math.round(video.videoWidth * scale);
    canvas.height = Math.round(video.videoHeight * scale);
    canvas.getContext("2d").drawImage(video, 0, 0, canvas.width, canvas.height);
    canvas.toBlob(
      (blob) => {
        if (!blob || socket.readyState !== WebSocket.OPEN) {
          scheduleSend(MIN_FRAME_INTERVAL_MS);
          return;
        }
        socket.send(blob);
        lastSentRef.current = performance.now();
        awaitingRef.current = true;
        window.clearTimeout(timerRef.current);
        timerRef.current = window.setTimeout(() => {
          if (awaitingRef.current) sendFrame();
        }, REPLY_TIMEOUT_MS);
      },
      "image/jpeg",
      0.8,
    );
  }

  function connect() {
    const scheme = window.location.protocol === "https:" ? "wss" : "ws";
    const socket = new WebSocket(`${scheme}://${window.location.host}/ws/detect`);
    socketRef.current = socket;
    onStatus("Connecting");
    socket.onopen = () => {
      onStatus("Connected");
      scheduleSend(0);
    };
    socket.onmessage = (event) => {
      if (typeof event.data !== "string") return;
      awaitingRef.current = false;
      const payload = JSON.parse(event.data);
      if (payload.type === "telemetry") {
        onTelemetry(payload);
        setMessage("");
      } else if (payload.type === "error") {
        setMessage(payload.message);
      }
      const elapsed = performance.now() - lastSentRef.current;
      scheduleSend(Math.max(0, MIN_FRAME_INTERVAL_MS - elapsed));
    };
    socket.onerror = () => setMessage("WebSocket connection failed. Is the backend running?");
    socket.onclose = () => {
      if (socketRef.current === socket) onStatus("Disconnected");
    };
  }

  async function start(source, file) {
    stop();
    setMessage("");
    const video = videoRef.current;
    try {
      if (source === "file") {
        if (!file) throw new Error("Choose a video file first.");
        objectUrlRef.current = URL.createObjectURL(file);
        video.src = objectUrlRef.current;
        video.loop = true;
      } else {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        });
        streamRef.current = stream;
        video.srcObject = stream;
      }
      await video.play();
      setHasVideo(true);
      connect();
    } catch (error) {
      stop();
      setMessage(error.message || "Could not start the video source.");
      onStatus("Source unavailable");
    }
  }

  function stop() {
    window.clearTimeout(timerRef.current);
    awaitingRef.current = false;
    const socket = socketRef.current;
    socketRef.current = null;
    socket?.close();
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    const video = videoRef.current;
    if (video) {
      video.pause();
      video.srcObject = null;
      video.removeAttribute("src");
      video.load();
    }
    if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current);
    objectUrlRef.current = null;
    setHasVideo(false);
    onStatus("Stopped");
  }

  useImperativeHandle(ref, () => ({ start, stop }));

  // Normalized to the video picture, not to the element (letterboxing).
  function toNormalized(event) {
    const bounds = overlayRef.current.getBoundingClientRect();
    const rect = contentRect(videoRef.current, bounds.width, bounds.height);
    return [
      clamp01((event.clientX - bounds.left - rect.x) / rect.w),
      clamp01((event.clientY - bounds.top - rect.y) / rect.h),
    ];
  }

  function handleClick(event) {
    if (drawing) setDraft((points) => [...points, toNormalized(event)]);
  }

  function handleDoubleClick() {
    if (!drawing) return;
    // The two clicks of the double-click already added the same point twice.
    const points = draft.filter(
      ([x, y], i) => i === 0 || Math.hypot(x - draft[i - 1][0], y - draft[i - 1][1]) > 0.005,
    );
    if (points.length < 3) {
      setMessage("A zone needs at least 3 points.");
      setDraft(points);
      return;
    }
    const name = window.prompt("Zone name", `masa ${zones.length + 1}`);
    if (name?.trim()) onZoneDrawn(name.trim(), points);
    onDrawingDone();
  }

  return (
    <section style={styles.panel}>
      <div style={styles.stage}>
        <video ref={videoRef} muted playsInline style={styles.video} />
        <canvas
          ref={overlayRef}
          onClick={handleClick}
          onDoubleClick={handleDoubleClick}
          style={{ ...styles.overlay, pointerEvents: drawing ? "auto" : "none", cursor: drawing ? "crosshair" : "default" }}
        />
        {!hasVideo && <div style={styles.placeholder}>Start the camera or a video file</div>}
      </div>
      <canvas ref={captureRef} style={styles.hidden} />
      {drawing && (
        <p style={styles.hint}>
          Click to add points, double-click to close the zone, Esc to cancel.
          {!hasVideo && " Start a video source first."}
        </p>
      )}
      {message && <p style={styles.error}>{message}</p>}
    </section>
  );
});

export default VisionViewport;

const styles = {
  panel: { padding: 12, background: "#151c2c", borderRadius: 12, minWidth: 0 },
  stage: { position: "relative" },
  video: {
    display: "block",
    width: "100%",
    minHeight: 320,
    maxHeight: "62vh",
    objectFit: "contain",
    background: "#080b12",
    borderRadius: 8,
  },
  overlay: { position: "absolute", inset: 0, width: "100%", height: "100%" },
  placeholder: {
    position: "absolute",
    inset: 0,
    display: "grid",
    placeItems: "center",
    color: "#9aa8bf",
    pointerEvents: "none",
  },
  hidden: { display: "none" },
  hint: { color: "#b9c6db", margin: "10px 0 0", fontSize: 14 },
  error: { color: "#ff8792", margin: "10px 0 0" },
};
