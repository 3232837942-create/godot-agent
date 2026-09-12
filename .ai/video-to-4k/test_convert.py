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
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

import convert  # noqa: E402
from common.dependency_utils import find_repo_root, resolve_tool_bin  # noqa: E402
from common.output_utils import resolve_output_path  # noqa: E402
from common.video_utils import video_output_name  # noqa: E402

REPO_ROOT = find_repo_root(Path(__file__))
assert REPO_ROOT is not None
PYTHON_BIN = resolve_tool_bin(REPO_ROOT, "python")
CONVERT_SCRIPT = SCRIPT_DIR / "convert.py"


class ConvertLogicTest(unittest.TestCase):
    def test_is_already_4k(self) -> None:
        self.assertTrue(convert.is_already_4k(3840, 2160))
        self.assertTrue(convert.is_already_4k(4096, 2160))
        self.assertFalse(convert.is_already_4k(1920, 1080))

    def test_pick_scale_general(self) -> None:
        self.assertEqual(convert.pick_scale(1920, 1080, convert.DEFAULT_MODEL), 4)
        self.assertEqual(convert.pick_scale(2560, 1440, convert.DEFAULT_MODEL), 4)

    def test_pick_scale_anime(self) -> None:
        self.assertEqual(convert.pick_scale(1920, 1080, convert.ANIME_MODEL), 2)

    def test_default_output_path(self) -> None:
        source = Path("/tmp/clip.mp4")
        out = resolve_output_path(
            "",
            source,
            convert.DEFAULT_OUTPUT_SUBDIR,
            video_output_name(source, suffix=".mp4"),
        )
        self.assertEqual(
            out,
            source.parent / convert.DEFAULT_OUTPUT_SUBDIR / "clip.mp4",
        )

    def test_default_upscaled_path(self) -> None:
        source = Path("/tmp/clip.mp4")
        upscaled = convert.default_upscaled_path(source)
        self.assertEqual(
            upscaled,
            source.parent
            / convert.DEFAULT_OUTPUT_SUBDIR
            / convert.DEFAULT_UPSCALED_SUBDIR
            / "clip.mkv",
        )

    def test_build_ffmpeg_final_args(self) -> None:
        ffmpeg = Path("/ffmpeg")
        cmd = convert.build_ffmpeg_final_args(ffmpeg, Path("/in.mp4"), Path("/out.mp4"), True)
        vf = cmd[cmd.index("-vf") + 1]
        self.assertIn("scale=3840:2160", vf)
        self.assertIn("libx265", cmd)
        self.assertIn("-c:a", cmd)


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
        self.assertIn("--video", result.stdout)
        self.assertIn("--output", result.stdout)
        self.assertIn("--anime", result.stdout)
        self.assertIn("--clean-upscaled", result.stdout)
        self.assertNotIn("--dry-run", result.stdout)
        self.assertNotIn("--overwrite", result.stdout)
        self.assertNotIn("--recurse", result.stdout)

    def test_missing_video(self) -> None:
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)

    def test_video_not_found(self) -> None:
        result = self.run_cli("--video", "missing-no-such.mp4")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Video file not found", result.stderr)

    def test_rejects_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("--video", tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn("directories are not supported", result.stderr)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
