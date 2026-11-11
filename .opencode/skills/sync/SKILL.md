---
name: sync
description: >-
  Diagnose or perform explicitly requested recovery for pyku's one-way
  GitLab-to-GitHub push mirror. GitLab is always canonical.
---

# Recover GitLab-to-GitHub synchronization

Use this skill only when a maintainer explicitly requests mirror diagnosis or
recovery. GitLab is the only source of truth. Routine branch and tag
synchronization is handled by GitLab's push mirror; do not make independent
changes on GitHub, merge a GitHub pull request there, or push to GitLab from
GitHub. Never force-push or rewrite history.

The human runbook is `doc/contribute/maintainers.rst`. GitHub pull requests
must be imported as branches for review in GitLab; see
`.opencode/skills/gitlab-contribution/SKILL.md`.

## Diagnose the mirror

1. Check the working tree and remotes. Do not overwrite or discard local work.
   Use a clean checkout if the current one has unrelated changes.
2. Fetch both remotes and inspect the exact refs:

   ```bash
   git fetch --prune --tags gitlab
   git fetch --prune --tags github
   git status --short --branch
   git ls-remote gitlab refs/heads/main refs/tags/vX.Y.Z
   git ls-remote github refs/heads/main refs/tags/vX.Y.Z
   ```

   Replace `vX.Y.Z` with the tag being investigated. A tag may be omitted
   when investigating only `main`.
3. Check GitLab's **Settings > Repository > Mirroring repositories** status.
   Review the reported error and fix mirror credentials or configuration there;
   never expose tokens in chat, logs, or repository files.
4. If the refs match after the mirror runs, stop. No manual push is needed.
   If GitHub contains commits or a tag that is absent from GitLab, stop and
   ask the maintainer to resolve the unexpected GitHub-side change. Do not
   import it into canonical GitLab `main` automatically.

## Explicit manual recovery

Only proceed with an explicit maintainer request to manually update GitHub
while the built-in mirror is unavailable. Confirm GitLab's `main` and tag are
the intended canonical refs and that the maintainer understands GitHub will be
updated. Do not disable the configured mirror unless asked.

For `main`, fetch both remote refs, prove GitHub's `main` is an ancestor of
GitLab's `main`, and push that exact GitLab ref. This prevents local commits
from being published to GitHub. Stop if the ancestry test fails or the push is
rejected:

```bash
git fetch gitlab refs/heads/main:refs/remotes/gitlab/main
git fetch github refs/heads/main:refs/remotes/github/main
git merge-base --is-ancestor refs/remotes/github/main refs/remotes/gitlab/main
git push github refs/remotes/gitlab/main:refs/heads/main
```

For a release tag, first confirm the tag exists on GitLab and GitHub does not
have a different object with the same name. Push the existing GitLab tag
object only:

```bash
git ls-remote --tags gitlab refs/tags/vX.Y.Z
git ls-remote --tags github refs/tags/vX.Y.Z
git push github vX.Y.Z
```

Never create a replacement tag or use `--force`. Afterward verify the refs on
both hosts:

```bash
git ls-remote gitlab refs/heads/main refs/tags/vX.Y.Z
git ls-remote github refs/heads/main refs/tags/vX.Y.Z
```

If either check is ambiguous, a ref is divergent, or access is denied, stop
and report what was observed. Do not attempt bidirectional reconciliation or
touch the deprecated `master` branch. GitHub pull requests are imported
manually into GitLab using `.opencode/skills/gitlab-contribution/SKILL.md`;
GitLab's push mirror is the one-way path for updates from GitLab to GitHub.
