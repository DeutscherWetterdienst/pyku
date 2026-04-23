#!/usr/bin/env python3
"""
Custom Indicator interface for climate-indicator tool.
Collection of indicators that are not handled by xclim
"""

from __future__ import annotations

from typing import Literal, Sequence

import xarray as xr
from xclim.core import Quantified
from xclim.core.calendar import resample_doy
from xclim.core.units import convert_units_to, declare_units
from xclim.indices.generic import compare, select_resample_op
from xclim.indices import (
    dry_spell_frequency,
    potential_evapotranspiration,
    wet_spell_frequency,
)


@declare_units(
    pr="[precipitation]",
    thresh_low="[precipitation]",
    thresh_high="[temperature]",
)
def wet_spell_frequency_bounded_thresh(
    pr: xr.DataArray,
    thresh_low: Quantified = "1.0 mm",
    thresh_high: Quantified = "10.0 mm",
    window: int = 3,
    freq: str = "YS",
    resample_before_rl: bool = True,
    op: Literal["sum", "min", "max", "mean"] = "sum",
    **indexer,
) -> xr.DataArray:
    r"""
    Return the number of wet periods of n days and more.

    Periods during which the accumulated, minimal,
    or maximal daily precipitation amount within a window
    of n days is between two thresholds.

    Parameters
    ----------
    pr : xr.DataArray
        Daily precipitation.
    thresh_low : Quantified
        Lower precipitation amount over which a period is
        considered dry. The value against which the threshold
        is compared depends on `op`.
    thresh_high : Quantified
        Higher precipitation amount over which a period is
        considered dry. The value against which the threshold
        is compared depends on `op`.
    window : int
        Minimum length of the spells.
    freq : str
        Resampling frequency.
    resample_before_rl : bool
        Determines if the resampling should take place before
        or after the run length encoding
        (or a similar algorithm) is applied to runs.
    op : {"sum", "min", "max", "mean"}
        Operation to perform on the window.
        Default is "sum", which checks that the sum of accumulated
        precipitation over the whole window is more than the threshold.
        "min" checks that the maximal daily precipitation amount
        within the window is more than the threshold. This is the same
        as verifying that each individual day is above the threshold.
    **indexer : {dim: indexer}, optional
        Indexing parameters to compute the indicator on a temporal
        subset of the data. It accepts the same arguments as
        :py:func:`xclim.indices.generic.select_time`.
        Indexing is done after finding the wet days, but before
        finding the spells.

    Returns
    -------
    xr.DataArray, [unitless]
        The {freq} number of wet periods of minimum {window} days
        between two thresholds.

    See Also
    --------
    xclim.indices.generic.spell_length_statistics : The parent
    function that computes the spell length statistics.

    Examples
    --------

    Derive number of days that have between 30 and 50 mm/day
    precipitation amount:

    >>> wsfb = wet_spell_frequency_bounded(
        pr=pr, thresh_low="30 mm/day", thresh_high="50 mm/day")
    """

    # Calculate wet spell frequencies that are bounded by two thresholds
    wsf_low = wet_spell_frequency(
        pr,
        thresh=thresh_low,
        window=window,
        freq=freq,
        resample_before_rl=resample_before_rl,
        op=op,
        **indexer,
    )

    wsf_high = wet_spell_frequency(
        pr,
        thresh=thresh_high,
        window=window,
        freq=freq,
        resample_before_rl=resample_before_rl,
        op=op,
        **indexer,
    )

    return wsf_low - wsf_high


