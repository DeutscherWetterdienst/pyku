import sys
import types
from typing import Any
from unittest.mock import Mock

import dask.array as dask_array
import geopandas as gpd
import numpy as np
import pytest
from pyresample.geometry import AreaDefinition
from shapely.geometry import Polygon, box

import xarray as xr
from pyku import features, geo, resources


def _area(
    width: int = 2,
    height: int = 2,
    extent: tuple[int, int, int, int] = (0, 0, 2, 2),
) -> AreaDefinition:
    return AreaDefinition(
        "test",
        "test area",
        "test",
        {"proj": "longlat", "datum": "WGS84"},
        width,
        height,
        extent,
    )


def _test_xvec(
    monkeypatch: pytest.MonkeyPatch,
    crs_values: list[Any],
) -> None:
    class Accessor:
        def __init__(self, dataset: xr.Dataset) -> None:
            self.dataset = dataset

        def set_geom_indexes(self, name: str, crs: Any) -> xr.Dataset:
            crs_values.append(crs)
            return self.dataset

        def to_crs(self, geometry: Any) -> xr.Dataset:
            crs_values.append(geometry)
            return self.dataset

    monkeypatch.setitem(sys.modules, "xvec", types.ModuleType("xvec"))
    monkeypatch.setattr(
        xr.Dataset,
        "xvec",
        property(Accessor),
        raising=False,
    )


def _grid_dataset(values: Any = None) -> xr.Dataset:
    if values is None:
        values = np.array([[1.0, 2.0], [3.0, 4.0]])
    return xr.Dataset(
        {"tas": (("y", "x"), values)},
        coords={"x": [0.5, 1.5], "y": [1.5, 0.5]},
    )


def test_apply_weights_preserves_dim_order_and_extra_dims() -> None:
    values = np.array(
        [
            [[[1, 3], [2, 4]]],
            [[[10, 30], [20, 40]]],
        ]
    )
    da = xr.DataArray(
        values,
        dims=("level", "time", "x", "y"),
        coords={"level": [0, 1], "time": ["a"]},
        name="tas",
    )
    weights = [(np.array([0, 1]), np.array([0.5, 0.5]))]

    result = features._apply_weights(
        da,
        weights,
        method="mean",
        y_name="y",
        x_name="x",
    )

    assert result.dims == ("geometry", "level", "time")
    np.testing.assert_allclose(result.values[:, :, 0], [[1.5, 15]])


def test_apply_weights_supports_time_independent_and_dask_data() -> None:
    da = xr.DataArray(
        dask_array.from_array(
            np.array([[1.0, 2.0], [3.0, 4.0]]), chunks=(1, 1)
        ),
        dims=("x", "y"),
        name="tas",
    )

    result = features._apply_weights(
        da,
        [(np.array([0, 1]), np.array([0.5, 0.5]))],
        y_name="y",
        x_name="x",
    )

    assert isinstance(result.data, dask_array.Array)
    assert result.compute().item() == pytest.approx(2.0)


@pytest.mark.parametrize(
    ("method", "expected"),
    [
        ("mean", 1.0),
        ("weighted_sum", 1.0),
        ("sum", 1.0),
        ("min", 1.0),
        ("max", 1.0),
        ("median", 1.0),
        ("std", 0.0),
    ],
)
def test_area_statistics_ignore_boundary_only_cells(
    method: str,
    expected: float,
) -> None:
    ds = _grid_dataset()
    weights = features._gen_weights(
        ds,
        [box(0, 1, 1, 2)],
        how="area",
        area_def=_area(),
    )

    assert weights[0][0].tolist() == [0]
    result = features._apply_weights(
        ds.tas,
        weights,
        method=method,
        y_name="y",
        x_name="x",
    )
    assert result.item() == pytest.approx(expected)


@pytest.mark.parametrize(
    "method",
    ["mean", "weighted_sum", "sum", "min", "max", "median", "std"],
)
@pytest.mark.parametrize(
    ("polygon", "how"),
    [
        (box(5, 5, 6, 6), "area"),
        (box(0.6, 1.6, 0.7, 1.7), "centroid"),
    ],
    ids=["outside", "sub-cell-without-centroid"],
)
def test_empty_regions_return_missing_values(
    method: str,
    polygon: Any,
    how: str,
) -> None:
    ds = _grid_dataset()
    weights = features._gen_weights(ds, [polygon], how=how, area_def=_area())

    result = features._apply_weights(
        ds.tas,
        weights,
        method=method,
        y_name="y",
        x_name="x",
    )

    assert np.isnan(result.item())


