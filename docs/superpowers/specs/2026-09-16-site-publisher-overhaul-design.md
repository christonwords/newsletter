# christon.xyz site and publisher overhaul

status: ready for final review

date: 2026-09-16

## objective

Rebuild christon.xyz as a distinctive, identity-first portfolio and archive, and replace the current single-file beat publisher with a fast batch publishing desk. The public site must remain a static GitHub Pages site with no paid backend. The local app must preserve drafts, support precise preview editing, and publish a reviewed batch with one Git commit and push.

## goals

- Make christon the first and strongest impression on the homepage.
- Use a gallery-white editorial index rather than the current dark card layout.
- Let visitors inspect content without turning the homepage into a long storefront.
- Keep all public-facing copy lowercase.
- Make beat browsing fast with precomputed waveforms and audio loaded only on demand.
- Support batch WAV import, metadata correction, precise 30-second preview selection, catalog ordering, and one-step publishing.
- Keep source WAV files and private working state local.
- Preserve the free GitHub Pages deployment model.
- Make failed exports or pushes recoverable without losing work.

## non-goals

- The publisher is not a DAW and will not rearrange sections inside a full beat.
- The website will not add accounts, payments, comments, streaming analytics, or a cloud CMS.
- The publisher will not upload full WAV files to GitHub.
- The first version will not manage drumkit or VST catalog entries from the beat publisher.

## public experience

### routes

- `/` is the identity-first living index.
- `/beats/` is the complete beat archive.
- `/drumkits/` is the complete drumkit catalog.
- `/vsts/` is the complete go to vsts contact sheet.
- `/a2v/` remains a distinct product-launch microsite.

The homepage previews each collection and links to its complete route. Contact remains available on the homepage and in the global utility navigation.

### visual system

The site uses a gallery-white editorial direction:

- paper: `#fafaf8`
- ink: `#090909`
- signal red: `#e62027`
- muted text: `#6f6f69`
- soft field: `#efefeb`
- rules: `#171717`

There are no gradients, glow effects, decorative shadows, glass panels, pill-heavy controls, or page-wide animation loops. Corners are square or nearly square. Thin rules encode structure instead of decorating cards.

The large christon wordmark uses a high-contrast editorial serif in the Bodoni family. Navigation, metadata, controls, and body copy use a compact neutral sans serif. The implementation should self-host the exact font files when licensing permits so the identity does not depend on a third-party font request.

Red is reserved for section index markers, active playback, current selections, availability, validation warnings, and primary actions. It is not used as a background wash.

All authored public copy is lowercase in the HTML or data. CSS text transformation is not the primary mechanism.

### homepage

The first viewport contains:

- a thin utility row with `christon.xyz`, Instagram, email, sound state, and business availability;
- the oversized christon wordmark;
- a short producer and sound-designer statement;
- a numbered content index.

The index contains beats, drumkits, go to vsts, A2V, and business inquiries. Only one row can be expanded at a time. Opening a row closes the previous row and updates the URL hash so that an expanded state can be linked. The control uses real buttons and correct expanded-state attributes for keyboard and screen-reader use.

Expanded content is specific to each row:

- Beats shows the first three published beats in catalog order, including play controls, waveform, title, BPM, key, and a link to the complete archive.
- Drumkits shows a compact horizontal sequence of cover images, names, and Payhip links.
- Go to vsts shows a restrained image contact sheet with product names and no categories.
- A2V shows the transparent product render, a short description, and the purchase action.
- Business inquiries shows `softparish@gmail.com` and `@christonwords` as direct actions.

The background track remains opt-in and starts off. Starting a beat preview pauses the background track. Starting the background track stops the active preview. Playback state is always visible.

### beats archive

The beat archive is a dense editorial list, not a grid of cards. Each row includes:

- one play or pause control;
- title;
- BPM and key;
- a precomputed waveform with playback progress;
- a direct business inquiry action where space permits.

The page includes one compact search field that matches title, BPM, and key. It does not add moods or genre categories. Manual publisher order is the default order.

