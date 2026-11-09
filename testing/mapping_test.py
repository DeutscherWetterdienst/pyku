import unittest

import xarray as xr

from pyku import PYKU_RESOURCES, drs


class TestVariableMappings(unittest.TestCase):

    def test_every_mapping_entry_has_a_comment_field(self):
        mapping_names = [
            name for name in PYKU_RESOURCES.list_resources()
            if name.startswith('mapping_')
        ]

        for mapping_name in mapping_names:
            mapping = PYKU_RESOURCES.load_resource(mapping_name)
            with self.subTest(mapping=mapping_name):
                for variable, definition in mapping.items():
                    with self.subTest(variable=variable):
                        self.assertIn('comment', definition)

    def test_tot_prec_maps_to_pr_for_icon_and_cosmo(self):
        for mapping_name in ['mapping_icon', 'mapping_cosmo_clm']:
            mapping = PYKU_RESOURCES.load_resource(mapping_name)
            with self.subTest(mapping=mapping_name):
                self.assertEqual(mapping['pr']['name'], 'TOT_PREC')
                self.assertTrue(mapping['pr']['comment'])

        icon_mapping = PYKU_RESOURCES.load_resource('mapping_icon')
        self.assertNotIn('prhmax', icon_mapping)
        self.assertIn('TOT_PREC', drs.get_cmor_varname_aliases('pr'))
        self.assertNotIn('TOT_PREC', drs.get_cmor_varname_aliases('prhmax'))

    def test_tot_prec_is_inferred_as_pr(self):
        data = xr.DataArray(
            [1.0],
            name='TOT_PREC',
            attrs={
                'standard_name': 'precipitation_amount',
                'long_name': 'total precipitation amount',
                'units': 'kg m-2',
            },
        )

        self.assertEqual(drs.get_cmor_varname(data), 'pr')

    def test_cosmo_clm_maps_to_standard_variable_names(self):
        mapping = PYKU_RESOURCES.load_resource('mapping_cosmo_clm')
        expected_aliases = {
            'clt': 'CLCT',
            'tdps': 'TD_2M',
            'rlns': 'ATHB_S',
        }

        for cmor_name, source_name in expected_aliases.items():
            with self.subTest(cmor_name=cmor_name):
                self.assertEqual(mapping[cmor_name]['name'], source_name)
                source = xr.DataArray([1.0], name=source_name)
                self.assertEqual(drs.get_cmor_varname(source), cmor_name)

        for old_name in ('cclm-clct', 'cclm-td-2m', 'cclm-athb-s'):
            with self.subTest(old_name=old_name):
                self.assertNotIn(old_name, mapping)
                self.assertNotIn(
                    old_name,
                    PYKU_RESOURCES.load_resource('cmor-like'),
                )

        cmor_like = PYKU_RESOURCES.load_resource('cmor-like')
        self.assertEqual(cmor_like['tdps']['valid_bounds'], [150, 400])
        self.assertEqual(cmor_like['rlns']['valid_bounds'], [-3000, 3000])


if __name__ == '__main__':
    unittest.main()
