import unittest
from unittest.mock import patch

import cftime
import numpy as np
import xarray as xr

from pyku import drs, timekit


def make_dataset(bounds):
    bounds = np.asarray(bounds)
    time = np.array([bounds[0, 0] + (bounds[0, 1] - bounds[0, 0]) / 2])
    return xr.Dataset(
        {
            "tas": ("time", [1.0]),
            "time_bnds": (("time", "bnds"), bounds),
        },
        coords={"time": time},
    )


class TestDailyFrequencyBounds(unittest.TestCase):
    def test_daily_midnight_bounds_normalize_24_hour_frequency(self):
        ds = make_dataset(
            np.array([["2026-09-01", "2026-09-02"]], dtype="datetime64[ns]")
        )
        with patch("pyku.meta.get_frequency", return_value="24h"):
            self.assertEqual(
                drs._get_cmor_frequency_offset(ds, "24h").freqstr, "D"
            )
            self.assertEqual(
                drs._to_cmor_attrs_frequency(ds).attrs["frequency"], "day"
            )

    def test_non_midnight_24_hour_bounds_are_not_normalized(self):
        ds = make_dataset(
            np.array(
                [["2026-09-01T12", "2026-09-02T12"]],
                dtype="datetime64[ns]",
            )
        )

        self.assertEqual(
            drs._get_cmor_frequency_offset(ds, "24h").freqstr, "24h"
        )

    def test_contiguous_cftime_daily_bounds_are_normalized(self):
        bounds = np.array(
            [
                [
                    cftime.DatetimeProlepticGregorian(2026, 9, 1),
                    cftime.DatetimeProlepticGregorian(2026, 9, 2),
                ],
                [
                    cftime.DatetimeProlepticGregorian(2026, 9, 2),
                    cftime.DatetimeProlepticGregorian(2026, 9, 3),
                ],
            ],
            dtype=object,
        )
        ds = xr.Dataset(
            {
                "tas": ("time", [1.0, 2.0]),
                "time_bnds": (("time", "bnds"), bounds),
            },
            coords={
                "time": [
                    cftime.DatetimeProlepticGregorian(2026, 9, 1, 12),
                    cftime.DatetimeProlepticGregorian(2026, 9, 2, 12),
                ]
            },
        )

        self.assertTrue(drs._has_daily_time_bounds(ds))
        self.assertEqual(
            drs._get_cmor_frequency_offset(ds, "24h").freqstr,
            "D",
        )

    def test_missing_or_non_daily_bounds_do_not_normalize(self):
        ds = xr.Dataset(
            {"tas": ("time", [1.0])},
            coords={
                "time": np.array(["2026-09-01T12"], dtype="datetime64[ns]")
            },
        )

        self.assertFalse(drs._has_daily_time_bounds(ds))
        self.assertEqual(
            drs._get_cmor_frequency_offset(ds, "24h").freqstr, "24h"
        )

    def test_gapped_daily_bounds_are_not_normalized(self):
        bounds = np.array(
            [
                ["2026-09-01", "2026-09-02"],
                ["2026-09-03", "2026-09-04"],
            ],
            dtype="datetime64[ns]",
        )
        ds = xr.Dataset(
            {
                "tas": ("time", [1.0, 2.0]),
                "time_bnds": (("time", "bnds"), bounds),
            },
            coords={
                "time": np.array(
                    ["2026-09-01T12", "2026-09-03T12"],
                    dtype="datetime64[ns]",
                )
            },
        )

        self.assertFalse(drs._has_daily_time_bounds(ds))
        self.assertEqual(
            drs._get_cmor_frequency_offset(ds, "24h").freqstr, "24h"
        )

    def test_sum_aggregation_of_precipitation_flux_is_rejected(self):
        time = np.arange(
            np.datetime64("2026-09-01T00:30"),
            np.datetime64("2026-09-02T00:30"),
            np.timedelta64(1, "h"),
        )
        bounds = np.stack(
            [
                time - np.timedelta64(30, "m"),
                time + np.timedelta64(30, "m"),
            ],
            axis=1,
        )
        ds = xr.Dataset(
            {
                "pr": (
                    ("time", "lat", "lon"),
                    np.full((len(time), 1, 1), 1 / 3600),
                ),
                "time_bnds": (("time", "bnds"), bounds),
            },
            coords={
                "time": time,
                "lat": ("lat", [50.0], {"units": "degrees_north"}),
                "lon": ("lon", [10.0], {"units": "degrees_east"}),
            },
        )
        ds["time"].attrs["bounds"] = "time_bnds"
        ds["pr"].attrs = {
            "cell_methods": "time: mean",
            "standard_name": "precipitation_flux",
            "units": "kg m-2 s-1",
        }

        summed = timekit.resample_datetimes(ds, how="sum", frequency="1D")

        self.assertAlmostEqual(summed["pr"].item(), 24.0)

        with self.assertRaisesRegex(
            ValueError,
            "expected CMOR units 'kg m-2 s-1'",
        ):
            drs._validate_cmor_units(summed)

    def test_sum_at_existing_cadence_normalizes_equivalent_units(self):
        time = np.array(
            [
                "2026-09-01T00:30",
                "2026-09-01T01:30",
                "2026-09-01T02:30",
            ],
            dtype="datetime64[ns]",
        )
        ds = xr.Dataset(
            {"tas": ("time", [280.0, 281.0, 282.0])},
            coords={"time": time},
        )
        ds["tas"].attrs = {
            "long_name": "Near-Surface Air Temperature",
            "standard_name": "air_temperature",
            "units": "kelvin",
        }

        resampled = timekit.resample_datetimes(ds, how="sum", frequency="1h")

        np.testing.assert_array_equal(
            resampled["tas"].values, [280.0, 281.0, 282.0]
        )
        drs._validate_cmor_units(resampled)

        self.assertEqual(resampled["tas"].attrs["units"], "K")
        np.testing.assert_array_equal(
            resampled["tas"].values, [280.0, 281.0, 282.0]
        )

    def test_convertible_but_non_equivalent_units_are_rejected(self):
        ds = xr.Dataset({"tas": ("time", [7.0])})
        ds["tas"].attrs = {
            "long_name": "Near-Surface Air Temperature",
            "standard_name": "air_temperature",
            "units": "degC",
        }

        with self.assertRaisesRegex(
            ValueError,
            "tas has units 'degC'; expected CMOR units 'K'",
        ):
            drs._validate_cmor_units(ds)

        self.assertEqual(ds["tas"].attrs["units"], "degC")


if __name__ == "__main__":
    unittest.main()
