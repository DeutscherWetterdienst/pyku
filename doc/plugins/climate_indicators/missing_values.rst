Missing values
==============

For indices calculation, CLIX uses built-in functions from xclim for the handling of **missing values** in input data. Output values are properly masked in case input values are missing or invalid. With the option ``--check_missing`` the following missing value methods are available:

* **wmo:**  A result is missing if 11 days are missing, or 5 consecutive values are missing in a month. Default.
* **pct:** A result is missing if more than a given fraction of values are missing.
* **any:** A result is missing if any input value is missing.
* **at_least_n:** A result is missing if less than a given number of valid values are present.
* **skip:** Skip missing value detection.

Missing options
~~~~~~~~~~~~~~~
For the method **pct** the maximum tolerated proportion of missing values per output frequency must be defined by the addtional option ``--allowed_miss_pct``, given as a float between 0 and 1.

For the method **at_least_n** masks output frequencies as missing if they don't have at least a given number of valid values. The additional option ``--min_valid_values`` must be given with an integer. It specifies the minimum number of needed valid values.

CLIX uses the **wmo** method by default if ``--check_missing`` is not set.

**Example: Skip missing value detection when calculating summer days**

This command calculates yearly ``txge25`` (summer days) and ignores any missing values:

.. code:: bash

    clixrun --input /path/to/tasmax_with_nas.nc --check_missing skip --frequency year txge25

This will give results even if there are (a lot of) missing values.

**Example: Use the pct method for calculating summer days**

This command calculates monthly ``txge25`` (summer days) only if no more than a fraction of ``--allowed_miss_pct`` are missing per input time series (grid cell) for each timestep of the output frequency:

.. code:: bash

   clixrun --input /path/to/tasmax_with_nas.nc --frequency month --check_missing pct --allowed_miss_pct 0.08 txge25

**Example: Use the at_least_n method for calculating summer days**

This command calculates monthly ``txge25`` (summer days) only if at least ``--min_valid_values`` valid values are available in the input time series (grid cell) for each timestep of the output frequency:

.. code:: bash

   clixrun --input /path/to/tasmax_with_nas.nc --frequency month --check_missing at_least_n --min_valid_values 20 txge25

    
**Example: Use the any method for calculating summer days**

This command calculates yearly ``txge25`` only if all input values are valid values. As soon as *any* of the input values is missing value, the result is a missing value:

.. code:: bash

   clixrun --input /path/to/tasmax_with_nas.nc --frequency year --check_missing any txge25


