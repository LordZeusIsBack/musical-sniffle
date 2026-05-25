import { useMemo } from "react";

export default function AmbientAura({ vector = [0, 0, 0, 0] }) {
  // sadness (index 2) drives colour; distress (0) drives intensity
  const hue = 40 + ((vector[2] ?? 0) + 1) / 2 * 220;
  const alpha = 0.04 + ((vector[0] ?? 0) + 1) / 2 * 0.06;

  const gradient = useMemo(
    () => `radial-gradient(ellipse 80% 60% at 50% 90%, hsla(${hue}, 50%, 60%, ${alpha}) 0%, transparent 70%)`,
    [hue, alpha]
  );

  return (
    <div
      className="pointer-events-none fixed inset-0 z-0 transition-all duration-1000 ease-in-out"
      style={{ background: gradient }}
    />
  );
}