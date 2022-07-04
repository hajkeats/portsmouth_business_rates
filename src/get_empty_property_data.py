#!/usr/bin/env python3

from constants import EMPTY_PROPERTIES_DATA_FILE, EMPTY_PROPERTIES_CSV, PORTSMOUTH_DATA_URL, BUSINESS_RATES_CSV
from helpers import download, create_dataframe_files
from pathlib import Path


def main():
    """
    Takes the business rates CSV and creates a dataframe file from it.
    """
    if not Path(EMPTY_PROPERTIES_CSV).is_file():
        download(f'{PORTSMOUTH_DATA_URL}/{EMPTY_PROPERTIES_CSV.replace("resources/", "")}', EMPTY_PROPERTIES_CSV)

    if not Path(BUSINESS_RATES_CSV).is_file(): # Required for comparison of files
        print("No business rates file yet")
        exit(1)

    if not Path(f'{EMPTY_PROPERTIES_CSV}.data').is_file():
        create_dataframe_files(EMPTY_PROPERTIES_CSV, EMPTY_PROPERTIES_DATA_FILE, compare_file=f'{BUSINESS_RATES_CSV}.data')


if __name__ == '__main__':
    main()
