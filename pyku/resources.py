#!/usr/bin/env python3

"""
Resources accessible on-the-fly
"""

__all__ = [
    'list_polygon_identifiers'
]

import warnings
from zarr.errors import ZarrUserWarning

from pyku import logger
from pyku import PYKU_RESOURCES, PYKU_CONFIG

pyku_resources = PYKU_RESOURCES.load_resource('resources')

# Supress warnings
# ----------------

# ZarrUserWarning: Consolidated metadata is currently not part in the Zarr
# format 3 specification. It may not be supported by other zarr implementations
# and may change in the future.

# UnstableSpecificationWarning: The data type (NullTerminatedBytes(length=1))
# does not have a Zarr V3 specification. That means that the representation of
# arrays saved with this data type may change without warning in a future
# version of Zarr Python. Arrays stored with this data type may be unreadable
# by other Zarr libraries. Use this data type at your own risk! Check
# https://github.com/zarr-developers/zarr-extensions/tree/main/data-types for
# the status of data type specifications for Zarr V3.

warnings.filterwarnings(
    "ignore",
    category=ZarrUserWarning,
    message=".*Consolidated metadata.*"
)

warnings.filterwarnings(
    "ignore",
    message=".*does not have a Zarr V3 specification.*"
)


def _warn_if_default_data_dir():
    """
    Checks if the current data directory is the default and warns the user.
    """

    from pathlib import Path
    from pyku import PYKU_CONFIG

    default_data_dir = Path(PYKU_CONFIG.get('_data_dir')).resolve()
    current_path = Path(PYKU_CONFIG.get('data_dir'))
    current_data_dir = Path(current_path).resolve()

    if default_data_dir == current_data_dir:
        warnings.warn(
            "Data are being downloaded to the default directory: "
            f"{current_data_dir}. This may consume significant disk space. "
            "To specify a different location, set the 'PYKU_DATA_DIR' "
            "environment variable.",
            category=UserWarning,
            stacklevel=3
        )


def _warn_of_data_download(pooch_installer):
    """
    For a pooch installer, list the data downloading and send a warning.
    """

    from pathlib import Path

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    filenames = ", ".join(pooch_installer.registry.keys())

    warnings.warn(
        f"Downloading {filenames} from {pooch_installer.base_url}"
        f"to {pyku_data_dir}"
    )


def _pooch_download(base_url=None, archive_file=None, target_file=None,
                    checksum=None):

    """
    Download a file with pooch. This function is not part of the pyku API.

    Arguments:
        base_url (str): Data base url.
        archive_file (str): Name of the archive file
        target_file (str): Name of the target file after unpacking
        checksum (str): sha256sum
    """

    import xarray as xr
    from pathlib import Path
    import pooch
    from filelock import FileLock

    # Get the pyku data directory
    # --------------------------

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    # Create pooch installer
    # ----------------------

    pooch_installer = pooch.create(
        path=pyku_data_dir,
        base_url=base_url,
        registry={
            archive_file: checksum,
        }
    )

    # Check if the file is a zip archive
    # ----------------------------------

    is_zip = Path(archive_file).suffix in [".zip"]

    if is_zip:
        archive_file_list = pooch_installer.fetch(
            archive_file,
            processor=pooch.Unzip(),
        )

        target_file, = [
            file for file in archive_file_list if target_file in file
        ]

        return target_file

    # Handle file decompression and format conversion
    # ----------------------------------------------
    # Pooch.Decompress defaults to 'decomp', which xarray cannot parse.
    # We strip this suffix to ensure compatibility and convert to Zarr
    # to optimize performance for concurrent read operations.

    def to_zarr_processor(fname, action, pooch):
        """
        Pooch processor: Converts downloaded file to Zarr.
        Returns the path to the Zarr directory.
        """

        zarr_path = Path(fname).with_suffix('.zarr')

        if not zarr_path.exists():
            with xr.open_dataset(fname) as ds:
                ds.to_zarr(zarr_path, mode="w", consolidated=True)

        return zarr_path

    suffixes = Path(archive_file).suffixes
    is_netcdf = suffixes[-1] == ".nc"
    is_compressed_tarball = suffixes[-2:] == [".tar", ".gz"]
    is_compressed = (
        suffixes[-1] in [".bz2", ".gzip", ".xz"] and not is_compressed_tarball
    )

    if is_compressed:
        processor = pooch.Decompress(name=Path(archive_file).with_suffix(''))
    elif is_compressed_tarball:
        processor = pooch.Untar(extract_dir=Path(archive_file).stem)
    elif is_netcdf:
        processor = to_zarr_processor
    else:
        processor = None

    # Lock download to avoid fetching twice in parallel
    # -------------------------------------------------

    lock_path = Path(pyku_data_dir) / f"{archive_file}.lock"
    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)

    # Fetch and return dataset
    # ------------------------

    with FileLock(lock_path):
        file_path = pooch_installer.fetch(
            archive_file,
            processor=processor,
        )

    return file_path


def list_polygon_identifiers():

    """
    List polygon(s) identifiers

    Returns:

        list: List of available polygon identifiers.

    Examples:

        The function can be loaded and used at the module level:

        .. ipython::

           In [0]: import pyku.resources as resources
              ...: resources.list_polygon_identifiers()

        Alternatively, the function can be loaded and used at the *pyku* level:

        .. ipython::

           In [0]: import pyku
              ...: pyku.list_polygon_identifiers()
    """

    return list(PYKU_RESOURCES.get_keys('resources', 'polygons'))


def get_polygon_identifiers():

    """
    This function was renamed to
    :func:`pyku.resources.list_polygon_identifiers`
    """

    import warnings

    warnings.warn(
        "Function 'get_polygon_identifiers' is deprecated. Use "
        "'list_polygon_identifiers'",
        FutureWarning
    )

    return list_polygon_identifiers()


def get_geodataframe(identifier):

    """
    Get geodataframe from identifier

    Arguments:
        identifier (str): The polygon identifier.

    Returns:
        :class:`geopandas.GeoDataFrame`: The polygon(s).

    Example:

        .. ipython::
           :okwarning:

           In [0]: import pyku.resources as resources
              ...: resources.get_geodataframe('germany')
    """
    import importlib

    import geopandas as gpd

    # Sanity checks
    # -------------

    identifiers = list_polygon_identifiers()

    if identifier not in identifiers:
        message = f"{identifier} does not exist. Try one of {identifiers}"
        raise Exception(message)

    # Get data parameters
    # -------------------

    base_url = (
        PYKU_RESOURCES.get_value('resources',
                                 'polygons',
                                 identifier,
                                 'base_url',
                                 default=None)
    )

    archive_file = (
        PYKU_RESOURCES.get_value('resources',
                                 'polygons',
                                 identifier,
                                 'archive_file',
                                 default=None)
    )

    target_file = (
        PYKU_RESOURCES.get_value('resources',
                                 'polygons',
                                 identifier,
                                 'target_file',
                                 default=None)
    )

    # Cases where polygons are built on-the-fly from other polygons
    # -------------------------------------------------------------

    # These cases are explicitely built in pyku and therefore hard-coded by
    # necessity and design

    if identifier in ['german_directions']:
        return _get_german_directions()

    if identifier in ['natural_areas_of_germany_merged4']:
        return _get_natural_areas_of_germany_merged4()

    # Case where polygons are delivered with pyku
    # -------------------------------------------

    if base_url is None and archive_file is None and target_file is not None:
        return gpd.read_file(importlib.resources.files(
            'pyku.etc.geodata') / target_file
        )

    # Get polygon file, download if not alreay davailable
    # ---------------------------------------------------

    polygon_file = _pooch_download(
        base_url=base_url,
        archive_file=archive_file,
        target_file=target_file,
        checksum=None,
    )

    # Get geopandas dataframe
    # -----------------------

    polygons = gpd.read_file(polygon_file)

    # Query as necessary
    # ------------------

    query = pyku_resources.get('polygons').get(identifier).get('query', None)

    if query is not None:
        polygons = polygons.query(query)

    return polygons


