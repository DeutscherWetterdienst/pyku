import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

from pyku.loess import loess, Loess, calc_loess
from pyku.resources import generate_fake_cmip6_data

DELTA = 0.01


class TestComputeLoess(unittest.TestCase):
    def setUp(self):
        self.time = np.linspace(0, 300, 301)
        np.random.seed(20200101)
        # Create dummy data
        self.dummy_data = np.random.randn(len(self.time))

    def test_loess_filter_empty(self):
        # Empty input to _loess should give a ValueError due to span limitation
        with self.assertRaises(ValueError):
            loess([], [])

    def test_loess_filter_zeros(self):
        # Inserting list of zeros should also result in zero line
        result = loess(list(self.time), [0]*len(self.time))
        self.assertIsInstance(result, Loess)
        self.assertEqual(np.mean(result.values), 0)
        self.assertEqual(np.mean(result.lower), 0)
        self.assertEqual(np.mean(result.upper), 0)

    def test_loess_filter_nan(self):
        result = loess(self.time, [np.nan]*len(self.time))
        self.assertTrue(all(np.isnan(result.values)))
        self.assertTrue(all(np.isnan(result.lower)))
        self.assertTrue(all(np.isnan(result.upper)))

    def test_loess_filter_short_time(self):
        with self.assertRaises(ValueError):
            _ = loess(self.time[:-2], [0]*len(self.time))

    def test_loess_filter_short_data(self):
        with self.assertRaises(ValueError):
            _ = loess(self.time, [0]*(len(self.time)-2))

    @patch('pyku.loess.skloess')
    def test_loess_filter_kw_handling(self, mock_loess):
        # this test mimics the function call and only
        # ensures that the DWD standard settings are correctly
        # passed to the skmisc.loess.loess function
        _ = loess(self.time, self.dummy_data)
        _, kwargs = mock_loess.call_args
        self.assertEqual(kwargs['surface'], 'direct')
        self.assertEqual(kwargs['span'], 42.0/len(self.time))
        self.assertEqual(kwargs['family'], 'gaussian')
        self.assertEqual(kwargs['degree'], 1)
        self.assertEqual(kwargs['statistics'], 'exact')


class TestCalibrateAgainstR(unittest.TestCase):
    """ Test loess implementation against R ku21 results

    This test has been calibrated against known output from R implementation of
    loess That means, the numbers used here have been taken from R output and
    should match closely.
    """
    def setUp(self):
        import datetime
        self.x = np.linspace(1881, 2024, 144, dtype=int)
        np.random.seed(20200101)

        self.y = np.random.randn(len(self.x)).cumsum()
        self.time = [datetime.date(x, 1, 1) for x in self.x]
        self.data = pd.DataFrame({
            'YEAR': self.time,
            'VALUE': self.y
        })

    def test_calibration_against_R(self):
        """ Test loess implementation against R ku21 results """
        import datetime
        from pyku.loess import loess

        result = loess(self.x, self.y, conf='wald')
        result.time = self.time
        with self.subTest('Test Loess Line'):
            self.assertAlmostEqual(
                np.mean(result.values), -1.586599691, places=8
            )
            self.assertAlmostEqual(
                np.std(result.values), 2.432827951102725, places=8
            )
            self.assertAlmostEqual(
                np.mean(result.lower), -1.9981594629905162, places=8
            )
            self.assertAlmostEqual(
                np.mean(result.upper), -1.1750399201422932, places=8
            )

        with self.subTest('Test Loess Trend'):
            trend = result.trend(143, (0, 30), index=True)
            self.assertEqual(trend[0], self.time[143])
            self.assertAlmostEqual(trend[1], -9.240042047019365, delta=1e-8)

            trend = result.trend(
                datetime.date(2024, 1, 1),
                (datetime.date(1881, 1, 1), datetime.date(1910, 1, 1)),
                index=False
            )
            self.assertEqual(trend[0], self.time[143])
            self.assertAlmostEqual(trend[1], -9.240042047019365, delta=1e-8)


