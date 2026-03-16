import pyproj

name = 'seamless_world'
description = 'World for seamless forecasts'

# Geodetic parameters:
# http://ku.pages.dwd.de/libraries/pyku/tutorials/geographic_projections.html

a = 6378.1370*1000
b = 6356.7523*1000

lon_0 = 0

lon_ll = -180
lon_ur = 180
lat_ll = -90
lat_ur = 90

p = pyproj.Proj(f'+proj=robin +lon_0={lon_0} +ellps=WGS84')

x_ll, y_ll = p(lon_ll, lat_ll)
x_ur, y_ur = p(lon_ur, lat_ur)

# Add padding to the projection
# -----------------------------

x_ll = x_ll - 8200000.
x_ur = x_ur + 8200000.

print(x_ll)
print(y_ur)

resolution = 100000.0
x_size = (x_ur-x_ll)/resolution
y_size = (y_ur-y_ll)/resolution

print(x_size)
print(y_size)

print(f"""
{name}:
  description: {description}
  projection:
    proj: robin
    lon_0: {round(lon_0, 4)}
    ellps: WGS84
  shape:
    height: {int(round(y_size, 0))}
    width: {int(round(x_size, 0))}
  area_extent:
    lower_left_xy: [{round(x_ll, 4)}, {round(y_ll, 4)}]
    upper_right_xy: [{round(x_ur, 4)}, {round(y_ur, 4)}]
""")
