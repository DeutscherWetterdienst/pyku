Climatologies
=============

CLIX provides the functionality to calculate **climatologies** of climate indicators using the ``--average`` option.

Calculating Climatologies
~~~~~~~~~~~~~~~~~~~~~~~~~

To calculate a climatology, use the ``--average`` option with ``clixrun``:

.. code:: bash

    clixrun --input /path/to/input/file.nc --frequency year --average rge1mm

The output's time dimension depends on the ``--frequency`` argument:

* If ``--frequency year`` is used, the result is a single average climatology over the full time period of the input data.
* If a monthly or seasonal frequency is provided (e.g., ``--frequency month`` or ``--frequency season``), the climatology will be computed for each month or season over the full period, resulting in a dataset with 12 (monthly) or 4 (seasonal) timesteps.

Specifying a Date Range
~~~~~~~~~~~~~~~~~~~~~~~

The ``--date_range`` argument offers further flexibility by allowing you to define the time period for the climatology calculation. Provide a start and end date in ``YYYYMMDD`` format.

**Example: Monthly Climatology for a Single Period**

The command below computes the monthly climatology for wet days between 1990 and 2020:

.. code:: bash

    clixrun --input /path/to/input/dir/ --date_range 19900101 20201231 --frequency month --average rge1mm

**Example: Monthly Climatology for Multiple Periods**

It's also possible to use the ``--date_range`` argument multiple times to select non-contiguous periods:

.. code:: bash

    clixrun --input /path/to/input/dir/ --date_range 19910101 20201231 --date_range 19610101 19901231 --frequency month --average rge1mm

.. important::
   When multiple ``--date_range`` arguments are provided, the ``--ofile`` parameter is neglected. CLIX will automatically generate distinct output filenames to prevent overwriting.


