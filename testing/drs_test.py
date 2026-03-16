import unittest


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
            'SMHI-RCA4_v1a_mon_19700116-20051216.nc'
        )

        ds = (
            self.cmip6.copy()
            .pyku.resample_datetimes(frequency='1D', how='mean')
        )

        self.assertEqual(
            ds,
            'CMIP6/CMIP/IPSL/IPSL-CM6A-LR-INCA/historical/r1i1p1f1/Amon/zg/'
            'gr/zg_Amon_IPSL-CM6A-LR-INCA_historical_r1i1p1f1_gr_'
            '20230101-20231231.nc'
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
            'v1a_mon_19700116-20051216.nc'
        )

        # to_cmor_units
        # -------------

        self.assertEqual(
            self.hyras.pyku.to_cmor_units().tas.units,
            'K'
        )


if __name__ == '__main__':
    unittest.main()
