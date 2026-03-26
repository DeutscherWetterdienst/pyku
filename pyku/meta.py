#!/usr/bin/env python3

"""
The :class:`pyku.meta` module provides functions for working with metadata in
:class:`xarray.Dataset`, particularly in the context of climate and geospatial
data. These functions assist in managing coordinate variables, spatial
information, and temporal metadata, while ensuring compatibility with common
conventions and formats.

**Metadata retrieval**

Functions such as :func:`pyku.meta.get_geographic_latlon_varnames`,
:func:`pyku.meta.get_crs_varname`, :func:`pyku.meta.get_geodata_varnames`, and
:func:`pyku.meta.get_spatial_varnames` enable retrieval of specific standard
climate variable names from :class:`xarray.Dataset`.

**Spatial metadata**

Determine if datasets are georeferenced (:func:`pyku.meta.is_georeferenced`) or
have projection coordinates (:func:`pyku.meta.has_projection_coordinates`).

**Temporal Metadata**:

:func:`pyku.meta.get_frequency` is a specialized function for detecting
temporal frequency with support for bounds checks and multiple output formats
(`freqstr`, `DateOffset`). Functions like
:func:`pyku.meta.get_time_bounds`, and :func:`pyku.meta.has_time_bounds`
provide tools to inspect, validate, and manage spatial and temporal
information.

**Example Usage**

Below are examples of typical usage:

.. code-block:: python

   import pyku

   # Retrieve a test dataset
   # -----------------------

   ds = pyku.resources.get_test_data('hyras')

   # Find variable names of georeferenced data in dataset
   # ----------------------------------------------------

   ds.pyku.get_geodata_varnames()

   # Get dataset frequency
   # ---------------------

   ds.pyku.get_frequency(dtype='freqstr')

   # Check if the dataset is georeferenced
   # -------------------------------------

   ds.pyku.is_georeferenced()

For more detailed information on each function, refer to their respective
docstrings.
"""

from . import meta_dict
from . import logger


def find_match(searched_words, words, excluded_words=None):
    """
    Finds the best match for a target set of names from available coordinates.

    Arguments:
        target_names (list): List of potential names to match, e.g., ['lat',
            'lats', 'latitude'].
        available_coords (list): List of available coordinate names, e.g., [
            'time', 'lat_3', 'lon_3', 'x', 'y'].
        exclude (list): Optional. List of names to exclude from matching,
            e.g., ['rlat', 'lat_bnds'].

    Returns:
        str: The best matching coordinate name.

    Example:

        For example, if we are looking for latitude, which could be represented
        by names such as ['lat', 'lats', 'latitude'], we want to identify the
        best match from a set of available coordinates like ['time', 'lat_3',
        'lon_3', 'x', 'y'].

        To refine the search, certain words should be excluded to prevent them
        from being returned as matches. For instance, when searching for
        geographic latitude, terms like rlat or lat_bnds should not be
        considered valid matches.

        .. ipython::

           In [0]: import pyku.meta as meta
              ...: meta.find_match(
              ...:    searched_words=['lat', 'lats', 'latitude'],
              ...:    words=['time', 'lat_3', 'lon_3', 'y_3', 'x_3'],
              ...:    excluded_words=['rlat', 'clats']
              ...: )
    """

    from rapidfuzz import process

    # Edge case
    # ---------

    # In some cases, a word may appear in both the included and excluded word
    # lists. To handle this, the word is first removed from the excluded words.
    # For example, "lat" and "lon" could represent either geographic or
    # projection coordinates. If we want to exclude all projection coordinates
    # from the search, "lat" and "lon" must be removed from the list of
    # excluded words.

    excluded_words = list(set(excluded_words) - set(words))

    # Edge case where words is an empty dictionay
    # -------------------------------------------

    # It is legimate for a data variable to have neither dimensions nor
    # coordinates as for example the crs variable. In that case, we can call
    # the function with words=[] and the function should return None.

    if len(words) == 0:
        return None

    # Look for exact matches
    # ----------------------

    exact_words = list(set(searched_words) & set(words))

    # Return if one exact word was found
    # ----------------------------------

    if len(exact_words) == 1:
        return exact_words[0]

    # Give a warning in case more than one exact word was found
    # ---------------------------------------------------------

    if len(exact_words) > 1:

        message = (
            f"Multiple possibilities found when looking for {searched_words}: "
            f"Found {exact_words}. Using {exact_words[0]} "
        )

        logger.warn(message)

        return exact_words[0]

    # Look for the best match in excluded words
    # -----------------------------------------

    # The score of the best match shall be higher than the best match from the
    # excluded words. In essence, if we are looking for geographic latitude, we
    # need to make sure that the score is higher than for rotated latitude,
    # which is called rlat.

    minimal_score = 0

    if excluded_words is not None:

        # Dictionary to store the best matches
        # ------------------------------------

        best_matches = {}

        # Loop through words in words and find best match from searched_words
        # -------------------------------------------------------------------

        for word in excluded_words:
            match, score, _ = process.extractOne(word, words)
            best_matches[word] = (match, score)

        # Find the entry with the highest score
        # -------------------------------------

        best_match = max(best_matches.items(), key=lambda item: item[1][1])

        # Extract the key, matched word, and score
        # ----------------------------------------

        word, (matched_word, score) = best_match

        minimal_score = score

    # Dictionary to store the best matches
    # ------------------------------------

    best_matches = {}

    # Loop through words in words and find best match from searched_words
    # -------------------------------------------------------------------

    for word in searched_words:
        match, score, _ = process.extractOne(word, words)
        best_matches[word] = (match, score)

    # Find the entry with the highest score
    # -------------------------------------

    best_match = max(best_matches.items(), key=lambda item: item[1][1])

    # Extract the key, matched word, and score
    # ----------------------------------------

    word, (matched_word, score) = best_match

    # Send warnings when needed
    # -------------------------

    if score < minimal_score:
        return None

    elif score < 50:
        return None

    return matched_word


