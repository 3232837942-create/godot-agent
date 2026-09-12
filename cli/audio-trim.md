# audio-trim

unit tests:

```bash
.dependency/python/python .ai/audio-trim/test_trim.py
```

Manual CLI (default output: `<audio-dir>/audio-trim/<audio-name>`):

```bash
.dependency/python/python .ai/audio-trim/trim.py --audio .ai/test/audio/han.wav
```

Custom threshold:

```bash
.dependency/python/python .ai/audio-trim/trim.py --audio .ai/test/audio/han.wav -t -45
```

Custom output path:

```bash
.dependency/python/python .ai/audio-trim/trim.py --audio .ai/test/audio/han.wav --output .ai/test/trim
```
