# from datetime import date, timedelta
# import requests
# import pandas as pd
# import geopandas as gpd
# import json
# import geojson
# from shapely.geometry import shape, Polygon

# # Open and read the JSON file
# with open('draft/configSentinel.json', 'r') as file:
#     config = json.load(file)

# # Access the variables
# password = config['password']
# username = config['username']

# ##----------------------------------

# # Open and read the GeoJSON file
# with open('draft/polygon/Aletsch.geojson', 'r') as file:
#     geojson_data = geojson.load(file)


# # Extract the polygon from the GeoJSON data
# polygon_data = geojson_data['features'][0]['geometry']  # Adjust index if needed
# polygon = shape(polygon_data)

# # Check if it's a polygon
# if isinstance(polygon, Polygon):
#     print("The GeoJSON data represents a polygon.")
#     print(f"Polygon Coordinates: {polygon}")
# else:
#     print("The GeoJSON data does not represent a polygon.")


# copernicus_user = username # copernicus User
# copernicus_password = password # copernicus Password
# ft = polygon # WKT Representation of BBOX
# data_collection = "SENTINEL-2" # Sentinel satellite

# today =  date.today()
# today_string = today.strftime("%Y-%m-%d")
# yesterday = today - timedelta(days=3)
# yesterday_string = yesterday.strftime("%Y-%m-%d")


# # get a token for access
# def get_keycloak(username: str, password: str) -> str:
#     data = {
#         "client_id": "cdse-public",
#         "username": username,
#         "password": password,
#         "grant_type": "password",
#     }
#     try:
#         r = requests.post(
#             "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
#             data=data,
#         )
#         r.raise_for_status()
#     except Exception as e:
#         raise Exception(
#             f"Keycloak token creation failed. Reponse from the server was: {r.json()}"
#         )
#     return r.json()["access_token"]


# json_ = requests.get(
#     f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq '{data_collection}' and OData.CSC.Intersects(area=geography'SRID=4326;{ft}') and ContentDate/Start gt {yesterday_string}T00:00:00.000Z and ContentDate/Start lt {today_string}T00:00:00.000Z&$count=True&$top=1000"
# ).json()  
# p = pd.DataFrame.from_dict(json_["value"]) # Fetch available dataset


# if p.shape[0] > 0 :
#     p["geometry"] = p["GeoFootprint"].apply(shape)
#     productDF = gpd.GeoDataFrame(p).set_geometry("geometry") # Convert PD to GPD
#     productDF = productDF[~productDF["Name"].str.contains("L1C")] # Remove L1C dataset
#     print(f" total L2A tiles found {len(productDF)}")
#     productDF["identifier"] = productDF["Name"].str.split(".").str[0]
#     allfeat = len(productDF) 

#     if allfeat == 0:
#         print("No tiles found for today")
#     else:
#         ## download all tiles from server
#         for index,feat in enumerate(productDF.iterfeatures()):
#             try:
#                 session = requests.Session()
#                 keycloak_token = get_keycloak(copernicus_user,copernicus_password)
#                 session.headers.update({"Authorization": f"Bearer {keycloak_token}"})
#                 url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({feat['properties']['Id']})/$value"
#                 response = session.get(url, allow_redirects=False)
#                 while response.status_code in (301, 302, 303, 307):
#                     url = response.headers["Location"]
#                     response = session.get(url, allow_redirects=False)
#                 print(feat["properties"]["Id"])
#                 file = session.get(url, verify=False, allow_redirects=True)

#                 with open(
#                     f"{feat['properties']['identifier']}.zip", #location to save zip from copernicus 
#                     "wb",
#                 ) as p:
#                     print(feat["properties"]["Name"])
#                     p.write(file.content)
#             except:
#                 print("problem with server")
# else :
#     print('no data found')

from datetime import date, timedelta
import requests
import pandas as pd
import geopandas as gpd
import os
import json
import geojson
from shapely.geometry import shape, Polygon

