"""
Data Reference Syntax (DRS) module

Resources:

* http://is-enes-data.github.io/
* http://is-enes-data.github.io/cordex_archive_specifications.pdf
* http://is-enes-data.github.io/CORDEX_variables_requirement_table.pdf
* https://github.com/IS-ENES-Data/IS-ENES-Data.github.io/blob/master/
  CORDEX_adjust_drs.pdf
* https://pcmdi.github.io/obs4MIPs/docs/ODSv2p1.pdf

The CMIP5 CORDEX standard has ambiguities regarding variable names. Appendix A
of the NetCDF header examples excludes the variable name from both mandatory
and optional metadata. While VariableName is listed in the Controlled
Vocabulary, suggesting it could be a mandatory global attribute, but no
standard key is defined. Consequently, most existing datasets omit the variable
name. In this context, 'variable_name' is automatically derived from the
dataset's climate data, even when it is not explicitly required by the
standard.

In contrast, newer standards like obs4mips explicitly include the variable name
in global attributes with the key 'variable_id'.
"""

__all__ = [
            'list_drs_standards'
            ]

import xarray as xr

from pyku import logger, PYKU_RESOURCES


def _check_available_standards(standard):
    """
    Checks if a standard is defined in etc/drs.standards

    Returns:
        None

    Raises:
        Value Error if standard is not defined
    """
    _available_standards = PYKU_RESOURCES.get_keys('drs', 'standards')
    if standard not in _available_standards:
        raise ValueError(
            f"DRS standard {standard} not implemented. Available standards "
            f"are {_available_standards}"
        )


def list_drs_standards():
    """
    List available DRS standards included in pyku

    Returns:
        List(str): List of DRS standards.
    """

    return list(PYKU_RESOURCES.get_keys('drs', 'standards'))


def drs_filename(ds, varname=None, standard=None, version=None):
    """
    Generate a filename based on the metadata in the given dataset and the
    standard from the 'drs.yaml' configuration file from pyku. Only one climate
    variable is supported.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset containing the required
            metadata.
        standard (str): The DRS standard to apply. Supported standards include
            {'cordex', 'cordex_adjust', 'reanalysis', 'obs4mips', 'cmip6'},
            as specified in ``pyku/drs.yaml``. The complete list of available
            standards can be obtained using ``pyku.list_drs_standards()``.
        version (str, optional): An optional version string. If provided, it
            will be used to create an additional directory between the CMOR
            path and the CMOR filename. While not CMOR-compliant, this practice
            is commonly used at DWD.

    Returns:
        str: The generated filename.

    Raises:
        ValueError: If the file contains no climate variable.
        ValueError: If the file contains more than one climate variable.
        ValueError: If the standard does not exist.

    Example:
        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('cordex_data')
              ...: ds.pyku.drs_filename(standard='cordex')
    """

    import os

    if varname is not None:
        logger.warning(
            "Parameter 'varname is deprecated' and now set automatically"
        )

    variable_names = ds.pyku.get_geodata_varnames()

    if len(variable_names) > 1:
        raise ValueError(
            "Only one climate variable is supported. The dataset contains "
            f"the following variables: {variable_names}."
        )

    elif len(variable_names) == 0:
        raise ValueError(
            "No climate dataset found in dataset. The dataset contains the "
            f"following variables: {ds.data_vars}."
        )

    # Check available standards
    # -------------------------

    _check_available_standards(standard)

    path = drs_parent(
        ds,
        standard=standard,
        version=version
    )

    stem = drs_stem(
        ds,
        standard=standard,
    )

    filename = os.path.join(path, stem)

    return filename


