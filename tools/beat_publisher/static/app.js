const token = document.querySelector('meta[name="publisher-token"]').content;
const state = { beats: [], selected: null, publish: {}, timer: null, reviewId: "" };
const $ = (selector) => document.querySelector(selector);

async function request(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("X-Beat-Publisher-Token", token);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(path, { ...options, headers });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "request failed");
  return data;
}

function log(message) { $("#activity").textContent = message; }
function selectedBeat() { return state.beats.find((beat) => beat.id === state.selected); }
function formatTime(value) {
  const minutes = Math.floor(value / 60).toString().padStart(2, "0");
  const seconds = (value % 60).toFixed(1).padStart(4, "0");
  return `${minutes}:${seconds}`;
}

function renderQueue() {
  const query = $("#search").value.trim().toLowerCase();
  const status = $("#status-filter").value;
  const filtered = state.beats.filter((beat) => {
    const matches = !query || `${beat.title} ${beat.bpm} ${beat.key}`.toLowerCase().includes(query);
    return matches && (!status || beat.status === status);
  });
  $("#queue-count").textContent = `${filtered.length} file${filtered.length === 1 ? "" : "s"}`;
  const queue = $("#queue");
  queue.replaceChildren();
  if (!filtered.length) {
    const message = document.createElement("p");
    message.className = "empty-state";
    message.textContent = state.beats.length ? "no matching beats." : "your batch queue is empty.";
    queue.append(message);
    return;
  }
  filtered.forEach((beat) => {
    const row = document.createElement("article");
    row.className = `queue-item${beat.id === state.selected ? " active" : ""}`;
    row.draggable = true;
    row.dataset.id = beat.id;
    const drag = document.createElement("span");
    drag.className = "drag";
    drag.textContent = "::";
    const copy = document.createElement("div");
    const title = document.createElement("h3");
    title.textContent = beat.title;
    const meta = document.createElement("p");
    meta.textContent = [beat.bpm ? `${beat.bpm} bpm` : "bpm?", beat.key || "key?", beat.status].join(" / ");
    copy.append(title, meta);
    const controls = document.createElement("div");
    controls.className = "order-buttons";
    ["up", "down"].forEach((direction) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = direction === "up" ? "^" : "v";
      button.title = `move ${direction}`;
      button.addEventListener("click", (event) => { event.stopPropagation(); moveBeat(beat.id, direction); });
      controls.append(button);
    });
    const dot = document.createElement("span");
    dot.className = `status-dot ${beat.status}`;
    controls.append(dot);
    row.append(drag, copy, controls);
    row.addEventListener("click", () => selectBeat(beat.id));
    row.addEventListener("dragstart", (event) => event.dataTransfer.setData("text/plain", beat.id));
    row.addEventListener("dragover", (event) => event.preventDefault());
    row.addEventListener("drop", (event) => { event.preventDefault(); reorder(event.dataTransfer.getData("text/plain"), beat.id); });
    queue.append(row);
  });
}

function renderSummary() {
  const count = (status) => state.beats.filter((beat) => beat.status === status).length;
  $("#draft-count").textContent = count("draft");
  $("#ready-count").textContent = count("ready");
  $("#live-count").textContent = count("published");
  $("#publish-state").textContent = state.publish.state || "saved locally";
  $("#save-state").textContent = state.publish.state || "saved locally";
  $("#retry-push").hidden = state.publish.state !== "push_required";
}

function drawWaveform(beat) {
  const canvas = $("#waveform");
  const ratio = window.devicePixelRatio || 1;
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  const context = canvas.getContext("2d");
  context.scale(ratio, ratio);
  context.fillStyle = "#fff";
  context.fillRect(0, 0, width, height);
  const maxStart = Math.max(0, beat.source_duration - 30);
  const selectionX = maxStart ? beat.preview_start / beat.source_duration * width : 0;
  const selectionWidth = Math.min(width, 30 / Math.max(30, beat.source_duration) * width);
  context.fillStyle = "rgba(230,32,39,.12)";
  context.fillRect(selectionX, 0, selectionWidth, height);
  const peaks = beat.source_peaks.length ? beat.source_peaks : Array(240).fill(12);
  context.fillStyle = "#0a0a0a";
  peaks.forEach((peak, index) => {
    const barHeight = Math.max(1, peak / 255 * (height - 28));
    const x = index / peaks.length * width;
    context.fillRect(x, (height - barHeight) / 2, Math.max(1, width / peaks.length - 1), barHeight);
  });
  context.strokeStyle = "#e62027";
  context.lineWidth = 2;
  context.strokeRect(selectionX + 1, 1, Math.max(2, selectionWidth - 2), height - 2);
  $("#range-label").textContent = `${formatTime(beat.preview_start)} - ${formatTime(beat.preview_start + 30)}`;
}

