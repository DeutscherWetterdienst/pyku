DWD color maps
==============

*pyku* is the reference implementation of the DWD colormaps:
`DWD default color maps <https://ninjoservices.dwd.de/wiki/display/KUQ/abgestimmte+Farbskalen>`_

Import library
--------------

Load the DWD colormap module.

.. ipython::
   :okwarning:

   In [0]: import pyku.colormaps as colormaps

Also import matplotlib, numpy and xarray for the examples

.. ipython::
   :okwarning:

   In [0]: import numpy as np
      ...: import xarray as xr
      ...: import matplotlib.pyplot as plt
      ...: import pyku

Get names of all colormaps
--------------------------

To get the names of all available colormaps:

.. ipython::
   :okwarning:

   In [0]: colormaps.get_colormaps_names()

Get a colormap
--------------

We can then get a colormap like so

.. ipython::
   :okwarning:

   In [0]: colormaps.get_cmap(
      ...:     'temp_ano',
      ...:     kind='segmented',
      ...:     nbins=10,
      ...:  )

Get colormap colors
-------------------

The colors can be obtained in RGB or HEX format like so:

.. ipython::
   :okwarning:

   In [0]: colormaps.get_cmap_colors(
      ...:     'temp_ano',
      ...:     kind='segmented',
      ...:     nbins=10,
      ...:     encoding='hex'
      ...: )

.. ipython::
   :okwarning:

   In [0]: colormaps.get_cmap_colors(
      ...:     'temp_ano',
      ...:     kind='original',
      ...:     encoding='rgb'
      ...: )

.. note::

   It is not possible to get a list of colors for the continuous colormaps,
   well, because it is continuous.

All colormaps
-------------

Linear colormaps
''''''''''''''''

.. ipython::
   :okwarning:

   @savefig all_linear_colormaps.png width=6in
   In [0]: colormaps.plot_colormaps(kind='linear')

Original colormaps
''''''''''''''''''

.. ipython::
   :okwarning:

   @savefig all_original_colormaps.png width=6in
   In [0]: colormaps.plot_colormaps(kind='original')

Segmented colormaps
'''''''''''''''''''

.. ipython::
   :okwarning:

   @savefig all_segmented_colormaps.png width=6in
   In [0]: colormaps.plot_colormaps(kind='segmented', nbins=7)

Example usage
-------------

matplotlib
''''''''''

.. ipython::
   :okwarning:

   @savefig matplotlib_colormap_usage.png width=4in
   In [0]: # Clear previous plot
      ...: # -------------------
      ...:
      ...: plt.clf() # Clear previous plot
      ...:
      ...: # Create a mesh grid
      ...: # ------------------
      ...:
      ...: X, Y = np.meshgrid(
      ...:     np.linspace(0,10,100),
      ...:     np.linspace(0,10,100),
      ...: )
      ...:
      ...: # Calculate sinusoid and plot
      ...: # ---------------------------
      ...:
      ...: plt.imshow(
      ...:     np.sin(X) + np.cos(Y),
      ...:     cmap=colormaps.get_cmap('temp_ano'),
      ...:     extent=[0, 10, 0, 10],
      ...:     origin='lower'
      ...: )

xarray
''''''

.. ipython::
   :okwarning:

   @savefig xarray_colormap_usage2.png width=4in
   In [0]: # Load xarray test dataset
      ...: # ------------------------
      ...:
      ...: airtemps = xr.tutorial.open_dataset("air_temperature")
      ...:
      ...: # Plot
      ...: # ----
      ...:
      ...: airtemps.isel(time=0)['air'].plot(
      ...:     cmap=colormaps.get_cmap('temp_ano', kind='original')
      ...: )

pyku.analyse
''''''''''''

.. ipython::
   :okwarning:

   @savefig pyku_colormap_usage.png width=4in
   In [0]: # Load xarray test dataset
      ...: # ------------------------
      ...:
      ...: airtemps = xr.tutorial.open_dataset("air_temperature")
      ...:
      ...: # Plot
      ...: # ----
      ...:
      ...: airtemps.isel(time=0).ana.one_map(
      ...:     var='air',
      ...:     cmap=colormaps.get_cmap('temp_ano', kind='segmented', nbins=11)
      ...: )
