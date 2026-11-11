"""
Evaluation module
"""

import calendar
import copy
import inspect
import itertools
import logging
import math
import re
import textwrap
from collections.abc import Callable
from typing import Any, Literal, Union, cast

import geopandas
import matplotlib
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pyresample
from matplotlib.axes import Axes

import xarray as xr

logger = logging.getLogger('visualisation')


def _get_map_spatial_dims(
    ds: xr.Dataset,
    var: str,
) -> tuple[str, str]:
    """Resolve the y/x dimensions used by a georeferenced variable."""
    from pyku import meta

    y_name, x_name = meta.get_projection_yx_varnames(ds)
    if y_name is None or x_name is None:
        raise ValueError("Could not resolve the map's spatial dimensions.")

    y_dims = ds[y_name].dims if y_name in ds else (y_name,)
    x_dims = ds[x_name].dims if x_name in ds else (x_name,)
    if len(y_dims) == 1 and len(x_dims) == 1 and y_dims != x_dims:
        spatial_dims = (y_dims[0], x_dims[0])
    elif y_dims == x_dims and len(y_dims) == 2:
        spatial_dims = (y_dims[0], y_dims[1])
    else:
        raise ValueError(
            f"Could not resolve spatial dimensions from {y_name!r} and "
            f"{x_name!r}."
        )

    if set(spatial_dims) != set(ds[var].dims):
        raise ValueError(
            f"Variable {var!r} dimensions {ds[var].dims} do not match "
            f"spatial dimensions {spatial_dims}."
        )
    return spatial_dims


def _validate_spatial_coordinates(
    ds: xr.Dataset,
    ref: xr.Dataset,
    var: str,
) -> None:
    """Raise when datasets do not describe matching spatial grid cells."""
    from pyku import meta

    spatial_dims = tuple(dim for dim in ds[var].dims if dim != "time")
    ref_spatial_dims = tuple(dim for dim in ref[var].dims if dim != "time")
    if set(spatial_dims) != set(ref_spatial_dims):
        raise ValueError("The datasets have different spatial dimensions.")

    for dim in spatial_dims:
        if ds.sizes[dim] != ref.sizes[dim]:
            raise ValueError("The datasets have different spatial sizes.")
        has_ds_coord = dim in ds.coords
        has_ref_coord = dim in ref.coords
        if has_ds_coord != has_ref_coord:
            raise ValueError(
                f"The datasets have different spatial coordinates for {dim!r}."
            )
        if has_ds_coord and not np.array_equal(
            ds[dim].values,
            ref[dim].values,
        ):
            raise ValueError(
                f"The datasets have different spatial coordinates for {dim!r}."
            )

    coordinate_name_getters = (
        meta.get_projection_yx_varnames,
        meta.get_geographic_latlon_varnames,
    )
    for get_names in coordinate_name_getters:
        ds_names = get_names(ds)
        ref_names = get_names(ref)
        for ds_name, ref_name in zip(ds_names, ref_names, strict=True):
            if ds_name is None or ref_name is None:
                continue
            if ds_name not in ds.coords or ref_name not in ref.coords:
                continue
            ds_coord = ds[ds_name]
            ref_coord = ref[ref_name]
            if set(ds_coord.dims) != set(ref_coord.dims):
                raise ValueError(
                    "The datasets have different spatial coordinate "
                    f"dimensions for {ds_name!r} and {ref_name!r}."
                )
            ref_values = ref_coord.transpose(*ds_coord.dims).values
            if not np.array_equal(ds_coord.values, ref_values):
                raise ValueError(
                    "The datasets have different spatial coordinates for "
                    f"{ds_name!r} and {ref_name!r}."
                )


def one_map(
    ds: xr.Dataset,
    var: str | None = None,
    colorbar: bool = True,
    cmap: Union[str, mcolors.Colormap] = "viridis",
    norm: Union[mcolors.Normalize, None] = None,
    vmin: float | None = None,
    vmax: float | None = None,
    draw_labels: bool = True,
    map_diagonal: float = 5.5,
    figure_kwargs: dict[str, Any] | None = None,
    pcolormesh_kwargs: dict[str, Any] | None = None,
    colorbar_kwargs: dict[str, Any] | None = None,
    gridlines_kwargs: dict[str, Any] | None = None,
    subplot_kwargs: dict[str, Any] | None = None,
    gca_kwargs: dict[str, Any] | None = None,
    gcf_kwargs: dict[str, Any] | None = None,
) -> None:
    """Plot a single map from an xarray Dataset.

    Convenience wrapper around :func:`n_maps` for plotting one dataset.

    Parameters
    ----------
    ds : xarray.Dataset
        Input dataset containing geospatial data to plot.
    var : str, optional
        Name of the variable to plot. Defaults to the first geodata variable
        found in the dataset.
    colorbar : bool, optional
        If True (default), a shared colorbar is added. If False, colormaps
        are set independently for each plot.
    cmap : str, optional
        Colormap name. Defaults to "viridis".
    norm : matplotlib.colors.Normalize, optional
        Normalization for the colormap. Defaults to None (auto-calculated).
    vmin : float, optional
        Minimum value for color scaling. Defaults to None (auto-calculated).
    vmax : float, optional
        Maximum value for color scaling. Defaults to None (auto-calculated).
    draw_labels : bool, optional
        Whether to draw gridline labels. Defaults to True.
    map_diagonal : float, optional
        Diagonal size of the map axes in inches. Defaults to 5.5.
    figure_kwargs : dict, optional
        Keyword arguments passed to :func:`matplotlib.pyplot.figure`.
    pcolormesh_kwargs : dict, optional
        Keyword arguments passed to :func:`matplotlib.pyplot.pcolormesh`.
    colorbar_kwargs : dict, optional
        Keyword arguments passed to :func:`matplotlib.pyplot.colorbar`.
    gridlines_kwargs : dict, optional
        Keyword arguments passed to :func:`cartopy.mpl.gridliner.gridlines`.
    subplot_kwargs : dict, optional
        Keyword arguments passed to
        :meth:`matplotlib.figure.Figure.add_subplot`.
    gca_kwargs : dict, optional
        Keyword arguments passed to the active axes via
        :func:`matplotlib.pyplot.gca`.
    gcf_kwargs : dict, optional
        Keyword arguments passed to the active figure via
        :func:`matplotlib.pyplot.gcf`.
    See Also
    --------
    n_maps : Plot an arbitrary number of maps.
    two_maps : Plot two maps side by side.

    Examples
    --------
    .. ipython::
        :okwarning:

        @savefig vis_one_map.png scale=70
        In [0]: %%time
           ...: import pyku
           ...: ds = (
           ...:    pyku.resources.get_test_data('small_tas_dataset')
           ...:    .isel(time=0).compute()
           ...: )
           ...: ds.vis.one_map(var='tas')
    """

    n_maps(
        ds,
        var=var,
        colorbar=colorbar,
        cmap=cmap,
        norm=norm,
        vmin=vmin,
        vmax=vmax,
        draw_labels=draw_labels,
        map_diagonal=map_diagonal,
        figure_kwargs=figure_kwargs,
        pcolormesh_kwargs=pcolormesh_kwargs,
        colorbar_kwargs=colorbar_kwargs,
        gridlines_kwargs=gridlines_kwargs,
        subplot_kwargs=subplot_kwargs,
        gca_kwargs=gca_kwargs,
        gcf_kwargs=gcf_kwargs,
    )


def two_maps(
    ds1: xr.Dataset,
    ds2: xr.Dataset,
    var: str | None = None,
    colorbar: bool = True,
    cmap: Union[str, mcolors.Colormap] = "viridis",
    norm: Union[mcolors.Normalize, None] = None,
    vmin: float | None = None,
    vmax: float | None = None,
    draw_labels: bool = True,
    map_diagonal: float = 5.5,
    layout: str | None = None,
    figure_kwargs: dict[str, Any] | None = None,
    pcolormesh_kwargs: dict[str, Any] | None = None,
    colorbar_kwargs: dict[str, Any] | None = None,
    gridlines_kwargs: dict[str, Any] | None = None,
    subplot_kwargs: dict[str, Any] | None = None,
    gca_kwargs: dict[str, Any] | None = None,
    gcf_kwargs: dict[str, Any] | None = None,
) -> None:
    """Plot two maps in a grid, side by side by default.

    Convenience wrapper around :func:`n_maps` for plotting two datasets.

    Parameters
    ----------
    ds1 : xarray.Dataset
        First input dataset to plot.
    ds2 : xarray.Dataset
        Second input dataset to plot.
    var : str, optional
        Name of the variable to plot. Defaults to the first geodata variable
        found in the datasets.
    colorbar : bool, optional
        If True (default), a shared colorbar is added. If False, colormaps
        are set independently for each plot.
    cmap : str, matplotlib.colors.Colormap, optional
        Colormap name. Defaults to "viridis".
    norm : matplotlib.colors.Normalize, optional
        Normalization for the colormap. If specified, it overrides vmin and
        vmax.
    vmin : float, optional
        Minimum value for color scaling. Defaults to None (auto-calculated).
    vmax : float, optional
        Maximum value for color scaling. Defaults to None (auto-calculated).
    draw_labels : bool, optional
        Whether to draw gridline labels. Defaults to True.
    map_diagonal : float, optional
        Diagonal size of each map axes in inches. Defaults to 5.5.
    layout : str, optional
        Subplot layout in ``"rowsxcolumns"`` form. For example, ``"2x1"``
        places the maps vertically. A missing dimension is calculated
        automatically, as in ``"2x"`` or ``"x1"``.
    figure_kwargs : dict, optional
        Keyword arguments passed to :func:`matplotlib.pyplot.figure`.
    pcolormesh_kwargs : dict, optional
        Keyword arguments passed to :func:`matplotlib.pyplot.pcolormesh`.
    colorbar_kwargs : dict, optional
        Keyword arguments passed to :func:`matplotlib.pyplot.colorbar`.
    gridlines_kwargs : dict, optional
        Keyword arguments passed to :func:`cartopy.mpl.gridliner.gridlines`.
    subplot_kwargs : dict, optional
        Keyword arguments passed to
        :meth:`matplotlib.figure.Figure.add_subplot`.
    gca_kwargs : dict, optional
        Keyword arguments passed to the active axes via
        :func:`matplotlib.pyplot.gca`.
    gcf_kwargs : dict, optional
        Keyword arguments passed to the active figure via
        :func:`matplotlib.pyplot.gcf`.

    See Also
    --------
    n_maps : Plot an arbitrary number of maps.
    one_map : Plot a single map.

    Examples
    --------
    .. ipython::
        :okwarning:

        @savefig two_maps.png scale=70
        In [0]: %%time
           ...: import pyku
           ...:
           ...: ds = pyku.resources.get_test_data('small_tas_dataset')
           ...:
           ...: pyku.visualisation.two_maps(
           ...:     ds.isel(time=0),
           ...:     ds.isel(time=1),
           ...:     var='tas',
           ...: )
    """

    n_maps(
        ds1,
        ds2,
        var=var,
        colorbar=colorbar,
        cmap=cmap,
        norm=norm,
        vmin=vmin,
        vmax=vmax,
        draw_labels=draw_labels,
        map_diagonal=map_diagonal,
        layout=layout,
        figure_kwargs=figure_kwargs,
        pcolormesh_kwargs=pcolormesh_kwargs,
        colorbar_kwargs=colorbar_kwargs,
        gridlines_kwargs=gridlines_kwargs,
        subplot_kwargs=subplot_kwargs,
        gca_kwargs=gca_kwargs,
        gcf_kwargs=gcf_kwargs,
    )


