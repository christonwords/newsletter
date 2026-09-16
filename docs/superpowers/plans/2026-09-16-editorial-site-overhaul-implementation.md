# Editorial Site Overhaul Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current dark card site with the approved gallery-white living editorial index and complete beats, drumkits, and go to vsts archive routes without interrupting the current beat catalog.

**Architecture:** The site stays build-free and static on GitHub Pages. Shared CSS and small ES modules own the design system, collection rendering, beat-catalog compatibility, waveform drawing, and media coordination. The beat loader accepts both the current array-shaped `beats/beats.json` and the publisher v2 `beats/catalog.json`, allowing this plan to ship before the publisher rewrite.

**Tech Stack:** HTML5, CSS, browser ES modules, Canvas 2D, JSON, Node built-in test runner, Playwright Chromium, Python static server.

**Spec:** `docs/superpowers/specs/2026-09-16-site-publisher-overhaul-design.md`

## Global Constraints

- Host only static files on GitHub Pages; add no paid backend or runtime service.
- Keep all authored public copy lowercase, except machine-readable metadata and the A2V logo bitmap.
- Use `#fafaf8` paper, `#090909` ink, `#e62027` signal red, `#6f6f69` muted text, `#efefeb` soft field, and `#171717` rules.
- Use red only for section indices, active playback, selection, availability, warnings, and primary actions.
- Add no gradients, glow, decorative shadows, glass panels, pill-heavy controls, or page-wide animation loops.
- Preserve `softparish@gmail.com`, `@christonwords`, the Payhip product URLs, and the existing background audio file.
- Keep background audio opt-in and off by default; a beat preview and background audio may never play together.
- Preserve the A2V product page as a separate dark launch experience and keep its buy URL `https://payhip.com/b/98Wpa`.
- Respect `prefers-reduced-motion`, visible keyboard focus, semantic controls, and mobile layouts without horizontal overflow.
- Do not remove `beats/beats.json` in this plan; publisher v2 owns the eventual migration.

---

## File Structure

### Shared public assets

- Create `assets/css/base.css`: color tokens, self-hosted fonts, reset, global shell, utility navigation, focus, and reduced-motion rules.
- Create `assets/css/home.css`: identity hero, living index, expanded sections, and home responsive rules.
- Create `assets/css/archive.css`: beats, drumkits, and go to vsts route layouts.
- Create `assets/js/catalog.js`: new and legacy beat-catalog normalization and loading.
- Create `assets/js/media.js`: one shared beat player and optional background-audio coordination.
- Create `assets/js/waveform.js`: peak normalization and Canvas rendering.
- Create `assets/js/home.js`: living-index state, URL hash synchronization, and homepage collection rendering.
- Create `assets/js/beats.js`: archive search, incremental rendering, and playback bindings.
- Create `assets/js/collections.js`: drumkit and VST JSON loading and markup creation.
- Create `assets/fonts/bodoni-moda-latin.woff2`: self-hosted variable display serif from the OFL Bodoni Moda distribution.
- Create `assets/fonts/inter-tight-latin.woff2`: self-hosted variable UI sans from the OFL Inter Tight distribution.
- Create `assets/fonts/OFL-bodoni-moda.txt` and `assets/fonts/OFL-inter-tight.txt`: upstream font licenses.

### Content and routes

- Rewrite `index.html`: gallery-white identity shell and five-row expandable index.
- Rewrite `beats/index.html`: complete searchable beat archive.
- Create `drumkits/index.html`: complete drumkit archive.
- Create `vsts/index.html`: complete go to vsts contact sheet.
- Create `data/drumkits.json`: five current covers and Payhip URLs.
- Create `data/vsts.json`: all 18 current VST image records.
- Modify `a2v/index.html`: lowercase authored copy and an explicit back-to-christon route.
- Modify `a2v/styles.css`: visible back-link treatment and removal of uppercase text transforms from authored labels.
- Delete `styles.css`, `script.js`, `beats/styles.css`, and `beats/script.js` only after no HTML file references them.

### Tests and tooling

