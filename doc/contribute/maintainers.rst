Maintainers
###########

GitLab is the canonical home of pyku. Merge requests, the ``main`` branch,
releases, and release tags are managed on GitLab. GitHub is a downstream mirror
for visibility, GitHub Actions checks, and GitHub Pages. Never merge directly
into GitHub ``main`` or create release tags on GitHub.

Contribution workflow
=====================

Merge requests
--------------

Start with a clean checkout and remotes named ``gitlab`` and ``github``. For
a new checkout, clone GitLab and add GitHub as the mirror remote:

.. code:: bash

   git clone https://gitlab.dwd.de/ku/libraries/pyku.git pyku
   cd pyku
   git remote rename origin gitlab
   git remote add github git@github.com:DeutscherWetterdienst/pyku.git

For an existing checkout, confirm these remote names and keep GitLab as the
source remote. Check the worktree and update local ``main`` from GitLab before
creating a topic branch:

.. code:: bash

   git status --short --branch
   git remote -v
   git fetch gitlab
   git switch main
   git pull --ff-only gitlab main
   git switch -c feature/short-description

After making and reviewing the change, stage only its files, run the applicable
checks, and push the topic branch to GitLab:

.. code:: bash

   git add path/to/changed-file
   git diff --cached --check
   git diff --cached
   git commit -m "Describe the change"
   git push --set-upstream gitlab HEAD

Then follow these steps:

1. Open a merge request from the topic branch to GitLab ``main``.
2. Review the changes and wait for the required GitLab CI checks to pass.
3. Merge the request on GitLab.
4. Confirm GitLab's push mirror has updated GitHub ``main``. Check the mirror
   status in GitLab if it has not; do not push the merged commit to GitHub by
   hand during normal operation. Compare the remote refs with:

   .. code:: bash

      git ls-remote gitlab refs/heads/main
      git ls-remote github refs/heads/main

GitHub pull requests
--------------------

GitHub pull requests can still run GitHub Actions checks, but they are not the
place to review or merge contributions. Import the pull request's head branch
into GitLab and open a merge request there:

1. In a checkout with GitLab and GitHub remotes, fetch the pull request head
   (replace ``123`` with the pull request number):

   .. code:: bash

      git fetch github pull/123/head:github-pr-123
      git fetch gitlab main
      git log --oneline --decorate gitlab/main..github-pr-123
      git diff --stat gitlab/main...github-pr-123

2. Review the fetched commits and diff. If the branch contains unrelated or
   unexpected changes, stop and resolve them with the contributor before
   importing it.
3. Push the branch to GitLab. Choose a unique branch name if that name already
   exists there:

   .. code:: bash

      git push gitlab github-pr-123:github-pr-123

4. In GitLab, create a merge request from ``github-pr-123`` to ``main``. Link
   the original GitHub pull request in the MR description so the contributor
   can follow the GitLab review and CI results.
5. Review and merge the GitLab MR using the normal process. Leave the GitHub
   pull request unmerged and close it with a link to the GitLab MR after the
   contribution is integrated.

Configure the GitLab push mirror
--------------------------------

This one-time setup requires a GitLab maintainer and a GitHub fine-grained
personal access token. Create a token restricted to the pyku repository with
read and write access to repository contents. Also grant read and write access
to Workflows because the repository contains ``.github/workflows``. Keep the
token private; never put it in the repository or a command recorded in shell
history.

Configure the mirror in GitLab:

1. Open **Settings > Repository > Mirroring repositories** and expand the
   mirroring section.
2. Set the repository URL to
   ``https://github.com/DeutscherWetterdienst/pyku.git`` and the mirror
   direction to **Push**.
3. Choose **Username and Password** authentication. Enter the GitHub username
   of the token owner as the username and the personal access token as the
   password.
4. Leave **Only mirror protected branches** unchecked to mirror branches and
   tags. Select **Keep divergent refs** so unexpected GitHub-side changes are
   preserved and reported instead of silently overwritten. Set this when
   creating the mirror; GitLab requires the API to change it later.
