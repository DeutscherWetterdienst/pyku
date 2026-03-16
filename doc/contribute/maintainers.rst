Maintainers
===========

Maintainers possess elevated permissions in comparison to developers and carry
the crucial responsibility of upholding code integrity. Their duties encompass
not only integrating merge requests into the master branch but also overseeing
the creation of new releases. This pivotal role involves ensuring that the
codebase remains cohesive and robust, aligning with project objectives and
quality standards. Additionally, maintainers play a pivotal role in fostering
collaboration among team members, facilitating efficient code reviews, and
resolving conflicts to uphold the overall health of the software development
process.

KU color map
------------

The official DWD color map is integrated in pyku. Updates of the colormaps are
performed manually from the `official colormap repository
<https://gitlab.dwd.de/ku/libraries/ku_colors>`_. To do this, the file
``pyku/etc/base_colors.yaml`` in the pyku repository must be overwritten by the
file ``base_colors.yaml`` from the `official colormap repository
<https://gitlab.dwd.de/ku/libraries/ku_colors>`_.

Merge request
-------------

Upon submission of a merge request, an automated pipeline is triggered to build
and deploy the documentation, while also conducting doctests, unit tests and
integration testing. It is imperative not to proceed with merging to the master
branch until the pipeline has completed successfully. The status of the
pipeline can be monitored at the following link: `Pipeline Status
<https://gitlab.dwd.de/ku/libraries/pyku/-/pipelines>`_.

Once the pipeline has executed without errors, you may proceed to merge by
clicking the designated button. At this juncture, conducting a thorough code
review is highly encouraged before finalizing the merge, ensuring adherence to
coding standards and promoting overall code quality.

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

A new pipeline is triggered which deploys *pyku* to the ``pyku.stable``
environment module for use in production. It also creates a python wheel which
is then available in the `pypi registry set up on the KU gitlab server
<https://gitlab.dwd.de/ku/pypi/-/packages>`_.

.. rubric:: Create a new gitlab release

Create a new gitlab release for the new tag under
https://gitlab.dwd.de/ku/libraries/pyku/-/releases

Copy the content of the ``CHANGELOG.rst``, reformat from rst to the Markdown.

CI/CD Pipelines
---------------

.. code:: bash

   echo -n 'youpassword' | base64
   eW91cGFzc3dvcmQ=

To convert the password back, as is done in the pipeline:

.. code:: bash

   echo -n 'eW91cGFzc3dvcmQ=' | base64 --decode
   youpassword

.. rubric:: token for automated wheel deployment to to pypi registry

The ``ku/pypi`` repository servers as a local pypi registry for automated
deployment. At each release, the wheel is built and uploaded to the registry.
The token for automated deployment of the wheel is located in the *pyku*
repository under:

.. code:: bash

   cat .pypirc 
   [distutils]
   index-servers =
       gitlab

   [gitlab]
   repository = https://gitlab.dwd.de/api/v4/projects/1719/packages/pypi
   username = pypi
   password = the_password

The token is only valid for a limited time. Hence it must be renewed in the
gitlab interface of the *pypi* repository at:

https://gitlab.dwd.de/ku/pypi/-/settings/access_tokens

The token should be created with the following permissions:

* **Role**: ``developer``
* **Scope**: ``api``

Which then allows to write in the registry.
