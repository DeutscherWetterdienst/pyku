import unittest


class TestTimekitMethods(unittest.TestCase):

    import pyku.timekit as timekit
    import pyku
    import os
    import glob
    import cftime

    model = pyku.resources.get_test_data('model_data')

    cftime_ds = (
        pyku.resources.get_test_data('cftime_data')
        .sel(time=slice('1981', None))
    )

    def test_resample_datetimes(self):

        import numpy as np
        import cftime

        self.assertEqual(

            np.array_equal(

                self.timekit.resample_datetimes(
                    self.model, frequency='QS-DEC', how='mean'
                ).time.values[0:5],

                np.array([
                    '1969-12-01T00:00:00.000000000',
                    '1970-03-01T00:00:00.000000000',
                    '1970-06-01T00:00:00.000000000',
                    '1970-09-01T00:00:00.000000000',
                    '1970-12-01T00:00:00.000000000'
                ], dtype='datetime64[ns]'),

            ),

            True
        )

        self.assertEqual(

            np.array_equal(

                self.timekit.resample_datetimes(
                    self.model, frequency='QS-DEC', how='mean', complete=False
                ).time.values[0:5],

                np.array([
                    '1969-12-01T00:00:00.000000000',
                    '1970-03-01T00:00:00.000000000',
                    '1970-06-01T00:00:00.000000000',
                    '1970-09-01T00:00:00.000000000',
                    '1970-12-01T00:00:00.000000000'
                ], dtype='datetime64[ns]')
            ),

            True
        )

        self.assertEqual(

            np.array_equal(

                self.timekit.resample_datetimes(
                    self.cftime_ds,
                    how='mean',
                    frequency='YS',
                    complete=False
                    ).time.values[0:5],

                np.array([
                    cftime.DatetimeNoLeap(1981, 1, 1, 0, 0, 0, 0, has_year_zero=True),  # noqa
                    cftime.DatetimeNoLeap(1982, 1, 1, 0, 0, 0, 0, has_year_zero=True),  # noqa
                    cftime.DatetimeNoLeap(1983, 1, 1, 0, 0, 0, 0, has_year_zero=True),  # noqa
                    cftime.DatetimeNoLeap(1984, 1, 1, 0, 0, 0, 0, has_year_zero=True),  # noqa
                    cftime.DatetimeNoLeap(1985, 1, 1, 0, 0, 0, 0, has_year_zero=True)  # noqa
                ], dtype=object)
            ),

            True
        )


if __name__ == '__main__':
    unittest.main()
