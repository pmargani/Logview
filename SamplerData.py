"Module for SamplerData class"

import os
from datetime import datetime
from astropy.io import fits
from astropy.time import Time
from isort import file
import numpy as np


class SamplerData:

    """
    A class for reading data in FITS files that were created by the GBT program sampler2log
    """

    def __init__(self, directory):
        self.directory = directory
        self.youngest_file = None
        self.colnames = []
        self.sampler_name = os.path.basename(os.path.normpath(self.directory))
        if not os.path.isdir(self.directory):
            raise Exception(f"Directory does not exist: {self.directory}")

    def find_column_info(self, start_datetime, end_datetime):
        startStr = start_datetime.strftime("%Y-%m-%d %H:%M:%S")
        endStr = end_datetime.strftime("%Y-%m-%d %H:%M:%S")
        print(f"Finding column info between {start_datetime} and {end_datetime}")
        files = self.get_fits_files_from_names(start_datetime, end_datetime)
        if not files:
            # raise Exception("No FITS files found in the specified range.")
            msg = f"No FITS files found in time range {startStr} to {endStr}"
            # logging.error(msg)
            return None, None, msg

        youngest_file = files[0]
        oldest_files = files[-1]

        cols1 = self.get_second_table_columns(file=youngest_file)
        cols2 = self.get_second_table_columns(file=oldest_files)
        if cols1 != cols2:
            # raise Exception("Column names do not match between the youngest and oldest files. Choose a date range where the columns do not change")
            msg = f"Column names do not match for files between {startStr} and {endStr}. Choose a date range where the columns do not change"
            return None, None, msg
        units = self.get_second_table_units(file=oldest_files)
        return cols1, units, None


    def find_youngest_fits(self):
        "for the current directory, return the FITS file with the youngest creation time"
        fits_files = [f for f in os.listdir(self.directory) if f.lower().endswith('.fits')]
        if not fits_files:
            return None
        fits_files_full = [os.path.join(self.directory, f) for f in fits_files]
        self.youngest_file = max(fits_files_full, key=os.path.getmtime)
        return self.youngest_file

    def get_second_table_columns(self, file=None):
        "The second table in these FITS files contains the data, specified by columns"
        if file is None:
            if not self.youngest_file:
                return []
        else:
            self.youngest_file = file
        try:
            with fits.open(self.youngest_file) as hdul:
                if len(hdul) < 2 or not hasattr(hdul[1], 'columns'):
                    return []
                self.colnames = hdul[1].columns.names
                return self.colnames
        except Exception:
            return []

    def get_second_table_units(self, file=None):
        "The second table in these FITS files contains the data, including unit info"
        if file is None:
            if not self.youngest_file:
                return []
        else:
            self.youngest_file = file

        try:
            with fits.open(self.youngest_file) as hdul:
                if len(hdul) < 2 or not hasattr(hdul[1], 'columns'):
                    return []
                self.colnames = hdul[1].columns.units
                return self.colnames
        except Exception:
            return []

    def datetime_to_mjd(self, dt):
        """
        Converts a datetime object to Modified Julian Date (MJD) using astropy.

        Args:
            dt (datetime): The datetime object to convert.

        Returns:
            float: The corresponding MJD value.
        """
        if not isinstance(dt, datetime):
            return None
        try:
            t = Time(dt)
            return t.mjd
        except Exception:
            return None

    def get_datetime_from_filename(self, filename):
        """
        Extracts a datetime object from a FITS filename formatted as '%Y_%m_%d_%H:%M:%S.fits'.

        Args:
            filename (str): The FITS filename.

        Returns:
            datetime: The extracted datetime object, or None if parsing fails.
        """
        base = os.path.basename(filename)
        name, _ = os.path.splitext(base)
        try:
            return datetime.strptime(name, "%Y_%m_%d_%H:%M:%S")
        except ValueError:
            return None

    def get_fits_files_from_names(self, start_datetime, end_datetime, before=False):
        """
        Returns a list of FITS files in the directory whose datetimes (parsed from filename)
        fall within the given datetime range, and also includes the file (if any) with the latest
        datetime before start_datetime.

        Args:
            start_datetime (datetime): Start of the datetime range.
            end_datetime (datetime): End of the datetime range.

        Returns:
            list: List of FITS file paths within the datetime range, plus the file right before
            the range if it exists.
        """
        fits_files = [f for f in os.listdir(self.directory) if f.lower().endswith('.fits')]
        fits_files_full = sorted([os.path.join(self.directory, f) for f in fits_files])
        files_in_range = []
        before_start = None
        before_start_dt = None

        # print(f"date range: {start_datetime} to {end_datetime}")
        for file_path in fits_files_full:
            file_dt = self.get_datetime_from_filename(file_path)
            if not file_dt:
                continue
            if start_datetime <= file_dt <= end_datetime:

                files_in_range.append(file_path)
            elif before and file_dt < start_datetime:
                if before_start is None or file_dt > before_start_dt:
                    before_start = file_path
                    before_start_dt = file_dt

        if before and before_start:
            files_in_range.insert(0, before_start)
        return files_in_range





    def get_data(self, columns, timestamp_range, pre_open_hook=None):
        """
        Extracts data for specified columns within a given timestamp range from the second
        table of all FITS files in the specified timestamp range.

        Args:
            columns (list): List of column names to extract.
            timestamp_range (tuple): (start, end) timestamps (inclusive).

        Returns:
            np.ndarray: Array of tuples with values for the specified columns within the
            timestamp range from all relevant files.
        """
        start, end = timestamp_range
        start_mjd = self.datetime_to_mjd(start)
        end_mjd = self.datetime_to_mjd(end)
        if start_mjd is None or end_mjd is None:
            return np.array([])
        files_in_range = self.get_fits_files_from_names(start, end)
        # print('Files in range:', files_in_range)
        result = []
        for ifile, file_path in enumerate(files_in_range):
            try:
                # an example of a pre_open_hook might be a method for updating the status
                # bar of an application using this class
                if pre_open_hook is not None:
                    pre_open_hook(file_path, ifile, len(files_in_range))
                with fits.open(file_path) as hdul:
                    if len(hdul) < 2 or not hasattr(hdul[1], 'data'):
                        # Skipping file: no second table HDU or data.
                        continue
                    data = hdul[1].data
                    # Ensure all requested columns and 'DMJD' exist
                    if not all(col in data.names for col in columns) or 'DMJD' not in data.names:
                        # Skipping file: not all requested columns or 'DMJD' exist.
                        continue
                    mask = (data['DMJD'] >= start_mjd) & (data['DMJD'] <= end_mjd)
                    # Extract the data for the specified columns
                    rows = zip(*(data[col][mask] for col in columns))
                    result.extend(rows)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue
        return np.array(result)

    def apply_expression_to_data(self, data, expression):
        """
        Applies a Python expression to the given data array. The expression should be a string
        that can reference 'data' as the variable.

        Args:
            data (np.ndarray): The data array to modify.
            expression (str): The Python expression to evaluate, e.g., 'data * 2'.

        Returns:
            np.ndarray: The modified data array.
        """
        try:
            # 'data' is available in the eval context
            result = eval(expression, {"np": np}, {"data": data})
            return result
        except Exception as e:
            print(f"Error evaluating expression '{expression}': {e}")
            return data
