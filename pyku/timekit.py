#!/usr/bin/env python3

"""
Functions for dealing with time
"""


from . import logger
from . import meta_dict


def date_range(*args, **kwargs):

    """
    This function is deprecated as its functionality has been integrated into
    the :func:`xarray.date_range` function, which follows the same conventions.
    """

    import xarray as xr

    logger.warning(
        "This function is deprecated as its functionality has been integrated "
        "into the `xarra.date_range` function, which follows the same "
        "conventions."
    )

    return xr.date_range(*args, **kwargs)


def resample_datetimes(ds, how=None, frequency=None, complete=False):

    """
    Resample along the time dimension.

    During resampling, the time labels are set to the lower time bound if
    applicable. This behavior differs from the CMOR convention, which sets the
    time labels to the middle of the time bounds.

    If needed, the time labels can be reset using the
    :func:`pyku.timekit.set_time_labels_from_time_bounds()` function by passing
    the parameter ``how='middle'``.

    Parameters:

        ds (:class:`xarray.Dataset`): The input dataset.

        how (str): The resampling method (*mean*, *max*, *min*, *sum*).

        frequency (str): The resampling frequency, e.g. *1H*, *1D*, *2MS*. For
            seasonal outputs, use *QS-DEC*. The hydrological year divided into
            to two periods of 6 months periods (winter half year Nov-Apr and
            summer half year Mai-Oct) can be obtained with *2QS-MAY*

        complete (bool): If True, filter groups of data with incomplete
            datetimes at the resampling frequency.

    Returns:

        :class:`xarray.Dataset`: The dataset resampled along the time
        dimension.

    References:

        https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases

        * For yearly resampling, use **YS** (Year Start).
        * For monthly resampling, use **MS** (Month Start).
        * For seasonal resampling, use **QS-DEC**.
        * For half year outputs, use **2QS-MAY** (Nov-Apr/Mai-Oct)
        * The use of **M** for month end is deprecated in the pandas library.

    Example:

        .. ipython::
           :okwarning:

           In [0]: %%time
              ...: import pyku
              ...:
              ...: ds = pyku.resources.get_test_data('low-res-hourly-tas-data')
              ...:
              ...: print('First 10 timesteps before:')
              ...: print(ds.time.values[0:10])
              ...:
              ...: ds = ds.pyku.resample_datetimes(frequency='1D', how='mean')
              ...:
              ...: print('\\nFirst 10 timesteps after:')
              ...: print(ds.time.values[0:10])
    """

    from metpy.units import units
    import pyku.meta as meta
    import xarray as xr
    from pandas.tseries.frequencies import to_offset

    # Check function inputs
    # ---------------------

    if how is None or frequency is None:
        raise Exception(f"Invalid input how: {how}, frequency {frequency}")

    # Get data frequency
    # ------------------

    data_frequency = meta.get_frequency(ds, dtype='freqstr')

    # Edge case
    # ---------

    if to_offset(frequency) == meta.get_frequency(ds, dtype='DateOffset'):
        logger.debug("Dataset already at resampling frequency. Doing nothing")
        return ds

    # Determine the type of CMOR outputs
    # ----------------------------------

    is_1hourly_output = to_offset(frequency) == to_offset('1h')
    is_3hourly_output = to_offset(frequency) == to_offset('3h')
    is_6hourly_output = to_offset(frequency) == to_offset('6h')
    is_12hourly_output = to_offset(frequency) == to_offset('12h')
    is_daily_output = to_offset(frequency) == to_offset('1D')
    is_monthly_output = to_offset(frequency) == to_offset('1MS')
    is_seasonal_output = to_offset(frequency) == to_offset('QS-DEC')
    is_yearly_output = to_offset(frequency) == to_offset('1YS')

    # Filter data for incomplete datetimes
    # ------------------------------------

    # Make sure there is no missing data. For example, if a month has one
    # missing day, the whole month is taken out from the dataset

    if complete is True:
        ds = filter_incomplete_datetimes(ds, frequency=frequency)

    # Keep attributes accross operations
    # ----------------------------------

    xr.set_options(keep_attrs=True)

    # Get spatial variables
    # ---------------------

    # Some variables (e.g. crs, rotated_pole) cannot be resampled and are
    # therefore removed during resampling.

    geodata_varnames = meta.get_geodata_varnames(ds)
    time_dependent_varnames = meta.get_time_dependent_varnames(ds)
    time_bounds_varname = meta.get_time_bounds_varname(ds)

    if time_bounds_varname is None:
        time_bounds_varname = []

    other_time_dependent_varnames = [
        varname for varname in time_dependent_varnames
        if varname not in geodata_varnames
        and varname not in time_bounds_varname
    ]

    other_varnames = [
        varname for varname in ds.data_vars
        if varname not in geodata_varnames and
        varname not in time_dependent_varnames and
        varname not in time_bounds_varname
    ]

    ds_out = ds.drop_vars(other_varnames)

    # Add time bounds to dataset if not already available
    # ---------------------------------------------------

    if meta.get_time_bounds(ds_out) is None:
        ds_out = set_time_bounds_from_time_labels(ds_out)

    time_bnds_lower = meta.get_time_bounds(ds_out, which='lower')
    ds_out = ds_out.assign_coords({"time": time_bnds_lower})

    # Resample
    # --------

    if how in ['mean']:
        ds_out = ds_out.resample(time=frequency).mean()

    elif how in ['min', 'minimum']:
        ds_out = ds_out.resample(time=frequency).min()

    elif how in ['max', 'maximum']:
        ds_out = ds_out.resample(time=frequency).max()

    elif how in ['sum']:

        # Loop over all geodata and integrate
        # -----------------------------------

        for var in meta.get_geodata_varnames(ds_out):

            # Get time intervals, quantify
            # ----------------------------

            intervals = meta.get_time_intervals(ds_out)
            da = ds_out[var].metpy.quantify()

            # If the value is in 1/second, integrate over time
            # ------------------------------------------------

            dimensionality = da.metpy.unit_array.dimensionality

            if '[time]' in dict(dimensionality) and \
                    dimensionality['[time]'] == -1:

                da = da * intervals.interval * units.seconds
            else:
                da = da * intervals.interval

            # Dequantify, rename, replace old var with new variable
            # -----------------------------------------------------

            da = da.metpy.dequantify().rename(var)
            ds_out = xr.merge([ds_out.drop(var), da], compat='no_conflicts')

        ds_out = ds_out.resample(time=frequency).sum()

    else:
        raise Exception(f"{how} is not defined")

    # Sanity check
    # ------------

    for varname in geodata_varnames + other_time_dependent_varnames:

        if 'time' not in ds[varname].dims:

            message = \
                f"{varname} has no dependence on time and cannot be resampled"
            raise Exception(message)

    # After resampling, apply cell_methods
    # ------------------------------------

    # The 'cell_methods' variable attribute is set automatically only for clear
    # cases. There should be a bit of work to improve the handling of the
    # 'cell_methods' variable attribute generality. In the meantime, a warning
    # is thrown.

    for varname in geodata_varnames + other_time_dependent_varnames:

        cell_methods = ds[varname].attrs.get('cell_methods')
        dimensionality = ds[varname].metpy.unit_array.dimensionality

        output_cell_methods = None

        if how in ['mean']:

            if cell_methods is not None:

                is_daily_input = to_offset(data_frequency) == to_offset('1D')

                if '[time]' in dict(dimensionality) and \
                        dimensionality['[time]'] == -1:
                    output_cell_methods = 'time: mean'

                elif cell_methods in ['time: point']:
                    output_cell_methods = 'time: mean'

                elif (cell_methods in ['time: maximum'] and
                      is_daily_input and
                      is_monthly_output):

                    output_cell_methods =\
                        'time: maximum within days time: mean over days'

                elif (cell_methods in ['time: minimum'] and
                      is_daily_input and
                      is_monthly_output):

                    output_cell_methods = \
                        'time: minimum within days time: mean over days'

                elif (cell_methods in ['time: sum'] and
                      is_daily_input and
                      is_monthly_output):

                    output_cell_methods = \
                        'time: sum within days time: mean over days'

        elif how in ['min', 'minimum']:
            message = f"{varname}: min not implemented"
            logger.warn(message)

        elif how in ['max', 'maximum']:
            message = f"{varname}: max not implemented"
            logger.warn(message)

        elif how in ['sum']:
            output_cell_methods = 'time: sum'

    if output_cell_methods is not None:
        message = \
            f"{varname}: Setting 'cell_methods' to {output_cell_methods}."
        logger.info(message)

        ds_out[varname].attrs['cell_methods'] = output_cell_methods

    else:

        if ds_out.attrs.get('cell_methods') is not None:
            del ds_out.attrs['cell_methods']
            message = (
                f"{varname}: Removing 'cell_methods' attribute after "
                "resampling"
            )
            logger.info(message)

        message = f"{varname}: 'cell_methods' was not set automatically"
        logger.warning(message)

    # After resampling datetimes, add other variables back to dataset
    # ---------------------------------------------------------------

    ds_out = xr.merge(
        [ds_out, ds[other_varnames]],
        compat='no_conflicts'
    )

    # Determine lower and upper bounds
    # --------------------------------

    # The lower bounds are calculated from the data lower bound and the number
    # of datetimes in the dataset. For cftime, the type is determined from the
    # first time stamp in the data.

    time_bnds_lower = xr.date_range(
        calendar=ds.time.dt.calendar,
        start=time_bnds_lower[0],
        freq=frequency,
        periods=len(ds_out.coords['time'].data)
    )

    # Create an empty DataArray without data for resampling
    # -----------------------------------------------------

    time_bnds_lower = xr.DataArray(
        None, dims=('time',), coords={'time': time_bnds_lower}
    )

    # The upper bounds are calculated from the data lower bound and the number
    # of datetimes in the dataset + 1. The first datetime is then removed. For
    # cftime, the type is determined from the first time stamp in the data.

    time_bnds_upper = xr.date_range(
        calendar=ds.time.dt.calendar,
        start=time_bnds_lower.time.values[0],
        freq=frequency,
        periods=len(ds_out.coords['time'].data)+1
    )

    time_bnds_upper = xr.DataArray(
        None, dims=('time',), coords={'time': time_bnds_upper[1:]}
    )

    # Determine lower and higher time bounds
    # --------------------------------------

    time_bnds = [
         [ts_left, ts_right]
         for ts_left, ts_right
         in zip(time_bnds_lower.time.values, time_bnds_upper.time.values)
    ]

    # Assign time bounds to dataset
    # -----------------------------

    ds_out = ds_out.assign(time_bnds=(['time', 'bnds'], time_bnds))
    ds_out.coords['time'].attrs['bounds'] = 'time_bnds'

    if is_1hourly_output:
        ds_out.attrs['frequency'] = '1hr'

    elif is_3hourly_output:
        ds_out.attrs['frequency'] = '3hr'

    elif is_6hourly_output:
        ds_out.attrs['frequency'] = '6hr'

    elif is_12hourly_output:
        ds_out.attrs['frequency'] = '12hr'

    elif is_daily_output:
        ds_out.attrs['frequency'] = 'day'

    elif is_monthly_output:
        ds_out.attrs['frequency'] = 'mon'

    elif is_seasonal_output:
        ds_out.attrs['frequency'] = 'sem'

    elif is_yearly_output:
        ds_out.attrs['frequency'] = 'year'

    else:
        message = f"frequency {frequency} not a CMOR standard."
        logger.warn(message)

        ds_out.attrs['frequency'] = to_offset(frequency).freqstr

    return ds_out