- Create `package.json`: Node tests and Playwright scripts.
- Create `playwright.config.js`: local static-server configuration for desktop and mobile Chromium.
- Create `tests/site/catalog.test.js`: catalog compatibility tests.
- Create `tests/site/media.test.js`: lazy playback and mutual-exclusion tests.
- Create `tests/site/home.spec.js`: homepage semantics, expansion, hash, audio, and responsive tests.
- Create `tests/site/beats.spec.js`: search, incremental rendering, waveform, and lazy MP3 tests.
- Create `tests/site/collections.spec.js`: drumkit, VST, and A2V route tests.

---

### Task 1: Catalog Compatibility Layer

**Files:**
- Create: `package.json`
- Create: `assets/js/catalog.js`
- Create: `tests/site/catalog.test.js`

**Interfaces:**
- Consumes: legacy array records from `beats/beats.json` and schema-1 objects from `beats/catalog.json`.
- Produces: `normalizeCatalog(payload): BeatCatalog`, `loadBeatCatalog(baseUrl, fetchImpl): Promise<BeatCatalog>`, and `formatBeatMeta(beat): string`.
- `BeatCatalog` is `{ schemaVersion: number, revision: string, publishedAt: string, beats: Beat[] }`.
- `Beat` is `{ id, slug, title, bpm, key, preview, duration, order, peaks }`; `peaks` is an integer array and may be empty for legacy entries.

- [ ] **Step 1: Add the Node test scripts and write failing compatibility tests**

```json
{
  "private": true,
  "type": "module",
  "scripts": {
    "test": "node --test tests/site/*.test.js",
    "test:e2e": "playwright test"
  }
}
```

```js
// tests/site/catalog.test.js
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
  const catalog = normalizeCatalog({ schemaVersion: 1, revision: "abc", publishedAt: "2026-09-16T00:00:00Z", beats: [] });
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
```

- [ ] **Step 2: Run the catalog tests and verify the missing module failure**

Run: `node --test tests/site/catalog.test.js`

Expected: FAIL with `ERR_MODULE_NOT_FOUND` for `assets/js/catalog.js`.

- [ ] **Step 3: Implement normalization, validation, fallback loading, and metadata formatting**

```js
// assets/js/catalog.js
const asBeat = (beat, order) => ({
  id: String(beat.id || beat.slug || `beat-${order}`),
  slug: String(beat.slug || ""),
  title: String(beat.title || beat.slug || "untitled").toLowerCase(),
  bpm: String(beat.bpm || ""),
  key: String(beat.key || "").toLowerCase(),
  preview: String(beat.preview || ""),
  duration: Number(beat.duration || 30),
  order: Number.isInteger(beat.order) ? beat.order : order,
  peaks: Array.isArray(beat.peaks) ? beat.peaks.map(Number) : []
});

export function normalizeCatalog(payload) {
  if (Array.isArray(payload)) {
    return { schemaVersion: 0, revision: "legacy", publishedAt: "", beats: payload.map(asBeat) };
  }
  if (!payload || payload.schemaVersion !== 1 || !Array.isArray(payload.beats)) {
    throw new Error("unsupported catalog schema");
  }
  return { ...payload, beats: payload.beats.map(asBeat).sort((a, b) => a.order - b.order) };
}

export async function loadBeatCatalog(baseUrl = "/beats/", fetchImpl = fetch) {
  for (const filename of ["catalog.json", "beats.json"]) {
    const response = await fetchImpl(`${baseUrl}${filename}`, { cache: "no-store" });
    if (response.ok) return normalizeCatalog(await response.json());
    if (response.status !== 404) throw new Error(`catalog request failed: ${response.status}`);
  }
  throw new Error("beat catalog is unavailable");
}

export function formatBeatMeta(beat) {
  return [beat.bpm ? `${beat.bpm} bpm` : "", beat.key].filter(Boolean).join(" / ") || "preview";
}
```

- [ ] **Step 4: Run the catalog tests and verify all pass**

Run: `node --test tests/site/catalog.test.js`

Expected: 3 tests pass, 0 fail.

