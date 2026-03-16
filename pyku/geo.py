#!/usr/bin/env python3

__all__ = [
            'list_standard_areas',
            'load_area_def'
            ]

"""
Functions for managing georeferencing

.. rubric:: Resources

https://cordex.org/domains/

"""

from . import logger
from . import areas_cf_data
from . import areas_data

# Define projections which are deprecated. This should be removed in a later
# version of pyku

DEPRECATED_PROJECTIONS = {
    "HYR-1": "HYR-LCC-1",
    "HYR-2": "HYR-LCC-2",
    "HYR-3": "HYR-LCC-3",
    "HYR-5": "HYR-LCC-5",
    "HYR-125": "HYR-LCC-12.5",
    "HYR-50": "HYR-LCC-50",
    "HYR-100": "HYR-LCC-100",
    "GER-LAEA-3": "HYR-GER-LAEA-3",
    "GER-LAEA-5": "HYR-GER-LAEA-5",
    "germany_5km_laea": "HYR-GER-LAEA-5",
    "germany_50km_laea": "HYR-GER-LAEA-50",
    "hyras_5km_laea": "HYR-GER-LAEA-5",
}


def list_standard_areas():
    """
    List pyku standard area definitions

    Returns:
        List[str]: List of pyku standard areas
    """

    return list(areas_data.keys())


def get_areas_cf_definitions():
    """
    Get the CF conform area definitions included in pyku

    Returns:
        dict: Dictionary of definitions of CF conform area definitions

    Example:

        .. ipython::

           In [0]: import pyku.geo as geo
              ...: geo.get_areas_cf_definitions().get('EUR-11').get('crs_cf')

    """

    return areas_cf_data


def get_areas_definitions():
    """
    Get all default areas definitions included in pyku.

    Returns:
        dict: Definitions of all areas included in pyku

    Example:

        .. ipython::

           In [0]: import pyku.geo as geo
              ...: geo.get_areas_definitions().keys()
    """

    return areas_data


def load_area_def(projection_name, area_file=None):
    """
    Load area definition from projection file and projection name.

    Arguments:
        projection_name (str): The projection name.
        area_file (str): File containing projection definition

    Returns:
        :class:`pyresample.geometry.AreaDefinition`: Area definition

    Example:

        .. ipython::
           :okwarning:

           In [0]: import pyku.geo as geo
              ...: geo.load_area_def('HYR-LAEA-5')
    """

    import warnings
    import importlib
    from pyresample.area_config import load_area

    warnings.filterwarnings(
        "ignore",
        "You will likely lose important projection information",
        UserWarning,
    )

    if projection_name is None:
        raise ValueError("projection_name is None")

    if area_file is None:
        area_file = importlib.resources.files('pyku.etc') / 'areas.yaml'

    area_def = load_area(area_file, projection_name)

    return area_def


def align_georeferencing(ds, ref, tolerance=None):
    """
    Align georeferencing of one dataset onto the other.

    Arguments:
        ds (:class:`xarray.Dataset`): The dataset to be aligned.
        ref (:class:`xarray.Dataset`): The reference dataset for alignment.
        tolerance (float): Absolute tolerance for projection yx coordinates.

    Raises:
        Exception: If the y and x projection coordinates are outside the
            tolerance and the georeferencing cannot be aligned.

    Returns:
        :class:`xarray.Dataset`: Dataset with georeferencing aligned to
        reference dataset.
    """

    import pyku.meta as meta
    import numpy as np

    # Get projection x/y and geographic lat/lon names
    # -----------------------------------------------

    y_name, x_name = meta.get_projection_yx_varnames(ds)
    y_name_ref, x_name_ref = meta.get_projection_yx_varnames(ref)

    lat_name, lon_name = meta.get_geographic_latlon_varnames(ds)
    lat_name_ref, lon_name_ref = meta.get_geographic_latlon_varnames(ref)

    # Sanity checks
    # -------------

    if y_name is None:
        raise AssertionError('No y projection coordinate in data')
    if x_name is None:
        raise AssertionError('No x projection coordinate in data')
    if lat_name is None:
        raise AssertionError('No geographic lat coordinate in data')
    if lon_name is None:
        raise AssertionError('No geographic lon coordinate in data')
    if y_name_ref is None:
        raise AssertionError('No y projection coordinate in reference')
    if x_name_ref is None:
        raise AssertionError('No x projection coordinate in reference')
    if lat_name_ref is None:
        raise AssertionError('No geographic lat coordinate in reference')
    if lon_name_ref is None:
        raise AssertionError('No geographic lon coordinate in reference')

    # Set tolerance
    # -------------

    x_name_units_ref = ref[x_name_ref].attrs.get('units')
    y_name_units_ref = ref[y_name_ref].attrs.get('units')

    # Check if projection y/x varname is in degree
    # --------------------------------------------

    is_degree = (
        x_name_units_ref is not None
        and y_name_units_ref is not None
        and x_name_units_ref.lower().find('degree') != -1
        and y_name_units_ref.lower().find('degree') != -1
    )

    # Check if projection y/x varname is in meters
    # --------------------------------------------

    is_meter = (
        x_name_units_ref is not None
        and y_name_units_ref is not None
        and x_name_units_ref.lower() in ['m']
        and y_name_units_ref.lower() in ['m']
    )

    # Set tolerance to defaults depending on unit
    # -------------------------------------------

    logger.debug(f'{is_degree=}')
    logger.debug(f'{is_meter=}')
    logger.debug(f'{tolerance=}')

    if tolerance is None and is_degree:
        tolerance = 1E-4

    if tolerance is None and is_meter:
        tolerance = 10

    if tolerance is None and is_meter is False and is_degree is False:
        tolerance = 1E-6
        logger.warning(
            f"Tolerance not set and cant read unit, using {tolerance=}"
        )

    # Reindex projection coordinates according to reference dataset
    # -------------------------------------------------------------

    ds = ds.reindex_like(
        ref[[y_name_ref, x_name_ref]],
        method='nearest',
        tolerance=tolerance,
        fill_value='outside_tolerance'
    )

    # The fill_value are strings and change the dtype when outside tolerance
    # ----------------------------------------------------------------------

    dtype_is_float = (
        ds[lat_name].dtype in [np.float32, np.float64]
        and ds[lon_name].dtype in [np.float32, np.float64]
    )

    if not dtype_is_float:
        raise ValueError(f"Values do not fall within tolerance of {tolerance}")

    # Sanity warning
    # --------------

    # The alignment of georeferencing solely reliese on the projection
    # coordinates. Here we further check the absoluted distance between the
    # geographic coordinates. a difference of 1E-3 corresponds to 100 meters

    lats_within_tolerance = \
        np.abs(ds[lat_name].values - ref[lat_name].values) <= 1E-3

    lons_within_tolerance = \
        np.abs(ds[lon_name].values - ref[lon_name].values) <= 1E-3

    all_lats_within_tolerance = np.all(lats_within_tolerance)
    all_lons_within_tolerance = np.all(lons_within_tolerance)

    if not all_lats_within_tolerance:
        logger.warning(
            "Not all geographic latitudes within tolerance of 1E-3 degree"
        )
    if not all_lons_within_tolerance:
        logger.warning(
            "Not all geographic longitudes within tolerance of 1E-3 degree"
        )

    # The index of the projection coordinates were aligned, now assign the
    # geographic projection coordinates of the reference dataset.

    ds = ds.assign_coords({
        lat_name: ref[lat_name_ref],
        lon_name: ref[lon_name_ref],
    })

    return ds


def get_ny(ds):
    """
    Get number of pixels in the y/lat direction

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        int: Number of pixels y/lat direction.

    Raises:
        Exception: if the dimension of projection coordinate y is more than 1.

    Example:

        .. ipython::
           :okwarning:

           In [0]: pyku
              ...:
              ...: ds = pyku.resources.get_test_data('hyras-tas-monthly')
              ...:
              ...: ds.pyku.get_ny()
    """

    import pyku.meta as meta

    y_name, x_name = meta.get_projection_yx_varnames(ds)

    ys = ds.coords[y_name].to_numpy()

    if ys.ndim > 1:
        raise ValueError(
            f"Dimension of projection coordinates is {ys.ndim}, when 1 is "
            "expected"
        )

    return len(ys)


def get_nx(ds):
    """
    Get number of pixels in the x/lon direction.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        int: Number of pixels in the x/lon direction.

    Example:
        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras-tas-monthly')
              ...: ds.pyku.get_nx()
    """

    import pyku.meta as meta

    y_name, x_name = meta.get_projection_yx_varnames(ds)

    # ys = ds.coords[y_name].to_numpy()
    xs = ds.coords[x_name].to_numpy()

    if xs.ndim > 1:
        raise ValueError(
            f"Dimension of projection coordinates is {xs.ndim}, when 1 is "
            "expected"
        )

    return len(xs)


def _set_georeferencing_attrs(ds, area_def=None):
    """
    Set gereferencing attributes.

    Arguments:

        ds (:class:`xarray.Dataset`): The input dataset.

        area_def (:class:`pyresample.AreaDefinition`): Optional. If the
            dataset does not contain projection attributes, these are set
            according to parameter `area_def`.

    Returns:
        :class:`xarray.Dataset`: The dataset with georeferencing attributes.
    """

    import pyresample
    import xarray as xr
    import numpy as np

    # Sanity checks
    # -------------

    if (
        area_def is not None and
        not isinstance(area_def, pyresample.AreaDefinition)
    ):

        raise TypeError(
            "Expected an instance of AreaDefinition, but got "
            f"{type(area_def).__name__} instead."
        )

    # Get area definition
    # -------------------

    if area_def is None:
        area_def = get_area_def(ds)

    # Get CF area definitions from pyku metadata file
    # -----------------------------------------------

    areas_cf_definitions = get_areas_cf_definitions()
    area_id = area_def.area_id

    # If the pyku area_id is defined, add crs
    # ---------------------------------------

    if area_id in list(areas_cf_definitions.keys()):

        ds['regions'].attrs['grid_mapping'] = 'crs'

        cf_crs = xr.DataArray(
            np.array(1, dtype='int32'),
            name=areas_cf_definitions.get(area_id).get('crs_name'),
            attrs=areas_cf_definitions.get(area_id).get('crs_data')
        )

        ds = xr.merge([ds, cf_crs])

    else:

        ds['regions'].attrs['grid_mapping'] = 'crs'

        cf_crs = xr.DataArray(
            np.array(1, dtype='int32'),
            name='crs',
            attrs={
                'proj4': area_def.proj_str,
                'proj4_params': area_def.proj_str,
                'crs_wkt': area_def.crs_wkt,
                'spatial_ref': area_def.crs_wkt,
            }
        )

        ds = xr.merge([ds, cf_crs])

    return ds


