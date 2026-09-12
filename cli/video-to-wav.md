# video-to-wav

unit tests:

```bash
.dependency/python/python .ai/video-to-wav/test_convert.py
```

Manual CLI (default output: `<video-dir>/video-to-wav/<basename>.wav`):

```bash
.dependency/python/python .ai/video-to-wav/convert.py --video .ai/test/video/opening.mp4
```

Explicit audio track (0-based):

```bash
.dependency/python/python .ai/video-to-wav/convert.py --video .ai/test/video/opening.mp4 --track 0
```

Custom output path:

```bash
.dependency/python/python .ai/video-to-wav/convert.py --video .ai/test/video/opening.mp4 --output .ai/test/video/video-to-wav/opening.wav
```