- [ ] **Step 5: Commit the compatibility layer**

```powershell
git add package.json assets/js/catalog.js tests/site/catalog.test.js
git commit -m "add compatible beat catalog loader"
```

### Task 2: Shared Media Controller And Waveforms

**Files:**
- Create: `assets/js/media.js`
- Create: `assets/js/waveform.js`
- Create: `tests/site/media.test.js`

**Interfaces:**
- Consumes: normalized `Beat` records from Task 1 and optional background `<audio>`.
- Produces: `createMediaController({ previewAudio, backgroundAudio, onChange })`, returning `toggleBeat(beat)`, `toggleBackground()`, `pauseAll()`, and `getState()`.
- Produces: `normalizePeaks(peaks, count): number[]` and `drawWaveform(canvas, peaks, progress, active): void`.

- [ ] **Step 1: Write failing tests for lazy source assignment and exclusive playback**

```js
// tests/site/media.test.js
import assert from "node:assert/strict";
import test from "node:test";
import { createMediaController } from "../../assets/js/media.js";
import { normalizePeaks } from "../../assets/js/waveform.js";

class FakeAudio {
  constructor() { this.src = ""; this.paused = true; this.currentTime = 0; }
  async play() { this.paused = false; }
  pause() { this.paused = true; }
}

test("assigns preview audio only after play is requested", async () => {
  const previewAudio = new FakeAudio();
  const backgroundAudio = new FakeAudio();
  backgroundAudio.paused = false;
  const media = createMediaController({ previewAudio, backgroundAudio, onChange() {} });
  assert.equal(previewAudio.src, "");
  await media.toggleBeat({ id: "one", preview: "previews/one.mp3" });
  assert.equal(previewAudio.src, "previews/one.mp3");
  assert.equal(backgroundAudio.paused, true);
});

test("starting background sound stops the active beat", async () => {
  const previewAudio = new FakeAudio();
  const backgroundAudio = new FakeAudio();
  const media = createMediaController({ previewAudio, backgroundAudio, onChange() {} });
  await media.toggleBeat({ id: "one", preview: "previews/one.mp3" });
  await media.toggleBackground();
  assert.equal(previewAudio.paused, true);
  assert.equal(backgroundAudio.paused, false);
});

test("normalizes sparse and overlong peak arrays", () => {
  assert.deepEqual(normalizePeaks([], 4), [0.18, 0.18, 0.18, 0.18]);
  assert.equal(normalizePeaks([0, 255, 128, 64, 32], 3).length, 3);
});
```

- [ ] **Step 2: Run the media tests and verify they fail on missing modules**

Run: `node --test tests/site/media.test.js`

Expected: FAIL with missing `media.js` or `waveform.js`.

- [ ] **Step 3: Implement the shared controller and Canvas renderer**

```js
// assets/js/media.js
export function createMediaController({ previewAudio, backgroundAudio = null, onChange = () => {} }) {
  let activeBeat = null;
  const emit = () => onChange({ activeBeat, beatPlaying: !previewAudio.paused, backgroundPlaying: Boolean(backgroundAudio && !backgroundAudio.paused) });
  return {
    async toggleBeat(beat) {
      if (backgroundAudio) backgroundAudio.pause();
      if (activeBeat === beat.id && !previewAudio.paused) previewAudio.pause();
      else {
        if (previewAudio.src !== beat.preview) { previewAudio.src = beat.preview; previewAudio.currentTime = 0; }
        activeBeat = beat.id;
        await previewAudio.play();
      }
      emit();
    },
    async toggleBackground() {
      if (!backgroundAudio) return;
      previewAudio.pause();
      activeBeat = null;
      if (backgroundAudio.paused) await backgroundAudio.play(); else backgroundAudio.pause();
      emit();
    },
    pauseAll() { previewAudio.pause(); if (backgroundAudio) backgroundAudio.pause(); emit(); },
    getState() { return { activeBeat, beatPlaying: !previewAudio.paused, backgroundPlaying: Boolean(backgroundAudio && !backgroundAudio.paused) }; }
  };
}
```

