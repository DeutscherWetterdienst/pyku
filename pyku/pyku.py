#!/usr/bin/env python3

"""
pyku command line utilities
"""

import argparse

from pyku import __version__


def read_parameters():
    """
    Determine the parameters given in the command line
    """

    parser = argparse.ArgumentParser()
    subparser = parser.add_subparsers(dest='command')

    parser.add_argument(
        '--version',
        '-v',
        action='store_true',
        default=False,
        dest='version',
        help='Print version'
    )

    # Add subparsers
    # --------------

    resample_datetimes_subparser(subparser=subparser)
    select_files_subparser(subparser=subparser)
    select_directories_subparser(subparser=subparser)
    check_subparser(subparser=subparser)
    cmorize_subparser(subparser=subparser)

    # Read arguments into a dictionary
    # --------------------------------

    params = vars(parser.parse_args())

    if params.get('version') is True:
        print(f"{__version__}")

    return params


def main():

    """
    Main
    """

    params = read_parameters()

    if params.get('command') in ['resample-datetimes']:
        resample_datetimes_run(params=read_parameters())

    if params.get('command') in ['select-files']:
        select_files_run(params=read_parameters())

    if params.get('command') in ['select-directories']:
        select_directories_run(params=read_parameters())

    if params.get('command') in ['check']:
        check_run(params=read_parameters())

    if params.get('command') in ['cmorize']:
        cmorize_run(params=read_parameters())


def resample_datetimes_subparser(subparser=None):

    """
    Add subparser for pyku resample-datetimes
    """

    parser = subparser.add_parser(
        'resample-datetimes',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Resample datetime",
        epilog=(
            "EXAMPLE\n"
            "pyku resample_datetimes file.nc --how sum --period 1H\n"
        )
    )

    # Add arguments
    # -------------

    parser.add_argument(
        '--period',
        action='store',
        dest='period',
        default='1D',
        required=True,
        help=(
            "Resampling period (e.g. 1D, 3H, 1D, 1Y, or Q). Full list:\n"
            "https://pandas.pydata.org/pandas-docs/stable/user_guide/"
            "timeseries.html#offset-aliases"
        )
    )

    parser.add_argument(
        '--how',
        action='store',
        dest='how',
        choices=['mean', 'max', 'min', 'sum'],
        default='mean',
        required=True,
        help='How to resample'
    )

    parser.add_argument(
        '--factor',
        action='store',
        dest='factor',
        default=None,
        type=float,
        required=False,
        help='Apply a correction factor to the dataset'
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        default=False,
        dest='verbose',
        help='Switch verbose mode on'
    )

    parser.add_argument(
        '--complete',
        action='store_true',
        default=False,
        dest='complete',
        help=(
            "When the complete option is set to True, any data that is only "
            "partially available within the resampling frequency will be "
            "excluded. For instance, if the data frequency is daily and the "
            "resampling frequency is monthly, any month with incomplete data "
            "will be removed from the dataset."
        )
    )

    parser.add_argument(
        '--overwrite',
        action='store_true',
        default=False,
        dest='overwrite',
        help='Overwrite output file if it exists'
    )

    parser.add_argument(
        'input_files',
        nargs='+',
        default='',
        # type=argparse.FileType('r'),
        help='Input file(s)'
    )

    parser.add_argument(
        '--output-file',
        '-o',
        action='store',
        dest='output_file',
        default=None,
        help='Output file'
    )


def resample_datetimes_run(params):

    """
    Resample datetimes

    Arguments:
        params: Dictionary of parameters
    """

    import os
    import sys
    import json
    import warnings
    from pathlib import Path
    import pyku  # noqa
    import xarray as xr

    # Construct output file name if not given
    # ---------------------------------------

    if params.get('output_file') is None:

        basename = os.path.basename(params.get('input_files')[0])
        stem = os.path.splitext(basename)[0]

        params['output_file'] = stem + '-resampled.nc'

    # Print parameters to screen in verbose mode
    # ------------------------------------------

    if params.get('verbose') is True:
        print(json.dumps(params, indent=2))

    # Or suppress warnings otherwise
    # ------------------------------

    else:
        warnings.filterwarnings("ignore")

    # Check if output file already exists
    # -----------------------------------

    if Path(params.get('output_file')).is_file():

        if params.get('overwrite') is True:
            print(f"Overwriting {params.get('output_file')}")
        else:
            message = f"""\
{params.get('output_file')} already exists. Doing nothing."""
            print(message)
            sys.exit()

    # Open data as an xarray
    # ----------------------

    ds = xr.open_mfdataset(
        params.get('input_files'),
        data_vars='different',
        chunks={'time': 50}
    )

    # Resample
    # --------

    ds = ds.pyku.resample_datetimes(
        how=params.get('how'),
        frequency=params.get('period'),
        complete=params.get('complete')
    )

    # Apply correction factor
    # -----------------------

    if params.get('factor') is not None:
        for varname in ds.pyku.get_geodata_varnames():
            ds[varname] = ds[varname]*params.get('factor')

    # Write to netcdf
    # ---------------

    ds.pyku.to_netcdf(params.get('output_file'))


