from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "release.sh"
GITLAB_URL = "git@gitlab.dwd.de:ku/libraries/pyku.git"
GITHUB_URL = "git@github.com:DeutscherWetterdienst/pyku.git"


def _run_git(
    directory: Path,
    *args: str,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=directory,
        check=check,
        capture_output=True,
        text=True,
    )


def _remote_sha(
    directory: Path,
    remote: str,
    ref: str,
) -> str:
    result = _run_git(directory, "ls-remote", remote, ref)
    return result.stdout.split()[0] if result.stdout else ""


def _make_release_repo(
    directory: Path,
    changelog_version: str = "v1.2.1",
) -> Path:
    repo = directory / "repo"
    gitlab = directory / "gitlab.git"
    github = directory / "github.git"
    repo.mkdir()

    _run_git(directory, "init", "--bare", "--initial-branch=main", str(gitlab))
    _run_git(directory, "init", "--bare", "--initial-branch=main", str(github))
    _run_git(repo, "init", "--initial-branch=main")
    _run_git(repo, "config", "user.name", "Release Test")
    _run_git(repo, "config", "user.email", "release-test@example.invalid")
    _run_git(
        repo,
        "config",
        f"url.{gitlab.as_uri()}.insteadOf",
        GITLAB_URL,
    )
    _run_git(
        repo,
        "config",
        f"url.{github.as_uri()}.insteadOf",
        GITHUB_URL,
    )
    _run_git(repo, "remote", "add", "gitlab", GITLAB_URL)
    _run_git(repo, "remote", "add", "github", GITHUB_URL)

    (repo / "scripts").mkdir()
    (repo / "scripts" / "release.sh").write_bytes(SCRIPT.read_bytes())
    (repo / "CHANGELOG.rst").write_text(
        "v1.2.0\n------\n\nBug fixes\n~~~~~~~~~\n\n* Old fix.\n",
        encoding="utf-8",
    )
    _run_git(repo, "add", "CHANGELOG.rst", "scripts/release.sh")
    _run_git(repo, "commit", "-m", "Initial changelog")
    _run_git(repo, "push", "gitlab", "main")
    _run_git(repo, "push", "github", "main")

    (repo / "CHANGELOG.rst").write_text(
        f"{changelog_version}\n----------\n\n"
        "Bug fixes\n~~~~~~~~~\n\n* A release fix.\n\n"
        "v1.2.0\n------\n\nBug fixes\n~~~~~~~~~\n\n* Old fix.\n",
        encoding="utf-8",
    )
    _run_git(repo, "add", "CHANGELOG.rst")
    _run_git(repo, "commit", "-m", f"Update changelog for {changelog_version}")
    _run_git(repo, "push", "gitlab", "main")

    return repo


def _run_release(
    repo: Path,
    *args: str,
    input_text: str = "",
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(repo / "scripts" / "release.sh"), *args],
        cwd=repo,
        input=input_text,
        capture_output=True,
        text=True,
        check=False,
    )


def test_release_script_help() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT), "--help"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "--release-version vX.Y.Z" in result.stdout
    assert "sync-tag" in result.stdout


def test_release_script_rejects_invalid_version() -> None:
    result = subprocess.run(
        ["bash", str(SCRIPT), "tag", "--release-version", "1.2.1"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 2
    assert "vX.Y.Z format" in result.stderr


@pytest.mark.parametrize("follow_tags", [False, True])
def test_release_script_tags_gitlab_then_syncs_github(
    tmp_path: Path,
    follow_tags: bool,
) -> None:
    repo = _make_release_repo(tmp_path)
    follow_tags_config = str(follow_tags).lower()
    _run_git(repo, "config", "push.followTags", follow_tags_config)
    _run_git(repo, "tag", "-a", "v0.9.9", "HEAD~1", "-m", "Local-only tag")

    tagged = _run_release(
        repo,
        "tag",
        "--release-version",
        "v1.2.1",
        input_text="y\n",
    )

    assert tagged.returncode == 0, tagged.stderr
    assert _remote_sha(repo, "gitlab", "refs/heads/main") == _remote_sha(
        repo,
        "github",
        "refs/heads/main",
    )
    gitlab_tag = _remote_sha(repo, "gitlab", "refs/tags/v1.2.1")
    assert gitlab_tag
    assert _remote_sha(repo, "gitlab", "refs/tags/v1.2.1^{}") == (
        _remote_sha(repo, "gitlab", "refs/heads/main")
    )
    assert not _remote_sha(repo, "github", "refs/tags/v1.2.1")
    for remote in ("gitlab", "github"):
        assert not _remote_sha(repo, remote, "refs/tags/v0.9.9")

    _run_git(repo, "tag", "-a", "v0.9.8", "HEAD~1", "-m", "Another local tag")

    synced = _run_release(
        repo,
        "sync-tag",
        "--release-version",
        "v1.2.1",
        input_text="y\n",
    )

    assert synced.returncode == 0, synced.stderr
    assert _remote_sha(repo, "github", "refs/tags/v1.2.1") == gitlab_tag
    assert _remote_sha(repo, "github", "refs/tags/v1.2.1^{}") == (
        _remote_sha(repo, "gitlab", "refs/tags/v1.2.1^{}")
    )
    for remote in ("gitlab", "github"):
        for tag in ("v0.9.9", "v0.9.8"):
            assert not _remote_sha(repo, remote, f"refs/tags/{tag}")
    assert _run_git(repo, "config", "--get", "push.followTags").stdout == (
        f"{follow_tags_config}\n"
    )


def test_release_script_rejects_changelog_mismatch_before_sync(
    tmp_path: Path,
) -> None:
    repo = _make_release_repo(tmp_path, changelog_version="v1.2.0")
    github_main_before = _remote_sha(repo, "github", "refs/heads/main")

    result = _run_release(
        repo,
        "tag",
        "--release-version",
        "v1.2.1",
    )

    assert result.returncode != 0
    assert "CHANGELOG.rst must start with v1.2.1" in result.stderr
    assert _remote_sha(repo, "github", "refs/heads/main") == github_main_before


def test_release_script_stops_on_divergent_github_main(
    tmp_path: Path,
) -> None:
    repo = _make_release_repo(tmp_path)
    github = tmp_path / "github.git"
    clone = tmp_path / "github-clone"
    _run_git(tmp_path, "clone", str(github), str(clone))
    _run_git(clone, "config", "user.name", "Release Test")
    _run_git(clone, "config", "user.email", "release-test@example.invalid")
    (clone / "divergence.txt").write_text("unexpected\n", encoding="utf-8")
    _run_git(clone, "add", "divergence.txt")
    _run_git(clone, "commit", "-m", "Divergent GitHub change")
    _run_git(clone, "push", "origin", "main")
    github_main_before = _remote_sha(repo, "github", "refs/heads/main")

    result = _run_release(
        repo,
        "tag",
        "--release-version",
        "v1.2.1",
    )

    assert result.returncode != 0
    assert "GitHub main is not an ancestor" in result.stderr
    assert _remote_sha(repo, "github", "refs/heads/main") == github_main_before
