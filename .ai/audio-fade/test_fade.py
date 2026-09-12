#!/usr/bin/env python3
"""Tests for fade.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import fade  # noqa: E402
from common.dependency_utils import find_repo_root, resolve_tool_bin  # noqa: E402

REPO_ROOT = find_repo_root(Path(__file__))
assert REPO_ROOT is not None
PYTHON_BIN = resolve_tool_bin(REPO_ROOT, "python")
FADE_SCRIPT = SCRIPT_DIR / "fade.py"
SAMPLE_AUDIO = REPO_ROOT / ".ai/test/audio/han.wav"


class FadeFilterTest(unittest.TestCase):
    def test_builds_fade_in_and_out(self) -> None:
        self.assertEqual(
            fade.build_filter(5.0, 1.0, 1.0, "tri", True, True),
            "afade=t=in:st=0:d=1.000000:curve=tri,"
            "afade=t=out:st=4.000000:d=1.000000:curve=tri",
        )

    def test_builds_fade_in_only(self) -> None:
        self.assertEqual(
            fade.build_filter(5.0, 0.1, 1.0, "exp", True, False),
            "afade=t=in:st=0:d=0.100000:curve=exp",
        )

    def test_rejects_combined_fades_at_clip_duration(self) -> None:
        with self.assertRaises(ValueError):
            fade.validate_fades(2.0, 1.0, 1.0, True, True)

    def test_rejects_disabled_fades(self) -> None:
        with self.assertRaises(ValueError):
            fade.build_filter(5.0, 1.0, 1.0, "tri", False, False)


class FadeCliTest(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(PYTHON_BIN), str(FADE_SCRIPT), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(REPO_ROOT),
        )

    def test_help(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--audio", result.stdout)
        self.assertIn("--fade-in", result.stdout)
        self.assertIn("--fade-out", result.stdout)

    def test_missing_audio(self) -> None:
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)

    def test_audio_not_found(self) -> None:
        result = self.run_cli("--audio", "missing-no-such.wav")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Audio file not found", result.stderr)

    def test_rejects_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("--audio", tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn("directories are not supported", result.stderr)

    def test_writes_faded_wav(self) -> None:
        if not SAMPLE_AUDIO.is_file():
            self.skipTest("sample audio missing")

        with tempfile.TemporaryDirectory() as tmp:
            out_file = Path(tmp) / "test.wav"
            result = self.run_cli(
                "--audio",
                str(SAMPLE_AUDIO),
                "--output",
                str(out_file),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out_file.is_file())
            self.assertGreater(out_file.stat().st_size, 0)

    def test_default_output_path(self) -> None:
        if not SAMPLE_AUDIO.is_file():
            self.skipTest("sample audio missing")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wav = root / SAMPLE_AUDIO.name
            wav.write_bytes(SAMPLE_AUDIO.read_bytes())
            result = self.run_cli("--audio", str(wav))
            self.assertEqual(result.returncode, 0, result.stderr)
            out_file = root / "audio-fade" / SAMPLE_AUDIO.name
            self.assertTrue(out_file.is_file())
            self.assertGreater(out_file.stat().st_size, 0)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
