# audio-to-ogg

unit tests:

```bash
.dependency/python/python .ai/audio-to-ogg/test_convert.py
```

Manual CLI (default output: `<audio-dir>/audio-to-ogg/<basename>.ogg`):

```bash
.dependency/python/python .ai/audio-to-ogg/convert.py --audio .ai/test/audio/han.wav
```

Lower quality for smaller files:

```bash
.dependency/python/python .ai/audio-to-ogg/convert.py --audio .ai/test/audio/han.wav -q 4
```

Custom output path:

```bash
.dependency/python/python .ai/audio-to-ogg/convert.py --audio .ai/test/audio/han.wav --output .ai/test/audio/audio-to-ogg/han.ogg
```
