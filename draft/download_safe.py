from datetime import date, timedelta
import requests
import geopandas as gpd
import os
import json
from shapely.geometry import shape, Polygon
import tqdm

from keycloak import get_keycloak

def download_all_safe(p, username: str, password :str, output_path : str):
    """ Download all the safe files in the output file given the list p (complex)
    Input:
    - p: dictionnary
    - username: str
    - password: str
    - output_path : str
    
    Return:
    Just download"""
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
            print(allfeat, " datasets were found. Please wait for download...")

            with tqdm.tqdm(total=allfeat, desc="Downloading", unit="file") as pbar:
                for index,feat in enumerate(productDF.iterfeatures()):
                    try:
                        session = requests.Session()
                        keycloak_token = get_keycloak(username,password)
                        session.headers.update({"Authorization": f"Bearer {keycloak_token}"})
                        url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({feat['properties']['Id']})/$value"
                        response = session.get(url, allow_redirects=False)
                        while response.status_code in (301, 302, 303, 307):
                            url = response.headers["Location"]
                            response = session.get(url, allow_redirects=False)
                        print(feat["properties"]["Id"])
                        file = session.get(url, verify=False, allow_redirects=True)

                        with open(
                            f"{output_path}/{feat['properties']['identifier']}.zip", #location to save zip from copernicus 
                            "wb",
                        ) as p:
                            print(feat["properties"]["Name"])
                            p.write(file.content)
                        pbar.update(1)
                        print("path : ",f"{output_path}/{feat['properties']['identifier']}")
                    except:
                        print("problem with server")
    else :
        print('no data found')