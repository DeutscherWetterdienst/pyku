Maintainers
===========

Maintainers possess elevated permissions in comparison to developers and carry
the responsibility of upholding code integrity. Their duties encompass not only
integrating merge requests into the master branch but also overseeing the
creation of new releases. This role involves ensuring that the codebase remains
cohesive and robust, aligning with project objectives and quality standards.
Additionally, maintainers play a pivotal role in fostering collaboration among
team members, facilitating efficient code reviews, and resolving conflicts to
uphold the overall health of the software development process.

Pull request
-------------

Upon submission of a merge request, an automated pipeline is triggered to build
and deploy the documentation, while also conducting doctests, unit tests and
integration testing. It is imperative not to proceed with merging to the main
branch until the pipeline has completed successfully. The status of the
pipeline can be monitored in the action tab. Only once the pipeline has
executed without errors may you proceed to merge.

.. rubric:: Checklist

* Review the code
* Merge to master
* Update the Changelog from master and commit

.. rubric:: Code review

Review the code.

.. rubric:: Merge

Merge after reviewing the code

.. rubric:: Update CHANGELOG.rst

Checkout master, pull, update the CHANGELOG, and commit. Review
``CHANGELOG.rst`` and modify if needed. the sections are:

* New Features
* Breaking changes
* Deprecations
* Bug fixes
* Documentation
* Internal changes

Release
-------

.. rubric:: Checklist

* Checkout master and pull
* Update the changelog, commit and push
* Create a new tag
* Create a gitlab release for the new tag

.. rubric:: Checkout master and pull

.. code:: bash

   git checkout master
   git pull

.. rubric:: Update ``CHANGELOG.rst``

Open ``CHANGELOG.rst``, change tag to next version, commit and push.

.. rubric:: Create new tag

Check the existing tags:

.. code:: bash

   git tag

   0.3.5
   0.3.6
   0.3.7
   0.3.8

The first number if for a major release that may have breaking changes. The
second number is when a new feature is added. The last number is for
improvements, bug fixes and minor modifications.

Now you can increment to e.g ``0.3.9``.

.. code:: bash

   git tag 0.3.9

Now you can push the tag to the remote:

.. code:: bash

   git push --tags

A new pipeline is triggered which deploys the pyku documentation.
