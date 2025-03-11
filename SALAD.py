#!/usr/bin/env python
# Description: SALAD.py:
# This script has three main parts
# 1) It downloads Sentinel-2 images and creates composit images
# 2) Uploads the composit images to the Picterra platform (machine learning)
# 3) Makes an analysis and report of the glacier lakes found on each glacier for each S2 image.
#
#__author__      = Saskia Gindraux
#__date_creation__   = 2019-2020
#__last_modification__ = 20.01.2021
# Inspired from https://gist.github.com/akatasonov/cb682ff5a064e7b3cbd4223c8fbcaeeb for downloading the S2 data

# Import libraries
from sentinelsat import SentinelAPI, read_geojson, geojson_to_wkt
import datetime
from datetime import date
from rasterio.mask import mask
from matplotlib.ticker import FormatStrFormatter
import rasterio.merge
from rasterio.warp import calculate_default_transform, reproject, Resampling
from rasterio.plot import reshape_as_raster  #, reshape_as_image
from shapely.geometry import Point as PPoint
from shapely.geometry import mapping, shape, Polygon, MultiPolygon  # Point class, shape() is a function to convert geo objects through the interface
import skimage
from skimage import exposure
import warnings
from zipfile import ZipFile
import cv2
from area import area
import shapefile
import matplotlib.pyplot as plt
import matplotlib as mpl
import fiona
import numpy as np
from picterra import APIClient
import os
import geojson
from geojson import Point  #, Feature, FeatureCollection, dump
from descartes import PolygonPatch
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.lib.units import mm
import xml.etree.ElementTree as ET
import rasterio
# from matplotlib import patheffects
# import time
# import requests
# import subprocess
# import shapely
# import shapely.geometry
# import shapely.ops
# import folium
# import json
# import pandas as pd
# import geopandas as gpd
# from rasterio import windows
# import cartopy.crs as ccrs

##--- Set paths
# for S2 data
s2_data_path = "X:\\02_GIS\\400_Sentinel\\A50004_schmeltzsaison_2021"  # where the S2 datasets are stored
api = SentinelAPI('sasgin_geoformer', 'gIn17sas', 'https://scihub.copernicus.eu/dhus')
json_aoi = "Y:\\A_Naturgefahren\\A5_Gletscher\\A50004_GefGletscher_VS\\GIS\\GIS_SALAD\\valais_aoi.geojson"  # area of interest (Wallis polygon)
shp_bbox = "Y:\\A_Naturgefahren\\A5_Gletscher\\A50004_GefGletscher_VS\\GIS\\GIS_SALAD\\GrenzKt_VS_wgs84_bbox.shp"  # box (4 points) that defines the corners of Wallis in world coordinates
# for Picterra
detection_areas_json = "Y:\\A_Naturgefahren\\A5_Gletscher\\A50004_GefGletscher_VS\\GIS\\GIS_SALAD\\glaciers_s2_2015_VS_wgs84_fix.geojson"  # glacier outlines (2015) in world coordinates
# for report
result_path = "Y:\\A_Naturgefahren\\A5_Gletscher\\A50004_GefGletscher_VS\\Fernerkundung\\reports_glacier_lakes_2021"  # where you want the results stored
slope_raster = "Y:\\A_Naturgefahren\\A5_Gletscher\\A50004_GefGletscher_VS\\GIS\\GIS_SALAD\\slope_VS_2m_wgs84.tif"  # slope raster in world coordinates
shp_sgi = "Y:\\A_Naturgefahren\\A5_Gletscher\\A50004_GefGletscher_VS\\GIS\\GIS_SALAD\\glaciers_s2_2015_VS_wgs84_fix.shp"
glacier_index = ["Feegletscher", "Fieschergletscher", "Glacier de l'A Neuve", "Glacier du Dolent", "Glacier du Trient", "Hohbärggletscher", "Nestgletscher", "Festigletscher", "Triftgletscher/Weissmies", "Aletschgletscher", "Fletschhorngletscher", "Mälligagletscher", "Riedgletscher", "Triftgletscher", "Bidergletscher", "Mellichgletscher", "Alphubelgletscher", "Öigschtchummugletscher", "Glacier de Ferpècle", "Glacier du Mont Miné", "Weisshorngletscher", "Bisgletscher", "Dirrugletscher", "Allalingletscher", "Chessjengletscher", "Zmuttgletscher", "Hohwänggletscher", "Glacier de Tsijiore Nouve", "Rottalgletscher", "Rotblattgletscher", "Triftjigletscher", "Glacier du Giétro", "Kingletscher", "Bas glacier d'Arolla", "Glacier de Saleina"]  # list of the "dangerous" glaciers (RisikoIndex > 10)
# glacier_index_2019 = ["Feegletscher", "Fieschergletscher", "Glacier de l'A Neuve", "Glacier du Dolent", "Glacier du Trient", "Hohbärggletscher", "Nestgletscher", "Festigletscher", "Triftgletscher/Weissmies", "Aletschgletscher", "Fletschhorngletscher", "Mälligagletscher", "Riedgletscher", "Triftgletscher", "Bidergletscher", "Mellichgletscher", "Alphubelgletscher", "Öigschtchummugletscher", "Glacier de Ferpècle", "Glacier du Mont Miné", "Weisshorngletscher", "Bisgletscher", "Dirrugletscher", "Stampbachgletscher", "Allalingletscher", "Chessjengletscher", "Zmuttgletscher", "Hohwänggletscher", "Glacier de Tsijiore Nouve", "Rottalgletscher", "Rotblattgletscher", "Triftjigletscher", "Glacier du Giétro", "Kingletscher", "Birchgletscher", "Bas glacier d'Arolla", "Glacier de Saleina"]  # list of the "dangerous" glaciers (RisikoIndex > 10)
# summary_table_tot = "C:\\A50018_glacier_lakes\\results_code\\reports_glacier_lakes\\season_report\\summary_table_tot.txt"

