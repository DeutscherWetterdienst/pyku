"""
Package initializer
"""

import logging
import warnings
from importlib.metadata import (version as importlib_version,
                                PackageNotFoundError)

import xarray as xr

from pyku.core import PYKU_RESOURCES, PYKU_CONFIG  # noqa

# Set up the logger
# -----------------

# Here the logger must be set at the top and before the import to the pyku
# individual libaries in order to avoid a circular reference. Hence the flake
# warnings are silenced when importing the pyku individual libraries

logger = logging.getLogger(__name__)
ch = logging.StreamHandler()
formatter = logging.Formatter(
    '%(asctime)s '
    '- %(name)s '
    '- %(module)s '
    '- %(lineno)d'
    '- %(levelname)s '
    '- %(message)s '
)
ch.setFormatter(formatter)
logger.addHandler(ch)
logger.propagate = False

warnings.filterwarnings(
    "ignore",
    "You will likely lose important projection information",
    UserWarning,
)

import pyku.magic as magic  # noqa
import pyku.features as libfeatures  # noqa
import pyku.compute as libcompute  # noqa
import pyku.geo as libgeo  # noqa
import pyku.meta as libmeta  # noqa
import pyku.mask as libmask  # noqa
import pyku.check as libcheck  # noqa
import pyku.analyse as libanalyse  # noqa
import pyku.drs as libdrs  # noqa
import pyku.timekit as timekit  # noqa

# Import public functions to pyku namespace
# ---------------------------------------

from pyku.find import * # noqa
from pyku.geo import * # noqa
from pyku.drs import *  # noqa
from pyku.resources import * # noqa

from pyku.resources import list_test_data  # noqa

from pyku.timekit import date_range  # noqa

# Get package version
# -------------------

try:
    __version__ = importlib_version(__name__)
except PackageNotFoundError:
    __version__ = "unknown"


