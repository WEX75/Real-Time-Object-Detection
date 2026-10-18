export default function EventLog({ events }) {
  return (
    <section style={styles.panel}>
      <h2 style={styles.heading}>Recent detections</h2>
      {events.length === 0 ? (
        <p style={styles.muted}>No detections recorded yet.</p>
      ) : (
        <ul style={styles.list}>
          {events.map((event) => (
            <li key={event.id} style={styles.item}>
              <span>{event.label}</span>
              <span>{Math.round(event.confidence * 100)}%</span>
              <time>{new Date(`${event.created_at}Z`).toLocaleTimeString()}</time>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

const styles = {
  panel: { padding: 18, background: "#151c2c", borderRadius: 12 },
  heading: { margin: "0 0 12px", fontSize: 18 },
  muted: { color: "#9aa8bf" },
  list: { listStyle: "none", padding: 0, margin: 0 },
  item: {
    display: "grid",
    gridTemplateColumns: "1fr 60px 100px",
    gap: 12,
    padding: "10px 0",
    borderTop: "1px solid #293348",
  },
};
