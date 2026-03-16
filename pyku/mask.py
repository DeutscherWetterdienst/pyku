"""
Module managing masking
"""


def apply_polygon_mask(dat, mask, from_nans=False, tolerance=0.001):

    """
    Mask data

    Arguments:

        dat (:class:`xarray.Dataset`): The input data.

        mask (:class:`geopandas.GeoDataFrame`): The mask representing either
            a polygon or a DataArray with the same projection coordinates.

        from_nans (bool): Indicates whether the mask is derived from NaN
            values.

        tolerance (float): A small value used as the default tolerance for
            aligning georeferencing. If the projection coordinates between the
            datasets are not an exact match, alignment occurs if falling within
            this tolerance.

    Returns:
        :class:`xarray.Dataset`: Data with the applied mask.

    Example:

        .. ipython::
           :okwarning:

           @savefig apply_mask.png width=6in
           In [0]: import pyku, pyku.mask, pyku.analyse
              ...: import pyku.features
              ...:
              ...: # Load example model data in rotated lon lat projection
              ...: # -----------------------------------------------------
              ...:
              ...: ds1 = (
              ...:     pyku.resources.get_test_data('model_data')
              ...:     .isel(time=0)
              ...: )
              ...:
              ...: # Load example hostrada data over germany in lcc projection
              ...: # ---------------------------------------------------------
              ...:
              ...: ds2 = pyku.resources.get_test_data('hostrada').isel(time=0)
              ...:
              ...: # Polygonize the mask of hostrada and apply to model data
              ...: # -------------------------------------------------------
              ...:
              ...: ds1_masked = (
              ...:     pyku.resources.get_test_data('model_data')
              ...:     .isel(time=0).pyku.apply_mask(ds2.pyku.polygonize())
              ...: )
              ...:
              ...: # Show mask before and after
              ...: # --------------------------
              ...:
              ...: pyku.analyse.two_maps(
              ...:     ds1.assign_attrs({'label': 'Before masking'}),
              ...:     ds1_masked.assign_attrs({'label': 'After masking'}),
              ...:     var='tas',
              ...:     crs='EUR-44',
              ...:     size_inches=(10,5)
              ...: )
    """

    import textwrap
    import numpy as np
    import xarray as xr
    import pyku.meta as meta
    import pyku.geo as geo
    import pyku.check as check
    import pyku.features as features

    # Experimenting with automated reprojection
    # -----------------------------------------

    out_dat = dat.copy()

    # Get a raster mask from polygon
    # ------------------------------

    mask = features.rasterize_polygons(
        mask, area_def=geo.get_area_def(out_dat)
    )

    # Rename the projection and geographic coordinates
    # ------------------------------------------------

    mask_y_name, mask_x_name = meta.get_projection_yx_varnames(mask)
    out_y_name, out_x_name = meta.get_projection_yx_varnames(out_dat)

    mask_lat_name, mask_lon_name = meta.get_geographic_latlon_varnames(mask)
    out_lat_name, out_lon_name = meta.get_geographic_latlon_varnames(out_dat)

    # If projection coordinates and geographic coordinates identical
    # --------------------------------------------------------------

    if out_y_name in [out_lat_name] and out_x_name in [out_lon_name]:

        mask = mask.drop_vars([mask_lat_name, mask_lon_name])

        mask = mask.rename({
            mask_y_name: out_lat_name,
            mask_x_name: out_lon_name,
        })

        mask[out_lat_name].attrs = out_dat[out_lat_name].attrs
        mask[out_lon_name].attrs = out_dat[out_lon_name].attrs

    # All other cases
    # ---------------

    else:

        mask = mask.rename({
            mask_y_name: out_y_name,
            mask_x_name: out_x_name,
            mask_lat_name: out_lat_name,
            mask_lon_name: out_lon_name,
        })

        mask[out_y_name].attrs = out_dat[out_y_name].attrs
        mask[out_x_name].attrs = out_dat[out_x_name].attrs
        mask[out_lat_name].attrs = out_dat[out_lat_name].attrs
        mask[out_lon_name].attrs = out_dat[out_lon_name].attrs

    # Convert nans to int
    # -------------------

    mask = xr.apply_ufunc(np.isnan, mask, dask='allowed').astype(int)

    # Check if georeferencing is aligned and correct if necessary
    # -----------------------------------------------------------

    checks = check.compare_geographic_alignment(
        out_dat, mask, tolerance=tolerance
    )

    ys_within_tolerance = checks.query(
        "key == 'y_projection_coordinates_within_tolerance'"
    ).value.all()

    xs_within_tolerance = checks.query(
        "key == 'x_projection_coordinates_within_tolerance'"
    ).value.all()

    if ys_within_tolerance is False or xs_within_tolerance is False:
        message = "y/x projection coordinates not within tolerance."
        raise Exception(message)

    # If the georeferencing between datasets nearly identical, align
    # --------------------------------------------------------------

    if ys_within_tolerance and xs_within_tolerance:

        try:
            mask = geo.align_georeferencing(
                mask, ref=out_dat, tolerance=tolerance
            )

        except Exception as e:

            message = textwrap.dedent(f"""\
                {e}
                The georeferencing was found to be not exact between dataset \
                but still within tolerance. However the operation to \
                alignment of georeferencing failed.""")

    # Loop georeferenced data and apply mask
    # --------------------------------------
    for var in meta.get_geodata_varnames(dat):
        if from_nans is True:
            out_dat[var] = out_dat[var].where(mask['regions'].notnull())

        else:
            out_dat[var] = out_dat[var].where(mask['regions'] == 0)

    return out_dat


