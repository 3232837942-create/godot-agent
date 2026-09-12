#!/usr/bin/env python3
"""
Compress a single video to stay under a max file size via FFmpeg (GPU-first).

Run through default python from .dependency/manifest.json.
Never use host python/py.

Usage
-----
    .dependency/python/python .ai/video-compress-to-size/compress.py --video path/to/clip.mp4 --max-size 50MB
    .dependency/python/python .ai/video-compress-to-size/compress.py --video path/to/clip.mp4 --max-size 50
    .dependency/python/python .ai/video-compress-to-size/compress.py --video path/to/clip.mp4 --max-size 50MB --cpu
    .dependency/python/python .ai/video-compress-to-size/compress.py --video path/to/clip.mp4 --max-size 50MB -o path/to/out.mp4
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[1]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from common.cli_tools import resolve_ffmpeg, resolve_ffprobe  # noqa: E402
from common.output_utils import format_default_output_help, resolve_output_path  # noqa: E402
from common.video_utils import resolve_video_file, video_output_name  # noqa: E402

DEFAULT_OUTPUT_SUBDIR = "video-compress-to-size"

SIZE_RE = re.compile(
    r"^\s*(\d+(?:\.\d+)?)\s*(B|K|KB|KiB|M|MB|MiB|G|GB|GiB)?\s*$",
    re.IGNORECASE,
)

SAFETY_FACTOR_CPU = 0.92
SAFETY_FACTOR_GPU = 0.90
MIN_VIDEO_BITRATE = 50_000
MAX_ATTEMPTS = 3
KIB = 1024
MIB = 1024 * 1024
GIB = 1024 * 1024 * 1024

NVENC_PRESET_MAP = {
    "ultrafast": "p1",
    "superfast": "p1",
    "veryfast": "p2",
    "faster": "p3",
    "fast": "p3",
    "medium": "p4",
    "slow": "p5",
    "slower": "p6",
    "veryslow": "p7",
    "placebo": "p7",
}
AMF_PRESET_MAP = {
    "ultrafast": "speed",
    "superfast": "speed",
    "veryfast": "speed",
    "faster": "speed",
    "fast": "balanced",
    "medium": "balanced",
    "slow": "quality",
    "slower": "quality",
    "veryslow": "quality",
    "placebo": "quality",
}
QSV_PRESET_MAP = {
    "ultrafast": "veryfast",
    "superfast": "veryfast",
    "veryfast": "veryfast",
    "faster": "faster",
    "fast": "fast",
    "medium": "medium",
    "slow": "slow",
    "slower": "slower",
    "veryslow": "veryslow",
    "placebo": "veryslow",
}


@dataclass(frozen=True)
class EncoderChoice:
    name: str
    kind: str
    hevc: bool
    label: str


def parse_size(text: str) -> int:
    match = SIZE_RE.match(text)
    if not match:
        raise ValueError(
            f"Invalid --max-size '{text}'. Examples: 50, 50MB, 500KB, 1GB, 52428800B"
        )

    value = float(match.group(1))
    unit = (match.group(2) or "MB").upper()
    if unit in {"K", "KB", "KIB"}:
        return int(value * KIB)
    if unit in {"M", "MB", "MIB"}:
        return int(value * MIB)
    if unit in {"G", "GB", "GIB"}:
        return int(value * GIB)
    if unit == "B":
        return int(value)
    raise ValueError(f"Unknown size unit in --max-size '{text}'")


def parse_bitrate(text: str) -> int:
    raw = text.strip().lower()
    if raw.endswith("k"):
        return int(float(raw[:-1]) * 1000)
    if raw.endswith("m"):
        return int(float(raw[:-1]) * 1_000_000)
    return int(float(raw))


def format_bytes(num: int) -> str:
    if num >= GIB:
        return f"{num / GIB:.2f} GiB"
    if num >= MIB:
        return f"{num / MIB:.2f} MiB"
    if num >= KIB:
        return f"{num / KIB:.1f} KiB"
    return f"{num} B"


def format_bitrate(bits_per_sec: int) -> str:
    if bits_per_sec >= 1_000_000:
        return f"{bits_per_sec / 1_000_000:.3f}M"
    return f"{max(1, bits_per_sec // 1000)}k"


def probe_duration(ffprobe: Path, file_path: Path) -> float:
    result = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe failed for: {file_path}\n{result.stderr.strip()}")

    payload = json.loads(result.stdout)
    duration = 0.0
    fmt = payload.get("format") or {}
    if fmt.get("duration"):
        duration = float(fmt["duration"])
    if duration <= 0:
        for stream in payload.get("streams") or []:
            if stream.get("codec_type") == "video" and stream.get("duration"):
                duration = float(stream["duration"])
                break
    if duration <= 0:
        raise RuntimeError(f"Could not determine duration for: {file_path}")
    return duration


def has_audio_streams(ffprobe: Path, file_path: Path) -> bool:
    result = subprocess.run(
        [
            str(ffprobe),
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-select_streams",
            "a",
            str(file_path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        return False
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False
    return bool(payload.get("streams"))


def null_output() -> str:
    return "NUL" if sys.platform == "win32" else "/dev/null"


def run_ffmpeg(cmd: list[str]) -> None:
    result = subprocess.run(
        cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            "FFmpeg failed:"
            + (f"\n{detail}" if detail else "")
            + f"\nCommand: {' '.join(cmd)}"
        )


def encoder_works(ffmpeg: Path, codec: str) -> bool:
    with tempfile.TemporaryDirectory(prefix="vcompress_probe_") as tmp:
        out = Path(tmp) / "probe.mp4"
        cmd = [
            str(ffmpeg),
            "-hide_banner",
            "-loglevel",
            "error",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=320x240:d=0.2",
            "-frames:v",
            "5",
            "-c:v",
            codec,
            "-b:v",
            "500k",
            "-y",
            str(out),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        return result.returncode == 0 and out.is_file() and out.stat().st_size > 0


def list_gpu_candidates(hevc: bool) -> list[EncoderChoice]:
    if hevc:
        return [
            EncoderChoice("hevc_nvenc", "nvenc", True, "NVIDIA NVENC HEVC"),
            EncoderChoice("hevc_amf", "amf", True, "AMD AMF HEVC"),
            EncoderChoice("hevc_qsv", "qsv", True, "Intel QSV HEVC"),
        ]
    return [
        EncoderChoice("h264_nvenc", "nvenc", False, "NVIDIA NVENC H.264"),
        EncoderChoice("h264_amf", "amf", False, "AMD AMF H.264"),
        EncoderChoice("h264_qsv", "qsv", False, "Intel QSV H.264"),
    ]


def select_encoder(ffmpeg: Path, hevc: bool, force_cpu: bool) -> EncoderChoice:
    if not force_cpu:
        for candidate in list_gpu_candidates(hevc):
            if encoder_works(ffmpeg, candidate.name):
                return candidate
    if hevc:
        return EncoderChoice("libx265", "cpu", True, "libx265 (CPU)")
    return EncoderChoice("libx264", "cpu", False, "libx264 (CPU)")


def map_preset(encoder: EncoderChoice, preset: str) -> str:
    key = preset.strip().lower()
    if encoder.kind == "nvenc":
        if key in NVENC_PRESET_MAP:
            return NVENC_PRESET_MAP[key]
        if re.fullmatch(r"p[1-7]", key):
            return key
        return "p4"
    if encoder.kind == "amf":
        if key in {"speed", "balanced", "quality"}:
            return key
        return AMF_PRESET_MAP.get(key, "balanced")
    if encoder.kind == "qsv":
        return QSV_PRESET_MAP.get(key, key if key else "medium")
    return preset


def compute_video_bitrate(
    max_bytes: int,
    duration: float,
    audio_bitrate: int,
    has_audio: bool,
    safety: float,
) -> int:
    budget_bits = max_bytes * 8 * safety
    audio_bits = audio_bitrate if has_audio else 0
    return int(budget_bits / duration - audio_bits)


def build_hwaccel_args(encoder: EncoderChoice) -> list[str]:
    if encoder.kind == "nvenc":
        return ["-hwaccel", "cuda"]
    if encoder.kind == "qsv":
        return ["-hwaccel", "qsv"]
    if encoder.kind == "amf":
        return ["-hwaccel", "d3d11va"]
    return []


def build_video_encode_args(
    encoder: EncoderChoice,
    video_bitrate: int,
    preset: str,
) -> list[str]:
    vb = format_bitrate(video_bitrate)
    maxrate = format_bitrate(int(video_bitrate * 1.05))
    bufsize = format_bitrate(video_bitrate * 2)
    mapped = map_preset(encoder, preset)
    args = ["-c:v", encoder.name, "-b:v", vb]

    if not encoder.hevc:
        args.extend(["-pix_fmt", "yuv420p"])
    elif encoder.kind == "nvenc":
        args.extend(["-pix_fmt", "yuv420p"])

    if encoder.kind == "nvenc":
        args.extend(
            [
                "-rc",
                "vbr",
                "-maxrate",
                maxrate,
                "-bufsize",
                bufsize,
                "-preset",
                mapped,
                "-multipass",
                "fullres",
            ]
        )
    elif encoder.kind == "amf":
        args.extend(
            [
                "-rc",
                "vbr_peak",
                "-maxrate",
                maxrate,
                "-bufsize",
                bufsize,
                "-quality",
                mapped,
            ]
        )
    elif encoder.kind == "qsv":
        args.extend(
            [
                "-maxrate",
                maxrate,
                "-bufsize",
                bufsize,
                "-preset",
                mapped,
            ]
        )
    else:
        args.extend(["-preset", mapped])

    if encoder.hevc:
        args.extend(["-tag:v", "hvc1"])
    return args


def compress_file_gpu(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    encoder: EncoderChoice,
    max_bytes: int,
    video_bitrate: int,
    effective_audio: int,
    has_audio: bool,
    preset: str,
) -> tuple[int, int]:
    last_size = 0
    for attempt in range(1, MAX_ATTEMPTS + 1):
        cmd = [str(ffmpeg), "-hide_banner", "-nostats", "-y"]
        cmd.extend(build_hwaccel_args(encoder))
        cmd.extend(["-i", str(file_path), "-map", "0:v:0"])
        cmd.extend(build_video_encode_args(encoder, video_bitrate, preset))
        if has_audio:
            cmd.extend(
                [
                    "-map",
                    "0:a:0?",
                    "-c:a",
                    "aac",
                    "-b:a",
                    format_bitrate(effective_audio),
                    "-ac",
                    "2",
                ]
            )
        else:
            cmd.append("-an")
        cmd.extend(["-movflags", "+faststart", str(out_path)])

        try:
            run_ffmpeg(cmd)
        except RuntimeError:
            if build_hwaccel_args(encoder):
                cmd = [str(ffmpeg), "-hide_banner", "-nostats", "-y", "-i", str(file_path)]
                cmd.extend(["-map", "0:v:0"])
                cmd.extend(build_video_encode_args(encoder, video_bitrate, preset))
                if has_audio:
                    cmd.extend(
                        [
                            "-map",
                            "0:a:0?",
                            "-c:a",
                            "aac",
                            "-b:a",
                            format_bitrate(effective_audio),
                            "-ac",
                            "2",
                        ]
                    )
                else:
                    cmd.append("-an")
                cmd.extend(["-movflags", "+faststart", str(out_path)])
                run_ffmpeg(cmd)
            else:
                raise

        last_size = out_path.stat().st_size
        if last_size <= max_bytes:
            return last_size, video_bitrate

        scale = (max_bytes * SAFETY_FACTOR_GPU) / last_size
        video_bitrate = max(MIN_VIDEO_BITRATE, int(video_bitrate * scale))
        print(
            f"  [retry {attempt}/{MAX_ATTEMPTS}] "
            f"{format_bytes(last_size)} > {format_bytes(max_bytes)}; "
            f"next video bitrate {format_bitrate(video_bitrate)}"
        )

    raise RuntimeError(
        f"Could not get under {format_bytes(max_bytes)} after {MAX_ATTEMPTS} attempts "
        f"(last size {format_bytes(last_size)})."
    )


def compress_file_cpu(
    ffmpeg: Path,
    file_path: Path,
    out_path: Path,
    encoder: EncoderChoice,
    max_bytes: int,
    video_bitrate: int,
    effective_audio: int,
    has_audio: bool,
    preset: str,
) -> tuple[int, int]:
    last_size = 0
    with tempfile.TemporaryDirectory(prefix="vcompress_") as tmp:
        passlog = Path(tmp) / "ffmpeg2pass"
        for attempt in range(1, MAX_ATTEMPTS + 1):
            vb = format_bitrate(video_bitrate)

            pass1 = [
                str(ffmpeg),
                "-hide_banner",
                "-nostats",
                "-y",
                "-i",
                str(file_path),
                "-map",
                "0:v:0",
                "-c:v",
                encoder.name,
                "-b:v",
                vb,
                "-preset",
                preset,
                "-pass",
                "1",
                "-passlogfile",
                str(passlog),
                "-an",
                "-f",
                "null",
                null_output(),
            ]
            run_ffmpeg(pass1)

            pass2 = [
                str(ffmpeg),
                "-hide_banner",
                "-nostats",
                "-y",
                "-i",
                str(file_path),
                "-map",
                "0:v:0",
                "-c:v",
                encoder.name,
                "-b:v",
                vb,
                "-preset",
                preset,
                "-pass",
                "2",
                "-passlogfile",
                str(passlog),
            ]
            if encoder.hevc:
                pass2.extend(["-tag:v", "hvc1"])
            if has_audio:
                pass2.extend(
                    [
                        "-map",
                        "0:a:0?",
                        "-c:a",
                        "aac",
                        "-b:a",
                        format_bitrate(effective_audio),
                        "-ac",
                        "2",
                    ]
                )
            else:
                pass2.append("-an")
            pass2.extend(["-movflags", "+faststart", str(out_path)])
            run_ffmpeg(pass2)

            last_size = out_path.stat().st_size
            if last_size <= max_bytes:
                return last_size, video_bitrate

            scale = (max_bytes * SAFETY_FACTOR_CPU) / last_size
            video_bitrate = max(MIN_VIDEO_BITRATE, int(video_bitrate * scale))
            print(
                f"  [retry {attempt}/{MAX_ATTEMPTS}] "
                f"{format_bytes(last_size)} > {format_bytes(max_bytes)}; "
                f"next video bitrate {format_bitrate(video_bitrate)}"
            )

    raise RuntimeError(
        f"Could not get under {format_bytes(max_bytes)} after {MAX_ATTEMPTS} attempts "
        f"(last size {format_bytes(last_size)})."
    )


def compress_file(
    ffmpeg: Path,
    ffprobe: Path,
    file_path: Path,
    out_path: Path,
    encoder: EncoderChoice,
    max_bytes: int,
    audio_bitrate: int,
    preset: str,
) -> tuple[int, int]:
    duration = probe_duration(ffprobe, file_path)
    has_audio = has_audio_streams(ffprobe, file_path)
    safety = SAFETY_FACTOR_GPU if encoder.kind != "cpu" else SAFETY_FACTOR_CPU

    effective_audio = audio_bitrate if has_audio else 0
    if has_audio:
        total_budget_bps = int(max_bytes * 8 * safety / duration)
        if effective_audio > total_budget_bps // 2:
            effective_audio = max(32_000, total_budget_bps // 4)

    video_bitrate = compute_video_bitrate(
        max_bytes, duration, effective_audio, has_audio, safety
    )
    if video_bitrate < MIN_VIDEO_BITRATE:
        raise RuntimeError(
            f"Target size {format_bytes(max_bytes)} is too small for "
            f"{duration:.1f}s video (video bitrate would be {format_bitrate(video_bitrate)}). "
            "Raise --max-size or lower --audio-bitrate."
        )

    out_path.parent.mkdir(parents=True, exist_ok=True)

    if encoder.kind == "cpu":
        return compress_file_cpu(
            ffmpeg,
            file_path,
            out_path,
            encoder,
            max_bytes,
            video_bitrate,
            effective_audio,
            has_audio,
            preset,
        )
    return compress_file_gpu(
        ffmpeg,
        file_path,
        out_path,
        encoder,
        max_bytes,
        video_bitrate,
        effective_audio,
        has_audio,
        preset,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compress a single video to stay under a max file size. "
            "Prefers GPU encoders (NVENC/AMF/QSV), falls back to CPU two-pass."
        )
    )
    parser.add_argument(
        "--video",
        required=True,
        help="Path to a single video file",
    )
    parser.add_argument(
        "--max-size",
        required=True,
        help="Max output size (e.g. 50, 50MB, 500KB, 1GB). Bare number = MB.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help=(
            "Output MP4 file or directory. "
            f"Default: {format_default_output_help(DEFAULT_OUTPUT_SUBDIR, output_name_label='source.mp4')}"
        ),
    )
    parser.add_argument(
        "--audio-bitrate",
        default="128k",
        help="AAC audio bitrate (default: 128k)",
    )
    parser.add_argument(
        "--preset",
        default="medium",
        help="Quality/speed preset (default: medium; mapped for GPU encoders)",
    )
    parser.add_argument(
        "--hevc",
        action="store_true",
        help="Prefer HEVC (hevc_nvenc / hevc_amf / hevc_qsv / libx265)",
    )
    parser.add_argument(
        "--cpu",
        action="store_true",
        help="Force CPU encoder (libx264/libx265 two-pass); skip GPU",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        max_bytes = parse_size(args.max_size)
        audio_bitrate = parse_bitrate(args.audio_bitrate)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1

    if max_bytes <= 0:
        print("--max-size must be positive", file=sys.stderr)
        return 1

    script_path = Path(__file__)
    ffmpeg = resolve_ffmpeg(script_path)
    ffprobe = resolve_ffprobe(ffmpeg)
    encoder = select_encoder(ffmpeg, args.hevc, force_cpu=args.cpu)
    mapped_preset = map_preset(encoder, args.preset)

    video_path = resolve_video_file(args.video)
    if video_path is None:
        return 1

    out_path = resolve_output_path(
        args.output,
        video_path,
        DEFAULT_OUTPUT_SUBDIR,
        video_output_name(video_path, suffix=".mp4"),
    )

    if out_path.resolve() == video_path.resolve():
        print(
            "Refusing to overwrite source file. Choose a separate output path "
            f"(default: {DEFAULT_OUTPUT_SUBDIR}/).",
            file=sys.stderr,
        )
        return 1

    src_size = video_path.stat().st_size
    if src_size <= max_bytes:
        print(
            f"[skip] {video_path.name} (already under limit: "
            f"{format_bytes(src_size)} <= {format_bytes(max_bytes)})"
        )
        return 0

    print(f"Video:    {video_path}")
    print(f"Max size: {format_bytes(max_bytes)} ({args.max_size})")
    print(
        f"Encoder:  {encoder.label} ({encoder.name}), "
        f"preset={args.preset}->{mapped_preset}, audio={args.audio_bitrate}"
    )
    print(f"Output:   {out_path}")
    print()

    try:
        print(
            f"[run]  {video_path.name} -> {out_path.name} "
            f"({format_bytes(src_size)} -> <= {format_bytes(max_bytes)}, {encoder.name})"
        )
        out_size, used_vb = compress_file(
            ffmpeg,
            ffprobe,
            video_path,
            out_path,
            encoder,
            max_bytes,
            audio_bitrate,
            args.preset,
        )
        print(
            f"  [ok]   {format_bytes(out_size)} "
            f"(video ~{format_bitrate(used_vb)})"
        )
    except RuntimeError as exc:
        print(f"[fail] {out_path.name}")
        print(exc)
        if out_path.exists():
            try:
                out_path.unlink()
            except OSError:
                pass
        return 1

    print()
    print(f"Done. wrote {out_path.name}")
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
        sys.stderr.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    except Exception:
        pass
    sys.exit(main())