def apply_georeferencing(ds, area_def):
    """
    Apply/force georeferencing to dataset. This function is usefull if data
    with a known georeferencing are available but the georeferencing is not
    correct/broken.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
        area_def (:class:`pyresample.AreaDefinition`): The area definition.

    Returns:
        :class:`xarray.Dataset`:
            Dataset containing projection coordinates, geographical coordinates
            according to the georeferincing dataset.

    Example:

        Exemplary data are loaded and regridded to a default *pyku* projection.
        Then the georeferencing is broken for the example.

        .. ipython::
           :okwarning:

           In [0]: %%time
              ...: import pyku
              ...: # Get data and project to HYRAS 5km resolution grid
              ...: # -------------------------------------------------
              ...:
              ...: ds = pyku.resources.get_test_data('global_data')
              ...: ds = ds.pyku.project('HYR-LAEA-5')
              ...:
              ...: # Break georeferencing
              ...: # --------------------
              ...:
              ...: broken = ds.drop_vars(['crs', 'y', 'x'])
              ...: print("Broken dataset")
              ...: print(broken)

        The georeferencing is then repaired by applying the georeferencing
        to the broken data.

        .. ipython::
           :okwarning:

           In [1]: %%time
              ...: import pyku.geo as geo
              ...: repaired = geo.apply_georeferencing(broken, 'HYR-LAEA-5')
              ...: print(repaired)
    """

    from pyku.meta import get_geographic_latlon_varnames
    from pyku.meta import get_projection_yx_varnames
    import xarray as xr

    # Info for sanity
    # ---------------

    logger.info(
        "Applying georeferencing to a dataset should not be the default. "
        "The georeferencing should be properly set in the first place. "
        "It is impossible to include all issues that could in a bad dataset. "
        "This function covers only common issues. "
    )

    # Sanity checks
    # -------------

    if isinstance(area_def, xr.DataArray):
        raise ValueError(
            'area_def must be a pyresample.AreaDefintion, not DataArray'
        )

    if isinstance(area_def, xr.Dataset):
        logger.warning("Using a xr.Dataset for the area_def is deprecated")
        area_def = get_area_def(area_def)

    # If a string identifier is passed, convert to an area definition
    # ---------------------------------------------------------------

    if isinstance(area_def, str):
        area_def = load_area_def(area_def)

    try:
        in_lat_name, in_lon_name = get_geographic_latlon_varnames(ds)
    except Exception:
        in_lat_name, in_lon_name = 'lat', 'lon'

    try:
        in_y_name, in_x_name = get_projection_yx_varnames(ds)
    except Exception:
        in_y_name, in_x_name = 'y', 'x'

    xs, ys = area_def.get_proj_coords()
    xs = xs[0, :]
    ys = ys[:, 0]

    lons, lats = area_def.get_lonlats()

    if in_y_name is None and in_x_name is None:
        ds = ds.assign_coords({'y': ys, 'x': xs})

    if in_y_name not in ds.coords or in_x_name not in ds.coords:
        ds = ds.assign_coords({'y': ys, 'x': xs})

    if in_lat_name is None and in_lon_name is None:
        ds = ds.assign_coords({'lat': lats, 'lon': lons})

    ds = project(ds, area_def=area_def)

    return ds


def get_georeferencing(ds):
    """
    Return georeferencing from dataset.

    The returned dataset contains projection coordinates x/y, geographical
    coordinates lat/lon.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`xarray.Dataset`:
            Dataset containing projection coordinates, geographical
            coordinates.

    Notes:
        Accepted names for geographic longitude, latitude, projection
        coordinates x and y are defined in pyku under ``etc/metadata.yaml``
    """

    import xarray as xr
    import pyku.meta as meta

    # Get geographic latlon names
    # ---------------------------

    lat_name, lon_name = meta.get_geographic_latlon_varnames(ds)
    y_name, x_name = meta.get_projection_yx_varnames(ds)

    # Something seems a bit off in this checking
    # ------------------------------------------

    if y_name == lat_name and x_name == lon_name:

        if ds[y_name] == 1 and ds[x_name].ndim == 1:

            nlons = get_nx(ds)
            nlats = get_ny(ds)

            # lats = np.array([lats.transpose()]*nlons).transpose()
            # lons = np.array([lons]*nlats)

        elif nlats == 1 and nlons != 1:
            raise Exception("Edge case in get_lonlats should not be possible")

        elif nlats != 1 and nlons == 1:
            raise Exception("Edge case in get_lonlats should not be possible")

        else:
            pass

    # Create DataArrays containing lons and lats
    # ------------------------------------------

    da_lons = xr.DataArray(
        data=ds.coords[lon_name].to_numpy(),
        coords=dict(
            y=([y_name], ds[y_name].to_numpy()),
            x=([x_name], ds[x_name].to_numpy()),
        ),
        dims=[y_name, x_name],
        name=lon_name,
    )

    da_lats = xr.DataArray(
        data=ds[lat_name].to_numpy(),
        coords=dict(
            y=([y_name,], ds[y_name].to_numpy()),
            x=([x_name,], ds[x_name].to_numpy()),
        ),
        dims=[y_name, x_name],
        name=lat_name,
    )

    # Merge into dataset and remove attributes
    # ----------------------------------------

    ds_georeferencing = xr.merge([da_lats, da_lons])
    ds_georeferencing.attrs = {}

    # Convert lat and lon from data to coordinates
    # --------------------------------------------

    ds_georeferencing = ds_georeferencing.set_coords((lat_name, lon_name))

    ds_georeferencing[lat_name].attrs = ds[lat_name].attrs
    ds_georeferencing[lon_name].attrs = ds[lon_name].attrs
    ds_georeferencing[y_name].attrs = ds[y_name].attrs
    ds_georeferencing[x_name].attrs = ds[x_name].attrs

    return ds_georeferencing


def get_yx(ds, dtype='ndarray'):
    """
    Return y x projection coordinates in dataset.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
        dtype (str): Output type, either ``ndarray`` for a tuple of ndarrays,
            or ``xr.Dataset``.

    Returns:
        tuple[:class:`numpy.ndarray`: (y, x). If no y or x projection
            coordinates are found in the dataset, ``None`` is returned.
    """

    import xarray as xr
    import numpy as np
    import pyku.meta as meta

    # Get geographic latlon names
    # ---------------------------

    y_name, x_name = meta.get_projection_yx_varnames(ds)

    ys = ds.coords[y_name].to_numpy()
    xs = ds.coords[x_name].to_numpy()

    nx = get_nx(ds)
    ny = get_ny(ds)

    ys2d = np.array([ys.transpose()] * nx).transpose()
    xs2d = np.array([xs] * ny)

    # Return tuple of numpy ndarrays
    # ------------------------------

    if dtype in ['ndarray']:
        return ys2d, xs2d

    # Return xarray Dataset
    # ---------------------

    elif dtype in ['xr.Dataset']:

        # Create DataArrays containing lons and lats
        # ------------------------------------------

        da_ys = xr.DataArray(
            data=ys2d,
            coords=dict(y=(['y'], ys), x=(['x'], xs)),
            dims=['y', 'x'],
            name='y2D',
            attrs={'standard_name': 'NA', 'units': 'NA'},
        )

        da_xs = xr.DataArray(
            data=xs2d,
            coords=dict(y=(['y'], ys), x=(['x'], xs)),
            dims=['y', 'x'],
            name='x2D',
            attrs={'standard_name': 'NA', 'units': 'NA'},
        )

        # Merge into dataset and remove attributes
        # ----------------------------------------

        ds_y_x = xr.merge([da_ys, da_xs])
        ds_y_x.attrs = {}

        # Convert lat and lon from data to coordinates
        # --------------------------------------------

        ds_y_x = ds_y_x.set_coords(('x2D', 'y2D'))

        return ds_y_x

    else:
        message = f"dtype {dtype} not implemented"
        raise Exception(message)


def get_yx_area_extent(ds):
    """
    Get area exent in projection coordinates

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        tuple: (lower_left_x, lower_left_y, upper_right_x, upper_right_y)
    """

    import pyku.meta as meta
    import pyresample.utils

    # Get y and x projection coordinate variable names
    y_varname, x_varname = meta.get_projection_yx_varnames(ds)

    # Scourging the source code of pyresample I found these internal functions
    # that do what I was trying to program myself. This is bad practice to use
    # internal functions from an external code but... these functions are great
    # and do exactly what I want them to do... Hence I implement them here and
    # keep my own code as backup for now.

    # Determine the area extent
    # -------------------------

    area_extent = pyresample.utils.cf._get_area_extent_from_cf_axis(
        pyresample.utils.cf._load_cf_axis_info(ds, x_varname),
        pyresample.utils.cf._load_cf_axis_info(ds, y_varname),
    )

    lower_left_x, lower_left_y, upper_right_x, upper_right_y = area_extent

    return lower_left_x, lower_left_y, upper_right_x, upper_right_y


def get_lonlats(ds, dtype='ndarray'):
    """
    Return lon lats in dataset

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
        dtype (str): Output type, either 'ndarray' for a tuple of ndarrays, or
            ``xarray.Dataset`` for an xarray dataset

    Returns:
        Tuple[:class:`numpy.ndarray`]: (lons, lats). If no latidudes or
        longitudes are found in the dataset, ``None`` is returned.

    Example:
        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...:
              ...: ds = pyku.resources.get_test_data('hyras-tas-monthly')
              ...:
              ...: ds.pyku.get_lonlats()
    """

    import xarray as xr
    import numpy as np
    import pyku.meta as meta

    # Sanity check
    # ------------

    is_dataset_or_dataarray = (
        isinstance(ds, xr.Dataset)
        or isinstance(ds, xr.DataArray)
    )
    if not is_dataset_or_dataarray:
        raise TypeError(f"Not a Dataset or DataArray {type(ds)}")

    # Get geographic latlon names
    # ---------------------------

    lat_name, lon_name = meta.get_geographic_latlon_varnames(ds)

    if lat_name is None and lon_name is None:
        logger.warning("Dataset has no longitudes or latitudes data")

        try:

            logger.warning(
                "Determining longitudes and latitudes data from "
                "area definition"
            )

            lons, lats = get_area_def(ds).get_lonlats()

            return lons, lats

        except Exception:

            return None, None

    lons = ds.coords[lon_name].to_numpy()
    lats = ds.coords[lat_name].to_numpy()

    if ds[lon_name].attrs.get('units') in ['radian']:
        logger.warning('longitude unit conversion from radians to degrees')
        lons = np.degrees(lons)

    if ds[lat_name].attrs.get('units') in ['radian']:
        logger.warning('latitude unit conversion from radians to degrees')
        lats = np.degrees(lats)

    # If geographic and projection coordinates are the same
    # -----------------------------------------------------

    if meta.has_projection_coordinates(ds):

        y_name, x_name = meta.get_projection_yx_varnames(ds)

        xs = ds.coords[x_name].to_numpy()
        ys = ds.coords[y_name].to_numpy()

        if y_name == lat_name and x_name == lon_name:

            if lats.ndim == 1 and lons.ndim == 1:

                nlons = get_nx(ds)
                nlats = get_ny(ds)

                lats = np.array([lats.transpose()] * nlons).transpose()
                lons = np.array([lons] * nlats)

            elif lats.ndim == 1 and lons.ndim != 1:
                raise ValueError(
                    "lon and lat do not have the same number of dimensions. "
                    f"latitudes have dimension {lats.ndim}, whereas "
                    f"longitudes have dimensions {lons.ndim}"
                )

            elif lats.ndim != 1 and lons.ndim == 1:
                raise Exception(
                    "lon and lat do not have the same number of dimensions. "
                    f"latitudes have dimension {lats.ndim}, whereas "
                    f"longitudes have dimensions {lons.ndim}"
                )

            elif xs is None or ys is None:
                raise Exception(
                    "Bug. This edge case in get_lonlats should not be possible"
                )

    # Return tuple of numpy ndarrays
    # ------------------------------

    if dtype in ['ndarray']:
        return lons, lats

    # Return xarray Dataset
    # ---------------------

    elif dtype in ['xr.Dataset']:

        # Create DataArrays containing lons and lats
        # ------------------------------------------

        da_lons = xr.DataArray(
            data=lons,
            coords=dict(y=(['y'], ys), x=(['x'], xs)),
            dims=['y', 'x'],
            name='lon',
            attrs={'standard_name': 'longitude', 'units': 'degrees_east'},
        )

        da_lats = xr.DataArray(
            data=lats,
            coords=dict(y=(['y',], ys), x=(['x',], xs)),
            dims=['y', 'x'],
            name='lat',
            attrs={'standard_name': 'latitude', 'units': 'degrees_north'},
        )

        # Merge into dataset and remove attributes
        # ----------------------------------------

        ds_lat_lon = xr.merge([da_lats, da_lons])
        ds_lat_lon.attrs = {}

        # Convert lat and lon from data to coordinates
        # --------------------------------------------

        ds_lat_lon = ds_lat_lon.set_coords(('lat', 'lon'))

        return ds_lat_lon

    else:
        raise TypeError(
            f"dtype should be 'xr.Dataset' or 'xr.DataArray', not {dtype}"
        )


