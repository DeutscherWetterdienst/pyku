#!/usr/bin/env python3


"""

Notes on data

.. code:: python3

   In [2]: ds=xr.open_dataset("caf2010011022.nc")

   # Check the number of lats and lons in file
   # -----------------------------------------

   In [3]: ds.coords["lat"].shape
   Out[3]: (224,)
   
   In [4]: ds.coords["lon"].shape
   Out[4]: (544,)

   # Determine the resolution
   # ------------------------
  
   In [8]: dlat = ds.coords["lat"].data[1] - ds.coords["lat"].data[0]
   
   In [9]: dlon = ds.coords["lon"].data[1] - ds.coords["lon"].data[0]
   
   In [10]: dlat
   Out[10]: 0.28103065
   
   In [11]: dlon
   Out[11]: 0.28125

   # Determine lower left and upper right corners
   # --------------------------------------------

   In [19]: ll_lat = ds.coords["lat"].data[0] - dlat / 2
   In [20]: ll_lon = ds.coords["lon"].data[0] - dlon / 2
   In [21]: ur_lat = ds.coords["lat"].data[-1] + dlat / 2
   In [22]: ur_lon = ds.coords["lon"].data[-1] + dlon / 2
   
   In [23]: (ll_lat, ll_lon)
   Out[23]: (19.11006450653076, -69.046875)

   In [36]: (ur_lat, ur_lon)
   Out[36]: (82.06076526641846, 83.953125)

   # Check the number of pixels is right
   # -----------------------------------

   In [40]: (ur_lat - ll_lat) / dlat
   Out[40]: 223.9994095329881

   In [41]: (ur_lon - ll_lon) / dlon
   Out[41]: 544.0

Note the small discrepency in dlon:

.. code:: python

   In [54]: print(ds.coords["lat"].data[1] - ds.coords["lat"].data[0])
   0.28103065
   
   In [55]: print(ds.coords["lat"].data[2] - ds.coords["lat"].data[1])
   0.28102875
   
   In [56]: print(ds.coords["lat"].data[3] - ds.coords["lat"].data[2])
   0.28103065
   
   In [57]: print(ds.coords["lat"].data[4] - ds.coords["lat"].data[3])
   0.28103065
   
   In [58]: print(ds.coords["lat"].data[5] - ds.coords["lat"].data[4])
   0.28103065

"""

import pyproj
import math

# Define PROJ string
# ------------------

# PROJ string taken from https://epsg.io/3034

proj_string='+proj=longlat +datum=WGS84'
p = pyproj.Proj(proj_string)

# Define the resolution
# ---------------------

# Define lower left and upper right corners (Taken from HYRAS file)
# -----------------------------------------------------------------

x_ll, y_ll = (-69.046875, 19.11006450653076)
x_ur, y_ur = (83.953125, 82.06076526641846)

# Define the number of pixels (Taken from HYRAS file)
# ---------------------------------------------------

x_size=544
y_size=224

from pyresample import utils
area_id = 'era5convert'
area_name = 'era5convert'
proj_id = 'era5convert'
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
