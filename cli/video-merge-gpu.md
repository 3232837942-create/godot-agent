# video-merge-gpu

unit tests:

```bash
.dependency/python/python .ai/video-merge-gpu/test_merge.py
```

Manual CLI (default output: `<folder>/video-merge-gpu/<folder-name>.mp4`):

```bash
.dependency/python/python .ai/video-merge-gpu/merge.py --folder .ai/test/video
```

Custom output path:

```bash
.dependency/python/python .ai/video-merge-gpu/merge.py --folder .ai/test/video --output .ai/test/video/video-merge-gpu/final.mp4
```
