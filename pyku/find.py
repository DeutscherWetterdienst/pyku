#!/usr/bin/env python3

__all__ = [
            'get_file_dataframe',
            'get_files_from_list_of_patterns',
            'get_files_by_drs',
            'list_ensembles',
            'select_files_by_datetimes',
            'select_directories_by_datetimes'
            ]

"""
Functions for finding data
"""

from . import logger
from . import drs_data
from . import ensembles_data


def expand_unix_patterns(patterns, regex=None):

    """
    Expand unix patterns into a list of file/directory patterns.

    Arguments:

        patterns (list[str]): The input list of patterns.

        regex (str): REGEX pattern. When given, the final list will be filtered
            according to the REGEX string. An example regex string is:
            "(?:_19[6-9]{1}[0-9]{1}|_20[0-9]{1}[0-9]{1})"

    Returns:

        list: List of file names.

    Example:

        For the example to run independently of an existing file system, a fake
        file system is created and the function is run within the fake file
        system.

        .. ipython::
           :okwarning:

           In [0]: import pyku.find as find
              ...: from pyfakefs.fake_filesystem_unittest import Patcher
              ...:
              ...: with Patcher() as patcher:
              ...:
              ...:     # Create list of fake files on fake filesystem
              ...:     # --------------------------------------------
              ...:
              ...:     fake_files = [
              ...:         '/fakedisk/tas/day/grid/HYRAS-5km/\\
              ...: tas_HYRAS-5km_19800101_19801231.nc',
              ...:         '/fakedisk/tas/day/grid/HYRAS-5km/\\
              ...: tas_HYRAS-5km_19810101_19811231.nc',
              ...:         '/fakedisk/tas/day/grid/HYRAS-5km/\\
              ...: tas_HYRAS-5km_19820101_19821231.nc',
              ...:         '/fakedisk/tas/day/grid/HYRAS-5km/\\
              ...: tas_HYRAS-5km_19830101_19831231.nc',
              ...:         '/fakedisk/pr/day/grid/HYRAS-5km/\\
              ...: pr_HYRAS-5km_19800101_19801231.nc',
              ...:         '/fakedisk/pr/day/grid/HYRAS-5km/\\
              ...: pr_HYRAS-5km_19810101_19811231.nc',
              ...:         '/fakedisk/pr/day/grid/HYRAS-5km/\\
              ...: pr_HYRAS-5km_19820101_19821231.nc',
              ...:         '/fakedisk/pr/day/grid/HYRAS-5km/\\
              ...: pr_HYRAS-5km_19830101_19831231.nc',
              ...:     ]
              ...:
              ...:     for fake_file in fake_files:
              ...:         patcher.fs.create_file(fake_file)
              ...:
              ...:     # Run function
              ...:     # ------------
              ...:
              ...:     files = find.expand_unix_patterns([
              ...:         '/fakedisk/{tas,pr}/day/grid/HYRAS-5km/\\
              ...: *_HYRAS-5km_????????_????????.nc',
              ...:     ])
              ...:
              ...: files

    """

    import re
    from braceexpand import braceexpand
    import itertools
    from glob import glob

    if isinstance(patterns, str) and not isinstance(patterns, list):
        raise Exception("pattern is a string and not a list!")

    if isinstance(patterns, str) and not isinstance(patterns, list):
        raise Exception("pattern is not a list!")

    # Loop over all patterns in list of patterns and perfrom brace expansion
    # ----------------------------------------------------------------------

    # The ``glob`` library does not implement bash brace expension
    # functionality which is why the function is needed.

    patterns_brace_expanded = list(itertools.chain.from_iterable(
        braceexpand(pattern)
        for pattern in patterns
    ))

    # Loop over all patterns and get list of files
    # --------------------------------------------

    files = list(itertools.chain.from_iterable(
        glob(pattern) for pattern in patterns_brace_expanded
    ))

    # Filter based on regex
    # ---------------------

    if regex is not None:

        tmp_list = []
        for f in files:
            if re.search(regex, f) is not None:
                tmp_list.append(f)

        files = tmp_list

    if len(files) == 0:
        logger.warning(f"Did not find any files for the following patterns: {', '.join(patterns)}")  # noqa

    return files


