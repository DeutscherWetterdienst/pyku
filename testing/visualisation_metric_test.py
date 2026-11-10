from typing import Any

import numpy as np
import pytest

import pyku
import pyku.visualisation as visualisation
import xarray as xr


@pytest.fixture(scope="module")
def small_dataset():
    """Return a small georeferenced dataset for metric tests."""
    return pyku.resources.get_test_data("small_tas_dataset")


@pytest.fixture(scope="module")
def seasonal_dataset():
    """Return a dataset containing all four calendar seasons."""
    return pyku.resources.get_test_data("hyras_tas_lowres_2yr")


@pytest.fixture
def captured_maps(monkeypatch):
    """Capture arguments passed to the common map plotting function."""
    captured = {}

    def capture(*datasets, **kwargs):
        captured["datasets"] = datasets
        captured["kwargs"] = kwargs

    monkeypatch.setattr(visualisation, "n_maps", capture)
    return captured


@pytest.mark.parametrize("metric", ["mae", "bias", "mse", "rmse", "pcc"])
def test_metric_map_supports_all_metrics(
    small_dataset,
    captured_maps,
    metric,
):
    visualisation.metric_map(
        small_dataset,
        ref=small_dataset,
        var="tas",
        metric=metric,
    )

    assert captured_maps["kwargs"]["var"] == metric
    assert len(captured_maps["datasets"]) == 1
    assert metric in captured_maps["datasets"][0]


def test_metric_map_passes_layout_to_map_renderer(
    small_dataset: xr.Dataset,
    captured_maps: dict[str, Any],
) -> None:
    visualisation.metric_map(
        small_dataset,
        ref=small_dataset,
        var="tas",
        metric="mae",
        layout="x3",
    )

    assert captured_maps["kwargs"]["layout"] == "x3"


def test_metric_map_supports_seasonal_grouping(
    seasonal_dataset: xr.Dataset,
    captured_maps: dict[str, Any],
) -> None:
    visualisation.metric_map(
        seasonal_dataset,
        ref=seasonal_dataset,
        var="tas",
        metric="bias",
        groupby="time.season",
        layout="x2",
    )

    results = captured_maps["datasets"]
    assert len(results) == 4
    assert {result["bias"].attrs["label"] for result in results} == {
        "DJF",
        "MAM",
        "JJA",
        "SON",
    }
    assert captured_maps["kwargs"]["layout"] == "x2"


def test_metric_map_calculates_bias_and_preserves_units(
    small_dataset: xr.Dataset,
    captured_maps: dict[str, Any],
) -> None:
    reference = small_dataset.copy(deep=True)
    reference["tas"] = reference["tas"] + 2.0

    visualisation.metric_map(
        small_dataset,
        ref=reference,
        var="tas",
        metric="bias",
    )

    result = captured_maps["datasets"][0]["bias"]
    values = result.compute().values
    assert np.isfinite(values).any()
    assert np.allclose(values[np.isfinite(values)], -2.0)
    assert result.attrs["units"] == small_dataset["tas"].attrs["units"]


def test_metric_map_rejects_misaligned_spatial_coordinates(
    small_dataset: xr.Dataset,
    captured_maps: dict[str, Any],
) -> None:
    reference = small_dataset.assign_coords(x=small_dataset.x + 1)

    with pytest.raises(ValueError, match="spatial coordinates"):
        visualisation.metric_map(
            small_dataset,
            ref=reference,
            var="tas",
        )


def test_metric_map_allows_extra_scalar_coordinates(
    small_dataset: xr.Dataset,
    captured_maps: dict[str, Any],
) -> None:
    model = small_dataset.assign_coords(height=2.0)

    visualisation.metric_map(
        model,
        ref=small_dataset,
        var="tas",
    )

    assert len(captured_maps["datasets"]) == 1


def test_grouped_metric_maps_use_calendar_order(
    seasonal_dataset: xr.Dataset,
    captured_maps: dict[str, Any],
) -> None:
    visualisation.metric_map(
        seasonal_dataset,
        ref=seasonal_dataset,
        var="tas",
        metric="bias",
        groupby="time.season",
    )

    labels = [
        result["bias"].attrs["label"]
        for result in captured_maps["datasets"]
    ]
    assert labels == ["DJF", "MAM", "JJA", "SON"]


def test_metric_map_rejects_unknown_metric(small_dataset):
    with pytest.raises(ValueError, match="Invalid metric"):
        visualisation.metric_map(
            small_dataset,
            ref=small_dataset,
            var="tas",
            metric="unknown",
        )


def test_metric_map_rejects_unknown_groupby(
    small_dataset,
):
    with pytest.raises(ValueError, match="Unsupported groupby"):
        visualisation.metric_map(
            small_dataset,
            ref=small_dataset,
            var="tas",
            metric="mae",
            groupby="time.year",
        )
