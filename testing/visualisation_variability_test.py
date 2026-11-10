import geopandas as gpd
import matplotlib
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from shapely.geometry import Point

matplotlib.use("Agg")

import matplotlib.pyplot as plt

import pyku.features as features
import pyku.visualisation as visualisation


@pytest.fixture
def variability_dataset() -> xr.Dataset:
    """Return a small two-year dataset for variability plotting."""
    values = np.arange(24 * 4, dtype=float).reshape(24, 2, 2)
    time = pd.date_range("2000-01-01", periods=24, freq="MS")
    return xr.Dataset(
        {"tas": (("time", "y", "x"), values)},
        coords={"time": time},
        attrs={"label": "Test dataset"},
    )


def test_variability_supports_monthly_and_seasonal_grouping(
    variability_dataset: xr.Dataset,
) -> None:
    _, monthly_ax = plt.subplots()
    visualisation.variability(
        variability_dataset,
        var="tas",
        ax=monthly_ax,
    )
    assert monthly_ax.get_xticklabels()[0].get_text() == "January"
    plt.close()

    _, seasonal_ax = plt.subplots()
    visualisation.variability(
        variability_dataset,
        var="tas",
        groupby="time.season",
        ax=seasonal_ax,
    )
    assert [label.get_text() for label in seasonal_ax.get_xticklabels()] == [
        "DJF",
        "MAM",
        "JJA",
        "SON",
    ]
    plt.close()


def test_variability_compares_two_datasets(
    variability_dataset: xr.Dataset,
) -> None:
    _, ax = plt.subplots()
    reference = variability_dataset.assign_attrs(label="Reference")
    visualisation.variability(
        variability_dataset,
        reference,
        var="tas",
        ax=ax,
    )

    legend = ax.get_legend()
    assert legend is not None
    assert [text.get_text() for text in legend.get_texts()] == [
        "Test dataset",
        "Reference",
    ]
    plt.close()


def test_variability_plots_regional_monthly_panels(
    variability_dataset: xr.Dataset,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    gdf = gpd.GeoDataFrame(
        {"name": ["Test region"]},
        geometry=[Point(0, 0)],
    )

    def regionalize(
        dataset: xr.Dataset,
        regions: gpd.GeoDataFrame,
    ) -> xr.Dataset:
        return dataset.expand_dims(region=["Test region"])

    monkeypatch.setattr(features, "regionalize", regionalize)
    visualisation.variability(
        variability_dataset,
        var="tas",
        gdf=gdf,
        layout="1x1",
    )

    assert plt.gcf().axes[0].get_title() == "Test region"
    assert len(plt.gcf().axes) == 1
    plt.close(plt.gcf())


def test_variability_rejects_regional_and_temporal_grouping(
    variability_dataset: xr.Dataset,
) -> None:
    gdf = gpd.GeoDataFrame(
        {"name": ["Test region"]},
        geometry=[Point(0, 0)],
    )

    with pytest.raises(ValueError, match="cannot be used together"):
        visualisation.variability(
            variability_dataset,
            var="tas",
            groupby="time.season",
            gdf=gdf,
        )


def test_variability_rejects_day_of_year_grouping(
    variability_dataset: xr.Dataset,
) -> None:
    with pytest.raises(ValueError, match="groupby must"):
        visualisation.variability(
            variability_dataset,
            var="tas",
            groupby="time.dayofyear",  # type: ignore[arg-type]
        )


def test_variability_is_available_on_dataset_accessor(
    variability_dataset: xr.Dataset,
) -> None:
    variability_dataset.vis.variability(var="tas", groupby="time.season")
    plt.close()