def set_latlon_bounds(ds):
    """
    Determine and set geographic coordinate bounds.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`xarray.Dataset`: The dataset with geographic coordinate bounds.

    Example:
        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras-tas-monthly')
              ...: ds.pyku.set_latlon_bounds()
    """

    import cf_xarray  # noqa, this library defines the cf namespace
    import pyku.meta as meta

    ds_out = ds.copy()

    lat_bnds_varname, lon_bnds_varname = meta.get_latlon_bounds_varnames(ds)

    if (lat_bnds_varname is None) != (lon_bnds_varname is None):
        raise AssertionError(
            "latitude and longitude bounds must both either exitst, or both "
            "be absent"
        )

    if lat_bnds_varname is not None and lon_bnds_varname is not None:
        return ds

    lat_name, lon_name = meta.get_geographic_latlon_varnames(ds_out)

    ds_out = ds_out.cf.add_bounds([lat_name, lon_name])

    return ds_out


def get_area_at_true_scale(ds):
    """
    Get the area of a single pixel at true scale. Given the dataset resolution
    and area definition, the area of a pixel centered at true scale is
    determined.

    Arguments:
        ds (:class:`xarray.Dataset`): Georeferenced dataset

    Returns:
        float: Area at true scale.

    Example:

        .. ipython::
           :okwarning:

           In [0]: import xarray
              ...: import pyku.geo as geo
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: geo.get_area_at_true_scale(ds)
    """

    import numpy as np
    import pyproj
    import pyku.meta as meta
    from pyproj import Geod

    # Initialize the Geod object with WGS84 ellipsoid
    # -----------------------------------------------

    geod = Geod(ellps='WGS84')

    # Get area definition
    # -------------------

    area_def = get_area_def(ds)

    # Get geographic and projection coordinate names
    # ----------------------------------------------

    y_name, x_name = meta.get_projection_yx_varnames(ds)

    proj_dict = area_def.proj_dict

    if 'longlat' in [proj_dict.get('proj')]:

        # e.g. Mercator or regular lat lon
        true_scale_lat, true_scale_lon = 0, 0

    elif (
        'ob_tran' in [proj_dict.get('proj')]
        and 'longlat' in [proj_dict.get('o_proj')]
    ):

        # Rotated grid
        inverse_transformer = pyproj.Transformer.from_crs(
            area_def.proj_str,
            'EPSG:4326',
            always_xy=True
        )

        true_scale_lon, true_scale_lat = \
            inverse_transformer.transform(0, 0)

    elif 'lat_ts' in proj_dict.keys() and 'lon_0' in proj_dict.keys():

        # e.g. Mercator or regular lat lon
        lat_ts = proj_dict.get('lat_ts')
        lon_0 = proj_dict.get('lon_0')
        true_scale_lat, true_scale_lon = lat_ts, lon_0

    elif 'lat_1' in proj_dict.keys() and 'lon_0' in proj_dict.keys():

        # e.g. LCC. Here there are two locations with true scale
        lat_1 = proj_dict.get('lat_1')
        lon_0 = proj_dict.get('lon_0')
        true_scale_lat, true_scale_lon = lat_1, lon_0

    elif 'lat_0' in proj_dict.keys() and 'lon_0' in proj_dict.keys():

        # e.g. LAEA. Here all grid cells have the same area
        lat_0 = proj_dict.get('lat_0')
        lon_0 = proj_dict.get('lon_0')
        true_scale_lat, true_scale_lon = lat_0, lon_0

    else:
        raise Exception(
            "Grid cell area at true scale could not be determined for "
            f"for projection {area_def.proj_str}"
        )

    # Define transformer and inverse transformer
    # ------------------------------------------

    transformer = pyproj.Transformer.from_crs(
        'EPSG:4326',
        area_def.proj_str,
        always_xy=True
    )

    inverse_transformer = pyproj.Transformer.from_crs(
        area_def.proj_str,
        'EPSG:4326',
        always_xy=True
    )

    # Determine step in y and x projection coordinates
    # ------------------------------------------------

    dy = np.diff(ds[y_name].values)
    dx = np.diff(ds[x_name].values)

    # Check projection coordinates are regularly distributed for sanity
    # -----------------------------------------------------------------

    # The spacing between y projection coordinates and x projection
    # coordinates is expected to be the same within a tight tolerance. the
    # acceptable tolerance is set depending on the units, either degrees or
    # meters.

    x_name_units_ref = ds[x_name].attrs.get('units')
    y_name_units_ref = ds[y_name].attrs.get('units')

    # Check if projection y/x varname is in degree
    is_degree = (
        x_name_units_ref is not None
        and y_name_units_ref is not None
        and x_name_units_ref.lower().find('degree') != -1
        and y_name_units_ref.lower().find('degree') != -1
    )

    # Check if projection y/x varname is in meters
    is_meter = (
        x_name_units_ref is not None
        and y_name_units_ref is not None
        and x_name_units_ref.lower() in ['m']
        and y_name_units_ref.lower() in ['m']
    )

    # Set tolerance to defaults depending on unit
    if is_degree:
        tolerance = 1E-4
    elif is_meter:
        tolerance = 10
    else:
        raise Exception(
            "The projection coordinates are not evenly spaced. See "
            "https://gitlab.dwd.de/ku/libraries/pyku/-/issues/195"
        )

    # Check if values fall within tolerance
    is_close_dy = np.isclose(dy, dy[0], atol=tolerance)
    is_close_dx = np.isclose(dx, dx[0], atol=tolerance)

    # Check if all values fall within tolerance
    dy_all_same = bool(np.all(is_close_dy))
    dx_all_same = bool(np.all(is_close_dx))

    if dy_all_same is False:
        raise Exception("Not all dys are the same")

    if dx_all_same is False:
        raise Exception("Not all dxs are the same")

    # Since all dys and dxs are the same, take the first element
    # ----------------------------------------------------------

    dy = dy[0]
    dx = dx[0]

    # Determine y/x projection coordinates at true scale
    # --------------------------------------------------

    true_scale_x, true_scale_y = transformer.transform(
        true_scale_lon, true_scale_lat
    )

    # Determine size of 'virtual' pixel at true scale
    # -----------------------------------------------

    # We have calculated the area of each pixels. Now we need to know the
    # area at true scale in order to obtain the proper scaling factor.
    # Hence we need to calculate the latitude and longitude of each corner
    # of a 'virtual' pixel centered at true scale. ll stands for lower
    # left, lr for lower right, ur for upper right and ul for upper left.

    ll = true_scale_x - dx/2, true_scale_y - dy/2
    lr = true_scale_x + dx/2, true_scale_y - dy/2
    ur = true_scale_x + dx/2, true_scale_y + dy/2
    ul = true_scale_x - dx/2, true_scale_y + dy/2

    ll = inverse_transformer.transform(*ll)
    lr = inverse_transformer.transform(*lr)
    ur = inverse_transformer.transform(*ur)
    ul = inverse_transformer.transform(*ul)

    # Determine the area of the 'virtual' pixel at true scale
    # -------------------------------------------------------

    true_scale_area, _ = geod.polygon_area_perimeter(
        [ll[0], lr[0], ur[0], ul[0]],
        [ll[1], lr[1], ur[1], ul[1]]
    )

    # Take the absolute value
    # -----------------------

    # This is necessary because the convention in pyresample is to read
    # from top to bottom, and the programmer was thinking from bottom to
    # top. Hence the orientation of the surface can be flipped.

    true_scale_area = abs(true_scale_area)

    return true_scale_area


def set_spatial_weights(ds, how='area'):
    """
    Set area weights for a dataset.

    Arguments:
        ds (:class:`xarray.Dataset`): Dataset which should contain latitude
            ('lat') as a coordinate.
        how (str): Method to determine weights. Default is set to 'area'.
            The gridcell areas will be calculated according to the lat and lon
            bounds. Optionally one can select weighting by cosinus of latitude
            how='cos'.

    Returns:
        :class:`xarray.Dataset`: Dataset with an added 'weights' variable
        containing the calculated area weights.

    Example:

        .. ipython::
           :okwarning:

           @savefig geo_spatial_weights1.png width=4in
           In [0]: import xarray, pyku
              ...: import pyku.analyse as analyse
              ...: ds = pyku.resources.get_test_data('global_data')
              ...: ds = ds.pyku.project('world_360x180')
              ...: ds = ds.pyku.set_spatial_weights(how='area')
              ...: analyse.one_map(ds.weights)

        .. ipython::
           :okwarning:

           @savefig geo_spatial_weights2.png width=4in
           In [0]: import xarray, pyku
              ...: import pyku.analyse as analyse
              ...: ds = pyku.resources.get_test_data('global_data')
              ...: ds = ds.pyku.project('EUR-44')
              ...: ds = ds.pyku.set_spatial_weights(how='area')
              ...: analyse.one_map(ds.weights, crs='EUR-44')
    """

    # Summary
    # -------

    # The function has gotten a little longer than usual. The function has two
    # options: 'cos' and 'area'
    #
    # - When using a cosine with a regular grid, everything is straightforward.
    # - When using the area option, which should work for any geographic
    #   projection, this is more complicated.
    #
    # For the general case, the strategy is:
    # - Determine the grid cell boundaries
    # - Calculate the area for each grid cell. There there are two cases. If
    #   the projection is regular, the bounds are given for latitudes (upper,
    #   lower) and longitudes (left, right) separately. For an irregular grid,
    #   the bounds are given for
    #   each grid cell (lower left, lower right, upper right, upper left)
    # - Calculate the area at true scale, which depends on the projection type.
    #   Since the true scale can be located outside the map, a 'virtual' grid
    #   cell is constructed at true scale and its area calculated.

    import xarray as xr
    import numpy as np
    import pyku.meta as meta
    from pyproj import Geod

    out_ds = ds.copy()

    # Sanity checks
    # -------------

    if how not in ['area', 'cos']:
        raise ValueError("Parameter 'how' should be either 'area', or 'cos'")

    # Get geographic and projection coordinate names
    # ----------------------------------------------

    lat_name, lon_name = meta.get_geographic_latlon_varnames(ds)
    y_name, x_name = meta.get_projection_yx_varnames(ds)

    # Get area definition
    # -------------------

    area_def = get_area_def(ds)

    if how == 'area':

        # Set latitude and longitude bounds if not readily available
        # ----------------------------------------------------------

        if 'lat_bounds' not in ds or 'lon_bounds' not in ds:
            out_ds = set_latlon_bounds(ds)

        lat_bnds = out_ds['lat_bounds']
        lon_bnds = out_ds['lon_bounds']

        # Get size of the bounds. For a generic cell, we have 4 bounds. For
        # a cell with a regular longlat raster, we have 2 bounds.
        lat_bounds_size = dict(lat_bnds.sizes)['bounds']
        lon_bounds_size = dict(lon_bnds.sizes)['bounds']

        # Check bounds have the same dimension for sanity
        if lat_bounds_size != lon_bounds_size:
            raise Exception(
                "latitudes and longitude bounds have different dimensions"
            )

        # Set bounds_size since they are identical
        # ----------------------------------------

        bounds_size = lat_bounds_size

        # Extract corners from bounds
        # ---------------------------

        if bounds_size == 2:

            corners_lat = xr.concat(
                [
                    lat_bnds.isel(bounds=0),
                    lat_bnds.isel(bounds=0),
                    lat_bnds.isel(bounds=1),
                    lat_bnds.isel(bounds=1)
                ],
                dim="corner"
            )

            corners_lon = xr.concat(
                [
                    lon_bnds.isel(bounds=0),
                    lon_bnds.isel(bounds=1),
                    lon_bnds.isel(bounds=1),
                    lon_bnds.isel(bounds=0)
                ],
                dim="corner"
            )

        elif bounds_size == 4:

            corners_lat = xr.concat(
                [
                    lat_bnds.isel(bounds=0),
                    lat_bnds.isel(bounds=1),
                    lat_bnds.isel(bounds=2),
                    lat_bnds.isel(bounds=3)
                ],
                dim="corner"
            )

            corners_lon = xr.concat(
                [
                    lon_bnds.isel(bounds=0),
                    lon_bnds.isel(bounds=1),
                    lon_bnds.isel(bounds=2),
                    lon_bnds.isel(bounds=3)
                ],
                dim="corner"
            )

        else:
            raise Exception(f"bounds of size {bounds_size} not supported")

        # Initialize the Geod object with WGS84 ellipsoid
        # -----------------------------------------------

        geod = Geod(ellps='WGS84')

        # Vectorized function to calculate the area of each grid cell
        # -----------------------------------------------------------

        # The dimensions of the object return is then lat, lon and not lon,
        # lat. This case is not checked for.

        def vectorized_area(lats, lons):
            area, _ = geod.polygon_area_perimeter(lons, lats)
            return np.abs(area)

        # Apply the vectorized_area function using xr.apply_ufunc
        # -------------------------------------------------------

        grid_cell_area = xr.apply_ufunc(
            vectorized_area,
            corners_lat,
            corners_lon,
            input_core_dims=[["corner"], ["corner"]],
            vectorize=True,
            keep_attrs=True
        )

        # Determine the area at true scale
        # --------------------------------

        true_scale_area = get_area_at_true_scale(ds)

        # Add the weights to dataset
        # --------------------------

        out_ds.coords['weights'] = grid_cell_area / true_scale_area

    elif how == 'cos':

        # assert that dataset projection is provided on a regular grid
        if area_def.proj_dict['proj'] not in ['eqc', 'longlat']:
            raise ValueError(
                "Latitudinal weighting by cosinus can only be applied to "
                "regular grids! Please use weighting by 'area'!"
            )

        # Get latitudes as 2D numpy array
        # -------------------------------

        longitudes, latitudes = get_lonlats(ds, dtype='ndarray')

        # Calculate weights based on cosine of latitude
        # ---------------------------------------------

        weights = np.cos(np.deg2rad(latitudes))

        # Add weights as to dataset
        # -------------------------

        out_ds.coords['weights'] = ([y_name, x_name], weights)

    return out_ds


