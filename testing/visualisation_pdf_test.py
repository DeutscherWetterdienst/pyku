import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import xarray as xr

import pyku.visualisation as visualisation


@pytest.fixture
def monthly_data() -> xr.DataArray:
    time = pd.date_range("2001-01-01", periods=12, freq="MS")
    return xr.DataArray(
        np.arange(12, dtype=float),
        dims="time",
        coords={"time": time},
    )


def test_pdf_accepts_custom_monthly_layout(
    monthly_data: xr.DataArray,
) -> None:
    visualisation.pdf(
        monthly_data,
        groupby="time.month",
        layout="3x4",
    )

    figure = plt.gcf()
    assert len(figure.axes) == 12
    subplot_spec = figure.axes[0].get_subplotspec()
    assert subplot_spec is not None
    grid = subplot_spec.get_gridspec()
    assert (grid.nrows, grid.ncols) == (3, 4)
    plt.close("all")


def test_pdf_preserves_requested_grouped_figure_size(
    monthly_data: xr.DataArray,
) -> None:
    visualisation.pdf(
        monthly_data,
        groupby="time.month",
        size_inches=(18, 12),
    )

    np.testing.assert_allclose(plt.gcf().get_size_inches(), (18, 12))
    plt.close("all")


def test_pdf_handles_dask_backed_data(
    monthly_data: xr.DataArray,
) -> None:
    visualisation.pdf(monthly_data.chunk({"time": 3}))

    assert len(plt.gca().lines) == 1
    plt.close("all")


def test_pdf_warns_when_seasonal_groups_are_missing(
    monthly_data: xr.DataArray,
    caplog: pytest.LogCaptureFixture,
) -> None:
    winter_data = monthly_data.sel(time=slice("2001-01-01", "2001-02-28"))

    visualisation.pdf(
        winter_data,
        groupby="time.season",
        layout="2x2",
    )

    assert "Expected 4 groups for season PDFs, but found group counts [1]" in (
        caplog.text
    )
    assert sum(ax.get_visible() for ax in plt.gcf().axes) == 1
    plt.close("all")


def test_pdf_matches_groups_by_calendar_key(
    monthly_data: xr.DataArray,
) -> None:
    partial_data = monthly_data.isel(time=[1, 2])

    visualisation.pdf(
        monthly_data,
        partial_data,
        groupby="time.month",
    )

    axes = plt.gcf().axes
    assert axes[0].get_title() == "January"
    assert [line.get_label() for line in axes[0].lines] == ["Dataset 0"]
    assert axes[1].get_title() == "February"
    assert [line.get_label() for line in axes[1].lines] == [
        "Dataset 0",
        "Dataset 1",
    ]
    plt.close("all")


def test_pdf_subsamples_dask_backed_data(
    monthly_data: xr.DataArray,
) -> None:
    visualisation.pdf(
        monthly_data.chunk({"time": 3}),
        nsamples=5,
    )

    assert len(plt.gca().lines) == 1
    plt.close("all")
