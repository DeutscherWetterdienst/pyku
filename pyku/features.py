#!/usr/bin/env python3

"""
Functions for dealing with features (polygons, points).
"""

from . import logger


def rasterize_points(features, area_def, reference_datetime=None):
    """
    Rasterize points.

    .. warning:

       This function was programmed having in mind  rasterizing lightning point
       data. This function is not maintained

    Arguments:

        features (:class:`geopandas.GeoDataFrame`): Features.

        area_def (:class:`pyresample.geometry.AreaDefinition`): Area
            definition.

    Returns:
        :class:`xarray.DataArray`: Dataset with features burnt in.
    """

    import pyku.geo as geo
    import numpy as np
    import xarray as xr
    import pyku.drs as drs
    import rasterio
    import rasterio.features

    logger.warn("This function is not maintained.")

    # Get coordinates from area definition
    # ------------------------------------

    lons, lats = area_def.get_lonlats(dtype=np.float32)
    x, y = area_def.get_proj_coords(dtype=np.float32)

    # Get the number of coordinates
    # -----------------------------

    ny = len(y[:, 0])
    nx = len(x[0])

    # Convert features to the output CRS
    # ----------------------------------

    features = features.to_crs(area_def.proj_str)

    if features.empty:
        message = "Empty GeoDataFrame, all values are masked."
        logger.info(message)

    # Get area extent
    # ---------------

    left, bottom, right, up = area_def.area_extent

    # Get transfrom
    # -------------

    transform = rasterio.transform.from_bounds(left, bottom, right, up, nx, ny)

    # Rasterize
    # ---------

    raster = rasterio.features.rasterize(
        features.geometry,
        out_shape=(ny, nx),
        fill=0,
        transform=transform,
        merge_alg=rasterio.enums.MergeAlg('ADD'),
        dtype=np.int32
    )

    # Construct data array
    # ====================

    da = xr.DataArray(
        name='data',
        data=[raster],
        dims=["time", "y", "x"],
        coords=dict(
            time=[reference_datetime],
            y=(["y"], y[:, 0]),
            x=(["x"], x[0]),
            lat=(["y", "x"], lats),
            lon=(["y", "x"], lons),
        ),
        attrs=dict(
            description="Data",
        ),
    )

    # Convert DataArray to DataSet
    # ----------------------------

    ds = da.to_dataset()

    # Set attributes
    # --------------

    ds = drs._to_cmor_attrs_coords(ds)

    # Set georeferencing metadata
    # ---------------------------

    ds = geo._set_georeferencing_attrs(ds, area_def=area_def)

    return ds


