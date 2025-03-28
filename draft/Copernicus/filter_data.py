
# import re
# from pathlib import Path
# import concurrent.futures

# def filter_granule_img_data(file_list, res_value, band):
#     """Filter only useful image files from a SAFE .zip archive.

#     Args:
#         file_list (list): List of file paths inside the .zip archive.
#         res_value (int): Resolution value (e.g., 10, 20, 60).
#         band (str): Band name (e.g., B02, B08).

#     Returns:
#         list: Filtered list of file paths matching the pattern.
#     """

#     pattern = re.compile(
#         rf"^.*/GRANULE/.*/IMG_DATA/R{res_value}m/.*_{band}_{res_value}m\.jp2$"
#     )
    
#     return [file for file in file_list if pattern.match(file)]



# import requests
# import re
# from pathlib import Path
# import geopandas as gpd
# import tqdm
# from shapely.geometry import shape
# from keycloak import get_keycloak
# import time
# import requests
# import tqdm
# import geopandas as gpd
# from shapely.geometry import shape
# from keycloak import get_keycloak

# def get_file_list_from_server(p, username, password, node_filter=None):
#     """Recursively retrieve file lists inside Sentinel-2 SAFE products before downloading.
    
#     Args:
#         p (DataFrame): DataFrame containing product metadata.
#         username (str): User login.
#         password (str): User password.
#         node_filter (function, optional): Function to filter useful files.
    
#     Returns:
#         dict: Dictionary with product IDs as keys and lists of file names as values.
#     """
    
#     if p.shape[0] == 0:
#         print("No data found")
#         return {}

#     p["geometry"] = p["GeoFootprint"].apply(shape)
#     productDF = gpd.GeoDataFrame(p).set_geometry("geometry")
#     productDF = productDF[~productDF["Name"].str.contains("L1C")]
#     print(f"Total L2A tiles found: {len(productDF)}")

#     productDF["identifier"] = productDF["Name"].str.split(".").str[0]
#     allfeat = len(productDF)

#     if allfeat == 0:
#         print("No tiles found for today")
#         return {}

#     print(f"{allfeat} datasets found. Fetching file lists...")

#     session = requests.Session()
#     keycloak_token = get_keycloak(username, password)
#     session.headers.update({"Authorization": f"Bearer {keycloak_token}"})

#     file_dict = {}

#     with tqdm.tqdm(total=allfeat, desc="Fetching file lists", unit="product") as pbar:
#         for _, feat in enumerate(productDF.iterfeatures()):
#             try:
#                 product_id = feat["properties"]["Id"]
#                 root_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products({product_id})/Nodes"

#                 print(f"\n🔵 Fetching root directory for {product_id}...\nURL: {root_url}")

#                 # Get the root folder
#                 response = session.get(root_url)

#                 if response.status_code != 200:
#                     print(f"🔴 Error fetching file list for {product_id}: {response.status_code}")
#                     continue

#                 json_response = response.json()
#                 if not json_response.get("result", []):
#                     print(f"⚠️ No nodes found for {product_id}")
#                     continue

#                 # Extract the main SAFE directory node
#                 nodes_uri = json_response["result"][0]["Nodes"]["uri"]
#                 print(f"🟢 Found root Nodes URI: {nodes_uri}")

#                 # Start recursive file search
#                 file_list = []
#                 fetch_files_recursively(session, nodes_uri, file_list)

#                 # Apply filtering if provided
#                 if node_filter:
#                     file_list = node_filter(file_list)

#                 file_dict[product_id] = file_list
#                 print(f"✅ Found {len(file_list)} files for {product_id}")

#                 pbar.update(1)
#                 time.sleep(1)  # Avoid rate limits

#             except Exception as e:
#                 print(f"🔴 Problem with server: {e}")

#     return file_dict

# def fetch_files_recursively(session, node_url, file_list):
#     """Recursively fetch all files inside a Sentinel-2 SAFE product.
    
