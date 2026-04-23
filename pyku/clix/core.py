#!/usr/bin/env python3

"""
CLIX - Climate indicators at DWD
Climate indicator tool based on the xclim library
Authors: Harald Rybka, Birgit Mannig
"""

import logging
import os
import time

import metpy  # noqa: F401  # required to enable xarray .metpy accessor
import pandas as pd
import xarray as xr
from dask.distributed import Client, LocalCluster
from rapidfuzz import process
from xclim.core.calendar import percentile_doy

from .. import logger
import pyku.drs as drs
from pyku.meta import (
    get_geodata_varnames,
    has_time_bounds,
    get_crs_varname
)
from pyku.timekit import (
    set_time_bounds_from_time_labels,
    to_gregorian_calendar
)
# from pyku.check import check_variables_role

from pyku.clix import manager as im
from pyku.clix.cli import parse_cli
from pyku.clix.custom_indicators import (
    expand_percentiles_to_daily,
    percentile_grouped
)
from . import indicator_data


# This is necessary to avoid warning using open_mfdataset
# for a future new version of xarray
# xr.set_options(use_new_combine_kwarg_defaults=True)


def main(args=None):

    """
    Main entrypoint.
    Args can be a namespace or a list of CLI args.
    """

    if args is None:
        # No args passed -> parse from sys.argv
        args = parse_cli()
    elif isinstance(args, list):
        # If a list of args is passed, parse them
        args = parse_cli(args)
    # else assume it's already an argparse.Namespace

    # Set logger level
    logger.setLevel(level=logging.INFO)

    if all(v == 'yaml' for v in args.input.values()):
        ifiles = im.validate_and_get_files_from_yaml_content(args.input)
    else:
        ifiles = im.get_files(args.input)

    indicator = args.subcommand
    params = vars(getattr(args, indicator))  # get namespace as dict
    frequency = args.frequency

    # Optional
    date_ranges = args.date_range
    average = args.average
    anomaly = args.anomaly
    ref_date_range = args.ref_date_range
    varnames = args.varnames
    na_handling = args.check_missing

    # Percentile options
    perc_date_ranges = args.perc_date_range or args.date_range
    percentile = args.percentile
    perc_freq = args.percentile_freq

    # Significance test options
    significance = args.significance
    sig_alpha = args.alpha

    # Missing values
    if na_handling == 'wmo':
        from xclim.core.missing import missing_wmo as check_missing
    elif na_handling == 'any':
        from xclim.core.missing import missing_any as check_missing
    elif na_handling == 'at_least_n':
        from xclim.core.missing import at_least_n_valid as check_missing
        if args.min_valid_values is None:
            logger.error("Argument --min_valid_values is required when --check_missing=at_least_n")  # noqa
        else:
            min_valid_values = args.min_valid_values
    elif na_handling == 'pct':
        from xclim.core.missing import missing_pct as check_missing
        if args.allowed_miss_pct is None:
            logger.error("Argument --allowed_miss_perc is required when --check_missing=at_least_n")  # noqa
        else:
            tolerance = args.allowed_miss_pct
    else:
        logger.error(f"Unknown check_missing method: {args.check_missing}")

    # Sanity checks
    available_indicators = list(indicator_data.keys())
    if indicator not in available_indicators:
        logger.error(f"Indicator not available. The following indicators can be chosen: {' '.join(available_indicators)}")  # noqa
        exit()

    if args.ofile and len(date_ranges) > 1:
        logger.warning(f'You have set an output filename and specified multiple date ranges! Automatic filenames are produced and the given output filename neglected!')  # noqa
        args.ofile = None

    # Settings if reference period is used
    if anomaly and not ref_date_range:
        raise ValueError(f'You have specified to calculate the anomaly and must provide a reference period using --ref_date_range')  # noqa
    elif anomaly and ref_date_range:
        date_ranges.insert(0, ref_date_range)

    # Initiate ClimateIndicator class
    clindicator = im.ClimateIndicator(indicator, frequency, params)

    # Sort files in order for xclim call
    ifiles = im.sort_files_by_xclim_order(
        ifiles,
        clindicator.input_vars,
        varnames
    )

    # Set start time of program execution
    start_runtime = time.time()

    # Start a remote Dask cluster
    if args.dask_cluster:
        client = Client(args.dask_cluster)

    # Start a local Dask cluster with automatic port selection
    if args.workers > 0 and not args.dask_cluster:
        mem_limit = f'{args.memory_limit}GB'
        cluster = LocalCluster(
            n_workers=args.workers,
            threads_per_worker=1,
            memory_limit=mem_limit,
        )
        client = Client(cluster)

        host = os.environ.get('HOSTNAME')
        port = client.dashboard_link.split(':')[-1]
        logger.info(f'The dashboard is located under: {host}:{port} using {args.workers} workers and {args.memory_limit}GB as the memory limit per worker.')  # noqa

    # Part of opening files and small preprocessing
    # ---------------------------------------------
    time_chunk = 5000
    ds_dict = {}
    ds_varmapping = {}
    crs_var = None
    for i, files in enumerate(ifiles):
        # probably include data_vars='all' or 'minimal' in the future needed
        ds = xr.open_mfdataset(
            files, chunks={'time': time_chunk}, parallel=True)
        ds = ds.unify_chunks()
        ds = drs.to_cmor_units(ds)
        ds = to_gregorian_calendar(ds, add_missing=True)

        # Check for CRS variable
        crs_varname = get_crs_varname(ds)
        if crs_varname:
            crs_var = ds[crs_varname]

        # Derive variable name(s) from dataset automatically
        ds_var = get_geodata_varnames(ds)[0]
        ds_varmapping[ds_var] = varnames[i] if varnames else ds_var

        # Compact solution handling date_ranges or None
        for idx, (sd, ed) in enumerate(date_ranges):
            _sd = sd or pd.to_datetime(ds.time.values[0]).strftime('%Y%m%d')  # noqa
            _ed = ed or pd.to_datetime(ds.time.values[-1]).strftime('%Y%m%d')  # noqa
            slice_ = ds.sel(time=slice(_sd, _ed))

            if 'time' in slice_.sizes and slice_.sizes['time'] == 0:
                logger.error(f'The dataset does not contain a time variable or the length of the time variable is zero. Please check that the date range of the input files!') # noqa
                exit()

            ds_dict.setdefault((_sd, _ed), {})[ds_var] = slice_

            # Set date_ranges variable for later use (if not set)
            if (sd, ed) == (None, None):
                date_ranges[idx] = (_sd, _ed)

            # Percentile calculation
            if clindicator.is_perc_indicator:
                if all(v == 'yaml' for v in args.input.values()):
                    ifiles_perc = \
                        im.validate_and_get_files_from_yaml_content(
                            args.input_perc)
                elif all(v in {"file", "folder"}
                         for v in args.input.values()):
                    ifiles_perc = im.get_files(args.input_perc)
                else:
                    # Backup, if no percentiles files provided use input files
                    ifiles_perc = ifiles
                    if args.percentile:
                        logger.info(f'Using input file(s) to calculate {percentile}th percentile for climate indicator {indicator}.')  # noqa
                    else:
                        logger.error('Using input files for percentile calculation but no percentile value provided. Aborting...')  # noqa
                        exit()

                for i, files in enumerate(ifiles_perc):
                    # tbd include data_vars='all' or 'minimal' in the future?
                    ds = xr.open_mfdataset(files, chunks={'time': time_chunk},
                                           parallel=True)
                    ds = ds.unify_chunks()
                    ds = drs.to_cmor_units(ds)

                    ds = to_gregorian_calendar(ds, add_missing=True)

                    # Derive variable name(s) from dataset automatically
                    ds_var_perc = get_geodata_varnames(ds)[0]
                    ds_varmapping[f'{ds_var_perc}_per'] = \
                        varnames[i] if varnames else f'{ds_var_perc}_per'  # noqa

                    if perc_date_ranges == date_ranges:
                        perc_slice_ = slice_
                    else:
                        for sd_perc, ed_perc in perc_date_ranges or [(None, None)]:  # noqa
                            _sd_perc = sd_perc or pd.to_datetime(ds.time.values[0]).strftime('%Y%m%d')  # noqa
                            _ed_perc = ed_perc or pd.to_datetime(ds.time.values[-1]).strftime('%Y%m%d')  # noqa
                            perc_slice_ = ds.sel(time=slice(_sd_perc, _ed_perc))  # noqa

                            logger.info(f'Computing percentile thresholds based on variable {ds_var_perc} for the period {_sd_perc, _ed_perc} over a frequency of {perc_freq}.')  # noqa

                    if 'time' in perc_slice_.sizes \
                       and perc_slice_.sizes['time'] == 0:
                        logger.error('The dataset to compute does not contain a time variable or the length of the time variable is zero. Please check  the date range of the input files!')  # noqa
                        exit()

                    if perc_freq in ['YS', 'MS', 'QS-DEC']:
                        arr_perc = percentile_grouped(
                            perc_slice_[ds_var_perc],
                            group_freq=perc_freq,
                            per=percentile,
                            climatology=True
                        )

                        arr_perc = expand_percentiles_to_daily(
                            slice_, arr_perc, perc_freq)
                    else:
                        from pandas.tseries.frequencies import to_offset
                        ndays = to_offset(perc_freq).n
                        arr_perc = percentile_doy(
                            perc_slice_[ds_var_perc],
                            per=percentile,
                            window=ndays
                        )

                    ds_dict.setdefault((_sd, _ed), {})[f'{ds_var_perc}_per'] = \
                        arr_perc.to_dataset(name=f'{ds_var_perc}_per')  # noqa

    # Chunk aligning and checking time labels
    for period_key, var_dict in ds_dict.items():
        datasets = list(var_dict.values())

        # Filter percentile datasets that have "dayofyear" coordinates
        datasets = [ds for ds in datasets if "dayofyear" not in ds.coords]

        # Step 1: Check if all time coordinates match the first one
        ref_time = datasets[0].time
        all_aligned = all(ds.time.equals(ref_time) for ds in datasets)

        if not all_aligned:
            logger.warning(f"Time misalignment in group '{period_key}', flooring all times to daily.")  # noqa
            datasets = [ds.assign_coords(time=ds.time.dt.floor('1D'))
                        for ds in datasets]

        # Step 2: Include time bounds labels
        for ds in datasets:
            if has_time_bounds(ds):
                ds = ds.drop_vars('time_bnds')
            ds = set_time_bounds_from_time_labels(ds)

        # Step 3: Re-unify chunks with minimum time chunksize
        unified = xr.unify_chunks(*datasets)
        min_time_chunk = 5000
        time_dim = unified[0]["time"].size
        time_chunks = min(min_time_chunk, time_dim)
        rechunked_datasets = []
        for unified_dataset in unified:
            rechunked_datasets.append(unified_dataset.chunk({"time": time_chunks}))  # noqa

        # Step 4: Reassign to var_dict
        for var_key, ds_unified in zip(var_dict.keys(), rechunked_datasets):
            var_dict[var_key] = ds_unified

    if len(clindicator.input_vars.keys()) != \
       len(ds_varmapping.keys()):
        raise ValueError('The number of provided input datasets does not match the required arguments for the climate indicator.')  # noqa

    try:
        xclim_ind_name, xclim_attrs = clindicator.xclim_indicator_info
    except TypeError:
        xclim_ind_name = None
        xclim_attrs = None

    # Thresholds
    # ----------

    parameter_args = {}

    thresholds = clindicator.get_thresholds()
    operators = clindicator.get_operators()

    # Get any keys and values (DataArrays) of ds_dict
    ds_vars = next(iter(ds_dict.values())).keys()
    ds_vals = next(iter(ds_dict.values())).values()

    if thresholds:
        parameter_args['hasThreshold'] = True
        threshold_dataclasses = im.threshold_dataclasses(
            thresholds,
            operators,
            list(ds_vars),
            list(ds_vals),
            xclim_ind_name
        )

    else:
        threshold_dataclasses = None

    # Duration
    duration = clindicator.get_duration()
    if duration:
        parameter_args['isSpelllength'] = True
        duration_dataclasses = im.duration_dataclasses(duration)
    else:
        duration_dataclasses = None

    # Global attributes
    global_attrs = im.get_global_attrs(
        indicator, list(ds_vars),  xclim_attrs)

    # Variable attributes
    index_attrs = im.get_variable_attrs(indicator, xclim_attrs)

    if 'long_name*' in index_attrs:
        parameter_args['long_name'] = index_attrs['long_name']
    if (param_string := im.get_parameter_attr(clindicator.optional_args, **parameter_args)) is not None:  # noqa
        index_attrs["parameters"] = param_string

    clind_results = {}
    # Start looping over all date_ranges (or full dataset timerange)
    param_name = {}
    for idx, trange in enumerate(date_ranges):
        ds_select = ds_dict[trange]
        da_masks = {}

        # This section defines the input xr.DataArrays of the dataset
        # for the xclim function call
        for req_param in clindicator.input_vars.keys():
            var_match = process.extractOne(req_param,
                                           ds_varmapping.values())[0]

            ds_varname = next((k for k, v in ds_varmapping.items()
                               if v == var_match), None)
            ds_match = ds_select[ds_varname]

            # Set parameter name according to xclim parameter name
            if req_param not in param_name:
                param_name[req_param] = \
                    next((k for k, v in clindicator.required_args.items()
                          if v is req_param), None)

            # Missing Values mask (skip for percentile inputs):
            if na_handling == 'at_least_n' and 'per' not in req_param:
                da_masks[ds_varname] = check_missing(ds_match[ds_varname],
                                                     freq=frequency,
                                                     n=min_valid_values)
            elif na_handling == 'pct' and 'per' not in req_param:
                da_masks[ds_varname] = check_missing(ds_match[ds_varname],
                                                     freq=frequency,
                                                     tolerance=tolerance)
            elif na_handling != 'skip' and 'per' not in req_param:
                da_masks[ds_varname] = check_missing(ds_match[ds_varname],
                                                     freq=frequency)

            clindicator.required_args[param_name[req_param]] = \
                ds_match[ds_varname]

        # Call climate indicator function
        clind_results[trange] = clindicator()

        # Apply missing value mask
        if na_handling != 'skip':
            combined_mask = xr.zeros_like(clind_results[trange], dtype=bool)
            for mask in da_masks.values():
                combined_mask = combined_mask | mask
            clind_results[trange] = clind_results[trange].where(~combined_mask)

        # Rename DataArray to indicator name!
        clind_results[trange] = clind_results[trange].rename(indicator)

    # Perform t-Test
    sig_mask = {}
    if significance and anomaly:
        logger.info(f"Performing significance test with alpha = {sig_alpha}")
        for idx, (sd, ed) in enumerate(date_ranges[1:], start=1):
            # First date_range item is always reference period
            da = clind_results[(sd, ed)]
            da_ref = clind_results[date_ranges[0]]
            sig_mask[(sd, ed)] = im.significance_mask(da_ref, da, frequency, sig_alpha)  # noqa
    else:
        sig_mask = {tr: None for tr, data in clind_results.items()}

    # Trigger warning
    if significance and not anomaly:
        logger.warning(
            "Significance tests can only be performed if the 'anomaly' option is enabled. "  # noqa
            "Please set '--anomaly' to True before running the significance test."  # noqa
        )

    # Calculate average over period
    if average:
        clind_results = {
            tr: im.average_over_period(data, frequency)
            for tr, data in clind_results.items()
        }

    # Get correct output frequency
    ofreq = im.get_output_frequency(
        frequency,
        average=average,
        anomaly=anomaly
    )

    # Stem facets for output: {indicator}_{ofreq}_{start_date}-{end_date}
    for idx, (sd, ed) in enumerate(date_ranges):
        if anomaly:
            # Skip first date_range entry because it's the reference period
            if idx == 0:
                continue
            # fix units_metadata attribute
            units_metadata = index_attrs.get('units_metadata')
            if units_metadata:
                index_attrs['units_metadata'] = 'temperature: difference'

            # Calculate anomaly between two results
            # first date_range item is always reference period
            da = clind_results[(sd, ed)]
            da_ref = clind_results[date_ranges[0]]

            percentage = False
            if anomaly == 'perc':
                percentage = True

            if average:
                result = da-da_ref
                if percentage:
                    result = result/da_ref*100
            else:
                result = im.anomaly_over_period(da, da_ref, frequency,
                                                percentage)

            # Set output filename
            ofile = '_'.join([indicator, ofreq,
                              anomaly, f'{sd}-{ed}'])+'.nc'
        else:

            result = clind_results[(sd, ed)]

            # Set output filename
            if not args.ofile:
                ofile = '_'.join([indicator, ofreq,
                                  f'{sd}-{ed}'])+'.nc'
            else:
                ofile = args.ofile

        # Include grid mapping attribute if CRS is available
        if crs_var:
            result.attrs['grid_mapping'] = crs_varname

            crs_wkt = crs_var.attrs.get("crs_wkt") or \
                crs_var.attrs.get("spatial_ref")

            if crs_wkt:
                result.attrs['esri_pe_string'] = crs_wkt

        ds = im.create_dataset(
            result,
            var_attrs=index_attrs,
            global_attrs=global_attrs,
            thresholds=threshold_dataclasses,
            durations=duration_dataclasses,
            significance=sig_mask[(sd, ed)]
        )

        # Set time coordinates and bounds
        ds = im.set_time_labels_and_bounds(ds, ofreq, sd, ed)

        # Include CRS variable in dataset
        if crs_var:
            ds[crs_varname] = crs_var

        ds = ds.compute()
        # Save result as netCDF
        ds.to_netcdf(ofile)

    # Shut down the Dask client
    if args.workers > 0:
        client.close()
        if not args.dask_cluster:
            cluster.close()

    # Get time of program execution
    end_runtime = time.time()
    runtime = (end_runtime-start_runtime)/60.
    minutes = int(runtime)
    seconds = int((runtime - minutes) * 60)
    logger.info('Calculation for climate indicator finished.')
    logger.info(f"Runtime: {minutes} min {seconds} sec")


if __name__ == "__main__":

    from multiprocessing import freeze_support
    freeze_support()  # comment

    main()
