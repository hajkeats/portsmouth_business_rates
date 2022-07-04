#!/usr/bin/env python3

from constants import (
    COLOURMAP,
    MAP_PNG,
    EMPTY_PROPERTIES_DATA_FILE,
    BUSINESS_RATES_DATA_FILE,
    FOODBANK_DELIVERIES_DATA_FILE,
    CUTOFF
)
import json
import matplotlib.pyplot as plt
import mpld3
from pandas import DataFrame


def create_poster(br_df, ep_df, fb_df, bbox):
    """
    Creates a high res image of the map
    :param br_df: business rates data frame
    :param ep_df: empty properties data frame
    :param fb_df: food bank data frame
    :param bbox: bounding box values
    """
    map_img = plt.imread(MAP_PNG)
    fig, ax = plt.subplots(dpi=900, figsize=(7, 7))
    cm = plt.cm.get_cmap(COLOURMAP)
    ax.set_title(f'Current Rateable Values in Portsmouth - January 2022 \nHighest {CUTOFF} values removed')
    ax.set_xlim(br_df.longitude.min(), br_df.longitude.max())
    ax.set_ylim(br_df.latitude.min(), br_df.latitude.max())
    ax.imshow(map_img, extent=bbox, aspect='auto')
    sc = ax.scatter(br_df.longitude, br_df.latitude, c=br_df.rate, vmin=br_df.rate.min(), vmax=br_df.rate.max(), s=2,
                    cmap=cm, alpha=0.8)
    ax.scatter(ep_df.longitude, ep_df.latitude, c='y', s=0.2, marker='*')
    ax.scatter(fb_df.longitude, fb_df.latitude, c='r', s=0.2, marker='+')
    plt.colorbar(sc)
    plt.savefig("poster.png")


def main():
    """
    Gets the relevant data and creates the poster
    """

    with open(f'{BUSINESS_RATES_DATA_FILE}', 'r') as f:
        records = json.load(f)
        br_df = DataFrame(records)

    with open(f'{EMPTY_PROPERTIES_DATA_FILE}', 'r') as f:
        records = json.load(f)
        ep_df = DataFrame(records)

    with open(f'{FOODBANK_DELIVERIES_DATA_FILE}', 'r') as f:
        records = json.load(f)
        fb_df = DataFrame(records)

    br_df = br_df.dropna()
    br_df.drop(index=br_df.rate.nlargest(n=CUTOFF).index, inplace=True)
    bbox = (br_df.longitude.min(), br_df.longitude.max(), br_df.latitude.min(), br_df.latitude.max())

    create_poster(br_df, ep_df, fb_df, bbox)


if __name__ == '__main__':
    main()
