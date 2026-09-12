# video-merge

unit tests:

```bash
.dependency/python/python .ai/video-merge/test_merge.py
```

Manual CLI (default output: `<folder>/video-merge/<folder-name>.mp4`):

```bash
.dependency/python/python .ai/video-merge/merge.py --folder .ai/test/video
```

Custom output path:

```bash
.dependency/python/python .ai/video-merge/merge.py --folder .ai/test/video --output .ai/test/video/video-merge/final.mp4
```
