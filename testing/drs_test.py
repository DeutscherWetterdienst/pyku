import unittest
from unittest.mock import patch, MagicMock


class TestDrsMethods(unittest.TestCase):

    import pyku.drs as drs
    import pyku
    import os
    import glob

    hostrada = pyku.resources.get_test_data('hostrada')
    cordex = pyku.resources.get_test_data('model_data')
    hyras = pyku.resources.get_test_data('hyras')
    cmip6 = pyku.resources.get_test_data('fake_cmip6_data')

    def test_drs_filename(self):

        self.assertEqual(
            self.drs.drs_filename(self.hostrada, standard='obs4mips'),
            'obs4MIPs/DWD/HOSTRADA-v1-0/1hr/tas/gn/v20231215/'
            'tas_1hr_HOSTRADA-v1-0_BE_gn_1995010100-1995013123.nc'
        )

        self.assertEqual(
            self.drs.drs_filename(self.cordex, standard='cordex'),
            'output/EUR-11/SMHI/MPI-M-MPI-ESM-LR/historical/r1i1p1/SMHI-RCA4/'
            'v1a/mon/tas/tas_EUR-11_MPI-M-MPI-ESM-LR_historical_r1i1p1_'
            'SMHI-RCA4_v1a_mon_197001-200512.nc'
        )

        ds = (
            self.cmip6.copy()
            .pyku.resample_datetimes(frequency='1D', how='mean')
        )

        self.assertEqual(
            ds,
            'CMIP6/CMIP/IPSL/IPSL-CM6A-LR-INCA/historical/r1i1p1f1/Amon/zg/'
            'gr/zg_Amon_IPSL-CM6A-LR-INCA_historical_r1i1p1f1_gr_'
            '202301-202312.nc'
        )

    def test_drs_parent(self):

        self.assertEqual(
            self.drs.drs_parent(self.hostrada, standard='obs4mips'),
            'obs4MIPs/DWD/HOSTRADA-v1-0/1hr/tas/gn/v20231215'
        )

        self.assertEqual(
            self.drs.drs_parent(self.cordex, standard='cordex'),
            'output/EUR-11/SMHI/MPI-M-MPI-ESM-LR/historical/r1i1p1/'
            'SMHI-RCA4/v1a/mon/tas'
        )

    def test_drs_stem(self):

        self.assertEqual(
            self.drs.drs_stem(self.hostrada, standard='obs4mips'),
            'tas_1hr_HOSTRADA-v1-0_BE_gn_1995010100-1995013123.nc'
        )

        self.assertEqual(
            self.drs.drs_stem(self.cordex, standard='cordex'),
            'tas_EUR-11_MPI-M-MPI-ESM-LR_historical_r1i1p1_SMHI-RCA4_'
            'v1a_mon_197001-200512.nc'
        )

        # to_cmor_units
        # -------------

        self.assertEqual(
            self.hyras.pyku.to_cmor_units().tas.units,
            'K'
        )

    def test_resolve_template(self):
        from pyku.drs import _resolve_template
        with self.subTest('Testing _resolve_template with all placeholders provided'):
            filename_pattern = '{variable}_{frequency}_{model}_{experiment}_' \
                            '{member}_{grid}_{start_time}-{end_time}'
            namespace = {
                'variable': 'tas',
                'frequency': '1hr',
                'model': 'HOSTRADA-v1-0',
                'experiment': 'historical',
                'member': 'BE',
                'grid': 'gn',
                'start_time': '1995010100',
                'end_time': '1995013123',
                'time_range': 'not_used_in_pattern'
            }
            expected_filename = 'tas_1hr_HOSTRADA-v1-0_historical_BE_gn_1995010100-1995013123'
            filename = _resolve_template(filename_pattern, namespace)
            self.assertEqual(filename, expected_filename)

        with self.subTest('Testing _resolve_template with missing placeholders'):
            filename_pattern = '{variable}_{frequency}_{model}_{experiment}'
            namespace = {
                'variable': 'tas',
                'frequency': '1hr',
                'model': 'HOSTRADA-v1-0',
            }
            expected_filename = 'tas_1hr_HOSTRADA-v1-0_historical'
            with self.assertRaises(KeyError):
                filename = _resolve_template(filename_pattern, namespace)
    
    @patch('pyku.meta.get_frequency')
    def test_to_cmor_attrs_frequency(self, mock_get_frequency):
        from pyku.drs import _to_cmor_attrs_frequency
        mappings = {'1h': '1hr',
                    '3h': '3hr',
                    '6h': '6hr',
                    '12h': '12hr',
                    '1D': 'day',
                    '1MS': 'mon',
                    '1YS': 'year',
                    'QS-DEC': 'sem'}
        data = MagicMock()
        data.attrs = {'frequency': 'one-hourly'}
        mock_get_frequency.return_value = '1h'
        new_data = _to_cmor_attrs_frequency(data)
        self.assertEqual(
            new_data.attrs['frequency'],
            '1hr'
        )
        self.assertIsInstance(new_data, type(data))

        for freq, cmor_freq in mappings.items():
            with self.subTest(f'Testing frequency {freq} to CMOR frequency {cmor_freq} mapping'):
                data.attrs = {'frequency': cmor_freq}
                mock_get_frequency.return_value = freq
                new_data = _to_cmor_attrs_frequency(data)
                self.assertEqual(
                    new_data.attrs['frequency'],
                    cmor_freq
                )
        with self.subTest('Testing unknown frequency mapping'):
            # This test checks that if the frequency is unknown, it defaults
            # to pandas offset alias and does not raise an error.
            data.attrs = {'frequency': 'unknown_freq'}
            mock_get_frequency.return_value = '1SMS'
            new_data = _to_cmor_attrs_frequency(data)
            self.assertEqual(
                new_data.attrs['frequency'],
                'SMS-15'
            )
        with self.subTest('Invalid frequency'):
            # This test checks that if the frequency is invalid (not a
            # pandas offset alias), it raises a ValueError.
            data.attrs = {'frequency': 'invalid_freq'}
            mock_get_frequency.return_value = 'invalid_freq'
            with self.assertRaises(ValueError):
                _to_cmor_attrs_frequency(data)


if __name__ == '__main__':
    unittest.main()