def filter_incomplete_datetimes(*args, **kwargs):
    """
    This function has moved to :func:`pyku.timekit.filter_incomplete_datetimes`
    """

    import warnings
    import pyku.timekit as timekit

    warnings.warn(
        "This function has moved to pyku.timekit.filter_incomplete_datetimes"
        "and will be removed soon",
        FutureWarning,
    )

    return timekit.filter_incomplete_datetimes(*args, **kwargs)


def get_pyku_metadata():
    """
    Get pyku metadata

    Returns:
        dict: dictionary of pyku metadata
    """

    return meta_dict


def get_dataset_size(ds):
    """
    Get dataset size in GB

    Arguments:
        ds (:class:`xarray.Dataset`): The in put dataset

    Returns:
        str: Dataset size
    """

    return f"{ds.nbytes/(1024 ** 3):.3f} GB"


def _reorder_dimensions(ds):
    """
    Reorders dataset dimensions to ensure:
    - 'time' comes first (if it exists)
    - projection y/x coordinates come last (if they exist)
    - All other dimensions maintain their relative order between them.

    Arguments:
        :class:`xarray.Dataset`: The input dataset.

    Returns
        :class:`xarray.Dataset`: Dataset with reordered dimensions.
    """

    source_ds = ds.copy()

    dims = list(source_ds.dims)

    y_name, x_name = get_projection_yx_varnames(source_ds)

    if "time" in dims:
        time_dim = [d for d in dims if d == "time"]
    else:
        time_dim = []

    if y_name is not None and x_name is not None:
        yx_dims = [d for d in dims if d in {y_name, x_name}]
    else:
        yx_dims = []

    other_dims = [d for d in dims if d not in time_dim + yx_dims]

    new_order = time_dim + other_dims + yx_dims

    return source_ds.transpose(*new_order)


def _reorder_coordinates(ds):
    """
    Reorders dataset coordinates to ensure:
    - 'time' comes first (if it exists)
    - 'lat' and 'lon' come last (if they exist)
    - All other coordinates maintain their relative order between them.

    Arguments:
        :class:`xarray.Dataset`: The input dataset.

    Returns
        :class:`xarray.Dataset`: Dataset with reordered dimensions.
    """

    source_ds = ds.copy()

    coords = list(source_ds.coords)

    y_name, x_name = get_projection_yx_varnames(source_ds)

    time_coord = []

    if "time" in coords:
        time_coord = [c for c in coords if c == "time"]
    if y_name is not None and x_name is not None:
        yx_coords = [c for c in coords if c in {y_name, x_name}]
    else:
        yx_coords = []

    other_coords = [c for c in coords if c not in time_coord + yx_coords]

    # Construct new coordinate order
    # ------------------------------

    new_order = time_coord + other_coords + yx_coords

    # Reassign coordinates in the new order
    # -------------------------------------

    new_coords = {c: source_ds[c] for c in new_order}

    return source_ds.assign_coords(**new_coords)


def has_ordered_dimensions_and_coordinates(ds):
    """
    Checks whether the dimensions and coordinates of the dataset are ordered
    according to Pyku's recommendations:

    - 'time' appears first (if it exists)
    - 'lat' and 'lon' are positioned last (if they exist)
    - All other coordinates retain their relative order

    While Pyku can handle any order of dimensions and coordinates, following
    this recommended structure ensures a more standardized data layout,
    reducing the likelihood of encountering edge cases.

    Arguments:
        dataset (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`bool`: Whether the dataset ordering of dimensions and
        coordinates corresponds pyku's recommendations.
    """

    in_ds = ds.copy()

    reordered_ds = reorder_dimensions_and_coordinates(in_ds)
    source_dims = list(in_ds.sizes.keys())
    source_coords = list(in_ds.coords)
    ordered_dims = list(reordered_ds.sizes.keys())
    ordered_coords = list(reordered_ds.coords)

    if source_dims == ordered_dims and source_coords == ordered_coords:
        return True
    else:
        return False


def reorder_dimensions_and_coordinates(ds):
    """
    Reorders dataset dimensions and coordinates to ensure:
    - 'time' comes first (if it exists)
    - 'lat' and 'lon' come last (if they exist)
    - All other coordinates maintain their relative order between them.

    While Pyku can handle any order of dimensions and coordinates, following
    this recommended structure ensures a more standardized data layout,
    reducing the likelihood of encountering edge cases.

    Arguments:
        :class:`xarray.Dataset`: The input dataset.

    Returns
        :class:`xarray.Dataset`: Dataset with reordered dimensions and
        coordinates.

    Examples:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('fake_cmip6_data')
              ...:
              ...: # Shuffle dimensions and coordinates
              ...: # ----------------------------------
              ...:
              ...: ds = ds.transpose('lon', 'lat', 'time')
              ...: ds = ds.assign_coords({
              ...:     'lon': ds.lon, 'lat': ds.lat, 'time': ds.time
              ...: })
              ...:
              ...: # Apply pyku default dimensions and coordinates ordering
              ...: # ------------------------------------------------------
              ...:
              ...: ds.pyku.reorder_dimensions_and_coordinates()
    """

    source_ds = ds.copy()

    # The order of the operation is important.
    source_ds = _reorder_dimensions(source_ds)
    source_ds = _reorder_coordinates(source_ds)

    return source_ds


