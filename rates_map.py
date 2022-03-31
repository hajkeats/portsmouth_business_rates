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
DATA_FILE = "data.file"
MAP_PNG = "map.png"

LOWEST_CUT_OFF = 300
HIGHEST_CUT_OFF = 300
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


def main():
    """
    Downloads business rates for Portsmouth. Gets the lat + long for each address, and plots it on a map of Portsmouth
    with a colour scale based on rate value
    """
    data_file = Path(DATA_FILE)
    ndr_file = Path(BUSINESS_RATES_CSV)
    empt_file = Path(EMPTY_PROPERTIES_CSV)
    map_file = Path(MAP_PNG)

    if not ndr_file.is_file():
        download(f'{PORTSMOUTH_DATA_URL}/{BUSINESS_RATES_CSV}', BUSINESS_RATES_CSV)

    if not empt_file.is_file():
        download(f'{PORTSMOUTH_DATA_URL}/{EMPTY_PROPERTIES_CSV}', EMPTY_PROPERTIES_CSV)

    if not data_file.is_file():
        reader = csv.DictReader(open(BUSINESS_RATES_CSV))

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

        with open(DATA_FILE, 'w') as f:
            json.dump(records, f)

    with open(DATA_FILE, 'r') as f:
        records = json.load(f)
        df = DataFrame(records)

    df = df.dropna()
    df.drop(index=df.rate.nlargest(n=HIGHEST_CUT_OFF).index, inplace=True)
    df.drop(index=df.rate.nsmallest(n=LOWEST_CUT_OFF).index, inplace=True)
    bbox = (df.longitude.min(), df.longitude.max(), df.latitude.min(), df.latitude.max())

    if not map_file.is_file():
        print(f'Getting map file for bbox {bbox}')
        bbox_format = f"{format(bbox[0], '.15f')},{format(bbox[2], '.15f')},{format(bbox[1], '.15f')}," \
                      f"{format(bbox[3], '.15f')}"
        map_url = f'{MAP_EXPORT_URL}?bbox={bbox_format}&scale=25000&format=png'
        input(f"Please open openstreetmap, and export {MAP_PNG} here using url {map_url}")

    map = plt.imread(MAP_PNG)
    fig, ax = plt.subplots()
    cm = plt.cm.get_cmap(COLOURMAP)
    sc = ax.scatter(df.longitude, df.latitude, c=df.rate, vmin=df.rate.min(), vmax=df.rate.max(), s=50, cmap=cm,
                    alpha=0.8)
    ax.set_title(f'Current Rateable Values in Portsmouth - Highest {HIGHEST_CUT_OFF} values removed, '
                 f'Lowest  {LOWEST_CUT_OFF} values removed')
    ax.set_xlim(df.longitude.min(), df.longitude.max())
    ax.set_ylim(df.latitude.min(), df.latitude.max())
    ax.imshow(map, extent=bbox, aspect='equal')
    plt.colorbar(sc)
    plt.show()


if __name__ == '__main__':
    main()