def test_area_weights_drop_cells_in_holes_and_concave_exteriors() -> None:
    ds = xr.Dataset(
        {"tas": (("y", "x"), np.arange(16).reshape(4, 4))},
        coords={"x": [0.5, 1.5, 2.5, 3.5], "y": [3.5, 2.5, 1.5, 0.5]},
    )
    area = _area(width=4, height=4, extent=(0, 0, 4, 4))
    shell = [(0, 0), (4, 0), (4, 4), (0, 4), (0, 0)]
    hole = [(0.1, 0.1), (2.9, 0.1), (2.9, 2.9), (0.1, 2.9), (0.1, 0.1)]
    donut = Polygon(shell, [hole])
    weights = features._gen_weights(ds, [donut], how="area", area_def=area)

    assert 9 not in weights[0][0]

    concave = Polygon([(0, 0), (4, 0), (4, 1), (1, 1), (1, 4), (0, 4), (0, 0)])
    concave_weights = features._gen_weights(
        ds,
        [concave],
        how="area",
        area_def=area,
    )
    assert len(concave_weights[0][0]) == 7


@pytest.mark.parametrize("named_area", [False, True])
@pytest.mark.parametrize("with_time_bounds", [False, True])
def test_aggregate_by_region_retains_variables_metadata_and_timestamps(
    monkeypatch: pytest.MonkeyPatch,
    named_area: bool,
    with_time_bounds: bool,
) -> None:
    crs_values = []
    _test_xvec(monkeypatch, crs_values)
    monkeypatch.setattr(
        "pyku.meta.get_geodata_varnames", lambda dataset: ["tas", "pr"]
    )
    monkeypatch.setattr(
        "pyku.meta.get_projection_yx_varnames", lambda dataset: ("y", "x")
    )
    area = _area()
    if named_area:
        monkeypatch.setattr(geo, "load_area_def", lambda name: area)
        supplied_area = "test-area"
    else:
        supplied_area = area

    data_vars = {
        "tas": (("time", "y", "x"), [[[1, 2], [3, 4]]]),
        "pr": (("time", "y", "x"), [[[10, 20], [30, 40]]]),
        "crs": ((), 1),
    }
    if with_time_bounds:
        data_vars["time_bounds"] = (
            ("time", "bounds"),
            [["2000-01-01", "2000-02-01"]],
        )
    ds = xr.Dataset(
        data_vars,
        coords={
            "time": np.array(["2000-01-15"], dtype="datetime64[ns]"),
            "y": [1.5, 0.5],
            "x": [0.5, 1.5],
            "bounds": [0, 1],
        },
        attrs={"title": "synthetic"},
    )
    ds.tas.attrs.update(units="K", grid_mapping="crs")
    ds.pr.attrs.update(units="mm", grid_mapping="crs")
    gdf = gpd.GeoDataFrame(
        geometry=[box(0, 1, 1, 2), box(1, 1, 2, 2)],
        crs="EPSG:4326",
    )

    result = features.aggregate_by_region(
        ds,
        gdf,
        area_def=supplied_area,
        cell_selection="area",
    )

    assert result.sizes["geometry"] == 2
    assert result.geometry.values.tolist() == gdf.geometry.to_numpy().tolist()
    assert result.time.values.tolist() == ds.time.values.tolist()
    assert result.tas.attrs["units"] == "K"
    assert result.pr.attrs["units"] == "mm"
    assert "grid_mapping" not in result.tas.attrs
    assert result.attrs["title"] == "synthetic"
    assert "crs" not in result
    if with_time_bounds:
        assert "time_bounds" in result