def are_longitudes_wrapped(ds):
    """
    Check if the longitudes in the dataset are within the range [-180, 180).

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset containing longitude
            values.

    Returns:
        bool: True if all longitudes are within the range [-180, 180),
        otherwise False.

    Example:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('global_data')
              ...: ds.pyku.are_longitudes_wrapped()
    """

    import pyku.meta as meta
    import numpy as np

    lat_name, lon_name = meta.get_geographic_latlon_varnames(ds)

    if lon_name is None:
        raise AssertionError("No geographic longitudes in dataset!")

    ds_copy = ds.copy()
    ds_copy[lon_name] = ((ds_copy[lon_name] + 180) % 360) - 180

    # Account for float precision noise in the modulo result. We use a
    # tolerance significantly stricter than the required 1e-4 for longitude
    # accuracy.

    is_wrapped = np.allclose(
        ds_copy[lon_name].values, ds[lon_name].values, atol=1e-12
    )

    return bool(is_wrapped)


def wrap_longitudes(ds):
    """
    Wrap longitudes to [-180, +180[, and sort by increasing longitudes.

    Arguments:
        ds (:class:`xarray.Dataset`): The input data

    Returns:
        :class:`xarray.Dataset`: Data with longitudes wrapped to [-180,180[,
        and sorted by increasing longitude.

    Example:

        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('global_data')
              ...: ds.pyku.wrap_longitudes()
    """

    import pyku.meta as meta
    import xarray as xr

    if (
        not meta.has_geographic_coordinates(ds) or
        not meta.has_projection_coordinates(ds)
    ):
        raise AssertionError(
            "Dataset must contain both geographic and projection coordinates!"
        )

    # Get projection and geographic coordinates names
    # -----------------------------------------------

    lat_name, lon_name = meta.get_geographic_latlon_varnames(ds)
    y_name, x_name = meta.get_projection_yx_varnames(ds)

    # Keep attributes during operations
    # ---------------------------------

    xr.set_options(keep_attrs=True)

    # Convert any longitudes from 0 to 360 to [-180 to 180[
    # -----------------------------------------------------

    # If longitude is in the data, wrap
    # ---------------------------------

    if lon_name is not None:
        ds[lon_name] = ((ds[lon_name] + 180) % 360) - 180

    # If y projection name is also the geographic longitude (e.g. lat long)
    # ---------------------------------------------------------------------

    if x_name in [lon_name]:
        ds[x_name] = ((ds[x_name] + 180) % 360) - 180

    # Sort by increasing y projection coordinate
    # ------------------------------------------

    # I may have a Gedankenfehler here but I do not think I do. Longitudes are
    # generally 2D arrays, whereas projection coordinates are one D arrays.
    # Also mostly this function will do something for regular lat lon
    # projections. So if I that is a Bug, it may go unnoticed...

    ds = ds.sortby(x_name)

    return ds


def is_georeferencing_sorted(ds):
    """
    Check if the georeferencing coordinates in the dataset are sorted in a
    standard geospatial order: x-coordinates (longitude/easting) increasing
    from left to right and y-coordinates (latitude/northing) increasing from
    bottom to top.

    Arguments:
        ds (xarray.Dataset): The input dataset containing georeferencing
            coordinates.

    Returns:
        bool: True if the georeferencing coordinates are sorted as described,
        False otherwise.

    Example:
        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('model_data')
              ...: ds.pyku.is_georeferencing_sorted()
    """

    import pyku.meta as meta

    if not meta.has_projection_coordinates(ds):
        raise AssertionError("Dataset must have projection coordinates!")

    # Get geographic and projection coordinates variable names
    # --------------------------------------------------------

    y_name, x_name = meta.get_projection_yx_varnames(ds)
    ds_copy = ds[[y_name, x_name]].copy()

    ds_copy = ds_copy.sortby(x_name, ascending=True)
    ds_copy = ds_copy.sortby(y_name, ascending=False)

    is_sorted = (
        ds_copy[x_name].equals(ds[x_name]) and
        ds_copy[y_name].equals(ds[y_name])
    )

    return bool(is_sorted)


def are_yx_projection_coordinates_strictly_monotonic(ds):
    """
    Checks if y projection coordinates are strictly increasing or strictly
    decreasing

    Arguments:
        ds (xarray.Dataset): The input dataset.

    Returns:
        bool: True if y and x coordinates are strictly monotonic.

    Example:
        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('model_data')
              ...: ds.pyku.are_yx_projection_coordinates_strictly_monotonic()
    """

    import pyku.meta as meta

    # For unstructured geographic coordinates (e.g., ICON grid), monotonicity
    # is not applicable; returning True by default.

    if meta.has_unstructured_geographic_coordinates(ds):
        return True

    y_name, x_name = meta.get_projection_yx_varnames(ds)

    y_diffs = ds[y_name].diff(dim=y_name)
    x_diffs = ds[x_name].diff(dim=x_name)

    is_y_increasing = (y_diffs > 0).all()
    is_y_decreasing = (y_diffs < 0).all()

    is_x_increasing = (x_diffs > 0).all()
    is_x_decreasing = (x_diffs < 0).all()

    are_strictly_monotonic = (
        bool(is_y_increasing or is_y_decreasing) and
        bool(is_x_increasing or is_x_decreasing)
    )

    return are_strictly_monotonic


def sort_georeferencing(ds):
    """
    Sort georeferencing. After this operation, the data are arranged from left
    to right and top to bottom.

    While Pyku can handle any arranging of the data, following this recommended
    structure ensures a more standardized data layout, reducing the likelihood
    of encountering edge cases.

    Arguments:
        ds (:class:`xarray.Dataset`): The input data.

    Returns:
        :class:`xarray.Dataset`: Data with georeferencing sorted from left to
        right and top to bottom.

    Example:
        .. ipython::
           :okwarning:

           @savefig geo_sort_georeferencing.png width=5in
           In [0]: import matplotlib.pyplot as plt
              ...: import pyku
              ...:
              ...: plt.close('all')
              ...:
              ...: # Get coordinate reference system of original data
              ...: # ------------------------------------------------
              ...:
              ...: ccrs_original = (
              ...:     pyku.resources.get_test_data('model_data')
              ...:     .pyku.get_area_def()
              ...:     .to_cartopy_crs()
              ...: )
              ...:
              ...: # Get coordinate reference system of sorted data
              ...: # ----------------------------------------------
              ...:
              ...: ccrs_sorted = (
              ...:     pyku.resources.get_test_data('model_data')
              ...:     .pyku.sort_georeferencing()
              ...:     .pyku.get_area_def()
              ...:     .to_cartopy_crs()
              ...: )
              ...:
              ...: # Plot side-by-side
              ...: # -----------------
              ...:
              ...: plt.figure(figsize=(10, 5))
              ...:
              ...: ax1 = plt.subplot(2, 2, 1, projection=ccrs_original)
              ...: ax1.set_title('original')
              ...: ax1.set_global()
              ...: ax1.coastlines('auto')
              ...: ax1.gridlines()
              ...:
              ...: ax2 = plt.subplot(2, 1, 1, projection=ccrs_sorted)
              ...: ax2.set_title('sorted')
              ...: ax2.set_global()
              ...: ax2.coastlines('auto')
              ...: ax2.gridlines()
    """

    import xarray as xr
    import pyku.meta as meta

    # Keep attributes during operations
    # ---------------------------------

    xr.set_options(keep_attrs=True)

    if not meta.has_projection_coordinates(ds):
        raise AssertionError("Data must have projection coordinates!")

    # Get geographic and projection coordinates variable names
    # --------------------------------------------------------

    y_name, x_name = meta.get_projection_yx_varnames(ds)

    ds_copy = ds.copy()

    ds_copy = ds_copy.sortby(x_name, ascending=True)
    ds_copy = ds_copy.sortby(y_name, ascending=False)

    return ds_copy


def _get_area_def_from_crs_cf(ds):
    """
    Get area definition from CF metadata

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`pyresample.geometry.AreaDefinition`: The area definition.

    Todos:
        This function could be split into further distinguishing between the
        pure CF standard and the CF standard where the WKT string is read.
    """

    import pyresample.utils

    try:
        area_def, cf_info = pyresample.utils.load_cf_area(ds)
        return area_def

    except Exception:
        return None


def _get_area_def_from_global_attrs(ds):
    """
    Get area definition from global attributes (deprecated)

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`pyresample.geometry.AreaDefinition`: The area definition.
    """

    import pyku.meta as meta
    from pyresample.geometry import AreaDefinition

    # Read the projection parameters from the global attributes
    # ---------------------------------------------------------

    # Like it used to be implemented in pyku by default but not anymore

    proj_str = ds.attrs.get('proj_str', None)
    area_extent = ds.attrs.get('area_extent', None)

    # Set the area definition by default to None
    # ------------------------------------------

    area_def = None

    # Build area definition if old pyku global metadata available
    # -----------------------------------------------------------

    if proj_str is not None and area_extent is not None:

        logger.warning("Trying to load custom projection global attrs")

        y_varname, x_varname = meta.get_projection_yx_varnames(ds)

        area_def = AreaDefinition(
            area_id='on-the-fly-area_id',
            description='on-the-fly-description',
            proj_id='on-the-fly-id',
            projection=proj_str,
            height=len(ds[y_varname]),
            width=len(ds[x_varname]),
            area_extent=area_extent
        )

    return area_def


