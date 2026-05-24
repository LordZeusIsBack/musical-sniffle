const AXIS_LABELS = ["D", "SH", "S", "A"];
const AXIS_COLORS = ["#4a7c59", "#f59e0b", "#ef4444", "#3b82f6"];

export default function EmotionalState({ vector }) {
  if (!vector || vector.length === 0) return null;

  return (
    <div className="emotion-panel">
      <h4>Emotional State</h4>
      <div className="emotion-bars">
        {vector.map((val, i) => {
          const pct = ((val + 1) / 2) * 100;
          return (
            <div className="emotion-bar" key={AXIS_LABELS[i]}>
              <span className="label">{AXIS_LABELS[i]}</span>
              <div className="track">
                <div
                  className="fill"
                  style={{
                    width: `${pct}%`,
                    background: AXIS_COLORS[i],
                  }}
                />
              </div>
              <span style={{ color: AXIS_COLORS[i], fontWeight: 600, width: 36, textAlign: "right" }}>
                {val.toFixed(2)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}