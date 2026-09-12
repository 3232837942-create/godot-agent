#!/usr/bin/env python3
"""
Convert a single audio file to PCM WAV using FFmpeg.

Run through default python from .dependency/manifest.json.
Never use host python/py.

Usage
-----
    .dependency/python/python .ai/audio-to-wav/convert.py --audio path/to/audio.flac
    .dependency/python/python .ai/audio-to-wav/convert.py --audio path/to/audio.mp3 -b 16
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[1]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from common.audio_utils import resolve_audio_file  # noqa: E402
from common.cli_tools import resolve_ffmpeg, resolve_ffprobe  # noqa: E402
from common.output_utils import format_default_output_help, resolve_output_path  # noqa: E402
from common.wav_utils import add_bit_depth_arg, can_pcm_stream_copy, describe_pcm_wav_plan, probe_audio_file, refuse_overwrite_source, resolve_bit_depth, run_pcm_wav_ffmpeg, wav_output_name  # noqa: E402

DEFAULT_OUTPUT_SUBDIR = "audio-to-wav"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a single audio file to PCM WAV."
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
            "Output WAV file or directory. "
            f"Default: {format_default_output_help(DEFAULT_OUTPUT_SUBDIR, output_name_label='source.wav')}"
        ),
    )
    add_bit_depth_arg(parser)
    return parser.parse_args(argv)


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
        wav_output_name(audio_path),
    )

    if refuse_overwrite_source(audio_path, out_path, DEFAULT_OUTPUT_SUBDIR):
        return 1

    forced_depth = args.bit_depth

    print(f"Audio:  {audio_path}")
    print(f"Mode:   preserve source sample rate, channels, and quality")
    print(f"Output: {out_path}")
    print()

    probe = probe_audio_file(ffprobe, audio_path)
    stream_copy = can_pcm_stream_copy(
        probe,
        forced_depth,
        require_wav_container=True,
        source_path=audio_path,
    )
    _, codec = resolve_bit_depth(probe, forced_depth)
    plan = describe_pcm_wav_plan(probe, forced_depth, stream_copy)

    try:
        print(f"[run]  {audio_path.name} -> {out_path.name} ({plan})")
        run_pcm_wav_ffmpeg(
            ffmpeg,
            audio_path,
            out_path,
            codec,
            stream_copy,
            action="convert",
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
