#!/usr/bin/env python3
"""Tests for compress.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AI_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

import compress  # noqa: E402
from common.dependency_utils import find_repo_root, resolve_tool_bin  # noqa: E402
from common.output_utils import resolve_output_path  # noqa: E402
from common.video_utils import video_output_name  # noqa: E402

REPO_ROOT = find_repo_root(Path(__file__))
assert REPO_ROOT is not None
PYTHON_BIN = resolve_tool_bin(REPO_ROOT, "python")
COMPRESS_SCRIPT = SCRIPT_DIR / "compress.py"
SAMPLE_VIDEO = REPO_ROOT / ".ai/test/video/opening.mp4"


class CompressLogicTest(unittest.TestCase):
    def test_parse_size_mb(self) -> None:
        self.assertEqual(compress.parse_size("50"), 50 * compress.MIB)
        self.assertEqual(compress.parse_size("50MB"), 50 * compress.MIB)
        self.assertEqual(compress.parse_size("500KB"), 500 * compress.KIB)

    def test_parse_size_invalid(self) -> None:
        with self.assertRaises(ValueError):
            compress.parse_size("not-a-size")

    def test_compute_video_bitrate(self) -> None:
        vb = compress.compute_video_bitrate(
            max_bytes=50 * compress.MIB,
            duration=10.0,
            audio_bitrate=128_000,
            has_audio=True,
            safety=0.90,
        )
        self.assertGreater(vb, compress.MIN_VIDEO_BITRATE)

    def test_map_preset_nvenc(self) -> None:
        encoder = compress.EncoderChoice("h264_nvenc", "nvenc", False, "NVENC")
        self.assertEqual(compress.map_preset(encoder, "medium"), "p4")
        self.assertEqual(compress.map_preset(encoder, "p6"), "p6")

    def test_default_output_path(self) -> None:
        source = Path("/tmp/clip.mp4")
        out = resolve_output_path(
            "",
            source,
            compress.DEFAULT_OUTPUT_SUBDIR,
            video_output_name(source, suffix=".mp4"),
        )
        self.assertEqual(
            out,
            source.parent / compress.DEFAULT_OUTPUT_SUBDIR / "clip.mp4",
        )


class CompressCliTest(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(PYTHON_BIN), str(COMPRESS_SCRIPT), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(REPO_ROOT),
        )

    def test_help(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--video", result.stdout)
        self.assertIn("--max-size", result.stdout)
        self.assertIn("--output", result.stdout)
        self.assertNotIn("--dry-run", result.stdout)
        self.assertNotIn("--overwrite", result.stdout)

    def test_missing_video(self) -> None:
        result = self.run_cli("--max-size", "50MB")
        self.assertNotEqual(result.returncode, 0)

    def test_missing_max_size(self) -> None:
        result = self.run_cli("--video", "clip.mp4")
        self.assertNotEqual(result.returncode, 0)

    def test_video_not_found(self) -> None:
        result = self.run_cli("--video", "missing-no-such.mp4", "--max-size", "50MB")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Video file not found", result.stderr)

    def test_rejects_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("--video", tmp, "--max-size", "50MB")
            self.assertEqual(result.returncode, 1)
            self.assertIn("directories are not supported", result.stderr)

    def test_skip_when_already_under_limit(self) -> None:
        if not SAMPLE_VIDEO.is_file():
            self.skipTest("sample video missing")

        huge_limit = "9999GB"
        result = self.run_cli("--video", str(SAMPLE_VIDEO), "--max-size", huge_limit)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("[skip]", result.stdout)
        self.assertIn("already under limit", result.stdout)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