def n_maps(
    *datasets: xr.Dataset | list[xr.Dataset] | tuple[xr.Dataset, ...],
    var: str | None = None,
    colorbar: bool = True,
    cmap: Union[str, mcolors.Colormap] = "viridis",
    norm: Union[mcolors.Normalize, None] = None,
    vmin: float | None = None,
    vmax: float | None = None,
    nrows: int | None = None,
    ncols: int | None = None,
    layout: str | None = None,
    draw_labels: bool = True,
    map_diagonal: float = 5.5,
    figure_kwargs: dict[str, Any] | None = None,
    pcolormesh_kwargs: dict[str, Any] | None = None,
    colorbar_kwargs: dict[str, Any] | None = None,
    gridlines_kwargs: dict[str, Any] | None = None,
    subplot_kwargs: dict[str, Any] | None = None,
    gca_kwargs: dict[str, Any] | None = None,
    gcf_kwargs: dict[str, Any] | None = None,
) -> None:
    """Plot n maps in a grid layout.

    Creates a figure with multiple map subplots arranged in a grid.
    Automatically handles colorbar scaling, gridlines, and cartopy features.

    Parameters
    ----------
    *datasets : xarray.Dataset
        One or more input datasets to plot.
    var : str, optional
        Name of the variable to plot. Defaults to the first geodata variable
        found in the datasets.
    colorbar : bool, optional
        If True (default), a shared colorbar is added. If False, colormaps
        are set independently for each plot.
    cmap : Union[str, matplotlib.colors.Colormap, None], optional
        Colormap name. Defaults to "viridis".
    norm : Union[matplotlib.colors.Normalize, None], optional
        Normalization for the colormap. If specified, it overrides vmin and
        vmax for extend
    vmin : float, optional
        Minimum value for color scaling. Defaults to None (auto-calculated as
        the 2nd percentile across all datasets).
    vmax : float, optional
        Maximum value for color scaling. Defaults to None (auto-calculated as
        the 98th percentile across all datasets).
    nrows : int, optional
        Number of rows in the subplot grid. Defaults to 1.
    ncols : int, optional
        Number of columns in the subplot grid. Defaults to the number of
        datasets.
    layout : str, optional
        Subplot layout as ``"rowsxcolumns"``. For example, ``"3x3"`` sets
        three rows and columns, ``"x3"`` sets three columns and calculates
        the rows, and ``"4x"`` sets four rows and calculates the columns.
        Cannot be combined with ``nrows`` or ``ncols``.
    draw_labels : bool, optional
        Whether to draw gridline labels. Defaults to True.
    map_diagonal : float, optional
        Diagonal size of each map axes in inches. Defaults to 5.5.
    figure_kwargs : dict, optional
        Keyword arguments passed to :func:`matplotlib.pyplot.figure`.
    pcolormesh_kwargs : dict, optional
        Keyword arguments passed to :func:`matplotlib.pyplot.pcolormesh`.
    colorbar_kwargs : dict, optional
        Keyword arguments passed to :func:`matplotlib.pyplot.colorbar`.
    gridlines_kwargs : dict, optional
        Keyword arguments passed to :func:`cartopy.mpl.gridliner.gridlines`.
    subplot_kwargs : dict, optional
        Keyword arguments passed to
        :meth:`matplotlib.figure.Figure.add_subplot`.
    gca_kwargs : dict, optional
        Keyword arguments passed to the active axes via
        :func:`matplotlib.pyplot.gca`.
    gcf_kwargs : dict, optional
        Keyword arguments passed to the active figure via
        :func:`matplotlib.pyplot.gcf`.
    Raises
    ------
    TypeError
        If inputs are not xarray.Dataset or a list/tuple of xarray.Datasets.
    ValueError
        If datasets have no geodata variables, inconsistent geodata variable
        names, or if the grid size is too small for the number of datasets.

    See Also
    --------
    one_map : Plot a single map.
    two_maps : Plot two maps side by side.

    Examples
    --------
    .. ipython::
        :okwarning:

        @savefig n_maps.png scale=70
        In [0]: %%time
           ...: import pyku
           ...:
           ...: ds = pyku.resources.get_test_data('small_tas_dataset')
           ...:
           ...: pyku.visualisation.n_maps(
           ...:     ds.isel(time=0),
           ...:     ds.isel(time=1),
           ...:     ds.isel(time=2),
           ...:     ds.isel(time=3),
           ...:     layout='2x2',
           ...:     var='tas',
           ...: )
    """

    import cartopy
    import cartopy.crs as ccrs
    from dask.base import compute

    from pyku import geo, meta

    figure_kwargs = dict(figure_kwargs or {})
    pcolormesh_kwargs = dict(pcolormesh_kwargs or {})
    colorbar_kwargs = dict(colorbar_kwargs or {})
    gridlines_kwargs = dict(gridlines_kwargs or {})
    subplot_kwargs = dict(subplot_kwargs or {})
    gca_kwargs = dict(gca_kwargs or {})
    gcf_kwargs = dict(gcf_kwargs or {})

    if gridlines_kwargs.pop("draw_labels", None) is not None:
        logger.warning(
            "Passing 'draw_labels' inside gridlines_kwargs is ignored; "
            "use the function's top-level 'draw_labels' argument instead."
        )

    if len(datasets) == 1 and isinstance(datasets[0], (list, tuple)):
        normalized_datasets = list(datasets[0])
    else:
        normalized_datasets = list(datasets)

    if not all(isinstance(ds, xr.Dataset) for ds in normalized_datasets):
        raise TypeError(
            "Expected an xarray.Dataset or a list/tuple of xarray.Datasets."
        )

    plot_datasets = cast(list[xr.Dataset], normalized_datasets)

    if not plot_datasets:
        raise ValueError("At least one dataset must be provided.")

    for idx, ds in enumerate(plot_datasets):
        if not geo.is_georeferencing_sorted(ds):
            logger.warning(
                f"Dataset [{idx}] projection coordinates are not sorted "
                "(left-to-right, top-to-bottom). Cartopy may throw errors. "
                "To fix, run `ds.pyku.sort_georeferencing()` on your datasets."
            )

    varnames_per_ds = [meta.get_geodata_varnames(ds) for ds in plot_datasets]

    if any(len(v) == 0 for v in varnames_per_ds):
        raise ValueError(
            "One or more datasets do not contain any geodata variables."
        )

    if var is None:
        var = str(varnames_per_ds[0][0])
    if var is None:
        raise ValueError("A geodata variable must be selected for mapping.")

    for idx, varnames in enumerate(varnames_per_ds):
        if var not in varnames:
            raise ValueError(
                f"Variable {var!r} is not a geodata variable in dataset "
                f"[{idx}]."
            )

    plot_datasets = [
        meta.get_geodataset(ds, var=var) for ds in plot_datasets
    ]

    for idx, ds in enumerate(plot_datasets):
        if ds[var].ndim != 2:
            raise ValueError(
                f"Dataset [{idx}] variable {var!r} must be 2D for map "
                f"plotting; found dimensions {ds[var].dims}."
            )

    plot_datasets = list(compute(*plot_datasets))

    if pcolormesh_kwargs.get("cmap") is None:
        pcolormesh_kwargs["cmap"] = cmap

    data_vmin, data_vmax = _map_data_limits(plot_datasets, var)
    if norm is None:
        norm = pcolormesh_kwargs.pop("norm", None)
    if norm is None:
        pcolormesh_vmin = pcolormesh_kwargs.pop("vmin", None)
        pcolormesh_vmax = pcolormesh_kwargs.pop("vmax", None)
        vmin = (
            vmin if vmin is not None else
            pcolormesh_vmin if pcolormesh_vmin is not None else data_vmin
        )
        vmax = (
            vmax if vmax is not None else
            pcolormesh_vmax if pcolormesh_vmax is not None else data_vmax
        )
        if vmin is not None and vmax is not None and vmin > vmax:
            raise ValueError("'vmin' must not be greater than 'vmax'.")
        pcolormesh_kwargs["vmin"] = vmin
        pcolormesh_kwargs["vmax"] = vmax
    else:
        resolved_norm = copy.deepcopy(norm)
        resolved_norm.vmin = (
            resolved_norm.vmin if resolved_norm.vmin is not None else data_vmin
        )
        resolved_norm.vmax = (
            resolved_norm.vmax if resolved_norm.vmax is not None else data_vmax
        )
        if resolved_norm.vmin > resolved_norm.vmax:
            raise ValueError("Normalization minimum must not exceed maximum.")
        pcolormesh_kwargs.pop("vmin", None)
        pcolormesh_kwargs.pop("vmax", None)
        pcolormesh_kwargs["norm"] = resolved_norm
        vmin, vmax = resolved_norm.vmin, resolved_norm.vmax

    if layout is not None:
        if nrows is not None or ncols is not None:
            raise ValueError(
                "'layout' cannot be combined with 'nrows' or 'ncols'."
            )
        nrows, ncols = _resolve_subplot_layout(
            layout,
            len(plot_datasets),
            "map",
        )
    else:
        if nrows is None:
            nrows = 1
        if ncols is None:
            ncols = subplot_kwargs.pop("ncols", len(plot_datasets))

    assert nrows is not None and ncols is not None
    if nrows <= 0 or ncols <= 0:
        raise ValueError("'nrows' and 'ncols' must be greater than zero.")

    if len(plot_datasets) > nrows * ncols:
        raise ValueError(
            f"Grid size ({nrows}x{ncols}={nrows * ncols}) is too small for "
            f"the number of datasets to plot ({len(plot_datasets)})."
        )

    if map_diagonal <= 0:
        raise ValueError("'map_diagonal' must be greater than zero.")

    nx = geo.get_nx(plot_datasets[0])
    ny = geo.get_ny(plot_datasets[0])
    map_ratios = [
        float(geo.get_nx(ds)) / float(geo.get_ny(ds))
        for ds in plot_datasets
    ]

    map_layout = _get_map_layout(
        nx,
        ny,
        nrows,
        ncols,
        draw_labels,
        colorbar,
        map_diagonal=map_diagonal,
        map_ratios=map_ratios,
    )
    fig = plt.figure(**figure_kwargs)
    fig.set_size_inches(map_layout["figure_size"])

    axs = []

    for idx, ds in enumerate(plot_datasets):
        area_def = ds.pyku.get_area_def()
        data_crs = area_def.to_cartopy_crs()

        ax = fig.add_axes(
            map_layout["map_axes"][idx],
            projection=data_crs,
            **subplot_kwargs,
        )

        axs.append(ax)

    im = None
    for ds, ax in zip(plot_datasets, axs, strict=True):
        lons, lats = geo.get_lonlats(ds)

        im = ax.pcolormesh(
            lons,
            lats,
            ds[var].transpose(*_get_map_spatial_dims(ds, var)).values,
            transform=ccrs.PlateCarree(),
            **pcolormesh_kwargs,
        )

        if ds[var].attrs.get("label") is not None:
            ax.set_title(ds[var].attrs.get("label"))

    cbar_label = ""

    if plot_datasets[-1][var].attrs.get("standard_name") is not None:
        cbar_label = plot_datasets[-1][var].attrs.get("standard_name")

    if plot_datasets[-1][var].attrs.get("long_name") is not None:
        cbar_label = plot_datasets[-1][var].attrs.get("long_name")

    if plot_datasets[-1][var].attrs.get("units") is not None:
        cbar_label = (
            f"{cbar_label} [{plot_datasets[-1][var].attrs.get('units')}]"
        )

    if colorbar:
        extend = "neither"

        below = any(bool((ds[var] < vmin).any()) for ds in plot_datasets)
        above = any(bool((ds[var] > vmax).any()) for ds in plot_datasets)
        if below and above:
            extend = "both"
        elif below:
            extend = "min"
        elif above:
            extend = "max"

        cb_ax = fig.add_axes(map_layout["colorbar_axes"])

        if "cbar_ticks" in colorbar_kwargs:
            if "ticks" in colorbar_kwargs:
                raise ValueError(
                    "Use only one of colorbar_kwargs['ticks'] and "
                    "colorbar_kwargs['cbar_ticks']."
                )
            colorbar_kwargs["ticks"] = colorbar_kwargs.pop("cbar_ticks")
        reserved_colorbar_kwargs = {"cax", "mappable"}
        conflicts = reserved_colorbar_kwargs.intersection(colorbar_kwargs)
        if conflicts:
            conflict_list = ", ".join(sorted(conflicts))
            raise ValueError(
                "These colorbar arguments are managed internally and cannot "
                f"be supplied: {conflict_list}."
            )
        colorbar_kwargs.setdefault("orientation", "vertical")
        colorbar_kwargs.setdefault("extend", extend)
        colorbar_kwargs.setdefault("label", cbar_label)
        assert im is not None
        fig.colorbar(im, cax=cb_ax, **colorbar_kwargs)

    for ax in axs:
        ax.set(**gca_kwargs)
    fig.set(**gcf_kwargs)

    for ax in axs:
        ax.add_feature(cartopy.feature.BORDERS)
        ax.add_feature(cartopy.feature.LAKES.with_scale("50m"))
        ax.add_feature(cartopy.feature.RIVERS)
        ax.add_feature(cartopy.feature.COASTLINE)

        gridlines_kwargs.setdefault("dms", True)
        gridlines_kwargs.setdefault("x_inline", False)
        gridlines_kwargs.setdefault("y_inline", False)
        gridlines_kwargs.setdefault("xpadding", 5)
        gridlines_kwargs.setdefault("ypadding", 5)
        gridlines_kwargs.setdefault("offset_angle", 25)
        gridlines_kwargs.setdefault("auto_update", False)
        gl = ax.gridlines(
            crs=ccrs.PlateCarree(),
            draw_labels=False,
            **gridlines_kwargs,
        )

        gl.inline = False
        gl.top_labels = False
        gl.right_labels = False
        gl.bottom_labels = draw_labels
        gl.left_labels = draw_labels


def _map_data_limits(
    datasets: list[xr.Dataset],
    var: str,
) -> tuple[float, float]:
    """Calculate robust shared map limits from finite values.

    The lower and upper bounds are the minimum per-dataset 2nd percentile
    and maximum per-dataset 98th percentile, respectively.
    """
    lower_quantiles: list[float] = []
    upper_quantiles: list[float] = []

    for dataset in datasets:
        values = np.asarray(dataset[var].values)
        finite_values = values[np.isfinite(values)]
        if finite_values.size == 0:
            continue
        lower_quantiles.append(float(np.quantile(finite_values, 0.02)))
        upper_quantiles.append(float(np.quantile(finite_values, 0.98)))

    if not lower_quantiles:
        raise ValueError(
            f"Variable {var!r} contains no finite values in any dataset."
        )

    return min(lower_quantiles), max(upper_quantiles)


def _parse_map_layout(
    layout: str,
    n_plots: int,
) -> tuple[int, int]:
    """Parse a map grid shorthand into its row and column counts.

    Parameters
    ----------
    layout : str
        Grid shorthand in ``"rowsxcolumns"`` form. Either dimension may
        be omitted and inferred from ``n_plots``.
    n_plots : int
        Number of plots to fit in the grid.

    Returns
    -------
    tuple of int
        Number of rows and columns.

    Raises
    ------
    ValueError
        If the shorthand is malformed or specifies a non-positive size.
    """
    match = re.fullmatch(r"(\d*)\s*[xX]\s*(\d*)", layout.strip())
    if match is None or not any(match.groups()):
        raise ValueError(
            "'layout' must be formatted as 'rowsxcolumns', such as '3x3', "
            "'x3', or '4x'."
        )

    row_text, col_text = match.groups()
    nrows = int(row_text) if row_text else None
    ncols = int(col_text) if col_text else None
    if nrows == 0 or ncols == 0:
        raise ValueError("'layout' dimensions must be greater than zero.")

    if nrows is None:
        assert ncols is not None
        nrows = max(1, math.ceil(n_plots / ncols))
    elif ncols is None:
        ncols = max(1, math.ceil(n_plots / nrows))

    return nrows, ncols


def _resolve_subplot_layout(
    layout: str,
    n_plots: int,
    plot_type: str,
) -> tuple[int, int]:
    """Resolve a layout shorthand and report unused subplot slots.

    Parameters
    ----------
    layout : str
        Grid shorthand in ``"rowsxcolumns"`` form.
    n_plots : int
        Number of plots that must fit in the grid.
    plot_type : str
        Plot description used in warnings and errors.

    Returns
    -------
    tuple of int
        Number of rows and columns.

    Raises
    ------
    ValueError
        If the grid is too small for the plots.
    """
    nrows, ncols = _parse_map_layout(layout, n_plots)
    n_slots = nrows * ncols

    if n_slots != n_plots:
        logger.warning(
            "Layout '%s' provides %d subplot slots for %d %s plots.",
            layout,
            n_slots,
            n_plots,
            plot_type,
        )

    if n_slots < n_plots:
        raise ValueError(
            f"Layout '{layout}' provides {n_slots} subplot slots for "
            f"{n_plots} {plot_type} plots."
        )

    return nrows, ncols


def _get_map_layout(
    nx: int,
    ny: int,
    nrows: int,
    ncols: int,
    draw_labels: bool,
    colorbar: bool,
    map_diagonal: float = 5.5,
    map_ratios: list[float] | None = None,
) -> dict[str, Any]:
    """Return axes rectangles for a grid of maps with fixed diagonals.

    Computes figure size and axes positions for a grid of maps, ensuring
    consistent diagonal sizes. Gridline labels sit in dedicated gutters to
    prevent overlap.

    Parameters
    ----------
    nx : int
        Number of grid points in the x direction.
    ny : int
        Number of grid points in the y direction.
    nrows : int
        Number of rows in the subplot grid.
    ncols : int
        Number of columns in the subplot grid.
    draw_labels : bool
        Whether to draw gridline labels.
    colorbar : bool
        Whether to include a colorbar.
    map_diagonal : float, optional
        Diagonal size of each map axes in inches. Defaults to 5.5.
    map_ratios : list of float, optional
        List of aspect ratios (width/height) for each map. Defaults to
        [nx / ny] if None.

    Returns
    -------
    dict
        Dictionary with the following keys:
        - 'figure_size' : tuple of (width, height) in inches.
        - 'map_axes' : list of (x, y, width, height) tuples for each map.
        - 'colorbar_axes' : (x, y, width, height) tuple for colorbar, or None.

    Raises
    ------
    ValueError
        If map_diagonal is not positive.
    """

    if map_diagonal <= 0:
        raise ValueError("'map_diagonal' must be greater than zero.")

    map_ratios = map_ratios or [nx / ny]
    reference_ratio = nx / ny
    map_ratios = list(map_ratios) + [reference_ratio] * (
        nrows * ncols - len(map_ratios)
    )
    map_sizes = [
        (
            map_diagonal * ratio / math.sqrt(1 + ratio ** 2),
            map_diagonal / math.sqrt(1 + ratio ** 2),
        )
        for ratio in map_ratios
    ]
    scale = map_diagonal / 5.5
    label_width = max(0.65, 0.65 * scale) if draw_labels else 0.0
    label_height = max(0.45, 0.45 * scale) if draw_labels else 0.0
    column_spacing = 0.15 * scale
    row_spacing = 0.15 * scale
    outer_left = 0.1 * scale
    outer_right = max(0.5, 0.5 * scale)
    outer_top = max(0.35, 0.35 * scale)
    colorbar_width = max(0.20, 0.20 * scale) if colorbar else 0.0
    colorbar_padding = 0.2 * scale if colorbar else 0.0
    column_widths = [
        max(map_sizes[row * ncols + col][0] for row in range(nrows))
        for col in range(ncols)
    ]
    row_heights = [
        max(map_sizes[row * ncols + col][1] for col in range(ncols))
        for row in range(nrows)
    ]
    figure_width = (
        outer_left
        + ncols * label_width
        + sum(column_widths)
        + (ncols - 1) * column_spacing
        + colorbar_padding
        + colorbar_width
        + outer_right
    )
    figure_height = (
        outer_top
        + nrows * label_height
        + sum(row_heights)
        + (nrows - 1) * row_spacing
    )
    map_axes = []

    for idx in range(nrows * ncols):
        row = idx // ncols
        col = idx % ncols
        map_width, map_height = map_sizes[idx]
        x = outer_left + label_width
        x += sum(
            label_width + width + column_spacing
            for width in column_widths[:col]
        )
        y = (
            sum(
                label_height + height + row_spacing
                for height in row_heights[row + 1:]
            )
            + label_height
        )
        map_axes.append((
            x / figure_width,
            y / figure_height,
            map_width / figure_width,
            map_height / figure_height,
        ))

    colorbar_axes = None

    if colorbar:
        x = (
            outer_left
            + ncols * label_width
            + sum(column_widths)
            + (ncols - 1) * column_spacing
            + colorbar_padding
        )
        colorbar_axes = (
            x / figure_width,
            label_height / figure_height,
            colorbar_width / figure_width,
            (figure_height - label_height - outer_top) / figure_height,
        )

    return {
        "figure_size": (figure_width, figure_height),
        "map_axes": map_axes,
        "colorbar_axes": colorbar_axes,
    }


