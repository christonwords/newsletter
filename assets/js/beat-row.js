import { formatBeatMeta } from "./catalog.js";
import { drawWaveform } from "./waveform.js";

export function createBeatRow(beat, { onToggle, inquiry = false, compact = false } = {}) {
  const row = document.createElement("article");
  row.className = `beat-row${compact ? " beat-row--compact" : ""}`;
  row.dataset.beatId = beat.id;

  const button = document.createElement("button");
  button.className = "play-control";
  button.type = "button";
  button.textContent = "play";
  button.setAttribute("aria-label", `play ${beat.title}`);
  button.addEventListener("click", () => onToggle?.(beat));

  const details = document.createElement("div");
  details.className = "beat-details";
  const heading = document.createElement("h3");
  heading.textContent = beat.title;
  const meta = document.createElement("p");
  meta.textContent = formatBeatMeta(beat);
  details.append(heading, meta);

  const canvas = document.createElement("canvas");
  canvas.className = "waveform";
  canvas.dataset.seed = beat.slug || beat.title;
  canvas.setAttribute("aria-hidden", "true");
  drawWaveform(canvas, beat.peaks);

  row.append(button, details, canvas);

  if (inquiry) {
    const contact = document.createElement("a");
    contact.className = "beat-inquiry";
    contact.href = `mailto:softparish@gmail.com?subject=${encodeURIComponent(`beat inquiry: ${beat.title}`)}`;
    contact.textContent = "inquire";
    row.append(contact);
  }

  return {
    element: row,
    canvas,
    setState({ active, progress = 0 }) {
      row.classList.toggle("is-playing", active);
      button.textContent = active ? "pause" : "play";
      button.setAttribute("aria-label", `${active ? "pause" : "play"} ${beat.title}`);
      drawWaveform(canvas, beat.peaks, progress, active);
    }
  };
}
