# This script downloads Sentinel-2 images from:
# - a polygon/zone of interest (shapefile or json)
#- two dates
# - selection of bands?

#we do it with sentinelsat (free), with sentinelhub it is faster but you have to pay
#documentation: https://sentinelsat.readthedocs.io/en/stable/api_overview.html 

from sentinelsat import SentinelAPI, geojson_to_wkt 
import geopandas as gpd

## Define API for Copernicus Open Access Hub
USERNAME = "moea.geffardlemaitre@gmail.com" #email adress
PASSWORD = "Des1gn_project"
api = SentinelAPI(USERNAME, PASSWORD, "https://apihub.copernicus.eu/apihub")

## Load Area Of Interest (AOI)

# Draw the polygon on geojson.io or QGIS, or download it with Opendataswisstopo

# Load AOI from a geojson file
path="./draft/polygon/polygon.geojson" #your path to the geojson file
aoi = gpd.read_file(path)
aoi_wkt = geojson_to_wkt(aoi.__geo_interface__)

## Define search parameters
date_begin="20240101"
date_end="20240101"

products = api.query(area=aoi_wkt, date=(date_begin, date_end),platformname="Sentinel-2",cloudcoverpercentage=(0, 30))

## Download images
api.download_all(products)

