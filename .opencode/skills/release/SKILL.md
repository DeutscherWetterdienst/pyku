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
4. After the changelog MR merges, run the repository release helper as
   described below. It safely synchronizes `main` to GitHub before tagging.

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

## Run the release helper

The helper is `scripts/release.sh`; it requires Bash and Git and does not use
`glab`. Its help is available with:

```bash
bash scripts/release.sh --help
```

After the changelog MR merges and its GitLab `main` pipeline passes, run:

```bash
bash scripts/release.sh tag --release-version vX.Y.Z
```

The helper requires a clean worktree and `gitlab`/`github` remotes pointing to
the pyku repositories. It checks that the requested version is the newest
changelog heading, the tag is unused, and GitHub `main` can be fast-forwarded
to GitLab `main`. It asks the maintainer to confirm the GitLab `main` pipeline
passed, then syncs `main` and creates an annotated tag on GitLab. It never
force-pushes or replaces refs.

Wait for the GitLab tag pipeline to pass, then run:

```bash
bash scripts/release.sh sync-tag --release-version vX.Y.Z
```

Confirm the tag pipeline succeeded when prompted. The helper pushes only that
tag to GitHub, verifies its tag object and target commit, and stops if GitHub
has a different tag. It does not delete or replace tags or push all tags.
After the GitHub tag workflow passes, that workflow creates a GitHub Release
from the same changelog notes. GitLab remains the canonical release host.

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
