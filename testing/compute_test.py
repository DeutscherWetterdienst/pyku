import unittest

import numpy as np

import xarray as xr
from pyku import compute, timekit


def make_daily_temperature_dataset(
    dates: list[str],
    temperatures: list[float],
) -> xr.Dataset:
    ds = xr.Dataset(
        {
            "tas": (
                ("time", "lat", "lon"),
                np.asarray(temperatures)[:, None, None],
                {"units": "Celsius"},
            )
        },
        coords={
            "time": np.array(dates, dtype="datetime64[ns]"),
            "lat": ("lat", [50.0], {"units": "degrees_north"}),
            "lon": ("lon", [10.0], {"units": "degrees_east"}),
        },
    )
    return ds


class TestComputeMethods(unittest.TestCase):
    def test_resampling_preserves_existing_time_sums(self) -> None:
        ds = xr.Dataset(
            {
                "pr": (
                    ("time", "lat", "lon"),
                    np.array([1.0, 2.0])[:, None, None],
                    {"units": "mm", "cell_methods": "time: sum"},
                )
            },
            coords={
                "time": np.array(
                    ["2024-01-01", "2024-01-02"], dtype="datetime64[ns]"
                ),
                "lat": ("lat", [50.0], {"units": "degrees_north"}),
                "lon": ("lon", [10.0], {"units": "degrees_east"}),
            },
        )

        output = timekit.resample_datetimes(
            ds,
            how="sum",
            frequency="1D",
            data_frequency="1D",
        )

        np.testing.assert_array_equal(output.pr.values[:, 0, 0], [1.0, 2.0])

    def test_time_bounds_reject_missing_timestamps(self) -> None:
        ds = make_daily_temperature_dataset(
            ["2024-01-01", "2024-01-03", "2024-01-04"],
            [10.0, 5.0, 0.0],
        )

        with self.assertRaisesRegex(ValueError, "missing or irregular"):
            timekit.set_time_bounds_from_time_labels(ds, frequency="1D")

    def test_calc_degreeday_infers_frequency_when_resampling(self) -> None:
        ds = make_daily_temperature_dataset(
            [
                "2024-01-01",
                "2024-01-02",
                "2024-01-03",
                "2024-01-04",
            ],
            [10.0, 15.0, 5.0, 20.0],
        )

        output = compute.calc_degreeday(ds, period="2D")

        np.testing.assert_array_equal(
            output.time.values,
            np.array(["2024-01-01", "2024-01-03"], dtype="datetime64[ns]"),
        )
        np.testing.assert_array_equal(output.gt.values[:, 0, 0], [10.0, 15.0])
        np.testing.assert_array_equal(
            output.time_bnds.values,
            np.array(
                [
                    ["2024-01-01", "2024-01-03"],
                    ["2024-01-03", "2024-01-05"],
                ],
                dtype="datetime64[ns]",
            ),
        )
        self.assertEqual(output.time.attrs["bounds"], "time_bnds")
        self.assertEqual(output.gt.attrs["units"], "K day")
        self.assertEqual(output.gt.attrs["long_name"], "degree day")
        self.assertEqual(output.gt.attrs["standard_name"], "degree_day")
        self.assertEqual(output.gt.attrs["cell_methods"], "time: sum")

    def test_calc_degreeday_integrates_when_frequency_is_unchanged(
        self,
    ) -> None:
        ds = make_daily_temperature_dataset(
            ["2024-01-01", "2024-01-02"],
            [10.0, 15.0],
        )

        output = compute.calc_degreeday(
            ds,
            period="1D",
            data_frequency="1D",
        )

        np.testing.assert_array_equal(output.gt.values[:, 0, 0], [10.0, 0.0])
        self.assertEqual(output.gt.attrs["units"], "K day")

    def test_calc_degreeday_uses_explicit_frequency_when_resampling(
        self,
    ) -> None:
        ds = make_daily_temperature_dataset(
            ["2024-01-01", "2024-01-02"],
            [10.0, 15.0],
        )

        output = compute.calc_degreeday(
            ds,
            period="2D",
            data_frequency="1D",
        )

        np.testing.assert_array_equal(
            output.time.values,
            np.array(["2024-01-01"], dtype="datetime64[ns]"),
        )
        np.testing.assert_array_equal(output.gt.values[:, 0, 0], [10.0])
        np.testing.assert_array_equal(
            output.time_bnds.values,
            np.array(
                [["2024-01-01", "2024-01-03"]],
                dtype="datetime64[ns]",
            ),
        )
        self.assertEqual(output.time.attrs["bounds"], "time_bnds")
        self.assertEqual(output.gt.attrs["units"], "K day")
        self.assertEqual(output.gt.attrs["long_name"], "degree day")
        self.assertEqual(output.gt.attrs["standard_name"], "degree_day")
        self.assertEqual(output.gt.attrs["cell_methods"], "time: sum")


if __name__ == "__main__":
    unittest.main()
