#!/usr/bin/env python3
"""Tests for convert.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import convert  # noqa: E402
from common.cli_tools import resolve_ffmpeg, resolve_ffprobe  # noqa: E402
from common.dependency_utils import find_repo_root, resolve_tool_bin  # noqa: E402

REPO_ROOT = find_repo_root(Path(__file__))
assert REPO_ROOT is not None
PYTHON_BIN = resolve_tool_bin(REPO_ROOT, "python")
CONVERT_SCRIPT = SCRIPT_DIR / "convert.py"
SAMPLE_AUDIO = REPO_ROOT / ".ai/test/audio/han.wav"


class ConvertLogicTest(unittest.TestCase):
    def test_stream_copy_only_for_vorbis_ogg(self) -> None:
        probe = {"codec": "vorbis", "sample_rate": 44100, "channels": 2}
        path = Path("clip.ogg")
        self.assertTrue(convert.can_stream_copy(path, probe, None))
        self.assertFalse(convert.can_stream_copy(path, probe, 1))
        self.assertFalse(convert.can_stream_copy(Path("clip.wav"), probe, None))

    def test_describe_stream_copy(self) -> None:
        probe = {"codec": "vorbis", "sample_rate": 44100, "channels": 2}
        text = convert.describe_file_plan(probe, 6, None, True)
        self.assertIn("stream copy", text)
        self.assertIn("44100 Hz", text)


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

    def assert_ogg_vorbis(self, source: Path, output: Path) -> None:
        ffmpeg = resolve_ffmpeg(CONVERT_SCRIPT)
        ffprobe = resolve_ffprobe(ffmpeg)
        source_probe = convert.probe_audio(ffprobe, source)
        output_probe = convert.probe_audio(ffprobe, output)

        self.assertTrue(source_probe, f"Could not probe source audio: {source}")
        self.assertTrue(output_probe, f"Could not probe output audio: {output}")
        self.assertEqual(output.suffix.lower(), ".ogg")
        self.assertEqual(
            output_probe.get("codec"),
            "vorbis",
            f"expected Vorbis codec, got {output_probe.get('codec')!r}",
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

    def test_help(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--audio", result.stdout)
        self.assertIn("--output", result.stdout)
        self.assertNotIn("--output-dir", result.stdout)
        self.assertNotIn("--recurse", result.stdout)

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

    def test_converts_wav_to_ogg(self) -> None:
        if not SAMPLE_AUDIO.is_file():
            self.skipTest("sample audio missing")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            wav = root / SAMPLE_AUDIO.name
            wav.write_bytes(SAMPLE_AUDIO.read_bytes())
            result = self.run_cli("--audio", str(wav))
            self.assertEqual(result.returncode, 0, result.stderr)
            out = root / "audio-to-ogg" / "han.ogg"
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size, 0)
            self.assert_ogg_vorbis(wav, out)

    def test_custom_output_file(self) -> None:
        if not SAMPLE_AUDIO.is_file():
            self.skipTest("sample audio missing")

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "test.ogg"
            result = self.run_cli(
                "--audio",
                str(SAMPLE_AUDIO),
                "--output",
                str(out),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size, 0)
            self.assert_ogg_vorbis(SAMPLE_AUDIO, out)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
