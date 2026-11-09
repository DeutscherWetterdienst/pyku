import unittest
from unittest.mock import patch

import pandas as pd
import xarray as xr

from pyku import drs


class TestPrecipitationCmorUnits(unittest.TestCase):
    @patch("pyku.meta.get_frequency")
    def test_amount_conversion_sets_mean_cell_method(self, mock_get_frequency):
        mock_get_frequency.return_value = pd.Timedelta(hours=1)
        ds = xr.Dataset(
            {"TOT_PREC": ("time", [1.0, 2.0])},
            coords={"time": pd.date_range("2026-09-01", periods=2, freq="h")},
        )
        ds.TOT_PREC.attrs = {
            "standard_name": "precipitation_amount",
            "long_name": "total precipitation amount",
            "units": "kg m-2",
            "cell_methods": "time: sum",
        }

        converted = drs.to_cmor_units(ds)

        self.assertEqual(converted.TOT_PREC.attrs["units"], "kg m-2 s-1")
        self.assertEqual(converted.TOT_PREC.attrs["cell_methods"], "time: mean")
        self.assertAlmostEqual(converted.TOT_PREC.values[0], 1.0 / 3600.0)
        self.assertEqual(ds.TOT_PREC.attrs["cell_methods"], "time: sum")


if __name__ == "__main__":
    unittest.main()
