#!/usr/bin/env python3
"""
Convert a single video file to OGV (Theora + Vorbis) using FFmpeg.

Run through default python from .dependency/manifest.json.
Never use host python/py.

Usage
-----
    .dependency/python/python .ai/video-to-ogv/convert.py --video path/to/video.mp4
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

DEFAULT_OUTPUT_SUBDIR = "video-to-ogv"
DEFAULT_LOSSLESS_SUBDIR = "lossless"
MAX_QUALITY = 10
GAME_STANDARD_SAMPLE_RATE = 48000
THEORA_CODEC = "libtheora"
VORBIS_CODEC = "libvorbis"
LOSSLESS_VIDEO_CODEC = "ffv1"
LOSSLESS_AUDIO_CODEC = "flac"
LOSSLESS_CONTAINER = ".mkv"

LOSSLESS_VIDEO_CODECS = {
    "ffv1",
    "huffyuv",
    "ffvhuff",
    "utvideo",
    "rawvideo",
    "vble",
    "magicyuv",
}
LOSSLESS_AUDIO_CODECS = {
    "flac",
    "pcm_s16le",
    "pcm_s24le",
    "pcm_s32le",
    "pcm_f32le",
    "pcm_s16be",
    "pcm_s24be",
    "pcm_s32be",
    "pcm_f32be",
}


def lossless_output_name(file_path: Path) -> str:
    return video_output_name(file_path, suffix=LOSSLESS_CONTAINER)


def probe_streams(ffprobe: Path, file_path: Path) -> dict:
    result = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return {"video": {}, "audio": {}}

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"video": {}, "audio": {}}

    video: dict = {}
    audio: dict = {}
    for stream in payload.get("streams") or []:
        codec_type = stream.get("codec_type")
        if codec_type == "video" and not video:
            video = {
                "codec": stream.get("codec_name", ""),
                "width": stream.get("width"),
                "height": stream.get("height"),
            }
        elif codec_type == "audio" and not audio:
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
            audio = {
                "codec": stream.get("codec_name", ""),
                "sample_rate": sample_rate,
                "channels": channels,
            }

    return {"video": video, "audio": audio}


def is_lossless_source(probe: dict) -> bool:
    video = probe.get("video") or {}
    if not video:
        return False
    if video.get("codec") not in LOSSLESS_VIDEO_CODECS:
        return False
    audio = probe.get("audio") or {}
    if not audio:
        return True
    return audio.get("codec") in LOSSLESS_AUDIO_CODECS


def export_lossless_intermediate(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    probe: dict,
    sample_rate: int | None,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-nostats",
        "-y",
        "-i",
        str(file_path),
        "-map",
        "0:v:0",
        "-c:v",
        LOSSLESS_VIDEO_CODEC,
        "-level",
        "3",
        "-pix_fmt",
        "yuv420p",
    ]

    audio = probe.get("audio") or {}
    if audio:
        cmd.extend(["-map", "0:a:0"])
        if sample_rate is not None:
            cmd.extend(["-ar", str(sample_rate)])
        cmd.extend(["-c:a", LOSSLESS_AUDIO_CODEC, "-compression_level", "0"])
    else:
        cmd.append("-an")

    cmd.append(str(out_path))
    run_ffmpeg(cmd, file_path, "lossless export")


def resolve_encode_source(
    ffmpeg: Path,
    ffprobe: Path,
    file_path: Path,
    lossless_dir: Path,
    source_probe: dict,
    sample_rate: int | None,
) -> tuple[Path, dict, str]:
    if is_lossless_source(source_probe):
        return file_path, source_probe, ""

    intermediate_name = lossless_output_name(file_path)
    intermediate_path = lossless_dir / intermediate_name
    note = f"via {intermediate_name}"

    if intermediate_path.is_file():
        intermediate_probe = probe_streams(ffprobe, intermediate_path)
        if intermediate_probe.get("video"):
            print(f"[reuse] {intermediate_name}")
            return intermediate_path, intermediate_probe, note

    print(f"[lossless] {file_path.name} -> {intermediate_name}")
    export_lossless_intermediate(
        ffmpeg,
        file_path,
        intermediate_path,
        source_probe,
        sample_rate,
    )
    intermediate_probe = probe_streams(ffprobe, intermediate_path)
    return intermediate_path, intermediate_probe, note


def can_stream_copy(
    file_path: Path,
    probe: dict,
    sample_rate: int | None,
) -> bool:
    if sample_rate is not None:
        return False
    if file_path.suffix.lower() != ".ogv":
        return False
    video = probe.get("video") or {}
    audio = probe.get("audio") or {}
    if video.get("codec") != "theora":
        return False
    if not audio:
        return True
    return audio.get("codec") == "vorbis"


def build_ffmpeg_args(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    probe: dict,
    sample_rate: int | None,
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
        cmd.extend(["-c", "copy", str(out_path)])
        return cmd

    cmd.extend(["-c:v", THEORA_CODEC, "-q:v", str(MAX_QUALITY)])

    audio = probe.get("audio") or {}
    if audio:
        if sample_rate is not None:
            cmd.extend(["-ar", str(sample_rate)])
        cmd.extend(["-c:a", VORBIS_CODEC, "-q:a", str(MAX_QUALITY)])
    else:
        cmd.append("-an")

    cmd.append(str(out_path))
    return cmd


def run_ffmpeg(cmd: list[str], file_path: Path, phase: str) -> None:
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"FFmpeg {phase} failed for: {file_path}"
            + (f"\n{detail}" if detail else "")
        )


def convert_file(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    probe: dict,
    sample_rate: int | None,
    stream_copy: bool,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_ffmpeg_args(
        ffmpeg,
        file_path,
        out_path,
        probe,
        sample_rate,
        stream_copy,
    )
    run_ffmpeg(cmd, file_path, "convert")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a single video file to OGV (Theora + Vorbis)."
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
            "Output OGV file or directory. "
            f"Default: {format_default_output_help(DEFAULT_OUTPUT_SUBDIR, output_name_label='source.ogv')}"
        ),
    )
    parser.add_argument(
        "--standardize",
        action="store_true",
        help="Resample audio to 48 kHz Vorbis (project batch preset)",
    )
    parser.add_argument(
        "--lossless-dir",
        default="",
        help=(
            "Lossless intermediate directory. "
            f"Default: {format_default_output_help(DEFAULT_OUTPUT_SUBDIR, output_name_label='lossless/source.mkv')}"
        ),
    )
    parser.add_argument(
        "--clean-lossless",
        action="store_true",
        help="Delete lossless intermediate MKV after successful OGV export",
    )
    return parser.parse_args(argv)


def resolve_forced_sample_rate(args: argparse.Namespace) -> int | None:
    if args.standardize:
        return GAME_STANDARD_SAMPLE_RATE
    return None


def describe_file_plan(
    probe: dict,
    forced_rate: int | None,
    stream_copy: bool,
    intermediate_note: str,
) -> str:
    video = probe.get("video") or {}
    audio = probe.get("audio") or {}

    if stream_copy:
        w, h = video.get("width"), video.get("height")
        size = f"{w}x{h}" if w and h else "source"
        if audio:
            rate = audio.get("sample_rate")
            ch = audio.get("channels") or "?"
            return f"stream copy ({size}, {rate} Hz, {ch} ch)"
        return f"stream copy ({size}, no audio)"

    w, h = video.get("width"), video.get("height")
    size = f"{w}x{h}" if w and h else "source"
    via = f", {intermediate_note}" if intermediate_note else ""
    rate = f"{forced_rate} Hz" if forced_rate else "source rate"
    ch = audio.get("channels") or "?" if audio else None

    if not audio:
        if is_lossless_source(probe):
            return f"{size}, Theora q={MAX_QUALITY}, Vorbis q={MAX_QUALITY}, no audio"
        return f"{size}, FFV1+FLAC → Theora q={MAX_QUALITY}{via}, no audio"
    if is_lossless_source(probe):
        return (
            f"{size}, Theora q={MAX_QUALITY}, Vorbis q={MAX_QUALITY}, "
            f"{rate}, {ch} ch"
        )
    return (
        f"{size}, FFV1+FLAC → Theora q={MAX_QUALITY}, "
        f"Vorbis q={MAX_QUALITY}, {rate}, {ch} ch{via}"
    )


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
        video_output_name(video_path, suffix=".ogv"),
    )
    lossless_dir = (
        Path(args.lossless_dir).expanduser().resolve()
        if args.lossless_dir
        else video_path.parent / DEFAULT_OUTPUT_SUBDIR / DEFAULT_LOSSLESS_SUBDIR
    )
    intermediate_path = lossless_dir / lossless_output_name(video_path)

    if out_path.resolve() == video_path.resolve():
        print(
            "Refusing to overwrite source file. Choose a separate output path "
            f"(default: {DEFAULT_OUTPUT_SUBDIR}/).",
            file=sys.stderr,
        )
        return 1
    if intermediate_path.resolve() == video_path.resolve():
        print(
            "Refusing to overwrite source file. Choose a separate lossless directory "
            f"(default: {DEFAULT_OUTPUT_SUBDIR}/{DEFAULT_LOSSLESS_SUBDIR}/).",
            file=sys.stderr,
        )
        return 1

    forced_rate = resolve_forced_sample_rate(args)

    print(f"Video:  {video_path}")
    print(
        "Mode:   lossless intermediate (FFV1+FLAC MKV in video-to-ogv/lossless/) → "
        f"Theora q={MAX_QUALITY}, Vorbis q={MAX_QUALITY} OGV"
    )
    print(f"Output: {out_path}")
    print(f"Lossless: {intermediate_path}")
    print()

    probe = probe_streams(ffprobe, video_path)
    if not probe.get("video"):
        print(f"[fail] {video_path.name} (no video stream)")
        return 1

    stream_copy = can_stream_copy(video_path, probe, forced_rate)

    intermediate_note = ""
    encode_path = video_path
    encode_probe = probe

    if not stream_copy:
        encode_path, encode_probe, intermediate_note = resolve_encode_source(
            ffmpeg,
            ffprobe,
            video_path,
            lossless_dir,
            probe,
            forced_rate,
        )

    plan = describe_file_plan(probe, forced_rate, stream_copy, intermediate_note)

    try:
        print(f"[run]  {video_path.name} -> {out_path.name} ({plan})")
        convert_file(
            ffmpeg,
            encode_path if not stream_copy else video_path,
            out_path,
            encode_probe if not stream_copy else probe,
            forced_rate,
            stream_copy,
        )
        if args.clean_lossless and intermediate_path.is_file():
            intermediate_path.unlink()
            print(f"[clean] removed {intermediate_path.name}")
    except RuntimeError as exc:
        print(f"[fail] {out_path.name}")
        print(exc)
        return 1

    print()
    print(f"Done. wrote {out_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