@declare_units(
    pr="[precipitation]",
    thresh="[length]",
)
def wet_spell_frequency_bounded_window(
    pr: xr.DataArray,
    thresh: Quantified = "1.0 mm",
    window_min: int = 4,
    window_max: int = 5,
    freq: str = "YS",
    resample_before_rl: bool = True,
    op: Literal["sum", "min", "max", "mean"] = "sum",
    **indexer,
) -> xr.DataArray:
    r"""
    Return the number of wet periods of n days and more.

    Periods during which the accumulated or maximal daily precipitation amount
    within a window of n days is under a given threshold.

    Parameters
    ----------
    pr : xr.DataArray
        Daily precipitation.
    thresh : Quantified
        Precipitation amount under which a period is considered wet.
        The value against which the threshold is compared depends on `op`.
    window_min : int
        Minimum length of the spells.
    window_max : int
        Maximum length of the spells.
    freq : str
        Resampling frequency.
    resample_before_rl : bool
        Determines if the resampling should take place before or after
        the run length encoding
        (or a similar algorithm) is applied to runs.
    op : {"sum", "max", "min", "mean"}
        Operation to perform on the window.
        Default is "sum", which checks that the sum of accumulated
        precipitation over the whole window is less than the threshold.
        "max" checks that the maximal daily precipitation amount within
        the window is less than the threshold. This is the same as
        verifying that each individual day is below the threshold.
    **indexer : {dim: indexer}, optional
        Indexing parameters to compute the indicator on a temporal
        subset of the data. It accepts the same arguments as
        :py:func:`xclim.indices.generic.select_time`.
        Indexing is done after finding the wet days, but before finding
        the spells.

    Returns
    -------
    xr.DataArray, [unitless]
        The {freq} number of wet periods of minimum {window} days.

    See Also
    --------
    xclim.indices.generic.spell_length_statistics : The parent function
    that computes the spell length statistics.

    Examples
    --------

    Derive number of wet spells with length between 4 and 5 days:

    >>> dsfb = wet_spell_frequency_bounded_window(
        pr=pr, window_min=4, window_max=5)
    """

    # Calculate wet spell frequencies that are bounded by two windows
    wsf_low = wet_spell_frequency(
        pr,
        thresh=thresh,
        window=window_min,
        freq=freq,
        resample_before_rl=resample_before_rl,
        op=op,
        **indexer,
    )

    wsf_high = wet_spell_frequency(
        pr,
        thresh=thresh,
        window=window_max+1,
        freq=freq,
        resample_before_rl=resample_before_rl,
        op=op,
        **indexer,
    )

    return wsf_low - wsf_high


@declare_units(
    pr="[precipitation]",
    thresh="[length]",
)
def dry_spell_frequency_bounded_window(
    pr: xr.DataArray,
    thresh: Quantified = "1.0 mm",
    window_min: int = 4,
    window_max: int = 5,
    freq: str = "YS",
    resample_before_rl: bool = True,
    op: Literal["sum", "min", "max", "mean"] = "sum",
    **indexer,
) -> xr.DataArray:
    r"""
    Return the number of dry periods of n days and more.

    Periods during which the accumulated or maximal daily precipitation amount
    within a window of n days is under a given threshold.

    Parameters
    ----------
    pr : xr.DataArray
        Daily precipitation.
    thresh : Quantified
        Precipitation amount under which a period is considered dry.
        The value against which the threshold is compared depends on `op`.
    window_min : int
        Minimum length of the spells.
    window_max : int
        Maximum length of the spells.
    freq : str
        Resampling frequency.
    resample_before_rl : bool
        Determines if the resampling should take place before or after the
        run length encoding (or a similar algorithm) is applied to runs.
    op : {"sum", "max", "min", "mean"}
        Operation to perform on the window.
        Default is "sum", which checks that the sum of accumulated
        precipitation over the whole window is less than the threshold.
        "max" checks that the maximal daily precipitation amount within
        the window is less than the threshold. This is the same as
        verifying that each individual day is below the threshold.
    **indexer : {dim: indexer}, optional
        Indexing parameters to compute the indicator on a temporal subset
        of the data. It accepts the same arguments as
        :py:func:`xclim.indices.generic.select_time`.
        Indexing is done after finding the dry days, but before finding
        the spells.

    Returns
    -------
    xr.DataArray, [unitless]
        The {freq} number of dry periods of minimum {window} days.

    See Also
    --------
    xclim.indices.generic.spell_length_statistics : The parent function
    that computes the spell length statistics.

    Examples
    --------

    Derive number of dry spells with length between 4 and 5 days:

    >>> dsfb = dry_spell_frequency_bounded_window(
        pr=pr, window_min=4, window_max=5)
    """

    # Calculate dry spell frequencies that are bounded by two windows
    dsf_low = dry_spell_frequency(
        pr,
        thresh=thresh,
        window=window_min,
        freq=freq,
        resample_before_rl=resample_before_rl,
        op=op,
        **indexer,
    )

    dsf_high = dry_spell_frequency(
        pr,
        thresh=thresh,
        window=window_max+1,
        freq=freq,
        resample_before_rl=resample_before_rl,
        op=op,
        **indexer,
    )

    return dsf_low - dsf_high