def _get_natural_areas_of_germany_merged4():

    """
    Return polygons with german western, northern, eastern and southern states.

    Returns:
        :class:`geopandas.GeoDataFrame`: The output polygons.
    """

    import pandas as pd
    import geopandas as gpd

    # Define aggregation function for the NAME column
    # -----------------------------------------------

    # For the name column when aggregating, we merely want to have a ','
    # followed by a space.

    def join_names(names):
        return ', '.join(names)

    # Get GeoDataFrame with natural areas of Germany
    # ----------------------------------------------

    areas = get_geodataframe('natural_areas_of_germany')

    SOUTH = [
        'Suedwestdeutsche Mittelgebirge',
        'Alpen',
        'Alpenvorland'
    ]

    SOUTH = areas[
        areas['NAME'].isin(SOUTH)].dissolve(aggfunc={'NAME': join_names})

    SOUTH = SOUTH.reset_index()
    SOUTH['DIRECTION'] = 'South'

    EAST = [
        'Oestliche Mittelgebirge',
        'Ostdeutsche Becken und Huegel',
        'Zentrale Mittelgebirge und Harz'
    ]

    EAST = areas[
        areas['NAME'].isin(EAST)].dissolve(aggfunc={'NAME': join_names})
    EAST = EAST.reset_index()
    EAST['DIRECTION'] = 'East'

    NORTH = [
        'Nordostdeutsches Tiefland',
        'Nordwestdeutsches Tiefland'
    ]

    NORTH = areas[
     areas['NAME'].isin(NORTH)].dissolve(aggfunc={'NAME': join_names})
    NORTH = NORTH.reset_index()
    NORTH['DIRECTION'] = 'North'

    WEST = [
        'Linksrheinische Mittelgebirge',
        'Oberrheinisches Tiefland',
        'Rechtsrheinische Mittelgebirge',
        'Westdeutsche Tieflandsbucht'
    ]

    WEST = areas[
      areas['NAME'].isin(WEST)].dissolve(aggfunc={'NAME': join_names})
    WEST = WEST.reset_index()
    WEST['DIRECTION'] = 'West'

    directions = gpd.GeoDataFrame(pd.concat([
        SOUTH,
        EAST,
        NORTH,
        WEST
    ], ignore_index=True))

    return directions


def _get_german_directions():

    """
    Return polygons with german western, northern, eastern and southern states.

    Returns:
        :class:`geopandas.GeoDataFrame`: The output polygons.
    """

    import pandas as pd
    import geopandas as gpd

    # Define aggregation function for the NAME column
    # -----------------------------------------------

    # For the name column when aggregating, we merely want to have a ','
    # followed by a space.

    def join_names(names):
        return ', '.join(names)

    # Get GeoDataFrame with German states
    # -----------------------------------

    german_states = get_geodataframe('german_states')

    DE_SOUTHERN_STATES = [
        'Bayern',
        'Baden-Württemberg',
    ]

    DE_SOUTHERN_STATES = german_states[
        german_states['name'].isin(DE_SOUTHERN_STATES)
    ].dissolve(aggfunc={'name': join_names})

    DE_SOUTHERN_STATES = DE_SOUTHERN_STATES.reset_index()
    DE_SOUTHERN_STATES['DIRECTION'] = 'South'

    DE_EASTERN_STATES = [
        'Berlin',
        'Brandenburg',
        'Sachsen',
        'Sachsen-Anhalt',
        'Thüringen',
    ]

    DE_EASTERN_STATES = german_states[
        german_states['name'].isin(DE_EASTERN_STATES)
    ].dissolve(aggfunc={'name': join_names})

    DE_EASTERN_STATES = DE_EASTERN_STATES.reset_index()
    DE_EASTERN_STATES['DIRECTION'] = 'East'

    DE_NORTHERN_STATES = [
        'Schleswig-Holstein',
        'Hamburg',
        'Bremen',
        'Niedersachsen',
        'Mecklenburg-Vorpommern',
    ]

    DE_NORTHERN_STATES = german_states[
        german_states['name'].isin(DE_NORTHERN_STATES)
    ].dissolve(aggfunc={'name': join_names})

    DE_NORTHERN_STATES = DE_NORTHERN_STATES.reset_index()
    DE_NORTHERN_STATES['DIRECTION'] = 'North'

    DE_WESTERN_STATES = [
        'Rheinland-Pfalz',
        'Saarland',
        'Nordrhein-Westfalen',
        'Hessen',
    ]

    DE_WESTERN_STATES = german_states[
        german_states['name'].isin(DE_WESTERN_STATES)
    ].dissolve(aggfunc={'name': join_names})

    DE_WESTERN_STATES = DE_WESTERN_STATES.reset_index()
    DE_WESTERN_STATES['DIRECTION'] = 'West'

    german_directions = gpd.GeoDataFrame(pd.concat([
        DE_SOUTHERN_STATES,
        DE_EASTERN_STATES,
        DE_NORTHERN_STATES,
        DE_WESTERN_STATES
    ], ignore_index=True))

    return german_directions


def _get_registry():
    return {
        'air_temperature': {
            'aliases': ['air_temperature_data'],
            'loader': _get_air_temperature_data
        },
        'fake_cmip6': {
            'aliases': ['fake_cmip6_data'],
            'loader': generate_fake_cmip6_data
        },
        'cftime_data': {
            'aliases': [],
            'loader': _get_cftime_data
        },
        'hyras': {
            'aliases': ['hyras_tas'],
            'loader': _get_hyras_tas_data
        },
        'hyras_pr': {
            'aliases': [],
            'loader': _get_hyras_pr_data
        },
        'hyras-tas-monthly': {
            'aliases': ['hyras-monthly'],
            'loader': _get_monthly_hyras_data
        },
        'monthly-hyras-files': {
            'aliases': ['monthly_hyras_files'],
            'loader': _get_monthly_hyras_files
        },
        'small_tas_dataset': {
            'aliases': [],
            'loader': _get_small_tas_dataset
        },
        'cosmo-rea6': {
            'aliases': ['cosmo-rea6-daily'],
            'loader': _get_daily_cosmo_rea6_data
        },
        'low-res-hourly-tas-data': {
            'aliases': ['low_res_hourly_tas_data'],
            'loader': _get_low_res_hourly_tas_data
        },
        'hourly-tas': {
            'aliases': ['hourly_tas', 'hostrada'],
            'loader': _get_hostrada_data
        },
        'GCM_CanESM5': {
            'aliases': [],
            'loader': _get_GCM_CanESM5_data
        },
        'MPI_ESM1_2_HR_tas': {
            'aliases': [],
            'loader': _get_MPI_ESM1_2_HR_tas_data
        },
        'MPI_ESM1_2_HR_pr': {
            'aliases': [],
            'loader': _get_MPI_ESM1_2_HR_pr_data
        },
        'tas_hurs': {
            'aliases': [],
            'loader': _get_tas_hurs_data
        },
        'tas_ps_huss': {
            'aliases': [],
            'loader': _get_tas_ps_huss_data
        },
        'ps_tdew': {
            'aliases': [],
            'loader': _get_ps_tdew_data
        },
        'monthly_eurocordex': {
            'aliases': ['cordex_data', 'model_data'],
            'loader': _get_monthly_eurocordex_data
        },
        'global_data': {
            'aliases': [],
            'loader': _get_global_data
        },
        'icon_grib_files': {
            'aliases': [],
            'loader': _get_icon_grib_files
        },
        'icon_grid_file': {
            'aliases': [],
            'loader': _get_icon_grid_file
        },
        'CCCma_CanESM2_Amon_world': {
            'aliases': [],
            'loader': _get_CCCma_CanESM2_Amon_world
        }
    }


