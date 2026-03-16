Adding New Indicators
=====================

CLIX primarily uses functions available within the **xclim.indices** package. You can find their comprehensive documentation here: `xclim indices Documentation <https://xclim.readthedocs.io/en/stable/apidoc/xclim.indices.html>`_.

If you identify an essential indicator that is not yet implemented and is available in `xclim.indices`, please open a new issue on our GitHub repository: `pyku GitHub Issues <https://gitlab.dwd.de/ku/libraries/pyku/-/issues/>`_. When opening an issue, refer to the specific `xclim.indices` function and provide a clear definition of the new climate indicator you would like to see implemented.

For flexible integration of custom indicators not available through `xclim`, CLIX provides a mechanism to include them as functions within a centralized location. The `clix_custom_indicators.py` file serves this purpose as the entry point for individually defined indicators. To implement new indicators, the following instructions should be followed:

* The function must accept at least one input ``xarray.DataArray``, defined as a mandatory argument.
* The function's output must also be an ``xarray.DataArray``.
* A complete docstring should be included for the function to aid in understanding the indicator's purpose and usage.

To ensure a consistent layout for the indicators, it can be helpful to review the indices defined in `xclim` and the `generic functions <https://xclim.readthedocs.io/en/stable/apidoc/xclim.indices.html#xclim-indices-generic-module>`_ that can be configured to address a broader set of problems.

Below is an example of a function within the `clix_custom_indicators.py` file and its integration within the `climate_indicators.yaml` file.

**Example: Definition for a New Indicator (Potential Snow Days)**

This example illustrates the definition of "Potential Snow Days" using a generic `xclim` function embedded as a Python wrapper, which is then linked within the YAML configuration file.

.. code-block:: python

   @declare_units(pr="[precipitation]", tas="[temperature]")
   def potsnowdays(
           pr: xr.DataArray,
           tas: xr.DataArray,
           thresh_pr: Quantified = "1.0 mm/day",
           thresh_tas: Quantified = "2 degC",
           freq: str = "YS",
           op_pr: Literal[">", "gt", ">=", "ge"] = ">=",
           op_tas: Literal["<", "lt", "<=", "le"] = "<=",
           var_reducer: Literal["all", "any"] = "all",
           constrain_pr: Sequence[str] | None = None,
           constrain_tas: Sequence[str] | None = None,
   ) -> xr.DataArray:
       r"""
       Potential Snow Days.

       The number of potential snow days, where daily precipitation is
       above or equal to ``thresh_pr`` (default: 1 mm/day) and daily mean
       temperature is below or equal to ``thresh_tas`` (default: 2 degC).

       Parameters
       ----------
       pr : xarray.DataArray
           Daily precipitation amount.
       tas : xarray.DataArray
           Daily mean temperature.
       thresh_pr : Quantified
           Precipitation threshold.
       thresh_tas : Quantified
           Temperature threshold.
       freq : str
           Resampling frequency defining the periods as defined in :ref:`timeseries.resampling`.
       op_pr : {">", "gt", ">=", "ge"}
           Logical operator for precipitation comparison (e.g., ``arr > thresh``).
       op_tas : {"<", "lt", "<=", "le"}
           Logical operator for temperature comparison (e.g., ``arr < thresh``).
       var_reducer : {"all", "any"}
           The condition must be fulfilled on *all* or *any* variables
           for the period to be considered an occurrence.
       constrain_pr : sequence of str, optional
           Optionally allowed comparison operators for precipitation (`pr`).
       constrain_tas : sequence of str, optional
           Optionally allowed comparison operators for temperature (`tas`).

       Returns
       -------
       xr.DataArray
           The DataArray of counted occurrences of potential snow days.
       """

       from xclim.indices.generic import bivariate_count_occurrences
       from xclim.core.units import convert_units_to # Assuming this is the correct import path

       # Convert units of DataArray and thresholds if necessary
       pr = convert_units_to(pr, thresh_pr, context="hydro")
       tas = convert_units_to(tas, thresh_tas)

       return bivariate_count_occurrences(
           data_var1=pr, data_var2=tas, freq=freq,
           threshold_var1=thresh_pr, threshold_var2=thresh_tas,
           op_var1=op_pr, op_var2=op_tas, var_reducer=var_reducer,
           constrain_var1=constrain_pr, constrain_var2=constrain_tas,
       )

.. code-block:: yaml

   rge1mmtmle2:
     standard_name: potential_snow_days
     long_name: "Potential snow days"
     units: days
     description: "The number of potential snow days, where daily precipitation is above or equal {thresh_pr} and daily mean temperature is below or equal {thresh_tas}."
     cell_methods: 'time: mean within days time: sum over days'
     xclim_function: pyku.indices.clix_custom_indicators.potsnowdays
     default_parameters:
       thresh_pr: 1 mm/day
       thresh_tas: 2 degC
       op_pr: '>='
       op_tas: '<='
       var_reducer: 'all'


