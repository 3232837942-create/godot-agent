---
name: video-merge-gpu
description: >-
  Merges multiple videos from a folder (sorted by filename) into one clip with a
  random xfade transition (0.5s) between each pair; freeze-pads so total duration
  equals the sum of sources. Encodes with GPU HEVC only (NVENC / AMF / QSV 鈥?no
  CPU libx265 fallback). Exports 3840脳2160 60fps H.265 Main10 40Mbps + AAC
  320kbps. Use when the user wants video-merge-gpu, GPU video merge, NVENC merge,
  hevc_nvenc concat, GPU 鎷兼帴, 瑙嗛鎷兼帴 GPU, or batch stitch clips with xfade on GPU.
disable-model-invocation: true
---

# Video Merge GPU

Same merge as [`video-merge`](../video-merge/SKILL.md): concatenate every video in a folder (filename sort) into **one** high-quality MP4, random FFmpeg `xfade` (0.5s) + matching `acrossfade`, freeze-pad so output length equals the sum of source durations.

**GPU encode only.** Probe `hevc_nvenc` 鈫?`hevc_amf` 鈫?`hevc_qsv` (HEVC Main10). If none work, **fail** 鈥?do not fall back to `libx265`. Use `video-merge` when CPU encode is wanted.

xfade / scale / pad still run on CPU; only the H.265 encode is hardware.

## Rules

When this skill applies, read and follow [skill-dependency-manager](../skill-dependency-manager.md) 鈥?run scripts as documented, install missing tools into `.dependency/`.

- Run `merge.py` through **`.dependency/python/python.exe`**. Never use host `python` / `ffmpeg`.
- **Never overwrite sources.** Outputs go under `video-merge-gpu/`.
- Use the bundled script 鈥?do not hand-write equivalent FFmpeg commands.
- **Folder input only** 鈥?pass `--folder` with a directory of clips (top-level files; no recurse).

## Quick Start

```bash
.dependency/python/python .ai/video-merge-gpu/merge.py --folder path/to/clips
```

Example:

```
assets/shots/
  01.mp4
  02.mp4
  03.mp4
鈫?assets/shots/video-merge-gpu/shots.mp4
```

## Output Spec (fixed)

| Setting | Value |
|---------|-------|
| Resolution | 3840脳2160 (scale + letterbox pad) |
| Frame rate | 60 fps |
| Video | H.265 Main10 (GPU: `hevc_nvenc` / `hevc_amf` / `hevc_qsv`, `p010le`) @ **40 Mbps** |
| Audio | AAC **320 kbps**, 48 kHz stereo |
| Transition | **0.5 s**, random from the pool below (freeze-pad; duration preserved) |
| Container | `.mp4` (`hvc1` tag) |

## Transition Pool (random per cut)

`fade` 路 `dissolve` 路 `wipeleft` 路 `wiperight` 路 `wipeup` 路 `wipedown` 路 `slideleft` 路 `slideright` 路 `circlecrop` 路 `pixelize` 路 `distance` 路 `radial` 路 `smoothleft` 路 `smoothright` 路 `circleopen` 路 `circleclose` 路 `diagtl` 路 `diagtr` 路 `hblur` 路 `zoomin`

Each cut independently samples one transition. Printed in the run log.

## Common Flags

`--folder` 路 `-o` / `--output`

```bash
.dependency/python/python .ai/video-merge-gpu/merge.py --folder clips
.dependency/python/python .ai/video-merge-gpu/merge.py --folder clips -o out/final.mp4
```

**Never overwrite source files.** Input must be a folder (`--folder`), not a single video file. Only top-level videos in the folder (no recurse). Supported: `.mp4`, `.mkv`, `.mov`, `.avi`, `.webm`, `.wmv`, `.flv`, `.m4v`, `.mpeg`, `.mpg`, `.ts`, `.mts`, `.m2ts`, `.3gp`, `.ogv`.

## Agent Notes

1. Use the bundled script 鈥?do **not** hand-write `ffmpeg` xfade chains.
2. Transition duration is fixed at **0.5s** 鈥?no duration override flag.
3. Every clip **except the first** must be **longer than 0.5s** (incoming side of `xfade`).
4. Single file in the folder 鈫?re-encode to the output spec with no transition.
5. Many clips (4K10) auto-chunk (max 8 inputs per filtergraph) to avoid OOM; transitions stay correct across chunk boundaries.
6. **No CPU fallback.** Missing GPU HEVC Main10 鈫?report the probe failure; suggest `video-merge` only if the user accepts CPU.
7. Missing Python/FFmpeg 鈫?populate `.dependency/` per skill-dependency-manager, retry.
8. FFmpeg filter / encoder details: [reference.md](reference.md)

## Tests

From repo root:

```bash
.dependency/python/python .ai/video-merge-gpu/test_merge.py
```

Manual CLI examples: [cli/video-merge-gpu.md](../../../cli/video-merge-gpu.md)
