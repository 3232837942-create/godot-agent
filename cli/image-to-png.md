# image-to-png

unit tests:

```bash
.dependency/python/python .ai/image-to-png/test_convert.py
```

Manual CLI (default output: `<image-dir>/image-to-png/<image-name>.png`):

```bash
.dependency/python/python .ai/image-to-png/convert.py --image .ai/test/image/tank1.jpg
```

Strip alpha (RGB output):

```bash
.dependency/python/python .ai/image-to-png/convert.py --image .ai/test/image/tank2.jpg --strip-alpha
```

Custom output path:

```bash
.dependency/python/python .ai/image-to-png/convert.py --image .ai/test/image/tank1.jpg -o .ai/test/image/image-to-png/
```
