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
SAMPLE_VIDEO = REPO_ROOT / ".ai/test/video/opening.mp4"


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

    def require_sample_video(self) -> Path:
        if not SAMPLE_VIDEO.is_file():
            self.skipTest("sample video missing")
        return SAMPLE_VIDEO

    def assert_pcm_wav(self, source: Path, output: Path, track: int = 0) -> None:
        ffmpeg = resolve_ffmpeg(CONVERT_SCRIPT)
        ffprobe = resolve_ffprobe(ffmpeg)
        source_probe = wav_utils.probe_video_audio_track(ffprobe, source, track)
        output_probe = wav_utils.probe_audio_file(ffprobe, output)

        self.assertTrue(source_probe, f"Could not probe source video audio: {source}")
        self.assertTrue(output_probe, f"Could not probe output audio: {output}")
        self.assertIn(output_probe.get("codec", ""), wav_utils.PCM_STREAM_CODECS)
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
        self.assertEqual(
            output_probe.get("codec"),
            expected_codec,
            f"expected converted codec {expected_codec!r}, got {output_probe.get('codec')!r}",
        )

    def test_help(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--video", result.stdout)
        self.assertIn("--output", result.stdout)
        self.assertNotIn("--standardize", result.stdout)
        self.assertNotIn("--mono", result.stdout)
        self.assertNotIn("--stereo", result.stdout)
        self.assertNotIn("--recurse", result.stdout)
        self.assertNotIn("--sample-rate", result.stdout)
        self.assertNotIn("--overwrite", result.stdout)
        self.assertNotIn("--dry-run", result.stdout)
        self.assertNotIn("--output-dir", result.stdout)

    def test_missing_video(self) -> None:
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)

    def test_video_not_found(self) -> None:
        result = self.run_cli("--video", "missing-no-such.mp4")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Video file not found", result.stderr)

    def test_rejects_directory(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("--video", tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn("directories are not supported", result.stderr)

    def test_converts_opening_mp4(self) -> None:
        sample = self.require_sample_video()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / sample.name
            video.write_bytes(sample.read_bytes())
            result = self.run_cli("--video", str(video))
            self.assertEqual(result.returncode, 0, result.stderr)
            out = root / convert.DEFAULT_OUTPUT_SUBDIR / sample.with_suffix(".wav").name
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size, 0)
            self.assert_pcm_wav(video, out)

    def test_custom_output_file(self) -> None:
        sample = self.require_sample_video()

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "opening-custom.wav"
            result = self.run_cli("--video", str(sample), "--output", str(out))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size, 0)
            self.assert_pcm_wav(sample, out)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
