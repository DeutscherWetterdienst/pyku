#!/usr/bin/env python3

"""
Pyku magic module

This modules redefines default parameters to fit the most common use when
working with climate data.
"""

from . import logger


def sorcery(ds):

    """
    Evil-magically makes datasets good. The evil_magic function attempts to
    auto-magically:

    * process datetimes reference to the lower bound of the time boundaries
    * process variable names towards CMOR standard
    * process units to SI units
    * sort geographical and projection coordinates from top to bottom and
      left to right

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`xarray.Dataset`: Magicked dataset
    """

    import pyku.drs as drs
    import pyku.timekit as timekit

    ds = timekit.to_gregorian_calendar(ds)
    ds = drs.to_cmor_varnames(ds)
    ds = drs.to_cmor_units(ds)
    ds = drs.to_cmor_attrs(ds)

    return ds


def open_mfdataset(files, option='auto'):

    """
    The xarray.open_mfdataset with default options for climate data

    Arguments:
        files (List[str]): The files to be open
        option (str): standardized optional parameters.
            Defaults to 'auto'

    Returns
        :classe:``xarray.Dataset``: Dataset
    """

    import xarray as xr

    logger.warn("Experimental")

    if option not in ['auto']:
        raise Exception("Only option='auto' is implemented")

    if option in ['auto']:
        ds = xr.open_mfdataset(
            files,
            concat_dim="time",
            combine="nested",
            data_vars='minimal',
            coords='minimal',
            compat='override'
        )

        return ds


def to_netcdf(ds, output_file, encoding='auto', complevel=None):

    """
    Write netcdf with climate data custom encoding

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
        output_file (str): Output file.
        encoding: Optional, defaults to ``auto``. one of ``{'auto', 'cmor'}``.
            If set to ``'cmor'``, the time encoding ``'units'`` key is set to
            ``'units': 'days since 1949-12-01T00:00:00Z'`` in conformance with
            the CMOR standar. If set to ``auto``, a pyku-default uncompressed
            encoding is used.
            http://is-enes-data.github.io/cordex_archive_specifications.pdf
    """

    import pyku.meta as meta

    if encoding not in ['auto', 'cmor']:
        raise Exception(
            "Parameter 'encoding' should be 'auto' or 'cmor'. Consider using "
            "xarray to_netcdf() function instead to use a custom encoding."
        )

    encoding = {}

    # Set encoding for time variables
    # -------------------------------

    if 'time' in ds.coords.keys():

        # Get the default from the original data
        # --------------------------------------

        if ds['time'].encoding.get('calendar') is not None:
            encoding.setdefault('time', {})['calendar'] = \
                ds['time'].encoding.get('calendar')
        else:
            encoding.setdefault('time', {})['calendar'] = \
                ds['time'].dt.calendar

        if ds['time'].encoding.get('units') is not None:
            encoding.setdefault('time', {})['units'] = \
                ds['time'].encoding.get('units')

        # Sanity check
        if encoding['time'].get('calendar') is None:
            raise Exception('Sanity check: No calendar for time ?!!!')

        if encoding['time'].get('units') is None:
            encoding.setdefault('time', {})['units'] = \
                'days since 1949-12-01T00:00:00Z'

        if encoding in ['cmor']:
            encoding.setdefault('time', {})['units'] = \
                'days since 1949-12-01T00:00:00Z'

        encoding['time']['dtype'] = 'float64'

    if meta.has_time_bounds(ds):

        time_bounds_var = meta.get_time_bounds_varname(ds)

        encoding.setdefault(time_bounds_var, {})['calendar'] = \
            encoding['time']['calendar']

        encoding.setdefault(time_bounds_var, {})['units'] = \
            encoding['time']['units']

        encoding[time_bounds_var]['dtype'] = 'float64'

    for var_name, da in ds.data_vars.items():
        if not ds[var_name].shape:
            continue
        encoding.setdefault(var_name, {})['chunksizes'] = ds[var_name].shape

    for coord_name, coord in ds.coords.items():
        encoding.setdefault(coord_name, {})['chunksizes'] = \
            ds[coord_name].shape

    # Set compression level
    # ---------------------

    if complevel is not None:
        for varname in ds.pyku.get_geodata_varnames():
            encoding.setdefault(varname, {})['dtype'] = 'float32'
            encoding.setdefault(varname, {})['zlib'] = True
            encoding.setdefault(varname, {})['complevel'] = complevel

    # Clear original encoding
    # -----------------------

    # This step ensures the encoding of the original data is cleared.
    # The original data might be compressed or chunked differently
    # based on the variables, which needs standardization.

    ds.encoding.clear()
    for var in ds.data_vars:
        ds[var].encoding.clear()

    # Unchunk the dataset
    # -------------------

    # The dataset should be uncompressed and in one chunk

    ds = ds.chunk(chunks=-1)

    # Set fill values
    # ---------------

    # This could use some work to be bettered.

    if 'lon' in ds.coords.keys():
        encoding['lon'] = {'_FillValue': None}

    if 'lat' in ds.coords.keys():
        encoding['lat'] = {'_FillValue': None}

    if 'rlon' in ds.coords.keys():
        encoding['rlon'] = {'_FillValue': None}

    if 'rlat' in ds.coords.keys():
        encoding['rlat'] = {'_FillValue': None}

    if 'rotated_pole' in ds.data_vars:
        encoding['rotated_pole'] = {
            'dtype': 'str'
        }

    # Write data to NetCDF
    # --------------------

    ds.to_netcdf(
        f"{output_file}",
        'w',
        encoding=encoding,
        unlimited_dims=['time']
    )


