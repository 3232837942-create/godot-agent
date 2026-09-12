#!/usr/bin/env python3
"""
Normalize a single video to unified 3840x2160 60FPS H.265 Main10 BT.709 SDR MP4.

Run through default python from .dependency/manifest.json.
Never use host python/py.

Usage
-----
    .dependency/python/python .ai/video-4k-normalization/normalize.py --video path/to/clip.mp4
    .dependency/python/python .ai/video-4k-normalization/normalize.py --video path/to/clip.mp4 -o path/to/out.mp4
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

DEFAULT_OUTPUT_SUBDIR = "video-4k-normalization"

TARGET_WIDTH = 3840
TARGET_HEIGHT = 2160
TARGET_FPS = 60
VIDEO_BITRATE = "40M"
AUDIO_BITRATE = "320k"

HDR_TRANSFERS = {
    "smpte2084",
    "arib-std-b67",
    "smpte428",
    "smpte2085",
}
HDR_PRIMARIES = {"bt2020"}
HDR_SPACES = {"bt2020nc", "bt2020c"}


def probe_video(ffprobe: Path, file_path: Path) -> dict:
    result = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-show_format",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"ffprobe failed for: {file_path}" + (f"\n{detail}" if detail else "")
        )
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ffprobe returned invalid JSON for: {file_path}") from exc


def parse_frame_rate(rate: str | None) -> float | None:
    if not rate or rate in {"0/0", "N/A"}:
        return None
    if "/" in rate:
        num_s, den_s = rate.split("/", 1)
        try:
            num = float(num_s)
            den = float(den_s)
        except ValueError:
            return None
        if den == 0:
            return None
        return num / den
    try:
        return float(rate)
    except ValueError:
        return None


def stream_info(payload: dict) -> tuple[dict, bool]:
    streams = payload.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video:
        raise RuntimeError("No video stream found")

    width = int(video.get("width") or 0)
    height = int(video.get("height") or 0)
    if width <= 0 or height <= 0:
        raise RuntimeError(f"Invalid video dimensions: {width}x{height}")

    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    return video, has_audio


def is_hdr(video: dict) -> bool:
    transfer = str(video.get("color_transfer") or "").lower()
    primaries = str(video.get("color_primaries") or "").lower()
    space = str(video.get("color_space") or "").lower()

    if transfer in HDR_TRANSFERS:
        return True
    if primaries in HDR_PRIMARIES:
        return True
    if space in HDR_SPACES:
        return True

    for side in video.get("side_data_list") or []:
        kind = str(side.get("side_data_type") or "").lower()
        if "mastering display" in kind or "content light" in kind:
            return True
    return False


def run_checked(cmd: list[str], label: str) -> None:
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"{label} failed" + (f"\n{detail}" if detail else ""))


def build_vf(hdr: bool) -> str:
    scale_fps = f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:flags=lanczos,fps={TARGET_FPS}"
    if hdr:
        return (
            "zscale=t=linear:npl=100,format=gbrpf32le,zscale=p=bt709,"
            "tonemap=hable:desat=0,"
            "zscale=t=bt709:m=bt709:r=tv,format=yuv420p10le,"
            f"{scale_fps}"
        )
    return f"{scale_fps},format=yuv420p10le"


def build_ffmpeg_args(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    has_audio: bool,
    hdr: bool,
) -> list[str]:
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-nostats",
        "-y",
        "-i",
        str(file_path),
        "-vf",
        build_vf(hdr),
        "-c:v",
        "libx265",
        "-profile:v",
        "main10",
        "-pix_fmt",
        "yuv420p10le",
        "-b:v",
        VIDEO_BITRATE,
        "-maxrate",
        VIDEO_BITRATE,
        "-bufsize",
        "80M",
        "-tag:v",
        "hvc1",
        "-x265-params",
        "profile=main10:colorprim=bt709:transfer=bt709:colormatrix=bt709",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "bt709",
        "-colorspace",
        "bt709",
        "-color_range",
        "tv",
    ]
    if has_audio:
        cmd.extend(["-c:a", "aac", "-b:a", AUDIO_BITRATE])
    else:
        cmd.append("-an")
    cmd.extend(["-movflags", "+faststart", str(out_path)])
    return cmd


def describe_plan(video: dict, hdr: bool) -> str:
    width = int(video.get("width") or 0)
    height = int(video.get("height") or 0)
    fps = parse_frame_rate(video.get("avg_frame_rate"))
    if fps is None or fps <= 0:
        fps = parse_frame_rate(video.get("r_frame_rate"))
    fps_label = f"{fps:.3g}" if fps else "?"
    path_label = "HDR->SDR tonemap" if hdr else "SDR"
    return (
        f"{path_label} ({width}x{height} @{fps_label}fps -> "
        f"{TARGET_WIDTH}x{TARGET_HEIGHT} @{TARGET_FPS}fps Main10 BT.709)"
    )


def normalize_file(
    ffmpeg: Path,
    ffprobe: Path,
    file_path: Path,
    out_path: Path,
) -> str:
    payload = probe_video(ffprobe, file_path)
    video, has_audio = stream_info(payload)
    hdr = is_hdr(video)
    plan = describe_plan(video, hdr)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    run_checked(
        build_ffmpeg_args(ffmpeg, file_path, out_path, has_audio, hdr),
        "FFmpeg normalize encode",
    )
    return plan


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Normalize a single video to unified 3840x2160 60FPS H.265 Main10 40Mbps + "
            "AAC 320kbps BT.709 SDR MP4 (FFmpeg re-encode; HDR tone-mapped)."
        )
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
            "Output MP4 file or directory. "
            f"Default: {format_default_output_help(DEFAULT_OUTPUT_SUBDIR, output_name_label='source.mp4')}"
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
        video_output_name(video_path, suffix=".mp4"),
    )

    if out_path.resolve() == video_path.resolve():
        print(
            "Refusing to overwrite source file. Choose a separate output path "
            f"(default: {DEFAULT_OUTPUT_SUBDIR}/).",
            file=sys.stderr,
        )
        return 1

    print(f"Video:  {video_path}")
    print(
        f"Target: {TARGET_WIDTH}x{TARGET_HEIGHT} @{TARGET_FPS}fps "
        f"H.265 Main10 {VIDEO_BITRATE} + AAC {AUDIO_BITRATE} BT.709 SDR"
    )
    print(f"Output: {out_path}")
    print()

    try:
        print(f"[run]  {video_path.name} -> {out_path.name}")
        plan = normalize_file(ffmpeg, ffprobe, video_path, out_path)
        print(f"       {plan}")
    except RuntimeError as exc:
        print(f"[fail] {out_path.name}")
        print(exc)
        return 1

    print()
    print(f"Done. wrote {out_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
