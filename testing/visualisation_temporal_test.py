import matplotlib

matplotlib.use("Agg")

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest

import pyku
import xarray as xr
from pyku import features, visualisation


@pytest.fixture
def hourly_dataset() -> xr.Dataset:
    times = pd.date_range("2001-01-01", periods=4, freq="D")
    values = np.array([[0.0, 2.0], [2.0, 4.0], [4.0, 6.0], [6.0, 8.0]])
    dataset = xr.Dataset(
        {"tas": (("time", "x"), values)},
        coords={"time": times, "x": [0, 1]},
        attrs={"label": "Model"},
    )
    dataset["tas"].attrs.update(
        {"long_name": "Temperature", "units": "K"}
    )
    return dataset


def test_time_series_plots_spatial_means_at_native_timestamps(
    hourly_dataset: xr.Dataset,
) -> None:
    visualisation.time_series(hourly_dataset, var="tas")

    line = plt.gca().lines[0]
    np.testing.assert_allclose(
        np.asarray(line.get_ydata(), dtype=float),
        [1, 3, 5, 7],
    )
    assert line.get_label() == "Model"
    assert plt.gca().get_ylabel() == "Temperature [K]"
    plt.close("all")


def test_time_series_resamples_and_averages_each_bin(
    hourly_dataset: xr.Dataset,
) -> None:
    visualisation.time_series(
        hourly_dataset,
        var="tas",
        time_resolution="2D",
    )

    np.testing.assert_allclose(
        np.asarray(plt.gca().lines[0].get_ydata(), dtype=float),
        [2, 6],
    )
    plt.close("all")


def test_time_plots_preserve_a_singleton_time_dimension() -> None:
    dataset = xr.Dataset(
        {"tas": (("time", "x"), [[2.0]])},
        coords={"time": pd.date_range("2001-01-01", periods=1), "x": [0]},
    )

    visualisation.time_series(dataset, var="tas")
    np.testing.assert_allclose(
        np.asarray(plt.gca().lines[0].get_ydata(), dtype=float),
        [2.0],
    )
    plt.close("all")

    visualisation.climatology(dataset, var="tas")
    np.testing.assert_allclose(
        np.asarray(plt.gca().lines[0].get_ydata(), dtype=float),
        [2.0],
    )
    plt.close("all")


