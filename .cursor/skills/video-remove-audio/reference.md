# Video Remove Audio — Reference

## Command Shape (stream copy)

The script probes for audio streams, then builds:

```bash
# Drop all audio; copy video bitstream unchanged
ffmpeg -i input.mp4 -map 0:v -c:v copy -an output.mp4
```

`-map 0:v` keeps every video stream. `-an` discards all audio. Subtitles/data streams are not mapped by default (video-only mute export).

## Already Silent

If `ffprobe` finds no audio streams, the file is skipped (`[skip]`) to avoid pointless copies.

## Notes

- Default output: `<video-dir>/video-remove-audio/<basename>` (same extension as source).
- Stream copy is bit-perfect for the video track; container remux may still change muxer metadata.
- Some players show a “no audio” track list; that is expected.
- For extracting (not removing) audio, see **video-to-wav**.
