Getting Started
===============

To begin, display the command-line help information:

.. code:: bash

    clixrun --help

The command structure requires a set of global arguments (both required and optional), followed by the name of the climate indicator you wish to compute.

For example, to calculate the number of **wet days** (days with precipitation ≥ 1 mm/day) on a yearly basis, use the following command:

.. code:: bash

    clixrun --input /path/to/precipitation/input/file.nc --frequency year rge1mm

This command generates a time series file containing the yearly count of days that meet the specified precipitation threshold.

Customizing Indicators
~~~~~~~~~~~~~~~~~~~~~~

You can customize the parameters for any indicator, such as its threshold or comparison operator. To see the available options for a specific indicator, view its help message.

.. code:: bash

    clixrun rge1mm --help

This help message will show you all the parameters you can modify. For example, to change the threshold to "> 2 mm/day", you would run:

.. code:: bash

    clixrun --input /path/to/input/file.nc --frequency year rge1mm --thresh "2 mm/day" --op ">"

.. warning::
   When you modify an indicator's parameters, the output filename will still default to the original indicator name (e.g., `rge1mm.nc`). To avoid confusion, you should specify a custom output filename using the `--ofile` argument.

.. note::
   If an indicator is run without any specific options, the default parameters from the German Weather Service (DWD) will be used.
   
Argument Order
~~~~~~~~~~~~~~

.. important::
   The order of arguments is critical. Global options (e.g., `--input`, `--frequency`) must be placed **before** the indicator name. Indicator-specific options (e.g., `--thresh`, `--op`) must be placed **after** it.

Working with Multiple Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~

CLIX offers several ways to handle multiple source files.

**Processing a Directory**

To process all NetCDF files for a single variable within a specified directory, provide the directory path as input.

CLIX attempts to open and concatenate all files in the given directory using the :py:func:`xarray.open_mfdataset` command.

.. code:: bash

    clixrun --input /path/to/input/dir/ --frequency month --ofile longest_dry_spell.nc cddmax

.. warning::
   Ensure that all NetCDF files in the directory share the *exact same grid definition*. Mismatched grid definitions will likely cause :py:func:`xarray.open_mfdataset` to fail.
    
**Providing Multiple Input Files**

Some indicators require several input variables (e.g., minimum and maximum temperature). Use the `--input` argument to provide a list of all required input files.

.. code:: bash

    clixrun --input /path/to/tasmax.nc /path/to/tasmin.nc --frequency season --ofile heatwaves.nc txge30tnge20ge3d

.. note::

   Multiple directory paths can also be provided using the ``--input`` option.

    
**Using a YAML Configuration File**

For complex cases, such as combining data from different historical and scenario folders, you can use a YAML configuration file. This method is ideal for navigating complex directory layouts like the Data Reference Syntax (DRS).

The YAML file allows you to define specific data facets and use wildcards to precisely select the required files. For detailed instructions, please see the :doc:`Climate Scenario documentation <scenario>`.

Using Percentile-Based Indicators
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Some climate indicators use percentiles as a dynamic threshold to derive exceedance probabilities. For example, the **Cold Spell Duration Index (CSDI)** is typically defined as the number of days with at least 6 consecutive days where the daily minimum temperature is below the 10th percentile.

CLIX provides flexibility for these indicators through several percentile-based parameters:

* ``--input_perc`` Specifies the input files, folders (probably containing precomputed percentile fields) or YAML file.
* ``--percentile`` Sets the percentile value (a value between 0 and 100) to be used as a threshold. If this parameter is **not set**, CLIX assumes that percentile fields are already provided via ``--input_perc``.
* ``--percentile_freq`` Defines the frequency over which percentiles should be computed. This is relevant when CLIX calculates percentiles on-the-fly.
* ``--perc_date_range`` Specifies an alternative period (``YYYYMMDD YYYYMMDD``) to compute percentiles. This allows for deriving percentiles from a different reference period than the main ``--date_range`` for the indicator calculation.

With this set of parameters, users have the flexibility to:

* Directly input precomputed percentile fields using ``--input_perc``.
* Instruct CLIX to compute percentiles on-the-fly, specifying the desired percentile value (``--percentile``), the frequency for computation (``--percentile_freq``), and an alternative reference period (``--perc_date_range``) if needed.

**Example: Deriving the Cold Spell Duration Index**

This command calculates the yearly Cold Spell Duration Index (CSDI) for the period 2000-2010, using a 10th percentile derived from the 1961-1990 reference period. If no percentile input dataset is provided via the ``--input_perc`` option, the percentile thresholds are automatically computed from the data supplied with ``--input``.

.. code-block:: bash

   clixrun \
     --input /folder/to/tasmin/files/ \
     --date_range 20000101 20101231 \
     --perc_date_range 19610101 19901231 \
     --percentile 10 \
     --frequency year \
     csdi

.. warning::

   Although CLIX simplifies the computation of climate indices, percentile-based thresholds require special consideration.
   This functionality is still under active development and may be subject to changes in future releases.
    
.. toctree::
   :maxdepth: 1
   :caption: Getting Started:

   configuration.rst
   climatology.rst
   anomaly.rst
   missing_values.rst
   scenario.rst
   troubleshooting.rst
   python_integration.rst