@xr.register_dataset_accessor("pyku")
class pykuDatasetAccessor:

    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    # magic
    # ----

    def to_netcdf(self, *args, **kwargs):
        return magic.to_netcdf(self._obj, *args, **kwargs)
    to_netcdf.__doc__ = magic.to_netcdf.__doc__

    def to_zarr(self, *args, **kwargs):
        return magic.to_zarr(self._obj, *args, **kwargs)
    to_zarr.__doc__ = magic.to_zarr.__doc__

    def sorcery(self, *args, **kwargs):
        return magic.sorcery(self._obj, *args, **kwargs)
    sorcery.__doc__ = magic.sorcery.__doc__

    # meta
    # ----

    def reorder_dimensions_and_coordinates(self, *args, **kwargs):
        return libmeta.reorder_dimensions_and_coordinates(
            self._obj, *args, **kwargs
        )
    reorder_dimensions_and_coordinates.__doc__ = \
        libmeta.reorder_dimensions_and_coordinates.__doc__

    def has_ordered_dimensions_and_coordinates(self, *args, **kwargs):
        return libmeta.has_ordered_dimensions_and_coordinates(
            self._obj, *args, **kwargs
        )
    has_ordered_dimensions_and_coordinates.__doc__ = \
        libmeta.has_ordered_dimensions_and_coordinates.__doc__

    def filter_incomplete_datetimes(self, *args, **kwargs):
        return libmeta.filter_incomplete_datetimes(self._obj, *args, **kwargs)
    filter_incomplete_datetimes.__doc__ = \
        libmeta.filter_incomplete_datetimes.__doc__

    def get_dataset_size(self, *args, **kwargs):
        return libmeta.get_dataset_size(self._obj, *args, **kwargs)
    get_dataset_size.__doc__ = libmeta.get_dataset_size.__doc__

    def get_geodataset(self, *args, **kwargs):
        return libmeta.get_geodataset(self._obj, *args, **kwargs)
    get_geodataset.__doc__ = libmeta.get_geodataset.__doc__

    def get_unidentified_varnames(self, *args, **kwargs):
        return libmeta.get_unidentified_varnames(self._obj, *args, **kwargs)
    get_unidentified_varnames.__doc__ = \
        libmeta.get_unidentified_varnames.__doc__

    def get_spatial_vertices_varnames(self, *args, **kwargs):
        return libmeta.get_spatial_vertices_varnames(
            self._obj, *args, **kwargs)
    get_spatial_vertices_varnames.__doc__ = \
        libmeta.get_spatial_vertices_varnames.__doc__

    def get_latlon_bounds_varnames(self, *args, **kwargs):
        return libmeta.get_latlon_bounds_varnames(self._obj, *args, **kwargs)
    get_latlon_bounds_varnames.__doc__ = \
        libmeta.get_latlon_bounds_varnames.__doc__

    def get_spatial_bounds_varnames(self, *args, **kwargs):
        return libmeta.get_spatial_bounds_varnames(self._obj, *args, **kwargs)
    get_spatial_bounds_varnames.__doc__ = \
        libmeta.get_spatial_bounds_varnames.__doc__

    def get_spatial_varnames(self, *args, **kwargs):
        return libmeta.get_spatial_varnames(self._obj, *args, **kwargs)
    get_spatial_varnames.__doc__ = libmeta.get_spatial_varnames.__doc__

    def get_crs_varname(self, *args, **kwargs):
        return libmeta.get_crs_varname(self._obj, *args, **kwargs)
    get_crs_varname.__doc__ = libmeta.get_crs_varname.__doc__

    def get_time_bounds_varname(self, *args, **kwargs):
        return libmeta.get_time_bounds_varname(self._obj, *args, **kwargs)
    get_time_bounds_varname.__doc__ = libmeta.get_time_bounds_varname.__doc__

    def get_time_dependent_varnames(self, *args, **kwargs):
        return libmeta.get_time_dependent_varnames(self._obj, *args, **kwargs)
    get_time_dependent_varnames.__doc__ = \
        libmeta.get_time_dependent_varnames.__doc__

    def get_time_bounds(self, *args, **kwargs):
        return libmeta.get_time_bounds(self._obj, *args, **kwargs)
    get_time_bounds.__doc__ = libmeta.get_time_bounds.__doc__

    def has_time_bounds(self, *args, **kwargs):
        return libmeta.has_time_bounds(self._obj, *args, **kwargs)
    has_time_bounds.__doc__ = libmeta.has_time_bounds.__doc__

    def get_time_intervals(self, *args, **kwargs):
        return libmeta.get_time_intervals(self._obj, *args, **kwargs)
    get_time_intervals.__doc__ = libmeta.get_time_intervals.__doc__

    def get_frequency(self, *args, **kwargs):
        return libmeta.get_frequency(self._obj, *args, **kwargs)
    get_frequency.__doc__ = libmeta.get_frequency.__doc__

    def has_geographic_coordinates(self, *args, **kwargs):
        return libmeta.has_geographic_coordinates(self._obj, *args, **kwargs)
    has_geographic_coordinates.__doc__ = \
        libmeta.has_geographic_coordinates.__doc__

    def has_projection_coordinates(self, *args, **kwargs):
        return libmeta.has_projection_coordinates(self._obj, *args, **kwargs)
    has_projection_coordinates.__doc__ = \
        libmeta.has_projection_coordinates.__doc__

    def is_georeferenced(self, *args, **kwargs):
        return libmeta.is_georeferenced(self._obj, *args, **kwargs)
    is_georeferenced.__doc__ = libmeta.is_georeferenced.__doc__

    def get_geographic_latlon_varnames(self, *args, **kwargs):
        return libmeta.get_geographic_latlon_varnames(
            self._obj, *args, **kwargs)
    get_geographic_latlon_varnames.__doc__ = \
        libmeta.get_geographic_latlon_varnames.__doc__

    def get_projection_yx_varnames(self, *args, **kwargs):
        return libmeta.get_projection_yx_varnames(self._obj, *args, **kwargs)
    get_projection_yx_varnames.__doc__ = \
        libmeta.get_projection_yx_varnames.__doc__

    def get_geodata_varnames(self, *args, **kwargs):
        return libmeta.get_geodata_varnames(self._obj, *args, **kwargs)
    get_geodata_varnames.__doc__ = libmeta.get_geodata_varnames.__doc__

    def to_gregorian_calendar(self, *args, **kwargs):
        return timekit.to_gregorian_calendar(self._obj, *args, **kwargs)
    to_gregorian_calendar.__doc__ = timekit.to_gregorian_calendar.__doc__

    def to_calendar(self, *args, **kwargs):
        return timekit.to_calendar(self._obj, *args, **kwargs)
    to_calendar.__doc__ = timekit.to_calendar.__doc__

    # mask
    # ----

    def apply_mask(self, *args, **kwargs):
        return libmask.apply_mask(self._obj, *args, **kwargs)
    apply_mask.__doc__ = libmask.apply_mask.__doc__

    def apply_polygon_mask(self, *args, **kwargs):
        return libmask.apply_polygon_mask(self._obj, *args, **kwargs)
    apply_polygon_mask.__doc__ = libmask.apply_polygon_mask.__doc__

    def apply_raster_mask(self, *args, **kwargs):
        return libmask.apply_raster_mask(self._obj, *args, **kwargs)
    apply_raster_mask.__doc__ = libmask.apply_raster_mask.__doc__

    def combine_masks(self, *args, **kwargs):
        return libmask.combine_mask(self._obj, *args, **kwargs)
    combine_masks.__doc__ = libmask.combine_masks.__doc__

    def get_mask(self, *args, **kwargs):
        return libmask.get_mask(self._obj, *args, **kwargs)
    get_mask.__doc__ = libmask.get_mask.__doc__

    # check
    # -----

    def check(self, *args, **kwargs):
        return libcheck.check(self._obj, *args, **kwargs)
    check.__doc__ = libcheck.check.__doc__

    def check_metadata(self, *args, **kwargs):
        return libcheck.check_metadata(self._obj, *args, **kwargs)
    check_metadata.__doc__ = libcheck.check_metadata.__doc__

    def check_datetimes(self, *args, **kwargs):
        return libcheck.check_datetimes(self._obj, *args, **kwargs)
    check_datetimes.__doc__ = libcheck.check_datetimes.__doc__

    def check_datetime_completeness(self, *args, **kwargs):
        return libcheck.check_datetime_completeness(self._obj, *args, **kwargs)
    check_datetime_completeness.__doc__ = \
        libcheck.check_datetime_completeness.__doc__

    def check_allnan_slices(self, *args, **kwargs):
        return libcheck.check_allnan_slices(self._obj, *args, **kwargs)
    check_allnan_slices.__doc__ = libcheck.check_allnan_slices.__doc__

    def check_valid_bounds(self, *args, **kwargs):
        return libcheck.check_valid_bounds(self._obj, *args, **kwargs)
    check_valid_bounds.__doc__ = libcheck.check_valid_bounds.__doc__

    def check_georeferencing(self, *args, **kwargs):
        return libcheck.check_georeferencing(self._obj, *args, **kwargs)
    check_georeferencing.__doc__ = libcheck.check_georeferencing.__doc__

    def check_units(self, *args, **kwargs):
        return libcheck.check_units(self._obj, *args, **kwargs)
    check_units.__doc__ = libcheck.check_units.__doc__

    def check_frequency(self, *args, **kwargs):
        return libcheck.check_frequency(self._obj, *args, **kwargs)
    check_frequency.__doc__ = libcheck.check_frequency.__doc__

    def check_cmor_varnames(self, *args, **kwargs):
        return libcheck.check_cmor_varnames(self._obj, *args, **kwargs)
    check_cmor_varnames.__doc__ = libcheck.check_cmor_varnames.__doc__

    def check_variables_cmor_metadata(self, *args, **kwargs):
        return libcheck.check_variables_cmor_metadata(self._obj, *args, **kwargs)  # noqa
    check_variables_cmor_metadata.__doc__ = \
        libcheck.check_variables_cmor_metadata.__doc__

    def check_variables_role(self, *args, **kwargs):
        return libcheck.check_variables_role(self._obj, *args, **kwargs)
    check_variables_role.__doc__ = libcheck.check_variables_role.__doc__

    def check_drs(self, *args, **kwargs):
        return libcheck.check_drs(self._obj, *args, **kwargs)
    check_drs.__doc__ = libcheck.check_drs.__doc__

    def check_files(self, *args, **kwargs):
        return libcheck.check_files(self._obj, *args, **kwargs)
    check_files.__doc__ = libcheck.check_files.__doc__

    def compare_geographic_alignment(self, *args, **kwargs):
        return libcheck.compare_geographic_alignment(self._obj, *args, **kwargs)  # noqa
    compare_geographic_alignment.__doc__ = \
        libcheck.compare_geographic_alignment.__doc__

    def compare_datasets(self, *args, **kwargs):
        return libcheck.compare_datasets(self._obj, *args, **kwargs)
    compare_datasets.__doc__ = libcheck.compare_datasets.__doc__

    def compare_attrs(self, *args, **kwargs):
        return libcheck.compare_attrs(self._obj, *args, **kwargs)
    compare_attrs.__doc__ = libcheck.compare_attrs.__doc__

    def compare_coordinates(self, *args, **kwargs):
        return libcheck.compare_coordinates(self._obj, *args, **kwargs)
    compare_coordinates.__doc__ = libcheck.compare_coordinates.__doc__

    def compare_dimensions(self, *args, **kwargs):
        return libcheck.compare_dimensions(self._obj, *args, **kwargs)
    compare_dimensions.__doc__ = libcheck.compare_dimensions.__doc__

    def compare_datetimes(self, *args, **kwargs):
        return libcheck.compare_datetimes(self._obj, *args, **kwargs)
    compare_datetimes.__doc__ = libcheck.compare_datetimes.__doc__

    # geo
    # ---

    def align_georeferencing(self, *args, **kwargs):
        return libgeo.align_georeferencing(self._obj, *args, **kwargs)
    align_georeferencing.__doc__ = libgeo.align_georeferencing.__doc__

    def sort_georeferencing(self, *args, **kwargs):
        return libgeo.sort_georeferencing(self._obj, *args, **kwargs)
    sort_georeferencing.__doc__ = libgeo.sort_georeferencing.__doc__

    def select_area_extent(self, *args, **kwargs):
        return libgeo.select_area_extent(self._obj, *args, **kwargs)
    select_area_extent.__doc__ = libgeo.select_area_extent.__doc__

    def select_neighborhood(self, *args, **kwargs):
        return libgeo.select_neighborhood(self._obj, *args, **kwargs)
    select_neighborhood.__doc__ = libgeo.select_neighborhood.__doc__

    def is_georeferencing_sorted(self, *args, **kwargs):
        return libgeo.is_georeferencing_sorted(self._obj, *args, **kwargs)
    is_georeferencing_sorted.__doc__ = libgeo.is_georeferencing_sorted.__doc__

    def are_yx_projection_coordinates_strictly_monotonic(
        self, *args, **kwargs
    ):
        return libgeo.are_yx_projection_coordinates_strictly_monotonic(
            self._obj, *args, **kwargs
        )
    are_yx_projection_coordinates_strictly_monotonic.__doc__ = \
        libgeo.are_yx_projection_coordinates_strictly_monotonic.__doc__

    def get_ny(self, *args, **kwargs):
        return libgeo.get_ny(self._obj, *args, **kwargs)
    get_ny.__doc__ = libgeo.get_ny.__doc__

    def get_nx(self, *args, **kwargs):
        return libgeo.get_nx(self._obj, *args, **kwargs)
    get_nx.__doc__ = libgeo.get_nx.__doc__

    def are_longitudes_wrapped(self, *args, **kwargs):
        return libgeo.are_longitudes_wrapped(self._obj, *args, **kwargs)
    are_longitudes_wrapped.__doc__ = libgeo.are_longitudes_wrapped.__doc__

    def wrap_longitudes(self, *args, **kwargs):
        return libgeo.wrap_longitudes(self._obj, *args, **kwargs)
    wrap_longitudes.__doc__ = libgeo.wrap_longitudes.__doc__

    def apply_georeferencing(self, *args, **kwargs):
        return libgeo.apply_georeferencing(self._obj, *args, **kwargs)
    apply_georeferencing.__doc__ = libgeo.apply_georeferencing.__doc__

    def get_georeferencing(self, *args, **kwargs):
        return libgeo.get_georeferencing(self._obj, *args, **kwargs)
    get_georeferencing.__doc__ = libgeo.get_georeferencing.__doc__

    def get_lonlats(self, *args, **kwargs):
        return libgeo.get_lonlats(self._obj, *args, **kwargs)
    get_lonlats.__doc__ = libgeo.get_lonlats.__doc__

    def get_yx(self, *args, **kwargs):
        return libgeo.get_yx(self._obj, *args, **kwargs)
    get_yx.__doc__ = libgeo.get_yx.__doc__

    def set_latlon_bounds(self, *args, **kwargs):
        return libgeo.set_latlon_bounds(self._obj, *args, **kwargs)
    set_latlon_bounds.__doc__ = libgeo.set_latlon_bounds.__doc__

    def set_spatial_weights(self, *args, **kwargs):
        return libgeo.set_spatial_weights(self._obj, *args, **kwargs)
    set_spatial_weights.__doc__ = libgeo.set_spatial_weights.__doc__

    def get_area_def(self, *args, **kwargs):
        return libgeo.get_area_def(self._obj, *args, **kwargs)
    get_area_def.__doc__ = libgeo.get_area_def.__doc__

    def project(self, *args, **kwargs):
        return libgeo.project(self._obj, *args, **kwargs)
    project.__doc__ = libgeo.project.__doc__

    # features
    # --------

    def polygonize(self, *args, **kwargs):
        return libfeatures.polygonize(self._obj, *args, **kwargs)
    polygonize.__doc__ = libfeatures.polygonize.__doc__

    def regionalize(self, *args, **kwargs):
        return libfeatures.regionalize(self._obj, *args, **kwargs)
    regionalize.__doc__ = libfeatures.regionalize.__doc__

    # drs
    # ---

    def drs_filename(self, *args, **kwargs):
        return libdrs.drs_filename(self._obj, *args, **kwargs)
    drs_filename.__doc__ = libdrs.drs_filename.__doc__

    def drs_stem(self, *args, **kwargs):
        return libdrs.drs_stem(self._obj, *args, **kwargs)
    drs_stem.__doc__ = libdrs.drs_stem.__doc__

    def drs_parent(self, *args, **kwargs):
        return libdrs.drs_parent(self._obj, *args, **kwargs)
    drs_parent.__doc__ = libdrs.drs_parent.__doc__

    def to_drs_netcdfs(self, *args, **kwargs):
        return libdrs.to_drs_netcdfs(self._obj, *args, **kwargs)
    to_drs_netcdfs.__doc__ = libdrs.to_drs_netcdfs.__doc__

    def to_cmor_units(self, *args, **kwargs):
        return libdrs.to_cmor_units(self._obj, *args, **kwargs)
    to_cmor_units.__doc__ = libdrs.to_cmor_units.__doc__

    def has_cmor_time_labels(self, *args, **kwargs):
        return libdrs.has_cmor_time_labels(self._obj, *args, **kwargs)
    has_cmor_time_labels.__doc__ = libdrs.has_cmor_time_labels.__doc__

    def get_cmor_varname(self, *args, **kwargs):
        return libdrs.get_cmor_varname(self._obj, *args, **kwargs)
    get_cmor_varname.__doc__ = libdrs.get_cmor_varname.__doc__

    def to_cmor_varnames(self, *args, **kwargs):
        return libdrs.to_cmor_varnames(self._obj, *args, **kwargs)
    to_cmor_varnames.__doc__ = libdrs.to_cmor_varnames.__doc__

    def to_cmor_attrs(self, *args, **kwargs):
        return libdrs.to_cmor_attrs(self._obj, *args, **kwargs)
    to_cmor_attrs.__doc__ = libdrs.to_cmor_attrs.__doc__

    def to_cmor_attrs(self, *args, **kwargs):
        return libdrs.to_cmor_attrs(self._obj, *args, **kwargs)
    to_cmor_attrs.__doc__ = libdrs.to_cmor_attrs.__doc__

    def cmorize(self, *args, **kwargs):
        return libdrs.cmorize(self._obj, *args, **kwargs)
    cmorize.__doc__ = libdrs.cmorize.__doc__

    # timekit
    # -------

    def resample_datetimes(self, *args, **kwargs):
        return timekit.resample_datetimes(self._obj, *args, **kwargs)
    resample_datetimes.__doc__ = timekit.resample_datetimes.__doc__

    def set_time_labels_from_time_bounds(self, *args, **kwargs):
        return timekit.set_time_labels_from_time_bounds(
            self._obj, *args, **kwargs)
    set_time_labels_from_time_bounds.__doc__ = \
        timekit.set_time_labels_from_time_bounds.__doc__

    def set_time_bounds(self, *args, **kwargs):

        warnings.warn(
            "set_time_bounds is now called set_time_bounds_from_time_labels "
            "and will be removed soon",
            FutureWarning
        )

        return timekit.set_time_bounds_from_time_labels(
            self._obj, *args, **kwargs)

    def set_time_bounds_from_time_labels(self, *args, **kwargs):
        return timekit.set_time_bounds_from_time_labels(
            self._obj, *args, **kwargs)
    set_time_bounds_from_time_labels.__doc__ = \
        timekit.set_time_bounds_from_time_labels.__doc__

    # compute
    # -------

    def calc(self, *args, **kwargs):
        return libcompute.calc(self._obj, *args, **kwargs)
    calc.__doc__ = libcompute.calc.__doc__

    def calc_tdew(self, *args, **kwargs):
        return libcompute.calc_tdew(self._obj, *args, **kwargs)
    calc_tdew.__doc__ = libcompute.calc_tdew.__doc__

    def calc_hurs(self, *args, **kwargs):
        return libcompute.calc_hurs(self._obj, *args, **kwargs)
    calc_hurs.__doc__ = libcompute.calc_hurs.__doc__

    def calc_windspeed(self, *args, **kwargs):
        return libcompute.calc_windspeed(self._obj, *args, **kwargs)
    calc_windspeed.__doc__ = libcompute.calc_windspeed.__doc__

    def calc_globalwarminglevels(self, *args, **kwargs):
        return libcompute.calc_globalwarminglevels(self._obj, *args, **kwargs)
    calc_globalwarminglevels.__doc__ = \
        libcompute.calc_globalwarminglevels.__doc__

    def inpainting(self, *args, **kwargs):
        return libcompute.inpainting(self._obj, *args, **kwargs)
    inpainting.__doc__ = libcompute.inpainting.__doc__


