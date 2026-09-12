# audio-loudness-normalization

unit tests:

```bash
.dependency/python/python .ai/audio-loudness-normalization/test_normalize.py
```

Manual CLI (default output: `<audio-dir>/audio-loudness-normalization/<audio-name>`):

```bash
.dependency/python/python .ai/audio-loudness-normalization/normalize.py --audio .ai/test/audio/han.wav
```

Custom LUFS:

```bash
.dependency/python/python .ai/audio-loudness-normalization/normalize.py --audio .ai/test/audio/han.wav -t -16
```

Custom output path:

```bash
.dependency/python/python .ai/audio-loudness-normalization/normalize.py --audio .ai/test/audio/han.wav -output .ai/test/loudness
```
