import csv
import random
import re
import json
import requests
from time import sleep
from constants import POSTCODE_API_URL


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


def create_dataframe_files(input_file, output_file, compare_file=None):
    """
    Creates a dataframe file for the file provided
    :param input_file: The csv file to read
    :param output_file: the file to create
    :compare_file: used to compare lat+long for properties of the same reference num
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

    with open(output_file, 'w') as f:
        json.dump(records, f)

    keys = failed_lookups[0].keys()
    with open(f'{output_file}-failed-lookups', 'w', newline='') as f:
        dict_writer = csv.DictWriter(f, keys)
        dict_writer.writeheader()
        dict_writer.writerows(failed_lookups)

    keys = failed_postcode_finds[0].keys()
    with open(f'{output_file}-failed-postcode-finds', 'w', newline='') as f:
        dict_writer = csv.DictWriter(f, keys)
        dict_writer.writeheader()
        dict_writer.writerows(failed_postcode_finds)