# Definitions
def normalize(array):
    array_min, array_max = array.min(), array.max()
    return (array - array_min) / (array_max - array_min)

def unsharp_mask(image, kernel_size=(5, 5), sigma=1.0, amount=1.0, threshold=0):
    """Return a sharpened version of the image, using an unsharp mask.
    amount is simply the amount of sharpening. For example, an amount of 2.0 gives
    a sharper image compared to the default value of 1.0. threshold is the threshold
    for the low-contrast mask. In other words, the pixels for which the difference
    between the input and blurred images is less than threshold will remain unchanged."""
    blurred = cv2.GaussianBlur(image, kernel_size, sigma)
    sharpened = float(amount + 1) * image - float(amount) * blurred
    sharpened = np.maximum(sharpened, np.zeros(sharpened.shape))
    sharpened = np.minimum(sharpened, 255 * np.ones(sharpened.shape))
    sharpened = sharpened.round().astype(np.uint8)
    if threshold > 0:
        low_contrast_mask = np.absolute(image - blurred) < threshold
        np.copyto(sharpened, image, where=low_contrast_mask)
    return sharpened


### START SCRIPT ###
print("*** Start script ***")

## Create folder for report
dt = datetime.datetime.today()
report_date_str = str(dt.year) + str(dt.month).zfill(2) + str(dt.day).zfill(2)
report_folder = result_path + "\\" + report_date_str + "_report"
if not os.path.exists(report_folder):
    os.makedirs(report_folder)

##--- Download Sentinel 2 data

## search by polygon, time, and SciHub query keywords
footprint = geojson_to_wkt(read_geojson(json_aoi))

# find the date of the last sentinel image
list_file_wehave = [p for p in os.listdir(s2_data_path) if p.endswith('.zip')]
list_file_wehave.sort()
last_satfile = list_file_wehave[-1].split('_')[2][0:8]

products = api.query(footprint,
                     date=('20210520', date(2021, 5, 27)),  # !!! last day excluded!!! for automatisation: last_satfile, date.today()
                     platformname='Sentinel-2',
                     cloudcoverpercentage=(0, 100),  # we take all datasets because otherwise it makes holes in the images. It is possible that a lake is visible through cloud by chance!
                     processinglevel='Level-2A')

# select the tiles we want
tiles = ['32TLS', '32TMS', '32TLR']
idx_products = []
list_tiem = list(products.items())
for i in range(len(list_tiem)):
    p, v = list_tiem[i]
    title = v['title']
    for tile in tiles:
        if tile in title:
            idx_products.append(p)

products2 = products.copy()
for k, v in list(products2.items()):
    if k not in idx_products:
        del products2[k]


# download all results from the search
print(len(products2), " datasets were found. Please wait for download...")
api.download_all(products2)  # , directory_path=s2_data_path doesn't work anymore??? TODO: fix later and remove shutil part below ***

api.to_geodataframe(products2)

##--- Unzip product
print("S2 data downloaded. Unzipping data...")
#*** remove
S2_zip_list = [os.path.abspath(os.path.join("C:\\Users\\sasgin.BRIG\\PycharmProjects\\glacier_lakes", p)) for p in os.listdir("C:\\Users\\sasgin.BRIG\\PycharmProjects\\glacier_lakes") if p.endswith('.zip')]
import shutil
for f in S2_zip_list:
    shutil.move(f, s2_data_path)
#*** remove

S2_zip_list = [os.path.abspath(os.path.join(s2_data_path, p)) for p in os.listdir(s2_data_path) if p.endswith('.zip')]

# get list of today's S2 downloaded datasets
S2_zip_list_today = []
for f in S2_zip_list:
    modified = os.path.getmtime(f)
    date_modified = datetime.datetime.fromtimestamp(modified)
    if date_modified.year == dt.year and date_modified.month == dt.month and date_modified.day == dt.day:
        S2_zip_list_today.append(f)
