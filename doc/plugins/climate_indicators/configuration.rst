Configuration
=============

CLIX leverages `Dask <https://docs.xarray.dev/en/v2024.06.0/user-guide/dask.html>`_ as its default backend to perform all computations in parallel, which is crucial for handling large climate datasets efficiently.

Dask Temporary Directory
~~~~~~~~~~~~~~~~~~~~~~~~

For small computations, the default Dask settings are usually sufficient. However, to prevent potential issues during runtime when processing larger datasets, it is **highly recommended** to configure Dask's temporary directory to a disk location with ample storage capacity.

To do this, set the following environment variable *before* running CLIX:

.. code:: bash

    export DASK_TEMPORARY_DIRECTORY=/path/to/bigger/tmpdir

This ensures that intermediate Dask files have enough space, preventing "disk full" errors or performance bottlenecks.

Local Cluster Settings and Feedback
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The configuration of the local Dask cluster, including internal chunking
strategies, is managed automatically by CLIX. **By default, CLIX executes all
computations sequentially**, without starting a local Dask cluster.

Parallel execution can be enabled explicitly by setting the number of Dask
workers to a value greater than zero using the ``--workers`` option. This allows
CLIX to distribute computations across multiple CPU cores, which can
significantly improve performance for large datasets, provided sufficient
memory is available.

To manually control the resources allocated to the local Dask cluster, the
following command-line options are available:

* ``--memory_limit <GB>``:
  Sets the memory limit per Dask worker in gigabytes.
  For example, ``--memory_limit 16`` allocates 16 GB of RAM to each worker.
  This option helps prevent individual workers from exceeding available memory.
  The default value is ``12`` GB per worker.

* ``--workers <N>``:
  Sets the number of Dask workers used for parallel computation.
  A value of ``0`` (the default) disables parallel execution.
  Setting this value to ``1`` or higher enables a local Dask cluster and allows
  computations to run in parallel on multi-core systems.

If you encounter performance issues such as memory exhaustion or excessive I/O
operations—even after adjusting these parameters—please report them to the CLIX
development team. Such feedback is valuable for improving the internal cluster
management and default configurations.

Using a remote cluster
~~~~~~~~~~~~~~~~~~~~~~

An experimental option has been implemented to use a remote or distributed cluster. In order to try this use the ``--dask_cluster`` option and provide the address to execute computation on the linked cluster. 

.. code:: bash

    clixrun --dask_cluster address ...

