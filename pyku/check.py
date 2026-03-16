#!/usr/bin/env python3

"""
Functions for checking data

See also:
    pyku configuration files:

    * ``./pyku/etc/drs.yaml``
    * ``./pyku/etc/metadata.yaml``
"""

from . import logger
from . import drs_data
from . import meta_dict as meta_data


def check(ds, standard=None, completeness_period=None, all_nan_slices=False):

    """
    Perform the following checks:

    * If any all NaN slice is found,
    * valid bounds,
    * georeferencing,
    * units,
    * CMOR variable names,
    * frequency,
    * the role of variables
    * if all timestamps are available within completeness period

    Arguments:

        ds (:class:`xarray.Dataset`): The input dataset.

        standard (str): Optional, defaults to None. `cordex`, `obs4mips`,
            `cordex_adjust`, `cordex_adjust_interp` or any standard implemented
            in the *pyku* configuration file ``./pyku/etc/drs.yaml``. If None,
            compliance of the metadata with a standard is not checked.

        completeness_period (freqstr): Optional frequency string (e.g. '1MS',
            '1YS'). Defaults to None. If given, it will be checked with the
            given data frequency if all timestamps are available. Possible
            values can be found at:
            https://pandas.pydata.org/docs/user_guide/timeseries.html#offset-aliases

        all_nan_slices (bool): Defaults to true, optional. Check if slices with
           only NaNs exist in dataset

    Returns:
        :class:`pandas.DataFrame`: The checks and issues.

    Example:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.check(standard='obs4mips')
    """

    import pandas as pd

    # All issues are gathered in the list of issues
    # ---------------------------------------------

    issues = []

    # Perform checks and append to the list of issues
    # -----------------------------------------------

    issues.append(check_valid_bounds(ds))
    issues.append(check_georeferencing(ds))
    issues.append(check_units(ds))
    issues.append(check_cmor_varnames(ds))
    issues.append(check_variables_cmor_metadata(ds))
    issues.append(check_frequency(ds))
    issues.append(check_variables_role(ds))
    issues.append(check_datetimes(ds))

    # Optional checks
    # ---------------

    if completeness_period is not None:
        issues.append(
            check_datetime_completeness(ds, frequency=completeness_period)
        )

    if all_nan_slices:

        dataset_size = ds.nbytes / (1024 ** 3)
        if dataset_size > 10:
            logger.warning(
                f"Large dataset detected ({dataset_size:.2f} GB). Checking for"
                "all NaN slices may be slow."
            )

        issues.append(check_allnan_slices(ds))

    if standard is not None:
        issues.append(check_drs(ds, standard=standard))

    # Concatenate issues and return
    # -----------------------------

    issues = pd.concat(issues, ignore_index=True)

    return issues


def check_metadata(ds, standard=None, completeness_period=None):

    """
    Perform the following checks:

    * georeferencing,
    * units,
    * CMOR variable names,
    * CMOR variables metdata
    * frequency,
    * the role of variables
    * CMOR standard
    * Completeness of data over a given period

    The difference with :func:`pyku.check.check` is that the resource intensive
    testing function like checking for all-nan slices or checking time bounds
    are left out.

    Arguments:

        ds (:class:`xarray.Dataset`): The input dataset.

        standard (str): Optional standard. One of `cordex`, `obs4mips`,
            `cordex_adjust`, `cordex_adjust_interp` or any standard implemented
            in pyku configuration file ``./pyku/etc/drs.yaml``. If None,
            compliance of metadata with a standard is not checked.

        completeness_period (freqstr): Frequency string (e.g. '1MS', '1YS'). It
            will then be checked with the given data frequency if all
            timestamps are available. Possible values can be found at:
            https://pandas.pydata.org/docs/user_guide/timeseries.html#offset-aliases

    Returns:
        :class:`pandas.DataFrame`: The checks and issues.

    Example:
        .. ipython::
           :okwarning:

           In [0]: %%time
              ...: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.check_metadata(standard='obs4mips')
    """

    import pandas as pd

    # Issues are gathered in a list
    # -----------------------------

    issues = []

    # perform checks and append to list of issues
    # -------------------------------------------

    issues.append(check_georeferencing(ds))
    issues.append(check_units(ds))
    issues.append(check_cmor_varnames(ds))
    issues.append(check_variables_cmor_metadata(ds))
    issues.append(check_frequency(ds))
    issues.append(check_variables_role(ds))
    issues.append(check_datetimes(ds))

    # Checking data completeness for a given period is optional
    # ---------------------------------------------------------

    if completeness_period is not None:
        issues.append(
            check_datetime_completeness(ds, frequency=completeness_period)
        )

    # Checking the DRS standard is optional
    # -------------------------------------

    if standard is not None:
        issues.append(check_drs(ds, standard=standard))

    # Concatenate issues and return
    # -----------------------------

    issues = pd.concat(issues, ignore_index=True)

    return issues


def check_datetimes(ds):

    """
    Check datetimes.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`pandas.DataFrame`: The checks and issues.

    Example:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.check_datetimes()
    """

    import cftime
    import numpy as np
    import pandas as pd
    import pyku.meta as meta
    from pandas.tseries.frequencies import to_offset

    # We will gather issues in this list
    # ----------------------------------

    list_of_issues = []

    # Check if time is a dimension
    # ----------------------------

    the_check = 'has_time_dimension'
    the_description = 'Check if data have a time dimension'
    the_result = True if 'time' in list(ds.sizes.keys()) else False
    the_issue = None if the_result else "Time dimension not available"

    list_of_issues.append((the_check, the_result, the_issue, the_description))

    # Immediately return if the time dimension is not available
    # ---------------------------------------------------------

    if the_result is False:
        return pd.DataFrame(
            data=[(the_check, the_result, the_issue, the_description)],
            columns=['key', 'value', 'issue', 'description']
        )

    # Check datatypes
    # ---------------

    the_check = 'time_is_numpy_datetime64_or_cftime'
    the_description = "Check the data type of the time stamps"

    the_result = (
        isinstance(ds['time'].values[0], np.datetime64)
        or isinstance(ds['time'].values[0], cftime.datetime)
    )

    the_issue = None if the_result else \
        "Only np.datetime64 and cftimes tested in pyku"

    list_of_issues.append((the_check, the_result, the_issue, the_description))

    # Get data frequency
    # ------------------

    try:

        data_frequency = meta.get_frequency(ds, dtype='freqstr')

    # Return immediately in case of issue
    # -----------------------------------

    except Exception as e:

        the_check = 'data_frequency_can_be_read'
        the_description = (
            "Check if the frequency can be read with the pyku meta "
            "get_frequency function. This message is only outputed in case "
            "an issue is found in that regard with the data. and further "
            "checks are not performed."
        )
        the_result = False
        the_issue = f"{e}"

        list_of_issues.append(
            (the_check, the_result, the_issue, the_description)
        )

        return pd.DataFrame(
            data=list_of_issues,
            columns=['key', 'value', 'issue', 'description']
        )

    # Check datetimes at midnight or midday, but not for cftime
    # ---------------------------------------------------------

    is_12hourly = to_offset(data_frequency) == to_offset('12h')
    is_daily = to_offset(data_frequency) == to_offset('1D')
    is_monthly = to_offset(data_frequency) == to_offset('1MS')
    is_seasonal = to_offset(data_frequency) == to_offset('QS-DEC')
    is_yearly = to_offset(data_frequency) == to_offset('1YS')

    if is_12hourly or is_daily or is_monthly or is_seasonal or is_yearly:

        the_check = 'time_stamps_are_midnight_or_noon'
        the_description = 'Check if all timestamps are midnight or noon'

        all_midnight_or_noon = bool(ds.time.dt.hour.isin([0, 12]).all())

        the_result = all_midnight_or_noon
        the_issue = None if all_midnight_or_noon else \
            f"datetimes are {ds['time'].values[0:10]}"

        list_of_issues.append(
            (the_check, the_result, the_issue, the_description)
        )

    issues = pd.DataFrame(
        data=list_of_issues,
        columns=['key', 'value', 'issue', 'description']
    )

    return issues


