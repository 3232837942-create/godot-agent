#!/usr/bin/env python3
"""Tests for adjust.py."""

from __future__ import annotations

import math
import struct
import subprocess
import sys
import tempfile
import unittest
import wave
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import adjust  # noqa: E402
from common.audio_utils import get_duration  # noqa: E402
from common.cli_tools import resolve_ffmpeg, resolve_ffprobe  # noqa: E402
from common.dependency_utils import find_repo_root, resolve_tool_bin  # noqa: E402

REPO_ROOT = find_repo_root(Path(__file__))
assert REPO_ROOT is not None
PYTHON_BIN = resolve_tool_bin(REPO_ROOT, "python")
ADJUST_SCRIPT = SCRIPT_DIR / "adjust.py"
SAMPLE_AUDIO = REPO_ROOT / ".ai/test/audio/han.wav"
TEST_VOLUME_DB = -6.0
VOLUME_TOLERANCE_DB = 0.5


def wav_rms(path: Path) -> float:
    with wave.open(str(path), "rb") as wav_file:
        if wav_file.getsampwidth() != 2:
            raise ValueError(f"unsupported sample width for RMS: {path}")
        frames = wav_file.readframes(wav_file.getnframes())

    if not frames:
        return 0.0

    samples = struct.unpack(f"<{len(frames) // 2}h", frames)
    sum_sq = sum((sample / 32768.0) ** 2 for sample in samples)
    return math.sqrt(sum_sq / len(samples))


class AdjustFilterTest(unittest.TestCase):
    def test_builds_decibel_filter(self) -> None:
        self.assertEqual(adjust.build_filter(-6), "volume=-6.000000dB")

    def test_builds_positive_decibel_filter(self) -> None:
        self.assertEqual(adjust.build_filter(3), "volume=3.000000dB")


class AdjustCliTest(unittest.TestCase):
    def format_cli_command(self, *args: str) -> str:
        def display(part: str) -> str:
            path = Path(part)
            if not path.is_absolute():
                return part
            try:
                return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
            except ValueError:
                return str(path)

        parts = [
            display(str(PYTHON_BIN)),
            display(str(ADJUST_SCRIPT)),
            *[display(arg) for arg in args],
        ]
        return " ".join(parts)

    def run_cli(self, *args: str, print_command: bool = False) -> subprocess.CompletedProcess[str]:
        if print_command:
            print(
                f"command: {self.format_cli_command(*args)}",
                file=sys.stderr,
                flush=True,
            )
        return subprocess.run(
            [str(PYTHON_BIN), str(ADJUST_SCRIPT), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(REPO_ROOT),
        )

    def assert_adjusted_wav(
        self, source: Path, output: Path, volume_db: float
    ) -> None:
        self.assertEqual(output.suffix.lower(), ".wav")

        with wave.open(str(source), "rb") as src_wav, wave.open(str(output), "rb") as out_wav:
            self.assertEqual(out_wav.getnchannels(), src_wav.getnchannels())
            self.assertEqual(out_wav.getframerate(), src_wav.getframerate())
            self.assertEqual(out_wav.getsampwidth(), src_wav.getsampwidth())
            self.assertGreater(out_wav.getnframes(), 0)

        ffmpeg = resolve_ffmpeg(ADJUST_SCRIPT)
        ffprobe = resolve_ffprobe(ffmpeg)
        source_duration = get_duration(ffprobe, source)
        output_duration = get_duration(ffprobe, output)
        source_rms = wav_rms(source)
        output_rms = wav_rms(output)
        self.assertGreater(source_rms, 0.0, "source audio is silent; cannot verify volume")

        measured_db = 20.0 * math.log10(output_rms / source_rms)
        print(
            f"\n[{source.name}] loudness before: {source_rms:.6f} RMS",
            flush=True,
        )
        print(
            f"[adjusted] loudness after:  {output_rms:.6f} RMS "
            f"(target {volume_db:+.1f} dB, measured {measured_db:+.2f} dB)",
            flush=True,
        )
        self.assertAlmostEqual(
            output_duration,
            source_duration,
            places=2,
            msg="volume adjust should preserve duration",
        )
        self.assertAlmostEqual(
            measured_db,
            volume_db,
            delta=VOLUME_TOLERANCE_DB,
            msg=(
                f"expected {volume_db:+.1f} dB volume change, "
                f"measured {measured_db:+.2f} dB from RMS"
            ),
        )

    def test_help(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--audio", result.stdout)
        self.assertIn("--volume", result.stdout)
        self.assertIn("--output", result.stdout)
        self.assertNotIn("--linear", result.stdout)
        self.assertNotIn("--decibels", result.stdout)
        self.assertNotIn("--gain", result.stdout)
        self.assertNotIn("--output-dir", result.stdout)

    def test_missing_audio(self) -> None:
        result = self.run_cli("--volume", "-6")
        self.assertNotEqual(result.returncode, 0)

    def test_missing_volume(self) -> None:
        result = self.run_cli("--audio", "missing-no-such.wav")
        self.assertNotEqual(result.returncode, 0)

    def test_audio_not_found(self) -> None:
        result = self.run_cli("--audio", "missing-no-such.wav", "--volume", "-6")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Audio file not found", result.stderr)

    def test_rejects_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("--audio", tmp, "--volume", "-6")
            self.assertEqual(result.returncode, 1)
            self.assertIn("directories are not supported", result.stderr)

    def test_writes_adjusted_wav(self) -> None:
        if not SAMPLE_AUDIO.is_file():
            self.skipTest("sample audio missing")

        with tempfile.TemporaryDirectory() as tmp:
            out_file = Path(tmp) / "test.wav"
            result = self.run_cli(
                "--audio",
                str(SAMPLE_AUDIO),
                "--volume",
                str(TEST_VOLUME_DB),
                "--output",
                str(out_file),
                print_command=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out_file.is_file())
            self.assertGreater(out_file.stat().st_size, 0)
            self.assert_adjusted_wav(SAMPLE_AUDIO, out_file, TEST_VOLUME_DB)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