def to_gregorian_calendar(ds, add_missing=False):

    """
    Process the calendar

    Arguments:

        ds (:class:`xarray.Dataset`): The input dataset.

        add_missing (bool): If set to True, NaN slices are created for any
            missing datetimes during the conversion process. Defaults to False.
            This option is useful when it is important to maintain a consistent
            time frequency across the dataset.

    Returns:
        :class:`xarray.Dataset`: ataset with time labels set in the gregorian
        calender.

    Example:
        .. ipython::
           :okwarning:

           In [0]: import xarray, pyku
              ...: ds = pyku.resources.get_test_data('cftime_data')
              ...: ds.pyku.to_gregorian_calendar()
    """

    import xarray as xr
    import numpy as np

    # Set the aling_on option to year for 306_day calendar
    # ----------------------------------------------------

    if ds.time.dt.calendar in ['360_day']:
        align_on = 'year'
    else:
        align_on = None

    # Prepare copy
    # ------------

    ds_out = ds.copy()

    if ds.time.dt.calendar in ['proleptic_gregorian']:

        logger.info(
            "Dataset already with a proleptic_gregorian calendar. "
            "Doing nothing."
        )
        return ds

    # Check the calendar convert to gegorian
    # --------------------------------------

    if ds.time.dt.calendar in ['noleap', '360_day']:

        ds_out = ds.convert_calendar(
            'proleptic_gregorian',
            missing=np.nan if add_missing else None,
            align_on=align_on,
            use_cftime=False
        )

    # Do the same for time_bnds if it is present in the dataset
    # ---------------------------------------------------------

    time_bounds_exist = any(
        elem in ds.keys() for elem in meta_dict['temporal_bounds']
    )

    if time_bounds_exist:

        # Check the type on the lower bound of the first time bound
        # ---------------------------------------------------------

        if ds.time_bnds.dt.calendar not in ['noleap', '360_day']:

            message = (
                "Calendar shall be 'noleap' or '360_day'. "
                f"{ds.time_bnds.dt.calendar} is not supported."
            )
            raise Exception(message)

        if ds.time_bnds.dt.calendar in ['noleap', '360_day']:

            # Generate xarray Datarrays with lower and upper time bounds
            # ----------------------------------------------------------

            lower_time_bounds = xr.DataArray(
                None,
                dims=["time"],
                coords={
                    "time": ds.time_bnds[:, 0].values,
                },
            )

            upper_time_bounds = xr.DataArray(
                None,
                dims=["time"],
                coords={
                    "time": ds.time_bnds[:, 1].values,
                },
            )

            # Convert to propleptic gregorian calendar
            # ----------------------------------------

            lower_time_bounds = lower_time_bounds.convert_calendar(
                'proleptic_gregorian',
                missing=np.nan if add_missing else None,
                align_on=align_on,
                use_cftime=False
            )

            upper_time_bounds = upper_time_bounds.convert_calendar(
                'proleptic_gregorian',
                missing=np.nan if add_missing else None,
                align_on=align_on,
                use_cftime=False
            )

            # Set new time bounds
            # -------------------

            time_bnds = [
                [lower, upper]
                for (lower, upper)
                in zip(
                    lower_time_bounds.time.values,
                    upper_time_bounds.time.values
                )
            ]

            # Assign new time boundaries
            # --------------------------

            ds_out['time_bnds'].values = time_bnds

    return ds_out