def check_datetime_completeness(ds, frequency):

    """
    Check data completeness for a given frequency/period. Note that the
    function says frequency when really, a period is needed.

    Arguments:

        ds (:class:`xarray.Dataset`): The input dataset.

        frequency (freqstr): Frequency string (e.g. `1D`, `3H`, `1D`, `1MS`,
            `1YS`, `1YS`, or `Q`). The complete list is available at:
            https://pandas.pydata.org/docs/user_guide/timeseries.html#offset-aliases

    Returns:
        :class:`pandas.DataFrame`: The checks and issues.

    Example:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.check_datetime_completeness(frequency='1MS')
    """

    import textwrap
    import cftime
    import numpy as np
    import pandas as pd
    import xarray as xr

    # We will gather issues in this list
    # ----------------------------------

    list_of_issues = []

    # Check if time is a dimension
    # ----------------------------

    if 'time' not in list(ds.sizes.keys()):

        list_of_issues.append((
            "Time dimension",
            "NA",
            "Time dimension not available"
        ))

        issues = pd.DataFrame(
            data=list_of_issues,
            columns=['key', 'value', 'issue']
        )

        return issues

    else:

        list_of_issues.append((
            "Time dimension",
            "available",
            None
        ))

    # Check datatypes
    # ---------------

    is_numpy_datetime64_or_cftime = (
        isinstance(ds['time'].values[0], np.datetime64) or
        isinstance(ds['time'].values[0], cftime.datetime)
    )

    if is_numpy_datetime64_or_cftime is False:

        list_of_issues.append((
            "Type of datetimes in first dataset",
            f"Type is {type(ds['time'].values[0])}",
            "Only numpy.datetime64 and cftime supported at the moment"
        ))

        issues = pd.DataFrame(
            data=list_of_issues,
            columns=['key', 'value', 'issue']
        )

        return issues

    else:

        list_of_issues.append((
            "Type of datetime in first dataset",
            f"Type is {type(ds['time'].values[0])}",
            None
        ))

    # Get the frequency of the data
    # -----------------------------

    if len(check_frequency(ds).query('issue.notna()')):

        list_of_issues.append((
            "Datetimes",
            "Not checking data completeness",
            "Not possible because frequency could not be determined"
        ))

        issues = pd.DataFrame(
            data=list_of_issues,
            columns=['key', 'value', 'issue']
        )

        return issues

    # Get the frequency of the data
    # -----------------------------

    data_frequency = xr.infer_freq(ds.time)

    if data_frequency is None:

        the_check = 'data_are_complete'
        the_result = 'Not applicable'
        the_issue = (
            'Frequency cannot be read from time labels and thus cannot check'
            'for datetime completeness'
        )
        the_description = 'Tried to infer frequency from the time labels'

        issues = pd.DataFrame(
            data=[(the_check, the_result, the_issue, the_description)],
            columns=['key', 'value', 'issue', 'description']
        )

        return issues

    # Resample data to frequency of analysis
    # --------------------------------------

    res = ds[['time']].resample(time=frequency)

    # Loop over all groups
    # --------------------

    # The strategy is to go through each group, calculate the number of
    # datetimes if the data were complete, and finally compare to the actual
    # number of datetimes

    for _, _ds in res:

        ts_range = xr.date_range(
            calendar=ds.time.dt.calendar,
            start=np.min(_ds.coords['time'].values),
            end=np.max(_ds.coords['time'].values),
            freq=data_frequency
        )

        # Create DataArray with time only for the convenience functions
        # -------------------------------------------------------------

        time_dataarray = xr.DataArray(None, coords=[ts_range], dims=["time"])

        resampled_left = time_dataarray.resample(
            time=frequency, label='left').sum()

        resampled_right = time_dataarray.resample(
            time=frequency, label='right').sum()

        left_datetime = resampled_left.time.values[0]
        right_datetime = resampled_right.time.values[0]

        if len(resampled_left.time.values) != 1 \
           or len(resampled_right.time.values) != 1:

            message = textwrap.dedent(
                f"""
                The code should not be in the situation. There should be only 2
                elements in the following variables. Need Thinking and
                debugging:

                {len(resampled_left.index)=}
                {resampled_left.index=}

                {len(resampled_right.index)=}
                {resampled_right.index=}

                """
            )

            raise Exception(message)

        # Calculate data expected between left and right datetimes
        # --------------------------------------------------------

        ts_range = xr.date_range(
            calendar=ds.time.dt.calendar,
            start=left_datetime,
            end=right_datetime,
            freq=data_frequency,
            inclusive='left'
        )

        # Compare number of datetimes in group to expectation for complete data
        # ---------------------------------------------------------------------

        count = len(ts_range)

        # If the count matches, data are complete
        # ---------------------------------------

        if len(_ds.coords['time']) == count:

            list_of_issues.append((
                "Datetimes",
                (
                    f"Checking data completeness between {left_datetime} "
                    f"and {right_datetime} for {frequency}"
                ),
                None
            ))

        else:

            difference = np.setdiff1d(
                ts_range.values, _ds.coords['time'].values
            )

            list_of_issues.append((
                "Datetimes",
                (
                    f"Checking data completeness between {left_datetime} "
                    f"and {right_datetime} for {frequency}"
                ),
                f"Incomplete datetimes: {difference}"
            ))

    # Gather issues in panda dataframe
    # --------------------------------

    issues = pd.DataFrame(
        data=list_of_issues,
        columns=['key', 'value', 'issue']
    )

    return issues


def check_allnan_slices(ds):

    """
    Check for allnan slices along time

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`pandas.DataFrame`: The checks and issues.

    Examples:
        .. ipython::

           In [0]: import pyku
              ...:
              ...: ds = pyku.resources.get_test_data('hyras')
              ...:
              ...: ds.pyku.check_allnan_slices()
    """

    import pandas as pd
    import pyku.meta as meta

    # Copy array to run operations out-of-place
    # -----------------------------------------

    # The in-place operations on the Datasets (e.g. where) otherwise modify the
    # original data

    ds_copy = ds.copy()

    # Automatically chunk the Dataset
    # -------------------------------

    # This avoid a large computation graph when looking for values below and
    # above the threshold. For the computations at hand, the exact chunking
    # should be quite unimportant.

    # Marker. This is turned off by default now and should be dealt with when
    # reading the data I think. The problem is that when using one of the weird
    # cftime calendars with the time bounds sets and using
    # ds[['time_bnds']].chunk(chunks='auto'), xarray/dask is not able to deal
    # with the chunking automatically and this must be done manually with
    # ds[['time_bnds']].chunk({'time': 10})

    # The command is kept commented out for now, but indeed should most likely
    # be left commented out and the user should take care of the chunking.

    # ds_copy = ds_copy.chunk(chunks='auto')

    # Special case if the dataset does not contain the time dimension
    # ---------------------------------------------------------------

    if 'time' not in list(ds_copy.sizes.keys()):

        the_check = 'has_all_nan_slices'
        the_result = 'na'
        the_issue = None
        the_description = 'No check fo all nan slices without time dimension.'

        issues = pd.DataFrame(
            data=[(the_check, the_result, the_issue, the_description)],
            columns=['key', 'value', 'issue', 'description']
        )

        return issues

    # Get the number of datetimes in the dataset
    # ------------------------------------------

    ntimes = len(ds.time.values)

    data = []

    for var in meta.get_geodata_varnames(ds_copy):

        var_ntimes = \
            len(ds_copy[var].dropna(dim='time', how='all').time.values)

        if var_ntimes == ntimes:
            data.append((
                f'{var} allnan',
                f"{var_ntimes} time labels for {var}",
                None
            ))

        else:
            data.append((
                f"{var} allnan",
                f"{var_ntimes} time labels for {var}",
                f"allnan slice found for {var} {var_ntimes}/{ntimes} time "
                + "labels"
            ))

    issues = pd.DataFrame(
        data=data,
        columns=['key', 'value', 'issue']
    )

    return issues


