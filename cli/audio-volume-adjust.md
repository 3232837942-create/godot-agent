# audio-volume-adjust

unit tests:

```bash
.dependency/python/python .ai/audio-volume-adjust/test_adjust.py
```

Manual CLI (default output: `<audio-dir>/audio-volume-adjust/<audio-name>`):

```bash
.dependency/python/python .ai/audio-volume-adjust/adjust.py --audio .ai/test/audio/han.wav --volume -12
```

Custom output path:

```bash
.dependency/python/python .ai/audio-volume-adjust/adjust.py --audio .ai/test/audio/han.wav --volume 12 --output .ai/test/audio-volume-adjust
```
