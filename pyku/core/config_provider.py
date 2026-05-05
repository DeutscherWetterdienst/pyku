import os
import tempfile
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


# for the writable data directory (i.e. the one where new data goes), follow
# the XDG guidelines found at
# https://standards.freedesktop.org/basedir-spec/basedir-spec-latest.html


class PykuConfigProvider:
    """Provides configuration settings for the pyku package."""

    def __init__(self):
        # Set default directories
        _writable_dir = Path.home() / '.local' / 'share'
        _data_dir = Path(os.environ.get("XDG_DATA_HOME", _writable_dir)) / \
            'pyku'
        _cache_dir = Path(tempfile.gettempdir()) / 'pyku_cache_dir'

        # Get PYKU_DATA_DIR if it exist
        pre_existing_data_dir = Path(os.environ.get('PYKU_DATA_DIR', ''))
        data_dir = Path(os.environ.get('PYKU_DATA_DIR', str(_data_dir)))

        # Sanity checks
        if not _check_sanity(data_dir):
            data_dir = _data_dir

        # Set the pyku configuration
        self.config = {
            'pre_existing_data_dir': pre_existing_data_dir,
            'data_dir': data_dir,
            'cache_dir': _cache_dir,
            'repo_data_dir': Path(__file__).parent / 'data',
            'default_data_dir': _data_dir,
            'downloaders': {},
        }
        logger.debug("Using pyku data directory: %s", self.config['data_dir'])

    def get(self, key):
        """Retrieve a configuration value by key."""
        return self.config.get(key)

    def set(self, key, value):
        """Set a configuration value by key."""
        self.config[key] = value

    @property
    def data_dir(self):
        """Get the data directory."""
        return self.get('data_dir')

    @data_dir.setter
    def data_dir(self, path):
        """Set the data directory."""
        self.set('data_dir', Path(path))

    @property
    def cache_dir(self):
        """Get the cache directory."""
        return self.get('cache_dir')

    @cache_dir.setter
    def cache_dir(self, path):
        """Set the cache directory."""
        self.set('cache_dir', Path(path))


def _check_sanity(data_dir: Path) -> bool:
    """Check if the data directory is valid."""
    if not data_dir.exists():
        logger.info("%s does not exist", data_dir)
        return False
    if not data_dir.is_dir():
        logger.info("%s not a directory", data_dir)
        return False
    if not os.access(data_dir, os.W_OK):
        logger.info("%s not writable", data_dir)
        return False
    return True


PykuConfigProviderSingleton = PykuConfigProvider()