def check_valid_bounds(ds, bounds=None):

    """
    Check bounds

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
        bounds (dict): Nested dictionary.

    Returns:
        :class:`pandas.DataFrame`: The checks and issues.

    Examples:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.check_valid_bounds()

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.check_valid_bounds(
              ...:     bounds = {
              ...:         'tas': {
              ...:             'units': 'celsius',
              ...:             'valid_bounds': [1, 20]
              ...:         }
              ...:     }
              ...: )
    """

    import pandas as pd
    import dask
    import pyku.meta as meta
    import pyku.drs as drs

    # Copy array to run operations out-of-place
    # -----------------------------------------

    # The in-place operations on the Datasets (e.g. where) otherwise modify the
    # original data

    ds_copy = ds.copy()

    # Automatically chunk the Dataset
    # -------------------------------

    # This avoid a large computation graph when looking for values
    # below and above the threshold. For the computations at hand, the exact
    # chunking should be quite unimportant.

    # Marker. This is turned off by default now and should be dealt with when
    # reading the data I think. The problem is that when using one of the weird
    # cftime calendars with the time bounds sets and using
    # ds[['time_bnds']].chunk(chunks='auto'), xarray/dask is not able to deal
    # with the chunking automatically and this must be done manually with
    # ds[['time_bnds']].chunk({'time': 10})

    # The command is kept commented out for now, but indeed should most likely
    # be left commented out and the user should take care of the chunking.

    # ds_copy = ds_copy.chunk(chunks='auto')

    if bounds:
        bounds_dict = {'variables': bounds}
        ds_varnames = list(bounds_dict.get('variables').keys())

    else:
        try:
            ds_copy = drs.to_cmor_varnames(ds_copy)
            ds_copy = drs.to_cmor_units(ds_copy)

        except Exception:

            the_check = 'can_convert_to_cmor_varname_and_cmor_units'
            the_description = (
                "Try to convert to CMOR varname and units. "
                "Sub check when checking valid bounds since unit conversion "
                "is needed. This issue is only visible when the check fails."
            )
            the_result = False
            the_issue = "Could not convert to CMOR varname or CMOR unit."

            issues = pd.DataFrame(
                data=[(the_check, the_result, the_issue, the_description)],
                columns=['key', 'value', 'issue', 'description']
            )

            return issues

        bounds_dict = drs_data
        ds_varnames = meta.get_geodata_varnames(ds_copy)

    data = []

    for var in ds_varnames:

        da = ds_copy[var]

        lower_threshold = \
            float(bounds_dict.get('variables').get(var).get('valid_bounds')[0])

        upper_threshold = \
            float(bounds_dict.get('variables').get(var).get('valid_bounds')[1])

        logger.debug(f"{var=}")
        logger.debug(f"{lower_threshold=}")
        logger.debug(f"{upper_threshold=}")

        above_threshold = da.where(da > upper_threshold)
        where_above_threshold = \
            dask.array.argwhere(~dask.array.isnan(above_threshold))
        where_above_threshold = where_above_threshold.compute()
        count_above_threshold = where_above_threshold.shape[0]

        logger.debug(f"{where_above_threshold=}")
        logger.debug(f"{count_above_threshold=}")

        data.append((
            f"{var} above {upper_threshold}",
            f"{count_above_threshold} values above threshold",
            f"Shape {above_threshold.data.shape} First 50 indices: " +
            f"{where_above_threshold[0:50]}"
            if count_above_threshold > 1 else None
        ))

        below_threshold = da.where(da < lower_threshold)
        where_below_threshold = \
            dask.array.argwhere(~dask.array.isnan(below_threshold))
        where_below_threshold = where_below_threshold.compute()
        count_below_threshold = where_below_threshold.shape[0]

        logger.debug(f"{where_below_threshold=}")
        logger.debug(f"{count_below_threshold=}")

        data.append((
            f"{var} below {lower_threshold}",
            f"{count_below_threshold} values below threshold",
            f"Shape {below_threshold.data.shape} First 50 indices: " +
            "{where_below_threshold[0:50]}"
            if count_below_threshold > 1 else None
        ))

    issues = pd.DataFrame(
        data,
        columns=['key', 'value', 'issue']
    )

    return issues


def _check_projection_coordinates_exist(ds):

    """
    Check if y and x projection coordinates exist

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        class:`pandas.DataFrame`: Dataframe containing checks and issues.
    """

    import pandas as pd
    import pyku.meta as meta

    # Gather issues in a list
    # -----------------------

    data = []

    # Get y and x projection coordinate variable names exist
    # ------------------------------------------------------

    y_name, x_name = meta.get_projection_yx_varnames(ds)

    the_check = "y_projection_coordinate_exist"
    the_description = "Checking if y projection coordinate available"
    the_result = True if y_name is not None else False
    the_issue = None if y_name is not None else \
        "y projection coordinate not found"

    data.append((the_check, the_result, the_issue, the_description))

    the_check = "x_projection_coordinate_exist"
    the_description = "Checking if x projection coordinate available"
    the_result = True if x_name is not None else False
    the_issue = None if x_name is not None else \
        "x projection coordinate not found"

    data.append((the_check, the_result, the_issue, the_description))

    issues = pd.DataFrame(
        data,
        columns=['key', 'value', 'issue', 'description']
    )

    return issues


def _check_geographic_coordinates_exist(ds):

    """
    Check if lat and lon geographic coordinates exist

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        class:`pandas.DataFrame`: Dataframe containing checks and issues.
    """

    import pandas as pd
    import pyku.meta as meta

    # Gather issues in a list
    # -----------------------

    data = []

    # Get y and x projection coordinate variable names
    # ------------------------------------------------

    lat_name, lon_name = meta.get_geographic_latlon_varnames(ds)

    # Check geographic latitude exist
    # -------------------------------

    the_check = "lat_geographic_coordinate_exist"
    the_description = "Checking if lat geographic coordinate available"
    the_result = True if lat_name is not None else False
    the_issue = None if lat_name is not None else \
        "lat geographic coordinate not found"

    data.append((the_check, the_result, the_issue, the_description))

    # Check geographic longitude exist
    # --------------------------------

    the_check = "lon_geographic_coordinate_exist"
    the_description = "Checking if lon geographic coordinate available"
    the_result = True if lon_name is not None else False
    the_issue = None if lon_name is not None else \
        "lon geographic coordinate not found"

    data.append((the_check, the_result, the_issue, the_description))

    # Build dataframe and return
    # --------------------------

    issues = pd.DataFrame(
        data, columns=['key', 'value', 'issue', 'description']
    )

    return issues


