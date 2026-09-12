---
name: audio-to-ogg
description: Converts a single audio file to OGG Vorbis using FFmpeg for Godot-ready compressed assets. Use when the user wants to convert audio to OGG, transcode WAV/MP3/FLAC/AAC to OGG, export a Godot-ready OGG asset, or mentions Vorbis, libvorbis, or Godot audio import.
---

# Audio to OGG

Convert a supported audio file to **OGG Vorbis** via FFmpeg. **Defaults preserve source sample rate** and encode at **Vorbis quality 10** (maximum) for minimal generation loss.

## Rules

When this skill applies, read and follow [skill-dependency-manager](../skill-dependency-manager.md) 鈥?run scripts as documented, install missing tools into `.dependency/`.

## Quick Start

Default output: `<audio-dir>/audio-to-ogg/<basename>.ogg`

```bash
.dependency/python/python .ai/audio-to-ogg/convert.py --audio path/to/audio.wav
```

Example: `audio/sfx/tank/tank_move.wav` 鈫?`audio/sfx/tank/audio-to-ogg/tank_move.ogg`

## Format Defaults

| Setting | Default | Notes |
|---------|---------|-------|
| Codec | OGG Vorbis (`libvorbis`) | Godot-native compressed format |
| Sample rate | Preserve source | Always keeps source rate; no resampling |
| Quality | `10` (`-q 10`) | Maximum Vorbis quality (~500 kbps VBR); use lower `-q` to shrink files |
| Channels | Preserve source | Use `--mono` or `--stereo` to force |
| Existing Vorbis OGG | Stream copy | Bit-perfect when no overrides |

## Quality Guide

| `-q` | Approx. bitrate | Typical use |
|------|-----------------|-------------|
| 10 | ~500 kbps | **Default** 鈥?highest fidelity |
| 7鈥? | ~224鈥?56 kbps | Smaller music/voice exports |
| 5鈥? | ~160鈥?92 kbps | Gameplay SFX, BGM |
| 3鈥? | ~96鈥?28 kbps | Short UI clicks, ambient loops |

## Common Flags

`--audio` 路 `-o` / `--output` 路 `-q` / `--quality` 路 `--mono` 路 `--stereo`

Lower quality for UI sounds:

```bash
.dependency/python/python .ai/audio-to-ogg/convert.py --audio path/to/click.wav -q 4
```

Custom output path:

```bash
.dependency/python/python .ai/audio-to-ogg/convert.py --audio path/to/audio.wav --output path/to/out.ogg
```

**Never overwrite source files.** The script writes only under `audio-to-ogg/` (or `--output`). Input must be a single audio file (`--audio`), not a directory. Supported inputs: `.mp3`, `.ogg`, `.flac`, `.aac`, `.m4a`, `.wma`, `.wav`.

## Agent Notes

1. Use the bundled script, not hand-written `ffmpeg -i 鈥 commands.
2. **Sample rate is always preserved** 鈥?use the `audio-sample-rate-standardize` skill if resampling is needed.
3. **Already Vorbis OGG?** Stream-copied by default (no generation loss).
4. Missing Python/FFmpeg 鈫?populate `.dependency/` per skill-dependency-manager, retry same command.
5. **Do not copy, move, or replace the source with converted output** 鈥?tell the user where output files are; they swap assets manually when ready.
6. FFmpeg codec and quality details: [reference.md](reference.md)

## Tests

From repo root:

```bash
.dependency/python/python .ai/audio-to-ogg/test_convert.py
```

Manual CLI examples: [cli/audio-to-ogg.md](../../../cli/audio-to-ogg.md)
