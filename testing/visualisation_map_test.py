from typing import Any

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pytest

import pyku
import xarray as xr
from pyku import meta, visualisation


@pytest.fixture(scope="module")
def small_dataset() -> xr.Dataset:
    """Return a small georeferenced dataset for map tests."""
    return pyku.resources.get_test_data("small_tas_dataset")


def test_map_data_limits_use_finite_robust_quantiles() -> None:
    dataset = xr.Dataset(
        {"tas": ("x", np.append(np.arange(100.0), 10000.0))},
    )

    lower, upper = visualisation._map_data_limits([dataset], "tas")

    assert lower == pytest.approx(2.0)
    assert upper == pytest.approx(98.0)


def test_map_data_limits_reject_all_nonfinite_values() -> None:
    dataset = xr.Dataset({"tas": ("x", [np.nan, np.inf, -np.inf])})

    with pytest.raises(ValueError, match="no finite values"):
        visualisation._map_data_limits([dataset], "tas")


def test_n_maps_does_not_mutate_plot_options(
    small_dataset: xr.Dataset,
) -> None:
    colorbar_kwargs: dict[str, Any] = {"label": "Custom label"}
    gridlines_kwargs: dict[str, Any] = {"linewidth": 0.5}
    axes_kwargs: dict[str, Any] = {"facecolor": "red"}
    figure_kwargs: dict[str, Any] = {"facecolor": "white"}

    visualisation.n_maps(
        small_dataset.isel(time=0),
        var="tas",
        colorbar_kwargs=colorbar_kwargs,
        gridlines_kwargs=gridlines_kwargs,
        gca_kwargs=axes_kwargs,
        gcf_kwargs=figure_kwargs,
    )

    figure = plt.gcf()
    assert len(figure.axes) == 2
    assert figure.axes[0].get_facecolor() == pytest.approx((1.0, 0.0, 0.0, 1.0))
    assert figure.axes[-1].get_ylabel() == "Custom label"
    assert colorbar_kwargs == {"label": "Custom label"}
    assert gridlines_kwargs == {"linewidth": 0.5}
    assert axes_kwargs == {"facecolor": "red"}
    assert figure_kwargs == {"facecolor": "white"}
    plt.close("all")


def test_map_spatial_dims_reorder_transposed_variable(
    small_dataset: xr.Dataset,
) -> None:
    dataset = small_dataset.isel(time=0)
    var = meta.get_geodata_varnames(dataset)[0]
    y_name, x_name = meta.get_projection_yx_varnames(dataset)
    assert y_name is not None
    assert x_name is not None
    if len(dataset[y_name].dims) == 1 and len(dataset[x_name].dims) == 1:
        expected_dims = (dataset[y_name].dims[0], dataset[x_name].dims[0])
    else:
        expected_dims = dataset[y_name].dims

    transposed = dataset.assign(
        {var: dataset[var].transpose(*reversed(dataset[var].dims))}
    )
    spatial_dims = visualisation._get_map_spatial_dims(transposed, var)

    assert spatial_dims == expected_dims
    np.testing.assert_array_equal(
        transposed[var].transpose(*spatial_dims).values,
        dataset[var].values,
    )


def test_percentile_map_accepts_other_spatial_dims_and_forwards_norm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = xr.Dataset(
        {
            "tas": (
                ("time", "northing", "easting"),
                np.arange(8.0).reshape(2, 2, 2),
            ),
        },
        coords={
            "time": [0, 1],
            "northing": [10, 20],
            "easting": [30, 40],
        },
    )
    norm = mcolors.Normalize(vmin=0, vmax=7)
    captured: dict[str, object] = {}

    def capture_maps(
        *datasets: xr.Dataset,
        **kwargs: object,
    ) -> None:
        captured["datasets"] = datasets
        captured.update(kwargs)

    monkeypatch.setattr(meta, "get_geodata_varnames", lambda _ds: ["tas"])
    monkeypatch.setattr(visualisation, "n_maps", capture_maps)

    visualisation.percentile_map(dataset, var="tas", norm=norm)

    plotted_datasets = captured["datasets"]
    assert isinstance(plotted_datasets, tuple)
    assert plotted_datasets[0]["p50"].dims == ("northing", "easting")
    assert captured["norm"] is norm