def _check_projection_coordinates_metadata(ds):

    """
    Check y and x projection coordinates metadata.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        class:`pandas.DataFrame`: Dataframe containing checks and issues.
    """

    import pandas as pd
    import pyku.meta as meta

    # Gather issues in a list
    # -----------------------

    data = []

    # Get y and x variable names
    # --------------------------

    y_name, x_name = meta.get_projection_yx_varnames(ds)

    # Return empty dataframe if y_name of x_name do not exist
    # -------------------------------------------------------

    # If projection coordinates y/x are not part of the dataset, it is not
    # possible to check the metadata.

    if y_name is None or x_name is None:
        return pd.DataFrame()

    # check y projection coordinate units
    # -----------------------------------

    y_units = ds[y_name].attrs.get('units', None)

    correct_units = [
        'm',
        'degrees_north',
        'degrees'
    ]

    the_check = "y_projection_coordinate_unit_correct"
    the_description = "Checking if y projection coordinates units"
    the_result = True if y_units in correct_units else False

    the_issue = None if y_units in correct_units else (
        f"y projection coordinate unit {y_units} not correct. "
        f"Acceptable values are {correct_units}'"
    )

    data.append((the_check, the_result, the_issue, the_description))

    # check y projection coordinate units
    # -----------------------------------

    x_units = ds[x_name].attrs.get('units', None)

    correct_units = [
        'm',
        'degrees_east',
        'degrees'
    ]

    the_check = "x_projection_coordinate_unit_correct"
    the_description = "Checking if x projection coordinates units"
    the_result = True if x_units in correct_units else False

    the_issue = None if x_units in correct_units else (
        f"x projection coordinate unit {x_units} not correct. "
        f"Acceptable units are {correct_units}"
    )

    data.append((the_check, the_result, the_issue, the_description))

    # Check y standard name
    # ---------------------

    y_standard_name = ds[y_name].attrs.get('standard_name', None)

    correct_standard_names = [
        'latitude',
        'projection_y_coordinate',
        'grid_latitude'
    ]

    the_check = "y_projection_coordinate_standard_name_correct"

    the_description = "Checking y projection coordinates standard_name"

    the_issue = None if y_standard_name in correct_standard_names else (
        f"y projection coordinate standard_name {y_standard_name} "
        f"not correct. Acceptable value are {correct_standard_names}"
    )

    data.append((the_check, the_result, the_issue, the_description))

    # Check x standard name
    # ---------------------

    x_standard_name = ds[x_name].attrs.get('standard_name', None)

    correct_standard_names = [
        'longitude',
        'projection_x_coordinate',
        'grid_longitude'
    ]

    the_check = "x_projection_coordinate_standard_name_correct"
    the_description = "Checking x projection coordinates standard_name"

    the_issue = None if x_standard_name in correct_standard_names else (
        f"x projection coordinate standard_name {x_standard_name} "
        f"not correct. Acceptable values are {correct_standard_names}"
    )

    data.append((the_check, the_result, the_issue, the_description))

    # Gather in pandas dataframe and return
    # -------------------------------------

    issues = pd.DataFrame(
        data,
        columns=['key', 'value', 'issue', 'description']
    )

    return issues


def _check_geographic_coordinates_metadata(ds):

    """
    Check lat and lon geographic coordinates metadata.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        class:`pandas.DataFrame`: Dataframe containing checks and issues.
    """

    import pandas as pd
    import pyku.meta as meta

    # Gather issues in a list
    # -----------------------

    data = []

    # Get lat and lon variable names
    # ------------------------------

    lat_name, lon_name = meta.get_geographic_latlon_varnames(ds)

    # Return empty dataframe if lat_name of lon_name do not exist
    # -----------------------------------------------------------

    # If geographic coordinates lat/lon are not part of the dataset, it is not
    # possible to check the metadata.

    if lat_name is None or lon_name is None:
        return pd.DataFrame()

    # check lat projection coordinate units
    # -------------------------------------

    lat_units = ds[lat_name].attrs.get('units', None)
    correct_units = ['degrees_north']

    the_check = "lat_geographic_coordinate_unit_correct"
    the_description = "Checking lat geographic coordinate units"
    the_result = True if lat_units in correct_units else False

    the_issue = None if lat_units in correct_units else (
        f"lat projection coordinate unit {lat_units} not correct. Acceptable"
        f"units are {correct_units}"
    )

    data.append((the_check, the_result, the_issue, the_description))

    # check lon projection coordinate units
    # -------------------------------------

    lon_units = ds[lon_name].attrs.get('units', None)

    correct_units = ['degrees_east']

    the_check = "lon_geographic_coordinate_unit_correct"
    the_description = "Checking if lat geographic coordinate units"
    the_result = True if lon_units in correct_units else False

    the_issue = None if lon_units in correct_units else (
        f"lon geographic coordinate unit {lon_units} not correct. Acceptable "
        f"Acceptable units are {correct_units}"
    )

    data.append((the_check, the_result, the_issue, the_description))

    # Check lat standard name
    # -----------------------

    correct_standard_names = ['latitude']

    lat_standard_name = ds[lat_name].attrs.get('standard_name', None)

    the_check = "lat_geographic_coordinate_standard_name_correct"
    the_description = "Checking lat geographic coordinate standard_name"
    the_result = True if lat_standard_name in correct_standard_names else False

    the_issue = None if lat_standard_name in correct_standard_names else (
        f"lat geographic coordinate standard_name {lat_standard_name} not "
        f"correct. Acceptable value are {correct_standard_names}"
    )

    data.append((the_check, the_result, the_issue, the_description))

    # Check lon standard name
    # -----------------------

    correct_standard_names = ['longitude']

    lon_standard_name = ds[lon_name].attrs.get('standard_name', None)

    the_check = "lon_geographic_coordinate_standard_name_correct"
    the_description = "Checking lon geographic coordinate standard_name"
    the_result = True if lon_standard_name in correct_standard_names else False
    the_issue = None if lon_standard_name in correct_standard_names \
        else f"lon geographic coordinate standard_name {lon_standard_name} \
not correct. Acceptable value are {correct_standard_names}"

    data.append((the_check, the_result, the_issue, the_description))

    # Gather in pandas dataframe and return
    # -------------------------------------

    issues = pd.DataFrame(
        data,
        columns=['key', 'value', 'issue', 'description']
    )

    return issues


def _check_cf_projection(ds):

    """
    Check CF projection metadata.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        class:`pandas.DataFrame`: Dataframe containing checks and issues.
    """

    import pandas as pd
    import pyresample.utils

    the_check = "cf_area_def_readable"
    the_description = "Check if CF projection metadata are readable"

    # Try loading area_def
    # --------------------

    try:
        area_def, cf_info = pyresample.utils.load_cf_area(ds)
        the_result = True
        the_issue = None

    except Exception as e:
        the_result = False
        the_issue = f"{str(e)}"

    # Gather in pandas dataframe and return
    # -------------------------------------

    issues = pd.DataFrame(
        [(the_check, the_result, the_issue, the_description)],
        columns=['key', 'value', 'issue', 'description']
    )

    return issues


def _check_area_extent(ds):

    """
    Check area extent.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        class:`pandas.DataFrame`: Dataframe containing checks and issues.
    """

    import pandas as pd
    import pyku.geo as geo
    import pyku.meta as meta

    # Gather issues in a list
    # -----------------------

    data = []

    # Check the data area extent
    # --------------------------

    the_check = 'area_extent_is_readable'

    the_description = (
        "Check if the area extent can be determined from the projection"
        "metadata and the lat and lon geographic coordinates"
    )

    try:

        area_def = geo.get_area_def(ds)

        lower_left_lon, lower_left_lat, upper_right_lon, upper_right_lat = \
            area_def.area_extent_ll

        the_result = True
        the_issue = None

    except Exception as e:

        the_result = False
        the_issue = f"Could not determine the area extent. {str(e)}"

    data.append((the_check, the_result, the_issue, the_description))

    # Check the range of longitudes
    # -----------------------------

    the_check = "longitudes_within_180W_and_180E"

    the_description = (
        "Check that the longitudes are within 180 degree West and 180 degree "
        "East"
    )

    try:

        lat_name, lon_name = meta.get_geographic_latlon_varnames(ds)

        is_between = (ds[lon_name] >= -180) & (ds[lon_name] <= 180)

        all_between = bool(is_between.all())

        if not all_between:

            the_result
            the_issue
            the_result = False
            the_issue = """Longitudes not between 180W and 180E"""

        else:
            the_result = True
            the_issue = None

        data.append((the_check, the_result, the_issue, the_description))

    except Exception as e:

        message = f"Tried to {the_description} but Could not. {e}"
        logger.warning(message)

    issues = pd.DataFrame(
        data,
        columns=['key', 'value', 'issue', 'description']
    )

    return issues