def get_files_from_list_of_patterns(patterns, regex=None):

    """
    Expand all patterns in a list of patterns.

    Arguments:

        patterns (list(str)): The input list of patterns.

        regex (str):
            REGEX pattern. When given, the final list will be filtered
            according to the REGEX string. An example regex string is:
            "(?:_19[6-9]{1}[0-9]{1}|_20[0-9]{1}[0-9]{1})"

    Returns:
        list: List expanded patterns

    Example:

        For the example to run independently of an existing file system, a fake
        file system is created and the function is run within the fake file
        system.

        .. ipython::
           :okwarning:

           In [0]: import pyku.find as find
              ...: from pyfakefs.fake_filesystem_unittest import Patcher
              ...:
              ...: with Patcher() as patcher:
              ...:
              ...:     # Create list of fake files on fake filesystem
              ...:     # --------------------------------------------
              ...:
              ...:     fake_files = [
              ...:         '/fakedisk/tas/day/grid/HYRAS-5km/\\
              ...: tas_HYRAS-5km_19800101_19801231.nc',
              ...:         '/fakedisk/tas/day/grid/HYRAS-5km/\\
              ...: tas_HYRAS-5km_19810101_19811231.nc',
              ...:         '/fakedisk/tas/day/grid/HYRAS-5km/\\
              ...: tas_HYRAS-5km_19820101_19821231.nc',
              ...:         '/fakedisk/tas/day/grid/HYRAS-5km/\\
              ...: tas_HYRAS-5km_19830101_19831231.nc',
              ...:         '/fakedisk/pr/day/grid/HYRAS-5km/\\
              ...: pr_HYRAS-5km_19800101_19801231.nc',
              ...:         '/fakedisk/pr/day/grid/HYRAS-5km/\\
              ...: pr_HYRAS-5km_19810101_19811231.nc',
              ...:         '/fakedisk/pr/day/grid/HYRAS-5km/\\
              ...: pr_HYRAS-5km_19820101_19821231.nc',
              ...:         '/fakedisk/pr/day/grid/HYRAS-5km/\\
              ...: pr_HYRAS-5km_19830101_19831231.nc',
              ...:     ]
              ...:
              ...:     for fake_file in fake_files:
              ...:         patcher.fs.create_file(fake_file)
              ...:
              ...:     # Run function
              ...:     # ------------
              ...:
              ...:     files = find.get_files_from_list_of_patterns([
              ...:         '/fakedisk/{tas,pr}/day/grid/HYRAS-5km/\\
              ...: *_HYRAS-5km_????????_????????.nc',
              ...:     ])
              ...:
              ...: files
    """

    return expand_unix_patterns(patterns=patterns, regex=regex)


def get_files_by_drs(standard, parent_dir=None,
                     version=None, file_suffix='.nc',
                     **kwargs):

    """
    Get list of files from DRS

    Arguments:
        standard (str): The CMOR standard of the files. in the dataframe. To
            get the list of available standards defined in *pyku*, see
            :func:`pyku.drs.list_drs_standards()`
        parent_dir (str): Parent directory where the DRS structure is found.
        version (str): An optional version string. If provided, it will be
            used to create an additional directory between the CMOR path
            and the CMOR filename. While not CMOR-compliant, this is used
            for the ESGF.
        file_suffix (str): The file extension (default: ".nc")
        **kwargs (dict): Keyword arguments corresponding to the expected DRS
            parameters. The required parameters are extracted from the
            standard’s `stem_pattern` and `parent_pattern`.

    Returns:
        list: List of files
    """

    import re
    from pathlib import Path

    # Raise exception if the standard is not defined
    # ----------------------------------------------

    if standard not in list(drs_data.get('standards').keys()):
        message = f"standard {standard} not defined"
        raise Exception(message)

    # Get the current standard stem and parent patterns
    # -------------------------------------------------

    parent_pattern = \
        drs_data.get('standards').get(standard).get('parent_pattern')
    stem_pattern = \
        drs_data.get('standards').get(standard).get('stem_pattern')

    # Raise exception if parent_dir does not exist
    # --------------------------------------------

    if parent_dir:
        if not Path(parent_dir).exists():
            message = f"parent_dir: {parent_dir} does not exist!"
            raise Exception(message)

    # Get available keywords from patterns
    parent_keys = re.findall(r"\{(.*?)\}", parent_pattern)
    stem_keys = re.findall(r"\{(.*?)\}", stem_pattern)

    # Combine required keys
    required_keys = set(parent_keys + stem_keys)

    # Check for invalid kwargs
    invalid_keys = set(kwargs.keys()) - required_keys
    if invalid_keys:
        raise ValueError(f"Invalid keyword arguments: {invalid_keys}. Expected: {required_keys}")  # noqa

    # Fill missing kwargs with "*"
    filled_kwargs = {key: kwargs.get(key, "*") for key in required_keys}
    logger.debug(f"The following facets have been set: {filled_kwargs}")

    # Format list entries in order to expand with curly braced strings
    def format_for_curly_braces(kwargs):
        formatted = {}
        for key, value in kwargs.items():
            if isinstance(value, list):
                if len(value) == 1:
                    formatted[key] = value[0]
                else:
                    formatted[key] = '{' + ','.join(map(str, value)) + '}'
            else:
                formatted[key] = value
        return formatted

    filled_kwargs = format_for_curly_braces(filled_kwargs)

    # Format list entries in order to expand with curly braced strings
    def format_for_curly_braces(kwargs):
        formatted = {}
        for key, value in kwargs.items():
            if isinstance(value, list):
                if len(value) == 1:
                    formatted[key] = value[0]
                else:
                    formatted[key] = '{' + ','.join(map(str, value)) + '}'
            else:
                formatted[key] = value
        return formatted

    filled_kwargs = format_for_curly_braces(filled_kwargs)

    # Construct the paths by replacing placeholders
    parent = parent_pattern.format(**filled_kwargs)
    stem = stem_pattern.format(**filled_kwargs)

    # Ensure parent_dir exists
    if parent_dir:
        parent_path = Path(parent_dir) / parent
    else:
        parent_path = Path(parent)

    # Add version as a subdirectory
    if version:
        parent_path = parent_path / version

    # Combine parent_path and stem to retrieve all files
    patterns = f"{parent_path}/{stem}{file_suffix}"

    return expand_unix_patterns(patterns=[patterns])


