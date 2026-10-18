import { useCallback, useEffect, useRef, useState } from "react";
import ControlPanel from "./components/ControlPanel.jsx";
import EventLog from "./components/EventLog.jsx";
import TelemetryBar from "./components/TelemetryBar.jsx";
import VisionViewport from "./components/VisionViewport.jsx";

export default function App() {
  const viewportRef = useRef(null);
  const [active, setActive] = useState(false);
  const [status, setStatus] = useState("Stopped");
  const [detections, setDetections] = useState([]);
  const [events, setEvents] = useState([]);
  const [apiError, setApiError] = useState("");

  const refreshEvents = useCallback(async () => {
    try {
      const response = await fetch("/api/events?limit=20");
      if (!response.ok) throw new Error("Could not load event history.");
      setEvents(await response.json());
      setApiError("");
    } catch (error) {
      setApiError(error.message);
    }
  }, []);

  useEffect(() => {
    refreshEvents();
    const timer = window.setInterval(refreshEvents, 3000);
    return () => window.clearInterval(timer);
  }, [refreshEvents]);

  function start() {
    setActive(true);
    viewportRef.current?.start();
  }

  function stop() {
    viewportRef.current?.stop();
    setActive(false);
  }

  return (
    <main style={styles.page}>
      <header>
        <p style={styles.eyebrow}>FUNDAMENTELE INGINERIEI SOFTWARE</p>
        <h1 style={styles.title}>Real-Time Object Detection</h1>
        <p style={styles.subtitle}>Live camera inference powered by YOLO11.</p>
      </header>
      <ControlPanel
        active={active}
        onStart={start}
        onStop={stop}
        status={status}
      />
      <TelemetryBar count={detections.length} connection={status} />
      <VisionViewport
        ref={viewportRef}
        onDetections={setDetections}
        onStatus={setStatus}
      />
      {apiError && <p style={styles.error}>{apiError}</p>}
      <EventLog events={events} />
    </main>
  );
}

const styles = {
  page: {
    width: "min(100% - 32px, 1080px)",
    margin: "32px auto",
    display: "grid",
    gap: 16,
  },
  eyebrow: {
    margin: "0 0 8px",
    color: "#80a4ff",
    fontSize: 12,
    letterSpacing: 2,
  },
  title: { margin: 0, fontSize: "clamp(28px, 5vw, 42px)" },
  subtitle: { margin: "8px 0 4px", color: "#9aa8bf" },
  error: { color: "#ff8792" },
};