def drs_stem(ds, varname=None, standard=None):
    """
    Generate a file stem (basename) according to the metadata in the given
    dataset and the standard from the 'drs.yaml' configuration file from pyku.
    Only one climate variable is supported.

    Arguments:
        ds (:class:`xarray.Dataset`): The input Dataset.
        standard (str): The DRS standard to apply. Supported standards include
            {'cordex', 'cordex_adjust', 'reanalysis', 'obs4mips', 'cmip6'},
            as specified in ``pyku/drs.yaml``. The complete list of available
            standards can be obtained using ``pyku.list_drs_standards()``.

    Returns:
        str: File base name

    Raises:
        ValueError: If the file contains no climate variable.
        ValueError: If the file contains more than one climate variable.
        ValueError: If the standard does not exist.

    Example:
        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('cordex_data')
              ...: ds.pyku.drs_stem(standard='cordex')
    """

    import re
    from dateutil import parser
    import numpy as np
    import pyku.meta as meta
    from pandas.tseries.frequencies import to_offset

    # Sanity check
    # ------------

    if varname is not None:
        logger.warning(
            "The use of varname in drs.drs_stem is deprecated. The name of "
            "of the climate variable is now determined automatically."
        )

    # Get the name of the variables availabe in the dataset
    # -----------------------------------------------------

    variable_names = meta.get_geodata_varnames(ds)

    if len(variable_names) > 1:
        raise ValueError(
            "Only one climate variable is supported. The dataset contains "
            f"the following variables: {variable_names}."
        )

    elif len(variable_names) == 0:
        raise ValueError(
            "No climate dataset found in dataset. The dataset contains the "
            f"following variables: {ds.data_vars}."
        )

    # Create a namespace to store local variables
    # -------------------------------------------

    namespace = {}

    # The variable name is used when evaluating the filename pattern
    # --------------------------------------------------------------

    variable_name = variable_names[0]  # noqa

    # Check available standards
    # -------------------------

    _check_available_standards(standard)

    # Initialize the filename
    # -----------------------

    filename = None

    # Get file start and end time if applicable
    # -----------------------------------------

    if 'time' not in ds.coords:
        start_time = None
        end_time = None

    else:

        start_time = min(ds.coords['time'].values)
        end_time = max(ds.coords['time'].values)

        # Convert to ISO String, datetime, timestamp yyyymmdd
        # ---------------------------------------------------

        if isinstance(start_time, np.datetime64):
            start_time = np.datetime_as_string(
                start_time, unit='m', timezone='UTC'
            )
            start_time = parser.parse(start_time)

        if isinstance(end_time, np.datetime64):
            end_time = np.datetime_as_string(
                end_time, unit='m', timezone='UTC'
            )
            end_time = parser.parse(end_time)

        # Get frequency string and set output format accordingly
        # ------------------------------------------------------

        freqstr = meta.get_frequency(ds, dtype='freqstr')

        # Define frequency mappings with their corresponding time formats
        frequency_format_mapping = {
            to_offset('1h'): "%Y%m%d%H",
            to_offset('3h'): "%Y%m%d%H",
            to_offset('6h'): "%Y%m%d%H",
            to_offset('12h'): "%Y%m%d%H",
            to_offset('1D'): "%Y%m%d",
            to_offset('1MS'): "%Y%m",
            to_offset('QS-DEC'): "%Y%m",
            to_offset('1YS'): "%Y",
        }

        # Get the format string for this frequency, default to full timestamp
        time_format = frequency_format_mapping.get(
            to_offset(freqstr),
            "%Y%m%d%H%M%S"
        )

        # Format the time strings
        start_time = start_time.strftime(time_format)
        end_time = end_time.strftime(time_format)

    # Get file pattern from json file
    # -------------------------------

    filename_pattern = (
        PYKU_RESOURCES.get_value('drs', 'standards', standard, 'stem_pattern')
    )

    # Get all variables needed from file pattern
    # ------------------------------------------

    filename_keys = re.findall(r'\{(.*?)\}', filename_pattern)

    # Locally set variables to their values
    # -------------------------------------
    for key in filename_keys:

        if key == 'member_id':
            # Check for CMIP6 member_id which distinguish different simulations
            # belonging to a common root experiment. The member_id is
            # constructed from the sub_experiment_id and variant_label
            # using the following algorithm (I don't like this, but cannot
            # figure it out in a nicer way...):

            logger.warning(
                "The DRS configuration for CMIP6 is new and not fully checked"
            )

            if ds.attrs.get('sub_experiment_id') == 'none':
                namespace[key] = ds.attrs.get('variant_label')
            else:
                namespace[key] = (f"{ds.attrs.get('sub_experiment_id')}-"
                                  f"{ds.attrs.get('variant_label')}")
        else:
            namespace[key] = ds.attrs.get(key)

    # Edge case
    # ---------

    # DWD-HR: Are you sure about that? I have seen this for CORDEX but the
    # CMIP6/5 standard omits the time_range fully.
    # >> https://docs.google.com/document/d/1h0r8RZr_f3-8egBMMh7aqLwy3snpD6_MrDz1q8n5XUk/edit?tab=t.0  # noqa
    # If there is no time dimension, the filename should end with "fx". For
    # example: [...]_x0n1-v1_fx.nc, rather than
    # [...]_x0n1-v1_day_20220101-20221231.nc.
    #

    if start_time is None and end_time is None:
        filename_pattern = filename_pattern.replace(
            "_{start_time}-{end_time}", ""
        )

    # Add variables to the namespace
    # ------------------------------

    namespace['variable_name'] = variable_name
    namespace['start_time'] = start_time
    namespace['end_time'] = end_time

    # Evaluate the file pattern as an f-string
    # ----------------------------------------

    filename = _resolve_template(filename_pattern, namespace) + '.nc'

    return filename


def drs_parent(ds, varname=None, standard=None, version=None):
    """
    Generate a directory according to the metadata in the given dataset and the
    standard from the 'drs.yaml' configuration file from pyku. Only one climate
    variable is supported.

    Arguments:
        ds (:class:`xarray.Dataset`): The input Dataset.
        standard (str): The DRS standard. Supported standards include
            {'cordex', 'cordex_adjust', 'reanalysis', 'obs4mips', 'cmip6'},
            as specified in ``pyku/drs.yaml``. The complete list of available
            standards can be obtained using ``pyku.list_drs_standards()``.
        version (str, optional):  Optional version string. If provided, it will
            create an additional directory between the CMOR path and the CMOR
            filename. This practice for cmip5 cordex standard is not
            CMOR-conform and should be discouraged. Note: In 'obs4mips', the
            version is part of the standard and should be read from the global
            attributes.

    Returns:
        str: The generated filename parent.

    Raises:
        ValueError: If the file contains no climate variable.
        ValueError: If the file contains more than one climate variable.
        KeyError: If the standard does not exist.

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('cordex_data')
              ...: ds.pyku.drs_parent(standard='cordex')
    """

    import re
    import os
    import pyku.meta as meta

    if varname is not None:
        raise Exception("Parameter 'varname' is deprecated")

    # Check available standards
    # -------------------------

    _check_available_standards(standard)

    # Generate a namespace to store local variables
    # ---------------------------------------------

    namespace = {}

    # Get the name of the variables availabe in the dataset
    # -----------------------------------------------------

    variable_names = meta.get_geodata_varnames(ds)

    if len(variable_names) > 1:
        raise ValueError(
            "Only one climate variable is supported. The dataset contains "
            f"the following variables: {variable_names}."
        )

    elif len(variable_names) == 0:
        raise ValueError(
            "No climate dataset found in dataset. The dataset contains the "
            f"following variables: {ds.data_vars}."
        )

    # The variable name is used when evaluating the filename pattern
    # --------------------------------------------------------------

    variable_name = variable_names[0]  # noqa

    # Get file pattern from json file
    # -------------------------------

    pathname_pattern = PYKU_RESOURCES.get_value('drs',
                                                'standards',
                                                standard,
                                                'parent_pattern')

    # Get all variables needed from file pattern
    # ------------------------------------------

    pathname_keys = re.findall(r'\{(.*?)\}', pathname_pattern)

    # Locally set variables to their values
    # -------------------------------------

    # Note: This is maybe a hack because I do not know better, or maybe
    # it is the right way to do thing idk.

    for key in pathname_keys:

        if key == 'member_id':

            # Check for CMIP6 member_id which distinguish different simulations
            # belonging to a common root experiment. The member_id is
            # constructed from the sub_experiment_id and variant_label using
            # the following algorithm (I don't like this, but cannot figure it
            # out in a nicer way...):

            if ds.attrs.get('sub_experiment_id') == 'none':
                namespace[key] = ds.attrs.get('variant_label')
            else:
                namespace[key] = (f"{ds.attrs.get('sub_experiment_id')}-"
                                  f"{ds.attrs.get('variant_label')}")
        else:
            namespace[key] = ds.attrs.get(key)

    # Add optional version to path name
    # ---------------------------------

    # The custom here is to append a version to the directory name, even though
    # this is not part of the standard and is absent from the global
    # attributes. However, 'version' is a standard attribute in CMIP6, where it
    # should be included but is sometimes missing. This discrepancy leads to
    # the complications described below.

    version_is_in_pattern = 'version' in pathname_keys
    version_from_attrs = ds.attrs.get('version', None)
    version_from_parameters = version

    # Remove version from pattern
    # ---------------------------

    pathname_pattern = pathname_pattern.replace("{version}", "")

    # Add variables to the namespace
    # ------------------------------

    namespace['variable_name'] = variable_name

    # Evaluate the file pattern as an f-string
    # ----------------------------------------

    pathname = _resolve_template(pathname_pattern, namespace)

    if version_is_in_pattern and version_from_attrs is None:

        logger.warning(
            "The metadata shall contain the 'version' attribute in accordance "
            f"with the standard {standard}, where the directory pattern is "
            f"defined as {pathname_pattern}"
        )

    if version_from_attrs is not None and version_from_parameters is not None:

        if version_from_attrs != version_from_parameters:
            logger.warning(
                f"Passing version={version_from_parameters} as an argument to "
                f"this function, but version={version_from_attrs} is already "
                "present as a global attribute"
            )

        version = version_from_parameters

    # Add version to path
    # -------------------

    if version_from_parameters is not None:
        pathname = os.path.join(pathname, version_from_parameters)
    elif version_from_attrs is not None and not version_is_in_pattern:
        logger.warning("Version not in pattern but in attributes")
        pathname = os.path.join(pathname, version_from_attrs)
    elif version_from_attrs is not None and version_is_in_pattern:
        logger.warning("Using version from attributes")
        pathname = os.path.join(pathname, version_from_attrs)

    return pathname