def expand_unix_directory_patterns(patterns, regex=None):

    """
    Get list of directories from list of patterns

    Arguments:
        patterns (list[str]): The list of patterns.
        regex (str):
            REGEX pattern. When given, the final list will be filtered
            according to the REGEX string. An example regex string is:
            "(?:_19[6-9]{1}[0-9]{1}|_20[0-9]{1}[0-9]{1})"

    Returns:
        list: List of directory names

    Example:

        For the example to run independently of an existing file system, a fake
        file system is created and the function is run within the fake file
        system.

        .. ipython::
           :okwarning:

           In [0]: import pyku.find as find
              ...: from pyfakefs.fake_filesystem_unittest import Patcher
              ...:
              ...: with Patcher() as patcher:
              ...:
              ...:     # Create list of fake files on fake filesystem
              ...:     # --------------------------------------------
              ...:
              ...:     fake_files = [
              ...:         '/fakedisk/tas/day/grid/HYRAS-5km/\\
              ...: tas_HYRAS-5km_19800101_19801231.nc',
              ...:         '/fakedisk/tas/day/grid/HYRAS-5km/\\
              ...: tas_HYRAS-5km_19810101_19811231.nc',
              ...:         '/fakedisk/tas/day/grid/HYRAS-5km/\\
              ...: tas_HYRAS-5km_19820101_19821231.nc',
              ...:         '/fakedisk/tas/day/grid/HYRAS-5km/\\
              ...: tas_HYRAS-5km_19830101_19831231.nc',
              ...:         '/fakedisk/pr/day/grid/HYRAS-5km/\\
              ...: pr_HYRAS-5km_19800101_19801231.nc',
              ...:         '/fakedisk/pr/day/grid/HYRAS-5km/\\
              ...: pr_HYRAS-5km_19810101_19811231.nc',
              ...:         '/fakedisk/pr/day/grid/HYRAS-5km/\\
              ...: pr_HYRAS-5km_19820101_19821231.nc',
              ...:         '/fakedisk/pr/day/grid/HYRAS-5km/\\
              ...: pr_HYRAS-5km_19830101_19831231.nc',
              ...:     ]
              ...:
              ...:     for fake_file in fake_files:
              ...:         patcher.fs.create_file(fake_file)
              ...:
              ...:     # Run function
              ...:     # ------------
              ...:
              ...:     files = find.expand_unix_directory_patterns([
              ...:         '/fakedisk/{tas,pr}/day/grid/HYRAS-5km/\\
              ...: *_HYRAS-5km_????????_????????.nc',
              ...:     ])
              ...:
              ...: files

    """

    # The function is exactly the same as for finding files from a list of
    # patterns. However for clarity the distinction is made.

    from pathlib import Path

    # Sanity checks
    # -------------

    if isinstance(patterns, str) and not isinstance(patterns, list):
        raise Exception("pattern is a string and not a list!")

    if isinstance(patterns, str) and not isinstance(patterns, list):
        raise Exception("pattern is not a list!")

    # Prepare empty list where to gather expanded patterns
    # ----------------------------------------------------

    expanded = []

    # Loop over each file patterns
    # ----------------------------

    for pattern in patterns:

        # Split into directory pattern and file pattern
        # ---------------------------------------------

        directory_pattern = str(Path(pattern).parent)
        file_pattern = str(Path(pattern).name)

        # Expand directory pattern
        # ------------------------

        expanded_directories = expand_unix_patterns(
            patterns=[directory_pattern], regex=regex
        )

        # Add back file pattern to each expanded directories
        # --------------------------------------------------

        for directory in expanded_directories:
            expanded.append(
                str(Path(directory) / Path(file_pattern))
            )

    return sorted(expanded)


