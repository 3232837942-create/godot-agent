#!/usr/bin/env python3
"""Tests for convert.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AI_ROOT = SCRIPT_DIR.parent
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import convert  # noqa: E402
from common.dependency_utils import find_repo_root, resolve_tool_bin  # noqa: E402

REPO_ROOT = find_repo_root(Path(__file__))
assert REPO_ROOT is not None
PYTHON_BIN = resolve_tool_bin(REPO_ROOT, "python")
CONVERT_SCRIPT = SCRIPT_DIR / "convert.py"
TANK1 = REPO_ROOT / ".ai/test/image/tank1.jpg"


class CanStreamCopyTest(unittest.TestCase):
    def test_png_source_can_stream_copy(self) -> None:
        path = Path("hero.png")
        probe = {"codec": "png", "has_alpha": True}
        self.assertTrue(convert.can_stream_copy(path, probe, strip_alpha=False))

    def test_strip_alpha_disables_stream_copy(self) -> None:
        path = Path("hero.png")
        probe = {"codec": "png", "has_alpha": True}
        self.assertFalse(convert.can_stream_copy(path, probe, strip_alpha=True))

    def test_jpeg_never_stream_copies(self) -> None:
        path = Path("hero.jpg")
        probe = {"codec": "mjpeg"}
        self.assertFalse(convert.can_stream_copy(path, probe, strip_alpha=False))


class BuildFfmpegArgsTest(unittest.TestCase):
    def test_stream_copy(self) -> None:
        args = convert.build_ffmpeg_args(
            Path("ffmpeg.exe"),
            Path("in.png"),
            Path("out.png"),
            stream_copy=True,
            strip_alpha=False,
            first_frame_only=False,
        )
        self.assertEqual(args[-3:], ["-c:v", "copy", "out.png"])

    def test_gif_first_frame(self) -> None:
        args = convert.build_ffmpeg_args(
            Path("ffmpeg.exe"),
            Path("in.gif"),
            Path("out.png"),
            stream_copy=False,
            strip_alpha=False,
            first_frame_only=True,
        )
        self.assertIn("-frames:v", args)
        self.assertIn("1", args)

    def test_strip_alpha_uses_rgb24(self) -> None:
        args = convert.build_ffmpeg_args(
            Path("ffmpeg.exe"),
            Path("in.webp"),
            Path("out.png"),
            stream_copy=False,
            strip_alpha=True,
            first_frame_only=False,
        )
        self.assertIn("-pix_fmt", args)
        self.assertIn("rgb24", args)


class ConvertCliTest(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(PYTHON_BIN), str(CONVERT_SCRIPT), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(REPO_ROOT),
        )

    def test_help(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--image", result.stdout)
        self.assertIn("--strip-alpha", result.stdout)

    def test_image_not_found(self) -> None:
        result = self.run_cli("--image", "missing-no-such-file.webp")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Image file not found", result.stderr)

    def test_directory_not_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("--image", tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn("Not an image file", result.stderr)

    def test_convert_jpg_to_png(self) -> None:
        if not TANK1.is_file():
            self.skipTest(f"sample image missing: {TANK1}")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "tank1.jpg"
            src.write_bytes(TANK1.read_bytes())

            result = self.run_cli("--image", str(src))
            self.assertEqual(result.returncode, 0, result.stderr)

            out = root / "image-to-png" / "tank1.png"
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size, 0)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
