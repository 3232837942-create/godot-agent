"""Shared helpers for resolving skill -o/--output paths."""

from __future__ import annotations

from pathlib import Path


def default_output_path(
    source: Path,
    output_subdir: str,
    output_name: str,
) -> Path:
    """Return the default output file beside a source input."""
    return source.parent / output_subdir / output_name


def resolve_output_path(
    args_output: str,
    source: Path,
    output_subdir: str,
    output_name: str,
) -> Path:
    """Resolve -o/--output to a concrete output file path.

    Rules:
    - ``args_output`` is empty → ``<source-dir>/<output_subdir>/<output_name>``
    - ``args_output`` is an existing directory → ``<args_output>/<output_name>``
    - ``args_output`` ends with ``/`` or ``\\``, or has no suffix → directory intent
    - otherwise → ``args_output`` is treated as an explicit output file path
    """
    if not args_output:
        return default_output_path(source, output_subdir, output_name)

    output = Path(args_output).expanduser()
    if output.exists() and output.is_dir():
        return output / output_name
    if args_output.endswith(("/", "\\")) or output.suffix == "":
        return output / output_name
    return output


def default_output_dir(input_root: Path, output_subdir: str) -> Path:
    """Return the default output directory beside a batch input root."""
    return input_root / output_subdir


def resolve_output_dir(
    args_output: str,
    input_root: Path,
    *,
    output_subdir: str,
) -> Path:
    """Resolve --output to an output directory for batch processing.

    Rules:
    - ``args_output`` is empty → ``<input-root>/<output_subdir>/``
    - otherwise → ``args_output`` as an output directory (resolved)
    """
    if not args_output:
        return default_output_dir(input_root, output_subdir)
    return Path(args_output).expanduser().resolve()


def format_default_output_help(
    output_subdir: str,
    *,
    source_dir_label: str = "source-dir",
    output_name_label: str = "source-name",
) -> str:
    """Build a short default-output hint for argparse help text."""
    return f"<{source_dir_label}>/{output_subdir}/{output_name_label}"


def format_default_output_dir_help(
    output_subdir: str,
    *,
    input_root_label: str = "input-path",
) -> str:
    """Build a short default output-directory hint for argparse help text."""
    return f"<{input_root_label}>/{output_subdir}/"
