import pyproj

name = 'seamless_germany'
description = 'Germany for seamless forecasts'

# Geodetic parameters:
# http://ku.pages.dwd.de/libraries/pyku/tutorials/geographic_projections.html

a = 6378.1370*1000
b = 6356.7523*1000

lat_ts = 50
lat_0 = 50
lon_0 = 10

lon_ll = 5.5
lon_ur = 15.5
lat_ll = 47
lat_ur = 55

p = pyproj.Proj(
    f'+proj=stere +lon_0={lon_0} +lat_ts={lat_ts} +lat_0={lat_0} +ellps=WGS84'
)

x_ll, y_ll = p(lon_ll, lat_ll)
x_ur, y_ur = p(lon_ur, lat_ur)

resolution = 5000.0
x_size = (x_ur-x_ll)/resolution
y_size = (y_ur-y_ll)/resolution

print(f"""
{name}:
  description: {description}
  projection:
    proj: stere
    lon_0: {round(lon_0, 4)}
    lat_0: {round(lat_0, 4)}
    lat_ts: {round(lat_ts, 4)}
    ellps: WGS84
  shape:
    height: {int(round(y_size, 0))}
    width: {int(round(x_size, 0))}
  area_extent:
    lower_left_xy: [{round(x_ll, 4)}, {round(y_ll, 4)}]
    upper_right_xy: [{round(x_ur, 4)}, {round(y_ur, 4)}]
""")
