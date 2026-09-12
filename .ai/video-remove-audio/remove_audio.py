#!/usr/bin/env python3
"""
Remove all audio tracks from a single video file using FFmpeg.

Run through default python from .dependency/manifest.json.
Never use host python/py.

Usage
-----
    .dependency/python/python .ai/video-remove-audio/remove_audio.py --video path/to/clip.mp4
    .dependency/python/python .ai/video-remove-audio/remove_audio.py --video path/to/clip.mp4 -o path/to/out.mp4
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

from common.cli_tools import resolve_ffmpeg, resolve_ffprobe  # noqa: E402
from common.output_utils import format_default_output_help, resolve_output_path  # noqa: E402
from common.video_utils import resolve_video_file, video_output_name  # noqa: E402

DEFAULT_OUTPUT_SUBDIR = "video-remove-audio"


def has_audio_streams(ffprobe: Path, file_path: Path) -> bool:
    result = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-select_streams",
            "a",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return False

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False

    return bool(payload.get("streams"))


def build_ffmpeg_args(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
) -> list[str]:
    return [
        str(ffmpeg),
        "-hide_banner",
        "-nostats",
        "-y",
        "-i",
        str(file_path),
        "-map",
        "0:v",
        "-c:v",
        "copy",
        "-an",
        str(out_path),
    ]


def remove_audio_file(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_ffmpeg_args(ffmpeg, file_path, out_path)
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"FFmpeg mute failed for: {file_path}"
            + (f"\n{detail}" if detail else "")
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Remove all audio tracks from a single video file."
    )
    parser.add_argument(
        "--video",
        required=True,
        help="Path to a single video file",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help=(
            "Output video file or directory. "
            f"Default: {format_default_output_help(DEFAULT_OUTPUT_SUBDIR)}"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    script_path = Path(__file__)
    ffmpeg = resolve_ffmpeg(script_path)
    ffprobe = resolve_ffprobe(ffmpeg)

    video_path = resolve_video_file(args.video)
    if video_path is None:
        return 1

    out_path = resolve_output_path(
        args.output,
        video_path,
        DEFAULT_OUTPUT_SUBDIR,
        video_output_name(video_path),
    )

    if out_path.resolve() == video_path.resolve():
        print(
            "Refusing to overwrite source file. Choose a separate output path "
            f"(default: {DEFAULT_OUTPUT_SUBDIR}/).",
            file=sys.stderr,
        )
        return 1

    print(f"Video:  {video_path}")
    print("Mode:   stream copy")
    print(f"Output: {out_path}")
    print()

    if not has_audio_streams(ffprobe, video_path):
        print(f"[skip] {video_path.name} (already silent)")
        return 0

    try:
        print(f"[run]  {video_path.name} -> {out_path.name} (copy video + -an)")
        remove_audio_file(ffmpeg, video_path, out_path)
    except RuntimeError as exc:
        print(f"[fail] {out_path.name}")
        print(exc)
        return 1

    print()
    print(f"Done. wrote {out_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
