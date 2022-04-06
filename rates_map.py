#!/usr/bin/env python3

import argparse
import csv
import random
import re
import json
from pathlib import Path
import requests
import matplotlib.pyplot as plt
from pandas import DataFrame
from time import sleep
import mpld3

PORTSMOUTH_DATA_URL = "https://data.portsmouth.gov.uk/media/tables"
POSTCODE_API_URL = "https://api.postcodes.io/postcodes"
MAP_EXPORT_URL = "https://render.openstreetmap.org/cgi-bin/export"

EMPTY_PROPERTIES_CSV = "empty-commercial-properties-january-2022.csv"
BUSINESS_RATES_CSV = "ndr-properties-january-2022.csv"
MAP_PNG = "map.png"

COLOURMAP = "RdBu"


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


def create_dataframe_files(input_file, compare_file=None):
    """
    Creates a dataframe file for the file provided
    :param input_file: The csv file to read
    """
    reader = csv.DictReader(open(input_file))

    records = []
    postcodes = []
    duplicate_postcodes = []
    failed_lookups = []
    failed_postcode_finds = []
    i = 0
    for _ in reader:
        record = next(reader)
        i += 1
        if i % 50 == 0:
            print(f'{i} processed')

        postcode = get_postcode(record['Full Property Address'])
        if postcode:
            if postcode not in postcodes:
                postcodes.append(postcode)
            elif postcode not in duplicate_postcodes:
                duplicate_postcodes.append(postcode)

            postcode_data = get_postcode_data(postcode)
            if not postcode_data:
                failed_lookups.append(record)
                continue
            record['postcode'] = postcode
            record['latitude'] = round(postcode_data['latitude'], 6)
            record['longitude'] = round(postcode_data['longitude'], 6)
            record['rate'] = int(record['Current Rateable Value'])
            records.append(record)
        else:
            failed_postcode_finds.append(record)
            continue

    print(f'{len(duplicate_postcodes)} duplicate postcodes found, {len(postcodes)} total')

    if compare_file:  # Used to make sure the location for each property is consistent across the dataframes
        with open(compare_file, 'r') as f:
            compare_records = json.load(f)
        for record in records:
            property_reference = record['\ufeffProperty Reference Number']
            for compare_record in compare_records:
                if compare_record['\ufeffProperty Reference Number'] == property_reference:
                    record['longitude'] = compare_record['longitude']
                    record['latitude'] = compare_record['latitude']
                    break
    else:  # Used to randomly differentiate locations between properties with the same postcode
        operator_functions = {
            '+': lambda a, b: a + b,
            '-': lambda a, b: a - b,
        }
        operators = list(operator_functions.keys())
        for record in records:
            if record['postcode'] in duplicate_postcodes:
                operator = random.choice(operators)
                record['latitude'] = round(operator_functions[operator](
                    record['latitude'], random.uniform(0.0001, 0.0005)
                ), 6)
                record['longitude'] = round(operator_functions[operator](
                    record['longitude'], random.uniform(0.0001, 0.0005)
                ), 6)

    with open(f'{input_file}.data', 'w') as f:
        json.dump(records, f)

    keys = failed_lookups[0].keys()
    with open(f'{input_file}-failed-lookup.data', 'w', newline='') as f:
        dict_writer = csv.DictWriter(f, keys)
        dict_writer.writeheader()
        dict_writer.writerows(failed_lookups)

    keys = failed_postcode_finds[0].keys()
    with open(f'{input_file}-failed-postcode-finds.data', 'w', newline='') as f:
        dict_writer = csv.DictWriter(f, keys)
        dict_writer.writeheader()
        dict_writer.writerows(failed_postcode_finds)


def create_interactive_map(br_df, ep_df, bbox, highres, cutoff):
    """
    Creates an interactive map on port 8888
    :param br_df: business rates data frame
    :param ep_df: empty properties data frame
    :param bbox: bounding box values
    :param highres: whether to create it in highres
    :param cutoff: the highest n values removed from dataset
    """
    map_img = plt.imread(MAP_PNG)
    if not highres:
        fig, ax = plt.subplots(dpi=240, figsize=(3, 3))
    if highres:
        fig, ax = plt.subplots(dpi=600, figsize=(3, 3))
    cm = plt.cm.get_cmap(COLOURMAP)
    ax.set_title(f'Current Rateable Values in Portsmouth - January 2022 \nHighest {cutoff} values removed')
    ax.set_xlim(br_df.longitude.min(), br_df.longitude.max())
    ax.set_ylim(br_df.latitude.min(), br_df.latitude.max())
    ax.imshow(map_img, extent=bbox, aspect='auto')
    sc = ax.scatter(br_df.longitude, br_df.latitude, c=br_df.rate, vmin=br_df.rate.min(), vmax=br_df.rate.max(), s=0.5,
                    cmap=cm, alpha=0.8)
    ep_sc = ax.scatter(ep_df.longitude, ep_df.latitude, c='y', s=0.2, marker='*')
    plt.colorbar(sc)
    names_and_rates = [f"{n}: {r}" for n, r in zip(br_df['Primary Liable party name'], br_df.rate)]
    tooltip = mpld3.plugins.PointLabelTooltip(sc, labels=names_and_rates)
    empty_list = [f"{n} (EMPTY)" for n in ep_df['Primary Liable party name']]
    empty_tooltip = mpld3.plugins.PointLabelTooltip(ep_sc, labels=empty_list)
    mpld3.plugins.connect(fig, tooltip)
    mpld3.plugins.connect(fig, empty_tooltip)
    mpld3.show()