def test_time_series_accessor_forwards_layout(
    hourly_dataset: xr.Dataset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def capture_time_series(
        dataset: xr.Dataset,
        *datasets: xr.Dataset | None,
        **kwargs: object,
    ) -> None:
        captured["dataset"] = dataset
        captured.update(kwargs)

    monkeypatch.setattr(pyku.libvis, "time_series", capture_time_series)

    hourly_dataset.vis.time_series(var="tas", layout="2x2")

    assert captured["dataset"] is hourly_dataset
    assert captured["layout"] == "2x2"


def test_climatology_groups_by_month_and_dayofyear() -> None:
    times = pd.to_datetime(
        [
            "2001-01-01",
            "2001-01-02",
            "2001-02-01",
            "2002-01-01",
            "2002-01-02",
            "2002-02-01",
        ]
    )
    dataset = xr.Dataset(
        {"tas": (("time", "x"), [[1], [2], [10], [3], [4], [14]])},
        coords={"time": times, "x": [0]},
    )

    visualisation.climatology(
        dataset,
        var="tas",
        groupby="time.month",
    )
    np.testing.assert_allclose(
        np.asarray(plt.gca().lines[0].get_ydata(), dtype=float),
        [2.5, 12],
    )
    assert [label.get_text() for label in plt.gca().get_xticklabels()] == [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ]
    plt.close("all")

    visualisation.climatology(
        dataset,
        var="tas",
        groupby="time.dayofyear",
    )
    np.testing.assert_allclose(
        np.asarray(plt.gca().lines[0].get_ydata(), dtype=float),
        [2, 3, 12],
    )
    plt.close("all")


def test_climatology_groups_by_season() -> None:
    times = pd.to_datetime(
        [
            "2001-01-01",
            "2001-04-01",
            "2001-07-01",
            "2001-10-01",
            "2002-01-01",
            "2002-04-01",
            "2002-07-01",
            "2002-10-01",
        ]
    )
    dataset = xr.Dataset(
        {
            "tas": (
                ("time", "x"),
                [[1], [2], [3], [4], [5], [6], [7], [8]],
            )
        },
        coords={"time": times, "x": [0]},
    )

    visualisation.climatology(
        dataset,
        var="tas",
        groupby="time.season",
    )

    np.testing.assert_allclose(
        np.asarray(plt.gca().lines[0].get_ydata(), dtype=float),
        [3, 4, 5, 6],
    )
    assert [label.get_text() for label in plt.gca().get_xticklabels()] == [
        "DJF",
        "MAM",
        "JJA",
        "SON",
    ]
    plt.close("all")


def test_climatology_rejects_unsupported_calendar_component(
    hourly_dataset: xr.Dataset,
) -> None:
    with pytest.raises(ValueError, match="groupby must"):
        visualisation.climatology(
            hourly_dataset,
            var="tas",
            groupby="time.year",  # type: ignore[arg-type]
        )


def test_time_series_plots_regional_panels(
    hourly_dataset: xr.Dataset,
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    regions = gpd.GeoDataFrame(
        {"name": ["North", "South", "East"]},
        geometry=gpd.points_from_xy([0, 1, 2], [0, 1, 2]),
        crs="EPSG:4326",
    )
    calls: list[tuple[gpd.GeoDataFrame, str]] = []

    def regionalize(
        dataset: xr.Dataset,
        polygons: gpd.GeoDataFrame,
        dtype: str,
    ) -> xr.Dataset:
        calls.append((polygons, dtype))
        return xr.concat(
            [dataset, dataset, dataset],
            dim=xr.IndexVariable("region", ["North", "South", "East"]),
        )

    monkeypatch.setattr(features, "regionalize", regionalize)

    visualisation.time_series(
        hourly_dataset,
        var="tas",
        regions=regions,
        layout="2x2",
    )

    axes = plt.gcf().axes
    assert len(calls) == 1
    assert len(axes) == 4
    assert [axes[idx].get_title() for idx in range(3)] == [
        "North",
        "South",
        "East",
    ]
    assert not axes[3].get_visible()
    assert "provides 4 subplot slots for 3 regional time-series plots" in (
        caplog.text
    )
    assert list(regions.columns) == ["name", "geometry"]
    plt.close("all")


def test_time_series_rejects_an_axes_with_regions(
    hourly_dataset: xr.Dataset,
) -> None:
    regions = gpd.GeoDataFrame(
        geometry=gpd.points_from_xy([0], [0]),
        crs="EPSG:4326",
    )
    _, ax = plt.subplots()

    with pytest.raises(ValueError, match="ax cannot be used"):
        visualisation.time_series(
            hourly_dataset,
            var="tas",
            regions=regions,
            ax=ax,
        )
    plt.close("all")


def test_time_series_handles_a_single_region(
    hourly_dataset: xr.Dataset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    regions = gpd.GeoDataFrame(
        {"name": ["North"]},
        geometry=gpd.points_from_xy([0], [0]),
        crs="EPSG:4326",
    )

    def regionalize(
        dataset: xr.Dataset,
        polygons: gpd.GeoDataFrame,
        dtype: str,
    ) -> xr.Dataset:
        return xr.concat(
            [dataset],
            dim=xr.IndexVariable("region", ["North"]),
        )

    monkeypatch.setattr(features, "regionalize", regionalize)
    visualisation.time_series(
        hourly_dataset,
        var="tas",
        regions=regions,
    )

    assert len(plt.gcf().axes) == 2
    np.testing.assert_allclose(
        np.asarray(plt.gcf().axes[0].lines[0].get_ydata(), dtype=float),
        [1, 3, 5, 7],
    )
    assert not plt.gcf().axes[1].get_visible()
    plt.close("all")


def test_dataset_accessor_exposes_consolidated_temporal_api(
    hourly_dataset: xr.Dataset,
) -> None:
    assert hasattr(hourly_dataset.vis, "time_series")
    assert hasattr(hourly_dataset.vis, "climatology")
    assert not hasattr(hourly_dataset.vis, "time_serie")
    assert not hasattr(hourly_dataset.vis, "mean_vs_time")
    assert not hasattr(hourly_dataset.vis, "regional_mean_vs_time")
    assert not hasattr(hourly_dataset.vis, "daily_mean")
    assert not hasattr(hourly_dataset.vis, "monthly_mean")
    assert not hasattr(visualisation, "time_serie")
    assert not hasattr(visualisation, "mean_vs_time")
    assert not hasattr(visualisation, "regional_mean_vs_time")
    assert not hasattr(visualisation, "daily_mean")
    assert not hasattr(visualisation, "monthly_mean")


def test_dataset_accessor_forwards_to_consolidated_functions(
    hourly_dataset: xr.Dataset,
) -> None:
    hourly_dataset.vis.time_series(var="tas")
    np.testing.assert_allclose(
        np.asarray(plt.gca().lines[0].get_ydata(), dtype=float),
        [1, 3, 5, 7],
    )
    plt.close("all")

    hourly_dataset.vis.climatology(
        var="tas",
        groupby="time.dayofyear",
    )
    np.testing.assert_allclose(
        np.asarray(plt.gca().lines[0].get_ydata(), dtype=float),
        [1, 3, 5, 7],
    )
    plt.close("all")
