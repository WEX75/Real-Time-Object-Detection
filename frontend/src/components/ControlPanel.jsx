export default function ControlPanel({ active, onStart, onStop, status }) {
  return (
    <section style={styles.panel}>
      <div>
        <strong>Camera controls</strong>
        <div style={styles.status}>{status}</div>
      </div>
      {!active ? (
        <button onClick={onStart} style={styles.button}>
          Start detection
        </button>
      ) : (
        <button onClick={onStop} style={{ ...styles.button, ...styles.stop }}>
          Stop detection
        </button>
      )}
    </section>
  );
}

const styles = {
  panel: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 16,
    padding: 18,
    background: "#151c2c",
    borderRadius: 12,
  },
  status: { color: "#9aa8bf", marginTop: 5, fontSize: 14 },
  button: {
    border: 0,
    borderRadius: 8,
    padding: "10px 15px",
    color: "white",
    background: "#4f7cff",
    cursor: "pointer",
  },
  stop: { background: "#d94b5b" },
};