@declare_units(pr="[precipitation]", pr_per="[precipitation]")
def prcpertot(
    pr: xr.DataArray,
    pr_per: xr.DataArray,
    freq: str = "YS",
    op: Literal[">", ">=", "gt", "ge"] = ">",
) -> xr.DataArray:
    r"""
    Accumulated total precipitation over given percentile threshold.

    The total accumulated precipitation from days where precipitation
    exceeds a given percentile.

    Parameters
    ----------
    pr : xr.DataArray
        Total precipitation flux [mm d-1], [mm week-1], [mm month-1]
        or similar.
    pr_per : xr.DataArray
        Percentile of wet day precipitation flux. Either computed daily
        (one value per day of year) or computed over a period (one value
        per spatial point).
    freq : str
        Resampling frequency.
    op : {">", ">=", "gt", "ge"}
        Comparison operation. Default: ">".

    Returns
    -------
    xr.DataArray, [length]
       Total {freq} precipitation.
    """

    import numpy as np

    pr = convert_units_to(pr, "mm", context="hydro")
    pr_per = convert_units_to(pr_per, "mm", context="hydro")

    tp = pr_per
    if "dayofyear" in pr_per.coords:
        # Create time series out of doy values.
        tp = resample_doy(tp, pr)

    constrain = (">", ">=")

    # Compute the days when precip is over the percentile threshold.
    over = (
        pr.where(compare(pr, op, tp, constrain), np.nan)
        .resample(time=freq)
        .sum(dim="time")
    )

    return over


@declare_units(rsds="[radiation]")
def rsds_mean(rsds: xr.DataArray, freq: str = "YS") -> xr.DataArray:
    r"""
    Mean of daily average temperature.

    Resample the original daily mean temperature series by taking the
    mean over each period.

    Parameters
    ----------
    tas : xr.DataArray
        Mean daily temperature.
    freq : str
        Resampling frequency.

    Returns
    -------
    xr.DataArray, [same units as tas]
        The mean daily temperature at the given time frequency.

    Notes
    -----
    Let :math:`TN_i` be the mean daily temperature of day :math:`i`,
    then for a period :math:`p` starting at day :math:`a` and finishing
    on day :math:`b`:

    .. math::

       TG_p = \frac{\sum_{i=a}^{b} TN_i}{b - a + 1}

    Examples
    --------
    The following would compute for each grid cell of file `tas.day.nc`
    the mean temperature at the seasonal frequency, i.e.
    DJF, MAM, JJA, SON, DJF, etc.:

    >>> from xclim.indices import tg_mean
    >>> t = xr.open_dataset(path_to_tas_file).tas
    >>> tg = tg_mean(t, freq="QS-DEC")
    """

    return select_resample_op(rsds, op="mean", freq=freq)


@declare_units(
    tasmin="[temperature]", tasmax="[temperature]", tas="[temperature]"
)
def potevap(
    tasmin: xr.DataArray,
    tasmax: xr.DataArray,
    tas: xr.DataArray,
    freq: str = "YS",
) -> xr.DataArray:
    r"""
    Potential evapotranspiration.

    The potential for water evaporation from soil and transpiration by
    plants if the water supply is sufficient, according to a given method.

    Parameters
    ----------
    tasmin : xr.DataArray
        Minimum daily Temperature.
    tasmax : xr.DataArray
        Maximum daily Temperature.
    tas : xr.DataArray
        Mean daily Temperature.
    freq : str
        Resampling frequency.

    Returns
    -------
    xr.DataArray
        Potential Evapotranspiration.

    """

    return potential_evapotranspiration(
        tasmin=tasmin, tasmax=tasmax, tas=tas, method="HG85"
    )


