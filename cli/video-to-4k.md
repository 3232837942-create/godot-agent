# video-to-4k

unit tests:

```bash
.dependency/python/python .ai/video-to-4k/test_convert.py
```

Manual CLI (default output: `<video-dir>/video-to-4k/<basename>.mp4`, intermediate: `<video-dir>/video-to-4k/upscaled/<basename>.mkv`):

```bash
.dependency/python/python .ai/video-to-4k/convert.py --video .ai/test/video/opening.mp4
```

Anime / cartoon content:

```bash
.dependency/python/python .ai/video-to-4k/convert.py --video .ai/test/video/opening.mp4 --anime
```

Delete upscaled intermediate after successful export:

```bash
.dependency/python/python .ai/video-to-4k/convert.py --video .ai/test/video/opening.mp4 --clean-upscaled
```

Custom output path:

```bash
.dependency/python/python .ai/video-to-4k/convert.py --video .ai/test/video/opening.mp4 --output .ai/test/video/video-to-4k/opening.mp4
```
