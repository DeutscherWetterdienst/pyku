#!/usr/bin/env python3
"""
CLI interface for climate-indicator tool.
Handles parsing via jsonargparse, validation, and returns parsed args.
"""

import glob
from datetime import datetime

from jsonargparse import ArgumentParser
from jsonargparse.typing import register_type
from pandas.tseries.frequencies import to_offset
from pint import Quantity
from rapidfuzz import process
from xclim.core import Quantified  # register new type
from xclim.core.units import units

from pyku.clix import indicator_data
from pyku.clix.manager import (
    get_indicator_description,
    load_function,
    replace_description_with_values,
    update_default_args,
)


# Helpers
def check_path(path_str: str):
    """
    Expand braces + wildcards and check that at least one match exists.
    """

    from braceexpand import braceexpand

    expanded = list(braceexpand(path_str))

    found = False
    for pat in expanded:
        matches = glob.glob(pat)
        if matches:  # at least one match found
            found = True
            break

    if not found:
        raise TypeError(f"No matching files found for: {path_str}")

    return path_str


def check_input(path_str: str) -> str:
    """
    Validate a given path string as 'yaml', 'file', or 'folder'.

    Parameters
    ----------
    path_str : str
        Input path or pattern (brace expansion supported).

    Returns
    -------
    str
        The original path_str, if it is a valid yaml, file, or folder.

    Raises
    ------
    TypeError
        If the path does not exist or is not a valid file/folder/yaml.
    """

    from pathlib import Path
    from braceexpand import braceexpand

    expanded_paths = [Path(p) for p in braceexpand(path_str)]

    if not all(p.exists() for p in expanded_paths):
        raise TypeError(f"Input path does not exist: {path_str}")

    # Directories
    if all(p.is_dir() for p in expanded_paths):
        return path_str

    # Files
    if all(p.is_file() for p in expanded_paths):
        if all(p.suffix.lower() in {".yaml", ".yml"} for p in expanded_paths):
            return path_str
        else:
            return path_str

    raise TypeError(f"Input path is not a valid file or folder: {path_str}")


def classify_input(path_str: str) -> dict:
    """
    Classify input path(s) as 'file', 'folder', or 'yaml'.

    Returns
    -------
    dict
        Mapping from the original input string to its classification.
    Raises
    ------
    TypeError
        If the path does not exist or is not a valid file/folder.
    """

    from pathlib import Path
    from braceexpand import braceexpand

    unbraced_paths = [p for part in path_str for p in braceexpand(part)]
    expanded_paths = [Path(p) for p in unbraced_paths]

    if not all(p.exists() for p in expanded_paths):
        raise TypeError(f"Input path does not exist: {path_str}")

    if all(p.is_dir() for p in expanded_paths):
        return {p: "folder" for p in path_str}

    if all(p.is_file() for p in expanded_paths):
        if all(p.suffix.lower() in {".yaml", ".yml"} for p in expanded_paths):
            return {p: "yaml" for p in path_str}
        elif all(p.suffix.lower() in {".csv", ".txt"} for p in expanded_paths):
            return {p: "text" for p in path_str}
        else:
            return {p: "file" for p in path_str}

    raise TypeError(f"Input path is not a file or folder: {path_str}")


def validate_and_sort_date_ranges(date_ranges):
    if not date_ranges:
        return []
    parsed, seen = [], set()
    for start, end in date_ranges:
        sd = datetime.strptime(start, "%Y%m%d")
        ed = datetime.strptime(end, "%Y%m%d")
        if sd >= ed:
            raise ValueError(f"{start} must be before {end}")
        key = (start, end)
        if key not in seen:
            seen.add(key)
            parsed.append((start, end))
    parsed.sort()
    return parsed


def get_frequency(freq):

    choices = {'year': 'YS', 'season': 'QS-DEC', 'month': 'MS'}

    if freq in choices.values():
        return freq
    else:
        best = process.extractOne(freq, choices.keys())[0]
        return choices[best]


def valid_freq(value: str) -> str:

    from argparse import ArgumentTypeError

    try:
        to_offset(value)  # Validate if it's a valid frequency string
        return value
    except ValueError:
        raise ArgumentTypeError(
            f"Invalid frequency string '{value}'. Must be something like 'MS', 'YS', 'QS-DEC', or '5D'."  # noqa
        )  # noqa


def percent_0_to_100(val: str) -> float:
    val = float(val)
    if not (0.0 <= val <= 100.0):
        raise ValueError('Value must be between 0 and 100.')
    return val


def parse_quantity(val: str) -> Quantity:
    try:
        return units.Quantity(val)
    except Exception as e:
        raise ValueError(f"Invalid quantity '{val}': {e}")


register_type(Quantified, str, parse_quantity)