def check_georeferencing(ds):

    """
    Check georeferencing

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`pandas.DataFrame`: The checks and issues.

    Examples:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...:
              ...: ds = pyku.resources.get_test_data('hyras')
              ...:
              ...: ds.pyku.check_georeferencing()
    """

    import pandas as pd

    issues = []
    issues.append(_check_projection_coordinates_exist(ds))
    issues.append(_check_geographic_coordinates_exist(ds))
    issues.append(_check_projection_coordinates_metadata(ds))
    issues.append(_check_geographic_coordinates_metadata(ds))
    issues.append(_check_cf_projection(ds))
    issues.append(_check_area_extent(ds))

    return pd.concat(issues, ignore_index=True)


def check_units(ds):

    """
    Check units

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`pandas.DataFrame`: The checks and issues.

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.check_units()
    """

    import pandas as pd
    import pyku.meta as meta

    ds_copy = ds.copy()
    data = []

    # The strategy is to loop over all geodata variables and try to read the
    # units with metpy/Pint. If this does not work, an issue is raised.

    for var in meta.get_geodata_varnames(ds_copy):

        the_check = f"{var}_units_can_be_read"
        the_description = "Check if units can be read automatically"

        try:

            da = ds_copy[var]
            da = da.metpy.quantify()

            the_result = True
            the_issue = None

        except Exception:

            the_result = False
            the_issue = 'Could not read unit'

            if da.attrs.get('units', None) in ['Celsius']:
                the_issue = "celsius should be in small caps"

            if da.attrs.get('units', None) in ['Percent']:
                the_issue = "percent should be in small caps"

        # Append to list of issues
        # ------------------------

        data.append((the_check, the_result, the_issue, the_description))

    # Generate dataframe from list of issues
    # --------------------------------------

    issues = pd.DataFrame(
        data, columns=['key', 'value', 'issue', 'description']
    )

    return issues


def check_cmor_varnames(ds):

    """
    Check if variable names are CMOR-conform

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`pandas.DataFrame`: The checks and issues.

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.check_cmor_varnames()
    """

    import pandas as pd
    import pyku.meta as meta

    data = [
        (var, var, None) if var in drs_data.get('variables').keys()
        else ('variable name', var, 'Variable not CMOR-conform')
        for var in meta.get_geodata_varnames(ds)
    ]

    issues = pd.DataFrame(
        data,
        columns=['key', 'value', 'issue']
    )

    return issues


def _check_variables_cmor_standard_name(ds):

    """
    Check variable CMOR standard_name.

    Arguments:
        ds (:class:`xarray.Dataset`): Input dataset

    Returns:
        :class:`pandas.DataFrame`: Dataframe containing checks and issues
    """

    import pandas as pd
    import pyku.drs as drs
    import pyku.meta as meta

    # Get geodata varnames in dataset
    # -------------------------------

    varnames = meta.get_geodata_varnames(ds)

    # Gather issues in a list
    # -----------------------

    data = []

    # Loop over all geodata variables
    # -------------------------------

    for varname in varnames:

        the_check = "is_cmor_standard_name"
        the_description = "If possible, check if standard name is CMOR conform"

        cmor_varname = drs.get_cmor_varname(ds[varname])

        if cmor_varname is None:
            the_result = False
            the_issue = "Could not get CMOR standard variable name and hence \
could not check if standard_name is CMOR-conform"

        elif ds[varname].attrs.get('standard_name') is None:
            the_result = False
            the_issue = "Variable has no attribute standard_name"

        else:
            expected_std_name = drs_data.get('variables')\
                                        .get(cmor_varname)\
                                        .get('standard_name')
            read_std_name = ds[varname].attrs.get('standard_name')

            the_result = \
                True if read_std_name in [expected_std_name] else False

            the_issue = None if read_std_name in [expected_std_name] \
                else f"{varname} standard_name is {read_std_name} but the \
expected standard_name is {expected_std_name}"

        data.append((the_check, the_result, the_issue, the_description))

    issues = pd.DataFrame(
        data=data,
        columns=['key', 'value', 'issue', 'description']
    )

    return issues


def _check_variables_cmor_long_name(ds):

    """
    Check variable CMOR long_name.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`pandas.DataFrame`: Dataframe containing checks and issues.
    """

    import pandas as pd
    import pyku.drs as drs
    import pyku.meta as meta

    # Get geodata varnames in dataset
    # -------------------------------

    varnames = meta.get_geodata_varnames(ds)

    # Gather issues in a list
    # -----------------------

    data = []

    # Loop over all geodata variables
    # -------------------------------

    for varname in varnames:

        the_check = "is_cmor_long_name"
        the_description = "Check if long_name is CMOR conform"

        cmor_varname = drs.get_cmor_varname(ds[varname])

        if cmor_varname is None:
            the_result = False
            the_issue = (
                "Could not get CMOR standard variable name and hence could "
                "not check if long_name is CMOR-conform"
            )

        elif ds[varname].attrs.get('long_name') is None:
            the_result = False
            the_issue = "Variable has no attribute long_name"

        else:
            expected_long_name = drs_data.get('variables')\
                                         .get(cmor_varname)\
                                         .get('long_name')
            read_long_name = ds[varname].attrs.get('long_name')

            the_result = \
                True if read_long_name in [expected_long_name] else False

            the_issue = None if read_long_name in [expected_long_name] \
                else f"{varname} long_name is {read_long_name} but the \
expected standard_name is {expected_long_name}"

        data.append((the_check, the_result, the_issue, the_description))

    issues = pd.DataFrame(
        data=data,
        columns=['key', 'value', 'issue', 'description']
    )

    return issues


def _check_variables_cmor_units(ds):

    """
    Check variable for CMOR-conform units.

    Arguments:
        ds (:class:`xarray.Dataset`): Input dataset

    Returns:
        :class:`pandas.DataFrame`: Dataframe containing checks and issues
    """

    import pandas as pd
    import pyku.drs as drs
    import pyku.meta as meta

    # Get geodata varnames in dataset
    # -------------------------------

    varnames = meta.get_geodata_varnames(ds)

    # Gather issues in a list
    # -----------------------

    data = []

    # Loop over all geodata variables
    # -------------------------------

    for varname in varnames:

        the_check = "is_cmor_units"
        the_description = "Check if units is CMOR conform"

        cmor_varname = drs.get_cmor_varname(ds[varname])

        if cmor_varname is None:
            the_result = False
            the_issue = (
                "Could not get units attribute and hence could not check if "
                "units is CMOR-conform"
            )

        elif ds[varname].attrs.get('units') is None:
            the_result = False
            the_issue = "Variable has no attribute units"

        else:
            expected_units = drs_data.get('variables').get(cmor_varname)\
                                     .get('cmor_units')
            read_units = ds[varname].attrs.get('units')

            the_result = \
                True if read_units in [expected_units] else False

            the_issue = None if read_units in [expected_units] \
                else f"{varname} unit is {read_units} but the expected units \
is {expected_units}"

        data.append((the_check, the_result, the_issue, the_description))

    issues = pd.DataFrame(
        data=data,
        columns=['key', 'value', 'issue', 'description']
    )

    return issues


def check_variables_cmor_metadata(ds):

    """
    Check variable CMOR metadata ('standard_name', 'long_name' and 'units')

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`pandas.DataFrame`: The checks and issues.

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('air_temperature')
              ...: ds.pyku.check_variables_cmor_metadata()
    """

    import pandas as pd

    issues = []
    issues.append(_check_variables_cmor_standard_name(ds))
    issues.append(_check_variables_cmor_long_name(ds))
    issues.append(_check_variables_cmor_units(ds))

    issues = pd.concat(issues, ignore_index=True)

    return issues