def check_subparser(subparser=None):

    """
    Add parser for pyku check
    """

    parser = subparser.add_parser(
        'check',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Check",
        epilog="""\
EXAMPLE
    pyku check file.nc --verbose
"""
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        default=False,
        dest='verbose',
        help='Switch verbose mode on.'
    )

    parser.add_argument(
        '--semicolon-separated-csv',
        action='store_true',
        default=False,
        dest='semicolon_separated',
        help='Use a semicolon-separated CSV output (German standard).'
    )

    parser.add_argument(
        'input_files',
        nargs='+',
        default='',
        help='Input file(s)'
    )

    parser.add_argument(
        '--overwrite',
        action='store_true',
        default=False,
        dest='overwrite',
        help='Overwrite output file if it exists'
    )

    parser.add_argument(
        '--standard',
        action='store',
        dest='standard',
        default=None,
        help="\
Optional. Check CMOR DRS standard (e.g. `cordex`, `cordex_adjust`). The CMOR \
standard is not checked by default."
    )

    parser.add_argument(
        '--output-file',
        '-o',
        action='store',
        dest='output_file',
        default=None,
        help='Output file'
    )


def check_run(params):

    """
    Run checks

    Arguments:
        params: Dictionary of parameters
    """

    import os
    import sys
    import json
    import warnings
    from pathlib import Path
    import pyku  # noqa
    import xarray as xr
    import pandas as pd
    import pyku.check as libcheck
    import pyku.find
    from tqdm import tqdm

    # Print parameters to screen in verbose mode
    # ------------------------------------------

    if params.get('verbose') is True:
        print(json.dumps(params, indent=2))

    # Or suppress warnings otherwise
    # ------------------------------

    else:
        warnings.filterwarnings("ignore")

    # Check if output file already exists
    # -----------------------------------

    if params.get('output_file') is not None and \
       Path(params.get('output_file')).is_file():

        if params.get('overwrite') is True:
            print(f"Overwriting {params.get('output_file')}")
        else:
            message = f"""\
{params.get('output_file')} already exists. Doing nothing."""
            print(message)
            sys.exit()

    # Supress warnings when not in verbose mode
    # -----------------------------------------

    if not params.get('verbose'):
        warnings.filterwarnings("ignore")

    # Construct output file name if not given
    # ---------------------------------------

    if params.get('output_file') is None:
        params['output_file'] = "output.csv"

    # Check if output file already exists
    # -----------------------------------

    if Path(params.get('output_file')).is_file():

        if params.get('overwrite') is True:
            print(f"Overwriting {params.get('output_file')}")
        else:
            message = f"""\
{params.get('output_file')} already exists. Doing nothing"""
            print(message)
            sys.exit()

    # Print parameters to screen in verbose mode
    # ------------------------------------------

    if params.get('verbose') is True:
        print(json.dumps(params, indent=2))

    # Loop over all files
    # -------------------

    list_of_issues = []

    for f in tqdm(pyku.find.get_files_from_list_of_patterns(
        params.get('input_files'))
    ):

        issues = libcheck.check(
            xr.open_dataset(f),
            standard=params.get('standard')
        )

        issues['filename'] = os.path.abspath(f)

        list_of_issues.append(issues)

    issues = pd.concat(list_of_issues)

    if len(issues.query("issue.notna()")):
        print("Issues found")

    if params.get('verbose') is True:
        print(issues.query("issue.notna()"))

    sep = ';' if params.get('semicolon_separated') else ','
    issues.to_csv(params.get('output_file'), sep=sep)


