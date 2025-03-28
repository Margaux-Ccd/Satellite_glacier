# # This script downloads Sentinel-2 images from:
# # - a polygon/zone of interest (shapefile or json)
# #- two dates
# # - selection of bands?

# #we do it with sentinelsat (free), with sentinelhub it is faster but you have to pay
# #documentation: https://sentinelsat.readthedocs.io/en/stable/api_overview.html 

# from sentinelsat import SentinelAPI, geojson_to_wkt 
# import geopandas as gpd

# ## Define API for Copernicus Open Access Hub
# USERNAME = "moea.geffardlemaitre@gmail.com" #email adress
# PASSWORD = "Des1gn_project"
# api = SentinelAPI(USERNAME, PASSWORD, "https://scihub.copernicus.eu/dhus")

# ## Load Area Of Interest (AOI)

# # Draw the polygon on geojson.io or QGIS, or download it with Opendataswisstopo

# # Load AOI from a geojson file
# path="./draft/polygon/polygon.geojson" #your path to the geojson file
# aoi = gpd.read_file(path)
# aoi_wkt = geojson_to_wkt(aoi.__geo_interface__)

# ## Define search parameters
# date_begin="20240101"
# date_end="20240101"

# products = api.query(area=aoi_wkt, date=(date_begin, date_end),platformname="Sentinel-2",cloudcoverpercentage=(0, 30))

# ## Download images
# api.download_all(products)

# Download SENTINEL-2 data over a period of time for specific points.
# Contact person: Amir H. Nikfal <a.nikfal@fz-juelich.de>

import csv
import os
import logging
import json as jsonmod
from glob import glob
import json
import user_inputs as inp


# Load credentials
with open('draft/configSentinel.json', 'r') as file:
    config = json.load(file)

username = config['username']
password = config['password']
try:
    import requests
except ImportError:
    print("Error: module <requests> is not installed. Install it and run again.")
    exit()

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

start_date = f"{inp.start_year}-{format(inp.start_month, '02d')}-{format(inp.start_day, '02d')}T{format(inp.start_hour, '02d')}:00:00.000Z"
end_date = f"{inp.end_year}-{format(inp.end_month, '02d')}-{format(inp.end_day, '02d')}T{format(inp.end_hour, '02d')}:00:00.000Z"
data_collection = "SENTINEL-2"
safe_start_date = start_date.replace(":", "-").replace("T", "_").replace("Z", "")
logging.basicConfig(filename=f"log_sentinel_download_{safe_start_date}.log",
                    filemode='a',
                    format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                    level=logging.INFO)


csvfile = open("draft/points_coordinates.csv", newline='')
all_points = csv.DictReader(csvfile)
keycloak_token = get_keycloak(username, password)

foundtiles_dict = dict()
count = 2
for point in all_points:
        logging.info("Row: " + str(count))
        if (count+4)%5 == 0:
            keycloak_token = get_keycloak(username, password)
        aoi = "POINT(" + point['LONG'] + " " + point['LAT'] + ")'"
        print("Looking for data over the point:", point)
        json = requests.get(f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq '{data_collection}' \
                            and OData.CSC.Intersects(area=geography'SRID=4326;{aoi}) and ContentDate/Start gt {start_date} \
                                and ContentDate/Start lt {end_date}").json()
        session = requests.Session()
        session.headers.update({'Authorization': f'Bearer {keycloak_token}'})
        lookedup_tiles = json['value']
        for var in lookedup_tiles:
            try:
                if "MSIL2A" in var['Name']:
                    logging.info("Row found: " + str(count))
                    myfilename = var['Name']
                    logging.info("File OK: " + myfilename)
                    mytile = myfilename.split("_")[-2]
                    foundtiles_dict[mytile] = [point['LONG'], point['LAT']]
                    url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products(" + var['Id'] + ")/$value"
                    response = session.get(url, allow_redirects=False)
                    while response.status_code in (301, 302, 303, 307):
                        logging.info("response: " + str(response.status_code))
                        url = response.headers['Location']
                        logging.info("next line ...")
                        response = session.get(url, allow_redirects=False)
                        logging.info("Last line ...")
                    file = session.get(url, verify=False, allow_redirects=True)
                    with open(f""+var['Name']+".zip", 'wb') as p:
                        p.write(file.content)
            except:
                pass
        count = count + 1

###############################################################################
# Verifying downloaded files
###############################################################################

keycloak_token = get_keycloak(username, password)
with open('list_downloaded_files.txt', 'w') as file:
   file.write(jsonmod.dumps(foundtiles_dict))

filelist=glob("S2*.SAFE.zip")
corrupted = []
for var in filelist:
   if int(os.path.getsize(var)/1024) < 10:
      corrupted.append(var)

count = 2
for point in corrupted:
        logging.info("Currpted Row: " + str(count))
        tile_retry = point.split("_")[-2]
        if (count+3)%4 == 0:
            keycloak_token = get_keycloak(username, password)
        mylong = foundtiles_dict[tile_retry][0]
        mylat = foundtiles_dict[tile_retry][1]
        aoi = "POINT(" + mylong + " " + mylat + ")'"
        print("Retrying to get the point:", mylong, mylat)
        json = requests.get(f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq '{data_collection}' \
                            and OData.CSC.Intersects(area=geography'SRID=4326;{aoi}) and ContentDate/Start gt {start_date} \
                                and ContentDate/Start lt {end_date}").json()
        session = requests.Session()
        session.headers.update({'Authorization': f'Bearer {keycloak_token}'})
        lookedup_tiles = json['value']
        for var in lookedup_tiles:
            try:
                if "MSIL2A" in var['Name']:
                    logging.info("Currpted Row found: " + str(count))
                    myfilename = var['Name']
                    logging.info("Currpted File OK: " + myfilename)
                    url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products(" + var['Id'] + ")/$value"
                    response = session.get(url, allow_redirects=False)
                    while response.status_code in (301, 302, 303, 307):
                        logging.info("Currpted response: " + str(response.status_code))
                        url = response.headers['Location']
                        logging.info("Currpted next line ...")
                        response = session.get(url, allow_redirects=False)
                        logging.info("Currpted Last line ...")
                    file = session.get(url, verify=False, allow_redirects=True)
                    with open(f""+var['Name']+".zip", 'wb') as p:
                        p.write(file.content)
            except:
                pass
        count = count + 1