def list_test_data(include_aliases=False):
    """
    Returns a list of available dataset identifiers.

    Arguments:
        include_aliases (bool): Defaults to False. If True, returns all valid
            strings. If False, returns only the primary identifier for each
            group.

    Examples:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...: pyku.list_test_data(include_aliases=True)
    """

    registry = _get_registry()

    if include_aliases:
        result = []
        for primary, info in registry.items():
            aliases = info.get('aliases', [])
            if aliases:
                result.append(f"{primary} ({', '.join(aliases)})")
            else:
                result.append(primary)
        return result

    return list(registry.keys())


def get_test_data(id):

    """
    Retrieves sample raster datasets for documentation and unit testing.

    Arguments:
        id (str): The identifier or alias of the test dataset to retrieve.
           Available identifiers can be listed using `pyku.list_identifiers()`.

    Returns:
        :class:`xarray.Dataset`: The requested test raster data.

    Raises:
        ValueError: If the provided `id` is not a recognized dataset
            identifier.

    Examples:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...: pyku.resources.get_test_data('hyras')

    """

    registry = _get_registry()
    for primary, info in registry.items():
        if id == primary or id in info['aliases']:
            return info['loader']()
    raise ValueError(f"Dataset {id} does not exist")


def _get_cftime_data():

    import xarray as xr
    from pathlib import Path
    import pooch
    from filelock import FileLock

    # Alternative data source
    # http://esg-dn1.nsc.liu.se/thredds/fileServer/esg_dataroot3/cordexdata/\
    # cordex/output/CAM-44/SMHI/CCCma-CanESM2/historical/r1i1p1/SMHI-RCA4/v1/\
    # day/tas/v20170508/tas_CAM-44_CCCma-CanESM2_historical_r1i1p1_SMHI-RCA4_\
    # v1_day_19810101-19851231.nc"
    # 370c06a42b2c0a09f8cc59d86d7c291789e26f006604e8d7778550dd18adfa36

    base_url = (
       "https://climate-modelling.canada.ca/modeloutput/AR5/CMIP5/output/"
       "CCCma/CanESM2/historical/day/atmos/tas/r1i1p1/"
    )
    file = "tas_day_CanESM2_historical_r1i1p1_19790101-20051231.nc"
    checksum = \
        '0b891424dd3041f21fcebc0e0ac2714e04bdbb09387a65e66cdc88050b0942bd'

    # Get the pyku data directory
    # --------------------------

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    # Create pooch installer
    # ----------------------

    pooch_installer = pooch.create(
        path=pyku_data_dir,
        base_url=base_url,
        registry={
            file: checksum,
        }
    )

    def to_zarr_processor(fname, action, pooch):
        zarr_path = Path(fname).with_suffix('.zarr')
        if not zarr_path.exists():
            _warn_of_data_download(pooch_installer)
            with xr.open_dataset(fname) as ds:
                _warn_if_default_data_dir()
                ds = ds.pyku.project('HYR-LAEA-50')  # Reduce data size
                ds.to_zarr(zarr_path, mode="w", consolidated=True)
            Path(fname).unlink()  # Delete source netCDF file
        else:
            logger.info(f"{zarr_path} already exists. Skipping download.")

        return zarr_path

    # Lock download to avoid fetching twice in parallel
    # -------------------------------------------------

    lock_path = Path(pyku_data_dir) / f"{file}.lock"
    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)

    # Fetch and return dataset
    # ------------------------

    with FileLock(lock_path):
        file_path = pooch_installer.fetch(
            file,
            processor=to_zarr_processor,
        )

    return xr.open_dataset(file_path)


def _get_tas_hurs_data():

    import xarray as xr
    from pathlib import Path
    import pooch
    from filelock import FileLock

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    pooch_installer = pooch.create(
        path=pyku_data_dir,
        base_url="",
        registry={
            "tas_EUR-11_MPI-M-MPI-ESM-LR_historical_r2i1p1_SMHI-RCA4_v1_day_19810101-19851231.nc": "sha256:a5f1064f2b851b86dd5b0937c219afdcb4e985924947ad75c90a592fd8c09a5d",  # noqa
            "hurs_EUR-11_MPI-M-MPI-ESM-LR_historical_r2i1p1_SMHI-RCA4_v1_day_19810101-19851231.nc": "sha256:1418f4ac7d00370d8c57579c1790e7f6e5204cdf7d47d8434f9cc0ab52a0f9ed",  # noqa
        },
        urls={
            "tas_EUR-11_MPI-M-MPI-ESM-LR_historical_r2i1p1_SMHI-RCA4_v1_day_19810101-19851231.nc": "http://esg-dn1.nsc.liu.se/thredds/fileServer/esg_dataroot7/cordexdata/cordex/output/EUR-11/SMHI/MPI-M-MPI-ESM-LR/historical/r2i1p1/SMHI-RCA4/v1/day/tas/v20191116/tas_EUR-11_MPI-M-MPI-ESM-LR_historical_r2i1p1_SMHI-RCA4_v1_day_19810101-19851231.nc",  # noqa
            "hurs_EUR-11_MPI-M-MPI-ESM-LR_historical_r2i1p1_SMHI-RCA4_v1_day_19810101-19851231.nc": "http://esg-dn1.nsc.liu.se/thredds/fileServer/esg_dataroot7/cordexdata/cordex/output/EUR-11/SMHI/MPI-M-MPI-ESM-LR/historical/r2i1p1/SMHI-RCA4/v1/day/hurs/v20191116/hurs_EUR-11_MPI-M-MPI-ESM-LR_historical_r2i1p1_SMHI-RCA4_v1_day_19810101-19851231.nc",  # noqa
        }
    )

    zarr_path = Path(pyku_data_dir) / "tas_hurs_data.zarr"
    lock_path = Path(pyku_data_dir) / "tas_hurs_data.lock"

    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)

    with FileLock(lock_path):
        if not zarr_path.exists():
            _warn_of_data_download(pooch_installer)

            # Fetch netCDF files
            # ------------------

            files = [
                pooch_installer.fetch(f) for f in pooch_installer.registry
            ]

            # Reduce resoltion and write to zarr
            # ----------------------------------

            with xr.open_mfdataset(
                files,
                data_vars='all',
                compat='no_conflicts',
            ).chunk(chunks=-1) as ds:
                _warn_if_default_data_dir()
                ds = ds.pyku.project('HYR-GER-LAEA-12.5')
                ds.to_zarr(zarr_path, mode="w", consolidated=True)

            # Remove netCDF files
            # -------------------

            for f in files:
                Path(f).unlink(missing_ok=True)

        else:
            logger.info(f"{zarr_path} already exists. Skipping download.")

    return xr.open_zarr(zarr_path)