def select_files_subparser(subparser=None):

    """
    Add parser for pyku select files
    """

    parser = subparser.add_parser(
        'select-files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Find files",
        epilog="""\
EXAMPLE
    pyku select-files list/of/file*.nc\\
        --min-datetime 2023-10-20\\
        --max-datetime 2023-10-21
"""
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        default=False,
        dest='verbose',
        help='Switch verbose mode on'
    )

    parser.add_argument(
        'input_files',
        nargs='+',
        default='',
        help='Input file(s)'
    )

    parser.add_argument(
        '--min-datetime',
        action='store',
        default=None,
        dest='min_datetime',
        help='Minimal datetime searched for in the directory name'
    )

    parser.add_argument(
        '--max-datetime',
        action='store',
        default=None,
        dest='max_datetime',
        help='Maximal datetime searched for in the directory name'
    )

    parser.add_argument(
        '--exclude-min',
        action='store_true',
        default=False,
        dest='exclude_min',
        help='Wether the minimal datetime should be excluded from the search'
    )

    parser.add_argument(
        '--exclude-max',
        action='store_true',
        default=False,
        dest='exclude_max',
        help='Wether the maximal datetime should be excluded from the search'
    )

    parser.add_argument(
        '--offset',
        action='store',
        default=None,
        dest='offset_string',
        help='Offset string'
    )


def select_files_run(params):

    """
    Run select-files

    Arguments:
        params: Dictionary of parameters
    """

    import json
    import pyku.find as find

    # Print parameters to screen in verbose mode
    # ------------------------------------------

    if params.get('verbose') is True:
        print(json.dumps(params, indent=2))

    input_files = find.get_files_from_list_of_patterns(
        params.get('input_files')
    )

    output_files = find.select_files_by_datetimes(
        input_files,
        min_date=params.get('min_datetime'),
        max_date=params.get('max_datetime'),
        exclude_min=params.get('exclude_min'),
        exclude_max=params.get('exclude_max'),
        offset=params.get('offset_string'),
    )

    # Sort files
    # ----------

    output_files = sorted(output_files)

    # Gather in single line
    # ---------------------

    print(" ".join(output_files))


def select_directories_subparser(subparser=None):

    """
    Add parser for pyku select files
    """

    parser = subparser.add_parser(
        'select-directories',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Find directories",
        epilog="""\
EXAMPLE
    pyku select-directories /list/of/directories\\
        --min-datetime 2023-10-20\\
        --max-datetime 2023-10-21
"""
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        default=False,
        dest='verbose',
        help='Switch verbose mode on'
    )

    parser.add_argument(
        'input_directories',
        nargs='+',
        default='',
        help='Input directories'
    )

    parser.add_argument(
        '--min-datetime',
        action='store',
        default=None,
        dest='min_datetime',
        help='Minimal datetime searched for in the files'
    )

    parser.add_argument(
        '--max-datetime',
        action='store',
        default=None,
        dest='max_datetime',
        help='Maximal datetime searched for in the files'
    )

    parser.add_argument(
        '--exclude-min',
        action='store_true',
        default=False,
        dest='exclude_min',
        help='Wether the minimal datetime should be excluded from the search'
    )

    parser.add_argument(
        '--exclude-max',
        action='store_true',
        default=False,
        dest='exclude_max',
        help='Wether the maximal datetime should be excluded from the search'
    )


def select_directories_run(params):

    """
    Run select-directories

    Arguments:
        params: Dictionary of parameters
    """

    import json
    import pyku.find as find

    # Print parameters to screen in verbose mode
    # ------------------------------------------

    if params.get('verbose') is True:
        print(json.dumps(params, indent=2))

    input_directories = find.expand_unix_directory_patterns(
        params.get('input_directories')
    )

    output_directories = find.select_directories_by_datetimes(
        input_directories,
        min_date=params.get('min_datetime'),
        max_date=params.get('max_datetime'),
        exclude_min=params.get('exclude_min'),
        exclude_max=params.get('exclude_max'),
    )

    # Sort files
    # ----------

    output_directories = sorted(output_directories)

    # Gather in single line
    # ---------------------

    print(" ".join(output_directories))