5. Select **Mirror repository**, then **Update now**. Check for a successful
   update and confirm the GitLab ``main`` branch and release tags appear on
   GitHub.

GitLab's current instructions are at `Push mirroring`_.
Check mirror status after setup and after a failed update. Do not make
independent changes on GitHub or use manual pushes to mask a mirror failure.
Resolve any reported divergence before retrying the mirror.

Release workflow
================

Prepare a release
-----------------

1. Start from the current GitLab ``main`` and confirm the latest changes have
   passed GitLab CI.
2. Review the merge requests merged since the previous release and curate their
   user-facing changes. Create a release branch from ``main`` and update
   ``CHANGELOG.rst`` with the next version heading and applicable sections:
   New Features, Breaking changes, Deprecations, Bug fixes, Documentation, and
   Internal changes.
3. Push the branch to GitLab, open an MR targeting ``main``, wait for checks,
   and merge it.
4. Confirm the GitLab push mirror has updated GitHub ``main`` before creating
   the release tag.

The tag pipeline checks that the tag matches the newest ``vX.Y.Z`` heading in
``CHANGELOG.rst`` and that the section contains release notes. A mismatch or
empty section fails the release pipeline before publishing.
Sections containing only headings or comments also fail validation. CI renders
the validated reStructuredText as HTML for the GitLab Release description.

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
existing ``v*`` tags. Pyku uses ``setuptools_scm`` to derive its version from
Git tags. Confirm the chosen tag does not already exist on GitLab:

.. code:: bash

   git ls-remote --tags gitlab refs/tags/vX.Y.Z

After the release MR is merged, update local ``main`` from GitLab, check that
the mirror has caught up, then create and push one annotated tag to GitLab:

.. code:: bash

   git fetch --prune --tags gitlab
   git fetch --prune --tags github
   git switch main
   git pull --ff-only gitlab main
   git ls-remote gitlab refs/heads/main
   git ls-remote github refs/heads/main
   git tag -a vX.Y.Z -m "pyku vX.Y.Z"
   git push gitlab vX.Y.Z

GitLab's push mirror propagates the tag to GitHub. Do not push the tag to
GitHub separately. Check the GitLab release pipeline and GitHub Actions run,
then verify that both hosts have the expected ``main`` commit and tag:

.. code:: bash

   git ls-remote gitlab refs/heads/main refs/tags/vX.Y.Z
   git ls-remote github refs/heads/main refs/tags/vX.Y.Z

The GitLab pipeline publishes the package to the internal PyPI, updates the
``pyku.latest`` module, deploys GitLab Pages, and creates a GitLab Release using
the matching changelog section. GitHub Actions tests the mirrored commit and
deploys GitHub Pages. Pushes to ``main`` also deploy the current documentation
on both hosts; a tag deployment replaces that same current site. Preserving
versioned documentation is tracked in `work item 343`_.

GitLab Pages deployments share the ``pages`` resource group and environment.
In **Settings > CI/CD > General pipelines**, keep **Prevent outdated deployment
jobs** enabled and **Allow job retries for rollback deployments** disabled.
These settings prevent an older pipeline or retry from replacing newer docs.

If the GitLab push mirror fails or the remote refs diverge, do not force-push.
Follow the guarded recovery steps in ``.opencode/skills/sync/SKILL.md`` and
resolve the mirror status before continuing. GitHub-originated pull requests
are imported manually into GitLab using the process described above; automatic
forwarding is not part of the agreed workflow.

Keep this page and ``.opencode/skills/release/SKILL.md`` synchronized whenever
the release process changes. GitLab contribution steps for OpenCode agents are
in ``.opencode/skills/gitlab-contribution/SKILL.md``.


.. _Push mirroring: https://docs.gitlab.com/user/project/repository/mirror/push/
.. _work item 343: https://gitlab.dwd.de/ku/libraries/pyku/-/work_items/343