def _get_tas_ps_huss_data():

    import xarray as xr
    from pathlib import Path
    import pooch
    from filelock import FileLock

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    pooch_installer = pooch.create(
        path=pyku_data_dir,
        base_url="",
        registry={
            "tas_EUR-11_MPI-M-MPI-ESM-LR_historical_r2i1p1_SMHI-RCA4_v1_day_19810101-19851231.nc": "sha256:a5f1064f2b851b86dd5b0937c219afdcb4e985924947ad75c90a592fd8c09a5d",  # noqa
            "ps_EUR-11_MPI-M-MPI-ESM-LR_historical_r2i1p1_SMHI-RCA4_v1_day_19810101-19851231.nc": "sha256:4946f00f40aa840958f3815c71c85d4057f7478ecbad505e6b845f10ca016464",  # noqa
            "huss_EUR-11_MPI-M-MPI-ESM-LR_historical_r2i1p1_SMHI-RCA4_v1_day_19810101-19851231.nc": "sha256:54f9a492cb76ba2fac1ee51c2c552eaff5209416890fab8552d433a6d8866294",  # noqa
        },
        urls={
            "tas_EUR-11_MPI-M-MPI-ESM-LR_historical_r2i1p1_SMHI-RCA4_v1_day_19810101-19851231.nc": "http://esg-dn1.nsc.liu.se/thredds/fileServer/esg_dataroot7/cordexdata/cordex/output/EUR-11/SMHI/MPI-M-MPI-ESM-LR/historical/r2i1p1/SMHI-RCA4/v1/day/tas/v20191116/tas_EUR-11_MPI-M-MPI-ESM-LR_historical_r2i1p1_SMHI-RCA4_v1_day_19810101-19851231.nc",  # noqa
            "ps_EUR-11_MPI-M-MPI-ESM-LR_historical_r2i1p1_SMHI-RCA4_v1_day_19810101-19851231.nc": "http://esg-dn1.nsc.liu.se/thredds/fileServer/esg_dataroot7/cordexdata/cordex/output/EUR-11/SMHI/MPI-M-MPI-ESM-LR/historical/r2i1p1/SMHI-RCA4/v1/day/ps/v20191116/ps_EUR-11_MPI-M-MPI-ESM-LR_historical_r2i1p1_SMHI-RCA4_v1_day_19810101-19851231.nc",  # noqa
            "huss_EUR-11_MPI-M-MPI-ESM-LR_historical_r2i1p1_SMHI-RCA4_v1_day_19810101-19851231.nc": "http://esg-dn1.nsc.liu.se/thredds/fileServer/esg_dataroot7/cordexdata/cordex/output/EUR-11/SMHI/MPI-M-MPI-ESM-LR/historical/r2i1p1/SMHI-RCA4/v1/day/huss/v20191116/huss_EUR-11_MPI-M-MPI-ESM-LR_historical_r2i1p1_SMHI-RCA4_v1_day_19810101-19851231.nc",  # noqa
        }
    )

    zarr_path = Path(pyku_data_dir) / "tas_ps_huss_data.zarr"
    lock_path = Path(pyku_data_dir) / "tas_ps_huss_data.lock"

    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)

    with FileLock(lock_path):
        if not zarr_path.exists():
            _warn_of_data_download(pooch_installer)

            # Fetch netCDF files
            # ------------------

            files = [
                pooch_installer.fetch(f) for f in pooch_installer.registry
            ]

            # Reduce resolution and write to zarr
            # -----------------------------------

            with xr.open_mfdataset(
                files,
                data_vars='all',
                compat='no_conflicts',
            ).chunk(chunks=-1) as ds:
                _warn_if_default_data_dir()
                ds = ds.pyku.project('HYR-GER-LAEA-12.5')
                ds.to_zarr(zarr_path, mode="w", consolidated=True)

            # Remove netCDF files
            # -------------------

            for f in files:
                Path(f).unlink(missing_ok=True)

        else:
            logger.info(f"{zarr_path} already exists. Skipping download.")

    return xr.open_zarr(zarr_path)


def _get_ps_tdew_data():

    import xarray as xr
    from pathlib import Path
    import pooch
    from filelock import FileLock

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    pooch_installer = pooch.create(
        path=pyku_data_dir,
        base_url="",
        registry={
            "ps_1hr_HOSTRADA-v1-0_BE_gn_2000010100-2000013123.nc": "sha256:3b429594fe3b8ac499560b70b55a92c53a45413241baf98cc4a2ce00d8601d94",  # noqa
            "tdew_1hr_HOSTRADA-v1-0_BE_gn_2000010100-2000013123.nc": "sha256:781bc1599d672ebbe8a013567f074f6521987c0f7a021b2c2bc440bf840b0338",  # noqa
        },
        urls={
            "ps_1hr_HOSTRADA-v1-0_BE_gn_2000010100-2000013123.nc": "https://opendata.dwd.de/climate_environment/CDC/grids_germany/hourly/hostrada/pressure_surface/ps_1hr_HOSTRADA-v1-0_BE_gn_2000010100-2000013123.nc",  # noqa
            "tdew_1hr_HOSTRADA-v1-0_BE_gn_2000010100-2000013123.nc": "https://opendata.dwd.de/climate_environment/CDC/grids_germany/hourly/hostrada/dew_point/tdew_1hr_HOSTRADA-v1-0_BE_gn_2000010100-2000013123.nc",  # noqa
        }
    )

    zarr_path = Path(pyku_data_dir) / "ps_tdew_data.zarr"
    lock_path = Path(pyku_data_dir) / "ps_tdew_data.lock"

    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)

    with FileLock(lock_path):
        if not zarr_path.exists():

            _warn_of_data_download(pooch_installer)

            # Fetch netCDF files
            # ------------------

            files = [
                pooch_installer.fetch(f) for f in pooch_installer.registry
            ]

            # Reduce resolution and write to zarr
            # -----------------------------------

            with xr.open_mfdataset(
                files,
                data_vars='all',
                compat='no_conflicts',
            ).chunk(chunks=-1) as ds:
                _warn_if_default_data_dir()
                ds = ds.pyku.project('HYR-GER-LAEA-12.5')
                ds.to_zarr(zarr_path, mode="w", consolidated=True)

            # Remove netCDF files
            # -------------------

            for f in files:
                Path(f).unlink(missing_ok=True)

        else:
            logger.info(f"{zarr_path} already exists. Skipping download.")

    return xr.open_zarr(zarr_path)


def _get_low_res_hourly_tas_data():

    import xarray as xr
    from pathlib import Path
    import pooch
    from filelock import FileLock

    base_url = (
        "https://opendata.dwd.de/climate_environment/CDC/grids_germany/hourly/"
        "radolan/reproc/2017_002/netCDF/2020/"
    )
    file = "RW2017.002_2020_netcdf.tar.gz"
    checksum = \
        "878680f1bc5bac7d1d46a3d196b843aec2b3d51e508324d430619df0af918ba9"

    # Get the pyku data directory
    # --------------------------

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    # Create pooch installer
    # ----------------------

    pooch_installer = pooch.create(
        path=pyku_data_dir,
        base_url=base_url,
        registry={
            file: checksum,
        }
    )

    # Define processor function
    # -------------------------

    def targz_zarr_processor(fname, action, pooch_instance):
        """
        Extracts tar.gz and converts all contained NetCDF files into a Zarr
        store.
        """

        import shutil

        zarr_path = Path(fname).with_suffix('.zarr')

        if not zarr_path.exists():

            _warn_of_data_download(pooch_installer)

            extract_dir = Path(fname).parent / Path(fname).stem
            unpacker = pooch.Untar(extract_dir=extract_dir)
            extracted_files = unpacker(fname, action, pooch_instance)

            # Reduce resolution of dataset and save to zarr
            # ---------------------------------------------

            with xr.open_mfdataset(
                extracted_files,
                data_vars="minimal",
                coords="minimal",
                compat="override",
                join="override"
            ) as ds:
                _warn_if_default_data_dir()
                ds = ds.pyku.project('HYR-GER-LAEA-12.5')
                ds.to_zarr(zarr_path, mode="w", consolidated=True)

            # Delete the .tar.gz file
            # -----------------------

            Path(fname).unlink()

            # Delete the extracted folder and all its contents
            # ------------------------------------------------

            shutil.rmtree(extract_dir)

        else:
            logger.info(f"{zarr_path} already exists. Skipping download.")

        return zarr_path

    # Lock download to avoid fetching twice in parallel
    # -------------------------------------------------

    lock_path = Path(pyku_data_dir) / f"{file}.lock"
    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)

    # Fetch and return dataset
    # ------------------------

    zarr_path = Path(f"{file}").with_suffix('.zarr')

    with FileLock(lock_path):

        if zarr_path.exists():
            return xr.open_dataset(zarr_path, engine="zarr")

        file_path = pooch_installer.fetch(
            file,
            processor=targz_zarr_processor,
        )

    return xr.open_dataset(file_path, engine='zarr')


