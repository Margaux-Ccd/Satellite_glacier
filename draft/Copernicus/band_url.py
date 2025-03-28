import requests
from urllib.parse import urljoin
from keycloak import get_keycloak


def get_band_url(username, password, prod_id, band_index=3, resolution="10m"):
    # Authenticate and set up session
    api_session = requests.Session()
    keycloak_token = get_keycloak(username, password)
    api_session.headers.update({"Authorization": f"Bearer {keycloak_token}"})
    
    api_url = "https://catalogue.dataspace.copernicus.eu/odata/v1/"
    
    # Get product name
    nodes = api_session.get(urljoin(api_url, f"Products('{prod_id}')/Nodes?$format=json"), verify=False).json()
    prod_name = nodes["d"]["results"][0]["Id"]
    
    # Get granule ID
    granules = api_session.get(urljoin(api_url, f"Products('{prod_id}')/Nodes('{prod_name}')/Nodes('GRANULE')/Nodes?$format=json")).json()
    gran_id = granules["d"]["results"][0]["Id"]
    
    # Get contents of IMG_DATA directory
    img_data_url = urljoin(api_url, f"Products('{prod_id}')/Nodes('{prod_name}')/Nodes('GRANULE')/Nodes('{gran_id}')/Nodes('IMG_DATA')/Nodes?$format=json")
    img_data = api_session.get(img_data_url).json()
    
    # Check for resolution folders (e.g., R10m, R20m, R60m)
    resolution_folder = None
    for item in img_data["d"]["results"]:
        if item["Id"].startswith(f"R{resolution}m"):
            resolution_folder = item["Id"]
            break
    
    # If resolution folder exists, update img_data_url
    if resolution_folder:
        img_data_url = urljoin(api_url, f"Products('{prod_id}')/Nodes('{prod_name}')/Nodes('GRANULE')/Nodes('{gran_id}')/Nodes('IMG_DATA')/Nodes('{resolution_folder}')/Nodes?$format=json")
        img_data = api_session.get(img_data_url).json()
    
    # Get band ID (assuming band_index corresponds correctly)
    band_id = img_data["d"]["results"][band_index]["Id"]
    
    # Construct final image URL
    img_url = urljoin(api_url, f"Products('{prod_id}')/Nodes('{prod_name}')/Nodes('GRANULE')/Nodes('{gran_id}')/Nodes('IMG_DATA')/Nodes('{resolution_folder}')/Nodes('{band_id}')/$value")
    
    return img_url





