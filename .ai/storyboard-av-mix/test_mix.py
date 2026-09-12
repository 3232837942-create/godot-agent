#!/usr/bin/env python3
"""Tests for mix.py."""

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

import mix  # noqa: E402
from common.dependency_utils import find_repo_root, resolve_tool_bin  # noqa: E402

REPO_ROOT = find_repo_root(Path(__file__))
assert REPO_ROOT is not None
PYTHON_BIN = resolve_tool_bin(REPO_ROOT, "python")
MIX_SCRIPT = SCRIPT_DIR / "mix.py"


class ListByStemTest(unittest.TestCase):
    def test_lists_matching_extensions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "01.mp4").write_bytes(b"x")
            (root / "02.mkv").write_bytes(b"x")
            (root / "notes.txt").write_bytes(b"x")
            found = mix.list_by_stem(root, mix.VIDEO_EXTENSIONS)
            self.assertEqual(sorted(found.keys()), ["01", "02"])
            self.assertEqual(found["01"].suffix, ".mp4")

    def test_missing_folder_returns_empty(self) -> None:
        self.assertEqual(mix.list_by_stem(Path("/no-such-folder"), mix.VIDEO_EXTENSIONS), {})


class BuildJobsTest(unittest.TestCase):
    def test_builds_bilingual_jobs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "Video").mkdir()
            (root / "Chinese").mkdir()
            (root / "English").mkdir()
            (root / "Video" / "01.mp4").write_bytes(b"v")
            (root / "Chinese" / "01.wav").write_bytes(b"a")
            (root / "English" / "01.wav").write_bytes(b"a")

            jobs = mix.build_jobs(root, "both")
            self.assertEqual(len(jobs), 2)
            langs = {job.lang for job in jobs}
            self.assertEqual(langs, {"chinese", "english"})
            self.assertEqual(jobs[0].output.parent.name, "Video-Chinese")

class VideoEncodeArgsTest(unittest.TestCase):
    def test_hevc_main10_preserves_hdr_params(self) -> None:
        probe = mix.VideoProbe(
            codec_name="hevc",
            profile="Main 10",
            pix_fmt="yuv420p10le",
            color_range="tv",
            color_space="bt2020nc",
            color_transfer="smpte2084",
            color_primaries="bt2020",
            bit_rate=40_000_000,
            mastering={
                "red_x": "34000/50000",
                "red_y": "16000/50000",
                "green_x": "13250/50000",
                "green_y": "34500/50000",
                "blue_x": "7500/50000",
                "blue_y": "3000/50000",
                "white_point_x": "15635/50000",
                "white_point_y": "16450/50000",
                "max_luminance": "10000000/10000",
                "min_luminance": "50/10000",
            },
            cll={"max_content": 1000, "max_average": 400},
        )
        args = mix.video_encode_args(probe)
        joined = " ".join(args)
        self.assertIn("libx265", joined)
        self.assertIn("main10", joined)
        self.assertIn("master-display=", joined)
        self.assertIn("max-cll=1000,400", joined)
        self.assertIn("-b:v 40000000", joined)
        self.assertIn("-preset slow", joined)

    def test_h264_fallback(self) -> None:
        probe = mix.VideoProbe(
            codec_name="h264",
            profile="High",
            pix_fmt="yuv420p",
            color_range="",
            color_space="",
            color_transfer="",
            color_primaries="",
            bit_rate=None,
        )
        args = mix.video_encode_args(probe)
        joined = " ".join(args)
        self.assertIn("-c:v libx264", joined)
        self.assertIn("-crf 14", joined)
        self.assertIn("-preset slow", joined)


class MasterDisplayTest(unittest.TestCase):
    def test_formats_x265_master_display(self) -> None:
        text = mix._master_display_x265(
            {
                "red_x": "34000/50000",
                "red_y": "16000/50000",
                "green_x": "13250/50000",
                "green_y": "34500/50000",
                "blue_x": "7500/50000",
                "blue_y": "3000/50000",
                "white_point_x": "15635/50000",
                "white_point_y": "16450/50000",
                "max_luminance": "10000000/10000",
                "min_luminance": "50/10000",
            }
        )
        self.assertIn("G(13250,34500)", text)
        self.assertIn("WP(15635,16450)", text)


class MixCliTest(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(PYTHON_BIN), str(MIX_SCRIPT), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(REPO_ROOT),
        )

    def test_help(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--lang", result.stdout)

    def test_missing_root(self) -> None:
        result = self.run_cli()
        self.assertNotEqual(result.returncode, 0)

    def test_root_not_found(self) -> None:
        result = self.run_cli("missing-no-such-root")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Root not found", result.stderr)

    def test_missing_video_folder(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli(tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn("Missing required folder", result.stderr)


if __name__ == "__main__":
    unittest.main()
