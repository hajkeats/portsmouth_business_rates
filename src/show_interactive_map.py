#!/usr/bin/env python3

from constants import (
    COLOURMAP,
    MAP_PNG,
    EMPTY_PROPERTIES_DATA_FILE,
    BUSINESS_RATES_DATA_FILE,
    FOODBANK_DELIVERIES_DATA_FILE,
    CUTOFF,
    HIGH_RES
)
import json
import matplotlib.pyplot as plt
import mpld3
from pandas import DataFrame


def create_interactive_map(br_df, ep_df, fb_df, bbox):
    """
    Creates an interactive map on port 8888
    :param br_df: business rates data frame
    :param ep_df: empty properties data frame
    :param fb_df: food bank data frame
    :param bbox: bounding box values
    """
    map_img = plt.imread(MAP_PNG)
    if not HIGH_RES:
        fig, ax = plt.subplots(dpi=240, figsize=(3, 3))
    if HIGH_RES:
        fig, ax = plt.subplots(dpi=600, figsize=(3, 3))

    cm = plt.cm.get_cmap(COLOURMAP)
    ax.set_title(f'Current Rateable Values in Portsmouth - January 2022 \nHighest {CUTOFF} values removed')
    ax.set_xlim(br_df.longitude.min(), br_df.longitude.max())
    ax.set_ylim(br_df.latitude.min(), br_df.latitude.max())
    ax.imshow(map_img, extent=bbox, aspect='auto')
    sc = ax.scatter(br_df.longitude, br_df.latitude, c=br_df.rate, vmin=br_df.rate.min(), vmax=br_df.rate.max(), s=0.5,
                    cmap=cm, alpha=0.8)
    ep_sc = ax.scatter(ep_df.longitude, ep_df.latitude, c='y', s=0.2, marker='*')
    fb_sc = ax.scatter(fb_df.longitude, fb_df.latitude, c='r', s=0.2, marker='+')
    plt.colorbar(sc)
    names_and_rates = [f"{n}: {r}" for n, r in zip(br_df['Primary Liable party name'], br_df.rate)]
    tooltip = mpld3.plugins.PointLabelTooltip(sc, labels=names_and_rates)
    empty_list = [f"{n} (EMPTY)" for n in ep_df['Primary Liable party name']]
    empty_tooltip = mpld3.plugins.PointLabelTooltip(ep_sc, labels=empty_list)
    mpld3.plugins.connect(fig, tooltip)
    mpld3.plugins.connect(fig, empty_tooltip)
    labels = ["Commercial Properties", "Empty Commercial Properties", "Foodbank deliveries"]
    scs = [sc, ep_sc, fb_sc]
    interactive_legend = mpld3.plugins.InteractiveLegendPlugin(scs, labels, legend_offset=(0, 580))
    mpld3.plugins.connect(fig, interactive_legend)
    mpld3.show()


def main():
    """
    Gets the relevant data and hosts the interactive map.
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

    create_interactive_map(br_df, ep_df, fb_df, bbox)


if __name__ == '__main__':
    main()
