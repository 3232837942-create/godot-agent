# storyboard-tts

unit tests (default python):

```bash
.dependency/python/python .ai/storyboard-tts/test_parse_storyboard.py
.dependency/python/python .ai/storyboard-tts/test_write_subtitles.py
```

IndexTTS batch driver (requires populated `index-tts`; not default `python`):

Unix: `.dependency/index-tts/.venv/bin/python`

```bash
.dependency/index-tts/.venv/Scripts/python.exe .ai/storyboard-tts/synthesize.py --storyboard path/to/storyboard.md --voice .ai/test/audio/han.wav --fp16 --limit 1 --report
```

Subtitles only (existing WAVs, default python):

```bash
.dependency/python/python .ai/storyboard-tts/write_subtitles.py --storyboard path/to/storyboard.md --audio-dir path/to/output-root
```