def apply_raster_mask(dat, mask, from_nans=False, tolerance=0.001):

    """
    Mask data

    Arguments:
        dat (:class:`xarray.Dataset`): The input data.
        mask (:class:`xarray.Dataset`): The mask. The mask shall have the same
            projection coordinates as the input data.
        from_nans (bool): Indicates whether the mask is derived from NaN
            values.
        tolerance (float): Optional. A small value used as the tolerance for
            aligning georeferencing. If the projection coordinates between the
            datasets are not an exact match, alignment occurs when falling
            within this tolerance.

    Returns:
        :class:`xarray.Dataset`: Data with the applied mask.

    Example:

        .. ipython::
           :okwarning:

           @savefig apply_mask.png width=6in
           In [0]: import pyku
              ...:
              ...: # Load example model data in rotated lon lat projection
              ...: # -----------------------------------------------------
              ...:
              ...: ds1 = (
              ...:     pyku.resources.get_test_data('model_data')
              ...:     .isel(time=0)
              ...: )
              ...: ds2 = pyku.resources.get_test_data('hostrada').isel(time=0)
              ...:
              ...: # Both dataset should have the same projection
              ...: # --------------------------------------------
              ...:
              ...: ds1 = ds1.pyku.project('HYR-LAEA-5')
              ...: ds2 = ds2.pyku.project('HYR-LAEA-5')
              ...:
              ...: themask = ds2.pyku.get_mask()
              ...:
              ...: # Polygonize the mask of hostrada and apply to model data
              ...: # -------------------------------------------------------
              ...:
              ...: ds1_masked = ds1.pyku.apply_raster_mask(themask)
              ...:
              ...: # Show mask before and after
              ...: # --------------------------
              ...:
              ...: pyku.analyse.two_maps(
              ...:     ds1.assign_attrs({'label': 'Before masking'}),
              ...:     ds1_masked.assign_attrs({'label': 'After masking'}),
              ...:     var='tas',
              ...:     crs='EUR-44',
              ...:     size_inches=(10,5)
              ...: )

    """

    import textwrap
    import pyku.meta as meta
    import pyku.geo as geo
    import pyku.check as check

    # Experimenting with automated reprojection
    # -----------------------------------------

    out_dat = dat.copy()

    # Rename the projection and geographic coordinates
    # ------------------------------------------------

    mask_y_name, mask_x_name = meta.get_projection_yx_varnames(mask)
    out_y_name, out_x_name = meta.get_projection_yx_varnames(out_dat)

    mask_lat_name, mask_lon_name = meta.get_geographic_latlon_varnames(mask)
    out_lat_name, out_lon_name = meta.get_geographic_latlon_varnames(out_dat)

    # Get name of variable for masking
    # --------------------------------

    # Here the behavious may need discussion.

    mask_varnames = meta.get_geodata_varnames(mask)

    if len(mask_varnames) > 1:
        message = "More than one variable in masking dataset not supported"
        raise Exception(message)

    if len(mask_varnames) == 0:
        message = "No data for masking found in dataset"
        raise Exception(message)

    mask_varname = mask_varnames[0]

    # If projection coordinates and geographic coordinates identical
    # --------------------------------------------------------------

    if out_y_name in [out_lat_name] and out_x_name in [out_lon_name]:

        mask = mask.drop_vars([mask_lat_name, mask_lon_name])

        mask = mask.rename({
            mask_y_name: out_lat_name,
            mask_x_name: out_lon_name,
        })

        mask[out_lat_name].attrs = out_dat[out_lat_name].attrs
        mask[out_lon_name].attrs = out_dat[out_lon_name].attrs

    # All other cases
    # ---------------

    else:

        mask = mask.rename({
            mask_y_name: out_y_name,
            mask_x_name: out_x_name,
            mask_lat_name: out_lat_name,
            mask_lon_name: out_lon_name,
        })

        mask[out_y_name].attrs = out_dat[out_y_name].attrs
        mask[out_x_name].attrs = out_dat[out_x_name].attrs
        mask[out_lat_name].attrs = out_dat[out_lat_name].attrs
        mask[out_lon_name].attrs = out_dat[out_lon_name].attrs

    # Check if georeferencing is aligned and correct if necessary
    # -----------------------------------------------------------

    checks = check.compare_geographic_alignment(
        out_dat, mask, tolerance=tolerance
    )

    tolerancity = checks.query(
        "(value == 'Check y projection coordinates within tolerance' and \
          issue.notna()) \
         or \
         (value == 'Check x projection coordinates within tolerance' and \
          issue.notna())"
    )

    if len(tolerancity) > 0:
        message = \
            f"y/x projection coordinates not within tolerance: {tolerancity}"
        raise Exception(message)

    # If the georeferencing between datasets nearly identical, align
    # --------------------------------------------------------------

    if len(tolerancity) == 0:

        try:

            mask = geo.align_georeferencing(
                mask, ref=out_dat, tolerance=tolerance
            )

        except Exception as e:

            message = textwrap.dedent(f"""\
                {e}
                The georeferencing was found to be not exact between dataset \
                but still within tolerance. However the operation to \
                alignment of georeferencing failed.""")

    # Mask all georeferenced variables and return
    # -------------------------------------------

    for var in meta.get_geodata_varnames(dat):

        if from_nans is True:
            out_dat[var] = out_dat[var].where(mask[mask_varname].notnull())

        else:
            out_dat[var] = out_dat[var].where(mask[mask_varname] == 0)

    return out_dat


