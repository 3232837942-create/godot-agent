# audio-denoise

unit tests:

```bash
.dependency/python/python .ai/audio-denoise/test_denoise.py
```

Manual CLI (default output: `<audio-dir>/audio-denoise/<audio-name>`):

```bash
.dependency/python/python .ai/audio-denoise/denoise.py --audio .ai/test/audio/zhu_ba_jie.wav
```

Custom output path:

```bash
.dependency/python/python .ai/audio-denoise/denoise.py --audio .ai/test/audio/zhu_ba_jie.wav --output .ai/test/denoise
```
