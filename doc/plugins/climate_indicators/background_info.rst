How CLIX Works
==============

The conceptual foundation of CLIX relies on the **xclim library** and its extensive collection of climate indicator functions. These functions are the core computational engine for CLIX. You can find detailed documentation for `xclim indices here <https://xclim.readthedocs.io/en/stable/apidoc/xclim.indices.html>`_.

Indicator Definitions
~~~~~~~~~~~~~~~~~~~~~

CLIX uses `xclim` functions to compute climate indicators. Each indicator is defined with its respective default parameter values, which may sometimes differ from the default values used directly in `xclim` to align with DWD's specific requirements.

The mapping between indicators and their corresponding `xclim` functions, along with their default parameters, is stored in a YAML configuration file (e.g., `climate_indicator.yaml`).

If a new indicator needs to be permanently integrated into CLIX, a new entry for it must be added to this `climate_indicator.yaml` file.

**Example: Definition for Summer Days (txge25)**

Below is an example of an indicator definition block for "summer days" (txge25) within the YAML configuration:

.. code-block:: yaml

    txge25:
        standard_name: txge25
        long_name: Number of summer days above or equal 25 degC
        units: days
        xclim_function: xclim.indices.tx_days_above
        default_parameters:
            threshold: 25 degC
            op: '>='

Each indicator definition block includes:

* ``standard_name``: A short, unique identifier for the indicator.
* ``long_name``: A descriptive, human-readable name for the indicator, often used for output file metadata.
* ``units``: The units of the calculated indicator, also for output file metadata.
* ``xclim_function``: The full path to the `xclim.indices` function used for the calculation.
* ``default_parameters``: A dictionary of parameters passed to the `xclim` function if not explicitly overridden by the user.

Custom Indicators
~~~~~~~~~~~~~~~~~

While `xclim` provides a wide range of specific indicator definitions, there are cases where custom or more complex indicator definitions are required. For these situations, custom indicator functions can be included within the `clix_custom_indicators.py` file. These functions are then linked using the `climate_indicators.yaml` configuration file to make them available to the public. The exact function structure is explained on the :doc:`Adding New Indicator page <new_indicators>`. It should be noted that `xclim` offers powerful `generic functions <https://xclim.readthedocs.io/en/stable/apidoc/xclim.indices.html#xclim-indices-generic-module>`_ that can be configured to tackle a broader set of problems.