#     Args:
#         session (requests.Session): Authenticated session.
#         node_url (str): API URL of the current node (folder).
#         file_list (list): List to store collected file paths.
#     """
    
#     response = session.get(node_url)
    
#     if response.status_code != 200:
#         print(f"🔴 Error accessing node: {node_url}")
#         return

#     nodes = response.json().get("value", [])

#     for node in nodes:
#         node_name = node["Name"]
#         node_uri = node["Nodes"]["uri"] if "Nodes" in node else None

#         if node_uri:
#             # This is a folder → Go deeper
#             fetch_files_recursively(session, node_uri, file_list)
#         else:
#             # This is a file → Save it
#             file_list.append(node_name)


import re
import time
import requests
import tqdm
import geopandas as gpd
from pathlib import Path
from shapely.geometry import shape
from keycloak import get_keycloak

def filter_granule_img_data(file_list, res_value, band):
    """Filter only useful image files from a SAFE .zip archive."""
    pattern = re.compile(
        rf"^.*/GRANULE/.*/IMG_DATA/R{res_value}m/.*_{band}_{res_value}m\.jp2$"
    )
    return [file for file in file_list if pattern.match(file)]

def get_file_list_from_server(p, username, password, node_filter=None):
    """Recursively retrieve file lists inside Sentinel-2 SAFE products."""
    if p.shape[0] == 0:
        print("No data found")
        return {}
    
    p["geometry"] = p["GeoFootprint"].apply(shape)
    productDF = gpd.GeoDataFrame(p).set_geometry("geometry")
    productDF = productDF[~productDF["Name"].str.contains("L1C")]
    print(f"Total L2A tiles found: {len(productDF)}")
    
    productDF["identifier"] = productDF["Name"].str.split(".").str[0]
    allfeat = len(productDF)
    if allfeat == 0:
        print("No tiles found for today")
        return {}
    
    print(f"{allfeat} datasets found. Fetching file lists...")
    
    session = requests.Session()
    keycloak_token = get_keycloak(username, password)
    session.headers.update({"Authorization": f"Bearer {keycloak_token}"})
    
    file_dict = {}
    
    with tqdm.tqdm(total=allfeat, desc="Fetching file lists", unit="product") as pbar:
        for _, feat in enumerate(productDF.iterfeatures()):
            try:
                product_id = feat["properties"]["Id"]
                root_url = f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products('{product_id}')/Nodes"
                
                print(f"\n🔵 Fetching root directory for {product_id}...")
                print(f"URL: {root_url}")
                
                response = session.get(root_url)
                print(f"Response Status Code: {response.status_code}")
                print(f"Response Content: {response.text}")
                
                if response.status_code != 200:
                    print(f"🔴 Error fetching file list for {product_id}: {response.status_code}")
                    continue
                
                json_response = response.json()
                
                nodes = json_response.get("value", [])
                if not nodes:
                    print(f"⚠️ No nodes found for {product_id}")
                    continue
                
                file_list = []
                fetch_files_recursively(session, root_url, file_list)
                
                if node_filter:
                    file_list = node_filter(file_list)
                
                file_dict[product_id] = file_list
                print(f"✅ Found {len(file_list)} files for {product_id}")
                pbar.update(1)
                time.sleep(1)  # Avoid rate limits
            
            except Exception as e:
                print(f"🔴 Problem with server: {e}")
    
    return file_dict

def fetch_files_recursively(session, node_url, file_list):
    """Recursively fetch all files inside a Sentinel-2 SAFE product."""
    response = session.get(node_url)
    
    print(f"🔍 Fetching node: {node_url}")
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Content: {response.text}")
    
    if response.status_code != 200:
        print(f"🔴 Error accessing node: {node_url}")
        return
    
    nodes = response.json().get("value", [])
    
    for node in nodes:
        node_name = node.get("Name", "")
        node_uri = node.get("Nodes", {}).get("uri")
        
        if node_uri:
            fetch_files_recursively(session, node_uri, file_list)
        else:
            file_list.append(node_name)