def select_files_by_datetimes(
    list_of_files, min_date=None, max_date=None, exclude_min=False,
    exclude_max=False, offset=None
):
    """
    Select files with that contains any data in the min_date/max_date range.
    The purpose of this function is to effectively filter files that do not
    contain the datetimes required in an analysis.

    Arguments:

        list_of_files (List[str]): The input list of files.

        min_date (str, datetime.datetime): The minimal date.

        max_date (str, datetime.datetime): The maximal date.

        exclude_min (str, optional): Whether to exclude the minimal date.
            Defaults to False.

        exclude_max (str, optional): Whether to exclude the maximal date.
            Defaults to False.

        offset (str, optional): Whether to apply an offset. The format of the
            string is taken from :func:`pandas.to_timedelta`. For example,
            ``-15 minutes`` can be passed, or ``1 day 15 minutes 3 seconds``.
            This is needed because for example the COSMO-CLM data have the time
            labels set to the upper time bounds. For exampled the data with
            filename lffd20220201000500.nc have a time label of
            ``2022-02-01T00:05:00``, a lower time bound of
            ``2022-02-01T00:00:00``, and an upper time bound of
            ``2022-02-01T00:05:00``.

    Returns:
        List[str]: List of selected files

    Example:

        For the testing and documenting this function, a temporary directory as
        well as temporary data are generated. The function is run on those fake
        files.

        .. ipython::
           :okwarning:

           In [0]: import tempfile
              ...: from pprint import pprint
              ...: import pyku.resources as resources
              ...: import pyku.find as find
              ...:
              ...: with tempfile.TemporaryDirectory() as temp_dir:
              ...:
              ...:     # Generate fake datatsets in temporary directory
              ...:     # ----------------------------------------------
              ...:
              ...:     input_files = (
              ...:         resources.
              ...:         generate_fake_datasets_with_datetimes_on_disk(temp_dir)
              ...:     )
              ...:
              ...:     print("Input files")
              ...:     pprint(input_files)
              ...:
              ...:     # Select files by datetime and print result
              ...:     # -----------------------------------------
              ...:
              ...:     output_files = find.select_files_by_datetimes(
              ...:         input_files,
              ...:         min_date='1988-02-01',
              ...:         max_date='1988-04-01',
              ...:         exclude_max=True
              ...:     )
              ...:
              ...:     print("Output files:")
              ...:     pprint(output_files)
    """ # noqa

    import warnings
    import cftime
    import pandas as pd
    import numpy.ma as ma
    # import dask
    # from dask import delayed
    import time

    # Note that here I removed the calls to dasked delayed as this was
    # resulting in errors. This is kept at the moment and maybe will be
    # turned back on in the future.

    if offset is not None:
        offset_in_seconds = pd.to_timedelta(offset).total_seconds()
    else:
        offset_in_seconds = 0

    # @delayed
    def file_has_datetimes(
        file, min_date=None, max_date=None, exclude_min=False,
        exclude_max=False
    ):

        from netCDF4 import Dataset, num2date

        try:

            with Dataset(file, 'r') as nc:
                times = nc.variables['time'][:]
                time_units = nc.variables['time'].units

        except Exception as e:

            # Very confused about why this would be needed. See issue:
            # https://gitlab.dwd.de/ku/libraries/pyku/-/issues/51

            warnings.warn(f"Could not read, trying again: {file}, {e}")
            time.sleep(0.5)

            with Dataset(file, 'r') as nc:
                times = nc.variables['time'][:]
                time_units = nc.variables['time'].units

        # Apply offset
        # ------------

        times = times + offset_in_seconds

        # Get min and max datetime in file. Convert to date
        # -------------------------------------------------

        first_time = ma.min(times)
        last_time = ma.max(times)

        # The times are read as unix timestamps, which are in seconds
        # -----------------------------------------------------------

        first_time = num2date(first_time, time_units)
        last_time = num2date(last_time, time_units)

        # Sanity check
        # ------------

        # Some cftime calendars are commented out because using num2date I
        # think result in a cftime calendar.

        if isinstance(first_time, cftime.datetime):

            is_weird_calendar = first_time.calendar in [
                '360_day',
                '365_day',
                '366_day',
                'all_leap',
                'noleap',
                # 'standard',
                # 'gregorian',
                # 'proleptic_gregorian',
                # 'julian',
            ]

            if is_weird_calendar:
                logger.warn("cftime implementation needs testing")

        # Convert to pandas Timestamp
        # ---------------------------

        earliest_date = pd.to_datetime(first_time.isoformat())
        latest_date = pd.to_datetime(last_time.isoformat())

        # Convert datetime to Pandas datetime
        # -----------------------------------

        if min_date is not None:
            min_datetime = pd.to_datetime(min_date)
        else:
            min_datetime = earliest_date

        if max_date is not None:
            max_datetime = pd.to_datetime(max_date)
        else:
            max_datetime = latest_date

        # If the datetimes have no time zone information, assume UTC
        # ----------------------------------------------------------

        if min_datetime.tz is None:
            min_datetime = min_datetime.tz_localize('UTC')

        if max_datetime.tz is None:
            max_datetime = max_datetime.tz_localize('UTC')

        if earliest_date.tz is None:
            earliest_date = earliest_date.tz_localize('UTC')

        if latest_date.tz is None:
            latest_date = latest_date.tz_localize('UTC')

        # Check if any datetime falls within the range
        # --------------------------------------------

        if exclude_min is False and exclude_max is False:
            any_within_range = (earliest_date <= max_datetime) and \
                               (latest_date >= min_datetime)

        elif exclude_min is True and exclude_max is False:
            any_within_range = (earliest_date <= max_datetime) and \
                               (latest_date > min_datetime)

        elif exclude_min is False and exclude_max is True:
            any_within_range = (earliest_date < max_datetime) and \
                               (latest_date >= min_datetime)

        else:
            any_within_range = (earliest_date < max_datetime) and \
                               (latest_date > min_datetime)

        if any_within_range:
            return file

    delayed_results = [
        file_has_datetimes(
            file, min_date=min_date, max_date=max_date,
            exclude_min=exclude_min, exclude_max=exclude_max
        )
        for file in list_of_files
    ]

    output_files = delayed_results

    # computed_results = dask.compute(
    #     *delayed_results,
    #     scheduler='single-threaded',
    # )
    # output_files = [item for item in computed_results if item is not None]

    # Remove None for output files
    # ----------------------------

    output_files = [item for item in output_files if item is not None]

    if len(output_files) == 0:
        message = "No files found in select_files_by_datetimes"
        warnings.warn(message)

    return sorted(output_files)