def apply_mask(dat, mask, from_nans=False, tolerance=0.001):

    """
    Mask data

    Arguments:

        dat (:class:`xarray.Dataset`): The input data.

        mask (:class:`xarray.Dataset`, :class:`geopandas.GeoDataFrame`):
            The mask can either be a polygon or a raster dataset with the same
            projection coordinates as the input data.

        from_nans (bool): Optional. Indicates whether the mask is derived from
            NaN values.

        tolerance (float): Optional. A small value used as the default
            tolerance for aligning georeferencing. If the projection
            coordinates between the datasets are not an exact match, alignment
            occurs if falling within this tolerance.

    Returns:
        :class:`xarray.Dataset`: Data with the applied mask.

    See Also:
        :func:`pyku.mask.apply_polygon_mask`,
        :func:`pyku.mask.apply_raster_mask`

    Example:

        .. ipython::
           :okwarning:

           @savefig apply_mask.png width=6in
           In [0]: import pyku, pyku.mask, pyku.analyse
              ...: import pyku.features
              ...:
              ...: # Load example model data in rotated lon lat projection
              ...: # -----------------------------------------------------
              ...:
              ...: ds1 = \\
              ...:    pyku.resources.get_test_data('model_data').isel(time=0)
              ...:
              ...: # Load example hostrada data over germany in lcc projection
              ...: # ---------------------------------------------------------
              ...:
              ...: ds2 = pyku.resources.get_test_data('hostrada').isel(time=0)
              ...:
              ...: # Polygonize the mask of hostrada and apply to model data
              ...: # -------------------------------------------------------
              ...:
              ...: ds1_masked = (
              ...:     pyku.resources.get_test_data('model_data')
              ...:     .isel(time=0).pyku.apply_mask(ds2.pyku.polygonize())
              ...: )
              ...:
              ...: # Show mask before and after
              ...: # --------------------------
              ...:
              ...: pyku.analyse.two_maps(
              ...:     ds1.assign_attrs({'label': 'Before masking'}),
              ...:     ds1_masked.assign_attrs({'label': 'After masking'}),
              ...:     var='tas',
              ...:     crs='EUR-44',
              ...:     size_inches=(10,5)
              ...: )
    """

    import geopandas as gpd
    import xarray as xr

    # If the mask is given as a polygon, convert mask to raster
    # ---------------------------------------------------------

    if isinstance(mask, gpd.geodataframe.GeoDataFrame):

        masked_dataset = apply_polygon_mask(
            dat, mask, from_nans=from_nans, tolerance=tolerance
        )

        return masked_dataset

    elif isinstance(mask, xr.Dataset):

        masked_dataset = apply_raster_mask(
            dat, mask, from_nans=from_nans, tolerance=tolerance
        )

        return masked_dataset

    else:
        message = f"Datatype {type(mask)} not supported"
        raise Exception(message)


