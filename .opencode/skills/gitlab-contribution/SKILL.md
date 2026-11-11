---
name: gitlab-contribution
description: >-
  Prepare and submit pyku changes through canonical GitLab branches and merge
  requests, including importing GitHub pull request branches for review.
---

# Contribute to pyku on GitLab

Use this skill when asked to submit pyku changes to GitLab. GitLab is the
canonical repository: merge requests target GitLab `main`; maintainers
manually synchronize merged GitLab refs to GitHub. Do not merge GitHub PRs,
force-push, or make independent changes on GitHub.
Do not install missing CLIs or expose credentials; report blockers and give the
maintainer the next step.

The human contribution and release runbook is
`doc/contribute/maintainers.rst`. Use `.opencode/skills/release/SKILL.md` for
release preparation and `.opencode/skills/sync/SKILL.md` for manual
GitLab-to-GitHub synchronization.

## Submit changes from the current checkout

1. Inspect the repository root, branch, remotes, and working tree. Confirm this
   is pyku and that `gitlab` points to
   `https://gitlab.dwd.de/ku/libraries/pyku.git` or its SSH equivalent. Do not
   change remote configuration without asking.
2. Review all staged and unstaged changes. Preserve unrelated user work; never
   stage everything blindly, discard changes, or amend an existing commit
   without permission. If the branch is `main`, detached, or otherwise unsafe
   to publish, stop and ask before creating or switching branches.
3. Confirm the intended changes are committed, or stage only the requested
   files and create a clear commit if submitting the work includes committing.
   Run the applicable project checks and inspect `git diff --check` and the
   exact commits to be pushed.
4. Fetch GitLab `main` and inspect the branch relationship. Do not rebase,
   reset, or rewrite the user's branch without explicit permission. If the
   local branch is behind or diverged in a way that blocks a safe push, stop
   and explain the issue.
5. Push only the current topic branch, without force:

   ```bash
   git fetch gitlab main
   git push --set-upstream gitlab HEAD
   ```

   If the push is rejected or the remote branch already contains unrelated
   commits, stop; do not force-push or overwrite it.
6. Create a GitLab MR from the topic branch to `main`. If `glab` is installed
   and authenticated for `gitlab.dwd.de`, use it after preparing a concise
   title and description:

   ```bash
   glab mr create --target-branch main --title "<title>" \
     --description "<summary and test results>"
   ```

   If the CLI is unavailable or unauthenticated, do not install it or handle
   credentials. Give the maintainer the branch name, commit summary, test
   results, and the GitLab project URL
   `https://gitlab.dwd.de/ku/libraries/pyku/-/merge_requests/new`, and ask them
   to create the MR in the browser.
7. Report the pushed branch, commit(s), checks, and MR URL or browser action
   needed. Do not merge the MR unless the user separately asks and the
   repository's review and CI requirements are satisfied.

## Import a GitHub pull request for GitLab review

Do not merge the GitHub PR. Import its head branch to GitLab, then open a GitLab
MR against `main`:

1. Confirm the GitHub remote points to
   `git@github.com:DeutscherWetterdienst/pyku.git` or its HTTPS equivalent and
   check the working tree is clean. Use a clean checkout if it is not.
2. Fetch the pull request head into a new local branch (`123` is its number):

   ```bash
   git fetch github pull/123/head:github-pr-123
   git fetch gitlab main
   git log --oneline --decorate gitlab/main..github-pr-123
   git diff --stat gitlab/main...github-pr-123
   ```

3. Review the complete diff and commits, including files changed. Stop if it
   includes unexpected content or if its base differs from GitLab `main` in a
   way that makes the proposed MR unclear. Do not merge `main` into the branch
   or rewrite its commits automatically.
4. Push the imported branch to GitLab, using a unique branch name if the
   destination already exists:

   ```bash
   git push gitlab github-pr-123:github-pr-123
   ```

5. Create an MR from the imported branch to GitLab `main`, link the original
   GitHub PR in the description, and follow the submission/reporting guidance
   above. The GitLab MR is the authoritative review; leave the GitHub PR
   unmerged. After the GitLab MR is merged, the maintainer can close the GitHub
   PR with a link to it.

If importing or pushing is rejected, stop and report the exact branch/ref
conflict. Never resolve it with a force-push. After a GitLab MR is merged,
the maintainer manually synchronizes GitHub `main` using
`.opencode/skills/sync/SKILL.md`.
