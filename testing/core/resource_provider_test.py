#!/usr/bin/env python3
"""
unittests for resource manager module
"""
import unittest
from unittest.mock import patch, mock_open
import importlib.resources

import yaml

# Add the src directory to the Python path
from pyku.core.resource_provider import PykuResourceProvider


class TestImportlibResource(unittest.TestCase):
    def test_get_resource_link(self):
        # This is a simple test to check if importlib.resource does what it
        # is supposed to do
        area_file = importlib.resources.files('pyku.etc') / 'areas.yaml'
        self.assertTrue(area_file.parts[-1].endswith('areas.yaml'))

    def test_load_area_file(self):
        #
        from pyresample.area_config import load_area
        from pyresample.geometry import AreaDefinition

        area_file = importlib.resources.files('pyku.etc') / 'areas.yaml'
        area_def = load_area(area_file, 'HYR-LAEA-5')
        self.assertIsInstance(area_def, AreaDefinition)


class TestPykuResourceProvider(unittest.TestCase):
    def setUp(self):
        self.pseudo_file = """Test1:
    test2:
        key : value
"""
        self.pseudo_dict = yaml.safe_load(self.pseudo_file)

    @patch('builtins.open')
    @patch('pathlib.Path.exists')
    def test_load_resource_success(self, mock_exists, mock_open_file):
        """Test successful YAML resource loading."""
        # Setup mocks
        mock_exists.return_value = True
        mock_file = mock_open(read_data=self.pseudo_file)
        mock_open_file.return_value = mock_file.return_value

        # Create ResourceManager and load resource
        resource_provider = PykuResourceProvider()
        result = resource_provider.load_resource("test_file")

        # Assertions - compare with expected parsed result
        self.assertEqual(result, self.pseudo_dict)
        mock_exists.assert_called_once_with()
        mock_open_file.assert_called_once()

        # check caching... a second call should not open the file again
        result_cache = resource_provider.load_resource("test_file")
        self.assertEqual(result, result_cache)
        mock_open_file.assert_called_once()
        self.assertEqual(mock_open_file.call_count, 1)

        # but if cache got cleared it should get called a second time!
        resource_provider.clear_cache()
        result = resource_provider.load_resource("test_file")
        self.assertEqual(mock_open_file.call_count, 2)

    @patch('builtins.open')
    @patch('pathlib.Path.exists')
    def test_get_keys(self, mock_exists, mock_open_file):
        mock_exists.return_value = True
        mock_file = mock_open(read_data=self.pseudo_file)
        mock_open_file.return_value = mock_file.return_value

        # Create ResourceManager and load resource
        resource_provider = PykuResourceProvider()
        _ = resource_provider.load_resource("test_file")

        keys = resource_provider.get_keys('test_file')
        self.assertEqual(list(keys), ['Test1'])

        keys = resource_provider.get_keys('test_file', 'Test1')
        self.assertEqual(list(keys), ['test2'])

    @patch('builtins.open')
    @patch('pathlib.Path.exists')
    def test_get_value(self, mock_exists, mock_open_file):
        mock_exists.return_value = True
        mock_file = mock_open(read_data=self.pseudo_file)
        mock_open_file.return_value = mock_file.return_value

        # Create ResourceManager and load resource
        resource_provider = PykuResourceProvider()
        _ = resource_provider.load_resource("test_file")

        res = resource_provider.get_value('test_file', 'Test1')
        self.assertEqual(res, self.pseudo_dict['Test1'])
        res = resource_provider.get_value(
                    'test_file', 'Test1', 'test2')
        self.assertEqual(res, self.pseudo_dict['Test1']['test2'])

        res = resource_provider.get_value(
                    'test_file', 'Test1', 'test2', 'key')
        self.assertEqual(res, 'value')

    @patch('builtins.open')
    @patch('pathlib.Path.exists')
    def test_get_value_default_kw(self, mock_exists, mock_open_file):
        mock_exists.return_value = True
        mock_file = mock_open(read_data=self.pseudo_file)
        mock_open_file.return_value = mock_file.return_value

        # Create ResourceManager and load resource
        resource_provider = PykuResourceProvider()
        _ = resource_provider.load_resource("test_file")
        # Calling a non-existent key should raise an error!
        with self.assertRaises(KeyError):
            resource_provider.get_value('test_file', 'Test3')

        # Return default value when given as kw
        default = resource_provider.get_value('test_file',
                                              'Test3',
                                              default='default')
        self.assertEqual(default, 'default')

        # Ensure that default None is possible and returns right type
        default = resource_provider.get_value('test_file',
                                              'Test3',
                                              default=None)
        self.assertIsNone(default)

    def test_real_resources(self):
        resource_provider = PykuResourceProvider()
        base_colours = resource_provider.load_resource("base_colours")

        keys = resource_provider.get_keys('base_colours')
        self.assertEqual(base_colours.keys(), keys)


if __name__ == "__main__":
    unittest.main()
