#############################################################################
# UPDATE_AFTER_DELETING_ROUTES.PY                                           #
#  Craig Heither, last revised 02/04/2010                                   #
#                                                                           # 
#    This program updates "rail_itinerary.dbf" after routes have been       #
#    deleted from "railnet_route_rail_lines".                               #
#                                                                           # 
#############################################################################

# ---------------------------------------------------------------
# Import System Modules, Load Toolboxes, etc.
# ---------------------------------------------------------------
import sys, string, os, arcgisscripting, subprocess, time, platform, datetime
from datetime import date
gp = arcgisscripting.create(9.3)
if platform.release() == "XP":
    # Toolbox path for Windows XP
    gp.AddToolbox("C:/Program Files/ArcGIS/ArcToolbox/Toolboxes/Conversion Tools.tbx")
    gp.AddToolbox("C:/Program Files/ArcGIS/ArcToolbox/Toolboxes/Data Management Tools.tbx")
else:
    # Toolbox path for Windows 7
    gp.AddToolbox("C:/Program Files (x86)/ArcGIS/ArcToolbox/Toolboxes/Conversion Tools.tbx")
    gp.AddToolbox("C:/Program Files (x86)/ArcGIS/ArcToolbox/Toolboxes/Data Management Tools.tbx")


# ---------------------------------------------------------------
# Local variables
# ---------------------------------------------------------------
c = r'V:\Secure\Master_Rail'                            # working directory

d = string.replace(c, "\\", '\\\\')
f = string.replace(c, "\\", '/') + "/Programs"
railnet_route_rail_lines = "railnet_route_rail_lines"
Temp = d + os.sep + os.sep + "Temp"
temp_route_shp = Temp + os.sep + os.sep + "temp_route.shp"
t = date.today()
x = date.__str__(t)
x1 = string.replace(x, "-", "")
rail_itinerary_dbf = d + os.sep + os.sep + "rail_itinerary.dbf"
new_itinerary_dbf = d + os.sep + os.sep + "itin_" + x1 + ".dbf"
itinerary = d + os.sep + os.sep + "mrn.gdb" + os.sep + os.sep + "itinerary"
new_segments_dbf = d + "\\Temp\\new_segments.dbf"

##set up to run SAS
bat = f + "/" + "sasrun.bat"                          # batch file name
fl = "remove_routes_from_itinerary"                   # SAS file name
z = f + "/" + fl + ".sas"
y = c + "$" + x1
sas_log_file = c + "\\Temp\\" + fl + ".log"
sas_list_file = d + "\\Temp\\" + fl + ".lst"
if platform.release() == "XP":
    sascall = "C:/Program Files/SAS/SAS 9.1/sas.exe"
else:
    sascall = "C:/Program Files/SAS/SASFoundation/9.2/sas.exe"
cmd = [ bat, sascall, z, y, sas_log_file, sas_list_file ] 


# ---------------------------------------------------------------
# Cleanup files if needed
# ---------------------------------------------------------------
if os.path.exists(temp_route_shp):
    gp.Delete_management(temp_route_shp, "ShapeFile")
if os.path.exists(new_itinerary_dbf):
    gp.Delete_management(new_itinerary_dbf, "DbaseTable")
if os.path.exists(sas_list_file):
    os.remove(sas_list_file)
if os.path.exists(new_segments_dbf):
    gp.Delete_management(new_segments_dbf, "DbaseTable")

gp.SelectLayerByAttribute_management(railnet_route_rail_lines, "CLEAR_SELECTION", "")


# ---------------------------------------------------------------
# Extract Route and Itinerary Data 
# ---------------------------------------------------------------
gp.AddMessage("---> Getting Route and Itinerary Data")
gp.FeatureClassToFeatureClass_conversion(railnet_route_rail_lines, Temp, "temp_route.shp", "", "", "")
gp.TableSelect_analysis(itinerary, new_itinerary_dbf, "\"OBJECTID\" >= 1")


# ---------------------------------------------------------------
# Update Rail_Itinerary.dbf
# ---------------------------------------------------------------
## run SAS with arguments supplied above
gp.AddMessage("---> Removing Deleted Routes from Itineraries")
subprocess.call(cmd)
if os.path.exists(sas_list_file):
    gp.AddMessage("---> SAS Processing Error!! Review the List File: " + sas_list_file)
    gp.AddMessage("---> If there is an Errorlevel Message, Review the Log File: " + sas_log_file)
    gp.AddMessage("-------------------------------------------------------------------")
    sys.exit[1]                                     

if os.path.exists(new_segments_dbf):
    gp.DeleteRows_management(itinerary)
    gp.Append_management(new_segments_dbf, itinerary, "NO_TEST")


# ---------------------------------------------------------------
# Cleanup files
# ---------------------------------------------------------------
gp.AddMessage("---> Removing Temporary Files")
if os.path.exists(temp_route_shp):
    gp.Delete_management(temp_route_shp, "ShapeFile")
if os.path.exists(new_segments_dbf):
    gp.Delete_management(new_segments_dbf, "DbaseTable")