def _validate_kwargs(
    target_func: Callable[..., Any],
    kwargs_dict: dict[str, Any],
    dict_name: str,
) -> None:
    """Validate that keys in a dictionary are valid arguments for a function.

    Parameters
    ----------
    target_func : callable
        The function to inspect for valid parameters.
    kwargs_dict : dict
        Dictionary of keyword arguments to validate.
    dict_name : str
        Name of the kwargs dictionary (used in error messages).

    Raises
    ------
    ValueError
        If any key in kwargs_dict is not a valid parameter for target_func.

    Returns
    -------
    None
    """

    if not kwargs_dict:
        return

    sig = inspect.signature(target_func)

    for key in kwargs_dict:
        if key not in sig.parameters:
            raise ValueError(
                f"Invalid argument '{key}' inside '{dict_name}'. Accepted "
                "parameters for "
                f"{target_func.__module__}.{target_func.__name__} are:\n"
                f"{list(sig.parameters.keys())}"
            )


def _ensure_single_time_chunk(
    da: Any,
) -> Any:
    """Rechunk xarray data to use a single chunk along time.

    Parameters
    ----------
    da : xarray.Dataset or xarray.DataArray
        Input data.

    Returns
    -------
    xarray.Dataset or xarray.DataArray
        Data with the time dimension in a single chunk, if present.
    """

    chunks = dict.fromkeys(da.dims, 'auto')

    if 'time' in da.dims:
        chunks['time'] = -1

    return da.chunk(chunks=chunks)


def _unchunk_along_time(
    da: Any,
) -> Any:
    """Compatibility alias for :func:`_ensure_single_time_chunk`.

    Parameters
    ----------
    da : xarray.Dataset or xarray.DataArray
        Input data.

    Returns
    -------
    xarray.Dataset or xarray.DataArray
        Data with the time dimension in a single chunk, if present.
    """
    return _ensure_single_time_chunk(da)


def _calculate_metric(
    model: xr.DataArray,
    reference: xr.DataArray,
    metric: str,
) -> xr.DataArray:
    """Calculate and label one supported evaluation metric."""
    import xskillscore

    if metric == "mae":
        result = xskillscore.mae(
            model,
            reference,
            dim="time",
            skipna=True,
        )
    elif metric == "bias":
        result = (model - reference).mean(
            "time",
            skipna=True,
            keep_attrs=True,
        )
    elif metric == "mse":
        result = xskillscore.mse(
            reference,
            model,
            dim="time",
            skipna=True,
        )
    elif metric == "rmse":
        result = xskillscore.rmse(
            reference,
            model,
            dim="time",
            skipna=True,
        )
    elif metric == "pcc":
        result = xskillscore.pearson_r(
            model,
            reference,
            dim="time",
            skipna=True,
        )
    else:
        raise ValueError(f"Unsupported metric: {metric}")

    result.attrs["long_name"] = metric.upper()
    units = model.attrs.get("units")
    if metric in {"mae", "bias", "rmse"} and units is not None:
        result.attrs["units"] = units
    elif metric == "mse" and units is not None:
        result.attrs["units"] = f"({units})^2"
    else:
        result.attrs.pop("units", None)
    return result


def _metric_result_dataset(
    model: xr.Dataset,
    result: xr.DataArray,
    metric: str,
    label: str | None = None,
) -> xr.Dataset:
    """Combine a metric field with its model grid and georeferencing."""
    from pyku import geo, meta

    template = model.isel(time=0, drop=True).copy(deep=True)
    template = template.drop_vars(meta.get_geodata_varnames(model))
    result_dataset = xr.merge(
        [template, result.to_dataset(name=metric)],
        combine_attrs="override",
        compat="no_conflicts",
    )
    if label is not None:
        result_dataset[metric].attrs["label"] = label

    return geo._copy_georeferencing_metadata_and_crs(
        result_dataset,
        model,
        [metric],
    )


def _validate_metric_grid(
    model: xr.Dataset,
    reference: xr.Dataset,
    var: str,
) -> None:
    """Require model and reference fields to share spatial grid metadata."""
    try:
        xr.align(model[var], reference[var], join="exact", exclude={"time"})
    except ValueError as exc:
        raise ValueError(
            "Model and reference spatial coordinates must match exactly."
        ) from exc

    from pyku import geo, meta

    model_projection_coords = meta.get_projection_yx_varnames(model)
    reference_projection_coords = meta.get_projection_yx_varnames(reference)
    model_geographic_coords = meta.get_geographic_latlon_varnames(model)
    reference_geographic_coords = meta.get_geographic_latlon_varnames(
        reference
    )
    coordinate_pairs = [
        ("projection y", model_projection_coords[0],
         reference_projection_coords[0]),
        ("projection x", model_projection_coords[1],
         reference_projection_coords[1]),
        ("latitude", model_geographic_coords[0],
         reference_geographic_coords[0]),
        ("longitude", model_geographic_coords[1],
         reference_geographic_coords[1]),
    ]
    for axis, model_name, reference_name in coordinate_pairs:
        if model_name is None and reference_name is None:
            continue
        if model_name is None or reference_name is None:
            raise ValueError(
                f"Model and reference must both define {axis} coordinates."
            )
        model_coord = model[model_name]
        reference_coord = reference[reference_name]
        if (
            model_coord.dims != reference_coord.dims
            or not model_coord.variable.equals(reference_coord.variable)
        ):
            raise ValueError(
                f"Model and reference {axis} coordinates must match."
            )

    model_area = geo.get_area_def(model)
    reference_area = geo.get_area_def(reference)
    if model_area.crs != reference_area.crs:
        raise ValueError("Model and reference CRS definitions must match.")


def _select_metric_pair(
    model: xr.Dataset,
    reference: xr.Dataset,
    var: str,
) -> tuple[xr.Dataset, xr.Dataset]:
    """Select common nonempty times and validate metric grid compatibility."""
    from pyku import timekit

    selected_reference, selected_model = timekit.select_common_datetimes(
        reference,
        model,
    )
    if selected_model.sizes.get("time", 0) == 0:
        raise ValueError("Model and reference have no common timestamps.")
    _validate_metric_grid(selected_model, selected_reference, var)
    return selected_model, selected_reference


def _ordered_group_keys(groupby: str, keys: Any) -> list[Any]:
    """Return observed group keys in calendar order when recognized."""
    key_set = set(keys)
    period = groupby.rsplit(".", maxsplit=1)[-1]
    if period == "month":
        ordered = list(range(1, 13))
    elif period == "season":
        ordered = ["DJF", "MAM", "JJA", "SON"]
    else:
        ordered = sorted(key_set)
    known = [key for key in ordered if key in key_set]
    remaining = key_set.difference(known)
    return known + sorted(remaining, key=str)


def regions(
    gdf: geopandas.GeoDataFrame,
    area_def: Union[str, pyresample.geometry.AreaDefinition],
    size_inches: Union[tuple[float, float], None] = None,
    gcf_kwargs: Union[dict, None] = None,
) -> None:
    """Plot regions

    Parameters
    ----------
    gdf : geopandas.GeoDataFrame
        Polygon data
    area_def : str or pyresample.AreaDefinition
        Area definition
    size_inches : tuple of float, optional
        Figure size in inches (width, height). Defaults to (14, 10).
    gcf_kwargs : dict, optional
        Additional keyword arguments passed to
        :func:`matplotlib.pyplot.gcf`.

    Returns
    -------
    None
        Displays a matplotlib figure with the plotted regions.

    Examples
    --------
    .. ipython::
       :okwarning:

       @savefig ana_regions.png scale=70
       In [0]: %%time
          ...: import pyku
          ...: gdf = pyku.resources.get_geodataframe(
          ...:     'natural_areas_of_germany'
          ...: )
          ...: pyku.visualisation.regions(gdf, area_def='HYR-GER-LAEA-5')
    """

    import cartopy

    from pyku import geo

    if isinstance(area_def, str):
        area_def = geo.load_area_def(area_def)

    plt.clf()

    if size_inches is None:
        size_inches = (14, 10)

    plt.gcf().set_size_inches(size_inches)

    crs = area_def.to_cartopy_crs()

    identifiers = range(gdf.shape[0])
    gdf['idx'] = identifiers
    cmap = 'tab20b'

    gdf.columns = [c.lower() for c in gdf.columns]

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

    if gcf_kwargs:
        plt.setp(plt.gcf(), **gcf_kwargs)


def _pdf_histogram(
    da: xr.DataArray,
    nbins: int,
    data_range: tuple[float, float] | None,
    nsamples: int | None,
) -> tuple[np.ndarray, np.ndarray] | None:
    """Calculate one PDF histogram, sampling large time series if needed."""
    import dask
    import dask.array

    if nbins <= 0:
        raise ValueError("'nbins' must be greater than zero.")
    if nsamples is not None and nsamples <= 0:
        raise ValueError("'nsamples' must be greater than zero.")
    if data_range is not None:
        if len(data_range) != 2:
            raise ValueError("'range' must contain exactly two values.")
        if data_range[0] >= data_range[1]:
            raise ValueError("'range' minimum must be less than its maximum.")

    selected = da
    data_size_gb = da.size * 4 / (1024 ** 3)
    max_data_size_gb = 32

    if data_size_gb > max_data_size_gb:
        logger.warning(
            "Amount of data above memory threshold. Subsampling along time."
        )
        times = copy.deepcopy(da.coords["time"].values)
        n_times = len(times)
        n_times_selected = int(
            n_times * max_data_size_gb / data_size_gb
        )
        np.random.shuffle(times)
        selected = da.sel(time=np.sort(times[:n_times_selected]))

    data = selected.data
    if nsamples is not None:
        flat_data = data.reshape(-1)
        sample_size = min(nsamples, flat_data.size)
        indices = np.random.choice(flat_data.size, size=sample_size)
        data = flat_data[indices]
    data = data[dask.array.isfinite(data)]

    if isinstance(data, dask.array.core.Array):
        if bool(dask.array.isnan(data).all().compute()):
            logger.warning("All-NaN data found; skipping its PDF.")
            return None
        hist, bins = dask.array.histogram(
            data,
            bins=nbins,
            range=(
                data_range
                if data_range is not None
                else (data.min(), data.max())
            ),
            density=True,
        )
        hist = hist.compute()
        if hasattr(bins, "compute"):
            bins = bins.compute()
    elif isinstance(data, np.ndarray):
        if np.isnan(data).all():
            logger.warning("All-NaN data found; skipping its PDF.")
            return None
        hist, bins = np.histogram(
            data,
            bins=nbins,
            range=data_range,
            density=True,
        )
    else:
        raise TypeError(
            f"Expected numpy or dask array data, got {type(data).__name__}."
        )

    centers = bins[:-1] + (bins[1] - bins[0]) / 2
    return np.asarray(hist), np.asarray(centers)


def pdf(
    *datasets: Any,
    var: Union[str, None] = None,
    ax: Union[matplotlib.axes.Axes, None] = None,
    groupby: Union[str, None] = None,
    layout: str | None = None,
    nbins: int = 128,
    range: Union[tuple, None] = None,
    nsamples: Union[int, None] = None,
    xlim: Union[tuple, None] = None,
    yscale: Union[str, None] = None,
    size_inches: Union[tuple[float, float], None] = None,
    gca_kwargs: Union[dict, None] = None,
    gcf_kwargs: Union[dict, None] = None,
) -> None:
    """Plot the probability distribution function of one or more datasets.

    Parameters
    ----------
    *datasets : xarray.Dataset, xarray.DataArray, list, or None
        Input dataset or datasets.
    var : str, optional
        Variable name. Required if input is an xarray.Dataset.
    ax : matplotlib.axes.Axes, optional
        Axes on which to draw the plot.
    nbins : int, optional
        Number of bins for the histogram. Defaults to 128.
    range : tuple, optional
        Data range for the histogram, e.g. (0, 10).
    nsamples : int, optional
        Number of data points to sample.
    xlim : tuple, optional
        X-axis limits, e.g. (0, 10).
    yscale : str, optional
        Y-axis scale, e.g. 'log' or 'linear'.
    size_inches : tuple of float, optional
        Figure size in inches (width, height). Defaults to (10, 5).
    groupby : str, optional
        Groupby expression for multi-panel plots. Use ``"time.month"`` for
        monthly PDFs (creates 6 rows × 2 columns) or ``"time.season"`` for
        seasonal PDFs (creates 2 rows × 2 columns). If None (default),
        produces a single plot.
    layout : str, optional
        Grid shorthand for grouped plots, such as ``"3x3"``, ``"x3"``, or
        ``"4x"``. Cannot be used when ``groupby`` is None.
    gca_kwargs : dict, optional
        Additional keyword arguments passed to
        :func:`matplotlib.pyplot.gca`.
    gcf_kwargs : dict, optional
        Additional keyword arguments passed to
        :func:`matplotlib.pyplot.gcf`.

    Returns
    -------
    None
        Displays a matplotlib figure with the PDF plot.

    Examples
    --------
    Single plot (no grouping):

    .. ipython::
       :okwarning:

       @savefig vis_pdf_single.png scale=70
       In [0]: %%time
          ...: import pyku
          ...: ds = pyku.resources.get_test_data('hyras_tas_lowres_2yr')
          ...: ds.vis.pdf(var='tas', nbins=80)

    Monthly PDFs with automatic 6×2 layout:

    .. ipython::
       :okwarning:

       @savefig vis_pdf_monthly.png scale=70
       In [0]: %%time
          ...: import pyku
          ...: ds = pyku.resources.get_test_data('hyras_tas_lowres_2yr')
          ...: ds.vis.pdf(var='tas', groupby='time.month')
    """

    datasets_list = []
    for dataset in datasets:
        if dataset is None:
            continue
        elif isinstance(dataset, list):
            datasets_list.extend(dataset)
        elif isinstance(dataset, (xr.Dataset, xr.DataArray)):
            datasets_list.append(dataset)
        else:
            raise TypeError(
                f"Unsupported data type: {type(dataset).__name__}. "
                f"Expected list, xr.Dataset, xr.DataArray, or None."
            )

    if not datasets_list:
        return

    if layout is not None and groupby is None:
        raise ValueError("layout can only be used with grouped PDFs.")
    if groupby is not None and ax is not None:
        raise ValueError("ax cannot be supplied when plotting grouped PDFs.")

    das = []
    for dat in datasets_list:
        if groupby is None:
            dat = dat.squeeze()
        else:
            squeeze_dims = [
                dim for dim in dat.dims
                if dim != "time" and dat.sizes[dim] == 1
            ]
            dat = dat.squeeze(dim=squeeze_dims)

        if isinstance(dat, xr.Dataset):
            if var is None:
                raise ValueError("Specify variable with var='variable_name'")

            if var not in dat.data_vars:
                raise KeyError(
                    f"Variable {var!r} not in dataset. It contains: "
                    f"{list(dat.data_vars)}"
                )

            da = dat[var].copy(deep=False)
            das.append(da)

            if dat.attrs.get('label') is not None:
                da.attrs['label'] = dat.attrs['label']

        elif isinstance(dat, xr.DataArray):
            das.append(dat)

        else:
            raise TypeError(
                f"Data must be a Dataset or DataArray, not "
                f"{type(dat).__name__}"
            )

    if groupby is not None:
        _pdf_grouped_mode(
            das=das,
            var=var,
            groupby=groupby,
            layout=layout,
            nbins=nbins,
            range=range,
            nsamples=nsamples,
            xlim=xlim,
            yscale=yscale,
            size_inches=size_inches,
            gca_kwargs=gca_kwargs,
            gcf_kwargs=gcf_kwargs,
        )
        return

    _pdf_plot_single(
        *das,
        var=var,
        ax=ax,
        nbins=nbins,
        range=range,
        nsamples=nsamples,
        xlim=xlim,
        yscale=yscale,
        size_inches=(
            size_inches if size_inches is not None else (10, 5)
        ),
        gca_kwargs=gca_kwargs,
        gcf_kwargs=gcf_kwargs,
    )


