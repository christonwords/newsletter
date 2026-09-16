# Beat Publisher V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the single-file preview utility with a persistent batch publishing desk that analyzes WAVs, edits exact 30-second previews, manages public order and visibility, and safely publishes one reviewed Git commit.

**Architecture:** A local Python server bound to `127.0.0.1` owns SQLite state, FFmpeg processing, filesystem writes, and Git operations. A separate browser UI consumes a token-protected JSON API. Publishing renders into staging, validates every artifact, atomically updates only managed `beats/` paths, commits those exact paths, pushes, and polls the public catalog revision.

**Tech Stack:** Python 3 standard library, SQLite, FFmpeg, FFprobe, HTML5, CSS, browser ES modules, Canvas 2D, Node built-in test runner, Playwright Chromium, Git CLI.

**Spec:** `docs/superpowers/specs/2026-09-16-site-publisher-overhaul-design.md`

## Global Constraints

- Keep the public site static and free on GitHub Pages.
- Bind the publisher only to `127.0.0.1`; require a random per-launch token and same-origin validation for every state-changing request.
- Store private state only under `.beat_publisher_data/`; never commit its database, imported WAV cache, temp previews, or logs.
- Never upload source WAV files to GitHub.
- Produce exactly 30-second MP3 previews around 160 kbps with short boundary fades.
- Embed exactly 240 normalized integer peaks per published beat in schema-1 `beats/catalog.json`.
- Keep all app and public copy lowercase.
- Autosave metadata, preview range, status, and order to SQLite.
- Never stage unrelated files; Git receives only the exact managed catalog, generated previews, and explicit managed deletions.
- Preserve the current site until a validated `catalog.json` exists; remove legacy `beats/beats.json` only in the same successful publish that creates the replacement catalog.
- Preserve local work after export, commit, push, or deployment-check failure.
- Do not implement DAW-style beat rearrangement.

---

## File Structure

### Python application

- Rewrite `tools/beat_publisher/app.py`: small entry point, configuration, browser launch, and shutdown.
- Create `tools/beat_publisher/models.py`: immutable beat and publish dataclasses.
- Create `tools/beat_publisher/catalog.py`: SQLite schema, migrations, transactions, ordering, and status changes.
- Create `tools/beat_publisher/metadata.py`: filename parsing, slugging, path normalization, and file fingerprints.
- Create `tools/beat_publisher/migration.py`: one-time import of current `beats/beats.json`.
- Create `tools/beat_publisher/audio.py`: FFprobe, analysis, smart start, waveform peaks, and MP3 export.
- Create `tools/beat_publisher/jobs.py`: bounded batch analysis and progress state.
- Create `tools/beat_publisher/picker.py`: native Windows file and folder selection.
- Create `tools/beat_publisher/public_catalog.py`: schema-1 catalog and content-hashed public asset generation.
- Create `tools/beat_publisher/publish.py`: staging, validation, exact Git staging, commit, push, retry, and deployment polling.
- Create `tools/beat_publisher/server.py`: loopback HTTP server, security checks, static files, and JSON routes.
- Create `tools/beat_publisher/__init__.py`: package marker.

### Publisher interface

- Create `tools/beat_publisher/static/index.html`: three-area publishing desk.
- Create `tools/beat_publisher/static/styles.css`: dense gallery-white operational UI.
- Create `tools/beat_publisher/static/api.js`: token-bearing fetch wrapper and typed API errors.
- Create `tools/beat_publisher/static/state.js`: normalized client state and subscriptions.
- Create `tools/beat_publisher/static/app.js`: bootstrap, queue, filters, selection, ordering, and publish review.
- Create `tools/beat_publisher/static/editor.js`: waveform region interaction, keyboard controls, source audition, and encoded preview audition.

### Tests and launcher

- Create `tools/beat_publisher/tests/__init__.py`.
- Create focused `test_catalog.py`, `test_metadata.py`, `test_migration.py`, `test_audio.py`, `test_jobs.py`, `test_server.py`, `test_public_catalog.py`, and `test_publish.py` under `tools/beat_publisher/tests/`.
- Create `tests/publisher/publisher.spec.js`: browser workflow coverage.
- Create `playwright.publisher.config.js`: isolated publisher test server.
- Create `run_beat_publisher.bat`: one-click Windows launcher.
- Rewrite `tools/beat_publisher/README.md`: prerequisites, workflow, recovery states, and test commands.
- Modify `.gitignore`: add `.beat_publisher_data/` while retaining `.beat_publisher_tmp/`, `__pycache__/`, and `.superpowers/`.

---

### Task 1: Persistent Catalog Store

**Files:**
- Create: `tools/beat_publisher/__init__.py`
- Create: `tools/beat_publisher/models.py`
- Create: `tools/beat_publisher/catalog.py`
- Create: `tools/beat_publisher/tests/__init__.py`
- Create: `tools/beat_publisher/tests/test_catalog.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `BeatRecord`, `PublishRevision`, and `CatalogStore`.
- `CatalogStore(db_path)` exposes `initialize()`, `upsert(record)`, `get(beat_id)`, `list(status=None)`, `update(beat_id, **changes)`, `set_order(ids)`, and `transaction()`.
- Valid statuses are `draft`, `ready`, `published`, `hidden`, and `removed`.

- [ ] **Step 1: Write failing persistence, restart, status, and order tests**

```python
# tools/beat_publisher/tests/test_catalog.py
import tempfile
import unittest
from pathlib import Path

from tools.beat_publisher.catalog import CatalogStore
from tools.beat_publisher.models import BeatRecord