def to_calendar(ds, calendar=None, add_missing=False):

    """
    Process the calendar

    Arguments:

        ds (:class:`xarray.Dataset`): The input dataset.

        calendar (str): The output calendar {noleap, 360_day}.

        add_missing (bool): If set to True, NaN slices are created for any
            missing datetimes during the conversion process. Defaults to False.
            This option is useful when it is important to maintain a consistent
            time frequency across the dataset.

    Returns:
        :class:`xarray.Dataset`:
            Dataset with time labels set in the gregorian calender

    Example:
        .. ipython::

           In [0]: import xarray, pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.to_calendar(calendar='noleap')
    """

    import xarray as xr

    # Prepare copy
    # ------------

    ds_out = ds.copy()

    data_calendar = ds.time.dt.calendar

    # Check the calendar convert to gegorian
    # --------------------------------------

    if calendar in ['noleap'] and data_calendar in ['proleptic_gregorian']:

        ds_out = ds.convert_calendar(
            'noleap',
            missing=None,
            use_cftime=True
        )

    elif calendar in ['360_day'] and data_calendar in ['proleptic_gregorian']:

        ds_out = ds.convert_calendar(
            '360_day',
            missing=None,
            use_cftime=True,
            align_on='year'
        )

    else:
        message = (
            f"convertion from {data_calendar} to {calendar} not implemented"
        )
        raise Exception(message)

    # Do the same for time_bnds if it is present in the dataset
    # ---------------------------------------------------------

    if 'time_bnds' in ds.keys():

        # Generate xarray Datarrays with lower and upper time bounds
        # ----------------------------------------------------------

        lower_time_bounds = xr.DataArray(
            None,
            dims=["time"],
            coords={
                "time": ds.time_bnds[:, 0].values,
            },
        )

        upper_time_bounds = xr.DataArray(
            None,
            dims=["time"],
            coords={
                "time": ds.time_bnds[:, 1].values,
            },
        )

        if calendar in ['noleap'] and data_calendar in ['proleptic_gregorian']:

            lower_time_bounds = lower_time_bounds.convert_calendar(
                'noleap',
                missing=None,
                use_cftime=True
            )

            upper_time_bounds = upper_time_bounds.convert_calendar(
                'noleap',
                missing=None,
                use_cftime=True
            )

        elif calendar in ['360_day'] \
                and data_calendar in ['proleptic_gregorian']:

            lower_time_bounds = lower_time_bounds.convert_calendar(
                '360_day',
                missing=None,
                use_cftime=True,
                align_on='year'
            )

            upper_time_bounds = upper_time_bounds.convert_calendar(
                'noleap',
                missing=None,
                use_cftime=True,
                align_on='year'
            )

        else:
            message = (
                f"convertion from {data_calendar} to {calendar} not "
                "implemented."
            )
            raise Exception(message)

        # Set new time bounds
        # -------------------

        time_bnds = [
            [lower, upper]
            for (lower, upper)
            in zip(
                lower_time_bounds.time.values,
                upper_time_bounds.time.values
            )
        ]

        # Assign new time boundaries
        # --------------------------

        ds_out['time_bnds'].values = time_bnds

    return ds_out


