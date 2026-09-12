#!/usr/bin/env python3
"""Tests for standardize.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

AI_ROOT = SCRIPT_DIR.parent
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from common.audio_utils import audio_output_name  # noqa: E402
from common.cli_tools import resolve_ffmpeg, resolve_ffprobe  # noqa: E402
import standardize  # noqa: E402
from common.dependency_utils import find_repo_root, resolve_tool_bin  # noqa: E402

REPO_ROOT = find_repo_root(Path(__file__))
assert REPO_ROOT is not None
PYTHON_BIN = resolve_tool_bin(REPO_ROOT, "python")
STANDARDIZE_SCRIPT = SCRIPT_DIR / "standardize.py"
SAMPLE_AUDIO = REPO_ROOT / ".ai/test/audio/han.wav"


class SampleRateRuleTest(unittest.TestCase):
    def test_uses_44100_at_or_below_threshold(self) -> None:
        self.assertEqual(standardize.resolve_output_sample_rate(44100), 44100)
        self.assertEqual(standardize.resolve_output_sample_rate(22050), 44100)
        self.assertEqual(standardize.resolve_output_sample_rate(None), 44100)

    def test_uses_48000_above_threshold(self) -> None:
        self.assertEqual(standardize.resolve_output_sample_rate(48000), 48000)
        self.assertEqual(standardize.resolve_output_sample_rate(96000), 48000)

    def test_describes_resample_plan(self) -> None:
        self.assertEqual(
            standardize.describe_output_format(96000, 48000),
            "48000 Hz (from 96000 Hz), 16-bit PCM WAV",
        )
        self.assertEqual(
            standardize.describe_output_format(44100, 44100),
            "44100 Hz (preserved), 16-bit PCM WAV",
        )

    def test_output_name_uses_wav_suffix(self) -> None:
        self.assertEqual(
            audio_output_name(Path("tank_move.mp3"), suffix=".wav"),
            "tank_move.wav",
        )


class StandardizeCliTest(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(PYTHON_BIN), str(STANDARDIZE_SCRIPT), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(REPO_ROOT),
        )

    def assert_standardized_sample_rate(self, source: Path, output: Path) -> None:
        ffmpeg = resolve_ffmpeg(STANDARDIZE_SCRIPT)
        ffprobe = resolve_ffprobe(ffmpeg)
        source_rate = standardize.probe_sample_rate(ffprobe, source)
        expected_rate = standardize.resolve_output_sample_rate(source_rate)
        output_rate = standardize.probe_sample_rate(ffprobe, output)

        source_label = "unknown Hz" if source_rate is None else f"{source_rate} Hz"
        output_label = "unknown Hz" if output_rate is None else f"{output_rate} Hz"
        print(
            f"\n[{source.name}] sample rate before: {source_label}",
            flush=True,
        )
        print(
            f"[standardized] sample rate after:  {output_label} "
            f"(target {expected_rate} Hz)",
            flush=True,
        )

        self.assertIsNotNone(output_rate, f"Could not read sample rate from: {output}")
        self.assertEqual(
            output_rate,
            expected_rate,
            f"expected {expected_rate} Hz (from source {source_rate} Hz), got {output_rate} Hz",
        )

    def test_help(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--audio", result.stdout)
        self.assertIn("--output", result.stdout)

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

    def test_writes_standardized_wav(self) -> None:
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
            self.assert_standardized_sample_rate(SAMPLE_AUDIO, out_file)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
