#!/usr/bin/env python3
"""Tests for split.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import split  # noqa: E402
from common.audio_utils import get_duration  # noqa: E402
from common.cli_tools import resolve_ffmpeg, resolve_ffprobe  # noqa: E402
from common.dependency_utils import find_repo_root, resolve_tool_bin  # noqa: E402

REPO_ROOT = find_repo_root(Path(__file__))
assert REPO_ROOT is not None
PYTHON_BIN = resolve_tool_bin(REPO_ROOT, "python")
SPLIT_SCRIPT = SCRIPT_DIR / "split.py"
SAMPLE_AUDIO = REPO_ROOT / ".ai/test/audio/han.wav"
DURATION_TOLERANCE_SECONDS = 0.05


class SplitLogicTest(unittest.TestCase):
    def test_default_split_is_half(self) -> None:
        self.assertEqual(split.resolve_split_seconds(4.0, None, None), 2.0)

    def test_split_at_seconds(self) -> None:
        self.assertEqual(split.resolve_split_seconds(4.0, 1.25, None), 1.25)

    def test_split_at_percent(self) -> None:
        self.assertEqual(split.resolve_split_seconds(10.0, None, 25.0), 2.5)

    def test_rejects_split_at_start(self) -> None:
        with self.assertRaises(ValueError):
            split.resolve_split_seconds(4.0, 0.0, None)

    def test_rejects_split_at_or_after_end(self) -> None:
        with self.assertRaises(ValueError):
            split.resolve_split_seconds(4.0, 4.0, None)
        with self.assertRaises(ValueError):
            split.resolve_split_seconds(4.0, 5.0, None)

    def test_output_paths(self) -> None:
        source = Path("Audio/SFX/click.wav").resolve()
        out_dir = Path("Audio/SFX/audio-split")
        part1, part2 = split.output_paths(out_dir, source)
        self.assertEqual(part1.name, "click_part1.wav")
        self.assertEqual(part2.name, "click_part2.wav")
        self.assertEqual(part1.parent, out_dir)
        self.assertEqual(part2.parent, out_dir)


class SplitCliTest(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(PYTHON_BIN), str(SPLIT_SCRIPT), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(REPO_ROOT),
        )

    def assert_split_durations(
        self, source: Path, part1: Path, part2: Path
    ) -> None:
        ffmpeg = resolve_ffmpeg(SPLIT_SCRIPT)
        ffprobe = resolve_ffprobe(ffmpeg)
        source_duration = get_duration(ffprobe, source)
        part1_duration = get_duration(ffprobe, part1)
        part2_duration = get_duration(ffprobe, part2)
        total_duration = part1_duration + part2_duration
        print(
            f"\n[{source.name}] duration before: {source_duration:.3f}s",
            flush=True,
        )
        print(
            f"[split] duration after:  {part1_duration:.3f}s + {part2_duration:.3f}s "
            f"= {total_duration:.3f}s (target match source)",
            flush=True,
        )
        self.assertAlmostEqual(
            total_duration,
            source_duration,
            delta=DURATION_TOLERANCE_SECONDS,
            msg=(
                f"split parts total {total_duration:.3f}s != source "
                f"{source_duration:.3f}s"
            ),
        )

    def test_help(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--audio", result.stdout)
        self.assertIn("--split-at", result.stdout)
        self.assertIn("--percent", result.stdout)
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

    def test_splits_wav_at_half(self) -> None:
        if not SAMPLE_AUDIO.is_file():
            self.skipTest("sample audio missing")

        with tempfile.TemporaryDirectory() as tmp:
            out_dir = Path(tmp) / "out"
            part1 = out_dir / f"{SAMPLE_AUDIO.stem}_part1{SAMPLE_AUDIO.suffix}"
            part2 = out_dir / f"{SAMPLE_AUDIO.stem}_part2{SAMPLE_AUDIO.suffix}"
            result = self.run_cli(
                "--audio",
                str(SAMPLE_AUDIO),
                "--output",
                str(out_dir),
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(part1.is_file())
            self.assertTrue(part2.is_file())
            self.assertGreater(part1.stat().st_size, 0)
            self.assertGreater(part2.stat().st_size, 0)
            self.assert_split_durations(SAMPLE_AUDIO, part1, part2)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
