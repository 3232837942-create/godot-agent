#!/usr/bin/env python3
"""
Standardize a single audio file to 44100 or 48000 Hz and export 16-bit PCM WAV.

Run through default python from .dependency/manifest.json.
Never use host python/py.

Usage
-----
    .dependency/python/python .ai/audio-sample-rate-standardize/standardize.py --audio path/to/audio.mp3
    .dependency/python/python .ai/audio-sample-rate-standardize/standardize.py --audio path/to/audio.mp3 --output path/to/out.wav
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

SAMPLE_RATE_44100 = 44100
SAMPLE_RATE_48000 = 48000
OUTPUT_CODEC = "pcm_s16le"
DEFAULT_OUTPUT_SUBDIR = "audio-sample-rate-standardize"


def probe_sample_rate(ffprobe: Path, file_path: Path) -> int | None:
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
        return None

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return None

    streams = payload.get("streams") or []
    if not streams:
        return None

    sample_rate = streams[0].get("sample_rate")
    try:
        return int(sample_rate) if sample_rate else None
    except (TypeError, ValueError):
        return None


def resolve_output_sample_rate(source_rate: int | None) -> int:
    if source_rate is None or source_rate <= SAMPLE_RATE_44100:
        return SAMPLE_RATE_44100
    return SAMPLE_RATE_48000


def describe_output_format(source_rate: int | None, output_rate: int) -> str:
    if source_rate is None:
        return f"{output_rate} Hz, 16-bit PCM WAV"
    if source_rate == output_rate:
        return f"{output_rate} Hz (preserved), 16-bit PCM WAV"
    return f"{output_rate} Hz (from {source_rate} Hz), 16-bit PCM WAV"


def standardize_file(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    sample_rate: int,
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
            "-ar",
            str(sample_rate),
            "-c:a",
            OUTPUT_CODEC,
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
            f"FFmpeg standardize failed for: {file_path}"
            + (f"\n{detail}" if detail else "")
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Standardize a single audio file to 44100 or 48000 Hz 16-bit PCM WAV."
    )
    parser.add_argument(
        "--audio",
        required=True,
        help="Path to a single audio file",
    )
    parser.add_argument(
        "--output",
        default="",
        help=(
            "Output WAV file or directory. "
            f"Default: {format_default_output_help(DEFAULT_OUTPUT_SUBDIR, output_name_label='source-name.wav')}"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script_path = Path(__file__)
    ffmpeg = resolve_ffmpeg(script_path)
    ffprobe = resolve_ffprobe(ffmpeg)

    audio_path = resolve_audio_file(args.audio)
    if audio_path is None:
        return 1

    out_path = resolve_output_path(
        args.output,
        audio_path,
        DEFAULT_OUTPUT_SUBDIR,
        audio_output_name(audio_path, suffix=".wav"),
    )
    if out_path.resolve() == audio_path.resolve():
        print(
            "Refusing to overwrite source file. Use a separate output path "
            f"(default: {format_default_output_help(DEFAULT_OUTPUT_SUBDIR, output_name_label='source-name.wav')}).",
            file=sys.stderr,
        )
        return 1

    source_rate = probe_sample_rate(ffprobe, audio_path)
    output_rate = resolve_output_sample_rate(source_rate)
    format_plan = describe_output_format(source_rate, output_rate)

    print(f"Audio:  {audio_path}")
    print(f"Format: {format_plan}")
    print(f"Output: {out_path}")
    print()

    try:
        print(f"[run]  {audio_path.name} -> {out_path.name} ({format_plan})")
        standardize_file(ffmpeg, audio_path, out_path, output_rate)
    except RuntimeError as exc:
        print(f"[fail] {out_path.name}")
        print(exc)
        return 1

    print()
    print(f"Done. wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