@xr.register_dataarray_accessor("pyku")
class pykuDataArrayAccessor:

    def __init__(self, xarray_obj):
        self._obj = xarray_obj


@xr.register_dataset_accessor("ana")
class analyseDatasetAccessor:

    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    def maps(self, *args, **kwargs):
        libanalyse.n_maps(self._obj, *args, **kwargs)
    maps.__doc__ = libanalyse.n_maps.__doc__

    def one_map(self, *args, **kwargs):
        libanalyse.one_map(self._obj, *args, **kwargs)
    one_map.__doc__ = libanalyse.one_map.__doc__

    def two_maps(self, *args, **kwargs):
        libanalyse.two_maps(self._obj, *args, **kwargs)
    one_map.__doc__ = libanalyse.two_maps.__doc__

    def n_maps(self, *args, **kwargs):
        libanalyse.n_maps(self._obj, *args, **kwargs)
    n_maps.__doc__ = libanalyse.n_maps.__doc__

    def pdf(self, *args, **kwargs):
        libanalyse.pdf(self._obj, *args, **kwargs)
    pdf.__doc__ = libanalyse.pdf.__doc__

    def var_vs_year(self, *args, **kwargs):
        libanalyse.var_vs_year(self._obj, *args, **kwargs)
    var_vs_year.__doc__ = libanalyse.var_vs_year.__doc__

    def monthly_pdf(self, *args, **kwargs):
        libanalyse.monthly_pdf(self._obj, *args, **kwargs)
    monthly_pdf.__doc__ = libanalyse.monthly_pdf.__doc__

    def monthly_diurnal_cycle(self, *args, **kwargs):
        libanalyse.monthly_diurnal_cycle(self._obj, *args, **kwargs)
    monthly_diurnal_cycle.__doc__ = libanalyse.monthly_diurnal_cycle.__doc__

    def monthly_mean(self, *args, **kwargs):
        libanalyse.monthly_mean(self._obj, *args, **kwargs)
    monthly_mean.__doc__ = libanalyse.monthly_mean.__doc__

    def monthly_bias(self, *args, **kwargs):
        libanalyse.monthly_bias(self._obj, *args, **kwargs)
    monthly_bias.__doc__ = libanalyse.monthly_bias.__doc__

    def monthly_bias_var(self, *args, **kwargs):
        libanalyse.monthly_bias_var(self._obj, *args, **kwargs)
    monthly_bias_var.__doc__ = libanalyse.monthly_bias_var.__doc__

    def monthly_variability(self, *args, **kwargs):
        libanalyse.monthly_variability(self._obj, *args, **kwargs)
    monthly_variability.__doc__ = libanalyse.monthly_variability.__doc__

    def seasonal_pdf(self, *args, **kwargs):
        libanalyse.seasonal_pdf(self._obj, *args, **kwargs)
    seasonal_pdf.__doc__ = libanalyse.seasonal_pdf.__doc__

    def seasonal_diurnal_cycle(self, *args, **kwargs):
        libanalyse.seasonal_diurnal_cycle(self._obj, *args, **kwargs)
    seasonal_diurnal_cycle.__doc__ = libanalyse.seasonal_diurnal_cycle.__doc__

    def seasonal_mean_bias_map(self, *args, **kwargs):
        libanalyse.seasonal_mean_bias_map(self._obj, *args, **kwargs)
    seasonal_mean_bias_map.__doc__ = libanalyse.seasonal_mean_bias_map.__doc__

    def diurnal_cycle(self, *args, **kwargs):
        libanalyse.diurnal_cycle(self._obj, *args, **kwargs)
    diurnal_cycle.__doc__ = libanalyse.diurnal_cycle.__doc__

    def diurnal_cycle_variability(self, *args, **kwargs):
        libanalyse.diurnal_cycle_variability(self._obj, *args, **kwargs)
    diurnal_cycle_variability.__doc__ = \
        libanalyse.diurnal_cycle_variability.__doc__

    def daily_mean(self, *args, **kwargs):
        libanalyse.daily_mean(self._obj, *args, **kwargs)
    daily_mean.__doc__ = libanalyse.daily_mean.__doc__

    def time_serie(self, *args, **kwargs):
        libanalyse.time_serie(self._obj, *args, **kwargs)
    time_serie.__doc__ = libanalyse.time_serie.__doc__

    def mean_map(self, *args, **kwargs):
        libanalyse.mean_map(self._obj, *args, **kwargs)
    mean_map.__doc__ = libanalyse.mean_map.__doc__

    def p98_map(self, *args, **kwargs):
        libanalyse.p98_map(self._obj, *args, **kwargs)
    p98_map.__doc__ = libanalyse.p98_map.__doc__

    def mean_vs_time(self, *args, **kwargs):
        libanalyse.mean_vs_time(self._obj, *args, **kwargs)
    mean_vs_time.__doc__ = libanalyse.mean_vs_time.__doc__

    def p98_vs_time(self, *args, **kwargs):
        libanalyse.p98_vs_time(self._obj, *args, **kwargs)
    p98_vs_time.__doc__ = libanalyse.p98_vs_time.__doc__

    def mae_map(self, *args, **kwargs):
        libanalyse.mae_map(self._obj, *args, **kwargs)
    mae_map.__doc__ = libanalyse.mae_map.__doc__

    def pcc_map(self, *args, **kwargs):
        libanalyse.pcc_map(self._obj, *args, **kwargs)
    pcc_map.__doc__ = libanalyse.pcc_map.__doc__

    def mean_bias_map(self, *args, **kwargs):
        libanalyse.mean_bias_map(self._obj, *args, **kwargs)
    mean_bias_map.__doc__ = libanalyse.mean_bias_map.__doc__

    def mse_map(self, *args, **kwargs):
        libanalyse.mse_map(self._obj, *args, **kwargs)
    mse_map.__doc__ = libanalyse.mse_map.__doc__

    def rmse_map(self, *args, **kwargs):
        libanalyse.rmse_map(self._obj, *args, **kwargs)
    rmse_map.__doc__ = libanalyse.rmse_map.__doc__

    def regional_mean_vs_time(self, *args, **kwargs):
        libanalyse.regional_mean_vs_time(self._obj, *args, **kwargs)
    regional_mean_vs_time.__doc__ = libanalyse.regional_mean_vs_time.__doc__