def select_common_datetimes(ds1, ds2):

    """
    Select the datetimes common to both datasets.

    Aruments:
        ds1 (:class:`xarray.Dataset`): The first dataset.
        ds2 (:class:`xarray.Dataset`): The second dataset.

    Returns:
        :class:`xarray.Dataset`:
            Tuple of :class:`xarray.Dataset` with common datetimes. If either
            dat_mod or dat_obs is None, the function just returns the inputs.
    """

    if ds1 is None or ds2 is None:
        return ds1, ds2

    # Drop entries with no data
    # -------------------------

    ds1 = ds1.dropna('time', how='all')
    ds2 = ds2.dropna('time', how='all')

    # Available model datetimes
    # -------------------------

    ds1_times = list(ds1.coords['time'].values)

    # Available observation datetimes
    # -------------------------------

    ds2_times = list(ds2.coords['time'].values)

    # Find intersection of model and observation datetimes
    # ----------------------------------------------------

    intersection = sorted(list(set(ds1_times) & set(ds2_times)))

    if len(intersection) == 0:
        message = (
            "No common datetimes between the dataset found. The first 3 time "
            f"labels of the first dataset are {ds1.time.values[0:3]} and the "
            "first 3 time labels of the second dataset are "
            f"{ds2.time.values[0:3]}"
        )
        logger.warn(message)

    # Select common datetimes
    # -----------------------

    return ds1.sel(time=intersection), ds2.sel(time=intersection)


