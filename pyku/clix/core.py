# pyku/clix/core.py
"""
CLIX - Climate indicators at DWD
Climate indicator tool based on the xclim library
Authors: Harald Rybka, Birgit Mannig

Contains helpers and the following core functions:
    * `run_tool_from_datasets()`:
       runs the indicator tool on already‑opened datasets
    * `compute_percentiles()`:
       computes percentiles from input files. Can be used individually.
    * `main()`:
       command‑line entry point that uses the above functions
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from collections import defaultdict
from collections.abc import Iterable
from typing import Literal

import pandas as pd
from dask.distributed import Client, LocalCluster
from pandas.tseries.frequencies import to_offset
from rapidfuzz import process
from xclim.core.calendar import percentile_doy

import xarray as xr
from pyku import drs, logger

# --------------------------------------------------------------------------- #
# Import the original CLI parser
# --------------------------------------------------------------------------- #
# from pyku.clix.cli import parse_cli  # the original argparse parser
from pyku.clix import indicator_data
from pyku.clix import manager as im
from pyku.clix.custom_indicators import (
    expand_percentiles_to_daily,
    percentile_grouped,
)
from pyku.meta import (
    get_crs_varname,
    get_geodata_varnames,
    get_projection_yx_varnames,
    has_time_bounds,
)
from pyku.timekit import (
    set_time_bounds_from_time_labels,
    to_gregorian_calendar,
)


# --------------------------------------------------------------------------- #
# Helper: preprocess xarray.Datasets for uniform time dimension
# --------------------------------------------------------------------------- #
def _preprocess(ds: xr.Dataset) -> xr.Dataset:
    """
    Preprocess an xarray Dataset to ensure consistent time handling
    and remove conflicting time-bound metadata.

    The preprocessing steps are:
    1. Normalize time coordinates to daily resolution (floor to 1D).
    2. Remove existing time bounds variables if present.
    3. Reconstruct time bounds from cleaned time coordinates.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`xarray.Dataset`: Dataset with preprocessed time stamps and
            time boundaries

    See Also
    --------
    xarray.open_mfdataset : Used with the `preprocess` argument.
    """

    # normalize timestamps
    ds = ds.assign_coords(
        time=ds.time.dt.floor("1D")
    )
    # set timebounds
    if has_time_bounds(ds):
        tb_name = getattr(
                ds.pyku,
                "get_time_bounds_varname",
                lambda: "time_bnds"
                )()
        if tb_name in ds:
            ds = ds.drop_vars(tb_name)
    ds = set_time_bounds_from_time_labels(ds)

    return ds


# --------------------------------------------------------------------------- #
# Helper: open a list of file paths into xarray.Datasets
# --------------------------------------------------------------------------- #
def _open_datasets(file_groups: Iterable[Iterable[str]]) -> list[xr.Dataset]:
    """
    Open each file in `file_groups` with xarray and apply the same
    preprocessing that the original CLI used:
        * combine by coords
        * fix time stamps and time bounds
        * cmor conversion, attributes, Gregorian calendar

    Arguments:
        file_groups (Iterable[Iterable[str]]): Iterable containing groups
            of file paths. Each inner iterable represents one logical
            dataset to open with ``xarray.open_mfdataset``.

    Returns:
        list[xarray.Dataset]: List of opened and preprocessed datasets.
    """

    datasets = []

    for paths in file_groups:

        if isinstance(paths, str):
            paths = [paths]

        ds = xr.open_mfdataset(
            paths,
            preprocess=_preprocess,
            combine="by_coords",
            chunks="auto",
            parallel=False,
        )

        ds = drs.to_cmor_units(ds)
        ds = drs.to_cmor_attrs(ds)
        ds = to_gregorian_calendar(ds, add_missing=True)

        datasets.append(ds)

    return datasets


# ----------------------------------------------------------------------------#
# Helper: ds.persist() for nested dictionary
# ----------------------------------------------------------------------------#
def _persist_nested(
        ds_dict: dict[im.Period, dict[str, xr.Dataset]]
) -> dict[im.Period, dict[str, xr.Dataset]]:
    """
    Persist all xarray objects inside a nested dictionary using Dask.

    This function traverses a nested dictionary structure and applies
    `.persist()` to all objects that support it. Necessary for percentile
    calculations, avoiding recomputation in later processing steps.

    Arguments:
        ds (dict[str, dict[str, xarray.DataArray]]): Nested dictionary where
            outer keys represent im.Periods and inner keys represent
            variable names. Values are xarray objects

    Returns:
        dict[str, dict[str, xarray.DataArray]]: Same dictionary structure with
        all Dask-enabled xarray objects persisted on distributed workers.
    """
    return {
        outer_key: {
            inner_key: (
                inner_value.persist()
                if hasattr(inner_value, "persist") else inner_value
                )
            for inner_key, inner_value in outer_value.items()
        }
        for outer_key, outer_value in ds_dict.items()
    }


# --------------------------------------------------------------------------- #
# Helper: crs Variable for final dataset
# --------------------------------------------------------------------------- #
def add_crs_to_dataset(
    ds: xr.Dataset,
    crs_var: xr.DataArray | None,
) -> xr.Dataset:
    """
    adds crs-Variable and links it to attributes

    Arguments:
        ds (:class:`xarray.Dataset`): The input Dataset
        crs_var (:class: `xarray.DataArray` | None)

    Returns:
        xr.Dataset: dataset with crs variable
    """

    if crs_var is None:
        logger.info("No crs variable found.")
        return ds

    if crs_var.name not in ds:
        ds[crs_var.name] = crs_var
    for var_name in ds.data_vars:
        if var_name != crs_var.name:
            ds[var_name].attrs['grid_mapping'] = crs_var.name
    crs_wkt = (crs_var.attrs.get("crs_wkt") or
               crs_var.attrs.get("spatial_ref"))
    if crs_wkt:
        ds.attrs['esri_pe_string'] = crs_wkt

    return ds


# ---------------------------------------------------------------------------
# Helper: create dictionary with datasets
# --------------------------------------------------------------------------

def build_period_slice(
    ds: xr.Dataset,
    sd: pd.Timestamp | None,
    ed: pd.Timestamp | None,
    role: Literal["target", "reference"]
) -> tuple[im.Period, xr.Dataset]:
    """
    Build a normalized :class:`Period` object and extract the
    corresponding temporal slice from a dataset.

    If ``sd`` or ``ed`` are ``None``, the dataset's first or last
    available timestep is used automatically.

    Arguments:
        ds (:class:`xarray.Dataset`):
            Input dataset containing a ``time`` coordinate.

        sd (pd.Timestamp | None):
            Start date of the requested period.

        ed (pd.Timestamp | None):
            End date of the requested period.

        role (Literal["target", "reference"]):
            Semantic role assigned to the resulting period.

    Returns:
        tuple[:class:`Period`, :class:`xarray.Dataset`]:
            A tuple containing:

            - The normalized :class:`Period`
            - The sliced dataset for the requested time span

    Raises:
        ValueError:
            Raised if the selected time range contains no data.
    """

    ds_start = pd.Timestamp(ds.time.values[0])
    ds_end = pd.Timestamp(ds.time.values[-1])

    start = pd.Timestamp(sd) if sd is not None else ds_start
    end = pd.Timestamp(ed) if ed is not None else ds_end

    period = im.Period(start, end, role)

    ds_slice = ds.sel(time=slice(start, end))

    if ds_slice.time.size == 0:
        raise ValueError(
            f"Timespan {start} to {end} has no data."
        )

    return period, ds_slice


# --------------------------------------------------------------------------- #
#  Helper: start a Dask cluster (local or remote)
# --------------------------------------------------------------------------- #

def start_dask_cluster(
    opts: argparse.Namespace
     ) -> tuple[Client, LocalCluster | None]:
    """
    Start a Dask cluster according to the options.

    Depending on the provided configuration, the function either
    connects to an existing external Dask cluster or creates a new
    local cluster instance.

    Arguments:
        opts (argparse.Namespace):
            Parsed command-line arguments containing the Dask cluster
            configuration options.

    Returns:
        tuple[Client, LocalCluster | None]:
            Tuple containing:

            - `Client`: Connected Dask client instance.
            - `LocalCluster | None`: The created local cluster instance,
              or `None` if an external cluster was used.
    """

    if opts.dask_cluster:
        client = Client(opts.dask_cluster)
        cluster = None
    else:
        workers = opts.workers or 0
        if workers > 0:
            mem_limit = f"{opts.memory_limit}GB"
            cluster = LocalCluster(
                n_workers=workers,
                threads_per_worker=1,
                memory_limit=mem_limit,
            )
            client = Client(cluster)
        else:
            cluster = None
            client = Client()  # default local client

    if cluster is not None:
        host = os.environ.get("HOSTNAME", "localhost")
        port = client.dashboard_link.split(":")[-1]
        logger.info(
            f"Dashboard: {host}:{port} – {opts.workers} workers, "
            f"{opts.memory_limit}GB per worker."
        )
    return client, cluster


# -------------------------------------------------------------------------- #
# Helper: Percentile Calculations
# -------------------------------------------------------------------------- #

def compute_percentiles(
    ifiles_perc: list[str] | list[list[str]],
    date_ranges: list[tuple[pd.Timestamp | None, pd.Timestamp | None]],
    perc_date_ranges: list[tuple[str | None, str | None]] | None,
    percentile: float,
    perc_freq: str,
    varnames: list[str] | None = None
) -> dict[im.Period, dict[str, xr.Dataset]]:

    """
    Compute grouped or day-of-year percentiles lazily using Dask.

    The function reads the input datasets using `_open_datasets` and
    computes percentiles by constructing a lazy Dask computation graph.

    Arguments:
        ifiles_perc (List[str] | List[List[str]]):
            Input file paths used for percentile computation. Can either
            be a flat list of files or a nested list grouping files.

        date_ranges (List[Tuple[pd.Timestamp | None, pd.Timestamp | None]]):
            List of start and end date tuples defining the target
            analysis periods. Each tuple contains
            `(start_date, end_date)`.

        perc_date_ranges (List[Tuple[str | None, str | None]] | None):
            Optional list of start and end date tuples defining the
            periods used specifically for percentile calculation.
            If `None`, `date_ranges` are used.

        percentile (float):
            Percentile value to compute (e.g. `90.0` for the 90th
            percentile).

        perc_freq (str):
            Frequency definition for percentile computation.
            Typically grouped frequencies such as `"month"` or
            `"dayofyear"`.

        varnames (List[str] | None):
            Optional list of variable names to process.
            If `None`, all variables are processed.

    Returns:
        Dict[im.Period, Dict[str, xr.Dataset]]:
            Nested dictionary containing the computed percentile
            datasets. The outer dictionary keys correspond to the
            associated target date range period, while the inner dictionary
            maps variable names to their percentile datasets.
    """

    perc_dict = defaultdict(dict)
    effective_perc_ranges = perc_date_ranges or date_ranges

    # ifiles_perc needs to be a structured list for _open_datasets,
    if ifiles_perc and isinstance(ifiles_perc[0], str):
        file_groups = [ifiles_perc]
    else:
        file_groups = ifiles_perc

    opened_perc_datasets = _open_datasets(file_groups)

    for ds in opened_perc_datasets:
        ds_var_perc = get_geodata_varnames(ds)[0]

        for (sd, ed), (sd_p, ed_p) in zip(date_ranges, effective_perc_ranges,
                                          strict=True):
            # dataset bounds
            ds_start = pd.Timestamp(ds.time.values[0])
            ds_end = pd.Timestamp(ds.time.values[-1])

            # main period
            _sd = pd.Timestamp(sd) if sd is not None else ds_start
            _ed = pd.Timestamp(ed) if ed is not None else ds_end

            # percentile training period
            _sd_perc = pd.Timestamp(sd_p) if sd_p is not None else _sd
            _ed_perc = pd.Timestamp(ed_p) if ed_p is not None else _ed

            perc_slice_ = ds.sel(time=slice(_sd_perc, _ed_perc))

            # chunking
            chunk_dict = {}
            # time chunks
            time_dim = perc_slice_.sizes.get("time", 0)
            # for calc_per function, time chunks should be larger
            min_time_chunk = 2000
            if time_dim > 0:
                chunk_dict = {
                    "time": min(min_time_chunk, time_dim)
                }
            # spatial chunks
            spatial_dims = get_projection_yx_varnames(perc_slice_)
            for d in spatial_dims:
                chunk_dict[d] = 50
            # rechunk
            perc_slice_ = perc_slice_.chunk(chunk_dict)

            if 'time' in perc_slice_.sizes and perc_slice_.sizes['time'] == 0:
                raise ValueError("No data available for percentile"
                                 f"calculation from {_sd_perc} to {_ed_perc}.")

            logger.info(f"Calculating percentiles {ds_var_perc}"
                        "from ({_sd_perc} to {_ed_perc})"
                        "with frequency {perc_freq}.")

            if perc_freq in ['YS', 'MS', 'QS-DEC']:
                arr_perc = percentile_grouped(
                    perc_slice_[ds_var_perc],
                    group_freq=perc_freq,
                    per=percentile,
                    climatology=True
                )
                target_slice = ds.sel(time=slice(_sd, _ed))
                arr_perc = expand_percentiles_to_daily(
                    target_slice,
                    arr_perc,
                    perc_freq
                )
            else:
                ndays = to_offset(perc_freq).n
                arr_perc = percentile_doy(
                    perc_slice_[ds_var_perc],
                    per=percentile,
                    window=ndays
                )

            perc_dataset = arr_perc.to_dataset(name=f'{ds_var_perc}_per')
            # for later use, the perc_dict needs the target Period as key
            perc_expand_period = im.Period(_sd, _ed, 'target')
            perc_dict[perc_expand_period][f'{ds_var_perc}_per'] = perc_dataset

    return perc_dict


# --------------------------------------------------------------------------- #
# dataset‑based API for calculating climate indicators with metadata
# --------------------------------------------------------------------------- #

def run_tool_from_datasets(
    datasets: list[xr.Dataset],
    *,
    clindicator: im.ClimateIndicator,
    date_ranges: (
        list[tuple[pd.Timestamp | None, pd.Timestamp | None]]
        | None
        ) = None,
    ref_date_range: (
        tuple[pd.Timestamp | None, pd.Timestamp | None] | None
        ) = None,
    perc_dict: dict[tuple[str, str], dict[str, xr.Dataset]] | None = None,
    varnames: list[str] | None = None,
    na_handling: str = "wmo",
    min_valid_values: int | None = None,
    tolerance: float | None = None,
    anomaly: str | None = None,
    significance: bool = False,
    sig_alpha: float = 0.05,
    average: bool = False,
) -> dict[tuple[str, str], xr.Dataset]:
    """
    Run the climate indicator calculation on already opened xarray Datasets.

    This function processes datasets in memory using a nested dictionary,
    preventing metadata loss.

    Arguments:
        datasets (List[:class:`xarray.Dataset`]):
            List of opened input datasets.

        clindicator (:class:`pyku.clix.manager.ClimateIndicator`):
            Pre-initialized indicator instance for required arguments,
            includes the name of the climate indicator and the
            target temporal frequency for the calculation (e.g. 'YS', 'MS').

        date_ranges (
            List[Tuple[pd.Timestamp | None, pd.Timestamp | None]], optional
            ):
            Period blocks to process as (start_date, end_date).
            Defaults to None.

        ref_date_range (
            List[Tuple[pd.Timestamp | None, pd.Timestamp | None]], optional
            ):
            Period blocks for anomaly reference period as
            (start_date, end_date). Defaults to None.

        perc_dict (Dict, optional):
            Precomputed percentile thresholds grouped by period.
            Defaults to None.

        varnames (List[str], optional):
            Custom variable names mapping to the datasets.
            Defaults to None.

        na_handling (str, optional):
            Missing value handling method. Valid options are
            'any', 'wmo', 'at_least_n', 'pct', 'skip'.
            Defaults to 'wmo'.

        min_valid_values (int, optional):
            Minimum number of valid values required if
            na_handling is 'at_least_n'.

        tolerance (float, optional):
            Allowed missing percentage if na_handling is 'pct'.

        anomaly (str, optional):
            Type of anomaly calculation ('absolute', 'perc', or None).

        significance (bool, optional):
            If True, perform a significance t-test for anomalies.
            Defaults to False.

        sig_alpha (float, optional):
            Significance level for the t-test. Defaults to 0.05.

        average (bool, optional):
            If True, compute the average over the full period block.
            Defaults to False.

    Returns:
        Dict[Tuple[datetime.date, datetime.date], :class:`xarray.Dataset`]:
            Dictionary mapping each processed period
            to its resulting lazy dataset.
    """
    # retrieve frequency and indicator from pre-initialized clindicator class
    frequency = clindicator.optional_args['freq']
    indicator = clindicator.name

    # Sanity checks
    if indicator not in indicator_data:
        raise ValueError(f"Indicator '{indicator}' is not available.")

    if anomaly and not ref_date_range:
        raise ValueError("You have specified to calculate the anomaly"
                         "and must provide a reference period"
                         "using --ref_date_range")

    # na handling
    # for further information check xclim documentation
    # https://xclim.readthedocs.io/en/latest/apidoc/xclim.core.html#module-xclim.core.missing
    from xclim.core import missing as xclim_missing

    na_dict = {
        "wmo": xclim_missing.missing_wmo,
        "any": xclim_missing.missing_any,
        "at_least_n": xclim_missing.at_least_n_valid,
        "pct": xclim_missing.missing_pct,
        "skip": None,
    }

    try:
        check_missing = na_dict[na_handling]
    except KeyError as e:
        raise ValueError(
            f"Invalid na_handling='{na_handling}'. "
            f"Must be one of {list(na_dict.keys())}"
        ) from e

    # shared call args
    missing_kwargs = {}

    if na_handling == "at_least_n":
        missing_kwargs["n"] = min_valid_values
    elif na_handling == "pct":
        missing_kwargs["tolerance"] = tolerance

    # ensure crs variable and save it for the result - dataset
    # --------------------------------------------------------

    # this retrieves the crs of the first dataset
    # possibly retrieve / check crs of all datasets in the future

    global_crs_var = None
    for ds in datasets:
        crs_name = get_crs_varname(ds)
        if crs_name:
            global_crs_var = ds[crs_name].copy()
            break

    # create ds_dict sorted by time slices and variable(s)
    # ----------------------------------------------------

    # nested dict for datasets
    ds_dict = defaultdict(dict)
    # list of date_ranges with types (target or reference)
    periods = []
    # variable names from datasets
    ds_varmapping = {}

    if date_ranges is None:
        date_ranges = [(None, None)]

    for i, ds in enumerate(datasets):
        ds_var = get_geodata_varnames(ds)[0]
        ds_varmapping[ds_var] = varnames[i] if varnames else ds_var
        # store reference period in data dict
        if anomaly:
            sd, ed = ref_date_range
            ref_period, slice_ = build_period_slice(ds, sd, ed, "reference")
            periods.append(ref_period)
            ds_dict[ref_period][ds_var] = slice_

        # store time ranges in dict
        for sd, ed in date_ranges:
            period, slice_ = build_period_slice(ds, sd, ed, "target")
            periods.append(period)
            ds_dict[period][ds_var] = slice_

    # percentiles in ds_dict
    if perc_dict:
        for period_key, perc_vars in perc_dict.items():
            if period_key in ds_dict:
                for p_var, p_ds in perc_vars.items():
                    ds_dict[period_key][p_var] = p_ds
                    ds_varmapping[p_var] = p_var

    # alignment and unifying chunks
    for period_key, var_dict in ds_dict.items():
        keys = [k for k, ds in var_dict.items() if "time" in ds.dims]
        datasets = [var_dict[k] for k in keys]

        if not datasets:
            continue

        try:
            unified = xr.unify_chunks(*datasets)
        except ValueError as err:
            logger.warning(
                f"Could not unify chunks for period {period_key}: {err}. "
                "Proceeding with independent rechunking."
            )
            unified = datasets

        # re-assign values
        for var_key, ds in zip(keys, unified, strict=True):
            var_dict[var_key] = ds

    if len(clindicator.input_vars.keys()) != \
       len(ds_varmapping.keys()):
        raise ValueError("The number of provided input datasets does not match"
                         "the required arguments for the climate indicator.")

    try:
        xclim_ind_name, xclim_attrs = clindicator.xclim_indicator_info
    except TypeError:
        xclim_ind_name, xclim_attrs = None, None

    # Set Metadata
    # ------------

    parameter_args = {}

    thresholds = clindicator.get_thresholds()
    operators = clindicator.get_operators()

    # inner dictionary of first time slice
    first_period_dict = next(iter(ds_dict.values()))

    ds_vars = first_period_dict.keys()
    ds_vals = first_period_dict.values()

    # threshold variable and attributes
    if thresholds:
        parameter_args["hasThreshold"] = True
        threshold_dataclasses = im.threshold_dataclasses(
            thresholds,
            operators,
            list(ds_vars),
            list(ds_vals),
            xclim_ind_name
        )
    else:
        threshold_dataclasses = None

    # spell length variable and attributes
    duration = clindicator.get_duration()
    if duration:
        parameter_args["isSpelllength"] = True
        duration_dataclasses = im.duration_dataclasses(duration)
    else:
        duration_dataclasses = None

    # global and variable attributes
    global_attrs = im.get_global_attrs(indicator, list(ds_vars), xclim_attrs)
    index_attrs = im.get_variable_attrs(indicator, xclim_attrs)

    if "long_name*" in index_attrs:
        parameter_args["long_name"] = index_attrs["long_name"]

    if (param_string := im.get_parameter_attr(
            clindicator.optional_args,
            **parameter_args)) is not None:
        index_attrs["parameters"] = param_string

    duration = clindicator.get_duration()
    duration_dataclasses = (im.duration_dataclasses(duration) if duration
                            else None)

    # actual indicator calculation and na - masking
    # ---------------------------------------------

    clind_results = {}

    for trange in periods:
        ds_select = ds_dict[trange]
        da_masks = {}
        indicator_call_args = {}

        for req_param in clindicator.input_vars.keys():

            # retrieve data array for required arguments
            var_match = process.extractOne(
                req_param,
                list(ds_varmapping.values())
            )[0]
            ds_varname = next((k for k, v in ds_varmapping.items()
                               if v == var_match), None)
            ds_match = ds_select[ds_varname]

            # missing value handling
            if na_handling == "skip" or "per" in req_param:
                pass
            else:
                da_masks[ds_varname] = check_missing(
                    ds_match[ds_varname],
                    freq=frequency,
                    **missing_kwargs
                )
            indicator_call_args[req_param] = ds_match[ds_varname]

        # to avoid chunk misalignment, fix chunks here
        for k, arr in indicator_call_args.items():
            chunk_dict = {}

            # time chunking (only if time dimension exists)
            if "time" in arr.dims:
                time_dim = arr.sizes.get("time", 0)
                if time_dim:
                    min_time_chunk = 2000
                    chunk_dict["time"] = min(min_time_chunk, time_dim)

            # spatial chunking
            spatial_dims = get_projection_yx_varnames(arr)
            for d in spatial_dims:
                chunk_dict[d] = 50

            # apply chunking only if needed
            if chunk_dict:
                arr = arr.chunk(chunk_dict)

            indicator_call_args[k] = arr

        # core calculation (Lazy Dask Graph)
        clind_results[trange] = clindicator(**indicator_call_args)

        if na_handling != "skip":
            combined_mask = xr.zeros_like(clind_results[trange], dtype=bool)
            for mask in da_masks.values():
                combined_mask = combined_mask | mask
            clind_results[trange] = clind_results[trange].where(~combined_mask)

        clind_results[trange] = clind_results[trange].rename(indicator)

    # Post-Processing: averaging, anomalies, significance
    # ---------------------------------------------------

    targets = [p for p in periods if p.role == "target"]

    if anomaly:
        ref_period = next(p for p in clind_results if p.role == "reference")
        da_ref = clind_results[ref_period]

    if significance and anomaly:
        logger.info(f"Performing significance test with alpha = {sig_alpha}")
        sig_mask = {}
        for period in targets:
            da = clind_results[period]
            sig_mask[period] = im.significance_mask(
                da_ref,
                da,
                frequency,
                sig_alpha
            )
    else:
        sig_mask = dict.fromkeys(clind_results, None)

    # Trigger warning
    if significance and not anomaly:
        logger.warning(
            "Significance tests can only be performed"
            "if the 'anomaly' option is enabled."
            "Please set '--anomaly' to True"
            "before running the significance test."
        )

    # average over period
    if average:
        clind_results = {tr: im.average_over_period(data, frequency)
                         for tr, data in clind_results.items()}

    ofreq = im.get_output_frequency(
        frequency,
        average=average,
        anomaly=anomaly
    )
    final_output_datasets = {}

    # create output dataset
    # ---------------------

    for period in targets:
        if anomaly:
            if index_attrs.get("units_metadata"):
                index_attrs["units_metadata"] = "temperature: difference"

            # Calculate anomaly between two results
            # first date_range item is always reference period
            da = clind_results[period]
            da_ref = clind_results[ref_period]
            percentage = (anomaly == "perc")

            if average:
                result = da - da_ref
                if percentage:
                    result = (result / da_ref) * 100
            else:
                result = im.anomaly_over_period(
                    da,
                    da_ref,
                    frequency,
                    percentage
                )
        else:
            result = clind_results[period]

        ds_out = im.create_dataset(
            result,
            var_attrs=index_attrs,
            global_attrs=global_attrs,
            thresholds=threshold_dataclasses,
            durations=duration_dataclasses,
            significance=sig_mask[period]
        )

        sd, ed = period.start.date(), period.end.date()
        ds_out = im.set_time_labels_and_bounds(ds_out, ofreq, sd, ed)
        ds_out = add_crs_to_dataset(ds_out, global_crs_var)
        final_output_datasets[(sd, ed)] = ds_out

    return final_output_datasets


# --------------------------------------------------------------------------- #
#  Command‑line entry point
# --------------------------------------------------------------------------- #
def main(args: list[str] | None = None) -> None:
    """
    Main entrypoint for the command-line interface (CLI).
    Parses arguments, executes the calculation,
    and writes the output NetCDF files.
    """
    from pyku.clix.cli import parse_cli

    if args is None:
        # No args passed -> parse from sys.argv
        args = parse_cli()

    elif isinstance(args, list):
        # If a list of args is passed, parse them
        args = parse_cli(args)

    elif not isinstance(args, argparse.Namespace):
        raise TypeError(
            f"args must be None, a list of strings, or argparse.Namespace, "
            f"got {type(args).__name__}"
        )

    logger.setLevel(level=logging.INFO)
    start_runtime = time.perf_counter()

    # start dask cluster
    client, cluster = start_dask_cluster(args)

    if all(v == 'yaml' for v in args.input.values()):
        ifiles = im.validate_and_get_files_from_yaml_content(args.input)
    else:
        ifiles = im.get_files(args.input)

    indicator = args.subcommand
    params = vars(getattr(args, indicator))

    clindicator = im.ClimateIndicator(indicator, args.frequency, params)
    ifiles = im.sort_files_by_xclim_order(
            ifiles,
            clindicator.input_vars,
            args.varnames
    )

    base_datasets = _open_datasets(ifiles)

    perc_dict = None

    if clindicator.is_perc_indicator:
        if args.input_perc is not None:
            input_modes = set(args.input.values())
            if input_modes == ["yaml"]:
                ifiles_perc = \
                    im.validate_and_get_files_from_yaml_content(
                        args.input_perc
                        )
            elif input_modes <= {"file", "folder"}:
                ifiles_perc = im.get_files(args.input_perc)
        else:
            # Backup, if no percentiles files provided use input files
            ifiles_perc = ifiles
            if args.percentile:
                logger.info("Using input file(s) to calculate"
                            f"{args.percentile}th percentile for"
                            f"climate indicator {indicator}.")
            else:
                raise ValueError("Using input files for percentile calculation"
                                 "but no percentile value provided."
                                 "Aborting...")

        perc_dict = compute_percentiles(
                ifiles_perc=ifiles_perc,
                date_ranges=args.date_range or [(None, None)],
                perc_date_ranges=args.perc_date_range or args.date_range,
                percentile=args.percentile,
                perc_freq=args.percentile_freq,
                varnames=args.varnames
            )
        perc_dict = _persist_nested(perc_dict)
        from dask.distributed import wait
        wait([v for outer in perc_dict.values() for v in outer.values()])

    # call core function to calculate indicator
    results = run_tool_from_datasets(
        datasets=base_datasets,
        indicator=indicator,
        frequency=args.frequency,
        clindicator=clindicator,
        date_ranges=args.date_range or [(None, None)],
        ref_date_range=args.ref_date_range or [(None, None)],
        perc_dict=perc_dict,
        varnames=args.varnames,
        na_handling=args.check_missing,
        min_valid_values=args.min_valid_values,
        tolerance=args.allowed_miss_pct,
        anomaly=args.anomaly,
        significance=args.significance,
        sig_alpha=args.alpha,
        average=args.average
    )

    # write netcdf file
    logger.info("writing indicators to netcdf file...")
    for period, ds_out in results.items():
        sd, ed = period

        if args.anomaly:
            ofreq = im.get_output_frequency(
                args.frequency,
                average=args.average,
                anomaly=args.anomaly,
            )
            ofile = f"{indicator}_{ofreq}_anomaly_{sd:%Y%m%d}-{ed:%Y%m%d}.nc"
        else:
            ofreq = im.get_output_frequency(
                args.frequency,
                average=args.average,
                anomaly=None,
            )
            ofile = f"{indicator}_{ofreq}_{sd:%Y%m%d}-{ed:%Y%m%d}.nc"

        if args.ofile and len(args.date_range or [(None, None)]) == 1:
            ofile = args.ofile

        logger.info(f"Save results for {sd:%Y%m%d} to {ed:%Y%m%d} as {ofile}")

        ds_out.to_netcdf(ofile)

    if client:
        client.close()
    if cluster:
        cluster.close()

    runtime = time.perf_counter() - start_runtime
    minutes, seconds = divmod(runtime, 60)

    logger.info("Calculation for climate indicator finished")
    logger.info(f"Runtime: {int(minutes)} min {seconds:.1f} sec")


if __name__ == "__main__":
    import re
    import sys
    from multiprocessing import freeze_support

    freeze_support()
    sys.argv[0] = re.sub(r"(-script\.pyw|\.exe)?$", "", sys.argv[0])
    main(sys.argv[1:])