`waveform.js` must clamp peaks to `0..255`, resample to the requested bar count, render legacy fallback bars without fetching MP3 data, and paint elapsed bars red according to `progress`.

- [ ] **Step 4: Run all Node tests**

Run: `npm test`

Expected: 6 tests pass, 0 fail.

- [ ] **Step 5: Commit the media foundation**

```powershell
git add assets/js/media.js assets/js/waveform.js tests/site/media.test.js
git commit -m "add shared audio and waveform controls"
```

### Task 3: Gallery-White Foundation And Identity Shell

**Files:**
- Create: `assets/css/base.css`
- Create: `assets/css/home.css`
- Create: `assets/fonts/bodoni-moda-latin.woff2`
- Create: `assets/fonts/inter-tight-latin.woff2`
- Create: `assets/fonts/OFL-bodoni-moda.txt`
- Create: `assets/fonts/OFL-inter-tight.txt`
- Rewrite: `index.html`
- Create: `playwright.config.js`
- Create: `tests/site/home.spec.js`

**Interfaces:**
- Consumes: the color and type tokens in the approved spec.
- Produces: reusable `.site-shell`, `.utility-nav`, `.wordmark`, `.content-index`, `.index-row`, and `.index-panel` classes.
- Produces: a homepage with five collapsed semantic disclosure rows before JavaScript enhancement.

- [ ] **Step 1: Install Playwright, self-hosted font packages, and Chromium**

Run: `npm install --save-dev @playwright/test @fontsource-variable/bodoni-moda @fontsource-variable/inter-tight`

Expected: `package-lock.json` is created and dependency installation exits 0.

Run: `npx playwright install chromium`

Expected: Chromium installation exits 0.

- [ ] **Step 2: Write failing shell and mobile-overflow tests**

```js
// tests/site/home.spec.js
import { expect, test } from "@playwright/test";

test("presents christon before the collection index", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("heading", { level: 1, name: "christon" })).toBeVisible();
  await expect(page.locator(".index-row")).toHaveCount(5);
  await expect(page.locator(".index-row button[aria-expanded='false']")).toHaveCount(5);
  await expect(page.locator("body")).toHaveCSS("background-color", "rgb(250, 250, 248)");
});

test("does not overflow a narrow viewport", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/");
  const sizes = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, client: document.documentElement.clientWidth }));
  expect(sizes.scroll).toBeLessThanOrEqual(sizes.client);
});
```

```js
// playwright.config.js
import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
  testDir: "tests/site",
  webServer: { command: "python -m http.server 4173", port: 4173, reuseExistingServer: true },
  use: { baseURL: "http://127.0.0.1:4173" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 7"] } }
  ]
});
```

- [ ] **Step 3: Run the homepage test and verify the old page fails the new contract**

Run: `npx playwright test tests/site/home.spec.js --project=desktop`

Expected: FAIL because `.index-row` and the gallery-white background do not exist.

- [ ] **Step 4: Add licensed fonts and implement the static homepage shell**

Copy `bodoni-moda-latin-wght-normal.woff2` and `inter-tight-latin-wght-normal.woff2` from the installed Fontsource packages into the planned `assets/fonts/` names. Copy each package's `LICENSE` file into the corresponding planned OFL text file. Confirm the copied WOFF2 paths exist before writing CSS. Define them locally:

```powershell
New-Item -ItemType Directory -Path assets\fonts -Force | Out-Null
Copy-Item node_modules\@fontsource-variable\bodoni-moda\files\bodoni-moda-latin-wght-normal.woff2 assets\fonts\bodoni-moda-latin.woff2
Copy-Item node_modules\@fontsource-variable\inter-tight\files\inter-tight-latin-wght-normal.woff2 assets\fonts\inter-tight-latin.woff2
Copy-Item node_modules\@fontsource-variable\bodoni-moda\LICENSE assets\fonts\OFL-bodoni-moda.txt
Copy-Item node_modules\@fontsource-variable\inter-tight\LICENSE assets\fonts\OFL-inter-tight.txt
```

