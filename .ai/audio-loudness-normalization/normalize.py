#!/usr/bin/env python3
"""
Loudness-normalize a single audio file to a target LUFS using FFmpeg two-pass loudnorm.

Run through default python from .dependency/manifest.json.
Never use host python/py.

Usage
-----
    .dependency/python/python .ai/audio-loudness-normalization/normalize.py --audio path/to/audio.wav
    .dependency/python/python .ai/audio-loudness-normalization/normalize.py --audio path/to/audio.wav -t -16
    .dependency/python/python .ai/audio-loudness-normalization/normalize.py --audio path/to/audio.wav -output path/to/out.wav
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[1]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from common.audio_utils import audio_output_name, resolve_audio_file  # noqa: E402
from common.cli_tools import resolve_ffmpeg, resolve_ffprobe  # noqa: E402
from common.output_utils import format_default_output_help, resolve_output_path  # noqa: E402


DEFAULT_OUTPUT_SUBDIR = "audio-loudness-normalization"
DEFAULT_TARGET_LUFS = -14.0
DEFAULT_TRUE_PEAK = -1.5
DEFAULT_LRA = 11


def probe_sample_rate(ffprobe: Path, file_path: Path) -> int:
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
        raise RuntimeError(
            f"ffprobe failed for: {file_path}\n{result.stderr.strip()}"
        )

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ffprobe JSON parse failed for: {file_path}") from exc

    streams = payload.get("streams") or []
    if not streams:
        raise RuntimeError(f"No audio stream found for: {file_path}")

    sample_rate = streams[0].get("sample_rate")
    try:
        rate = int(sample_rate) if sample_rate else 0
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Invalid sample rate for: {file_path}") from exc
    if rate <= 0:
        raise RuntimeError(f"Missing sample rate for: {file_path}")
    return rate


def build_loudnorm_filter(
    target_lufs: float,
    measured: dict[str, str],
    *,
    true_peak: float = DEFAULT_TRUE_PEAK,
    lra: float = DEFAULT_LRA,
) -> str:
    return (
        f"loudnorm=I={target_lufs}:TP={true_peak}:LRA={lra}"
        f":measured_I={measured['input_i']}"
        f":measured_LRA={measured['input_lra']}"
        f":measured_TP={measured['input_tp']}"
        f":measured_thresh={measured['input_thresh']}"
        f":offset={measured['target_offset']}"
        ":linear=true"
    )


def measure_loudnorm(ffmpeg: Path, file_path: Path, target_lufs: float) -> dict:
    result = subprocess.run(
        [
            str(ffmpeg),
            "-hide_banner",
            "-nostats",
            "-i",
            str(file_path),
            "-af",
            (
                f"loudnorm=I={target_lufs}:TP={DEFAULT_TRUE_PEAK}"
                f":LRA={DEFAULT_LRA}:print_format=json"
            ),
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg analysis failed for: {file_path}\n{result.stderr.strip()}"
        )

    match = re.search(r"\{[\s\S]*\}", result.stderr)
    if not match:
        raise RuntimeError(f"Could not parse loudnorm JSON for: {file_path}")

    return json.loads(match.group(0))


def normalize_file(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    target_lufs: float,
    sample_rate: int,
    measured: dict,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    filter_str = build_loudnorm_filter(target_lufs, measured)
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
            "-ar",
            str(sample_rate),
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
            f"FFmpeg normalize failed for: {file_path}"
            + (f"\n{detail}" if detail else "")
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Loudness-normalize a single audio file to a target LUFS."
    )
    parser.add_argument(
        "--audio",
        required=True,
        help="Path to a single audio file",
    )
    parser.add_argument(
        "-t",
        "--target-lufs",
        type=float,
        default=DEFAULT_TARGET_LUFS,
        help=f"Target integrated loudness in LUFS (default: {DEFAULT_TARGET_LUFS:g})",
    )
    parser.add_argument(
        "-output",
        dest="output",
        default="",
        help=(
            "Output audio file or directory. "
            f"Default: {format_default_output_help(DEFAULT_OUTPUT_SUBDIR)}"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    ffmpeg = resolve_ffmpeg(Path(__file__))
    ffprobe = resolve_ffprobe(ffmpeg)

    audio_path = resolve_audio_file(args.audio)
    if audio_path is None:
        return 1

    out_path = resolve_output_path(
        args.output,
        audio_path,
        DEFAULT_OUTPUT_SUBDIR,
        audio_output_name(audio_path),
    )
    if out_path.resolve() == audio_path.resolve():
        print(
            "Refusing to overwrite source file. Use a separate output path "
            f"(default: {format_default_output_help(DEFAULT_OUTPUT_SUBDIR)}).",
            file=sys.stderr,
        )
        return 1

    print(f"Audio:       {audio_path}")
    print(f"Target LUFS: {args.target_lufs}")
    print(f"True Peak:   {DEFAULT_TRUE_PEAK} dBTP")
    print(f"Sample rate: preserve source")
    print(f"Output:      {out_path}")
    print()

    try:
        print(f"[run]  {audio_path.name}")
        sample_rate = probe_sample_rate(ffprobe, audio_path)
        measured = measure_loudnorm(ffmpeg, audio_path, args.target_lufs)
        normalize_file(
            ffmpeg,
            audio_path,
            out_path,
            args.target_lufs,
            sample_rate,
            measured,
        )
    except RuntimeError as exc:
        print(f"[fail] {audio_path.name}")
        print(exc)
        return 1

    print()
    print(f"Done. wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
