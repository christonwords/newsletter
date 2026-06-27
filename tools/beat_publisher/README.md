# beat publisher

local app for creating 30 second mp3 previews from full wav beats.

run from the repo root:

```powershell
python tools/beat_publisher/app.py
```

workflow:

1. import a full wav.
2. the app reads title, bpm, and key from the filename.
3. it suggests a preview start by scanning the loudest usable section.
4. adjust the start time if needed.
5. click `make preview`.
6. play the mp3 before export.
7. click `export to site`.
8. optionally check `commit and push after export`.

the `uploaded previews` section shows everything already in `beats/beats.json`.
use `up` and `down` to set the public order, `play` to audition an uploaded preview, or `remove` to delete it from the site.
with `commit and push after export` checked, exports, reorders, and removals are committed and pushed too.

full wavs stay local in `.beat_publisher_tmp/` while the app is running. only 30 second mp3 previews and `beats/beats.json` are meant to be committed.
