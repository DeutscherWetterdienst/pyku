import unittest


class TestClixMethods(unittest.TestCase):

    import importlib.resources

    from pyku.clix.manager import ClimateIndicator

    def calc_indicator(self, indicator_name, frequency, data):
        from pyku.clix.custom_indicators import (
            expand_percentiles_to_daily,
            percentile_grouped
        )
        # Define parameters
        # (use an empty dictionary for default indicator setup)
        clind = self.ClimateIndicator(indicator_name, frequency)

        if clind.is_perc_indicator:
            req_args = data.copy()
            for varname, da in data.items():
                arr_perc = percentile_grouped(
                    da,
                    group_freq=frequency,
                    per=95.,
                    climatology=True
                )
                arr_perc = expand_percentiles_to_daily(
                        da,
                        arr_perc,
                        frequency
                )
            req_args[f'{varname}_per'] = arr_perc
        else:
            req_args = data

        result = clind(**req_args)

        return result

    def test_all_indicators(self):
        import pyku
        from pyku.resources import generate_fake_cmip6_data
        # Load indicator data
        # ------------------------

        grouped_indicator_data = pyku.PYKU_RESOURCES.load_resource(
                    'climate_indicators'
                )

        # Derive dictionary with variables as keys and list of indicator names
        indicator_data = {
            group: list(indicators.keys())
            for group, indicators in grouped_indicator_data.items()
        }

        for varnames, indicators in indicator_data.items():
            data = {}
            for varname in varnames.split('+'):
                data[varname] = generate_fake_cmip6_data(
                    variable=varname,
                    ntime=2,
                    nlat=1,
                    nlon=1,
                    freq='D'
                )[varname]

            for indicator_name in indicators:
                print(f"Testing indicator {indicator_name}")
                self.calc_indicator(indicator_name, 'YS', data)


if __name__ == '__main__':
    unittest.main()
