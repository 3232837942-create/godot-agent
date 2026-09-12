# video-to-60fps

unit tests:

```bash
.dependency/python/python .ai/video-to-60fps/test_convert.py
```

Manual CLI (default output: `<video-dir>/video-to-60fps/<basename>.mp4`):

```bash
.dependency/python/python .ai/video-to-60fps/convert.py --video .ai/test/video/opening.mp4
```

Select GPU and force UHD RIFE mode:

```bash
.dependency/python/python .ai/video-to-60fps/convert.py --video .ai/test/video/opening.mp4 --gpu 0 --uhd
```

Custom output path:

```bash
.dependency/python/python .ai/video-to-60fps/convert.py --video .ai/test/video/opening.mp4 --output .ai/test/video/video-to-60fps/opening.mp4
```
