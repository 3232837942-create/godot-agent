# audio-split

unit tests:

```bash
.dependency/python/python .ai/audio-split/test_split.py
```

Manual CLI (default output: `<audio-dir>/audio-split/<basename>_part1.ext` and `<basename>_part2.ext`):

```bash
.dependency/python/python .ai/audio-split/split.py --audio .ai/test/audio/han.wav
```

Split at a specific time (seconds):

```bash
.dependency/python/python .ai/audio-split/split.py --audio .ai/test/audio/han.wav -s 1.25
```

Custom output directory:

```bash
.dependency/python/python .ai/audio-split/split.py --audio .ai/test/audio/han.wav --output .ai/test/split
```
