#!/usr/bin/env python3

from constants import BUSINESS_RATES_CSV, BUSINESS_RATES_DATA_FILE, PORTSMOUTH_DATA_URL
from helpers import download, create_dataframe_files
from pathlib import Path


def main():
    """
    Takes the business rates CSV and creates a dataframe file from it.
    """
    if not Path(BUSINESS_RATES_CSV).is_file():
        download(f'{PORTSMOUTH_DATA_URL}/{BUSINESS_RATES_CSV.replace("resources/", "")}', BUSINESS_RATES_CSV)

    if not Path(f'{BUSINESS_RATES_CSV}.data').is_file():
        create_dataframe_files(BUSINESS_RATES_CSV, BUSINESS_RATES_DATA_FILE)


if __name__ == '__main__':
    main()