```css
@font-face { font-family:"bodoni moda"; src:url("../fonts/bodoni-moda-latin.woff2") format("woff2"); font-weight:400 900; font-display:swap; }
@font-face { font-family:"inter tight"; src:url("../fonts/inter-tight-latin.woff2") format("woff2"); font-weight:400 800; font-display:swap; }
:root { --paper:#fafaf8; --ink:#090909; --red:#e62027; --muted:#6f6f69; --field:#efefeb; --rule:#171717; }
```

Rewrite `index.html` with the utility row, `h1` wordmark, statement, five real disclosure buttons, associated panels, one hidden shared preview `<audio>`, and the existing opt-in background `<audio>`. Keep panels collapsed but useful without scripting through links inside each panel.

- [ ] **Step 5: Run the shell tests on desktop and mobile**

Run: `npx playwright test tests/site/home.spec.js`

Expected: all shell and overflow tests pass in both projects.

- [ ] **Step 6: Commit the visual foundation**

```powershell
git add package.json package-lock.json playwright.config.js assets/css assets/fonts index.html tests/site/home.spec.js
git commit -m "build gallery white identity shell"
```

### Task 4: Living Index And Homepage Collections

**Files:**
- Create: `data/drumkits.json`
- Create: `data/vsts.json`
- Create: `assets/js/collections.js`
- Create: `assets/js/home.js`
- Modify: `index.html`
- Modify: `tests/site/home.spec.js`

**Interfaces:**
- Consumes: `loadBeatCatalog`, `formatBeatMeta`, `createMediaController`, `drawWaveform`, and the two collection JSON files.
- Produces: `openIndexPanel(id, { updateHash }): void`, `renderHomeBeats(beats): void`, `renderHomeDrumkits(items): void`, and `renderHomeVsts(items): void`.
- `data/drumkits.json` records are `{ title, image, url }`.
- `data/vsts.json` records are `{ title, image }`.

- [ ] **Step 1: Add complete collection data**

`data/drumkits.json` must contain these five records in this order:

```json
[
  { "title": "michael drumkit", "image": "/Drumkit Covers & Links/Michael Drumkit.jpg", "url": "https://payhip.com/b/LFezG" },
  { "title": "rolling stone soundkit", "image": "/Drumkit Covers & Links/Rolling Stone Soundkit.jpg", "url": "https://payhip.com/b/4Zgut" },
  { "title": "prosper drumkit", "image": "/Drumkit Covers & Links/Prosper Drumkit.jpg", "url": "https://payhip.com/b/HqM5w" },
  { "title": "trappy drumkit", "image": "/Drumkit Covers & Links/Trappy Drumkit.jpg", "url": "https://payhip.com/b/NWvLx" },
  { "title": "beauty is swxg drumkit", "image": "/Drumkit Covers & Links/Beauty is Swxg Drumkit.jpg", "url": "https://payhip.com/b/p28u7" }
]
```

`data/vsts.json` must contain, in the current public order, `6s montana rack`, `d - 50`, `jd - 800`, `jv - 1080`, `kontakt bank - emu proteus rack`, `kontakt bank - 5000 karat`, `kontakt bank - evolution infinity`, `kontakt bank - history world tour`, `kontakt bank - roland fantom x8`, `kontakt bank - techno rap`, `kontakt bank - trap back`, `kontakt bank - trap motivation 101`, `kontakt bank - yamaha motif pianos`, `lounge lizard`, `pure synth platinum`, `romantic keys`, `studio strings`, and `xv - 5080`. Preserve the existing misspelled EMU filename in its `image` path while displaying the corrected title.

- [ ] **Step 2: Extend the failing homepage tests for disclosure behavior and hashes**

```js
test("keeps one index panel open and synchronizes the hash", async ({ page }) => {
  await page.goto("/");
  await page.getByRole("button", { name: /beats/ }).click();
  await expect(page.locator("#beats-panel")).toBeVisible();
  await expect(page).toHaveURL(/#beats$/);
  await page.getByRole("button", { name: /drumkits/ }).click();
  await expect(page.locator("#beats-panel")).toBeHidden();
  await expect(page.locator("#drumkits-panel")).toBeVisible();
  await expect(page).toHaveURL(/#drumkits$/);
});

test("deep links directly into an expanded row", async ({ page }) => {
  await page.goto("/#vsts");
  await expect(page.locator("#vsts-panel")).toBeVisible();
  await expect(page.locator("#vsts-panel figure")).toHaveCount(6);
});
```