def _get_icon_grid_file():

    from pathlib import Path
    import pooch
    from filelock import FileLock

    base_url = (
        "http://icon-downloads.mpimet.mpg.de/grids/public/edzw/"
    )
    file = "icon_grid_0027_R03B08_N02.nc"
    checksum = \
        "de22bb247525166865cdb8c396d3c39fecfadbc04cb613ced040074b60354c16"

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    pooch_installer = pooch.create(
        path=pyku_data_dir,
        base_url=base_url,
        registry={
            file: checksum,
        }
    )

    lock_path = Path(pyku_data_dir) / "icon_grid_file.lock"
    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)

    with FileLock(lock_path):

        # Send warnings if files need to be downloaded
        # --------------------------------------------

        if any(
            not pooch_installer.is_available(f)
            for f in pooch_installer.registry
        ):
            _warn_of_data_download(pooch_installer)
            _warn_if_default_data_dir()

        # Fetch files
        # -----------

        file = pooch_installer.fetch(file)

    return file


def _get_icon_grib_files():

    from pathlib import Path
    import pooch
    from filelock import FileLock

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    pooch_installer = pooch.create(
        path=pyku_data_dir,
        base_url=(
            "https://opendata.dwd.de/climate_environment/REA/ICON-DREAM-EU/"
            "hourly/T_2M/"
        ),
        registry={
            "ICON-DREAM-EU_202501_T_2M_hourly.grb": (
                "sha256:c4a3324532d1de1670d0f2c65c4e455b44870c52258319cc3bbabc"
                "9f56cc5d7c"
            ),
        }
    )

    # Lock download to avoid fetching twice in parallel
    # -------------------------------------------------

    lock_path = Path(pyku_data_dir) / "icon_grib_files.lock"
    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)

    # Fetch and return dataset
    # ------------------------

    with FileLock(lock_path):

        registry_files = list(pooch_installer.registry.keys())

        if any(
            not pooch_installer.is_available(f)
            for f in pooch_installer.registry
        ):
            _warn_of_data_download(pooch_installer)
            _warn_if_default_data_dir()

        files = [
            pooch_installer.fetch(fname)
            for fname in registry_files
        ]

    return files


def _get_small_tas_dataset():

    import xarray as xr
    from pathlib import Path
    import pooch
    from filelock import FileLock

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    pooch_installer = pooch.create(
        path=pyku_data_dir,
        base_url=(
            "https://opendata.dwd.de/climate_environment/CDC/grids_germany/"
            "daily/hyras_de/air_temperature_mean/"
        ),
        registry={
            "tas_hyras_1_1981_v6-1_de.nc": (
                "sha256:bfdbf66ba78fe131ea5b6ec3b4de940a0ca5a09b094f571609a990"
                "4538654acc"
            ),
        }
    )

    zarr_path = Path(pyku_data_dir) / "small_tas_dataset.zarr"
    lock_path = Path(pyku_data_dir) / "small_tas_dataset.lock"

    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)

    with FileLock(lock_path):
        if not zarr_path.exists():

            _warn_of_data_download(pooch_installer)

            # Fetch netCDF files
            # ------------------

            files = [
                pooch_installer.fetch(f) for f in pooch_installer.registry
            ]

            # Write to zarr
            # -------------

            with xr.open_mfdataset(
                files,
                data_vars='all'
            ).chunk(chunks=-1) as ds:
                _warn_if_default_data_dir()
                ds = ds.isel(time=[0, 1, 2, 4]).pyku.project('HYR-GER-LAEA-5')
                ds.to_zarr(zarr_path, mode="w", consolidated=True)

            # Remove netCDF files
            # -------------------

            for f in files:
                Path(f).unlink(missing_ok=True)

        else:
            logger.info(f"{zarr_path} already exists. Skipping download.")

    return xr.open_zarr(zarr_path)


def _get_hyras_tas_data():

    import xarray as xr
    from pathlib import Path
    import pooch
    from filelock import FileLock

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    pooch_installer = pooch.create(
        path=pyku_data_dir,
        base_url=(
            "https://opendata.dwd.de/climate_environment/CDC/grids_germany/"
            "daily/hyras_de/air_temperature_mean/"
        ),
        registry={
            "tas_hyras_1_1981_v6-1_de.nc": (
                "sha256:bfdbf66ba78fe131ea5b6ec3b4de940a0ca5a09b094f571609a990"
                "4538654acc"
            ),
            "tas_hyras_1_1982_v6-1_de.nc": (
                "sha256:f693fafa8a9ef2173ff12846aff4e99313107e6c2fd7e8d6444655"
                "b05f8dad36"
            ),
        }
    )

    zarr_path = Path(pyku_data_dir) / "hyras_tas.zarr"
    lock_path = Path(pyku_data_dir) / "hyras_tas.lock"

    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)

    with FileLock(lock_path):

        if not zarr_path.exists():

            _warn_of_data_download(pooch_installer)

            # Fetch netCDF files
            # ------------------

            files = [
                pooch_installer.fetch(f) for f in pooch_installer.registry
            ]

            # Convert netCDF files to zarr
            # ----------------------------

            with xr.open_mfdataset(
                files,
                data_vars='all'
            ).chunk(chunks=-1) as ds:
                _warn_if_default_data_dir()
                ds = ds.pyku.project('HYR-GER-LAEA-5')
                ds.to_zarr(zarr_path, mode="w", consolidated=True)

            # Delete the original netCDF files
            # --------------------------------

            for f in files:
                Path(f).unlink()
        else:
            logger.info(f"{zarr_path} already exists. Skipping download.")

    return xr.open_zarr(zarr_path)


def _get_hyras_pr_data():

    import xarray as xr
    from pathlib import Path
    import pooch
    from filelock import FileLock

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    pooch_installer = pooch.create(
        path=pyku_data_dir,
        base_url=(
            "https://opendata.dwd.de/climate_environment/CDC/grids_germany/"
            "daily/hyras_de/precipitation/"
        ),
        registry={
            "pr_hyras_1_1981_v6-1_de.nc": (
                "sha256:cfdd658b9a5a136bd357265da522e832d34bb6e6625ad55e84383d"
                "32f4473827"
            ),
            "pr_hyras_1_1982_v6-1_de.nc": (
                "sha256:5181de0615c2f489f1186074570c91d59450b872ea9326d77d9de0"
                "ed3aefa59c"
            ),
        }
    )

    zarr_path = Path(pyku_data_dir) / "hyras_pr.zarr"
    lock_path = Path(pyku_data_dir) / "hyras_pr.lock"

    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)

    with FileLock(lock_path):
        if not zarr_path.exists():

            _warn_of_data_download(pooch_installer)

            # Download netCDF files
            # ---------------------

            files = [
                pooch_installer.fetch(f) for f in pooch_installer.registry
            ]

            # Convert netCDF files to zarr
            # ----------------------------

            with xr.open_mfdataset(
                files,
                combine="nested",
                concat_dim="time",
                coords="minimal",
                data_vars="minimal",
                compat="no_conflicts"
            ).chunk(chunks=-1) as ds:
                _warn_if_default_data_dir()
                ds.to_zarr(zarr_path, mode="w", consolidated=True)

            # Delete the original netCDF files
            # --------------------------------

            for f in files:
                Path(f).unlink()

        else:
            logger.info(f"{zarr_path} already exists. Skipping download.")

    return xr.open_zarr(zarr_path)