def _pdf_auto_layout(n: int) -> tuple[int, int]:
    """Calculate subplot layout with maximum 2 columns.

    Parameters
    ----------
    n : int
        Number of subplots to arrange.

    Returns
    -------
    tuple[int, int]
        (nrows, ncols) for subplot grid.

    Examples
    --------
    >>> _pdf_auto_layout(12)  # months
    (6, 2)
    >>> _pdf_auto_layout(4)   # seasons
    (2, 2)
    >>> _pdf_auto_layout(5)   # custom
    (3, 2)
    """
    if n <= 1:
        return (1, 1)
    ncols = 2
    nrows = (n + 1) // 2
    return (nrows, ncols)


def _pdf_plot_single(
    *das: xr.DataArray,
    var: Union[str, None],
    ax: Union[matplotlib.axes.Axes, None],
    nbins: int,
    range: Union[tuple, None],
    nsamples: Union[int, None],
    xlim: Union[tuple, None],
    yscale: Union[str, None],
    size_inches: tuple[float, float] | None,
    gca_kwargs: Union[dict, None],
    gcf_kwargs: Union[dict, None],
) -> None:
    """Plot PDFs for one or more data arrays on the given axes.

    This is the core PDF plotting logic used by both the main pdf() function
    and by _pdf_grouped_mode() for multi-panel plots.

    Parameters
    ----------
    *das : xarray.DataArray
        Input data arrays, already selected and normalized by the caller.
    var : str or None
        Variable name used for the x-axis label when metadata is missing.
    ax : matplotlib.axes.Axes or None
        Axes on which to draw the plot.
    nbins : int
        Number of histogram bins.
    range : tuple or None
        Data range for histogram.
    nsamples : int or None
        Number of samples to draw.
    xlim : tuple or None
        X-axis limits.
    yscale : str or None
        Y-axis scale.
    size_inches : tuple of float or None
        Figure size. Leave as None to preserve the parent figure size.
    gca_kwargs : dict or None
        Additional axes kwargs.
    gcf_kwargs : dict or None
        Additional figure kwargs.
    """

    linestyles = itertools.cycle(["-", ":", "--", "-.",])
    colors = itertools.cycle(['black', 'blue', 'red', 'orange', 'green'])

    if ax is None:
        plt.clf()
    else:
        plt.sca(ax)

    current_yscale = yscale
    for idx, da in enumerate(das):
        histogram = _pdf_histogram(da, nbins, range, nsamples)
        if histogram is None:
            continue
        hist, bins = histogram

        all_finites = np.isfinite(hist).all()

        if not all_finites and yscale == 'log':
            current_yscale = 'linear'
        else:
            current_yscale = yscale

        plt.plot(
            bins,
            hist,
            label=da.attrs.get('label', f'Dataset {idx}'),
            linestyle=next(linestyles),
            color=next(colors),
        )
        plt.legend()

    if var is not None:
        if 'long_name' in das[0].attrs and 'units' in das[0].attrs:
            xlabel = f"{das[0].attrs['long_name']} [{das[0].attrs['units']}]"
        else:
            print(
                f"WARNING: {var} has no 'long_name' and/or 'units' "
                f"in attributes"
            )
            xlabel = f"{var}"

        plt.xlabel(xlabel)
        plt.ylabel('Probability')

    if xlim is not None:
        plt.xlim(xlim)

    if current_yscale is not None:
        plt.yscale(current_yscale)

    if size_inches is not None:
        plt.gcf().set_size_inches(size_inches)

    if gca_kwargs:
        plt.setp(plt.gca(), **gca_kwargs)

    if gcf_kwargs:
        plt.setp(plt.gcf(), **gcf_kwargs)


def _pdf_grouped_mode(
    das: list[Any],
    var: Union[str, None],
    groupby: str,
    layout: str | None,
    nbins: int,
    range: Union[tuple, None],
    nsamples: Union[int, None],
    xlim: Union[tuple, None],
    yscale: Union[str, None],
    size_inches: Union[tuple[float, float], None],
    gca_kwargs: Union[dict, None],
    gcf_kwargs: Union[dict, None],
) -> None:
    """Plot PDFs in a grid grouped by time.month or time.season.

    Parameters
    ----------
    das : list of xarray.DataArray
        DataArrays to plot.
    var : str or None
        Variable name.
    groupby : str
        Groupby expression ("time.month" or "time.season").
    layout : str or None
        Grid shorthand for the grouped panels.
    nbins : int
        Number of histogram bins.
    range : tuple or None
        Data range for histogram.
    nsamples : int or None
        Number of samples to draw.
    xlim : tuple or None
        X-axis limits.
    yscale : str or None
        Y-axis scale.
    size_inches : tuple or None
        Figure size in inches.
    gca_kwargs : dict or None
        Additional axes kwargs.
    gcf_kwargs : dict or None
        Additional figure kwargs.
    """
    plt.clf()

    if groupby not in {"time.month", "time.season"}:
        raise ValueError(
            "groupby must be 'time.month' or 'time.season'."
        )
    if not das:
        raise ValueError(
            "At least one data array is required for grouped PDFs."
        )
    for data_array in das:
        if "time" not in data_array.dims:
            raise ValueError("Grouped PDFs require a 'time' dimension.")

    grouped_das = [da.groupby(groupby) for da in das]

    group_counts = [len(grouped_da.groups) for grouped_da in grouped_das]
    period = groupby.rsplit(".", maxsplit=1)[-1]
    expected_groups = {"month": 12, "season": 4}[period]
    all_groups = set().union(
        *(set(grouped_da.groups) for grouped_da in grouped_das)
    )
    ordered_groups = _ordered_group_keys(groupby, all_groups)
    if not ordered_groups:
        raise ValueError("The input datasets contain no time groups.")

    if expected_groups is not None and any(
        count != expected_groups for count in group_counts
    ):
        logger.warning(
            "Expected %d groups for %s PDFs, but found group counts %s.",
            expected_groups,
            period,
            group_counts,
        )

    if layout is None:
        nrows, ncols = _pdf_auto_layout(expected_groups)
    else:
        nrows, ncols = _resolve_subplot_layout(
            layout,
            expected_groups,
            f"{period} PDF",
        )

    if size_inches is None:
        if groupby == "time.month":
            size_inches = (15, 20)
        elif groupby == "time.season":
            size_inches = (15, 15)
        else:
            size_inches = (15, 15)

    fig, axs = plt.subplots(nrows, ncols, squeeze=False)
    fig.set_size_inches(size_inches)
    flat_axes = axs.reshape(-1)

    for idx, group_name in enumerate(ordered_groups):
        group_das = [
            grouped_da[group_name]
            for grouped_da in grouped_das
            if group_name in grouped_da.groups
        ]
        cax = flat_axes[idx]
        _pdf_plot_single(
            *group_das,
            var=var,
            ax=cax,
            nbins=nbins,
            range=range,
            nsamples=nsamples,
            xlim=xlim,
            yscale=yscale,
            size_inches=None,
            gca_kwargs=gca_kwargs,
            gcf_kwargs=gcf_kwargs,
        )
        if groupby == "time.month":
            title = calendar.month_name[int(group_name)]
        else:
            title = str(group_name)
        cax.set_title(title)

    for cax in flat_axes[len(ordered_groups):]:
        cax.set_visible(False)

    if gcf_kwargs:
        plt.setp(plt.gcf(), **gcf_kwargs)


def mean_map(
    *datasets: xr.Dataset,
    var: str,
    ref: Union[xr.Dataset, None] = None,
    colorbar: bool = True,
    cmap: Union[str, matplotlib.colors.Colormap, None] = "viridis",
    norm: Union[matplotlib.colors.Normalize, None] = None,
    vmin: Union[float, None] = None,
    vmax: Union[float, None] = None,
    nrows: Union[int, None] = None,
    ncols: Union[int, None] = None,
    layout: str | None = None,
    draw_labels: bool = True,
    map_diagonal: float = 5.5,
    figure_kwargs: Union[dict, None] = None,
    pcolormesh_kwargs: Union[dict, None] = None,
    colorbar_kwargs: Union[dict, None] = None,
    gridlines_kwargs: Union[dict, None] = None,
    subplot_kwargs: Union[dict, None] = None,
    gca_kwargs: Union[dict, None] = None,
    gcf_kwargs: Union[dict, None] = None,
) -> None:
    """Map of the mean.

    Parameters
    ----------
    *datasets : xarray.Dataset
        The input dataset(s).
    var : str
        Variable name.
    ref : xarray.Dataset, optional
        The reference dataset. Defaults to None.
    colorbar : bool, optional
        Defaults to ``True``. If ``False``, the colorbar is omitted and
        colormaps for each plot are set independently.
    cmap : str, optional
        Colormap name or object. Defaults to ``"viridis"``.
    norm : matplotlib.colors.Normalize, optional
        Normalization for the colormap. If specified, it overrides vmin and
        vmax.
    vmin : float, optional
        Minimum data value for color scaling. Defaults to None.
    vmax : float, optional
        Maximum data value for color scaling. Defaults to None.
    nrows : int, optional
        Number of rows in the subplot grid. Defaults to None.
    ncols : int, optional
        Number of columns in the subplot grid. Defaults to None.
    layout : str, optional
        Grid shorthand such as ``"3x3"``, ``"x3"`` (three columns), or
        ``"4x"`` (four rows). Cannot be combined with ``nrows`` or ``ncols``.
    draw_labels : bool, optional
        Whether to draw gridline labels. Defaults to ``True``.
    map_diagonal : float, optional
        Diagonal size of each map axes in inches. Defaults to ``5.5``.
    figure_kwargs : dict, optional
        Keyword arguments passed to :func:`matplotlib.pyplot.figure`.
    pcolormesh_kwargs : dict, optional
        Keyword arguments passed to :func:`matplotlib.pyplot.pcolormesh`.
    colorbar_kwargs : dict, optional
        Keyword arguments passed to :func:`matplotlib.pyplot.colorbar`.
    gridlines_kwargs : dict, optional
        Keyword arguments passed to :func:`cartopy.mpl.gridliner.gridlines`.
    subplot_kwargs : dict, optional
        Keyword arguments passed to
        :meth:`matplotlib.figure.Figure.add_subplot`.
    gca_kwargs : dict, optional
        Keyword arguments passed to the active axes.
    gcf_kwargs : dict, optional
        Keyword arguments passed to the active figure.

    Returns
    -------
    None
        Displays a matplotlib figure with the mean map plot.

    Examples
    --------

    .. ipython::
       :okwarning:

       @savefig mean_map.png scale=70
       In [0]: %%time
          ...: import pyku
          ...: ds = pyku.resources.get_test_data('hyras-tas-monthly')
          ...: ds = ds.pyku.sort_georeferencing()
          ...: ds.vis.mean_map(var='tas')
    """

    from pyku import colormaps, meta

    for idx, ds in enumerate(datasets):
        if not isinstance(ds, xr.Dataset):
            raise TypeError(
                f"Dataset at index {idx} must be xarray.Dataset; "
                f"got {type(ds).__name__}."
            )
        if "time" not in ds.dims or ds.sizes["time"] == 0:
            raise ValueError(
                f"Dataset at index {idx} must have a non-empty 'time' "
                "dimension."
            )

    if not datasets:
        raise ValueError("At least one dataset must be provided.")

    for ds in datasets:

        if var not in meta.get_geodata_varnames(ds):
            raise KeyError(f"Variable '{var}' missing from dataset.")

    if cmap is None and var == 'pr':
        cmap = colormaps.get_cmap('precip_abs')

    das_mean = []

    for ds in datasets:

        ds_mean = (
            ds.isel(time=0).copy(deep=True)
            .drop_vars(ds.pyku.get_geodata_varnames())
        )

        da_mean = ds[var].mean('time', keep_attrs=True).compute()

        da_mean.attrs['long_name'] = f'mean {var}'
        da_mean.attrs['units'] = ds[var].attrs.get('units', None)

        ds_mean = xr.merge(
            [ds_mean, da_mean.to_dataset(name="mean")],
            combine_attrs="override",
            compat='no_conflicts'
        )

        das_mean.append(ds_mean)

    n_maps(
        *das_mean,
        var='mean',
        colorbar=colorbar,
        cmap=cmap,
        norm=norm,
        vmin=vmin,
        vmax=vmax,
        nrows=nrows,
        ncols=ncols,
        layout=layout,
        draw_labels=draw_labels,
        map_diagonal=map_diagonal,
        figure_kwargs=figure_kwargs,
        pcolormesh_kwargs=pcolormesh_kwargs,
        colorbar_kwargs=colorbar_kwargs,
        gridlines_kwargs=gridlines_kwargs,
        subplot_kwargs=subplot_kwargs,
        gca_kwargs=gca_kwargs,
        gcf_kwargs=gcf_kwargs,
    )


