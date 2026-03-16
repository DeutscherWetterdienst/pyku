Distributed computing
=====================

This starter pack explains how to enable multiprocessing and distributed
computing using Dask within xarray. The emphasis is on data processing, as it
is a commonly performed operation and is seamlessly integrated with pyku.

Single threaded
---------------

The default setting is single-threaded processing for development, minimizing
the overhead associated with enabling multiprocessing.

Pyku provides functionality to persistently process data, allowing for
efficient reuse without keeping intermediate data permanently. This is
especially helpful during development or repeated calculations, where
reprocessing data can be computationally expensive.

With pyku, you can define a processing function to apply to each file
individually. The processed files are stored in a temporary directory, and the
function returns a list of these processed files. This is particularly useful
for heavy computations or tasks requiring multiprocessing, as it ensures you
work with a "clean(er)" dataset. The files are pre-chunked directly on disk
with sizes and formats optimized for memory usage and your computation.

Key Benefits:

* Optimized for Heavy Calculations: Saves time by avoiding redundant
  processing.
* Multiprocessing Ready: Large files are chunked and parallel-ready.
* Improved Debugging: Single large files are split into smaller, manageable
  chunks, making debugging easier.

.. code-block:: ipython

   # Load the necessary libraries
   # ----------------------------

   import xarray as xr
   import pyku
   import pyku.resources as resources
   import pyku.compute as compute
   import tempfile

   # Define a directory to store temporary outputs
   # ---------------------------------------------

   tempdir = tempfile.TemporaryDirectory(dir='/path/to/scratch/dir')

   # Define a list of test files
   # ---------------------------

   files = !ls /path/to/regional/CLMcom-DWD-CCLM5-0-16/x0n1-v1/day/tas/v????????/tas_GER-0275_ECMWF-ERA5_evaluation_r1i1p1_CLMcom-DWD-CCLM5-0-16_x0n1-v1_day_????????-????????.nc

   # Define a processing function
   # ----------------------------

   def preprocess(ds):

       ds = ds.pyku.project('HYR-LAEA-5')
       ds = ds.pyku.set_time_labels_from_time_bounds(how='lower')
       ds = ds.pyku.to_cmor_varnames()
       ds = ds.pyku.to_cmor_units()

       return ds

   # Apply the processing function to all files
   # ------------------------------------------

   processed_files = compute.persistent_processing(
       func=preprocess,
       files=files,
       tmpdir=tempdir.name,
   )

   # Check the files produced in the temporary directory
   # ---------------------------------------------------

   !ls {tempdir.name}

You can finally cleanup the temporary directory with:

.. code-block:: ipython

   tempdir.cleanup()

Multiprocessing
---------------

Multiprocessing is fully integrated into pyku. In cases where it isn't, it
should be. This section explains how to quickly enable multiprocessing by
starting a local cluster with a single command, without needing to modify any
code.

While multiprocessing offers significant performance benefits, it also
introduces overhead. Decisions must be made regarding the number of processes
to spawn, the amount of RAM to allocate, and whether the bottleneck lies in
disk I/O or data transfer across the network. Additionally, efficient data
chunking is essential.

The approach we use is advantageous because it allows you to start by running
without multiprocessing, fine-tuning the setup, and then optimize for
performance later. The Dask dashboard, in particular, is extremely useful for
understanding and visualizing how the code is executing, offering insights into
how resources are being utilized.

After you have turned on multiprocessing, you will then be able to access the
dask dashboard with your browser. For example, if you are running on the
``machine_scheduler`` server, the dash board will be available at
http://machine_scheduler:8787/status.

To start a local cluster with 10 cpus, one thread per CPU as well as 5GB of
memory per worker, use the following code in front of your single-threaded
code:

.. code-block:: ipython

   from dask.distributed import LocalCluster, Client

   cluster = LocalCluster(
       n_workers=10,
       threads_per_worker=1,
       memory_limit="5GB"
   )

   client = Client(cluster)

That is it, you can now open the dashboard in your browser, run your code which
is now parallelized.

.. tip::

   To modify the warning threshold for large graph sizes:

   .. code:: python

      import dask
      dask.config.set({
          "distributed.admin.large-graph-warning-threshold": 500 * 1024 * 1024
      })

Distributed computing
---------------------

In this section, we go beyond multiprocessing to explore how distributed
computing can be enabled and utilized with pyku. Distributed computing allows
you to use ridiculus amout of computational power by setting up a cluster of
machines to share tasks. These machines can reside on an HPC, in the cloud, on
Level 2 servers, or even in diverse environments simultaneously connected and
working together.

While setting up a cluster does introduce some overhead, I argue that when
significant computational resources are required, this overhead is well worth
the investment. Pyku's approach is quite simple: tasks can be distributed
across the cluster with a single line of code, ideally without requiring
changes to the original single-threaded code. But we are not in a perfect world
and optimization is hard.

That said, there is additional overhead in scheduling tasks and transferring
data between machines.

The components are:

* The machine where the code is located.
* A machine acting as a **scheduler**, always ready to take jobs from the code
  of the developer and send it to a worker.
* Very many **worker** machines connected to the **scheduler**, loaded with
  *pyku*. The machines stay idle when no job packets are sent.

Libraries must match between all machines. This means that using a development
feature branch of *pyku* on the developement machine may not work with the
latest stable release of *pyku* on the worker machines. However, keeping the
libraries synchronized between the machines is quite trivial using our module
system.

The procedure is as follows:

.. rubric:: Start scheduler

Log in to ``machine_scheduler``, load your environment, and start the
scheduler. Take note of the scheduler's address, as it is required to connect
both your workers and your code to the scheduler. You can then to connect to
``tcp://sch.ed.ul.er:8786``, where ``sch.ed.ul.er`` is the ip of the machine.

.. code:: bash

   ssh machine_scheduler
   source /path/to/your/environment.src
   dask scheduler

With each machine having approximately 120 GB of RAM. With 30 workers, we could
use up to 4GB per worker.

.. rubric:: Start worker 1

Login to ``machine_worker1``, load the environment and start a worker:

.. code:: bash

   ssh machine_worker1
   source /path/to/your/environment.src
   dask worker tcp://sch.ed.ul.er:8786 --nworkers 30 --nthreads 1 --memory-limit '4G'

.. rubric:: Start worker 1

Login to ``machine_worker_2``, load the environment and start a worker:

.. code:: bash

   ssh machine_worker1
   source /path/to/your/environment.src
   dask worker tcp://sch.ed.ul.er:8786 --nworkers 30 --nthreads 1 --memory-limit '4G'

.. rubric:: Start worker n

Login to ``machine_worker_n``, load the environment and start a worker:

.. code:: bash

   ssh machine_worker_n
   source /path/to/your/environment.src
   dask worker tcp://sch.ed.ul.er:8786 --nworkers 30 --nthreads 1 --memory-limit '4G'

The developer would need to know the address of the scheduler and connect to
all resources available with a single line:

.. code-block:: ipython

   client = Client('tcp://sch.ed.ul.er:8786')

From the maintainer side the following command is needed to start the
scheduler, ready to distribute computation packets:
