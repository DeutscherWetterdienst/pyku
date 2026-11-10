import numpy as np
import pytest

import xarray as xr
from pyku import compute, timekit


def make_dataset(
    values: list[float],
    units: str,
) -> xr.Dataset:
    return xr.Dataset(
        {
            "tas": (
                ("time", "lat", "lon"),
                np.asarray(values)[:, None, None],
                {"units": units},
            ),
        },
        coords={
            "time": xr.date_range("2024-01-01", periods=len(values), freq="D"),
            "lat": ("lat", [50.0], {"units": "degrees_north"}),
            "lon": ("lon", [10.0], {"units": "degrees_east"}),
        },
    )


@pytest.mark.parametrize("cell_methods", [None, "time: sum"])
@pytest.mark.parametrize("frequency", ["1D", "2D"])
def test_sum_preserves_amounts_without_duration_scaling(
    cell_methods: str | None,
    frequency: str,
) -> None:
    ds = make_dataset([1.0, 2.0, 3.0, 4.0], "mm")
    if cell_methods is not None:
        ds.tas.attrs["cell_methods"] = cell_methods

    output = timekit.resample_datetimes(ds, how="sum", frequency=frequency)

    expected = [1.0, 2.0, 3.0, 4.0] if frequency == "1D" else [3.0, 7.0]
    np.testing.assert_allclose(output.tas.values.ravel(), expected)
    assert output.tas.attrs["cell_methods"] == "time: sum"


@pytest.mark.parametrize("units", ["mm", "mm s-1"])
@pytest.mark.parametrize("frequency", ["1D", "2D"])
def test_sum_preserves_all_missing_bins(
    units: str,
    frequency: str,
) -> None:
    ds = make_dataset([np.nan, np.nan, 2.0, np.nan], units)

    output = timekit.resample_datetimes(ds, how="sum", frequency=frequency)

    expected = [np.nan, np.nan, 2.0, np.nan]
    if frequency == "2D":
        expected = [np.nan, 2.0]
    scale = 86400 if units == "mm s-1" else 1
    np.testing.assert_allclose(
        output.tas.values.ravel(),
        np.asarray(expected) * scale,
        equal_nan=True,
    )


@pytest.mark.parametrize("frequency", ["1D", "2D"])
@pytest.mark.parametrize("units", ["mm s-1", "mm h-1"])
def test_sum_integrates_rates_with_unit_conversion(
    frequency: str,
    units: str,
) -> None:
    ds = make_dataset([1.0, 2.0, 3.0, 4.0], units)

    output = timekit.resample_datetimes(ds, how="sum", frequency=frequency)

    expected = [1.0, 2.0, 3.0, 4.0] if frequency == "1D" else [3.0, 7.0]
    scale = 86400 if units == "mm s-1" else 24
    amounts = output.tas.metpy.convert_units("mm")
    np.testing.assert_allclose(
        amounts.values.ravel(),
        np.asarray(expected) * scale,
    )


def test_degree_days_integrate_subdaily_temperature_intervals() -> None:
    ds = make_dataset([10.0, 10.0, 5.0, 5.0], "Celsius")
    ds = ds.assign_coords(
        time=xr.date_range("2024-01-01", periods=4, freq="12h"),
    )

    output = compute.calc_degreeday(ds, period="1D", data_frequency="12h")

    np.testing.assert_allclose(output.gt.values.ravel(), [10.0, 15.0])
    assert output.gt.attrs["units"] == "K day"
    output.gt.metpy.quantify()
