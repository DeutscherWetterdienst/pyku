import importlib.resources
import yaml

from pyku.resources import generate_fake_cmip6_data

import xarray as xr

from pyku.clix.manager import ClimateIndicator
from pyku.clix.custom_indicators import (
    expand_percentiles_to_daily,
    percentile_grouped
)

from xclim.core.calendar import percentile_doy

def calc_indicator(indicator_name, frequency, data):

    # Define parameters (use an empty dictionary for default indicator setup)
    params = {}   
    clind = ClimateIndicator(indicator_name, frequency)
    
    if clind.is_perc_indicator:
        req_args = data.copy()
        for varname, da in data.items():
            arr_perc = percentile_grouped(
                    da,
                    group_freq=frequency,
                    per=95.,
                    climatology=True
                )
            arr_perc = expand_percentiles_to_daily(da, arr_perc, frequency)
        req_args[f'{varname}_per'] = arr_perc
    else:
        req_args = data

    clind.required_args = req_args
    result = clind()
        
    return result

# Load indicator yaml data
# ------------------------

indicator_file = importlib.resources.files(
    'pyku.etc') / 'climate_indicators.yaml'

with open(indicator_file) as f:
    grouped_indicator_data = yaml.safe_load(f)

# Derive dictionary with variables as keys and list of indicator names
indicator_data = {
    group: list(indicators.keys())
    for group, indicators in grouped_indicator_data.items()
}

for varnames, indicators in indicator_data.items():
    data = {}
    #print(f'Variable(s) to use for caculation: {', '.join(varnames.split('+'))}')
    for varname in varnames.split('+'):
        data[varname] = generate_fake_cmip6_data(
            variable=varname, ntime=2, nlat=1, nlon=1, freq='D')[varname]
    for indicator_name in indicators:
        #print(indicator_name)
        calc_indicator(indicator_name, 'YS', data)
