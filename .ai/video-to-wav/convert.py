#!/usr/bin/env python3
"""
Extract audio from a single video file to PCM WAV using FFmpeg.

Run through default python from .dependency/manifest.json.
Never use host python/py.

Usage
-----
    .dependency/python/python .ai/video-to-wav/convert.py --video path/to/video.mp4
    .dependency/python/python .ai/video-to-wav/convert.py --video clip.mkv --track 1
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[1]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from common.cli_tools import resolve_ffmpeg, resolve_ffprobe  # noqa: E402
from common.output_utils import format_default_output_help, resolve_output_path  # noqa: E402
from common.video_utils import resolve_video_file  # noqa: E402
from common.wav_utils import add_bit_depth_arg, can_pcm_stream_copy, describe_pcm_wav_plan, probe_video_audio_track, refuse_overwrite_source, resolve_bit_depth, run_pcm_wav_ffmpeg, wav_output_name  # noqa: E402

DEFAULT_OUTPUT_SUBDIR = "video-to-wav"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Extract audio from a single video file to PCM WAV."
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
            "Output WAV file or directory. "
            f"Default: {format_default_output_help(DEFAULT_OUTPUT_SUBDIR, output_name_label='source.wav')}"
        ),
    )
    parser.add_argument(
        "--track",
        type=int,
        default=0,
        metavar="N",
        help="Audio stream index to extract (0-based, default: 0)",
    )
    add_bit_depth_arg(parser)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.track < 0:
        print("--track must be >= 0", file=sys.stderr)
        return 1

    ffmpeg = resolve_ffmpeg(Path(__file__))
    ffprobe = resolve_ffprobe(ffmpeg)

    video_path = resolve_video_file(args.video)
    if video_path is None:
        return 1

    out_path = resolve_output_path(
        args.output,
        video_path,
        DEFAULT_OUTPUT_SUBDIR,
        wav_output_name(video_path),
    )

    if refuse_overwrite_source(video_path, out_path, DEFAULT_OUTPUT_SUBDIR):
        return 1

    forced_depth = args.bit_depth

    print(f"Video:  {video_path}")
    print(f"Track:  {args.track}")
    print(f"Mode:   preserve source sample rate, channels, and quality")
    print(f"Output: {out_path}")
    print()

    probe = probe_video_audio_track(ffprobe, video_path, args.track)
    if not probe:
        print(f"[fail] {video_path.name}")
        print(
            f"No audio track at index {args.track} in: {video_path}",
            file=sys.stderr,
        )
        return 1

    stream_copy = can_pcm_stream_copy(probe, forced_depth)
    _, codec = resolve_bit_depth(probe, forced_depth)
    plan = describe_pcm_wav_plan(
        probe,
        forced_depth,
        stream_copy,
        track=args.track,
    )

    try:
        print(f"[run]  {video_path.name} -> {out_path.name} ({plan})")
        run_pcm_wav_ffmpeg(
            ffmpeg,
            video_path,
            out_path,
            codec,
            stream_copy,
            track=args.track,
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
