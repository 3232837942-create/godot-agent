#!/usr/bin/env python3
"""Tests for trim.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import trim  # noqa: E402
from common.audio_utils import get_duration  # noqa: E402
from common.cli_tools import resolve_ffmpeg, resolve_ffprobe  # noqa: E402
from common.dependency_utils import find_repo_root, resolve_tool_bin  # noqa: E402

REPO_ROOT = find_repo_root(Path(__file__))
assert REPO_ROOT is not None
PYTHON_BIN = resolve_tool_bin(REPO_ROOT, "python")
TRIM_SCRIPT = SCRIPT_DIR / "trim.py"
SAMPLE_AUDIO = REPO_ROOT / ".ai/test/audio/han.wav"


class TrimFilterTest(unittest.TestCase):
    def test_builds_filter(self) -> None:
        self.assertEqual(
            trim.build_filter(-50),
            "areverse,silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB,"
            "areverse,silenceremove=start_periods=1:start_duration=0:start_threshold=-50dB",
        )

    def test_builds_custom_threshold(self) -> None:
        self.assertEqual(
            trim.build_filter(-45),
            "areverse,silenceremove=start_periods=1:start_duration=0:start_threshold=-45dB,"
            "areverse,silenceremove=start_periods=1:start_duration=0:start_threshold=-45dB",
        )


class TrimCliTest(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(PYTHON_BIN), str(TRIM_SCRIPT), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(REPO_ROOT),
        )

    def assert_trimmed_wav(self, source: Path, output: Path) -> None:
        self.assertEqual(output.suffix.lower(), ".wav")

        with wave.open(str(source), "rb") as src_wav, wave.open(str(output), "rb") as out_wav:
            self.assertEqual(out_wav.getnchannels(), src_wav.getnchannels())
            self.assertEqual(out_wav.getframerate(), src_wav.getframerate())
            self.assertEqual(out_wav.getsampwidth(), src_wav.getsampwidth())
            self.assertGreater(out_wav.getnframes(), 0)

        ffmpeg = resolve_ffmpeg(TRIM_SCRIPT)
        ffprobe = resolve_ffprobe(ffmpeg)
        source_duration = get_duration(ffprobe, source)
        output_duration = get_duration(ffprobe, output)
        trimmed_seconds = source_duration - output_duration
        print(
            f"\n[{source.name}] duration before: {source_duration:.3f}s",
            flush=True,
        )
        print(
            f"[trimmed] duration after:  {output_duration:.3f}s "
            f"(trimmed {trimmed_seconds:.3f}s)",
            flush=True,
        )
        self.assertGreater(output_duration, 0)
        self.assertLessEqual(
            output_duration,
            source_duration + 0.01,
            "trimmed audio should not be longer than source",
        )
        self.assertGreater(
            output_duration,
            source_duration * 0.8,
            "trimmed speech shorter than 80% of source; likely over-trimmed",
        )

    def test_help(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--audio", result.stdout)
        self.assertIn("--output", result.stdout)
        self.assertNotIn("--output-dir", result.stdout)
        self.assertNotIn("--no-start", result.stdout)
        self.assertNotIn("--no-end", result.stdout)

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

    def test_writes_trimmed_wav(self) -> None:
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
            self.assert_trimmed_wav(SAMPLE_AUDIO, out_file)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
