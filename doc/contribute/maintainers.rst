Maintainers
###########

Maintainers review contributions, protect the project's code quality, and
coordinate releases. Pyku supports GitLab and GitHub as source hosts. For each
change or release, choose one host as the source, then synchronize its ``main``
branch and release tags to the other host. Do not make independent changes on
both hosts at the same time.

Contribution workflow
=====================

Merge requests and pull requests
--------------------------------

1. Choose GitLab or GitHub as the source host for the change.
2. Open a merge request or pull request targeting ``main`` on that host.
3. Review the code and wait for that host's required checks to pass.
4. Merge the request.
5. Synchronize the merged ``main`` commit to the other host using the
   instructions below.

Synchronize main
----------------

Use a clean checkout with remotes named ``gitlab`` and ``github``. When
cloning from GitLab, configure the remotes like this:

.. code:: bash

   git clone https://gitlab.dwd.de/ku/libraries/pyku.git pyku-sync
   cd pyku-sync
   git remote rename origin gitlab
   git remote add github git@github.com:DeutscherWetterdienst/pyku.git

When cloning from GitHub, configure them in the opposite order:

.. code:: bash

   git clone git@github.com:DeutscherWetterdienst/pyku.git pyku-sync
   cd pyku-sync
   git remote rename origin github
   git remote add gitlab https://gitlab.dwd.de/ku/libraries/pyku.git

Fetch both hosts before synchronizing:

.. code:: bash

   git fetch --prune --tags gitlab
   git fetch --prune --tags github
   git switch main

For a GitLab-sourced change, update the local branch from GitLab and
fast-forward GitHub:

.. code:: bash

   git pull --ff-only gitlab main
   git merge-base --is-ancestor github/main main
   git push github main:main

For a GitHub-sourced change, reverse the host names:

.. code:: bash

   git pull --ff-only github main
   git merge-base --is-ancestor gitlab/main main
   git push gitlab main:main

The ancestry check must succeed before pushing. If it fails or the push is
rejected, stop and ask the maintainers to reconcile the branch histories.
Resume only when the source commit can be fast-forwarded onto the other host.
Never force-push to synchronize the hosts. After synchronization, verify that
both remote branches identify the same commit:

.. code:: bash

   git ls-remote gitlab refs/heads/main
   git ls-remote github refs/heads/main

The ``master`` branch is deprecated. Do not merge changes into it or use it as
a release branch. GitLab CI must not run branch pipelines for ``master``.

Release workflow
================

Prepare a release
-----------------

1. Choose GitLab or GitHub as the source host for the release. Do not merge
   other changes independently on the other host during the release.
2. Start from the source host's current ``main`` and verify its merge
   request or pull request checks passed.
3. Create a release branch from that ``main`` and update ``CHANGELOG.rst``.
   Add the next version heading and organize changes under the applicable
   sections:
   New Features, Breaking changes, Deprecations, Bug fixes, Documentation,
   and Internal changes.
4. Stage, review, commit, and push the release branch. Open an MR or PR
   targeting ``main``, wait for checks, and merge it.
5. Fetch both hosts again, update the local ``main`` from the source host, then
   synchronize it to the other host using the commands above. Both ``main``
   branches must be at the same commit before tagging.

For a GitLab-sourced release, create and push the release branch:

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

For a GitHub-sourced release, use ``github`` as the remote:

.. code:: bash

   git switch main
   git pull --ff-only github main
   git switch -c release/vX.Y.Z
   # Edit CHANGELOG.rst for vX.Y.Z.
   git add CHANGELOG.rst
   git diff --cached --check
   git diff --cached
   git commit -m "Update changelog for vX.Y.Z"
   git push github release/vX.Y.Z

After merging the MR or PR, fetch both hosts again and switch back to ``main``
before using the source-specific synchronization commands above:

.. code:: bash

   git fetch --prune --tags gitlab
   git fetch --prune --tags github
   git switch main

Create and publish the version tag
----------------------------------

Use the next version according to the project's semantic versioning and
existing ``v*`` tags. Pyku uses ``setuptools_scm`` to derive its version from
Git tags. Check that the chosen tag does not already exist on either host:

.. code:: bash

   git ls-remote --tags gitlab refs/tags/vX.Y.Z
   git ls-remote --tags github refs/tags/vX.Y.Z

Create an annotated tag once, on the selected source host's synchronized
``main`` commit, then push that same tag to both hosts. For a GitLab-sourced
release:

.. code:: bash

   git tag -a vX.Y.Z -m "pyku vX.Y.Z"
   git push gitlab vX.Y.Z
   git push github vX.Y.Z

For a GitHub-sourced release, push the tag to GitHub first:

.. code:: bash

   git tag -a vX.Y.Z -m "pyku vX.Y.Z"
   git push github vX.Y.Z
   git push gitlab vX.Y.Z

Pushing the tag starts each host's tag pipeline; it does not create a GitLab
or GitHub Release page entry. The GitLab pipeline publishes the package to the
internal PyPI, updates the ``pyku.latest`` module, and deploys GitLab Pages.
The GitHub workflow builds and tests the package and deploys GitHub Pages.
Check both pipelines and confirm that both hosts have the same tag and
``main`` commit:

.. code:: bash

   git ls-remote gitlab refs/heads/main refs/tags/vX.Y.Z
   git ls-remote github refs/heads/main refs/tags/vX.Y.Z

Keep this page and ``.opencode/skills/release/SKILL.md`` synchronized whenever
the release process changes. The release skill provides the same workflow for
OpenCode agents.
