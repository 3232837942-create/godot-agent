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
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import normalize  # noqa: E402
from common.dependency_utils import find_repo_root, resolve_tool_bin  # noqa: E402

REPO_ROOT = find_repo_root(Path(__file__))
assert REPO_ROOT is not None
PYTHON_BIN = resolve_tool_bin(REPO_ROOT, "python")
NORMALIZE_SCRIPT = SCRIPT_DIR / "normalize.py"


class CleanSegmentTest(unittest.TestCase):
    def test_drops_long_pure_digit_ids(self) -> None:
        self.assertIsNone(normalize.clean_segment("81135"))
        self.assertIsNone(normalize.clean_segment("38126"))

    def test_keeps_short_pure_digit_variants(self) -> None:
        self.assertEqual(normalize.clean_segment("1"), "1")
        self.assertEqual(normalize.clean_segment("02"), "02")
        self.assertEqual(normalize.clean_segment("001"), "001")

    def test_strips_leading_digits_from_mixed_segments(self) -> None:
        self.assertEqual(normalize.clean_segment("001Hero"), "Hero")

    def test_strips_trailing_digits_from_mixed_segments(self) -> None:
        self.assertEqual(normalize.clean_segment("Attack02"), "Attack")
        self.assertEqual(normalize.clean_segment("foisal72"), "foisal")


class NormalizeStemTest(unittest.TestCase):
    def test_splits_on_common_separators(self) -> None:
        self.assertEqual(normalize.normalize_stem("001_Hero_Attack_02", [], False), "001_Hero_Attack_02")

    def test_converts_hyphens_to_underscores(self) -> None:
        self.assertEqual(normalize.normalize_stem("sfx-button-click", [], False), "sfx_button_click")

    def test_drops_long_digit_asset_ids(self) -> None:
        self.assertEqual(
            normalize.normalize_stem("freesound_community-shoot-1-81135", [], False),
            "freesound_community_shoot_1",
        )

    def test_keeps_short_digit_segments(self) -> None:
        self.assertEqual(normalize.normalize_stem("UI 12 Panel Open", [], False), "UI_12_Panel_Open")

    def test_strip_removes_substrings_from_segments(self) -> None:
        self.assertEqual(normalize.normalize_stem("SFX_001_button", ["SFX"], False), "001_button")

    def test_strip_case_insensitive(self) -> None:
        self.assertEqual(normalize.normalize_stem("sfx_button", ["SFX"], True), "button")

    def test_empty_after_cleaning_returns_empty_string(self) -> None:
        self.assertEqual(normalize.normalize_stem("81135", [], False), "")


class TargetNameTest(unittest.TestCase):
    def test_preserves_extension(self) -> None:
        path = Path("001-Hero-Attack-02.wav")
        self.assertEqual(normalize.target_name(path, [], False), "001_Hero_Attack_02.wav")

    def test_returns_none_when_unchanged(self) -> None:
        path = Path("sfx_button_click.mp3")
        self.assertIsNone(normalize.target_name(path, [], False))


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
        self.assertIn("--dry-run", result.stdout)
        self.assertIn("--strip", result.stdout)

    def test_path_not_found(self) -> None:
        result = self.run_cli("missing-no-such-path")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Path not found", result.stderr)

    def test_dry_run_renames(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "001-Hero-Attack-02.wav"
            src.write_bytes(b"x")

            result = self.run_cli(str(root), "--dry-run")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("001-Hero-Attack-02.wav", result.stdout)
            self.assertIn("001_Hero_Attack_02.wav", result.stdout)
            self.assertTrue(src.is_file())
            self.assertFalse((root / "001_Hero_Attack_02.wav").exists())

    def test_in_place_rename(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "UI 12 Panel Open.png"
            src.write_bytes(b"x")

            result = self.run_cli(str(root))
            self.assertEqual(result.returncode, 0, result.stderr)
            dst = root / "UI_12_Panel_Open.png"
            self.assertFalse(src.exists())
            self.assertTrue(dst.is_file())

    def test_output_dir_copy(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "SFX_001_button.wav"
            src.write_bytes(b"x")
            out_dir = root / "normalized"

            result = self.run_cli(str(root), "-o", str(out_dir), "--strip", "SFX")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(src.is_file())
            self.assertTrue((out_dir / "001_button.wav").is_file())

    def test_collision_aborts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Hero-Attack.wav").write_bytes(b"a")
            (root / "Hero.Attack.wav").write_bytes(b"b")

            result = self.run_cli(str(root))
            self.assertEqual(result.returncode, 1)
            self.assertIn("Name collision", result.stderr)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
