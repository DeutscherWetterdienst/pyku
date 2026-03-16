#!/usr/bin/env python3

###########
# Sources #
###########

"""
RADOLAN/RADVOR
==============

Beschreibung des Kompositformats, Version 2.5, Oktober 2019

https://www.dwd.de/DE/leistungen/radolan/radolan_info/radolan_radvor_op_komposit_format_pdf.pdf?__blob=publicationFile&v=13

Lower left corner: 46.1929 N, 4.6759 E
Upper right corner: 55.5342 N, 17.1128 E

Note: Radolan documentation can be found at
https://www.dwd.de/DE/leistungen/radolan/radolan.html
"""

import pyproj
import math

name='radolan_wx'
description=name
a=6370.040*1000
b=6370.040*1000

lon_0=10.0
lat_ts=60.0
lat_0=60.0

lat_ll=46.1929
lon_ll=4.6759
lat_ur=55.5342
lon_ur=17.1128

p = pyproj.Proj('+proj=stere +lon_0={flon_0} +lat_ts={flat_ts} +lat_0={flat_0} \
+a={fa} +b={fb}'.format(flon_0=lon_0, flat_ts=lat_ts, flat_0=lat_0, \
fa=a, fb=b))

x_ll, y_ll = p(lon_ll, lat_ll)
x_ur, y_ur = p(lon_ur, lat_ur)

resolution=1000.0
x_size=(x_ur-x_ll)/resolution
y_size=(y_ur-y_ll)/resolution

print(name+":")
print("  description: '{}'".format(description))
print("  projection:")
print("    proj: eqc")
print("    lat_ts: {}".format(lat_ts))
print("    lat_0: {}".format(lat_0))
print("    lon_0: {}".format(lon_0))
print("    a: {}".format(a))
print("    b: {}".format(b))
print("  shape:")
print("    height: {}".format(round(y_size)))
print("    width: {}".format(round(x_size)))
print("  area_extent:")
print("    lower_left_xy: [{}, {}]".format(round(x_ll,4), round(y_ll,4)))
print("    upper_right_xy: [{}, {}]".format(round(x_ur,4), round(y_ur,4)))

