"""
Split a uniform sprite sheet grid into individual frame PNGs via FFmpeg crop.

Run through default python from .dependency/manifest.json.
Never use host python/py.

Usage
-----
    .dependency/python/python .ai/image-sprite-sheet-split/split_frames.py --image sheet.png --grid 4x4
    .dependency/python/python .ai/image-sprite-sheet-split/split_frames.py --image sheet.png --grid 6x3 -o image/effects/frames
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

from common.cli_tools import resolve_ffmpeg, resolve_ffprobe  # noqa: E402
from common.image_utils import resolve_image_file  # noqa: E402

DEFAULT_OUTPUT_SUBDIR = "image-sprite-sheet-split"
GRID_RE = re.compile(r"^(\d+)x(\d+)$", re.IGNORECASE)


def parse_grid(value: str) -> tuple[int, int]:
    match = GRID_RE.match(value.strip())
    if not match:
        raise argparse.ArgumentTypeError(
            f"Invalid grid '{value}'. Expected format like 4x4."
        )
    cols, rows = int(match.group(1)), int(match.group(2))
    if cols < 1 or rows < 1:
        raise argparse.ArgumentTypeError("Grid columns and rows must be >= 1.")
    return cols, rows


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
    try:
        width = int(stream.get("width") or 0)
        height = int(stream.get("height") or 0)
    except (TypeError, ValueError):
        width = height = 0

    return {"width": width, "height": height}


def compute_layout(
    width: int,
    height: int,
    cols: int,
    rows: int,
) -> tuple[int, int, list[tuple[int, int, int, int]], list[str]]:
    cell_width = width // cols
    cell_height = height // rows
    if cell_width <= 0 or cell_height <= 0:
        raise ValueError("Computed cell size is zero or negative.")

    warnings: list[str] = []
    if width % cols:
        warnings.append(f"{width % cols}px unused horizontally after dividing into {cols} columns.")
    if height % rows:
        warnings.append(f"{height % rows}px unused vertically after dividing into {rows} rows.")

    crops: list[tuple[int, int, int, int]] = []
    for row in range(rows):
        for col in range(cols):
            x = col * cell_width
            y = row * cell_height
            crops.append((x, y, cell_width, cell_height))

    return cell_width, cell_height, crops, warnings


def crop_frame(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    x: int,
    y: int,
    w: int,
    h: int,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        str(ffmpeg),
        "-hide_banner",
        "-nostats",
        "-loglevel",
        "error",
        "-y",
        "-i",
        str(file_path),
        "-vf",
        f"crop={w}:{h}:{x}:{y}",
        "-frames:v",
        "1",
        "-c:v",
        "png",
        str(out_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"FFmpeg crop failed for: {file_path}"
            + (f"\n{detail}" if detail else "")
        )


def resolve_frames_dir(args_output: str, image_path: Path) -> Path:
    stem = image_path.stem
    if not args_output:
        return image_path.parent / DEFAULT_OUTPUT_SUBDIR / stem

    output = Path(args_output).expanduser()
    if args_output.endswith(("/", "\\")) or output.suffix == "":
        return output / stem
    if output.exists() and output.is_dir():
        return output / stem
    return output


def frame_name(stem: str, index: int, digits: int) -> str:
    return f"{stem}_{index:0{digits}d}.png"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Split a uniform sprite sheet grid into individual PNG frames."
    )
    parser.add_argument(
        "--image",
        required=True,
        help="Path to a single sprite sheet image file",
    )
    parser.add_argument(
        "--grid",
        required=True,
        type=parse_grid,
        metavar="COLSxROWS",
        help="Grid layout, e.g. 4x4 or 3x6",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help=(
            "Output directory root. "
            f"Default: <image-dir>/{DEFAULT_OUTPUT_SUBDIR}/<sheet-stem>/"
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    cols, rows = args.grid

    image_path = resolve_image_file(args.image)
    if image_path is None:
        return 1

    frames_dir = resolve_frames_dir(args.output, image_path)
    frame_count = cols * rows
    digits = max(3, len(str(frame_count)))
    planned = [
        frames_dir / frame_name(image_path.stem, index, digits)
        for index in range(1, frame_count + 1)
    ]

    existing = [path for path in planned if path.exists()]
    if existing:
        print(f"Output already exists: {existing[0]}", file=sys.stderr)
        return 1

    ffmpeg = resolve_ffmpeg(Path(__file__))
    ffprobe = resolve_ffprobe(ffmpeg)

    probe = probe_image(ffprobe, image_path)
    width = probe.get("width") or 0
    height = probe.get("height") or 0
    if width <= 0 or height <= 0:
        print(f"Could not read image dimensions: {image_path}", file=sys.stderr)
        return 1

    try:
        cell_w, cell_h, crops, warnings = compute_layout(width, height, cols, rows)
    except ValueError as exc:
        print(f"Layout error: {exc}", file=sys.stderr)
        return 1

    print(f"Image:  {image_path}")
    print(f"Size:   {width}x{height}")
    print(f"Grid:   {cols}x{rows} ({frame_count} frames)")
    print(f"Cell:   {cell_w}x{cell_h}")
    print(f"Output: {frames_dir}/")
    for warning in warnings:
        print(f"Warn:   {warning}")
    print()

    frames_dir.mkdir(parents=True, exist_ok=True)
    failed = 0

    for (x, y, w, h), out_path in zip(crops, planned):
        try:
            crop_frame(ffmpeg, image_path, out_path, x, y, w, h)
            print(f"[ok]   {out_path.name} ({w}x{h})")
        except RuntimeError as exc:
            print(f"[fail] {out_path.name}")
            print(f"       {exc}")
            failed += 1

    print()
    if failed:
        print(f"Done with errors. failed={failed}")
        return 1

    print(f"Done. wrote {frame_count} frame(s) to {frames_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
