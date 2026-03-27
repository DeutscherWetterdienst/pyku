import unittest


class TestMetaMethods(unittest.TestCase):

    import glob
    import os

    import pyku
    from pyku import meta

    hyras_tas = pyku.resources.get_test_data('hyras')
    GCM_CanESM5 = pyku.resources.get_test_data('GCM_CanESM5')
    fake_cmip6 = pyku.resources.get_test_data('fake_cmip6_data')

    def test_meta_get_unidentified_varnames(self):

        import xarray as xr

        ds = self.fake_cmip6.copy()
        ds['number_of_stations'] = xr.DataArray(data=12)

        self.assertEqual(
            self.meta.get_unidentified_varnames(ds),
            ['number_of_stations']
        )

        self.assertEqual(
            ds.pyku.get_unidentified_varnames(),
            ['number_of_stations']
        )

    def test_meta_get_frequency(self):

        import pandas

        self.assertIsInstance(
            self.meta.get_frequency(self.hyras_tas, dtype='Timedelta'),
            pandas._libs.tslibs.timedeltas.Timedelta
        )

        self.assertEqual(
            self.meta.get_frequency(self.GCM_CanESM5, dtype='freqstr'),
            'MS'
        )

        self.assertEqual(
            self.meta.get_frequency(self.hyras_tas, dtype='freqstr'),
            'D'
        )

    def test_meta_is_georeferenced(self):
        self.assertTrue(self.meta.is_georeferenced(self.hyras_tas))

    def test_meta_get_time_intervals(self):

        import numpy as np

        calculated_intervals = self.meta.get_time_intervals(
            self.GCM_CanESM5.isel(time=[0, 1, 2, 3])).interval.values
        expected_intervals = np.array([2678400., 2419200., 2678400., 2592000.])

        self.assertEqual(
            np.array_equal(calculated_intervals, expected_intervals),
            True
        )

    def test_meta_get_geographic_latlon_varnames(self):

        self.assertEqual(
            self.meta.get_projection_yx_varnames(
                self.fake_cmip6.rename({'lat': 'lat_1'})
            ),
            ('lat_1', 'lon')
        )


if __name__ == '__main__':
    unittest.main()