- [ ] **Step 3: Run the new tests and verify the static shell fails interaction**

Run: `npx playwright test tests/site/home.spec.js --project=desktop`

Expected: FAIL because clicks do not change panel state or URL hash.

- [ ] **Step 4: Implement collections and living-index behavior**

`collections.js` must fetch JSON, create elements with `textContent`, set image `loading="lazy"` and useful `alt`, and never inject untrusted strings with `innerHTML`. `home.js` must initialize from `location.hash`, update all `aria-expanded` states, set `hidden` on closed panels, render the first three beats and first six VSTs, and keep the current panel stable after data loads.

Bind the shared media controller so beat play pauses background sound and the sound control stops the beat. Render legacy beat waveforms from deterministic fallback peaks without fetching MP3 data.

- [ ] **Step 5: Run Node and homepage tests**

Run: `npm test`

Expected: all Node tests pass.

Run: `npx playwright test tests/site/home.spec.js`

Expected: all homepage tests pass on desktop and mobile.

- [ ] **Step 6: Commit the living index**

```powershell
git add data assets/js/collections.js assets/js/home.js index.html tests/site/home.spec.js
git commit -m "add living homepage index"
```

### Task 5: Searchable Beat Archive

**Files:**
- Create: `assets/css/archive.css`
- Create: `assets/js/beats.js`
- Rewrite: `beats/index.html`
- Create: `tests/site/beats.spec.js`

**Interfaces:**
- Consumes: `loadBeatCatalog("/beats/")`, `formatBeatMeta`, `createMediaController`, and `drawWaveform`.
- Produces: `filterBeats(beats, query): Beat[]`, `renderNextBatch(): void`, and an archive that renders 24 rows at a time.

- [ ] **Step 1: Write failing archive behavior and network tests**

```js
// tests/site/beats.spec.js
import { expect, test } from "@playwright/test";

const beats = Array.from({ length: 30 }, (_, order) => ({
  id: `beat-${order}`, slug: `beat-${order}`, title: order === 4 ? "needlework" : `beat ${order}`,
  bpm: String(120 + order), key: order === 4 ? "f min" : "c min",
  preview: `previews/beat-${order}.mp3`, duration: 30, order, peaks: [20, 80, 140, 220, 100]
}));

test.beforeEach(async ({ page }) => {
  await page.route("**/beats/catalog.json", (route) => route.fulfill({ json: { schemaVersion: 1, revision: "test", publishedAt: "", beats } }));
});

test("renders 24 beats first and filters all catalog records", async ({ page }) => {
  await page.goto("/beats/");
  await expect(page.locator(".beat-row")).toHaveCount(24);
  await page.getByRole("searchbox").fill("needlework");
  await expect(page.locator(".beat-row")).toHaveCount(1);
  await expect(page.getByRole("heading", { name: "needlework" })).toBeVisible();
});

test("does not request mp3 audio until play", async ({ page }) => {
  const mp3Requests = [];
  page.on("request", (request) => { if (request.url().endsWith(".mp3")) mp3Requests.push(request.url()); });
  await page.goto("/beats/");
  expect(mp3Requests).toHaveLength(0);
  await page.locator(".beat-row").first().getByRole("button", { name: /play/ }).click();
  await expect.poll(() => mp3Requests.length).toBe(1);
});
```

- [ ] **Step 2: Run the archive tests and verify the old archive fails**

Run: `npx playwright test tests/site/beats.spec.js --project=desktop`

Expected: FAIL because the old page downloads audio to draw waveforms and has no searchbox or 24-item batching.

- [ ] **Step 3: Build the editorial archive markup and renderer**

