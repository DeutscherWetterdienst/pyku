"""
Indicator initializer
"""

import importlib.resources
import yaml

# Load indicator yaml data
# ------------------------

indicator_file = importlib.resources.files(
    'pyku.etc') / 'climate_indicators.yaml'

with open(indicator_file) as f:
    grouped_indicator_data = yaml.safe_load(f)

    indicator_data = {}
    for indicator_group, indicator in grouped_indicator_data.items():
        for name, params in indicator.items():
            indicator_data[name] = params