def combine_masks(*dats):

    """
    Warnings:
        This function is not used and untested. It may be taken out.

    Combine data masks

    The mask is identified with NaN values. The combination is done for each
    timestep. To get the data mask over all timestemps, use
    :func:`~libmask.get_mask`

    Arguments:
        *dats (:class:`xarray.Dataset`): The input data.

    Returns:
        :class:`xarray.Dataset`: The data with combined masks.

    See Also:
        :func:`~mask.get_mask`
    """

    import xarray as xr
    import numpy as np

    # Check user inputs and deliver error
    # -----------------------------------

    data_types = [type(da) for da in dats]
    data_type = data_types[0]

    if (
        not isinstance(dats[0], xr.Dataset) and
        not isinstance(dats[0], xr.DataArray)
    ):
        message = (
            "Inputs shall be xarray Dataset or DataArray. The following data "
            "type were passed: {data_types}"
        )
        raise Exception(message)

    if data_types.count(data_type) != len(data_types):
        message = (
            f"Inputs shall be all be xarray Datasets, or all be DataArrays, "
            "but not a mix. The following data types were passed: "
            f"{data_types}"
        )
        raise Exception(message)

    # Combine the mask of the data
    # ----------------------------

    out_dats = []

    for current_da in dats:

        out_da = current_da

        for da in dats:
            out_da = out_da.where(~np.isnan(da))

        out_dats.append(out_da)

    return tuple(out_dats)


def get_mask(dat):

    """
    Get mask from Dataset.

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.

    Returns:
        :class:`xarray.Dataset`: The dataset mask.

    Example:

        .. ipython::
           :okwarning:

           @savefig mask_get_mask.png width=4in
           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hostrada')
              ...: mask = ds.pyku.get_mask()
              ...: pyku.analyse.one_map(mask, var='mask')
    """

    import pyku.meta as meta
    import numpy as np
    import xarray as xr

    if not isinstance(dat, xr.Dataset):
        message = "Input shall be a xarray.Dataset, not {type(dat)}"
        raise Exception(message)

    def _get_DataArray_mask(da):

        # Get all dimensions which are not spatial
        # ----------------------------------------

        non_spatial_dimensions = \
            set(da.dims) - set(meta.get_spatial_varnames(da))

        # Calculate the sum over dimensions which are not spatials
        # --------------------------------------------------------

        da_mask = da.reduce(np.sum, dim=non_spatial_dimensions)

        # Convert to boolean array where NaN, then convert to integer array
        # -----------------------------------------------------------------

        da_mask = xr.apply_ufunc(np.isnan, da_mask, dask='allowed').astype(int)

        # Rename DataArray
        # ----------------

        da_mask = da_mask.rename('mask')

        return da_mask

    # Get the masks for all data variables
    # ------------------------------------

    masks = [
        _get_DataArray_mask(dat[var])
        for var in meta.get_geodata_varnames(dat)
    ]

    # Caculate the sum over all masks
    # -------------------------------

    mask = sum(masks)

    # Maks if larger than 0 and convert to int
    # ----------------------------------------

    mask = np.greater(mask, 0).astype(int)

    # Drop unused time coordinate
    # ---------------------------

    if 'time' in mask.coords and mask.time.size == 1:
        mask = mask.drop('time')

    # Convert mask to dataset
    # -----------------------

    mask = mask.to_dataset()

    # Note I had an issue when using the mask in parallel and likely also
    # because the data that where being mask did not have the same chunking.
    # Hence the compute()

    mask = mask.compute()

    return mask
