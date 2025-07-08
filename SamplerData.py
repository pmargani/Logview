import os
from astropy.io import fits
from datetime import datetime
from astropy.time import Time
import numpy as np


class SamplerData:


    def __init__(self, directory):
        self.directory = directory
        self.youngest_file = None
        self.colnames = []
        self.sampler_name = os.path.basename(os.path.normpath(self.directory))

    def find_youngest_fits(self):
        fits_files = [f for f in os.listdir(self.directory) if f.lower().endswith('.fits')]
        if not fits_files:
            return None
        fits_files_full = [os.path.join(self.directory, f) for f in fits_files]
        self.youngest_file = max(fits_files_full, key=os.path.getmtime)
        return self.youngest_file

    def get_second_table_columns(self):
        if not self.youngest_file:
            return []
        try:
            with fits.open(self.youngest_file) as hdul:
                if len(hdul) < 2 or not hasattr(hdul[1], 'columns'):
                    return []
                self.colnames = hdul[1].columns.names
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
        
    def get_fits_files_from_names(self, start_datetime, end_datetime):
        """
        Returns a list of FITS files in the directory whose datetimes (parsed from filename)
        fall within the given datetime range, and also includes the file (if any) with the latest
        datetime before start_datetime.

        Args:
            start_datetime (datetime): Start of the datetime range.
            end_datetime (datetime): End of the datetime range.

        Returns:
            list: List of FITS file paths within the datetime range, plus the file right before the range if it exists.
        """
        fits_files = [f for f in os.listdir(self.directory) if f.lower().endswith('.fits')]
        fits_files_full = [os.path.join(self.directory, f) for f in fits_files]
        files_in_range = []
        before_start = None
        before_start_dt = None


        for file_path in fits_files_full:
            file_dt = self.get_datetime_from_filename(file_path)
            if not file_dt:
                continue
            if start_datetime <= file_dt <= end_datetime:
                files_in_range.append(file_path)
            elif file_dt < start_datetime:
                if before_start is None or file_dt > before_start_dt:
                    before_start = file_path
                    before_start_dt = file_dt

        if before_start:
            files_in_range.insert(0, before_start)
        return files_in_range
    
    def get_fits_files_in_range(self, start_datetime, end_datetime):
        """
        Returns a list of FITS files in the directory whose modification times fall within the given datetime range,
        and also includes the file (if any) with the latest modification time before start_datetime.

        Args:
            start_datetime (datetime): Start of the datetime range.
            end_datetime (datetime): End of the datetime range.

        Returns:
            list: List of FITS file paths within the datetime range, plus the file right before the range if it exists.
        """

        fits_files = [f for f in os.listdir(self.directory) if f.lower().endswith('.fits')]
        fits_files_full = [os.path.join(self.directory, f) for f in fits_files]
        files_in_range = []
        before_start = None
        before_start_mtime = None

        for file_path in fits_files_full:
            try:
                mtime = os.path.getmtime(file_path)
                file_datetime = datetime.fromtimestamp(mtime)
                if start_datetime <= file_datetime <= end_datetime:
                    files_in_range.append(file_path)
                elif file_datetime < start_datetime:
                    if before_start is None or mtime > before_start_mtime:
                        before_start = file_path
                        before_start_mtime = mtime
            except Exception:
                continue

        if before_start:
            files_in_range.insert(0, before_start)
        return files_in_range
    



    def get_data(self, columns, timestamp_range):
        """
        Extracts data for specified columns within a given timestamp range from the second table of all FITS files
        in the specified timestamp range.

        Args:
            columns (list): List of column names to extract.
            timestamp_range (tuple): (start, end) timestamps (inclusive).

        Returns:
            np.ndarray: Array of tuples with values for the specified columns within the timestamp range from all relevant files.
        """
        start, end = timestamp_range
        start_mjd = self.datetime_to_mjd(start)
        end_mjd = self.datetime_to_mjd(end)
        if start_mjd is None or end_mjd is None:
            return np.array([])
        files_in_range = self.get_fits_files_from_names(start, end)
        print('Files in range:', files_in_range)
        result = []
        for file_path in files_in_range:
            try:
                with fits.open(file_path) as hdul:
                    if len(hdul) < 2 or not hasattr(hdul[1], 'data'):
                        print(f"Skipping {file_path}: no second table HDU or data.")
                        continue
                    data = hdul[1].data
                    # Ensure all requested columns and 'DMJD' exist
                    if not all(col in data.names for col in columns) or 'DMJD' not in data.names:
                        print(f"Skipping {file_path}: not all requested columns or 'DMJD' exist.")
                        continue
                    mask = (data['DMJD'] >= start_mjd) & (data['DMJD'] <= end_mjd)
                    print(f"Mask for {file_path}: {mask}")
                    # Extract the data for the specified columns
                    rows = zip(*(data[col][mask] for col in columns))
                    # print(f"Extracted {len(rows)} rows from {file_path} for columns {columns}")
                    print("rows:", rows)
                    result.extend(rows)
            except Exception as e:
                print(f"Error processing {file_path}: {e}")
                continue
        return np.array(result)
