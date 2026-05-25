import { useRef, useEffect, useCallback } from "react";

// Simple pseudo-noise using sine waves — smooth, no dependencies
function noise(x, y, t) {
  return (
    Math.sin(x * 1.7 + t * 0.8) * Math.cos(y * 2.3 + t * 1.1) +
    Math.sin(x * 3.1 + y * 0.5 + t * 1.7) * 0.5
  );
}

function generateBlobPath(cx, cy, radius, roundness, time, count = 10) {
  const pts = [];
  for (let i = 0; i < count; i++) {
    const angle = (2 * Math.PI * i) / count;
    const nz = noise(Math.cos(angle), Math.sin(angle), time);
    // roundness controls how much the noise perturbs the radius
    const r = radius * (1 + (1 - roundness) * nz * 0.4);
    pts.push({
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    });
  }

  // Catmull-Rom → cubic bezier for smooth closed curve
  function getP(i) {
    return pts[((i % count) + count) % count];
  }

  let d = "";
  for (let i = 0; i < count; i++) {
    const p0 = getP(i - 1);
    const p1 = getP(i);
    const p2 = getP(i + 1);
    const p3 = getP(i + 2);

    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;

    if (i === 0) d += `M ${p1.x} ${p1.y}`;
    d += `C ${cp1x} ${cp1y}, ${cp2x} ${cp2y}, ${p2.x} ${p2.y}`;
  }
  d += "Z";
  return d;
}

export default function MoodBloom({ vector = [0, 0, 0, 0], size = 120, className = "" }) {
  const pathRef = useRef(null);
  const timeRef = useRef(0);

  const n = vector.map((v) => ((v ?? 0) + 1) / 2); // [0, 1]

  // Anger → roundness (lower = more jagged)
  const roundness = 0.85 - n[3] * 0.45;
  // Somatic → size
  const baseRadius = (size / 2) * (0.7 + n[1] * 0.3);
  // Distress → speed
  const speed = 0.3 + n[0] * 1.2;

  // Colour: sadness axis shifts hue
  const hue = 40 + n[2] * 220;
  const sat = 55 - n[0] * 20;
  const lit = 65 - n[1] * 15;
  const fillColor = `hsl(${hue}, ${sat}%, ${lit}%)`;

  const animate = useCallback(() => {
    timeRef.current += 0.016 * speed;
    if (pathRef.current) {
      pathRef.current.setAttribute(
        "d",
        generateBlobPath(size / 2, size / 2, baseRadius, roundness, timeRef.current, 12)
      );
    }
  }, [size, baseRadius, roundness, speed]);

  useEffect(() => {
    let raf;
    function loop() {
      animate();
      raf = requestAnimationFrame(loop);
    }
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [animate]);

  return (
    <svg
      width={size}
      height={size}
      viewBox={`0 0 ${size} ${size}`}
      className={className}
      aria-hidden="true"
    >
      <defs>
        <filter id="moodBloomGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <path ref={pathRef} fill={fillColor} filter="url(#moodBloomGlow)" />
    </svg>
  );
}