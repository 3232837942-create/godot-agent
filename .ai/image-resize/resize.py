#!/usr/bin/env python3
"""
Resize a single image file using ImageMagick.

Run through default python from .dependency/manifest.json.
Never use host python/py.

Usage
-----
    .dependency/python/python .ai/image-resize/resize.py --image assets/sprites/hero.png --width 128 --height 128
    .dependency/python/python .ai/image-resize/resize.py --image assets/ui/icon.png --width 64 --height 64 --mode fill
    .dependency/python/python .ai/image-resize/resize.py --image assets/icons/badge.png -o assets/icons_64 --width 64 --height 64
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[1]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from common.cli_tools import resolve_magick  # noqa: E402
from common.image_utils import image_output_name, resolve_image_file  # noqa: E402
from common.output_utils import format_default_output_help, resolve_output_path  # noqa: E402

DEFAULT_OUTPUT_SUBDIR = "image-resize"
RESIZE_MODES = ("fit", "fill", "exact")


def build_resize_geometry(width: int, height: int, mode: str) -> str:
    size = f"{width}x{height}"
    if mode == "exact":
        return f"{size}!"
    if mode == "fill":
        return f"{size}^"
    return size


def build_magick_args(
    magick: Path,
    file_path: Path,
    out_path: Path,
    width: int,
    height: int,
    mode: str,
) -> list[str]:
    geometry = build_resize_geometry(width, height, mode)
    cmd = [
        str(magick),
        str(file_path),
        "-resize",
        geometry,
    ]
    if mode == "fill":
        cmd.extend(["-gravity", "center", "-extent", f"{width}x{height}"])
    cmd.append(str(out_path))
    return cmd


def describe_mode(mode: str, width: int, height: int) -> str:
    labels = {
        "fit": f"fit within {width}x{height} (preserve aspect)",
        "fill": f"fill {width}x{height} (crop center)",
        "exact": f"force {width}x{height} (ignore aspect)",
    }
    return labels[mode]


def resize_file(
    magick: Path,
    file_path: Path,
    out_path: Path,
    width: int,
    height: int,
    mode: str,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_magick_args(magick, file_path, out_path, width, height, mode)
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"ImageMagick resize failed for: {file_path}"
            + (f"\n{detail}" if detail else "")
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Resize a single image file using ImageMagick."
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Path to a single image file",
    )
    parser.add_argument(
        "-W",
        "--width",
        type=int,
        required=True,
        help="Target width in pixels (required)",
    )
    parser.add_argument(
        "-H",
        "--height",
        type=int,
        required=True,
        help="Target height in pixels (required)",
    )
    parser.add_argument(
        "--mode",
        choices=RESIZE_MODES,
        default="fit",
        help="Resize mode: fit (default), fill, exact",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help=(
            "Output image file or directory. "
            f"Default: {format_default_output_help(DEFAULT_OUTPUT_SUBDIR)}"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.width <= 0 or args.height <= 0:
        print("Width and height must be positive integers.", file=sys.stderr)
        return 1

    image_path = resolve_image_file(args.image)
    if image_path is None:
        return 1

    out_path = resolve_output_path(
        args.output,
        image_path,
        DEFAULT_OUTPUT_SUBDIR,
        image_output_name(image_path),
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

    magick = resolve_magick(Path(__file__))
    mode_desc = describe_mode(args.mode, args.width, args.height)

    print(f"Image:  {image_path}")
    print(f"Size:   {args.width}x{args.height}")
    print(f"Mode:   {mode_desc}")
    print(f"Output: {out_path}")
    print()

    try:
        print(f"[run]  {image_path.name} -> {out_path.name} ({mode_desc})")
        resize_file(
            magick,
            image_path,
            out_path,
            args.width,
            args.height,
            args.mode,
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
