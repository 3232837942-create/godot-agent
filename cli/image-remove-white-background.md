# image-remove-white-background

Manual CLI only. Uses the **`image-remove-white-background`** venv, not default `python`.

Unix: `.dependency/image-remove-white-background/.venv/bin/python`

Default white preset (output: `<image-dir>/image-remove-white-background/<image-name>.png`):

```bash
.dependency/image-remove-white-background/.venv/Scripts/python.exe .ai/image-remove-white-background/remove_white_bg.py --image .ai/test/image/tank1.jpg
```

Green screen preset:

```bash
.dependency/image-remove-white-background/.venv/Scripts/python.exe .ai/image-remove-white-background/remove_white_bg.py --image .ai/test/image/tank1.jpg --preset green
```

Border flood-fill mode (preserve interior same-color details):

```bash
.dependency/image-remove-white-background/.venv/Scripts/python.exe .ai/image-remove-white-background/remove_white_bg.py --image .ai/test/image/tank2.jpg --mode border
```

Custom output directory:

```bash
.dependency/image-remove-white-background/.venv/Scripts/python.exe .ai/image-remove-white-background/remove_white_bg.py --image .ai/test/image/tank1.jpg -o .ai/test/image/image-remove-white-background/
```
