import unittest

import pyku
import xarray as xr
from pyku import geo


class TestGeoMethods(unittest.TestCase):

    ds = (
        pyku.resources.get_test_data('global_data')
        .pyku.wrap_longitudes()
        .pyku.sort_georeferencing()
        .compute()
    )

    def test_project_eur_11_rotated_pole(self):
        """Test projection to EUR-11 grid.

        Verifies that rotated_pole variable and rlat coordinate are generated
        correctly and that rlat contains degree units.
        """
        ds_proj = self.ds.pyku.project("EUR-11")

        self.assertIn("rotated_pole", ds_proj)
        self.assertIn("rlat", ds_proj.coords)
        self.assertEqual(ds_proj["rlat"].dims, ("rlat",))
        self.assertEqual(ds_proj["rlon"].dims, ("rlon",))
        self.assertEqual(ds_proj["lat"].dims, ("rlat", "rlon"))
        self.assertEqual(ds_proj["lon"].dims, ("rlat", "rlon"))

        rlat_units = str(ds_proj["rlat"].attrs.get("units", "")).lower()
        self.assertIn("degree", rlat_units)

    def test_project_updates_cordex_domain(self):
        """The CORDEX domain describes the target projection."""

        source = self.ds.assign_attrs(CORDEX_domain='source-domain')
        projected = source.pyku.project('EUR-11')

        self.assertEqual(projected.attrs['CORDEX_domain'], 'EUR-11')

    def test_round_spatial_coordinates(self):
        """Test round_spatial_coordinates on projected dataset coordinates.

        Verifies that floating-point coordinate precision drift is cleaned
        across both 1D/2D geographic and projected coordinates.
        """

        projected = self.ds.pyku.project("HYR-LAEA-5")

        rounded = projected.pyku.round_spatial_coordinates()

        self.assertEqual(projected.dims, rounded.dims)
        self.assertEqual(projected.coords.keys(), rounded.coords.keys())

        orig_val = float(projected["lon"].values[0, 0])
        round_val = float(rounded["lon"].values[0, 0])

        self.assertNotEqual(orig_val, round_val)
        self.assertAlmostEqual(orig_val, round_val, places=5)
        self.assertEqual(round_val, round(orig_val, 6))

    def test_apply_georeferencing_regular_grid(self):
        """
        Test apply_georeferencing on valid, unbroken regular grid data.

        Verifies compatibility with 1D geographic (lat/lon) grids,
        where projection dimensions (y/x) align directly with lat/lon.
        """

        regular = pyku.resources.get_test_data('air_temperature')
        regular_grid = (
            regular.pyku.sort_georeferencing()
            .pyku.wrap_longitudes()
            .pyku.get_area_def()
        )

        repaired = regular.pyku.apply_georeferencing(regular_grid)

        self.assertIn('lat', repaired.coords)
        self.assertIn('lon', repaired.coords)
        self.assertEqual(repaired['lat'].dims, ('lat',))
        self.assertEqual(repaired['lon'].dims, ('lon',))

    def test_apply_georeferencing_projected_broken(self):
        """
        Test apply_georeferencing on a dataset with missing spatial metadata.

        Intentionally breaks the projection and spatial coordinates of a
        dataset to verify that correct georeferencing is successfully restored.
        """

        target_area = 'HYR-LAEA-5'
        projected = self.ds.pyku.project(target_area)

        # Break georeferencing by removing spatial/CRS variables
        broken = projected.drop_vars(['crs', 'y', 'x'], errors='ignore')

        repaired = geo.apply_georeferencing(broken, target_area)

        self.assertIn('y', repaired.coords)
        self.assertIn('x', repaired.coords)
        self.assertIn('lat', repaired.coords)
        self.assertIn('lon', repaired.coords)
        self.assertEqual(repaired['lat'].ndim, 2)
        self.assertEqual(repaired['lon'].ndim, 2)

    def test_apply_georeferencing_missing_and_partial_coordinates(
        self,
    ) -> None:
        """Rebuild all spatial coordinates when some are missing."""

        target_area = 'HYR-LAEA-5'
        projected = self.ds.pyku.project(target_area)

        for missing_coords in (
            ['crs', 'y', 'x', 'lat', 'lon'],
            ['lat'],
            ['lon'],
            ['lat', 'lon'],
            ['x', 'lon'],
        ):
            with self.subTest(missing_coords=missing_coords):
                broken = projected.drop_vars(
                    missing_coords,
                    errors='ignore',
                )
                repaired = geo.apply_georeferencing(broken, target_area)

                for coord_name in ('y', 'x', 'lat', 'lon'):
                    xr.testing.assert_allclose(
                        repaired[coord_name],
                        projected[coord_name],
                    )

    def test_default_methods(self):
        """
        Test default projection methods.
        """

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
        """
        Test pyresample projection methods.
        """

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
