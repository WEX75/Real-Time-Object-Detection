import { useEffect, useState } from "react";
import { STATE_COLORS } from "./VisionViewport.jsx";

const RULE_TYPES = [
  { value: "left_unattended", label: "Left unattended" },
  { value: "presence", label: "Presence" },
  { value: "count_threshold", label: "Count threshold" },
];

const splitWords = (text) =>
  text
    .split(",")
    .map((word) => word.trim())
    .filter(Boolean);

export default function ControlPanel(props) {
  return (
    <div style={styles.column}>
      <SourceSection {...props} />
      <VocabularySection {...props} />
      <ZonesSection {...props} />
      <RulesSection {...props} />
    </div>
  );
}

function SourceSection({ running, status, onStart, onStop, source, onSourceChange, file, onFileChange }) {
  return (
    <section style={styles.panel}>
      <div style={styles.row}>
        <div>
          <strong>Video source</strong>
          <div style={styles.muted}>{status}</div>
        </div>
        {!running ? (
          <button onClick={onStart} style={styles.button} disabled={source === "file" && !file}>
            Start
          </button>
        ) : (
          <button onClick={onStop} style={{ ...styles.button, ...styles.danger }}>
            Stop
          </button>
        )}
      </div>
      <div style={styles.row}>
        <label style={styles.radio}>
          <input
            type="radio"
            checked={source === "camera"}
            disabled={running}
            onChange={() => onSourceChange("camera")}
          />
          Webcam
        </label>
        <label style={styles.radio}>
          <input type="radio" checked={source === "file"} disabled={running} onChange={() => onSourceChange("file")} />
          Video file
        </label>
      </div>
      {source === "file" && (
        <input
          type="file"
          accept="video/*"
          disabled={running}
          onChange={(event) => onFileChange(event.target.files[0] ?? null)}
          style={styles.file}
        />
      )}
      {source === "file" && file && <div style={styles.muted}>{file.name} (plays in a loop)</div>}
    </section>
  );
}

function VocabularySection({ vocabulary, unsupported, onSaveVocabulary }) {
  const [text, setText] = useState("");
  useEffect(() => setText(vocabulary.join(", ")), [vocabulary]);

  function submit(event) {
    event.preventDefault();
    onSaveVocabulary(splitWords(text));
  }

  return (
    <section style={styles.panel}>
      <strong>What to look for</strong>
      <form onSubmit={submit} style={styles.inline}>
        <input
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="person, cup, bottle"
          style={styles.input}
          aria-label="Vocabulary, comma separated"
        />
        <button type="submit" style={styles.button}>
          Apply
        </button>
      </form>
      {unsupported.length > 0 && (
        <div style={styles.warning}>Not supported by this detector: {unsupported.join(", ")}</div>
      )}
    </section>
  );
}

