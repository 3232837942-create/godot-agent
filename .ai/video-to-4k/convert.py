#!/usr/bin/env python3
"""
Upscale a single below-4K video with Video2X, then encode a unified 4K H.265 Main10 MP4.

Run through default python from .dependency/manifest.json.
Never use host python/py.

Usage
-----
    .dependency/python/python .ai/video-to-4k/convert.py --video path/to/clip.mp4
    .dependency/python/python .ai/video-to-4k/convert.py --video path/to/clip.mp4 --anime
    .dependency/python/python .ai/video-to-4k/convert.py --video path/to/clip.mp4 --gpu 0 --clean-upscaled
    .dependency/python/python .ai/video-to-4k/convert.py --video path/to/clip.mp4 -o path/to/out.mp4
"""

from __future__ import annotations

import argparse
import json
import shutil
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

DEFAULT_OUTPUT_SUBDIR = "video-to-4k"
DEFAULT_UPSCALED_SUBDIR = "upscaled"

TARGET_WIDTH = 3840
TARGET_HEIGHT = 2160
VIDEO_BITRATE = "40M"
AUDIO_BITRATE = "320k"
DEFAULT_MODEL = "realesrgan-plus"
ANIME_MODEL = "realesr-animevideov3"

MODEL_SCALES: dict[str, tuple[int, ...]] = {
    "realesrgan-plus": (4,),
    "realesrgan-plus-anime": (4,),
    "realesr-animevideov3": (2, 3, 4),
}


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


def is_already_4k(width: int, height: int) -> bool:
    return width >= TARGET_WIDTH and height >= TARGET_HEIGHT


def pick_scale(width: int, height: int, model: str = DEFAULT_MODEL) -> int:
    scales = MODEL_SCALES.get(model, (2, 4))
    for scale in scales:
        if width * scale >= TARGET_WIDTH and height * scale >= TARGET_HEIGHT:
            return scale
    return scales[-1]


def default_upscaled_path(video_path: Path) -> Path:
    name = video_path.with_suffix(".mkv").name
    return video_path.parent / DEFAULT_OUTPUT_SUBDIR / DEFAULT_UPSCALED_SUBDIR / name


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
        "Video2X upscale failed" + (f"\n{detail}" if detail else "")
    )


def build_video2x_args(
    video2x: Path,
    file_path: Path,
    out_path: Path,
    scale: int,
    model: str,
    gpu: int | None,
) -> list[str]:
    cmd = [
        str(video2x),
        "-i",
        str(file_path),
        "-o",
        str(out_path),
        "-p",
        "realesrgan",
        "-s",
        str(scale),
        "--realesrgan-model",
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
    if gpu is not None:
        cmd.extend(["-d", str(gpu)])
    return cmd


def build_ffmpeg_final_args(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    has_audio: bool,
) -> list[str]:
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-nostats",
        "-y",
        "-i",
        str(file_path),
        "-vf",
        f"scale={TARGET_WIDTH}:{TARGET_HEIGHT}:flags=lanczos,format=yuv420p10le",
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
        "profile=main10",
    ]
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
    upscaled_path: Path,
    model: str,
    gpu: int | None,
    clean_upscaled: bool,
) -> str:
    payload = probe_video(ffprobe, file_path)
    width, height, fps, has_audio = stream_info(payload)
    already_4k = is_already_4k(width, height)
    fps_label = f"{fps:.3g}" if fps else "?"

    if already_4k:
        plan = f"ffmpeg-only ({width}x{height} @{fps_label}fps -> 4K Main10, fps kept)"
        out_path.parent.mkdir(parents=True, exist_ok=True)
        run_checked(
            build_ffmpeg_final_args(ffmpeg, file_path, out_path, has_audio),
            "FFmpeg final encode",
        )
        return plan

    scale = pick_scale(width, height, model)
    plan = (
        f"video2x x{scale} ({width}x{height} @{fps_label}fps, {model}) -> "
        f"ffmpeg 4K Main10 (fps kept)"
    )

    upscaled_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    tmp_upscaled = upscaled_path.with_name(
        f".{upscaled_path.stem}.tmp{upscaled_path.suffix}"
    )
    if tmp_upscaled.exists():
        tmp_upscaled.unlink()
    try:
        run_video2x(
            build_video2x_args(video2x, file_path, tmp_upscaled, scale, model, gpu),
            tmp_upscaled,
        )
        if upscaled_path.exists():
            upscaled_path.unlink()
        shutil.move(str(tmp_upscaled), str(upscaled_path))
    finally:
        if tmp_upscaled.exists():
            tmp_upscaled.unlink()

    up_payload = probe_video(ffprobe, upscaled_path)
    _, _, _, up_has_audio = stream_info(up_payload)

    run_checked(
        build_ffmpeg_final_args(ffmpeg, upscaled_path, out_path, up_has_audio),
        "FFmpeg final encode",
    )

    if clean_upscaled and upscaled_path.exists():
        upscaled_path.unlink()

    return plan


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Upscale a single below-4K video with Video2X, then encode unified "
            "3840x2160 H.265 Main10 40Mbps + AAC 320kbps MP4 "
            "(source frame rate preserved)."
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
        "--anime",
        action="store_true",
        help=f"Use Real-ESRGAN anime model ({ANIME_MODEL})",
    )
    parser.add_argument(
        "--gpu",
        type=int,
        default=None,
        help="Vulkan GPU index for Video2X (-d)",
    )
    parser.add_argument(
        "--clean-upscaled",
        action="store_true",
        help="Delete Video2X intermediate after successful final encode",
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
    upscaled_path = default_upscaled_path(video_path)

    if out_path.resolve() == video_path.resolve():
        print(
            "Refusing to overwrite source file. Choose a separate output path "
            f"(default: {DEFAULT_OUTPUT_SUBDIR}/).",
            file=sys.stderr,
        )
        return 1
    if upscaled_path.resolve() == video_path.resolve():
        print(
            "Refusing to overwrite source file. Upscaled intermediate path "
            f"collides with source (default: {DEFAULT_OUTPUT_SUBDIR}/{DEFAULT_UPSCALED_SUBDIR}/).",
            file=sys.stderr,
        )
        return 1

    model = ANIME_MODEL if args.anime else DEFAULT_MODEL
    print(f"Video:    {video_path}")
    print(f"Model:    {model}")
    print(
        f"Target:   {TARGET_WIDTH}x{TARGET_HEIGHT} H.265 Main10 {VIDEO_BITRATE} "
        f"+ AAC {AUDIO_BITRATE} (source fps kept)"
    )
    print(f"Output:   {out_path}")
    print(f"Upscaled: {upscaled_path}")
    if args.gpu is not None:
        print(f"GPU:      {args.gpu}")
    print()

    try:
        print(f"[run]  {video_path.name} -> {out_path.name}")
        plan = convert_file(
            ffmpeg,
            ffprobe,
            video2x,
            video_path,
            out_path,
            upscaled_path,
            model,
            args.gpu,
            args.clean_upscaled,
        )
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
