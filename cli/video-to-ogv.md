# video-to-ogv

unit tests:

```bash
.dependency/python/python .ai/video-to-ogv/test_convert.py
```

Manual CLI (default output: `<video-dir>/video-to-ogv/<basename>.ogv`, intermediate: `<video-dir>/video-to-ogv/lossless/<basename>.mkv`):

```bash
.dependency/python/python .ai/video-to-ogv/convert.py --video .ai/test/video/opening.mp4
```

Custom output path:

```bash
.dependency/python/python .ai/video-to-ogv/convert.py --video .ai/test/video/opening.mp4 --output .ai/test/video/video-to-ogv/opening.ogv
```

Delete lossless intermediate after successful export:

```bash
.dependency/python/python .ai/video-to-ogv/convert.py --video .ai/test/video/opening.mp4 --clean-lossless
```

Resample audio to 48 kHz:

```bash
.dependency/python/python .ai/video-to-ogv/convert.py --video .ai/test/video/opening.mp4 --standardize
```
