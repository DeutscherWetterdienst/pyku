#!/usr/bin/env python3


"""
HYRAS Metadata
--------------


code:: bash

        int crs ;
                crs:grid_mapping_name = "lambert_conformal_conic" ;
                crs:standard_parallel = 35.f, 65.f ;
                crs:longitude_of_central_meridian = 10.f ;
                crs:latitude_of_projection_origin = 52.f ;
                crs:semi_major_axis = 6378137.f ;
                crs:semi_minor_axis = 6356752.f ;
                crs:inverse_flattening = 298.2572f ;
                crs:false_easting = 4000000.f ;
                crs:false_northing = 2800000.f ;
                crs:scale_factor_at_projection_origin = 0.01745329f ;
                crs:spatial_ref = "ETRS_1989_LCC,DATUM:\\D_ETRS_1989\\,SPHEROID:\\GRS_1980\\,AUTHORITY:\\EPSG 3034\\,PRIMEM:\\Greenwich 0.0\\,PROJECTION:\\Lambert_Conformal_Conic\\" ;

"""

import pyproj
import math

# Define PROJ string
# ------------------

# PROJ string taken from https://epsg.io/3034

proj_string=f"+proj=lcc +lat_1=35 +lat_2=65 +lat_0=52 +lon_0=10 +x_0=4000000 +y_0=2800000 +ellps=GRS80 +units=m +no_defs"

p = pyproj.Proj(proj_string)

# Define the resolution
# ---------------------

resolution=5000

# Define lower left and upper right corners (Taken from HYRAS file
# ----------------------------------------------------------------

# Taken from HYRAS file
# x_min, y_min = min(ds.coords['x'].values), min(ds.coords['y'].values)
# x_max, y_max = max(ds.coords['x'].values), max(ds.coords['y'].values)

x_min, y_min = (3502500.0, 2102500.0)
x_max, y_max = (4697500.0, 3197500.0)

x_ll, y_ll = x_min - resolution/2., y_min - resolution /2.
x_ur, y_ur = x_max + resolution/2., y_max + resolution /2.

# Define the number of pixels (Taken from HYRAS file)
# ---------------------------------------------------

x_size = 240
y_size = 220


from pyresample import utils
area_id = 'HYR-LCC-5'
area_name = 'HYR-LCC-5'
proj_id = 'HYR-LCC-5'
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