def filter_incomplete_datetimes(ds, frequency=None, freq_resampled=None):

    """
    Filter dataset for incomplete datetimes.

    **Use case 1**

    When analyzing hourly data to calculate daily averages, it is crucial to
    address instances where hourly data is incomplete. For instance, if the
    dataset begins at 2010-04-07T01:00 instead of 2010-04-07T00:00, the entire
    day of 2010-04-07 should be excluded from the analysis.

    **Use case 2**

    In the analysis of hourly data for computing daily averages, it is crucial
    to account for instances of incomplete hourly data. For example, if the
    dataset starts at 2010-04-07T01:00 rather than 2010-04-07T00:00, it's
    necessary to exclude the entire day of 2010-04-07 from the analysis.

    Arguments:

        ds (:class:`xarray.Dataset`): The input dataset.

        frequency (str):
            Resampling frequency string (e.g. ``1H``, ``1D``).

        freq_resampled (str): Deprecated. Do not use.

    Returns:
        :class:`xarray.Dataset`: Dataset filtered for partial data.

    References:
        https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases
    """

    import xarray as xr
    import numpy as np
    import pyku.meta as meta

    if freq_resampled is not None and frequency is not None:
        raise Exception(
            "Use parameter 'frequency' and set 'freq_resampled to None'")

    if freq_resampled is not None:
        logger.warn("'freq_resampled' is deprecated. Please use 'frequency'")

    if frequency is not None:
        freq_resampled = frequency

    # Sanity checks
    # -------------

    assert freq_resampled is not None, "Parameter frequency is mandatory!"
    assert isinstance(ds, xr.Dataset), "ds not a xarray Dataset!"

    # Get the frequency of the data
    # -----------------------------

    data_frequency = meta.get_frequency(ds, dtype='freqstr')

    # Resample data to frequency of analysis
    # --------------------------------------

    resampled = ds.resample(time=freq_resampled)

    # Gather datetimes of groups with complete data in list
    # -----------------------------------------------------

    datetimes = []

    # Loop over all groups
    # --------------------

    # The approach involves iterating through each group, determining the
    # expected number of datetimes if the data were complete, and then
    # comparing it to the actual number of datetimes.

    for _, elem in resampled:

        # Calculate datetimes between min and max at frequency
        # ----------------------------------------------------

        ts_range = xr.date_range(
            calendar=ds.time.dt.calendar,
            start=np.min(elem.coords['time'].values),
            end=np.max(elem.coords['time'].values),
            freq=data_frequency
        )

        # Create an empty DataArray without data for resampling
        # -----------------------------------------------------

        time_da = xr.DataArray(None, dims=('time',), coords={'time': ts_range})

        # Resample to frequency. Time label is lower (left) or upper (right)
        # ------------------------------------------------------------------

        resampled_left = \
            time_da.resample(time=freq_resampled, label='left').sum()

        resampled_right = \
            time_da.resample(time=freq_resampled, label='right').sum()

        # Sanity checks
        # -------------

        # There should be one and only one time label. If not this is a Bug.

        assert len(resampled_left.time) == 1, 'pyku Bug: contact a maintainer'
        assert len(resampled_right.time) == 1, 'pyku Bug: contact a maintainer'

        # Create datetime range
        # ---------------------

        ts_range = xr.date_range(
            calendar=ds.time.dt.calendar,
            start=resampled_left.time.values[0],
            end=resampled_right.time.values[0],
            freq=data_frequency,
            inclusive='left'
        )

        # Compare number of datetimes in group to expectation for complete data
        # ---------------------------------------------------------------------

        count = len(ts_range)

        # If the count matches, data are complete and add to list
        # -------------------------------------------------------

        if len(elem.coords['time']) == count:
            datetimes.append(elem.coords['time'].values)

    # Concatenate datetimes of all complete groups
    # --------------------------------------------

    datetimes = np.concatenate(datetimes)

    # Selecte datetimes of complete datasets and return
    # -------------------------------------------------

    return ds.sel(time=datetimes)


