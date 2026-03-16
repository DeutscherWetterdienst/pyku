import unittest


class TestGeoMethods(unittest.TestCase):

    import pyku.geo as geo
    import pyku
    import os
    import glob

    ds = (
        pyku.resources.get_test_data('global_data')
        .pyku.wrap_longitudes()
        .pyku.sort_georeferencing()
        .compute()
    )

    def test_default_methods(self):

        _ = self.ds.pyku.project(
            area_def='HYR-LAEA-5'
        )
        _ = self.ds.pyku.project(
            area_def='HYR-LAEA-5',
            method='nearest_neighbor'
        )
        _ = self.ds.pyku.project(
            area_def='HYR-LAEA-5',
            method='bilinear'
        )
        # _ = self.ds.pyku.project(
        #     area_def='HYR-LAEA-5',
        #     method='conservative'
        # )
        _ = self.ds.pyku.project(
            area_def='HYR-LAEA-5',
            method='idw',
            power_parameter=2
        )

    def test_pyresample_methods(self):
        _ = self.ds.pyku.project(
            area_def='HYR-LAEA-5',
            method='pyresample_nearest_neighbor'
        )
        _ = self.ds.pyku.project(
            area_def='HYR-LAEA-5',
            method='pyresample_bilinear'
        )
        _ = self.ds.pyku.project(
            area_def='HYR-LAEA-5',
            method='pyresample_idw',
            power_parameter=2
        )
        _ = self.ds.pyku.project(
            area_def='HYR-LAEA-5',
            method='pyresample_bilinear_swath_to_grid'
        )

    # def test_pyresample_legacy_methods(self):
    #     _ = self.ds.pyku.project(
    #         area_def='HYR-LAEA-5',
    #         method='pyresample_bilinear_swath_to_grid_legacy'
    #     )
    #     _ = self.ds.pyku.project(
    #         area_def='HYR-LAEA-5',
    #         method='pyresample_bilinear_swath_to_swath_legacy'
    #     )
    #     _ = self.ds.pyku.project(
    #         area_def='HYR-LAEA-5',
    #         method='pyresample_nearest_neighbor_legacy'
    #     )

    # def test_esmf_methods(self):
    #     _ = self.ds.pyku.project(
    #         area_def='HYR-LAEA-5',
    #         method='esmf_conservative'
    #     )
    #     _ = self.ds.pyku.project(
    #         area_def='HYR-LAEA-5',
    #         method='esmf_conservative_normed'
    #     )
    #     _ = self.ds.pyku.project(
    #         area_def='HYR-LAEA-5',
    #         method='esmf_patch'
    #     )
    #     _ = self.ds.pyku.project(
    #         area_def='HYR-LAEA-5',
    #         method='esmf_nearest_s2d'
    #     )
    #     _ = self.ds.pyku.project(
    #         area_def='HYR-LAEA-5',
    #         method='esmf_nearest_d2s'
    #     )


if __name__ == '__main__':
    unittest.main()
