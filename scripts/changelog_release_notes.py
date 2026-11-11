"""Validate and print the changelog section for a release tag."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from docutils import nodes
from docutils.core import publish_doctree, publish_parts

_VERSION = re.compile(r"v\d+\.\d+\.\d+")


def _is_version_heading(
    lines: list[str],
    index: int,
) -> bool:
    heading = lines[index]
    return (
        _VERSION.fullmatch(heading) is not None
        and index + 1 < len(lines)
        and lines[index + 1] == "-" * len(heading)
    )


def extract_release_notes(
    changelog: str,
    version: str,
) -> str:
    lines = changelog.splitlines()
    headings = [
        index
        for index in range(len(lines))
        if _is_version_heading(lines, index)
    ]

    if not headings or lines[headings[0]] != version:
        latest = lines[headings[0]] if headings else "no version heading"
        raise ValueError(
            f"CHANGELOG.rst must start with {version}; found {latest}"
        )

    start = headings[0] + 2
    end = headings[1] if len(headings) > 1 else len(lines)
    notes = "\n".join(lines[start:end]).strip()
    document = publish_doctree(notes, settings_overrides={"report_level": 5})
    if not any(
        paragraph.astext().strip()
        for paragraph in document.findall(nodes.paragraph)
        if not isinstance(paragraph.parent, nodes.system_message)
    ):
        raise ValueError(f"CHANGELOG.rst has no release notes for {version}")

    return notes


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("version")
    parser.add_argument("--format", choices=("rst", "html"), default="rst")
    args = parser.parse_args()

    if _VERSION.fullmatch(args.version) is None:
        parser.error("version must use the vX.Y.Z format")

    try:
        notes = extract_release_notes(
            Path("CHANGELOG.rst").read_text(encoding="utf-8"),
            args.version,
        )
    except ValueError as error:
        parser.error(str(error))

    if args.format == "html":
        notes = publish_parts(
            notes,
            writer_name="html5",
            settings_overrides={
                "doctitle_xform": False,
                "initial_header_level": 2,
                "report_level": 5,
            },
        )["fragment"]
    print(notes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
