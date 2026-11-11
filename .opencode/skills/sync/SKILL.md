---
name: sync
description: >-
  Manually synchronize pyku's canonical GitLab branches and release tags to
  GitHub, with guarded ref and ancestry checks.
---

# Synchronize GitLab to GitHub

GitLab is the canonical repository. GitHub is updated manually after GitLab
changes. Use this skill for routine one-way synchronization of merged `main`
and individual release tags. Never force-push, delete refs, push all tags, or
make independent changes on GitHub.

The human runbook is `doc/contribute/maintainers.rst`. GitHub pull requests
must be imported as branches for review in GitLab; see
`.opencode/skills/gitlab-contribution/SKILL.md`.

## Before synchronizing

1. Check the working tree, current branch, and remote URLs. Do not overwrite or
   discard local work. Use a clean checkout if unrelated changes are present.
2. Fetch and inspect the exact refs to be synchronized:

   ```bash
   git fetch gitlab refs/heads/main:refs/remotes/gitlab/main
   git fetch github refs/heads/main:refs/remotes/github/main
   git ls-remote gitlab refs/heads/main
   git ls-remote github refs/heads/main
   ```

3. Stop if access is denied, a ref is missing unexpectedly, or the remote URLs
   are not the expected pyku repositories. GitLab remains canonical.

## Synchronize `main`

After a GitLab MR is merged, prove that GitHub `main` is an ancestor of GitLab
`main`. This permits a fast-forward only and prevents overwriting commits on
GitHub. If the check fails, stop and ask the maintainer to resolve the
divergence; never force-push or merge GitHub changes into canonical `main`
automatically.

```bash
git merge-base --is-ancestor \
  refs/remotes/github/main refs/remotes/gitlab/main
```

Proceed with the push only when the ancestry check succeeds. If both refs
already match, no push is needed. After a successful push, verify the `main`
object IDs on both hosts match. If a push is rejected or refs do not match,
stop and report the observed refs.

```bash
git push github refs/remotes/gitlab/main:refs/heads/main
git ls-remote gitlab refs/heads/main
git ls-remote github refs/heads/main
```

## Synchronize one release tag

Create and push the annotated tag on GitLab first, after confirming the release
commit is the synchronized `main` commit. Check the exact tag ref on both hosts.
Push only the existing GitLab tag object to GitHub; do not create a second tag
or push all tags because historical refs can differ between hosts.

```bash
git ls-remote --tags gitlab refs/tags/vX.Y.Z
git ls-remote --tags github refs/tags/vX.Y.Z
```

Push only if GitLab has the intended tag and GitHub does not have that name.
If GitHub already has the same tag object, no push is needed. If refs differ,
stop; never delete or replace a tag. When GitHub lacks the tag, fetch the
canonical GitLab object to a separate local ref, then push that exact object
and verify:

```bash
git fetch gitlab refs/tags/vX.Y.Z:refs/pyku-sync/tags/vX.Y.Z
git push github refs/pyku-sync/tags/vX.Y.Z:refs/tags/vX.Y.Z
git ls-remote --tags gitlab refs/tags/vX.Y.Z
git ls-remote --tags github refs/tags/vX.Y.Z
```

Do not touch the deprecated `master` branch. Report any divergence, denied
access, or ambiguous result instead of attempting a destructive recovery.
