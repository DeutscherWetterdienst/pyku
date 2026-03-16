Troubleshooting
===============

.. raw:: html

   <hr/>

.. rst-class:: heading-level-2

Crashes while processing NetCDF files
-------------------------------------

If you encounter crashes when processing **NetCDF** files, particularly in
environments using **xarray** or similar libraries, the following steps offer
solutions from simplest to most involved.

The error shows as:

``OSError: [Errno -101] NetCDF: HDF error``

Our observation
'''''''''''''''

If it is a solution for you, we had good results using numpy version 1.26.4
together with netCDF 1.6.5.

Best Practice
'''''''''''''

First, ensure you are following the best practices for file handling:

* **Use a ``with`` statement:** As recommended by the **xarray** documentation,
  using a ``with`` statement ensures files are properly opened and closed,
  which is critical for preventing resource leaks and conflicts, especially in
  **multiprocessing** scenarios.
* **Try an alternative backend:** Depending on your setup, switching the
  underlying I/O engine might resolve the issue (e.g., trying ``netcdf4`` or
  ``h5netcdf``).

Reading the xarray documentation for I/O is highly recommended for
understanding all available options:
<https://docs.xarray.dev/en/stable/user-guide/io.html>

Recompiling Against System Libraries
''''''''''''''''''''''''''''''''''''

The common cause of crashes, especially those related to **HDF5** and
**NetCDF4**, is a **version conflict** between libraries.

The **wheel** packages installed via ``pip`` often bundle their own copies of
the underlying **HDF5** and **NetCDF** dynamic libraries (``.so`` files). If
your system also has these libraries installed, the Python packages might
incorrectly link to different versions at runtime, causing instability (e.g.,
when one process tries to open a file using one version, and another process
tries to close it using a different, incompatible version).

To resolve this, you need to force ``pip`` to compile **h5py** and **netCDF4**
from source against the specific, consistent HDF5 and NetCDF libraries already
on your system.

Follow these steps to uninstall the conflicting versions and install the new
ones compiled against your system's libraries.

1.  **Uninstall Existing Libraries**

    If the libraries are already installed, they must be uninstalled first:

    .. code:: bash

      pip3 uninstall h5py netCDF4

2.  **Clear the ``pip`` Cache**

    Purge the cache to ensure that ``pip`` does not simply reinstall the older,
    pre-compiled **wheel** versions from cache:

    .. code:: bash

      pip3 cache purge

3.  **Install ``h5py`` from Source**

    You must set the ``HDF5_DIR`` environment variable to point to the root
    installation path of your system's **HDF5** library.

    .. code:: bash

      export HDF5_DIR=/kp/kpbkp/module/modules_rocky/apps/hdf5/1.14.6/
      export HDF5_VERSION=1.14.6
      pip3 install h5py --no-binary h5py

4.  **Install Remaining Libraries from Source**

    The other dependent libraries can now be compiled. The ``--no-binary`` flag
    forces a source compilation.

    .. code:: bash

      pip3 install netCDF4 --no-binary netCDF4

This process ensures that all your Python packages are consistently linked to
the same underlying **HDF5** and **NetCDF** shared objects on your system.

Opening GRIB file with time and step
------------------------------------

Some of grib files may have the following format:

.. code:: python

   Dimensions:     (time: 63, step: 12)
   Coordinates:
     * time        (time) datetime64[ns] 504B 2022-12-31T18:00:00 ... 2023-01-31...
     * step        (step) timedelta64[ns] 96B 01:00:00 02:00:00 ... 12:00:00
       valid_time  (time, step) datetime64[ns] 6kB ...

To extract the time dimension as usual, use the option below:

.. code:: python

   xr.open_dataset(
       '/path/to/your/file.grib',
       time_dims=["valid_time"]
   )

This will result in:

.. code:: python

   Dimensions:     (valid_time: 744)
   Coordinates:
     * valid_time  (valid_time) datetime64[ns] 6kB 2023-01-01 ... 2023-01-31T23:...

Object has inconsistent chunks along dimension time
---------------------------------------------------

This happens when you open files containing different variables with different
timesteps with ``open_mfdataset``. By default, ``open_mfdataset`` gather each
files individually and creates NaN slices along time where no data are
available. So you may find yourself in the following situation:

.. code:: python

   ds.hurs.chunks
   ((1097,), (22,), (24,))

.. code:: python

   ds.pr.chunks
   ((365, 732), (22,), (24,))

There, the chunks have been set differently and automatically for each
:class:`xarray.DataArray` contained in the :class:`xarray.Dataset`. This means
that for the :class:`xarray.Dataset`, the chunks are not defined! By default,
xarray will then merely chunk the datasets along time for each year, which will
massively slow down calculations. This is the reason why unifying chunks along
time is necessary with:

.. code:: python

   ds.unify_chunks()

In a dataset, it's worth noting that some variables may be compressed while
others are not. When compression is applied, a chunking parameter is often set
as part of the compression process. This means that the native chunks of
different variables within the same dataset might not align. To verify this,
you can inspect the encoding of the variables. For instance, the encoding of
the ``time`` variable might appear as follows:

.. code:: python

   ds.time.encoding
   {'dtype': dtype('float64'),
    'zlib': False,
    'szip': False,
    'zstd': False,
    'bzip2': False,
    'blosc': False,
    'shuffle': False,
    'complevel': 0,
    'fletcher32': False,
    'contiguous': False,
    'chunksizes': (512,),
    'preferred_chunks': {'time': 512},
    'original_shape': (23376,),
    'units': 'days since 1949-12-01T00:00:00Z',
    'calendar': 'proleptic_gregorian'}

Whereas the ``pr`` variable is compressed with a different chunk size:

.. code:: python

   ds.pr.encoding
   {'dtype': dtype('float32'),
    'zlib': True,
    'szip': False,
    'zstd': False,
    'bzip2': False,
    'blosc': False,
    'shuffle': True,
    'complevel': 9,
    'fletcher32': False,
    'contiguous': False,
    'chunksizes': (1, 412, 424),
    'preferred_chunks': {'time': 1, 'rlat': 412, 'rlon': 424},
    'original_shape': (23376, 412, 424),
    'missing_value': np.float32(1e+20),
    '_FillValue': np.float32(1e+20),
    'coordinates': 'lon lat'}

The solution here again is to use:

.. code:: python

   ds.unify_chunks()

Slicing is producing a large chunk
----------------------------------

.. code:: bash

    PerformanceWarning: Slicing is producing a large chunk. To accept the large
    chunk and silence this warning, set the option
        >>> with dask.config.set(**{'array.slicing.split_large_chunks': False}):
        ...     array[indexer]

    To avoid creating the large chunks, set the option
        >>> with dask.config.set(**{'array.slicing.split_large_chunks': True}):
        ...     array[indexer]
      return self.array[key]

This occurs when you are merging files with different variables that do not
have the same time labels. During the merging, all NaN slices are created along
time where this is no data. This slices are not automatically chunked. The
solution is then to force dask to chunk these slices like so:

.. code:: python

   import dask
   dask.config.set({'array.slicing.split_large_chunks': True})

And then open your dataset. Note you will very likely need to unify the chunks
on each variables with ``ds.unify_chunks()``

Plots not rendering properly in a cronjob
-----------------------------------------

If your plot renders correctly in bash but not in a cronjob, the culprit may
not be *pyku*, but rather the internal rendering mechanism of *matplotlib*.
Differences in plot rendering can arise based on whether X-Forwarding is
enabled or not. Since cronjobs typically don't utilize X-Forwarding, issues may
surface when running under this condition. To diagnose, compare the plot
outputs after logging in with and without X-Forwarding enabled. You can check
if X-Forwarding is in use by examining the environment variable ``DISPLAY``. To
test the matplotlib backend in Python, you can run:

.. code:: python

   import matplotlib
   print(matplotlib.get_backend())

If X-forwarding is enabled, you should see *TkAgg*, and if not, you should see
*agg*. The solution is to set the matplotlib backend explicitely to *agg*.

Plots do not show in ipython
----------------------------

Import matplotlib python:

.. code:: python

   import matplotlib.pyplot as plt

Use magic:

.. code:: python

   %matplotlib tk

Show

.. code:: python

   plt.show()


Plot is cut
-----------

matplotlib ``savefig`` does not honor the figure size per default. Make sure
you use the ``bbox_inches='tight'`` option when saving the figure:

.. code:: python

   plt.gcf().savefig(output_file, bbox_inches='tight')

Empty plot in jupyter notebook
------------------------------

When saving the plot in a jupyter notebook with

.. code:: python

   plt.gcf().savefig('dummy.png', bbox_inches='tight')

Make sure that the ``savefig`` is in the same cell as the plot:

.. code:: python

   ds.isel(time=0).ana.n_maps(var='tas')
   plt.gcf().savefig('dummy.png', bbox_inches='tight')

This is due to a feature of jupyter that clears the current figures after a
cell was run.

Issues with UTF-8 characters
----------------------------

If you have issues with e.g. German characters, check that you are using UTF-8
environment variables. For example, you can use ``de_DE.UTF-8`` which should
generally be available on DWD systems.

For bash:

.. code:: bash

   export LANG=de_DE.UTF-8
   export LC_ALL=de_DE.UTF-8

If you are using a module file, you can set it up like so:

.. code:: tcl

   setenv LANG de_DE.UTF-8
   setenv LC_ALL de_DE.UTF-8