def _get_monthly_hyras_data():

    import xarray as xr
    from pathlib import Path
    import pooch
    from filelock import FileLock

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    pooch_installer = pooch.create(
        path=pyku_data_dir,
        base_url=(
            "https://opendata.dwd.de/climate_environment/CDC/grids_germany/"
            "monthly/hyras_de/air_temperature_mean/"
        ),
        registry={
            "tas_hyras_1_1961_v6-1_de_monmean.nc": (
                "sha256:bc89f78936d190db301b72bf19b914dc343c3401e3d74e126fcede"
                "258444c53b"
            ),
            "tas_hyras_1_1962_v6-1_de_monmean.nc": (
                "sha256:face20f31b0d2c421c4c5ccfde498a497a4645242a71c08f7d1431"
                "32100f5c57"
            ),
        }
    )

    zarr_path = Path(pyku_data_dir) / "monthly_hyras_data.zarr"
    lock_path = Path(pyku_data_dir) / "monthly_hyras_data.lock"

    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)

    with FileLock(lock_path):
        if not zarr_path.exists():

            _warn_of_data_download(pooch_installer)

            # Fetch netCDF files
            # ------------------

            files = [
                pooch_installer.fetch(f) for f in pooch_installer.registry
            ]

            # Write to zarr
            # -------------

            with xr.open_mfdataset(
                files,
                data_vars='all'
            ).chunk(chunks=-1) as ds:
                _warn_if_default_data_dir()
                ds.to_zarr(zarr_path, mode="w", consolidated=True)

            # Remove netCDF files
            # -------------------

            for f in files:
                Path(f).unlink(missing_ok=True)

        else:
            logger.info(f"{zarr_path} already exists. Skipping download.")

    return xr.open_zarr(zarr_path)


def _get_monthly_hyras_files():

    from pathlib import Path
    import pooch
    from filelock import FileLock

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    pooch_installer = pooch.create(
        path=pyku_data_dir,
        base_url=(
            "https://opendata.dwd.de/climate_environment/CDC/grids_germany/"
            "monthly/hyras_de/air_temperature_mean/"
        ),
        registry={
            "tas_hyras_1_1961_v6-1_de_monmean.nc": (
                "sha256:bc89f78936d190db301b72bf19b914dc343c3401e3d74e126fcede"
                "258444c53b"
            ),
            "tas_hyras_1_1962_v6-1_de_monmean.nc": (
                "sha256:face20f31b0d2c421c4c5ccfde498a497a4645242a71c08f7d1431"
                "32100f5c57"
            ),
        }
    )

    lock_path = Path(pyku_data_dir) / "monthly_hyras_files.lock"

    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)

    with FileLock(lock_path):

        if any(
            not pooch_installer.is_available(f)
            for f in pooch_installer.registry
        ):
            _warn_of_data_download(pooch_installer)
            _warn_if_default_data_dir()

        files = [
            pooch_installer.fetch(f) for f in pooch_installer.registry
        ]

    return files


def _get_daily_cosmo_rea6_data():

    import xarray as xr
    from pathlib import Path
    import pooch
    from filelock import FileLock

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    pooch_installer = pooch.create(
        path=pyku_data_dir,
        base_url=(
            "https://opendata.dwd.de/climate_environment/REA/COSMO_REA6/daily/"
            "2D/T_2M/"
        ),
        registry={
            "T_2M.2D.200301.DayMean.grb": (
                "sha256:46fd06e9980b41a1620c4a48e573b499a92733f364688ef9d72ce3"
                "5d0c669860"
            ),
            "T_2M.2D.200302.DayMean.grb": (
                "sha256:13e16921d196136b23afe8cf8d4d2b9c9107219b16c9a72096b02b"
                "5de6db8cc6"
            ),
            "T_2M.2D.200303.DayMean.grb": (
                "sha256:b9f4ef00b7564bce4c83ad61e408ded4c809a970a1c3baa06fe40d"
                "bf56fa4fde"
            ),
        }
    )

    zarr_path = Path(pyku_data_dir) / "daily_cosmo_rea6_data.zarr"
    lock_path = Path(pyku_data_dir) / "daily_cosmo_rea6_data.lock"

    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)

    with FileLock(lock_path):
        if not zarr_path.exists():

            _warn_of_data_download(pooch_installer)

            # Fetch netCDF files
            # ------------------

            files = [
                pooch_installer.fetch(f) for f in pooch_installer.registry
            ]

            # Convert to zarr
            # ---------------

            with xr.open_mfdataset(
                files,
                engine='cfgrib',
                data_vars='all',
                backend_kwargs={"indexpath": ""}
            ).chunk(chunks=-1) as ds:
                _warn_if_default_data_dir()
                ds.to_zarr(zarr_path, mode="w", consolidated=True)

            # Remove netCDF files
            # -------------------

            for f in files:
                Path(f).unlink(missing_ok=True)

        else:
            logger.info(f"{zarr_path} already exists. Skipping download.")

    return xr.open_zarr(zarr_path)


def _get_hostrada_data():

    import xarray as xr
    from pathlib import Path
    import pooch
    from filelock import FileLock

    base_url = (
      "https://opendata.dwd.de/climate_environment/CDC/grids_germany/hourly/"
      "hostrada/air_temperature_mean/"
    )
    file = "tas_1hr_HOSTRADA-v1-0_BE_gn_1995010100-1995013123.nc"
    checksum = \
        "8d69fe00d339025e15ea6dacf16950dc0dec4867e3a2992a7837d381cf79e364"

    # Get the pyku data directory
    # --------------------------

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    # Create pooch installer
    # ----------------------

    pooch_installer = pooch.create(
        path=pyku_data_dir,
        base_url=base_url,
        registry={
            file: checksum,
        }
    )

    def to_zarr_processor(fname, action, pooch):

        if not zarr_path.exists():

            # Warn of download
            # ----------------

            _warn_of_data_download(pooch_installer)
            _warn_if_default_data_dir()

            # Write to zarr
            # -------------

            with xr.open_dataset(fname) as ds:
                ds.to_zarr(zarr_path, mode="w", consolidated=True)

            # Remove netCDF files
            # -------------------

            Path(fname).unlink(missing_ok=True)

        return zarr_path

    # Lock download to avoid fetching twice in parallel
    # -------------------------------------------------

    lock_path = Path(pyku_data_dir) / f"{file}.lock"
    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)
    zarr_path = Path(pyku_data_dir) / f"{Path(file).stem}.zarr"

    # Fetch and return dataset
    # ------------------------

    with FileLock(lock_path):

        if zarr_path.exists():
            return xr.open_dataset(zarr_path, engine="zarr")

        file_path = pooch_installer.fetch(
            file,
            processor=to_zarr_processor,
        )

    return xr.open_dataset(file_path)


def _get_air_temperature_data():

    import xarray.tutorial as tutorial

    ds = tutorial.open_dataset('air_temperature').rename({'air': 'tas'})
    ds = ds.pyku.sort_georeferencing()
    return ds


