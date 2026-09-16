import { createBeatRow } from "./beat-row.js";
import { loadBeatCatalog } from "./catalog.js";
import { renderDrumkits, renderVsts } from "./collections.js";
import { createMediaController } from "./media.js";

export function createDisclosureController({ ids, onChange = () => {} }) {
  const allowed = new Set(ids);
  let openId = "";
  const set = (next) => {
    if (next && !allowed.has(next)) return;
    openId = next;
    onChange({ openId });
  };
  return {
    open(id) { set(id); },
    toggle(id) { if (allowed.has(id)) set(openId === id ? "" : id); },
    current() { return openId; }
  };
}

const init = async () => {
  const buttons = [...document.querySelectorAll("[data-index-target]")];
  const panels = [...document.querySelectorAll("[data-index-panel]")];
  const ids = buttons.map((button) => button.dataset.indexTarget);
  const controller = createDisclosureController({
    ids,
    onChange: ({ openId }) => {
      buttons.forEach((button) => button.setAttribute("aria-expanded", String(button.dataset.indexTarget === openId)));
      panels.forEach((panel) => { panel.hidden = panel.dataset.indexPanel !== openId; });
      const nextUrl = openId ? `${location.pathname}#${openId}` : location.pathname;
      history.replaceState(null, "", nextUrl);
    }
  });

  buttons.forEach((button) => button.addEventListener("click", () => controller.toggle(button.dataset.indexTarget)));
  const initial = location.hash.slice(1);
  if (ids.includes(initial)) controller.open(initial);

  const previewAudio = document.querySelector("#preview-audio");
  const backgroundAudio = document.querySelector("#background-audio");
  const soundButton = document.querySelector("#sound-toggle");
  const rows = new Map();
  const media = createMediaController({
    previewAudio,
    backgroundAudio,
    onChange: (state) => {
      rows.forEach((row, id) => row.setState({ active: state.activeBeat === id && state.beatPlaying, progress: 0 }));
      soundButton.textContent = state.backgroundPlaying ? "sound on" : "sound off";
      soundButton.setAttribute("aria-pressed", String(state.backgroundPlaying));
    }
  });

  soundButton.addEventListener("click", async () => {
    backgroundAudio.volume = 0.38;
    try { await media.toggleBackground(); }
    catch { soundButton.textContent = "sound blocked"; }
  });

  previewAudio.addEventListener("timeupdate", () => {
    const state = media.getState();
    const duration = Number.isFinite(previewAudio.duration) ? previewAudio.duration : 30;
    rows.get(state.activeBeat)?.setState({ active: state.beatPlaying, progress: previewAudio.currentTime / duration });
  });

  try {
    const catalog = await loadBeatCatalog("/beats/");
    const homeBeats = document.querySelector("#home-beats");
    const rendered = catalog.beats.slice(0, 3).map((beat) => {
      const row = createBeatRow(beat, { compact: true, onToggle: (item) => media.toggleBeat(item) });
      rows.set(beat.id, row);
      return row.element;
    });
    homeBeats.replaceChildren(...rendered);
    document.querySelector("[data-beat-count]").textContent = `${catalog.beats.length} previews`;
  } catch {
    document.querySelector("#home-beats").textContent = "the beat archive is unavailable right now.";
  }

  await Promise.allSettled([
    renderDrumkits(document.querySelector("#home-drumkits")),
    renderVsts(document.querySelector("#home-vsts"), { limit: 6 })
  ]);
};

if (typeof document !== "undefined") init();
