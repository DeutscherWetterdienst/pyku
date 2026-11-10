import matplotlib
matplotlib.use("Agg")

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import xarray as xr

import pyku.features as features
import pyku.visualisation as visualisation


@pytest.fixture
def bias_datasets() -> tuple[xr.Dataset, xr.Dataset]:
    times = pd.date_range("2001-01-01", periods=12, freq="MS")
    bias = np.arange(-6, 6, dtype=float)[:, None, None]
    model = xr.Dataset(
        {"tas": (("time", "y", "x"), bias)},
        coords={"time": times, "y": [0], "x": [0]},
    )
    reference = xr.zeros_like(model)
    return model, reference


def test_bias_cycle_defaults_to_monthly_grouping(
    bias_datasets: tuple[xr.Dataset, xr.Dataset],
) -> None:
    model, reference = bias_datasets

    visualisation.bias_cycle(model, reference, var="tas")

    ax = plt.gca()
    assert [label.get_text() for label in ax.get_xticklabels()] == [
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
    assert ax.get_ylabel() == "Mean bias for tas"
    plt.close("all")


def test_bias_cycle_groups_by_season(
    bias_datasets: tuple[xr.Dataset, xr.Dataset],
) -> None:
    model, reference = bias_datasets

    visualisation.bias_cycle(
        model,
        reference,
        var="tas",
        groupby="time.season",
    )

    assert [label.get_text() for label in plt.gca().get_xticklabels()] == [
        "DJF",
        "MAM",
        "JJA",
        "SON",
    ]
    plt.close("all")


def test_bias_cycle_plots_regional_panels(
    bias_datasets: tuple[xr.Dataset, xr.Dataset],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    model, reference = bias_datasets
    gdf = gpd.GeoDataFrame(
        {"name": ["North", "South"]},
        geometry=gpd.points_from_xy([0, 1], [0, 1]),
        crs="EPSG:4326",
    )
    calls: list[tuple[gpd.GeoDataFrame, str]] = []

    def regionalize(
        dataset: xr.Dataset,
        regions: gpd.GeoDataFrame,
        dtype: str,
    ) -> xr.Dataset:
        calls.append((regions, dtype))
        return xr.concat(
            [dataset, dataset],
            dim=xr.IndexVariable("region", ["North", "South"]),
        )

    monkeypatch.setattr(features, "regionalize", regionalize)

    visualisation.bias_cycle(
        model,
        reference,
        var="tas",
        gdf=gdf,
        layout="1x2",
    )

    axes = plt.gcf().axes
    assert len(calls) == 2
    assert len(axes) == 2
    assert [axes[idx].get_title() for idx in range(2)] == ["North", "South"]
    plt.close("all")


def test_bias_cycle_accessor_replaces_specific_bias_accessors(
    bias_datasets: tuple[xr.Dataset, xr.Dataset],
) -> None:
    model, _reference = bias_datasets

    assert hasattr(model.vis, "bias_cycle")
    assert not hasattr(model.vis, "monthly_bias")
    assert not hasattr(model.vis, "regional_monthly_bias")
    assert hasattr(visualisation, "bias_cycle")
    assert not hasattr(visualisation, "monthly_bias")
    assert not hasattr(visualisation, "regional_monthly_bias")


def test_bias_cycle_rejects_unsupported_groupby(
    bias_datasets: tuple[xr.Dataset, xr.Dataset],
) -> None:
    model, reference = bias_datasets

    with pytest.raises(ValueError, match="groupby must"):
        visualisation.bias_cycle(
            model,
            reference,
            var="tas",
            groupby="time.year",  # type: ignore[arg-type]
        )


def test_bias_cycle_rejects_mismatched_spatial_coordinates(
    bias_datasets: tuple[xr.Dataset, xr.Dataset],
) -> None:
    model, reference = bias_datasets
    reference = reference.assign_coords(y=[1])

    with pytest.raises(ValueError, match="spatial coordinates"):
        visualisation.bias_cycle(model, reference, var="tas")
