#!/usr/bin/env python3
"""
Trim leading and trailing silence from a single audio file using FFmpeg silenceremove.

Run through default python from .dependency/manifest.json.
Never use host python/py.

Usage
-----
    .dependency/python/python .ai/audio-trim/trim.py --audio path/to/audio.wav
    .dependency/python/python .ai/audio-trim/trim.py --audio path/to/audio.wav -t -45
    .dependency/python/python .ai/audio-trim/trim.py --audio audio/sfx.wav --output path/to/out.wav
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[1]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from common.audio_utils import audio_output_name, resolve_audio_file  # noqa: E402
from common.cli_tools import resolve_ffmpeg  # noqa: E402
from common.output_utils import format_default_output_help, resolve_output_path  # noqa: E402


DEFAULT_OUTPUT_SUBDIR = "audio-trim"


def build_filter(threshold: float) -> str:
    start = (
        f"silenceremove=start_periods=1:start_duration=0:"
        f"start_threshold={threshold}dB"
    )
    # Trim both ends with start_periods only. Positive stop_periods keeps just
    # one trailing non-silence period and over-trims long clips.
    return f"areverse,{start},areverse,{start}"


def trim_file(
    ffmpeg: Path, file_path: Path, out_path: Path, filter_str: str
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-nostats",
            "-y",
            "-i",
            str(file_path),
            "-af",
            filter_str,
            str(out_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"FFmpeg trim failed for: {file_path}"
            + (f"\n{detail}" if detail else "")
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Trim leading and trailing silence from a single audio file."
    )
    parser.add_argument(
        "--audio",
        required=True,
        help="Path to a single audio file",
    )
    parser.add_argument(
        "-t",
        "--threshold",
        type=float,
        default=-50,
        help="Silence threshold in dB (default: -50)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help=(
            "Output file or directory. "
            f"Default: {format_default_output_help(DEFAULT_OUTPUT_SUBDIR)}"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ffmpeg = resolve_ffmpeg(Path(__file__))

    audio_path = resolve_audio_file(args.audio)
    if audio_path is None:
        return 1

    out_path = resolve_output_path(
        args.output,
        audio_path,
        DEFAULT_OUTPUT_SUBDIR,
        audio_output_name(audio_path),
    )

    filter_str = build_filter(args.threshold)

    print(f"Audio:     {audio_path}")
    print(f"Threshold: {args.threshold} dB")
    print(f"Filter:    {filter_str}")
    print(f"Output:    {out_path}")
    print()

    try:
        print(f"[run]  {audio_path.name}")
        trim_file(ffmpeg, audio_path, out_path, filter_str)
    except RuntimeError as exc:
        print(f"[fail] {audio_path.name}")
        print(exc)
        return 1

    print()
    print(f"Done. wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
