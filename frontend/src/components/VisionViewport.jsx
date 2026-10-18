import { forwardRef, useImperativeHandle, useRef, useState } from "react";

const VisionViewport = forwardRef(function VisionViewport(
  { onDetections, onStatus },
  ref,
) {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const socketRef = useRef(null);
  const streamRef = useRef(null);
  const animationRef = useRef(null);
  const lastFrameRef = useRef(0);
  const [imageUrl, setImageUrl] = useState("");
  const [message, setMessage] = useState("");

  function stop() {
    cancelAnimationFrame(animationRef.current);
    socketRef.current?.close();
    socketRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (videoRef.current) videoRef.current.srcObject = null;
    onStatus("Stopped");
  }

  async function start() {
    try {
      setMessage("");
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      streamRef.current = stream;
      videoRef.current.srcObject = stream;
      await videoRef.current.play();

      const scheme = window.location.protocol === "https:" ? "wss" : "ws";
      const socket = new WebSocket(`${scheme}://${window.location.host}/ws/detect`);
      socket.binaryType = "blob";
      socketRef.current = socket;
      socket.onopen = () => {
        onStatus("Connected");
        sendFrames();
      };
      socket.onmessage = (event) => {
        if (typeof event.data === "string") {
          const payload = JSON.parse(event.data);
          if (payload.type === "telemetry") onDetections(payload.detections);
          if (payload.type === "error") setMessage(payload.message);
          return;
        }
        const nextUrl = URL.createObjectURL(event.data);
        setImageUrl((previous) => {
          if (previous) URL.revokeObjectURL(previous);
          return nextUrl;
        });
      };
      socket.onerror = () => setMessage("WebSocket connection failed.");
      socket.onclose = () => onStatus("Disconnected");
      onStatus("Connecting");
    } catch (error) {
      stop();
      setMessage(error.message || "Could not access the camera.");
      onStatus("Camera unavailable");
    }
  }

  function sendFrames(timestamp = 0) {
    animationRef.current = requestAnimationFrame(sendFrames);
    if (timestamp - lastFrameRef.current < 100) return;
    const video = videoRef.current;
    const socket = socketRef.current;
    const canvas = canvasRef.current;
    if (!video?.videoWidth || socket?.readyState !== WebSocket.OPEN) return;

    lastFrameRef.current = timestamp;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d").drawImage(video, 0, 0);
    canvas.toBlob((blob) => {
      if (blob && socket.readyState === WebSocket.OPEN) socket.send(blob);
    }, "image/jpeg", 0.8);
  }

  useImperativeHandle(ref, () => ({ start, stop }));

  return (
    <section style={styles.panel}>
      <video ref={videoRef} muted playsInline style={styles.hidden} />
      <canvas ref={canvasRef} style={styles.hidden} />
      {imageUrl ? (
        <img src={imageUrl} alt="Live object detection" style={styles.image} />
      ) : (
        <div style={styles.placeholder}>Camera feed will appear here</div>
      )}
      {message && <p style={styles.error}>{message}</p>}
    </section>
  );
});

export default VisionViewport;

const styles = {
  panel: { padding: 12, background: "#151c2c", borderRadius: 12 },
  hidden: { display: "none" },
  image: {
    display: "block",
    width: "100%",
    maxHeight: "62vh",
    objectFit: "contain",
    background: "#080b12",
    borderRadius: 8,
  },
  placeholder: {
    display: "grid",
    placeItems: "center",
    minHeight: 320,
    color: "#9aa8bf",
    background: "#080b12",
    borderRadius: 8,
  },
  error: { color: "#ff8792", marginBottom: 0 },
};
