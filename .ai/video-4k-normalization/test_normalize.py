#!/usr/bin/env python3
"""Tests for normalize.py."""

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

import normalize  # noqa: E402
from common.dependency_utils import find_repo_root, resolve_tool_bin  # noqa: E402
from common.output_utils import resolve_output_path  # noqa: E402
from common.video_utils import video_output_name  # noqa: E402

REPO_ROOT = find_repo_root(Path(__file__))
assert REPO_ROOT is not None
PYTHON_BIN = resolve_tool_bin(REPO_ROOT, "python")
NORMALIZE_SCRIPT = SCRIPT_DIR / "normalize.py"
SAMPLE_VIDEO = REPO_ROOT / ".ai/test/video/opening.mp4"


class NormalizeLogicTest(unittest.TestCase):
    def test_is_hdr_detects_pq(self) -> None:
        video = {"color_transfer": "smpte2084", "color_primaries": "bt709"}
        self.assertTrue(normalize.is_hdr(video))

    def test_is_hdr_detects_bt2020(self) -> None:
        video = {"color_primaries": "bt2020"}
        self.assertTrue(normalize.is_hdr(video))

    def test_is_hdr_sdr(self) -> None:
        video = {"color_transfer": "bt709", "color_primaries": "bt709"}
        self.assertFalse(normalize.is_hdr(video))

    def test_build_vf_sdr(self) -> None:
        vf = normalize.build_vf(False)
        self.assertIn("scale=3840:2160", vf)
        self.assertIn("fps=60", vf)
        self.assertIn("yuv420p10le", vf)
        self.assertNotIn("tonemap", vf)

    def test_build_vf_hdr(self) -> None:
        vf = normalize.build_vf(True)
        self.assertIn("tonemap=hable", vf)
        self.assertIn("scale=3840:2160", vf)

    def test_parse_frame_rate(self) -> None:
        self.assertAlmostEqual(normalize.parse_frame_rate("30000/1001"), 29.97002997002997)
        self.assertEqual(normalize.parse_frame_rate("60"), 60.0)
        self.assertIsNone(normalize.parse_frame_rate("0/0"))

    def test_default_output_path(self) -> None:
        source = Path("/tmp/clip.mp4")
        out = resolve_output_path(
            "",
            source,
            normalize.DEFAULT_OUTPUT_SUBDIR,
            video_output_name(source, suffix=".mp4"),
        )
        self.assertEqual(
            out,
            source.parent / normalize.DEFAULT_OUTPUT_SUBDIR / "clip.mp4",
        )


class NormalizeCliTest(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(PYTHON_BIN), str(NORMALIZE_SCRIPT), *args],
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
        self.assertNotIn("--dry-run", result.stdout)
        self.assertNotIn("--overwrite", result.stdout)

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
