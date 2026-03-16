#!/usr/bin/env python3

################################################################################
#                                                                              #
# National Imagery and Mapping Agency (NIMA), Department of Defense World      #
# Geodetic System 1984,                                                        #
# NIMA TR8350.2, third edition, 2000                                           #
# Equator radius: 6378137.0                                                    #
# Polar radius: 6356752.3142                                                   #
#                                                                              #
################################################################################

################################################################################
#                                                                              #
# EUMETSAT, LRIT/HRIT Global Specifications, CGMS/DOC/12/0017, issue 2.8,      #
# 2013 par 4.4.3.2                                                             #
# Distance between spacecraft and the radius of the earth: 42164 km            #
# Equator radius: 6378.1370 km                                                 #
# Polar radius: 6356.7523 km                                                   #
# Altitude of the spacecraft: 35785.863 km                                     #
#                                                                              #
################################################################################

import pyproj
import math

name='linet_eqc'
description=name
a=6378.1370*1000
b=6356.7523*1000
h=35785.863*1000

lon_0 = 10
lat_ts= 50

lon_ll=-10
lon_ur=+30
lat_ll=+35
lat_ur=+65

p = pyproj.Proj('+proj=eqc +lon_0={} +lat_ts={} +a={} +b={}'\
    .format(lon_0, lat_ts, a, b))

x_ll, y_ll = p(lon_ll, lat_ll)
x_ur, y_ur = p(lon_ur, lat_ur)

resolution=1000.0
x_size=(x_ur-x_ll)/resolution
y_size=(y_ur-y_ll)/resolution

print("REGION: linet_eqc {")
print("  NAME: ")
print("  PCS_ID: eqc")
print("  PCS_DEF: proj=eqc, lon_0={}, lat_ts={},  a={}, b={}"\
      .format(lon_0, lat_ts, a, b))
print("  XSIZE: {}".format(int(round(x_size, 0))))
print("  YSIZE: {}".format(int(round(y_size, 0))))
print("  AREA_EXTENT: ({}, {}, {}, {})".format(round(x_ll), round(y_ll), round(x_ur), round(y_ur)))
print("};")
print(name+":")
print("  description:" + description)
print("  projection:")
print("    proj: tpers")
print("    lat_ts: {}".format(lat_ts))
print("    lon_0: {}".format(lon_0))
print("    a: {}".format(a))
print("    b: {}".format(b))
print("  shape:")
print("    height: {}".format(y_size))
print("    width: {}".format(x_size))
print("  area_extent:")
print("    lower_left_xy: [{}, {}]".format(x_ll, y_ll))
print("    upper_right_xy: [{}, {}]".format(x_ur, y_ur))
