# audio-sample-rate-standardize

unit tests:

```bash
.dependency/python/python .ai/audio-sample-rate-standardize/test_standardize.py
```

Manual CLI (default output: `<audio-dir>/audio-sample-rate-standardize/<name>.wav`):

```bash
.dependency/python/python .ai/audio-sample-rate-standardize/standardize.py --audio .ai/test/audio/han.wav
```

Custom output path:

```bash
.dependency/python/python .ai/audio-sample-rate-standardize/standardize.py --audio .ai/test/audio/han.wav --output .ai/test/sample-rate
```