def guess_time_in_string(input_string):

    """
    Guess the time from the name of a directory

    Arguments:
        input_string (str): The input string.

    Returns:
        :class:`pandas.Timestamp`: The time guessed from the string.

    Example:

        For the example to run independently of an existing file system, a fake
        file system is created and the function is run within the fake file
        system.

        .. ipython::
           :okwarning:

           In [0]: import pyku.find as find
              ...: from pyfakefs.fake_filesystem_unittest import Patcher
              ...:
              ...: with Patcher() as patcher:
              ...:
              ...:     # Create directory on fake filesystem
              ...:     # -----------------------------------
              ...:
              ...:     patcher.fs.create_dir('/CLMcom-DWD/ECMWF-ERA5/\\
              ...: evaluation/r1i1p1/CLMcom-DWD-CCLM5-0-16/x0n1-v1/1hr/\\
              ...: tas/v20221116')
              ...:
              ...:     # Run function
              ...:     # ------------
              ...:     guessed_time = find.guess_time_in_string(
              ...:         '/CLMcom-DWD/ECMWF-ERA5/evaluation/r1i1p1/\\
              ...: CLMcom-DWD-CCLM5-0-16/x0n1-v1/1hr/tas/v20221116')
              ...:
              ...: guessed_time

    """

    from datetime import datetime
    import pandas as pd
    import re

    # The strategy of this function is to define possible time format as well
    # as possible datetime strings found with a regex. The possible datetime
    # strings are then checked against all possible format. If a match is found
    # the guessed datetime is returned.

    possible_formats = [
        '%Y%m%d%H%M',
        '%Y%m%d%H',
        '%Y%m%d',
        '%Y%m',
        '%Y_%m_%d',
        '%Y_%m',
        '%Y'
    ]

    possible_datetime_strings = [
        re.findall(r'\d{4}\d{2}\d{2}\d{2}\d{2}', input_string),
        re.findall(r'\d{4}\d{2}\d{2}\d{2}', input_string),
        re.findall(r'\d{4}\d{2}\d{2}', input_string),
        re.findall(r'\d{4}\d{2}', input_string),
        re.findall(r'\d{4}_\d{1,2}_\d{1,2}', input_string),
        re.findall(r'\d{4}_\d{1,2}', input_string),
        re.findall(r'\d{4}\d{2}', input_string),
        re.findall(r'\d{4}', input_string),
    ]

    for possible_datetime_string in possible_datetime_strings:

        if len(possible_datetime_string) > 1:
            message = \
                f"More that one possible date found {possible_datetime_string}"
            raise Exception(message)

        if len(possible_datetime_string) > 0:
            identified_datetime_string = possible_datetime_string[0]

            for date_format in possible_formats:
                try:

                    # Guess time given a string and format
                    # ------------------------------------

                    guessed_time = datetime.strptime(
                        identified_datetime_string,
                        date_format
                    )

                    # The issue solved with the following code is that strptime
                    # is not able to check if the values in the string are
                    # zero-padded. Hence the guessed datetime datetime is
                    # converted back to a string and compared to the original
                    # string. This should be the same. If not, it means the
                    # format of the string does not correspond to the expected
                    # format.

                    guessed_datetime_string = \
                        guessed_time.strftime(date_format)

                    if identified_datetime_string != guessed_datetime_string:
                        raise ValueError("Not zero-padded")

                    # Convert to pandas Timestamp and return
                    # --------------------------------------

                    guessed_time = pd.to_datetime(guessed_time)

                    return guessed_time

                except ValueError:
                    pass

    return None


