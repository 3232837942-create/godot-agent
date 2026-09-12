"""Shared file discovery and FFmpeg helpers for audio skill scripts."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

AUDIO_EXTENSIONS = {".wav", ".mp3", ".ogg", ".flac", ".aac", ".m4a", ".opus", ".wma"}


def resolve_audio_file(args_audio: str) -> Path | None:
    """Resolve a single audio file path, or print an error and return None."""
    path = Path(args_audio).expanduser()
    if not path.exists():
        print(f"Audio file not found: {args_audio}", file=sys.stderr)
        return None
    path = path.resolve()
    if not path.is_file():
        print(
            f"Not an audio file (directories are not supported): {args_audio}",
            file=sys.stderr,
        )
        return None
    if path.suffix.lower() not in AUDIO_EXTENSIONS:
        print(f"Not a supported audio file: {path}", file=sys.stderr)
        return None
    return path


def find_audio_files(path: Path, recurse: bool = False) -> list[Path]:
    """Find supported audio files at a path, optionally recursing directories."""
    if path.is_file():
        if path.suffix.lower() not in AUDIO_EXTENSIONS:
            print(f"Not a supported audio file: {path}", file=sys.stderr)
            sys.exit(1)
        return [path.resolve()]

    if not path.is_dir():
        print(f"Input path not found: {path}", file=sys.stderr)
        sys.exit(1)

    candidates = path.rglob("*") if recurse else path.iterdir()
    files = [
        item.resolve()
        for item in candidates
        if item.is_file() and item.suffix.lower() in AUDIO_EXTENSIONS
    ]
    return sorted(files)


def relative_audio_path(file_path: Path, input_root: Path) -> str:
    """Return a stable relative path for mirroring an input directory tree."""
    try:
        return file_path.relative_to(input_root).as_posix()
    except ValueError:
        return file_path.name


def audio_output_name(source: Path, *, suffix: str | None = None) -> str:
    """Return the default output filename for a single-file audio skill."""
    if suffix is None:
        return source.name
    return source.with_suffix(suffix).name


def get_duration(ffprobe: Path, file_path: Path) -> float:
    """Return audio duration in seconds via ffprobe."""
    result = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"Could not read duration for: {file_path}")
    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(f"Invalid duration for: {file_path}") from exc