Only one shared audio element is used. MP3 data is requested only after the visitor presses play. Waveforms are drawn from peaks in the catalog rather than by downloading and decoding every MP3. The first 24 entries render immediately and additional entries render in groups as the visitor approaches the end of the list.

### drumkits and go to vsts

The drumkits route uses square cover art with names and direct Payhip links. The visual hierarchy favors the artwork and uses no descriptive filler copy.

The go to vsts route uses one responsive contact sheet. Images remain fully visible with `object-fit: contain`; product names sit on a consistent baseline. There are no categories.

### A2V

The A2V page keeps its separate dark, product-launch identity and transparent product box. It gains a quiet, consistent route back to christon.xyz. No install-location language is introduced because the app is portable.

### motion and responsiveness

Motion is limited to purposeful state changes:

- index open and close;
- waveform playback progress;
- restrained pointer feedback on interactive media;
- confirmation feedback after an action.

Reduced-motion preferences disable nonessential transitions. Desktop layout uses a wide editorial measure. Mobile preserves the same information order, uses full-width rows, avoids clipped wordmarks, and keeps all playback and contact actions reachable without horizontal scrolling.

## local beat publisher

### architecture

The publisher remains a local Python application serving an HTML interface on `127.0.0.1`. It uses:

- SQLite for private local catalog and draft state;
- FFmpeg and FFprobe for audio analysis and export;
- Git commands for narrowly scoped commits and pushes;
- separate Python modules for catalog storage, audio work, publishing, and HTTP routes;
- separate HTML, CSS, and JavaScript assets instead of one embedded HTML string.

Private data is stored under `.beat_publisher_data/` and ignored by Git. The database is not part of the website and is never pushed.

The server accepts connections only on the loopback address. Every launch creates a random session token, and all state-changing requests require that token and a same-origin request. Imported names and generated paths are normalized and constrained to their owned directories before any write or deletion.

### persistent beat record

Each local beat record contains:

- stable internal UUID;
- source WAV path and file fingerprint;
- original filename;
- public title, BPM, key, and slug;
- source duration;
- preview start and fixed 30-second preview duration;
- normalization preference;
- manual public order;
- status: draft, ready, published, hidden, or removed;
- generated preview fingerprint;
- last published fingerprint and revision;
- created and updated timestamps.

A source selected through the native Windows file or folder picker remains linked in place. Dragged files may use an app-managed local working copy so browser security does not prevent resuming the draft. The interface identifies managed copies clearly and offers cleanup only after a successful publish.

### workspace layout

The desktop workspace has three persistent areas:

- Left: batch import, search, status filters, and the draggable catalog queue.
- Center: selected beat metadata, full-source waveform, draggable 30-second region, preview player, and approval controls.
- Right: pending-change summary, validation checklist, Git state, and publish action.

The publisher shares the public site's white, black, and red system but is denser and more operational. It does not imitate the public homepage at the expense of clarity.

### batch import

The user can choose multiple WAV files or a folder. Analysis runs concurrently with a conservative worker limit so the computer remains responsive. Each file gets:

- filename metadata parsing;
- duration probing;
- source fingerprinting and duplicate detection;
- waveform peak generation;
- a suggested preview range based on sustained energy and a complete usable passage.

Filename parsing is only a suggestion. Uncertain or missing metadata creates a visible flag but does not stop other imports. Duplicate source fingerprints, duplicate slugs, unsupported files, and unreadable WAVs receive distinct messages.

### preview editor

The full-source waveform displays the proposed 30-second region. The region can be dragged as a unit or adjusted by entering an exact start time. Its duration remains locked to 30 seconds. Controls include:

- play the full source from the current selection;
- audition the exact encoded MP3 preview;
- restore the smart selection;
- toggle normalization;
- approve and advance to the next flagged or unreviewed beat.

Metadata edits and selection changes autosave to SQLite. Keyboard controls cover play or pause, small selection nudges, larger selection nudges, approve and next, and moving through the queue.

### catalog management

The queue supports drag-and-drop ordering, multi-selection, search, and filters for draft, ready, published, hidden, and removed. Published entries can be edited, hidden, reordered, have their preview replaced, or be marked for removal.

