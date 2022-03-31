#!/usr/bin/env python3

import csv
import re
import json
from pathlib import Path
import requests
import matplotlib.pyplot as plt
from pandas import DataFrame
from time import sleep

PORTSMOUTH_DATA_URL = "https://data.portsmouth.gov.uk/media/tables"
POSTCODE_API_URL = "https://api.postcodes.io/postcodes"
MAP_EXPORT_URL = "https://render.openstreetmap.org/cgi-bin/export"

EMPTY_PROPERTIES_CSV = "empty-commercial-properties-january-2022.csv"
BUSINESS_RATES_CSV = "ndr-properties-january-2022.csv"
MAP_PNG = "map.png"

LOWEST_CUT_OFF = 200
HIGHEST_CUT_OFF = 200
COLOURMAP = "inferno"


def get_postcode(address):
    """
    For a given address string, return the postcode found. If none found, return None.
    :param address: an address to search
    """
    try:
        return re.findall(r'[A-Z]{1,2}[0-9R][0-9A-Z]? [0-9][A-Z]{2}', address)[0]
    except IndexError:
        return None


def get_postcode_data(postcode):
    """
    Call the postcodes.io API to return data on a given postcode.
    :param postcode: the postcode to retrieve information for
    """
    try:
        resp = requests.get(f'{POSTCODE_API_URL}/{postcode}', timeout=10)
    except requests.exceptions.RequestException:
        print(f"Request Exception. Sleeping 10 then retrying.")
        sleep(10)
        resp = requests.get(f'{POSTCODE_API_URL}/{postcode}')

    try:
        result = resp.json()['result']
        return result
    except KeyError:
        print(resp.status_code)
        return None


def download(url, file_path):
    """
    Uses requests to download a file from a url to a specific file path
    :param url: the URL to download from
    :param file_path: the file path to download to
    """
    resp = requests.get(url, allow_redirects=True)
    open(file_path, 'wb').write(resp.content)


def create_dataframe_files(input_file):
    """
    Creates a dataframe file for the file provided
    """
    reader = csv.DictReader(open(input_file))

    records = []
    i = 0
    for _ in reader:
        record = next(reader)
        i += 1
        if i % 50 == 0:
            print(f'{i} processed')

        postcode = get_postcode(record['Full Property Address'])
        if postcode:
            postcode_data = get_postcode_data(postcode)
            if not postcode_data:
                continue
            record['latitude'] = round(postcode_data['latitude'], 6)
            record['longitude'] = round(postcode_data['longitude'], 6)
            record['rate'] = int(record['Current Rateable Value'])
            records.append(record)

    with open(f'{input_file}.data', 'w') as f:
        json.dump(records, f)


def main():
    """
    Downloads business rates for Portsmouth. Gets the lat + long for each address, and plots it on a map of Portsmouth
    with a colour scale based on rate value
    """
    ndr_file = Path(BUSINESS_RATES_CSV)
    ndr_data_file = Path(f'{BUSINESS_RATES_CSV}.data')
    empt_file = Path(EMPTY_PROPERTIES_CSV)
    empt_data_file = Path(f'{EMPTY_PROPERTIES_CSV}.data')
    map_file = Path(MAP_PNG)

    if not ndr_file.is_file():
        download(f'{PORTSMOUTH_DATA_URL}/{BUSINESS_RATES_CSV}', BUSINESS_RATES_CSV)

    if not empt_file.is_file():
        download(f'{PORTSMOUTH_DATA_URL}/{EMPTY_PROPERTIES_CSV}', EMPTY_PROPERTIES_CSV)

    if not ndr_data_file.is_file():
        create_dataframe_files(BUSINESS_RATES_CSV)

    if not empt_data_file.is_file():
        create_dataframe_files(EMPTY_PROPERTIES_CSV)

    with open(f'{BUSINESS_RATES_CSV}.data', 'r') as f:
        records = json.load(f)
        ndr_df = DataFrame(records)

    with open(f'{EMPTY_PROPERTIES_CSV}.data', 'r') as f:
        records = json.load(f)
        empt_df = DataFrame(records)

    ndr_df = ndr_df.dropna()
    ndr_df.drop(index=ndr_df.rate.nlargest(n=HIGHEST_CUT_OFF).index, inplace=True)
    ndr_df.drop(index=ndr_df.rate.nsmallest(n=LOWEST_CUT_OFF).index, inplace=True)
    bbox = (ndr_df.longitude.min(), ndr_df.longitude.max(), ndr_df.latitude.min(), ndr_df.latitude.max())

    if not map_file.is_file():
        print(f'Getting map file for bbox {bbox}')
        bbox_format = f"{format(bbox[0], '.15f')},{format(bbox[2], '.15f')},{format(bbox[1], '.15f')}," \
                      f"{format(bbox[3], '.15f')}"
        map_url = f'{MAP_EXPORT_URL}?bbox={bbox_format}&scale=25000&format=png'
        input(f"Please open openstreetmap, and export {MAP_PNG} here using url {map_url}")

    map = plt.imread(MAP_PNG)
    fig, ax = plt.subplots()
    cm = plt.cm.get_cmap(COLOURMAP)
    sc = ax.scatter(ndr_df.longitude, ndr_df.latitude, c=ndr_df.rate, vmin=ndr_df.rate.min(), vmax=ndr_df.rate.max(),
                    s=50, cmap=cm, alpha=0.8)
    ax.scatter(empt_df.longitude, empt_df.latitude, c='w', s=20, marker='*')
    ax.set_title(f'Current Rateable Values in Portsmouth - Highest {HIGHEST_CUT_OFF} values removed, '
                 f'Lowest  {LOWEST_CUT_OFF} values removed')
    ax.set_xlim(ndr_df.longitude.min(), ndr_df.longitude.max())
    ax.set_ylim(ndr_df.latitude.min(), ndr_df.latitude.max())
    ax.imshow(map, extent=bbox, aspect='equal')
    plt.colorbar(sc)
    plt.show()


if __name__ == '__main__':
    main()
