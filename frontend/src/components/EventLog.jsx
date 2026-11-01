const KIND_LABELS = {
  zone_state_changed: "State",
  rule_triggered: "Alert",
  rule_cleared: "Cleared",
};

const KIND_COLORS = {
  zone_state_changed: "#80a4ff",
  rule_triggered: "#ff9f43",
  rule_cleared: "#3ccf7a",
};

function describe(event) {
  const detail = event.detail ?? {};
  if (event.kind === "zone_state_changed") return `${detail.from} -> ${detail.to}`;
  if (event.kind === "rule_triggered") {
    const counts = Object.entries(detail.counts ?? {})
      .filter(([, count]) => count > 0)
      .map(([label, count]) => `${count} ${label}`)
      .join(", ");
    const threshold = detail.threshold != null ? ` > ${detail.threshold}` : "";
    return `${detail.type}${threshold} for ${detail.seconds} s${counts ? ` (${counts})` : ""}`;
  }
  const reason = detail.reason ? `, ${detail.reason.replace("_", " ")}` : "";
  return `${detail.type} after ${detail.active_seconds} s${reason}`;
}

export default function EventLog({ events }) {
  return (
    <section style={styles.panel}>
      <h2 style={styles.heading}>Events</h2>
      {events.length === 0 ? (
        <p style={styles.muted}>No events yet. Draw a zone and add a rule.</p>
      ) : (
        <ul style={styles.list}>
          {events.map((event) => (
            <li key={event.id} style={styles.item}>
              <time style={styles.muted}>{new Date(event.created_at).toLocaleTimeString()}</time>
              <span>{event.zone_name}</span>
              <span style={{ color: KIND_COLORS[event.kind] }}>{KIND_LABELS[event.kind]}</span>
              <span style={styles.detail}>{describe(event)}</span>
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
  list: { listStyle: "none", padding: 0, margin: 0, maxHeight: 360, overflowY: "auto" },
  item: {
    display: "grid",
    gridTemplateColumns: "90px minmax(80px, 140px) 70px 1fr",
    gap: 12,
    padding: "10px 0",
    borderTop: "1px solid #293348",
    fontSize: 14,
  },
  detail: { color: "#b9c6db", overflowWrap: "anywhere" },
};
