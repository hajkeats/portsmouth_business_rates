from constants import FOODBANK_DELIVERIES_CSV, FOODBANK_DELIVERIES_DATA_FILE
from helpers import get_postcode_data
import csv
import json


def get_food_bank_points():
    """
    Gets the lat + long for food bank deliveries
    """
    reader = csv.DictReader(open(FOODBANK_DELIVERIES_CSV))
    records = []
    for _ in reader:
        record = next(reader)
        postcode_data = get_postcode_data(record['postcode'])
        if not postcode_data:
            continue
        record['latitude'] = round(postcode_data['latitude'], 6)
        record['longitude'] = round(postcode_data['longitude'], 6)
        records.append(record)
    return records


def main():
    """
    Gets the foodbank data and stores it in a .data file.
    """
    records = get_food_bank_points()
    with open(FOODBANK_DELIVERIES_DATA_FILE, 'w') as f:
        json.dump(records, f)


if __name__ == '__main__':
    main()