def rasterize_polygons(features, area_def, all_touched=False):
    """
    Rasterize polygons

    Arguments:

        features (:class:`geopandas.DataFrame`): The input polygons.

        area_def (:class:`pyresample.AreaDefinition` or str): The target
            projection. This can be provided either as a
            :class:`pyresample.geometry.AreaDefinition` object or as a string
            representing a named projection (e.g., "HYR-LAEA-5"). Named
            projections are predefined in the pyku library and fully defined in
            the default projection configuration file.

        all_touched (boolean): Optional. If True, all pixels touched by
            geometries will be burned in. If false, only pixels whose center is
            within the polygon or that are selected by Bresenham line algorithm
            will be burned in.

    Returns:
        :class:`xarray.Dataset`: Raster with burnt in features.

    Example:

        .. ipython::
           :okwarning:

           @savefig features_rasterize_polygons.png width=4in
           In [0]: %%time
              ...: import pyku
              ...: gdf = pyku.resources.get_geodataframe(
              ...:     'natural_areas_of_germany'
              ...: )
              ...: ds = pyku.features.rasterize_polygons(gdf, 'HYR-LAEA-5')
              ...: pyku.analyse.one_map(ds, var='regions', crs='HYR-LAEA-5')
    """

    import warnings
    import numpy as np
    import numpy.ma as ma
    import xarray as xr
    import rasterio
    import rasterio.features
    from pyproj import CRS
    from pyproj import Transformer
    import pyku.geo as geo
    import pyku.drs as drs

    # Filter unused UserWarning
    # -------------------------

    warnings.filterwarnings(
        "ignore",
        "You will likely lose important projection information",
        UserWarning,
    )

    # Get area definition if a string was provided
    # --------------------------------------------

    if isinstance(area_def, str):
        area_def = geo.load_area_def(area_def)

    # Get 2D arrays of latitudes and longitudes
    # -----------------------------------------

    epsg4326 = CRS("EPSG:4326")

    transformer = Transformer.from_crs(
        area_def.proj_str,
        epsg4326,
        always_xy=True
    )

    # Get projection and geographic coordinates from area definition
    # --------------------------------------------------------------

    x, y = area_def.get_proj_coords()
    lons, lats = transformer.transform(x, y)

    # Convert projection coordinates to 1D arrays
    # -------------------------------------------

    # pyresample get_proj_coords return 2D arrays. However projection
    # coordinates can always be reduced to 1D arrays.

    ys = y[:, 0]
    xs = x[0, :]

    # Get the number of coordinates
    # -----------------------------

    ny = len(y[:, 0])
    nx = len(x[0])

    # Convert features to the output CRS
    # ----------------------------------

    features = features.to_crs(area_def.proj_str)

    # Select features within area definition
    # --------------------------------------

    left, bottom, right, up = area_def.area_extent

    features = features.cx[left:right, bottom:up]

    if features.empty:
        logger.info("Empty GeoDataFrame, returning None")
        return None

    # Get transfrom
    # -------------

    transform = rasterio.transform.from_bounds(left, bottom, right, up, nx, ny)

    # polygons and indices are gathered in a list of tuples
    # -----------------------------------------------------

    # The index is increased by one in order to obtain polygons from 1 up to N
    # included [1, 2, ..., N]. When rasterizing, the fill values is zero where
    # there are no Polygons. This is then reset when building the mask to 0 up
    # to N excluded [0, 1, 2, ..., N-1]

    list_of_polygons_and_indices = []

    for index, feature in features.reset_index().iterrows():
        list_of_polygons_and_indices.append((feature.geometry, index+1))

    # Rasterize
    # ---------

    # See function documentation at:
    # https://rasterio.readthedocs.io/en/latest/api/rasterio.features.html#rasterio.features.rasterize

    raster = rasterio.features.rasterize(
        list_of_polygons_and_indices,
        out_shape=(ny, nx),
        fill=0,
        transform=transform,
        all_touched=all_touched,
        dtype=np.int32
    )

    # Mask values with no polygons
    # ----------------------------

    raster = raster-1
    mask = np.where(np.equal(raster, -1), True, False)
    raster = ma.masked_array(raster, mask=mask)

    # Construct data array
    # --------------------

    da = xr.DataArray(
        name='regions',
        data=raster,
        dims=["y", "x"],
        coords=dict(
            y=(["y"], ys),
            x=(["x"], xs),
            lat=(["y", "x"], lats),
            lon=(["y", "x"], lons),
        ),
        attrs=dict(
            description="Data",
        ),
    )

    # Convert to Dataset
    # ------------------

    ds = da.to_dataset()

    # Set coordinate attributes
    # -------------------------

    ds = drs._to_cmor_attrs_coords(ds)

    # Construct a Dataarray containing the mapping between polygon index
    # ------------------------------------------------------------------

    da_regions = xr.DataArray(
        name='region_index',
        data=features.reset_index().index.values,
        dims=["region_name"],
        coords=dict(
            region_name=(["region_name"], features.index.values),
        ),
        attrs=dict(
            description="Regions mapping",
        ),
    )

    ds = xr.merge([ds, da_regions])
    ds = ds.assign_coords(region_index=ds.region_index)
    ds = ds.swap_dims({'region_name': 'region_index'})

    # Set georeferencing metadata
    # ---------------------------

    ds = geo._set_georeferencing_attrs(ds, area_def=area_def)

    return ds


