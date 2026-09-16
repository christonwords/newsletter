# beat publisher

local batch preview editor for `christon.xyz/beats`. source wavs and app state stay in `.beat_publisher_data/` and are never committed.

## run

requirements: python 3.11+, ffmpeg, ffprobe, and git.

double-click `run_beat_publisher.bat`, or run:

```powershell
python tools\beat_publisher\app.py
```

the app binds only to `127.0.0.1` and opens a token-protected local page.

## workflow

1. choose several wav files at once.
2. review parsed title, bpm, and key in the queue.
3. move the fixed 30-second range with the slider, waveform, arrow keys, or shift+arrow keys.
4. make and listen to the encoded mp3, then approve it.
5. reorder with drag and drop or the arrow buttons. use status to hide, restore, or remove previews.
6. review publish, then create and push one scoped git commit.

if github rejects a push, the commit remains local and the app shows `retry github push`. reopening the app restores metadata, order, status, and preview ranges from sqlite.

## tests

```powershell
python -m unittest discover -s tools\beat_publisher\tests -v
npm.cmd test
```
