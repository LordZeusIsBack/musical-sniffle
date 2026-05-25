const AXIS_META = [
  { label: "Distress", low: "Calm", high: "Anxious" },
  { label: "Somatic", low: "Light", high: "Heavy" },
  { label: "Sadness", low: "Bright", high: "Somber" },
  { label: "Anger", low: "Gentle", high: "Tense" },
];

const TENSIONS = [
  "Restless", "Uneasy", "Afloat", "Clouded",
  "Still", "Open", "Grounded", "At ease",
];

function lerp(a, b, t) {
  return a + (b - a) * t;
}

function clamp(v, min, max) {
  return Math.max(min, Math.min(max, v));
}

export default function useEmotion(vector) {
  const v = vector ?? [0, 0, 0, 0];

  // Normalise each axis from [-1,1] to [0,1]
  const n = v.map((x) => clamp((x + 1) / 2, 0, 1));

  // --- Colour (HSL) ---
  // Low sadness → warm gold (40°), high sadness → cool lavender (260°)
  const hue = lerp(40, 260, n[2]);
  // Low distress → more saturation, high distress → wash out slightly
  const saturation = lerp(55, 35, n[0]);
  // Low somatic → lighter, high → deeper
  const lightness = lerp(65, 50, n[3]);
  const color = `hsl(${hue}, ${saturation}%, ${lightness}%)`;

  // --- Shape ---
  // Anger → more jagged (less round)
  const roundness = lerp(0.85, 0.4, n[3]);
  // Somatic → bigger size
  const sizeScale = lerp(0.7, 1.3, n[1]);
  // Distress → faster motion
  const motionSpeed = lerp(0.3, 1.5, n[0]);

  // --- Mood words ---
  // Pick axes where the normalised value is extreme (> 0.6 or < 0.4)
  const words = [];
  n.forEach((val, i) => {
    if (val > 0.6) words.push(AXIS_META[i].high);
    else if (val < 0.4) words.push(AXIS_META[i].low);
  });
  // Fallback: pick a general tension word
  if (words.length === 0) {
    const avg = n.reduce((a, b) => a + b, 0) / n.length;
    const idx = Math.round(lerp(0, TENSIONS.length - 1, avg));
    words.push(TENSIONS[idx]);
  }
  // Take 2-3 words
  const moodWords = words.slice(0, 3);

  return { color, hue, saturation, lightness, roundness, sizeScale, motionSpeed, moodWords, raw: v };
}