#!/usr/bin/env python3


"""
HYRAS Projection
"""

import pyproj
from pyresample import utils

# Define PROJ string
# ------------------

# PROJ string taken from https://epsg.io/3034

proj_string = (
    "+proj=lcc +lat_1=35 +lat_2=65 +lat_0=52 +lon_0=10 +x_0=4000000 "
    "+y_0=2800000 +ellps=GRS80 +units=m +no_defs"
)

p = pyproj.Proj(proj_string)

# Define lower left and upper right corners (Taken from HYRAS file
# ----------------------------------------------------------------

x_ll, y_ll = 3500000.0, 2100000.0
x_ur, y_ur = 4700000.0, 3200000.0

# Define resolution and calculate the number of pixels
# ----------------------------------------------------

resolution = 1000.0

x_size = (x_ur-x_ll)/resolution
y_size = (y_ur-y_ll)/resolution

area_id = 'HYR-LCC-1'
area_name = 'HYR-LCC-1'
proj_id = 'HYR-LCC-1'
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
