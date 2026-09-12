"""Shared PCM WAV probing and FFmpeg helpers for *-to-wav skill scripts."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

BIT_DEPTH_CODECS = {
    16: "pcm_s16le",
    24: "pcm_s24le",
    32: "pcm_s32le",
}

PCM_STREAM_CODECS = {
    "pcm_s16le",
    "pcm_s24le",
    "pcm_s32le",
    "pcm_f32le",
    "pcm_s16be",
    "pcm_s24be",
    "pcm_s32be",
    "pcm_f32be",
}


def wav_output_name(source: Path, *, suffix: str = ".wav") -> str:
    """Return the default output filename for a single-file WAV export skill."""
    return source.with_suffix(suffix).name


def _probe_selected_audio(ffprobe: Path, file_path: Path, select_streams: str) -> dict:
    """Run ffprobe for one audio stream and return codec/rate/channel metadata."""
    result = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-select_streams",
            select_streams,
            str(file_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return {}

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}

    streams = payload.get("streams") or []
    if not streams:
        return {}

    stream = streams[0]
    bits_raw = stream.get("bits_per_raw_sample") or stream.get("bits_per_sample") or 0
    try:
        bits = int(bits_raw)
    except (TypeError, ValueError):
        bits = 0

    sample_rate = stream.get("sample_rate")
    try:
        sample_rate = int(sample_rate) if sample_rate else None
    except (TypeError, ValueError):
        sample_rate = None

    channels = stream.get("channels")
    try:
        channels = int(channels) if channels is not None else None
    except (TypeError, ValueError):
        channels = None

    return {
        "codec": stream.get("codec_name", ""),
        "bits": bits,
        "sample_rate": sample_rate,
        "channels": channels,
    }


def probe_audio_file(ffprobe: Path, audio_path: Path) -> dict:
    """Probe the primary audio stream in an audio file."""
    return _probe_selected_audio(ffprobe, audio_path, "a:0")


def probe_video_audio_track(ffprobe: Path, video_path: Path, track: int = 0) -> dict:
    """Probe one embedded audio track in a video container."""
    return _probe_selected_audio(ffprobe, video_path, f"a:{track}")


def resolve_bit_depth(probe: dict, forced: int | None) -> tuple[int, str]:
    """Map probe metadata (and optional override) to PCM bit depth and FFmpeg codec."""
    if forced is not None:
        return forced, BIT_DEPTH_CODECS[forced]

    bits = probe.get("bits", 0)
    codec = probe.get("codec", "")

    if bits in BIT_DEPTH_CODECS:
        return bits, BIT_DEPTH_CODECS[bits]
    if "pcm_f32" in codec or "float" in codec:
        return 32, "pcm_f32le"
    if "24" in codec:
        return 24, "pcm_s24le"
    if "16" in codec:
        return 16, "pcm_s16le"
    if codec in PCM_STREAM_CODECS:
        if "24" in codec:
            return 24, "pcm_s24le"
        if "32" in codec:
            return 32, "pcm_s32le"
        return 16, "pcm_s16le"

    return 32, "pcm_f32le"


def can_pcm_stream_copy(
    probe: dict,
    bit_depth: int | None,
    *,
    require_wav_container: bool = False,
    source_path: Path | None = None,
) -> bool:
    """Return True when output can bit-copy embedded PCM without re-encoding."""
    if bit_depth is not None:
        return False
    if require_wav_container:
        if source_path is None or source_path.suffix.lower() != ".wav":
            return False
    return probe.get("codec", "") in PCM_STREAM_CODECS


def describe_pcm_wav_plan(
    probe: dict,
    forced_depth: int | None,
    stream_copy: bool,
    *,
    track: int | None = None,
) -> str:
    """Build a short human-readable conversion plan for logging."""
    prefix = f"track {track}, " if track is not None else ""

    if stream_copy:
        rate = probe.get("sample_rate")
        bits = probe.get("bits") or "?"
        ch = probe.get("channels") or "?"
        return f"{prefix}stream copy ({rate} Hz, {bits}-bit, {ch} ch)"

    rate = probe.get("sample_rate")
    rate_text = f"{rate} Hz" if rate else "source rate"
    if forced_depth is not None:
        depth = f"{forced_depth}-bit PCM"
    else:
        _, codec = resolve_bit_depth(probe, None)
        depth = codec
    ch = probe.get("channels") or "preserve"
    return f"{prefix}{rate_text}, {depth}, {ch} ch"


def build_pcm_wav_cmd(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    codec: str,
    stream_copy: bool,
    *,
    track: int | None = None,
) -> list[str]:
    """Build an FFmpeg command that writes PCM WAV (or stream-copies embedded PCM)."""
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-nostats",
        "-y",
        "-i",
        str(file_path),
    ]
    if track is not None:
        cmd.extend(["-vn", "-map", f"0:a:{track}"])
    if stream_copy:
        cmd.extend(["-c:a", "copy", str(out_path)])
        return cmd

    cmd.extend(["-c:a", codec, str(out_path)])
    return cmd


def run_pcm_wav_ffmpeg(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    codec: str,
    stream_copy: bool,
    *,
    track: int | None = None,
    action: str = "convert",
) -> None:
    """Run FFmpeg to produce PCM WAV, raising RuntimeError on failure."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_pcm_wav_cmd(
        ffmpeg,
        file_path,
        out_path,
        codec,
        stream_copy,
        track=track,
    )
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"FFmpeg {action} failed for: {file_path}"
            + (f"\n{detail}" if detail else "")
        )


def add_bit_depth_arg(parser: argparse.ArgumentParser) -> None:
    """Register -b / --bit-depth on a skill argument parser."""
    parser.add_argument(
        "-b",
        "--bit-depth",
        type=int,
        choices=sorted(BIT_DEPTH_CODECS),
        help="Force PCM bit depth (default: match source; 32-bit float for lossy)",
    )


def refuse_overwrite_source(source: Path, output: Path, default_subdir: str) -> bool:
    """Print an error and return True when output would overwrite the source file."""
    if output.resolve() == source.resolve():
        print(
            "Refusing to overwrite source file. Choose a separate output path "
            f"(default: {default_subdir}/).",
            file=sys.stderr,
        )
        return True
    return False
