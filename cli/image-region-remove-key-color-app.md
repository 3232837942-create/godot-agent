# image-region-remove-key-color-app

Interactive Gradio UI — manual test only. Uses the **`image-region-remove-key-color-app`** venv, not default `python`.

Unix: `.dependency/image-region-remove-key-color-app/.venv/bin/python`

Preload a test image (opens http://127.0.0.1:7860):

```bash
.dependency/image-region-remove-key-color-app/.venv/Scripts/python.exe .ai/image-region-remove-key-color-app/app.py .ai/test/image/tank1.jpg
```

Agent / headless launch (no browser auto-open):

```bash
.dependency/image-region-remove-key-color-app/.venv/Scripts/python.exe .ai/image-region-remove-key-color-app/app.py .ai/test/image/tank1.jpg --no-browser --port 7861
```

Other fixtures: `.ai/test/image/tank2.jpg`, `.ai/test/image/tank3.jpg`

White preset:

```bash
.dependency/image-region-remove-key-color-app/.venv/Scripts/python.exe .ai/image-region-remove-key-color-app/app.py .ai/test/image/tank2.jpg --preset white --no-browser --port 7861
```
