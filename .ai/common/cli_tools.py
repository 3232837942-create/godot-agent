"""Shared command-line tool resolution helpers for skill scripts."""

from __future__ import annotations

import sys
from pathlib import Path

from common.dependency_utils import find_repo_root, resolve_tool_bin


def resolve_ffmpeg(script_path: Path) -> Path:
    """Resolve FFmpeg from the repository manifest containing a skill script."""
    repo_root = find_repo_root(script_path)
    if repo_root is None:
        print(
            "Could not find .dependency/manifest.json by walking up from this script. "
            "Run from the project that owns this skill.",
            file=sys.stderr,
        )
        sys.exit(1)
    return resolve_tool_bin(repo_root, "ffmpeg")


def resolve_magick(script_path: Path) -> Path:
    """Resolve ImageMagick from the repository manifest containing a skill script."""
    repo_root = find_repo_root(script_path)
    if repo_root is None:
        print(
            "Could not find .dependency/manifest.json by walking up from this script. "
            "Run from the project that owns this skill.",
            file=sys.stderr,
        )
        sys.exit(1)
    return resolve_tool_bin(repo_root, "imagemagick")


def resolve_ffprobe(ffmpeg: Path) -> Path:
    """Resolve ffprobe next to a manifest-resolved ffmpeg binary."""
    name = "ffprobe.exe" if sys.platform == "win32" else "ffprobe"
    probe = ffmpeg.parent / name
    if probe.is_file():
        return probe
    print(
        f"ffprobe not found next to ffmpeg at {ffmpeg.parent}. "
        "Install a full FFmpeg build that includes ffprobe.",
        file=sys.stderr,
    )
    sys.exit(1)