def set_time_labels_from_time_bounds(ds, how='lower'):

    """
    Set time labels to lower bound, middle of bounds, or upper bound.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
        how (str): 'lower', 'middle', 'upper'

    Returns:
        :class:`xarray.Dataset`:
            Dataset with time labels set to the lower bound of the time bounds.

    Note:
        The CMOR standard is to use the middle of the bounds

    Example:
        .. ipython::

           In [0]: import xarray, pyku
              ...: ds = pyku.resources.get_test_data('hyras-tas-monthly')
              ...: ds.pyku.set_time_labels_from_time_bounds(how='lower')
    """

    import pyku.meta as meta

    # Sanity checks
    # -------------

    list_of_time_point_variables = []

    for var in meta.get_geodata_varnames(ds):
        if ds[var].attrs.get('cell_methods', None) in ['time: point']:
            list_of_time_point_variables.append(var)

    if len(list_of_time_point_variables) != 0:

        message = (
            f"Variables {list_of_time_point_variables} have attribute "
            "`cell_methods=time:point`. This means that the variable should "
            "not have time bounds, and therefore the time labels should not "
            "be set from the time bounds. To override, you can remove the "
            "`cell_methods` attribute."
        )
        raise Exception(message)

    # Get time bounds
    # ---------------

    time_bnds = meta.get_time_bounds(ds)

    if time_bnds is None:
        return ds

    if how == 'lower':
        times = [lower for lower, upper in time_bnds]

    elif how == 'middle':
        times = [lower + (upper - lower) / 2. for lower, upper in time_bnds]

    elif how == 'upper':
        times = [upper for lower, upper in time_bnds]

    else:
        message = (
            "Parameter 'how' shall be 'lower', 'middle', or 'upper', "
            f"not {how}"
        )
        raise Exception(message)

    # Assign time bounds to dataset
    # -----------------------------

    ds = ds.assign(time=times)

    return ds


