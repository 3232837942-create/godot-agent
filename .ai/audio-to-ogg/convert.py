#!/usr/bin/env python3
"""
Convert a single audio file to OGG Vorbis using FFmpeg.

Run through default python from .dependency/manifest.json.
Never use host python/py.

Usage
-----
    .dependency/python/python .ai/audio-to-ogg/convert.py --audio path/to/audio.wav
    .dependency/python/python .ai/audio-to-ogg/convert.py --audio path/to/audio.wav -q 4
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[1]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from common.audio_utils import audio_output_name, resolve_audio_file  # noqa: E402
from common.cli_tools import resolve_ffmpeg, resolve_ffprobe  # noqa: E402
from common.output_utils import format_default_output_help, resolve_output_path  # noqa: E402

DEFAULT_OUTPUT_SUBDIR = "audio-to-ogg"
DEFAULT_QUALITY = 10
VORBIS_CODEC = "libvorbis"


def probe_audio(ffprobe: Path, file_path: Path) -> dict:
    result = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-select_streams",
            "a:0",
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
        "sample_rate": sample_rate,
        "channels": channels,
    }


def can_stream_copy(file_path: Path, probe: dict, channels: int | None) -> bool:
    if channels is not None:
        return False
    if file_path.suffix.lower() != ".ogg":
        return False
    return probe.get("codec", "") == "vorbis"


def build_ffmpeg_args(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    quality: int,
    channels: int | None,
    stream_copy: bool,
) -> list[str]:
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-nostats",
        "-y",
        "-i",
        str(file_path),
    ]
    if stream_copy:
        cmd.extend(["-c:a", "copy", str(out_path)])
        return cmd

    if channels is not None:
        cmd.extend(["-ac", str(channels)])
    cmd.extend(["-c:a", VORBIS_CODEC, "-q:a", str(quality), str(out_path)])
    return cmd


def convert_file(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    quality: int,
    channels: int | None,
    stream_copy: bool,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_ffmpeg_args(ffmpeg, file_path, out_path, quality, channels, stream_copy)
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"FFmpeg convert failed for: {file_path}"
            + (f"\n{detail}" if detail else "")
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a single audio file to OGG Vorbis."
    )
    parser.add_argument(
        "--audio",
        required=True,
        help="Path to a single audio file",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help=(
            "Output OGG file or directory. "
            f"Default: {format_default_output_help(DEFAULT_OUTPUT_SUBDIR, output_name_label='source.ogg')}"
        ),
    )
    parser.add_argument(
        "-q",
        "--quality",
        type=int,
        choices=range(0, 11),
        default=DEFAULT_QUALITY,
        help=f"Vorbis quality 0-10 (default: {DEFAULT_QUALITY})",
    )
    channel_group = parser.add_mutually_exclusive_group()
    channel_group.add_argument("--mono", action="store_true", help="Force mono output")
    channel_group.add_argument("--stereo", action="store_true", help="Force stereo output")
    return parser.parse_args(argv)


def resolve_channels(args: argparse.Namespace) -> int | None:
    if args.mono:
        return 1
    if args.stereo:
        return 2
    return None


def describe_file_plan(
    probe: dict,
    quality: int,
    forced_channels: int | None,
    stream_copy: bool,
) -> str:
    if stream_copy:
        rate = probe.get("sample_rate")
        ch = probe.get("channels") or "?"
        return f"stream copy ({rate} Hz, {ch} ch)"

    ch = {1: "mono", 2: "stereo"}.get(forced_channels, "preserve")
    return f"source rate, Vorbis q={quality}, {ch}"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ffmpeg = resolve_ffmpeg(Path(__file__))
    ffprobe = resolve_ffprobe(ffmpeg)

    audio_path = resolve_audio_file(args.audio)
    if audio_path is None:
        return 1

    out_path = resolve_output_path(
        args.output,
        audio_path,
        DEFAULT_OUTPUT_SUBDIR,
        audio_output_name(audio_path, suffix=".ogg"),
    )

    if out_path.resolve() == audio_path.resolve():
        print(
            "Refusing to overwrite source file. Choose a separate output path "
            f"(default: {DEFAULT_OUTPUT_SUBDIR}/).",
            file=sys.stderr,
        )
        return 1

    forced_channels = resolve_channels(args)

    print(f"Audio:  {audio_path}")
    print(f"Mode:   Vorbis q={args.quality}, preserve sample rate")
    print(f"Output: {out_path}")
    print()

    probe = probe_audio(ffprobe, audio_path)
    stream_copy = can_stream_copy(audio_path, probe, forced_channels)
    plan = describe_file_plan(probe, args.quality, forced_channels, stream_copy)

    try:
        print(f"[run]  {audio_path.name} -> {out_path.name} ({plan})")
        convert_file(
            ffmpeg,
            audio_path,
            out_path,
            args.quality,
            forced_channels,
            stream_copy,
        )
    except RuntimeError as exc:
        print(f"[fail] {out_path.name}")
        print(exc)
        return 1

    print()
    print(f"Done. wrote {out_path.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
