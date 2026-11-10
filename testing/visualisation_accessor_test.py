import pytest

import pyku
import xarray as xr


def test_combine_masks_accessor_calls_plural_function(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    dataset = xr.Dataset({"tas": ("x", [1.0])})
    captured: list[xr.Dataset] = []

    def combine_masks(*datasets: xr.Dataset) -> xr.Dataset:
        captured.extend(datasets)
        return dataset

    monkeypatch.setattr(pyku.libmask, "combine_masks", combine_masks)

    result = dataset.pyku.combine_masks()

    assert result is dataset
    assert len(captured) == 1
    assert captured[0] is dataset