S2_zip_list_today.sort()

for i in S2_zip_list_today:
    thefile = ZipFile(i, 'r')
    thefile.extractall(s2_data_path)
    thefile.close()

##--- Compose IRG images
print("Unzipping data terminated. Preparing composite images...")
list_safe_abs = [os.path.abspath(os.path.join(s2_data_path, p)) for p in os.listdir(s2_data_path) if p.endswith('.SAFE')]

list_safe_abs_today = []
list_safe_today = []
for f in list_safe_abs:
    modified = os.path.getmtime(f)
    date_modified = datetime.datetime.fromtimestamp(modified)
    # if date_modified.year == dt.year and date_modified.month == dt.month and date_modified.day == 7:
    if date_modified.year == dt.year and date_modified.month == dt.month and date_modified.day == dt.day:
        list_safe_abs_today.append(f)
        list_safe_today.append(f.split("\\")[-1])

if list_safe_today == []:
    warnings.warn("The list_safe_today is empty!!")

# group .SAFE files per date
product_groups = {}
for product_fn in list_safe_today:
    product_attrs = product_fn.split('_')  # Split the product name into parts
    datatake_time = product_attrs[2]
    tile_number = product_attrs[5]

    # since the aoi provided covers several tiles, group tiles by datatake_time
    if datatake_time in product_groups:
        product_groups[datatake_time].append(product_fn)
    else:
        product_groups[datatake_time] = [product_fn]

# sort the dict in the chronological order
product_groups = dict(sorted(product_groups.items()))
print("There is in total of", len(product_groups), "S2 dataset for this report.")

count = 0
for product_group in product_groups:
    print('Processing ', count+1, '/', len(product_groups), ': {}   '.format(product_group))
    b3 = []  # all B4 bands for a group, green
    b4 = []  # all B4 bands for a group, red
    b8 = []  # all B8 bands for a group
    for product_fn in product_groups[product_group]:
        b3fn = ''
        b4fn = ''
        b8fn = ''
        safe_abs_path = [s for s in list_safe_abs if product_fn in s]
        pathtoR10 = safe_abs_path[0] + "\\GRANULE\\" + os.listdir(safe_abs_path[0] + "\\GRANULE")[0] + "\\IMG_DATA\\R10m"
        for bandfn in os.listdir(pathtoR10):
            if 'B03' in bandfn:
                b3fn = bandfn
            if 'B04' in bandfn:
                b4fn = bandfn
            if 'B08' in bandfn:
                b8fn = bandfn

        b3.append(rasterio.open(pathtoR10 + "\\" + b3fn))
        b4.append(rasterio.open(pathtoR10 + "\\" + b4fn))
        b8.append(rasterio.open(pathtoR10 + "\\" + b8fn))
    count = count + 1

    # for a group of tiles/products, merge bands from different tiles together
    green, _ = rasterio.merge.merge(b3)
    red, out_trans = rasterio.merge.merge(b4)
    nir, _ = rasterio.merge.merge(b8)

    # for rgb
    # blue2 = normalize(blue*4.85)
    # green2 = normalize(green*5.10)
    # red2 = normalize(red*5.05)

    # for false-color infrared
    red2 = normalize(red * 5.15)
    green2 = normalize(green * 5.15)
    nir2 = normalize(nir * 5.5)

    red3 = (red2*255).astype('uint8')
    green3 = (green2*255).astype('uint8')
    nir3 = (nir2*255).astype('uint8')

    # sharpen image
    green4 = unsharp_mask((np.squeeze(green3, axis=0)))
    red4 = unsharp_mask((np.squeeze(red3, axis=0)))
    nir4 = unsharp_mask((np.squeeze(nir3, axis=0)))

    # stack bands
    bandstack_infra = np.stack((nir4, red4, green4), axis=0)

    # # adjust contrast
    # bandstack_infra_adjusted = cv2.convertScaleAbs(bandstack_infra, alpha=2, beta=0)

    # adjust constrast
    cutoff = 0.15; gain = 12  # cutoff = 0.15, gain = 12 for infra
    bandstack_infra_adjusted = skimage.exposure.adjust_sigmoid(bandstack_infra, cutoff=cutoff, gain=gain, inv=False)

    # create composite .tif
    meta = b4[0].meta.copy()
    meta.update(dtype='uint8', driver='GTiff', transform=out_trans, height=red.shape[1], width=red.shape[2], count=3)  # , count=4, , dtype='uint8', dtype=rasterio.float64
    with rasterio.open(report_folder + "\\" + "infra_{}.tif".format(product_group), 'w', **meta) as dst:
        dst.write(bandstack_infra_adjusted)  # numpy array needs to be in bands, rows, cols order (z, y, x)!
        dst.close()

    # change crs
    dst_crs = 'EPSG:4326'
    with rasterio.open(report_folder + "\\" + "infra_{}.tif".format(product_group)) as src:
        transform, width, height = calculate_default_transform(src.crs, dst_crs, src.width, src.height, *src.bounds)
        kwargs = src.meta.copy()
        kwargs.update({'crs': dst_crs, 'transform': transform, 'width': width, 'height': height})

        with rasterio.open(report_folder + "\\" + "infra_{}_wgs.tif".format(product_group), 'w', **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=dst_crs,
                    resampling=Resampling.nearest)

    # crop on Valais
    with fiona.open(shp_bbox, "r") as shpfile:
        shapes = [feature["geometry"] for feature in shpfile]
    shpfile.close()

    with rasterio.open(report_folder + "\\" + "infra_{}_wgs.tif".format(product_group)) as src:
        out_image, out_transform = rasterio.mask.mask(src, shapes, crop=True)
        out_meta = src.meta
    out_meta.update({"driver": "GTiff", "height": out_image.shape[1], "width": out_image.shape[2], "transform": out_transform})

    with rasterio.open(report_folder + "\\" + "infra_{}_wgs_crop.tif".format(product_group), "w", **out_meta) as dest:
        dest.write(out_image)
        dest.close()