@pytest.mark.parametrize("method", [None, "cover", "intersects"])
def test_clip_to_geometry_uses_regular_cell_sizes(
    method: str | None,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ds = _grid_dataset()
    area = _area()
    monkeypatch.setattr(
        ds.pyku,
        "get_area_def",
        Mock(return_value=area),
    )

    if method is None:
        result = features.clip_to_geometry(ds, box(0, 0, 2, 2))
    else:
        result = features.clip_to_geometry(
            ds,
            box(0, 0, 2, 2),
            method=method,
        )

    assert result.tas.shape == (2, 2)


def test_clip_centroid_includes_boundary_centers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ds = _grid_dataset()
    monkeypatch.setattr(
        ds.pyku,
        "get_area_def",
        Mock(return_value=_area()),
    )

    result = features.clip_to_geometry(
        ds,
        box(0, 0, 0.5, 2),
        method="centroid",
    )

    assert result.tas.shape == (2, 1)
    assert result.x.values.tolist() == [0.5]


def test_clip_intersects_partial_cell(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ds = _grid_dataset()
    monkeypatch.setattr(
        ds.pyku,
        "get_area_def",
        Mock(return_value=_area()),
    )

    result = features.clip_to_geometry(ds, box(0.1, 1.1, 0.9, 1.9))

    assert result.tas.shape == (1, 1)
    assert result.tas.item() == 1


@pytest.mark.parametrize("crs_as_coordinate", [False, True])
def test_clip_preserves_non_spatial_cf_metadata(
    crs_as_coordinate: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ds = _grid_dataset()
    ds = ds.assign_coords(
        time=np.array(["2000-01-15"], dtype="datetime64[ns]"),
        bnds=[0, 1],
    )
    ds["time_bounds"] = (
        ("time", "bnds"),
        np.array([[0, 31]], dtype=np.int32),
    )
    ds.time_bounds.attrs.update(
        units="days since 2000-01-01",
        long_name="time bounds",
    )
    ds.time_bounds.encoding["dtype"] = "int32"
    ds.time.attrs["bounds"] = "time_bounds"
    ds["crs"] = xr.DataArray(
        0,
        attrs={"grid_mapping_name": "latitude_longitude"},
    )
    ds.crs.encoding["dtype"] = "int32"
    if crs_as_coordinate:
        ds = ds.set_coords("crs")
    ds.tas.attrs["grid_mapping"] = "crs"
    ds.attrs["title"] = "synthetic clipping metadata"

    area = _area()
    monkeypatch.setattr(
        ds.pyku,
        "get_area_def",
        Mock(return_value=area),
    )
    triangle = Polygon([(0, 0), (2, 0), (0, 2)])

    result = features.clip_to_geometry(
        ds,
        triangle,
        method="centroid",
    )

    np.testing.assert_equal(
        result.tas.values,
        np.array([[1.0, np.nan], [3.0, 4.0]]),
    )
    assert result.tas.attrs["grid_mapping"] == "crs"
    assert result.time_bounds.dims == ("time", "bnds")
    np.testing.assert_array_equal(result.time_bounds.values, [[0, 31]])
    assert result.time_bounds.attrs == ds.time_bounds.attrs
    assert result.time_bounds.encoding["dtype"] == "int32"
    assert result.time.attrs["bounds"] == "time_bounds"

    crs = result.coords["crs"] if crs_as_coordinate else result["crs"]
    assert crs.dims == ()
    assert crs.item() == 0
    assert crs.attrs == ds.crs.attrs
    assert crs.encoding["dtype"] == "int32"
    assert result.attrs == ds.attrs


def test_regionalize_stays_grid_preserving_and_not_deprecated(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    warning = Mock()
    monkeypatch.setattr(features.logger, "warning", warning)
    monkeypatch.setattr(geo, "get_area_def", lambda dataset: _area())
    monkeypatch.setattr(
        features,
        "rasterize_polygons",
        lambda gdf, area_def: xr.Dataset(
            {
                "regions": (("y", "x"), [[0, 0], [1, 1]]),
                "region_index": ("region_name", [0, 1]),
                "region_name": ("region_name", ["west", "east"]),
            }
        ),
    )
    monkeypatch.setattr(
        "pyku.meta.get_geodata_varnames",
        lambda dataset: ["tas"],
    )
    ds = xr.Dataset(
        {"tas": (("time", "y", "x"), [[[1, 2], [3, 4]]])},
        coords={"time": [0], "y": [1.5, 0.5], "x": [0.5, 1.5]},
    )

    result = ds.pyku.regionalize(
        gpd.GeoDataFrame(geometry=[], crs="EPSG:4326"),
        method="mean",
        how="area",
    )

    assert result.tas.dims == ("region", "time", "y", "x")
    assert result.region.values.tolist() == ["west", "east"]
    np.testing.assert_equal(
        result.tas.values,
        np.array(
            [
                [[[1, 2], [np.nan, np.nan]]],
                [[[np.nan, np.nan], [3, 4]]],
            ]
        ),
    )
    warning.assert_not_called()


def test_aggregate_by_region_accessor_forwards_explicit_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ds = xr.Dataset()
    expected = xr.Dataset()
    aggregate = Mock(return_value=expected)
    monkeypatch.setattr(features, "aggregate_by_region", aggregate)
    gdf = gpd.GeoDataFrame(geometry=[], crs="EPSG:4326")

    result = ds.pyku.aggregate_by_region(
        gdf,
        statistic="sum",
        cell_selection="area",
    )

    assert result is expected
    aggregate.assert_called_once_with(
        ds,
        gdf,
        area_def=None,
        statistic="sum",
        cell_selection="area",
    )


def test_get_geometry_dataset_valid_and_invalid_area_names(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    crs_values = []
    _test_xvec(monkeypatch, crs_values)
    gdf = gpd.GeoDataFrame(geometry=[box(0, 0, 1, 1)], crs="EPSG:4326")
    monkeypatch.setattr(resources, "get_geodataframe", lambda identifier: gdf)
    area = _area()
    monkeypatch.setattr(geo, "list_standard_areas", lambda: ["test-area"])
    monkeypatch.setattr(geo, "load_area_def", lambda name: area)

    result = resources.get_geometry_dataset("test", area_def="test-area")

    assert "geometry" in result.coords
    assert crs_values == [gdf.crs, area.crs_wkt]
    with pytest.raises(ValueError, match="not a standard area"):
        resources.get_geometry_dataset("test", area_def="unknown")


def test_get_geometry_dataset_returns_real_geometry_indexed_dataset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gdf = gpd.GeoDataFrame(
        {"label": ["region"]},
        geometry=[box(0, 0, 1, 1)],
        crs="EPSG:4326",
    )
    monkeypatch.setattr(resources, "get_geodataframe", lambda identifier: gdf)

    result = resources.get_geometry_dataset("synthetic")

    assert isinstance(result, xr.Dataset)
    assert result.xvec.geom_coords_indexed
    assert result.sizes["geometry"] == 1
