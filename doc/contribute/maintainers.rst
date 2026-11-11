Maintainers
###########

GitLab is the canonical home of pyku. Merge requests, the ``main``
branch, releases, and release tags are managed on GitLab. GitHub is
updated manually after GitLab changes for visibility, GitHub Actions
checks, and GitHub Pages. Never make independent changes on GitHub or
merge pull requests there.

Contribution workflow
=====================

Merge requests
--------------

Start with a clean checkout and remotes named ``gitlab`` and ``github``.
For a new checkout, clone GitLab and add GitHub as the downstream
remote:

.. code:: bash

   git clone https://gitlab.dwd.de/ku/libraries/pyku.git pyku
   cd pyku
   git remote rename origin gitlab
   git remote add github git@github.com:DeutscherWetterdienst/pyku.git

For an existing checkout, confirm these remote names and keep GitLab as
the source remote. Check the worktree and update local ``main`` from
GitLab before creating a topic branch:

.. code:: bash

   git status --short --branch
   git remote -v
   git fetch gitlab
   git switch main
   git pull --ff-only gitlab main
   git switch -c feature/short-description

After making and reviewing the change, stage only its files, run the
applicable checks, and push the topic branch to GitLab:

.. code:: bash

   git add path/to/changed-file
   git diff --cached --check
   git diff --cached
   git commit -m "Describe the change"
   git push --set-upstream gitlab HEAD

Then follow these steps:

#. Open a merge request from the topic branch to GitLab ``main``.
#. Review the changes and wait for the required GitLab CI checks to
   pass.
#. Merge the request on GitLab.
#. Manually synchronize GitHub ``main`` from GitLab after the merge,
   using the safe fast-forward procedure below.

GitHub pull requests
--------------------

GitHub pull requests can still run GitHub Actions checks, but they are
not the place to review or merge contributions. Import the pull
request's head branch into GitLab and open a merge request there:

#. In a checkout with GitLab and GitHub remotes, fetch the pull request
   head (replace ``123`` with the pull request number):

   .. code:: bash

      git fetch github pull/123/head:github-pr-123
      git fetch gitlab main
      git log --oneline --decorate gitlab/main..github-pr-123
      git diff --stat gitlab/main...github-pr-123

#. Review the fetched commits and diff. If the branch contains unrelated
   or unexpected changes, stop and resolve them with the contributor
   before importing it.

#. Push the branch to GitLab. Choose a unique branch name if that name
   already exists there:

   .. code:: bash

      git push gitlab github-pr-123:github-pr-123

#. In GitLab, create a merge request from ``github-pr-123`` to ``main``.
   Link the original GitHub pull request in the MR description so the
   contributor can follow the GitLab review and CI results.

#. Review and merge the GitLab MR using the normal process. Leave the
   GitHub pull request unmerged and close it with a link to the GitLab
   MR after the contribution is integrated.

Synchronize GitHub main
-----------------------

After each GitLab merge to ``main``, update GitHub manually. Use remotes
named ``gitlab`` and ``github``. Check the refs, fetch their exact
``main`` branches, and verify GitHub is an ancestor of GitLab before
pushing. If refs differ unexpectedly or the ancestry check fails, stop.
Never force-push, overwrite divergent work, or push all branches or
tags.

.. code:: bash

   git ls-remote gitlab refs/heads/main
   git ls-remote github refs/heads/main
   git fetch gitlab refs/heads/main:refs/remotes/gitlab/main
   git fetch github refs/heads/main:refs/remotes/github/main
   git merge-base --is-ancestor \
       refs/remotes/github/main refs/remotes/gitlab/main

Proceed only when the ancestry command succeeds. If both refs already
match, no push is needed. Otherwise push only GitLab's ``main`` ref to
GitHub and verify both refs match afterward:

.. code:: bash

   git push github refs/remotes/gitlab/main:refs/heads/main
   git ls-remote gitlab refs/heads/main
   git ls-remote github refs/heads/main

Release workflow
================

Prepare a release
-----------------

#. Start from the current GitLab ``main`` and confirm the latest changes
   have passed GitLab CI. Use a clean checkout with remotes named
   ``gitlab`` and ``github``.

#. Review the merge requests merged since the previous release and
   curate their user-facing changes. Create a release branch from
   ``main`` and update ``CHANGELOG.rst`` with the next version heading
   and applicable sections: New Features, Breaking changes,
   Deprecations, Bug fixes, Documentation, and Internal changes.

