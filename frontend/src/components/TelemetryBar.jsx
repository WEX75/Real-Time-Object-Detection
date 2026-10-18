export default function TelemetryBar({ count, connection }) {
  return (
    <div style={styles.bar}>
      <span>Connection: {connection}</span>
      <span>Objects in latest frame: {count}</span>
    </div>
  );
}

const styles = {
  bar: {
    display: "flex",
    justifyContent: "space-between",
    gap: 12,
    color: "#b9c6db",
    fontSize: 14,
    padding: "4px 2px",
  },
};