def _get_CCCma_CanESM2_Amon_world():

    import xarray as xr
    from pathlib import Path
    from filelock import FileLock
    import s3fs
    import warnings

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    s3_paths = [
        "s3://esgf-world/CMIP6/CMIP/CCCma/CanESM5/historical/r1i1p1f1/Amon/"
        "tas/gn/v20190306/tas_Amon_CanESM5_historical_r1i1p1f1_gn_"
        "185001-201412.nc",
        "s3://esgf-world/CMIP6/ScenarioMIP/CCCma/CanESM5/ssp585/r1i1p1f1/Amon/"
        "tas/gn/v20190306/tas_Amon_CanESM5_ssp585_r1i1p1f1_gn_201501-210012.nc"
    ]

    zarr_path = Path(pyku_data_dir) / "CCCma_CanESM2_Amon_world.zarr"
    lock_path = Path(pyku_data_dir) / "CCCma_CanESM2_Amon_world.lock"

    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)

    with FileLock(lock_path):

        if not zarr_path.exists():

            warnings.warn(f"Downloading NetCDFs to {zarr_path}")
            fs = s3fs.S3FileSystem(anon=True)

            datasets = [xr.open_dataset(fs.open(p)) for p in s3_paths]
            ds = xr.concat(datasets, dim="time")

            for var in ds.variables:
                ds[var].encoding.clear()

            _warn_if_default_data_dir()
            ds.to_zarr(zarr_path)

            for d in datasets:
                d.close()

        else:
            logger.info(f"{zarr_path} already exists. Skipping download.")

    return xr.open_dataset(zarr_path)


def _get_MPI_ESM1_2_HR_tas_data():

    import xarray as xr
    from pathlib import Path
    from filelock import FileLock
    import s3fs
    import warnings

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    s3_path = (
        "s3://esgf-world/CMIP6/CMIP/MPI-M/MPI-ESM1-2-HR/historical/r1i1p1f1/"
        "day/tas/gn/v20190710/tas_day_MPI-ESM1-2-HR_historical_r1i1p1f1_gn_"
        "19800101-19841231.nc"
    )

    zarr_path = Path(pyku_data_dir) / "MPI_ESM1_2_HR_tas_data.zarr"
    lock_path = Path(pyku_data_dir) / "MPI_ESM1_2_HR_tas_data.lock"

    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)

    with FileLock(lock_path):
        if not zarr_path.exists():

            warnings.warn(f"Downloading NetCDF: {s3_path} to {pyku_data_dir}")

            fs = s3fs.S3FileSystem(anon=True)

            with fs.open(s3_path) as f:
                with xr.open_dataset(
                    f,
                ) as ds:
                    for var in ds.variables:
                        ds[var].encoding.clear()

                    _warn_if_default_data_dir()
                    ds.to_zarr(zarr_path)

    return xr.open_dataset(zarr_path)


def _get_MPI_ESM1_2_HR_pr_data():

    import xarray as xr
    from pathlib import Path
    from filelock import FileLock
    import s3fs
    import warnings

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    s3_path = (
        "s3://esgf-world/CMIP6/CMIP/MPI-M/MPI-ESM1-2-HR/historical/r1i1p1f1/"
        "day/pr/gn/v20190710/pr_day_MPI-ESM1-2-HR_historical_r1i1p1f1_gn_"
        "19800101-19841231.nc"
    )

    zarr_path = Path(pyku_data_dir) / "MPI_ESM1_2_HR_pr_data.zarr"
    lock_path = Path(pyku_data_dir) / "MPI_ESM1_2_HR_pr_data.lock"

    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)

    with FileLock(lock_path):
        if not zarr_path.exists():
            warnings.warn(f"Downloading NetCDF: {s3_path} to {pyku_data_dir}")
            fs = s3fs.S3FileSystem(anon=True)
            with fs.open(s3_path) as f:
                with xr.open_dataset(
                    f,
                ) as ds:
                    for var in ds.variables:
                        ds[var].encoding.clear()

                    _warn_if_default_data_dir()
                    ds.to_zarr(zarr_path)

    return xr.open_dataset(zarr_path)


def _get_global_data():
    import xarray as xr
    from pathlib import Path
    from filelock import FileLock
    import s3fs
    import warnings

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    s3_path = (
        "s3://esgf-world/CMIP6/CMIP/EC-Earth-Consortium/EC-Earth3-Veg/"
        "historical/r1i1p1f1/day/tas/gr/v20200225/"
        "tas_day_EC-Earth3-Veg_historical_r1i1p1f1_gr_19800101-19801231.nc"
    )

    zarr_path = Path(pyku_data_dir) / "global_data.zarr"
    lock_path = Path(pyku_data_dir) / "global_data.lock"

    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)

    with FileLock(lock_path):
        if not zarr_path.exists():
            warnings.warn(f"Downloading NetCDF: {s3_path} to {pyku_data_dir}")
            fs = s3fs.S3FileSystem(anon=True)
            with fs.open(s3_path) as f:
                with xr.open_dataset(f) as ds:
                    for var in ds.variables:
                        ds[var].encoding.clear()

                    _warn_if_default_data_dir()
                    ds.to_zarr(zarr_path)

    return xr.open_dataset(zarr_path)


def _get_monthly_eurocordex_data():

    import xarray as xr
    from pathlib import Path
    from filelock import FileLock
    import s3fs
    import warnings

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    s3_path = (
        "s3://euro-cordex/CMIP5/cordex/output/EUR-11/SMHI/MPI-M-MPI-ESM-LR/"
        "historical/r1i1p1/RCA4/v1a/mon/tas/v20160803/"
    )

    zarr_path = Path(pyku_data_dir) / "monthly_eurocordex_data.zarr"
    lock_path = Path(pyku_data_dir) / "monthly_eurocordex_data.lock"

    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)

    with FileLock(lock_path):
        if not zarr_path.exists():
            warnings.warn(f"Downloading zarr: {s3_path} to {pyku_data_dir}")
            fs = s3fs.S3FileSystem(anon=True)
            store = s3fs.S3Map(root=s3_path, s3=fs, check=False)
            with xr.open_zarr(store, consolidated=True) as ds:
                for var in ds.variables:
                    ds[var].encoding.clear()
                _warn_if_default_data_dir()
                ds.to_zarr(zarr_path)

    return xr.open_zarr(zarr_path)


def _get_GCM_CanESM5_data():

    import xarray as xr
    from pathlib import Path
    from filelock import FileLock
    import s3fs
    import warnings

    pyku_data_dir = Path(PYKU_CONFIG.get('data_dir'))

    s3_path = (
        "s3://euro-cordex/CMIP5/cordex-reklies/output/EUR-11/CLMcom/"
        "CCCma-CanESM2/historical/r1i1p1/CCLM4-8-17/v1/mon/tas/v20171121"
    )

    zarr_path = Path(pyku_data_dir) / "GCM_CanESM5_data.zarr"
    lock_path = Path(pyku_data_dir) / "GCM_CanESM5_data.lock"

    Path(pyku_data_dir).mkdir(parents=True, exist_ok=True)

    with FileLock(lock_path):
        if not zarr_path.exists():
            warnings.warn(f"Downloading zarr: {s3_path} to {pyku_data_dir}")
            fs = s3fs.S3FileSystem(anon=True)
            store = s3fs.S3Map(root=s3_path, s3=fs, check=False)
            with xr.open_zarr(store, consolidated=True) as ds:
                for var in ds.variables:
                    ds[var].encoding.clear()
                _warn_if_default_data_dir()
                ds.to_zarr(zarr_path)

    return xr.open_zarr(zarr_path)


def _get_fake_cmip6_data():
    ds = _get_fake_cmip6_data()
    ds = ds.pyku.sort_georeferencing()
    return ds