class TestLoessStandalone(unittest.TestCase):
    def test_loess(self):
        x = pd.date_range(start='1920-06-01', periods=101, freq='YS')
        y = np.arange(101)
        result = loess(x, y)
        self.assertEqual(len(result.values), len(x))
        self.assertEqual(len(result.lower), len(x))
        self.assertEqual(len(result.upper), len(x))
        self.assertTrue(np.all(result.upper >= result.lower))
        self.assertTrue(np.all(np.abs(result.values - y) <= DELTA))

    def test_loess_trend(self):
        x = pd.date_range(start='1920-06-01', periods=101, freq='YS')
        y = np.arange(101)
        result = loess(x, y)

        with self.subTest('Trend index based'):
            target_idx = 100
            ref_idx = (0, 21)
            trend_idx = result.trend(target_idx, ref_idx, index=True)
            self.assertAlmostEqual(trend_idx[1], 90.0, delta=DELTA)
        # Calculate trend for time-based target and ref periods
        with self.subTest('Trend time-based'):
            target_time = x[100]
            ref_time = (x[0], x[20])
            trend_time = result.trend(target_time, ref_time, index=False)
            self.assertAlmostEqual(trend_time[1], 90.0, delta=DELTA)

    def test_loess_trend_inclusion(self):
        x = pd.date_range(start='1920-06-01', periods=101, freq='YS')
        y = np.arange(101)
        result = loess(x, y)

        _ = result.trend(100, (0, 21), index=True)
        self.assertEqual(len(list(result.time[slice(0, 21)])), 21)

        _ = result.trend(x[100], (x[0], x[20]), index=False)
        self.assertEqual(len(list(result.time[slice(0, 21)])), 21)


class TestLoessDataset(unittest.TestCase):
    def setUp(self):
        self.ds = generate_fake_cmip6_data()

    def test_loss_filter_too_short(self):
        """ Test that applying loess filter to dataset with too few time
            points raises ValueError.
        """
        with self.assertRaises(ValueError):
            calc_loess(self.ds)

    def test_loess_filter_spatial_mean(self):
        self.ds = generate_fake_cmip6_data(
            ntime=101, freq='YS', nlat=18, nlon=36
        )
        filtered_ds = calc_loess(self.ds, var='tas', spatial_reduce=True)

        with self.subTest('Check lengths and values'):
            self.assertEqual(
                len(filtered_ds['tas_loess'].values), len(self.ds['time'])
            )
            self.assertEqual(
                len(filtered_ds['tas_loess_lower']), len(self.ds['time'])
            )
            self.assertEqual(
                len(filtered_ds['tas_loess_upper']), len(self.ds['time'])
            )
            self.assertIn('tas_loess', filtered_ds.variables)
            self.assertIn('tas_loess_lower', filtered_ds.variables)
            self.assertIn('tas_loess_upper', filtered_ds.variables)
        self.assertTrue(
            np.all(
                filtered_ds['tas_loess_upper'] > filtered_ds['tas_loess_lower']
            )
        )

    def test_loess_filter_gridwise(self):
        self.ds = generate_fake_cmip6_data(
            ntime=101, freq='YS', nlat=18, nlon=36
        )

        filtered_ds = calc_loess(self.ds, var='tas', spatial_reduce=None)

        with self.subTest('Check shapes and values'):
            self.assertEqual(
                filtered_ds['tas_loess'].shape,
                (18, 36, len(self.ds['time']))
            )
            self.assertEqual(
                filtered_ds['tas_loess_lower'].shape,
                (18, 36, len(self.ds['time']))
            )
            self.assertEqual(
                filtered_ds['tas_loess_upper'].shape,
                (18, 36, len(self.ds['time']))
            )
            self.assertIn('tas_loess', filtered_ds.variables)
            self.assertIn('tas_loess_lower', filtered_ds.variables)
            self.assertIn('tas_loess_upper', filtered_ds.variables)
        self.assertTrue(np.all(
            filtered_ds['tas_loess_upper'] > filtered_ds['tas_loess_lower']
        ))
