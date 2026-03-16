Troubleshooting
===============

This section addresses common issues you might encounter while using CLIX.

Parallelization and Storage Issues
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you experience problems related to parallelization or storage, such as:

.. code-block:: text

    OSError: [Errno 28] No space left on device: [...]

These issues often indicate insufficient resources allocated to Dask or a lack of disk space for temporary files. To resolve them, consider adjusting the following CLIX configuration parameters:

* **Dask Temporary Directory:** Ensure your ``DASK_TEMPORARY_DIRECTORY`` environment variable points to a disk location with ample free space.
* **Memory Limit:** Increase the memory allocated per Dask worker using ``--memory_limit <GB>``.
* **Number of Workers:** Adjust the number of Dask workers with ``--workers <N>`` to match your system's capabilities and resource availability.

For detailed instructions on how to set these parameters, please refer to the :doc:`Configuration <configuration>` section.
