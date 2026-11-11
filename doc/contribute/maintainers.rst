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
   have passed GitLab CI.

#. Review the merge requests merged since the previous release and
   curate their user-facing changes. Create a release branch from
   ``main`` and update ``CHANGELOG.rst`` with the next version heading
   and applicable sections: New Features, Breaking changes,
   Deprecations, Bug fixes, Documentation, and Internal changes.

#. Push the branch to GitLab, open an MR targeting ``main``, wait for
   checks, and merge it.

#. Manually synchronize GitHub ``main`` from GitLab and verify the refs
   match before creating the release tag.

The tag pipeline checks that the tag matches the newest ``vX.Y.Z``
heading in ``CHANGELOG.rst`` and that the section contains release
notes. A mismatch or empty section fails the release pipeline before
publishing. Sections containing only headings or comments also fail
validation. CI renders the validated reStructuredText as HTML for the
GitLab Release description.

For example, prepare a release branch as follows:

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

Use the next version according to the project's semantic versioning and
existing ``v*`` tags. Pyku uses ``setuptools_scm`` to derive its version
from Git tags. Confirm the chosen tag does not already exist on either
host:

.. code:: bash

   git ls-remote --tags gitlab refs/tags/vX.Y.Z
   git ls-remote --tags github refs/tags/vX.Y.Z

After the release MR is merged, update local ``main`` from GitLab and
verify GitHub ``main`` matches. Create and push one annotated tag to
GitLab first:

.. code:: bash

   git fetch --prune --tags gitlab
   git fetch --prune --tags github
   git switch main
   git pull --ff-only gitlab main
   git ls-remote gitlab refs/heads/main
   git ls-remote github refs/heads/main
   git tag -a vX.Y.Z -m "pyku vX.Y.Z"
   git push gitlab vX.Y.Z

Wait for the GitLab release pipeline to succeed. Check that the GitHub
tag is absent or already matches the GitLab tag object. If it is absent,
push only this release tag; stop if it differs. Never delete or replace
a tag, and do not push all tags:

.. code:: bash

   git ls-remote --tags gitlab refs/tags/vX.Y.Z
   git ls-remote --tags github refs/tags/vX.Y.Z
   git push github vX.Y.Z

Verify the expected ``main`` commit and tag on both hosts:

.. code:: bash

   git ls-remote gitlab refs/heads/main refs/tags/vX.Y.Z
   git ls-remote github refs/heads/main refs/tags/vX.Y.Z

The GitLab pipeline publishes the package to the pyku project's package
registry, updates the ``pyku.latest`` module, deploys GitLab Pages, and
creates a GitLab Release using the matching changelog section. GitHub
Actions and GitHub Pages run after the corresponding ``main`` commit or
release tag is pushed there manually. A tag deployment replaces the
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
