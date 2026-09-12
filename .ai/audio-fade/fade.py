#!/usr/bin/env python3
"""
Apply fade-in and/or fade-out to a single audio file using FFmpeg afade.

Run through default python from .dependency/manifest.json.
Never use host python/py.

Usage
-----
    .dependency/python/python .ai/audio-fade/fade.py --audio path/to/audio.wav
    .dependency/python/python .ai/audio-fade/fade.py --audio path/to/audio.wav --no-fade-out
    .dependency/python/python .ai/audio-fade/fade.py --audio audio/sfx.wav -fi 0.05 -fo 0.15
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[1]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from common.audio_utils import audio_output_name, get_duration, resolve_audio_file  # noqa: E402
from common.cli_tools import resolve_ffmpeg, resolve_ffprobe  # noqa: E402
from common.output_utils import format_default_output_help, resolve_output_path  # noqa: E402


DEFAULT_OUTPUT_SUBDIR = "audio-fade"
DEFAULT_CURVE = "tri"


def validate_fades(
    duration: float,
    fade_in: float,
    fade_out: float,
    fade_in_enabled: bool,
    fade_out_enabled: bool,
) -> None:
    total = 0.0
    if fade_in_enabled:
        if fade_in <= 0:
            raise ValueError("Fade-in duration must be greater than 0.")
        total += fade_in
    if fade_out_enabled:
        if fade_out <= 0:
            raise ValueError("Fade-out duration must be greater than 0.")
        total += fade_out
    if total >= duration:
        raise ValueError(
            f"Combined fade duration ({total:.3f}s) must be less than file duration "
            f"({duration:.3f}s)."
        )


def build_filter(
    duration: float,
    fade_in: float,
    fade_out: float,
    curve: str,
    fade_in_enabled: bool,
    fade_out_enabled: bool,
) -> str:
    parts: list[str] = []
    if fade_in_enabled:
        parts.append(f"afade=t=in:st=0:d={fade_in:.6f}:curve={curve}")
    if fade_out_enabled:
        start = max(0.0, duration - fade_out)
        parts.append(f"afade=t=out:st={start:.6f}:d={fade_out:.6f}:curve={curve}")
    if not parts:
        raise ValueError("At least one of fade-in or fade-out must be enabled.")
    return ",".join(parts)


def fade_file(
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
            f"FFmpeg fade failed for: {file_path}"
            + (f"\n{detail}" if detail else "")
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply fade-in and/or fade-out to a single audio file."
    )
    parser.add_argument(
        "--audio",
        required=True,
        help="Path to a single audio file",
    )
    parser.add_argument(
        "-fi",
        "--fade-in",
        type=float,
        default=1.0,
        help="Fade-in duration in seconds (default: 1.0)",
    )
    parser.add_argument(
        "-fo",
        "--fade-out",
        type=float,
        default=1.0,
        help="Fade-out duration in seconds (default: 1.0)",
    )
    parser.add_argument(
        "--no-fade-in", action="store_true", help="Do not apply fade-in"
    )
    parser.add_argument(
        "--no-fade-out", action="store_true", help="Do not apply fade-out"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help=(
            "Output WAV file or directory. "
            f"Default: {format_default_output_help(DEFAULT_OUTPUT_SUBDIR)}"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    ffmpeg = resolve_ffmpeg(Path(__file__))
    ffprobe = resolve_ffprobe(ffmpeg)

    fade_in_enabled = not args.no_fade_in
    fade_out_enabled = not args.no_fade_out
    if not fade_in_enabled and not fade_out_enabled:
        print(
            "At least one of fade-in or fade-out must remain enabled.",
            file=sys.stderr,
        )
        return 1

    audio_path = resolve_audio_file(args.audio)
    if audio_path is None:
        return 1

    out_path = resolve_output_path(
        args.output,
        audio_path,
        DEFAULT_OUTPUT_SUBDIR,
        audio_output_name(audio_path),
    )

    fade_sides = []
    if fade_in_enabled:
        fade_sides.append(f"in {args.fade_in}s")
    if fade_out_enabled:
        fade_sides.append(f"out {args.fade_out}s")

    print(f"Audio:  {audio_path}")
    print(f"Fade:   {', '.join(fade_sides)}")
    print(f"Output: {out_path}")
    print()

    try:
        duration = get_duration(ffprobe, audio_path)
        validate_fades(
            duration,
            args.fade_in,
            args.fade_out,
            fade_in_enabled,
            fade_out_enabled,
        )
        filter_str = build_filter(
            duration,
            args.fade_in,
            args.fade_out,
            DEFAULT_CURVE,
            fade_in_enabled,
            fade_out_enabled,
        )
    except (RuntimeError, ValueError) as exc:
        print(f"[fail] {audio_path.name}")
        print(exc)
        return 1

    try:
        print(f"[run]  {audio_path.name} ({duration:.3f}s)")
        fade_file(ffmpeg, audio_path, out_path, filter_str)
    except RuntimeError as exc:
        print(f"[fail] {audio_path.name}")
        print(exc)
        return 1

    print()
    print(f"Done. wrote {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
