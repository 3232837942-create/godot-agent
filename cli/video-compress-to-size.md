# video-compress-to-size

unit tests:

```bash
.dependency/python/python .ai/video-compress-to-size/test_compress.py
```

Manual CLI (default output: `<video-dir>/video-compress-to-size/<basename>.mp4`):

```bash
.dependency/python/python .ai/video-compress-to-size/compress.py --video .ai/test/video/opening.mp4 --max-size 1MB
```

Bare numbers mean MB:

```bash
.dependency/python/python .ai/video-compress-to-size/compress.py --video .ai/test/video/opening.mp4 --max-size 50
```

Force CPU two-pass:

```bash
.dependency/python/python .ai/video-compress-to-size/compress.py --video .ai/test/video/opening.mp4 --max-size 50MB --cpu
```

Custom output path:

```bash
.dependency/python/python .ai/video-compress-to-size/compress.py --video .ai/test/video/opening.mp4 --max-size 50MB --output .ai/test/video/video-compress-to-size/opening.mp4
```
