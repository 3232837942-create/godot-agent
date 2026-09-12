# audio-fade

unit tests:

```bash
.dependency/python/python .ai/audio-fade/test_fade.py
```

Manual CLI (default output: `<audio-dir>/audio-fade/<audio-name>`):

```bash
.dependency/python/python .ai/audio-fade/fade.py --audio .ai/test/audio/han.wav -fi 2 -fo 2
```

Custom output path:

```bash
.dependency/python/python .ai/audio-fade/fade.py --audio .ai/test/audio/han.wav --output .ai/test/fade
```