def polygonize(
    dat, area_def=None, mask_value=None, dtype='Polygons', **kwargs
):
    """
    Polygonize raster data.

    Arguments:

        dat (:class:`xarray.Dataset`):
            The input data. If the file contains more than one timestep or
            variable, only the first timestep of the first georeferenced data
            variable is polygonized.

        area_def (:class:`pyresample.geometry.AreaDefinition` or str):
            Deprecated. The projection informations are now read directly from
            the dataset georeferencing.

        mask_value (number, optional):
            By default, all data values that are not `None` are polygonized. If
            the input data uses a specific value (e.g., `999`) to represent
            missing data, you can specify `mask_value` to exclude these values
            from the polygonization process.

        dtype (str, optional):
            Determines the geometry type of the output polygons.

            - ``"Polygons"``: Returns individual polygons for each contiguous
              region.

            - ``"MultiPolygon"``: Combines multiple polygons into a single
              MultiPolygon object, which is useful for creating masks with
              holes.

            For example, to build a mask with holes or a single geometrical
            representation of disjoint regions, use ``"MultiPolygon"``.
            Otherwise, selecting ``"Polygons"`` will generate separate
            polygon objects for each region.

    Returns:
        :class:`geopandas.GeoDataFrame`:
            A GeoDataFrame containing the geo-referenced polygon(s).

    Example:

        .. ipython::
           :okwarning:

           @savefig features_polygonize.png width=4in
           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: gdf = ds.pyku.polygonize()
              ...: pyku.analyse.regions(gdf, area_def='HYR-LAEA-5')
    """

    import warnings
    import rasterio
    import pyproj
    import dask
    from rasterio.features import shapes
    from shapely.geometry import shape, MultiPolygon
    import shapely.ops
    import geopandas as gpd
    import pandas as pd
    import numpy as np
    import xarray as xr
    from pyproj import CRS
    import pyku.meta as meta
    import pyku.geo as geo

    # The function is half recursive. Polygonizing DataArrays consists of
    # looping over numpy arrays.

    # If area definition is given as a string, load projection
    # --------------------------------------------------------

    if area_def is not None:
        warnings.warn(
            "The parameter 'area_def' is deprecated. Do not set this "
            "parameter and the area definition will be read from the data.",
            DeprecationWarning,
            stacklevel=2,
        )

    if isinstance(area_def, str):
        area_def = geo.get_area_def(area_def)

    if dtype not in ['Polygons', 'MultiPolygon']:
        raise TypeError(
            f"dtype shall be 'Polygons' or 'MultiPolygon', not {dtype}"
        )

    # Polygonize Dataset
    # ------------------

    if isinstance(dat, xr.Dataset):

        # # Get a copy of the dataset
        # # -------------------------

        # dat = dat.copy()

        # Get area definition from dataset
        # --------------------------------

        if area_def is None:
            area_def = geo.get_area_def(dat)

        # Choose first data variable
        # --------------------------

        geodata_varnames = meta.get_geodata_varnames(dat)

        if len(geodata_varnames) < 1:

            raise AssertionError(
                "No georeferenced data found in the dataset. It is therefore "
                "not possible to polygonize. Variables in dataset are: "
                f"{dat.data_vars}"
            )

        geodata_varname = geodata_varnames[0]

        if 'time' in dat.sizes.keys():

            logger.info(
                f"Building the mask from the first time step of variable: "
                f"{geodata_varname}."
            )

            da = dat[geodata_varname].isel(time=0)

        else:
            logger.info(f"Building the mask from {geodata_varname}.")
            da = dat[geodata_varname]

        # Polygonize the DataArray
        # ------------------------

        result = polygonize(
            da,
            area_def=area_def,
            mask_value=mask_value,
            dtype=dtype,
            **kwargs
        )

        return result

    # Polygonize DataArray
    # --------------------

    elif isinstance(dat, np.ndarray) or isinstance(dat, dask.array.core.Array):

        """
        Return a list of polygons for np.ndarray
        """

        # shape returns a generator (ogr_geometry, value) polygonalizing the
        # mask, only polygons with values 0 or 1 are possible Further using the
        # option mask= only polygons with value 0 are possible

        transform = kwargs.get('transform')
        project = kwargs.get('project')

        # Get mask from mask_value
        # ------------------------

        if mask_value is not None:
            mask = np.where(np.equal(dat, mask_value), True, False)
        else:
            mask = np.where(np.isnan(dat), True, False)

        generator = shapes(
            mask.astype(rasterio.uint8),
            mask=(1-mask.astype(int)).astype(rasterio.uint8),
            transform=transform
        )

        polygons = []

        for ogr_geometry, value in generator:

            # buffer(0) fixes issue 'OGC ring self intersection'
            # The issue is that rasterio, which in turn calls gdal, delivers
            # OGR polygons. Here, we force compliance with OGC.

            ogr_shapely = shape(ogr_geometry)
            ogc_shapely = ogr_shapely.buffer(0)

            # Project to epsg:4326
            # --------------------

            ogc_shapely = shapely.ops.transform(project, ogc_shapely)

            # longitudes and latitudes come in the wrong order, flip it
            # ---------------------------------------------------------

            ogc_shapely = shapely.ops.transform(
                lambda x, y: (y, x), ogc_shapely)

            # Append polygon to the list of polygons
            # --------------------------------------

            polygons.append(ogc_shapely)

        return polygons

    elif isinstance(dat, xr.DataArray):

        # Get the projection and convert to an area definition
        # ----------------------------------------------------

        # Note that only the projection string from the area definition is
        # used; the boundaries are ignored. If no area definition is provided,
        # we assume EPSG:4326.

        if area_def is not None:
            input_crs = CRS.from_string(area_def.proj_str)

        else:
            input_crs = pyproj.CRS('EPSG:4326')

        output_crs = pyproj.CRS('EPSG:4326')

        # Get area extent
        # ---------------

        bottom_left_x, bottom_left_y, upper_right_x, upper_right_y = \
            area_def.area_extent

        # Get transform
        # -------------

        west, south, east, north = \
            bottom_left_x, bottom_left_y, upper_right_x, upper_right_y

        width, height = geo.get_nx(dat), geo.get_ny(dat)

        transform = rasterio.transform.from_bounds(
            west=west,
            south=south,
            east=east,
            north=north,
            width=width,
            height=height,
        )

        project = pyproj.Transformer.from_crs(input_crs, output_crs).transform

        # Get dimensions that are not spatial
        # -----------------------------------

        dims = set(dat.dims) - set(meta.get_spatial_varnames(dat))

        if len(dims) > 1:

            raise AssertionError(
                "The DataArray passed shall be 2D (x, y/lat,lon). No time or "
                "height dependence is accepted. You can accomplish that by "
                "selecting a single timestep with e.g. ``dat.isel(time=0)``."
            )

        # Case where there are no dimesion only var (y, x)
        # ------------------------------------------------

        if len(dims) == 0:

            polygons = polygonize(
                dat.data,
                transform=transform,
                project=project,
                mask_value=mask_value
            )

            if dtype in ['MultiPolygon']:
                polygons = [MultiPolygon(polygons)]

            gdf = gpd.GeoDataFrame(
                crs='epsg:4326',
                geometry=polygons,
            )

            # Set polygons attributes
            # -----------------------

            gdf['name'] = dat.name
            gdfs = pd.concat([gdf])

    else:
        raise TypeError(f"{type(dat)} not supported")

    return gdfs


