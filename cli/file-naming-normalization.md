# file-naming-normalization

unit tests:

```bash
.dependency/python/python .ai/file-naming-normalization/test_normalize.py
```

Manual CLI (dry-run preview, in-place rename):

```bash
.dependency/python/python .ai/file-naming-normalization/normalize.py path/to/folder --dry-run
```

Strip custom segment text:

```bash
.dependency/python/python .ai/file-naming-normalization/normalize.py path/to/folder --strip SFX --strip UI --dry-run
```

Recursive + copy to output folder (originals unchanged):

```bash
.dependency/python/python .ai/file-naming-normalization/normalize.py path/to/folder -r -o normalized/
```