def get_unidentified_varnames(ds):
    """
    Get name of unidentified variables

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        List[str]: The names of unidentified variables.

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.get_unidentified_varnames()
    """

    geodata_variables = get_geodata_varnames(ds)
    geographic_latlon = get_geographic_latlon_varnames(ds)
    projection_yx = get_projection_yx_varnames(ds)
    time_bounds_variable = get_time_bounds_varname(ds)
    crs_variable = get_crs_varname(ds)
    spatial_bounds_variables = get_spatial_bounds_varnames(ds)
    spatial_vertices_variables = get_spatial_vertices_varnames(ds)

    unidentified_varnames = [
        var
        for var in ds.data_vars
        if var not in geodata_variables
        and var not in geographic_latlon
        and var not in projection_yx
        and var not in [time_bounds_variable]
        and var not in [crs_variable]
        and var not in spatial_bounds_variables
        and var not in spatial_vertices_variables
    ]

    return unidentified_varnames


def get_spatial_vertices_varnames(ds):
    """
    Get name of spatial vertices variables

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset

    Returns:
        list: The names of the time bounds

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.get_spatial_vertices_varnames()
    """

    # Find the name of the temporal bounds in file
    # --------------------------------------------

    spatial_vertices_varnames = list(
        set(meta_dict.get("spatial_vertices")) & set(ds.data_vars)
    )

    return spatial_vertices_varnames


def get_spatial_bounds_varnames(ds):
    """
    Get name of spatial bounds variable

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        list: Names of the time bounds

    Example:

        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.get_spatial_bounds_varnames()
    """

    # Find the name of the temporal bounds in file
    # --------------------------------------------

    spatial_bnds_varnames = list(
        set(meta_dict.get("spatial_bounds")) & set(ds.data_vars)
    )

    return spatial_bnds_varnames


def get_latlon_bounds_varnames(ds):
    """
    Get name of geographic lat/lon bounds variable name

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        list: Names of the geographic bounds varname

    Example:

        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.get_latlon_bounds_varnames()
    """

    possible_lat_bounds_varnames = list(
        set(meta_dict.get("latitude_bounds")) & set(ds.data_vars)
    )

    possible_lon_bounds_varnames = list(
        set(meta_dict.get("longitude_bounds")) & set(ds.data_vars)
    )

    if len(possible_lat_bounds_varnames) == 0:
        lat_bounds_varname = None
    elif len(possible_lat_bounds_varnames) == 1:
        lat_bounds_varname = possible_lat_bounds_varnames[0]
    elif len(possible_lat_bounds_varnames) > 1:
        raise Exception(
            f"Found more than one possible name for latitude bounds "
            f"{possible_lat_bounds_varnames}"
        )
    else:
        raise Exception("Impossible!")

    if len(possible_lon_bounds_varnames) == 0:
        lon_bounds_varname = None
    elif len(possible_lon_bounds_varnames) == 1:
        lon_bounds_varname = possible_lon_bounds_varnames[0]
    elif len(possible_lon_bounds_varnames) > 1:
        raise Exception(
            f"Found more than one possible name for longitude bounds "
            f"{possible_lon_bounds_varnames}"
        )
    else:
        raise Exception("Impossible!")

    return lat_bounds_varname, lon_bounds_varname


def get_spatial_varnames(ds):
    """
    Get name of spatial variables:

    - ``spatial_vertices_varnames``
    - ``spatial_bounds_varnames``
    - ``geographic_latlon_varnames``
    - ``projection_yx_varnames``
    - ``crs_varname``

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset

    Returns:
        list: Names of the time bounds

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.get_spatial_varnames()
    """

    import textwrap
    import xarray as xr

    if isinstance(ds, xr.Dataset):

        spatial_varnames = (
            list(get_spatial_vertices_varnames(ds))
            + list(get_spatial_bounds_varnames(ds))
            + list(get_geographic_latlon_varnames(ds))
            + list(get_projection_yx_varnames(ds))
        )

        if get_crs_varname(ds) is not None:
            spatial_varnames.append(get_crs_varname(ds))

    elif isinstance(ds, xr.DataArray):
        spatial_varnames = list(get_geographic_latlon_varnames(ds)) + list(
            get_projection_yx_varnames(ds)
        )

    else:
        message = textwrap.dedent(
            f"""
            ds shall be a xarray.Dataset or xarray.DataArray, not {type(ds)}
            """
        )
        raise Exception(message)

    return spatial_varnames


def get_crs_varname(ds):
    """
    Get name of the crs variable

    Arguments:
        ds (:class:`xarray.Dataset`): The input Dataset.

    Returns:
        str: Name of the crs variable.

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.get_crs_varname()
    """

    # Find the name of the temporal bounds in file
    # --------------------------------------------

    crs_varnames = list(
        set(meta_dict.get("coordinate_reference_system")) & set(ds.data_vars)
    )

    if len(crs_varnames) > 1:

        logger.warning(f"Found more than one crs in dataset {crs_varnames}")

    if len(crs_varnames) == 0:
        return None

    crs_varname = crs_varnames[0]

    return crs_varname


