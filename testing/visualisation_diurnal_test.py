import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import xarray as xr

import pyku.visualisation as visualisation
from pyku.resources import get_test_data


@pytest.fixture
def hourly_dataset() -> xr.Dataset:
    times = pd.date_range("2020-01-01", periods=24 * 60, freq="h")
    values = (
        np.arange(len(times), dtype=float)[:, None, None]
        + np.array([[0, 1], [2, 3]])
    )
    dataset = xr.Dataset(
        {"tas": (("time", "y", "x"), values)},
        coords={"time": times, "y": [0, 1], "x": [0, 1]},
        attrs={"label": "Dataset"},
    )
    dataset["tas"].attrs.update(
        {"long_name": "Temperature", "units": "K"}
    )
    return dataset


@pytest.fixture(scope="module")
def hourly_test_datasets() -> tuple[xr.Dataset, xr.Dataset]:
    dataset = get_test_data("7day-low-res-hourly-tas")
    reference = get_test_data("low-res-hourly-tas-data")
    return dataset, reference


def test_diurnal_cycle_plots_up_to_two_datasets(
    hourly_test_datasets: tuple[xr.Dataset, xr.Dataset],
) -> None:
    dataset, reference = hourly_test_datasets

    visualisation.diurnal_cycle(
        dataset,
        reference,
        var="tas",
        variability=False,
    )

    assert len(plt.gca().lines) == 2
    legend = plt.gca().get_legend()
    assert legend is not None
    assert len(legend.texts) == 2
    plt.close("all")


def test_dataset_accessor_exposes_only_unified_diurnal_cycle(
    hourly_dataset: xr.Dataset,
) -> None:
    assert hasattr(hourly_dataset.vis, "diurnal_cycle")
    assert not hasattr(hourly_dataset.vis, "diurnal_cycle_by_period")
    assert not hasattr(hourly_dataset.vis, "diurnal_cycle_variability")


def test_diurnal_cycle_rejects_more_than_two_datasets(
    hourly_dataset: xr.Dataset,
) -> None:
    with pytest.raises(ValueError, match="at most two"):
        visualisation.diurnal_cycle(
            hourly_dataset,
            hourly_dataset,
            hourly_dataset,
            var="tas",
        )


def test_diurnal_cycle_groups_by_month(
    hourly_dataset: xr.Dataset,
) -> None:
    visualisation.diurnal_cycle(
        hourly_dataset,
        var="tas",
        groupby="time.month",
    )

    figure = plt.gcf()
    assert len(figure.axes) == 12
    subplot_spec = figure.axes[0].get_subplotspec()
    assert subplot_spec is not None
    grid = subplot_spec.get_gridspec()
    assert grid.nrows == 4
    assert grid.ncols == 3
    assert figure.axes[0].get_title() == "January"
    assert figure.axes[1].get_title() == "February"
    plt.close("all")


def test_diurnal_cycle_accepts_a_custom_monthly_layout(
    hourly_dataset: xr.Dataset,
) -> None:
    visualisation.diurnal_cycle(
        hourly_dataset,
        var="tas",
        groupby="time.month",
        layout="3x4",
    )

    figure = plt.gcf()
    assert len(figure.axes) == 12
    subplot_spec = figure.axes[0].get_subplotspec()
    assert subplot_spec is not None
    grid = subplot_spec.get_gridspec()
    assert grid.nrows == 3
    assert grid.ncols == 4
    plt.close("all")


def test_diurnal_cycle_warns_when_seasons_are_missing(
    hourly_dataset: xr.Dataset,
    caplog: pytest.LogCaptureFixture,
) -> None:
    winter_data = hourly_dataset.sel(time=slice("2020-01-01", "2020-01-31"))

    visualisation.diurnal_cycle(
        winter_data,
        var="tas",
        groupby="time.season",
        layout="2x2",
    )

    assert (
        "Expected 4 groups for season diurnal cycles, but found group "
        "counts [1]"
    ) in caplog.text
    assert sum(ax.get_visible() for ax in plt.gcf().axes) == 1
    plt.close("all")


def test_diurnal_cycle_groups_two_datasets(
    hourly_dataset: xr.Dataset,
) -> None:
    reference = hourly_dataset.copy(deep=True)

    visualisation.diurnal_cycle(
        hourly_dataset,
        reference,
        var="tas",
        groupby="time.month",
    )

    assert len(plt.gcf().axes[0].lines) == 2
    plt.close("all")


def test_diurnal_cycle_matches_periods_by_key(
    hourly_dataset: xr.Dataset,
) -> None:
    january = hourly_dataset.sel(time=slice("2020-01-01", "2020-01-31"))
    february = hourly_dataset.sel(time=slice("2020-01-01", "2020-01-31"))
    february = february.assign_coords(
        time=february.time + pd.Timedelta(days=31)
    )
    february.attrs["label"] = "February data"

    visualisation.diurnal_cycle(
        january,
        february,
        var="tas",
        groupby="time.month",
    )

    axes = plt.gcf().axes
    assert axes[0].get_title() == "January"
    assert [line.get_label() for line in axes[0].lines] == ["Dataset"]
    assert axes[1].get_title() == "February"
    assert [line.get_label() for line in axes[1].lines] == [
        "February data"
    ]
    plt.close("all")


def test_diurnal_cycle_groups_by_season(
    hourly_dataset: xr.Dataset,
) -> None:
    visualisation.diurnal_cycle(
        hourly_dataset,
        var="tas",
        groupby="time.season",
    )

    figure = plt.gcf()
    assert len(figure.axes) == 4
    assert figure.axes[0].get_title() == "DJF"
    plt.close("all")


def test_diurnal_cycle_variability_plots_one_dataset(
    hourly_dataset: xr.Dataset,
) -> None:
    visualisation.diurnal_cycle(
        hourly_dataset,
        var="tas",
        variability=True,
    )

    legend = plt.gca().get_legend()
    assert legend is not None
    assert [text.get_text() for text in legend.texts] == ["Dataset"]
    assert plt.gca().get_ylabel() == "Temperature (K)"
    plt.close("all")


def test_diurnal_cycle_variability_compares_two_datasets(
    hourly_test_datasets: tuple[xr.Dataset, xr.Dataset],
) -> None:
    dataset, reference = hourly_test_datasets

    visualisation.diurnal_cycle(
        dataset,
        reference,
        var="tas",
        variability=True,
    )

    legend = plt.gca().get_legend()
    assert legend is not None
    assert len(legend.texts) == 2
    expected_ylabel = (
        f"{dataset.tas.attrs['long_name']} "
        f"({dataset.tas.attrs['units']})"
    )
    assert plt.gca().get_ylabel() == expected_ylabel
    plt.close("all")


def test_diurnal_cycle_rejects_unsupported_groupby(
    hourly_dataset: xr.Dataset,
) -> None:
    with pytest.raises(ValueError, match="groupby must"):
        visualisation.diurnal_cycle(
            hourly_dataset,
            var="tas",
            groupby="time.year",
        )


def test_diurnal_cycle_rejects_combined_modes(
    hourly_dataset: xr.Dataset,
) -> None:
    with pytest.raises(ValueError, match="cannot be used together"):
        visualisation.diurnal_cycle(
            hourly_dataset,
            hourly_dataset,
            var="tas",
            groupby="time.month",
            variability=True,
        )
