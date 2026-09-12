# audio-to-wav

unit tests:

```bash
.dependency/python/python .ai/audio-to-wav/test_convert.py
```

Manual CLI (default output: `<audio-dir>/audio-to-wav/<basename>.wav`):

```bash
.dependency/python/python .ai/audio-to-wav/convert.py --audio .ai/test/audio/han.wav
```

Force 16-bit PCM:

```bash
.dependency/python/python .ai/audio-to-wav/convert.py --audio .ai/test/audio/han.wav -b 16
```

Custom output path:

```bash
.dependency/python/python .ai/audio-to-wav/convert.py --audio .ai/test/audio/han.wav --output .ai/test/audio/audio-to-wav/han.wav
```