def check_frequency(ds):

    """
    Check frequency from time labels and time bounds. If the period between
    consecutive data is not homogenous, an issue is raised.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`pandas.DataFrame`: The checks and issues.

    Examples:

        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.check_frequency()
    """

    # The functions does the following:
    # * Try to infer the frequency from the time labels
    # * Try to infer the frequency with pyku, which handles edge cases.

    import pandas as pd
    import xarray as xr
    import pyku.meta as meta

    # All issues are gathered in the list of issues
    # ---------------------------------------------

    list_of_issues = []

    # Check if frequency can be read from time labels
    # -----------------------------------------------

    try:
        data_frequency = xr.infer_freq(ds.time)
    except Exception:
        data_frequency = None

    the_check = 'frequency_can_be_inferred_from_data'
    the_description = 'Tried to infer frequency from the time labels'
    the_result = False if data_frequency is None else True
    the_issue = 'Frequency cannot be read from time labels.' \
        if the_result is False else None

    list_of_issues.append((the_check, the_result, the_issue, the_description))

    # Check if frequency can be read with get_frequency function
    # ----------------------------------------------------------

    the_check = 'frequency_can_be_determined'
    the_description = (
        'Check if frequency can be determined from the time labels, or from'
        'global attributes, or from the time bounds'
    )

    try:

        data_frequency = meta.get_frequency(ds, dtype='freqstr')

        if data_frequency is None:
            the_result = False
            the_issue = "could not determine frequency"
        else:
            the_result = True
            the_issue = None

    except Exception:

        # The exception should not occur, hence this is a safety in case the
        # function get_frequency crashes due to an edge case.

        the_result = False
        the_issue = "could not determine frequency"

    # Append issues, create DataFrame and return
    # ------------------------------------------

    list_of_issues.append((the_check, the_result, the_issue, the_description))

    issues = pd.DataFrame(
        list_of_issues,
        columns=['key', 'value', 'issue', 'description']
    )

    return issues


def check_variables_role(ds):

    """
    Look for variables which role is not identified. Identified roles for
    variables are *coordinate reference system*, *spatial bounds*, *spatial
    vertices*, *geographic longitude*, *geographic latitude*, *projection
    coordinate x*, *projection coordinate y*, *georeferenced data*

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`pandas.DataFrame`: The checks and issues.

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.check_variables_role()
    """

    import textwrap
    import pandas as pd
    import pyku.meta as meta

    for var in ds.data_vars:

        # Check if crs information depends on time
        # ----------------------------------------

        if var in meta_data.get('coordinate_reference_system') + \
                  meta_data.get('spatial_bounds') + \
                  meta_data.get('spatial_vertices') + \
                  meta_data.get('geographic_longitude') + \
                  meta_data.get('geographic_latitude') + \
                  meta_data.get('projection_coordinate_x') + \
                  meta_data.get('projection_coordinate_y') \
           and 'time' in ds[var].dims:

            message = textwrap.dedent(
                f"""
                WARNING: Variable {var} depends on time.

                maybe the dataset should be opened with the following options
                in open_mfdataset:

                - data_vars='minimal'
                - coords='minimal'
                - compat='override'
                """
            )

            print(message)

    # Load identified variables
    # -------------------------

    geodata_vars = meta.get_geodata_varnames(ds)
    geographic_latlon = meta.get_geographic_latlon_varnames(ds)
    projection_yx = meta.get_projection_yx_varnames(ds)
    time_dependent_vars = meta.get_time_dependent_varnames(ds)
    time_bounds_var = meta.get_time_bounds_varname(ds)
    spatial_bounds_vars = meta.get_spatial_bounds_varnames(ds)
    spatial_vertices_vars = meta.get_spatial_vertices_varnames(ds)
    crs_var = meta.get_crs_varname(ds)
    unidentified_vars = meta.get_unidentified_varnames(ds)

    warning_unidentified = 'warning' if unidentified_vars in [None] else None

    data = [
        ('geodata_vars', geodata_vars, None),
        ('geographic_latlon', geographic_latlon, None),
        ('projection_yx', projection_yx, None),
        ('time_dependent_vars', time_dependent_vars, None),
        ('time_bounds_var', time_bounds_var, None),
        ('spatial_bounds_vars', spatial_bounds_vars, None),
        ('spatial_vertices_vars', spatial_vertices_vars, None),
        ('crs_var', crs_var, None),
        ('unidentified_vars', unidentified_vars, warning_unidentified)
    ]

    issues = pd.DataFrame(
        data,
        columns=['key', 'value', 'issue']
    )

    return issues


def check_drs(ds, standard=None):

    """
    Check metadata for Data Reference Syntax (DRS)

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
        standards (str): Standard, can be one of 'cordex', 'cordex_adjust',
            'obs4mips',  or 'cordex_adjust_interp'.

    Returns:
        :class:`pandas.DataFrame`: The checks and issues.

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.check_drs(standard='cordex')
    """

    import pandas as pd

    # Get available standards from file
    # ---------------------------------

    available_standards = list(drs_data.get('standards').keys())

    # Check the standard given as input of the function
    # -------------------------------------------------

    if standard not in available_standards:

        message = (
            f"DRS standard {standard} is not implemented. Available standards "
            f"are {available_standards} "
        )

        raise Exception(message)

    # Get all drs keys from the standard chosen
    # -----------------------------------------

    keys = drs_data.get('standards').get(standard).get('metadata')

    # Loop and check
    # --------------

    data = [
        (
            key,
            ds.attrs.get(key),
            None if ds.attrs.get(key) is not None
            else ds.attrs.get(key, 'missing value')
        )
        for key in keys
    ]

    issues = pd.DataFrame(data, columns=['key', 'value', 'issue'])

    return issues


def check_files_multi(
    list_of_files, standard='cordex', completeness_period=None
):

    """
    Check list of files (multiprocessed version). This function should not be
    used as the multiprocessing should run on each files, instead of loading
    many files at once and running them in parallel.

    Todo:
        * Check if functional outside of dask distributed
        * Write docstring

    Arguments:
        list_of_files (list): List of files to be checked

    Returns:
        :class:`pandas.DataFrame`: Issues
    """

    import dask
    import xarray as xr
    import pandas as pd
    from dask import delayed

    logger.warn('This function is deprecated')

    @delayed
    def check_one_file(file):

        with dask.config.set(**{'array.slicing.split_large_chunks': True}):

            # Open file
            # ---------

            ds = xr.open_dataset(file)

            # Check for issues
            # ----------------

            issues = check(
                ds,
                standard=standard,
                completeness_period=completeness_period
            )

            issues['filename'] = file

            # Close file and add to list of issues
            # ------------------------------------

            ds.close()

            return issues

    delayed_results = [check_one_file(file) for file in list_of_files]
    computed_results = dask.compute(*delayed_results)
    issues = pd.concat(computed_results, ignore_index=True)

    return issues


def check_files(
    list_of_files, standard=None, completeness_period=None, progress=False
):

    """

    .. warning::

       Do not use this function as this may be taken out in the near future.

    Check list of files.

    Arguments:
        list_of_files (list): List of files to be checked
        standard (str): Standard (e.g. 'cordex'), defaults to None. If 'None',
            the standard metadata are not checked.
        completeness_period (freqstr): The files will be checked for
            completeness within the defined period (e.g. '1MS').

    Returns:
        :class:`pandas.DataFrame`: Issues
    """

    import dask
    import xarray as xr
    import pandas as pd
    from tqdm import tqdm

    logger.warning('This function is deprecated')

    def check_one_file(file):

        with dask.config.set(**{'array.slicing.split_large_chunks': True}):

            # Open file
            # ---------

            ds = xr.open_dataset(file)

            # Check for issues
            # ----------------

            issues = check(
                ds,
                standard=standard,
                completeness_period=completeness_period
            )

            issues['filename'] = file

            # Close file and add to list of issues
            # ------------------------------------

            ds.close()

            return issues

    # Set progress bar
    # ----------------

    if progress is True:
        iterator = tqdm(list_of_files)
    else:
        iterator = list_of_files

    # Compute checks for each file
    # ----------------------------

    computed_results = [check_one_file(file) for file in iterator]

    # Concatenate issues
    # ------------------

    issues = pd.concat(computed_results, ignore_index=True)

    return issues