#. Push the branch to GitLab, open an MR targeting ``main``, wait for
   checks, and merge it.

#. After the merge, run the release script. It
   synchronizes ``main`` to GitHub when safe, verifies the refs and
   changelog, asks you to confirm the GitLab ``main`` pipeline passed,
   then creates and pushes the annotated tag to GitLab.

The tag pipeline checks that the tag matches the newest ``vX.Y.Z``
heading in ``CHANGELOG.rst`` and that the section contains release
notes. A mismatch or empty section fails the release pipeline before
publishing. Sections containing only headings or comments also fail
validation. CI renders the validated reStructuredText as HTML for the
GitLab Release description.

For example, prepare a release branch as follows, replacing ``X.Y.Z``
with the next semantic version:

.. code:: bash

   git switch main
   git pull --ff-only gitlab main
   git switch -c release/vX.Y.Z
   # Edit CHANGELOG.rst for vX.Y.Z.
   git add CHANGELOG.rst
   git diff --cached --check
   git diff --cached
   git commit -m "Update changelog for vX.Y.Z"
   git push gitlab release/vX.Y.Z

Create and publish the version tag
----------------------------------

Pyku uses ``setuptools_scm`` to derive its version from Git tags. The
release helper requires Bash and Git and does not use ``glab``. Its help
is available with:

.. code:: bash

   bash scripts/release.sh --help

After the changelog MR is merged, run the ``tag`` stage with the same
version as the newest changelog heading:

.. code:: bash

   bash scripts/release.sh tag --release-version vX.Y.Z

The script stops if the worktree is not clean, the requested version is
not the newest changelog heading, the tag already exists, the remotes
are unexpected, or GitHub ``main`` is not an ancestor of GitLab
``main``. It never force-pushes or overwrites divergent refs. Confirm
the displayed GitLab ``main`` pipeline succeeded before answering ``y``
to the prompt. The script then pushes the annotated tag to GitLab.

Wait for the GitLab tag pipeline to succeed. Then sync only that tag to
GitHub:

.. code:: bash

   bash scripts/release.sh sync-tag --release-version vX.Y.Z

Confirm the displayed GitLab tag pipeline succeeded when prompted. The
script pushes only the requested tag, verifies the tag object and target
commit on both hosts, and stops if GitHub already has a different tag.
It does not delete or replace tags or push all tags.

The script can be run from any directory in the checkout. Both stages
require a clean worktree and the ``gitlab`` and ``github`` remotes to
point to the pyku repositories. After the GitHub tag workflow passes,
it creates a GitHub Release from the same changelog notes; GitLab
remains the canonical release. The GitHub repository must allow the
workflow token to create releases.

Verify the expected ``main`` commit and tag on both hosts if you need to
inspect the result manually:

.. code:: bash

   git ls-remote gitlab refs/heads/main refs/tags/vX.Y.Z
   git ls-remote github refs/heads/main refs/tags/vX.Y.Z

The GitLab pipeline publishes the package to the pyku project's package
registry, updates the ``pyku.latest`` module, deploys GitLab Pages, and
creates a GitLab Release using the matching changelog section. GitHub
Actions and GitHub Pages run after the corresponding ``main`` commit or
release tag is pushed there manually. The tag workflow creates a GitHub
Release after its checks pass. A tag deployment replaces the
current docs site. Preserving versioned documentation is tracked in
`work item 343`_.

GitLab Pages deployments share the ``pages`` resource group and
environment. In **Settings > CI/CD > General pipelines**, keep **Prevent
outdated deployment jobs** enabled and **Allow job retries for rollback
deployments** disabled. These settings prevent an older pipeline or
retry from replacing newer docs.

If either remote ref is divergent, a push is rejected, or access is
denied, stop and follow ``.opencode/skills/sync/SKILL.md``. Never
force-push or overwrite a divergent ref. GitHub-originated pull requests
are imported manually into GitLab using the process described above.

Keep this page and ``.opencode/skills/release/SKILL.md`` synchronized
whenever the release process changes. GitLab contribution steps for
OpenCode agents are in
``.opencode/skills/gitlab-contribution/SKILL.md``.

.. _work item 343: https://gitlab.dwd.de/ku/libraries/pyku/-/work_items/343
