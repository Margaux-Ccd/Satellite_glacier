from datetime import date, timedelta
import requests
import geopandas as gpd
import os
import json
from shapely.geometry import shape, Polygon
import tqdm
import pandas as pd

from keycloak import get_keycloak
from AOI_polygon import load_polygon_from_geojson
from Search_dataset import request_dataset
from download_safe import download_all_safe
# from filter_data import *
def main():
    # Ask for the output path
    output_path = r"./data/Sentinel" #input("Please enter the output path to download files: ")

    # # Open and read the JSON file
    with open('draft/configSentinel.json', 'r') as file:
        config = json.load(file)

    # Access the variables
    password = config['password']
    username = config['username']
    # username = input('Enter your email adress (=copernicus username):')
    # password = input('Enter your copernicus password:')

    polygon_path = 'draft/polygon/Aletsch.geojson'


    polygon = load_polygon_from_geojson(polygon_path)
    ft = polygon  # WKT Representation of BBOX
    data_collection = "SENTINEL-2"  # Sentinel satellite

    today = date.today()
    today_string = today.strftime("%Y-%m-%d")
    yesterday = today - timedelta(days=3)
    yesterday_string = yesterday.strftime("%Y-%m-%d")
    resolution_value = 10  # Example resolution in meters
    
    

    # Construct the query URL with additional filters
    bands_list = ['B02', 'B03', 'B04']  # Example bands list


    # Actions----------------#
    p=request_dataset(data_collection, ft, yesterday_string, today_string)
    tile_footprints = p[[ "Name","GeoFootprint", "Id"]]
    print(tile_footprints)
    # print(p.keys)
    
    from filter_data import get_file_list_from_server, filter_granule_img_data
    # Example Usage
    test_product_data = pd.DataFrame([
    {
        "Id": "22e2fbfe-0aa7-423d-b0b5-df46527f03f5",  # Example product ID
        "Name": "S2A_MSIL2A_20240320T103021_N0500_R092_T31TGL_20240320T140053.SAFE",
        "GeoFootprint": {"type": "Polygon", "coordinates": [[[0,0], [1,0], [1,1], [0,1], [0,0]]]}  # Example geo-coordinates
    }
    ])

        # Function to filter for only 10m resolution and B03 band
    def filter_b03_10m(file_list):
        return filter_granule_img_data(file_list, res_value=10, band="B03")

    # Run the function to get file list
    file_dict = get_file_list_from_server(test_product_data, username, password, node_filter=filter_b03_10m)

    # Print results
    for product_id, files in file_dict.items():
        print(f"\n✅ Product ID: {product_id}")
        print(f"🔹 Files Found: {files}")

        if files:
            print(f"✅ The B03 band at 10m resolution was found: {files[0]}")
        else:
            print("❌ No matching files found.")
    #download_all_safe(p,username, password, output_path)

   

if __name__ == "__main__":
    main()