def compare_datasets(ds1, ds2):

    """
    Check the compatibility of two climate datasets:

    * Compare geographic alignment
    * Compare datasets datetimes
    * Compare datasets dimensions
    * Compare datasets coordinates

    Arguments:
        ds1 (:class:`xarray.Dataset`): The first dataset.
        ds2 (:class:`xarray.Dataset`): The second dataset.

    Returns:
        :class:`pandas.DataFrame`: The checks and issues.

    Example:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...:
              ...: ds1 = pyku.resources.get_test_data('model_data')
              ...: ds2 = pyku.resources.get_test_data('hyras')
              ...:
              ...: ds1.pyku.compare_datasets(ds2)
    """

    import pandas as pd

    issues = []

    issues.append(compare_geographic_alignment(ds1, ds2))
    issues.append(compare_datetimes(ds1, ds2))
    issues.append(compare_dimensions(ds1, ds2))
    issues.append(compare_coordinates(ds1, ds2))

    issues = pd.concat(issues, ignore_index=True)

    return issues


def compare_datetimes(ds1, ds2):

    """
    Check if datetimes are the same in both datasets

    Arguments:
        ds1 (:class:`xarray.Dataset`): The first dataset.
        ds2 (:class:`xarray.Dataset`): The second dataset.

    Returns:
        :class:`pandas.DataFrame`: The checks and issues.

    Example:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...:
              ...: ds1 = pyku.resources.get_test_data('model_data')
              ...: ds2 = pyku.resources.get_test_data('hyras')
              ...:
              ...: ds1.pyku.compare_datetimes(ds2)
    """

    import warnings
    import pandas as pd
    import numpy as np

    # Gather issues in a list
    # -----------------------

    list_of_issues = []

    # Check if time is a dimension in first dataset
    # ---------------------------------------------

    the_check = "first_dataset_has_time_dimension"
    the_result = 'time' in list(ds1.sizes.keys())
    the_issue = "First dataset has no time dimension" \
        if the_result is False else None
    list_of_issues.append((the_check, the_result, the_issue))

    # Check if time is a dimension in second dataset
    # ---------------------------------------------

    the_check = "second_dataset_has_time_dimension"
    the_result = 'time' in list(ds2.sizes.keys())
    the_issue = "Second dataset has no time dimension" \
        if the_result is False else None
    list_of_issues.append((the_check, the_result, the_issue))

    # Return if either dataset has no time dimension
    # ----------------------------------------------

    if 'time' not in list(ds1.sizes.keys()) or \
       'time' not in list(ds2.sizes.keys()):

        issues = pd.DataFrame(
            data=list_of_issues, columns=['key', 'value', 'issue']
        )

        return issues

    # Get datetimes in first and second dataset
    # -----------------------------------------

    ds1_datetimes = ds1['time'].values
    ds2_datetimes = ds2['time'].values

    # Check datatypes of the first dataset
    # ------------------------------------

    the_check = "first_dataset_datetimes_are_numpy_datetime64"
    the_result = isinstance(ds1_datetimes[0], np.datetime64)
    the_issue = "First dataset datetimes are not numpy.datetime64" \
        if the_result is False else None
    list_of_issues.append((the_check, the_result, the_issue))

    # Check datatypes of the second dataset
    # -------------------------------------

    the_check = "second_dataset_datetimes_are_numpy_datetime64"
    the_result = isinstance(ds1_datetimes[0], np.datetime64)
    the_issue = "Second dataset datetimes are not numpy.datetime64" \
        if the_result is False else None
    list_of_issues.append((the_check, the_result, the_issue))

    # Return if either dataset has time datatype which is not numpy.datetime64
    # ------------------------------------------------------------------------

    if not isinstance(ds1_datetimes[0], np.datetime64) or \
       not isinstance(ds2_datetimes[0], np.datetime64):

        warnings.warn("Only np.datetime64 is fully supported.")

        issues = pd.DataFrame(
            data=list_of_issues,
            columns=['key', 'value', 'issue']
        )

        return issues

    # Check the difference in datetimes
    # ---------------------------------

    diff = list(set(ds1_datetimes) - set(ds2_datetimes))

    the_check = "same_datetimes_in_both_datasets"
    the_result = len(diff) == 0

    if the_result is False:
        the_issue = (
            "The first 2 timesteps in the first dataset are "
            f"{ds1_datetimes[0:2]}, and the first 2 timesteps in the second "
            "dataset are {ds2_datetimes[0:2]}. If no difference is seen in "
            "the first timesteps, you may have search for the differences "
            "manually."
        )
    else:
        the_issue = None

    list_of_issues.append((the_check, the_result, the_issue))

    # Check the between datetimes rounded to a second
    # -----------------------------------------------

    serie1 = pd.Series(ds1_datetimes).dt.round('s')
    serie2 = pd.Series(ds2_datetimes).dt.round('s')
    diff = list(set(serie1.values) - set(serie2.values))

    the_check = "same_rounded_datetimes_in_both_datasets"
    the_result = len(diff) == 0
    if the_result is False:
        the_issue = (
            "The first 2 timesteps in the first dataset are "
            f"{ds1_datetimes[0:2]}, and the first 2 timesteps in the second "
            f"dataset are {ds2_datetimes[0:2]}. If no difference is seen in "
            "the first timesteps, you may have search for the differences "
            "manually."
        )
    else:
        the_issue = None

    list_of_issues.append((the_check, the_result, the_issue))

    # Build dataframe of issues and return
    # ------------------------------------

    issues = pd.DataFrame(
        data=list_of_issues, columns=['key', 'value', 'issue']
    )

    return issues


def compare_dimensions(ds1, ds2):

    """
    Check if dimensions are the same in both datasets

    Arguments:
        ds1 (:class:`xarray.Dataset`): The first dataset.
        ds2 (:class:`xarray.Dataset`): The second dataset.

    Returns:
        :class:`pandas.DataFrame`: The checks and issues.

    Example:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...:
              ...: ds1 = pyku.resources.get_test_data('model_data')
              ...: ds2 = pyku.resources.get_test_data('hyras')
              ...:
              ...: ds1.pyku.compare_dimensions(ds2)
    """

    import pandas as pd

    # We gather issues in a list
    # --------------------------

    list_of_issues = []

    # Check if time is a dimension
    # ----------------------------

    set1 = set(sorted(list(ds1.sizes.keys())))
    set2 = set(sorted(list(ds2.sizes.keys())))
    diff = set1.symmetric_difference(set2)

    the_check = 'dimensions_names_equal'
    the_issue = (
        f"Not equal, ds1: {list(ds1.sizes.keys())}, ds2: "
        f"{list(ds1.sizes.keys())}"
    )

    if not diff:
        list_of_issues.append((the_check, False, the_issue))
    else:
        list_of_issues.append((the_check, True, None))

    # Build dataframe of issues and return
    # ------------------------------------

    issues = pd.DataFrame(
        data=list_of_issues,
        columns=['key', 'value', 'issue']
    )

    return issues


