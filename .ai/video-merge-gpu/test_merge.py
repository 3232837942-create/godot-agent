#!/usr/bin/env python3
"""Tests for merge.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPT_DIR = Path(__file__).resolve().parent
AI_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

import merge  # noqa: E402
from common.dependency_utils import find_repo_root, resolve_tool_bin  # noqa: E402

REPO_ROOT = find_repo_root(Path(__file__))
assert REPO_ROOT is not None
PYTHON_BIN = resolve_tool_bin(REPO_ROOT, "python")
MERGE_SCRIPT = SCRIPT_DIR / "merge.py"


class MergeLogicTest(unittest.TestCase):
    def test_build_filter_complex_two_clips(self) -> None:
        files = [Path("a.mp4"), Path("b.mp4")]
        graph, _extra = merge.build_filter_complex(
            files, [10.0, 8.0], [True, True], ["fade"]
        )
        self.assertIn("xfade=transition=fade", graph)
        self.assertIn("acrossfade", graph)

    def test_default_output_path(self) -> None:
        folder = Path("/tmp/shots")
        out = merge.resolve_merge_output("", folder)
        self.assertEqual(out, folder / merge.DEFAULT_OUTPUT_SUBDIR / "shots.mp4")

    def test_select_gpu_encoder_exits_when_none(self) -> None:
        ffmpeg = Path("/fake/ffmpeg")
        with mock.patch.object(merge, "encoder_works", return_value=False):
            with self.assertRaises(SystemExit) as ctx:
                merge.select_gpu_encoder(ffmpeg)
            self.assertEqual(ctx.exception.code, 1)


class MergeCliTest(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(PYTHON_BIN), str(MERGE_SCRIPT), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(REPO_ROOT),
        )

    def test_help(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--folder", result.stdout)
        self.assertIn("--output", result.stdout)
        self.assertNotIn("--dry-run", result.stdout)
        self.assertNotIn("--overwrite", result.stdout)
        self.assertNotIn("--seed", result.stdout)

    def test_missing_folder(self) -> None:
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)

    def test_folder_not_found(self) -> None:
        result = self.run_cli("--folder", "missing-no-such-folder")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Folder not found", result.stderr)

    def test_rejects_file(self) -> None:
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        try:
            result = self.run_cli("--folder", str(tmp_path))
            self.assertEqual(result.returncode, 1)
            self.assertIn("Not a folder", result.stderr)
        finally:
            tmp_path.unlink(missing_ok=True)

    def test_empty_folder_without_gpu_probe(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("--folder", tmp)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("No supported video files", result.stdout)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
