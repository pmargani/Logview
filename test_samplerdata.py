import unittest
import os
import tempfile
import shutil
from datetime import datetime, timedelta
from astropy.io import fits
import numpy as np
from SamplerData import SamplerData

class TestSamplerData(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory
        self.test_dir = tempfile.mkdtemp()
        self.sampler = SamplerData(self.test_dir)
        # Create a test FITS file with a second table HDU
        self.fits_filename = os.path.join(self.test_dir, '2025_07_07_17:56:08.fits')
        # Parse the initial datetime from the filename
        initial_dt = datetime.strptime('2025_07_07_17:56:08', '%Y_%m_%d_%H:%M:%S')
        dts = [initial_dt + timedelta(seconds=i) for i in range(3)]
        dmjd_values = [self.sampler.datetime_to_mjd(dt) for dt in dts]
        # Convert to MJD (Modified Julian Date)
        # initial_mjd = self.sampler.datetime_to_mjd(initial_dt)
        # Create DMJD values based on the initial MJD
        # dmjd_values = np.array([initial_mjd, initial_mjd + 1.0, initial_mjd + 2.0])
        col1 = fits.Column(name='DMJD', array=dmjd_values, format='D')
        col2 = fits.Column(name='A', array=np.array([1.0, 2.0, 3.0]), format='D')
        col3 = fits.Column(name='B', array=np.array([3.0, 4.0, 5.0]), format='D')
        cols = fits.ColDefs([col1, col2, col3])
        hdu1 = fits.BinTableHDU.from_columns(cols)
        hdul = fits.HDUList([fits.PrimaryHDU(), hdu1])
        hdul.writeto(self.fits_filename)

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_find_youngest_fits(self):
        youngest = self.sampler.find_youngest_fits()
        self.assertTrue(youngest.endswith('.fits'))

    def test_get_second_table_columns(self):
        self.sampler.find_youngest_fits()
        cols = self.sampler.get_second_table_columns()
        self.assertIn('DMJD', cols)
        self.assertIn('A', cols)
        self.assertIn('B', cols)

    def test_datetime_to_mjd(self):
        dt = datetime(2025, 7, 7, 17, 56, 8)
        mjd = self.sampler.datetime_to_mjd(dt)
        self.assertIsInstance(mjd, float)

    def test_get_datetime_from_filename(self):
        dt = self.sampler.get_datetime_from_filename('2025_07_07_17:56:08.fits')
        self.assertEqual(dt, datetime(2025, 7, 7, 17, 56, 8))

    def test_get_fits_files_from_names(self):
        start = datetime(2025, 7, 7, 0, 0, 0)
        end = datetime(2025, 7, 8, 0, 0, 0)
        files = self.sampler.get_fits_files_from_names(start, end)
        self.assertTrue(any(f.endswith('.fits') for f in files))

    def test_get_data(self):
        def print_it(filename, n, m):
            print(f"Opening file: {filename} ({n}/{m})")
        start = datetime(2025, 7, 7, 0, 0, 0)
        end = datetime(2025, 7, 8, 0, 0, 0)
        columns = ['DMJD', 'A', 'B']
        data = self.sampler.get_data(columns, (start, end), pre_open_hook=print_it)
        print(data)
        self.assertEqual(data.shape[1], 3)
        self.assertTrue(np.all(data[:, 0] >= 60000.0))

    def test_apply_expression_to_data(self):
        arr = np.array([1, 2, 3])
        # Test a simple multiplication
        result = self.sampler.apply_expression_to_data(arr, 'data * 2')
        print("Result of multiplication:", result)
        np.testing.assert_array_equal(result, arr * 2)
        # Test with numpy function
        result = self.sampler.apply_expression_to_data(arr, 'np.sqrt(data)')
        np.testing.assert_array_equal(result, np.sqrt(arr))
        # Test with invalid expression (should return original data)
        result = self.sampler.apply_expression_to_data(arr, 'data + unknown_var')
        np.testing.assert_array_equal(result, arr)

if __name__ == '__main__':
    unittest.main()