def has_time_bounds(ds):
    """
    Check if dataset has time bounds

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset

    Returns:
        bool: True if dataset has time bounds, False otherwise.

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.has_time_bounds()
    """

    time_bounds_varname = get_time_bounds_varname(ds)

    if time_bounds_varname is None:
        return False
    else:
        return True


def get_time_bounds_varname(ds):
    """
    Get name of time bounds variable

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        str: Name of the time bounds.

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.get_time_bounds_varname()
    """

    # Find the name of the temporal bounds in file
    # --------------------------------------------

    time_bnds_varnames = list(
        set(meta_dict.get("temporal_bounds")) & set(ds.data_vars)
    )

    # Raise a warning if multiple values are found
    # --------------------------------------------

    if len(time_bnds_varnames) > 1:
        logger.warning("Found more than one temporal bounds in dataset")

    # Retrun None if no value were found
    # ----------------------------------

    if len(time_bnds_varnames) == 0:
        return None

    # Return name of temporal bounds
    # ------------------------------

    time_bnds_varname = time_bnds_varnames[0]

    return time_bnds_varname


def get_time_dependent_varnames(ds):
    """
    Get time dependent variables

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        list(str): List of variables depending on time

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.get_time_dependent_varnames()
    """

    return [var for var in ds.data_vars if "time" in ds[var].dims]


def get_time_bounds(ds, which=None):
    """
    Get time bounds from dataset

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
        which (str): Either ``None``, ``lower``, or ``upper``. Default is None.

    Returns:
        :class:`numpy.ndarray`: Array of time bounds.

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.get_time_bounds()[0:5]
    """

    import numpy as np
    import warnings

    # Find the name of the temporal bounds in file
    # --------------------------------------------

    time_bnds_names = list(
        set(meta_dict.get("temporal_bounds")) & set(ds.data_vars)
    )

    if len(time_bnds_names) > 1:
        warnings.warn("Found more than one temporal bounds in dataset")

    if len(time_bnds_names) == 0:
        return None

    if which not in [None, "lower", "upper"]:
        raise Exception("which shall be None, lower or upper")

    time_bnds_name = time_bnds_names[0]

    # Extract time bounds to a numpy array
    # ------------------------------------

    time_bnds = ds[time_bnds_name].values

    # Edge case where there is only one time step
    # -------------------------------------------

    # In that case, we get an array with two values [min, max], instead of
    # and array of mins and maxs [[min1, max1], [min2, max2],...]

    if time_bnds.size == 2:

        if which in ["lower"]:
            return min(time_bnds)
        elif which in ["upper"]:
            return max(time_bnds)
        elif which is None:
            return time_bnds

    # Return time bounds
    # ------------------

    if which in ["lower"]:
        return np.array([min(bounds) for bounds in time_bnds])
    elif which in ["upper"]:
        return np.array([max(bounds) for bounds in time_bnds])
    elif which is None:
        return time_bnds
    else:
        raise Exception("Could not get the temporal bounds")


def get_time_intervals(ds):
    """
    Get time intervals between consecutive datapoints.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`xarray.Dataset`: Dataset with time intervals

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.get_time_intervals().interval.values[0:5]
    """

    import xarray as xr
    import pandas as pd

    # Determine periods from the time boundaries
    # ------------------------------------------

    time_bnds = get_time_bounds(ds)

    # Determine the calendar type
    # ---------------------------

    # Some cftime calendars are commented out because I assume pandas Timestamp
    # handles them. These calendars likely use numpy.datetime64,
    # datetime.datetime, or pandas.Timestamp, and there is no data available
    # for testing or verification.

    is_cftime_calendar = ds.time.dt.calendar in [
        "360_day",
        "365_day",
        "366_day",
        "all_leap",
        "noleap",
        # 'standard',
        # 'gregorian',
        # 'proleptic_gregorian',
        # 'julian',
    ]

    if time_bnds is None:
        return None

    if time_bnds is not None:

        # Calculate arrays of time intervals
        # ----------------------------------

        # The prefered solution is to use pandas time objects. However the
        # function should stay compatible with the defaults datetime objects,
        # numpy.datetime64, as well as cftime

        if is_cftime_calendar:
            time_bnds_intervals = [
                (upper - lower).total_seconds() for lower, upper in time_bnds
            ]

        else:
            time_bnds_intervals = [
                (pd.Timestamp(upper) - pd.Timestamp(lower)).total_seconds()
                for lower, upper in time_bnds
            ]

    # Create DataArray
    # ----------------

    da = xr.DataArray(
        name="interval",
        data=time_bnds_intervals,
        dims="time",
        coords={"time": ds.time},
        attrs={"units": "seconds"},
    )

    # Merge with time bounds in a Dataset and return
    # ----------------------------------------------

    return xr.merge([da, ds.time_bnds])


def _get_freqstr_from_cmor_attrs(ds):
    """
    Get frequency string from CMOR attributes.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        Pandas DateOffset Frequency String: frequency

    References:
        https://pandas.pydata.org/docs/user_guide/timeseries.html#dateoffset-objects

    """

    if "frequency" not in list(ds.attrs.keys()):
        return None

    attrs_freqstr = ds.attrs.get("frequency")

    if attrs_freqstr in ["1hr"]:
        freqstr = "h"
    elif attrs_freqstr in ["3hr"]:
        freqstr = "3h"
    elif attrs_freqstr in ["6hr"]:
        freqstr = "6h"
    elif attrs_freqstr in ["12hr"]:
        freqstr = "12h"
    elif attrs_freqstr in ["day"]:
        freqstr = "D"
    elif attrs_freqstr in ["mon"]:
        freqstr = "MS"
    elif attrs_freqstr in ["sem"]:
        freqstr = "QS-DEC"
    elif attrs_freqstr in ["year"]:
        freqstr = "YS"
    else:
        logger.warning(f"Frequency {attrs_freqstr} not a CMOR standard")
        freqstr = None

    return freqstr


