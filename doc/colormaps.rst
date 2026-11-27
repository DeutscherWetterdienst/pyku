pyku.core.colourscales
######################

Use :mod:`pyku.core.colourscales` to build and inspect DWD KU colormaps.
See :doc:`tutorials/colormaps` for examples.

Migration note
==============

``pyku.colormaps`` remains available as a deprecated compatibility
layer. Its legacy ``kind="segmented"`` sampling can produce different
colors from ``kind="from_levels"`` in :mod:`pyku.core.colourscales`.
Compare rendered output when migrating plots where preserving their
existing appearance matters.

API
===

.. autofunction:: pyku.core.colourscales.get_colormap

.. autofunction:: pyku.core.colourscales.get_norm

.. autofunction:: pyku.core.colourscales.get_cmap

.. autofunction:: pyku.core.colourscales.get_cmap_colors

.. autofunction:: pyku.core.colourscales.get_cmap_names

.. autofunction:: pyku.core.colourscales.get_cmap_scale_names

.. autofunction:: pyku.core.colourscales.register_all
