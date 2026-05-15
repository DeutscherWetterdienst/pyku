Adding New Indicators
=====================

CLIX primarily uses functions available within the **xclim.indices** package.
You can find their comprehensive documentation here: `xclim indices
Documentation
<https://xclim.readthedocs.io/en/stable/apidoc/xclim.indices.html>`_.

If you identify an essential indicator that is not yet implemented and is
available in `xclim.indices`, please open a new issue on our GitHub repository:
`pyku GitHub Issues <hhttps://github.com/deutscherwetterdienst/pyku/issues>`_.
When opening an issue, refer to the specific `xclim.indices` function and
provide a clear definition of the new climate indicator you would like to see
implemented.

For flexible integration of custom indicators not available through `xclim`,
CLIX provides a mechanism to include them as functions within a centralized
location. The `clix_custom_indicators.py` file serves this purpose as the entry
point for individually defined indicators. To implement new indicators, the
following instructions should be followed:

* The function must accept at least one input ``xarray.DataArray``, defined as
  a mandatory argument.
* The function's output must also be an ``xarray.DataArray``.
* A complete docstring should be included for the function to aid in
  understanding the indicator's purpose and usage.

To ensure a consistent layout for the indicators, it can be helpful to review
the indices defined in `xclim` and the `generic functions
<https://xclim.readthedocs.io/en/stable/apidoc/xclim.indices.html#xclim-indices-generic-module>`_
that can be configured to address a broader set of problems.

Below is an example of a function within the `clix_custom_indicators.py` file
and its integration within the `climate_indicators.yaml` file.

**Example: Definition for a New Indicator (Potential Snow Days)**

This example illustrates the definition of "Potential Snow Days" using a
generic `xclim` function embedded as a Python wrapper, which is then linked
within the YAML configuration file.

.. code-block:: python
    @declare_units(
        pr="[precipitation]",
	tas="[temperature]",
	pr_thresh="[precipitation]",
	tas_thresh="[temperature]",
    )
    def potsnowday(
        pr: xr.DataArray,
	tas: xr.DataArray,
	pr_thresh: Quantified = "1 mm/d",
	tas_thresh: Quantified = "2 degC",
	op_pr: Literal[">", "gt", ">=", "ge", "<", "lt", "<=", "le"] = ">=",
	op_tas: Literal[">", "gt", ">=", "ge", "<", "lt", "<=", "le"] = "<=",
	freq: str = "YS",
    ) -> xr.DataArray:
    """
    Number of days with precipitation above threshold and temperature
    below threshold.

    Number of days when precipitation is greater or equal to some threshold,
    and temperatures are colder than some threshold. This can be used for
    example to identify days with the potential for freezing rain or icing
    conditions.

    Parameters
    ----------
    pr : xarray.DataArray
        Mean daily precipitation flux.
    tas : xarray.DataArray
        Daily mean, minimum or maximum temperature.
    pr_thresh : Quantified
        Precipitation threshold to exceed.
    tas_thresh : Quantified
        Temperature threshold not to exceed.
    freq : str

    Returns
    -------
    xarray.DataArray, [time]
        Count of days with high precipitation and low temperatures.

    Examples
    --------
    To compute the number of days with intense rainfall while minimum
    temperatures dip below -0.2C:
    >>> pr = xr.open_dataset(path_to_pr_file).pr
    >>> tasmin = xr.open_dataset(path_to_tasmin_file).tasmin
    >>> high_precip_low_temp(pr, tas=tasmin, pr_thresh="10 mm/d",
    >>>                      tas_thresh="-0.2 degC")
    """
    pr_thresh = convert_units_to(pr_thresh, pr, context="hydro")
    tas_thresh = convert_units_to(tas_thresh, tas)

    constrain = (">", "<", ">=", "<=", "==", "!=")
    cond = (
        compare(pr, op_pr, pr_thresh, constrain) &
        compare(tas, op_tas, tas_thresh, constrain)
    )

    out = cond.resample(time=freq).sum(dim="time")
    return to_agg_units(out, pr, "count", deffreq="D")


.. code-block:: yaml

   rge1mmtmle2:
     standard_name: potential_snow_days
     long_name: "Potential snow days"
     units: days
     description: "The number of potential snow days, where daily precipitation is above or equal {thresh_pr} and daily mean temperature is below or equal {thresh_tas}."
     cell_methods: 'time: mean within days time: sum over days'
     function: pyku.indices.clix_custom_indicators.potsnowdays
     default_parameters:
       thresh_pr: 1 mm/day
       thresh_tas: 2 degC
       op_pr: '>='
       op_tas: '<='

