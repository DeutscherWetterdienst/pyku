import importlib.util
import warnings
from pathlib import Path
import unittest

import matplotlib
import numpy as np
import pandas as pd
import xarray as xr

matplotlib.use("Agg")


def _load_analyse():
    path = Path(__file__).parents[1] / "pyku" / "analyse.py"
    spec = importlib.util.spec_from_file_location("legacy_analyse", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None, "loader must be present"
    spec.loader.exec_module(module)
    return module


def _data_array():
    values = np.arange(48, dtype=float).reshape(12, 2, 2)
    return xr.DataArray(
        values,
        dims=("time", "y", "x"),
        coords={"time": pd.date_range("2000-01-01", periods=12, freq="MS")},
        name="tas",
        attrs={"long_name": "Temperature", "units": "K"},
    )


class TestAnalyseDeprecation(unittest.TestCase):
    def test_all_documented_public_functions_warn(self):
        analyse = _load_analyse()

        expected_deprecated = [
            "pdf",
            "monthly_pdf",
            "seasonal_pdf",
            "monthly_bias",
            "daily_mean",
            "monthly_mean",
            "diurnal_cycle",
            "monthly_diurnal_cycle",
            "seasonal_diurnal_cycle",
            "monthly_variability",
            "diurnal_cycle_variability",
            "regional_monthly_variability",
            "regional_monthly_bias",
            "regional_mean_vs_time",
            "time_serie",
            "mean_vs_time",
            "percentile_map",
            "p98_map",
            "mse_map",
            "rmse_map",
            "pcc_map",
            "pdf2D",
        ]

        for function_name in expected_deprecated:
            with self.subTest(function_name=function_name):
                function = getattr(analyse, function_name, None)
                if function is None or not callable(function):
                    self.fail(f"{function_name} not found or not callable")
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always", DeprecationWarning)
                    try:
                        function()
                    except Exception:
                        pass
                self.assertTrue(
                    any(item.category is DeprecationWarning for item in caught),
                    function_name,
                )

    def test_pdf_docstring_paths_run(self):
        analyse = _load_analyse()
        data = _data_array()

        for function_name in ["pdf", "monthly_pdf", "seasonal_pdf"]:
            with self.subTest(function_name=function_name):
                with warnings.catch_warnings(record=True) as caught:
                    warnings.simplefilter("always", DeprecationWarning)
                    getattr(analyse, function_name)(data, var="tas")

                self.assertTrue(
                    any(item.category is DeprecationWarning for item in caught),
                    function_name,
                )
