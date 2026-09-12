# storyboard

Agent-only skill — write bilingual storyboard markdown. No bundled script under `.ai/`.

Delivery:

| Mode | Behavior |
|------|----------|
| User gives a file path | Write the full storyboard markdown to that path |
| User names a directory only | Create `storyboard.md` in that directory |
| No path | Deliver the full storyboard in chat only |

Downstream CLI (after storyboard exists):

```bash
.dependency/index-tts/.venv/Scripts/python.exe .ai/storyboard-tts/synthesize.py --storyboard path/to/storyboard.md --voice .ai/test/audio/han.wav --fp16 --report
```
