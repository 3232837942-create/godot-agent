#!/usr/bin/env python3
"""
Merge videos in a folder with random 0.5s xfade into 4K60 GPU HEVC Main10 (no CPU fallback).

Run through default python from .dependency/manifest.json.
Never use host python/py.

Usage
-----
    .dependency/python/python .ai/video-merge-gpu/merge.py --folder path/to/clips
    .dependency/python/python .ai/video-merge-gpu/merge.py --folder path/to/clips -o path/to/final.mp4
"""

from __future__ import annotations

import argparse
import json
import random
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parents[1]
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from common.cli_tools import resolve_ffmpeg, resolve_ffprobe  # noqa: E402
from common.video_utils import VIDEO_EXTENSIONS  # noqa: E402

DEFAULT_OUTPUT_SUBDIR = "video-merge-gpu"

TRANSITION_DURATION = 0.5
OUTPUT_WIDTH = 3840
OUTPUT_HEIGHT = 2160
OUTPUT_FPS = 60
VIDEO_BITRATE = "40M"
AUDIO_BITRATE = "320k"
AUDIO_RATE = 48000
MAX_INPUTS_PER_GRAPH = 8

TRANSITIONS = (
    "fade",
    "dissolve",
    "wipeleft",
    "wiperight",
    "wipeup",
    "wipedown",
    "slideleft",
    "slideright",
    "circlecrop",
    "pixelize",
    "distance",
    "radial",
    "smoothleft",
    "smoothright",
    "circleopen",
    "circleclose",
    "diagtl",
    "diagtr",
    "hblur",
    "zoomin",
)


@dataclass(frozen=True)
class EncoderChoice:
    name: str
    kind: str
    label: str
    pix_fmt: str


def get_video_files(folder: Path) -> list[Path]:
    files = [
        item.resolve()
        for item in folder.iterdir()
        if item.is_file() and item.suffix.lower() in VIDEO_EXTENSIONS
    ]
    return sorted(files, key=lambda path: path.name.lower())


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
        detail = result.stderr.strip() or result.stdout.strip()
        raise RuntimeError(
            f"ffprobe failed for: {file_path}" + (f"\n{detail}" if detail else "")
        )

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"ffprobe JSON parse failed for: {file_path}") from exc

    for stream in payload.get("streams") or []:
        if stream.get("codec_type") == "video":
            dur = stream.get("duration")
            if dur is not None:
                return float(dur)

    fmt = payload.get("format") or {}
    if fmt.get("duration") is not None:
        return float(fmt["duration"])

    raise RuntimeError(f"Could not determine duration for: {file_path}")


def has_audio_stream(ffprobe: Path, file_path: Path) -> bool:
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


def encoder_works(ffmpeg: Path, codec: str, pix_fmt: str) -> bool:
    with tempfile.TemporaryDirectory(prefix="vmerge_gpu_probe_") as tmp:
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
            "-vf",
            f"format={pix_fmt}",
            "-frames:v",
            "5",
            "-c:v",
            codec,
            "-profile:v",
            "main10",
            "-pix_fmt",
            pix_fmt,
            "-b:v",
            "500k",
            "-tag:v",
            "hvc1",
            "-y",
            str(out),
        ]
        result = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        return result.returncode == 0 and out.is_file() and out.stat().st_size > 0


def list_gpu_candidates() -> list[tuple[str, str, str]]:
    return [
        ("hevc_nvenc", "nvenc", "NVIDIA NVENC HEVC Main10"),
        ("hevc_amf", "amf", "AMD AMF HEVC Main10"),
        ("hevc_qsv", "qsv", "Intel QSV HEVC Main10"),
    ]


def select_gpu_encoder(ffmpeg: Path) -> EncoderChoice:
    pix_fmts = ("p010le", "yuv420p10le")
    tried: list[str] = []
    for name, kind, label in list_gpu_candidates():
        for pix_fmt in pix_fmts:
            tried.append(f"{name}/{pix_fmt}")
            if encoder_works(ffmpeg, name, pix_fmt):
                return EncoderChoice(name, kind, label, pix_fmt)

    print(
        "No GPU HEVC Main10 encoder available "
        f"(tried: {', '.join(tried)}). "
        "This skill does not fall back to CPU libx265. "
        "Install NVIDIA/AMD/Intel GPU drivers and an FFmpeg build with "
        "NVENC/AMF/QSV, or use video-merge for CPU encode.",
        file=sys.stderr,
    )
    sys.exit(1)


