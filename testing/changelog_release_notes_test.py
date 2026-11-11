import subprocess
import sys
from pathlib import Path

import pytest

from scripts.changelog_release_notes import extract_release_notes


def test_extracts_only_the_requested_latest_release() -> None:
    changelog = (
        "v1.2.0\n"
        "------\n"
        "\n"
        "Bug fixes\n"
        "~~~~~~~~~\n"
        "\n"
        "* Fix a bug.\n"
        "\n"
        "v1.1.0\n"
        "------\n"
        "\n"
        "* Previous change.\n"
    )

    assert extract_release_notes(changelog, "v1.2.0") == (
        "Bug fixes\n~~~~~~~~~\n\n* Fix a bug."
    )


def test_rejects_a_release_older_than_the_latest_entry() -> None:
    changelog = "v1.2.0\n------\n\n* Current change.\n"

    with pytest.raises(ValueError, match=r"must start with v1\.1\.0"):
        extract_release_notes(changelog, "v1.1.0")


def test_rejects_an_empty_release_section() -> None:
    changelog = "v1.2.0\n------\n\nv1.1.0\n------\n\n* Older change.\n"

    with pytest.raises(ValueError, match=r"no release notes for v1\.2\.0"):
        extract_release_notes(changelog, "v1.2.0")


@pytest.mark.parametrize(
    "notes",
    [
        "Bug fixes\n~~~~~~~~~\n",
        "Bug fixes\n~~~~~~~~\n",
        "Bug fixes\n~~~~~~~~~\n\nDocumentation\n~~~~~~~~~~~~~\n",
        ".. Add release notes here.\n",
    ],
)
def test_rejects_release_sections_without_changes(
    notes: str,
) -> None:
    changelog = f"v1.2.0\n------\n\n{notes}"

    with pytest.raises(ValueError, match=r"no release notes for v1\.2\.0"):
        extract_release_notes(changelog, "v1.2.0")


@pytest.mark.parametrize("output_format", ["rst", "html"])
def test_cli_formats_release_notes(
    tmp_path: Path,
    output_format: str,
) -> None:
    notes = (
        "Bug fixes\n~~~~~~~~~\n\n* Fix a bug.\n\n"
        "Documentation\n~~~~~~~~~~~~~\n\n* Update ``example``.\n"
    )
    (tmp_path / "CHANGELOG.rst").write_text(
        f"v1.2.0\n------\n\n{notes}", encoding="utf-8"
    )
    script = (
        Path(__file__).resolve().parents[1]
        / "scripts/changelog_release_notes.py"
    )
    result = subprocess.run(
        [sys.executable, str(script), "v1.2.0", "--format", output_format],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )

    if output_format == "rst":
        assert result.stdout == notes
    else:
        assert "<h2>Bug fixes</h2>" in result.stdout
        assert "<h2>Documentation</h2>" in result.stdout
        assert "<li><p>Fix a bug.</p></li>" in result.stdout
        assert '<span class="docutils literal">example</span>' in result.stdout
        assert "~~~" not in result.stdout
