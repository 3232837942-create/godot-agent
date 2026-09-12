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

REPO_ROOT = find_repo_root(Path(__file__))
assert REPO_ROOT is not None
PYTHON_BIN = resolve_tool_bin(REPO_ROOT, "python")
CONVERT_SCRIPT = SCRIPT_DIR / "convert.py"
SAMPLE_VIDEO = REPO_ROOT / ".ai/test/video/opening.mp4"


class ConvertLogicTest(unittest.TestCase):
    def test_stream_copy_only_for_theora_vorbis_ogv(self) -> None:
        probe = {
            "video": {"codec": "theora", "width": 640, "height": 360},
            "audio": {"codec": "vorbis", "sample_rate": 44100, "channels": 2},
        }
        path = Path("clip.ogv")
        self.assertTrue(convert.can_stream_copy(path, probe, None))
        self.assertFalse(convert.can_stream_copy(path, probe, 48000))
        self.assertFalse(convert.can_stream_copy(Path("clip.mp4"), probe, None))

    def test_is_lossless_source(self) -> None:
        lossy = {
            "video": {"codec": "h264"},
            "audio": {"codec": "aac"},
        }
        lossless = {
            "video": {"codec": "ffv1"},
            "audio": {"codec": "flac"},
        }
        self.assertFalse(convert.is_lossless_source(lossy))
        self.assertTrue(convert.is_lossless_source(lossless))

    def test_describe_lossless_pipeline(self) -> None:
        probe = {
            "video": {"codec": "h264", "width": 1280, "height": 720},
            "audio": {"codec": "aac", "sample_rate": 44100, "channels": 2},
        }
        text = convert.describe_file_plan(probe, None, False, "via intro.mkv")
        self.assertIn("FFV1+FLAC", text)
        self.assertIn("Theora q=10", text)
        self.assertIn("2 ch", text)


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

    def assert_theora_vorbis(self, source: Path, output: Path) -> None:
        ffmpeg = resolve_ffmpeg(CONVERT_SCRIPT)
        ffprobe = resolve_ffprobe(ffmpeg)
        source_probe = convert.probe_streams(ffprobe, source)
        output_probe = convert.probe_streams(ffprobe, output)

        self.assertTrue(source_probe.get("video"), f"Could not probe source video: {source}")
        self.assertTrue(output_probe.get("video"), f"Could not probe output video: {output}")
        self.assertEqual(output.suffix.lower(), ".ogv")
        self.assertEqual(output_probe["video"].get("codec"), "theora")
        if source_probe.get("audio"):
            self.assertEqual(output_probe["audio"].get("codec"), "vorbis")
            self.assertEqual(
                output_probe["audio"].get("sample_rate"),
                source_probe["audio"].get("sample_rate"),
            )
            self.assertEqual(
                output_probe["audio"].get("channels"),
                source_probe["audio"].get("channels"),
            )

    def test_help(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--video", result.stdout)
        self.assertIn("--output", result.stdout)
        self.assertNotIn("--no-lossless", result.stdout)
        self.assertNotIn("--fast", result.stdout)
        self.assertNotIn("-vq", result.stdout)
        self.assertNotIn("-aq", result.stdout)
        self.assertNotIn("--recurse", result.stdout)
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

    def test_convert_single_file(self) -> None:
        sample = self.require_sample_video()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            video = root / sample.name
            video.write_bytes(sample.read_bytes())
            result = self.run_cli("--video", str(video))
            self.assertEqual(result.returncode, 0, result.stderr)
            out = root / convert.DEFAULT_OUTPUT_SUBDIR / sample.with_suffix(".ogv").name
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size, 0)
            self.assert_theora_vorbis(video, out)

    def test_custom_output_file(self) -> None:
        sample = self.require_sample_video()

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "opening-custom.ogv"
            result = self.run_cli("--video", str(sample), "--output", str(out))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size, 0)
            self.assert_theora_vorbis(sample, out)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
