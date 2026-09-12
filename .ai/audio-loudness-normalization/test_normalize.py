#!/usr/bin/env python3
"""Tests for normalize.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import normalize  # noqa: E402
from common.cli_tools import resolve_ffmpeg  # noqa: E402
from common.dependency_utils import find_repo_root, resolve_tool_bin  # noqa: E402

REPO_ROOT = find_repo_root(Path(__file__))
assert REPO_ROOT is not None
PYTHON_BIN = resolve_tool_bin(REPO_ROOT, "python")
NORMALIZE_SCRIPT = SCRIPT_DIR / "normalize.py"
SAMPLE_AUDIO = REPO_ROOT / ".ai/test/audio/han_loud.wav"


class BuildLoudnormFilterTest(unittest.TestCase):
    def test_builds_two_pass_filter(self) -> None:
        measured = {
            "input_i": "-20.0",
            "input_lra": "5.0",
            "input_tp": "-3.0",
            "input_thresh": "-30.0",
            "target_offset": "6.0",
        }
        self.assertEqual(
            normalize.build_loudnorm_filter(-14.0, measured),
            (
                "loudnorm=I=-14.0:TP=-1.5:LRA=11"
                ":measured_I=-20.0"
                ":measured_LRA=5.0"
                ":measured_TP=-3.0"
                ":measured_thresh=-30.0"
                ":offset=6.0"
                ":linear=true"
            ),
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
        self.assertIn("--audio", result.stdout)
        self.assertIn("--target-lufs", result.stdout)
        self.assertIn("-output", result.stdout)

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

    def test_writes_normalized_wav(self) -> None:
        if not SAMPLE_AUDIO.is_file():
            self.skipTest("sample audio missing")

        with tempfile.TemporaryDirectory() as tmp:
            out_file = Path(tmp) / "test.wav"
            result = self.run_cli(
                "--audio",
                str(SAMPLE_AUDIO),
                "-output",
                str(out_file),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out_file.is_file())
            self.assertGreater(out_file.stat().st_size, 0)

    def test_output_matches_target_lufs(self) -> None:
        if not SAMPLE_AUDIO.is_file():
            self.skipTest("sample audio missing")

        target_lufs = normalize.DEFAULT_TARGET_LUFS
        ffmpeg = resolve_ffmpeg(NORMALIZE_SCRIPT)

        source_measured = normalize.measure_loudnorm(ffmpeg, SAMPLE_AUDIO, target_lufs)
        source_lufs = float(source_measured["input_i"])
        source_tp = float(source_measured["input_tp"])

        with tempfile.TemporaryDirectory() as tmp:
            out_file = Path(tmp) / "test.wav"
            result = self.run_cli(
                "--audio",
                str(SAMPLE_AUDIO),
                "-output",
                str(out_file),
            )
            self.assertEqual(result.returncode, 0, result.stderr)

            output_measured = normalize.measure_loudnorm(ffmpeg, out_file, target_lufs)
            output_lufs = float(output_measured["input_i"])
            output_tp = float(output_measured["input_tp"])

            print(
                f"\n[{SAMPLE_AUDIO.name}] loudness before: {source_lufs:.2f} LUFS, "
                f"true peak {source_tp:.2f} dBTP",
                flush=True,
            )
            print(
                f"[normalized] loudness after:  {output_lufs:.2f} LUFS, "
                f"true peak {output_tp:.2f} dBTP "
                f"(target {target_lufs:g} LUFS)",
                flush=True,
            )

            self.assertAlmostEqual(
                output_lufs,
                target_lufs,
                delta=1.0,
                msg=(
                    f"output loudness {output_lufs} LUFS, "
                    f"expected {target_lufs} ± 1.0"
                ),
            )

            self.assertLessEqual(
                output_tp,
                normalize.DEFAULT_TRUE_PEAK + 0.1,
                msg=(
                    f"output true peak {output_tp} dBTP exceeds limit "
                    f"{normalize.DEFAULT_TRUE_PEAK} dBTP"
                ),
            )

    def test_default_output_path(self) -> None:
        if not SAMPLE_AUDIO.is_file():
            self.skipTest("sample audio missing")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wav = root / SAMPLE_AUDIO.name
            wav.write_bytes(SAMPLE_AUDIO.read_bytes())
            result = self.run_cli("--audio", str(wav))
            self.assertEqual(result.returncode, 0, result.stderr)
            out_file = root / "audio-loudness-normalization" / SAMPLE_AUDIO.name
            self.assertTrue(out_file.is_file())
            self.assertGreater(out_file.stat().st_size, 0)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
