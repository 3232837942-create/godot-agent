#!/usr/bin/env python3
"""Tests for trim.py."""

from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from PIL import Image

SCRIPT_DIR = Path(__file__).resolve().parent
AI_ROOT = SCRIPT_DIR.parent
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import trim  # noqa: E402
from common.dependency_utils import find_repo_root, resolve_tool_bin  # noqa: E402

REPO_ROOT = find_repo_root(Path(__file__))
assert REPO_ROOT is not None
TRIM_BIN = resolve_tool_bin(REPO_ROOT, "image-trim")
TRIM_SCRIPT = SCRIPT_DIR / "trim.py"
TANK1 = REPO_ROOT / ".ai/test/image/tank1.jpg"
TANK3 = REPO_ROOT / ".ai/test/image/tank3.jpg"


def read_image_size(path: Path) -> tuple[int, int]:
    with Image.open(path) as img:
        return img.size


def aspect_ratio(width: int, height: int) -> float:
    return width / height


class DetectContentBboxTest(unittest.TestCase):
    def test_auto_mode_trims_opaque_border(self) -> None:
        image = Image.new("RGB", (100, 100), (255, 255, 255))
        for x in range(30, 70):
            for y in range(30, 70):
                image.putpixel((x, y), (0, 0, 0))
        bbox = trim.detect_content_bbox(
            image,
            mode="auto",
            alpha_threshold=trim.DEFAULT_ALPHA_THRESHOLD,
            background=(255, 255, 255),
            tolerance=trim.DEFAULT_TOLERANCE,
        )
        self.assertIsNotNone(bbox)
        assert bbox is not None
        left, top, right, bottom = bbox
        self.assertLess(right - left, 100)
        self.assertLess(bottom - top, 100)


class TrimCliTest(unittest.TestCase):
    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(TRIM_BIN), str(TRIM_SCRIPT), *args],
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
        self.assertIn("--mode", result.stdout)
        self.assertIn("--tight", result.stdout)

    def test_image_not_found(self) -> None:
        result = self.run_cli("--image", "missing-no-such-file.png")
        self.assertEqual(result.returncode, 1)
        self.assertIn("Image file not found", result.stderr)

    def test_directory_not_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            result = self.run_cli("--image", tmp)
            self.assertEqual(result.returncode, 1)
            self.assertIn("Not an image file", result.stderr)


class TrimOutputSizeTest(unittest.TestCase):
    size_changes: list[tuple[str, str, str, str, str]] = []
    report_order = ("auto preserve aspect", "alpha", "color", "tight")

    def run_cli(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [str(TRIM_BIN), str(TRIM_SCRIPT), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            cwd=str(REPO_ROOT),
        )

    def assert_size_changed(
        self,
        label: str,
        src: Path,
        out: Path,
        *,
        preserve_aspect: bool,
    ) -> None:
        before_w, before_h = read_image_size(src)
        after_w, after_h = read_image_size(out)
        before = f"{before_w}x{before_h}"
        after = f"{after_w}x{after_h}"
        same = before_w == after_w and before_h == after_h
        aspect_note = ""
        if preserve_aspect:
            before_ratio = aspect_ratio(before_w, before_h)
            after_ratio = aspect_ratio(after_w, after_h)
            aspect_note = "same aspect" if abs(before_ratio - after_ratio) < 0.02 else "aspect changed"
        else:
            aspect_note = "tight crop"
        self.__class__.size_changes.append((label, src.name, before, after, aspect_note))

        self.assertFalse(
            same,
            f"expected trimmed output to differ from source, but both are {before}",
        )
        self.assertLessEqual(after_w, before_w)
        self.assertLessEqual(after_h, before_h)
        self.assertLess(after_w * after_h, before_w * before_h)

        if preserve_aspect:
            before_ratio = aspect_ratio(before_w, before_h)
            after_ratio = aspect_ratio(after_w, after_h)
            self.assertAlmostEqual(before_ratio, after_ratio, places=2)

    @classmethod
    def tearDownClass(cls) -> None:
        if not cls.size_changes:
            return

        order = {label: index for index, label in enumerate(cls.report_order)}
        rows = sorted(cls.size_changes, key=lambda item: order.get(item[0], len(order)))
        label_w = max(len(label) for label, _, _, _, _ in rows)
        name_w = max(len(name) for _, name, _, _, _ in rows)

        lines = ["", "Trim output sizes (before -> after must differ):"]
        for label, name, before, after, aspect_note in rows:
            lines.append(
                f"  {label:<{label_w}}  {name:<{name_w}}  {before} -> {after}  ({aspect_note})"
            )
        print("\n".join(lines), file=sys.stderr)

    @contextmanager
    def trim_sample(
        self,
        sample: Path,
        *extra_args: str,
    ) -> Iterator[tuple[Path, Path, subprocess.CompletedProcess[str]]]:
        if not sample.is_file():
            self.skipTest(f"sample image missing: {sample}")

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / sample.name
            src.write_bytes(sample.read_bytes())

            result = self.run_cli("--image", str(src), *extra_args)
            out = root / trim.DEFAULT_OUTPUT_SUBDIR / sample.name
            yield src, out, result

    def test_trim_output_size_auto_preserve_aspect(self) -> None:
        with self.trim_sample(TANK1) as (src, out, result):
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size, 0)
            self.assert_size_changed("auto preserve aspect", src, out, preserve_aspect=True)

    def test_trim_output_size_alpha(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "alpha_sample.png"
            image = Image.new("RGBA", (120, 120), (0, 0, 0, 0))
            for x in range(40, 80):
                for y in range(40, 80):
                    image.putpixel((x, y), (200, 50, 50, 255))
            image.save(src)

            result = self.run_cli("--image", str(src), "--mode", "alpha")
            out = root / trim.DEFAULT_OUTPUT_SUBDIR / src.name
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertTrue(out.is_file())
            self.assert_size_changed("alpha", src, out, preserve_aspect=True)

    def test_trim_output_size_color(self) -> None:
        with self.trim_sample(
            TANK3,
            "--mode",
            "color",
            "--color",
            "FFFFFF",
        ) as (src, out, result):
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertTrue(out.is_file())
            self.assert_size_changed("color", src, out, preserve_aspect=True)

    def test_trim_output_size_tight(self) -> None:
        with self.trim_sample(TANK1, "--tight") as (src, out, result):
            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            self.assertTrue(out.is_file())
            self.assert_size_changed("tight", src, out, preserve_aspect=False)


if __name__ == "__main__":
    raise SystemExit(unittest.main())