class CatalogStoreTests(unittest.TestCase):
    def test_round_trip_survives_reopen(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "catalog.sqlite3"
            store = CatalogStore(path)
            store.initialize()
            store.upsert(BeatRecord(id="one", title="holdher15", slug="holdher15", status="draft", public_order=0))
            reopened = CatalogStore(path)
            reopened.initialize()
            self.assertEqual(reopened.get("one").title, "holdher15")

    def test_reorders_every_record_in_one_transaction(self):
        with tempfile.TemporaryDirectory() as temp:
            store = CatalogStore(Path(temp) / "catalog.sqlite3")
            store.initialize()
            store.upsert(BeatRecord(id="one", title="one", slug="one", status="ready", public_order=0))
            store.upsert(BeatRecord(id="two", title="two", slug="two", status="ready", public_order=1))
            store.set_order(["two", "one"])
            self.assertEqual([beat.id for beat in store.list()], ["two", "one"])

    def test_rejects_unknown_status(self):
        with tempfile.TemporaryDirectory() as temp:
            store = CatalogStore(Path(temp) / "catalog.sqlite3")
            store.initialize()
            with self.assertRaisesRegex(ValueError, "invalid status"):
                store.upsert(BeatRecord(id="one", title="one", slug="one", status="lost", public_order=0))
```

- [ ] **Step 2: Run the catalog tests and verify missing modules fail**

Run: `python -m unittest tools.beat_publisher.tests.test_catalog -v`

Expected: FAIL with import errors for `catalog` or `models`.

- [ ] **Step 3: Define the complete beat model and SQLite schema**

```python
# tools/beat_publisher/models.py
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class BeatRecord:
    id: str
    title: str
    slug: str
    status: str
    public_order: int
    bpm: str = ""
    key: str = ""
    source_path: str = ""
    source_fingerprint: str = ""
    original_filename: str = ""
    source_duration: float = 0.0
    suggested_start: float = 0.0
    preview_start: float = 0.0
    preview_duration: float = 30.0
    normalize: bool = True
    source_peaks: tuple[int, ...] = ()
    preview_path: str = ""
    preview_peaks: tuple[int, ...] = ()
    preview_fingerprint: str = ""
    published_preview_path: str = ""
    published_fingerprint: str = ""
    published_revision: str = ""
    managed_source: bool = False
    warnings: tuple[str, ...] = ()
    previous_status: str = ""
    created_at: str = ""
    updated_at: str = ""
```

`CatalogStore.initialize()` must create a `beats` table with one column for every field, a unique slug index, a source-fingerprint index, a status check constraint, and a `settings` table with schema version `1`. Store `source_peaks`, `preview_peaks`, and `warnings` as JSON arrays and map them back to immutable tuples. Every mutating method must use a transaction and update `updated_at` in UTC ISO-8601 form.

- [ ] **Step 4: Implement CRUD, filtered listing, and transactional ordering**

Use `sqlite3.Row`, parameterized SQL only, and explicit mapping between rows and `BeatRecord`. `set_order(ids)` must reject duplicates, unknown IDs, or a partial list; successful ordering assigns contiguous zero-based values.

- [ ] **Step 5: Run the catalog test module**

Run: `python -m unittest tools.beat_publisher.tests.test_catalog -v`

Expected: all catalog tests pass.

- [ ] **Step 6: Commit the persistent store**

```powershell
git add .gitignore tools/beat_publisher/__init__.py tools/beat_publisher/models.py tools/beat_publisher/catalog.py tools/beat_publisher/tests
git commit -m "add persistent beat catalog store"
```

### Task 2: Metadata Parsing And Legacy Migration

**Files:**
- Create: `tools/beat_publisher/metadata.py`
- Create: `tools/beat_publisher/migration.py`
- Create: `tools/beat_publisher/tests/test_metadata.py`
- Create: `tools/beat_publisher/tests/test_migration.py`

**Interfaces:**
- Consumes: `CatalogStore`, current array-shaped `beats/beats.json`, and existing MP3 paths.
- Produces: `parse_filename(name): ParsedMetadata`, `slugify(value): str`, `fingerprint_file(path): str`, and `migrate_legacy_catalog(store, legacy_path, preview_dir): MigrationResult`.
- `ParsedMetadata` is `{ title, bpm, key, slug, warnings }`.

- [ ] **Step 1: Write failing parser and fingerprint tests**

```python
# tools/beat_publisher/tests/test_metadata.py
import tempfile
import unittest
from pathlib import Path

from tools.beat_publisher.metadata import fingerprint_file, parse_filename


class MetadataTests(unittest.TestCase):
    def test_parses_existing_filename_style(self):
        parsed = parse_filename("holdher15 d# min 153bpm.wav")
        self.assertEqual((parsed.title, parsed.bpm, parsed.key, parsed.slug), ("holdher15", "153", "d# min", "holdher15"))

    def test_flags_missing_key_without_rejecting_the_title(self):
        parsed = parse_filename("throneoccupier3 156bpm.wav")
        self.assertEqual(parsed.title, "throneoccupier3")
        self.assertIn("key missing", parsed.warnings)

    def test_fingerprint_changes_with_file_content(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "beat.wav"
            path.write_bytes(b"one")
            first = fingerprint_file(path)
            path.write_bytes(b"two")
            self.assertNotEqual(first, fingerprint_file(path))
```

- [ ] **Step 2: Write a failing migration test that preserves order and files**

The test creates a two-entry legacy JSON file and two dummy MP3 files, runs migration twice, and asserts two published SQLite records in original order, stable UUIDs across both runs, empty source paths, and unchanged source JSON and MP3 hashes.

- [ ] **Step 3: Run both test modules and verify missing implementations fail**

Run: `python -m unittest tools.beat_publisher.tests.test_metadata tools.beat_publisher.tests.test_migration -v`

Expected: FAIL with import or missing-function errors.

- [ ] **Step 4: Move the current parsing logic into typed, tested functions**

Use `uuid.uuid5(uuid.NAMESPACE_URL, f"christon.xyz/beats/{slug}")` for stable migrated IDs. Normalize `major`, `maj`, `minor`, `min`, and compact `m` spellings. Use SHA-256 for source and preview fingerprints and read files in 1 MiB chunks.

Migration must mark records `published`, copy no audio, preserve order, record the repository-relative path in `published_preview_path`, record the existing preview fingerprint, and return counts for imported and skipped records. A setting key `legacy_migration_v1` makes reruns idempotent. Preview peaks are added in Task 3 once the shared audio reader exists.

- [ ] **Step 5: Run parser, migration, and catalog tests**

Run: `python -m unittest tools.beat_publisher.tests.test_catalog tools.beat_publisher.tests.test_metadata tools.beat_publisher.tests.test_migration -v`

Expected: all tests pass.

- [ ] **Step 6: Commit parsing and migration**

```powershell
git add tools/beat_publisher/metadata.py tools/beat_publisher/migration.py tools/beat_publisher/tests
git commit -m "add metadata parsing and catalog migration"
```

### Task 3: Audio Analysis And Exact Preview Export

**Files:**
- Create: `tools/beat_publisher/audio.py`
- Create: `tools/beat_publisher/tests/test_audio.py`
- Modify: `tools/beat_publisher/migration.py`
- Modify: `tools/beat_publisher/tests/test_migration.py`

**Interfaces:**
- Produces: `AudioAnalysis(duration, sample_rate, peaks, suggested_start)`.
- Produces: `analyze_source(path, peak_count=240): AudioAnalysis`, `extract_peaks(path, peak_count=240): tuple[int, ...]`, `export_preview(source, output, start, normalize): PreviewArtifact`, and `probe_duration(path): float`.
- `PreviewArtifact` is `{ path, duration, size, fingerprint }`.

- [ ] **Step 1: Write failing tests using a generated WAV fixture**

```python
# tools/beat_publisher/tests/test_audio.py
import math
import shutil
import struct
import tempfile
import unittest
import wave
from pathlib import Path

from tools.beat_publisher.audio import analyze_source, export_preview, probe_duration


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"), "ffmpeg tools required")
class AudioTests(unittest.TestCase):
    def make_wav(self, path, seconds=40, rate=8000):
        with wave.open(str(path), "wb") as output:
            output.setparams((1, 2, rate, seconds * rate, "NONE", "not compressed"))
            frames = bytearray()
            for index in range(seconds * rate):
                amplitude = 4000 if index < 10 * rate else 14000
                frames.extend(struct.pack("<h", int(amplitude * math.sin(index * 0.07))))
            output.writeframes(frames)

    def test_analysis_returns_240_bounded_peaks_and_valid_start(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "beat.wav"
            self.make_wav(source)
            analysis = analyze_source(source)
            self.assertEqual(len(analysis.peaks), 240)
            self.assertTrue(all(0 <= peak <= 255 for peak in analysis.peaks))
            self.assertLessEqual(analysis.suggested_start, 10.0)

    def test_export_is_exactly_30_seconds_and_decodable(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "beat.wav"
            preview = Path(temp) / "preview.mp3"
            self.make_wav(source)
            artifact = export_preview(source, preview, 5.0, normalize=True)
            self.assertAlmostEqual(probe_duration(preview), 30.0, delta=0.05)
            self.assertGreater(artifact.size, 1000)
```

- [ ] **Step 2: Run the audio tests and verify the module is missing**

Run: `python -m unittest tools.beat_publisher.tests.test_audio -v`

Expected: FAIL with missing `audio.py`.

- [ ] **Step 3: Implement probing, mono analysis, smart range selection, and peaks**

Decode analysis audio through FFmpeg as mono signed 16-bit PCM at 8 kHz. Build one-second RMS windows for smart selection and evenly bucket absolute peak amplitude into exactly 240 integers from 0 to 255. Clamp the suggested start to `0 <= start <= max(0, duration - 30)` and prefer sustained high energy over one isolated spike. `extract_peaks` applies the same bounded peak algorithm to WAV or MP3 input.

- [ ] **Step 4: Implement exact MP3 rendering and post-export validation**

Render with `libmp3lame`, `-b:a 160k`, a 0.06-second fade in, and a 0.35-second fade out beginning at 29.65 seconds. When normalization is enabled, apply a consistent FFmpeg loudness filter; when disabled, apply only fades. Probe the output and delete it if duration differs from 30 seconds by more than 0.05 seconds or FFprobe cannot decode it.

Update legacy migration to call `extract_peaks` for every existing public MP3 and persist the result as `preview_peaks`. If an old MP3 is unreadable, preserve the migrated record with a `preview unreadable` warning so the app can flag it without deleting anything.

- [ ] **Step 5: Run the audio and metadata tests**

Run: `python -m unittest tools.beat_publisher.tests.test_audio tools.beat_publisher.tests.test_metadata -v`

Expected: all tests pass; any FFmpeg skip is reported explicitly rather than counted as a pass during final verification.

- [ ] **Step 6: Commit the audio pipeline**

```powershell
git add tools/beat_publisher/audio.py tools/beat_publisher/migration.py tools/beat_publisher/tests/test_audio.py tools/beat_publisher/tests/test_migration.py
git commit -m "add exact preview audio pipeline"
```

### Task 4: Bounded Batch Import And Native Selection

**Files:**
- Create: `tools/beat_publisher/jobs.py`
- Create: `tools/beat_publisher/picker.py`
- Create: `tools/beat_publisher/tests/test_jobs.py`

**Interfaces:**
- Consumes: `CatalogStore`, `parse_filename`, `fingerprint_file`, and `analyze_source`.
- Produces: `BatchImporter(store, managed_source_dir, workers=None)`, `import_paths(paths): list[ImportResult]`, `import_upload(filename, bytes): ImportResult`, `relink_source(beat_id, path): BeatRecord`, `refresh_source_state(): dict[str, bool]`, `choose_wav_files(): list[Path]`, and `choose_wav_folder(): Path | None`.
- Each `ImportResult` contains beat ID, state, warnings, and a plain-language error when one item fails.

- [ ] **Step 1: Write failing batch isolation and duplicate tests**

Create three small WAV fixtures, make one unreadable, and assert that `import_paths` returns two successful records and one error without rolling back successes. Import one source twice and assert the second result is `duplicate` with the existing beat ID. Delete one linked source, reopen the service, and assert `refresh_source_state` marks it missing without changing a published preview. Relink to a matching replacement and assert the missing state clears. Assert the default worker count is `min(4, max(1, (os.cpu_count() or 2) // 2))`.

- [ ] **Step 2: Run the jobs tests and verify missing implementation failure**

Run: `python -m unittest tools.beat_publisher.tests.test_jobs -v`

Expected: FAIL with missing `jobs.py`.

- [ ] **Step 3: Implement batch analysis with bounded workers**

Use `concurrent.futures.ThreadPoolExecutor`, preserve user selection order in returned results, and write each successful item independently. Persist analysis peaks in `source_peaks`, the smart choice in `suggested_start`, the initial selection in `preview_start`, and parser messages in `warnings`. A duplicate source fingerprint returns the existing beat without creating a second record. A duplicate slug from different audio receives a deterministic `-2`, `-3`, and later suffix plus a warning. Source refresh reports missing links as derived UI state; it does not replace a published status or delete output.

- [ ] **Step 4: Implement Windows pickers and managed drag-drop sources**

Use `tkinter.filedialog.askopenfilenames` for files and `askdirectory` for folders. Folder import selects `.wav` files only and does not recurse. `import_upload` sanitizes the filename with `Path(name).name`, writes beneath `.beat_publisher_data/sources/`, fingerprints the final path, and marks `managed_source=True`.

- [ ] **Step 5: Run batch tests and the full Python suite**

Run: `python -m unittest discover -s tools/beat_publisher/tests -v`

Expected: all implemented tests pass.

- [ ] **Step 6: Commit batch import**

```powershell
git add tools/beat_publisher/jobs.py tools/beat_publisher/picker.py tools/beat_publisher/tests/test_jobs.py
git commit -m "add resilient batch beat import"
```

### Task 5: Secure Local API And App Entry Point

**Files:**
- Rewrite: `tools/beat_publisher/app.py`
- Create: `tools/beat_publisher/server.py`
- Create: `tools/beat_publisher/tests/test_server.py`

**Interfaces:**
- Consumes: catalog and import services from Tasks 1-4.
- Produces: `PublisherServer(config)`, `create_session_token(): str`, and a loopback server with JSON API routes.
- Test configuration variables are `BEAT_PUBLISHER_DATA_DIR`, `BEAT_PUBLISHER_PORT`, `BEAT_PUBLISHER_NO_BROWSER`, and `BEAT_PUBLISHER_TOKEN`.

- [ ] **Step 1: Write failing security and path-containment tests**

```python
# tools/beat_publisher/tests/test_server.py
import tempfile
import unittest
from pathlib import Path

from tools.beat_publisher.server import RequestGuard, safe_child


class ServerSecurityTests(unittest.TestCase):
    def test_mutation_requires_cookie_header_token_and_same_origin(self):
        guard = RequestGuard(token="secret", origin="http://127.0.0.1:8765")
        self.assertFalse(guard.allows("", "", ""))
        self.assertFalse(guard.allows("secret", "secret", "https://example.com"))
        self.assertTrue(guard.allows("secret", "secret", "http://127.0.0.1:8765"))

    def test_safe_child_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            with self.assertRaisesRegex(ValueError, "outside managed directory"):
                safe_child(root, "../escape.mp3")
```

- [ ] **Step 2: Run server tests and verify missing module failure**

Run: `python -m unittest tools.beat_publisher.tests.test_server -v`

Expected: FAIL with missing `server.py`.

- [ ] **Step 3: Implement session bootstrap and guarded routing**

Bind `ThreadingHTTPServer` to `127.0.0.1` only. Opening `/?token=<random>` validates the token, sets an HttpOnly `SameSite=Strict` cookie, injects the same token into a `<meta name="publisher-token">`, and removes the query through client history replacement. Reject mutation unless cookie, `X-Beat-Publisher-Token`, and exact `Origin` all match. Send no permissive CORS headers.

Require the valid session cookie for every `/api/`, source-audio, and private-preview response, including reads. `BEAT_PUBLISHER_TOKEN` may force a deterministic token only for automated tests; normal launches always use `secrets.token_urlsafe(32)`.

Implement these initial routes:

- `GET /api/bootstrap`: beat list, filters, import state, and pending counts.
- `POST /api/import/files`: open native file picker and enqueue results.
- `POST /api/import/folder`: open native folder picker and enqueue results.
- `POST /api/import/upload`: accept a bounded multipart WAV upload into managed sources.
- `POST /api/beats/<id>/relink`: open a native file picker, validate the selected WAV, and update the source link.
- `PATCH /api/beats/<id>`: allowlisted metadata, status, preview start, and normalize changes.
- `POST /api/order`: complete ordered ID list.
- `GET /api/beats/<id>/source`: range-capable local source audio for audition.

- [ ] **Step 4: Rewrite `app.py` as a small configurable entry point**

`app.py` must check FFmpeg and FFprobe at startup, initialize `.beat_publisher_data/catalog.sqlite3`, run legacy migration, create the random token, choose port 8765 unless overridden, open the tokenized URL unless disabled, and stop cleanly on Ctrl+C. It must not contain HTML, CSS, catalog SQL, or audio algorithms.

- [ ] **Step 5: Run all Python tests**

Run: `python -m unittest discover -s tools/beat_publisher/tests -v`

Expected: all tests pass.

- [ ] **Step 6: Commit the secure service boundary**

```powershell
git add tools/beat_publisher/app.py tools/beat_publisher/server.py tools/beat_publisher/tests/test_server.py
git commit -m "add secure local publisher api"
```

### Task 6: Publisher Desk Shell And Queue

**Files:**
- Create: `tools/beat_publisher/static/index.html`
- Create: `tools/beat_publisher/static/styles.css`
- Create: `tools/beat_publisher/static/api.js`
- Create: `tools/beat_publisher/static/state.js`
- Create: `tools/beat_publisher/static/app.js`
- Create: `playwright.publisher.config.js`
- Create: `tests/publisher/publisher.spec.js`
- Modify: `tools/beat_publisher/server.py`

**Interfaces:**
- Consumes: Task 5 JSON routes and injected session token.
- Produces: three-area desk with batch queue, selected editor empty state, and publish summary.
- Produces: `api.request(path, options)`, `store.getState()`, `store.setState(next)`, and `store.subscribe(listener)`.

- [ ] **Step 1: Add an isolated Playwright publisher server configuration**

Set `BEAT_PUBLISHER_DATA_DIR` to a temporary test fixture directory, `BEAT_PUBLISHER_PORT=8766`, `BEAT_PUBLISHER_NO_BROWSER=1`, and `BEAT_PUBLISHER_TOKEN=test-token`. Start `python tools/beat_publisher/app.py` as Playwright's web server and use `http://127.0.0.1:8766` as base URL.

- [ ] **Step 2: Write a failing shell and queue test**

```js
// tests/publisher/publisher.spec.js
import { expect, test } from "@playwright/test";

test("shows the batch queue, editor, and publish summary", async ({ page }) => {
  await page.goto("/?token=test-token");
  await expect(page.getByRole("heading", { name: "christon / publisher" })).toBeVisible();
  await expect(page.locator("[data-region='queue']")).toBeVisible();
  await expect(page.locator("[data-region='editor']")).toBeVisible();
  await expect(page.locator("[data-region='publish']")).toBeVisible();
  await expect(page.getByRole("button", { name: "choose wavs" })).toBeVisible();
  await expect(page.getByRole("button", { name: "choose folder" })).toBeVisible();
});
```

- [ ] **Step 3: Run the shell test and verify static files are missing**

Run: `npx playwright test -c playwright.publisher.config.js -g "batch queue"`

Expected: FAIL with a 404 or missing heading.

- [ ] **Step 4: Build the dense gallery-white shell and state flow**

Use the approved left queue, center editor, and right publish summary. Render queue rows with title, BPM, key, status, warning count, and drag handle. Add search and status filters. The API wrapper must attach `X-Beat-Publisher-Token`, parse structured `{ error, detail }` responses, and never use `innerHTML` for server values.

- [ ] **Step 5: Run the publisher shell test**

Run: `npx playwright test -c playwright.publisher.config.js -g "batch queue"`

Expected: the shell test passes in Chromium.

- [ ] **Step 6: Commit the publisher shell**

```powershell
git add tools/beat_publisher/static tools/beat_publisher/server.py playwright.publisher.config.js tests/publisher
git commit -m "build publisher desk shell"
```

### Task 7: Waveform Selection And Encoded Preview Review

**Files:**
- Create: `tools/beat_publisher/static/editor.js`
- Modify: `tools/beat_publisher/static/app.js`
- Modify: `tools/beat_publisher/static/index.html`
- Modify: `tools/beat_publisher/static/styles.css`
- Modify: `tools/beat_publisher/server.py`
- Modify: `tests/publisher/publisher.spec.js`

**Interfaces:**
- Consumes: source audio route, `AudioAnalysis.peaks`, and persisted `preview_start`.
- Produces: `mountEditor(container, beat, actions)`, `setSelectionStart(seconds)`, and API routes `POST /api/beats/<id>/preview` plus `GET /api/previews/<id>`.

- [ ] **Step 1: Add failing preview-editor browser coverage**

Seed one draft beat in the test database. Assert its full waveform contains 240 bars, selection label reads `00:48.2 - 01:18.2` for a 48.2-second start, arrow keys nudge by 0.1 seconds, Shift+Arrow nudges by 1 second, selection never crosses source bounds, `use smart selection` restores the suggestion, and `approve & next` changes status to ready.

- [ ] **Step 2: Run the editor test and verify the empty state fails the interaction contract**

Run: `npx playwright test -c playwright.publisher.config.js -g "preview editor"`

Expected: FAIL because the interactive waveform and preview endpoint do not exist.

- [ ] **Step 3: Implement Canvas selection interaction and autosave**

Draw source peaks without decoding in the browser. Pointer down inside the selected region drags the fixed 30-second range; pointer down outside moves its center. Clamp the start on every pointer and keyboard update. Debounce metadata and range PATCH requests by 250 ms and flush them before changing selection.

- [ ] **Step 4: Implement encoded preview generation and range serving**

`POST /api/beats/<id>/preview` exports into `.beat_publisher_data/previews/<id>.mp3`, extracts 240 preview peaks, persists `preview_path`, `preview_peaks`, and `preview_fingerprint`, and returns a cache-busted URL. Regeneration replaces only that private preview. `GET /api/previews/<id>` and source audition support byte ranges and require the session cookie. Encoded preview playback is a separate explicit control from source audition.

- [ ] **Step 5: Run editor browser tests and Python API tests**

Run: `python -m unittest tools.beat_publisher.tests.test_server tools.beat_publisher.tests.test_audio -v`

Run: `npx playwright test -c playwright.publisher.config.js -g "preview editor"`

Expected: all selected tests pass.

- [ ] **Step 6: Commit the preview editor**

```powershell
git add tools/beat_publisher/static tools/beat_publisher/server.py tools/beat_publisher/tests tests/publisher/publisher.spec.js
git commit -m "add precise beat preview editor"
```

### Task 8: Catalog Ordering, Visibility, And Reversible Removal

**Files:**
- Modify: `tools/beat_publisher/catalog.py`
- Modify: `tools/beat_publisher/server.py`
- Modify: `tools/beat_publisher/static/app.js`
- Modify: `tools/beat_publisher/static/state.js`
- Modify: `tools/beat_publisher/static/styles.css`
- Modify: `tools/beat_publisher/tests/test_catalog.py`
- Modify: `tests/publisher/publisher.spec.js`

**Interfaces:**
- Consumes: complete ordered ID lists and valid status transitions.
- Produces: drag ordering, multi-select, `hide`, `restore`, `remove`, and `undo remove` actions.

- [ ] **Step 1: Add failing transition and complete-order tests**

Assert that published can transition to hidden or removed, hidden can return to published, removed can return to its previous status before publish, and a partial or duplicate order list rolls back completely. Add a browser test that drags the second row above the first, reloads, and observes the same order. Add a multi-select test that checks three rows, applies `hide selected`, and verifies one batched request changes only those three records.

- [ ] **Step 2: Run catalog and browser tests to verify failures**

Run: `python -m unittest tools.beat_publisher.tests.test_catalog -v`

Run: `npx playwright test -c playwright.publisher.config.js -g "catalog order"`

Expected: new status-transition or drag assertions fail.

- [ ] **Step 3: Implement explicit status transitions and undo metadata**

Store `previous_status` when entering `removed`; clear it after restore or successful publish. Keep removed rows visible only under the removed filter. Hiding affects the next public catalog without deleting its current MP3 until publish succeeds.

- [ ] **Step 4: Implement pointer and keyboard reordering**

Use HTML drag events plus `move up` and `move down` keyboard-accessible buttons. Send one complete ID array to `/api/order`, optimistically render it, and roll back client order on API failure.

Queue checkboxes maintain a selected-ID set across filtering. Batch status actions send one guarded transaction to `POST /api/beats/batch-status`; if any ID or transition is invalid, change none of them and return the specific rejected ID.

- [ ] **Step 5: Run all catalog and publisher browser tests**

Run: `python -m unittest tools.beat_publisher.tests.test_catalog -v`

Run: `npx playwright test -c playwright.publisher.config.js`

Expected: all current tests pass.

- [ ] **Step 6: Commit catalog management**

```powershell
git add tools/beat_publisher/catalog.py tools/beat_publisher/server.py tools/beat_publisher/static tools/beat_publisher/tests/test_catalog.py tests/publisher/publisher.spec.js
git commit -m "add reversible beat catalog management"
```

### Task 9: Public Catalog And Content-Hashed Assets

**Files:**
- Create: `tools/beat_publisher/public_catalog.py`
- Create: `tools/beat_publisher/tests/test_public_catalog.py`

**Interfaces:**
- Consumes: published and ready `BeatRecord` values, private encoded previews, and analysis peaks.
- Produces: `build_public_catalog(records, revision, published_at): dict`, `hashed_preview_name(slug, fingerprint): str`, and `render_public_assets(store, staging_dir): RenderResult`.
- Schema-1 output is `{ schemaVersion, revision, publishedAt, beats }` with each beat containing `id`, `slug`, `title`, `bpm`, `key`, `preview`, `duration`, `order`, and 240 `peaks`.

- [ ] **Step 1: Write failing schema, ordering, hash, and visibility tests**

```python
# tools/beat_publisher/tests/test_public_catalog.py
import unittest
from tools.beat_publisher.models import BeatRecord
from tools.beat_publisher.public_catalog import build_public_catalog, hashed_preview_name


class PublicCatalogTests(unittest.TestCase):
    def test_catalog_excludes_hidden_and_removed_and_preserves_manual_order(self):
        peaks = tuple([64] * 240)
        records = [
            BeatRecord(id="two", title="two", slug="two", status="published", public_order=1, preview_peaks=peaks, preview_fingerprint="22222222", published_preview_path="previews/two.mp3"),
            BeatRecord(id="hidden", title="hidden", slug="hidden", status="hidden", public_order=0, preview_peaks=peaks),
            BeatRecord(id="one", title="one", slug="one", status="ready", public_order=0, preview_peaks=peaks, preview_fingerprint="11111111", preview_path="private/one.mp3")
        ]
        catalog = build_public_catalog(records, "rev1", "2026-09-16T00:00:00Z")
        self.assertEqual(catalog["schemaVersion"], 1)
        self.assertEqual([beat["id"] for beat in catalog["beats"]], ["one", "two"])

    def test_hashed_name_is_cacheable_and_slug_safe(self):
        self.assertEqual(hashed_preview_name("holdher15", "abcdef123456"), "holdher15-abcdef12.mp3")
```

- [ ] **Step 2: Run the public-catalog tests and verify missing module failure**

Run: `python -m unittest tools.beat_publisher.tests.test_public_catalog -v`

Expected: FAIL with missing `public_catalog.py`.

- [ ] **Step 3: Implement deterministic schema and staged asset rendering**

Reject duplicate IDs, slugs, orders, preview paths, peak arrays not exactly 240 integers, preview durations outside tolerance, and path traversal. Sort by `public_order`, then rewrite exported order to contiguous zero-based integers. Use the first eight lowercase SHA-256 characters in each public MP3 filename.

`render_public_assets` writes only beneath its staging directory. For a new or edited beat it reads `preview_path` and `preview_peaks`; for an unchanged migrated beat it reads `published_preview_path` and the migrated `preview_peaks`. It rejects a ready record without a valid private preview and a published record without a valid current public preview. It copies each selected MP3 and writes `catalog.json` with UTF-8, two-space indentation, and a final newline.

- [ ] **Step 4: Run catalog generation tests**

Run: `python -m unittest tools.beat_publisher.tests.test_public_catalog -v`

Expected: all tests pass.

- [ ] **Step 5: Commit public artifact generation**

```powershell
git add tools/beat_publisher/public_catalog.py tools/beat_publisher/tests/test_public_catalog.py
git commit -m "generate versioned public beat catalog"
```

### Task 10: Transactional Publish And Scoped Git Operations

**Files:**
- Create: `tools/beat_publisher/publish.py`
- Create: `tools/beat_publisher/tests/test_publish.py`
- Modify: `tools/beat_publisher/server.py`

**Interfaces:**
- Consumes: `render_public_assets`, catalog state, repository root, and a command runner.
- Produces: `PublishService.prepare()`, `confirm(review_id)`, `retry_push()`, `cleanup_managed_sources(ids)`, and `poll_live_revision(url, revision, timeout)`.
- `prepare()` returns immutable additions, replacements, deletions, byte sizes, warnings, and a random review ID.

- [ ] **Step 1: Write failing staging rollback and exact-path Git tests**

Create a temporary Git repository with a bare local remote, a modified unrelated `index.html`, current beat assets, and a fake renderer. Assert:

- a validation failure leaves current `beats/` byte-for-byte unchanged;
- successful confirm stages `beats/catalog.json`, new hashed MP3s, obsolete managed MP3 deletions, and legacy `beats/beats.json` deletion only;
- unrelated `index.html` remains unstaged;
- one commit is created with `publish N beat previews`;
- a simulated push failure leaves the commit at `HEAD` and reports retryable state.
- managed source cleanup is rejected before successful publish and deletes only app-owned sources after the corresponding records have a published revision.

- [ ] **Step 2: Run publish tests and verify missing implementation failure**

Run: `python -m unittest tools.beat_publisher.tests.test_publish -v`

Expected: FAIL with missing `publish.py`.

- [ ] **Step 3: Implement immutable review preparation and one-at-a-time locking**

Render into `.beat_publisher_data/staging/<review-id>/`, write a manifest containing source record fingerprints and intended paths, and reject confirm if any record changed after prepare. Guard prepare and confirm with one process lock and return `publish already running` on overlap.

- [ ] **Step 4: Implement atomic working-tree update and exact Git staging**

Copy validated staged files into `beats/` using same-volume temporary names followed by `Path.replace`. Remove only obsolete preview files that appear in the previous public catalog. Run `git add -- <exact paths>` and `git rm -- <exact managed deletions>`; never run `git add .`, `git add -A`, or stage a directory. Verify `git diff --cached --name-only` is a subset of the review manifest before committing.

- [ ] **Step 5: Implement push recovery and live-revision polling**

After commit, push the configured upstream. On failure, persist `commit_hash` and `push_pending=true`; `retry_push()` runs only push and never rerenders. Poll `https://christon.xyz/beats/catalog.json?revision=<hash>` until its `revision` matches, timeout is reached, or the app closes. Timeout returns `pushed, live status unknown` rather than failure.

- [ ] **Step 6: Expose prepare, confirm, retry, and status routes**

Add guarded routes:

- `POST /api/publish/prepare`
- `POST /api/publish/confirm`
- `POST /api/publish/retry-push`
- `POST /api/publish/cleanup-sources`
- `GET /api/publish/status`

Return separate states for `saved locally`, `ready for review`, `committed`, `pushed`, and `live`.

- [ ] **Step 7: Run publish and complete Python tests**

Run: `python -m unittest tools.beat_publisher.tests.test_publish -v`

Expected: all publish tests pass, including the simulated push failure.

Run: `python -m unittest discover -s tools/beat_publisher/tests -v`

Expected: all Python tests pass.

- [ ] **Step 8: Commit transactional publishing**

```powershell
git add tools/beat_publisher/publish.py tools/beat_publisher/server.py tools/beat_publisher/tests/test_publish.py
git commit -m "add transactional beat publishing"
```

### Task 11: Publish Review UI And Recovery States

**Files:**
- Modify: `tools/beat_publisher/static/index.html`
- Modify: `tools/beat_publisher/static/styles.css`
- Modify: `tools/beat_publisher/static/api.js`
- Modify: `tools/beat_publisher/static/app.js`
- Modify: `tests/publisher/publisher.spec.js`

**Interfaces:**
- Consumes: Task 10 publish routes and state vocabulary.
- Produces: review modal, exact changed-file summary, publish progress, retry-push action, live revision status, and post-publish managed-source cleanup.

- [ ] **Step 1: Write failing review, failure, and retry browser tests**

Mock or fixture the API to return one addition, one replacement, one removal, and an unrelated dirty file warning. Assert the modal lists all four facts, requires explicit confirmation, labels unrelated files as untouched, and disables a second publish. Simulate push failure, reload, assert `committed / push required`, click `retry push`, and assert status advances to `pushed` without another prepare call.

- [ ] **Step 2: Run the targeted browser tests and verify missing review UI failure**

Run: `npx playwright test -c playwright.publisher.config.js -g "publish review|retry push"`

Expected: FAIL because review and recovery controls are absent.

- [ ] **Step 3: Implement review and progress UI**

The right column always shows pending counts and validation state. `review & publish N` opens a modal with additions, replacements, removals, sizes, warnings, exact commit message, and `publish changes`. During work, expose current phase with `aria-live="polite"`. Never label a local save as published.

- [ ] **Step 4: Implement persisted recovery presentation**

On bootstrap, render the server's saved publish state. A pending push shows commit hash and retry action. A pushed-but-not-live state shows `check live status`. A validation failure links the affected queue item and keeps all edits intact. After a successful publish, list only app-managed source copies eligible for cleanup, show their combined size, require confirmation, and leave user-linked original WAV paths untouched.

- [ ] **Step 5: Run all publisher browser tests**

Run: `npx playwright test -c playwright.publisher.config.js`

Expected: all publisher workflow tests pass.

- [ ] **Step 6: Commit publish review and recovery UI**

```powershell
git add tools/beat_publisher/static tests/publisher/publisher.spec.js
git commit -m "add publisher review and recovery states"
```

### Task 12: Launcher, Documentation, And End-To-End Verification

**Files:**
- Create: `run_beat_publisher.bat`
- Rewrite: `tools/beat_publisher/README.md`
- Modify: `tools/beat_publisher/app.py`
- Modify: `tests/publisher/publisher.spec.js`

**Interfaces:**
- Consumes: the completed publisher package and public-site compatibility layer.
- Produces: one-click local launch, documented recovery, and final verified workflow.

- [ ] **Step 1: Create a one-click launcher with stable working directory**

```bat
@echo off
setlocal
cd /d "%~dp0"
python tools\beat_publisher\app.py
if errorlevel 1 pause
```

- [ ] **Step 2: Rewrite the README with exact operating states**

Document FFmpeg and Python prerequisites, launcher and command-line startup, batch file and folder import, flagged-item review, preview selection keys, status filters, reversible removal, one-batch publish, `committed / push required` recovery, `pushed / live unknown` recovery, private data location, backup behavior, and all unit and browser test commands.

- [ ] **Step 3: Add a full happy-path browser test**

The test imports a two-WAV fixture batch through the managed upload API, corrects one missing key, drags one preview start, generates and plays the encoded preview, approves both, reorders them, opens publish review, confirms against a temporary local Git remote, and verifies schema-1 `catalog.json` plus two 30-second hashed MP3s. It also asserts the test repository's unrelated file remains unstaged.

- [ ] **Step 4: Add a restart-resume browser test**

Import and edit a draft, stop the test server, restart with the same data directory, and assert title, BPM, key, selection start, order, and status are restored from SQLite.

- [ ] **Step 5: Run fresh complete verification**

Run: `python -m py_compile tools/beat_publisher/*.py`

Expected: exit 0 with no syntax errors.

Run: `python -m unittest discover -s tools/beat_publisher/tests -v`

Expected: all Python tests pass with zero failures and no FFmpeg skips on the release machine.

Run: `npm test`

Expected: all public-site Node tests pass.

Run: `npm run test:e2e`

Expected: all public-site desktop and mobile tests pass.

Run: `npx playwright test -c playwright.publisher.config.js`

Expected: all publisher browser tests pass.

Run: `git diff --check`

Expected: no whitespace errors.

- [ ] **Step 6: Manually verify the real app without publishing**

Run: `python tools/beat_publisher/app.py`

Import a disposable WAV, confirm folder selection, queue filtering, waveform dragging, source playback, encoded preview playback, keyboard nudges, autosave after browser refresh, and app restart persistence. Stop before `publish changes` so production beat files remain untouched.

- [ ] **Step 7: Commit the complete publisher v2**

```powershell
git add run_beat_publisher.bat tools/beat_publisher tests/publisher playwright.publisher.config.js .gitignore
git commit -m "complete batch beat publisher v2"
```

- [ ] **Step 8: Push the completed plans in order**

First push the public-site overhaul commits and verify GitHub Pages serves the legacy catalog through the adapter. Then push publisher v2. Open the publisher against the real repository, verify the migrated three published beats, and perform the first real schema-1 publish only after the user reviews its publish summary.
