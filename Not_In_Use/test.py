# ---------------------------------------------------------------
# Import System Modules
# ---------------------------------------------------------------
import sys, string, os, arcpy, subprocess, time, platform, datetime, fileinput
from datetime import date
from arcpy import env


# ---------------------------------------------------------------
# Local variables
# ---------------------------------------------------------------
c = r"V:\Secure\Master_Rail"                                 # working directory

d = string.replace(c, "\\", '\\\\')
e = d + os.sep + os.sep + "Temp"
f = string.replace(c, "\\", '/') + "/Programs"
rail_test = e
railnet_arc = "railnet_arc"
railnet_route_rail_lines = "railnet_route_rail_lines"
mrn_gdb = d + os.sep + os.sep + "mrn.gdb"
railnet = mrn_gdb + os.sep + os.sep + "railnet"
railrt = railnet + "\\railnet_route_rail_lines"
Temp = e
t = date.today()
x = date.__str__(t)
x1 = string.replace(x, "-", "")
orig_itinerary_dbf = d + os.sep + os.sep + "itin_" + x1 + ".dbf"
itinerary = d + os.sep + os.sep + "mrn.gdb" + os.sep + os.sep + "itinerary"
new_segments_dbf = e + "\\new_segments.dbf"
temp_route_shp = e + os.sep + os.sep + "temp_route.shp"
outFl = e + os.sep + os.sep + "geom_out.txt"
infl = e + os.sep + os.sep + "geom_in.txt"
rte_updt = e + os.sep + os.sep + "rte_updt.dbf"
rte_updt_View = "rte_updt_View"
test = railnet + os.sep + os.sep + "test"
temp_rte_layer = e + os.sep + os.sep + "temp_rte_Layer"


##################
mxd = arcpy.mapping.MapDocument("CURRENT")
df = arcpy.mapping.ListDataFrames(mxd)[0]
arcpy.MakeFeatureLayer_management(railrt, temp_rte_layer)
addLayer = arcpy.mapping.Layer(temp_rte_layer)
arcpy.mapping.AddLayer(df, addLayer, "BOTTOM")
arcpy.AddMessage("---> OK 3")
mxd.save()
##del mxd, addLayer
