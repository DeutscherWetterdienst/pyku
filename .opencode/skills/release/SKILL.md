---
name: release
description: >-
  Use when preparing a pyku release, reviewing the release workflow, or
  synchronizing GitLab and GitHub main branches and version tags.
---

# Pyku release workflow

Pyku supports GitLab and GitHub as source hosts. For each change or release,
choose one source host, then synchronize its `main` branch and release tags to
the other host. Do not make independent changes on both hosts at the same time.

The human maintainer runbook is `doc/contribute/maintainers.rst`. Keep this
skill and that document synchronized whenever the process changes.

## Merge a change

1. Choose GitLab or GitHub as the source host.
2. Open an MR or PR targeting `main` on that host.
3. Review the change and wait for that host's required checks to pass.
4. Merge the request.
5. Fast-forward the other host's `main` to the merged commit.

Use a clean checkout with remotes named `gitlab` and `github`. From GitLab:

```bash
git clone https://gitlab.dwd.de/ku/libraries/pyku.git pyku-sync
cd pyku-sync
git remote rename origin gitlab
git remote add github git@github.com:DeutscherWetterdienst/pyku.git
```

Or clone from GitHub and configure the remotes in reverse:

```bash
git clone git@github.com:DeutscherWetterdienst/pyku.git pyku-sync
cd pyku-sync
git remote rename origin github
git remote add gitlab https://gitlab.dwd.de/ku/libraries/pyku.git
```

Fetch both hosts and check out `main`:

```bash
git fetch --prune --tags gitlab
git fetch --prune --tags github
git switch main
```

For a GitLab-sourced change:

```bash
git pull --ff-only gitlab main
git merge-base --is-ancestor github/main main
git push github main:main
```

For a GitHub-sourced change:

```bash
git pull --ff-only github main
git merge-base --is-ancestor gitlab/main main
git push gitlab main:main
```

The ancestry check must succeed before pushing. If it fails or the push is
rejected, stop and ask maintainers to reconcile the branch histories. Resume
only when the source commit can be fast-forwarded onto the other host. Never
force-push. Verify both remote branch refs point to the same commit:

```bash
git ls-remote gitlab refs/heads/main
git ls-remote github refs/heads/main
```

The `master` branch is deprecated. Do not merge changes into it or use it as a
release branch.

## Prepare a release

1. Choose GitLab or GitHub as the release's source host. Avoid independent
   changes on the other host during the release.
2. Start from the source host's current `main`; confirm its MR/PR checks passed.
3. Create a release branch from `main` and update `CHANGELOG.rst` with the next
   version and applicable sections:
   New Features, Breaking changes, Deprecations, Bug fixes, Documentation,
   and Internal changes.
4. Stage, review, commit, and push the release branch. Open an MR or PR
   targeting `main`, wait for checks, and merge it.
5. Fetch both hosts again, update local `main` from the source host, then
   synchronize it to the other host. Both `main` branches must identify the same
   commit before tagging.

For a GitLab-sourced release, create and push the release branch:

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

For a GitHub-sourced release, use `github` as the remote:

```bash
git switch main
git pull --ff-only github main
git switch -c release/vX.Y.Z
# Edit CHANGELOG.rst for vX.Y.Z.
git add CHANGELOG.rst
git diff --cached --check
git diff --cached
git commit -m "Update changelog for vX.Y.Z"
git push github release/vX.Y.Z
```

After merging the MR or PR, fetch both hosts again and switch back to `main`
before running the source-specific synchronization commands above:

```bash
git fetch --prune --tags gitlab
git fetch --prune --tags github
git switch main
```

Use the next version according to semantic versioning and existing `v*` tags.
`setuptools_scm` derives the package version from Git tags. Confirm the tag is
unused on both remotes:

```bash
git ls-remote --tags gitlab refs/tags/vX.Y.Z
git ls-remote --tags github refs/tags/vX.Y.Z
```

Create the annotated tag once on the selected source's synchronized `main`,
then push the same tag to both remotes. For a GitLab-sourced release:

```bash
git tag -a vX.Y.Z -m "pyku vX.Y.Z"
git push gitlab vX.Y.Z
git push github vX.Y.Z
```

For a GitHub-sourced release:

```bash
git tag -a vX.Y.Z -m "pyku vX.Y.Z"
git push github vX.Y.Z
git push gitlab vX.Y.Z
```

Pushing a tag starts each host's tag pipeline; it does not create a GitLab or
GitHub Release page entry. GitLab publishes to the internal PyPI, updates the
`pyku.latest` module, and deploys GitLab Pages. GitHub builds and tests the
package and deploys GitHub Pages. Check both pipelines and verify the refs:

```bash
git ls-remote gitlab refs/heads/main refs/tags/vX.Y.Z
git ls-remote github refs/heads/main refs/tags/vX.Y.Z
```