@declare_units(
    pr="[precipitation]",
    tas="[temperature]",
    thresh_pr="[precipitation]",
    thresh_tas="[temperature]",
)
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

    The number of potential snow days, where the min precipitation is
    above or equal thresh_pr (default: 1mm/day) and mean
    temperature is below or equal thresh_tas (default 2 degC)."

    Parameters
    ----------
    pr : xr.DataArray
        Minimum daily Temperature.
    tas : xr.DataArray
        Maximum daily Temperature.
    thresh_pr : Quantified
        Threshold for data pr.
    thresh_tas : Quantified
        Threshold for data tas.
    freq : str
        Resampling frequency defining the periods as defined in
        :ref:`timeseries.resampling`.
    op_pr : {">", "gt", ">=", "ge"}
        Logical operator for data pr e.g. arr > thresh.
    op_tas : {"<", "lt", "<=", "le"}
        Logical operator for data tas e.g. arr > thresh.
    var_reducer : {"all", "any"}
        The condition must either be fulfilled on *all* or *any* variables
        for the period to be considered an occurrence.
    constrain_pr : sequence of str, optional
        Optionally allowed comparison operators for pr.
    constrain_tas : sequence of str, optional
        Optionally allowed comparison operators for tas.

    Returns
    -------
    xr.DataArray
        The DataArray of counted occurrences of potential snow days.
    """

    from xclim.indices.generic import bivariate_count_occurrences

    # Convert units of DataArray and thresholds if necessary
    pr = convert_units_to(pr, thresh_pr, context="hydro")
    tas = convert_units_to(tas, thresh_tas)

    return bivariate_count_occurrences(
        data_var1=pr,
        data_var2=tas,
        freq=freq,
        threshold_var1=thresh_pr,
        threshold_var2=thresh_tas,
        op_var1=op_pr,
        op_var2=op_tas,
        var_reducer=var_reducer,
        constrain_var1=constrain_pr,
        constrain_var2=constrain_tas,
    )


@declare_units(
    pr="[precipitation]",
    tasmax="[temperature]",
    thresh_pr="[precipitation]",
    thresh_tasmax_low="[temperature]",
    thresh_tasmax_high="[temperature]",
)
def tourism_days(
    pr: xr.DataArray,
    tasmax: xr.DataArray,
    thresh_pr: Quantified = "0.5 mm/day",
    thresh_tasmax_low: Quantified = "15 degC",
    thresh_tasmax_high: Quantified = "30 degC",
    freq: str = "YS",
    op_pr: Literal["<", "lt", "<=", "le"] = "<",
    op_tasmax_low: Literal[">", "gt", ">=", "ge"] = ">=",
    op_tasmax_high: Literal["<", "lt", "<=", "le"] = "<=",
) -> xr.DataArray:
    r"""
    Tourism day index.

    The number of days, where the precipitation is
    lower (or equal) thresh_pr (default: 0.5 mm/day) and maximum
    temperature is above or equal thresh_tasmax_low (default 15 degC)
    and maximum temperature is lower or equal to
    thresh_tasmax_high (default 30 degC)."

    Parameters
    ----------
    pr : xr.DataArray
        Daily precipitation.
    tasmax : xr.DataArray
        Maximum daily Temperature.
    thresh_pr : Quantified
        Threshold for data pr.
    thresh_tasmax_low : Quantified
        Lower threshold for data tasmax.
    thresh_tasmax_high : Quantified
        Higher threshhold for data tasmax
    freq : str
        Resampling frequency defining the periods as defined in
        :ref:`timeseries.resampling`.
    op_pr : {"<", "lt", "<=", "le"}
        Logical operator for data pr e.g. arr < thresh_pr.
    op_tasmax_low : {">", "gt", ">=", "ge"}
        Logical operator for data tasmax e.g. arr > thresh_low.
    op_tasmax_high : {"<", "lt", "<=", "le"}
        Logical operator for data tasmax e.g. arr < thresh_high.

    Returns
    -------
    xr.DataArray
        The DataArray of counted occurrences of tourism days.
    """

    from xclim.indices.generic import compare
    from xclim.core.units import to_agg_units

    # Convert units of DataArray and thresholds if necessary
    thresh_pr = convert_units_to(thresh_pr, pr, context="hydro")
    thresh_tasmax_low = convert_units_to(thresh_tasmax_low, tasmax)
    thresh_tasmax_high = convert_units_to(thresh_tasmax_high, tasmax)

    constrain_low = (">", ">=")
    constrain_high = ("<", "<=")

    cond = (
        compare(pr, op_pr, thresh_pr, constrain_high)
        & compare(tasmax, op_tasmax_low, thresh_tasmax_low, constrain_low)
        & compare(tasmax, op_tasmax_high, thresh_tasmax_high, constrain_high)
    )

    out = cond.resample(time=freq).sum()

    return to_agg_units(out, pr, "count", dim="time")


@declare_units(sfcWind="[wind]")
def sfcWindp98(
    sfcWind: xr.DataArray,
    sfcWind_percentile: float = 98,
    freq: str = "YS",
) -> xr.DataArray:
    r"""
    Calculates the 98th percentile of 10m wind speed.
    """

    return percentile_grouped(sfcWind, per=sfcWind_percentile, group_freq=freq)


def percentile_grouped(
    arr: xr.DataArray,
    group_freq: str = "YS",
    per: float | Sequence[float] = 10.0,
    alpha: float = 1.0 / 3.0,
    beta: float = 1.0 / 3.0,
    copy: bool = True,
    climatology: bool = False,
) -> xr.DataArray:
    """

    Compute percentiles over time using grouped time frequency (e.g.,
    monthly, seasonal, yearly). If `climatology=True`, compute
    climatological percentiles across all years for each group.

    Parameters
    ----------
    arr : xr.DataArray
        Input data with a time dimension.
    group_freq : str
        Frequency string like 'MS', 'YS', 'QS-DEC', etc.
    per : float or list of float
        Percentile(s) to compute (0–100).
    alpha, beta : float
        Parameters for Hyndman & Fan quantile estimator (used in calc_perc).
    copy : bool
        Whether to copy the input data (passed to `calc_perc`).
    climatology : bool
        If True, computes percentiles over all years for each
        frequency period (e.g., month-wise climatology).

    Returns
    -------
    xr.DataArray
        Resulting percentiles with dimensions ('time', 'percentiles', ...)
    """

    from xclim.core.utils import uses_dask, calc_perc
    import xarray as xr
    import numpy as np

    if np.isscalar(per):
        per = [per]

    if uses_dask(arr):
        arr = arr.chunk({"time": -1})

    def apply_perc(group: xr.DataArray) -> xr.DataArray:
        result = xr.apply_ufunc(
            calc_perc,
            group,
            input_core_dims=[["time"]],
            output_core_dims=[["percentiles"]],
            kwargs={
                "percentiles": per,
                "alpha": alpha,
                "beta": beta,
                "copy": copy,
            },
            dask="parallelized",
            output_dtypes=[arr.dtype],
            dask_gufunc_kwargs={"output_sizes": {"percentiles": len(per)}},
        )
        result.coords["percentiles"] = per
        return result

    def get_climatology_group(time: xr.DataArray, freq: str) -> xr.DataArray:
        FREQ_GROUP_MAP = {
            "MS": lambda t: t.dt.month.rename("month"),
            "YS": lambda t: xr.ones_like(t, dtype=int).rename("all"),
            "QS-DEC": lambda t: t.dt.quarter.rename("quarter"),
        }
        try:
            return FREQ_GROUP_MAP[freq](time)
        except KeyError:
            raise ValueError(
                f"Unsupported climatology grouping frequency: {freq}"
            )  # noqa

        # FREQ_TO_FUNC = {
        #     "MS": assign_month,
        #     "YS": assign_year,
        #     "QS-DEC": assign_quarter,
        # }

        # try:
        #     return FREQ_TO_FUNC[freq](time)
        # except KeyError:
        #     raise ValueError(f"Unsupported frequency for period assignment: {freq}")  # noqa

    if climatology:
        # Use grouping key like "month" or "season" based on group_freq
        group = get_climatology_group(arr["time"], group_freq)
        grouped = arr.groupby(group)
        result = grouped.map(apply_perc)

        # Rename grouped dimension with time
        result = result.rename({result.dims[0]: "time"})
    else:
        grouped = arr.resample(time=group_freq)
        result = grouped.map(apply_perc)

    if len(per) == 1:
        result = result.squeeze("percentiles", drop=True)

    result.attrs.update(arr.attrs)
    result.attrs["group_freq"] = group_freq
    result.attrs["percentiles"] = str(per)

    return result.rename("per")


def expand_percentiles_to_daily(
    daily: xr.DataArray, per: xr.DataArray, freq: str
) -> xr.DataArray:
    """
    Expand a grouped percentile array (e.g., monthly) to match a daily
    time series.

    Parameters
    ----------
    daily : xr.DataArray
        Daily data with a 'time' dimension.
    per : xr.DataArray
        Percentile values grouped by time period (with 'time' from 1–12 for MS,
        1–4 for QS-DEC, or years for YS).
    freq : str
        Grouping frequency of the percentiles: 'MS', 'QS-DEC', or 'YS'.

    Returns
    -------
    xr.DataArray
        Percentiles expanded to daily resolution matching `daily.time`.
    """

    import xarray as xr

    # Get group labels for each day based on the frequency
    def get_group_labels(time, freq):
        if freq == "MS":
            return xr.DataArray(
                time.dt.month, coords={"time": time}, dims="time"
            )
        elif freq == "QS-DEC":
            return xr.DataArray(
                time.dt.quarter, coords={"time": time}, dims="time"
            )
        elif freq == "YS":
            return xr.DataArray(
                [1] * time.size, coords={"time": time}, dims="time"
            )
        else:
            raise ValueError(f"Unsupported frequency: {freq}")

    group_labels = get_group_labels(daily.time, freq)

    # Map daily values to corresponding percentile
    per_expanded = per.sel(time=group_labels)

    # Ensure time coordinate is set
    per_expanded["time"] = daily["time"]

    return per_expanded