print("All composite images were created. See data here: ", report_folder)

#####------------------

##--- Upload S2 images to Picterra
print('Uploading S2 images to Picterra platform...')

# log-in
api_key = "14acb66bcfcad19901afd01dbc9060108e9673e07badaa6222e6dad3bf4d184d"
client = APIClient(api_key=api_key)
server_url = "https://app.picterra.ch/public/api/v1"
headers = {'X-Api-Key': api_key}
folder_id = "5531a7af-c863-4d8c-8bbe-96337a05dcac"

detection_data_paths = [os.path.abspath(os.path.join(report_folder, p)) for p in os.listdir(report_folder)if p.endswith("wgs_crop.tif")]
detection_data_names = [p[:-4] for p in os.listdir(report_folder) if p.endswith("wgs_crop.tif")]

raster_id_list = []
for i, j in zip(detection_data_paths, detection_data_names):
    raster_id = client.upload_raster(i, name=j, folder_id=folder_id)  # upload raster
    raster_id_list.append(raster_id)

print('Upload finished. Start detection...')
detector_id = '8fbf3b87-3df4-48a0-9ed7-f5debb0ac65f'  # detector alpine_lakes copy: 108246e9-115b-4e37-bc06-156a65fa3668

with open(detection_areas_json, 'rb') as f:  # Open geojson file
    areas_json = f.read()

for i in range(0, len(raster_id_list)):
    # print("Detection ", i+1, "/", len(raster_id_list))
    # # get url and id of the uploaded rasters
    # url = '%s/rasters/%s/detection_areas/upload/file/' % (server_url, raster_id_list[i])
    # r = requests.post(url, headers=headers)  # get upload URL
    # assert r.status_code == 201
    #
    # response = r.json()
    # upload_url = response["upload_url"]
    # upload_id = response["upload_id"]

    # set detection area based on geojson (glacier outlines with buffer)
    client.set_raster_detection_areas_from_file(raster_id_list[i], detection_areas_json)

    #
    # r = requests.put(upload_url, data=areas_json)  # Upload GeoJSON
    # url = '%s/rasters/%s/detection_areas/upload/%s/commit/' % (server_url, raster_id_list[i], upload_id)
    # r = requests.post(url, headers=headers)  # commit detection area upload
    # poll_interval = r.json()["poll_interval"]
    # url = '%s/rasters/%s/detection_areas/upload/%s/' % (server_url, raster_id_list[i], upload_id)
    # timeout = time.time() + (30 * 60)  # 15 minutes timeout for polling
    # while True:  # Check upload commit status
    #     time.sleep(poll_interval)
    #     r = requests.get(url, headers=headers)
    #     if r.json()["status"] in ("ready", "failed"):
    #         break
    #     if time.time() > timeout:
    #         break
    # assert r.json()["status"] == "ready", "Error committing detection area"

    # run detector
    result_id = client.run_detector(detector_id, raster_id_list[i])
    # download results
    client.download_result_to_file(result_id, report_folder + "\\" + detection_data_names[i][:-8] + "picterra.geojson")



    # url = "%s/detectors/%s/run/" % (server_url, detector_id)
    # data = {'raster_id': raster_id_list[i]}
    # r = requests.post(url, headers=headers, data=data)  # Start detection
    # assert r.status_code == 201, "Error starting detection"
    # # check outcome
    # response = r.json()
    # result_id = response["result_id"]
    # poll_interval = response["poll_interval"]
    # url = "%s/results/%s/" % (server_url, result_id)
    # timeout = time.time() + (30 * 60)  # 30 minutes timeout for polling
    # download_url = None
    # while True:  # check detection status
    #     time.sleep(poll_interval)
    #     r = requests.get(url, headers=headers)
    #     assert r.status_code == 200, "Error detailing detection result"
    #     if r.json()["ready"]:
    #         download_url = r.json()["result_url"]
    #         break
    #     if time.time() > timeout:
    #         break
    # assert download_url is not None, "Prediction exceeded timeout"
    #
    # # download results
    # client.download_result_to_file(result_id, report_folder + "\\" + detection_data_names[i][:-8] + "picterra.geojson")
    # # TODO: probably better to delete the uploaded images straight afterwards (and not manually on the platform)
    # # for raster in client.list_rasters(folder_id):
    # #     pprint('raster %s' % "\n".join(["%s=%s" % item for item in raster.items()]))
    # #
    # # client.delete_raster(raster_id)
    # # print('Deleted raster=', raster_id)
