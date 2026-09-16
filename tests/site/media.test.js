import assert from "node:assert/strict";
import test from "node:test";

import { createMediaController } from "../../assets/js/media.js";
import { normalizePeaks } from "../../assets/js/waveform.js";

class FakeAudio {
  constructor() {
    this.src = "";
    this.paused = true;
    this.currentTime = 0;
  }

  async play() {
    this.paused = false;
  }

  pause() {
    this.paused = true;
  }
}

test("assigns preview audio only after play is requested", async () => {
  const previewAudio = new FakeAudio();
  const backgroundAudio = new FakeAudio();
  backgroundAudio.paused = false;
  const media = createMediaController({ previewAudio, backgroundAudio });

  assert.equal(previewAudio.src, "");
  await media.toggleBeat({ id: "one", preview: "previews/one.mp3" });

  assert.equal(previewAudio.src, "previews/one.mp3");
  assert.equal(backgroundAudio.paused, true);
});

test("starting background sound stops the active beat", async () => {
  const previewAudio = new FakeAudio();
  const backgroundAudio = new FakeAudio();
  const media = createMediaController({ previewAudio, backgroundAudio });

  await media.toggleBeat({ id: "one", preview: "previews/one.mp3" });
  await media.toggleBackground();

  assert.equal(previewAudio.paused, true);
  assert.equal(backgroundAudio.paused, false);
});

test("normalizes sparse and overlong peak arrays", () => {
  assert.deepEqual(normalizePeaks([], 4), [0.18, 0.18, 0.18, 0.18]);
  assert.equal(normalizePeaks([0, 255, 128, 64, 32], 3).length, 3);
});