def regionalize(ds, gdf=None, area_def=None, **kwargs):

    """
    Group data into the regions given in the GeoDataFrame

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
        gdf (:class:`geopandas.GeoDataFrame`): The regions.
        area_def (:class:`pyresample.geometry.AreaDefinition`, str):
            Optional. The area defintion of the Dataset can be explicitely
            passed if not, it is read from the dataset.

    Returns:
        :class:`xarray.Dataset`: Regionalized dataset with regions along the
        new 'region' dimension. for example, if the dataset had the dimension
        (time x lat x lon), the new dataset has the dimensions (region x time x
        lat x lon)

    Example:

        .. ipython::
           :okwarning:

           @savefig features_regionalize.png width=4in
           In [0]: %%time
              ...: import pyku
              ...:
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: gdf = pyku.resources.get_geodataframe(
              ...:     'natural_areas_of_germany'
              ...: )
              ...:
              ...: regionalized = ds.pyku.regionalize(gdf)
              ...:
              ...: pyku.analyse.n_maps(
              ...:     regionalized.isel(time=0).isel(region=0),
              ...:     regionalized.isel(time=0).isel(region=1),
              ...:     regionalized.isel(time=0).isel(region=2),
              ...:     regionalized.isel(time=0).isel(region=3),
              ...:     nrows=2,
              ...:     ncols=2,
              ...:     crs='HYR-LAEA-5',
              ...:     var='tas'
              ...: )
    """

    import itertools
    import pyku.geo as geo
    import pyku.meta as meta
    import xarray as xr

    # Sanity checks
    # -------------

    if gdf is None:
        message = "Parameter 'gdf' is mandatory."
        raise ValueError(message)

    if area_def is None:
        try:
            area_def = geo.get_area_def(ds)
        except Exception:
            message = "Could not guess area definition from dataset."
            raise Exception(message)

    # Rasterize polygons
    # ------------------

    rasterized_polygons = rasterize_polygons(
        gdf,
        area_def=area_def,
    )

    indices = rasterized_polygons['region_index'].values
    names = rasterized_polygons['region_name'].values

    # Get geodata variables names and non-geodata variable names
    # ----------------------------------------------------------

    geodata_varnames = meta.get_geodata_varnames(ds)
    other_varnames = [
        el for el in ds.data_vars
        if el not in geodata_varnames
    ]

    # Concatenate regions in a single dataset
    # ---------------------------------------

    ds_grouped_regions = xr.concat(
        [
            ds[var].where(rasterized_polygons['regions'].data == idx)
            for var, idx in itertools.product(geodata_varnames, indices)
        ],
        dim=xr.DataArray(
            data=names,
            dims='region'
        ),
    )

    # Put back other data (the one which are not georeferenced) and return
    # --------------------------------------------------------------------

    out_ds = xr.merge([ds_grouped_regions, ds[other_varnames]])

    return out_ds
