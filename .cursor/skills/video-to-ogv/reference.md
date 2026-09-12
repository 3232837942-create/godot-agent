# Video to OGV — Reference

## Default Pipeline (lossy sources)

Per file, the script probes with `ffprobe` then runs two stages:

```bash
# Stage 1 — lossless intermediate (FFV1 level 3 + FLAC)
ffmpeg -i input.mp4 -map 0:v:0 -c:v ffv1 -level 3 -pix_fmt yuv420p \
  -map 0:a:0 -c:a flac -compression_level 0 video-to-ogv/lossless/intro.mkv

# Stage 2 — max-quality Theora from pristine frames
ffmpeg -i video-to-ogv/lossless/intro.mkv -c:v libtheora -q:v 10 -c:a libvorbis -q:a 10 video-to-ogv/intro.ogv
```

Already **Theora+Vorbis OGV** → stream copy (no re-encode).

Already **lossless source** (FFV1, HuffYUV, …) → skip stage 1, encode OGV directly at q=10.

## Alternate Modes

| Flag | Pipeline |
|------|----------|
| (default) | FFV1+FLAC MKV → Theora q=10 OGV |
| `--clean-lossless` | Delete intermediate MKV after successful OGV export |
| `--standardize` | Resample audio to 48 kHz before encode |

## Why Lossless Intermediate?

H.264/HEVC → Theora directly applies **two lossy codecs in sequence** (generation loss). Decoding to FFV1 first gives Theora a clean frame buffer — only one lossy generation remains (Theora itself). This is the workflow Godot documents for best OGV quality.

## Intermediate Layout

For `Video/intro.mp4`:

```
Video/video-to-ogv/lossless/intro.mkv   # FFV1+FLAC (large)
Video/video-to-ogv/intro.ogv             # final Godot asset
```

Run one file per invocation with `--video`. Repeat for each clip in a folder.

## Godot Notes

- Godot imports `.ogv` as `VideoStreamTheora` without extra transcoding.
- OGV is the native open-format choice; MP4/H.264 is not supported in core Godot.
- Point `VideoStreamPlayer.stream` at the `.ogv` file, not the source `.mp4`.