def create_poster(br_df, ep_df, bbox, cutoff):
    """
    Creates a high res image of the map
    :param br_df: business rates data frame
    :param ep_df: empty properties data frame
    :param bbox: bounding box values
    :param cutoff: the highest n values removed from dataset
    """
    map_img = plt.imread(MAP_PNG)
    fig, ax = plt.subplots(dpi=900, figsize=(7, 7))
    cm = plt.cm.get_cmap(COLOURMAP)
    ax.set_title(f'Current Rateable Values in Portsmouth - January 2022 \nHighest {cutoff} values removed')
    ax.set_xlim(br_df.longitude.min(), br_df.longitude.max())
    ax.set_ylim(br_df.latitude.min(), br_df.latitude.max())
    ax.imshow(map_img, extent=bbox, aspect='auto')
    sc = ax.scatter(br_df.longitude, br_df.latitude, c=br_df.rate, vmin=br_df.rate.min(), vmax=br_df.rate.max(), s=2,
                    cmap=cm, alpha=0.8)
    ax.scatter(ep_df.longitude, ep_df.latitude, c='y', s=0.2, marker='*')
    plt.colorbar(sc)
    plt.savefig("poster.png")


def parse_args():
    """
    Parses arguments
    """
    parser = argparse.ArgumentParser()
    parser.add_argument('--poster', action='store_true', help='Create a PNG')
    parser.add_argument('--interactive', action='store_true', help='Create an interactive map')
    parser.add_argument('--highres', action='store_true', help='Create a high res interactive map')
    parser.add_argument('--cutoff', type=int, help='The top n values to remove', default=150)
    return parser.parse_args()


def main():
    """
    Downloads business rates for Portsmouth. Gets the lat + long for each address, and plots it on a map of Portsmouth
    with a colour scale based on rate value. Shows empty properties using a star.
    """
    args = parse_args()

    if not Path(BUSINESS_RATES_CSV).is_file():
        download(f'{PORTSMOUTH_DATA_URL}/{BUSINESS_RATES_CSV}', BUSINESS_RATES_CSV)

    if not Path(EMPTY_PROPERTIES_CSV).is_file():
        download(f'{PORTSMOUTH_DATA_URL}/{EMPTY_PROPERTIES_CSV}', EMPTY_PROPERTIES_CSV)

    if not Path(f'{BUSINESS_RATES_CSV}.data').is_file():
        create_dataframe_files(BUSINESS_RATES_CSV)

    if not Path(f'{EMPTY_PROPERTIES_CSV}.data').is_file():
        create_dataframe_files(EMPTY_PROPERTIES_CSV, compare_file=f'{BUSINESS_RATES_CSV}.data')

    with open(f'{BUSINESS_RATES_CSV}.data', 'r') as f:
        records = json.load(f)
        br_df = DataFrame(records)

    with open(f'{EMPTY_PROPERTIES_CSV}.data', 'r') as f:
        records = json.load(f)
        ep_df = DataFrame(records)

    br_df = br_df.dropna()
    br_df.drop(index=br_df.rate.nlargest(n=args.cutoff).index, inplace=True)
    bbox = (br_df.longitude.min(), br_df.longitude.max(), br_df.latitude.min(), br_df.latitude.max())

    if not Path(MAP_PNG).is_file():
        print(f'Getting map file for bbox {bbox}')
        bbox_format = f"{format(bbox[0], '.15f')},{format(bbox[2], '.15f')},{format(bbox[1], '.15f')}," \
                      f"{format(bbox[3], '.15f')}"
        map_url = f'{MAP_EXPORT_URL}?bbox={bbox_format}&scale=25000&format=png'
        input(f"Please open openstreetmap, and export {MAP_PNG} here using url {map_url}")

    if args.poster:
        create_poster(br_df, ep_df, bbox, args.cutoff)
    if args.interactive:
        create_interactive_map(br_df, ep_df, bbox, args.highres, args.cutoff)


if __name__ == '__main__':
    main()
