import { createBeatRow } from "./beat-row.js";
import { loadBeatCatalog } from "./catalog.js";
import { createMediaController } from "./media.js";

export function filterBeats(beats, query) {
  const needle = String(query || "").trim().toLowerCase();
  if (!needle) return beats;
  return beats.filter((beat) => [beat.title, beat.bpm, beat.key].join(" ").toLowerCase().includes(needle));
}

const init = async () => {
  const list = document.querySelector("#beat-list");
  const search = document.querySelector("#beat-search");
  const count = document.querySelector("#beat-count");
  const more = document.querySelector("#load-more");
  const audio = document.querySelector("#preview-audio");
  const rows = new Map();
  let catalog = [];
  let visible = [];
  let rendered = 0;
  const pageSize = 24;

  const media = createMediaController({
    previewAudio: audio,
    onChange: (state) => {
      rows.forEach((row, id) => row.setState({ active: id === state.activeBeat && state.beatPlaying, progress: 0 }));
    }
  });

  const renderNext = () => {
    const fragment = document.createDocumentFragment();
    visible.slice(rendered, rendered + pageSize).forEach((beat) => {
      const row = createBeatRow(beat, { inquiry: true, onToggle: (item) => media.toggleBeat(item) });
      rows.set(beat.id, row);
      fragment.append(row.element);
    });
    list.append(fragment);
    rendered = Math.min(rendered + pageSize, visible.length);
    more.hidden = rendered >= visible.length;
  };

  const reset = () => {
    media.pauseAll();
    rows.clear();
    list.replaceChildren();
    rendered = 0;
    visible = filterBeats(catalog, search.value);
    count.textContent = `${visible.length} preview${visible.length === 1 ? "" : "s"}`;
    if (!visible.length) {
      const empty = document.createElement("p");
      empty.className = "empty-state";
      empty.textContent = "no beats match that search.";
      list.append(empty);
      more.hidden = true;
      return;
    }
    renderNext();
  };

  more.addEventListener("click", renderNext);
  search.addEventListener("input", reset);
  audio.addEventListener("timeupdate", () => {
    const state = media.getState();
    const duration = Number.isFinite(audio.duration) ? audio.duration : 30;
    rows.get(state.activeBeat)?.setState({ active: state.beatPlaying, progress: audio.currentTime / duration });
  });

  try {
    const loaded = await loadBeatCatalog("/beats/");
    catalog = loaded.beats;
    reset();
  } catch {
    count.textContent = "archive unavailable";
    const error = document.createElement("p");
    error.className = "empty-state";
    error.textContent = "the beat archive could not load. email or dm for current work.";
    list.replaceChildren(error);
  }
};

if (typeof document !== "undefined") init();
