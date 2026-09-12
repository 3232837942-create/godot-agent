#!/usr/bin/env python3
"""Tests for resize.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
AI_ROOT = SCRIPT_DIR.parent
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import resize  # noqa: E402
from common.cli_tools import resolve_magick  # noqa: E402
from common.dependency_utils import find_repo_root, resolve_tool_bin  # noqa: E402
from common.image_utils import read_image_size  # noqa: E402

REPO_ROOT = find_repo_root(Path(__file__))
assert REPO_ROOT is not None
PYTHON_BIN = resolve_tool_bin(REPO_ROOT, "python")
RESIZE_SCRIPT = SCRIPT_DIR / "resize.py"
TANK1 = REPO_ROOT / ".ai/test/image/tank1.jpg"
TANK2 = REPO_ROOT / ".ai/test/image/tank2.jpg"
TANK3 = REPO_ROOT / ".ai/test/image/tank3.jpg"


class BuildResizeGeometryTest(unittest.TestCase):
    def test_fit(self) -> None:
        self.assertEqual(resize.build_resize_geometry(128, 64, "fit"), "128x64")

    def test_fill(self) -> None:
        self.assertEqual(resize.build_resize_geometry(128, 64, "fill"), "128x64^")

    def test_exact(self) -> None:
        self.assertEqual(resize.build_resize_geometry(128, 64, "exact"), "128x64!")


class BuildMagickArgsTest(unittest.TestCase):
    def test_fill_includes_extent(self) -> None:
        magick = Path("magick.exe")
        src = Path("hero.png")
        dst = Path("out/hero.png")
        args = resize.build_magick_args(magick, src, dst, 128, 128, "fill")
        self.assertEqual(args[:7], [
            "magick.exe",
            "hero.png",
            "-resize",
            "128x128^",
            "-gravity",
            "center",
            "-extent",
        ])
        self.assertEqual(args[7], "128x128")
        self.assertEqual(Path(args[8]), dst)

    def test_fit_omits_extent(self) -> None:
        dst = Path("out/hero.png")
        args = resize.build_magick_args(
            Path("magick.exe"),
            Path("hero.png"),
            dst,
            64,
            32,
            "fit",
        )
        self.assertEqual(args[:4], ["magick.exe", "hero.png", "-resize", "64x32"])
        self.assertEqual(Path(args[4]), dst)


class ResizeCliTest(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(PYTHON_BIN), str(RESIZE_SCRIPT), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(REPO_ROOT),
        )

    def test_help(self) -> None:
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0)
        self.assertIn("--image", result.stdout)
        self.assertIn("--width", result.stdout)
        self.assertIn("--mode", result.stdout)

    def test_image_not_found(self) -> None:
        result = self.run_cli(
            "--image",
            "missing-no-such-file.png",
            "--width",
            "64",
            "--height",
            "64",
        )
        self.assertEqual(result.returncode, 1)
        self.assertIn("Image file not found", result.stderr)

    def test_directory_not_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli(
                "--image",
                tmp,
                "--width",
                "64",
                "--height",
                "64",
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("Not an image file", result.stderr)

    def test_invalid_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "hero.png"
            src.write_bytes(b"x")

            result = self.run_cli(
                "--image",
                str(src),
                "--width",
                "0",
                "--height",
                "64",
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("positive integers", result.stderr)


class ResizeOutputSizeTest(unittest.TestCase):
    size_changes: list[tuple[str, str, str, str]] = []
    report_order = ("fit square", "fit non-square", "fill", "exact")

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(PYTHON_BIN), str(RESIZE_SCRIPT), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(REPO_ROOT),
        )

    def assert_size_change(
        self,
        label: str,
        src: Path,
        out: Path,
        expected_width: int,
        expected_height: int,
    ) -> None:
        magick = resolve_magick(RESIZE_SCRIPT)
        before_w, before_h = read_image_size(magick, src)
        after_w, after_h = read_image_size(magick, out)
        before = f"{before_w}x{before_h}"
        after = f"{after_w}x{after_h}"
        self.__class__.size_changes.append((label, src.name, before, after))
        self.assertEqual(
            (after_w, after_h),
            (expected_width, expected_height),
            f"expected {expected_width}x{expected_height}, got {after}",
        )

    @classmethod
    def tearDownClass(cls) -> None:
        if not cls.size_changes:
            return

        order = {label: index for index, label in enumerate(cls.report_order)}
        rows = sorted(cls.size_changes, key=lambda item: order.get(item[0], len(order)))
        label_w = max(len(label) for label, _, _, _ in rows)
        name_w = max(len(name) for _, name, _, _ in rows)

        lines = ["", "Resize output sizes:"]
        for label, name, before, after in rows:
            lines.append(f"  {label:<{label_w}}  {name:<{name_w}}  {before} -> {after}")
        print("\n".join(lines), file=sys.stderr)

    @contextmanager
    def resize_sample(
        self,
        sample: Path,
        width: int,
        height: int,
        *,
        mode: str | None = None,
    ) -> Iterator[tuple[Path, Path, subprocess.CompletedProcess[str]]]:
        if not sample.is_file():
            self.skipTest(f"sample image missing: {sample}")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / sample.name
            src.write_bytes(sample.read_bytes())

            args = [
                "--image",
                str(src),
                "--width",
                str(width),
                "--height",
                str(height),
            ]
            if mode is not None:
                args.extend(["--mode", mode])

            result = self.run_cli(*args)
            out = root / "image-resize" / sample.name
            yield src, out, result

    def test_resize_output_size_fit_square(self) -> None:
        with self.resize_sample(TANK1, 128, 128) as (src, out, result):
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size, 0)
            self.assert_size_change("fit square", src, out, 128, 128)

    def test_resize_output_size_fit_non_square(self) -> None:
        with self.resize_sample(TANK2, 128, 64, mode="fit") as (src, out, result):
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out.is_file())
            self.assert_size_change("fit non-square", src, out, 64, 64)

    def test_resize_output_size_fill(self) -> None:
        with self.resize_sample(TANK2, 128, 128, mode="fill") as (src, out, result):
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out.is_file())
            self.assert_size_change("fill", src, out, 128, 128)

    def test_resize_output_size_exact(self) -> None:
        with self.resize_sample(TANK3, 128, 128, mode="exact") as (src, out, result):
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(out.is_file())
            self.assert_size_change("exact", src, out, 128, 128)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