def metric_map(
    *datasets: xr.Dataset,
    ref: xr.Dataset,
    var: str,
    metric: str = "mae",
    groupby: Union[str, None] = None,
    colorbar: bool = True,
    cmap: Union[str, matplotlib.colors.Colormap, None] = None,
    norm: matplotlib.colors.Normalize = None,
    vmin: Union[float, None] = None,
    vmax: Union[float, None] = None,
    nrows: Union[int, None] = None,
    ncols: Union[int, None] = None,
    layout: str | None = None,
    draw_labels: bool = True,
    map_diagonal: float = 5.5,
    figure_kwargs: Union[dict, None] = None,
    pcolormesh_kwargs: Union[dict, None] = None,
    colorbar_kwargs: Union[dict, None] = None,
    gridlines_kwargs: Union[dict, None] = None,
    subplot_kwargs: Union[dict, None] = None,
    gca_kwargs: Union[dict, None] = None,
    gcf_kwargs: Union[dict, None] = None,
) -> None:
    """Map of evaluation metrics.

    Computes and plots evaluation metrics between one or more model datasets
    and a reference dataset for a specified variable. Supports multiple metrics
    and optional grouping by time (e.g., monthly or seasonal metrics).

    Parameters
    ----------
    *datasets : xarray.Dataset
        The input model dataset(s).
    ref : xarray.Dataset
        The reference dataset for comparison.
    var : str
        Variable name for which to compute the metric. Must exist in both
        model and reference datasets.
    metric : str, optional
        Evaluation metric. Options: ``'mae'`` (default), ``'bias'``,
        ``'mse'``, ``'rmse'``, ``'pcc'``.
    groupby : str, optional
        Groupby expression for multi-panel plots. Use ``"time.month"`` for
        monthly metrics (creates 6 rows × 2 columns) or ``"time.season"``
        for seasonal metrics (creates 2 rows × 2 columns). If None (default),
        produces a single plot.
    colorbar : bool, optional
        Defaults to ``True``. If ``False``, the colorbar is omitted and
        colormaps for each plot are set independently.
    cmap : str or matplotlib.colors.Colormap, optional
        Colormap name or object. Defaults to ``"viridis"`` for most metrics,
        ``"bwr"`` (diverging) for ``'bias'``.
    norm : matplotlib.colors.Normalize, optional
        Normalization for the colormap. If specified, it overrides vmin and
        vmax.
    vmin : float, optional
        Minimum data value for color scaling. Defaults to None.
    vmax : float, optional
        Maximum data value for color scaling. Defaults to None.
    nrows : int, optional
        Number of rows in the subplot grid. Defaults to None (auto-calculated
        for grouped mode).
    ncols : int, optional
        Number of columns in the subplot grid. Defaults to None.
    layout : str, optional
        Grid shorthand such as ``"3x3"``, ``"x3"`` (three columns), or
        ``"4x"`` (four rows). Cannot be combined with ``nrows`` or ``ncols``.
    draw_labels : bool, optional
        Whether to draw gridline labels. Defaults to ``True``.
    map_diagonal : float, optional
        Diagonal size of each map axes in inches. Defaults to ``5.5``.
    figure_kwargs : dict, optional
        Keyword arguments passed to :func:`matplotlib.pyplot.figure`.
    pcolormesh_kwargs : dict, optional
        Keyword arguments passed to :func:`matplotlib.pyplot.pcolormesh`.
    colorbar_kwargs : dict, optional
        Keyword arguments passed to :func:`matplotlib.pyplot.colorbar`.
    gridlines_kwargs : dict, optional
        Keyword arguments passed to :func:`cartopy.mpl.gridliner.gridlines`.
    subplot_kwargs : dict, optional
        Keyword arguments passed to
        :meth:`matplotlib.figure.Figure.add_subplot`.
    gca_kwargs : dict, optional
        Keyword arguments passed to the active axes.
    gcf_kwargs : dict, optional
        Keyword arguments passed to the active figure.

    Raises
    ------
    ValueError
        If ``var`` is None, if ``metric`` is not recognized, or if the
        reference dataset is missing the specified variable.
    TypeError
        If any dataset is not an :class:`xarray.Dataset` or if the reference
        is not an :class:`xarray.Dataset`.

    Returns
    -------
    None
        Displays a matplotlib figure with the metric map plot.

    Examples
    --------
    A single metric map and seasonal metric maps:

    .. ipython::
       :okwarning:

       @savefig metric_map.png scale=70
       In [0]: %%time
          ...: import pyku
          ...:
          ...: ref = (
          ...:     pyku.resources.get_test_data('hyras')
          ...:     .pyku.to_cmor_units()
          ...:     .pyku.set_time_labels_from_time_bounds(how='lower')
          ...:     .pyku.project('HYR-GER-LAEA-12.5')
          ...:     .sel(time='1981')
          ...: )
          ...:
          ...: ds = (
          ...:     pyku.resources.get_test_data('model_data')
          ...:     .pyku.project('HYR-GER-LAEA-12.5')
          ...:     .pyku.set_time_labels_from_time_bounds(how='lower')
          ...:     .sel(time='1981')
          ...: )
          ...:
          ...: ds.vis.metric_map(ref=ref, var='tas', metric='mae')
          ...:
          ...: ds.vis.metric_map(
          ...:     ref=ref, var='tas', metric='bias', groupby='time.season'
          ...: )
    """

    from pyku import meta

    valid_metrics = ['mae', 'bias', 'mse', 'rmse', 'pcc']
    if metric not in valid_metrics:
        raise ValueError(
            f"Invalid metric '{metric}'. Must be one of: {valid_metrics}"
        )

    if not datasets:
        raise ValueError("At least one model dataset must be provided.")

    for ds in datasets:
        if not isinstance(ds, xr.Dataset):
            raise TypeError(
                "Dataset item must be an xarray.Dataset, got "
                f"{type(ds).__name__}"
            )

        if var not in meta.get_geodata_varnames(ds):
            raise KeyError(f"Variable '{var}' missing from dataset.")

    if not isinstance(ref, xr.Dataset):
        raise TypeError(
            "Reference dataset must be an xarray.Dataset, "
            f"got {type(ref).__name__}"
        )

    if "time" not in ref.dims or ref.sizes["time"] == 0:
        raise ValueError(
            "Reference dataset must have a non-empty 'time' dimension."
        )
    if var not in meta.get_geodata_varnames(ref):
        raise KeyError(f"Variable '{var}' missing from reference dataset.")

    if cmap is None:
        cmap = 'bwr' if metric == 'bias' else 'viridis'

    if groupby is not None:
        _metric_grouped_mode(
            datasets=datasets,
            ref=ref,
            var=var,
            metric=metric,
            groupby=groupby,
            colorbar=colorbar,
            cmap=cmap,
            norm=norm,
            vmin=vmin,
            vmax=vmax,
            nrows=nrows,
            ncols=ncols,
            layout=layout,
            draw_labels=draw_labels,
            map_diagonal=map_diagonal,
            figure_kwargs=figure_kwargs,
            pcolormesh_kwargs=pcolormesh_kwargs,
            colorbar_kwargs=colorbar_kwargs,
            gridlines_kwargs=gridlines_kwargs,
            subplot_kwargs=subplot_kwargs,
            gca_kwargs=gca_kwargs,
            gcf_kwargs=gcf_kwargs,
        )
        return

    das_metric = []

    for ds in datasets:
        if "time" not in ds.dims or ds.sizes["time"] == 0:
            raise ValueError(
                "Every model dataset must have a non-empty 'time' "
                "dimension."
            )
        sel_ds, sel_ref = _select_metric_pair(ds, ref, var)

        if sel_ref.chunks or sel_ds.chunks:
            sel_ref = _ensure_single_time_chunk(sel_ref)
            sel_ds = _ensure_single_time_chunk(sel_ds)

        da_metric = _calculate_metric(
            sel_ds[var],
            sel_ref[var],
            metric,
        )
        das_metric.append(_metric_result_dataset(sel_ds, da_metric, metric))

    n_maps(
        *das_metric,
        var=metric,
        colorbar=colorbar,
        cmap=cmap,
        norm=norm,
        vmin=vmin,
        vmax=vmax,
        nrows=nrows,
        ncols=ncols,
        layout=layout,
        draw_labels=draw_labels,
        map_diagonal=map_diagonal,
        figure_kwargs=figure_kwargs,
        pcolormesh_kwargs=pcolormesh_kwargs,
        colorbar_kwargs=colorbar_kwargs,
        gridlines_kwargs=gridlines_kwargs,
        subplot_kwargs=subplot_kwargs,
        gca_kwargs=gca_kwargs,
        gcf_kwargs=gcf_kwargs,
    )


def _metric_grouped_mode(
    datasets: tuple[xr.Dataset, ...],
    ref: xr.Dataset,
    var: str,
    metric: str,
    groupby: str,
    colorbar: bool = True,
    cmap: Union[str, matplotlib.colors.Colormap, None] = None,
    norm: Union[matplotlib.colors.Normalize, None] = None,
    vmin: Union[float, None] = None,
    vmax: Union[float, None] = None,
    nrows: Union[int, None] = None,
    ncols: Union[int, None] = None,
    layout: str | None = None,
    draw_labels: bool = True,
    map_diagonal: float = 5.5,
    figure_kwargs: Union[dict, None] = None,
    pcolormesh_kwargs: Union[dict, None] = None,
    colorbar_kwargs: Union[dict, None] = None,
    gridlines_kwargs: Union[dict, None] = None,
    subplot_kwargs: Union[dict, None] = None,
    gca_kwargs: Union[dict, None] = None,
    gcf_kwargs: Union[dict, None] = None,
) -> None:
    """Plot evaluation metrics grouped by time (monthly/seasonal)."""

    if groupby == 'time.month':
        n_plots = 12
        default_layout = (6, 2)
    elif groupby == 'time.season':
        n_plots = 4
        default_layout = (2, 2)
    else:
        raise ValueError(
            f"Unsupported groupby: {groupby}. "
            "Must be 'time.month' or 'time.season'."
        )

    if layout is not None and (nrows is not None or ncols is not None):
        raise ValueError(
            "'layout' cannot be combined with 'nrows' or 'ncols'."
        )
    if layout is None and nrows is None and ncols is None:
        ncols = default_layout[1]
        nrows = math.ceil(n_plots * len(datasets) / ncols)

    if map_diagonal <= 0:
        raise ValueError("'map_diagonal' must be greater than zero.")

    figure_kwargs = figure_kwargs or {}
    pcolormesh_kwargs = pcolormesh_kwargs or {}
    colorbar_kwargs = colorbar_kwargs or {}
    gridlines_kwargs = gridlines_kwargs or {}
    subplot_kwargs = subplot_kwargs or {}
    gca_kwargs = gca_kwargs or {}
    gcf_kwargs = gcf_kwargs or {}

    if cmap is None:
        cmap = 'bwr' if metric == 'bias' else 'viridis'

    if not datasets:
        raise ValueError("At least one model dataset must be provided.")

    results = []

    for ds in datasets:
        if "time" not in ds.dims or ds.sizes["time"] == 0:
            raise ValueError(
                "Every model dataset must have a non-empty 'time' "
                "dimension."
            )
        sel_ds, sel_ref = _select_metric_pair(ds, ref, var)

        grp_ref = sel_ref.groupby(groupby)
        grp_ds = sel_ds.groupby(groupby)

        common_groups = grp_ds.groups.keys() & grp_ref.groups.keys()
        groups = _ordered_group_keys(groupby, common_groups)
        if not groups:
            raise ValueError(
                "The model and reference have no common calendar groups."
            )
        if len(groups) != n_plots:
            logger.warning(
                "Expected %d groups for %s metric maps, but found %d.",
                n_plots,
                groupby.rsplit(".", maxsplit=1)[-1],
                len(groups),
            )
        if len(grp_ref.groups) != n_plots:
            logger.warning(
                "Expected %d groups in the reference for %s metric maps, "
                "but found %d.",
                n_plots,
                groupby.rsplit(".", maxsplit=1)[-1],
                len(grp_ref.groups),
            )

        for key in groups:

            da = grp_ds[key][var]
            da_ref_group = grp_ref[key][var]
            if da.chunks or da_ref_group.chunks:
                da = _ensure_single_time_chunk(da)
                da_ref_group = _ensure_single_time_chunk(da_ref_group)

            da_metric = _calculate_metric(
                da,
                da_ref_group,
                metric,
            )

            if groupby == "time.month":
                label = calendar.month_name[int(key)]
            else:
                label = str(key)

            results.append(
                _metric_result_dataset(sel_ds, da_metric, metric, label)
            )

    n_maps(
        *results,
        var=metric,
        colorbar=colorbar,
        cmap=cmap,
        norm=norm,
        vmin=vmin,
        vmax=vmax,
        nrows=nrows,
        ncols=ncols,
        layout=layout,
        draw_labels=draw_labels,
        map_diagonal=map_diagonal,
        figure_kwargs=figure_kwargs,
        pcolormesh_kwargs=pcolormesh_kwargs,
        colorbar_kwargs=colorbar_kwargs,
        gridlines_kwargs=gridlines_kwargs,
        subplot_kwargs=subplot_kwargs,
        gca_kwargs=gca_kwargs,
        gcf_kwargs=gcf_kwargs,
    )


def bias_cycle(
    ds: xr.Dataset,
    ref: xr.Dataset,
    var: str,
    groupby: Literal["time.month", "time.season"] = "time.month",
    gdf: geopandas.GeoDataFrame | None = None,
    layout: str | None = None,
    ax: Axes | None = None,
    size_inches: tuple[float, float] | None = None,
    ylim: tuple[float, float] | None = None,
    yscale: str | None = None,
    gca_kwargs: dict[str, Any] | None = None,
    gcf_kwargs: dict[str, Any] | None = None,
) -> None:
    """Plot monthly or seasonal mean bias, optionally for each region.

    The bias is calculated as ``ds - ref`` and averaged over space and time
    within each month or season. Supplying a GeoDataFrame creates one panel
    per region.

    Parameters
    ----------
    ds : xarray.Dataset
        Model dataset containing ``var`` and a time coordinate.
    ref : xarray.Dataset
        Reference dataset containing ``var`` and a time coordinate.
    var : str
        Name of the variable to compare.
    groupby : {"time.month", "time.season"}, default "time.month"
        Time grouping used to calculate the bias cycle.
    gdf : geopandas.GeoDataFrame, optional
        Regions to plot separately. The area definition is inferred from the
        input datasets.
    layout : str, optional
        Grid shorthand for regional panels, such as ``"3x3"``, ``"x3"``, or
        ``"4x"``. Can only be used when ``gdf`` is provided.
    ax : matplotlib.axes.Axes, optional
        Axes on which to draw a non-regional plot. Cannot be combined with
        ``gdf``.
    size_inches : tuple of float, optional
        Figure size in inches (width, height). Defaults to (10, 7) for a
        single plot and (20, number_of_rows * 7) for regional plots.
    ylim : tuple of float, optional
        Y-axis limits, for example ``(-2, 2)``.
    yscale : str, optional
        Y-axis scale, for example ``"linear"`` or ``"log"``.
    gca_kwargs : dict, optional
        Additional keyword arguments applied to each axes.
    gcf_kwargs : dict, optional
        Additional keyword arguments applied to the figure.

    Raises
    ------
    ValueError
        If ``groupby`` is unsupported, a required variable or time coordinate
        is missing, the datasets have no common times or matching spatial
        coordinates, or ``ax`` is combined with ``gdf``.
    TypeError
        If either input is not an :class:`xarray.Dataset`.

    Returns
    -------
    None
        Displays a matplotlib figure with the bias cycle.

    Examples
    --------
    Plot a monthly cycle:

    .. ipython::
       :okwarning:

       @savefig bias_cycle.png scale=70
       In [0]: %%time
          ...: import pyku
          ...: ref = pyku.resources.get_test_data('hyras')
          ...: ref = (
          ...:     ref.pyku.to_cmor_units()
          ...:     .pyku.set_time_labels_from_time_bounds(how='lower')
          ...:     .pyku.project('HYR-LAEA-50')
          ...:     .sel(time='1981')
          ...: )
          ...: ds = pyku.resources.get_test_data('model_data')
          ...: ds = (
          ...:     ds.pyku.project('HYR-LAEA-50')
          ...:     .pyku.set_time_labels_from_time_bounds(how='lower')
          ...:     .sel(time='1981')
          ...: )
          ...: ds.vis.bias_cycle(ref, var='tas')

    Plot a seasonal cycle for each region:

    .. ipython::
       :okwarning:

       @savefig bias_cycle_regions.png width=100%
       In [0]: %%time
          ...: import pyku
          ...: ref = pyku.resources.get_test_data('hyras')
          ...: ref = (
          ...:     ref.pyku.to_cmor_units()
          ...:     .pyku.set_time_labels_from_time_bounds(how='lower')
          ...:     .pyku.project('HYR-LAEA-50')
          ...:     .sel(time='1981')
          ...: )
          ...: ds = pyku.resources.get_test_data('model_data')
          ...: ds = (
          ...:     ds.pyku.project('HYR-LAEA-50')
          ...:     .pyku.set_time_labels_from_time_bounds(how='lower')
          ...:     .sel(time='1981')
          ...: )
          ...: regions = pyku.resources.get_geodataframe(
          ...:     'natural_areas_of_germany'
          ...: ).head(3)
          ...: ds.vis.bias_cycle(
          ...:     ref, var='tas', groupby='time.season', gdf=regions
          ...: )
    """

    from pyku import features, timekit

    if groupby not in {"time.month", "time.season"}:
        raise ValueError(
            "groupby must be 'time.month' or 'time.season'."
        )
    if gdf is not None and ax is not None:
        raise ValueError("ax cannot be supplied when plotting regions.")
    if layout is not None and gdf is None:
        raise ValueError("layout can only be used when plotting regions.")
    if not isinstance(ds, xr.Dataset) or not isinstance(ref, xr.Dataset):
        raise TypeError("ds and ref must be xarray.Dataset instances.")
    if var not in ds.data_vars:
        raise ValueError(f"Variable '{var}' is missing from ds.")
    if var not in ref.data_vars:
        raise ValueError(f"Variable '{var}' is missing from ref.")
    if "time" not in ds.dims or "time" not in ref.dims:
        raise ValueError("Both datasets must have a non-empty time dimension.")
    if ds.sizes["time"] == 0 or ref.sizes["time"] == 0:
        raise ValueError("Both datasets must have a non-empty time dimension.")
    _validate_spatial_coordinates(ds, ref, var)

    if gdf is not None:
        if not isinstance(gdf, geopandas.GeoDataFrame):
            raise TypeError("gdf must be a geopandas.GeoDataFrame.")
        ds = features.regionalize(ds, gdf, dtype="xr.Dataset")
        ref = features.regionalize(ref, gdf, dtype="xr.Dataset")
        regions = ds.region.values
        if len(regions) == 0:
            raise ValueError("gdf must contain at least one region.")
        if layout is None:
            number_of_cols = 3
            number_of_rows = (len(regions) + number_of_cols - 1) // (
                number_of_cols
            )
        else:
            number_of_rows, number_of_cols = _resolve_subplot_layout(
                layout,
                len(regions),
                "regional bias-cycle",
            )
        if size_inches is None:
            size_inches = (20, number_of_rows * 7)
        plt.clf()
        fig, axes = plt.subplots(
            number_of_rows,
            number_of_cols,
            squeeze=False,
        )
        axes_flat = axes.reshape(-1)
        for unused_ax in axes_flat[len(regions):]:
            unused_ax.set_visible(False)
        plot_axes = list(zip(regions, axes_flat, strict=False))
    else:
        if ax is None:
            plt.clf()
            ax = plt.gca()
        else:
            plt.sca(ax)
        fig = ax.figure
        if size_inches is None:
            size_inches = (10, 7)
        plot_axes = [(None, ax)]

    fig.set_size_inches(size_inches)
    period_name = groupby.rsplit(".", maxsplit=1)[-1]
    season_order = {"DJF": 0, "MAM": 1, "JJA": 2, "SON": 3}

    for region, plot_ax in plot_axes:
        ds_region = ds.sel(region=region) if region is not None else ds
        ref_region = ref.sel(region=region) if region is not None else ref
        da_mod = ds_region[var]
        da_ref = ref_region[var]
        inter_mod, inter_ref = timekit.select_common_datetimes(
            da_mod,
            da_ref,
        )
        if inter_mod.sizes.get("time", 0) == 0:
            raise ValueError(
                "The intersection of the datasets resulted in an empty "
                "time dimension."
            )

        bias = inter_mod - inter_ref
        grouped_bias = (
            bias.groupby(groupby)
            .mean(tuple(bias.dims), method="cohorts")
            .compute()
        )
        periods = grouped_bias[period_name].values
        values = np.asarray(grouped_bias.values).reshape(-1)
        order = list(range(len(periods)))
        if period_name == "season":
            order.sort(key=lambda idx: season_order[str(periods[idx])])
            labels = [str(periods[idx]) for idx in order]
        else:
            order.sort(key=lambda idx: int(periods[idx]))
            labels = [calendar.month_name[int(periods[idx])] for idx in order]
        values = values[order]
        positions = np.arange(len(values))

        plot_ax.bar(
            positions,
            np.where(values >= 0, values, np.nan),
            color="red",
        )
        plot_ax.bar(
            positions,
            np.where(values < 0, values, np.nan),
            color="blue",
        )
        plot_ax.set_ylabel(f"Mean bias for {var}")
        plot_ax.set_xticks(positions, labels)
        plot_ax.tick_params(axis="x", labelrotation=45)
        plot_ax.set_xlabel(None)

        if ylim is not None:
            plot_ax.set_ylim(ylim)
        if yscale is not None:
            plot_ax.set_yscale(yscale)
        if gca_kwargs:
            plt.setp(plot_ax, **gca_kwargs)
        if region is not None:
            plot_ax.set_title(str(region))

    if gcf_kwargs:
        plt.setp(fig, **gcf_kwargs)


