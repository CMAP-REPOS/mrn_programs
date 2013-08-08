#############################################################################
# UPDATE_NETWORK_EDITS.PY                                                   #
#  Craig Heither, last revised 05/18/2010                                   #
#                                                                           #
#    This program updates the location of rail network nodes after any of   # 
#    the following edits have been made to the arcs:                        #
#         - arcs deleted,                                                   #
#         - existing arc ends moved,                                        #
#         - new arcs digitized or                                           #
#         - existing arcs split (no more than 2 splits per link).           #
#                                                                           #
#                        -------------------------                          #
#     rev. 05-18-2010: topology validation dropped from script.             #
#                                                                           #
#############################################################################

# ---------------------------------------------------------------
# Import System Modules, Load Toolboxes, etc.
# ---------------------------------------------------------------
import sys, string, os, arcgisscripting, subprocess, time, platform
gp = arcgisscripting.create(9.3)
gp.SetProduct("ArcInfo")
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
c = "V:\Secure\Master_Rail"                            # working directory

d = string.replace(c, "\\", '\\\\')
e = d + os.sep + os.sep + "Temp"
f = string.replace(c, "\\", '/') + "/Programs"
railnet_arc = "railnet_arc"
railnet_node = "railnet_node"
rail_test = e
temp_arcstart_shp = e + os.sep + os.sep + "temp_arcstart.shp"
temp_arcend_shp = e + os.sep + os.sep + "temp_arcend.shp"
temp_node_shp = e + os.sep + os.sep + "temp_node.shp"
new_node_dbf = e + os.sep + os.sep + "new_node.dbf"
temp_node_Layer = e + os.sep + os.sep + "temp_node_Layer"
temp = d + os.sep + os.sep + "mrn.gdb\\temp"
mrn_gdb = d + os.sep + os.sep + "mrn.gdb"
new_mile_dbf = e + os.sep + os.sep + "new_mile.dbf"
split_orig_nodes_dbf = e + os.sep + os.sep + "split_orig_nodes.dbf"

##set up to run SAS
bat = f + "/" + "sasrun.bat"                          # batch file name
fl = "update_nodes"                                   # SAS file name
z = f + "/" + fl + ".sas"
sas_log_file = c + "\\Temp\\" + fl + ".log"
sas_list_file = d + "\\Temp\\" + fl + ".lst"
if platform.release() == "XP":
    sascall = "C:/Program Files/SAS/SAS 9.1/sas.exe"
else:
    sascall = "C:/Program Files/SAS/SASFoundation/9.2/sas.exe"
cmd = [ bat, sascall, z, c, sas_log_file, sas_list_file ] 


# ---------------------------------------------------------------
# Cleanup files if needed
# ---------------------------------------------------------------
if os.path.exists(temp_arcend_shp):
    gp.Delete_management(temp_arcend_shp, "ShapeFile")
if os.path.exists(temp_arcstart_shp):
    gp.Delete_management(temp_arcstart_shp, "ShapeFile")
if os.path.exists(temp_node_shp):
    gp.Delete_management(temp_node_shp, "ShapeFile")
if os.path.exists(temp_node_Layer):
    gp.Delete_management(temp_node_Layer, "Layer")
if os.path.exists(new_node_dbf):
    gp.Delete_management(new_node_dbf, "DbaseTable")
if os.path.exists(new_mile_dbf):
    gp.Delete_management(new_mile_dbf, "DbaseTable")
if os.path.exists(split_orig_nodes_dbf):
    gp.Delete_management(split_orig_nodes_dbf, "DbaseTable")
if os.path.exists(sas_list_file):
    os.remove(sas_list_file)


try:
    gp.Delete_management(temp, "FeatureClass")
except:
    print gp.GetMessages(2)

try:
    gp.DeleteField_management(railnet_node, "keep")
except:
    print gp.GetMessages(2)

try:
    gp.DeleteField_management(railnet_arc, "newmile")
except:
    print gp.GetMessages(2)
    