def select_directories_by_datetimes(
    list_of_directories, min_date=None, max_date=None, exclude_min=False,
    exclude_max=False
):
    """
    Select directories by datetimes. The datetime is guessed from the directory
    name. The purpose of this function is to effectively filter directories
    that do not contain the datetimes required in an analysis.

    Arguments:
        list_of_directories (List[str]): The input list of files or
            directories.
        min_date (str, datetime.datetime): Optional. The minimal date. Defaults
            to :attr:`pandas.Timestamp.min`.
        max_date (str, datetime.datetime): Optional. The maximal date. Default
            to :attr:`pandas.Timestamp.max`.
        exclude_min (str, optional): Optional. Whether to exclude the minimal
            date. Defaults to False.
        exclude_max (str, optional): Optional. Whether to exclude the maximal
            date. Defaults to False.

    Returns:
        List[str]: List of selected files.

    Example:

        For the example to run independently of an existing file system, a fake
        file system is created and the function is run within the fake file
        system.

        .. ipython::
           :okwarning:

           In [0]: import pyku.find as find
              ...: from pyfakefs.fake_filesystem_unittest import Patcher
              ...:
              ...: # Create a fake filesystem to run example
              ...: # ---------------------------------------
              ...:
              ...: with Patcher() as patcher:
              ...:
              ...:     # The list of input directories
              ...:     # -----------------------------
              ...:
              ...:     list_of_directories = [
              ...:         '/kp/kpxx/integra/data4dwd/projectdata/seasonalfc/\\
              ...: hindcasts/DWD/GCFS1/seas198801',
              ...:         '/kp/kpxx/integra/data4dwd/projectdata/seasonalfc/\\
              ...: hindcasts/DWD/GCFS1/seas198802',
              ...:         '/kp/kpxx/integra/data4dwd/projectdata/seasonalfc/\\
              ...: hindcasts/DWD/GCFS1/seas198803',
              ...:         '/kp/kpxx/integra/data4dwd/projectdata/seasonalfc/\\
              ...: hindcasts/DWD/GCFS1/seas198804',
              ...:         '/kp/kpxx/integra/data4dwd/projectdata/seasonalfc/\\
              ...: hindcasts/DWD/GCFS1/seas198805',
              ...:     ]
              ...:
              ...:     # Create the input directories on the fake filesystem
              ...:     # ---------------------------------------------------
              ...:
              ...:     for directory in list_of_directories:
              ...:         patcher.fs.create_dir(directory)
              ...:
              ...:     # Run function within the fake filesystem
              ...:     # ---------------------------------------
              ...:
              ...:     output_directories = find.select_directories_by_datetimes(
              ...:         list_of_directories,
              ...:         min_date='1988-02-01',
              ...:         max_date='1988-04-01',
              ...:         exclude_max=True
              ...:     )
              ...:
              ...: output_directories

    """  # noqa

    import warnings
    import pandas as pd
    from pathlib import Path

    # Set the minimal and maximal datetimes
    # -------------------------------------

    if min_date is not None:
        min_datetime = pd.to_datetime(min_date)
    else:
        min_datetime = pd.Timestamp.min

    if max_date is not None:
        max_datetime = pd.to_datetime(max_date)
    else:
        max_datetime = pd.Timestamp.max

    # Assume UTC if time zone not given
    # ---------------------------------

    if min_datetime.tz is None:
        min_datetime = min_datetime.tz_localize('UTC')

    if max_datetime.tz is None:
        max_datetime = max_datetime.tz_localize('UTC')

    # Prepare a list of output directories
    # ------------------------------------

    output_directories = []

    # List all directories and add to list if it falls within range
    # -------------------------------------------------------------

    for directory in list_of_directories:

        # Guess datetime from directory name
        # ----------------------------------

        # Here I gues it could be done nicer. But a directory also has a
        # parent. So idk how to nicely get the directory if it is a directory
        # and the directory, if it is a file.

        if not Path(directory).suffix in ['']:
            file_pattern = Path(directory).name
            directory = Path(directory).parent
        else:
            file_pattern = None

        if not Path(directory).exists():
            message = f"{directory} does not exist"
            raise Exception(message)

        if Path(directory).is_dir():
            directory_datetime = guess_time_in_string(str(Path(directory)))

        else:
            directory_datetime = guess_time_in_string(
                str(Path(directory).parent)
            )

        # Assume UTC if the datetime is not localized
        # -------------------------------------------

        if directory_datetime.tz is None:
            directory_datetime = directory_datetime.tz_localize('UTC')

        # Skip if the directory contains no datetime
        # ------------------------------------------

        if directory_datetime is None:
            continue

        # Check if any datetime falls within the range
        # --------------------------------------------

        if exclude_min is False and exclude_max is False:
            is_in_range = (directory_datetime <= max_datetime) and \
                          (directory_datetime >= min_datetime)

        elif exclude_min is True and exclude_max is False:
            is_in_range = (directory_datetime <= max_datetime) and \
                          (directory_datetime > min_datetime)

        elif exclude_min is False and exclude_max is True:
            is_in_range = (directory_datetime < max_datetime) and \
                          (directory_datetime >= min_datetime)

        else:
            is_in_range = (directory_datetime < max_datetime) and \
                          (directory_datetime > min_datetime)

        # Re-add the file pattern
        # -----------------------

        if file_pattern is not None:
            directory = Path(directory) / file_pattern

        # Add to list if it falls within range
        # ------------------------------------

        if is_in_range:
            output_directories.append(str(directory))

    # Send a warning if no directories were found
    # -------------------------------------------

    if len(output_directories) == 0:
        message = "No files found in select_files_by_datetimes"
        warnings.warn(message)

    return sorted(output_directories)


