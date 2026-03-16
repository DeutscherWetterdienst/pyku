import unittest


class TestComputeMethods(unittest.TestCase):

    import pyku.compute as compute
    import pyku
    import os
    import glob

    model = pyku.resources.get_test_data('model_data')

    def test_resample_datetimes(self):

        # Placeholder. No function tested yet.

        self.assertEqual(True, True)


if __name__ == '__main__':
    unittest.main()