@xr.register_dataarray_accessor("ana")
class analyseDataArrayAccessor:

    def __init__(self, xarray_obj):
        self._obj = xarray_obj

    def maps(self, *args, **kwargs):
        libanalyse.n_maps(self._obj, *args, **kwargs)
    maps.__doc__ = libanalyse.n_maps.__doc__

    def one_map(self, *args, **kwargs):
        libanalyse.one_map(self._obj, *args, **kwargs)
    one_map.__doc__ = libanalyse.one_map.__doc__

    def two_maps(self, *args, **kwargs):
        libanalyse.two_maps(self._obj, *args, **kwargs)
    one_map.__doc__ = libanalyse.two_maps.__doc__

    def n_maps(self, *args, **kwargs):
        libanalyse.n_maps(self._obj, *args, **kwargs)
    n_maps.__doc__ = libanalyse.n_maps.__doc__

    def pdf(self, *args, **kwargs):
        libanalyse.pdf(self._obj, *args, **kwargs)
    pdf.__doc__ = libanalyse.pdf.__doc__

    def monthly_pdf(self, *args, **kwargs):
        libanalyse.monthly_pdf(self._obj, *args, **kwargs)
    monthly_pdf.__doc__ = libanalyse.monthly_pdf.__doc__

    def seasonal_pdf(self, *args, **kwargs):
        libanalyse.seasonal_pdf(self._obj, *args, **kwargs)
    seasonal_pdf.__doc__ = libanalyse.seasonal_pdf.__doc__

    def diurnal_cycle(self, *args, **kwargs):
        libanalyse.diurnal_cycle(self._obj, *args, **kwargs)
    diurnal_cycle.__doc__ = libanalyse.diurnal_cycle.__doc__

    def mean_map(self, *args, **kwargs):
        libanalyse.mean_map(self._obj, *args, **kwargs)
    mean_map.__doc__ = libanalyse.mean_map.__doc__
