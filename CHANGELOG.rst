v1.2.0
------

New Features
~~~~~~~~~~~~

* Add a dataset visualization accessor for maps, metrics, climatologies,
  time series, diurnal cycles, and variability plots.

Bug fixes
~~~~~~~~~

* Correct CMOR variable mappings and resampling for supported datasets.
* Fix georeferencing for rotated latitude-longitude coordinates.

Documentation
~~~~~~~~~~~~~

* Expand visualization documentation and tutorials, and improve
  documentation builds.
* Document the GitLab-canonical contribution, release, and mirror workflows.

Internal changes
~~~~~~~~~~~~~~~~

* Align CI and release workflows with GitLab as the canonical host, including
  changelog validation and GitLab Release-note publishing.
* Improve data caching and test coverage; close async clients used for
  test-data downloads.

v1.1.3
------

Bug fixes
~~~~~~~~~

* Fix the CLIX core function call by removing unsupported keyword arguments.

v1.0.0
------

* Initial stable version of pyku