def diurnal_cycle(
    *datasets: xr.Dataset,
    var: Union[str, None] = None,
    ax: Union[matplotlib.axes.Axes, None] = None,
    size_inches: Union[tuple[float, float], None] = None,
    ylim: Union[tuple[float, float], None] = None,
    yscale: Union[str, None] = None,
    fig_kwargs: Union[dict, None] = None,
    ax_kwargs: Union[dict, None] = None,
    title_kwargs: Union[dict, None] = None,
    groupby: Union[str, None] = None,
    layout: str | None = None,
    variability: bool = False,
    gca_kwargs: Union[dict, None] = None,
    gcf_kwargs: Union[dict, None] = None,
) -> None:
    """Plot diurnal cycles for one or two datasets.

    By default, plots the mean value for each hour of the day. Set ``groupby``
    to ``"time.month"`` or ``"time.season"`` to create one subplot per
    period. Set ``variability=True`` to show hourly value distributions with
    box plots, optionally comparing two datasets.

    At most two datasets may be supplied. Two datasets in the default or
    grouped mode are plotted as separate mean cycles.

    Parameters
    ----------
    *datasets : xarray.Dataset
        One or two input datasets.
    var : str
        The variable name.
    ax : matplotlib.axes.Axes, optional
        Axes on which to draw the plot. If None, a new figure
        is created.
    size_inches : tuple of float, optional
        Figure size in inches (width, height). Defaults to
        (7, 5) when a new figure is created; when ``ax`` is
        given, applied to ``ax.figure``.
    ylim : tuple of float, optional
        Y-axis limits, e.g. (0, 15).
    yscale : str, optional
        Y-axis scale, e.g. 'log' or 'linear'.
    fig_kwargs : dict, optional
        Keyword arguments applied to the figure, e.g.
        ``{'dpi': 150, 'facecolor': 'white'}``.
    ax_kwargs : dict, optional
        Keyword arguments applied to the axes, e.g.
        ``{'grid': True}``.
    title_kwargs : dict, optional
        Keyword arguments passed to ``ax.set_title()`` for the
        'Diurnal cycle' title, e.g. ``{'fontsize': 14}``.
    groupby : {None, "time.month", "time.season"}, optional
        If provided, create a subplot for each month or season.
    layout : str, optional
        Grid shorthand for grouped plots, such as ``"3x3"``, ``"x3"``, or
        ``"4x"``. Can only be used with ``groupby`` and not ``variability``.
    variability : bool, default False
        If True, plot hourly box plots for one dataset or compare two.
    gca_kwargs : dict, optional
        Keyword arguments applied to the active axes.
    gcf_kwargs : dict, optional
        Keyword arguments applied to the active figure.

    Returns
    -------
    None
        Displays a matplotlib figure with the diurnal cycle plot.

    Raises
    ------
    ValueError
        If no dataset is provided, more than two datasets are supplied,
        ``var`` is missing or unavailable, or mode options are invalid.
    TypeError
        If an input is not an ``xarray.Dataset``.

    Examples
    --------
    .. ipython::

        @savefig diurnal_cycle.png scale=70
        In [0]: %%time
           ...: import pyku
           ...:
           ...: # Get 7 days of hourly tas data on HYR-GER-LAEA-50 grid
           ...: ds = pyku.resources.get_test_data('7day-low-res-hourly-tas')
           ...:
           ...: # Plot
           ...: ds.vis.diurnal_cycle(var='tas')
    """

    if len(datasets) == 0:
        raise ValueError("At least one dataset must be provided.")
    if len(datasets) > 2:
        raise ValueError("diurnal_cycle accepts at most two datasets.")
    if not all(isinstance(dataset, xr.Dataset) for dataset in datasets):
        raise TypeError("All inputs must be xarray.Dataset instances.")
    if variability and groupby is not None:
        raise ValueError("variability and groupby cannot be used together.")
    if groupby is not None and ax is not None:
        raise ValueError("ax cannot be supplied when plotting grouped cycles.")
    if layout is not None and (groupby is None or variability):
        raise ValueError(
            "layout can only be used for grouped diurnal cycles."
        )

    if var is None:
        raise ValueError("Specify a variable with var='variable_name'.")
    for dataset in datasets:
        if var not in dataset.data_vars:
            raise ValueError(
                f"Variable {var!r} is not present in an input dataset."
            )
        if "time" not in dataset.dims or dataset.sizes["time"] == 0:
            raise ValueError(
                "Every input dataset must have a non-empty 'time' "
                "dimension."
            )

    if variability:
        _diurnal_cycle_variability(
            datasets[0], datasets[1] if len(datasets) == 2 else None,
            var=var, ax=ax, size_inches=size_inches,
            ylim=ylim, yscale=yscale, gca_kwargs=gca_kwargs,
            gcf_kwargs=gcf_kwargs, fig_kwargs=fig_kwargs,
            ax_kwargs=ax_kwargs, title_kwargs=title_kwargs,
        )
        return

    if groupby is not None:
        if groupby not in {"time.month", "time.season"}:
            raise ValueError("groupby must be 'time.month' or 'time.season'.")
        _diurnal_cycle_by_period(
            *datasets,
            var=var,
            freq=groupby.rsplit(".", maxsplit=1)[-1],
            layout=layout,
            size_inches=size_inches,
            ylim=ylim,
            yscale=yscale,
            fig_kwargs=fig_kwargs,
            ax_kwargs=ax_kwargs,
            title_kwargs=title_kwargs,
        )
        return

    if ax is None:
        plt.clf()
        if size_inches is None:
            size_inches = (7, 5)
        plt.gcf().set_size_inches(size_inches)
    else:
        plt.sca(ax)
        if size_inches is not None:
            ax.figure.set_size_inches(size_inches)

    if fig_kwargs:
        plt.setp(plt.gcf(), **fig_kwargs)

    das = []
    for dat in datasets:
        if dat is None:
            continue

        dat = dat.squeeze(
            dim=[
                dim for dim in dat.dims
                if dim != "time" and dat.sizes[dim] == 1
            ]
        )

        if isinstance(dat, xr.Dataset):
            if var not in dat.data_vars:
                raise KeyError(
                    f"Variable {var!r} not in dataset. It contains: "
                    f"{list(dat.data_vars)}"
                )

            da = dat[var].copy(deep=False)
            das.append(da)

            if dat.attrs.get('label') is not None:
                da.attrs['label'] = dat.attrs['label']

        else:
            raise TypeError(
                f"Expected xr.Dataset, got {type(dat).__name__}"
            )

    if not das:
        return

    linestyles = itertools.cycle(["-", ":", "--", "-.",])
    markers = itertools.cycle(["s", "o", "D", "v", "^",])
    fillstyles = itertools.cycle(["none", "full", "left"])
    colors = itertools.cycle(['black', 'blue', 'red', 'orange', 'green'])

    for idx, da in enumerate(das):

        p = (
            da
            .groupby('time.hour')
            .mean(
                dim=tuple(da.dims),
                keep_attrs=True,
                method="cohorts"
            )
            .compute()
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

    plt.gca().set_xticks(ticks=list(np.arange(0, 24)))
    plt.gca().set_xticklabels(list(np.arange(0, 24)))
    plt.gca().tick_params(axis='x', which='both', length=0)
    plt.xticks(rotation=0)
    plt.gca().set_xlabel(None)

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

    if ylim is not None:
        plt.ylim(ylim)
    if yscale is not None:
        plt.yscale(yscale)

    plt.legend(loc='best', ncol=1, shadow=True, fancybox=True)

    plt.gca().set_title('Diurnal cycle', **(title_kwargs or {}))

    if ax_kwargs:
        current_ax = plt.gca()
        valid_props = set(
            matplotlib.artist.Artist.properties(current_ax).keys()
        )
        plt.setp(
            current_ax,
            **{k: v for k, v in ax_kwargs.items() if k in valid_props}
        )

    if gca_kwargs:
        plt.setp(plt.gca(), **gca_kwargs)

    if gcf_kwargs:
        plt.setp(plt.gcf(), **gcf_kwargs)


def _diurnal_cycle_by_period(
    *datasets: xr.Dataset,
    var: Union[str, None] = None,
    freq: str = "month",
    layout: str | None = None,
    size_inches: Union[tuple[float, float], None] = None,
    ylim: Union[tuple[float, float], None] = None,
    yscale: Union[str, None] = None,
    fig_kwargs: Union[dict, None] = None,
    ax_kwargs: Union[dict, None] = None,
    title_kwargs: Union[dict, None] = None,
) -> None:
    """Diurnal cycle mean broken down by period (month or season).

    Calculates the diurnal cycle for each period of each input
    dataset and plots one subplot per period in a grid of
    subplots (4 rows x 3 columns for 'month', 2x2 for 'season').

    Parameters
    ----------
    *datasets : xarray.Dataset
        One or more xarray Datasets to plot (e.g. a model run,
        observations, ensemble members).
    var : str, optional
        Variable name to plot.
    freq : {'month', 'season'}, default 'month'
        Grouping frequency for the subplots.
    layout : str, optional
        Grid shorthand for the grouped panels.
    size_inches : tuple of float, optional
        Figure size in inches (width, height). Defaults to
        (30, 20) for 'month' and (15, 10) for 'season'.
    ylim : tuple of float, optional
        Y-axis limits, e.g. (0, 15). Passed to the downstream
        diurnal_cycle.
    yscale : str, optional
        Y-axis scale (e.g. 'log', 'linear'). Passed to the
        downstream diurnal_cycle.
    fig_kwargs : dict, optional
        Additional keyword arguments passed directly to
        ``plt.subplots()``.
    ax_kwargs : dict, optional
        Keyword arguments applied to each subplot's axes, e.g.
        ``{'grid': True}``.
    title_kwargs : dict, optional
        Keyword arguments passed to ``ax.set_title()`` for the
        subplot titles, e.g. ``{'fontsize': 14}``.

    Returns
    -------
    None
        Displays a matplotlib figure with the diurnal cycle by period
        plot.

    Raises
    ------
    ValueError
        If no dataset is provided, if ``freq`` is not 'month' or
        'season', or if ``var`` is not in a dataset.
    TypeError
        If an input is not an ``xarray.Dataset``.

    See Also
    --------
    diurnal_cycle
        Diurnal cycle over the full period.

    Examples
    --------
    .. ipython::

        @savefig diurnal_cycle_by_period.png scale=70
        In [0]: %%time
           ...: import pyku
           ...: ds = pyku.resources.get_test_data('low-res-hourly-pr-data')
            ...: ds.vis.diurnal_cycle(
            ...:     var='RR', groupby='time.month', ylim=(0, 15)
           ...: )
    """

    if len(datasets) == 0:
        raise ValueError("At least one dataset must be provided.")

    if freq not in ("month", "season"):
        raise ValueError(f"freq must be 'month' or 'season', got '{freq}'")

    if size_inches is None:
        size_inches = (30, 20) if freq == "month" else (15, 10)

    validated_ds = []
    for ds in datasets:
        ds_squeezed = ds.squeeze(
            dim=[
                dim for dim in ds.dims
                if dim != "time" and ds.sizes[dim] == 1
            ]
        )
        if not isinstance(ds_squeezed, xr.Dataset):
            raise TypeError(
                f"Expected xr.Dataset, got {type(ds_squeezed).__name__}"
            )
        if var is not None and var not in ds_squeezed.data_vars:
            raise ValueError(
                f"Variable '{var}' not in dataset. Available variables: "
                f"{list(ds_squeezed.data_vars)}"
            )
        if "time" not in ds_squeezed.dims or ds_squeezed.sizes["time"] == 0:
            raise ValueError(
                "Every input dataset must have a non-empty 'time' "
                "dimension."
            )
        validated_ds.append(ds_squeezed)

    group_key = f"time.{freq}"
    groups = [ds.groupby(group_key) for ds in validated_ds]

    expected_groups = 12 if freq == "month" else 4
    group_counts = [len(grouped.groups) for grouped in groups]
    if any(count != expected_groups for count in group_counts):
        logger.warning(
            "Expected %d groups for %s diurnal cycles, but found group "
            "counts %s.",
            expected_groups,
            freq,
            group_counts,
        )
    if layout is None:
        nrows, ncols = (4, 3) if freq == "month" else (2, 2)
    else:
        nrows, ncols = _resolve_subplot_layout(
            layout,
            expected_groups,
            f"{freq} diurnal-cycle",
        )
    sub_kwargs = fig_kwargs.copy() if fig_kwargs else {}
    sub_kwargs.setdefault("figsize", size_inches)
    sub_kwargs["squeeze"] = False

    _fig, axs = plt.subplots(nrows, ncols, **sub_kwargs)
    flat_axs = axs.reshape(-1)

    all_group_keys = set().union(
        *(set(grouped.groups) for grouped in groups)
    )
    ordered_group_keys = _ordered_group_keys(group_key, all_group_keys)

    for idx, key in enumerate(ordered_group_keys):
        cax = flat_axs[idx]
        selected_slices = [
            grouped[key] for grouped in groups if key in grouped.groups
        ]

        # Figure sizing and subplot titles are handled by this parent function.
        diurnal_cycle(
            *selected_slices,
            var=var,
            ax=cax,
            ylim=ylim,
            yscale=yscale,
            ax_kwargs=ax_kwargs,
        )

        if freq == "month":
            title = calendar.month_name[int(key)]
        else:
            title = str(key)

        cax.set_title(title, **(title_kwargs or {}))

    for cax in flat_axs[len(ordered_group_keys):]:
        cax.set_visible(False)


def variability(
    *datasets: xr.Dataset,
    var: str,
    groupby: Literal["time.month", "time.season"] = "time.month",
    gdf: geopandas.GeoDataFrame | None = None,
    layout: str | None = None,
    ax: matplotlib.axes.Axes | None = None,
    size_inches: tuple[float, float] | None = None,
    gca_kwargs: dict | None = None,
    gcf_kwargs: dict | None = None,
) -> None:
    """Plot monthly, seasonal, or regional variability for one or two datasets.

    With no ``gdf``, the data are grouped by month by default. Set
    ``groupby="time.season"`` to plot seasonal variability. Supplying a
    ``GeoDataFrame`` selects regional monthly variability and creates one
    subplot per region. At most two datasets can be compared.

    Parameters
    ----------
    *datasets : xarray.Dataset
        One or two input datasets.
    var : str
        Name of the variable to plot.
    groupby : {"time.month", "time.season"}, optional
        Temporal grouping for non-regional plots. Defaults to monthly
        variability. Cannot be combined with ``gdf``.
    gdf : geopandas.GeoDataFrame, optional
        Regions used to calculate and plot regional monthly variability.
    layout : str, optional
        Grid shorthand for regional panels, such as ``"3x3"``, ``"x3"``, or
        ``"4x"``. Can only be used when ``gdf`` is provided.
    ax : matplotlib.axes.Axes, optional
        Axes for a non-regional plot. Regional mode creates its own axes.
    size_inches : tuple of float, optional
        Figure size in inches (width, height). Defaults to (12, 5) for
        non-regional plots and (20, number_of_rows * 7) for regional plots.
    gca_kwargs : dict, optional
        Additional keyword arguments applied to each plot's axes.
    gcf_kwargs : dict, optional
        Additional keyword arguments applied to the figure.

    Returns
    -------
    None
        Displays a matplotlib figure with the variability plot.

    Raises
    ------
    ValueError
        If the number of datasets is not one or two, a variable is missing,
        an option is invalid, or regional and temporal grouping are combined.
    TypeError
        If a dataset is not an ``xarray.Dataset`` or ``gdf`` is not a
        ``geopandas.GeoDataFrame``.

    Examples
    --------
    .. ipython::

        @savefig variability.png scale=70
        In [0]: %%time
           ...: import pyku
           ...: ds = pyku.resources.get_test_data('hyras_tas')
           ...: ds.vis.variability(var='tas')

    .. ipython::

        @savefig regional_variability.png width=100%
        In [1]: regions = (
           ...:     pyku.resources
           ...:     .get_geodataframe('natural_areas_of_germany')
           ...:     .head(3)
           ...: )
           ...: ds.vis.variability(var='tas', gdf=regions)
    """

    if not 1 <= len(datasets) <= 2:
        raise ValueError("variability accepts one or two datasets.")
    if not all(isinstance(dataset, xr.Dataset) for dataset in datasets):
        raise TypeError("All inputs must be xarray.Dataset instances.")
    if gdf is not None and not isinstance(gdf, geopandas.GeoDataFrame):
        raise TypeError("gdf must be a geopandas.GeoDataFrame.")
    if groupby not in ("time.month", "time.season"):
        raise ValueError(
            "groupby must be 'time.month' or 'time.season'."
        )
    if gdf is not None and groupby != "time.month":
        raise ValueError(
            "gdf and non-monthly grouping cannot be used together."
        )
    if gdf is not None and ax is not None:
        raise ValueError("ax cannot be supplied when plotting regions.")
    if layout is not None and gdf is None:
        raise ValueError("layout can only be used when plotting regions.")

    for dataset in datasets:
        if var not in dataset.data_vars:
            raise ValueError(
                f"Variable '{var}' not in dataset. Available variables: "
                f"{list(dataset.data_vars)}"
            )

    if gdf is not None:
        from pyku import features

        regional_datasets = [
            features.regionalize(dataset, gdf) for dataset in datasets
        ]
        number_of_regions = len(regional_datasets[0].region)
        if number_of_regions == 0:
            raise ValueError("gdf must contain at least one region.")

        if layout is None:
            number_of_cols = 3
            number_of_rows = (number_of_regions + number_of_cols - 1) // (
                number_of_cols
            )
        else:
            number_of_rows, number_of_cols = _resolve_subplot_layout(
                layout,
                number_of_regions,
                "regional variability",
            )
        if size_inches is None:
            size_inches = (20, number_of_rows * 7)
        _fig, axs = plt.subplots(
            number_of_rows,
            number_of_cols,
            figsize=size_inches,
            squeeze=False,
        )
        flat_axes = axs.reshape(-1)

        for idx, cax in enumerate(flat_axes):
            if idx >= number_of_regions:
                cax.set_visible(False)
                continue

            region = regional_datasets[0].region.values[idx]
            selected_datasets = [
                dataset.sel(region=region) for dataset in regional_datasets
            ]
            variability(
                *selected_datasets,
                var=var,
                ax=cax,
                gca_kwargs=gca_kwargs,
            )

            lower_columns = {
                str(column).lower(): column for column in gdf.columns
            }
            if "name" in lower_columns:
                cax.set_title(str(region))
            elif "short_name" in lower_columns:
                cax.set_title(str(gdf.iloc[idx][lower_columns["short_name"]]))
            else:
                cax.set_title(str(idx))

        if gcf_kwargs:
            plt.setp(plt.gcf(), **gcf_kwargs)
        return

    frequency = groupby
    is_monthly = frequency == "time.month"
    if is_monthly:
        periods: tuple[int | str, ...] = tuple(range(1, 13))
        period_labels = list(calendar.month_name[1:])
        colors = ("blue", "black")
        rotation = 45
    else:
        periods = ("DJF", "MAM", "JJA", "SON")
        period_labels = list(periods)
        colors = ("blue", "black")
        rotation = 0

    resize_figure = ax is None or size_inches is not None
    if ax is None:
        plt.clf()
    else:
        plt.sca(ax)
    if size_inches is None:
        size_inches = (12, 5)
    if resize_figure:
        plt.gcf().set_size_inches(size_inches)
    if gcf_kwargs:
        plt.setp(plt.gcf(), **gcf_kwargs)

    current_ax = plt.gca() if ax is None else ax
    patches = []
    first_da: xr.DataArray | None = None

    for dataset_idx, dataset in enumerate(datasets):
        data_array = dataset[var]
        if "time" not in data_array.dims:
            raise ValueError(f"Variable '{var}' must have a 'time' dimension.")
        spatial_dims = [dim for dim in data_array.dims if dim != "time"]
        if spatial_dims:
            data_array = data_array.mean(spatial_dims, keep_attrs=True)
        if first_da is None:
            first_da = data_array

        data_array = data_array.compute()
        values = np.asarray(data_array.values).reshape(-1)
        group_component = frequency.rsplit(".", maxsplit=1)[-1]
        time_groups = np.asarray(
            getattr(data_array.time.dt, group_component).values
        )

        offset = 0
        if len(datasets) == 2:
            offset = -0.25 if dataset_idx == 0 else 0.25
        position_groups = []
        position_values = []
        for position, period in enumerate(periods, start=1):
            period_values = values[time_groups == period]
            if period_values.size == 0:
                continue
            period_values = period_values[np.isfinite(period_values)]
            if period_values.size == 0:
                continue
            position_groups.append(period_values)
            position_values.append(position + offset)

        color = colors[dataset_idx]
        if position_groups:
            current_ax.boxplot(
                position_groups,
                positions=position_values,
                widths=0.25,
                boxprops={"color": color},
                whiskerprops={"color": color},
                capprops={"color": color},
                medianprops={"color": color},
                flierprops={"markeredgecolor": color},
            )
        patches.append(
            mpatches.Patch(
                color=color,
                label=dataset.attrs.get(
                    "label",
                    f"Dataset {dataset_idx + 1}",
                ),
            )
        )

    if first_da is not None:
        ylabel = first_da.attrs.get("standard_name", var)
        ylabel = first_da.attrs.get("long_name", ylabel)
        if first_da.attrs.get("units") is not None:
            ylabel = f"{ylabel} [{first_da.attrs['units']}]"
        current_ax.set_ylabel(str(ylabel))

    current_ax.grid(False)
    current_ax.set_xticks(np.arange(1, len(periods) + 1))
    current_ax.set_xticklabels(period_labels)
    current_ax.tick_params(axis="x", which="both", length=0)
    current_ax.legend(handles=patches)
    plt.setp(current_ax.get_xticklabels(), rotation=rotation)

    if gca_kwargs:
        plt.setp(current_ax, **gca_kwargs)