def _get_area_def_from_crs_proj_str(ds):
    """
    Get area definition from PROJ string in the crs metadata.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`pyresample.geometry.AreaDefinition`: The area definition.
    """

    import pyku.meta as meta
    from pyresample.geometry import AreaDefinition

    try:

        crs_varname = meta.get_crs_varname(ds)

        proj4 = ds[crs_varname].attrs.get('proj4', None)
        proj4_params = ds[crs_varname].attrs.get('proj4_params', None)

        if proj4 is not None:
            proj_str = proj4

        if proj4_params is not None:
            proj_str = proj4_params

        y_varname, x_varname = meta.get_projection_yx_varnames(ds)

        area_extent = get_yx_area_extent(ds)

        area_def = AreaDefinition(
            area_id='on-the-fly-area_id',
            description='on-the-fly-description',
            proj_id='on-the-fly-id',
            projection=proj_str,
            height=len(ds[y_varname]),
            width=len(ds[x_varname]),
            area_extent=area_extent
        )

        return area_def

    except Exception:
        return None


def get_area_def(ds):
    """
    Get area definition.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`pyresample.geometry.AreaDefinition`: The area definition.

    Example:
        .. ipython::
           :okwarning:

           In [0]: import xarray, pyku
              ...: ds = pyku.resources.get_test_data('model_data')
              ...: print(ds.pyku.get_area_def())
    """

    if not are_yx_projection_coordinates_strictly_monotonic(ds):
        logger.warning(
            "Non-monotonic projection coordinates detected. "
            "The calculated area extent may be incorrect."
        )

    # Get area definitions
    # --------------------

    area_def_from_cf = _get_area_def_from_crs_cf(ds)
    area_def_from_crs_proj_str = _get_area_def_from_crs_proj_str(ds)
    area_def_from_global_attrs = _get_area_def_from_global_attrs(ds)

    # Return area definitions by priority
    # -----------------------------------

    if area_def_from_cf is not None:
        return area_def_from_cf
    elif area_def_from_crs_proj_str is not None:
        return area_def_from_crs_proj_str
    elif area_def_from_global_attrs is not None:
        return area_def_from_global_attrs
    else:
        raise Exception("Could not read area definition")


def select_area_extent(
    ds, lower_left_lat=None, lower_left_lon=None, upper_right_lat=None,
    upper_right_lon=None
):
    """
    Select an area extent in geographic coordinates, defined by the latitude
    and longitude of the lower-left and upper-right corners.

    Since only indexed coordinates can be selected in xarray, and these are
    typically the y and x projection coordinates rather than geographic
    latitudes and longitudes, this function allows selection based on
    geographic coordinates, which are generally not indexed.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
        lower_left_lat (float): Latitude of the lower left corner.
        lower_left_lon (float): Longitude of the lower left corner.
        upper_right_lat (float): Latitude of the upper right corner.
        upper_right_lon (float): Longitude of the upper right corner.

    Returns:
        :class:`xarray.Dataset`: Dataset within the selected area extent.

    Example:
        .. ipython::
           :okwarning:

           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: print(ds.pyku.get_area_def())
              ...:
              ...: ds = ds.pyku.select_area_extent(
              ...:     lower_left_lat=48.0,
              ...:     lower_left_lon=5.0,
              ...:     upper_right_lat=51.0,
              ...:     upper_right_lon=15.0,
              ...: )
              ...:
              ...: ds.isel(time=0).ana.one_map(var='tas')
    """

    import pyku.meta as meta
    import pyproj

    # Set default values to system min and max of data projection
    # -----------------------------------------------------------

    data_lower_left_lon, data_lower_left_lat, \
        data_upper_right_lon, data_upper_right_lat = \
        get_area_def(sort_georeferencing(ds)).area_extent_ll

    if lower_left_lat is None:
        lower_left_lat = data_lower_left_lat
    if lower_left_lon is None:
        lower_left_lon = data_lower_left_lon
    if upper_right_lat is None:
        upper_right_lat = data_upper_right_lat
    if upper_right_lon is None:
        upper_right_lon = data_upper_right_lon

    # Copy dataset to perform operations out-of-place
    # -----------------------------------------------

    ds_copy = ds.copy()

    # Get the original area definition
    # --------------------------------

    original_area_def = ds_copy.pyku.get_area_def()

    # Create transformer to convert from geographic to projection coordinates
    # -----------------------------------------------------------------------

    latlon_to_xy = pyproj.Transformer.from_crs(
        'EPSG:4326',
        original_area_def.proj_str,
        always_xy=True
    )

    # Transform lower left and upper right corners
    # --------------------------------------------

    lower_left_x, lower_left_y = latlon_to_xy.transform(
        lower_left_lon, lower_left_lat
    )

    upper_right_x, upper_right_y = latlon_to_xy.transform(
        upper_right_lon, upper_right_lat
    )

    # Get the name the of projection coordinates
    # ------------------------------------------

    y_varname, x_varname = meta.get_projection_yx_varnames(ds_copy)

    # The sort values
    # ---------------

    # The projection coordinates for y and x may not be sorted in ascending
    # order. but the slice function must align with the data's order.

    def ordering(dat, coord):

        ascend = (dat[coord].data == dat[coord].sortby(
            coord, ascending=True).data).all()

        descend = (dat[coord].data == dat[coord].sortby(
            coord, ascending=False).data).all()

        if ascend:
            return 'ascending'
        elif descend:
            return 'descending'
        else:
            return 'unordered'

    x_ordering = ordering(ds_copy, x_varname)
    y_ordering = ordering(ds_copy, y_varname)

    # Select area extent
    # ------------------

    if x_ordering == 'ascending':
        ds_copy = ds_copy.sel({x_varname: slice(lower_left_x, upper_right_x)})
    elif x_ordering == 'descending':
        ds_copy = ds_copy.sel({x_varname: slice(upper_right_x, lower_left_x)})
    else:
        logger.warn(
            f'Reordering projection coordinate {x_varname} in ascending order'
        )
        ds_copy = ds_copy.sortby(x_varname, ascending=True)
        ds_copy = ds_copy.sel({x_varname: slice(lower_left_x, upper_right_x)})

    if y_ordering == 'ascending':
        ds_copy = ds_copy.sel({y_varname: slice(lower_left_y, upper_right_y)})
    elif y_ordering == 'descending':
        ds_copy = ds_copy.sel({y_varname: slice(upper_right_y, lower_left_y)})
    else:
        logger.warn(
            f'Reordering projection coordinate {y_varname} in ascending order'
        )
        ds_copy = ds_copy.sortby(y_varname, ascending=True)
        ds_copy = ds_copy.sel({y_varname: slice(upper_right_y, lower_left_y)})

    return ds_copy


def select_neighborhood(
        ds, lat, lon, roi=10000, neighbours=1000, crop=False
):
    """
    Select all the given number of neighbours within the radius of influence
    (roi) around the selected point given in geographic coordinates.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
        lat (float): Geographic latitude.
        lon (float): Geographic longitude.
        roi (float): Radius of influence, given in meters.
        neighbours (int): Number of neighbours to be selected within radius of
            influence. Only the neighbours within the radius of influence are
            returned. If the number of neigbours within the radius of influence
            is smaller than the value given, only a subset is returned.
        crop (bool): Crop dataset with selected neighborhood.

    Returns:
        :class:`xarray.Dataset`: Dataset within the selected neighborhood.

    Example:
        .. ipython::
           :okwarning:

           @savefig geo_select_neighborhood.png width=4in
           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: selection = ds.pyku.select_neighborhood(
              ...:     lat=51,
              ...:     lon=10,
              ...:     roi=50000,
              ...:     neighbours=1000,
              ...:     crop=False
              ...: )
              ...: selection.ana.mean_map(var='tas')
    """

    import numpy as np
    import pandas as pd
    import pyku.meta as meta
    from pyresample import geometry, kd_tree

    # Get the source area definition
    # ------------------------------

    source_area_def = ds.pyku.get_area_def()

    # Generate a Swath Definition in geographic coordinates for given point
    # ---------------------------------------------------------------------

    target_area_def = geometry.SwathDefinition(
        lons=[lon],
        lats=[lat],
    )

    # Search the indices of n neighbours within the radius of influence
    # -----------------------------------------------------------------

    vii, voi, index_array, distance_array = kd_tree.get_neighbour_info(
        source_area_def,
        target_area_def,
        radius_of_influence=roi,
        neighbours=neighbours
    )

    # Determine the number of elements within radius of influence
    # -----------------------------------------------------------

    # The number of elements can be lower than the number of neighbours
    # requested if there are not enough pixels within the radius of influence.

    nelements = len(distance_array[np.isfinite(distance_array)])

    # Get the 2D numpy arrays of y/x projection coordinates

    ys, xs = ds.pyku.get_yx()

    # Edge case
    # ---------

    # When querying the index array for multiple points (e.g., 5 nearest
    # neighbors), the result is typically a 2D array like [[28419, 28420,
    # 28660, 28659, 28179]]. However, when querying a single point, the result
    # is a 1D array like [28419]. This requires handling to account for this
    # edge case.

    if index_array.ndim == 1:
        index_array = index_array[np.newaxis, :]

    # Flatten and select the indices of all elements
    # ----------------------------------------------

    ys = ys.flatten()[index_array[0][0:nelements]]
    xs = xs.flatten()[index_array[0][0:nelements]]

    # Generate coordinates of all elements selected within radius of influence
    # ------------------------------------------------------------------------

    y_name, x_name = meta.get_projection_yx_varnames(ds)
    coords = list(zip(xs, ys))
    coords = pd.DataFrame(coords, columns=["x", "y"])

    # Generate a mask for all elements selected
    # -----------------------------------------

    flag = (
        coords.assign(flag=1)
        .set_index(["x", "y"])
        .flag
        .to_xarray()
        .fillna(0)
    )

    # Reindex based on the y/x projection coordinates of the original data
    # --------------------------------------------------------------------

    # The following options may be usefull method="nearest", tolerance=1e-9
    flag = flag.reindex(x=ds[x_name], y=ds[y_name], fill_value=0)

    # Copy dataset and mask all climate variables
    # -------------------------------------------

    ds_copy = ds.copy()
    for varname in meta.get_geodata_varnames(ds_copy):
        ds_copy[varname] = ds_copy[varname].where(flag)

    if crop:
        ds_copy = ds_copy.dropna(dim=x_name, how='all')
        ds_copy = ds_copy.dropna(dim=y_name, how='all')

    return ds_copy


def _resampling_nearest_from_swath_to_grid(
    in_arr, source_swath, target_grid, roi, chunks, use_dask=True
):
    """
    Block resampling

    Arguments:
       in_arr (:class:`dask.Array`): Array to resample.
       source_swath (:class:`pyresample.geometry.SwathDefinition`): Source
            swath.
       target_grid (:class:`pyresample.geometry.AreaDefinition`): Target grid.
       roi (float): Radius of influence.
       chunks (dict): Chunks.

    Returns:
        :class:`dask.Array`: Resampled dask array
    """

    import numpy as np
    import dask
    from pyresample import kd_tree

    logger.warning('Experimental function')

    # source_swath.lons=np.pad(source_swath.lons, 1, mode='edge')
    # source_swath.lats=np.pad(source_swath.lats, 1, mode='edge')

    # Added noqa because I don't know any better how the line should be
    # formatted.

    valid_input_index, valid_output_index, index_array, distance_array = \
        kd_tree.get_neighbour_info(
            source_swath,
            target_grid,
            roi,
            neighbours=1
        )

    def block_resampling(arr):

        results = []

        for idx in range(arr.shape[0]):

            # Temporary solution. Very tricky. What happens is in some cases,
            # we need the nearest neighbor to be equal to nan. To achieve this
            # the frame of the dataarray is set to np.nan. This is turned off
            # by default.

            # padded_arr=np.pad(
            #    arr[idx], 1, mode='constant', constant_values=np.nan
            # )

            cut_arr = arr[idx]
            # cut_arr[:,[0,-1]] = cut_arr[[0,-1]] = np.nan

            out_arr = kd_tree.get_sample_from_neighbour_info(
                'nn',
                target_grid.shape,
                cut_arr,
                valid_input_index,
                valid_output_index,
                index_array,
                fill_value=np.nan
            )

            # out_arr = kd_tree.resample_nearest(
            #     source_swath,
            #     arr[idx],
            #     target_swath,
            #     radius_of_influence=roi,
            #     epsilon=0,
            #     fill_value=np.nan,
            # )

            results.append(out_arr)

        return np.stack(results, axis=0)

    if use_dask is True:
        out_arr = dask.array.map_blocks(
            block_resampling,
            in_arr,
            chunks=chunks,
            dtype=in_arr.dtype
        )

    else:
        out_arr = block_resampling(in_arr.compute())

    return out_arr