def set_time_bounds_from_time_labels(ds, offset=None):

    """
    Infer time bounds from time labels.

    Arguments:

        ds (:class:`xarray.Dataset`): The input dataset.

        offset (str): Optional, default to None. Specifies an offset to adjust
            the time bounds, given as a frequency string. This is useful when
            the timestamp is, for example, `1986-01-01T12:00:00`, and the
            desired time bounds are `[1986-01-01T00:00:00,
            1986-01-02T00:00:00]`. For available offset aliases, refer to the
            Pandas documentation:
            https://pandas.pydata.org/docs/user_guide/timeseries.html#offset-aliases

    Returns:
        :class:`xarray.Dataset`: Dataset including time bounds.

    Example:
        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hostrada')
              ...: ds.pyku.set_time_bounds_from_time_labels()
    """

    import pyku.meta as meta
    import xarray as xr
    from pandas.tseries.frequencies import to_offset

    # Sanity checks
    # -------------

    if not isinstance(ds, xr.Dataset):

        raise TypeError(
            "Expected an instance of AreaDefinition, but got "
            f"{type(ds).__name__} instead."
        )

    if 'time' not in list(dict(ds.sizes).keys()):
        raise KeyError("No 'time' dimension in dataset.")

    # Keep attributes accross operations
    # ----------------------------------

    xr.set_options(keep_attrs=True)

    # Get the time bounds name
    # ------------------------

    time_bounds_varname = meta.get_time_bounds_varname(ds)

    # Sanity checks
    # -------------

    if time_bounds_varname is not None:
        raise KeyError("time bounds already in dataset")

    # Get the data frequency
    # ----------------------

    frequency = meta.get_frequency(ds, dtype='freqstr')

    # Get the first time label
    # ------------------------

    first_datetime = ds.coords['time'].values[0]

    # Add offset as needed
    # --------------------

    idealized_calendars = [
        'noleap', '365_day', '360_day', '366_day', 'all_leap'
    ]

    if offset is not None and ds.time.dt.calendar in idealized_calendars:
        raise Exception(
            f"calendar {ds.time.dt.calendar} is not implemented when used "
            "together with parameter 'offset'."
        )

    if offset is not None:
        first_datetime = first_datetime + to_offset(offset)

    # Determine lower and upper bounds
    # --------------------------------

    time_bnds_lower = xr.date_range(
        start=first_datetime,
        freq=frequency,
        periods=len(ds.coords['time'].data),
        calendar=ds.time.dt.calendar,
    )

    time_bnds_upper = xr.date_range(
        start=time_bnds_lower[1],
        freq=frequency,
        periods=len(ds.coords['time'].data),
        calendar=ds.time.dt.calendar,
    )

    # Determine lower and higher time bounds
    # --------------------------------------

    time_bnds = [
        [ts_left, ts_right]
        for ts_left, ts_right
        in zip(time_bnds_lower, time_bnds_upper)
    ]

    # Create DataArray with time bounds and merge
    # -------------------------------------------

    da = xr.DataArray(
        name='time_bnds',
        data=time_bnds,
        dims=["time", "bnds"],
        attrs={}
    )

    # Merge time bounds to dataset
    # ----------------------------

    # Why is there a join=override here?

    ds = xr.merge([ds, da], join='override')

    return ds