function ZonesSection({ zones, zoneStates, drawing, onToggleDrawing, onDeleteZone }) {
  return (
    <section style={styles.panel}>
      <div style={styles.row}>
        <strong>Zones</strong>
        <button onClick={onToggleDrawing} style={{ ...styles.button, ...(drawing ? styles.secondary : {}) }}>
          {drawing ? "Cancel drawing" : "Draw zone"}
        </button>
      </div>
      {zones.length === 0 ? (
        <div style={styles.muted}>No zones yet. Draw one on the video.</div>
      ) : (
        <ul style={styles.list}>
          {zones.map((zone) => {
            const state = zoneStates[zone.id] ?? "FREE";
            return (
              <li key={zone.id} style={styles.item}>
                <span>{zone.name}</span>
                <span style={{ ...styles.badge, background: STATE_COLORS[state] }}>{state}</span>
                <button onClick={() => onDeleteZone(zone)} style={styles.link} aria-label={`Delete ${zone.name}`}>
                  Delete
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}

function RulesSection({ zones, rules, onCreateRule, onToggleRule, onDeleteRule }) {
  const [zoneId, setZoneId] = useState("");
  const [type, setType] = useState("left_unattended");
  const [labels, setLabels] = useState("cup, bottle");
  const [seconds, setSeconds] = useState("20");
  const [threshold, setThreshold] = useState("3");
  const zoneNames = Object.fromEntries(zones.map((zone) => [zone.id, zone.name]));
  const selectedZone = zoneNames[zoneId] ? zoneId : zones[0]?.id ?? "";

  async function submit(event) {
    event.preventDefault();
    await onCreateRule({
      zone_id: selectedZone,
      type,
      target_labels: splitWords(labels),
      seconds: Number(seconds) || 0,
      threshold: type === "count_threshold" ? Number(threshold) : null,
    });
  }

  return (
    <section style={styles.panel}>
      <strong>Rules</strong>
      <form onSubmit={submit} style={styles.form}>
        <select value={selectedZone} onChange={(event) => setZoneId(event.target.value)} style={styles.input}>
          {zones.length === 0 && <option value="">Draw a zone first</option>}
          {zones.map((zone) => (
            <option key={zone.id} value={zone.id}>
              {zone.name}
            </option>
          ))}
        </select>
        <select value={type} onChange={(event) => setType(event.target.value)} style={styles.input}>
          {RULE_TYPES.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
        <input
          value={labels}
          onChange={(event) => setLabels(event.target.value)}
          placeholder="Target labels, e.g. cup, bottle"
          style={styles.input}
          aria-label="Target labels"
        />
        <div style={styles.inline}>
          <label style={styles.field}>
            Seconds
            <input
              type="number"
              min="0"
              step="0.5"
              value={seconds}
              onChange={(event) => setSeconds(event.target.value)}
              style={styles.input}
            />
          </label>
          {type === "count_threshold" && (
            <label style={styles.field}>
              More than
              <input
                type="number"
                min="0"
                value={threshold}
                onChange={(event) => setThreshold(event.target.value)}
                style={styles.input}
              />
            </label>
          )}
        </div>
        <button type="submit" style={styles.button} disabled={!selectedZone}>
          Add rule
        </button>
      </form>
      {rules.length > 0 && (
        <ul style={styles.list}>
          {rules.map((rule) => (
            <li key={rule.id} style={styles.ruleItem}>
              <label style={styles.radio}>
                <input type="checkbox" checked={rule.enabled} onChange={() => onToggleRule(rule)} />
                <span style={rule.enabled ? undefined : styles.muted}>
                  {zoneNames[rule.zone_id] ?? "?"}: {rule.type} [{rule.target_labels.join(", ")}]
                  {rule.type === "count_threshold" && ` > ${rule.threshold}`} for {rule.seconds} s
                </span>
              </label>
              <button onClick={() => onDeleteRule(rule)} style={styles.link}>
                Delete
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

const styles = {
  column: { display: "grid", gap: 16 },
  panel: { display: "grid", gap: 10, padding: 18, background: "#151c2c", borderRadius: 12 },
  row: { display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" },
  inline: { display: "flex", gap: 8, alignItems: "flex-end" },
  form: { display: "grid", gap: 8 },
  field: { display: "grid", gap: 4, flex: 1, color: "#9aa8bf", fontSize: 13 },
  muted: { color: "#9aa8bf", fontSize: 14 },
  warning: { color: "#ff9f43", fontSize: 14 },
  radio: { display: "flex", alignItems: "center", gap: 6, cursor: "pointer" },
  file: { color: "#b9c6db", maxWidth: "100%" },
  input: {
    flex: 1,
    minWidth: 0,
    padding: "8px 10px",
    color: "#e8eefc",
    background: "#0d1320",
    border: "1px solid #293348",
    borderRadius: 8,
    font: "inherit",
  },
  button: {
    border: 0,
    borderRadius: 8,
    padding: "9px 14px",
    color: "white",
    background: "#4f7cff",
    cursor: "pointer",
    font: "inherit",
  },
  secondary: { background: "#3a4560" },
  danger: { background: "#d94b5b" },
  link: { border: 0, background: "none", color: "#ff8792", cursor: "pointer", padding: 0, font: "inherit" },
  list: { listStyle: "none", padding: 0, margin: 0 },
  item: {
    display: "grid",
    gridTemplateColumns: "1fr auto auto",
    alignItems: "center",
    gap: 10,
    padding: "8px 0",
    borderTop: "1px solid #293348",
  },
  ruleItem: {
    display: "flex",
    justifyContent: "space-between",
    alignItems: "center",
    gap: 10,
    padding: "8px 0",
    borderTop: "1px solid #293348",
    fontSize: 14,
  },
  badge: { padding: "2px 8px", borderRadius: 999, color: "#080b12", fontSize: 12, fontWeight: 600 },
};
