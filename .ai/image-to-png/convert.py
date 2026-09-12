#!/usr/bin/env python3
"""
Convert a single image file to PNG using FFmpeg.

Run through default python from .dependency/manifest.json.
Never use host python/py.

Usage
-----
    .dependency/python/python .ai/image-to-png/convert.py --image assets/ui/icon.webp
    .dependency/python/python .ai/image-to-png/convert.py --image assets/sprites/hero.jpg --strip-alpha
    .dependency/python/python .ai/image-to-png/convert.py --image assets/ui/icon.webp -o assets/ui_png
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
from common.image_utils import image_output_name, resolve_image_file  # noqa: E402
from common.output_utils import format_default_output_help, resolve_output_path  # noqa: E402

DEFAULT_OUTPUT_SUBDIR = "image-to-png"


def probe_image(ffprobe: Path, file_path: Path) -> dict:
    result = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-select_streams",
            "v:0",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return {}

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}

    streams = payload.get("streams") or []
    if not streams:
        return {}

    stream = streams[0]
    width = stream.get("width")
    height = stream.get("height")
    try:
        width = int(width) if width else None
    except (TypeError, ValueError):
        width = None
    try:
        height = int(height) if height else None
    except (TypeError, ValueError):
        height = None

    pix_fmt = stream.get("pix_fmt", "")
    has_alpha = "a" in pix_fmt or pix_fmt.endswith("a")

    return {
        "codec": stream.get("codec_name", ""),
        "width": width,
        "height": height,
        "pix_fmt": pix_fmt,
        "has_alpha": has_alpha,
    }


def can_stream_copy(
    file_path: Path,
    probe: dict,
    strip_alpha: bool,
) -> bool:
    if strip_alpha:
        return False
    if file_path.suffix.lower() != ".png":
        return False
    return probe.get("codec", "") == "png"


def build_ffmpeg_args(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    stream_copy: bool,
    strip_alpha: bool,
    first_frame_only: bool,
) -> list[str]:
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-nostats",
        "-y",
        "-i",
        str(file_path),
    ]
    if first_frame_only:
        cmd.extend(["-frames:v", "1"])
    if stream_copy:
        cmd.extend(["-c:v", "copy", str(out_path)])
        return cmd

    if strip_alpha:
        cmd.extend(["-pix_fmt", "rgb24"])
    cmd.extend(["-c:v", "png", str(out_path)])
    return cmd


def convert_file(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    stream_copy: bool,
    strip_alpha: bool,
    first_frame_only: bool,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_ffmpeg_args(
        ffmpeg, file_path, out_path, stream_copy, strip_alpha, first_frame_only
    )
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"FFmpeg convert failed for: {file_path}"
            + (f"\n{detail}" if detail else "")
        )


def describe_plan(
    probe: dict,
    stream_copy: bool,
    strip_alpha: bool,
    is_gif: bool,
) -> str:
    if stream_copy:
        w = probe.get("width") or "?"
        h = probe.get("height") or "?"
        return f"stream copy ({w}x{h})"

    parts = ["lossless PNG"]
    w = probe.get("width")
    h = probe.get("height")
    if w and h:
        parts.append(f"{w}x{h}")
    if strip_alpha:
        parts.append("RGB (alpha stripped)")
    elif probe.get("has_alpha"):
        parts.append("RGBA")
    if is_gif:
        parts.append("first frame")
    return ", ".join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Convert a single image file to PNG using FFmpeg."
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Path to a single image file",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help=(
            "Output PNG file or directory. "
            f"Default: {format_default_output_help(DEFAULT_OUTPUT_SUBDIR, output_name_label='source-name.png')}"
        ),
    )
    parser.add_argument(
        "--strip-alpha",
        action="store_true",
        help="Export RGB PNG without alpha channel",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    image_path = resolve_image_file(args.image)
    if image_path is None:
        return 1

    out_path = resolve_output_path(
        args.output,
        image_path,
        DEFAULT_OUTPUT_SUBDIR,
        image_output_name(image_path, suffix=".png"),
    )

    if out_path.resolve() == image_path.resolve():
        print(
            "Refusing to overwrite source file. Choose a separate output path "
            f"(default: {DEFAULT_OUTPUT_SUBDIR}/).",
            file=sys.stderr,
        )
        return 1

    if out_path.exists():
        print(f"Output already exists: {out_path}", file=sys.stderr)
        return 1

    ffmpeg = resolve_ffmpeg(Path(__file__))
    ffprobe = resolve_ffprobe(ffmpeg)

    probe = probe_image(ffprobe, image_path)
    is_gif = image_path.suffix.lower() == ".gif"
    first_frame_only = is_gif
    stream_copy = can_stream_copy(image_path, probe, args.strip_alpha)
    plan = describe_plan(probe, stream_copy, args.strip_alpha, is_gif)

    print(f"Image:  {image_path}")
    print(f"Plan:   {plan}")
    print(f"Output: {out_path}")
    print()

    try:
        print(f"[run]  {image_path.name} -> {out_path.name} ({plan})")
        convert_file(
            ffmpeg,
            image_path,
            out_path,
            stream_copy,
            args.strip_alpha,
            first_frame_only,
        )
    except RuntimeError as exc:
        print(f"[fail] {out_path.name}")
        print(exc)
        return 1

    print()
    print(f"Done. wrote {out_path.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
