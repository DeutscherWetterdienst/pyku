DWD KU colormaps
################

*pyku* provides DWD KU reference colormaps for consistent use across projects.
The supported API is in :mod:`pyku.core.colourscales`.

Import the API
==============

Import the functions used in these examples, together with Matplotlib and
NumPy:

.. ipython::
   :okwarning:

   In [1]: import matplotlib.pyplot as plt
      ...: import numpy as np
      ...: from pyku.core.colourscales import (
      ...:     get_cmap,
      ...:     get_cmap_colors,
      ...:     get_cmap_names,
      ...:     get_cmap_scale_names,
      ...:     get_colormap,
      ...: )

Discover palettes and scales
============================

List available palettes and the explicitly configured named scales. The
implicit ``default`` scale is available for every palette but is not included
in the named-scale list.

.. ipython::
   :okwarning:

   In [2]: get_cmap_names()[:5]
   In [3]: get_cmap_scale_names("temp_ano")

All DWD KU colormaps
====================

See every configured palette at a glance. This plot uses each palette's
default scale; named scales are not shown.

.. plot::

   import matplotlib.pyplot as plt
   import numpy as np
   from pyku.core.colourscales import get_cmap, get_cmap_names

   names = get_cmap_names()
   samples = np.linspace(0.0, 1.0, 256)
   strips = np.array(
       [get_cmap(name)(samples) for name in names]
   )
   fig, ax = plt.subplots(figsize=(9, 12), dpi=180)
   ax.imshow(strips, aspect="auto", interpolation="nearest")
   ax.set_yticks(np.arange(len(names)), labels=names)
   ax.set_xticks([])
   ax.tick_params(axis="y", length=0, labelsize=8)
   fig.subplots_adjust(left=0.32, right=0.99, top=0.99, bottom=0.01)

Preview a palette
=================

Use :func:`get_cmap` to preview a palette with Matplotlib:

.. ipython::
   :okwarning:

   @savefig pyku_colormap_preview.png scale=70
   In [4]: fig, ax = plt.subplots(figsize=(6, 1))
      ...: gradient = np.linspace(0.0, 1.0, 256)[None, :]
      ...: ax.imshow(gradient, aspect="auto", cmap=get_cmap("temp_ano"))
      ...: ax.set_axis_off()
   In [5]: plt.close(fig)

Get sampled colors
==================

Use :func:`get_cmap_colors` to inspect or export colors. Continuous maps are
sampled evenly at the requested resolution.

.. ipython::
   :okwarning:

   In [6]: get_cmap_colors(
      ...:     "temp_abs", kind="linear_segmented", resolution=5
      ...: )

Build a matched colormap and normalization
==========================================

For plotting a configured scale, prefer :func:`get_colormap`. It returns a
colormap and normalization built from the same kind, scale, domain, and bin
configuration. The ``kind="auto"`` default follows the selected configuration;
``scale="default"`` selects its default scale. Named scales such as
``"yearly"`` and ``"monthly"`` can be discovered with
:func:`get_cmap_scale_names`.

Explicit ``domain``, ``boundaries``, ``nbins``, and ``step`` options can
override configured values. Explicit boundaries take precedence over other
bin options. A supplied step takes precedence over ``nbins`` if both are
given. Supply a domain when the selected scale does not define one; explicit
boundaries provide their own domain endpoints.

.. ipython::
   :okwarning:

   @savefig pyku_colormap_pair.png scale=70
   In [7]: cmap, norm = get_colormap("temp_ano", scale="yearly")
      ...: fig, ax = plt.subplots()
      ...: mesh = ax.pcolormesh(
      ...:     [[-2, 0], [1, 3]], cmap=cmap, norm=norm
      ...: )
      ...: fig.colorbar(mesh, label="Temperature anomaly (°C)")
   In [8]: plt.close(fig)

Map test data with one_map
==========================

The visualization API can use a configured colormap and normalization with
pyku's small test dataset. The data are daily mean air temperatures, so use
the default absolute-temperature scale:

.. ipython::
   :okwarning:

   @savefig pyku_colormap_one_map.png scale=70
   In [9]: import pyku
      ...: from pyku.visualisation import one_map
      ...: temperature = pyku.resources.get_test_data("small_tas_dataset")
      ...: temperature = temperature.isel(time=0).compute()
      ...: cmap, norm = get_colormap("temp_abs")
      ...: one_map(
      ...:     temperature,
      ...:     var="tas",
      ...:     cmap=cmap,
      ...:     norm=norm,
      ...: )
   In [10]: plt.close("all")