function renderEditor() {
  const beat = selectedBeat();
  $("#empty-editor").hidden = Boolean(beat);
  $("#editor").hidden = !beat;
  if (!beat) return;
  $("#title").value = beat.title;
  $("#bpm").value = beat.bpm;
  $("#key").value = beat.key;
  $("#slug").value = beat.slug;
  $("#normalize").checked = beat.normalize;
  $("#visibility").value = beat.status;
  $("#start").max = Math.max(0, beat.source_duration - 30);
  $("#start").value = beat.preview_start;
  $("#warnings").textContent = beat.warnings.join(" / ");
  $("#preview-play").disabled = !beat.preview_path;
  drawWaveform(beat);
}

function render() { renderQueue(); renderEditor(); renderSummary(); }
function selectBeat(id) { state.selected = id; render(); }

async function load() {
  const data = await request(`/api/state?token=${encodeURIComponent(token)}`);
  state.beats = data.beats;
  state.publish = data.publish;
  if (!state.selected && state.beats.length) state.selected = state.beats[0].id;
  render();
}

async function saveBeat(changes, immediate = false) {
  const beat = selectedBeat();
  if (!beat) return;
  Object.assign(beat, changes);
  renderQueue();
  renderSummary();
  clearTimeout(state.timer);
  const send = async () => {
    try {
      const data = await request(`/api/beats/${beat.id}`, { method: "PATCH", body: JSON.stringify(changes) });
      Object.assign(beat, data.beat);
      $("#save-state").textContent = "saved locally";
    } catch (error) { log(error.message); }
  };
  $("#save-state").textContent = "saving...";
  if (immediate) await send(); else state.timer = setTimeout(send, 250);
}

async function setOrder(ids) {
  const data = await request("/api/order", { method: "POST", body: JSON.stringify({ ids }) });
  state.beats = data.beats;
  render();
}

function moveBeat(id, direction) {
  const ids = state.beats.map((beat) => beat.id);
  const from = ids.indexOf(id);
  const to = Math.max(0, Math.min(ids.length - 1, from + (direction === "up" ? -1 : 1)));
  if (from === to) return;
  ids.splice(to, 0, ids.splice(from, 1)[0]);
  setOrder(ids).catch((error) => log(error.message));
}

function reorder(sourceId, targetId) {
  if (!sourceId || sourceId === targetId) return;
  const ids = state.beats.map((beat) => beat.id);
  ids.splice(ids.indexOf(targetId), 0, ids.splice(ids.indexOf(sourceId), 1)[0]);
  setOrder(ids).catch((error) => log(error.message));
}

$("#wav-files").addEventListener("change", async (event) => {
  if (!event.target.files.length) return;
  const form = new FormData();
  [...event.target.files].forEach((file) => form.append("files", file));
  log(`analyzing ${event.target.files.length} wav file${event.target.files.length === 1 ? "" : "s"}...`);
  try {
    const data = await request("/api/import", { method: "POST", body: form });
    state.beats = data.beats;
    state.publish = data.publish;
    const imported = data.results.filter((result) => result.state === "imported");
    if (imported.length) state.selected = imported[0].beat_id;
    log(data.results.map((result) => result.error || `${result.state}: ${result.beat_id}`).join("\n"));
    render();
  } catch (error) { log(error.message); }
  event.target.value = "";
});

