import assert from "node:assert/strict";
import test from "node:test";

import { formatBeatMeta, loadBeatCatalog, normalizeCatalog } from "../../assets/js/catalog.js";

test("normalizes the legacy array without changing order", () => {
  const catalog = normalizeCatalog([
    { title: "first", bpm: "153", key: "d# min", slug: "first", preview: "previews/first.mp3" },
    { title: "second", bpm: "", key: "", slug: "second", preview: "previews/second.mp3" }
  ]);

  assert.equal(catalog.schemaVersion, 0);
  assert.deepEqual(catalog.beats.map((beat) => beat.order), [0, 1]);
  assert.deepEqual(catalog.beats[0].peaks, []);
  assert.equal(formatBeatMeta(catalog.beats[0]), "153 bpm / d# min");
});

test("accepts schema 1 and rejects unsupported schemas", () => {
  const catalog = normalizeCatalog({
    schemaVersion: 1,
    revision: "abc",
    publishedAt: "2026-09-16T00:00:00Z",
    beats: []
  });

  assert.equal(catalog.revision, "abc");
  assert.throws(() => normalizeCatalog({ schemaVersion: 2, beats: [] }), /unsupported catalog schema/);
});

test("falls back to beats.json when catalog.json is absent", async () => {
  const requested = [];
  const fetchImpl = async (url) => {
    requested.push(url);
    return url.endsWith("catalog.json")
      ? { ok: false, status: 404 }
      : { ok: true, json: async () => [{ title: "legacy", slug: "legacy", preview: "previews/legacy.mp3" }] };
  };

  const catalog = await loadBeatCatalog("/beats/", fetchImpl);

  assert.deepEqual(requested, ["/beats/catalog.json", "/beats/beats.json"]);
  assert.equal(catalog.beats[0].title, "legacy");
});
