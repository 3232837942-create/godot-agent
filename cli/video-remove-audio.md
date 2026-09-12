# video-remove-audio

unit tests:

```bash
.dependency/python/python .ai/video-remove-audio/test_remove_audio.py
```

Manual CLI (default output: `<video-dir>/video-remove-audio/<basename>`):

```bash
.dependency/python/python .ai/video-remove-audio/remove_audio.py --video .ai/test/video/opening.mp4
```

Custom output path:

```bash
.dependency/python/python .ai/video-remove-audio/remove_audio.py --video .ai/test/video/opening.mp4 --output .ai/test/video/video-remove-audio/opening.mp4
```