print("Picterra successful. See results here: ", report_folder)

# TODO: Sometimes, the loop over the datasets has a bug. The error messages are listed below. See if that occurs often, when and why.
# urllib3.exceptions.ProtocolError: ('Connection aborted.', OSError("(10054, 'WSAECONNRESET')"))
# requests.exceptions.ConnectionError: ('Connection aborted.', OSError("(10054, 'WSAECONNRESET')"))

#####------------------

##--- Analyse data
print("Data analysis...")

# get list of results from picterra
picterra_list = [os.path.abspath(os.path.join(report_folder, p)) for p in os.listdir(report_folder) if p.endswith(".geojson")]

# Loop of the different S2 datasets dates
summary_table = np.zeros(shape=(len(picterra_list), 6))  # cols = date, tot_nbr_lakes, lakes_index, lakes_nonindex, cloud_percent, half_valais
for i in range(0, len(picterra_list)):  # loop over the number of .geojson files given by picterra (1 per satellite image date)
    result = picterra_list[i]
    with open(result) as f:  # open geojson file
        data = geojson.load(f)

    date_dataset = result.split('\\')[-1][6:14]  # change here if file name changes
    summary_table[i, 0] = date_dataset

    # collect metadata (cloud cover and tile name) from .SAFE files
    list_cloudcover = []
    list_tiles = []
    safe_paths = [os.path.abspath(os.path.join(s2_data_path, p)) for p in os.listdir(s2_data_path) if date_dataset in p and p.endswith(".SAFE")]  # get all products for that date
    for safe_path in safe_paths:
        xml_path = [os.path.abspath(os.path.join(safe_path, p)) for p in os.listdir(safe_path) if p.endswith('L2A.xml')]
        if len(xml_path) == 0: # empty list means no metadata
            print("There is no metadata .xml file in the .SAFE folder: ", safe_path)
        tree = ET.parse(xml_path[0])
        root = tree.getroot()
        quality_indicator = root[3]
        cloud_cover = quality_indicator.find("Cloud_Coverage_Assessment").text
        list_cloudcover.append(cloud_cover)

        tile_name = safe_path.split("_")[-2][-3:]
        list_tiles.append(tile_name)

    summary_table[i, 4] = np.mean([float(j) for j in list_cloudcover])

    if "TLS" not in list_tiles:  # means that unterwallis is not represented
        half_valais = 1  # 1 for true, 0 for false
    else:
        half_valais = 0
    summary_table[i, 5] = half_valais

    # filter inaccurate lakes and calculate the center of each picterra polygon and its surface
    poly_area = []
    lake_polygons = []
    lake_bbox = []
    lake_poly_shapely = []
    lake_center_coor = []
    lake_center_xcoor_list = []
    lake_center_ycoor_list = []
    for Polygones in data['coordinates']:
        # Polygones = polygones['geometry']['coordinates']  # line for geojson downloaded from platform manually
        obj = {'type': 'Polygon', 'coordinates': Polygones}
        # print(obj)

        # filter lakes with slope raster before saving to arrays and lists
        with rasterio.open(slope_raster) as src:
            out_image, out_transform =rasterio.mask.mask(src, [obj], crop=True)  # all_touched=False, invert=False, nodata=None, filled=True,, nodata=-3.4028231e+38

        out_image[out_image < 0] = np.nan  # takes out the -3.4028231e+38 (no data values) which doesn't work above
        mean_slope = np.nanmedian(out_image)
        # print(mean_slope)

        if mean_slope > 0 and mean_slope < 20 and area(obj) > 200.0:  # if mean slope within the lake area is lower than x° we take the polygon. Otherwise it is discarded.

            lake_polygons.append(obj)
            poly_area.append(area(obj))  # in m2 --> checked 05.06.2020 that's correct
            lake_poly_shapely.append(Polygon(Polygones[0]))
            x_list = []; y_list = []
            for ply in range(len(Polygones[0])):
                x_list.append(Polygones[0][ply][0])
                y_list.append(Polygones[0][ply][1])

            # get polygon centers
            maxx = max(x_list); minx = min(x_list); maxy = max(y_list); miny = min(y_list)  # bbox
            lake_bbox.append([minx, maxx, miny, maxy])
            lake_center_coor.append(((minx + maxx) / 2, (miny + maxy) / 2))  # tuple (x, y)
            lake_center_xcoor_list.append((minx + maxx) / 2)
            lake_center_ycoor_list.append((miny + maxy) / 2)

    ## find the corresponding glacier for each glacier lake (polygon)
    multi_gl_outlines = MultiPolygon([shape(pol['geometry']) for pol in fiona.open(shp_sgi)])  # load shapefile glacier inventory
    polygons_gl_outlines = list(multi_gl_outlines)  # shapely Polygon object

    gl_lakes_names = []
    shp = shapefile.Reader(shp_sgi)  # open the shapefile
    all_glaciers = shp.shapes()  # get all the polygons (another type of object as shapely Polygon)
    all_records = shp.records()  # rec = sf.record(2); rec['SGI']
    Gl_names = np.array(all_records)[:, 24]  # array of strings
    unknown_idx = np.where(Gl_names == "")
    Gl_names[unknown_idx] = "unknown"

    ## create all glacier .txt file (unique run)
    Gl_names_unique = list(set(list(Gl_names)))
    Gl_names_unique_modif = [x.replace("'", "").replace("/", "").replace(" ", "") for x in Gl_names_unique]
    # for i, j in zip(Gl_names_unique, Gl_names_unique_modif):
    #     with open("C:\\A50018_glacier_lakes\\results_code\\reports_glacier_lakes_supraonly\\" + j + ".txt", "w") as myfile:
    #             myfile.writelines(i)

    # loop over each detected lake to assign it a glacier name
    for lake in lake_center_coor:
        count = 0
        for glacier in range(0, len(all_glaciers)):
            boundary = all_glaciers[glacier]  # get a boundary polygon
            if PPoint(lake).within(shape(boundary)):
                # if lake in glacier outline, assign glacier name
                gl_lakes_names.append(Gl_names[glacier])
                count = 1
        if count == 0:  # if lake is not in any glacier outline, find the closest glacier
            min_poly = min(polygons_gl_outlines, key=PPoint(lake).distance)
            index = polygons_gl_outlines.index(min_poly)
            gl_lakes_names.append(Gl_names[index])  # if lake is in proglacial area

    # create new geojson file with point coordinates of lakes and lake names (for Rachel)

    # write a new point shapefile as point feature geometry with one attribute
    schema = {'geometry': 'Point', 'properties': {'id': 'str'}, }
    with fiona.open(report_folder + "\\" + result.split("\\")[-1][0:-8] + "_pts.shp", "w", 'ESRI Shapefile', schema) as c:
        for pts in range(len(lake_center_coor)):
            point = Point(lake_center_coor[pts])
            c.write({'geometry': mapping(point), 'properties': {'id': gl_lakes_names[pts]}, })

    # write a new polygon shapefile enhancing the picterra geojson result
    schema = {'geometry': 'Polygon', 'properties': {'ID': 'str', 'AREA': 'float:16'}, }
    with fiona.open(report_folder + "\\" + result.split("\\")[-1][0:-8] + "_poly.shp", "w", 'ESRI Shapefile', schema) as c:
        for plyply in range(len(lake_poly_shapely)):
            c.write({'geometry': mapping(lake_poly_shapely[plyply]), 'properties': {'ID': gl_lakes_names[plyply], 'AREA': poly_area[plyply]},})

    # find the corresponding number of lake per glacier in the glacier_index
    nbr_lakes = []
    for gli in glacier_index:  # len(glacier_index)=37
        nbr_lakes.append(gl_lakes_names.count(gli))

    summary_table[i, 1] = len(lake_center_coor)  # nbr of detected  lakes
    summary_table[i, 2] = sum(nbr_lakes)  # number of lakes on dangerous glaciers (index list)
    summary_table[i, 3] = len(lake_center_coor) - sum(nbr_lakes)  # number of lakes on non-dangerous glaciers
    summary_table = summary_table.astype(np.int)


    ## Create plots

    # create map with lakes and tables for each glacier
    base_tif = detection_data_paths[i]  # load corresponding S2 image

    # build new list with all glacier names, index-glaciers first.
    glacier_index_modif = [x.replace("'", "").replace("/", "").replace(" ", "") for x in glacier_index]
    glacier_nonindex_modif = list(set(Gl_names_unique_modif) - set(glacier_index_modif))
    tot_glacier_modif = glacier_index_modif + glacier_nonindex_modif

    gl_lakes_names_modif = [x.replace("'", "").replace("/", "").replace(" ", "") for x in gl_lakes_names]

    # take only window on specific glacier
    for gl in tot_glacier_modif:
        if gl in gl_lakes_names_modif:  # take only the glacier if it has lakes on it
            # # Figure's window on whole glacier!
            # idx = np.where(Gl_names == gl)
            # bboxs_coord = np.zeros(shape=(len(idx[0]), 4))
            # for id in range(0, len(idx[0])):
            #     bboxs_coord[id, :] = all_glaciers[idx[0][id]].bbox  # (minx, miny, maxx, maxy)

            # all lake polygons on one perticular glacier
            lake_idx = [n for n, x in enumerate(gl_lakes_names_modif) if x == gl]  # get indices of lakes corresponding to that glacier
            lakes_for_gl_bbox = []
            lakes_for_gl_poly = []
            for lidx in lake_idx:
                lakes_for_gl_poly.append(lake_polygons[lidx])
                lakes_for_gl_bbox.append(lake_bbox[lidx])

            # make a figure for all individual lakes
            counter = 0
            for lke in lakes_for_gl_bbox:
                minx = lke[0]
                maxx = lke[1]
                miny = lke[2]
                maxy = lke[3]

                # open rasterio based on the bounding box above
                with rasterio.open(base_tif) as src:
                    # rst = src.read(window=windows.from_bounds(minx-0.01, miny-0.01, maxx+0.01, maxy+0.01, src.transform))
                    src = rasterio.open(base_tif)

                    # plot lake polygons on raster
                    fig_lake_on_gl = report_folder + "\\" + date_dataset + "_" + gl + "_" + str(counter+1) + ".png"
                    fig, ax = plt.subplots()

                    rasterio.plot.show(src)  # , extent=[minx, maxx, miny, maxy]
                    ax = plt.gca()
                    # plot lakes polygon
                    # patches = [PolygonPatch(feature, edgecolor="red", facecolor=(0, 0, 0, 0), linewidth=1) for feature in lakes_for_gl_poly]
                    patches = [PolygonPatch(lakes_for_gl_poly[counter], edgecolor="red", facecolor=(0, 0, 0, 0), linewidth=1)]
                    ax.add_collection(mpl.collections.PatchCollection(patches, match_original=True))
                    ax.axis('scaled')
                    ax.set(xlim=(minx-0.005, maxx+0.005), ylim=(miny-0.005, maxy+0.005))

                    # plt.show()
                    plt.savefig(fig_lake_on_gl, bbox_inches='tight', dpi=200)
                    plt.clf()
                    plt.close('all')

                    counter = counter + 1

        else:
            lakes_for_gl_poly = []  # if the glacier does not have lakes, set empty list (=0)


        # add data (nbr of lakes) to glacier .txt file
        glacier_txt_file = [os.path.abspath(os.path.join(result_path, p)) for p in os.listdir(result_path) if p.endswith(gl + '.txt')]
        with open(glacier_txt_file[0], "a") as myfile:
            myfile.writelines("\n")
            myfile.writelines(str(date_dataset) + "," + str(len(lakes_for_gl_poly)))