def build_parser():

    # Setup argument parser
    parser = ArgumentParser(
        description="CLIX - Climate Indicator tool at DWD",
        env_prefix='CLIX'
    )

    # Create a mandatory group (mg) for input arguments
    # mg = parser.add_argument_group(
    ig = parser.add_argument_group(
        'Mandatory input arguments',
    )

    ig.add_argument('-i', '--input',
                    nargs='*',
                    required=True,
                    type=check_input,
                    help="Select input files, folders or yaml configuration.")
    ig.add_argument(
        '-f', '--frequency',
        help='Resampling frequency year/month/season.',  # noqa
        type=str, required=True
    )

    # Create a group for calculation mode arguments (calc group)
    cg = parser.add_argument_group("Calculation mode")
    cg.add_argument('--average', action='store_true',
                    help="Calculate averages")
    cg.add_argument('--anomaly', type=str, choices=['abs', 'perc'],
                    help="Calculate anomaly")
    cg.add_argument(
        '--ref_date_range', action='append', nargs=2,
        metavar=('START', 'END'),
        help='Provide one or more reference date ranges as YYYYMMDD YYYYMMDD for anomaly calculation.'  # noqa
    )

    # Create optional group (optional group)
    og = parser.add_argument_group("Optional arguments")
    og.add_argument(
        '--date_range', action='append', nargs=2,
        metavar=('START', 'END'),
        help='Provide one or more date ranges as YYYYMMDD YYYYMMDD.')
    og.add_argument('--varnames', nargs='*', default=[])
    og.add_argument('--ofile', help="Output filename")
    og.add_argument('--check_missing', type=str, default='wmo',
                    choices=['any', 'wmo', 'at_least_n', 'pct', 'skip'],
                    help="how to handle missing values")
    og.add_argument('--min_valid_values', type=int, default=None,
                    help="The minimum number of valid values needed "
                    "(only for check_missing = at_least_n)")
    og.add_argument(
        '--allowed_miss_pct', type=float, default=None,
        help=("The maximum tolerated proportion of missing values, "
              "given as a number between 0 and 1 per output frequency "
              "(only for check_missing = pct).")
    )

    # Create cluster managment group
    cmg = parser.add_argument_group("Cluster managment arguments")
    cmg.add_argument('--workers', type=int, default=0,
                     help='Set number of CPU workers')
    cmg.add_argument('--memory_limit', type=int, default=12,
                     help='Increase memory limit per CPU (in Gigabyte)')
    cmg.add_argument("--dask_cluster", type=str, default=None,
                     help=(
                         """Optional: Dask scheduler address to execute
    computations on a remote or distributed cluster. If not provided,
    computations run locally."""))

    # Create percentile group
    pg = parser.add_argument_group("Percentile arguments")

    ig.add_argument(
        '--input_perc', nargs='*', type=check_input,
        help="Select input files, folders or yaml configuration for percentiles.",  # noqa
    )
    pg.add_argument(
        '--percentile', type=percent_0_to_100,
        help='Set percentile value between 0 to 100. If not set, assumes percentiles are precomputed.',  # noqa
    )
    pg.add_argument(
        '--percentile_freq', type=valid_freq, default='5D',
        help=(
            "Specify the grouping for percentile calculation. "
            "Accepts a frequency string (e.g., 'MS' for monthly, 'YS' for yearly, 'QS-DEC' for seasonal) "  # noqa
            "or a number of days (e.g., '5D' for a 5-day window)."
        )  # noqa
    )
    pg.add_argument(
        '--perc_date_range', action='append', nargs=2,
        metavar=('START', 'END'),
        help='Set period to compute percentiles as YYYYMMDD YYYYMMDD.',  # noqa
    )

    # Create percentile group (percentile group)
    sg = parser.add_argument_group("Significance test options")

    # Boolean flag to perform significance test
    sg.add_argument(
        "--significance",
        action="store_true",
        help="Perform a statistical significance test"
    )

    # Optional float for significance level
    sg.add_argument(
        "--alpha",
        type=float,
        default=0.05,
        help="Significance level for the test (default: 0.05)"
    )

    # Dynamic subcommands for climate indicators
    subs = parser.add_subcommands(
        title="Climate Indicators",
        description='For more details on each Climate Indicator, add it as an argument followed by --help.',  # noqa
        required=True)

    for indicator, params in indicator_data.items():

        # Subparser for indicators
        indp = ArgumentParser()
        fn = load_function(params['function'])

        # Add arguments based on the specified function
        # Skips required arguments that represent input DataArrays
        indp.add_function_arguments(
            fn,
            skip=['tas', 'pr', 'tasmax', 'tasmin', 'sfcWind', 'rsds',
                  'tas_per', 'pr_per', 'tasmax_perc', 'tasmin_per',
                  'data1', 'data2', 'data_var1', 'data_var2', 'freq'],
            sub_configs=True)

        # Update default function value with values based on
        # climate_indicators.yaml
        if params.get('default_parameters'):
            update_default_args(indp, params['default_parameters'])

        # Set parser description using additional indicator descriptions
        # and replace with default values
        desc = get_indicator_description(indicator)
        desc = replace_description_with_values(indp, desc)
        indp.description = desc
        subs.add_subcommand(indicator, indp, help=desc)

    return parser


def parse_cli(cli_args=None):
    parser = build_parser()
    args = parser.parse_args(cli_args)

    # Post-validation
    args.input = classify_input(args.input)
    args.frequency = get_frequency(args.frequency)
    args.date_range = validate_and_sort_date_ranges(args.date_range)

    # Set default (None, None) date slice!
    if not args.date_range:
        args.date_range.append((None, None))

    if args.anomaly:
        args.ref_date_range = validate_and_sort_date_ranges(args.ref_date_range)[0]  # noqa
    else:
        args.ref_date_range = []

    if args.input_perc:
        args.input_perc = classify_input(args.input_perc)

    args.perc_date_range = validate_and_sort_date_ranges(
        args.perc_date_range)

    return args