Removal is soft until a publish succeeds. Before publishing, the user can undo it. After publishing, the public asset is removed from the working tree but remains recoverable from Git history.

## public data and generated assets

Publishing writes only managed files under `beats/`:

- `beats/catalog.json`;
- `beats/previews/<slug>-<content-hash>.mp3`;
- the site assets that are explicitly owned by the beat catalog.

Each public catalog entry includes stable ID, slug, title, BPM, key, preview URL, duration, order, and a normalized array of 240 waveform peak values. Peaks are embedded in the catalog because they remain small and eliminate one request per visible beat.

MP3 previews are exactly 30 seconds, use a web-appropriate stereo MP3 setting around 160 kbps, and include short boundary fades. Optional normalization uses a consistent transparent target across the batch. Content-hashed filenames provide durable browser caching and make preview replacement reliable.

The catalog also includes a schema version, revision identifier, and published timestamp. The public code rejects an unsupported schema with a useful empty state rather than failing silently.

## publishing flow

The publish action opens a review screen showing additions, edits, reorderings, hides, removals, generated file sizes, and validation warnings.

On confirmation, the publisher:

1. verifies every ready entry and source dependency;
2. renders new previews and waveform peaks into a staging directory;
3. validates exact duration, decodability, metadata, unique slugs, asset paths, and catalog order;
4. writes the new catalog and assets into managed `beats/` paths;
5. stages only the exact managed files changed by this publish;
6. creates one commit such as `publish 4 beat previews`;
7. pushes the current branch to its configured upstream;
8. polls the public catalog revision and reports when that revision is live.

Unrelated modified or untracked files are never staged. They are shown as an informational warning only. This protects manual site work and the user's uncommitted drumkit changes.

## failure handling

- A failed file analysis affects only that queue item.
- A missing source reopens as `relink required`; published output remains untouched.
- Export occurs in staging, so failed validation cannot partially replace the live working tree.
- If the Git commit fails, generated files remain staged for review and retry.
- If the push fails, the successful local commit is preserved and the interface offers retry push.
- If deployment polling cannot reach christon.xyz, the app reports `pushed, live status unknown` and can retry without republishing.
- Git and FFmpeg errors are summarized in plain language with expandable technical details.
- The app refuses a second simultaneous publish while one is running.
- Browser refresh or app restart restores the current batch from SQLite.
- Invalid or manipulated paths are rejected before the filesystem is touched.

## migration

On first run, the new publisher imports the current `beats/beats.json` records and existing MP3 previews into SQLite as published records. Existing preview order is preserved. Source WAVs are optional during migration and are marked `relink required` only when the user later edits their audio range.

The migration does not alter or delete current previews until the first validated publish using the new catalog format.

## verification

Automated tests cover:

- filename variants and metadata normalization;
- duplicate source and slug handling;
- preview selection bounds for short and long sources;
- exact exported duration and decodability;
- waveform peak shape and size;
- SQLite save, restart, status, and ordering behavior;
- migration from the current catalog;
- staged export rollback after failure;
- exact Git path staging and failed-push recovery;
- local session-token enforcement and generated-path containment;
- public catalog schema parsing;
- one-player-at-a-time behavior;
- search and incremental rendering with large generated catalogs.

Browser verification covers desktop and mobile layouts, keyboard focus, reduced motion, row expansion, playback progress, missing-audio errors, and the A2V route back to the archive. A large synthetic catalog verifies that the archive remains responsive before real usage reaches that size.

## success criteria

- A visitor immediately reads the site as christon's identity and body of work.
- The homepage remains visually calm with every section collapsed and useful with any one section expanded.
- No beat audio downloads before explicit playback.
- A folder of valid WAVs can be imported, reviewed, ordered, and published as one batch.
- Draft work survives browser and app restarts.
- A failed export, commit, push, or deployment check does not lose local edits or damage the previously published catalog.
- Publishing never stages unrelated files.
- The finished site and app remain lowercase, responsive, accessible, and free to host on GitHub Pages.
