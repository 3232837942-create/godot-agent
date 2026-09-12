#!/usr/bin/env python3
"""
Interpolate a single below-60fps video to 60fps with Video2X RIFE at source resolution.

Run through default python from .dependency/manifest.json.
Never use host python/py.

Usage
-----
    .dependency/python/python .ai/video-to-60fps/convert.py --video path/to/clip.mp4
    .dependency/python/python .ai/video-to-60fps/convert.py --video path/to/clip.mp4 --gpu 0
    .dependency/python/python .ai/video-to-60fps/convert.py --video path/to/clip.mp4 --uhd --rife-model rife-v4.6
    .dependency/python/python .ai/video-to-60fps/convert.py --video path/to/clip.mp4 -o path/to/out.mp4
"""

from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[1]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from common.cli_tools import resolve_ffmpeg, resolve_ffprobe  # noqa: E402
from common.dependency_utils import find_repo_root, resolve_tool_bin  # noqa: E402
from common.output_utils import format_default_output_help, resolve_output_path  # noqa: E402
from common.video_utils import resolve_video_file, video_output_name  # noqa: E402

DEFAULT_OUTPUT_SUBDIR = "video-to-60fps"

TARGET_FPS = 60.0
FPS_TOLERANCE = 0.5
DEFAULT_RIFE_MODEL = "rife-v4.6"
AUDIO_BITRATE = "320k"
UHD_MIN_WIDTH = 1920


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


def stream_info(payload: dict) -> tuple[int, int, float | None, bool]:
    streams = payload.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video:
        raise RuntimeError("No video stream found")

    width = int(video.get("width") or 0)
    height = int(video.get("height") or 0)
    if width <= 0 or height <= 0:
        raise RuntimeError(f"Invalid video dimensions: {width}x{height}")

    fps = parse_frame_rate(video.get("avg_frame_rate"))
    if fps is None or fps <= 0:
        fps = parse_frame_rate(video.get("r_frame_rate"))

    has_audio = any(s.get("codec_type") == "audio" for s in streams)
    return width, height, fps, has_audio


def is_already_60(fps: float) -> bool:
    return abs(fps - TARGET_FPS) <= FPS_TOLERANCE


def rife_multiplier(fps: float) -> int:
    rounded = max(2, round(TARGET_FPS / fps))
    if abs(fps * rounded - TARGET_FPS) <= FPS_TOLERANCE:
        return rounded
    return max(2, math.ceil(TARGET_FPS / fps - 1e-9))


def run_checked(cmd: list[str], label: str) -> None:
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(f"{label} failed" + (f"\n{detail}" if detail else ""))


def run_video2x(cmd: list[str], out_path: Path) -> None:
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    detail = (result.stderr or "") + "\n" + (result.stdout or "")
    ok_marker = "Video processed successfully" in detail
    usable = out_path.is_file() and out_path.stat().st_size > 0

    if result.returncode == 0 and usable:
        return
    if usable and (ok_marker or result.returncode == -1073741819):
        print(
            f"[warn] Video2X exited {result.returncode} after writing output; continuing"
        )
        return

    detail = detail.strip()
    raise RuntimeError(
        "Video2X interpolate failed" + (f"\n{detail}" if detail else "")
    )


def build_video2x_rife_args(
    video2x: Path,
    file_path: Path,
    out_path: Path,
    mul: int,
    model: str,
    uhd: bool,
    gpu: int | None,
) -> list[str]:
    cmd = [
        str(video2x),
        "-i",
        str(file_path),
        "-o",
        str(out_path),
        "-p",
        "rife",
        "-m",
        str(mul),
        "--rife-model",
        model,
        "-c",
        "libx265",
        "--pix-fmt",
        "yuv420p10le",
        "-e",
        "preset=medium",
        "-e",
        "crf=12",
    ]
    if uhd:
        cmd.append("--rife-uhd")
    if gpu is not None:
        cmd.extend(["-d", str(gpu)])
    return cmd


def build_ffmpeg_fps_args(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    has_audio: bool,
    copy_video: bool,
) -> list[str]:
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-nostats",
        "-y",
        "-i",
        str(file_path),
    ]
    if copy_video:
        cmd.extend(["-c:v", "copy", "-tag:v", "hvc1"])
    else:
        cmd.extend(
            [
                "-vf",
                f"fps={int(TARGET_FPS)},format=yuv420p10le",
                "-c:v",
                "libx265",
                "-profile:v",
                "main10",
                "-pix_fmt",
                "yuv420p10le",
                "-crf",
                "12",
                "-preset",
                "medium",
                "-tag:v",
                "hvc1",
                "-x265-params",
                "profile=main10",
            ]
        )
    if has_audio:
        cmd.extend(["-c:a", "aac", "-b:a", AUDIO_BITRATE])
    else:
        cmd.append("-an")
    cmd.extend(["-movflags", "+faststart", str(out_path)])
    return cmd


