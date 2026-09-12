"""Shared file discovery helpers for video skill scripts."""

from __future__ import annotations

import sys
from pathlib import Path

VIDEO_EXTENSIONS = {
    ".mp4",
    ".mkv",
    ".mov",
    ".avi",
    ".webm",
    ".wmv",
    ".flv",
    ".m4v",
    ".mpeg",
    ".mpg",
    ".ts",
    ".mts",
    ".m2ts",
    ".3gp",
    ".ogv",
}


def video_output_name(source: Path, *, suffix: str | None = None) -> str:
    """Return the default output filename for a single-file video skill."""
    if suffix is None:
        return source.name
    return source.with_suffix(suffix).name


def resolve_video_file(args_video: str) -> Path | None:
    """Resolve a single video file path, or print an error and return None."""
    path = Path(args_video).expanduser()
    if not path.exists():
        print(f"Video file not found: {args_video}", file=sys.stderr)
        return None
    path = path.resolve()
    if not path.is_file():
        print(
            f"Not a video file (directories are not supported): {args_video}",
            file=sys.stderr,
        )
        return None
    if path.suffix.lower() not in VIDEO_EXTENSIONS:
        print(f"Not a supported video file: {path}", file=sys.stderr)
        return None
    return path
