"""
Resource Manager
"""

import yaml


class PykuResourceProvider:
    """Following the singleton design pattern, this class is meant
    to provide an global instance of a resource manager. An instance is
    created during initialization of pyku, and provides access to all (yaml)
    files in etc/ on a per-read basis (while enabling caching)"""
    def __init__(self, resource_dir='pyku.etc'):
        """ Initialise a resource manager with a given package internal
        directory/module
        """
        import importlib.resources

        self._resource_dir = importlib.resources.files(resource_dir)
        self.clear_cache()

    def load_resource(self, resource_name: str):
        """ On the fly resource loading and caching """
        if resource_name in self._resource_cache:
            return self._resource_cache[resource_name]

        resource_path = self._resource_dir / (resource_name + '.yaml')

        if not resource_path.exists():
            raise FileNotFoundError(f"Resource file not found: \
                                    {resource_path}")

        resource = _parse_yaml_file(resource_path)

        self._resource_cache[resource_name] = resource

        return resource

    def clear_cache(self):
        self._resource_cache = {}

    def get_value(self, resource_name, *keys, **kwargs):
        """ get a specific key from a resource file giving
        ordered arguments indicating the dictionary chain

        Params:
            resource_name (str) : a file in etc/ given without extension
                                    i.e. 'areas_cf'
            *args (str)         : arbitrary number of ordered strings that
                                    get refere to keys within the opened
                                    resource file.
            **kwargs            : only 'default' as a kwargs gets used. If
                                    given, this value gets returned. Only
                                    works with at least one given *arg

        Returns:
            Union[Dict,int, float, str]

        Example:
            resource_provider = PykuResourceProvider()
            drs_standards = resource_provider.get_keys('drs','standards')
            # returns e.g. {'cmip5':{...},'cmip6':{...},....}
        """
        d = self.load_resource(resource_name)
        return _walk_dictionary(d, *keys, **kwargs)

    def get_keys(self, resource_name, *keys):
        """ get all keys of a resource at the level *keys

        resource_name (str) : a file in etc/ given without extension
                                i.e. 'areas_cf'
        *args (str)         : arbitrary number of ordered strings that
                                referes to key-chains within the opened
                                resource file.

        Returns:
            DictKeys

        Example:
            resource_provider = PykuResourceProvider()
            drs_standards = resource_provider.get_keys('drs','standards')
            # returns e.g. DictKeys['cmip5','cmip6',....]
        """
        return self.get_value(resource_name, *keys).keys()


PykuResourceProviderSingleton = PykuResourceProvider()


# Private Helper Functions
def _parse_yaml_file(resource_path):
    """ Helper function to safe_load a yaml file """
    with open(resource_path, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data


def _walk_dictionary(d, *keys, **kwargs):
    """helper function to walk through a dictionary
    in an ordered way through *keys and returns the
    resulting value

    Params:
        d (dict) : Dictionary to walk through
        *keys (str) : ordered strings of keys
                    inside of d
        **kwargs (str) : only `default` has an effect.
                    if key-chain *keys is not found in
                    d, default gets returned. otherwise
                    a KeyError

    Returns:
        Union[dict, int, float, str]

    Raises:
        KeyError : when *args not in d
    """
    for key in keys:
        if isinstance(d, dict) and key in d:
            d = d[key]
        else:
            if 'default' in kwargs.keys():
                return kwargs.get('default', None)
            raise KeyError(f"Key {key} not found")
    return d