def _get_freqstr_from_single_time_bound(ds):
    """
    Edge case for determining dataset frequency. If there is only one time
    stamp, but this time stamp as time bounds, infer the frequency from those
    time bounds. The assumption is that climate dataset have no gap between
    time bounds.
    """

    import pandas as pd
    import pyku.meta as meta
    import numpy as np
    from pandas.tseries.frequencies import to_offset

    # Intialize to None
    # -----------------

    freqstr_from_single_time_bound = None

    # Check if there is only one time label and available time bounds
    # ---------------------------------------------------------------

    if ds.time.size == 1 and meta.has_time_bounds(ds):

        time_bounds_varname = meta.get_time_bounds_varname(ds)

        # Squeeze to [[begin, end]] to [begin, end] if applicable
        time_bounds = np.squeeze(ds[time_bounds_varname].values)

        lower = pd.to_datetime(time_bounds[0])
        upper = pd.to_datetime(time_bounds[1])

        freqstr_from_single_time_bound = to_offset(upper - lower).freqstr

        logger.info(
            "Infering frequency from data with a single time step and time "
            "bounds"
        )

    return freqstr_from_single_time_bound


def _get_freqstr_from_two_time_bounds(ds):
    """
    Edge case for determining dataset frequency. If there is are only two time
    stamps, but these time stamps have time bounds, infer the frequency from
    those time bounds. The assumption is that climate dataset have no gap
    between time bounds.
    """

    import pandas as pd
    import pyku.meta as meta

    # Intialize to None
    # -----------------

    freqstr_from_two_time_bounds = None

    # Check if there is only two time labels with available time bounds
    # -----------------------------------------------------------------

    if ds.time.size == 2 and meta.has_time_bounds(ds):

        time_bounds_varname = meta.get_time_bounds_varname(ds)

        # Get lower and upper time bounds for the first time step
        # -------------------------------------------------------

        lower_1 = pd.to_datetime(ds[time_bounds_varname].values[0, 0])
        upper_1 = pd.to_datetime(ds[time_bounds_varname].values[0, 1])

        # Get lower and upper time bounds for the second time step
        # --------------------------------------------------------

        lower_2 = pd.to_datetime(ds[time_bounds_varname].values[1, 0])
        upper_2 = pd.to_datetime(ds[time_bounds_varname].values[1, 1])

        # Get the resolution strings
        # --------------------------

        freqstr_from_first_time_bound = (upper_1 - lower_1).resolution_string
        freqstr_from_second_time_bound = (upper_2 - lower_2).resolution_string

        # Compare and set
        # ---------------

        if freqstr_from_first_time_bound == freqstr_from_second_time_bound:
            freqstr_from_two_time_bounds = freqstr_from_first_time_bound
            logger.warning(
                "Guessing frequency from two time stamps with two time bounds"
           )

    return freqstr_from_two_time_bounds