def _resampling_idw_from_swath_to_swath(
    in_arr, source_swath, target_swath, roi, chunks, use_dask=True,
    power_parameter=None
):
    """
    Block resampling

    Arguments:
       in_arr (:class:`dask.Array`): Array to be resampled
       source_swath (:class:`pyresample.geometry.SwathDefinition`):
            Source swath definition
       target_swath (:class:`pyresample.geometry.SwathDefinition`):
            Target swath definition
       roi (float): Radius of influence.
       chunks (dict): Chunks

    Returns:
        :class:`dask.Array`: Resampled dask array
    """

    import numpy as np
    import dask
    from pyresample import kd_tree

    def block_resampling(arr):

        # Define inverse distance weighting power function
        # ------------------------------------------------

        def wf(r):
            return 1 / r ** power_parameter

        # A function is needed for each other_dimensions (i.e. time)
        # ----------------------------------------------------------

        wfs = [wf for idx in range(arr.shape[0])]

        # Reshape from (other_dimensions x y x x) to (y x x x other_dimensions)
        # ---------------------------------------------------------------------

        arr = np.moveaxis(arr, 0, -1)

        # Apply resampling with weight functions
        # --------------------------------------

        out_arr = kd_tree.resample_custom(
            source_swath,
            arr,
            target_swath,
            radius_of_influence=roi,
            weight_funcs=wfs
        )

        # Reshape back to (other_dimensions x y x x)
        # ------------------------------------------

        out_arr = np.moveaxis(out_arr, -1, 0)

        return out_arr

    if use_dask is True:

        out_arr = dask.array.map_blocks(
            block_resampling,
            in_arr,
            chunks=chunks,
            dtype=in_arr.dtype
        )

    else:
        out_arr = block_resampling(in_arr.compute())

    return out_arr


def _resampling_nearest_from_swath_to_swath(
    in_arr, source_swath, target_swath, roi, chunks, use_dask=True
):
    """
    Block resampling

    Arguments:
        in_arr (:class:`dask.Array`): Array to be resampled.
        source_swath (:class:`pyresample.geometry.SwathDefinition`): Source
            swath definition
        target_swath (:class:`pyresample.geometry.SwathDefinition): Target
            swath definition
        roi (float): Radius of influence.
        chunks (dict): Chunks.
        use_dask (bool): Whether dask shall be used. Defaults to True.

    Returns:
        :class:`dask.Array`: Resampled dask array
    """

    import numpy as np
    import dask
    from pyresample import kd_tree

    # source_swath.lons=np.pad(source_swath.lons, 1, mode='edge')
    # source_swath.lats=np.pad(source_swath.lats, 1, mode='edge')

    valid_input_index, valid_output_index, index_array, distance_array = \
        kd_tree.get_neighbour_info(
            source_swath,
            target_swath,
            roi,
            neighbours=1
        )

    def block_resampling(arr):

        arr = np.moveaxis(arr, 0, -1)

        out_arr = kd_tree.get_sample_from_neighbour_info(
            'nn',
            target_swath.shape,
            arr,
            valid_input_index,
            valid_output_index,
            index_array,
            fill_value=np.nan
        )

        out_arr = np.moveaxis(out_arr, -1, 0)

        return out_arr

    if use_dask is True:

        out_arr = dask.array.map_blocks(
            block_resampling,
            in_arr,
            chunks=chunks,
            dtype=in_arr.dtype
        )

    else:
        out_arr = block_resampling(in_arr.compute())

    return out_arr


def _resampling_nearest_from_swath_to_swath_legacy(
    in_arr, source_swath, target_swath, roi, chunks, use_dask=True
):
    """
    Block resampling

    Arguments:

       in_arr (:class:`dask.Array`): The array to be resampled.
       source_swath (:class:`pyresample.geometry.SwathDefinition`):
            Source swath definition
       target_swath (:class:`pyresample.geometry.SwathDefinition`):
            Target swath definition
       roi (float): Radius of influence
       chunks (dict): Chunks

    Returns:
        :class:`dask.Array`: Resampled dask array
    """

    import numpy as np
    import dask
    from pyresample.image import ImageContainerNearest
    from pyresample.utils import generate_nearest_neighbour_linesample_arrays

    row_indices, col_indices = generate_nearest_neighbour_linesample_arrays(
        source_swath,
        target_swath,
        radius_of_influence=roi
    )

    def block_resampling(arr):

        results = []

        for idx in range(arr.shape[0]):

            img_con = ImageContainerNearest(
                arr[idx],
                source_swath,
                fill_value=None,
                radius_of_influence=roi,
            )

            # out_arr = img_con.resample(target_swath).image_data

            out_arr = img_con.get_array_from_linesample(
                row_indices,
                col_indices
            )

            results.append(out_arr)

        return np.stack(results, axis=0)

    if use_dask is True:
        out_arr = dask.array.map_blocks(
            block_resampling,
            in_arr,
            chunks=chunks,
            dtype=in_arr.dtype
        )

    else:
        out_arr = block_resampling(in_arr.compute())

    return out_arr


def _resampling_bilinear_from_swath_to_swath_legacy(
    in_arr, source_swath, target_swath, roi, chunks, use_dask=True
):
    """
    Block resampling

    Arguments:
       in_arr (:class:`dask.Array`): The array to be resampled.
       source_swath (:class:`pyresample.geometry.SwathDefinition`): Source
           swath definition
       target_swath (:class:`pyresample.geometry.SwathDefinition`): Target
           swath definition
       roi (float): The Radius of influence.
       chunks (dict): Chunks.

    Returns:
        :class:`dask.Array`: Resampled dask array
    """

    import warnings
    import numpy as np
    import dask
    from pyresample.image import ImageContainerBilinear
    from pyresample.utils import generate_nearest_neighbour_linesample_arrays

    warnings.warn("Using legacy bilinear resampling from swath to swath")

    row_indices, col_indices = generate_nearest_neighbour_linesample_arrays(
        source_swath,
        target_swath,
        radius_of_influence=roi
    )

    def block_resampling(arr):

        results = []

        for idx in range(arr.shape[0]):

            cut_arr = arr[idx]
            # cut_arr[:,[0,-1]] = cut_arr[[0,-1]] = np.nan

            img_con = ImageContainerBilinear(
                cut_arr,
                source_swath,
                fill_value=None,
                radius_of_influence=roi,
            )

            # out_arr = img_con.resample(target_swath).image_data

            out_arr = img_con.get_array_from_linesample(
                row_indices,
                col_indices
            )

            results.append(out_arr)

        return np.stack(results, axis=0)

    if use_dask is True:
        out_arr = dask.array.map_blocks(
            block_resampling,
            in_arr,
            chunks=chunks,
            dtype=in_arr.dtype
        )

    else:
        out_arr = block_resampling(in_arr.compute())

    return out_arr


def _resampling_bilinear_from_swath_to_grid(
        in_da, source_swath, target_grid, roi
):
    """
    xarray bilinear resampling

    Arguments:
       in_arr (:class:`xarray.DataArray`): DataArray to resample
       source_swath (:class:`pyresample.SwathDefinition`): Source swath.
       target_grid (:class:`pyresample.AreaDefinition`): Target grid.
       roi (float): Radius of influence.

    Returns:
        :class:`dask.Array`: Resampled dask array

    Note:
        The xarray resampling function is slightly different from the other
        since it already implements block resampling in pyresample.
    """

    import pyku.meta as meta
    from pyresample.bilinear import XArrayBilinearResampler

    # The function XArrayBilinearResampler only needs y and x projection
    # coordinates dimension name but these shall be named 'y' and 'x'

    y_name, x_name = meta.get_projection_yx_varnames(in_da)

    if y_name is None:
        logger.warning('Could not find y projection coordinates')

    if x_name is None:
        logger.warning('Could not find x projection coordinates')

    in_da = in_da.rename({y_name: 'y', x_name: 'x'})

    # Perform bilinear resampling
    # ---------------------------

    resampler = XArrayBilinearResampler(
        source_swath,
        target_grid,
        roi,
        reduce_data=False
    )

    result = resampler.resample(
        in_da,
        fill_value=None
    )

    # Return the dask array from the dataArray
    # ----------------------------------------

    return result


def _resampling_bilinear_from_swath_to_grid_legacy(
    in_arr, source_swath, target_grid, roi, chunks, use_dask=True
):
    """
    Block resampling.

    Arguments:
       in_arr (dask.Array): Array to resample.
       source_swath (pyresample.SwathDefinition): Source swath definition.
       target_grid (pyresample.AreadDefinition): Target area definition.
       roi (float): Radius of influence.
       chunks (dict): Chunks.

    Returns:
        dask.Array: Resampled dask array.
    """

    import numpy as np
    import dask
    from pyresample.image import ImageContainerBilinear

    def block_resampling(arr):

        arr = np.nan_to_num(arr)
        arr = np.moveaxis(arr, 0, -1)

        img_con = ImageContainerBilinear(
            arr,
            source_swath,
            fill_value=None,
            radius_of_influence=roi,
        )

        out_arr = img_con.resample(target_grid).image_data

        out_arr = np.moveaxis(out_arr, -1, 0)

        return out_arr

    if use_dask is True:
        out_arr = dask.array.map_blocks(
            block_resampling,
            in_arr,
            chunks=chunks,
            dtype=in_arr.dtype
        )

    else:
        out_arr = block_resampling(in_arr.compute())

    return out_arr


