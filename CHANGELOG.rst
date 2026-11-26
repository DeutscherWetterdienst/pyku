v1.3.0
------

New Features
~~~~~~~~~~~~

* Add xvec-indexed geometry datasets and polygon-value maps. Add
  ``aggregate_by_region`` for regional statistics with centroid or
  area-overlap cell selection while keeping ``regionalize`` grid-preserving.
* Expose Dataset LOESS through ``pyku.compute.calc_loess`` and
  ``ds.pyku.calc_loess``, with configurable frequency and time reduction.

Deprecations
~~~~~~~~~~~~

* Deprecate ``pyku.loess.calc_loess`` in favor of
  ``pyku.compute.calc_loess`` while retaining the old API as a forwarding
  wrapper.

Bug fixes
~~~~~~~~~

* Preserve non-spatial CF metadata, including scalar CRS and time-bounds
  metadata, when clipping datasets to polygons.

Documentation
~~~~~~~~~~~~~

* Update polygon and LOESS tutorials and API documentation for geometry
  regionalization and Dataset-level LOESS workflows.

Internal changes
~~~~~~~~~~~~~~~~

* Add ``xvec`` as a direct dependency.

v1.2.2
------

Documentation
~~~~~~~~~~~~~

* Update the maintainer runbook and release guidance to use the release
  helper for tagging and GitLab-to-GitHub synchronization.

Internal changes
~~~~~~~~~~~~~~~~

* Add a parameterized release helper with pipeline confirmations and guarded
  synchronization of ``main`` and individual release tags. Keep unrelated
  local tags private even when ``push.followTags`` is enabled.
* Create GitHub Releases from changelog notes after tag checks and Pages
  deployment pass.

v1.2.1
------

Documentation
~~~~~~~~~~~~~

* Document the manual synchronization of GitLab ``main`` and release tags
  to GitHub.

Internal changes
~~~~~~~~~~~~~~~~

* Publish releases to pyku's project package registry and authenticate
  ``pyku.latest`` installs with the GitLab CI job token.

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