def to_zarr(ds, output_file, encoding='auto'):

    """
    Write netcdf with climate data custom encoding

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
        output_file (str): Output file.
        encoding: Optional, defaults to ``auto``. one of ``{'auto', 'cmor'}``.
            If set to ``'cmor'``, the time encoding ``'units'`` key is set to
            ``'units': 'days since 1949-12-01T00:00:00Z'`` in conformance with
            the CMOR standar.
            http://is-enes-data.github.io/cordex_archive_specifications.pdf
    """

    import pyku.meta as meta
    import warnings

    warnings.filterwarnings(
        "ignore",
        # category=UserWarning,
        message=".*chunk_store is not yet implemented.*"
    )

    if encoding not in ['auto', 'cmor']:
        raise Exception(
            "Parameter 'encoding' should be 'auto' or 'cmor'. Consider using "
            "xarray to_netcdf() function instead to use a custom encoding."
        )

    encoding = {}

    # Set encoding for time variables
    # -------------------------------

    if 'time' in ds.coords.keys():

        # Get the default from the original data
        # --------------------------------------

        if ds['time'].encoding.get('calendar') is not None:
            encoding.setdefault('time', {})['calendar'] = \
                ds['time'].encoding.get('calendar')
        else:
            encoding.setdefault('time', {})['calendar'] = \
                ds['time'].dt.calendar

        if ds['time'].encoding.get('units') is not None:
            encoding.setdefault('time', {})['units'] = \
                ds['time'].encoding.get('units')

        # Sanity check
        if encoding['time'].get('calendar') is None:
            raise Exception('Sanity check: No calendar for time ?!!!')

        if encoding['time'].get('units') is None:
            encoding.setdefault('time', {})['units'] = \
                'days since 1949-12-01T00:00:00Z'

        if encoding in ['cmor']:
            encoding.setdefault('time', {})['units'] = \
                'days since 1949-12-01T00:00:00Z'

        encoding['time']['dtype'] = 'float64'

    if meta.has_time_bounds(ds):

        time_bounds_var = meta.get_time_bounds_varname(ds)

        encoding.setdefault(time_bounds_var, {})['calendar'] = \
            encoding['time']['calendar']

        encoding.setdefault(time_bounds_var, {})['units'] = \
            encoding['time']['units']

        encoding[time_bounds_var]['dtype'] = 'float64'

    # Clear original encoding
    # -----------------------

    # This step ensures the encoding of the original data is cleared.
    # The original data might be compressed or chunked differently
    # based on the variables, which needs standardization.

    ds.encoding.clear()
    for var in ds.data_vars:
        ds[var].encoding.clear()

    # Set fill values
    # ---------------

    # This could use some work to be bettered.

    if 'lon' in ds.coords.keys():
        encoding['lon'] = {'_FillValue': None}

    if 'lat' in ds.coords.keys():
        encoding['lat'] = {'_FillValue': None}

    if 'rlon' in ds.coords.keys():
        encoding['rlon'] = {'_FillValue': None}

    if 'rlat' in ds.coords.keys():
        encoding['rlat'] = {'_FillValue': None}

    if 'rotated_pole' in ds.data_vars:
        encoding['rotated_pole'] = {
            'dtype': 'str'
        }

    # Write data to NetCDF
    # --------------------

    ds.to_zarr(
        f"{output_file}",
        'w',
        encoding=encoding,
        # unlimited_dims=['time'],
        # consolidated=True
    )