def project(
    ds, area_def=None, roi=1E6, method='nearest_neighbor', use_dask=True,
    area_file=None, keep_mask=False, power_parameter=None
):
    """
    Project dataset to target projection.

    Arguments:

        ds (:class:`xarray.Dataset`): The input dataset.

        area_def (:class:`pyresample.geometry.AreaDefinition`, str): Target
            projection can be given as a pyresample.AreaDefinition, as a
            predefined projection identified by a string (e.g. 'EUR-44'), or as
            an :class:`xarray.Dataset` for swath resampling (Experimental).

        roi (int): Radius of influence for nearest-neighbor calculations
            (default 1000 km); it should be at least five times the data
            resolution to avoid data gaps, though lower values can be used to
            increase calculation speed.

        method (str): Specifies the resampling method to use. Options include:

            - ``nearest_neighbor`` (pyresample)
            - ``bilinear`` (pyresample)
            - ``idw`` (Inverse Distance Weighting, pyresample)
            - ``conservative`` (ESMF)

            The default method is ``nearest_neighbor``. When using the ``idw``
            method, the ``power_parameter`` must be specified. The resampling
            can be performed using either the `pyresample` or the `ESMF`
            library. The specific method and library can be explicitly chosen
            by passing one of the following options:

            - ``pyresample_nearest_neighbor``
            - ``pyresample_bilinear``
            - ``pyresample_idw``
            - ``esmf_bilinear``
            - ``esmf_conservative``
            - ``esmf_conservative_normed``
            - ``esmf_patch``
            - ``esmf_nearest_s2d``
            - ``esmf_nearest_d2s``
            - ``pyresample_bilinear_swath_to_grid``
            - ``pyresample_bilinear_swath_to_grid_legacy``
            - ``pyresample_bilinear_swath_to_swath_legacy``
            - ``pyresample_nearest_neighbor_legacy``

            Depending on the choice, the resampling will be executed with the
            corresponding library and method.

        keep_mask (bool): If the data is projected to a region larger than the
            original, the nearest_neighbor algorithm alwas returns the value of
            the nearest data point and does not return NaNs! Hence in that case
            the radius of influence shall be reduced to set values to NaN
            beyond the roi, or the mask is calculated from the input and
            applied to the output.

        use_dask (bool): Whether to use dask for block resampling. Defaults to
            True.

    Other parameters:

        area_file (str): Path to area file where predefined projections which
            are defined by a string are defined.

        power_parameter (float): Power parameter for Inverse Distance Weighting
            (IDW). Defaults to 2.5. For other interpolation methods, this
            parameter is ignored.

    Returns:
        :class:`xarray.Dataset`: Dataset in target projection.

    Examples:

        .. ipython::
           :okwarning:

           @savefig geo_project_standard.png width=4in
           In [0]: import pyku
              ...:
              ...: # Select first timestep and wrap longitudes of global data
              ...: ds = (
              ...:     pyku.resources.get_test_data('global_data')
              ...:     .isel(time=0)
              ...: )
              ...:
              ...: # Project to HYRAS grid
              ...: projected = ds.pyku.project(area_def='EUR-44')
              ...:
              ...: # Plot
              ...: projected.ana.one_map(var='tas', crs='EUR-44')

        .. ipython::
           :okwarning:

           @savefig geo_project_bilinear.png width=4in
           In [0]: import pyku
              ...:
              ...: # Select first timestep and wrap longitudes of global data
              ...: ds = (
              ...:     pyku.resources.get_test_data('global_data')
              ...:     .isel(time=0)
              ...: )
              ...:
              ...: # Project to HYRAS grid
              ...: projected = ds.pyku.project(
              ...:    area_def='HYR-LAEA-5',
              ...:    method='bilinear'
              ...: )
              ...:
              ...: # Plot
              ...: projected.ana.one_map(var='tas', crs='HYR-LAEA-5')

        .. ipython::
           :okwarning:

           @savefig geo_project_idw.png width=4in
           In [0]: import pyku
              ...:
              ...: # Select first timestep and wrap longitudes of global data
              ...: ds = (
              ...:    pyku.resources.get_test_data('global_data')
              ...:    .isel(time=0)
              ...: )
              ...:
              ...: # Project to HYRAS grid
              ...: projected = ds.pyku.project(
              ...:    area_def='DWD_RADOLAN_900x900',
              ...:    method='idw',
              ...:    roi=500000,
              ...:    power_parameter=1
              ...: )
              ...:
              ...: # Plot
              ...: projected.ana.one_map(var='tas', crs='DWD_RADOLAN_900x900')
    """

    # This is an unusually long function. It is not split because I do not
    # think it would add to clarity. Hence here is a summary:
    #
    # - Load libraries
    # - Ignore warnings
    # - Get output projection as an AreaDefinition object
    # - Get output geographic and projection coordinates
    # - Get input geographic coordinates
    # - Create a swath of lat/lon for the input projection
    # - Create a swath of lat/lon for the output projection
    # - Loop through all data variables and project georeferenced data
    # - Create the projection output dataset
    # - Set the metadata
    #
    # The preferred method is to use swath resampling, however it is possible
    # to also do grid resampling, or a mix of both. Keeping this option adds to
    # complexity but is being kept at the moment.

    import copy
    import pyku.meta as meta
    import pyku.drs as drs
    import pyku.features as features
    import pyku.mask as mask
    import xarray as xr
    import numpy as np
    import pyresample
    from pyresample import geometry
    import pyku.geo as geo
    import dask.array as dk
    from pyproj import CRS, Transformer

    # Shallow copy the input and rename for clarity
    # ---------------------------------------------

    in_ds = ds.copy()
    out_area_def = area_def

    valid_methods = [
        'pyresample_nearest_neighbor',
        'pyresample_bilinear',
        'pyresample_idw',
        'esmf_bilinear',
        'esmf_conservative',
        'esmf_conservative_normed',
        'esmf_patch',
        'esmf_nearest_s2d',
        'esmf_nearest_d2s',
        'pyresample_bilinear_swath_to_grid',
        'pyresample_bilinear_swath_to_grid_legacy',
        'pyresample_bilinear_swath_to_swath_legacy',
        'pyresample_nearest_neighbor_legacy'
    ]

    default_methods = [
        'nearest_neighbor',
        'bilinear',
        'idw',
        'conservative'
    ]

    if method in ['nearest_neighbor']:
        method = 'pyresample_nearest_neighbor'
    if method in ['bilinear']:
        method = 'pyresample_bilinear'
    if method in ['idw']:
        method = 'pyresample_idw'
    if method in ['conservative']:
        method = 'esmf_conservative'

    # Get target area definition
    # --------------------------

    # Validate projection and retrieve area definition. If out_area_def is a
    # string, it is matched against current and deprecated names in the pyku
    # configuration. Returns a pyresample.AreaDefinition object.

    if isinstance(out_area_def, str):

        valid_areas = list_standard_areas()

        if out_area_def in DEPRECATED_PROJECTIONS:
            new_name = DEPRECATED_PROJECTIONS[out_area_def]
            raise ValueError(
                f"Projection '{out_area_def}' is deprecated and has been "
                f"removed. Please use '{new_name}' instead."
            )

        if out_area_def not in valid_areas:
            raise ValueError(
                f"Invalid projection: '{out_area_def}'. "
                "Must be one of the predefined pyku areas: "
                f"{', '.join(valid_areas)}"
            )

        out_area_def = load_area_def(out_area_def, area_file)

    elif isinstance(out_area_def, pyresample.AreaDefinition):
        pass
    else:
        raise AssertionError('Could not determine area definition')

    # Sanity checks
    # -------------

    if method not in valid_methods:
        raise Exception(
            f"Method {method} not implemented. Use one of the default "
            f"methods {default_methods}, or one of the implemented methods "
            f"{valid_methods}"
        )

    if not are_yx_projection_coordinates_strictly_monotonic(ds):
        logger.warning(
            "Non-monotonic projection coordinates detected. "
            "The calculated area extent may be incorrect."
        )

    if (
        meta.has_geographic_coordinates(in_ds) and
        not are_longitudes_wrapped(in_ds)
    ):
        logger.info(
            "Longitudes are not within the range [-180,+180). Consider "
            "wrapping longitudes using ds.pyku.wrap_longitudes()."
        )

    if isinstance(out_area_def, xr.Dataset):
        raise DeprecationWarning(
            "Passing a xarray Dataset is deprecated. Use "
            "ds.pyku.get_area_def() to extract the area definition instead"
        )

    if isinstance(out_area_def, xr.DataArray):
        raise DeprecationWarning(
            "Passing a xarray DataArray is deprecated. Use "
            "ds.pyku.get_area_def() to extract the area definition instead"
        )

    if method in ['idw'] and power_parameter is None:
        raise AssertionError(
            "`power_parameter` must be passed for IDW resampling"
        )

    if (
        method in ['bilinear'] and
        out_area_def.proj_dict.get('proj') in ['ob_tran']
    ):
        raise Exception(
            "Rotated lat/lon is not supported for the default "
            "bilinear method from the pyresample library. As an "
            "alternative, use pyresample with method='nearest_neighbor"
            " or ESMF with method='esmf_bilinear'. Installing the "
            "optional ESMF regridder requires manual steps"
        )

    if meta.has_ordered_dimensions_and_coordinates(in_ds) is False:
        logger.info(
            "Pyku recommends ordering dimensions and coordinates as follows: "
            "time, other dimensions, y projection coordinate, and x "
            "projection coordinate. You can reorder them using "
            "ds.pyku.reorder_dimensions_and_coordinates()."
        )

    # Determine target geographic and projection coordinates
    # ------------------------------------------------------

    # Get the target projection y/x coordinates and calculate the corresponding
    # target geographic lat/lon coordinates on the WGS84 sphere (AKA
    # EPSG:4326).

    epsg4326 = CRS("EPSG:4326")

    transformer = Transformer.from_crs(
        out_area_def.proj_str,
        epsg4326,
        always_xy=True
    )

    out_x, out_y = out_area_def.get_proj_coords()
    out_lons, out_lats = transformer.transform(out_x, out_y)

    # Get 1D arrays of projection coordinates
    # ---------------------------------------

    # With the execption of unstructured grids like the ICON model native grid,
    # projection coordinates can always be simplified to 1D arrays of
    # coordinates.

    out_y = out_y[:, 0]
    out_x = out_x[0]

    # Get number of target coordinates
    # --------------------------------

    out_ny = len(out_y)
    out_nx = len(out_x)

    # Get source geographic lat/lon coordinates
    # -----------------------------------------

    in_lons, in_lats = geo.get_lonlats(in_ds)

    # Get source y/x projection and lat/lon geographic coordinate names
    # -----------------------------------------------------------------

    y_name, x_name = meta.get_projection_yx_varnames(in_ds)
    lat_name, lon_name = meta.get_geographic_latlon_varnames(ds)

    # Projecting, we can chunk over time or height, but not over lat/lon, x/y
    # -----------------------------------------------------------------------

    # For geographic reprojection, the data cannot be chunked along the source
    # y/x projection coordinates. Therefore, we need to check if projection
    # coordinates are present and unchunk along the y/x projection coordinates.
    # This check also handles the edge case of the ICON unstructured grid,
    # which lacks projection coordinates. Additionally, some datasets may have
    # missing projection coordinates, in which case swath resampling relies
    # solely on geographic coordinates.

    if meta.has_projection_coordinates(in_ds):
        in_ds = in_ds.chunk({y_name: -1, x_name: -1})

    # Define source and target swath
    # ------------------------------

    swath_in = geometry.SwathDefinition(lons=in_lons, lats=in_lats)
    swath_out = geometry.SwathDefinition(lons=out_lons, lats=out_lats)

    # DataArrays of each variables in Dataset are gathered in a list
    # --------------------------------------------------------------

    out_da_list = []

    # Iterate over all variables in Dataset
    # -------------------------------------

    for varname, in_da in in_ds.data_vars.items():

        # Skip/remove spatial variables
        # -----------------------------

        # Spatial variables such as geographic lat/lon coordinate bounds are
        # not valid after geographic reprojection.

        if varname in meta.get_spatial_varnames(in_ds):
            continue

        # Keep variables which are not georeferenced
        # ------------------------------------------

        if varname not in meta.get_geodata_varnames(in_ds):
            out_da_list.append(in_da)
            continue

        # Determine the shape of the output numpy array
        # ---------------------------------------------

        # To deal with all dimensions, the array is reshaped. The spatial
        # dimensions are not the same after resampling process and are deleted,
        # keeping all other dimensions as they were.
        #
        # EXAMPLES
        #
        # For a standard grid:
        # - Before: time x height x y_coord x x_coord
        # - After: time*height x y_coord x x_coord
        #
        # For a restructured grid
        # - Before: time x height x ncells
        # - After: time*height x y_coord x x_coord

        in_shape = in_da.shape
        out_shape = list(in_da.shape)

        if meta.has_unstructured_geographic_coordinates(in_ds):
            del out_shape[-1]

        else:
            del out_shape[-1]
            del out_shape[-1]

        out_shape.append(out_ny)
        out_shape.append(out_nx)
        out_shape = tuple(out_shape)

        # Get the input array, force the type to dask
        # -------------------------------------------

        if isinstance(in_da.data, np.ndarray):
            in_arr = dk.from_array(in_da.data)
        else:
            in_arr = in_da.data

        # Reshape numpy arrays to loop over all dimensions at once
        # --------------------------------------------------------

        # Standard grid: time x height x y_coord x x_coord
        # Restructured grid: time x height x ncells

        if meta.has_unstructured_geographic_coordinates(in_ds):
            in_arr = in_arr.reshape(-1, in_shape[-1])
        else:
            in_arr = in_arr.reshape(-1, in_shape[-2], in_shape[-1])

        # Apply block resampling
        # ----------------------

        if method in [
            'pyresample_bilinear',
            'pyresample_bilinear_swath_to_grid'
        ]:
            out_da = _resampling_bilinear_from_swath_to_grid(
                in_da,
                source_swath=swath_in,
                target_grid=out_area_def,
                roi=roi,
            )

            out_arr = out_da.data

        elif method in ['pyresample_nearest_neighbor']:

            out_arr = _resampling_nearest_from_swath_to_swath(
                in_arr,
                source_swath=swath_in,
                target_swath=swath_out,
                roi=roi,
                chunks=(in_arr.chunks[0], (out_ny,), (out_nx,)),
                use_dask=use_dask,
            )

        elif method in ['pyresample_idw']:

            out_arr = _resampling_idw_from_swath_to_swath(
                in_arr,
                source_swath=swath_in,
                target_swath=swath_out,
                roi=roi,
                chunks=(in_arr.chunks[0], (out_ny,), (out_nx,)),
                use_dask=use_dask,
                power_parameter=power_parameter
            )

        elif method in [
            'esmf_bilinear',
            'esmf_conservative',
            'esmf_conservative_normed',
            'esmf_patch',
            'esmf_nearest_s2d',
            'esmf_nearest_d2s',
        ]:

            if method in ['esmf_bilinear']:
                method = 'bilinear'
            if method in ['esmf_conservative']:
                method = 'conservative'
            if method in ['esmf_conservative_normed']:
                method = 'conservative_normed'
            if method in ['esmf_patch']:
                method = 'patch'
            if method in ['esmf_nearest_s2d']:
                method = 'nearest_s2d'
            if method in ['esmf_nearest_d2s']:
                method = 'nearest_d2s'

            # Raise exception if xesmf is not installed
            # -----------------------------------------

            try:
                import xesmf as xe  # type: ignore
            except ImportError:
                raise ImportError(
                    "xesmf and esmpy for conservative resampling are not "
                    "installed by default. ESMF binaries must first be "
                    "compiled and installed first! For installation "
                    "instructions, see the Pyku documentation. With the DWD "
                    "module system, you can load it using:\n"
                    "    module load esmf/8.8.0\n\n"
                    "If you are using ESMF binaries in version 8.8.0 as "
                    "above, you can install esmpy with:\n"
                    "    pip install git+https://github.com/esmf-org/esmf.git@v8.8.0#subdirectory=src/addon/esmpy\n\n"  # noqa
                    "Then, install xesmf:\n"
                    "    pip install xesmf"
                )

            # Generate Dataset with projection lat/lon information
            # ----------------------------------------------------

            ds_target = xr.Dataset(
                coords={
                    "y": (["y"], out_y, {}),
                    "x": (["x"], out_x, {}),
                    "lat": (["y", "x"], out_lats, {}),
                    "lon": (["y", "x"], out_lons, {}),
                }
            )

            # Add lat/lon bounds
            # ------------------

            # Conservatve regridding needs boundaries

            ds_target = set_latlon_bounds(ds_target)

            # The `cf.add_bounds` function is only available for Datasets.
            # Hence the temporary conversion with to_dataset().

            data_in_regridder_format = \
                set_latlon_bounds(in_da.to_dataset())

            # Create conservative regridder
            # -----------------------------

            regridder = xe.Regridder(
                data_in_regridder_format,
                ds_target,
                method=method,
            )

            # Perform geographic resampling
            # -----------------------------

            out_da = regridder(
                data_in_regridder_format,
                keep_attrs=True
            )[varname]

            out_arr = out_da.data

        elif method in ['pyresample_bilinear_swath_to_grid']:

            out_da = _resampling_bilinear_from_swath_to_grid(
                in_da,
                source_swath=swath_in,
                target_grid=out_area_def,
                roi=roi,
            )

            if use_dask is not True:
                logger.warning('use_dask=False not implemented and ignored')

            # Get dask array from DataArray
            # -----------------------------

            out_arr = out_da.data

        elif method in ['pyresample_bilinear_swath_to_grid_legacy']:

            out_arr = _resampling_bilinear_from_swath_to_grid_legacy(
                in_arr,
                source_swath=swath_in,
                target_grid=out_area_def,
                roi=roi,
                chunks=(in_arr.chunks[0], (out_ny,), (out_nx,)),
                use_dask=use_dask,
            )

        elif method in ['pyresample_bilinear_swath_to_swath_legacy']:

            out_arr = _resampling_bilinear_from_swath_to_swath_legacy(
                in_arr,
                source_swath=swath_in,
                target_swath=swath_out,
                roi=roi,
                chunks=(in_arr.chunks[0], (out_ny,), (out_nx,)),
                use_dask=use_dask,
            )

        elif method in ['pyresample_nearest_neighbor_legacy']:

            out_arr = _resampling_nearest_from_swath_to_swath_legacy(
                in_arr,
                source_swath=swath_in,
                target_swath=swath_out,
                roi=roi,
                chunks=(in_arr.chunks[0], (out_ny,), (out_nx,)),
                use_dask=use_dask,
            )

        else:
            raise Exception(
                f"Method {method} not implemented. 'nearest_neighbor'",
                "'bilinear' and 'idw' are available."
            )

        # Reshape resampling output to the output shape
        # ---------------------------------------------

        out_arr = out_arr.reshape(out_shape)

        # Copy output coordinates
        # -----------------------

        out_coords = dict(in_da.coords)

        # Remove georeferencing which is invalid after gegoraphic reprojection
        # --------------------------------------------------------------------

        for element in meta.get_geographic_latlon_varnames(in_ds):
            out_coords.pop(element, None)

        for element in meta.get_projection_yx_varnames(in_ds):
            out_coords.pop(element, None)

        for element in meta.get_spatial_vertices_varnames(in_ds):
            out_coords.pop(element, None)

        out_coords.pop('nlat', None)  # Remove nlat if it exists
        out_coords.pop('nlon', None)  # Remove nlon if it exists

        # Add geographic lat/lon and projection coordinates to target Dataset
        # -------------------------------------------------------------------

        out_coords['y'] = (["y"], out_y)
        out_coords['x'] = (["x"], out_x)
        out_coords['lat'] = (["y", "x"], out_lats)
        out_coords['lon'] = (["y", "x"], out_lons)

        # Copy and modify variable attributes
        # -----------------------------------

        out_attrs = copy.deepcopy(in_da.attrs)

        # Remove any reference to former coordinate system
        # ------------------------------------------------

        out_attrs.pop('grid', None)
        out_attrs.pop('grid_mapping', None)
        out_attrs.pop('CoordinateSystems', None)
        out_attrs.pop('esri_pe_string', None)

        # Add CF-conform grid_mapping attribute
        # -------------------------------------

        # CF-Conform georeferencing is only included if the projection Area Id
        # pre-defined in pyku configuration files

        areas_cf_definitions = get_areas_cf_definitions()
        out_area_id = out_area_def.area_id

        if out_area_id in list(areas_cf_definitions.keys()):
            out_attrs['grid_mapping'] = \
                areas_cf_definitions.get(out_area_id).get('crs_name')

        # Set dimensions
        # --------------

        out_dims = dict(in_da.sizes)

        # Remove georeferencing which is not valid after projecting
        # ---------------------------------------------------------

        if meta.has_unstructured_geographic_coordinates(in_ds):
            # There seems to be multiple conventions with respect to the naming
            # of the cell/ncells dimension
            out_dims.pop('ncells', None)
            out_dims.pop('cell', None)

        for element in meta.get_geographic_latlon_varnames(in_ds):
            out_dims.pop(element, None)

        for element in meta.get_projection_yx_varnames(in_ds):
            out_dims.pop(element, None)

        for element in meta.get_spatial_vertices_varnames(in_ds):
            out_dims.pop(element, None)

        out_dims.pop('nlat', None)
        out_dims.pop('nlon', None)

        out_dims['y'] = out_ny
        out_dims['x'] = out_nx

        # Create DataArray
        # ----------------

        out_da = xr.DataArray(
            name=varname,
            data=out_arr,
            dims=out_dims,
            coords=out_coords,
            attrs=out_attrs
        )

        # Set CMOR-Conform default attributes
        # -----------------------------------

        # For 'irregular' projection attributes (e.g. rlats and rlons), the
        # names for the y/x projection coordinates are set later in the code by
        # reading the CF-conform area definition.

        out_da.coords['lat'].attrs = \
            drs.drs_data.get('coordinates').get('lat')['attrs']
        out_da.coords['lon'].attrs = \
            drs.drs_data.get('coordinates').get('lon')['attrs']
        out_da.coords['y'].attrs = \
            drs.drs_data.get('coordinates').get('y')['attrs']
        out_da.coords['x'].attrs = \
            drs.drs_data.get('coordinates').get('x')['attrs']

        # Append DataArray to the list of DataArrays
        # ------------------------------------------

        out_da_list.append(out_da)

    # Merge DataArrays into Dataset
    # -----------------------------

    out_ds = xr.merge(out_da_list, compat='no_conflicts')

    # Add CF-conform georeferencing
    # -----------------------------

    # CF-Conform georeferencing is only included if the projection Area Id
    # pre-defined in pyku configuration files

    areas_cf_definitions = get_areas_cf_definitions()
    out_area_id = out_area_def.area_id

    if out_area_id in list(areas_cf_definitions.keys()):

        # Set crs coodinate
        # -----------------

        cf_crs = xr.DataArray(
            np.array(1, dtype='int32'),
            name=areas_cf_definitions.get(out_area_id).get('crs_name'),
            attrs=areas_cf_definitions.get(out_area_id).get('crs_data')
        )

        # Get name of projection coordinates
        # ----------------------------------

        x_name = areas_cf_definitions.get(out_area_id).get('x_coordinate', 'x')
        y_name = areas_cf_definitions.get(out_area_id).get('y_coordinate', 'y')

        # Rename x and y coordinates if necessary
        # ---------------------------------------

        if x_name not in ['x'] and y_name not in ['y']:
            out_ds = out_ds.rename({'x': x_name, 'y': y_name})

        # Set CMOR-conform coordinate attributes
        # --------------------------------------

        out_ds = drs._to_cmor_attrs_coords(out_ds)

        # Merge CRS to dataset
        # --------------------

        out_ds = xr.merge([out_ds, cf_crs])

        # Copy global metadata
        # --------------------

        out_ds.attrs = in_ds.attrs

        # Add/overwrite cordex domain the the global metadata
        # ---------------------------------------------------

        out_ds = out_ds.assign_attrs({
            'CORDEX_domain': areas_cf_definitions.get(out_area_id).get(
                'CORDEX_domain', 'undefined'
            )
        })

    else:
        logger.warning("No CF-conform georeferencing added")

        # Set crs coodinate
        # -----------------

        default_crs = xr.DataArray(
            np.array(1, dtype='int32'),
            name='crs',
            attrs={
                'proj_str': out_area_def.proj_str,
                'proj4_string': out_area_def.proj4_string,
                'proj4': out_area_def.proj4_string,
                'proj4_params': out_area_def.proj4_string,
                'crs_wkt': out_area_def.crs_wkt,
                'spatial_ref': out_area_def.crs_wkt,
            }
        )

        out_ds = xr.merge([out_ds, default_crs])

    # For all variables, set the grid_mapping attribute
    # -------------------------------------------------

    for var in meta.get_geodata_varnames(out_ds):
        out_ds[var].attrs['grid_mapping'] = meta.get_crs_varname(out_ds)

    # Apply the original mask
    # -----------------------

    # In some situation, the nearest neighbour is calculated outside the
    # original mask. This is a feature and not a bug, but mostly not the wanted
    # feature.

    if keep_mask is True:
        polygon_mask = features.polygonize(in_ds)
        out_ds = mask.apply_mask(out_ds, polygon_mask)

    return out_ds