def encode_args(encoder: EncoderChoice, out_path: Path) -> list[str]:
    args = [
        "-c:v",
        encoder.name,
        "-profile:v",
        "main10",
        "-pix_fmt",
        encoder.pix_fmt,
        "-b:v",
        VIDEO_BITRATE,
        "-maxrate",
        VIDEO_BITRATE,
        "-bufsize",
        "80M",
    ]
    if encoder.kind == "nvenc":
        args.extend(["-rc", "vbr", "-preset", "p4", "-multipass", "fullres"])
    elif encoder.kind == "amf":
        args.extend(["-rc", "vbr_peak", "-quality", "balanced"])
    elif encoder.kind == "qsv":
        args.extend(["-preset", "medium"])

    args.extend(
        [
            "-r",
            str(OUTPUT_FPS),
            "-tag:v",
            "hvc1",
            "-c:a",
            "aac",
            "-b:a",
            AUDIO_BITRATE,
            "-ar",
            str(AUDIO_RATE),
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(out_path),
        ]
    )
    return args


def video_normalize_filter(label_in: str, label_out: str) -> str:
    return (
        f"[{label_in}]scale={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:"
        f"force_original_aspect_ratio=decrease,"
        f"pad={OUTPUT_WIDTH}:{OUTPUT_HEIGHT}:(ow-iw)/2:(oh-ih)/2:black,"
        f"fps={OUTPUT_FPS},format=yuv420p10le,setpts=PTS-STARTPTS[{label_out}]"
    )


def audio_normalize_filter(label_in: str, label_out: str) -> str:
    return (
        f"[{label_in}]aformat=sample_rates={AUDIO_RATE}:channel_layouts=stereo,"
        f"aresample={AUDIO_RATE},asetpts=PTS-STARTPTS[{label_out}]"
    )


def build_filter_complex(
    files: list[Path],
    durations: list[float],
    has_audio: list[bool],
    transitions: list[str],
) -> tuple[str, list[str]]:
    parts: list[str] = []
    extra_inputs: list[str] = []
    silent_index = 0

    for i, file_path in enumerate(files):
        parts.append(video_normalize_filter(f"{i}:v", f"v{i}"))
        if has_audio[i]:
            parts.append(audio_normalize_filter(f"{i}:a", f"a{i}"))
        else:
            dur = durations[i]
            extra_inputs.extend(
                [
                    "-f",
                    "lavfi",
                    "-t",
                    f"{dur:.6f}",
                    "-i",
                    f"anullsrc=channel_layout=stereo:sample_rate={AUDIO_RATE}",
                ]
            )
            src_idx = len(files) + silent_index
            parts.append(audio_normalize_filter(f"{src_idx}:a", f"a{i}"))
            silent_index += 1

    if len(files) == 1:
        parts.append("[v0]null[vout]")
        parts.append("[a0]anull[aout]")
        return ";".join(parts), extra_inputs

    cur_v = "v0"
    cur_a = "a0"
    cum = durations[0]

    for i in range(1, len(files)):
        transition = transitions[i - 1]
        next_v = f"vx{i}"
        next_a = f"ax{i}"
        pad_v = f"vp{i}"
        pad_a = f"ap{i}"
        parts.append(
            f"[{cur_v}]tpad=stop_mode=clone:stop_duration={TRANSITION_DURATION}[{pad_v}]"
        )
        parts.append(f"[{cur_a}]apad=pad_dur={TRANSITION_DURATION}[{pad_a}]")
        offset = cum
        parts.append(
            f"[{pad_v}][v{i}]xfade=transition={transition}:"
            f"duration={TRANSITION_DURATION}:offset={offset:.6f}[{next_v}]"
        )
        parts.append(
            f"[{pad_a}][a{i}]acrossfade=d={TRANSITION_DURATION}:c1=tri:c2=tri[{next_a}]"
        )
        cur_v = next_v
        cur_a = next_a
        cum = cum + durations[i]

    parts.append(f"[{cur_v}]null[vout]")
    parts.append(f"[{cur_a}]anull[aout]")
    return ";".join(parts), extra_inputs


