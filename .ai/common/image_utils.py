"""Shared file discovery and batch-path helpers for image skill scripts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

IMAGE_EXTENSIONS = {
    ".avif",
    ".bmp",
    ".gif",
    ".ico",
    ".jfif",
    ".jpg",
    ".jpeg",
    ".png",
    ".tif",
    ".tiff",
    ".webp",
}


def resolve_image_file(args_image: str) -> Path | None:
    """Resolve a single image file path, or print an error and return None."""
    path = Path(args_image).expanduser()
    if not path.exists():
        print(f"Image file not found: {args_image}", file=sys.stderr)
        return None
    path = path.resolve()
    if not path.is_file():
        print(
            f"Not an image file (directories are not supported): {args_image}",
            file=sys.stderr,
        )
        return None
    if path.suffix.lower() not in IMAGE_EXTENSIONS:
        print(f"Not a supported image file: {path}", file=sys.stderr)
        return None
    return path


def read_image_size(magick: Path, image_path: Path) -> tuple[int, int]:
    """Return image width and height in pixels via ImageMagick identify."""
    result = subprocess.run(
        [str(magick), "identify", "-format", "%wx%h", str(image_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"Could not read image size for: {image_path}"
            + (f"\n{detail}" if detail else "")
        )
    width_text, _, height_text = result.stdout.partition("x")
    try:
        return int(width_text), int(height_text)
    except ValueError as exc:
        raise RuntimeError(f"Invalid image size for: {image_path}") from exc


def find_image_files(path: Path, recurse: bool = False) -> list[Path]:
    """Find supported image files at a path, optionally recursing directories."""
    if path.is_file():
        if path.suffix.lower() not in IMAGE_EXTENSIONS:
            print(f"Not a supported image file: {path}", file=sys.stderr)
            sys.exit(1)
        return [path.resolve()]

    if not path.is_dir():
        print(f"Input path not found: {path}", file=sys.stderr)
        sys.exit(1)

    candidates = path.rglob("*") if recurse else path.iterdir()
    files = [
        item.resolve()
        for item in candidates
        if item.is_file() and item.suffix.lower() in IMAGE_EXTENSIONS
    ]
    return sorted(files)


def relative_image_path(file_path: Path, input_root: Path) -> str:
    """Return a stable relative path for mirroring an input directory tree."""
    try:
        return file_path.relative_to(input_root).as_posix()
    except ValueError:
        return file_path.name


def image_output_name(source: Path, *, suffix: str | None = None) -> str:
    """Return the default output filename for a single-file image skill."""
    if suffix is None:
        return source.name
    return source.with_suffix(suffix).name


def resolve_input_root(input_path: Path) -> Path:
    """Return the directory root used to mirror relative output paths."""
    return input_path.parent if input_path.is_file() else input_path


def mirror_output_rel(
    file_path: Path,
    input_root: Path,
    *,
    suffix: str | None = None,
) -> str:
    """Return the mirrored relative output path for a source file."""
    rel = relative_image_path(file_path, input_root)
    if suffix is not None:
        return Path(rel).with_suffix(suffix).as_posix()
    return rel


def filter_output_files(files: list[Path], output_dir: Path) -> list[Path]:
    """Drop files that already live under the output directory."""
    out = output_dir.resolve()
    kept: list[Path] = []
    for file_path in files:
        try:
            file_path.resolve().relative_to(out)
        except ValueError:
            kept.append(file_path)
    return kept


def find_source_collisions(
    files: list[Path],
    input_root: Path,
    output_dir: Path,
    *,
    output_suffix: str | None = None,
) -> list[tuple[Path, Path]]:
    """Find outputs that would overwrite their own source files."""
    collisions: list[tuple[Path, Path]] = []
    for file_path in files:
        rel = mirror_output_rel(file_path, input_root, suffix=output_suffix)
        out_path = output_dir / rel
        if out_path.resolve() == file_path.resolve():
            collisions.append((file_path, out_path))
    return collisions