# create / update bar plot (nbr lakes over time), one per glacier, made with the .txt files
glacier_txt_file = [os.path.abspath(os.path.join(result_path, p)) for p in os.listdir(result_path) if p.endswith('.txt')]
glacier_txt_file_names = [p[:-4] for p in os.listdir(result_path) if p.endswith('.txt')]

for txt, txt_name in zip(glacier_txt_file, glacier_txt_file_names):
    date, nb_lake = np.loadtxt(txt, delimiter=',', unpack=True, skiprows=1)

    d = [str(np.int(d)) for d in date]
    x = np.arange(len(d))  # the label locations


    fig_barplot_gl = result_path + "\\barplot_" + txt_name + ".png"
    fig, ax = plt.subplots()
    fig.subplots_adjust(bottom=0.2)
    ax.bar(x, nb_lake, width=0.5)
    ax.set_xticks(x)
    ax.set_xticklabels(d, rotation=90, fontsize=8)
    plt.yticks(np.arange(0, 20 + 1, 1))
    ax.yaxis.set_major_formatter(FormatStrFormatter('%i'))
    plt.ylabel('Number of detected lakes')
    plt.legend(['Nbr lakes'])
    plt.savefig(fig_barplot_gl, bbox_inches='tight', dpi=200)
    plt.clf()
    plt.close('all')


