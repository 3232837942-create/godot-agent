# image-inpaint-region

Manual CLI only. Uses the **`iopaint`** venv (Python 3.11), not default `python`. LaMa weights download on first run.

Unix: `.dependency/iopaint/.venv/bin/python`

Manual CLI (default output: `<image-dir>/image-inpaint-region/<image-name>.png`):

```bash
.dependency/iopaint/.venv/Scripts/python.exe .ai/image-inpaint-region/inpaint.py --image .ai/test/image/girl.png --region 512,300,64
```

GPU inference:

```bash
.dependency/iopaint/.venv/Scripts/python.exe .ai/image-inpaint-region/inpaint.py --image .ai/test/image/tank1.jpg --region 512,512,64 --device cuda
```

Custom output path:

```bash
.dependency/iopaint/.venv/Scripts/python.exe .ai/image-inpaint-region/inpaint.py --image .ai/test/image/tank1.jpg --region 512,512,64 -o .ai/test/image/image-inpaint-region/
```
