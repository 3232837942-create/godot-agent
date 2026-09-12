#!/usr/bin/env python3
"""Tests for image_utils.py."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

AI_ROOT = Path(__file__).resolve().parent.parent
if str(AI_ROOT) not in sys.path:
    sys.path.insert(0, str(AI_ROOT))

from common import image_utils  # noqa: E402
from common.cli_tools import resolve_magick  # noqa: E402
from common.dependency_utils import find_repo_root  # noqa: E402

REPO_ROOT = find_repo_root(Path(__file__))
assert REPO_ROOT is not None
SAMPLE_IMAGE = REPO_ROOT / ".ai/test/image/tank1.jpg"


class RelativeImagePathTest(unittest.TestCase):
    def test_returns_posix_relative_path(self) -> None:
        root = Path("assets/sprites")
        file_path = Path("assets/sprites/hero.png")
        self.assertEqual(
            image_utils.relative_image_path(file_path, root),
            "hero.png",
        )

    def test_falls_back_to_filename(self) -> None:
        file_path = Path("/elsewhere/hero.png")
        self.assertEqual(
            image_utils.relative_image_path(file_path, Path("assets")),
            "hero.png",
        )


class MirrorOutputRelTest(unittest.TestCase):
    def test_preserves_suffix_by_default(self) -> None:
        root = Path("assets")
        file_path = Path("assets/icon.webp")
        self.assertEqual(
            image_utils.mirror_output_rel(file_path, root),
            "icon.webp",
        )

    def test_can_change_suffix(self) -> None:
        root = Path("assets")
        file_path = Path("assets/icon.webp")
        self.assertEqual(
            image_utils.mirror_output_rel(file_path, root, suffix=".png"),
            "icon.png",
        )


class ImageOutputNameTest(unittest.TestCase):
    def test_preserves_name(self) -> None:
        self.assertEqual(image_utils.image_output_name(Path("hero.png")), "hero.png")

    def test_changes_suffix(self) -> None:
        self.assertEqual(
            image_utils.image_output_name(Path("hero.jpg"), suffix=".png"),
            "hero.png",
        )


class ResolveInputRootTest(unittest.TestCase):
    def test_file_uses_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "hero.png"
            src.write_bytes(b"x")
            self.assertEqual(
                image_utils.resolve_input_root(src.resolve()).resolve(),
                root.resolve(),
            )

    def test_directory_uses_self(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertEqual(image_utils.resolve_input_root(root.resolve()), root.resolve())


class FilterOutputFilesTest(unittest.TestCase):
    def test_excludes_files_under_output_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            out_dir = root / "resized"
            out_dir.mkdir()
            source = root / "hero.png"
            source.write_bytes(b"x")
            nested = out_dir / "old.png"
            nested.write_bytes(b"y")

            kept = image_utils.filter_output_files([source, nested], out_dir)
            self.assertEqual(len(kept), 1)
            self.assertEqual(kept[0].resolve(), source.resolve())


class FindSourceCollisionsTest(unittest.TestCase):
    def test_detects_output_same_as_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "hero.png"
            src.write_bytes(b"x")
            collisions = image_utils.find_source_collisions([src], root, root)
            self.assertEqual(len(collisions), 1)
            self.assertEqual(collisions[0][0].resolve(), src.resolve())

    def test_honors_output_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            src = root / "hero.jpg"
            src.write_bytes(b"x")
            out_dir = root / "png"
            out_dir.mkdir()
            dst = out_dir / "hero.png"
            dst.write_bytes(b"y")

            collisions = image_utils.find_source_collisions(
                [src, dst],
                root,
                out_dir,
                output_suffix=".png",
            )
            self.assertEqual(collisions, [])


class ResolveImageFileTest(unittest.TestCase):
    def test_returns_none_for_missing_file(self) -> None:
        self.assertIsNone(image_utils.resolve_image_file("missing-no-such-file.png"))

    def test_returns_none_for_unsupported_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "notes.txt"
            path.write_text("hello", encoding="utf-8")
            self.assertIsNone(image_utils.resolve_image_file(str(path)))


class ReadImageSizeTest(unittest.TestCase):
    def test_reads_sample_image_dimensions(self) -> None:
        if not SAMPLE_IMAGE.is_file():
            self.skipTest("sample image missing")

        magick = resolve_magick(Path(__file__))
        self.assertEqual(image_utils.read_image_size(magick, SAMPLE_IMAGE), (1024, 1024))


if __name__ == "__main__":
    raise SystemExit(unittest.main())
