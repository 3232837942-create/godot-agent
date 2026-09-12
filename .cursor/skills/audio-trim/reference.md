# Audio Trim — Reference

## FFmpeg Filter

The bundled script trims **both ends** by running `silenceremove` on the start twice, with `areverse` in between:

```
areverse,silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB,areverse,silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB
```

Do **not** combine `start_periods=1` with positive `stop_periods=1`. In FFmpeg, positive `stop_periods` does not mean “remove one trailing silence block”; with both start and stop enabled it can keep only a short middle segment and cut the rest (e.g. 6.7 s → 0.4 s).

| Parameter | Meaning |
|-----------|---------|
| `start_periods=1` | Skip one leading silence run, then keep the rest |
| `start_duration=0` | No minimum silence length before trimming begins |
| `start_threshold` | Levels at or below this are treated as silence (use `dB` suffix) |
| `areverse` | Flip audio so “start trim” can target the original tail |

## Trim vs Silence Removal

| Term | Role |
|------|------|
| **Trim / Audio Trimming** | General edit action — crop boundaries at start or end |
| **Silence Removal** | Automated batch strategy — detect silence, then delete it |

## Manual Trim (when automation is wrong)

For precise in/out points, use sample-accurate trim instead of silence detection:

```bash
ffmpeg -i input.wav -af "atrim=start=0.05:end=1.2" -y output.wav
```

Or time-based cut:

```bash
ffmpeg -ss 0.05 -to 1.2 -i input.wav -c copy -y output.wav
```

Prefer `silenceremove` for automated silence trimming; use `atrim` or `-ss`/`-to` when boundaries are known.

## Category Guidance

| Category | Trim start | Trim end | Threshold |
|----------|------------|----------|-----------|
| UI clicks | Yes | Yes | -50 dB |
| Impacts / weapons | Yes | Often yes | -50 to -45 dB |
| Voice lines | Yes | Yes | -50 dB (watch breath) |
| BGM loops | Rarely | **Avoid** | N/A — manual |
| Ambience beds | Careful | Careful | -60 dB or skip |
