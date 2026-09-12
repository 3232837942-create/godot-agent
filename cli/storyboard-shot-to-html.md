# storyboard-shot-to-html

Agent-only skill — write a self-contained shot preview `.html`. No bundled script under `.ai/`.

Open preview in the system browser (Windows):

```bash
Start-Process path\to\shot-01-preview.html
```

If `file://` is flaky, serve the parent directory from repo root:

```bash
.dependency/python/python -m http.server 8765 --directory path\to\preview-dir
Start-Process http://127.0.0.1:8765/shot-01-preview.html
```

Unix:

```bash
open path/to/shot-01-preview.html
.dependency/python/python -m http.server 8765 --directory path/to/preview-dir
xdg-open http://127.0.0.1:8765/shot-01-preview.html
```
