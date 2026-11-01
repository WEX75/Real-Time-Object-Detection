import { useCallback, useEffect, useRef, useState } from "react";
import ControlPanel from "./components/ControlPanel.jsx";
import EventLog from "./components/EventLog.jsx";
import TelemetryBar from "./components/TelemetryBar.jsx";
import VisionViewport from "./components/VisionViewport.jsx";

const EVENT_POLL_MS = 2000;
const FPS_WINDOW_MS = 2000;

function formatDetail(detail) {
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail.map((error) => `${(error.loc ?? []).slice(1).join(".")}: ${error.msg}`).join("; ");
  }
  return "Request failed.";
}

async function api(path, { method = "GET", body } = {}) {
  const response = await fetch(path, {
    method,
    headers: body === undefined ? undefined : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      message = formatDetail((await response.json()).detail);
    } catch {
      // keep the status line
    }
    throw new Error(message);
  }
  return response.status === 204 ? null : response.json();
}

export default function App() {
  const viewportRef = useRef(null);
  const frameTimesRef = useRef([]);
  const [running, setRunning] = useState(false);
  const [source, setSource] = useState("camera");
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState("Stopped");
  const [telemetry, setTelemetry] = useState(null);
  const [fps, setFps] = useState(0);
  const [detector, setDetector] = useState("");
  const [vocabulary, setVocabulary] = useState([]);
  const [unsupported, setUnsupported] = useState([]);
  const [zones, setZones] = useState([]);
  const [rules, setRules] = useState([]);
  const [events, setEvents] = useState([]);
  const [drawing, setDrawing] = useState(false);
  const [apiError, setApiError] = useState("");

  const run = useCallback(async (action) => {
    try {
      const result = await action();
      setApiError("");
      return result;
    } catch (error) {
      setApiError(error.message);
      return undefined;
    }
  }, []);

  const refreshEvents = useCallback(() => run(async () => setEvents(await api("/api/events?limit=50"))), [run]);
  const refreshZones = useCallback(() => run(async () => setZones(await api("/api/zones"))), [run]);
  const refreshRules = useCallback(() => run(async () => setRules(await api("/api/rules"))), [run]);

  useEffect(() => {
    run(async () => {
      const health = await api("/api/health");
      setDetector(health.detector);
      setUnsupported(health.unsupported);
      setVocabulary((await api("/api/vocabulary")).words);
    });
    refreshZones();
    refreshRules();
    refreshEvents();
    const timer = window.setInterval(refreshEvents, EVENT_POLL_MS);
    return () => window.clearInterval(timer);
  }, [run, refreshZones, refreshRules, refreshEvents]);

  const handleTelemetry = useCallback(
    (payload) => {
      setTelemetry(payload);
      setDetector(payload.detector);
      const now = performance.now();
      const times = [...frameTimesRef.current, now].filter((t) => now - t <= FPS_WINDOW_MS);
      frameTimesRef.current = times;
      setFps(times.length > 1 ? ((times.length - 1) * 1000) / (now - times[0]) : 0);
      if (payload.events.length > 0) refreshEvents();
    },
    [refreshEvents],
  );

  const stopDrawing = useCallback(() => setDrawing(false), []);

  async function start() {
    setRunning(true);
    await viewportRef.current?.start(source, file);
  }

  function stop() {
    viewportRef.current?.stop();
    setRunning(false);
    setTelemetry(null);
    setFps(0);
    frameTimesRef.current = [];
  }

  function saveVocabulary(words) {
    return run(async () => {
      const result = await api("/api/vocabulary", { method: "PUT", body: { words } });
      setVocabulary(result.words);
      setUnsupported(result.unsupported);
    });
  }

  function createZone(name, polygon) {
    run(async () => {
      await api("/api/zones", { method: "POST", body: { name, polygon } });
      await refreshZones();
    });
  }

  function deleteZone(zone) {
    run(async () => {
      await api(`/api/zones/${zone.id}`, { method: "DELETE" });
      await Promise.all([refreshZones(), refreshRules()]);
    });
  }

  function createRule(body) {
    return run(async () => {
      await api("/api/rules", { method: "POST", body });
      await refreshRules();
      return true;
    });
  }

  function toggleRule(rule) {
    run(async () => {
      await api(`/api/rules/${rule.id}`, { method: "PATCH", body: { enabled: !rule.enabled } });
      await refreshRules();
    });
  }

  function deleteRule(rule) {
    run(async () => {
      await api(`/api/rules/${rule.id}`, { method: "DELETE" });
      await refreshRules();
    });
  }

  const zoneStates = Object.fromEntries((telemetry?.zones ?? []).map((zone) => [zone.id, zone.state]));

  return (
    <main style={styles.page}>
      <header>
        <p style={styles.eyebrow}>FUNDAMENTELE INGINERIEI SOFTWARE</p>
        <h1 style={styles.title}>Vigilo</h1>
        <p style={styles.subtitle}>Tell the camera what to watch and what to do.</p>
      </header>
      <TelemetryBar
        connection={status}
        detector={detector}
        fps={fps}
        inferMs={telemetry?.infer_ms}
        count={telemetry?.detections.length ?? 0}
      />
      {apiError && <p style={styles.error}>{apiError}</p>}
      <div style={styles.layout}>
        <div style={styles.viewport}>
          <VisionViewport
            ref={viewportRef}
            zones={zones}
            telemetry={telemetry}
            drawing={drawing}
            onTelemetry={handleTelemetry}
            onStatus={setStatus}
            onZoneDrawn={createZone}
            onDrawingDone={stopDrawing}
          />
        </div>
        <div style={styles.sidebar}>
          <ControlPanel
            running={running}
            status={status}
            onStart={start}
            onStop={stop}
            source={source}
            onSourceChange={setSource}
            file={file}
            onFileChange={setFile}
            vocabulary={vocabulary}
            unsupported={unsupported}
            onSaveVocabulary={saveVocabulary}
            zones={zones}
            zoneStates={zoneStates}
            drawing={drawing}
            onToggleDrawing={() => setDrawing((value) => !value)}
            onDeleteZone={deleteZone}
            rules={rules}
            onCreateRule={createRule}
            onToggleRule={toggleRule}
            onDeleteRule={deleteRule}
          />
        </div>
      </div>
      <EventLog events={events} />
    </main>
  );
}

const styles = {
  page: {
    width: "min(100% - 32px, 1280px)",
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
  error: { color: "#ff8792", margin: 0 },
  layout: { display: "flex", flexWrap: "wrap", gap: 16, alignItems: "flex-start" },
  viewport: { flex: "3 1 520px", minWidth: 0 },
  sidebar: { flex: "1 1 300px", minWidth: 0 },
};
