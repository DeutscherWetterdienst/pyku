---
name: release
description: >-
  Prepare a pyku release on canonical GitLab, including the changelog MR,
  release tag, and manual synchronization of GitHub refs.
---

# Pyku release workflow

GitLab is the source of truth for pyku. Prepare and merge the changelog MR,
then manually synchronize GitLab `main` and the specific release tag to
GitHub. Never make independent changes on GitHub or force-push divergent refs.

The human runbook is `doc/contribute/maintainers.rst`. Keep it synchronized
with this skill whenever the process changes. For synchronization checks, see
`.opencode/skills/sync/SKILL.md`.

## Prepare the release

1. Check out the latest GitLab `main` and confirm GitLab CI passed.
2. Review MRs merged since the previous release and update `CHANGELOG.rst`
   with the next `vX.Y.Z` heading and applicable sections: New Features,
   Breaking changes, Deprecations, Bug fixes, Documentation, and Internal
   changes.
3. Create and push a release branch to GitLab, then open an MR targeting
   `main`. Review the staged diff, wait for required checks, and merge the MR.
4. Manually fast-forward GitHub `main` from GitLab using
   `.opencode/skills/sync/SKILL.md`; verify both refs match before tagging.

Example release branch commands (replace `X.Y.Z`):

```bash
git switch main
git pull --ff-only gitlab main
git switch -c release/vX.Y.Z
# Edit CHANGELOG.rst for vX.Y.Z.
git add CHANGELOG.rst
git diff --cached --check
git diff --cached
git commit -m "Update changelog for vX.Y.Z"
git push gitlab release/vX.Y.Z
```

The tag pipeline requires the tag to match the newest `vX.Y.Z` heading in
`CHANGELOG.rst` and the section to contain release notes. It fails before
publishing if the changelog is stale or empty.
Heading-only and comment-only sections are empty. A tag-validation job gates
publishing and Pages, and renders the notes as HTML for the GitLab Release.

## Tag and verify

Use the next semantic version and confirm the tag is unused on both hosts:

```bash
git ls-remote --tags gitlab refs/tags/vX.Y.Z
git ls-remote --tags github refs/tags/vX.Y.Z
```

After merging the release MR, refresh the refs and verify GitLab and GitHub
`main` match. Create one annotated tag on GitLab `main` first:

```bash
git fetch --prune --tags gitlab
git fetch --prune --tags github
git switch main
git pull --ff-only gitlab main
git ls-remote gitlab refs/heads/main
git ls-remote github refs/heads/main
git tag -a vX.Y.Z -m "pyku vX.Y.Z"
git push gitlab vX.Y.Z
```

Wait for the GitLab release pipeline to succeed. If GitHub lacks this tag,
push only this tag. If it already has the same tag object, no push is needed;
stop if it differs. Never delete or replace a tag, and do not push all tags.
Check the GitHub Actions run and verify both hosts have the expected refs:

```bash
git ls-remote --tags gitlab refs/tags/vX.Y.Z
git ls-remote --tags github refs/tags/vX.Y.Z
git push github vX.Y.Z
git ls-remote gitlab refs/heads/main refs/tags/vX.Y.Z
git ls-remote github refs/heads/main refs/tags/vX.Y.Z
```

GitLab publishes to the pyku project's package registry, updates the
`pyku.latest` module, deploys GitLab Pages, and creates a GitLab Release using
the changelog section.
GitHub Actions tests the manually synchronized commit and deploys GitHub Pages.
Pushes to `main` also deploy current documentation on both hosts; a tag
deployment replaces that same current site. Versioned documentation is
tracked in GitLab work item
[#343](https://gitlab.dwd.de/ku/libraries/pyku/-/work_items/343).

GitLab Pages uses the shared `pages` resource group and environment. In
**Settings > CI/CD > General pipelines**, keep **Prevent outdated deployment
jobs** enabled and **Allow job retries for rollback deployments** disabled so
older pipelines and retries cannot replace newer documentation.

If refs diverge, a push is rejected, or access is denied, stop and follow
`.opencode/skills/sync/SKILL.md`. Never force-push or replace a tag.