# create summary table for front page
fig_summary_table = report_folder + "\\" + "summary_table.png"
fig, ax = plt.subplots()
fig.patch.set_visible(False)
ax.axis('off')  # hide axes
ax.axis('tight')
columns = ('Date', 'Tot. nbr of lakes', 'Lakes index', 'Lakes non-index', 'Mean cloud cover %', 'half of data yes/no')
the_table = ax.table(cellText=summary_table, colLabels=columns, loc='center')
fig.savefig(fig_summary_table, bbox_inches='tight', dpi=200)
plt.clf()

# add/save information in summary table (.txt file)
with open(result_path + "\\season_report\\summary_table_tot.txt", "a") as myfile:
    for l in range(0, len(summary_table)):
        myfile.writelines("\n")
        myfile.writelines(str(summary_table[l][0]) + "," + str(summary_table[l][1]) + "," + str(summary_table[l][2]) + "," + str(summary_table[l][3])+ "," + str(summary_table[l][4])+ "," + str(summary_table[l][5]))


# plot summary table as bar plot
date, tot_lake, lake_idx, lake_nonidx, clouds_perc, coverage = np.loadtxt(result_path + "\\season_report\\summary_table_tot.txt", delimiter=',', unpack=True, skiprows=1)
cov = [str(np.int(c)) for c in coverage]
d = [str(np.int(d)) for d in date]
x = np.arange(len(d))  # the label locations

