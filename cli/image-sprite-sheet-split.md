# image-sprite-sheet-split

unit tests:

```bash
.dependency/python/python .ai/image-sprite-sheet-split/test_split_frames.py
```

Manual CLI (default output: `<image-dir>/image-sprite-sheet-split/<sheet-stem>/`):

```bash
.dependency/python/python .ai/image-sprite-sheet-split/split_frames.py --image .ai/test/image/tank1.jpg --grid 1x1
```

4×4 grid:

```bash
.dependency/python/python .ai/image-sprite-sheet-split/split_frames.py --image sheet.png --grid 4x4
```

3×6 grid:

```bash
.dependency/python/python .ai/image-sprite-sheet-split/split_frames.py --image sheet.png --grid 6x3
```

Custom output root:

```bash
.dependency/python/python .ai/image-sprite-sheet-split/split_frames.py --image sheet.png --grid 4x4 -o image/effects/frames/
```
