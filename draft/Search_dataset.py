import requests
import pandas as pd

def request_dataset(data_collection : str, ft, yesterday_string, today_string):
    """Search copernicus dataset given:
        - the name of the satellite : data_collection 
        - a polygon (Area Of Interest) : ft
        - limit dates: yesterday_string and today_string
        
        Returns:
        - a pandas dictionary : p
        """
    json_ = requests.get(
    f"https://catalogue.dataspace.copernicus.eu/odata/v1/Products?$filter=Collection/Name eq '{data_collection}' and OData.CSC.Intersects(area=geography'SRID=4326;{ft}') and ContentDate/Start gt {yesterday_string}T00:00:00.000Z and ContentDate/Start lt {today_string}T00:00:00.000Z&$count=True&$top=1000"
    ).json()

    # Make the request
    p = pd.DataFrame.from_dict(json_["value"])  # Fetch available dataset

    return p