#!/usr/bin/env python3
"""Tests for wav_utils.py."""

from __future__ import annotations

import sys
import unittest
import unittest.mock
from pathlib import Path

COMMON_DIR = Path(__file__).resolve().parent
AI_ROOT = COMMON_DIR.parent
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from common import wav_utils  # noqa: E402


class WavUtilsTest(unittest.TestCase):
    def test_resolve_bit_depth_for_lossy(self) -> None:
        depth, codec = wav_utils.resolve_bit_depth({"codec": "mp3", "bits": 0}, None)
        self.assertEqual(depth, 32)
        self.assertEqual(codec, "pcm_f32le")

    def test_can_pcm_stream_copy_requires_wav_container_for_audio(self) -> None:
        probe = {"codec": "pcm_s16le", "sample_rate": 44100, "bits": 16, "channels": 1}
        wav = Path("clip.wav")
        mp3 = Path("clip.mp3")
        self.assertTrue(
            wav_utils.can_pcm_stream_copy(
                probe,
                None,
                require_wav_container=True,
                source_path=wav,
            )
        )
        self.assertFalse(
            wav_utils.can_pcm_stream_copy(
                probe,
                None,
                require_wav_container=True,
                source_path=mp3,
            )
        )
        self.assertFalse(wav_utils.can_pcm_stream_copy(probe, 16, require_wav_container=True, source_path=wav))

    def test_can_pcm_stream_copy_for_embedded_pcm_in_video(self) -> None:
        probe = {"codec": "pcm_s16le", "sample_rate": 48000, "bits": 16, "channels": 2}
        self.assertTrue(wav_utils.can_pcm_stream_copy(probe, None))
        self.assertFalse(wav_utils.can_pcm_stream_copy({"codec": "aac"}, None))

    def test_describe_stream_copy(self) -> None:
        probe = {"codec": "pcm_s16le", "sample_rate": 44100, "bits": 16, "channels": 1}
        text = wav_utils.describe_pcm_wav_plan(probe, None, True)
        self.assertIn("stream copy", text)
        self.assertIn("44100 Hz", text)

    def test_describe_track_prefix(self) -> None:
        probe = {"codec": "aac", "sample_rate": 48000, "bits": 0, "channels": 2}
        text = wav_utils.describe_pcm_wav_plan(probe, None, False, track=1)
        self.assertIn("track 1,", text)

    def test_build_pcm_wav_cmd_for_video_track(self) -> None:
        ffmpeg = Path(".dependency/ffmpeg/bin/ffmpeg.exe")
        cmd = wav_utils.build_pcm_wav_cmd(
            ffmpeg,
            Path("in.mkv"),
            Path("out.wav"),
            "pcm_f32le",
            False,
            track=1,
        )
        self.assertIn("-vn", cmd)
        self.assertIn("0:a:1", cmd)
        self.assertIn("pcm_f32le", cmd)

    def test_probe_audio_file(self) -> None:
        probe = {"codec": "pcm_s16le", "sample_rate": 44100, "bits": 16, "channels": 1}
        with unittest.mock.patch.object(
            wav_utils,
            "_probe_selected_audio",
            return_value=probe,
        ) as mocked:
            result = wav_utils.probe_audio_file(Path("ffprobe"), Path("song.flac"))
        mocked.assert_called_once_with(Path("ffprobe"), Path("song.flac"), "a:0")
        self.assertEqual(result, probe)

    def test_probe_video_audio_track(self) -> None:
        probe = {"codec": "aac", "sample_rate": 48000, "bits": 0, "channels": 2}
        with unittest.mock.patch.object(
            wav_utils,
            "_probe_selected_audio",
            return_value=probe,
        ) as mocked:
            result = wav_utils.probe_video_audio_track(Path("ffprobe"), Path("clip.mkv"), 1)
        mocked.assert_called_once_with(Path("ffprobe"), Path("clip.mkv"), "a:1")
        self.assertEqual(result, probe)

    def test_wav_output_name(self) -> None:
        self.assertEqual(wav_utils.wav_output_name(Path("clip.mp4")), "clip.wav")


if __name__ == "__main__":
    raise SystemExit(unittest.main())