def _diurnal_cycle_variability(
    ds: xr.Dataset,
    ref: Union[xr.Dataset, None] = None,
    var: Union[str, None] = None,
    ax: Union[matplotlib.axes.Axes, None] = None,
    size_inches: Union[tuple[float, float], None] = None,
    ylim: Union[tuple[float, float], None] = None,
    yscale: Union[str, None] = None,
    gca_kwargs: Union[dict, None] = None,
    gcf_kwargs: Union[dict, None] = None,
    fig_kwargs: Union[dict, None] = None,
    ax_kwargs: Union[dict, None] = None,
    title_kwargs: Union[dict, None] = None,
) -> None:
    """Plot hourly distributions for one dataset or compare two datasets.

    Parameters
    ----------
    ds : xarray.Dataset
        The first dataset.
    ref : xarray.Dataset, optional
        An optional reference dataset to compare with the first dataset.
    var : str
        The variable name.
    ax : matplotlib.axes.Axes, optional
        Axes on which to draw the plot.
    size_inches : tuple of float, optional
        Figure size in inches (width, height). Defaults to (8, 6).
    ylim : tuple of float, optional
        Y-axis limits, e.g. (0, 15).
    yscale : str, optional
        Y-axis scale, e.g. 'log' or 'linear'.
    gca_kwargs : dict, optional
        Additional keyword arguments passed to
        :func:`matplotlib.pyplot.gca`.
    gcf_kwargs : dict, optional
        Additional keyword arguments passed to
        :func:`matplotlib.pyplot.gcf`.
    fig_kwargs : dict, optional
        Keyword arguments applied to the figure.
    ax_kwargs : dict, optional
        Keyword arguments applied to the axes.
    title_kwargs : dict, optional
        Keyword arguments passed to the axes title.

    Returns
    -------
    None
        Displays a matplotlib figure with the diurnal cycle variability
        plot.

    Examples
    --------

    .. ipython::
      :okwarning:

      @savefig diurnal_cycle_variability.png scale=70
      In [0]: %%time
         ...: import pyku
         ...: ds = pyku.resources.get_test_data('7day-low-res-hourly-tas')
         ...: ds.vis.diurnal_cycle(
         ...:     var='tas', variability=True, ylim=(-20, 20)
         ...: )
    """

    if ax is None:
        plt.clf()
    else:
        plt.sca(ax)

    if size_inches is None:
        size_inches = (8, 6)
    plt.gcf().set_size_inches(size_inches)

    ds = ds.squeeze(
        dim=[
            dim for dim in ds.dims
            if dim != "time" and ds.sizes[dim] == 1
        ]
    )
    if var is None:
        raise ValueError("Specify variable with var='variable_name'")
        if var not in ds.data_vars:
            raise KeyError(
                f"Variable {var!r} not in dataset. It contains: "
                f"{list(ds.data_vars)}"
            )
    da_mod = ds[var].copy(deep=False)
    if ds.attrs.get('label') is not None:
        da_mod.attrs['label'] = ds.attrs['label']

    if ref is not None:
        ref = ref.squeeze(
            dim=[
                dim for dim in ref.dims
                if dim != "time" and ref.sizes[dim] == 1
            ]
        )
        if var not in ref.data_vars:
            raise KeyError(
                f"Variable {var!r} not in dataset. It contains: "
                f"{list(ref.data_vars)}"
            )
        da_obs = ref[var].copy(deep=False)
        if ref.attrs.get('label') is not None:
            da_obs.attrs['label'] = ref.attrs['label']
    else:
        da_obs = None

    patches = []

    dims_mod = [dim for dim in da_mod.dims if dim != 'time']
    if dims_mod:
        # Average spatial dimensions to retain one value per hour.
        da_mod = da_mod.mean(dims_mod, keep_attrs=True)
    ts_mod = da_mod.compute().to_dataframe()
    hourly_mod = ts_mod.groupby(lambda value: value.hour)[[da_mod.name]]
    hours_mod = np.asarray(list(hourly_mod.groups.keys()))

    patches.append(mpatches.Patch(
        color='blue',
        label=ds.attrs.get('label', "Dataset"),
    ))

    ax1 = hourly_mod.boxplot(
        subplots=False,
        rot=90,
        color='blue',
        flierprops={'markeredgecolor': 'blue'},
        positions=hours_mod - (0.25 if da_obs is not None else 0),
        widths=0.25
    )

    if da_obs is not None:

        dims_obs = [dim for dim in da_obs.dims if dim != 'time']
        if dims_obs:
            da_obs = da_obs.mean(dims_obs, keep_attrs=True)
        ts_obs = da_obs.compute().to_dataframe()
        hourly_obs = ts_obs.groupby(
            lambda value: value.hour
        )[[da_obs.name]]
        hours_obs = np.asarray(list(hourly_obs.groups.keys()))

        patches.append(mpatches.Patch(
            color='black',
            label=ref.attrs.get('label', "Reference")
        ))

        hourly_obs.boxplot(
            subplots=False,
            rot=90,
            ax=ax1,
            color='black',
            flierprops={'markeredgecolor': 'black'},
            positions=hours_obs + 0.25,
            widths=0.25,
        )

    if 'long_name' in da_mod.attrs.keys() and 'units' in da_mod.attrs.keys():
        ax1.set_ylabel(
            f"{da_mod.attrs['long_name']} ({da_mod.attrs['units']})"
        )

    ax1.grid(False)
    ax1.set_xticks(ticks=list(range(24)))
    ax1.set_xticklabels(list(range(24)))
    ax1.tick_params(axis='x', which='both', length=0)

    if ylim is not None:
        ax1.set_ylim(ylim)
    if yscale is not None:
        ax1.set_yscale(yscale)

    plt.legend(handles=patches)
    plt.xticks(rotation=0)

    ax1.set_title("Diurnal cycle variability", **(title_kwargs or {}))

    if ax_kwargs:
        valid_props = set(matplotlib.artist.Artist.properties(ax1).keys())
        props = {
            k: v
            for k, v in ax_kwargs.items()
            if k in valid_props
        }
        plt.setp(ax1, **props)

    if gca_kwargs:
        plt.setp(plt.gca(), **gca_kwargs)

    if gcf_kwargs:
        plt.setp(plt.gcf(), **gcf_kwargs)

    if fig_kwargs:
        plt.setp(plt.gcf(), **fig_kwargs)


def _time_plot_data(
    *datasets: xr.Dataset | None,
    var: str | None,
) -> list[xr.DataArray]:
    """Select a variable from each input dataset for time plots."""
    das: list[xr.DataArray] = []
    for dataset in datasets:
        if dataset is None:
            continue
        if not isinstance(dataset, xr.Dataset):
            raise TypeError(
                f"Expected xr.Dataset, got {type(dataset).__name__}"
            )
        if var is None:
            raise ValueError("Specify variable with var='variable_name'")
        if var not in dataset.data_vars:
            raise ValueError(
                f"Variable {var!r} not in dataset; available variables: "
                f"{list(dataset.data_vars)}"
            )

        da = dataset[var].squeeze(
            dim=[
                dim for dim in dataset[var].dims
                if dim != "time" and dataset[var].sizes[dim] == 1
            ]
        )
        if "time" not in da.dims or da.sizes["time"] == 0:
            raise ValueError(
                "Time plots require a non-empty 'time' dimension."
            )
        da.attrs = da.attrs.copy()
        if dataset.attrs.get("label") is not None:
            da.attrs["label"] = dataset.attrs["label"]
        das.append(da)

    return das


def _time_plot_ylabel(
    da: xr.DataArray,
    var: str,
) -> str:
    """Build a y-axis label from variable metadata."""
    ylabel = da.attrs.get("long_name")
    if ylabel is None:
        ylabel = da.attrs.get("standard_name", var)
    if da.attrs.get("units") is not None:
        ylabel = f"{ylabel} [{da.attrs['units']}]"
    return str(ylabel)