def generate_fake_cmip6_data(ntime=1, nlat=180, nlon=360, freq='D'):
    """
    Generate fake cmip6 data for testing

    Arguments:
        ntime (int): Number of years
        nlat (int): Number of latitudes
        nlon (int): Number of longitudes
        freq (str): Frequency of the time dimension

    Returns:
        :class:`xarray.Dataset`: Fake CMIP6 dataset
    """

    import datetime
    import numpy as np
    import xarray as xr
    import pandas as pd

    lat = np.linspace(-90, 90, nlat)
    lon = np.linspace(-180, 180, nlon)

    enddate = datetime.date(2023, 12, 31).strftime("%Y-%m-%d")
    startdate = datetime.date(2023-(ntime-1), 1, 1).strftime("%Y-%m-%d")

    time = pd.date_range(pd.Timestamp(startdate),
                         pd.Timestamp(enddate),
                         freq=freq)
    dayofyear = time.dayofyear.values

    temperature = (
        15
        + 10 * np.sin(np.radians(lat[:, None, None]))
             * np.cos(np.radians(lon[None, :, None]))
        + 5 * np.sin(2 * np.pi * (dayofyear / 365.0))[None, None, :]
        + np.random.randn(len(lat), len(lon), len(time)) * 2
    )

    attrs = {
        'name': '/ccc/work/cont003/gencmip6/checagar/IGCM_OUT/IPSLCM6/PROD/'
                'historical/IPSLESM-historical-v2/CMIP6/ATM/zg_Amon_IPSL-'
                'CM6A-LR-INCA_historical_r1i1p1f1_gr_%start_date%-%end_date%',
        'Conventions': 'CF-1.7 CMIP-6.2',
        'creation_date': '2020-10-18T15:18:15Z',
        'tracking_id': 'hdl:21.14100/4f03accf-6a30-44d9-a20e-8ac4fde7055f',
        'description': 'CMIP6 historical',
        'title': 'IPSL-CM6A-LR-INCA model output prepared for CMIP6 / CMIP '
                 'historical',
        'activity_id': 'CMIP',
        'contact': 'ipsl-cmip6@listes.ipsl.fr',
        'data_specs_version': '01.00.28',
        'dr2xml_version': '1.16',
        'experiment_id': 'historical',
        'experiment': 'all-forcing simulation of the recent past',
        'external_variables': 'areacella',
        'forcing_index': np.int32(1),
        'frequency': 'day',
        'further_info_url': 'https://furtherinfo.es-doc.org/CMIP6.IPSL.IPSL-'
                            'CM6A-LR-INCA.historical.none.r1i1p1f1',
        'grid': 'LMDZ grid',
        'grid_label': 'gr',
        'nominal_resolution': '250 km',
        'comment': 'Start from spinup (using the same setup as current '
                   'simulation). The spinup started from parent experiment '
                   '(performed with IPSL-CM6A-LR model, i.e with no '
                   'interactive aerosols).',
        'history': 'none',
        'initialization_index': np.int32(1),
        'institution_id': 'IPSL',
        'institution': 'Institut Pierre Simon Laplace, Paris 75252, France',
        'license':
            'CMIP6 model data produced by IPSL is licensed under a '
            'Creative Commons Attribution-NonCommercial-ShareAlike 4.0 '
            'International License (https://creativecommons.org/'
            'licenses). Consult https://pcmdi.llnl.gov/CMIP6/TermsOfUse '
            'for terms of use governing CMIP6 output, including citation '
            'requirements and proper acknowledgment. Further information '
            'about this data, including some limitations, can be found '
            'via the further_info_url (recorded as a global attribute in '
            'this file) and at https://cmc.ipsl.fr/. The data producers '
            'and data providers make no warranty, either express or '
            'implied, including, but not limited to, warranties of '
            'merchantability and fitness for a particular purpose. All '
            'liabilities arising from the supply of the information '
            '(including any liability arising in negligence) are excluded '
            'to the fullest extent permitted by law.',
        'mip_era': 'CMIP6',
        'parent_experiment_id': 'piControl',
        'parent_mip_era': 'CMIP6',
        'parent_activity_id': 'CMIP',
        'parent_source_id': 'IPSL-CM6A-LR-INCA',
        'parent_time_units': 'days since 1850-01-01 00:00:00',
        'parent_variant_label': 'r1i1p1f1',
        'branch_method': 'standard',
        'branch_time_in_parent': np.float64(21914.0),
        'branch_time_in_child': np.float64(0.0),
        'physics_index': np.int32(1),
        'product': 'model-output',
        'realization_index': np.int32(1),
        'realm': 'atmos',
        'source':
            'IPSL-CM6A-LR-INCA (2019):  aerosol: INCA v6 AER atmos: LMDZ '
            '(NPv6 ; 144 x 143 longitude/latitude; 79 levels; top level '
            '80000 m) land: ORCHIDEE (v2.0, Water/Carbon/Energy mode) '
            'ocean: NEMO-OPA (eORCA1.3, tripolar primarily 1deg; 362 x 332 '
            'longitude/latitude; 75 levels; top grid cell 0-2 m) '
            'ocnBgchem: NEMO-PISCES seaIce: NEMO-LIM3',
        'source_id': 'IPSL-CM6A-LR-INCA',
        'source_type': 'AOGCM BGC AER',
        'sub_experiment_id': 'none',
        'sub_experiment': 'none',
        'table_id': 'Amon',
        'variable_id': 'zg',
        'variant_label': 'r1i1p1f1',
        'EXPID': 'historical',
        'CMIP6_CV_version': 'cv=6.2.15.1',
        'dr2xml_md5sum': 'b6f602401512e82e2d7cadc2c6f36c2a',
        'model_version': '6.1.11',
    }

    ds = xr.Dataset(
        {
            "tas": (["lat", "lon", "time"], temperature),
        },
        coords={
            "lat": lat,
            "lon": lon,
            "time": time,
        },
        attrs=attrs,
    )

    return ds


def generate_fake_datasets_with_datetimes_on_disk(directory=None):
    """
    Generate fake NetCDF datasets with datetimes

    Arguments:
        directory (str): The output directory.

    Returns:
        (List(str)): List of fake files.
    """

    import xarray as xr
    import pandas as pd
    from pathlib import Path

    # Sanity checks
    # -------------

    if directory is None:
        raise ValueError("Output directory not set")

    # Prepare a list of datetimes for start and end of each file
    # ----------------------------------------------------------

    starts_and_ends = [
        ['1988-01-01T00', '1988-06-30T18'],
        ['1988-02-01T00', '1988-07-31T18'],
        ['1988-03-01T00', '1988-08-31T18'],
        ['1988-04-01T00', '1988-09-30T18'],
        ['1988-05-01T00', '1988-10-31T18'],
        ['1988-06-01T00', '1988-11-30T18'],
        ['1988-07-01T00', '1988-12-31T18'],
        ['1988-08-01T00', '1989-01-31T18'],
        ['1988-09-01T00', '1989-02-28T18']
    ]

    # Files are gathered in a list
    # ----------------------------

    list_of_files = []

    # Loop over all start and end times
    # ---------------------------------

    for idx, (start, end) in enumerate(starts_and_ends):

        # Convert to pandas timestamp
        # ---------------------------

        start_ts = pd.Timestamp(start)
        end_ts = pd.Timestamp(end)

        # Generate a fake file name
        # -------------------------

        filename = f"projectdata/seasonalfc/hindcasts/DWD/GCFS1/\
seas{start_ts.strftime('%Y%m')}/day/atmos/tas/r15i1p1/\
tas_day_GCFS1_seas{start_ts.strftime('%Y%m')}_r15i1p1/\
tas_day_r1i1p1_{start_ts.strftime('%Y%m%d%H')}-\
{end_ts.strftime('%Y%m%d%H')}.nc"

        # Join temporary directory with the file name
        # -------------------------------------------

        filename = Path(directory) / Path(filename)

        # Generate a fake dataset that contains datetimes
        # -----------------------------------------------

        if not filename.exists():

            filename.parent.mkdir(parents=True, exist_ok=True)

            xr.Dataset(
                coords={'time': pd.date_range(
                    start=start_ts, end=end_ts, freq='1h')}
            ).to_netcdf(filename)

        # Gather file name to the list of files
        # -------------------------------------

        list_of_files.append(str(filename))

    return list_of_files