def get_file_dataframe(files, standard='cordex'):
    """
    Build cordex dataframe from list of files. The dataframe contains the
    standard facets determined from the file directory and name. This permits
    to efficiently select files.

    Arguments:
        files (list): List of files

    Returns:
        :class:`pandas.DataFrame`: The output dataframe.

    Example:

        For the example to run independently of an existing file system, a fake
        file system is created and the function is run within the fake file
        system.

        .. ipython::
           :okwarning:

           In [0]: import pyku.find as find
              ...: from pyfakefs.fake_filesystem_unittest import Patcher
              ...:
              ...: # Create a fake filesystem to run example
              ...: # ---------------------------------------
              ...:
              ...: with Patcher() as patcher:
              ...:
              ...:     # Create fake files on fake filesystem
              ...:     # ------------------------------------
              ...:
              ...:     fake_files = [
              ...:         '/fakedisk/DWD-CPS/output/GER-0275/CLMcom-DWD/\\
              ...: ECMWF-ERA5/evaluation/r1i1p1/CLMcom-DWD-CCLM5-0-16/\\
              ...: x0n1-v1/1hr/tas/v20221116/tas_GER-0275_ECMWF-ERA5_\\
              ...: evaluation_r1i1p1_CLMcom-DWD-CCLM5-0-16_x0n1-v1_\\
              ...: 1hr_202001010000-202012312300.nc',
              ...:         '/fakedisk/DWD-CPS/output/GER-0275/CLMcom-DWD/\\
              ...: ECMWF-ERA5/evaluation/r1i1p1/CLMcom-DWD-CCLM5-0-16/\\
              ...: x0n1-v1/1hr/tas/v20221116/tas_GER-0275_ECMWF-ERA5_\\
              ...: evaluation_r1i1p1_CLMcom-DWD-CCLM5-0-16_x0n1-v1_1hr_\\
              ...: 202101010000-202112312300.nc',
              ...:         '/fakedisk/DWD-CPS/output/GER-0275/CLMcom-DWD/\\
              ...: ECMWF-ERA5/evaluation/r1i1p1/CLMcom-DWD-CCLM5-0-16/\\
              ...: x0n1-v1/day/pr/v20230630/pr_GER-0275_ECMWF-ERA5_\\
              ...: evaluation_r1i1p1_CLMcom-DWD-CCLM5-0-16_x0n1-v1_day_\\
              ...: 20220101-20221231.nc'
              ...:     ]
              ...:
              ...:     for fake_file in fake_files:
              ...:         patcher.fs.create_file(fake_file)
              ...:
              ...:     df = find.get_file_dataframe(
              ...:         fake_files, standard='cordex'
              ...:     )
              ...:
              ...: # Show the data
              ...: # -------------
              ...:
              ...: df.head()

        With that the following facets are available in the dataframe:

        .. ipython::
           :okwarning:

           In [0]: df.columns

        A query can be run:

        .. ipython::
           :okwarning:

           In [0]: df.query("variable_name == 'pr'")

        And the files returned:

        .. ipython::
           :okwarning:

           In [0]: df.query("variable_name == 'pr'").file.values
    """

    import pandas as pd
    import parse
    import re
    from pathlib import Path

    # Sanity check
    # ------------

    if isinstance(files, str) and not isinstance(files, list):
        raise TypeError("Input is a string and not a list!")

    if isinstance(files, str) and not isinstance(files, list):
        raise TypeError("Input is not a list!")

    # Get string for the case we have PosixPath objects
    # -------------------------------------------------

    files = [str(file) for file in files]

    # Filters
    # -------

    files = [file for file in files if 'r0i0p0' not in file]
    files = [file for file in files if '/fx/' not in file]

    # If patterns are given, generate a list of files from the patterns
    # -----------------------------------------------------------------

    files = get_files_from_list_of_patterns(files)

    # Raise exception if the standard is not defined
    # ----------------------------------------------

    if standard not in list(drs_data.get('standards').keys()):
        message = f"standard {standard} not defined"
        raise Exception(message)

    # Create a simple function to generate keys from file name and pattern
    # --------------------------------------------------------------------

    # Marker here I am working on a function get_facets_from_file_name in the
    # drs library, which maybe may be reused here and simplify the code.

    def extract_variables_from_filename(filename, pattern):

        result = parse.parse(pattern, filename)

        if result:
            return result.named

        else:
            message = f"Could not read file pattern for {filename}"
            raise Exception(message)

    # Get the current standard
    # ------------------------

    stem_pattern = drs_data.get('standards').get(standard).get('stem_pattern')

    # Filter files that do not match the pattern
    # ------------------------------------------

    # In this sanity check, the files that do not match the pattern are
    # filtered out. Indeed, it can happen that random files are located in the
    # search directory.

    filtered_files = []

    for file in files:

        result = parse.parse(stem_pattern, Path(file).stem)

        if result:
            filtered_files.append(file)
        else:
            message = f"Cannot read pattern from {file}. Skipping."
            logger.warn(message)

    files = filtered_files

    # Get the keys from the file pattern
    # ----------------------------------

    stem_keys = re.findall(r'\{(\w+)\}', stem_pattern)

    # Construct dataframe of filename
    # -------------------------------

    df = pd.DataFrame(files, columns=['file'])

    filenames = df['file'].tolist()
    stems = [Path(filename).stem for filename in filenames]

    for key in stem_keys:

        # This certainly can be optimized
        df[key] = [
            extract_variables_from_filename(stem, stem_pattern)[key]
            for stem in stems
        ]

    # Add pandas Timestamp
    # --------------------

    if 'start_time' in df:
        df['start_timestamp'] = df['start_time'].apply(guess_time_in_string)

    if 'end_time' in df:
        df['end_timestamp'] = df['end_time'].apply(guess_time_in_string)

    return df