def run_ffmpeg_merge(
    ffmpeg: Path,
    encoder: EncoderChoice,
    files: list[Path],
    durations: list[float],
    has_audio: list[bool],
    transitions: list[str],
    out_path: Path,
) -> None:
    filter_complex, extra_inputs = build_filter_complex(
        files, durations, has_audio, transitions
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd: list[str] = [str(ffmpeg), "-hide_banner", "-y"]
    for file_path in files:
        cmd.extend(["-i", str(file_path)])
    cmd.extend(extra_inputs)
    cmd.extend(
        [
            "-filter_complex",
            filter_complex,
            "-map",
            "[vout]",
            "-map",
            "[aout]",
        ]
    )
    cmd.extend(encode_args(encoder, out_path))

    log_path = out_path.with_suffix(out_path.suffix + ".ffmpeg.log")
    with log_path.open("w", encoding="utf-8", errors="replace") as log_file:
        result = subprocess.run(
            cmd,
            stdout=log_file,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    if result.returncode != 0:
        detail = ""
        if log_path.is_file():
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            detail = "\n".join(lines[-40:])
        raise RuntimeError(
            f"ffmpeg merge failed (exit {result.returncode})"
            + (f"\n{detail}" if detail else "")
        )
    if log_path.is_file():
        log_path.unlink(missing_ok=True)


def merge_chunked(
    ffmpeg: Path,
    encoder: EncoderChoice,
    files: list[Path],
    durations: list[float],
    has_audio: list[bool],
    transitions: list[str],
    out_path: Path,
    work_dir: Path,
    depth: int = 0,
) -> None:
    if len(files) <= MAX_INPUTS_PER_GRAPH:
        run_ffmpeg_merge(
            ffmpeg, encoder, files, durations, has_audio, transitions, out_path
        )
        return

    work_dir.mkdir(parents=True, exist_ok=True)
    chunk_files: list[Path] = []
    chunk_durations: list[float] = []
    chunk_audio: list[bool] = []
    boundary_transitions: list[str] = []

    start = 0
    chunk_idx = 0
    while start < len(files):
        end = min(start + MAX_INPUTS_PER_GRAPH, len(files))
        part_files = files[start:end]
        part_durs = durations[start:end]
        part_audio = has_audio[start:end]
        part_trans = transitions[start : end - 1] if end - start > 1 else []

        if end - start == 1 and depth == 0:
            chunk_out = work_dir / f"d{depth}_{chunk_idx:03d}.mp4"
            print(
                f"[chunk] d{depth} clip {start + 1}/{len(files)} "
                f"-> {chunk_out.name}"
            )
            run_ffmpeg_merge(
                ffmpeg,
                encoder,
                part_files,
                part_durs,
                part_audio,
                part_trans,
                chunk_out,
            )
        elif end - start == 1:
            chunk_out = part_files[0]
        else:
            chunk_out = work_dir / f"d{depth}_{chunk_idx:03d}.mp4"
            print(
                f"[chunk] d{depth} clips {start + 1}-{end}/{len(files)} "
                f"-> {chunk_out.name}"
            )
            merge_chunked(
                ffmpeg,
                encoder,
                part_files,
                part_durs,
                part_audio,
                part_trans,
                chunk_out,
                work_dir,
                depth + 1,
            )

        chunk_files.append(chunk_out)
        chunk_durations.append(sum(part_durs))
        chunk_audio.append(True)
        if end < len(files):
            boundary_transitions.append(transitions[end - 1])
        start = end
        chunk_idx += 1

    print(f"[chunk] d{depth} join {len(chunk_files)} parts -> {out_path.name}")
    merge_chunked(
        ffmpeg,
        encoder,
        chunk_files,
        chunk_durations,
        chunk_audio,
        boundary_transitions,
        out_path,
        work_dir,
        depth + 1,
    )


def resolve_merge_output(args_output: str, folder: Path) -> Path:
    if not args_output:
        return folder / DEFAULT_OUTPUT_SUBDIR / f"{folder.name}.mp4"

    output = Path(args_output).expanduser()
    if output.exists() and output.is_dir():
        return output / f"{folder.name}.mp4"
    if args_output.endswith(("/", "\\")) or output.suffix == "":
        return output / f"{folder.name}.mp4"
    return output.resolve()


def resolve_folder(args_folder: str) -> Path | None:
    path = Path(args_folder).expanduser()
    if not path.exists():
        print(f"Folder not found: {args_folder}", file=sys.stderr)
        return None
    path = path.resolve()
    if not path.is_dir():
        print(
            f"Not a folder (single files are not supported): {args_folder}",
            file=sys.stderr,
        )
        return None
    return path


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Merge videos in a folder (filename sort) with random 0.5s transitions "
            "(freeze-pad; duration = sum of clips) into 3840x2160 60fps "
            "H.265 Main10 40Mbps + AAC 320kbps using GPU encode only "
            "(hevc_nvenc / hevc_amf / hevc_qsv; no CPU fallback)."
        )
    )
    parser.add_argument(
        "--folder",
        required=True,
        help="Directory containing videos to merge (top-level files only)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="",
        help=(
            "Output MP4 file or directory. "
            f"Default: <folder>/{DEFAULT_OUTPUT_SUBDIR}/<folder-name>.mp4"
        ),
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    script_path = Path(__file__)
    ffmpeg = resolve_ffmpeg(script_path)
    ffprobe = resolve_ffprobe(ffmpeg)

    folder = resolve_folder(args.folder)
    if folder is None:
        return 1

    files = get_video_files(folder)
    if not files:
        print(f"No supported video files found under: {args.folder}")
        return 0

    out_path = resolve_merge_output(args.output, folder)
    if out_path.suffix.lower() != ".mp4":
        print(f"Output must be an .mp4 file: {out_path}", file=sys.stderr)
        return 1

    for src in files:
        if out_path.resolve() == src.resolve():
            print(
                "Refusing to overwrite a source file. Choose a different -o path.",
                file=sys.stderr,
            )
            return 1

    durations: list[float] = []
    audio_flags: list[bool] = []
    for file_path in files:
        try:
            dur = probe_duration(ffprobe, file_path)
        except RuntimeError as exc:
            print(exc, file=sys.stderr)
            return 1
        if len(files) > 1 and file_path != files[0] and dur <= TRANSITION_DURATION:
            print(
                f"Clip shorter than transition ({TRANSITION_DURATION}s): "
                f"{file_path.name} ({dur:.3f}s)",
                file=sys.stderr,
            )
            return 1
        durations.append(dur)
        audio_flags.append(has_audio_stream(ffprobe, file_path))

    encoder = select_gpu_encoder(ffmpeg)

    transitions: list[str] = []
    if len(files) > 1:
        transitions = [random.choice(TRANSITIONS) for _ in range(len(files) - 1)]

    total_duration = sum(durations)
    print(f"Folder:      {folder}")
    print(f"Clips:       {len(files)}")
    print(
        f"Transition:  {TRANSITION_DURATION}s (random xfade, "
        "freeze-pad — total duration = sum of clips)"
    )
    print(f"Duration:    {total_duration:.3f}s (preserved)")
    print(
        f"Encoder:     {encoder.label} ({encoder.name}, {encoder.pix_fmt}) — GPU only"
    )
    print(
        f"Output spec: {OUTPUT_WIDTH}x{OUTPUT_HEIGHT} @{OUTPUT_FPS} "
        f"H.265 Main10 {VIDEO_BITRATE} + AAC {AUDIO_BITRATE}"
    )
    print(f"Output:      {out_path}")
    print()

    for i, file_path in enumerate(files):
        audio_note = "audio" if audio_flags[i] else "silent->anullsrc"
        print(f"  [{i + 1:02d}] {file_path.name}  {durations[i]:.3f}s  ({audio_note})")
        if i < len(transitions):
            print(f"       xfade: {transitions[i]} (freeze-pad {TRANSITION_DURATION}s)")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    work_dir = out_path.parent / f".tmp-{out_path.stem}"
    if work_dir.exists():
        for stale in work_dir.glob("*"):
            if stale.is_file():
                stale.unlink(missing_ok=True)

    print()
    if len(files) > MAX_INPUTS_PER_GRAPH:
        print(
            f"[run] ffmpeg merge GPU ({encoder.name}, chunked, max {MAX_INPUTS_PER_GRAPH} "
            "inputs/graph to limit RAM) …"
        )
    else:
        print(f"[run] ffmpeg merge GPU ({encoder.name}) …")

    try:
        merge_chunked(
            ffmpeg,
            encoder,
            files,
            durations,
            audio_flags,
            transitions,
            out_path,
            work_dir,
        )
    except RuntimeError as exc:
        print("[fail] merge failed", file=sys.stderr)
        print(exc, file=sys.stderr)
        return 1
    finally:
        if work_dir.exists():
            for stale in work_dir.glob("*"):
                if stale.is_file():
                    stale.unlink(missing_ok=True)
            try:
                work_dir.rmdir()
            except OSError:
                pass

    print(f"[ok]  {out_path}")
    print()
    print("Done. merged=1")
    return 0


if __name__ == "__main__":
    sys.exit(main())