def get_frequency(ds, dtype="freqstr"):
    """
    This function differs from the standard xarray function
    :func:`xarray.infer_freq` by additionally checking time bounds.

    Arguments:
        ds (:class:`xarray.Dataset`):
            The input dataset.

        dtype (str):
            Specifies the desired data type for frequency representation.
            Choose one of the following:

            - 'freqstr': Represents the frequency as a string. This is the
              recommended default.
            - 'DateOffset': Represents the frequency using pandas' DateOffset.
            - 'Timedelta': Represents the frequency using pandas' Timedelta.
    Returns:
        freqstr, :class:`pandas.tseries.offsets.DateOffset`, :class:`pandas.Timedelta`:
        The inferred frequency of the dataset.

    Examples:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...:
              ...: # Get the dataset
              ...: ds = pyku.resources.get_test_data('hyras')

           In [0]: # Get the frequency string
              ...: ds.pyku.get_frequency(dtype='freqstr')

           In [0]: # Get the frequency as DateOffset
              ...: ds.pyku.get_frequency(dtype='DateOffset')

           In [0]: # Get the frequency as DateOffset
              ...: ds.pyku.get_frequency(dtype='Timedelta')


        To create an offset that can be compared, use ``to_offset``,
        which converts a frequency string into an offset object. This ensures that
        the frequency of your data can be compared unambiguously.

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...: from pandas.tseries.frequencies import to_offset
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: myoffset = ds.pyku.get_frequency(dtype='DateOffset')
              ...: to_offset('1D') == myoffset
    """

    import pandas as pd
    from pandas.tseries.frequencies import to_offset

    import xarray as xr

    # Sanity checks
    # -------------

    if dtype not in ["freqstr", "DateOffset", "Timedelta"]:
        raise ValueError(
            f"Invalid dtype '{dtype}'. Expected one of: 'freqstr', "
            "'DateOffset', or 'Timedelta'."
        )

    if "time" not in dict(ds.coords).keys():
        raise KeyError("Time dimension needed to get frequency")

    if ds["time"].size == 0:
        raise ValueError("time dimension exist, but contains zero values")

    # Read frequency from CMOR attributes
    # -----------------------------------

    freqstr_from_cmor_attrs = _get_freqstr_from_cmor_attrs(ds)

    # Edge case with only one time step, but still with time bounds
    # -------------------------------------------------------------

    freqstr_from_single_time_bound = _get_freqstr_from_single_time_bound(ds)

    # Edge case with only two time step, but still with time bounds
    # -------------------------------------------------------------

    freqstr_from_two_time_bounds = _get_freqstr_from_two_time_bounds(ds)

    # Infer frequency from time labels
    # --------------------------------

    if ds["time"].values.size >= 3:  # Need 3 time steps to infer frequency
        freqstr_from_time_labels = xr.infer_freq(ds.time)
    else:
        freqstr_from_time_labels = None

    # Get lower and upper time bounds
    # -------------------------------

    lower_time_bnds = get_time_bounds(ds, which="lower")
    upper_time_bnds = get_time_bounds(ds, which="upper")

    # Conver to xarray DataArray for the convenience functions
    # --------------------------------------------------------

    if lower_time_bnds is not None and lower_time_bnds.size >= 3:
        lower_time_bnds = xr.DataArray(lower_time_bnds, dims="time")

    if upper_time_bnds is not None and upper_time_bnds.size >= 3:
        upper_time_bnds = xr.DataArray(upper_time_bnds, dims="time")

    # Infer frequency from lower time bounds
    # --------------------------------------

    if lower_time_bnds is not None and lower_time_bnds.size >= 3:
        freqstr_from_lower_time_bounds = xr.infer_freq(lower_time_bnds)
    else:
        freqstr_from_lower_time_bounds = None

    # Infer frequency from upper time bounds
    # --------------------------------------

    if upper_time_bnds is not None and upper_time_bnds.size >= 3:
        freqstr_from_upper_time_bounds = xr.infer_freq(upper_time_bnds)
    else:
        freqstr_from_upper_time_bounds = None

    # Get a list of all frequencies found
    # -----------------------------------

    freqstr_list = [
        freqstr_from_cmor_attrs,
        freqstr_from_time_labels,
        freqstr_from_lower_time_bounds,
        freqstr_from_upper_time_bounds,
        freqstr_from_single_time_bound,
        freqstr_from_two_time_bounds,
    ]

    # Remove None elements
    # --------------------

    freqstr_list = [elem for elem in freqstr_list if elem is not None]

    # If all time strings are None, raise Exception
    # ---------------------------------------------

    if all(element is None for element in freqstr_list):
        raise Exception("Could not determine frequency")

    # Convert frequency strings to pandas frequency objects
    # -----------------------------------------------------

    freq_objects = [
        pd.tseries.frequencies.to_offset(freq) for freq in freqstr_list
    ]

    # Check if all elements in the list are equal
    # -------------------------------------------

    all_equal = all(freq == freq_objects[0] for freq in freq_objects)

    if not all_equal and ds["time"].size > 2:
        message = (
            f"Frequency mismatsch:\n"
            f"From CMOR attributes: {freqstr_from_cmor_attrs}\n"
            f"From time labels: {freqstr_from_time_labels}\n"
            f"From lower time bounds: {freqstr_from_lower_time_bounds}\n"
            f"From upper time bounds: {freqstr_from_upper_time_bounds}\n"
        )
        raise Exception(message)

    elif not all_equal:
        logger.warning(
                "Time size of dataset to small to calculate frequency. "
                f"Continue with best estimation: {freqstr_from_cmor_attrs}."
                )

        freqstr = freqstr_from_cmor_attrs

    else:

        # Take first element of list (other element are equal as checked above)
        # ---------------------------------------------------------------------

        freqstr = freqstr_list[0]

    # Return
    # ------

    if dtype == "Timedelta":
        offset = to_offset(freqstr)
        if hasattr(offset, "nanos"):
            return pd.Timedelta(offset.nanos)
        else:
            raise Exception(
                f"The detected frequency is {freqstr}. A time delta in "
                "seconds cannot be returned. Try dtype='freqstr'"
            )
    if dtype == "DateOffset":
        return to_offset(freqstr)
    elif dtype == "freqstr":
        return freqstr
    else:
        message = "dtype should be DateOffset, or freqstr"
        raise Exception(message)


def has_geographic_coordinates(dat):
    """
    Determine if the data has geographic coordinates.

    Arguments:
        dat (:class:`xarray.Dataset`): The input data.

    Returns:
        bool: True if data has geograpic coordinates.

    Example:

        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.has_geographic_coordinates()
    """

    lat_name, lon_name = get_geographic_latlon_varnames(dat)

    if lat_name is not None and lon_name is not None:
        return True
    else:
        return False


def has_projection_coordinates(dat):
    """
    Determine if the data has y/x projection coordinates.

    Arguments:
        dat (:class:`xarray.Dataset`): The input data

    Returns:
        bool: True if data has projection coordinates.

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.has_projection_coordinates()
    """

    y_name, x_name = get_projection_yx_varnames(dat)

    if y_name is not None and x_name is not None:
        return True
    else:
        return False


