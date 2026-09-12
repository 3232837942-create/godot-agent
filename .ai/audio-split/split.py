#!/usr/bin/env python3
"""
Split a single audio file into part 1 (before split) and part 2 (after split) using FFmpeg.

Run through default python from .dependency/manifest.json.
Never use host python/py.

Usage
-----
    .dependency/python/python .ai/audio-split/split.py --audio path/to/audio.wav
    .dependency/python/python .ai/audio-split/split.py --audio path/to/audio.wav -s 1.25
    .dependency/python/python .ai/audio-split/split.py --audio path/to/audio.wav -p 25
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[1]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from common.audio_utils import get_duration, resolve_audio_file  # noqa: E402
from common.cli_tools import resolve_ffmpeg, resolve_ffprobe  # noqa: E402
from common.output_utils import format_default_output_dir_help, resolve_output_dir  # noqa: E402

DEFAULT_OUTPUT_SUBDIR = "audio-split"


def resolve_split_seconds(
    duration: float, split_at: float | None, percent: float | None
) -> float:
    if split_at is not None:
        point = split_at
    elif percent is not None:
        point = duration * (percent / 100.0)
    else:
        point = duration * 0.5

    if point <= 0:
        raise ValueError("Split point must be after the start ( > 0 seconds ).")
    if point >= duration:
        raise ValueError(
            f"Split point ({point:.3f}s) must be before file end ({duration:.3f}s)."
        )
    return point


def output_paths(out_dir: Path, file_path: Path) -> tuple[Path, Path]:
    stem = file_path.stem
    suffix = file_path.suffix
    return out_dir / f"{stem}_part1{suffix}", out_dir / f"{stem}_part2{suffix}"


def split_file(
    ffmpeg: Path, file_path: Path, part1: Path, part2: Path, split_at: float
) -> None:
    part1.parent.mkdir(parents=True, exist_ok=True)
    part2.parent.mkdir(parents=True, exist_ok=True)

    result1 = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-nostats",
            "-y",
            "-i",
            str(file_path),
            "-t",
            f"{split_at:.6f}",
            str(part1),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result1.returncode != 0:
        detail = result1.stderr.strip() or result1.stdout.strip()
        raise RuntimeError(
            f"FFmpeg part 1 failed for: {file_path}"
            + (f"\n{detail}" if detail else "")
        )

    result2 = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-nostats",
            "-y",
            "-ss",
            f"{split_at:.6f}",
            "-i",
            str(file_path),
            str(part2),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result2.returncode != 0:
        detail = result2.stderr.strip() or result2.stdout.strip()
        raise RuntimeError(
            f"FFmpeg part 2 failed for: {file_path}"
            + (f"\n{detail}" if detail else "")
        )


def parse_args() -> argparse.Namespace:
    default_out = format_default_output_dir_help(
        DEFAULT_OUTPUT_SUBDIR, input_root_label="audio-dir"
    )
    parser = argparse.ArgumentParser(
        description="Split a single audio file into part 1 (before split) and part 2 (after split)."
    )
    parser.add_argument(
        "--audio",
        required=True,
        help="Path to a single audio file",
    )
    split = parser.add_mutually_exclusive_group()
    split.add_argument(
        "-s",
        "--split-at",
        type=float,
        help="Split time in seconds (part 1 ends here; part 2 starts here)",
    )
    split.add_argument(
        "-p",
        "--percent",
        type=float,
        help="Split position as percent of duration (default: 50)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help=f"Output directory (default: {default_out})",
    )
    return parser.parse_args()


def format_split_label(
    split_at: float | None, percent: float | None, resolved: float
) -> str:
    if split_at is not None:
        return f"{resolved:.3f}s (from -s {split_at})"
    if percent is not None:
        return f"{resolved:.3f}s ({percent}% of duration)"
    return f"{resolved:.3f}s (50% default)"


def main() -> int:
    args = parse_args()
    ffmpeg = resolve_ffmpeg(Path(__file__))
    ffprobe = resolve_ffprobe(ffmpeg)

    audio_path = resolve_audio_file(args.audio)
    if audio_path is None:
        return 1

    output_dir = resolve_output_dir(
        args.output, audio_path.parent, output_subdir=DEFAULT_OUTPUT_SUBDIR
    )
    part1, part2 = output_paths(output_dir, audio_path)

    try:
        duration = get_duration(ffprobe, audio_path)
        split_seconds = resolve_split_seconds(duration, args.split_at, args.percent)
        label = format_split_label(args.split_at, args.percent, split_seconds)
    except (RuntimeError, ValueError) as exc:
        print(f"[fail] {audio_path.name}")
        print(exc)
        return 1

    print(f"Audio:  {audio_path}")
    print(f"Split:  {label}")
    print(f"Output: {output_dir}")
    print(f"        -> {part1.name}")
    print(f"        -> {part2.name}")
    print()

    try:
        print(f"[run]  {audio_path.name}")
        split_file(ffmpeg, audio_path, part1, part2, split_seconds)
    except RuntimeError as exc:
        print(f"[fail] {audio_path.name}")
        print(exc)
        return 1

    print()
    print(f"Done. wrote {part1.name} and {part2.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
