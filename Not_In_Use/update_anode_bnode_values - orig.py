#############################################################################
# UPDATE_ANODE_BNODE_VALUES.PY                                              #
#  Craig Heither, last revised 07/13/2010                                   #
#                                                                           #                     
#    This program updates the values of "Anode" and "Bnode" in the arc      #
#    table after edits have been made to "Node" in the node table. It also  #
#    updates the corresponding values in the itinerary coding.              # 
#                                                                           #
#############################################################################

# ---------------------------------------------------------------
# Import System Modules, Load Toolboxes, etc.
# ---------------------------------------------------------------
import sys, string, os, arcgisscripting, subprocess, time, platform, datetime
from datetime import date

gp = arcgisscripting.create(9.3)
gp.SetProduct("ArcInfo")
if platform.release() == "XP":
    # Toolbox path for Windows XP
    gp.AddToolbox("C:/Program Files/ArcGIS/ArcToolbox/Toolboxes/Data Management Tools.tbx")
    gp.AddToolbox("C:/Program Files/ArcGIS/ArcToolbox/Toolboxes/Analysis Tools.tbx")
else:
    # Toolbox path for Windows 7
    gp.AddToolbox("C:/Program Files (x86)/ArcGIS/ArcToolbox/Toolboxes/Data Management Tools.tbx")
    gp.AddToolbox("C:/Program Files (x86)/ArcGIS/ArcToolbox/Toolboxes/Analysis Tools.tbx")

    
# ---------------------------------------------------------------
# Local variables
# ---------------------------------------------------------------
c = "V:\Secure\Master_Rail"                            # working directory

d = string.replace(c, "\\", '\\\\')
e = d + os.sep + os.sep + "Temp"
f = string.replace(c, "\\", '/') + "/Programs"
t = date.today()
x = date.__str__(t)
x1 = string.replace(x, "-", "")
railnet_arc = "railnet_arc"
railnet_node = "railnet_node"
temp_arcstart_shp = e + os.sep + os.sep + "temp_arcstart.shp"
temp_arcend_shp = e + os.sep + os.sep + "temp_arcend.shp"
temp_start_join_shp = e + os.sep + os.sep + "temp_start_join.shp"
temp_end_join_shp = e + os.sep + os.sep + "temp_end_join.shp"
itinerary = d + os.sep + os.sep + "mrn.gdb" + os.sep + os.sep + "itinerary"
new_itinerary_dbf = d + os.sep + os.sep + "itin_" + x1 + ".dbf"
new_segments_dbf = e + os.sep + os.sep + "new_segments.dbf"
new_mile_dbf = e + os.sep + os.sep + "new_mile.dbf"

##set up to run SAS
bat = f + "/" + "sasrun.bat"                          # batch file name
fl = "update_split_itinerary"                         # SAS file name
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
if os.path.exists(temp_arcstart_shp):
    gp.Delete_management(temp_arcstart_shp, "ShapeFile")
if os.path.exists(temp_arcend_shp):
    gp.Delete_management(temp_arcend_shp, "ShapeFile")
if os.path.exists(temp_start_join_shp):
    gp.Delete_management(temp_start_join_shp, "ShapeFile")
if os.path.exists(temp_end_join_shp):
    gp.Delete_management(temp_end_join_shp, "ShapeFile")
if os.path.exists(sas_list_file):
    os.remove(sas_list_file)
if os.path.exists(new_segments_dbf):
    gp.Delete_management(new_segments_dbf, "DbaseTable")

try:
    gp.DeleteField_management(railnet_arc, "node")
except:
    print gp.GetMessages(2)


# ---------------------------------------------------------------
# Separate Arcs into Beginning and Ending Points
# ---------------------------------------------------------------
gp.AddMessage("---> Separating Arcs into Beginning and Ending Points")
gp.SelectLayerByAttribute_management(railnet_arc, "CLEAR_SELECTION", "")
gp.FeatureVerticesToPoints_management(railnet_arc, temp_arcstart_shp, "START")
gp.FeatureVerticesToPoints_management(railnet_arc, temp_arcend_shp, "END")