def compare_coordinates(ds1, ds2):

    """
    Check if coordinates are the same in both datasets.

    Arguments:
        ds1 (:class:`xarray.Dataset`): The first dataset.
        ds2 (:class:`xarray.Dataset`): The second dataset.

    Returns:
        :class:`pandas.DataFrame`: The checks and issues.

    Example:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...:
              ...: ds1 = pyku.resources.get_test_data('model_data')
              ...: ds2 = pyku.resources.get_test_data('hyras')
              ...:
              ...: ds1.pyku.compare_coordinates(ds2)
    """

    import pandas as pd

    # We gather issues in a list
    # --------------------------

    list_of_issues = []

    # Check if time is a dimension
    # ----------------------------

    set1 = set(dict(ds1.coords).keys())
    set2 = set(dict(ds2.coords).keys())
    diff = set1.symmetric_difference(set2)

    the_check = "coordinate_names_are_the_same"
    the_result = not diff
    the_issue = f"Different keys {diff}" if the_result is False else None
    list_of_issues.append((the_check, the_result, the_issue))

    # Build dataframe of issues and return
    # ------------------------------------

    issues = pd.DataFrame(
        data=list_of_issues, columns=['key', 'value', 'issue']
    )

    return issues


def compare_geographic_alignment(ds1, ds2, tolerance=None):

    """
    Check the alignment of georeferencing of two datasets

    Arguments:

        ds1 (:class:`xarray.Dataset`): The first dataset.
        ds2 (:class:`xarray.Dataset`): The second dataset.

        tolerance (float): Defaults to 0.001. Tolerance with respect to
            alignment. If the difference of any values from the geographic
            coordinates or projection coordinates does not fall within the
            tolerance, the function reports the difference.

    Returns:
        :class:`pandas.DataFrame`: The checks and issues.

    Example:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...:
              ...: ds1 = pyku.resources.get_test_data('model_data')
              ...: ds2 = pyku.resources.get_test_data('hyras')
              ...:
              ...: ds1.pyku.compare_geographic_alignment(ds2)
    """

    import pandas as pd
    import pyku.meta as meta
    import pyku.geo as geo
    import xarray as xr

    # Sanity checks
    # -------------

    assert isinstance(ds1, xr.Dataset), "first entry must be a xarray Dataset"
    assert isinstance(ds2, xr.Dataset), "second entry must be a xarray Dataset"

    # We gather issues in a list
    # --------------------------

    list_of_issues = []

    # Get projection and geographic coordinate names
    # ----------------------------------------------

    y_name_1, x_name_1 = meta.get_projection_yx_varnames(ds1)
    y_name_2, x_name_2 = meta.get_projection_yx_varnames(ds2)

    lat_name_1, lon_name_1 = meta.get_geographic_latlon_varnames(ds1)
    lat_name_2, lon_name_2 = meta.get_geographic_latlon_varnames(ds2)

    # Sanity checks
    # -------------

    assert y_name_1 is not None, 'No y projection coordinate in dataset 1'
    assert x_name_1 is not None, 'No x projection coordinate in dataset 1'
    assert lat_name_1 is not None, 'No geographic lat coordinate in dataset 1'
    assert lon_name_1 is not None, 'No geographic lon coordinate in dataset 1'

    assert y_name_2 is not None, 'No y projection coordinate in dataset 2'
    assert x_name_2 is not None, 'No x projection coordinate in dataset 2'
    assert lat_name_2 is not None, 'No geographic lat coordinate in dataset 2'
    assert lon_name_2 is not None, 'No geographic lon coordinate in dataset 2'

    if lat_name_1 is not None and lat_name_2 is not None and \
       lon_name_1 is not None and lon_name_2 is not None:

        lons_1, lats_1 = geo.get_lonlats(ds1, dtype='ndarray')
        lons_2, lats_2 = geo.get_lonlats(ds2, dtype='ndarray')

    # Check number of x and y projection coordinates
    # ----------------------------------------------

    have_same_number_of_pixels_in_y_and_x_directions = (
        geo.get_ny(ds1) == geo.get_ny(ds2)
        and geo.get_nx(ds1) == geo.get_nx(ds2)
    )

    the_check = 'have_same_number_of_pixels_in_y_and_x_directions'
    the_description = (
        'Check if number of pixels is the same in the y and x direction')
    the_result = have_same_number_of_pixels_in_y_and_x_directions
    the_issue = None if the_result else (
        "Datasets do not have the same number of pixels in either the y or x"
        "direction"
    )

    # Return immedately as further tests will not make sense
    # ------------------------------------------------------

    if not have_same_number_of_pixels_in_y_and_x_directions:
        return pd.DataFrame(
            data=[(the_check, the_result, the_issue, the_description)],
            columns=['key', 'value', 'issue', 'description']
        )
    else:
        list_of_issues.append(
            (the_check, the_result, the_issue, the_description))

    # Check if datasets georeferencing can be aligned
    # -----------------------------------------------

    # The strategy is to run the align_georeferencing function and use the
    # exceptions built in the function for the check.

    the_check = 'datasets_georeferencing_can_be_aligned'
    the_description = (
        'Check if datasets georeferencing can be aligned. It is checked '
        'if projection y/x coordiantes and lat/lon fall withing tolerance'
    )

    try:
        geo.align_georeferencing(ds1, ds2, tolerance=tolerance)
        the_result = True
        the_issue = None

    except Exception as e:
        the_result = False
        the_issue = f"{e}"

    list_of_issues.append(
        (the_check, the_result, the_issue, the_description)
    )

    issues = pd.DataFrame(
        data=list_of_issues,
        columns=['key', 'value', 'issue', 'description']
    )

    return issues


def compare_attrs(ds1, ds2, var=None):

    """
    Compare global or variable attrs

    Arguments:

        ds1 (:class:`xarray.Dataset`): The first input dataset.
        ds2 (:class:`xarray.Dataset`): The second input dataset.

        var (str): Variable name. Defaults to None. If variable is None, the
            global attributes are compared, otherwise the variable attributes
            are analyzed.

    Returns:
        :class:`pandas.DataFrame`: The checks and issues.

    Example:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...:
              ...: ds1 = pyku.resources.get_test_data('model_data')
              ...: ds2 = pyku.resources.get_test_data('hyras')
              ...:
              ...: ds1.pyku.compare_attrs(ds2)
    """

    import pandas as pd

    list_of_differences = []

    # Check inputs
    # ------------

    if var is not None and var not in ds1.data_vars:
        message = f"Variable {var} not in first dataset"
        raise Exception(message)

    if var is not None and var not in ds2.data_vars:
        message = f"Variable {var} not in seconds dataset"
        raise Exception(message)

    # Function to determine the depth of the dictionary
    # -------------------------------------------------

    def depth(d):
        if isinstance(d, dict):
            return 1 + (max(map(depth, d.values())) if d else 0)
        return 0

    # Get global or variable attributes
    # ---------------------------------

    if var is None:
        attrs1 = ds1.attrs
        attrs2 = ds2.attrs

    else:
        attrs1 = ds1[var].attrs
        attrs2 = ds2[var].attrs

    # Calculate the difference in keys
    # --------------------------------

    for key in list(attrs1.keys()) + list(attrs2.keys()):
        if key not in attrs1.keys() or key not in attrs2.keys():

            list_of_differences.append((
                f"attrs['{key}']",
                f"{ds1.attrs.get(key)}",
                f"{ds2.attrs.get(key)}",
            ))

    # Differences in common keys
    # --------------------------

    set1 = set(attrs1.keys())
    set2 = set(attrs2.keys())

    differences = list(set1 - set2)

    for difference in differences:
        key = difference[0]

        if key in attrs1.keys() and key in attrs2.keys():

            list_of_differences.append((
                f"attrs['{key}']",
                f"{ds1.attrs.get(key)}",
                f"{ds2.attrs.get(key)}",
            ))

    differences = pd.DataFrame(
        data=list_of_differences,
        columns=[
            'differences',
            f"{ds1.attrs.get('label', 'dataset 1')}",
            f"{ds2.attrs.get('label', 'dataset 2')}",
        ]
    )

    return differences
