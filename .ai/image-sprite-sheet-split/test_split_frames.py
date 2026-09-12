#!/usr/bin/env python3
"""Tests for split_frames.py."""

from __future__ import annotations

import argparse
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

import split_frames  # noqa: E402
from common.dependency_utils import find_repo_root, resolve_tool_bin  # noqa: E402

REPO_ROOT = find_repo_root(Path(__file__))
assert REPO_ROOT is not None
PYTHON_BIN = resolve_tool_bin(REPO_ROOT, "python")
SPLIT_SCRIPT = SCRIPT_DIR / "split_frames.py"
TANK1 = REPO_ROOT / ".ai/test/image/tank1.jpg"


class ParseGridTest(unittest.TestCase):
    def test_valid(self) -> None:
        self.assertEqual(split_frames.parse_grid("4x4"), (4, 4))
        self.assertEqual(split_frames.parse_grid("6X3"), (6, 3))

    def test_invalid(self) -> None:
        with self.assertRaises(argparse.ArgumentTypeError):
            split_frames.parse_grid("4-by-4")


class ComputeLayoutTest(unittest.TestCase):
    def test_even_4x4(self) -> None:
        cell_w, cell_h, crops, warnings = split_frames.compute_layout(2048, 2048, 4, 4)
        self.assertEqual((cell_w, cell_h), (512, 512))
        self.assertEqual(len(crops), 16)
        self.assertEqual(crops[0], (0, 0, 512, 512))
        self.assertEqual(crops[-1], (1536, 1536, 512, 512))
        self.assertEqual(warnings, [])

    def test_remainder_warning(self) -> None:
        _, _, crops, warnings = split_frames.compute_layout(100, 100, 3, 3)
        self.assertEqual(len(crops), 9)
        self.assertTrue(any("unused horizontally" in warning for warning in warnings))
        self.assertTrue(any("unused vertically" in warning for warning in warnings))


class ResolveFramesDirTest(unittest.TestCase):
    def test_default(self) -> None:
        image = Path("image/effects/fire_sheet.png")
        out = split_frames.resolve_frames_dir("", image)
        self.assertEqual(out, Path("image/effects/image-sprite-sheet-split/fire_sheet"))

    def test_custom_dir(self) -> None:
        image = Path("image/effects/fire_sheet.png")
        out = split_frames.resolve_frames_dir("image/effects/out/", image)
        self.assertEqual(out, Path("image/effects/out/fire_sheet"))


class SplitFramesCliTest(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(PYTHON_BIN), str(SPLIT_SCRIPT), *args],
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
        self.assertIn("--grid", result.stdout)
        self.assertNotIn("--trim", result.stdout)
        self.assertNotIn("--cols", result.stdout)

    def test_image_not_found(self) -> None:
        result = self.run_cli("--image", "missing-no-such-file.png", "--grid", "4x4")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Image file not found", result.stderr)

    def test_directory_not_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("--image", tmp, "--grid", "4x4")
            self.assertEqual(result.returncode, 1)
            self.assertIn("Not an image file", result.stderr)

    def test_missing_grid(self) -> None:
        if not TANK1.is_file():
            self.skipTest(f"sample image missing: {TANK1}")
        result = self.run_cli("--image", str(TANK1))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("--grid", result.stderr + result.stdout)

    def test_split_1x1(self) -> None:
        if not TANK1.is_file():
            self.skipTest(f"sample image missing: {TANK1}")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / TANK1.name
            src.write_bytes(TANK1.read_bytes())

            result = self.run_cli("--image", str(src), "--grid", "1x1")
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

            out_dir = root / split_frames.DEFAULT_OUTPUT_SUBDIR / src.stem
            frame = out_dir / f"{src.stem}_001.png"
            self.assertTrue(frame.is_file())
            self.assertGreater(frame.stat().st_size, 0)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
