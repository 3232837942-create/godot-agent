# Audio to OGG — Reference

## Default Command Shape

Per file, the script probes with `ffprobe` then builds:

```bash
# Lossless or lossy source — preserve rate, Vorbis q=10
ffmpeg -i input.wav -c:a libvorbis -q:a 10 output.ogg

# Already Vorbis OGG — stream copy (no generation loss)
ffmpeg -i input.ogg -c:a copy output.ogg
```

## Flags

| Flag | Effect |
|------|--------|
| (default) | Preserve sample rate, Vorbis q=10 |
| `-q 6` | Balanced quality (~192 kbps) |
| `-q 4` | Lower quality (~128 kbps) |
| `--mono` / `--stereo` | Force channel layout |

Sample rate is always preserved. For resampling, use the `audio-sample-rate-standardize` skill first.

## Vorbis Quality Scale

FFmpeg `-q:a` maps to libvorbis quality 0–10 (higher = larger files, better fidelity).

| Quality | Approx. stereo bitrate |
|---------|------------------------|
| 0 | ~64 kbps |
| 3 | ~96 kbps |
| 4 | ~128 kbps |
| 5 | ~160 kbps |
| 6 | ~192 kbps |
| 7 | ~224 kbps |
| 8 | ~256 kbps |
| 10 | ~500 kbps |

Actual bitrate varies by content (VBR).

## Supported Input Formats

`.mp3`, `.ogg`, `.flac`, `.aac`, `.m4a`, `.wma`, `.wav`

## Output Layout

For `Audio/SFX/click.wav` with default output:

```
Audio/SFX/audio-to-ogg/click.ogg
```

Pass `--output` for an explicit file or directory.

## Godot Notes

- Godot imports `.ogg` as `AudioStreamOggVorbis` without extra import settings.
- Prefer OGG for shipped game assets; keep WAV/FLAC as source masters.
- Loop points and streaming are configured in Godot import metadata, not during FFmpeg conversion.
