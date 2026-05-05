import unittest


class TestConfigProvider(unittest.TestCase):

    def test_config_initialization(self):
        from pyku.core.config_provider import PykuConfigProviderSingleton

        config_provider = PykuConfigProviderSingleton

        config_attributes = [
            'pre_existing_data_dir',
            'data_dir',
            'cache_dir',
            'repo_data_dir',
            'default_data_dir',
            'downloaders',
        ]
        for attr in config_attributes:
            self.assertIn(attr, config_provider.config)

    def test_get_set_config(self):
        from pyku.core.config_provider import PykuConfigProviderSingleton

        config_provider = PykuConfigProviderSingleton

        # Test setting a config value
        config_provider.set('test_key', 'test_value')
        self.assertEqual(config_provider.get('test_key'), 'test_value')

        # Test getting a non-existing key returns None
        self.assertIsNone(config_provider.get('non_existing_key'))