def is_georeferenced(ds):
    """
    Determine if the dataset is georeferenced.

    A dataset is considered georeferenced if projection information is
    available  in any supported format (CF, EPSG, WKT, or PROJ string) and
    either geographic  or projected coordinates are present to compute the
    lower-left and upper-right corners.

    Arguments:
        dat (:class:`xarray.Dataset`): The input dataset.

    Returns:
        bool: True if the dataset is georeferenced, False otherwise.

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.is_georeferenced()
    """

    import pyku.geo as geo

    # Special case if the georeferencing exist but is unstructured
    # ------------------------------------------------------------

    # This would be the case for the ICON unstructured grid

    if has_unstructured_geographic_coordinates(ds):
        return True

    if has_projection_coordinates(ds) and not has_geographic_coordinates(ds):
        logger.warning(
            "Dataset has projection coordinates but no geographic coordinates!"
        )

    if has_geographic_coordinates(ds) and not has_projection_coordinates(ds):
        logger.warning(
            "Dataset has geographic coordinates but no projection coordinates!"
        )

    # Get area definitions
    # --------------------

    area_def_from_cf = geo._get_area_def_from_crs_cf(ds) is not None
    area_def_from_crs_proj_str = \
        geo._get_area_def_from_crs_proj_str(ds) is not None
    area_def_from_global_attrs = \
        geo._get_area_def_from_global_attrs(ds) is not None

    has_projection_information = (
        area_def_from_cf or area_def_from_crs_proj_str or
        area_def_from_global_attrs
    )

    # Return area definitions by priority
    # -----------------------------------

    if (
        (has_projection_coordinates(ds) or has_geographic_coordinates(ds)) and
        has_projection_information
    ):
        return True
    else:
        return False


def has_unstructured_geographic_coordinates(ds):
    """
    Determine if the lat/lon geographic coordinates are unstructured.

    Arguments:
      ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        bool: True if the lat/lon geographic coordinates are unstructured.
    """

    # Get dataset coordinate name
    # ---------------------------

    coord_names = list(ds.coords.keys())

    # ICON unstructured grid
    # ----------------------

    # For this first version and the forseable future, the 'clat' and 'clon'
    # variable names of the ICON grid is hard-coded. This is kept simple first
    # and it will be check in the future if it is needed to move the names for
    # the unstructured grid to the configuration file

    if "clat" in coord_names and "clon" in coord_names:
        return True
    else:
        return False


def get_geographic_latlon_varnames(ds):
    """
    Identify the variables holding geographic latitudes and longitudes within
    the dataset.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        tuple[str]:
            Name of variables holding geographic latitudes and longitudes.

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras-tas-monthly')
              ...: ds.pyku.get_geographic_latlon_varnames()
    """

    # Dataset coordinate names
    # ------------------------

    dataset_coord_names = list(ds.coords.keys())

    # Search for geographic latitude variable name
    # ---------------------------------------------

    # Get valid names
    valid_lat_names = meta_dict["geographic_latitude"]

    # Get other coordinate names, flatten the list of list to a list
    other_coord_names = [
        value
        for key, value in meta_dict.items()
        if key != "geographic_latitude"
    ]

    other_coord_names = [
        item for sublist in other_coord_names for item in sublist
    ]

    # Find matches
    lat_name = find_match(
        valid_lat_names, dataset_coord_names, other_coord_names
    )

    # Search for geographic longitude variable name
    # ---------------------------------------------

    # Get valid names
    valid_lon_names = meta_dict["geographic_longitude"]

    # Get other coordinate names, flattten the list of list ot a list
    other_coord_names = [
        value
        for key, value in meta_dict.items()
        if key != "geographic_longitude"
    ]

    other_coord_names = [
        item for sublist in other_coord_names for item in sublist
    ]

    # Find matches
    lon_name = find_match(
        valid_lon_names, dataset_coord_names, other_coord_names
    )

    return lat_name, lon_name


def get_projection_yx_varnames(ds):
    """
    Get the name of projection coordinate names

    Arguments:
        ds (:class:`xarray.Dataset`): Input dataset.

    Returns:
        tuple[str]: (y, x) Name of projection coordinates in dataset.

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras-tas-monthly')
              ...: ds.pyku.get_projection_yx_varnames()
    """

    # Unstructured georeferencing will contain geographic lat lon
    # -----------------------------------------------------------

    if has_unstructured_geographic_coordinates(ds):
        return None, None

    # Dataset coordinate and dimension names
    # --------------------------------------

    # It is possible, and unfortunately common, for dimensions not to have
    # corresponding coordinates. For instance, it is not unusual to encounter
    # data with lat/lon values associated with y/x dimensions but not defined
    # explicitly as coordinates.

    dataset_axes_names = list(
        set(list(ds.coords.keys()) + list(ds.sizes.keys()))
    )

    # Search for geographic latitude variable name
    # ---------------------------------------------

    # Get valid names
    valid_y_names = meta_dict["projection_coordinate_y"]

    # Get other coordinate names, flatten the list of list to a list
    other_coord_names = [
        value
        for key, value in meta_dict.items()
        if key != "projection_coordinate_y"
    ]

    other_coord_names = [
        item for sublist in other_coord_names for item in sublist
    ]

    # Find matches
    y_name = find_match(valid_y_names, dataset_axes_names, other_coord_names)

    # Search for geographic longitude variable name
    # ---------------------------------------------

    # Get valid names
    valid_x_names = meta_dict["projection_coordinate_x"]

    # Get other coordinate names, flattten the list of list ot a list
    other_coord_names = [
        value
        for key, value in meta_dict.items()
        if key != "projection_coordinate_x"
    ]

    other_coord_names = [
        item for sublist in other_coord_names for item in sublist
    ]

    # Find matches
    x_name = find_match(valid_x_names, dataset_axes_names, other_coord_names)

    # If not available, the projection is likely a lat/lon grid
    # ---------------------------------------------------------

    # In this special case, the map is provided on a lat/lon grid, which may
    # have irregular spacing. Here, the geographic lat/lon variables also serve
    # as the projection's y/x variable names.

    if x_name is None and y_name is None:

        lat_name, lon_name = get_geographic_latlon_varnames(ds)

        if has_geographic_coordinates(ds) is False:
            return None, None

        if ds[lat_name].ndim == 1 and ds[lat_name].ndim == 1:
            return lat_name, lon_name

        else:
            return None, None

    else:

        return y_name, x_name


