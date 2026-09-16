import assert from "node:assert/strict";
import test from "node:test";

import { filterBeats } from "../../assets/js/beats.js";

const beats = [
  { title: "needlework", bpm: "153", key: "d# min" },
  { title: "throneoccupier", bpm: "142", key: "f min" }
];

test("searches title, bpm, and key", () => {
  assert.equal(filterBeats(beats, "needle").length, 1);
  assert.equal(filterBeats(beats, "142").length, 1);
  assert.equal(filterBeats(beats, "d# min").length, 1);
});

test("empty search preserves catalog order", () => {
  assert.deepEqual(filterBeats(beats, ""), beats);
});