def to_drs_netcdfs(
    ds, base_dir=None, standard='cordex', var=None, version=None,
    dry_run=False, encoding='auto', overwrite=False, complevel=None, **kwargs
):
    """
    Write CMOR-conform NetCDF files.

    Arguments:

        ds (:class:`xarray.Dataset`): Dataset with CMOR-conform metadata.

        base_dir (str): Output base directory. The file will be written
        according to 'base_dir/cmor_path/cmor_filename.nc'

        standard (str): The DRS standard to apply. Supported standards include
        {'cordex', 'cordex_adjust', 'reanalysis', 'obs4mips', 'cmip6'}, as
        specified in ``pyku/drs.yaml``. The complete list of available
        standards can be obtained using ``pyku.list_drs_standards()``.

        var (str): Variable to be cmorized. Only one variable per file is
        supported at the moment.

        version (str): Optional. The version string creates an additional
        directory between the cmor path and the cmor filename
        ``/cmor/path/version/cmor_filename.nc``. The practice is not
        CMOR-conform and its usage should be discouraged. However the use of
        the version argument in that manner is widespread at DWD.

        dry_run (bool): Optional. Whether to try a dry run without writing the
        data first.

        encoding (dict): Deprecated. Now the encoding is set from yaml file
        ``drs.yaml``. Optional encoding parameters when writing the NetCDF
        files. For details, see :func:`xarray.Dataset.to_netcdf`.

        overwrite (bool): Optional. Whether exiting files should be overwritten
        if they already exist. Defaults to False

..        **kwargs: Additional keyword arguments.
..            output_frequency (str, optional): Specifies the frequency type of
..            the output (e.g., "year", "month").
..            interval_range (int, optional): Specifies the time interval of
..            the output.

    """

    import os
    import uuid
    import itertools
    import pathlib
    import calendar
    import numpy as np
    import pyku.meta as meta
    import pyku.magic as magic
    from pandas.tseries.frequencies import to_offset

    # Sanity check if any of the attributes exist but is None
    # -------------------------------------------------------

    for key, value in ds.attrs.items():
        assert value is not None, "Dataset key {} is None".format(key)

    logger.debug(f"{ds.pyku.get_dataset_size()=}")

    # Get the name of the data variables in file
    # ------------------------------------------

    data_variables = meta.get_geodata_varnames(ds)

    # Sanity checks
    # -------------

    assert base_dir is not None, "base_dir is mandatory"
    assert len(data_variables) == 1, \
        "One and only one CMOR variable in dataset supported"

    if 'time' not in list(dict(ds.sizes).keys()):
        logger.warning("No 'time' dimension found in dataset")
        logger.warning("Trying cmorization of a constant field")

        # No grouping necessary
        groups = [1]
        has_time_dim = False

    else:

        has_time_dim = True

        if has_cmor_time_labels(ds, var=data_variables[0]) is False:

            logger.warning(
                "Time labels are not CMOR-compliant. By design, pyku does not "
                "enforce this part of the CMOR convention. If you need the "
                "time labels to be set to the middle of the time bounds, use "
                "the dedicated pyku function set_time_labels_from_time_bounds "
                "with the how='lower' option."
            )

        # Split years into groups of 5 years
        # ----------------------------------

        # Setting splitting according to
        # http://is-enes-data.github.io/cordex_archive_specifications.pdf

        # Get data frequency
        # ------------------

        data_frequency = meta.get_frequency(ds, dtype='freqstr')

        # Determine the type of CMOR outputs
        # ----------------------------------

        # Split data into groups of 1 year, if 1-hourly, 3-hourly or 6-hourly
        # -------------------------------------------------------------------

        interval_type = kwargs.get('output_frequency', 'year')
        if to_offset(data_frequency) in \
           [to_offset('h'), to_offset('3h'), to_offset('6h')]:
            interval_range = kwargs.get('interval_range', 1)

        elif to_offset(data_frequency) in [to_offset('12h'), to_offset('1D')]:
            interval_range = kwargs.get('interval_range', 5)

        elif (
            to_offset(data_frequency) in
            [to_offset('1MS'), to_offset('QS-DEC')]
        ):
            interval_range = kwargs.get('interval_range', 10)

        elif (to_offset(data_frequency) == to_offset('1YS')):
            interval_range = kwargs.get('interval_range', 100)

        else:
            interval_range = kwargs.get('interval_range', 5)
            logger.warning('Not data frequency detected!')
            logger.warning('Splitting data into groups of 5 years!')

        if interval_type == 'month':
            # year + month
            times, _ = zip(*ds.groupby(['time.year', 'time.month']))
            times = list(times)

            # index for year-month-combination
            times_sorted = sorted(times)
            logger.info(f"TIMES SORTED {times_sorted}")
            times_idx = list(range(len(times_sorted)))

            groups = np.array([
                [times_sorted[i] for i in g]
                for k, g in itertools.groupby(
                    times_idx, lambda i: i // interval_range)
            ], dtype=object)

        else:
            times, _ = zip(*ds.groupby(f'time.{interval_type}'))

            groups = np.array([
                list(g) for k, g
                in itertools.groupby(
                    times, lambda i: (i - 1) // interval_range)
            ], dtype=object)

    for group in groups:

        logger.info(f"Processing {group}")

        # Select data within yearly group time range
        # ------------------------------------------

        if has_time_dim:
            if interval_type == 'month':
                start = f"{group[0][0]:04d}-{group[0][1]:02d}-01"
                end_year, end_month = group[-1]
                last_day = calendar.monthrange(end_year, end_month)[1]
                end = f"{end_year:04d}-{end_month:02d}-{last_day:02d}"
                ds_sel = ds.sel(time=slice(start, end))
            else:
                ds_sel = ds.sel(time=slice(f"{min(group)}", f"{max(group)}"))
        else:
            ds_sel = ds

        # Set file tracking id
        # --------------------

        ds_sel.attrs['tracking_id'] = str(uuid.uuid4())

        # Determine DRS file name from metadata
        # -------------------------------------

        filename = drs_filename(
            ds_sel,
            version=version,
            standard=standard
        )

        path = drs_parent(
            ds_sel,
            version=version,
            standard=standard
        )

        # Set output dir and output_file
        # ------------------------------

        # The output file consists of where the data are written on disk plus
        # the DRS filename.

        output_file = os.path.join(base_dir, filename)
        output_dir = os.path.join(base_dir, path)

        # Show what the filename would be for a dry run
        # ---------------------------------------------

        if dry_run is True:
            logger.info(f"Dry output: {output_file}")

        # Write to file
        # -------------

        if dry_run is False:

            # Create directory structure
            # --------------------------

            pathlib.Path(output_dir).mkdir(parents=True, exist_ok=True)

            # Write data to NetCDF
            # --------------------

            if pathlib.Path(f'{output_file}').is_file() and not overwrite:
                logger.info(f"{output_file} already exists. Doing nothing!")

            else:

                magic.to_netcdf(
                    ds_sel,
                    f"{output_file}",
                    encoding=encoding,
                    complevel=complevel,
                )


def _is_precipitations(ds, var=None):
    """
    Determine if variable var in dataset is precipitations.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
        var (str): The variable

    Returns:
        bool: Whether variable in dataset is precipitation
    """

    # Sanity check
    # ------------

    assert var is not None, "Parameter 'var' is mandatory"

    # Detect precipitations
    # ---------------------

    # We lower the case and strip white spaces for the function to work despite
    # typos

    standard_name = ds[var].attrs.get('standard_name', 'na').lower().strip()
    long_name = ds[var].attrs.get('long_name', 'na').lower().strip()

    is_precipitation = (
        get_cmor_varname(ds[var]) in ['pr']
        or standard_name in ['precipitation_amount']
        or standard_name in ["thickness_of_rainfall_amount"]
        or long_name in ['total precipitation amount']
        or long_name in ["precipitation heigth"]
        or long_name in ["daily precipitation sum"]
        or long_name in ["hourly rainfall"]
        or long_name in ["daily rainfall"]
    )

    return is_precipitation


def _to_precipitations_cmor_units(ds, var=None):
    """
    Convert units for preciptations to CMOR-conform units.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
        var (str): The precipitations variable

    Returns:
        :class:`xarray.Dataset`: The dataset with CMOR-conform units for
        precipitations
    """

    from pyku import meta

    # Sanity check
    # ------------

    assert var is not None, "Parameter 'var' is mandatory"

    # Keep variables attributes
    # -------------------------

    xr.set_options(keep_attrs=True)

    # Create a shallow copy
    # ---------------------

    # Some operations modify the data inplace. By creating a shallow copy, we
    # leave the original object untouched. This may not be needed for this case

    ds_copy = ds.copy()

    # Case where dataset variable is not precipitations
    # -------------------------------------------------

    if _is_precipitations(ds_copy, var=var) is False:
        logger.warning('No precipitations in dataarray, cannot convert units')
        return ds

    pr_units = ds[var].attrs.get('units').lower().strip()

    # Case where units are already correct
    # ------------------------------------

    if pr_units in ['kg m-2 s-1', 'kg m^-2 s^-1']:
        return ds

    if pr_units not in ['kg m-2', 'kg m^-2', 'mm']:
        logger.warning(
            f"Units are {pr_units}. Unit assumes it is equivalent to kg m-2."
            "per default. Check your output."
        )

    # Get DataArray
    # -------------

    # Ideally, it would be great in the future to quantify with
    # da.metpy.quantify() and then convert units using Pint and the time
    # intervals with ``get_time_intervals``. Note however that some datasets
    # are bad and do not include the time bounds by default. Hence this should
    # be first included in the ``repair_time_bounds`` function.

    da = ds_copy[var]

    # Divide values by the number of seconds
    # --------------------------------------

    # Here with metpy.quantify it will be better to update
    # and use get_time_intervals for it to be more general

    time_delta = meta.get_frequency(ds_copy, dtype='Timedelta')

    # Divide by the total number of seconds
    # -------------------------------------

    da = da / time_delta.total_seconds()

    # Set the CMOR precipitation units
    # --------------------------------

    da.attrs['units'] = PYKU_RESOURCES.get_value('drs',
                                                 'variables',
                                                 'pr',
                                                 'cmor_units')

    # Set CMOR attributes
    # -------------------

    # Strictly speaking, the function should only change the units and not the
    # attributes. However there is so much creativity for precipitation units,
    # standard_name and long_name, that this is set here.

    da.attrs['standard_name'] = (
        PYKU_RESOURCES.get_value('drs', 'variables', 'pr', 'standard_name')
    )

    da.attrs['long_name'] = (
        PYKU_RESOURCES.get_value('drs', 'variables', 'pr', 'long_name')
    )

    # Overwrite DataArray into Dataset and return
    # -------------------------------------------

    ds_copy[var] = da

    return ds_copy


def to_cmor_units(ds):
    """
    Convert CMOR variables to CMOR-conform units.

    Arguments:
        ds (:class:`xarray.Dataset`): The input data.

    Returns:
        :class:`xarray.Dataset`: The data with CMOR-conform units.

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('cordex_data')
              ...: ds.pyku.to_cmor_units()['tas'].attrs
    """

    import metpy  # noqa: F401

    # Notes
    # -----

    # - Loop over data variables
    #     - Check if the variable has a CMOR standard:
    #         - If special case of precipitation, convert precipitation units
    #         - Otherwise convert units

    # Keep variables attributes
    # -------------------------

    xr.set_options(keep_attrs=True)

    # Create a shallow copy
    # ---------------------

    # This is necessary because operations like ``ds[var] = newdatarray``
    # modify the data inplace. By creating a shallow copy, we leave the
    # original object untouched

    ds_out = ds.copy()

    # Loop over data variables
    # ------------------------

    for var in ds_out.data_vars:

        # Get variable CMOR name
        # ----------------------

        cmor_varname = get_cmor_varname(ds_out[var])

        if cmor_varname in PYKU_RESOURCES.get_keys('drs', 'variables'):

            # Deal with units of precipitations, which can be creative
            # --------------------------------------------------------

            if _is_precipitations(ds_out, var=var):

                ds_out[var] = _to_precipitations_cmor_units(ds_out, var)[var]

            else:

                # Get CMOR unit for variable
                # --------------------------

                units = (
                    PYKU_RESOURCES.get_value('drs',
                                             'variables',
                                             cmor_varname,
                                             'units')
                )

                # Quantify
                # --------

                da = ds_out[var].metpy.quantify()

                # Apply units and set attributes
                # ------------------------------

                da.data.ito(units)

                # Dequantify and return
                # ---------------------

                da = da.metpy.dequantify()

                # Set unit attribute
                # ------------------

                da.attrs['units'] = (
                    PYKU_RESOURCES.get_value('drs',
                                             'variables',
                                             cmor_varname,
                                             'cmor_units')
                )

                ds_out[var] = da

    return ds_out


def get_cmor_varname(da):
    """
    Infer CMOR variable name

    Arguments:
        da (:class:`xarray.DataArray`): The input data array.

    Returns:
        str: CMOR-conform variable name infered from the data
    """

    import xarray as xr

    if not isinstance(da, xr.DataArray):
        raise Exception(
            "get_cmor_varname takes as input a xarray DataArray, "
            f"not {type(da)} with value {da}"
        )

    # Case where the name of the variable is already CMOR-conform
    # -----------------------------------------------------------

    if da.name in PYKU_RESOURCES.get_keys('drs', 'variables'):
        return da.name

    # Try identifying the variable with `other_names`
    # -----------------------------------------------

    for var in PYKU_RESOURCES.get_keys('drs', 'variables'):
        if da.name in PYKU_RESOURCES.get_value('drs',
                                               'variables',
                                               var,
                                               'other_names'):
            return var

    # Try identifying the variable with `standard_name`
    # -------------------------------------------------

    for var in PYKU_RESOURCES.get_keys('drs', 'variables'):

        if (
            da.attrs.get('standard_name') is not None and
            da.attrs.get('standard_name') in (
                PYKU_RESOURCES.get_value('drs',
                                         'variables',
                                         var,
                                         'standard_name')
                )
        ):

            return var

    # Try identifying the variable with `long_name`
    # ---------------------------------------------

    for var in PYKU_RESOURCES.get_keys('drs', 'variables'):
        if (
            da.attrs.get('long_name') is not None and
            da.attrs.get('long_name') in (
                PYKU_RESOURCES.get_value('drs',
                                         'variables',
                                         var,
                                         'long_name')
            )
        ):

            return var

    # We have reached the end and could not find the variable
    # -------------------------------------------------------

    return None


def to_cmor_varnames(ds):
    """
    Convert variables to CMOR-conform variables.

    Arguments:
        ds (:class:`xarray.Dataset`): The input data.

    Returns:
        :class:`xarray.Dataset`: Data with CMOR-conform variable names
    """

    import xarray as xr
    import pyku.meta as meta

    # Keep variables attributes
    # -------------------------

    xr.set_options(keep_attrs=True)

    # Remove variable_id field if present
    # -----------------------------------

    # If the file contains more than one variable, the field variable_id should
    # not be present at the Dataset level. The field is therefore removed by
    # default.

    if "variable_id" in ds.attrs and \
       len(meta.get_geodata_varnames(ds)) > 1:
        del ds.attrs["variable_id"]

    # Loop over all data variables in dataset
    # ---------------------------------------

    for var in ds.data_vars:

        # Get the corresponding CMOR variable name
        # ----------------------------------------

        cmor_varname = get_cmor_varname(ds[var])

        if cmor_varname is None:
            continue

        # If the variable name is not CMOR-conform, rename
        # ------------------------------------------------

        if var not in [cmor_varname]:

            ds = ds.rename({var: cmor_varname})

    return ds


def _to_cmor_attrs_var(ds):
    """
    Set variable attribute to CMOR standard.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset

    Returns:
        :class:`xarray.Dataset`: Dataset with CMOR-conform variable attributes.
    """

    import xarray as xr
    import pyku.meta as meta

    # Keep variables attributes
    # -------------------------

    xr.set_options(keep_attrs=True)

    # Loop over all data variables in dataset
    # ---------------------------------------

    for var in ds.data_vars:

        # Convert GRIB convention
        # -----------------------

        # Note that this is very 'pragmatic' and may be subject to change as I
        # am not sure whether or not pyku should support GRIB, and whether
        # dedicated conversion functions should be written. This is thus
        # exploratory.

        if ds[var].attrs.get('GRIB_stepType', None) in ['instant']:

            if (
                ds[var].attrs.get('cell_methods', None) is not None and
                ds[var].attrs.get('cell_methods', None) not in ['time: point']
            ):
                raise Exception(
                    "GRIB_stepType is instant, but the CF-conform are not "
                    "'time: point', which is inconsistent. You may need to "
                    "delete the GRIB_stepType attribute and set "
                    "'cell_methods' manually."
                )

            ds[var].attrs['cell_methods'] = 'time: point'

        # Get the CMOR variable name
        # --------------------------

        cmor_varname = get_cmor_varname(ds[var])

        if cmor_varname in PYKU_RESOURCES.get_keys('drs', 'variables'):

            # Send a warning if rotated wind components are found
            # ---------------------------------------------------

            if (
                ds[var].attrs.get('standard_name') in
                ['grid_eastward_wind', 'grid_northward_wind']
            ):

                logger.warning = (
                    "The standard name for {var} is "
                    "{ds[var].attrs['standard_name']}. Are you using rotated "
                    "latitude/longitude coordinates and forgetting to "
                    "derotate the data? If so, you must manually adjust the "
                    f"attributes for {var} before using the function. "
                    "Alternatively, you can use the pyku derotate function."
                )

            # Set CMOR attributes
            # -------------------

            ds[var].attrs['standard_name'] = (
                PYKU_RESOURCES.get_value('drs',
                                         'variables',
                                         cmor_varname,
                                         'standard_name')
            )

            ds[var].attrs['long_name'] = (
                PYKU_RESOURCES.get_value('drs',
                                         'variables',
                                         cmor_varname,
                                         'long_name')
            )

        else:

            if var in meta.get_geodata_varnames(ds):
                logger.warning(
                    f"No CMOR attributes were found for {var} in the pyku "
                    "configuration file. Continuing without setting them."
                )

    return ds


def _get_cmor_coordinate_name(coordinate_name):
    """
    Infer CMOR-confrom coordinate name from coordinate name.

    Arguments:
        coordinate_name (str): The input coordinate name.

    Returns:
        str: CMOR-conform coordinate name.
    """

    # Case where the name of the coordinate is already CMOR-conform
    # -------------------------------------------------------------

    if coordinate_name in PYKU_RESOURCES.get_keys('drs', 'coordinates'):
        return coordinate_name

    # Try identifying the variable with aliases
    # -----------------------------------------

    for name in PYKU_RESOURCES.get_keys('drs', 'coordinates'):
        if name in PYKU_RESOURCES.get_value('drs',
                                            'coordinates',
                                            name,
                                            'aliases'):
            return name

    # We have reached the end and could not find the variable
    # -------------------------------------------------------

    return None


def _to_cmor_attrs_coords(ds):
    """
    Set coordinate attributes to CMOR standard.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`xarray.Dataset`: Dataset with CMOR-conform coordinate
        attributes.
    """

    import xarray as xr

    # Keep variables attributes
    # -------------------------

    xr.set_options(keep_attrs=True)

    # Loop over know coordinate keys
    # ------------------------------

    for coordinate in ds.coords.keys():

        if _get_cmor_coordinate_name(coordinate) is not None:

            ds[coordinate].attrs = \
                PYKU_RESOURCES.get_value('drs',
                                         'coordinates',
                                         coordinate,
                                         'attrs')

        else:
            message = \
                f"No CMOR coordinate attributes for {coordinate} available"
            logger.info(message)

    return ds


def _to_cmor_attrs_frequency(ds):
    """
    Set frequency attribute to CMOR standard.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset

    Returns:
        :class:`xarray.Dataset`: Dataset with CMOR-conform frequency attribute
    """

    import xarray as xr
    import pyku.meta as meta
    from pandas.tseries.frequencies import to_offset

    # Keep variables attributes
    # -------------------------

    xr.set_options(keep_attrs=True)

    # Get frequency from dataset
    # --------------------------

    frequency = meta.get_frequency(ds, dtype='freqstr')

    # Find if frequency is part of the CMOR standard
    # ----------------------------------------------

    # Mapping of frequency offsets to CMOR-conform frequency strings
    frequency_mapping = {
        to_offset('1h'): '1hr',
        to_offset('3h'): '3hr',
        to_offset('6h'): '6hr',
        to_offset('12h'): '12hr',
        to_offset('1D'): 'day',
        to_offset('1MS'): 'mon',
        to_offset('QS-DEC'): 'sem',
        to_offset('1YS'): 'year',
    }

    # Set CMOR-conform frequency attribute
    # ------------------------------------

    offset = to_offset(frequency)

    if offset in frequency_mapping:
        ds.attrs['frequency'] = frequency_mapping[offset]
    else:
        logger.warning(
            f"frequency not a CMOR standard, using frequency="
            f"'{offset.freqstr}'. See "
            "https://pandas.pydata.org/pandas-docs/stable/user_guide/"
            "timeseries.html#offset-aliases"
        )
        ds.attrs['frequency'] = offset.freqstr

    return ds


def to_cmor_attrs(ds):
    """
    Set dataset attributes to CMOR standard.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`xarray.Dataset`: Dataset with CMOR-conform attributes
    """

    ds = _to_cmor_attrs_var(ds)
    ds = _to_cmor_attrs_coords(ds)
    ds = _to_cmor_attrs_frequency(ds)

    return ds


def has_cmor_time_labels(ds, var=None):
    """
    Check if time labels are conform to the CMOR convention.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
        var (str): The input variable.

    Returns:
        bool: Whether the time labels are CMOR-conform

    Example:
        .. ipython::

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('cordex_data')
              ...: ds.pyku.has_cmor_time_labels(var='tas')
    """

    import warnings
    import numpy as np
    import pyku.meta as meta
    import pyku.timekit as timekit

    # Sanity checks
    # -------------

    if var is None:
        raise Exception("Specify variable with 'var'")

    # Get variable as dataset with all climate data (i.e. with crs, time_bnds)
    # ------------------------------------------------------------------------

    var_ds = meta.get_geodataset(ds, var=var)

    # Check 'cell_methods' attribute and return False if not available
    # ----------------------------------------------------------------

    if var_ds[var].attrs.get('cell_methods', None) is None:
        warnings.warn("Variable has no 'cell_methods' attribute!")
        return False

    # Initialize to True
    # ------------------

    is_cmor_conform = True

    # If variable has time bounds, check time label in the middle
    # -----------------------------------------------------------

    if meta.has_time_bounds(var_ds):

        time_labels = var_ds.time.values

        middle_time_labels = timekit.set_time_labels_from_time_bounds(
            var_ds, how='middle'
        ).time.values

        are_equal = np.array_equal(time_labels, middle_time_labels)

        is_cmor_conform = are_equal

    return is_cmor_conform


def get_facets_from_file_parent(filename, standard, has_version=False):
    """
    Read facets from file path.

    Arguments:

        filename (string): The filename with or without path.

        standards (str): One of the standards defined in pyku (for example
            cordex, obs4mips). All standard can be listed with
            :func:`pyku.drs.list_drs_standards`

        has_version (bool): Defaults to false. If the facets include a non-CMOR
            conform version at the end of the directory. For example, if the
            file directory is of the form ``/path/to/1hr/tas/v20230630/``, it
            contains a non-conform CMOR path including a version number.

    Note:

        The available standards are available in dictionary
        ``pyku.PYKU_RESOURCES.load_resource('drs')``:

        .. ipython::

           In [0]: import pyku.drs as drs
              ...: list(drs.list_drs_standards())

        For example the patterns for the cordex standard can be obtained with:

        .. ipython::

           In [0]: print(pyku.PYKU_RESOURCES.get_value('drs', \
                                                       'standards', \
                                                       'cordex', \
                                                       'parent_pattern'))

    Example:

        .. ipython::

           In [0]: import pyku.drs as drs
              ...:
              ...: filename = '/path/to/DATA/CMOR/OUT/DWD-CPS/\\
              ...: output/GER-0275/CLMcom-DWD/ECMWF-ERA5/evaluation/r1i1p1/\\
              ...: CLMcom-DWD-CCLM5-0-16/x0n1-v1/1hr/tas/v20230630/\\
              ...: tas_GER-0275_ECMWF-ERA5_evaluation_r1i1p1_\\
              ...: CLMcom-DWD-CCLM5-0-16_x0n1-v1_1hr_\\
              ...: 202201010000-202212312300.nc'
              ...:
              ...: drs.get_facets_from_file_parent(
              ...:     filename,
              ...:     standard='cordex',
              ...:     has_version=True
              ...: )
    """

    from pathlib import Path
    import parse

    # Get stem pattern from standard
    # ------------------------------

    parent_pattern = (
        PYKU_RESOURCES.get_value('drs',
                                 'standards',
                                 standard,
                                 'parent_pattern')
    )

    # Deal with the variable name
    # ---------------------------

    # If the path has an extra and non-CMOR conform version, we need to add
    # this by hand.

    if has_version is True:
        parent_pattern = str(Path(parent_pattern)) + '/{version}'

    # Check for a file
    # ----------------

    # Files are identified by checking if there is a suffix

    has_file = Path(filename).suffix not in ['']

    # Get directory
    # -------------

    if has_file is True:
        directory = str(Path(filename).parent)
    else:
        directory = filename

    # Get the number of parts expected from the pattern
    # -------------------------------------------------

    # Split the directory into its components and count the number of
    # components

    nparts = len(Path(parent_pattern).parts)

    # Select these parts from the file directory
    # ------------------------------------------

    directory_parts = Path(directory).parts[-nparts:]

    # Get the directory without the root
    # ----------------------------------

    # For example, if the directory is:
    # '/path/to/DATA/CLM/CMOR/OUT/DWD-CPS/GER-0275/CLMcom-DWD/more/
    # We then obtain /DWD-CPS/GER-0275/CLMcom-DWD/more/

    directory_without_root = str(Path(*directory_parts))

    # Match directory facets to pattern
    # ---------------------------------

    facets = parse.parse(parent_pattern, directory_without_root)

    if facets:
        return facets.named
    else:
        logger.warning(f"Could not match {parent_pattern} to {directory}")
        return None


def get_facets_from_file_stem(filename, standard):
    """
    Read facets from file stem

    Arguments:
        filename (string): The filename with or without path.
        standard (str): The DRS standard. Supported standards include
            {'cordex', 'cordex_adjust', 'reanalysis', 'obs4mips', 'cmip6'},
            as specified in ``pyku/drs.yaml``. The complete list of available
            standards can be obtained using ``pyku.list_drs_standards()``.

    Note:

        The available standards are available in dictionary
        ``pyku.PYKU_RESOURCES.load_resource('drs')``:

        .. ipython::

           In [0]: import pyku.drs as drs
              ...: list(drs.PYKU_RESOURCES.get_keys('drs', 'standards'))

        For example the patterns for the cordex standard can be obtained with:

        .. ipython::

           In [0]: print(pyku.PYKU_RESOURCES.get_value('drs', \
                                                       'standards', \
                                                       'cordex', \
                                                       'stem_pattern'))

    Example:

        .. ipython::

           In [0]: import pyku.drs as drs
              ...:
              ...: filename = '/path/to/DATA/CLM/CMOR/OUT/DWD-CPS/\\
              ...: output/GER-0275/CLMcom-DWD/ECMWF-ERA5/evaluation/r1i1p1/\\
              ...: CLMcom-DWD-CCLM5-0-16/x0n1-v1/1hr/tas/v20230630/\\
              ...: tas_GER-0275_ECMWF-ERA5_evaluation_r1i1p1_\\
              ...: CLMcom-DWD-CCLM5-0-16_x0n1-v1_1hr_\\
              ...: 202201010000-202212312300.nc'
              ...:
              ...: drs.get_facets_from_file_stem(filename, standard='cordex')
    """

    from pathlib import Path
    import parse

    # Get stem pattern from standard
    # ------------------------------

    stem_pattern = (
        PYKU_RESOURCES.get_value('drs', 'standards', standard, 'stem_pattern')
    )

    # Get stem from file name
    # -----------------------

    facets = parse.parse(
        stem_pattern,
        str(Path(filename).stem)
    )

    if facets:
        return facets.named
    else:
        logger.warning(f"Could not match {stem_pattern} to {filename}")
        return None


def cmorize(ds, global_metadata={}, area_def=None):
    """
    CMORize dataset. The variable shall contain only one variable.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
        metadata (dict): The dictionary of global metadata.
        area_def(:class:`pyresample.geometry.AreaDefinition`, str):
            (Deprecated) Output area definition.

    Returns:
        :class:`xarray.Dataset`: CMORized dataset.

    Raises:
        ValueError: If the file contains no climate variable.
        ValueError: If the file contains more than one climate variable.
    """

    import pyku.timekit as timekit
    import pyku.meta as meta
    import pyku.geo as geo

    if area_def is not None:
        raise DeprecationWarning(
            "The parameter for area definition 'area_def' is deprecated and "
            "geographic operations should be done before or after this "
            "function by using `pyku.geo.project()`."
        )

    # Get geodata variable names in dataset
    # -------------------------------------

    geodata_varnames = meta.get_geodata_varnames(ds)

    # Remove spatial bounds and vertices for sanity
    # ---------------------------------------------

    # This is a simplified design choice at the moment. It certainly is good to
    # keep the original spatial bounds in the CMORized dataset. At the same
    # time it is not strictly needed and can be calculated with
    # pyku.geo.set_latlon_bounds

    spatial_bounds_varnames = meta.get_spatial_bounds_varnames(ds)
    spatial_vertices_varnames = meta.get_spatial_vertices_varnames(ds)

    if len(spatial_bounds_varnames) > 0:
        logger.warning("Removing spatial bounds from dataset")
        ds = ds.drop_vars(spatial_bounds_varnames)

    if len(spatial_vertices_varnames) > 0:
        logger.warning("Removing vertices from dataset")
        ds = ds.drop_vars(spatial_vertices_varnames)

    # Sanity checks
    # -------------

    if len(geodata_varnames) > 1:
        raise ValueError(
            "Only one climate variable is supported. The dataset contains "
            f"the following variables: {geodata_varnames}."
        )

    if len(geodata_varnames) == 0:
        raise ValueError(
            "No climate dataset found in dataset. The dataset contains the "
            f"following variables: {ds.data_vars}."
        )

    # The variable name is the first and only entry
    # ---------------------------------------------

    var = geodata_varnames[0]

    # Check the variable be cmorized
    # -----------------------------

    if get_cmor_varname(ds[var]) is None:
        raise NotImplementedError(
            f"Variable {var} not implemented in pyku drs.yaml configuration "
            "file"
        )

    # Set time labels from lower time bound
    # -------------------------------------

    if meta.has_time_bounds(ds):
        ds = timekit.set_time_labels_from_time_bounds(ds, how='middle')

    # Get the variable dataset
    # ------------------------

    dsvar = meta.get_geodataset(ds, var)

    # Set CMOR variable names, units and attributes
    # ---------------------------------------------

    dsvar = dsvar.pyku.to_cmor_varnames()
    dsvar = dsvar.pyku.to_cmor_units()
    dsvar = dsvar.pyku.to_cmor_attrs()

    # Assign global metadata
    # ----------------------

    dsvar = dsvar.assign_attrs(global_metadata)

    # Resample geographic projection
    # ------------------------------

    if area_def is not None:
        dsvar = geo.project(dsvar, area_def)

    if meta.get_crs_varname(ds) is None:
        logger.warning("No CF-conform CRS in dataset")

    # Remove non-CMOR coordinates
    # ---------------------------

    # The COSMO model contains height_2m, height_10m or height_toa. These
    # are not requested in CMOR. Hence only the geographic and projection
    # coordinates are kept together with the time coordinate

    latlon_varnames = meta.get_geographic_latlon_varnames(ds)
    yx_varnames = meta.get_projection_yx_varnames(ds)

    valid_cmor_coordinates = [
        'time',
        *latlon_varnames,
        *yx_varnames,
    ]

    invalid_cmor_coordinates = \
        set(dsvar.coords.keys()) - set(valid_cmor_coordinates)

    dsvar = dsvar.drop_vars(invalid_cmor_coordinates)

    return dsvar


def _resolve_template(tstring, namespace):
    """
    Templating a string with a namespace.

    Arguments:
        tstring (str or :class:`string.Template`): The string to resolve. If
        a string.Template is provided, the function will use the substitute
        method of the Template class. If a string is provided, the function
        will use the format method of the string class.
        namespace (dict): The namespace to use for templating. The keys of the
        dictionary should correspond to the placeholders in the string.

    Returns:
        str: The templated string.

    Raises:
        KeyError: If there are unresolved placeholders in the string after
        templating.
    """
    if isinstance(tstring, str):
        return tstring.format(**namespace)

    from string import Template
    if isinstance(tstring, Template):
        return tstring.substitute(namespace)