def main():
    # Ask for the output path
    output_path = input("Please enter the output path to download files: ")

    # Ask for the type of tiles
    tile_type = input("Please enter the type of tiles (e.g., RGB, NIR): ")

    # # Open and read the JSON file containing the copernicus username and password
    # with open('draft/configSentinel.json', 'r') as file:
    #     config = json.load(file)

    # Access the variables
    username = input('Enter your copernicus eu username:')
    password = input('Enter your copernicus eu password:')

    # Open and read the GeoJSON file
    polygon_path=input('Enter your polygon path (the file must be a .geojson):')
    with open(polygon_path, 'r') as file:
        geojson_data = geojson.load(file)

    # Extract the polygon from the GeoJSON data
    polygon_data = geojson_data['features'][0]['geometry']  # Adjust index if needed
    polygon = shape(polygon_data)

    # Check if it's a polygon
    if isinstance(polygon, Polygon):
        print("The GeoJSON data represents a polygon.")
        print(f"Polygon Coordinates: {polygon}")
    else:
        print("The GeoJSON data does not represent a polygon.")
        return

    copernicus_user = username  # Copernicus User
    copernicus_password = password  # Copernicus Password
    ft = polygon  # WKT Representation of BBOX
    data_collection = "SENTINEL-2"  # Sentinel satellite

    today = date.today()
    today_string = today.strftime("%Y-%m-%d")
    yesterday = today - timedelta(days=3)
    yesterday_string = yesterday.strftime("%Y-%m-%d")

    # Get a token for access
    def get_keycloak(username: str, password: str) -> str:
        data = {
            "client_id": "cdse-public",
            "username": username,
            "password": password,
            "grant_type": "password",
        }
        try:
            r = requests.post(
                "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token",
                data=data,
            )
            r.raise_for_status()
        except Exception as e:
            raise Exception(
                f"Keycloak token creation failed. Response from the server was: {r.json()}"
            )
        return r.json()["access_token"]

    json_ = requests.get(
        f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq '{data_collection}' and OData.CSC.Intersects(area=geography'SRID=4326;{ft}') and ContentDate/Start gt {yesterday_string}T00:00:00.000Z and ContentDate/Start lt {today_string}T00:00:00.000Z&$count=True&$top=1000"
    ).json()
    p = pd.DataFrame.from_dict(json_["value"])  # Fetch available dataset

    if p.shape[0] > 0:
        p["geometry"] = p["GeoFootprint"].apply(shape)
        productDF = gpd.GeoDataFrame(p).set_geometry("geometry")  # Convert PD to GPD
        productDF = productDF[~productDF["Name"].str.contains("L1C")]  # Remove L1C dataset
        print(f"Total L2A tiles found: {len(productDF)}")
        productDF["identifier"] = productDF["Name"].str.split(".").str[0]
        allfeat = len(productDF)

        if allfeat == 0:
            print("No tiles found for today")
        else:
            # Download all tiles from server
            for index, feat in enumerate(productDF.iterfeatures()):
                try:
                    session = requests.Session()
                    keycloak_token = get_keycloak(copernicus_user, copernicus_password)
                    session.headers.update({"Authorization": f"Bearer {keycloak_token}"})
                    url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({feat['properties']['Id']})/$value"
                    response = session.get(url, allow_redirects=False)
                    while response.status_code in (301, 302, 303, 307):
                        url = response.headers["Location"]
                        response = session.get(url, allow_redirects=False)
                    print(feat["properties"]["Id"])
                    file = session.get(url, verify=False, allow_redirects=True)

                    # Save the file to the specified output path
                    file_path = os.path.join(output_path, f"{feat['properties']['identifier']}_{tile_type}.zip")
                    with open(file_path, "wb") as p:
                        print(feat["properties"]["Name"])
                        p.write(file.content)
                except Exception as e:
                    print(f"Problem with server: {e}")
    else:
        print('No data found')

if __name__ == "__main__":
    main()