# set cloud coverage with alphas
rgba_colors_red = np.zeros((len(d), 4))
rgba_colors_red[:, 0] = 1.0  # for red the first column needs to be one
rgba_colors_red[:, 3] = 1-(clouds_perc/100)  # the fourth column needs to be your alphas
rgba_colors_blue = np.zeros((len(d), 4))
rgba_colors_blue[:, 0] = 0.1  # numbers are for the blue color
rgba_colors_blue[:, 1] = 0.2
rgba_colors_blue[:, 2] = 0.5
rgba_colors_blue[:, 3] = 1-(clouds_perc/100)

# set if the coverage is partial with patterns
pat = [c.replace('1', "///").replace("0", "") for c in cov]
patterns = pat + pat

fig_barplot_tot = result_path + "\\season_report\\summary_bars_tot.png"
fig, ax = plt.subplots()
fig.subplots_adjust(bottom=0.2)

bars = ax.bar(x, lake_idx, width=0.5, color=rgba_colors_red, label='Index', hatch="/////") + ax.bar(x, lake_nonidx, bottom=lake_idx, width=0.5, color=rgba_colors_blue, label='Non-index')

for bar, pattern in zip(bars, patterns):
    bar.set_hatch(pattern)

ax.set_xticks(x)
ax.set_xticklabels(d, rotation=90)
plt.ylabel('Number of detected lakes')
plt.ylim([0, np.max(tot_lake)+2])
plt.legend(loc='upper left')
plt.savefig(fig_barplot_tot, bbox_inches='tight', dpi=200)
plt.clf()
plt.close('all')
#####------------------

##--- Create report (.pdf)
# report_date_str = report_folder[-15:-7]  # delete and change title below when the code is operational

pdf_report_name = report_folder + "\\" + report_date_str + "_report.pdf"
canvas = Canvas(pdf_report_name, pagesize=A4)  # Helvetica 12, A4(210 mm x 297 mm) = default

# Front page
canvas.setFont('Helvetica', 40)
# title = "Report of the " + str(dt.day).zfill(2) + "." + str(dt.month).zfill(2) + "." + str(dt.year)
title = "Report of the " + report_date_str

canvas.drawString(30*mm, 260*mm, title)

table_title = "Available datasets since the last report"
canvas.setFont('Helvetica', 16)
canvas.drawString(30*mm, 230*mm, table_title)

img = ImageReader(fig_summary_table)
x = 105*mm
y = 150*mm
w = 200*mm
h = 390*mm
canvas.drawImage(img, x, y, w, h, anchor='c', anchorAtXY=True,  preserveAspectRatio=True, showBoundary=False)  #
canvas.showPage()  # goes to next page

# One/several page per glacier
canvas.setFont('Helvetica', 20)

for gl_name in tot_glacier_modif:
    # list of plot and barplot for one perticular glacier
    gl_plot_list = [os.path.abspath(os.path.join(report_folder, p)) for p in os.listdir(report_folder) if gl_name in p]
    gl_plot_list.sort() ## so that dates are chronogical and bar plot is at the end

    # get real glacier name (not modified)
    name_idx = Gl_names_unique_modif.index(gl_name)
    real_name = Gl_names_unique[name_idx]

    if len(gl_plot_list) != 0:
        title_gl = "Lakes found for : " + real_name
        canvas.drawString(30*mm, 260*mm, title_gl)

        i = 0
        while i < len(gl_plot_list):
            if i == 3 or i == 5 or i == 7 or i == 9 or i == 11:
                canvas.showPage()

            if(i % 2) == 0:  # the second plot should be lower A4(210 mm x 297 mm)
                img = ImageReader(gl_plot_list[i])
                x = 105 * mm
                y = 200 * mm
                w = 100 * mm
                h = 290 * mm
                canvas.drawImage(img, x, y, w, h, anchor='c', anchorAtXY=True, preserveAspectRatio=True, showBoundary=False)  #
            else:
                img = ImageReader(gl_plot_list[i])
                x = 105 * mm
                y = 100 * mm
                w = 100 * mm
                h = 290 * mm
                canvas.drawImage(img, x, y, w, h, anchor='c', anchorAtXY=True, preserveAspectRatio=True, showBoundary=False)

            i = i + 1
        canvas.showPage()
canvas.save()
print("Report generated in: " + report_folder)
print("*** Script terminated successfully ***")
