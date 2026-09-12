# video-publish

Agent-only skill — write a multi-platform publish pack. No bundled script under `.ai/`.

Output directory:

| Mode | Write files to |
|------|----------------|
| User provides an input file | That file's parent directory |
| No input file | Project root |

Required output files (overwrite if present):

- `zhihu.md` — Chinese Zhihu article
- `reddit.md` — English Reddit post
- `covers-landscape.md` — 3 landscape cover prompts
- `covers-portrait.md` — 3 portrait cover prompts
- `platforms.md` — title / description / tags for 8 platforms