# ---------------------------------------------------------------
# Convert Arc Ends to Points & Add Coordinates
# ---------------------------------------------------------------
gp.AddMessage("---> Updating Node Locations")
gp.SelectLayerByAttribute_management(railnet_arc, "CLEAR_SELECTION", "")
gp.FeatureVerticesToPoints_management(railnet_arc, temp_arcstart_shp, "START")
gp.AddXY_management(temp_arcstart_shp)
gp.FeatureVerticesToPoints_management(railnet_arc, temp_arcend_shp, "END")
gp.AddXY_management(temp_arcend_shp)


# ---------------------------------------------------------------
# Make a Copy of Current Nodes and Run SAS to Process Changes
# ---------------------------------------------------------------
gp.FeatureClassToFeatureClass_conversion(railnet_node, rail_test, "temp_node.shp", "", "", "")
subprocess.call(cmd)
if os.path.exists(sas_list_file):
    gp.AddMessage("---> SAS Processing Error!! Review the List File: " + sas_list_file)
    gp.AddMessage("---> If there is an Errorlevel Message, Review the Log File: " + sas_log_file)
    gp.AddMessage("-------------------------------------------------------------------")
    sys.exit[1]                                     


# ---------------------------------------------------------------
# Update Node Feature Class Based on Changes
# ---------------------------------------------------------------
gp.AddMessage("---> Updating Node Feature Class")
gp.MakeXYEventLayer_management(new_node_dbf, "point_x", "point_y", temp_node_Layer, "PROJCS['NAD_1927_StatePlane_Illinois_East_FIPS_1201',GEOGCS['GCS_North_American_1927',DATUM['D_North_American_1927',SPHEROID['Clarke_1866',6378206.4,294.9786982]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Transverse_Mercator'],PARAMETER['False_Easting',500000.0],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',-88.33333333333333],PARAMETER['Scale_Factor',0.999975],PARAMETER['Latitude_Of_Origin',36.66666666666666],UNIT['Foot_US',0.3048006096012192]];IsHighPrecision")
gp.FeatureClassToFeatureClass_conversion(temp_node_Layer, mrn_gdb, "temp", "", "", "")
gp.AddField_management(temp, "keep", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
gp.CalculateField_management(temp, "keep", "1", "PYTHON", "")
gp.AddField_management(railnet_node, "keep", "SHORT", "", "", "", "", "NULLABLE", "NON_REQUIRED", "")
gp.CalculateField_management(railnet_node, "keep", "0", "PYTHON", "")
gp.Append_management(temp, railnet_node, "TEST", "", "")   
gp.SelectLayerByAttribute_management(railnet_node, "NEW_SELECTION", "\"keep\" = 0")
gp.DeleteRows_management(railnet_node)
gp.DeleteField_management(railnet_node, "keep")
gp.AddXY_management(railnet_node)


# ---------------------------------------------------------------
# Update Miles Value for Split Links if needed
# ---------------------------------------------------------------   
if os.path.exists(new_mile_dbf):
    gp.AddMessage("---> Updating Miles Value for Split Links")
    gp.JoinField_management(railnet_arc, "OBJECTID", new_mile_dbf, "ORIG_FID", "newmile")
    gp.SelectLayerByAttribute_management(railnet_arc, "NEW_SELECTION", "\"newmile\" > 0")
    gp.CalculateField_management(railnet_arc, "MILES", "!newmile!", "PYTHON", "")
    gp.DeleteField_management(railnet_arc, "newmile")
else:
    gp.AddMessage("---> No Split Links to Update")


# ---------------------------------------------------------------
# Cleanup files
# ---------------------------------------------------------------
gp.AddMessage("---> Removing Temporary Files")
if os.path.exists(temp_arcend_shp):
    gp.Delete_management(temp_arcend_shp, "ShapeFile")
if os.path.exists(temp_arcstart_shp):
    gp.Delete_management(temp_arcstart_shp, "ShapeFile")
if os.path.exists(temp_node_shp):
    gp.Delete_management(temp_node_shp, "ShapeFile")
if os.path.exists(temp_node_Layer):
    gp.Delete_management(temp_node_Layer, "Layer")

try:
    gp.Delete_management(temp, "FeatureClass")
except:
    print gp.GetMessages(2)
