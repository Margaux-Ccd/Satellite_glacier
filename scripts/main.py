from datetime import date, timedelta
import requests
import geopandas as gpd
import os
import json
from shapely.geometry import shape, Polygon

from keycloak import get_keycloak
from AOI_polygon import load_polygon_from_geojson
from Search_dataset import request_dataset

def main():
    # Ask for the output path
    output_path = r"/data/Sentinel" #input("Please enter the output path to download files: ")

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
    copernicus_user = username  # Copernicus User
    copernicus_password = password  # Copernicus Password
    ft = polygon  # WKT Representation of BBOX
    data_collection = "SENTINEL-2"  # Sentinel satellite

    today = date.today()
    today_string = today.strftime("%Y-%m-%d")
    yesterday = today - timedelta(days=2)
    yesterday_string = yesterday.strftime("%Y-%m-%d")
    resolution_value = 10  # Example resolution in meters
    
    

    # Construct the query URL with additional filters
    bands_list = ['B02', 'B03', 'B04']  # Example bands list


    # Actions----------------#
    p=request_dataset(data_collection, ft, yesterday_string, today_string)

    if p.shape[0] > 0 :
        p["geometry"] = p["GeoFootprint"].apply(shape)
        productDF = gpd.GeoDataFrame(p).set_geometry("geometry") # Convert PD to GPD
        productDF = productDF[~productDF["Name"].str.contains("L1C")] # Remove L1C dataset
        print(f" total L2A tiles found {len(productDF)}")
        productDF["identifier"] = productDF["Name"].str.split(".").str[0]
        allfeat = len(productDF) 

        if allfeat == 0:
            print("No tiles found for today")
        else:
            ## download all tiles from server
            for index,feat in enumerate(productDF.iterfeatures()):
                try:
                    session = requests.Session()
                    keycloak_token = get_keycloak(copernicus_user,copernicus_password)
                    session.headers.update({"Authorization": f"Bearer {keycloak_token}"})
                    url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({feat['properties']['Id']})/$value"
                    response = session.get(url, allow_redirects=False)
                    while response.status_code in (301, 302, 303, 307):
                        url = response.headers["Location"]
                        response = session.get(url, allow_redirects=False)
                    print(feat["properties"]["Id"])
                    file = session.get(url, verify=False, allow_redirects=True)

                    with open(
                        f"{feat['properties']['identifier']}.zip", #location to save zip from copernicus 
                        "wb",
                    ) as p:
                        print(feat["properties"]["Name"])
                        p.write(file.content)
                except:
                    print("problem with server")
    else :
        print('no data found')

if __name__ == "__main__":
    main()

# from datetime import date, timedelta
# import requests
# import geopandas as gpd
# import os
# import json
# from tqdm import tqdm  # Import tqdm for progress tracking
# from shapely.geometry import shape

# from keycloak import get_keycloak
# from AOI_polygon import load_polygon_from_geojson
# from Search_dataset import request_dataset

# def main():
#     # Output directory
#     output_path = r"/data/Sentinel"
#     os.makedirs(output_path, exist_ok=True)  # Ensure directory exists

#     # Load credentials from config
#     with open('draft/configSentinel.json', 'r') as file:
#         config = json.load(file)

#     username = config['username']
#     password = config['password']

#     # Define search parameters
#     polygon_path = 'draft/polygon/Aletsch.geojson'
#     polygon = load_polygon_from_geojson(polygon_path)
#     data_collection = "SENTINEL-2"

#     today = date.today()
#     yesterday = today - timedelta(days=2)

#     # Filtering conditions
#     resolution_value = 10  # Only process this resolution
#     bands_list = ['B02', 'B03', 'B04']  # Download only these bands

#     # Request dataset
#     p = request_dataset(data_collection, polygon, yesterday.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d"))

#     if p.shape[0] > 0:
#         p["geometry"] = p["GeoFootprint"].apply(shape)
#         productDF = gpd.GeoDataFrame(p).set_geometry("geometry")

#         # Remove L1C datasets (keep only L2A)
#         productDF = productDF[~productDF["Name"].str.contains("L1C")]
        
#         # Ensure resolution column exists before filtering
#         if "Resolution" in productDF.columns:
#             productDF = productDF[productDF["Resolution"] == resolution_value]

#         print(f"Total L2A tiles found with {resolution_value}m resolution: {len(productDF)}")
        
#         if len(productDF) == 0:
#             print("No matching tiles found")
#             return

#         # Download process with tqdm progress bar
#         for feat in tqdm(productDF.iterfeatures(), desc="Downloading Files", unit="file"):
#             try:
#                 session = requests.Session()
#                 keycloak_token = get_keycloak(username, password)
#                 session.headers.update({"Authorization": f"Bearer {keycloak_token}"})

#                 product_id = feat['properties']['Id']
#                 identifier = feat['properties']['Name']
#                 url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({product_id})/$value"

#                 response = session.get(url, allow_redirects=False)
#                 while response.status_code in (301, 302, 303, 307):
#                     url = response.headers["Location"]
#                     response = session.get(url, allow_redirects=False)

#                 # Download only if it contains the required bands
#                 if any(band in identifier for band in bands_list):
#                     file = session.get(url, verify=False, allow_redirects=True)
#                     file_path = os.path.join(output_path, f"{identifier}.zip")

#                     with open(file_path, "wb") as p:
#                         p.write(file.content)

#                 else:
#                     print(f"Skipping {identifier} (Bands not in {bands_list})")

#             except Exception as e:
#                 print(f"Error downloading {identifier}: {e}")

#     else:
#         print('No data found')

# if __name__ == "__main__":
#     main()