Use one hidden shared `<audio>`, a semantic search input, an `aria-live` result count, a `<template>` for `.beat-row`, a bottom sentinel for incremental rendering, and an error state with direct email and Instagram links. `filterBeats` must match lowercase title, BPM, and key. Clearing search restores manual catalog order.

Use `IntersectionObserver` to append the next 24 rows. If unavailable, show a `load more` button. Canvas redraws on resize and playback updates through `requestAnimationFrame` only while audio plays.

- [ ] **Step 4: Run archive tests on both viewports**

Run: `npx playwright test tests/site/beats.spec.js`

Expected: all archive tests pass on desktop and mobile.

- [ ] **Step 5: Commit the beat archive**

```powershell
git add beats/index.html assets/css/archive.css assets/js/beats.js tests/site/beats.spec.js
git commit -m "rebuild searchable beat archive"
```

### Task 6: Drumkit And Go To VSTs Routes

**Files:**
- Create: `drumkits/index.html`
- Create: `vsts/index.html`
- Modify: `assets/css/archive.css`
- Modify: `assets/js/collections.js`
- Create: `tests/site/collections.spec.js`

**Interfaces:**
- Consumes: `data/drumkits.json`, `data/vsts.json`, and shared archive CSS.
- Produces: `renderDrumkitArchive(container, items): void` and `renderVstArchive(container, items): void`.

- [ ] **Step 1: Write failing route and content tests**

```js
// tests/site/collections.spec.js
import { expect, test } from "@playwright/test";

test("shows all drumkits with direct purchase links", async ({ page }) => {
  await page.goto("/drumkits/");
  await expect(page.locator(".drumkit-item")).toHaveCount(5);
  await expect(page.getByRole("link", { name: /beauty is swxg drumkit/ })).toHaveAttribute("href", "https://payhip.com/b/p28u7");
});

test("shows all vsts without categories or cropped images", async ({ page }) => {
  await page.goto("/vsts/");
  await expect(page.locator(".vst-item")).toHaveCount(18);
  await expect(page.locator("[data-category]")).toHaveCount(0);
  await expect(page.locator(".vst-item img").first()).toHaveCSS("object-fit", "contain");
});
```

- [ ] **Step 2: Run the collection tests and verify both routes return 404**

Run: `npx playwright test tests/site/collections.spec.js --project=desktop`

Expected: FAIL because `/drumkits/` and `/vsts/` do not exist.

- [ ] **Step 3: Implement both routes from shared JSON data**

Each page uses the same utility navigation and title rhythm as `/beats/`. Drumkit links open Payhip in a new tab with `rel="noreferrer"`. VST figures use the complete image, a fixed media track, and one baseline caption. Add concise empty and fetch-error states without filler copy.

- [ ] **Step 4: Run route tests on desktop and mobile**

Run: `npx playwright test tests/site/collections.spec.js`

Expected: all drumkit and VST tests pass.

- [ ] **Step 5: Commit the collection routes**

```powershell
git add drumkits vsts assets/css/archive.css assets/js/collections.js tests/site/collections.spec.js
git commit -m "add drumkit and vst archive routes"
```

### Task 7: A2V Archive Return And Lowercase Copy

**Files:**
- Modify: `a2v/index.html`
- Modify: `a2v/styles.css`
- Modify: `tests/site/collections.spec.js`

**Interfaces:**
- Consumes: the existing A2V page, product imagery, and Payhip URL.
- Produces: an always-visible `back to christon` link and lowercase authored text while preserving the product microsite layout.

- [ ] **Step 1: Add failing A2V navigation and copy tests**

```js
test("keeps a2v purchasable and provides a route back", async ({ page }) => {
  await page.goto("/a2v/");
  await expect(page.getByRole("link", { name: "back to christon" })).toHaveAttribute("href", "../");
  await expect(page.getByRole("link", { name: "buy now" }).first()).toHaveAttribute("href", "https://payhip.com/b/98Wpa");
  const authoredText = await page.locator("body").innerText();
  expect(authoredText).not.toMatch(/A2V|Windows|FFmpeg/);
});
```

