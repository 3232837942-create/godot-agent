# video-4k-normalization

unit tests:

```bash
.dependency/python/python .ai/video-4k-normalization/test_normalize.py
```

Manual CLI (default output: `<video-dir>/video-4k-normalization/<basename>.mp4`):

```bash
.dependency/python/python .ai/video-4k-normalization/normalize.py --video .ai/test/video/opening.mp4
```

Custom output path:

```bash
.dependency/python/python .ai/video-4k-normalization/normalize.py --video .ai/test/video/opening.mp4 --output .ai/test/video/video-4k-normalization/opening.mp4
```