def get_geodata_varnames(ds):
    """
    Get variable names of georeferenced data from dataset.

    The minimal requirement for a variable to be deemed georeferenced is to
    have either geographic or projection coordinates.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        list: Names of the georeferenced variables.

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras-tas-monthly')
              ...: ds.pyku.get_geodata_varnames()
    """

    return [
        var
        for var in list(ds.data_vars)
        if (
            (
                has_geographic_coordinates(ds[var]) or
                has_projection_coordinates(ds[var])
            ) and
            var not in meta_dict.get("spatial_vertices") and
            var not in meta_dict.get("spatial_bounds")
        )
    ]


def get_geodataset(ds, var):
    """
    Get dataset for georeferenced dataset. This function is usefull because it
    gets the variable with all climate data associated.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
        var (str, List(str)): The variable name(s).

    Returns:
        :class:`xarray.Dataset`: The geodata variable(s) with all associated
        climate data variables.

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.pyku.get_geodataset(var='tas')

    """

    import copy

    # If a string for a single variable is passed, make it a list of strings
    # ----------------------------------------------------------------------

    # Making a deep copy otherwise the original list gets modified by
    # reference.

    if isinstance(var, str):
        vars = [copy.deepcopy(var)]
    else:
        vars = copy.deepcopy(var)

    # Check that the variable(s) chosen is are georeferenced
    # ------------------------------------------------------

    geodata_varnames = get_geodata_varnames(ds)

    for var in vars:
        if var not in geodata_varnames:
            message = f"Variable {var} is not a georeferenced data variable"
            raise Exception(message)

    # Get the name of the climate data variables
    # ------------------------------------------

    crs_varname = get_crs_varname(ds)
    time_bounds_varname = get_time_bounds_varname(ds)
    spatial_bounds_varnames = get_spatial_bounds_varnames(ds)
    spatial_vertices_varnames = get_spatial_vertices_varnames(ds)

    # Get a list of point variables and remove time bounds if possible
    # ----------------------------------------------------------------

    list_of_point_variables = []

    for var in vars:
        if ds[var].attrs.get("cell_methods", None) in ["time: point"]:
            list_of_point_variables.append(var)

    if set(list_of_point_variables) == set(vars):
        time_bounds_varname = None

    # Add to the list of selected data variables
    # ------------------------------------------

    selected_datavars = vars

    if crs_varname is not None:
        selected_datavars.append(crs_varname)
    if time_bounds_varname is not None:
        selected_datavars.append(time_bounds_varname)
    if spatial_bounds_varnames != []:
        selected_datavars.extend(spatial_bounds_varnames)
    if spatial_vertices_varnames != []:
        selected_datavars.extend(spatial_vertices_varnames)

    return ds[selected_datavars]


def set_time_labels_from_time_bounds(*args, **kwargs):
    """
    This function has moved to
    :func:`pyku.timekit.set_time_labels_from_time_bounds`
    """

    import warnings
    import pyku.timekit as timekit

    warnings.warn(
        "This function has moved to "
        "pyku.timekit.set_time_labels_from_time_bounds and will be removed "
        "soon.",
        FutureWarning,
    )

    return timekit.set_time_labels_from_time_bounds(*args, **kwargs)


def set_time_bounds(*args, **kwargs):
    """
    This function has changed name and moved to
    timekit.set_time_bounds_from_time_labels.
    """

    import warnings
    import pyku.timekit as timekit

    warnings.warn(
        "This function changed named and moved to "
        "pyku.timekit.set_time_bounds_from_time_labels.",
        FutureWarning,
    )

    return timekit.set_time_bounds_from_time_labels(*args, **kwargs)


def to_gregorian_calendar(*args, **kwargs):
    """
    This function has moved to :func:`pyku.timekit.to_gregorian_calendar`.
    """

    import warnings
    import pyku.timekit as timekit

    warnings.warn(
        "This function has moved to pyku.timekit.to_gregorian_calendar.",
        FutureWarning,
    )

    ds = timekit.to_gregorian_calendar(*args, **kwargs)

    return ds


def select_common_datetimes(*args, **kwargs):
    """
    This function has moved to :func:`pyku.timekit.select_common_datetimes`
    """

    import warnings
    import pyku.timekit as timekit

    warnings.warn(
        "This function has moved to pyku.timekit.select_common_datetimes "
        "and will be removed soon.",
        FutureWarning,
    )

    return timekit.select_common_datetimes(*args, **kwargs)


def to_netcdf(ds, output_file):
    """
    Deprecated. Use :func:`pyku.magic.to_netcdf` instead
    """

    import pyku.magic as magic

    logger.warning("This function is about to get deprecated")

    magic.to_netcdf(ds=ds, output_file=output_file, cmor_encoding=True)