["title", "bpm", "key", "slug"].forEach((id) => $("#" + id).addEventListener("input", (event) => saveBeat({ [id]: event.target.value })));
$("#normalize").addEventListener("change", (event) => saveBeat({ normalize: event.target.checked }));
$("#visibility").addEventListener("change", (event) => saveBeat({ status: event.target.value }, true));
$("#start").addEventListener("input", (event) => {
  const beat = selectedBeat();
  beat.preview_start = Number(event.target.value);
  drawWaveform(beat);
  saveBeat({ preview_start: beat.preview_start });
});
$("#smart").addEventListener("click", () => {
  const beat = selectedBeat();
  beat.preview_start = beat.suggested_start;
  $("#start").value = beat.preview_start;
  drawWaveform(beat);
  saveBeat({ preview_start: beat.preview_start });
});
$("#waveform").addEventListener("pointerdown", (event) => {
  const beat = selectedBeat();
  const bounds = event.currentTarget.getBoundingClientRect();
  const start = Math.max(0, Math.min(beat.source_duration - 30, (event.clientX - bounds.left) / bounds.width * beat.source_duration - 15));
  beat.preview_start = Math.round(start * 10) / 10;
  $("#start").value = beat.preview_start;
  drawWaveform(beat);
  saveBeat({ preview_start: beat.preview_start });
});
$("#waveform").addEventListener("keydown", (event) => {
  if (!['ArrowLeft', 'ArrowRight'].includes(event.key)) return;
  event.preventDefault();
  const beat = selectedBeat();
  const delta = (event.shiftKey ? 1 : .1) * (event.key === 'ArrowLeft' ? -1 : 1);
  beat.preview_start = Math.max(0, Math.min(beat.source_duration - 30, Math.round((beat.preview_start + delta) * 10) / 10));
  $("#start").value = beat.preview_start;
  drawWaveform(beat);
  saveBeat({ preview_start: beat.preview_start });
});

$("#source-play").addEventListener("click", () => {
  const beat = selectedBeat();
  $("#audio").src = `/api/audio/${beat.id}?kind=source&token=${encodeURIComponent(token)}`;
  $("#audio").currentTime = beat.preview_start;
  $("#audio").play();
});
$("#make-preview").addEventListener("click", async () => {
  const beat = selectedBeat();
  log(`encoding ${beat.title}...`);
  try {
    const data = await request(`/api/beats/${beat.id}/preview`, { method: "POST", body: "{}" });
    Object.assign(beat, data.beat);
    $("#audio").src = data.url;
    $("#preview-play").disabled = false;
    log("encoded preview ready. listen before approval.");
    renderEditor();
  } catch (error) { log(error.message); }
});
$("#preview-play").addEventListener("click", () => {
  const beat = selectedBeat();
  $("#audio").src = `/api/audio/${beat.id}?kind=preview&token=${encodeURIComponent(token)}`;
  $("#audio").play();
});
$("#approve").addEventListener("click", async () => {
  const beat = selectedBeat();
  try {
    const data = await request(`/api/beats/${beat.id}/approve`, { method: "POST", body: "{}" });
    Object.assign(beat, data.beat);
    const index = state.beats.findIndex((item) => item.id === beat.id);
    state.selected = state.beats[index + 1]?.id || beat.id;
    log(`${beat.title} is ready.`);
    render();
  } catch (error) { log(error.message); }
});

$("#search").addEventListener("input", renderQueue);
$("#status-filter").addEventListener("change", renderQueue);
$("#review-publish").addEventListener("click", async () => {
  try {
    await new Promise((resolve) => setTimeout(resolve, 300));
    const data = await request("/api/publish/prepare", { method: "POST", body: "{}" });
    state.reviewId = data.review.id;
    $("#review-summary").textContent = `${data.review.ready} ready / ${data.review.visible} public / ${data.review.removals} removed or hidden`;
    $("#publish-dialog").showModal();
  } catch (error) { log(error.message); }
});
$("#confirm-publish").addEventListener("click", async () => {
  $("#publish-dialog").close();
  log("validating, committing, and pushing...");
  try {
    const data = await request("/api/publish/confirm", { method: "POST", body: JSON.stringify({ reviewId: state.reviewId }) });
    state.beats = data.beats;
    state.publish = data.publish;
    log(data.result.error || `pushed commit ${data.result.commit}`);
    render();
  } catch (error) { log(error.message); }
});
$("#retry-push").addEventListener("click", async () => {
  try {
    const data = await request("/api/publish/retry", { method: "POST", body: "{}" });
    state.publish = data.publish;
    log(`pushed commit ${data.result.commit}`);
    renderSummary();
  } catch (error) { log(error.message); }
});
window.addEventListener("resize", () => { if (selectedBeat()) drawWaveform(selectedBeat()); });

load().catch((error) => log(error.message));
