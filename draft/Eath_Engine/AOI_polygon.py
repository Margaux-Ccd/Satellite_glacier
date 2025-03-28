import geojson
from shapely.geometry import shape, Polygon

def load_polygon_from_geojson(polygon_path : str):
    """
    Load a polygon from a GeoJSON file.

    Parameters:
    - polygon_path (str): The path to the GeoJSON file.

    Returns:
    - Polygon or None: The extracted polygon if valid, otherwise None.
    """
    try:
        with open(polygon_path, 'r') as file:
            geojson_data = geojson.load(file)

        # Extract the polygon from the GeoJSON data
        polygon_data = geojson_data['features'][0]['geometry']  # Adjust index if needed
        polygon = shape(polygon_data)

        # Check if it's a polygon
        if isinstance(polygon, Polygon):
            print("The GeoJSON data represents a polygon.")
            return polygon
        else:
            print("The GeoJSON data does not represent a polygon.")
            return None
    except Exception as e:
        print(f"Error loading GeoJSON file: {e}")
        return None