def search_dataframe(df, search_dict):

    """
    Search dataframe by model keys

    Returns:
        :class:`pandas.DataFrame`: The output pandas dataframe.
    """

    import pandas as pd

    # Initialize a boolean mask with all True values
    mask = pd.Series([True] * len(df), index=df.index)

    # Iterate over dictionary items and update the mask based on matches
    for col, val in search_dict.items():
        mask = mask & (df[col] == val)

    # Apply the mask to the DataFrame
    filtered_df = df[mask]

    # Display the filtered DataFrame
    return filtered_df


def get_ensemble_definition(ensemble):

    """
    Get a pandas dataframe of all facets of ensemble.

    Arguments:

        ensemble (str): Ensemble identifier (e.g. 'cmip5_dwd_core'). You can
        obtain the list of ensembles available with ``pyku.list_ensembles()``.

    Returns:
        :class:`pandas.DataFrame`: Dataframe of core ensemble facets.

    Example:

        .. ipython::
           :okwarning:

           In [0]: import pyku.find as find
              ...: find.get_ensemble_definition('dwd_cmip5_core')
    """

    import pandas as pd

    # Get data from yaml file
    # -----------------------

    data = ensembles_data.get(ensemble)

    # Construct dataframe
    # -------------------

    df = pd.DataFrame(data)

    return df


def select_ensemble(df, ensemble_name=None, standard=None):

    """
    Select ensemble members from file dataframe.

    .. tip:

        This function may take a few minutes to run on a large amount of files.
        For example, with 100000 cordex files, the function takes of the order
        of 2 minutes to run.

    Arguments:

        df (:class:`pandas.Dataframe`): The input dataframe. This dataframe
            contains the list of all files and their facets. Tise dataframe
            given as an input is expected to have been built using the function
            :func:`pyku.find.get_file_dataframe`.

        ensemble_name (str): Name of the ensemble as defined in *pyku*. To get
            the full list of ensembles defined in *pyku*, you can use
            :func:`pyku.find.list_ensembles()`. For example, you can select the
            DWD CMIP5 core ensemble using the name 'cmip5_dwd_core_ensemble'.

        standard (str): The CMOR standard of the files. in the dataframe. To
            get the list of available standards defined in *pyku*, see
            :func:`pyku.drs.list_drs_standards()`

    Returns:
        :class:`pandas.Dataframe`: The dataframe with selected ensemble.

    Note:
        It should be possible to automate the detection of the standard, but
        this is not built in at the moment and the standard shall be passed.
    """

    logger.warning("This function is experimental and the API may change")

    import pandas as pd
    import pyku.drs as drs

    # Sanity checks
    # -------------

    assert df is not None, 'df is a mandatory argument'

    assert standard in drs.list_drs_standards(), (
        f"standard {standard} not defined. Available standards are "
        f"{drs.list_drs_standards()}"
    )

    assert ensemble_name in list_ensembles(), (
        f"{ensemble_name} not defined. Available ensembles are "
        f"{list_ensembles()}"
    )

    # Get the DWD core ensemble
    # -------------------------

    ensemble_definition = get_ensemble_definition(ensemble_name)

    # Select all files which belong to the core ensemble
    # --------------------------------------------------

    list_of_files = [
        search_dataframe(df, search_dict=member.to_dict())
        for idx, member in ensemble_definition.iterrows()
    ]

    # Sanity check
    # ------------

    assert len(list_of_files) > 0, \
        f'No {ensemble_name} files found in dataframe'

    # Merge all single dataframes
    # ---------------------------

    ensemble = pd.concat(list_of_files)

    return ensemble


def list_ensembles():

    """
    Show all named ensembles

    Returns:
        dict: Dictionary of availabe ensembes

    Example:

        To list all named ensembles defined in pyku:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...: pyku.list_ensembles()
    """

    return list(ensembles_data.keys())
