export default function TelemetryBar({ connection, detector, fps, inferMs, count }) {
  return (
    <div style={styles.bar}>
      <span>Connection: {connection}</span>
      <span>Detector: {detector || "-"}</span>
      <span>FPS: {fps ? fps.toFixed(1) : "-"}</span>
      <span>Inference: {inferMs != null ? `${Math.round(inferMs)} ms` : "-"}</span>
      <span>Objects: {count}</span>
    </div>
  );
}

const styles = {
  bar: {
    display: "flex",
    flexWrap: "wrap",
    justifyContent: "space-between",
    gap: "6px 16px",
    color: "#b9c6db",
    fontSize: 14,
    padding: "4px 2px",
  },
};
