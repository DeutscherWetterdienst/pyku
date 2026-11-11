from pathlib import Path

import yaml


def test_tag_pages_waits_for_release_validation() -> None:
    config = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / ".gitlab-ci.yml").read_text(
            encoding="utf-8"
        )
    )
    validation = config["verify-release-notes"]
    pages = config["pages"]

    assert validation["stage"] == "test"
    assert validation["rules"] == [{"if": "$CI_COMMIT_TAG"}]
    assert {"job": "verify-release-notes", "optional": True} in pages["needs"]
    assert "verify-release-notes" in config["create-gitlab-release"]["needs"]
    assert validation["artifacts"]["paths"] == ["release-notes.html"]
    assert config["pypi-deploy"]["stage"] == "deploy"
    assert "needs" not in config["pypi-deploy"]


def test_pages_deployments_share_a_lock_and_environment() -> None:
    config = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / ".gitlab-ci.yml").read_text(
            encoding="utf-8"
        )
    )

    assert config["pages"]["resource_group"] == "pages"
    assert config["pages"]["environment"]["name"] == "pages"


def test_documentation_build_runs_in_merge_request_pipelines() -> None:
    config = yaml.safe_load(
        (Path(__file__).resolve().parents[1] / ".gitlab-ci.yml").read_text(
            encoding="utf-8"
        )
    )
    merge_request_rule = {"if": '$CI_PIPELINE_SOURCE == "merge_request_event"'}

    assert merge_request_rule in config["install-wheel"]["rules"]
    assert merge_request_rule in config["documentation"]["rules"]


def test_github_tag_release_waits_for_build_and_uses_changelog_notes() -> None:
    config = yaml.safe_load(
        (
            Path(__file__).resolve().parents[1]
            / ".github"
            / "workflows"
            / "pipeline.yaml"
        ).read_text(encoding="utf-8")
    )
    release = config["jobs"]["create-github-release"]
    notes_command = next(
        step["run"]
        for step in release["steps"]
        if step.get("name") == "Generate release notes"
    )
    release_command = next(
        step["run"]
        for step in release["steps"]
        if step.get("name") == "Create GitHub Release"
    )

    assert release["if"] == "startsWith(github.ref, 'refs/tags/v')"
    assert release["needs"] == ["build-and-test", "deploy"]
    assert release["permissions"]["contents"] == "write"
    assert "uv run --no-project" in notes_command
    assert '"$GITHUB_REF_NAME" --format html' in notes_command
    assert "gh release create" in release_command
    assert "--verify-tag" in release_command
    assert "--notes-file release-notes.html" in release_command