def split_by_datetimes(ds):

    """
    Subset a dataset by datetime according to the CMOR convention.

    This function partitions large datasets into smaller, manageable segments
    following the Climate Model Output Rewriter (CMOR) convention. It generates
    subsets of the dataset organized by specified time intervals, such as
    yearly, 5-year, 10-year, or 100-year periods. By using a generator, this
    function optimizes memory usage by loading only the required data into
    memory as needed.

    If the frequency cannot be inferred from the data or the dataset is large,
    an hourly frequency is assumed, and files are split into one-year segments.
    For smaller datasets, the original dataset is returned without
    modifications.

    Arguments:
        dataset (:class:`xarray.Dataset`): The input dataset containing
            time-based data to be split.

    Yields:
        :class:`xarray.Dataset`: Subsets of the input dataset, grouped by
        appropriate time intervals based on the temporal resolution of the
        data.
    """

    import pyku.meta as meta
    import numpy as np
    import itertools
    from pandas.tseries.frequencies import to_offset

    # Edge case
    # ---------

    if 'time' not in ds.sizes.keys() or len(ds.time) < 2:
        yield ds
        return

    # Get data frequency
    # ------------------

    # The goal is to determine the frequency and split the files following the
    # COMR convention. Hourly files are split into one-year segments, daily and
    # 12-hourly files into five-year segments, and monthly files into ten-year
    # segments. Other frequencies are handled similarly based on available
    # guidelines. If the frequency cannot be inferred from the data or the
    # dataset is large, an hourly frequency is assumed, and files are split
    # into one-year segments. For smaller datasets, the original dataset is
    # returned without modifications.

    try:
        data_frequency = meta.get_frequency(ds, dtype='freqstr')

    except Exception:
        logger.warning(
            "Unable to determine the frequency from the dataset. This might "
            "be due to missing timestamps. Please check your data for gaps."
        )
        if ds.nbytes/(1024 ** 3) > 4:
            logger.warning(
                "The dataset is large. Assuming an hourly or higher "
                "frequency, the file will be split into yearly files for "
                "better manageability."
            )
            data_frequency = '1h'
        else:
            yield ds
            return

    # Split data into groups of 1 year, if 1-hourly, 3-hourly or 6-hourly
    # -------------------------------------------------------------------

    if to_offset(data_frequency) in \
            [to_offset('h'), to_offset('3h'), to_offset('6h')]:

        years, _ = zip(*ds.groupby('time.year'))
        groups = np.array([
            list(g) for k, g
            in itertools.groupby(years, lambda i: (i - 1) // 1)
        ], dtype=object)

    # Split data into groups of 5 years, if daily
    # --------------------------------------------

    elif to_offset(data_frequency) in [to_offset('12h'), to_offset('1D')]:

        years, _ = zip(*ds.groupby('time.year'))
        groups = np.array([
            list(g) for k, g
            in itertools.groupby(years, lambda i: (i - 1) // 5)
        ], dtype=object)

    # Split data into groups of 10 years, if monthly or seasonal
    # ----------------------------------------------------------

    elif to_offset(data_frequency) in [to_offset('1ME'), to_offset('QS-DEC')]:

        years, _ = zip(*ds.groupby('time.year'))
        groups = np.array([
            list(g) for k, g
            in itertools.groupby(years, lambda i: (i - 1) // 10)
        ], dtype=object)

    # Split data into groups of 100 years, if yearly
    # ----------------------------------------------

    elif (to_offset(data_frequency) == to_offset('1YS')):
        years, _ = zip(*ds.groupby('time.year'))
        groups = np.array([
            list(g) for k, g
            in itertools.groupby(years, lambda i: (i - 1) // 100)
        ], dtype=object)

    # If no data frequency detected, split in 5 groups and raise warning
    # ------------------------------------------------------------------

    else:
        years, _ = zip(*ds.groupby('time.year'))
        groups = np.array([
            list(g) for k, g
            in itertools.groupby(years, lambda i: (i - 1) // 5)
        ], dtype=object)

        logger.warning('No data frequency detected!')
        logger.warning('Splitting data into groups of 5 years!')

    for group in groups:
        yield ds.sel(time=slice(f"{min(group)}", f"{max(group)}"))


def add_missing_time_labels(ds, frequency=None):
    """
    Add missing time labels to the dataset, filling corresponding data
    slices with NaN.

    This function ensures that all expected time labels, based on the specified
    frequency, are present in the dataset. Missing time labels are inserted
    along with data slices filled entirely with NaN values.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
        frequency (str, mandatory): The frequency string defining the expected
            time intervals (e.g., "1H" for hourly, "1D" for daily).

    Returns:
        :class:`xarray.Dataset`: The dataset with missing time labels added,
        where corresponding slices are filled with NaN values.
    """

    import pyku.meta as meta
    import pandas as pd

    if frequency is None:
        raise Exception("Parameter 'frequency' is mandatory")

    expected_times = pd.date_range(
        start=ds.time.data[0],
        end=ds.time.data[-1],
        freq=frequency
    )

    if meta.has_time_bounds(ds):
        logger.warning(
            "Time bounds detected in the dataset. Dropping them as support "
            "for this feature is not yet implemented."
        )
        time_bounds_varname = meta.get_time_bounds_varname(ds)
        ds = ds.drop_vars(time_bounds_varname)

    ds = ds.reindex(time=expected_times)

    return ds
