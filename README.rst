.. |github-badge| image:: https://img.shields.io/badge/github-repo-blue?style=flat&logo=github
  :target: https://github.com/deutscherwetterdienst/pyku
  :alt: GitHub Repository

.. |docs-badge| image:: https://img.shields.io/badge/docs-gh--pages-blue?style=flat&logo=github
   :target: https://deutscherwetterdienst.github.io/pyku/
   :alt: Documentation Status

.. |issue-github-badge| image:: https://img.shields.io/badge/Issues-View%20on%20GitHub-blue
  :target: https://github.com/deutscherwetterdienst/pyku/issues
  :alt: GitHub Issues

|github-badge| |docs-badge| |issue-github-badge|

Comprehensive climate data handling with Xarray
-----------------------------------------------

Pyku is an extension built on **xarray** for working with climate data.
It provides tools to read, manipulate, validate, and analyze climate
datasets while handling metadata and geospatial information in a
consistent way.

* **Geospatial data handling**

  * Define standardized geographic projections
  * Read metadata to build area definitions (PROJ, WKT, CF)
  * Convert between raster and vector formats
  * Create and apply masks from polygons or files

* **Climate metadata handling**

  * Handle time bounds, units, coordinates, and variable metadata
  * Interpret CMOR-like metadata to infer variable names and convert units
  * Write standardized CMOR-like data paths and files

* **Validation and quality control**

  * Detect inconsistencies in units, time bounds, and frequencies
  * Compare datasets to identify differences in coordinates and metadata

* **Climate analysis utilities**

  * Resample time series while preserving climate metadata
  * Compute DWD-specific climate indices
  * Perform downscaling operations
  * Perform bias adjustement operations

* **Convenience utilities**

  * Define ensembles
  * Provide dedicated colormaps for climate variables
  * Download standardized polygon datasets on demand
  * Provide test datasets for unit testing
  * Basic plotting and quantity visualization

Acknowledgments
---------------

Special thanks to `Seth Woodworth <https://github.com/sethwoodworth>`_ for his
generosity in transferring the PyPI package name **pyku**. Seth originally
established the name as an English portmanteau of "Python" and "Haiku." It is
now being repurposed for the **py Klima und Umwelt** project.

