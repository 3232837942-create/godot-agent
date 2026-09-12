# image-trim

Uses the **`image-trim`** venv, not default `python`.

Unix: `.dependency/image-trim/.venv/bin/python`

Unit tests (assert output size differs from source; default mode keeps aspect ratio):

```bash
.dependency/image-trim/.venv/Scripts/python.exe .ai/image-trim/test_trim.py
```

Manual CLI (default output: `<image-dir>/image-trim/<image-name>`):

```bash
.dependency/image-trim/.venv/Scripts/python.exe .ai/image-trim/trim.py --image .ai/test/image/tank1.jpg
```

Alpha-only trim on RGBA cutout:

```bash
.dependency/image-trim/.venv/Scripts/python.exe .ai/image-trim/trim.py --image .ai/test/image/tank2.jpg --mode alpha
```

Trim white padding on opaque image:

```bash
.dependency/image-trim/.venv/Scripts/python.exe .ai/image-trim/trim.py --image .ai/test/image/tank3.jpg --mode color --color FFFFFF
```

Tight crop (no aspect-ratio lock):

```bash
.dependency/image-trim/.venv/Scripts/python.exe .ai/image-trim/trim.py --image .ai/test/image/tank1.jpg --tight
```

Keep 4 px breathing room:

```bash
.dependency/image-trim/.venv/Scripts/python.exe .ai/image-trim/trim.py --image .ai/test/image/tank1.jpg --padding 4
```

Custom output path:

```bash
.dependency/image-trim/.venv/Scripts/python.exe .ai/image-trim/trim.py --image .ai/test/image/tank1.jpg -o .ai/test/image/image-trim/
```