- [ ] **Step 2: Run the A2V test and verify it fails on current uppercase content**

Run: `npx playwright test tests/site/collections.spec.js -g "a2v" --project=desktop`

Expected: FAIL because the named back link and lowercase copy contract are absent.

- [ ] **Step 3: Update authored text and navigation without changing product behavior**

Change visible text to `a2v`, `windows`, and `ffmpeg`; leave proper filenames such as `A2V.exe` only where the literal file name is required, but expose them with lowercase visible text. Add the back link to the fixed navigation and preserve the transparent product image and all buy links. Remove CSS `text-transform: uppercase` from labels that would violate the lowercase direction.

- [ ] **Step 4: Run the A2V and full collection tests**

Run: `npx playwright test tests/site/collections.spec.js`

Expected: all tests pass on desktop and mobile.

- [ ] **Step 5: Commit the A2V bridge**

```powershell
git add a2v/index.html a2v/styles.css tests/site/collections.spec.js
git commit -m "connect a2v to the editorial archive"
```

### Task 8: Accessibility, Performance, Cleanup, And Visual Verification

**Files:**
- Modify: `tests/site/home.spec.js`
- Modify: `tests/site/beats.spec.js`
- Modify: `assets/css/base.css`
- Modify: `assets/css/home.css`
- Modify: `assets/css/archive.css`
- Delete: `styles.css`
- Delete: `script.js`
- Delete: `beats/styles.css`
- Delete: `beats/script.js`

**Interfaces:**
- Consumes: every public route completed in Tasks 1-7.
- Produces: final verified static site with no references to legacy CSS or JavaScript.

- [ ] **Step 1: Add failing keyboard, reduced-motion, and network assertions**

Add Playwright coverage that tabs through every index button, opens a row with Enter, closes it with Space, verifies a visible focus outline, emulates reduced motion and checks transition duration, captures all `.mp3` requests before user playback, and checks all pages for `scrollWidth <= clientWidth` at 390px.

- [ ] **Step 2: Run the complete suite and record each failure**

Run: `npm test`

Expected: all unit tests pass.

Run: `npm run test:e2e`

Expected: any remaining focus, motion, overflow, or request failures are reported with a route and assertion.

- [ ] **Step 3: Fix only the reported accessibility and responsive defects**

Use `:focus-visible` with a 2px red outline and 3px offset, keep closed panel controls in the accessibility tree only when appropriate, disable nonessential transitions under reduced motion, and size media with stable aspect ratios. Do not add new visual decoration during this pass.

- [ ] **Step 4: Remove unreferenced legacy files and verify references**

Run: `rg -n "styles\.css|script\.js" --glob "*.html"`

Expected: references resolve only to current route-specific files such as `a2v/styles.css` and `a2v/script.js`; root `styles.css`, root `script.js`, `beats/styles.css`, and `beats/script.js` are absent from output.

Delete only those four confirmed-unreferenced legacy files.

- [ ] **Step 5: Capture and inspect desktop and mobile screenshots**

Run: `npx playwright screenshot --viewport-size="1440,1000" http://127.0.0.1:4173/ artifacts/home-desktop.png`

Run: `npx playwright screenshot --device="Pixel 7" http://127.0.0.1:4173/ artifacts/home-mobile.png`

Inspect both images for clipped type, overlapping index rows, accidental red washes, inconsistent rules, and horizontal scrolling. Repeat for `/beats/` if either viewport reveals a shared-shell problem.

- [ ] **Step 6: Run final public-site verification**

Run: `npm test`

Expected: all unit tests pass, 0 fail.

Run: `npm run test:e2e`

Expected: all desktop and mobile Playwright tests pass, 0 fail.

Run: `git diff --check`

Expected: no whitespace errors.

- [ ] **Step 7: Commit the verified site overhaul**

```powershell
git add -A assets data index.html beats drumkits vsts a2v tests package.json package-lock.json playwright.config.js styles.css script.js
git commit -m "complete editorial site overhaul"
```

Do not push until the publisher plan has either been completed or the user explicitly chooses to deploy the public redesign first.
