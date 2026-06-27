const list = document.querySelector("#beat-list");
const template = document.querySelector("#beat-template");
const count = document.querySelector("#beat-count");
let activeAudio = null;

const formatMeta = (beat) => {
  const bits = [];
  if (beat.bpm) bits.push(`${beat.bpm} bpm`);
  if (beat.key) bits.push(beat.key);
  return bits.join(" / ") || "preview";
};

const drawFallback = (canvas) => {
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = "rgba(255, 28, 28, 0.9)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  for (let x = 0; x < width; x += 8) {
    const value = Math.sin(x * 0.05) * Math.sin(x * 0.013);
    const y = height / 2 + value * height * 0.34;
    if (x === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();
};

const drawWaveform = async (canvas, src) => {
  const ctx = canvas.getContext("2d");
  try {
    const response = await fetch(src);
    const buffer = await response.arrayBuffer();
    const audioContext = new AudioContext();
    const audioBuffer = await audioContext.decodeAudioData(buffer);
    const data = audioBuffer.getChannelData(0);
    const width = canvas.width;
    const height = canvas.height;
    const step = Math.ceil(data.length / width);
    const middle = height / 2;

    ctx.clearRect(0, 0, width, height);
    ctx.fillStyle = "rgba(255, 28, 28, 0.08)";
    ctx.fillRect(0, 0, width, height);
    ctx.strokeStyle = "rgba(255, 28, 28, 0.96)";
    ctx.lineWidth = 2;

    for (let i = 0; i < width; i += 1) {
      let min = 1;
      let max = -1;
      for (let j = 0; j < step; j += 1) {
        const datum = data[i * step + j] || 0;
        if (datum < min) min = datum;
        if (datum > max) max = datum;
      }
      ctx.beginPath();
      ctx.moveTo(i, middle + min * middle * 0.82);
      ctx.lineTo(i, middle + max * middle * 0.82);
      ctx.stroke();
    }

    await audioContext.close();
  } catch {
    drawFallback(canvas);
  }
};

const renderBeat = (beat) => {
  const node = template.content.cloneNode(true);
  const card = node.querySelector(".beat-card");
  const title = node.querySelector("h3");
  const meta = node.querySelector(".beat-meta p");
  const audio = node.querySelector("audio");
  const button = node.querySelector(".play-button");
  const canvas = node.querySelector("canvas");

  title.textContent = beat.title || "untitled";
  meta.textContent = formatMeta(beat);
  audio.src = beat.preview;

  button.addEventListener("click", async () => {
    if (activeAudio && activeAudio !== audio) {
      activeAudio.pause();
      activeAudio.currentTime = 0;
      document.querySelectorAll(".play-button").forEach((btn) => {
        if (btn !== button) btn.textContent = "play";
      });
    }

    if (audio.paused) {
      activeAudio = audio;
      await audio.play();
      button.textContent = "pause";
      card.classList.add("playing");
      return;
    }

    audio.pause();
    button.textContent = "play";
    card.classList.remove("playing");
  });

  audio.addEventListener("ended", () => {
    button.textContent = "play";
    card.classList.remove("playing");
  });

  drawWaveform(canvas, beat.preview);
  return node;
};

const loadBeats = async () => {
  try {
    const response = await fetch("beats.json", { cache: "no-store" });
    if (!response.ok) throw new Error("missing beats.json");
    const beats = await response.json();
    list.innerHTML = "";

    if (!beats.length) {
      count.textContent = "0 previews";
      list.innerHTML = '<p class="empty">no previews in the bin yet.</p>';
      return;
    }

    count.textContent = `${beats.length} preview${beats.length === 1 ? "" : "s"}`;
    beats.forEach((beat) => list.appendChild(renderBeat(beat)));
  } catch {
    count.textContent = "0 previews";
    list.innerHTML = '<p class="error">beats.json is not ready yet. use the local publisher app to export previews.</p>';
  }
};

loadBeats();
