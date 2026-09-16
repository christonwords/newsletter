const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

export function normalizePeaks(peaks, count = 96) {
  if (!Array.isArray(peaks) || peaks.length === 0) return Array(count).fill(0.18);

  return Array.from({ length: count }, (_, index) => {
    const start = Math.floor((index * peaks.length) / count);
    const end = Math.max(start + 1, Math.floor(((index + 1) * peaks.length) / count));
    const bucket = peaks.slice(start, end).map(Number);
    const peak = Math.max(...bucket.map((value) => clamp(value, 0, 255)));
    return peak / 255;
  });
}

export function fallbackPeaks(seed, count = 96) {
  let value = [...String(seed)].reduce((total, character) => total + character.charCodeAt(0), 17);
  return Array.from({ length: count }, (_, index) => {
    value = (value * 1103515245 + 12345 + index) & 0x7fffffff;
    return 0.16 + (value / 0x7fffffff) * 0.76;
  });
}

export function drawWaveform(canvas, sourcePeaks, progress = 0, active = false) {
  if (!canvas) return;
  const rect = canvas.getBoundingClientRect();
  const ratio = globalThis.devicePixelRatio || 1;
  const width = Math.max(1, Math.round(rect.width * ratio));
  const height = Math.max(1, Math.round(rect.height * ratio));
  if (canvas.width !== width || canvas.height !== height) {
    canvas.width = width;
    canvas.height = height;
  }

  const context = canvas.getContext("2d");
  const barWidth = Math.max(1, Math.round(2 * ratio));
  const gap = Math.max(1, Math.round(2 * ratio));
  const bars = Math.max(12, Math.floor(width / (barWidth + gap)));
  const peaks = Array.isArray(sourcePeaks) && sourcePeaks.length
    ? normalizePeaks(sourcePeaks, bars)
    : fallbackPeaks(canvas.dataset.seed || "christon", bars);

  context.clearRect(0, 0, width, height);
  peaks.forEach((peak, index) => {
    const x = index * (barWidth + gap);
    const barHeight = Math.max(2 * ratio, peak * height * 0.86);
    const played = index / peaks.length <= clamp(progress, 0, 1);
    context.fillStyle = played && active ? "#e62027" : "#171717";
    context.fillRect(x, (height - barHeight) / 2, barWidth, barHeight);
  });
}