def cmorize_subparser(subparser=None):

    """
    Add parser for pyku cmorize
    """

    parser = subparser.add_parser(
        'cmorize',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="cmorize",
        epilog="""\
EXAMPLE
    Example to be written
    pyku cmorize /path/to/data/2010_??/T_2M_ts.nc \\
         --conf /path/to/global-metadata.json \\
         --varnames U_10M V_10M
         --output-dir /path/to/outputdir \\
         --standard cordex \\
         --version yourversion \\
         --verbose
"""
    )

    parser.add_argument(
        '--verbose',
        '-v',
        action='store_true',
        default=False,
        dest='verbose',
        help='Switch verbose mode on'
    )

    parser.add_argument(
        'input_files',
        nargs='*',
        default='',
        help='Input files'
    )

    parser.add_argument(
        '--version',
        action='store',
        dest='version',
        default=None,
        required=False,
        help='Version number added to the path'
    )

    parser.add_argument(
        '--varnames',
        action='store',
        dest='varnames',
        nargs='+',
        type=str,
        default=None,
        required=False,
        help='List of variable names to be cmorized'
    )

    parser.add_argument(
        '--area-def',
        action='store',
        dest='area_def',
        default=None,
        required=False,
        help='Area definition of the output files'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        default=False,
        dest='dry_run',
        help='Perform dry run'
    )

    parser.add_argument(
        '--min-datetime',
        action='store',
        dest='min_datetime',
        default=None,
        required=False,
        help="""ISO8601 format (e.g. 2010-07-01T01:00+000). Many files can be
opened at once. the --min-datetime option permits to filter the datetimes in
the dataset."""
    )

    parser.add_argument(
        '--max-datetime',
        action='store',
        dest='max_datetime',
        default=None,
        required=False,
        help="""ISO8601 format (e.g. 2010-07-01T01:00+000). Many files can be
opened at once. the --min-datetime option permits to filter the datetimes in
the dataset"""
    )

    parser.add_argument(
        '--exclude-min-datetime',
        action='store_true',
        default=False,
        dest='exclude_min_datetime',
        help="""If set, the first datetime is excluded from the cmorization."""
    )

    parser.add_argument(
        '--exclude-max-datetime',
        action='store_true',
        default=False,
        dest='exclude_max_datetime',
        help="""If set, the last datetime is excluded from the cmorization."""
    )

    parser.add_argument(
        '--global-metadata',
        action='store',
        dest='global_metadata',
        default='',
        required=False,
        help='Global metadata'
    )

    parser.add_argument(
        '--output-dir',
        action='store',
        dest='output_dir',
        default='./',
        required=False,
        help='Output directory'
    )

    parser.add_argument(
        '--standard',
        action='store',
        dest='standard',
        choices=['cordex', 'cordex-adjust', 'cordex-adjust-interp'],
        default=None,
        required=True,
        help='Type of cordex DRS'
    )

    parser.add_argument(
        '--overwrite',
        action='store_true',
        default=False,
        dest='overwrite',
        help='Overwrite output file if it exists'
    )

    parser.add_argument(
        '--resample-datetimes',
        action='store_true',
        default=False,
        dest='resample_datetimes',
        help='Resample datetimes'
    )

    parser.add_argument(
        '--resample-datetimes-frequency',
        action='store',
        dest='resample_datetimes_frequency',
        default=None,
        required=False,
        help="Frequency for datetime resampling (e.g. '1D', '1M', 'YS')"
    )

    parser.add_argument(
        '--resample-datetimes-how',
        action='store',
        dest='resample_datetimes_how',
        choices=['mean', 'min', 'max', 'sum'],
        default=None,
        required=False,
        help='How to resample datetimes'
    )


