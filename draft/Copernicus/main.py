"""This file was an attempt to download sentinel data directly from Copernicus Data Space Ecosystem
It is however unable to filter the bands or resolution from the metadata. This code permits to download a 
.SAFE file (which is huge) as a .zip file. It takes around 10 min to download one .SAFE file."""

from datetime import date, timedelta
import json

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

    # Actions----------------#
    p=request_dataset(data_collection, ft, yesterday_string, today_string)
    tile_footprints = p[[ "Name","GeoFootprint", "Id"]]
    print(tile_footprints)
    # print(p.keys)
    
    download_all_safe(p,username, password, output_path)

   

if __name__ == "__main__":
    main()