# ---------------------------------------------------------------
# Find Node Nearest Beginning and Ending Points of Arcs
# ---------------------------------------------------------------
gp.AddMessage("---> Finding Node Nearest Beginning and Ending Points of Arcs")
gp.SelectLayerByAttribute_management(railnet_node, "CLEAR_SELECTION", "")
gp.SpatialJoin_analysis(temp_arcstart_shp, railnet_node, temp_start_join_shp, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "CLOSEST", "10 Feet", "")
gp.SpatialJoin_analysis(temp_arcend_shp, railnet_node, temp_end_join_shp, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "CLOSEST", "10 Feet", "")


# ---------------------------------------------------------------
# Update Arc Anode and Bnode Values
# ---------------------------------------------------------------
gp.AddMessage("---> Updating Arc Anode and Bnode Values")
gp.JoinField_management(railnet_arc, "OBJECTID", temp_start_join_shp, "ORIG_FID", "node")
gp.SelectLayerByAttribute_management(railnet_arc, "CLEAR_SELECTION", "")
gp.CalculateField_management(railnet_arc, "ANODE", "!node!", "PYTHON", "")
gp.DeleteField_management(railnet_arc, "node")
gp.JoinField_management(railnet_arc, "OBJECTID", temp_end_join_shp, "ORIG_FID", "node")
gp.SelectLayerByAttribute_management(railnet_arc, "CLEAR_SELECTION", "")
gp.CalculateField_management(railnet_arc, "BNODE", "!node!", "PYTHON", "")
gp.DeleteField_management(railnet_arc, "node")


# ---------------------------------------------------------------
# Update Itineraries if needed
# ---------------------------------------------------------------
if os.path.exists(new_mile_dbf):
    gp.AddMessage("---> Updating Itinerary with New Node Numbers for Split Links")
    ## Store copy of current itinerary coding for safekeeping ##
    if os.path.exists(new_itinerary_dbf):
        gp.Delete_management(new_itinerary_dbf, "DbaseTable")
    gp.TableSelect_analysis(itinerary, new_itinerary_dbf, "\"OBJECTID\" >= 1")

    ## Run SAS to Update Itineraries ##
    subprocess.call(cmd)
    if os.path.exists(sas_list_file):
        gp.AddMessage("---> SAS Processing Error!! Review the List File: " + sas_list_file)
        gp.AddMessage("---> If there is an Errorlevel Message, Review the Log File: " + sas_log_file)
        gp.AddMessage("-------------------------------------------------------------------")
        sys.exit[1]
    
    ## Update Itinerary Table in Geodatabase ##
    if os.path.exists(new_segments_dbf):
        gp.AddMessage("---> Updating Itinerary Table in Geodatabase")
          ## Note: Testing showed it takes less processing time (and fewer scripting commands) to delete the table contents
          ##       and append the entire .dbf file, than to selectively delete records from the table and only append the changes.
        gp.DeleteRows_management(itinerary)
        gp.Append_management(new_segments_dbf, itinerary, "NO_TEST")


# ---------------------------------------------------------------
# Cleanup files 
# ---------------------------------------------------------------
gp.AddMessage("---> Removing Temporary Files")
if os.path.exists(temp_arcstart_shp):
    gp.Delete_management(temp_arcstart_shp, "ShapeFile")
if os.path.exists(temp_arcend_shp):
    gp.Delete_management(temp_arcend_shp, "ShapeFile")
if os.path.exists(temp_start_join_shp):
    gp.Delete_management(temp_start_join_shp, "ShapeFile")
if os.path.exists(temp_end_join_shp):
    gp.Delete_management(temp_end_join_shp, "ShapeFile")
if os.path.exists(new_mile_dbf):
    gp.Delete_management(new_mile_dbf, "DbaseTable")
if os.path.exists(new_segments_dbf):
    gp.Delete_management(new_segments_dbf, "DbaseTable")