def cmorize_run(params):

    """
    CMORize

    Arguments:
        params: Dictionary of parameters
    """

    import textwrap
    import yaml
    import json
    import warnings
    import xarray as xr
    import pandas as pd
    import pyku.compute as compute
    import pyku.meta as meta
    import pyku.drs as drs
    import pyku.find as find
    import pyku  # noqa
    import pyku.postmodel as postmodel

    # Sanity modification
    # -------------------

    # The following code solves what to do if the datetimes are localize. If
    # the time is localized and the timestamp is UTC, delocalize time. If the
    # time is localized and the timestamp is not UTC, raise an exception. This
    # is necessary to do so because generally climate metadata are not
    # localized.

    if params.get('min_datetime') is not None:
        min_datetime = pd.Timestamp(params.get('min_datetime'))
    if params.get('max_datetime') is not None:
        max_datetime = pd.Timestamp(params.get('max_datetime'))

    if min_datetime is not None and min_datetime.tz is not None and \
       min_datetime.utcoffset().total_seconds() != 0:
        message = (
            "Min datetime was passed with a timestamp which is not UTC",
            "Use a UTC timestamp or no localization"
        )
        raise Exception(message)

    if max_datetime is not None and max_datetime.tz is not None and \
       max_datetime.utcoffset().total_seconds() != 0:
        message = (
            "Max datetime was passed with a timestamp which is not UTC",
            "Use a UTC timestamp or no localization"
        )
        raise Exception(message)

    if min_datetime is not None and min_datetime.tz is not None and \
       min_datetime.utcoffset().total_seconds() == 0:
        min_datetime = min_datetime.tz_localize(None)
        min_datetime = min_datetime.isoformat()

    if max_datetime is not None and max_datetime.tz is not None and \
       max_datetime.utcoffset().total_seconds() == 0:
        max_datetime = max_datetime.tz_localize(None)
        max_datetime = max_datetime.isoformat()

    # Print parameters to screen in verbose mode
    # ------------------------------------------

    if params.get('verbose') is True:
        print(json.dumps(params, indent=2))

    # Or suppress warnings otherwise
    # ------------------------------

    else:
        warnings.filterwarnings("ignore")

    # Load metadata file if given
    # ---------------------------

    global_metadata = {}

    if params.get('global_metadata') != '':
        with open(params.get('global_metadata')) as f:
            global_metadata = yaml.safe_load(f)

    input_files = find.select_files_by_datetimes(
        params.get('input_files'),
        min_date=min_datetime,
        max_date=max_datetime
    )

    # Open data as an xarray
    # ----------------------

    # A large amount of files with the same coordinates and dimensions is
    # expected. The options permit to ignore checks performed by xarray
    # open_mfdataset in that regard and load the data with high performance

    ds = xr.open_mfdataset(
        input_files,
        data_vars="minimal",
        coords="minimal",
        compat="override",
        join="override"
    )

    # Derotate
    # --------

    ds = postmodel.derotate(ds)

    # Calculate computable variables (e.g. wind speed from wind components)
    # ---------------------------------------------------------------------

    ds = postmodel.post(ds)

    # Select variables
    # ----------------

    ds = meta.get_geodataset(ds, var=params.get('varnames'))

    # Loop over variables
    # -------------------

    for var in params.get('varnames'):

        # Get variable dataset
        # --------------------

        vards = meta.get_geodataset(ds, var)

        # Set time label to middle time bounds
        # ------------------------------------

        if meta.has_time_bounds(vards):
            vards = meta.set_time_labels_from_time_bounds(vards, how='middle')

        # Select time slice
        # -----------------

        vards = vards.sel(time=slice(min_datetime, max_datetime))

        # Exclude min and/or max datetime
        # -------------------------------

        if params.get('exclude_max_datetime') is True:
            vards = vards.sel(
                time=~(vards['time'] == pd.Timestamp(max_datetime))
            )

        if params.get('exclude_min_datetime') is True:
            vards = vards.sel(
                time=~(vards['time'] == pd.Timestamp(min_datetime))
            )

        # CMORize the dataset
        # -------------------

        vards = vards.pyku.project(area_def=params.get('area_def', None))
        cmorized_vards = drs.cmorize(
            vards,
            global_metadata=global_metadata,
        )

        # Resample datetimes
        # ------------------

        if params.get('resample_datetimes') is True:

            if params.get('resample_datetimes_frequency') is None:
                message = textwrap.dedent("""\
                    --resample-datetimes-frequency is a mandatory parameter if
                    option --resample-datetimes is passed.
                """).replace('\n', ' ')
                raise Exception(message)

            if params.get('resample_datetimes_how') is None:
                message = textwrap.dedent("""\
                    --resample-datetimes-how is a mandatory parameter if option
                    --resample-datetimes is passed.
                """).replace('\n', ' ')
                raise Exception(message)

            cmorized_vards = compute.resample_datetimes(
                cmorized_vards,
                how=params.get('resample_datetimes_how'),
                frequency=params.get('resample_datetimes_frequency'),
                complete=params.get('complete', False)
            )

            # Set time label to middle time bounds
            # ------------------------------------

            # Marker. This is because the time lable used when resampling
            # datetimes is the lower time label after resampling. Would like to
            # keep it like that since it is imo the right thing to use. Maybe
            # add an option idk.

            if meta.has_time_bounds(cmorized_vards):
                cmorized_vards = meta.set_time_labels_from_time_bounds(
                    cmorized_vards,
                    how='middle'
                )

        # Write to file
        # -------------

        drs.to_drs_netcdfs(
            cmorized_vards,
            base_dir=params.get('output_dir'),
            standard=params.get('standard'),
            version=params.get('version'),
            dry_run=params.get('dry_run'),
            overwrite=params.get('overwrite')
        )


if __name__ == "__main__":
    main()
