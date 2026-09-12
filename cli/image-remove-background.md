# image-remove-background

Manual CLI only. Uses the **`rembg`** venv, not default `python`. Model weights download on first run (~hundreds of MB).

Unix: `.dependency/rembg/.venv/bin/python`

Manual CLI (default output: `<image-dir>/image-remove-background/<image-name>.png`):

```bash
.dependency/rembg/.venv/Scripts/python.exe .ai/image-remove-background/remove_background.py --image .ai/test/image/tank1.jpg
```

Default model `u2net` on another sample:

```bash
.dependency/rembg/.venv/Scripts/python.exe .ai/image-remove-background/remove_background.py --image .ai/test/image/tank2.jpg
```

Portrait model with alpha matting:

```bash
.dependency/rembg/.venv/Scripts/python.exe .ai/image-remove-background/remove_background.py --image .ai/test/image/tank1.jpg --model birefnet-portrait --alpha-matting
```

Higher quality general matting:

```bash
.dependency/rembg/.venv/Scripts/python.exe .ai/image-remove-background/remove_background.py --image .ai/test/image/tank3.jpg --model birefnet-general
```

Crop transparent borders after matting:

```bash
.dependency/rembg/.venv/Scripts/python.exe .ai/image-remove-background/remove_background.py --image .ai/test/image/tank1.jpg --crop
```

Custom output path:

```bash
.dependency/rembg/.venv/Scripts/python.exe .ai/image-remove-background/remove_background.py --image .ai/test/image/tank1.jpg -o .ai/test/image/image-remove-background/
```
