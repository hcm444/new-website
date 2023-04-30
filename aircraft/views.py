from django.shortcuts import render
from django.views.decorators.cache import cache_page
import requests
import datetime
from map import map
import geopandas as gpd
from .models import Aircraft
import configparser
config = configparser.ConfigParser()
config.read('config/config.ini')
username = config['credentials']['username']
password = config['credentials']['password']
@cache_page(120)  # Cache the response for 2 minutes
def aircraft_info(request):
    url = "https://opensky-network.org/api/states/all"
    shapefile = gpd.read_file("static/gadm41_BLR_shp/gadm41_BLR_0.shp")
    shapefile = shapefile.to_crs(epsg=4326)
    shapefile_boundary = shapefile.geometry.unary_union.bounds
    params = {"lamin": shapefile_boundary[1], "lomin": shapefile_boundary[0],
              "lamax": shapefile_boundary[3], "lomax": shapefile_boundary[2]}
    response = requests.get(url, auth=(username, password), params=params)
    data = response.json()["states"]
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
    aircraft_within = gpd.sjoin(aircraft_df, shapefile, op="within")
    aircrafts = []
    for index, row in aircraft_within.iterrows():
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
    return render(request, "index.html", context)
