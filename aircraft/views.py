from django.shortcuts import render
from django.views.decorators.cache import cache_page
import requests
import datetime
from map import map
import geopandas as gpd

# Import the Aircraft model
from .models import Aircraft
import configparser

# Create a ConfigParser object
config = configparser.ConfigParser()

# Read the configuration file
config.read('config/config.ini')

# Get the username and password values from the configuration file
username = config['credentials']['username']
password = config['credentials']['password']


# Use the username and password values in your program
# For example, you could pass them as arguments to an API call


@cache_page(120)  # Cache the response for 2 minutes
def aircraft_info(request):
    url = "https://opensky-network.org/api/states/all"

    # Read Belarus shapefile
    shapefile = gpd.read_file("static/gadm41_BLR_shp/gadm41_BLR_0.shp")

    # Define coordinate reference system for the shapefile
    shapefile = shapefile.to_crs(epsg=4326)

    # Get the boundary
    shapefile_boundary = shapefile.geometry.unary_union.bounds

    # Set up API query parameters based on the boundary
    params = {"lamin": shapefile_boundary[1], "lomin": shapefile_boundary[0],
              "lamax": shapefile_boundary[3], "lomax": shapefile_boundary[2]}

    # Query aircraft data from API
    response = requests.get(url, auth=(username, password), params=params)
    data = response.json()["states"]

    # Convert aircraft data to geopandas dataframe
    aircraft_df = gpd.GeoDataFrame(
        {"icao24": [item[0] for item in data],
         "callsign": [item[1] for item in data],
         "origin_country": [item[2] for item in data],
         "latitude": [item[6] for item in data],
         "longitude": [item[5] for item in data],
         "altitude": [item[7] for item in data],
         "velocity": [item[9] for item in data],
         "heading": [item[10] for item in data]},
        geometry=gpd.points_from_xy([item[5] for item in data], [item[6] for item in data]),
        crs=shapefile.crs
    )

    # Perform spatial join to determine which aircraft are within Belarus
    aircraft_within_belarus = gpd.sjoin(aircraft_df, shapefile, op="within")

    # Extract relevant information from the spatial join results
    aircrafts = []
    for index, row in aircraft_within_belarus.iterrows():
        aircrafts.append({
            "icao24": row["icao24"],
            "callsign": row["callsign"],
            "origin_country": row["origin_country"],
            "latitude": row["latitude"],
            "longitude": row["longitude"],
            "altitude": row["altitude"],
            "velocity": row["velocity"],
            "heading": row["heading"]
        })
        # Save the aircraft to the database
        Aircraft.objects.create(
            icao24=row["icao24"],
            callsign=row["callsign"],
            origin_country=row["origin_country"],
            latitude=row["latitude"],
            longitude=row["longitude"],
            altitude=row["altitude"],
            velocity=row["velocity"],
            heading=row["heading"]
        )

    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    context = {"aircrafts": aircrafts, "timestamp": timestamp}

    map()
    # Save the map and legend images
    map_filename = 'static/maps/map.png'
    legend_filename = 'static/maps/legend.png'

    # Return the map and legend image filenames to the template
    context_map = {
        'map_filename': map_filename,
        'legend_filename': legend_filename,
    }

    return render(request, "index.html", context)