def convert_file(
    ffmpeg: Path,
    ffprobe: Path,
    video2x: Path,
    file_path: Path,
    out_path: Path,
    model: str,
    gpu: int | None,
    force_uhd: bool | None,
) -> str | None:
    payload = probe_video(ffprobe, file_path)
    width, height, fps, has_audio = stream_info(payload)
    if fps is None or fps <= 0:
        raise RuntimeError(f"Could not probe frame rate: {file_path}")

    fps_label = f"{fps:.3g}"

    if is_already_60(fps):
        return None

    if fps > TARGET_FPS + FPS_TOLERANCE:
        plan = (
            f"ffmpeg drop ({width}x{height} @{fps_label}fps -> 60fps, "
            "no RIFE)"
        )
        out_path.parent.mkdir(parents=True, exist_ok=True)
        run_checked(
            build_ffmpeg_fps_args(ffmpeg, file_path, out_path, has_audio, False),
            "FFmpeg fps=60",
        )
        return plan

    mul = rife_multiplier(fps)
    uhd = force_uhd if force_uhd is not None else width >= UHD_MIN_WIDTH
    plan = (
        f"rife x{mul} ({width}x{height} @{fps_label}fps, {model}"
        f"{', uhd' if uhd else ''}) -> 60fps"
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_rife = out_path.with_name(f".{out_path.stem}.rife.tmp.mkv")
    if tmp_rife.exists():
        tmp_rife.unlink()
    try:
        run_video2x(
            build_video2x_rife_args(
                video2x, file_path, tmp_rife, mul, model, uhd, gpu
            ),
            tmp_rife,
        )
        rife_payload = probe_video(ffprobe, tmp_rife)
        _, _, rife_fps, rife_audio = stream_info(rife_payload)
        copy_video = rife_fps is not None and is_already_60(rife_fps)
        run_checked(
            build_ffmpeg_fps_args(
                ffmpeg, tmp_rife, out_path, rife_audio, copy_video
            ),
            "FFmpeg 60fps master",
        )
    finally:
        if tmp_rife.exists():
            tmp_rife.unlink()

    return plan


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Interpolate a single video to 60fps with Video2X RIFE at source resolution. "
            "Already ~60fps files are skipped. Above 60fps is FFmpeg drop, not RIFE."
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
    parser.add_argument(
        "--rife-model",
        default=DEFAULT_RIFE_MODEL,
        help=f"RIFE model name (default: {DEFAULT_RIFE_MODEL})",
    )
    parser.add_argument(
        "--uhd",
        action="store_true",
        help="Force RIFE Ultra HD mode (default: on when width >= 1920)",
    )
    parser.add_argument(
        "--gpu",
        type=int,
        default=None,
        help="Vulkan GPU index for Video2X (-d)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    script_path = Path(__file__)
    repo_root = find_repo_root(script_path)
    if repo_root is None:
        print(
            "Could not find .dependency/manifest.json by walking up from this script.",
            file=sys.stderr,
        )
        return 1

    ffmpeg = resolve_ffmpeg(script_path)
    ffprobe = resolve_ffprobe(ffmpeg)
    video2x = resolve_tool_bin(repo_root, "video2x")

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

    force_uhd = True if args.uhd else None
    print(f"Video:  {video_path}")
    print(f"Model:  {args.rife_model}")
    print(f"Target: {int(TARGET_FPS)}fps RIFE at source resolution")
    print(f"Output: {out_path}")
    if args.gpu is not None:
        print(f"GPU:    {args.gpu}")
    print()

    try:
        plan = convert_file(
            ffmpeg,
            ffprobe,
            video2x,
            video_path,
            out_path,
            args.rife_model,
            args.gpu,
            force_uhd,
        )
    except RuntimeError as exc:
        print(f"[fail] {out_path.name}")
        print(exc)
        return 1

    if plan is None:
        payload = probe_video(ffprobe, video_path)
        _, _, fps, _ = stream_info(payload)
        fps_label = f"{fps:.3g}" if fps else "?"
        print(f"[skip] {video_path.name} (already ~{fps_label}fps)")
        return 0

    print(f"[run]  {video_path.name} -> {out_path.name}")
    print(f"       {plan}")
    print()
    print(f"Done. wrote {out_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
