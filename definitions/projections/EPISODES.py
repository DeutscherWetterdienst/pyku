#!/usr/bin/env python3


"""
EPISODES Metadata
-----------------
        lon = 60 ;
        lat = 55 ;

                :predictor_spatial_resolution = "0.75deg" ;
                :predictor_spatial_resolution = "0.75deg" ;
                :predictor_typical_domain_size = "10W30E/40N60N" ;
                :predictor_lonrange = "10degW30degE" ;
                :predictor_latrange = "40degN60degN" ;

 lon = 3.5, 3.8, 4.1, 4.4, 4.7, 5, 5.3, 5.6, 5.9, 6.2, 6.5, 6.8, 7.1, 7.4,
    7.7, 8, 8.3, 8.6, 8.9, 9.2, 9.5, 9.8, 10.1, 10.4, 10.7, 11, 11.3, 11.6,
    11.9, 12.2, 12.5, 12.8, 13.1, 13.4, 13.7, 14, 14.3, 14.6, 14.9, 15.2,
    15.5, 15.8, 16.1, 16.4, 16.7, 17, 17.3, 17.6, 17.9, 18.2, 18.5, 18.8,
    19.1, 19.4, 19.7, 20, 20.3, 20.6, 20.9, 21.2 ;

 lat = 45.3, 45.5, 45.7, 45.9, 46.1, 46.3, 46.5, 46.7, 46.9, 47.1, 47.3,
    47.5, 47.7, 47.9, 48.1, 48.3, 48.5, 48.7, 48.9, 49.1, 49.3, 49.5, 49.7,
    49.9, 50.1, 50.3, 50.5, 50.7, 50.9, 51.1, 51.3, 51.5, 51.7, 51.9, 52.1,
    52.3, 52.5, 52.7, 52.9, 53.1, 53.3, 53.5, 53.7, 53.9, 54.1, 54.3, 54.5,
    54.7, 54.9, 55.1, 55.3, 55.5, 55.7, 55.9, 56.1 ;


"""

import pyproj
from pyresample import utils

# Define PROJ string
# ------------------

# PROJ string taken from https://epsg.io/3034

proj_string = "+proj=latlong"

p = pyproj.Proj(proj_string)

# Define the resolution
# ---------------------

x_ll, y_ll = 3.5 - (3.8-3.5)/2, 45.3 - (45.5-45.3)/2.
x_ur, y_ur = 21.2 + (21.2-20.9)/2, 56.1 + (56.1-55.9)/2.

x_ll, y_ll = round(x_ll, 2), round(y_ll, 2)
x_ur, y_ur = round(x_ur, 2), round(y_ur, 2)

# Define the number of pixels (Taken from HYRAS file)
# ---------------------------------------------------

x_size = 60
y_size = 55

area_id = 'EPISODES'
area_name = 'EPISODES'
proj_id = 'EPISODES'
proj4_args = proj_string

area_extent = (x_ll, y_ll, x_ur, y_ur)
area_def = utils.get_area_def(
    area_id,
    area_name,
    proj_id,
    proj4_args,
    x_size,
    y_size,
    area_extent
)


print(area_def.create_areas_def())
