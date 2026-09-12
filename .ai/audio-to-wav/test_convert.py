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
from common.cli_tools import resolve_ffmpeg, resolve_ffprobe  # noqa: E402
from common.dependency_utils import find_repo_root, resolve_tool_bin  # noqa: E402
from common import wav_utils  # noqa: E402

REPO_ROOT = find_repo_root(Path(__file__))
assert REPO_ROOT is not None
PYTHON_BIN = resolve_tool_bin(REPO_ROOT, "python")
CONVERT_SCRIPT = SCRIPT_DIR / "convert.py"
SAMPLE_AUDIO = REPO_ROOT / ".ai/test/audio/han.wav"


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

    def assert_pcm_wav(self, source: Path, output: Path) -> None:
        ffmpeg = resolve_ffmpeg(CONVERT_SCRIPT)
        ffprobe = resolve_ffprobe(ffmpeg)
        source_probe = wav_utils.probe_audio_file(ffprobe, source)
        output_probe = wav_utils.probe_audio_file(ffprobe, output)

        self.assertTrue(source_probe, f"Could not probe source audio: {source}")
        self.assertTrue(output_probe, f"Could not probe output audio: {output}")
        self.assertEqual(output.suffix.lower(), ".wav")

        output_codec = output_probe.get("codec", "")
        self.assertIn(
            output_codec,
            wav_utils.PCM_STREAM_CODECS,
            f"expected PCM WAV codec, got {output_codec!r}",
        )
        self.assertEqual(
            output_probe.get("sample_rate"),
            source_probe.get("sample_rate"),
            "output sample rate should match source",
        )
        self.assertEqual(
            output_probe.get("channels"),
            source_probe.get("channels"),
            "output channel count should match source",
        )

        _, expected_codec = wav_utils.resolve_bit_depth(source_probe, None)
        if wav_utils.can_pcm_stream_copy(
            source_probe,
            None,
            require_wav_container=True,
            source_path=source,
        ):
            self.assertEqual(
                output_codec,
                source_probe.get("codec"),
                "stream copy should preserve source PCM codec",
            )
        else:
            self.assertEqual(
                output_codec,
                expected_codec,
                f"expected converted codec {expected_codec!r}, got {output_codec!r}",
            )

    def test_help(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--audio", result.stdout)
        self.assertIn("--output", result.stdout)
        self.assertNotIn("--output-dir", result.stdout)
        self.assertNotIn("--recurse", result.stdout)
        self.assertNotIn("--sample-rate", result.stdout)
        self.assertNotIn("--standardize", result.stdout)
        self.assertNotIn("--mono", result.stdout)
        self.assertNotIn("--stereo", result.stdout)

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

    def test_converts_wav_to_wav(self) -> None:
        if not SAMPLE_AUDIO.is_file():
            self.skipTest("sample audio missing")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wav = root / SAMPLE_AUDIO.name
            wav.write_bytes(SAMPLE_AUDIO.read_bytes())
            result = self.run_cli("--audio", str(wav))
            self.assertEqual(result.returncode, 0, result.stderr)
            out = root / convert.DEFAULT_OUTPUT_SUBDIR / "han.wav"
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size, 0)
            self.assert_pcm_wav(wav, out)

    def test_custom_output_file(self) -> None:
        if not SAMPLE_AUDIO.is_file():
            self.skipTest("sample audio missing")

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "test.wav"
            result = self.run_cli(
                "--audio",
                str(SAMPLE_AUDIO),
                "--output",
                str(out),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size, 0)
            self.assert_pcm_wav(SAMPLE_AUDIO, out)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
