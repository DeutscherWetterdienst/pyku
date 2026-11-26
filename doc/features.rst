pyku.features
#############

Grid-preserving regionalization
===============================

Use :func:`pyku.features.regionalize` to mask the grid independently for each
polygon. It retains spatial dimensions; a dataset with ``time``, ``y``, and
``x`` dimensions typically produces ``region, time, y, x`` data. This is
also available as ``ds.pyku.regionalize(gdf)``.

Aggregation by region
=====================

Use :func:`pyku.features.aggregate_by_region` when reduced values are wanted.
It accepts a GeoDataFrame and returns an xvec-indexed Dataset, usually with
``geometry, time`` dimensions (plus retained non-spatial dimensions).

.. code-block:: python

    regional = pyku.features.aggregate_by_region(
        ds,
        gdf,
        statistic="mean",
        cell_selection="area",
    )

With ``cell_selection="area"``, area fractions weight the mean. ``sum``,
``min``, ``max``, ``median``, and ``std`` operate on selected cells without
area weighting. ``weighted_sum`` uses per-region normalized weights and is
not a conservative area integral. The Dataset accessor is
``ds.pyku.aggregate_by_region(gdf, ...)``.

Clipping
========

:func:`pyku.features.clip_to_geometry` crops a grid to a polygon and masks
spatial fields. Non-spatial variables such as scalar CRS metadata and time
bounds retain their dimensions and values.

.. automodule:: pyku.features
    :members:
    :undoc-members:
    :show-inheritance:
