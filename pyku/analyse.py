#!/usr/bin/env python3
"""
Analysis module
"""

import logging
import os
import textwrap
import matplotlib
import matplotlib.pyplot as plt

# Set tight parameter when saving figures
# ---------------------------------------

plt.rcParams['savefig.bbox'] = 'tight'

logger = logging.getLogger('analyse')


def _unchunk_along_time(da):

    """
    Unchunk xarray DataArray along time

    Arguments:
        da ([xarray.Dataset, xarray.DataArray]): Input data

    Returns:
        xarray.Dataset, or xarray.DataArray:
            Data unchunked along the time dimension if present
    """

    chunks = {dim: 'auto' for dim in da.dims}

    if 'time' in da.dims:
        chunks['time'] = -1

    return da.chunk(chunks=chunks)


def _get_DataArrays(dats, var=None):

    """
    Internal function that permits do distinguish between xarray.Dataset,
    xarray.DataArray, lists and squeezes dimensions

    Arguments:
        dats (:class:`xarray.Dataset`, List[:class:`xarray.Dataset`]):
            The input dataset(s).

    Returns:
        list: List of DataArrays if dats is a list
    """

    import textwrap
    import xarray as xr

    # If we get None, return None
    # ---------------------------

    if dats is None:
        return None

    # If a single dataset/datarray is passed, convert to list
    # -------------------------------------------------------

    if isinstance(dats, xr.DataArray) or isinstance(dats, xr.Dataset):
        dats = [dats]

    # Build list of data
    # ------------------

    list_of_data = []

    for dat in dats:

        if isinstance(dat, list):
            list_of_data.extend(dat)
        elif isinstance(dat, xr.Dataset):
            list_of_data.append(dat)
        elif isinstance(dat, xr.DataArray):
            list_of_data.append(dat)
        elif dat is None:
            pass
        else:
            message = textwrap.dedent(
                f"""
                Data is neither a list, a xr.Dataset, xr.DataArray, or None but
                {type(dat)}.
                """)

            raise Exception(message)

    datas = list_of_data

    # List of xr.DataArrays to be returned
    # ------------------------------------

    das = list()

    for dat in datas:

        # Squeeze dimensions
        # ------------------

        dat = dat.squeeze()

        if isinstance(dat, xr.Dataset):

            if var is None:
                message = "Specify variable with var='variable_name'"
                raise ValueError(message)

            if var not in dat.data_vars:
                message = textwrap.dedent(
                    f"""
                    Variable {var} not in dataset.

                    The dataset contains:
                    {dat.data_vars}
                    """)
                raise Exception(message)

            # Select variable from xr.Dataset
            # -------------------------------

            da = dat[var]
            das.append(da)

            # Pass label from xr.Dataset to xr.Datarray
            # -----------------------------------------

            if dat.attrs.get('label') is not None:
                da.attrs['label'] = dat.attrs['label']

        elif isinstance(dat, xr.DataArray):
            da = dat
            das.append(da)

        elif dat is None:
            pass

        else:
            raise ValueError(
                f"Data shall be a Dataset or a DataArray, not {type(dat)}"
            )

    return das


def one_map(dat, var=None, crs=None, **kwargs):

    """
    Plot one map

    Arguments:
        dat (:class:`xarray.Dataset`): The input dataset.
        var (str): The name of the variable.
        crs (Union[:class:`cartopy.crs.CRS`, :class:`pyresample.geometry.AreaDefinition`, str]):
            Coordinate reference system. A pyku pre-defined projection
            identifier can be passed with a string.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to
            :func:`matplotlib.pyplot.pcolormesh`,
            :func:`matplotlib.pyplot.axes`, :func:`matplotlib.pyplot.figure`,
            or :func:`cartopy.mpl.geoaxes.GeoAxes.gridlines`. For example,
            ``cmap``, ``vmin``, ``vmax``, or ``size_inches`` can be passed.

    Example:

        .. ipython::
           :okwarning:

           @savefig ana_one_map.png width=5in
           In [0]: %%time
              ...: import pyku
              ...: ds = (
              ...:    pyku.resources.get_test_data('small_tas_dataset')
              ...:    .isel(time=0).compute()
              ...: )
              ...: ds.ana.one_map(var='tas', crs='seamless_world')

    """  # noqa

    n_maps(dat, var=var, crs=crs, **kwargs)


def two_maps(dat1, dat2, var=None, crs=None, **kwargs):

    """
    Plot two maps side by side

    Arguments:
        dat1 (:class:`xarray.Dataset`): The first dataset.
        dat2 (:class:`xarray.Dataset`): The second dataset.
        var (str): The name of the variable.
        crs (Union[:class:`cartopy.crs.CRS`, :class:`pyresample.geometry.AreaDefinition`, str]):
            Coordonate reference system. A pyku pre-defined projection
            identifier can be passed with a string.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to
            :func:`matplotlib.pyplot.pcolormesh`,
            :func:`matplotlib.pyplot.axes` :func:`matplotlib.pyplot.figure`, or
            :func:`cartopy.mpl.geoaxes.GeoAxes.gridlines`. For example,
            ``cmap``, ``vmin``, ``vmax``, or ``size_inches`` can be passed.

    Notes:
        If an argument is passed which is not recognized, no error message is
        thrown and the argument is ignored.

    Example:

        .. ipython::
           :okwarning:

           @savefig two_maps.png width=6in
           In [0]: %%time
              ...: import pyku
              ...:
              ...: ds = pyku.resources.get_test_data('small_tas_dataset')
              ...:
              ...: pyku.analyse.two_maps(
              ...:     ds.isel(time=0),
              ...:     ds.isel(time=1),
              ...:     rows=1,
              ...:     cols=2,
              ...:     var='tas',
              ...:     crs='HYR-GER-LAEA-5',
              ...: )

    """  # noqa

    n_maps(dat1, dat2, var=var, crs=crs, **kwargs)


def n_maps(*dats, var=None, crs=None, colorbar=True, **kwargs):

    """
    Plot n maps side by side

    Arguments:
        dats (:class:`xarray.Dataset`, or List[:class:`xarray.Dataset`]):
            The input dataset.
        var (str):
            The variable name
        crs (:class:`cartopy.crs.CRS`, :class:`pyresample.geometry.AreaDefinition`, str):
            (Optional) Coordinate reference system of the plot. If a string is
            passed, a pre-configured projection definition is taken from the
            configuration files (e.g. 'EUR-44', 'HYR-LAEA-5').
        colorbar (bool):
            Optional. Defaults to ``True``. If set to ``False``, the colorbar
            is not shown and the colormap of all plots is set independently.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to
            :func:`matplotlib.pyplot.pcolormesh`,
            :func:`matplotlib.pyplot.axes` :func:`matplotlib.pyplot.figure`, or
            :func:`cartopy.mpl.gridliner.gridlines`. For example, ``cmap``,
            ``vmin``, ``vmax``, or ``size_inches`` can be passed.
            Further options to control the layout: ``wspace`` (value for plt.subplots_adjust),

    Example:

        .. ipython::
           :okwarning:

           @savefig n_maps.png width=6in
           In [0]: %%time
              ...: import pyku
              ...:
              ...: ds = (
              ...:     pyku.resources.get_test_data('small_tas_dataset')
              ...:     .compute()
              ...: )
              ...:
              ...: pyku.analyse.n_maps(
              ...:     ds.isel(time=0),
              ...:     ds.isel(time=1),
              ...:     ds.isel(time=2),
              ...:     ds.isel(time=3),
              ...:     nrows=2,
              ...:     ncols=2,
              ...:     var='tas',
              ...:     crs='HYR-GER-LAEA-5'
              ...: )
    """  # noqa

    import textwrap
    import numpy as np
    import cartopy
    import cartopy.crs as ccrs
    import pyresample.utils
    import pyku.geo as geo

    # Get xr.DataArrays
    # -----------------

    das = _get_DataArrays(dats, var=var)

    for dat_idx, dat in enumerate(das):
        das[dat_idx] = dat.compute()

    # Clear any existing matplotlib figures
    # -------------------------------------

    plt.clf()

    # Set the data CRS
    # ----------------

    # Since we read latitudes and longitudes from the data, every pixel is
    # converted using the Plate Caree projection, even though it is not
    # striclty speaking the projection of the data

    data_crs = ccrs.PlateCarree()

    if isinstance(crs, pyresample.geometry.AreaDefinition):
        crs = crs.to_cartopy_crs()

    if isinstance(crs, str):
        crs = geo.load_area_def(crs).to_cartopy_crs()

    # Set default projection of the plot to projection of data
    # --------------------------------------------------------

    # This is a first step towards setting the projection of the plot to the
    # projection of the data by default. If there is one than one dataset,
    # these could have different projections and that case is not included yet.

    # print("Marker", len(dats))
    # if crs is None and len(dats) == 1:
    #     try:
    #         print("Marker Here")
    #         area_def = geo.get_area_def(dats[0])
    #         crs = area_def.to_cartopy_crs()

    #     except Exception as e:
    #         message = f"could not read CRS from data using Plate Carree {e}"
    #         warnings.warn(message)
    #         crs = ccrs.PlateCarree()

    # Default the plot CRS to a Plate Carree
    # --------------------------------------

    if crs is None:
        crs = ccrs.PlateCarree()

    # Set the default map
    # -------------------

    if kwargs.get('cmap') is None:
        kwargs['cmap'] = 'viridis'

    # Calculate the lower quantile of all datasets, and keep the lowest
    # -----------------------------------------------------------------

    if kwargs.get('vmin') is None and colorbar is True:

        lower_quantiles = [
            das[idx].quantile(0.02).values
            for idx, _ in enumerate(das)
        ]

        kwargs['vmin'] = min(lower_quantiles)

    # Calculate the highest quantile of all datasets and keep the highest
    # -------------------------------------------------------------------

    if kwargs.get('vmax') is None and colorbar is True:

        upper_quantiles = [
            das[idx].quantile(0.98).values
            for idx, _ in enumerate(das)
        ]

        kwargs['vmax'] = max(upper_quantiles)

    # Get arguments that can be passed to plt.subplots
    # ------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) & set(plt.figure.__code__.co_varnames)
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    # Prepare two plots side by side
    # ------------------------------

    nrows = 1
    ncols = len(das)

    if kwargs.get('nrows') is not None:
        nrows = kwargs.get('nrows')

    if kwargs.get('ncols') is not None:
        ncols = kwargs.get('ncols')

    if len(das) > nrows*ncols:
        message = textwrap.dedent(
            f"""
            Trying to plot for {len(das)} data arrays but 'ncols' is {ncols}
            and 'nrows' is {nrows}. Increase 'nrows' and/or 'ncols' according
            to the number of arrays to plot.
            """
        )
        raise Exception(message)

    fig, axs = plt.subplots(
        nrows,
        ncols,
        subplot_kw={'projection': crs},
        **extra_kwargs
    )

    # bring columns of axes (subplots) closer together
    # ------------------------------------------------

    if kwargs.get('wspace') is not None:
        wspace = kwargs.get('wspace')
        if ncols > 1:
            plt.subplots_adjust(wspace=wspace)

    # Get arguments that can be passed to ax1.pcolormesh
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) & set(matplotlib.pyplot.pcolormesh.__code__.co_varnames)  # noqa
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    # Plot
    # ----

    for dat_idx, dat in enumerate(das):

        # Get lons and lats from file
        # ---------------------------

        lons, lats = geo.get_lonlats(dat)

        ax_ = np.array(axs).reshape(-1)[dat_idx]

        if len(dat.dims) > 2:
            message = textwrap.dedent(
                f"""
                The function does a 2D plot. However the number of dimension in
                the dataset passed is {len(dat.dims)}, with the following
                dimension names: {dat.dims}. Select 2D spatial data, for
                example by selecting a single time and/or level. This can be
                done with xarray ``sel`` or ``isel`` functions. For example the
                first datatime in your dataset can be selected with:
                yourdata.isel(time=0).
                """)
            raise Exception(message)

        # plot
        # ----

        im = ax_.pcolormesh(
            lons,
            lats,
            dat.values,
            transform=data_crs,
            **extra_kwargs,
        )

        # Set plots titles if label available in the metadata
        # ---------------------------------------------------

        if dat.attrs.get("label") is not None:
            ax_.set_title(dat.attrs.get("label"))

    # Set colorbar label
    # ------------------

    cbar_label = ''

    if das[-1].attrs.get('standard_name') is not None:
        cbar_label = das[-1].attrs.get('standard_name')

    if das[-1].attrs.get('long_name') is not None:
        cbar_label = das[-1].attrs.get('long_name')

    if das[-1].attrs.get('units') is not None:
        cbar_label = f"{cbar_label} [{das[-1].attrs.get('units')}]"

    # Get figure size
    # ---------------

    pixel_width, pixel_height = fig.get_size_inches()*fig.dpi
    inches_width, inches_height = fig.get_size_inches()

    fig.set_size_inches((inches_width * ncols, inches_height * nrows))

    # Build the color bar
    # -------------------

    if colorbar is True:

        # Set pointy ends for out-of-range values
        # ---------------------------------------

        extend = 'neither'

        for idx, _ in enumerate(das):

            if das[idx].max() > kwargs['vmax']:
                extend = 'max'

            if das[idx].min() < kwargs['vmin']:
                extend = 'min'

            if das[idx].min() < kwargs['vmin'] and \
               das[idx].max() > kwargs['vmax']:
                extend = 'both'

        cbar_xpos = 1 + 0.07/ncols
        cbar_ypos = .05
        cbar_width = .03/ncols
        cbar_height = .95
        cbar_ticks = None

        if kwargs.get('cbar_xpos') is not None:
            cbar_xpos = kwargs.get('cbar_xpos')
        if kwargs.get('cbar_ypos') is not None:
            cbar_ypos = kwargs.get('cbar_ypos')
        if kwargs.get('cbar_width') is not None:
            cbar_width = kwargs.get('cbar_width')
        if kwargs.get('cbar_height') is not None:
            cbar_height = kwargs.get('cbar_height')
        if kwargs.get('cbar_ticks') is not None:
            cbar_ticks = kwargs.get('cbar_ticks')

        cb_ax = fig.add_axes([cbar_xpos, cbar_ypos,
                              cbar_width, cbar_height])

        fig.colorbar(
            im,
            orientation='vertical',
            cax=cb_ax,
            extend=extend,
            label=cbar_label,
            ticks=cbar_ticks
        )

    # Pass any extra arguments that can be passed to gca
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gca()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gca(), **extra_kwargs)

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)

    # Add cartopy features
    # --------------------

    for idx, ax in enumerate(np.array(axs).reshape(-1)):

        if idx > len(das)-1:
            ax.set_visible(False)  # to remove last plot
            continue

        ax.add_feature(cartopy.feature.BORDERS)
        ax.add_feature(cartopy.feature.LAKES)
        ax.add_feature(cartopy.feature.RIVERS)
        ax.add_feature(cartopy.feature.BORDERS)
        ax.add_feature(cartopy.feature.COASTLINE)
        ax.gridlines(
            draw_labels=kwargs.get('draw_labels', True),
            dms=kwargs.get('dms', True),
            xlocs=kwargs.get('xlocs', None),
            ylocs=kwargs.get('ylocs', None),
            x_inline=kwargs.get('x_inline', False),
            y_inline=kwargs.get('y_inline', False),
            xformatter=kwargs.get('xformatter', None),
            yformatter=kwargs.get('yformatter', None),
            auto_inline=kwargs.get('auto_inline', True),
            xlim=kwargs.get('xlim', None),
            ylim=kwargs.get('ylim', None),
            rotate_labels=kwargs.get('rotate_labels', None),
            xlabel_style=kwargs.get('xlabel_style', None),
            ylabel_style=kwargs.get('ylable_style', None),
            labels_bbox_style=kwargs.get('labels_bbox_style', None),
            xpadding=kwargs.get('xpadding', 5),
            ypadding=kwargs.get('ypadding', 5),
            offset_angle=kwargs.get('offset_angle', 25),
            auto_update=kwargs.get('auto_update', False),
            formatter_kwargs=kwargs.get('formatter_kwargs', None),
        )


def metadata(ds_mod, ds_obs):

    """
    Report on metadata

    Arguments:
        ds_mod (:class:`xarray.Dataset`): Model dataset.
        ds_obs (:class:`xarray.Dataset`): Reference dataset.

    Returns:
        str: reStructuredText report
    """

    import pyku.meta as meta
    import pyku.timekit as timekit
    import pandas as pd

    # Initialize report string
    # ------------------------

    report = ""

    # Available variables
    # -------------------

    mod_variables = list(ds_mod.data_vars)

    if ds_obs is not None:
        obs_variables = list(ds_obs.data_vars)
    else:
        obs_variables = []

    report += textwrap.dedent(
        f"""
        Metadata
        ========

        Variables:

        - Model: {mod_variables}

        - Reference: {obs_variables}

        """)

    # Get data variables by removing know spatial and temporal variables
    # ------------------------------------------------------------------

    mod_variables = meta.get_geodata_varnames(ds_mod)

    if ds_obs is not None:
        obs_variables = meta.get_geodata_varnames(ds_obs)
    else:
        obs_variables = []

    report += textwrap.dedent(
        f"""
        Data variables:
        - Model: {mod_variables}
        - Reference: {obs_variables}
        """)

    # Datetimes for data variables
    # ----------------------------

    for varname in set(mod_variables + obs_variables):

        report += textwrap.dedent(
            f"""

            {varname}

            """)

        if varname in mod_variables:

            mod_datetimes = list(ds_mod[varname].coords['time'].values)
            mod_datetimes = [pd.to_datetime(str(el)) for el in mod_datetimes]

            min_datetime = min(mod_datetimes, default="NA")
            max_datetime = max(mod_datetimes, default="NA")

            min_datetime = "NA" if min_datetime == "NA" \
                else min_datetime.strftime("%Y-%m-%d %H:%M")

            max_datetime = "NA" if max_datetime == "NA" \
                else max_datetime.strftime("%Y-%m-%d %H:%M")

            report += f"""\
- Model: {len(mod_datetimes)} datetimes from {min_datetime} to {max_datetime}
"""

        if ds_obs is not None and varname in list(ds_obs.data_vars):

            obs_datetimes = list(ds_obs[varname].coords['time'].values)
            obs_datetimes = [pd.to_datetime(str(el)) for el in obs_datetimes]

            min_datetime = min(obs_datetimes, default="NA")
            max_datetime = max(obs_datetimes, default="NA")

            min_datetime = "NA" if min_datetime == "NA" \
                else min_datetime.strftime("%Y-%m-%d %H:%M")

            max_datetime = "NA" if max_datetime == "NA" \
                else max_datetime.strftime("%Y-%m-%d %H:%M")

            report += f"""\
- Reference: {len(obs_datetimes)} datetimes from {min_datetime} to \
{max_datetime}
"""

        if (
            ds_obs is not None
            and varname in list(ds_mod.data_vars)
            and varname in list(ds_obs.data_vars)
        ):

            # Get DataArrays and select common datetimes
            # ------------------------------------------

            da_mod = _get_DataArrays(ds_mod, var=varname)[0]
            da_obs = _get_DataArrays(ds_obs, var=varname)[0]
            da_mod, da_obs = timekit.select_common_datetimes(da_mod, da_obs)

            # Get the times from the model data and return min and max
            # --------------------------------------------------------

            inter_datetimes = list(da_mod.coords['time'].values)
            inter_datetimes = [
                pd.to_datetime(str(el)) for el in inter_datetimes
            ]

            min_datetime = min(inter_datetimes, default="NA")
            max_datetime = max(inter_datetimes, default="NA")

            min_datetime = "NA" if min_datetime == "NA" \
                else min_datetime.strftime("%Y-%m-%d %H:%M")
            max_datetime = "NA" if max_datetime == "NA" \
                else max_datetime.strftime("%Y-%m-%d %H:%M")

            report += f"""\
- Common {len(inter_datetimes)} datetimes from {min_datetime} to {max_datetime}
"""

        else:

            report += textwrap.dedent(
                f"""

                - {varname} not included in reference dataset

                """)

    report += textwrap.dedent(
        """

        .. raw:: pdf

           PageBreak

        """)

    return report


def summary_table(ds_mod, ds_obs, **kwargs):

    """
    Summary in table form

    Arguments:
        ds_mod (:class:`xarray.Dataset`): Model dataset.
        ds_obs (:class:`xarray.Dataset`): Reference dataset.

    Returns:
        str: reStructuredText table
    """

    import csv
    import pyku.meta as meta

    # Set file name
    # -------------

    file_name = "summary.csv"
    output_file = os.path.join(kwargs['PLOT_DIR'], file_name)

    with open(output_file, 'w') as f:

        writer = csv.writer(f)

        writer.writerow([
            'Variable',
            'Long name',
            'Mod Mean',
            'Ref Mean',
            'Mod Std',
            'Ref Std',
        ])

        for var in meta.get_geodata_varnames(ds_mod):

            row = []
            row.append(var)
            if 'long_name' in ds_mod[var].attrs.keys():
                row.append(ds_mod[var].attrs['long_name'])
            else:
                logger.info(f"Warning, {var} has no 'long_name' attributes")
                row.append('Unknown')

            if var in ds_mod.data_vars.keys():
                row.append(ds_mod[var].mean().values)
            else:
                row.append('NA')

            if ds_obs is not None and var in ds_obs.data_vars.keys():
                row.append(ds_obs[var].mean().values)
            else:
                row.append('NA')

            if var in ds_mod.data_vars.keys():
                row.append(ds_mod[var].std().values)
            else:
                row.append('NA')

            if ds_obs is not None and var in ds_obs.data_vars.keys():
                row.append(ds_obs[var].std().values)
            else:
                row.append('NA')

            writer.writerow(row)

    print(f'- Summary table: {output_file}')

    return textwrap.dedent(
        f"""
        .. csv-table:: Prototype table
           :file: {file_name}
           :header-rows: 1
        """)


def regions(gdf, area_def, **kwargs):

    """
    Plot regions

    Arguments:
        gdf (geopandas.GeoDataFrame): Polygon data
        area_def ([pyresample.AreaDefinition, string]): Area definition

    Other Parameters:
        **kwargs:
            Any argument that can be passed to :obj:`matplotlib.Artist`
            In particular ``size_inches`` can be passed.

    Example:

        .. ipython::
           :okwarning:

           @savefig ana_regions.png width=4in
           In [0]: import pyku
              ...: gdf = pyku.resources.get_geodataframe(
              ...:     'natural_areas_of_germany'
              ...: )
              ...: pyku.analyse.regions(gdf, area_def='HYR-LAEA-5')
    """

    import textwrap
    import pyku.geo as geo
    import cartopy

    if isinstance(area_def, str):
        area_def = geo.load_area_def(area_def)

    # Clear figures
    # -------------

    plt.clf()

    # Set figure size
    # ---------------

    if kwargs.get('size_inches') is None:
        kwargs['size_inches'] = (14, 10)

    # Get pyresample and cartopy projections
    # --------------------------------------

    crs = area_def.to_cartopy_crs()

    # Set the color map
    # -----------------

    identifiers = range(gdf.shape[0])
    gdf['idx'] = identifiers
    cmap = 'tab20b'

    # Lower column case (to make column case insensitive)
    # ---------------------------------------------------

    gdf.columns = [c.lower() for c in gdf.columns]

    # Convert the CRS of the data to custom CRS
    # -----------------------------------------

    gdf = gdf.to_crs(crs)

    ax = plt.axes(
        projection=crs,
    )

    ax.set_extent(crs.bounds, crs=crs)

    gdf.plot(
        column='idx',
        cmap=cmap,
        edgecolor="red",
        ax=ax
    )

    if 'name' in gdf.columns:
        gdf.apply(
            lambda x: ax.annotate(
                text=textwrap.fill(x['name'], 20),
                xy=x.geometry.centroid.coords[0],
                ha='center',
                wrap=True
            ),
            axis=1
        )

    ax.axes.add_feature(cartopy.feature.BORDERS)
    ax.axes.add_feature(cartopy.feature.LAKES)
    ax.axes.add_feature(cartopy.feature.RIVERS)
    ax.axes.add_feature(cartopy.feature.BORDERS)
    ax.axes.add_feature(cartopy.feature.COASTLINE)
    ax.axes.gridlines(
        draw_labels=True, dms=True, x_inline=False, y_inline=False)

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)


def pdf(*dats, var=None, ax=None, **kwargs):

    """
    Probability distribution function

    Arguments:
        dats ([:class:`xarray.Dataset`, List[:class:`xarray.DataArray`]]):
            The input dataset(s)
        var (str): The variable names.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to :obj:`matplotlib.pyplot.figure`
            or :func:`matplotlib.pyplot.axes`. In particular ``ylim=(0,15)``,
            ``size_inches=(20, 40))``, or ``yscale='log'`` can be passed.
        range (tuple): data Range, e.g. ``range=(0, 10)``.
        nbins (int): Number of bins.
        nsamples (int): Number of points sampled from the data..

    Example:

        .. ipython::
           :okwarning:

           @savefig ana_pdf.png width=4in
           In [0]: %%time
              ...: import pyku
              ...: ds = pyku.resources.get_test_data('hyras_tas').compute()
              ...: ds.ana.pdf(var='tas', nbins=80)
    """

    import warnings
    import textwrap
    import copy
    import dask
    import dask.array
    import numpy as np
    import itertools

    # Get xr.DataArrays
    # -----------------

    das = _get_DataArrays(dats, var=var)

    # Define cycles
    # -------------

    linestyles = itertools.cycle(["-", ":", "--", "-.",])
    # markers = itertools.cycle(["s", "o", "D", "v", "^"])
    # fillstyles = itertools.cycle(["none", "full", "left"])
    colors = itertools.cycle(['black', 'blue', 'red', 'orange', 'green'])

    # Clear figure
    # ------------

    if ax is None:
        plt.clf()
    else:
        plt.sca(ax)

    # Set bins
    # --------

    nbins = kwargs.get("nbins", 128)
    figsize = (10, 5)

    # Prepare list of patches
    # -----------------------

    for idx, da in enumerate(das):

        da_sel = da

        # Calculate the size of the data in GB
        # ------------------------------------

        # The amount of data analyzed is limited to 32GB

        GB = 1
        data_size = da.size*32/8/(1024*1024*1024)*GB
        max_data_size = 32*GB

        if data_size > max_data_size:

            message = textwrap.dedent(
                """
                Amount of data above memory threshold. Subsampling the data
                along time the time dimension.
                """
            )
            warnings.warn(message)

            # Get datetimes available in dataset
            # ----------------------------------

            times = da.coords['time'].values
            ntimes = len(times)

            # Calculate the number of timesteps that can fit in memory limit
            # --------------------------------------------------------------

            ntimes_cut = int(ntimes*max_data_size/data_size)

            # Get datetimes from dataarray, shuffle, cut and sort
            # ---------------------------------------------------

            times_sel = copy.deepcopy(da.coords['time'].values)
            np.random.shuffle(times_sel)
            times_sel = times_sel[0:ntimes_cut]
            times_sel = np.sort(times_sel)

            # Take only the randomly selected datetimes for the analysis
            # ----------------------------------------------------------

            da_sel = da.sel(time=times_sel)

        else:
            da_sel = da

        # Get numpy array
        # ---------------

        dat = da_sel.data

        # Remove NaNs
        # -----------

        dat = dat[dask.array.isfinite(dat)]

        if kwargs.get('nsamples') is not None:
            dat = dat.reshape(-1)
            dat = np.random.choice(dat, kwargs.get('nsamples'))

        # Check if data are all NaNs
        # --------------------------

        if isinstance(dat, dask.array.core.Array) and \
                dask.array.isnan(dat).all():

            warnings.warn("All nan numpy array found!")
            return

        if isinstance(dat, np.ndarray) and np.isnan(dat).all():
            warnings.warn("All nan dask array found!")
            return

        # Calculate histogram
        # -------------------

        if isinstance(dat, np.ndarray):

            hist, bins = np.histogram(
                dat,
                bins=nbins,
                range=kwargs.get('range'),
                density=True
            )

        elif isinstance(dat, dask.array.core.Array):

            hist, bins = dask.array.histogram(
                dat,
                bins=nbins,
                range=kwargs.get('range', (dat.min(), dat.max())),
                density=True
            )

            hist.compute()

        else:
            message = textwrap.dedent(
                f"""
                Data neither numpy nor dask arrays, but unspported {type(dat)}
                """
            )
            raise Exception(message)

        # If there is e.g. no snow in August, we get nans and infs
        # --------------------------------------------------------

        all_finites = np.isfinite(hist).all()

        if not all_finites and kwargs.get('yscale') in ['log']:
            kwargs['yscale'] = 'linear'

        # Convert bin edges to centers
        # ----------------------------

        bins = bins[:-1] + (bins[1] - bins[0])/2

        # Plot
        # ----

        plt.plot(
            bins,
            hist,
            label=da.attrs.get('label', f'Dataset {idx}'),
            linestyle=next(linestyles),
            color=next(colors)
        )
        plt.legend()

    # Set label from first dataset that is passed
    # -------------------------------------------

    if 'long_name' in das[0].attrs.keys() and 'units' in das[0].attrs.keys():
        xlabel = f"{das[0].attrs['long_name']} [{das[0].attrs['units']}]"
    else:
        print(
            f"WARNING: {var} has no 'long_name' and/or 'units' in attributes"
        )
        xlabel = f"{var}"

    plt.xlabel(xlabel)
    plt.ylabel('Probability')

    # Set x Axis min and max
    # ----------------------

    if kwargs.get('xlim') is not None:
        plt.xlim(kwargs.get('xlim'))

    # Set figure size
    # ---------------

    fig = plt.gcf()
    fig.set_size_inches(figsize)

    # plt.legend(handles=patches)

    # Pass any extra arguments that can be passed to gca
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gca()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gca(), **extra_kwargs)

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)


def monthly_pdf(*dats, var=None, **kwargs):

    """

    Probability distribution function for each season

    Arguments:
        *dats (:class:`xarray.Dataset`, List[:class:`xarray.Dataset`]):
            The input dataset(s)
        var (str): The variable name.
        crs (:class:`cartopy.crs.CRS`, :class:`pyresample.geometry.AreaDefinition`, str):
            (Optional). The coordinate reference system of the plot.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to :func:`matplotlib.pyplot.figure`
            or :func:`matplotlib.pyplot.axes`. In particular ``ylim=(0,15)``,
            ``size_inches=(20, 40))``, or ``yscale='log'`` can be passed.

    Example:

        .. ipython::

           @savefig monthly_pdf.png width=4in
           In [0]: %%time
              ...: import pyku
              ...: ds = pyku.resources.get_test_data('hyras_tas').compute()
              ...: ds.ana.monthly_pdf(var='tas')
    """  # noqa

    # Set default figure size
    # -----------------------

    if kwargs.get('size_inches') is None:
        kwargs['size_inches'] = (15, 20)

    # Get xr.DataArrays
    # -----------------

    das = _get_DataArrays(dats, var=var)

    # Clear figure
    # ------------

    plt.clf()

    # Define subplots
    # ---------------

    fig, axs = plt.subplots(4, 3)

    # List of datasets grouped by seasons
    # -----------------------------------

    grouped_das = []

    for da in das:
        grouped_das.append(da.groupby('time.month'))

    # Loop over all seasons
    # ---------------------

    for idx, month in enumerate(zip(*grouped_das)):

        # Get the season identifier from first dataset
        # --------------------------------------------

        # season is of the form:
        # [ (season_name, dataset1), (season_name, dataset2), ... ]

        month_name = month[0][0]

        # Seasonal_das is of the form
        # [ dataset1, dataset2, ... ]

        # Searching for empty data was moved to the pdf plot
        # for el in month:
        #     if bool(el[1].isnull().all()):
        #         warnings.warn("Found empty data")

        monthly_das = [el[1] for el in month]

        cax = axs.reshape(-1)[idx]
        pdf(*monthly_das, var=var, ax=cax, **kwargs)

        # Set axis title
        # --------------

        cax.set_title(f'{month_name}')

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)


def seasonal_pdf(*dats, var=None, **kwargs):

    """

    Probability distribution function for each season

    Arguments:
        dats (:class:`xarray.Dataset`, List[:class:`xarray.Dataset`]]):
            The input dataset(s).
        var (str): The variable name.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to :func:`matplotlib.pyplot.figure`
            or :func:`matplotlib.pyplot.axes`. In particular ``ylim=(0,15)``,
            ``size_inches=(20, 40))``, or ``yscale='log'`` can be passed.

    Example:

        .. ipython::

           @savefig seasonal_pdf.png width=4in
           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras_tas')
              ...: ds.ana.seasonal_pdf(var='tas')

    """

    # Set default figure size
    # -----------------------

    if kwargs.get('size_inches') is None:
        kwargs['size_inches'] = (15, 15)

    # Get xr.DataArrays
    # -----------------

    das = _get_DataArrays(dats, var=var)

    # Clear figure
    # ------------

    plt.clf()

    # Define subplots
    # ---------------

    fig, axs = plt.subplots(2, 2)

    # List of datasets grouped by seasons
    # -----------------------------------

    grouped_das = []

    for da in das:
        grouped_das.append(da.groupby('time.season'))

    # Loop over all seasons
    # ---------------------

    for idx, season in enumerate(zip(*grouped_das)):

        # Get the season identifier from first dataset
        # --------------------------------------------

        # season is of the form:
        # [ (season_name, dataset1), (season_name, dataset2), ... ]

        season_name = season[0][0]

        # Seasonal_das is of the form
        # [ dataset1, dataset2, ... ]

        seasonal_das = [el[1] for el in season]

        cax = axs.reshape(-1)[idx]
        pdf(*seasonal_das, var=var, ax=cax, **kwargs)

        # Set axis title
        # --------------

        cax.set_title(f'{season_name}')

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)


def mean_map(*dats, var=None, crs=None, same_datetimes=True, **kwargs):

    """
    Map of the mean

    Arguments:
        dats (:class:`xarray.Dataset`, List[:class:`xarray.Dataset`]): The
            input dataset(s)
        var (str): The variable name.
        crs (:class:`cartopy.crs.CRS`, :class:`pyresample.geometry.AreaDefinition, str`):
            (Optional) Coordinate reference system of the plot.
        same_datetimes (bool):
            (Optional) Defaults to ``True``. Select common datetimes between
            datasets.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to
            :func:`matplotlib.pyplot.pcolormesh`,
            :func:`matplotlib.pyplot.axes` :func:`matplotlib.pyplot.figure`, or
            :func:`cartopy.mpl.gridliner.gridlines`. For example, ``cmap``,
            ``vmin``, ``vmax``, or ``size_inches`` can be passed.

    Example:

        .. ipython::
           :okwarning:

           @savefig mean_map.png width=5in
           In [0]: %%time
              ...: import pyku
              ...: ds = (
              ...:     pyku.resources.get_test_data('hyras-tas-monthly')
              ...:     .compute()
              ...: )
              ...: ds.ana.mean_map(var='tas', crs='HYR-LAEA-5')
    """  # noqa

    import pyku.colormaps as colormaps

    # Set colormaps
    # -------------

    if kwargs.get('cmap') is None and var in ['pr']:
        kwargs['cmap'] = colormaps.get_cmap('precip_abs')

    # Get xr.DataArrays
    # -----------------

    das = _get_DataArrays(dats, var=var)

    # Throw exceptions
    # ----------------

    for idx, da in enumerate(das):
        if 'time' not in list(da.dims):
            message = \
                f'Only one timestep or time not a dimension in dataset {idx}!'
            raise Exception(message)

    # Clear figure
    # ------------

    plt.clf()

    # Calculate the mean
    # ------------------

    das_mean = [da.mean('time', keep_attrs=True) for da in das]

    # Plot
    # ----

    n_maps(*das_mean, crs=crs, **kwargs)


def mae_map(*dats, ref=None, var=None, crs=None, **kwargs):

    """
    Map of the mean absolute error.

    Arguments:
        dats (:class:`xarray.Dataset`): The input dataset(s).
        ref (:class:`xarray.Dataset`): The reference dataset.
        var (str): The variable name.
        crs (:class:`cartopy.crs.CRS`): The coordinate reference system.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to
            :func:`matplotlib.pyplot.pcolormesh`,
            :func:`matplotlib.pyplot.axes` :func:`matplotlib.pyplot.figure`, or
            :func:`cartopy.mpl.gridliner.gridlines`. For example, ``cmap``,
            ``vmin``, ``vmax``, or ``size_inches`` can be passed.

    Notes:
        If an argument is passed which is not recognized, no error message is
        thrown and the argument is ignored.

    Example:

        .. ipython::
           :okwarning:

           @savefig mae_map.png width=5in
           In [0]: %%time
              ...: import pyku
              ...:
              ...: # Open reference dataset and preprocess as needed
              ...: # -----------------------------------------------
              ...:
              ...: ref = pyku.resources.get_test_data('hyras')\\
              ...:       .pyku.to_cmor_units()\\
              ...:       .pyku.set_time_labels_from_time_bounds(how='lower')\\
              ...:       .pyku.project('HYR-LAEA-50')\\
              ...:       .sel(time='1981')\\
              ...:       .compute()
              ...:
              ...: # Open model dataset and preprocess as needed
              ...: # -------------------------------------------
              ...:
              ...: ds = pyku.resources.get_test_data('model_data')\\
              ...:      .pyku.project('HYR-LAEA-50')\\
              ...:      .pyku.set_time_labels_from_time_bounds(how='lower')\\
              ...:      .sel(time='1981')\\
              ...:      .compute()
              ...:
              ...: # Calculate and plot
              ...: # ------------------
              ...:
              ...: ds.ana.mae_map(ref=ref, var='tas', crs='HYR-LAEA-5')
    """  # noqa

    import xskillscore
    import pyku.timekit as timekit

    # Get xr.DataArrays
    # -----------------

    das = _get_DataArrays(dats, var=var)
    da_ref = _get_DataArrays(ref, var=var)[0]

    # Calculate
    # ---------

    das_mae = []

    for da in das:

        # Select common datetimes and unchunk along time
        # ----------------------------------------------

        sel_ref, sel_da = timekit.select_common_datetimes(da_ref, da)

        sel_ref = _unchunk_along_time(sel_ref)
        sel_da = _unchunk_along_time(sel_da)

        # Calculate the MSE
        # -----------------

        da_mae = xskillscore.mae(sel_da, sel_ref, dim='time', skipna=True)

        # Set attributes and append to list of results
        # --------------------------------------------

        da_mae.attrs = da.attrs
        da_mae.attrs['long_name'] = 'MAE'
        da_mae.attrs.pop('units', None)
        das_mae.append(da_mae)

    # Plot
    # ----

    n_maps(*das_mae, crs=crs, **kwargs)


def monthly_bias_var(ds_mod, ds_obs, var, **kwargs):

    """
    Monthly bias variation

    Arguments:
        ds_mod (:class:`xarray.Dataset`): The input dataset.
        ds_obs (:class:`xarray.Dataset`): The reference dataset.
        var (str): The variable name.
        crs (:class:`cartopy.crs.CRS`, :class:`pyresample.geometry.AreaDefinition`):
            (Optional) Coordinate reference system of the plot.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to :func:`matplotlib.pyplot.figure`
            or :func:`matplotlib.pyplot.axes`. In particular ``ylim=(0,15)``,
            ``size_inches=(20, 40))``, or ``yscale='log'`` can be passed.

    Example:

        .. ipython::
           :okwarning:

           @savefig monthly_bias_var.png width=4in
           In [0]: %%time
              ...: import pyku
              ...:
              ...: # Open, reproject
              ...: # ---------------
              ...:
              ...: ref = pyku.resources.get_test_data('hyras')\\
              ...:      .pyku.set_time_labels_from_time_bounds(how='lower')\\
              ...:      .pyku.to_cmor_units()\\
              ...:      .pyku.project('HYR-LAEA-50')\\
              ...:      .sel(time='1981')
              ...:
              ...: # Open model, reproject, reset time labels, select the year
              ...: # ---------------------------------------------------------
              ...:
              ...: ds = pyku.resources.get_test_data('model_data')\\
              ...:      .pyku.project('HYR-LAEA-50')\\
              ...:      .pyku.set_time_labels_from_time_bounds(how='lower')\\
              ...:      .sel(time='1981')
              ...:
              ...: # Calculate and plot
              ...: # ------------------
              ...:
              ...: ds.ana.monthly_bias_var(ref, var='tas')
    """  # noqa

    import calendar

    import numpy as np

    from pyku import timekit

    # Clear current figure
    # --------------------

    plt.clf()

    # Set default figure size
    # -----------------------

    if kwargs.get('size_inches') is None:
        kwargs['size_inches'] = (12, 8)

    # Get xr.DataArrays
    # -----------------

    da_mod = _get_DataArrays(ds_mod, var=var)[0]
    da_obs = _get_DataArrays(ds_obs, var=var)[0]

    # Select common datetimes
    # -----------------------

    da_mod, da_obs = timekit.select_common_datetimes(da_mod, da_obs)

    # Calculate bias
    # --------------

    bias_da = (da_mod-da_obs)

    # The dimensions are listed and the time dimension removed in order to
    # perform the mean on all dimensions but the time. The data are grouped by
    # month with ``groupby`` and the month number can be accessed with
    # ``.groups.keys()``. Type conversion to numpy array is performed with
    # np.asarray(list(GroupBy.groups.keys()))

    dims = list(bias_da.dims)
    dims.remove('time')

    # Group by month, calculate the mean and convert to dataframe
    # -----------------------------------------------------------

    group = bias_da.groupby('time.month')
    bias_df = group.mean(dims).to_dataframe()

    # Select column
    # -------------

    bias_df = bias_df[[var]]

    # Plot
    # ----

    ax1 = bias_df.groupby(lambda x: x.strftime("%m")).boxplot(
        subplots=False,
        rot=90,
        color='blue',
        flierprops={'markeredgecolor': 'blue'},
        positions=np.asarray(list(group.groups.keys()))-0.25,
    )

    ax1.set_ylabel("Bias")
    ax1.grid(False)
    ax1.set_xticks(ticks=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
    ax1.set_xticklabels(list(calendar.month_name[1:]))
    ax1.tick_params(axis='x', which='both', length=0)
    plt.xticks(rotation=45)

    # Pass any extra arguments that can be passed to gca
    # --------------------------------------------------

    extra_arguments = list(
      set(kwargs.keys()) &
      set(matplotlib.artist.Artist.properties(plt.gca()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gca(), **extra_kwargs)

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)


def monthly_bias(dat_mod, dat_obs, var=None, ax=None, **kwargs):

    """
    Monthly bias

    Arguments:
        dat_mod (:class:`xarray.Dataset`): The input dataset.
        dat_obs (:class:`xarray.Dataset`): The reference dataset.
        var (str): The variable name.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to :func:`matplotlib.pyplot.figure`
            or :func:`matplotlib.pyplot.axes`. In particular ``ylim=(0,15)``,
            ``size_inches=(20, 40))``, or ``yscale='log'`` can be passed.

    Example:

        .. ipython::
           :okwarning:

           @savefig monthly_bias.png width=4in
           In [0]: import pyku
              ...:
              ...: # Open reference data and preprocess as needed
              ...: # --------------------------------------------
              ...:
              ...: ref = pyku.resources.get_test_data('hyras')\\
              ...:      .pyku.to_cmor_units()\\
              ...:      .pyku.set_time_labels_from_time_bounds(how='lower')\\
              ...:      .pyku.project('HYR-LAEA-50')\\
              ...:      .sel(time='1981')\\
              ...:      .compute()
              ...:
              ...: # Open model data and preprocess as needed
              ...: # ----------------------------------------
              ...:
              ...: ds = pyku.resources.get_test_data('model_data')\\
              ...:      .pyku.project('HYR-LAEA-50')\\
              ...:      .pyku.set_time_labels_from_time_bounds(how='lower')\\
              ...:      .sel(time='1981')\\
              ...:      .compute()
              ...:
              ...: # Calculate and plot
              ...: # ------------------
              ...:
              ...: ds.ana.monthly_bias(ref, var='tas')
    """

    import calendar
    import pyku.timekit as timekit

    if dat_mod is None or dat_obs is None:
        raise ValueError("Input shall no be None")

    # Sanity checks
    # -------------

    if dat_mod.time.size == 0:
        raise ValueError(
            "dat_mod contains no time steps (dimension is empty)."
        )

    if dat_obs.time.size == 0:
        raise ValueError(
            "dat_obs contains no time steps (dimension is empty)."
        )

    # Get xr.DataArray
    # ----------------

    da_mod = _get_DataArrays(dat_mod, var=var)[0]
    da_obs = _get_DataArrays(dat_obs, var=var)[0]

    # Clear figure
    # ------------

    if ax is None:
        plt.clf()
    else:
        plt.sca(ax)

    # Set default figure size
    # -----------------------

    if kwargs.get('size_inches') is None:
        kwargs['size_inches'] = (10, 7)

    # Select common datetimes
    # -----------------------

    inter_mod, inter_obs = timekit.select_common_datetimes(da_mod, da_obs)

    # Sanity check
    # ------------

    if inter_mod.time.size == 0 or inter_obs.time.size == 0:
        raise ValueError(
            "The intersection of the datasets resulted in an empty time "
            f"dimension. \n {da_mod.time=} \n{da_obs.time=}"
        )

    # Calculate bias
    # --------------

    bias_da = (inter_mod-inter_obs)

    bias_df = \
        bias_da.groupby('time.month').mean(tuple(bias_da.dims)).to_dataframe()

    # Select column
    # -------------

    bias_df = bias_df[[da_mod.name]]

    # Plot
    # ----

    positives = bias_df[bias_df >= 0]
    negatives = bias_df[bias_df < 0]

    positives.plot.bar(color='red', legend=None, ax=plt.gca())
    negatives.plot.bar(color='blue', legend=None, ax=plt.gca())

    # Get current axis and set label
    # ------------------------------

    ax = plt.gca()
    ax.set_ylabel(f"Mean bias for {da_mod.name}")

    # Get the month numbers from the index and convert to list of month name
    # ----------------------------------------------------------------------

    month_numbers = bias_df.index.to_numpy()
    month_names_list = [calendar.month_name[i] for i in month_numbers]

    # Set tick label with month names and rotate by 45 degrees
    # --------------------------------------------------------

    ax.set_xticklabels(month_names_list)

    # Rotate xticks by 45 degrees
    # ---------------------------

    plt.xticks(rotation=45)
    ax.set_xlabel(None)

    # Pass any extra arguments that can be passed to gca
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gca()).keys())
    )
    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gca(), **extra_kwargs)

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)


def mean_bias_map(*dats, ref, var=None, crs=None, **kwargs):

    """
    Map of the mean bias

    Arguments:
        dats (:class:`xarray.Dataset`, List[:class:`xarray.Dataset`]):
            The input model dataset(s)
        ref (:class:`xarray.Dataset`): The Reference/Observation data
        var (str): The variable name
        crs (:class:`cartopy.crs.CRS`, :class:`pyresample.geometry.AreaDefinition`, str):
            Optional. The plot coordinate reference system.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to
            :func:`matplotlib.pyplot.pcolormesh`,
            :func:`matplotlib.pyplot.axes` :func:`matplotlib.pyplot.figure`, or
            :func:`cartopy.mpl.gridliner.gridlines`. For example, ``cmap``,
            ``vmin``, ``vmax``, or ``size_inches`` can be passed.

    Notes:
        If an argument is passed which is not recognized, no error message is
        thrown and the argument is ignored.

    Example:

        .. ipython::
           :okwarning:

           @savefig mean_bias_map.png width=4in
           In [0]: %%time
              ...: import pyku
              ...:
              ...: # Open reference dataset and preprocess as needed
              ...: # -----------------------------------------------
              ...:
              ...: ref = pyku.resources.get_test_data('hyras')\\
              ...:       .pyku.project('HYR-LAEA-50')\\
              ...:       .sel(time='1981')\\
              ...:       .compute()
              ...:
              ...: # Open model dataset and preprocess as needed
              ...: # -------------------------------------------
              ...:
              ...: ds = pyku.resources.get_test_data('model_data')\\
              ...:      .pyku.project('HYR-LAEA-50')\\
              ...:      .sel(time='1981')\\
              ...:      .compute()
              ...:
              ...: # Calculate and plot
              ...: # ------------------
              ...:
              ...: ds.ana.mean_bias_map(dats=ds, ref=ref, var='tas', crs='HYR-LAEA-5')
    """  # noqa

    # Set default diverging color map
    # -------------------------------

    if kwargs.get('cmap') is None:
        kwargs['cmap'] = 'bwr'

    # Get xr.DataArrays
    # -----------------

    das = _get_DataArrays(dats, var=var)
    da_ref = _get_DataArrays(ref, var=var)[0]

    # Calculate bias
    # --------------

    das_bias = []

    for da in das:

        da = _unchunk_along_time(da)
        da_ref = _unchunk_along_time(da_ref)

        # Calculate bias
        # --------------

        bias = (da - da_ref).mean('time', keep_attrs=True)

        # set attributes
        # --------------

        bias.attrs = da.attrs
        bias.attrs['long_name'] = 'bias'

        das_bias.append(bias)

    # Set vmin and vmax automatically if not specified
    # ------------------------------------------------

    if kwargs.get('vmin') is None and kwargs.get('vmax') is None:

        min_val = float(das_bias[-1].compute().quantile(0.02).values)
        max_val = float(das_bias[-1].compute().quantile(0.98).values)

        kwargs['vmin'] = -max(abs(min_val), abs(max_val))
        kwargs['vmax'] = max(abs(min_val), abs(max_val))

    # Plot
    # ----

    n_maps(*das_bias, crs=crs, **kwargs)


def seasonal_mean_bias_map(dats, ref, var=None, crs=None, **kwargs):

    """
    Map of the mean bias

    Arguments:
        dats (:class:`xarray.Dataset`): The input model dataset
        ref (:class:`xarray.Dataset`): The Reference/Observation data
        var (str): The variable name
        crs (:class:`cartopy.crs.CRS`, :class:`pyresample.geometry.AreaDefinition`, str):
            Optional. The plot coordinate reference system.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to
            :func:`matplotlib.pyplot.pcolormesh`,
            :func:`matplotlib.pyplot.axes` :func:`matplotlib.pyplot.figure`, or
            :func:`cartopy.mpl.gridliner.gridlines`. For example, ``cmap``,
            ``vmin``, ``vmax``, or ``size_inches`` can be passed.

    Notes:
        If an argument is passed which is not recognized, no error message is
        thrown and the argument is ignored.

    Example:

        .. ipython::
           :okwarning:

           @savefig seasonal_mean_bias_map.png width=4in
           In [0]: import pyku
              ...:
              ...: # Open reference dataset and preprocess as needed
              ...: # -----------------------------------------------
              ...:
              ...: ref = (
              ...:     pyku.resources.get_test_data('hyras')
              ...:     .pyku.project('HYR-LAEA-50')
              ...:     .sel(time='1981')
              ...:     .compute()
              ...: )
              ...:
              ...: # Open model dataset and preprocess as needed
              ...: # -------------------------------------------
              ...:
              ...: ds = (
              ...:     pyku.resources.get_test_data('model_data')
              ...:     .pyku.project('HYR-LAEA-50')
              ...:     .sel(time='1981')
              ...:     .compute()
              ...: )
              ...:
              ...: # Calculate and plot
              ...: # ------------------
              ...:
              ...: ds.ana.seasonal_mean_bias_map(
              ...:     ref=ref,
              ...:     var='tas',
              ...:     crs='HYR-LAEA-50'
              ...: )
    """  # noqa

    # Set default diverging color map
    # -------------------------------

    if kwargs.get('cmap') is None:
        kwargs['cmap'] = 'bwr'

    # Get xr.DataArrays
    # -----------------

    das = _get_DataArrays(dats, var=var)[0]
    da_ref = _get_DataArrays(ref, var=var)[0]

    grp_mod = das.groupby('time.season')
    grp_obs = da_ref.groupby('time.season')

    # Calculate bias
    # --------------

    das_bias = []
    seasons = grp_mod.groups.keys()

    for key in seasons:

        da = _unchunk_along_time(grp_mod[key])
        da_ref = _unchunk_along_time(grp_obs[key])

        # Calculate bias
        # --------------

        bias = (da - da_ref).mean('time', keep_attrs=True)

        # set attributes
        # --------------

        bias.attrs = da.attrs
        bias.attrs['long_name'] = 'bias'
        bias.attrs['label'] = key

        das_bias.append(bias)

    # Set vmin and vmax automatically if not specified
    # ------------------------------------------------

    if kwargs.get('vmin') is None and kwargs.get('vmax') is None:

        min_val = float(das_bias[-1].compute().quantile(0.02).values)
        max_val = float(das_bias[-1].compute().quantile(0.98).values)

        kwargs['vmin'] = -max(abs(min_val), abs(max_val))
        kwargs['vmax'] = max(abs(min_val), abs(max_val))

    # Plot
    # ----

    n_maps(*das_bias, crs=crs, **kwargs, nrows=2, ncols=2)


def daily_mean(*dats, var=None, ax=None, **kwargs):

    """
    Daily mean

    Arguments:
        dats (:class:`xarray.Dataset`): The input dataset(s)
        var (str): The variable name.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to :func:`matplotlib.pyplot.figure`
            or :func:`matplotlib.pyplot.axes`. In particular ``ylim=(0,15)``,
            ``size_inches=(20, 40))``, or ``yscale='log'`` can be passed.

    Example:

        .. ipython::

           @savefig daily_mean.png width=4in
           In [0]: %%time
              ...: import pyku
              ...: ds = pyku.resources.get_test_data('hyras_tas').compute()
              ...: ds.ana.daily_mean(var='tas')
    """

    import itertools

    # Clear figure
    # ------------

    if ax is None:
        plt.clf()
    else:
        plt.sca(ax)

    # Set default figure size
    # -----------------------

    if kwargs.get('size_inches') is None:
        kwargs['size_inches'] = (10, 5)

    # Convert to DataArrays
    # ---------------------

    das = _get_DataArrays(dats, var=var)

    # Define cycles
    # -------------

    linestyles = itertools.cycle(["-", ":", "--", "-.",])
    markers = itertools.cycle(["s", "o", "D", "v", "^",])
    fillstyles = itertools.cycle(["none", "full", "left"])
    colors = itertools.cycle(['black', 'blue', 'red', 'orange', 'green'])

    # Loop over data and plot
    # -----------------------

    for idx, da in enumerate(das):

        p = da.groupby('time.dayofyear').mean(
            dim=tuple(da.dims),
            keep_attrs=True
        )

        p.plot.line(
            add_legend=True,
            label=da.attrs.get('label', f'Dataset {idx}'),
            color=next(colors),
            linewidth=0.75,
            linestyle=next(linestyles),
            fillstyle=next(fillstyles),
            marker=next(markers),
        )

    # Set labels from first DataArray in the loop above
    # -------------------------------------------------

    ylabel = ''

    if var is not None:
        ylabel = f'{var}'

    if das[0].attrs.get('standard_name') is not None:
        ylabel = das[0].attrs.get('standard_name')

    if das[0].attrs.get('long_name') is not None:
        ylabel = das[0].attrs.get('long_name')

    if das[0].attrs.get('units') is not None:
        ylabel = f"{ylabel} [{das[0].attrs.get('units')}]"

    plt.ylabel(ylabel)

    # Pass any extra arguments that can be passed to gca
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gca()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gca(), **extra_kwargs)

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)

    plt.legend(loc='best', ncol=1, shadow=True, fancybox=True)


def monthly_mean(*dats, var=None, **kwargs):

    """
    Monthly mean

    Arguments:
        dats (Union[:class:`xarray.Dataset`, List[:class:`xarray.Dataset`]]):
            The input dataset(s)
        var (str): The variable name.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to :func:`matplotlib.pyplot.figure`
            or :func:`matplotlib.pyplot.axes`. In particular ``ylim=(0,15)``,
            ``size_inches=(20, 40))``, or ``yscale='log'`` can be passed.

    Example:

        .. ipython::

           @savefig monthly_mean.png width=4in
           In [0]: %%time
              ...: import pyku
              ...: ds = pyku.resources.get_test_data('hyras_tas')
              ...: ds.ana.monthly_mean(var='tas')
    """

    import calendar
    import itertools
    import pyku.meta as meta
    import xarray as xr

    # Keep attrs throuh operations
    # ----------------------------

    xr.set_options(keep_attrs=True)

    # Clear figure
    # ------------

    plt.clf()

    # Set default figure size
    # -----------------------

    if kwargs.get('size_inches') is None:
        kwargs['size_inches'] = (12, 5)

    # Get xr.DataArrays
    # -----------------

    das = _get_DataArrays(dats, var=var)

    # Define cycles
    # -------------

    linestyles = itertools.cycle(["-", ":", "--", "-.",])
    markers = itertools.cycle(["s", "o", "D", "v", "^",])
    fillstyles = itertools.cycle(["none", "full", "left"])
    colors = itertools.cycle(['black', 'blue', 'red', 'orange', 'green'])

    for idx, da in enumerate(das):

        y_varname, x_varname = meta.get_projection_yx_varnames(da)

        # Applying the mean over dim=('time', 'y', and 'x') at the same time
        # seems to result in all data beeing loaded into memory. Since the mean
        # is a linear operation, it should in my opinion not be the case. Hence
        # the mean is calculated over all dimensions one after the other.

        p_mod = da.groupby('time.month').mean(dim='time')\
                  .mean(dim=[x_varname, y_varname])

        if 'height' in p_mod.dims:
            # I do not think this case occurs, better safe with an exception
            raise Exception('height nor implemented in monthly_mean')

        p_mod.plot.line(
            add_legend=True,
            label=da.attrs.get('label', f'Dataset {idx}'),
            color=next(colors),
            linewidth=0.75,
            linestyle=next(linestyles),
            fillstyle=next(fillstyles),
            marker=next(markers),
        )

    # Set the x ticks and labels
    # --------------------------

    plt.gca().set_xticks(ticks=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
    plt.gca().set_xticklabels(list(calendar.month_name[1:]))
    plt.gca().tick_params(axis='x', which='both', length=0)
    plt.xticks(rotation=45)
    plt.gca().set_xlabel(None)

    # Set labels from first DataArray in the loop above
    # -------------------------------------------------

    ylabel = ''

    if var is not None:
        ylabel = f'{var}'

    if das[0].attrs.get('standard_name') is not None:
        ylabel = das[0].attrs.get('standard_name')

    if das[0].attrs.get('long_name') is not None:
        ylabel = das[0].attrs.get('long_name')

    if das[0].attrs.get('units') is not None:
        ylabel = f"{ylabel} [{das[0].attrs.get('units')}]"

    plt.ylabel(ylabel)

    # Set legend
    # ----------

    plt.legend(loc='best', ncol=1, shadow=True, fancybox=True)

    # Pass any extra arguments that can be passed to gca
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gca()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gca(), **extra_kwargs)

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)


def diurnal_cycle(*dats, var=None, ax=None, **kwargs):

    """
    Diurnal cycle

    Arguments:
        dats ([:class:`xarray.Dataset`, List[:class:`xarray.Dataset`]]):
            The input dataset(s)
        var (str): The variable name.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to :func:`matplotlib.pyplot.figure`
            or :func:`matplotlib.pyplot.axes`. In particular ``ylim=(0,15)``,
            ``size_inches=(20, 40))``, or ``yscale='log'`` can be passed.

    Example:

        .. ipython::

           @savefig diurnal_cycle.png width=4in
           In [0]: %%time
              ...: import pyku
              ...: ds = pyku.resources.get_test_data('hourly-tas').compute()
              ...: ds.ana.diurnal_cycle(var='tas')
    """

    import matplotlib
    import numpy as np
    import itertools

    # Clear figure
    # ------------

    if ax is None:
        plt.clf()
    else:
        plt.sca(ax)

    # Set default figure size
    # -----------------------

    if kwargs.get('size_inches') is None:
        kwargs['size_inches'] = (7, 5)

    # Convert to DataArrays
    # ---------------------

    das = _get_DataArrays(dats, var=var)

    # Define cycles
    # -------------

    linestyles = itertools.cycle(["-", ":", "--", "-.",])
    markers = itertools.cycle(["s", "o", "D", "v", "^",])
    fillstyles = itertools.cycle(["none", "full", "left"])
    colors = itertools.cycle(['black', 'blue', 'red', 'orange', 'green'])

    # Loop over data and plot
    # -----------------------

    for idx, da in enumerate(das):

        p = da.groupby('time.hour').mean(dim=tuple(da.dims), keep_attrs=True)

        p.plot.line(
            add_legend=True,
            label=da.attrs.get('label', f'Dataset {idx}'),
            color=next(colors),
            linewidth=0.75,
            linestyle=next(linestyles),
            fillstyle=next(fillstyles),
            marker=next(markers),
        )

    # Set the x ticks and labels
    # --------------------------

    plt.gca().set_xticks(ticks=list(np.arange(0, 24)))
    plt.gca().set_xticklabels(list(np.arange(0, 24)))
    plt.gca().tick_params(axis='x', which='both', length=0)
    plt.xticks(rotation=0)
    plt.gca().set_xlabel(None)

    # Set labels from first DataArray in the loop above
    # -------------------------------------------------

    ylabel = ''

    if var is not None:
        ylabel = f'{var}'

    if das[0].attrs.get('standard_name') is not None:
        ylabel = das[0].attrs.get('standard_name')

    if das[0].attrs.get('long_name') is not None:
        ylabel = das[0].attrs.get('long_name')

    if das[0].attrs.get('units') is not None:
        ylabel = f"{ylabel} [{das[0].attrs.get('units')}]"

    plt.ylabel(ylabel)

    # Set legend
    # ----------

    plt.legend(loc='best', ncol=1, shadow=True, fancybox=True)

    # Pass any extra arguments that can be passed to gca
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gca()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gca(), **extra_kwargs)

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)


def monthly_diurnal_cycle(dat1, dat2=None, var=None, ax=None, **kwargs):

    """
    Diurnal cycle mean for each month

    Arguments:
        ds_mod (:class:`xarray.Dataset`): The input dataset.
        ds_obs (:class:`xarray.Dataset`): Optional. The second dataset.
        var (str): variable name

    Other Parameters:
        **kwargs:
            Any argument that can be passed to :func:`matplotlib.pyplot.figure`
            or :func:`matplotlib.pyplot.axes`. In particular ``ylim=(0,15)``,
            ``size_inches=(20, 40))``, or ``yscale='log'`` can be passed.

    Example:

        .. ipython::

           @savefig monthly_diurnal_cycle.png width=4in
           In [0]: %%time
              ...: import pyku
              ...: ds = pyku.resources.get_test_data('low-res-hourly-tas-data')
              ...: ds = ds.compute()
              ...: ds.ana.monthly_diurnal_cycle(var='RR')
    """

    import calendar

    # Set default figure size
    # -----------------------

    if kwargs.get('size_inches') is None:
        kwargs['size_inches'] = (30, 20)

    # Get DataArrays
    # --------------

    da1 = _get_DataArrays(dat1, var=var)[0]

    if dat2 is not None:
        da2 = _get_DataArrays(dat2, var=var)[0]
    else:
        da2 = None

    # Group by month
    # --------------

    grp_mod = da1.groupby('time.month')

    if da2 is not None:
        grp_obs = da2.groupby('time.month')

    fig, axs = plt.subplots(3, 4)

    # Plot
    # ----

    if da2 is not None:

        for idx, (el_mod, el_obs) in enumerate(zip(grp_mod, grp_obs)):

            cax = axs.reshape(-1)[idx]

            key = el_mod[0]
            sel_mod = el_mod[1]
            sel_obs = el_obs[1]

            diurnal_cycle(sel_mod, sel_obs, var=var, ax=cax, **kwargs)
            cax.set_title(f'{calendar.month_name[key]}')

    else:

        for idx, el_mod in enumerate(grp_mod):

            cax = axs.reshape(-1)[idx]

            key = el_mod[0]
            sel_mod = el_mod[1]

            diurnal_cycle(sel_mod, dat2=None, var=var, ax=cax, **kwargs)
            cax.set_title(f'{calendar.month_name[key]}')

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)


def seasonal_diurnal_cycle(dat1, dat2=None, var=None, ax=None, **kwargs):

    """
    Diurnal cycle for each seasons

    Arguments:
        ds_mod (:class:`xarray.Dataset`): Model data
        ds_obs (:class:`xarray.Dataset`): Reference data
        var (str): The variable name.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to :func:`matplotlib.pyplot.figure`
            or :func:`matplotlib.pyplot.axes`. In particular ``ylim=(0,15)``,
            ``size_inches=(20, 40))``, or ``yscale='log'`` can be passed.

    Examples:

        .. ipython::

           @savefig seasonal_diurnal_cycle.png width=4in
           In [0]: %%time
              ...: import pyku
              ...: ds = pyku.resources.get_test_data('low-res-hourly-tas-data')
              ...: ds.ana.seasonal_diurnal_cycle(var='RR')
    """

    # Set default figure size
    # -----------------------

    if kwargs.get('size_inches') is None:
        kwargs['size_inches'] = (15, 10)

    # Get DataArrays
    # --------------

    da1 = _get_DataArrays(dat1, var=var)[0]

    if dat2 is not None:
        da2 = _get_DataArrays(dat2, var=var)[0]
    else:
        da2 = None

    # Group by seasons
    # ----------------

    grp_mod = da1.groupby('time.season')

    if da2 is not None:
        grp_obs = da2.groupby('time.season')

    fig, axs = plt.subplots(2, 2)

    if dat2 is not None:

        for idx, (el_mod, el_obs) in enumerate(zip(grp_mod, grp_obs)):

            cax = axs.reshape(-1)[idx]
            key = el_mod[0]
            sel_mod = el_mod[1]
            sel_obs = el_obs[1]

            diurnal_cycle(sel_mod, sel_obs, var=var, ax=cax, **kwargs)
            cax.set_title(f'{key}')

    else:

        for idx, el_mod in enumerate(grp_mod):

            cax = axs.reshape(-1)[idx]
            key = el_mod[0]
            sel_mod = el_mod[1]

            diurnal_cycle(sel_mod, dat2=None, var=var, ax=cax, **kwargs)
            cax.set_title(f'{key}')

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)


def monthly_variability(dat1, dat2=None, var=None, ax=None, **kwargs):

    """
    Monthly variability

    Arguments:
        dat1 (:class:`xarray.Dataset`): The first dataset.
        dat2 (:class:`xarray.Dataset`): Optional. The second dataset.
        var (str): The variable name.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to :func:`matplotlib.pyplot.figure`
            or :func:`matplotlib.pyplot.axes`. In particular ``ylim=(0,15)``,
            ``size_inches=(20, 40))``, or ``yscale='log'`` can be passed.

    Example:

        .. ipython::

           @savefig monthly_variability.png width=4in
           In [0]: import pyku
              ...: ds = pyku.resources.get_test_data('hyras_tas').compute()
              ...: ds.ana.monthly_variability(var='tas', size_inches=(8, 6))
    """

    import matplotlib.patches as mpatches
    import numpy as np
    import calendar

    # Clear figure
    # ------------

    if ax is None:
        plt.clf()
    else:
        plt.sca(ax)

    # Set default figure size
    # -----------------------

    if kwargs.get('size_inches') is None:
        kwargs['size_inches'] = (12, 5)

    da_mod = _get_DataArrays(dat1, var=var)[0]

    if dat2 is not None:
        da_obs = _get_DataArrays(dat2, var=var)[0]
    else:
        da_obs = None

    patches = []

    # Plot
    # ----

    # The dimensions are listed and the time dimension removed in order to
    # perform the mean on all dimensions but the time. The data are grouped by
    # month with ``groupby`` and the month number can be accessed with
    # ``.groups.keys()``. Type conversion to numpy array is performed with
    # np.asarray(list(GroupBy.groups.keys()))

    dims_mod = list(da_mod.dims)
    dims_mod.remove('time')

    group_mod = da_mod.groupby('time.month')
    ts_mod = group_mod.mean(dims_mod, keep_attrs=True).to_dataframe()

    patches.append(mpatches.Patch(
        color='blue',
        label=da_mod.attrs.get('label'),
    ))

    ax1 = ts_mod.groupby(lambda x: x.strftime("%m"))[[da_mod.name]].boxplot(
        subplots=False,
        rot=90,
        color='blue',
        flierprops={'markeredgecolor': 'blue'},
        positions=np.asarray(list(group_mod.groups.keys()))-0.25,
        widths=0.25
    )

    if da_obs is not None:  # and var in list(ds_obs.data_vars):

        dims_obs = list(da_obs.dims)
        dims_obs.remove('time')

        group_obs = da_obs.groupby('time.month')
        ts_obs = da_obs.groupby('time.month')\
                       .mean(dims_obs, keep_attrs=True)\
                       .to_dataframe()

        patches.append(mpatches.Patch(
            color='black',
            label=da_obs.attrs.get('label')
        ))

        ts_obs.groupby(
            lambda x: x.strftime("%m"))[[da_obs.name]].boxplot(
            subplots=False,
            rot=90,
            ax=ax1,
            color='black',
            flierprops={'markeredgecolor': 'black'},
            positions=np.asarray(list(group_obs.groups.keys()))+0.25,
            widths=0.25,
        )

    # Set the label
    # -------------

    ylabel = ''

    if var is not None:
        ylabel = f'{var}'

    if da_mod.attrs.get('standard_name') is not None:
        ylabel = da_mod.attrs.get('standard_name')

    if da_mod.attrs.get('long_name') is not None:
        ylabel = da_mod.attrs.get('long_name')

    if da_mod.attrs.get('units') is not None:
        ylabel = f"{ylabel} [{da_mod.attrs.get('units')}]"

    plt.ylabel(ylabel)

    # Set grid and ticks
    # ------------------

    ax1.grid(False)
    ax1.set_xticks(ticks=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12])
    ax1.set_xticklabels(list(calendar.month_name[1:]))
    ax1.tick_params(axis='x', which='both', length=0)

    plt.legend(handles=patches)
    plt.xticks(rotation=45)

    # Pass any extra arguments that can be passed to gca
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gca()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gca(), **extra_kwargs)

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)


def diurnal_cycle_variability(dat1, dat2=None, var=None, ax=None, **kwargs):

    """
    Diurnal cycle variability

    Arguments:
        dat1 (:class:`xarray.Dataset`): The first dataset.
        dat2 (:class:`xarray.Dataset`): Optional. The second dataset.
        var (str): The variable name.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to :func:`matplotlib.pyplot.figure`
            or func:`matplotlib.pyplot.axes`. In particular ``ylim=(0,15)``,
            ``size_inches=(20, 40))``, or ``yscale='log'`` can be passed.

    Example:

        .. ipython::
           :okwarning:

           @savefig diurnal_cycle_variability.png width=4in
           In [0]: %%time
              ...: import pyku
              ...: ds = pyku.resources.get_test_data('hourly-tas')
              ...: ds.ana.diurnal_cycle_variability(var='tas', ylim=(-20, 20))
    """

    import matplotlib.patches as mpatches
    import numpy as np

    # Clear figure
    # ------------

    if ax is None:
        plt.clf()
    else:
        plt.sca(ax)

    # Set figure size
    # ---------------

    if kwargs.get('size_inches') is None:
        kwargs['size_inches'] = (8, 6)

    # Get DataArray
    # -------------

    # Set behaviour depending on input type (DataArray or a Dataset)
    # --------------------------------------------------------------

    da_mod = _get_DataArrays(dat1, var=var)[0]

    if dat2 is not None:
        da_obs = _get_DataArrays(dat2, var=var)[0]
    else:
        da_obs = None

    patches = []

    # Plot
    # ----

    # The dimensions are listed and the time dimension removed in order to
    # perform the mean on all dimensions but the time. The data are grouped by
    # month with ``groupby`` and the month number can be accessed with
    # ``.groups.keys()``. Type conversion to numpy array is performed with
    # np.asarray(list(GroupBy.groups.keys()))

    dims_mod = list(da_mod.dims)
    dims_mod.remove('time')

    group_mod = da_mod.groupby('time.hour')
    ts_mod = group_mod.mean(dims_mod, keep_attrs=True).to_dataframe()

    patches.append(mpatches.Patch(
        color='blue',
        label="Dataset",
    ))

    ax1 = ts_mod.groupby(lambda x: x.strftime("%H"))[[da_mod.name]].boxplot(
        subplots=False,
        rot=90,
        color='blue',
        flierprops={'markeredgecolor': 'blue'},
        positions=np.asarray(list(group_mod.groups.keys()))-0.25,
        widths=0.25
    )

    if da_obs is not None:

        dims_obs = list(da_obs.dims)
        dims_obs.remove('time')

        group_obs = da_obs.groupby('time.hour')
        ts_obs = group_obs.mean(dims_obs, keep_attrs=True).to_dataframe()

        patches.append(mpatches.Patch(
            color='black',
            label="Reference"
        ))

        ax2 = \
            ts_obs.groupby(lambda x: x.strftime("%H"))[[da_obs.name]].boxplot(  # noqa
                subplots=False,
                rot=90,
                ax=ax1,
                color='black',
                flierprops={'markeredgecolor': 'black'},
                positions=np.asarray(list(group_obs.groups.keys()))+0.25,
                widths=0.25,
            )

    # Set the label
    # -------------

    if 'long_name' in da_mod.attrs.keys() and 'units' in da_mod.attrs.keys():
        ax1.set_ylabel(
            f"{da_mod.attrs['long_name']} ({da_mod.attrs['units']})"
        )

    ax1.grid(False)
    ax1.set_xticks(ticks=list(range(0, 24)))
    ax1.set_xticklabels(list(range(0, 24)))
    ax1.tick_params(axis='x', which='both', length=0)

    plt.legend(handles=patches)
    plt.xticks(rotation=0)

    # Pass any extra arguments that can be passed to gca
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gca()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gca(), **extra_kwargs)

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}


def regional_monthly_variability(ds1, ds2, gdf=None, var=None, **kwargs):

    """
    Monthly variability

    Arguments:
        ds1 (:class:`xarray.Dataset`): The first dataset.
        ds2 (:class:`xarray.Dataset`): The second dataset.
        gdf (:class:`geopandas.GeoDataFrame`): The polygon data.
        var (str): The variable name.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to :func:`matplotlib.pyplot.figure`
            or :func:`matplotlib.pyplot.axes`. In particular ``ylim=(0,15)``,
            ``size_inches=(20, 40))``, or ``yscale='log'`` can be passed.

    Examples:

        .. ipython::

           @savefig regional_monthly_variability.png width=4in
           In [0]: import xarray as xr
              ...: import pyku
              ...: import pyku.analyse as analyse
              ...:
              ...: # Open and preprocess test data as needed
              ...: # ---------------------------------------
              ...:
              ...: ds1 = (
              ...:     pyku.resources.get_test_data('hyras')
              ...:     .pyku.to_cmor_varnames()
              ...:     .pyku.to_cmor_units()
              ...: )
              ...:
              ...: ds2 = pyku.resources.get_test_data('cordex_data')
              ...:
              ...: # Get a subset ot the natrual areas or germany
              ...: # --------------------------------------------
              ...:
              ...: regions = (
              ...:     pyku.resources
              ...:     .get_geodataframe('natural_areas_of_germany')
              ...:    .head(3)
              ...:  )
              ...:
              ...: # Calculate and plot
              ...: # ------------------
              ...:
              ...: analyse.regional_monthly_variability(
              ...:     ds1,
              ...:     ds2,
              ...:     gdf=regions,
              ...:     var='tas'
              ...: )
    """

    import pyku.features as features

    # Raise exceptions
    # ----------------

    if gdf is None:
        raise Exception("Parameter 'gdf' is mandatory")

    # Group data by regions
    # ---------------------

    grp_ds1 = features.regionalize(ds1, gdf)

    if ds2 is not None:
        grp_ds2 = features.regionalize(ds2, gdf)
    else:
        grp_ds2 = None

    # Determine the number of regions
    # -------------------------------

    number_of_regions = len(grp_ds1.region)
    number_of_rows = number_of_regions//3 + 1

    # Set default figure size
    # -----------------------

    if kwargs.get('size_inches') is None:
        kwargs['size_inches'] = (20, number_of_rows*7)

    # Lower column case (to make column case insensitive)
    # ---------------------------------------------------

    gdf.columns = [c.lower() for c in gdf.columns]

    # Lower column case (to make column case insensitive)
    # ---------------------------------------------------

    fig, axs = plt.subplots(number_of_rows, 3)

    # Set plot visibility to False by default
    # ---------------------------------------

    # The total number of plots (nrows x ncolumns) may exceed the number of
    # regions.  All plots are initially hidden by default and made visible
    # later when plotting each region using set_visible(True).

    for idx, cax in enumerate(axs.reshape(-1)):
        cax.set_visible(False)

    for idx, region in enumerate(grp_ds1.region):

        cax = axs.reshape(-1)[idx]
        cax.set_visible(True)

        if grp_ds2 is None:
            monthly_variability(
                grp_ds1.sel(region=region),
                None,
                var=var,
                ax=cax
            )
        else:
            monthly_variability(
                grp_ds1.sel(region=region),
                grp_ds2.sel(region=region),
                var=var,
                ax=cax
            )

        if 'name' in gdf.columns:
            cax.set_title(f'{region.values}')
        elif 'short_name' in gdf.columns:
            cax.set_title(f'{gdf.short_name[idx]}')
        else:
            cax.set_title(f'{idx}')

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)


def regional_monthly_bias(ds_mod, ds_obs, gdf, area_def, var=None, **kwargs):

    """
    Monthly variability

    Todo:

        * Check if this function is working
        * Get the ipython code right
        * Check documentation is right. I think area_def can be passed as
          cartopy crs?

    Arguments:
        ds_mod (:class:`xarray.Dataset`): The first input dataset.
        ds_obs (:class:`xarray.Dataset`): The second input dataset.
        gdf (:class:`geopandas.GeoDataFrame`): The polygon data.
        var (str): variable name
        area_def (:class:`pyresample.geometry.AreaDefinition`): Optional.
            The plot coordinate reference system.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to :func:`matplotlib.pyplot.figure`
            or :func:`matplotlib.pyplot.axes`. In particular ``ylim=(0,15)``,
            ``size_inches=(20, 40))``, or ``yscale='log'`` can be passed.

    Examples:

        .. ipython::
           :okwarning:

           @savefig regional_monthly_bias.png width=4in
           In [0]: %%time
              ...: import pyku
              ...:
              ...: # Open reference data and preprocess as needed
              ...: # --------------------------------------------
              ...:
              ...: ref = (
              ...:     pyku.resources.get_test_data('hyras')
              ...:     .pyku.to_cmor_units()
              ...:     .pyku.set_time_labels_from_time_bounds(how='lower')
              ...:     .pyku.project('HYR-LAEA-50')
              ...:     .sel(time='1981')
              ...:     .compute()
              ...: )
              ...:
              ...: # Open model data and preprocess as needed
              ...: # ----------------------------------------
              ...:
              ...: ds = (
              ...:     pyku.resources.get_test_data('model_data')
              ...:     .pyku.project('HYR-LAEA-50')
              ...:     .pyku.set_time_labels_from_time_bounds(how='lower')
              ...:     .sel(time='1981')
              ...:     .compute()
              ...: )
              ...:
              ...: gdf = (
              ...:     pyku.resources
              ...:     .get_geodataframe('natural_areas_of_germany')
              ...:     .loc[0:4]
              ...: )
              ...:
              ...: print('Polygons: ', gdf)
              ...:
              ...: # Calculate and plot
              ...: # ------------------
              ...:
              ...: # pyku.analyse.regional_monthly_bias(
              ...: #     ds, ref, gdf, area_def='HYR-LAEA-50', var='tas'
              ...: # )

    """

    import pyku.features as features

    # Group data by regions
    # ---------------------

    grp_mod = features.regionalize(
        ds_mod, gdf, area_def, dtype='xr.Dataset')

    grp_obs = features.regionalize(
        ds_obs, gdf, area_def, dtype='xr.Dataset')

    # Determine the number of regions
    # -------------------------------

    number_of_regions = len(grp_mod.region)
    number_of_rows = number_of_regions//3 + 1

    # Set default figure size
    # -----------------------

    if kwargs.get('size_inches') is None:
        kwargs['size_inches'] = (20, number_of_rows*7)

    # Lower column case (to make column case insensitive)
    # ---------------------------------------------------

    gdf.columns = [c.lower() for c in gdf.columns]

    # Lower column case (to make column case insensitive)
    # ---------------------------------------------------

    fig, axs = plt.subplots(number_of_rows, 3)

    # Set plot visibility to False by default
    # ---------------------------------------

    # The total number of plots (nrows x ncolumns) may exceed the number of
    # regions.  All plots are initially hidden by default and made visible
    # later when plotting each region using set_visible(True).

    for idx, cax in enumerate(axs.reshape(-1)):
        cax.set_visible(False)

    for idx, region in enumerate(grp_mod.region):

        cax = axs.reshape(-1)[idx]
        cax.set_visible(True)

        if grp_obs is None:
            monthly_bias(
                grp_mod.sel(region=region),
                None,
                var=var,
                ax=cax
            )

        else:
            monthly_bias(
                grp_mod.sel(region=region),
                grp_obs.sel(region=region),
                var=var,
                ax=cax
            )

        if 'name' in gdf.columns:
            cax.set_title(f'{region.values}')
        elif 'short_name' in gdf.columns:
            cax.set_title(f'{gdf.short_name[idx]}')
        else:
            cax.set_title(f'{idx}')

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)


def regional_mean_vs_time(ds_mod, ds_obs=None, gdf=None, time_resolution='1MS',
                          var=None, **kwargs):

    """
    Time series per region

    Arguments:
        ds_mod (:class:`xarray.Dataset`): The first input dataset.
        ds_obs (:class:`xarray.Dataset`): The second input dataset.
        gdf (:class:`geopandas.GeoDataFrame`): The polygon data.
        var (str): variable name

    Other Parameters:
        **kwargs:
            Any argument that can be passed to :func:`matplotlib.pyplot.figure`
            or :func:`matplotlib.pyplot.axes`. In particular ``ylim=(0,15)``,
            ``size_inches=(20, 40))``, or ``yscale='log'`` can be passed.

    Examples:

        .. ipython::
           :okwarning:

           @savefig regional_mean_vs_time.png width=4in
           In [0]: %%time
              ...: import xarray as xr
              ...: import pyku
              ...: import pyku.analyse as analyse
              ...:
              ...: # Open and preprocess test data as needed
              ...: # ---------------------------------------
              ...:
              ...: ds = pyku.resources.get_test_data('hyras')
              ...:
              ...: # Get a subset ot the natrual areas or germany
              ...: # --------------------------------------------
              ...:
              ...: regions = (
              ...:     pyku.resources
              ...:     .get_geodataframe('natural_areas_of_germany')
              ...:     .head(3)
              ...: )
              ...:
              ...: ds.ana.regional_mean_vs_time(
              ...:     gdf=regions,
              ...:     time_resolution='1MS',
              ...:     var='tas'
              ...: )
    """

    import pyku.features as features

    # Group data by regions
    # ---------------------

    grp_mod = features.regionalize(ds_mod, gdf, dtype='xr.Dataset')

    if ds_obs is not None:
        grp_obs = features.regionalize(ds_obs, gdf, dtype='xr.Dataset')
    else:
        grp_obs = None

    # Determine the number of regions
    # -------------------------------

    number_of_regions = len(grp_mod.region)
    number_of_cols = 2
    number_of_rows = number_of_regions//number_of_cols + 1

    # Set default figure size
    # -----------------------

    if kwargs.get('size_inches') is None:
        kwargs['size_inches'] = (20, number_of_rows*7)

    # Lower column case (to make column case insensitive)
    # ---------------------------------------------------

    gdf.columns = [c.lower() for c in gdf.columns]

    # Lower column case (to make column case insensitive)
    # ---------------------------------------------------

    fig, axs = plt.subplots(number_of_rows, number_of_cols)

    # Set plot visibility to False by default
    # ---------------------------------------

    # The total number of plots (nrows x ncolumns) may exceed the number of
    # regions.  All plots are initially hidden by default and made visible
    # later when plotting each region using set_visible(True).

    for idx, cax in enumerate(axs.reshape(-1)):
        cax.set_visible(False)

    for idx, region in enumerate(grp_mod.region):

        cax = axs.reshape(-1)[idx]
        cax.set_visible(True)

        if grp_obs is None:
            mean_vs_time(
                grp_mod.sel(region=region),
                time_resolution=time_resolution,
                var=var,
                ax=cax
            )

        else:
            mean_vs_time(
                grp_mod.sel(region=region),
                grp_obs.sel(region=region),
                time_resolution=time_resolution,
                var=var,
                ax=cax
            )

        if 'name' in gdf.columns:
            cax.set_title(f'{region.values}')
        # e.g. for prudence:
        elif 'short_name' in gdf.columns:
            cax.set_title(f'{gdf.short_name[idx]}')
        else:
            cax.set_title(f'{idx}')

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)


def time_serie(*dats, var=None, ax=None, **kwargs):

    """
    Time serie. The data are averaged over y/x and plotting against time

    Arguments:
        *dats (:class:`xarray.Dataset`, List[:class:`xarray.Dataset`]):
            The input dataset(s).
        var (str):
            The variable name.
        ax (:class:`matplotlib.pyplot.axes`):
            Optional. Matplotlib pyplot axis.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to :func:`matplotlib.pyplot.figure`
            or :func:`matplotlib.pyplot.axes`. In particular ``ylim=(0,15)``,
            ``size_inches=(20, 40))``, or ``yscale='log'`` can be passed.

    Example:

        .. ipython::

           @savefig time_serie.png width=4in
           In [0]: pyku
              ...: ds = pyku.resources.get_test_data('hyras_tas')\\
              ...: .isel(time=[0,1,2,3,4,5])
              ...: ds.ana.time_serie(var='tas')
    """

    import itertools

    # Clear figure
    # ------------

    if ax is None:
        plt.clf()
    else:
        plt.sca(ax)

    # Set default figure size
    # -----------------------

    if kwargs.get('size_inches') is None:
        kwargs['size_inches'] = (10, 5)

    # Convert to DataArrays
    # ---------------------

    das = _get_DataArrays(dats, var=var)

    # Define cycles
    # -------------

    linestyles = itertools.cycle(["-", ":", "--", "-.",])
    markers = itertools.cycle(["s", "o", "D", "v", "^",])
    fillstyles = itertools.cycle(["none", "full", "left"])
    colors = itertools.cycle(['black', 'blue', 'red', 'orange', 'green'])

    # Loop over data and plot
    # -----------------------

    for idx, da in enumerate(das):

        # Get all dimensions but time
        # ---------------------------

        dims_for_mean = [el for el in list(da.dims) if el not in ['time']]

        # Average over all dimensions but time
        # ------------------------------------

        mean_df = da.mean(dims_for_mean).to_dataframe()[[var]]

        # Plot
        # ----

        plt.plot(
            mean_df,
            label=da.attrs.get('label', f'Dataset {idx}'),
            color=next(colors),
            linewidth=0.75,
            linestyle=next(linestyles),
            fillstyle=next(fillstyles),
            marker=next(markers),
        )

    # Add legend
    # ----------

    plt.legend(loc="upper left")

    # Rotate ticks
    # ------------

    plt.xticks(rotation=45)

    # Set labels from first DataArray in the loop above
    # -------------------------------------------------

    ylabel = ''
    if das[0].attrs.get('standard_name') is not None:
        ylabel = das[0].attrs.get('standard_name')

    if das[0].attrs.get('long_name') is not None:
        ylabel = das[0].attrs.get('long_name')

    if das[0].attrs.get('units') is not None:
        ylabel = f"{ylabel} [{das[0].attrs.get('units')}]"

    plt.ylabel(ylabel)

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)

    # Pass any extra arguments that can be passed to gca
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gca()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gca(), **extra_kwargs)

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)


def mean_vs_time(*dats, var=None, time_resolution='1YS', ax=None, **kwargs):

    """
    Mean vs time

    Arguments:
        *dats (:class:`xarray.Dataset`, List[:class:`xarray.Dataset`]):
            The input dataset(s).
        time_resolution (freqstr): Time resolution (e.g. '1MS' or '6D')
        var (str): The variable name.
        ax (:class:`matplotlib.pyplot.axes`): Optional. Matplotlib pyplot axis.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to :func:`matplotlib.pyplot.figure`
            or :func:`matplotlib.pyplot.axes`. In particular ``ylim=(0,15)``,
            ``size_inches=(20, 40))``, or ``yscale='log'`` can be passed.

    Example:

        .. ipython::
           :okwarning:

           @savefig mean_vs_time_1MS.png width=4in
           In [0]: %%time
              ...: import pyku
              ...: ds = pyku.resources.get_test_data('hyras')
              ...: ds.ana.mean_vs_time(var='tas', time_resolution='1MS')
    """

    import itertools
    import pandas as pd

    # Clear figure
    # ------------

    if ax is None:
        plt.clf()
    else:
        plt.sca(ax)

    # Set default figure size
    # -----------------------

    if kwargs.get('size_inches') is None:
        kwargs['size_inches'] = (10, 5)

    # Convert to DataArrays
    # ---------------------

    das = _get_DataArrays(dats, var=var)

    # Define cycles
    # -------------

    linestyles = itertools.cycle(["-", ":", "--", "-.",])
    markers = itertools.cycle(["s", "o", "D", "v", "^",])
    fillstyles = itertools.cycle(["none", "full", "left"])
    colors = itertools.cycle(['black', 'blue', 'red', 'orange', 'green'])

    # Loop over data and plot
    # -----------------------

    for idx, da in enumerate(das):

        # Resample data
        # -------------

        resampled = da.resample(time=time_resolution)

        # Gather results into lists
        # -------------------------

        ls_dat = []
        ls_years = []

        for year, da_year in resampled:
            mean = da_year.mean(
                da.dims, skipna=True, keep_attrs=True).compute()
            ls_dat.append(mean)
            ls_years.append(year)

        # Create dataframe
        # ----------------

        ls_dat = [float(i.values) for i in ls_dat]

        timeserie = {}
        timeserie['dat'] = ls_dat
        timeserie['year'] = ls_years

        df = pd.DataFrame(timeserie).set_index("year")

        # Plot
        # ----

        plt.plot(
            df["dat"],
            label=da.attrs.get('label', f'Dataset {idx}'),
            color=next(colors),
            linewidth=0.75,
            linestyle=next(linestyles),
            fillstyle=next(fillstyles),
            marker=next(markers),
        )

    # Add legend
    # ----------

    plt.legend(loc="upper left")

    # Rotate ticks
    # ------------

    plt.xticks(rotation=45)

    # Set labels from first DataArray in the loop above
    # -------------------------------------------------

    ylabel = ''
    if das[0].attrs.get('standard_name') is not None:
        ylabel = das[0].attrs.get('standard_name')

    if das[0].attrs.get('long_name') is not None:
        ylabel = das[0].attrs.get('long_name')

    if das[0].attrs.get('units') is not None:
        ylabel = f"{ylabel} [{das[0].attrs.get('units')}]"

    plt.ylabel(ylabel)

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)

    # Pass any extra arguments that can be passed to gca
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gca()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gca(), **extra_kwargs)

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)


def var_vs_year(dat_mod, dat_obs, var=None, **kwargs):

    """
    Variability vs year

    Todo:

        * Function looks very outdated and needs to be reworked

    Arguments:
        ds_mod (:class:`xarray.Dataset`): The first dataset.
        ds_obs (:class:`xarray.Dataset`): The second dataset.
        var (str): Variable name

    Other Parameters:
        **kwargs:
            Any argument that can be passed to :func:`matplotlib.pyplot.figure`
            or :func:`matplotlib.pyplot.axes`. In particular ``ylim=(0,15)``,
            ``size_inches=(20, 40))``, or ``yscale='log'`` can be passed.

    .. Example:

    ..     .. ipython::

    ..        @savefig var_vs_year.png width=4in
    ..        In [0]: import pyku
    ..           ...: ds = pyku.resources.get_test_data('hyras')
    ..           ...: #ds.ana.var_vs_year(var='tas')
    """

    import matplotlib.patches as mpatches
    import pandas as pd
    import numpy as np
    import warnings

    warnings.warn("var_vs_year may need maintenance")

    # Clear figures
    # -------------

    plt.clf()

    # Set default figure size
    # -----------------------

    if kwargs.get('size_inches') is None:
        kwargs['size_inches'] = (40, 5)

    # Get DataArray
    # -------------

    da_mod = _get_DataArrays(dat_mod, var=var)[0]
    da_obs = _get_DataArrays(dat_obs, var=var)[0]

    if da_obs is not None:

        # Get available years from both model and reference DataSets, get
        # common values and reorder

        available_datetimes_mod = list(da_mod.coords['time'].values)
        available_datetimes_obs = list(da_obs.coords['time'].values)

        available_datetimes = set(
            available_datetimes_mod + available_datetimes_obs
        )

        available_years = [
            item.astype(dtype='datetime64[Y]') for item in
            available_datetimes
        ]

        available_years = list(set(available_years))
        available_years.sort()

    else:

        available_datetimes_mod = list(da_mod.coords['time'].values)

        available_datetimes = set(available_datetimes_mod)
        available_years = [
            item.astype(dtype='datetime64[Y]') for item in available_datetimes
        ]
        available_years = list(set(available_years))
        available_years.sort()

    kwargs['size_inches'] = (
        kwargs['size_inches'][0]*len(available_years)//10,
        kwargs['size_inches'][1]
    )

    # Average over space and convert to panda dataframe
    # -------------------------------------------------

    ts_mod = da_mod.mean(('x', 'y')).to_dataframe()
    ts_mod = ts_mod.rename(columns={da_mod.name: "mod"})  # Rename

    ts_concat = pd.concat([ts_mod], axis=1)  # case observation also available

    # Rename variables and merge along the time dimension
    # ---------------------------------------------------

    if da_obs is not None:
        ts_obs = da_obs.mean(('x', 'y')).to_dataframe()
        ts_obs = ts_obs.rename(columns={da_obs.name: "obs"})
        ts_concat = pd.concat([ts_obs, ts_mod], axis=1)

    # Get the years available in model and convert to ndarray
    # -------------------------------------------------------

    years = ts_concat['mod'].to_frame()\
                            .groupby(lambda x: x.strftime("%Y"))\
                            .groups.keys()
    years = list(years)
    years = [float(y) for y in years]
    years = np.array(years)

    # Prepare patches for the legend
    # ------------------------------

    patches = []

    # Get pandas series, convert to dataframe and group by year
    # ---------------------------------------------------------

    df_mod = ts_concat['mod'].to_frame().groupby(lambda x: x.strftime("%Y"))

    ax1 = df_mod.boxplot(
        subplots=False,
        rot=90,
        color='blue',
        flierprops={'markeredgecolor': 'blue'},
        positions=years+0.25,
        widths=0.3,
    )

    patches.append(mpatches.Patch(color='blue', label='Dataset'))

    if da_obs is not None:

        df_obs = ts_concat['obs'].to_frame()\
                                 .groupby(lambda x: x.strftime("%Y"))

        df_obs.boxplot(
            subplots=False,
            ax=ax1,
            rot=90,
            color='black',
            flierprops={'markeredgecolor': 'black'},
            positions=years-0.25,
            widths=0.3
        )

        patches.append(mpatches.Patch(color='black', label='Reference'))

    # Set label
    # ---------

    ylabel = ''

    if var is not None:
        ylabel = f'{var}'

    if da_mod.attrs.get('standard_name') is not None:
        ylabel = da_mod.attrs.get('standard_name')

    if da_mod.attrs.get('long_name') is not None:
        ylabel = da_mod.attrs.get('long_name')

    if da_mod.attrs.get('units') is not None:
        ylabel = f"{ylabel} [{da_mod.attrs.get('units')}]"

    plt.ylabel(ylabel)

    # Set ticks, ticks label, and legend
    # ----------------------------------

    ax1.set_xticks(ticks=list(years))
    ax1.set_xticklabels([str(int(y)) for y in list(years)])
    ax1.grid(False)
    plt.xticks(rotation=45)
    plt.legend(handles=patches)

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)

    # Pass any extra arguments that can be passed to gca
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gca()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gca(), **extra_kwargs)


def percentile_map(ds_mod, ds_obs, var=None, percentile=0.5, crs=None,
                   **kwargs):

    """
    Map of the nth percentile

    Todo:

        * Check if function is actually working
        * Create a documentation
        * I think the CRS should also work with
          :class:`pyresample.geometry.AreaDefinition`.

    Arguments:
        ds_mod (:class:`xarray.Dataset`): The first dataset.
        ds_obs (:class:`xarray.Dataset`): The second dataset.
        var (str): Variable name
        percentile (float): Percentile between 0 and 1
        crs (:class:`cartopy.crs.CRS`): Coordinate reference system
    """

    da_mod = _get_DataArrays(ds_mod, var=var)
    da_obs = _get_DataArrays(ds_obs, var=var)

    # Calculate quantile
    # ------------------

    p_mod = da_mod.chunk(dict(time=-1, y=10))\
                  .quantile(percentile, 'time', keep_attrs=True, skipna=False)\
                  .chunk(dict(y=-1))

    if ds_obs is not None and var in list(ds_obs.data_vars):
        p_obs = da_obs.chunk(dict(time=-1, y=10))\
                      .quantile(percentile, 'time', keep_attrs=True,
                                skipna=False)\
                      .chunk(dict(y=-1))

    # Remove the word mean from long_name if needed
    # ---------------------------------------------

    if 'long_name' in p_mod.attrs.keys():

        p_mod.attrs = {
            **p_mod.attrs,
            'long_name': p_mod.attrs['long_name'].replace('mean ', '')
        }

    if da_obs is not None and 'long_name' in p_obs.attrs.keys():
        p_obs.attrs = {
            **p_obs.attrs,
            'long_name': p_obs.attrs['long_name'].replace('mean ', '')
        }


def p98_map(*dats, var, crs=None, **kwargs):

    """
    Map of the 98th percentile

    Arguments:
        *dats ([:class:`xarray.Dataset, List[:class:`xarray.Dataset`]]):
            The input dataset(s)
        var (str): The variable name.
        crs (:class:`cartopy.crs.CRS`, :class:`pyresample.geometry.AreaDefinition`, str):
            Optional. The coordinate reference system of the plot.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to
            :func:`matplotlib.pyplot.pcolormesh`,
            :func:`matplotlib.pyplot.axes` :func:`matplotlib.pyplot.figure`, or
            :func:`cartopy.mpl.gridliner.gridlines`. For example, ``cmap``,
            ``vmin``, ``vmax``, or ``size_inches`` can be passed.

    """  # noqa

    import pyku.colormaps as colormaps

    # Set colormaps
    # -------------

    if kwargs.get('cmap') is None and var in ['pr']:
        kwargs['cmap'] = colormaps.get_cmap('precip_abs')

    # if kwargs.get('cmap') is None and var in ['tas', 'tasminx', 'tasmax']:
    #     kwargs['cmap'] = colormaps.get_cmap('temp_abs')

    # Get xr.DataArrays
    # -----------------

    das = _get_DataArrays(dats, var=var)

    das_percentile = []

    for da in das:

        # Unchunk
        # -------

        if da.chunks is not None:
            da = _unchunk_along_time(da)

        # Calculate quantile
        # ------------------

        das_percentile.append(
            da.quantile(
                0.98,
                'time',
                keep_attrs=True,
                skipna=True,
                method='closest_observation'
            ).compute()  # .copy(deep=True)
        )

    # Plot
    # ----

    n_maps(*das_percentile, crs=crs, **kwargs)


def p98_vs_time(*dats, var=None, time_resolution='1YS', ax=None, **kwargs):

    """
    98th percentile vs time

    Arguments:
        *dats ([:class:`xarray.Dataset`, List[:class:`xarray.Dataset`]]):
            The input dataset(s).
        time_resolution (str): The time resolution, e.g. '1MS' or '6D'.
        var (str): The variable name.
        ax (:class:matplotlib.pyplot.axes): Optional. Matplotlib pyplot axis.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to :func:`matplotlib.pyplot.figure`
            or :func:`matplotlib.pyplot.axes`. In particular ``ylim=(0,15)``,
            ``size_inches=(20, 40))``, or ``yscale='log'`` can be passed.

    Example:

        .. ipython::

           @savefig p98_vs_time.png width=4in
           In [0]: %%time
              ...: import pyku
              ...: ds = pyku.resources.get_test_data('hyras_tas')
              ...: ds.ana.p98_vs_time(var='tas')
    """

    import itertools
    import textwrap
    import dask
    import numpy as np
    import pandas as pd

    # Clear figure
    # ------------

    if ax is None:
        plt.clf()
    else:
        plt.sca(ax)

    # Set default figure size
    # -----------------------

    if kwargs.get('size_inches') is None:
        kwargs['size_inches'] = (10, 5)

    # Convert to DataArrays
    # ---------------------

    das = _get_DataArrays(dats, var=var)

    if len(das) == 0:
        message = textwrap.dedent(
            """ The dataset passed is and empty list.""")
        raise Exception(message)

    # Define cycles
    # -------------

    linestyles = itertools.cycle(["-", ":", "--", "-.",])
    markers = itertools.cycle(["s", "o", "D", "v", "^",])
    fillstyles = itertools.cycle(["none", "full", "left"])
    colors = itertools.cycle(['black', 'blue', 'red', 'orange', 'green'])

    # Loop over data and plot
    # -----------------------

    for idx, da in enumerate(das):

        # Resample data
        # -------------

        resampled = da.resample(time=time_resolution)

        # Gather results into lists
        # -------------------------

        ls_dat = []
        ls_years = []

        for year, da_year in resampled:

            if da_year.chunks is not None:
                chunked = _unchunk_along_time(da_year)
            else:
                chunked = da_year

            dat = chunked.data

            if isinstance(dat, np.ndarray):

                dat = dat[~np.isnan(dat)]
                quantiled = np.percentile(
                    dat.reshape(-1),
                    98
                )

            else:
                dat = dat[~dask.array.isnan(dat)]
                quantiled = dask.array.percentile(
                    dat.reshape(-1),
                    98
                ).compute()

            ls_dat.append(quantiled)
            ls_years.append(year)

        # Create dataframe
        # ----------------

        ls_dat = [float(el) for el in ls_dat]
        # ls_dat=[float(el.values) for el in ls_dat]

        timeserie = {}
        timeserie['dat'] = ls_dat
        timeserie['year'] = ls_years

        df = pd.DataFrame(timeserie).set_index("year")

        # Plot
        # ----

        plt.plot(
            df["dat"],
            label=da.attrs.get('label', f'Dataset {idx}'),
            color=next(colors),
            linewidth=0.75,
            linestyle=next(linestyles),
            fillstyle=next(fillstyles),
            marker=next(markers),
        )

    # Add legend
    # ----------

    plt.legend(loc="upper left")

    # Set labels from first dataset
    # -----------------------------

    ylabel = ''
    if das[0].attrs.get('standard_name') is not None:
        ylabel = das[0].attrs.get('standard_name')

    if das[0].attrs.get('long_name') is not None:
        ylabel = das[0].attrs.get('long_name')

    if das[0].attrs.get('units') is not None:
        ylabel = f"{ylabel} [{das[0].attrs.get('units')}]"

    plt.ylabel(ylabel)

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)

    # Pass any extra arguments that can be passed to gca
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gca()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gca(), **extra_kwargs)


def mse_map(*dats, ref, var=None, ds_ref=None, crs=None, **kwargs):

    """
    Map of the Mean Squared Error (MSE)

    Arguments:
        dats ([:class:`xarray.Dataset`, List[:class:`xarray.Dataset`]):
            The input dataset(s).
        ref (:class:`xarray.Dataset`): The reference dataset.
        var (str): The variable name.
        crs (:class:`cartopy.crs.CRS`, :class:`pyresample.geometry.AreaDefinition`, str):
            Optional. The coordinate reference system of the plot.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to
            :func:`matplotlib.pyplot.pcolormesh`,
            :func:`matplotlib.pyplot.axes` :func:`matplotlib.pyplot.figure`, or
            :func:`cartopy.mpl.gridliner.gridlines`. For example, ``cmap``,
            ``vmin``, ``vmax``, or ``size_inches`` can be passed.

    Example:

        .. ipython::
           :okwarning:

           @savefig mse_map.png width=4in
           In [0]: %%time
              ...: import pyku
              ...:
              ...: # Open reference dataset and preprocess as needed
              ...: # -----------------------------------------------
              ...:
              ...: ref = (
              ...:     pyku.resources.get_test_data('hyras')
              ...:     .pyku.to_cmor_units()
              ...:     .pyku.set_time_labels_from_time_bounds(how='lower')
              ...:     .pyku.project('HYR-GER-LAEA-5')
              ...:     .sel(time='1981')
              ...:     .compute()
              ...: )
              ...:
              ...: # Open model dataset and preprocess as needed
              ...: # -------------------------------------------
              ...:
              ...: ds = (
              ...:     pyku.resources.get_test_data('model_data')
              ...:     .pyku.project('HYR-GER-LAEA-5')
              ...:     .pyku.set_time_labels_from_time_bounds(how='lower')
              ...:     .sel(time='1981')
              ...:     .compute()
              ...: )
              ...:
              ...: # Calculate and plot
              ...: # ------------------
              ...:
              ...: ds.ana.mse_map(ref=ref, var='tas', crs='HYR-GER-LAEA-5')
    """  # noqa

    import xskillscore
    import pyku.timekit as timekit

    # Get xr.DataArrays
    # -----------------

    das = _get_DataArrays(dats, var=var)
    da_ref = _get_DataArrays(ref, var=var)[0]

    # Calculate
    # ---------

    das_mse = []

    for da in das:

        # Select common datetimes and unchunck along time
        # -----------------------------------------------

        sel_ref, sel_da = timekit.select_common_datetimes(da_ref, da)

        sel_ref = _unchunk_along_time(sel_ref)
        sel_da = _unchunk_along_time(sel_da)

        # Calculate the MSE
        # -----------------

        da_mse = xskillscore.mse(
            sel_ref,
            sel_da,
            dim='time',
            skipna=True
        )

        # Set attributes and append to list of results
        # --------------------------------------------

        da_mse.attrs = da.attrs
        da_mse.attrs['long_name'] = 'MSE'
        da_mse.attrs.pop('units', None)

        das_mse.append(da_mse)

    # Plot
    # ----

    n_maps(*das_mse, crs=crs, **kwargs)


def rmse_map(*dats, ref, var=None, crs=None, ds_ref=None, **kwargs):

    """
    Map of the Root Mean Squared Error (RMSE)

    Arguments:
        dats ([:class:`xarray.Dataset`, List[:class:`xarray.Dataset`]]):
            The input dataset(s).
        ref (:class:`xarray.Dataset`): The reference dataset.
        var (str): The variable name.
        crs (:class:`cartopy.crs.CRS`, :class:`pyresample.geometry.AreaDefinition`, str):
            Optional. The coordinate reference system of the plot.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to
            :func:`matplotlib.pyplot.pcolormesh`,
            :func:`matplotlib.pyplot.axes` :func:`matplotlib.pyplot.figure`, or
            :func:`cartopy.mpl.gridliner.gridlines`. For example, ``cmap``,
            ``vmin``, ``vmax``, or ``size_inches`` can be passed.

    Example:

        .. ipython::
           :okwarning:

           @savefig rmse_map.png width=4in
           In [0]: %%time
              ...: import pyku
              ...:
              ...: # Open reference dataset and preprocess as needed
              ...: # -----------------------------------------------
              ...:
              ...: ref = pyku.resources.get_test_data('hyras')\\
              ...:       .pyku.to_cmor_units()\\
              ...:       .pyku.set_time_labels_from_time_bounds(how='lower')\\
              ...:       .pyku.project('HYR-LAEA-50')\\
              ...:       .sel(time='1981')\\
              ...:       .load()
              ...:
              ...: # Open model dataset and preprocess as needed
              ...: # -------------------------------------------
              ...:
              ...: ds = pyku.resources.get_test_data('model_data')\\
              ...:      .pyku.project('HYR-LAEA-50')\\
              ...:      .pyku.set_time_labels_from_time_bounds(how='lower')\\
              ...:      .sel(time='1981')\\
              ...:      .load()
              ...:
              ...: # Calculate and plot
              ...: # ------------------
              ...:
              ...: ds.ana.rmse_map(ref=ref, var='tas')
    """  # noqa

    import xskillscore
    import pyku.meta as meta

    # Get xr.DataArrays
    # -----------------

    das = _get_DataArrays(dats, var=var)
    da_ref = _get_DataArrays(ref, var=var)[0]

    # Calculate
    # ---------

    das_rmse = []

    for da in das:

        # Select common datetimes and unchunk along time
        # ----------------------------------------------

        sel_ref, sel_da = meta.select_common_datetimes(da_ref, da)

        sel_ref = _unchunk_along_time(sel_ref)
        sel_da = _unchunk_along_time(sel_da)

        # Calculate the MSE
        # -----------------

        da_rmse = xskillscore.rmse(
            sel_ref,
            sel_da,
            dim='time',
            skipna=True
        )

        # Set attributes and append to list of results
        # --------------------------------------------

        da_rmse.attrs = da.attrs
        da_rmse.attrs['long_name'] = 'RMSE'
        da_rmse.attrs.pop('units', None)

        das_rmse.append(da_rmse)

    # Plot
    # ----

    n_maps(*das_rmse, crs=crs, **kwargs)


def pcc_map(*dats, ref, var=None, crs=None, **kwargs):

    """
    Map of the Pearson Correlation Coefficient (PCC)

    Arguments:
        dats ([:class:`xarray.Dataset`, List[:class:`xarray.Datasets`]]):
            The input dataset(s)
        ref (:class:`xarray.Dataset`): The reference dataset.
        var (str): Variable name
        crs (:class:`cartopy.crs.CRS`, :class:`pyresample.geometry.AreaDefinition`, str):
            Optional. The coordinate reference system of the plot.

    Other Parameters:
        **kwargs:
            Any argument that can be passed to
            :func:`matplotlib.pyplot.pcolormesh`,
            :func:`matplotlib.pyplot.axes` :func:`matplotlib.pyplot.figure`, or
            :func:`cartopy.mpl.gridliner.gridlines`. For example, ``cmap``,
            ``vmin``, ``vmax``, or ``size_inches`` can be passed.

    Example:

        .. ipython::
           :okwarning:

           @savefig pcc_map.png width=4in
           In [0]: %%time
              ...: import pyku
              ...:
              ...: # Open reference dataset and preprocess as needed
              ...: # -----------------------------------------------
              ...:
              ...: ref = (
              ...:     pyku.resources.get_test_data('hyras')
              ...:     .pyku.to_cmor_units()
              ...:     .pyku.set_time_labels_from_time_bounds(how='lower')
              ...:     .pyku.project('HYR-GER-LAEA-5')
              ...:     .sel(time='1981')
              ...:     .compute()
              ...: )
              ...:
              ...: # Open model dataset and preprocess as needed
              ...: # -------------------------------------------
              ...:
              ...: ds = (
              ...:     pyku.resources.get_test_data('model_data')
              ...:     .pyku.project('HYR-GER-LAEA-5')
              ...:     .pyku.set_time_labels_from_time_bounds(how='lower')
              ...:     .sel(time='1981')
              ...:     .compute()
              ...: )
              ...:
              ...: # Calculate and plot
              ...: # ------------------
              ...:
              ...: ds.ana.pcc_map(ref=ref, var='tas', crs='HYR-GER-LAEA-5')
    """  # noqa

    import xskillscore
    import pyku.meta as meta

    # Get xr.DataArrays
    # -----------------

    das = _get_DataArrays(dats, var=var)
    da_ref = _get_DataArrays(ref, var=var)[0]

    # Calculate
    # ---------

    das_pcc = []

    for da in das:

        # Select common datetimes and unchunck along time
        # -----------------------------------------------

        sel_ref, sel_da = meta.select_common_datetimes(da_ref, da)

        sel_ref = _unchunk_along_time(sel_ref)
        sel_da = _unchunk_along_time(sel_da)

        # Calculate pearson_r
        # -------------------

        da_pcc = xskillscore.pearson_r(
            sel_da,
            sel_ref,
            dim='time',
            skipna=True
        )

        # Set attributes and append to list of results
        # --------------------------------------------

        da_pcc.attrs = da.attrs
        da_pcc.attrs['long_name'] = 'PCC'
        da_pcc.attrs.pop('units', None)

        das_pcc.append(da_pcc)

    # Plot
    # ----

    n_maps(*das_pcc, crs=crs, **kwargs)


def pdf2D(ds, var=None, varx=None, vary=None, sample_size=100, ax=None,
          **kwargs):

    """
    2D distribution

    Arguments:
        ds (:class:`xarray.Dataset`): The input dataset.
        varx (str): The variable on the x axis.
        vary (str): The variable on the y axis.
        sample_size (int): The sample size.

    Other Parameters:

        **kwargs:
            Any argument that can be passed to :func:`matplotlib.pyplot.figure`
            or :func:`matplotlib.pyplot.axes`. In particular ``ylim=(0,15)``,
            ``size_inches=(20, 40))``, or ``yscale='log'`` can be passed.
    """

    import seaborn as sns
    import numpy as np

    # Clear figure
    # ------------

    if ax is None:
        plt.clf()
    else:
        plt.sca(ax)

    # Set default figure size
    # -----------------------

    if kwargs.get('size_inches') is None:
        kwargs['size_inches'] = (10, 10)

    # Get DataArray
    # -------------

    da_x = _get_DataArrays(ds, var=varx)[0]
    da_y = _get_DataArrays(ds, var=vary)[0]

    x = da_x.values.reshape(-1)
    y = da_y.values.reshape(-1)

    indices = np.array(np.arange(0, len(x)))
    np.random.shuffle(indices)
    indices = indices[0:sample_size]

    x_sample = x[indices]
    y_sample = y[indices]

    sns.kdeplot(
        x=x_sample,
        y=y_sample,
        fill=True,
        cmap="viridis"
    )

    # Set ticks, ticks label, and legend
    # ----------------------------------

    if 'long_name' in da_x.attrs.keys() and 'units' in da_x.attrs.keys():
        xlabel = f"{da_x.attrs['long_name']} [{da_x.attrs['units']}]"

    else:
        print(
            f"WARNING: {varx} as no 'long_name' and/or 'units' in attributes"
        )
        xlabel = f"{varx}"

    if 'long_name' in da_y.attrs.keys() and 'units' in da_y.attrs.keys():
        ylabel = f"{da_y.attrs['long_name']} [{da_y.attrs['units']}]"

    else:
        print(
            f"WARNING: {vary} as no 'long_name' and/or 'units' in attributes"
        )
        ylabel = f"{vary}"

    plt.xlabel(xlabel)
    plt.ylabel(ylabel)

    if 'label' in ds.attrs.keys():
        plt.title(ds.attrs.get('label'))

    # Pass any extra arguments that can be passed to gcf
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gcf()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gcf(), **extra_kwargs)

    # Pass any extra arguments that can be passed to gca
    # --------------------------------------------------

    extra_arguments = list(
        set(kwargs.keys()) &
        set(matplotlib.artist.Artist.properties(plt.gca()).keys())
    )

    extra_kwargs = {k: kwargs.get(k) for k in extra_arguments}

    if bool(extra_kwargs):
        plt.setp(plt.gca(), **extra_kwargs)


def wasserstein_distance(ds_mod, ds_obs, nsamples=10000, numItermax=500000):

    """
    Warning:
        This function is under construction

    Wasserstein distance
    """

    import ot
    import numpy as np

    # Get variables in datasets
    # -------------------------

    mod_variables = sorted(ds_mod.clu.get_geodata_varnames())
    obs_variables = sorted(ds_obs.clu.get_geodata_varnames())

    # Check datasets contain the same variables
    # -----------------------------------------

    if mod_variables != obs_variables:

        message = textwrap.dedent(f"""
        The datasets to be compaired do not contain the same variables
        Dataset1: {mod_variables}
        Dataset2: {obs_variables}
        """)
        raise Exception(message)

    # Construct numpy arrays of size nfeatures x npixels
    # --------------------------------------------------

    np_mod = np.array([
        ds_mod[var].values.reshape(-1) for var in mod_variables
    ])

    np_obs = np.array([
        ds_obs[var].values.reshape(-1) for var in obs_variables
    ])

    # Construct numpy arrays of shape nfeatures x npixels without NaNs
    # ----------------------------------------------------------------

    nu_mod = np.array([
        np_mod[idx][np.isfinite(np_mod[idx])] for idx in range(np_mod.shape[0])
    ])

    nu_obs = np.array([
        np_obs[idx][np.isfinite(np_obs[idx])] for idx in range(np_obs.shape[0])
    ])

    # Construct the sparsity matrix
    # -----------------------------

    mod_sample_indices = np.arange(0, nu_mod.shape[1])
    obs_sample_indices = np.arange(0, nu_obs.shape[1])

    np.random.shuffle(mod_sample_indices)
    np.random.shuffle(obs_sample_indices)

    mod_sample_indices = sorted(mod_sample_indices[0:nsamples])
    obs_sample_indices = sorted(obs_sample_indices[0:nsamples])

    # obs_sample_indices = sorted(obs_sample_indices[0:20000])
    # mod_sample_indices = sorted(mod_sample_indices[0:20000])

    nu_mod = np.array([
        nu_mod[idx][mod_sample_indices] for idx in range(nu_mod.shape[0])
    ])

    nu_obs = np.array([
        nu_obs[idx][obs_sample_indices] for idx in range(nu_obs.shape[0])
    ])

    # Calculate Wassertein distance
    # -----------------------------

    M = ot.dist(nu_mod.T, nu_obs.T, metric='euclidean')

    distance = ot.emd2([], [], M, numItermax=numItermax)
    # distance = ot.sinkhorn2([], [], M, reg=0.1)

    return distance
