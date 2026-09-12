# image-resize

unit tests:

```bash
.dependency/python/python .ai/image-resize/test_resize.py
```

Manual CLI (default output: `<image-dir>/image-resize/<image-name>`):

```bash
.dependency/python/python .ai/image-resize/resize.py --image .ai/test/image/tank1.jpg --width 128 --height 128
```

Cover mode (center crop to exact size):

```bash
.dependency/python/python .ai/image-resize/resize.py --image .ai/test/image/tank1.jpg --width 128 --height 128 --mode fill
```

Custom output path:

```bash
.dependency/python/python .ai/image-resize/resize.py --image .ai/test/image/tank1.jpg --width 64 --height 64 --output .ai/test/image/image-resize/
```