def _plot_time_series(
    das: list[xr.DataArray],
    var: str,
    time_resolution: str | None,
    ax: Axes,
    ylim: tuple[float, float] | None,
    yscale: str | None,
    gca_kwargs: dict[str, Any] | None,
) -> None:
    """Draw time series on one axes."""
    linestyles = itertools.cycle(("-", ":", "--", "-."))
    markers = itertools.cycle(("s", "o", "D", "v", "^"))
    fillstyles = itertools.cycle(("none", "full", "left"))
    colors = itertools.cycle(("black", "blue", "red", "orange", "green"))

    for idx, da in enumerate(das):
        if time_resolution is None:
            spatial_dims = [dim for dim in da.dims if dim != "time"]
            series = da.mean(
                dim=spatial_dims,
                skipna=True,
                keep_attrs=True,
            ).compute()
        else:
            with xr.set_options(use_flox=False):
                series = da.resample(time=time_resolution).mean(
                    dim=list(da.dims),
                    skipna=True,
                    keep_attrs=True,
                ).compute()
            if "time" not in series.dims:
                series = series.expand_dims("time")

        ax.plot(
            series["time"].values,
            series.values,
            label=da.attrs.get("label", f"Dataset {idx}"),
            color=next(colors),
            linewidth=0.75,
            linestyle=next(linestyles),
            fillstyle=next(fillstyles),
            marker=next(markers),
        )

    ax.legend(loc="upper left")
    ax.tick_params(axis="x", labelrotation=45)
    ax.set_ylabel(_time_plot_ylabel(das[0], var))
    if ylim is not None:
        ax.set_ylim(ylim)
    if yscale is not None:
        ax.set_yscale(yscale)
    if gca_kwargs:
        plt.setp(ax, **gca_kwargs)


def time_series(
    *datasets: xr.Dataset | None,
    var: str | None = None,
    time_resolution: str | None = None,
    regions: geopandas.GeoDataFrame | None = None,
    layout: str | None = None,
    ax: Axes | None = None,
    ylim: tuple[float, float] | None = None,
    yscale: str | None = None,
    size_inches: tuple[float, float] | None = None,
    gca_kwargs: dict[str, Any] | None = None,
    gcf_kwargs: dict[str, Any] | None = None,
) -> None:
    """Plot spatial means through time, optionally resampled or regionalized.

    With ``time_resolution=None``, each input is spatially averaged at its
    existing timestamps. When a resolution is provided, each time bin is
    averaged over both time and all remaining dimensions. Passing ``regions``
    creates a panel for each polygon.

    Parameters
    ----------
    *datasets : xarray.Dataset or None
        Input datasets. Dataset-level ``label`` attributes are used in the
        legend when present.
    var : str
        Variable name to plot.
    time_resolution : str, optional
        Xarray resampling frequency, such as ``"1D"``, ``"1MS"``, or
        ``"1YS"``. Defaults to no resampling.
    regions : geopandas.GeoDataFrame, optional
        Polygon regions used to mask the datasets and create one panel per
        region.
    layout : str, optional
        Grid shorthand for regional panels, such as ``"3x3"``, ``"x3"``, or
        ``"4x"``. Can only be used when ``regions`` is provided.
    ax : matplotlib.axes.Axes, optional
        Axes on which to draw the plot. Cannot be combined with ``regions``.
    ylim : tuple of float, optional
        Y-axis limits.
    yscale : str, optional
        Y-axis scale, such as ``"linear"`` or ``"log"``.
    size_inches : tuple of float, optional
        Figure size in inches. Regional plots default to a two-column layout.
    gca_kwargs : dict, optional
        Additional properties set on each axes.
    gcf_kwargs : dict, optional
        Additional properties set on the figure.

    Returns
    -------
    None
        Displays a matplotlib figure.

    Examples
    --------
    .. ipython::

        @savefig time_series.png scale=70
        In [0]: import pyku
           ...: ds = pyku.resources.get_test_data('hyras_tas')
           ...: ds.vis.time_series(var='tas', time_resolution='1MS')
    """
    das = _time_plot_data(*datasets, var=var)
    if not das:
        return
    if var is None:
        raise ValueError("Specify variable with var='variable_name'")
    if regions is not None and ax is not None:
        raise ValueError("ax cannot be used together with regions")
    if layout is not None and regions is None:
        raise ValueError("layout can only be used when plotting regions.")

    if regions is not None:
        if regions.empty:
            raise ValueError("regions must contain at least one feature")
        from pyku import features

        grouped = [
            features.regionalize(dataset, regions, dtype="xr.Dataset")
            for dataset in datasets
            if dataset is not None
        ]
        region_values = grouped[0].region.values
        if layout is None:
            ncols = 2
            nrows = (len(region_values) + ncols - 1) // ncols
        else:
            nrows, ncols = _resolve_subplot_layout(
                layout,
                len(region_values),
                "regional time-series",
            )
        fig, axes = plt.subplots(nrows, ncols, squeeze=False)
        axes_flat = axes.reshape(-1)
        if size_inches is None:
            size_inches = (20, nrows * 5)
        fig.set_size_inches(size_inches)

        title_column = next(
            (
                column
                for column in regions.columns
                if column.lower() in {"name", "short_name"}
            ),
            None,
        )
        for idx, region in enumerate(region_values):
            region_ax = axes_flat[idx]
            region_das = _time_plot_data(
                *(group.sel(region=region) for group in grouped),
                var=var,
            )
            _plot_time_series(
                region_das,
                var,
                time_resolution,
                region_ax,
                ylim,
                yscale,
                gca_kwargs,
            )
            if title_column is None:
                title = str(region)
            else:
                title = str(regions.iloc[idx][title_column])
            region_ax.set_title(title)

        for region_ax in axes_flat[len(region_values):]:
            region_ax.set_visible(False)
        if gcf_kwargs:
            plt.setp(fig, **gcf_kwargs)
        return

    if ax is None:
        plt.clf()
        ax = plt.gca()
    else:
        plt.sca(ax)
    if size_inches is None:
        size_inches = (10, 5)
    ax.figure.set_size_inches(size_inches)
    _plot_time_series(
        das,
        var,
        time_resolution,
        ax,
        ylim,
        yscale,
        gca_kwargs,
    )
    if gcf_kwargs:
        plt.setp(ax.figure, **gcf_kwargs)


def climatology(
    *datasets: xr.Dataset | None,
    var: str | None = None,
    groupby: Literal[
        "time.dayofyear",
        "time.month",
        "time.season",
    ] = "time.month",
    ax: Axes | None = None,
    size_inches: tuple[float, float] | None = None,
    gca_kwargs: dict[str, Any] | None = None,
    gcf_kwargs: dict[str, Any] | None = None,
) -> None:
    """Plot a day-of-year, monthly, or seasonal climatology.

    The values are averaged across years within each calendar group and then
    spatially averaged.

    Parameters
    ----------
    *datasets : xarray.Dataset or None
        Input datasets. Dataset-level ``label`` attributes are used in the
        legend when present.
    var : str
        Variable name to plot.
    groupby : {"time.dayofyear", "time.month", "time.season"},
        default "time.month"
        Calendar component used to group the data.
    ax : matplotlib.axes.Axes, optional
        Axes on which to draw the plot.
    size_inches : tuple of float, optional
        Figure size in inches. Defaults to ``(10, 5)``.
    gca_kwargs : dict, optional
        Additional properties set on the axes.
    gcf_kwargs : dict, optional
        Additional properties set on the figure.

    Returns
    -------
    None
        Displays a matplotlib figure.

    Examples
    --------
    .. ipython::

        @savefig climatology.png scale=70
        In [0]: import pyku
           ...: ds = pyku.resources.get_test_data('hyras_tas')
           ...: ds.vis.climatology(var='tas', groupby='time.month')
    """
    if groupby not in {
        "time.dayofyear",
        "time.month",
        "time.season",
    }:
        raise ValueError(
            "groupby must be 'time.dayofyear', 'time.month', or "
            "'time.season'."
        )

    das = _time_plot_data(*datasets, var=var)
    if not das:
        return
    if var is None:
        raise ValueError("Specify variable with var='variable_name'")

    if ax is None:
        plt.clf()
        ax = plt.gca()
    else:
        plt.sca(ax)
    if size_inches is None:
        size_inches = (10, 5)
    ax.figure.set_size_inches(size_inches)

    linestyles = itertools.cycle(("-", ":", "--", "-."))
    markers = itertools.cycle(("s", "o", "D", "v", "^"))
    colors = itertools.cycle(("black", "blue", "red", "orange", "green"))

    component = groupby.rsplit(".", maxsplit=1)[-1]
    if groupby == "time.month":
        periods: tuple[int | str, ...] = tuple(range(1, 13))
        period_labels = tuple(calendar.month_name[1:])
    elif groupby == "time.season":
        periods = ("DJF", "MAM", "JJA", "SON")
        period_labels = periods
    else:
        periods = ()
        period_labels = ()

    for idx, da in enumerate(das):
        spatial_dims = [dim for dim in da.dims if dim != "time"]
        climatology_da = da.groupby(groupby).mean(
            dim="time",
            skipna=True,
            keep_attrs=True,
        )
        if spatial_dims:
            climatology_da = climatology_da.mean(
                dim=spatial_dims,
                skipna=True,
                keep_attrs=True,
            )
        if groupby == "time.season":
            climatology_da = climatology_da.reindex(
                {component: periods}
            )
        climatology_da = climatology_da.compute()
        if groupby == "time.season":
            x_values = range(1, len(periods) + 1)
        else:
            x_values = climatology_da[component].values
        ax.plot(
            x_values,
            climatology_da.values,
            label=da.attrs.get("label", f"Dataset {idx}"),
            color=next(colors),
            linewidth=0.75,
            linestyle=next(linestyles),
            marker=next(markers),
        )

    ax.legend(loc="best")
    ax.set_ylabel(_time_plot_ylabel(das[0], var))
    if groupby == "time.month":
        ax.set_xticks(range(1, 13))
        ax.set_xticklabels(period_labels, rotation=45)
        ax.set_xlabel("")
    elif groupby == "time.season":
        ax.set_xticks(range(1, len(periods) + 1))
        ax.set_xticklabels(period_labels)
        ax.set_xlabel("")
    elif groupby == "time.dayofyear":
        ax.set_xlabel("Day of year")
    if gca_kwargs:
        plt.setp(ax, **gca_kwargs)
    if gcf_kwargs:
        plt.setp(ax.figure, **gcf_kwargs)


def percentile_map(
    *datasets: xr.Dataset,
    var: str | None = None,
    percentile: float = 0.5,
    colorbar: bool = True,
    cmap: Union[str, mcolors.Colormap, None] = "viridis",
    norm: Union[mcolors.Normalize, None] = None,
    vmin: float | None = None,
    vmax: float | None = None,
    nrows: int | None = None,
    ncols: int | None = None,
    layout: str | None = None,
    draw_labels: bool = True,
    map_diagonal: float = 5.5,
    figure_kwargs: dict[str, Any] | None = None,
    pcolormesh_kwargs: dict[str, Any] | None = None,
    colorbar_kwargs: dict[str, Any] | None = None,
    gridlines_kwargs: dict[str, Any] | None = None,
    subplot_kwargs: dict[str, Any] | None = None,
    gca_kwargs: dict[str, Any] | None = None,
    gcf_kwargs: dict[str, Any] | None = None,
) -> None:
    """Map of the nth percentile.

    Computes and plots the nth percentile for one or more datasets over time
    for a specified variable.

    Parameters
    ----------
    *datasets : xarray.Dataset
        The input dataset(s).
    var : str, optional
        Variable name for which to compute the percentile.
    percentile : float, optional
        Percentile between 0 and 1. Defaults to 0.5 (median).
    colorbar : bool, optional
        Defaults to ``True``. If ``False``, the colorbar is omitted and
        colormaps for each plot are set independently.
    cmap : str or matplotlib.colors.Colormap, optional
        Colormap name or object. Defaults to ``"viridis"``.
    norm : matplotlib.colors.Normalize, optional
        Normalization for the colormap. If specified, it overrides vmin and
        vmax.
    vmin : float, optional
        Minimum data value for color scaling. Defaults to None.
    vmax : float, optional
        Maximum data value for color scaling. Defaults to None.
    nrows : int, optional
        Number of rows in the subplot grid. Defaults to None.
    ncols : int, optional
        Number of columns in the subplot grid. Defaults to None.
    layout : str, optional
        Grid shorthand such as ``"3x3"``, ``"x3"`` (three columns), or
        ``"4x"`` (four rows). Cannot be combined with ``nrows`` or ``ncols``.
    draw_labels : bool, optional
        Whether to draw gridline labels. Defaults to ``True``.
    map_diagonal : float, optional
        Diagonal size of each map axes in inches. Defaults to 5.5.
    figure_kwargs : dict, optional
        Keyword arguments passed to :func:`matplotlib.pyplot.figure`.
    pcolormesh_kwargs : dict, optional
        Keyword arguments passed to :func:`matplotlib.pyplot.pcolormesh`.
    colorbar_kwargs : dict, optional
        Keyword arguments passed to :func:`matplotlib.pyplot.colorbar`.
    gridlines_kwargs : dict, optional
        Keyword arguments passed to :func:`cartopy.mpl.gridliner.gridlines`.
    subplot_kwargs : dict, optional
        Keyword arguments passed to
        :meth:`matplotlib.figure.Figure.add_subplot`.
    gca_kwargs : dict, optional
        Keyword arguments passed to the active axes.
    gcf_kwargs : dict, optional
        Keyword arguments passed to the active figure.
    Raises
    ------
    ValueError
        If a dataset lacks the 'time' dimension or if the variable is
        missing from a dataset.
    TypeError
        If any dataset is not an :class:`xarray.Dataset`.

    Examples
    --------

    .. ipython::
       :okwarning:

       @savefig percentile_map.png scale=70
       In [0]: %%time
          ...: import pyku
          ...: ds = pyku.resources.get_test_data('hyras_tas')
          ...: ds.vis.percentile_map(var='tas')
    """

    from pyku import colormaps, meta

    for idx, ds in enumerate(datasets):
        if "time" not in ds.dims:
            raise ValueError(
                f"Dataset at index {idx} missing required 'time' dimension."
            )

    if var is None:
        raise ValueError("Specify variable with var='variable_name'")

    for ds in datasets:
        if not isinstance(ds, xr.Dataset):
            raise TypeError(
                "Dataset item must be an xarray.Dataset, got "
                f"{type(ds).__name__}"
            )

        if var not in meta.get_geodata_varnames(ds):
            raise KeyError(f"Variable '{var}' missing from dataset.")

    if cmap is None and var == 'pr':
        cmap = colormaps.get_cmap('precip_abs')

    das_percentile = []

    for ds in datasets:

        ds_percentile = (
            ds.isel(time=0).copy(deep=True)
            .drop_vars(ds.pyku.get_geodata_varnames())
        )

        da = ds[var]

        if da.chunks is not None:
            da = da.chunk({"time": -1})

        da_percentile = da.quantile(
            percentile, 'time', keep_attrs=True, skipna=False
        ).compute()

        da_percentile.attrs['long_name'] = \
            f'{int(percentile*100)}th percentile {var}'
        da_percentile.attrs['units'] = ds[var].attrs.get('units', None)

        ds_percentile = xr.merge(
            [
                ds_percentile,
                da_percentile.to_dataset(name=f"p{int(percentile*100)}")
            ],
            combine_attrs="override",
            compat='no_conflicts'
        )

        das_percentile.append(ds_percentile)

    n_maps(
        *das_percentile,
        var=f"p{int(percentile*100)}",
        colorbar=colorbar,
        cmap=cmap,
        norm=norm,
        vmin=vmin,
        vmax=vmax,
        nrows=nrows,
        ncols=ncols,
        layout=layout,
        draw_labels=draw_labels,
        map_diagonal=map_diagonal,
        figure_kwargs=figure_kwargs,
        pcolormesh_kwargs=pcolormesh_kwargs,
        colorbar_kwargs=colorbar_kwargs,
        gridlines_kwargs=gridlines_kwargs,
        subplot_kwargs=subplot_kwargs,
        gca_kwargs=gca_kwargs,
        gcf_kwargs=gcf_kwargs,
    )
