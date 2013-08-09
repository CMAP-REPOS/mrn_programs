#############################################################################
# UPDATE_ANODE_BNODE_VALUES.PY                                              #
#  Craig Heither, last revised 08/07/2012                                   #
#                                                                           #                     
#    This program updates the values of "Anode" and "Bnode" in the arc      #
#    table after edits have been made to "Node" in the node table. It also  #
#    updates the corresponding values in the itinerary table coding.        # 
#                                                                           #
#                        -------------------------                          #
#  revision summary:                                                        #
#   09-13-2010: updated for ArcMap 10 (arcgisscripting replaced by arcpy).  #
#   04-05-2011: SAS call moved to sasrun.bat.                               #
#   09-14-2011: Spatial join of data stopped working; use Identity instead. #
#   08-07-2012: Revised to iterate through & update all itinerary tables.   #
#                                                                           #
#############################################################################

# ---------------------------------------------------------------
# Import System Modules
# ---------------------------------------------------------------
import sys, string, os, arcpy, subprocess, time, platform, datetime
from datetime import date
from arcpy import env

    
# ---------------------------------------------------------------
# Local variables
# ---------------------------------------------------------------
c = "C:\Master_Rail"                            # working directory

d = string.replace(c, "\\", '\\\\')
e = d + "\\Temp"
f = string.replace(c, "\\", '/') + "/mrn_programs"
t = date.today()
x = date.__str__(t)
x1 = string.replace(x, "-", "")
railnet_arc = "railnet_arc"
railnet_node = "railnet_node"
temp_arcstart_shp = e + "\\temp_arcstart.shp"
temp_arcend_shp = e + "\\temp_arcend.shp"
temp_start_join_shp = e + "\\temp_start_join.shp"
temp_end_join_shp = e + "\\temp_end_join.shp"

new_segments_dbf = e + "\\new_segments.dbf"
new_mile_dbf = e + "\\new_mile.dbf"

##set up to run SAS
bat = f + "/" + "sasrun.bat"                          # batch file name
fl = "update_split_itinerary_Aug2012"                 # SAS file name
z = f + "/" + fl + ".sas"
sas_log_file = c + "\\Temp\\" + fl + ".log"
sas_list_file = d + "\\Temp\\" + fl + ".lst"


# ---------------------------------------------------------------
# Cleanup files if needed
# ---------------------------------------------------------------
if os.path.exists(temp_arcstart_shp):
    arcpy.Delete_management(temp_arcstart_shp, "ShapeFile")
if os.path.exists(temp_arcend_shp):
    arcpy.Delete_management(temp_arcend_shp, "ShapeFile")
if os.path.exists(temp_start_join_shp):
    arcpy.Delete_management(temp_start_join_shp, "ShapeFile")
if os.path.exists(temp_end_join_shp):
    arcpy.Delete_management(temp_end_join_shp, "ShapeFile")
if os.path.exists(sas_list_file):
    os.remove(sas_list_file)
if os.path.exists(new_segments_dbf):
    arcpy.Delete_management(new_segments_dbf, "DbaseTable")

try:
    arcpy.DeleteField_management(railnet_arc, "node")
except:
    print arcpy.GetMessages(2)


# ---------------------------------------------------------------
# Separate Arcs into Beginning and Ending Points
# ---------------------------------------------------------------
arcpy.AddMessage("---> Separating Arcs into Beginning and Ending Points")
arcpy.SelectLayerByAttribute_management(railnet_arc, "CLEAR_SELECTION", "")
arcpy.FeatureVerticesToPoints_management(railnet_arc, temp_arcstart_shp, "START")
arcpy.FeatureVerticesToPoints_management(railnet_arc, temp_arcend_shp, "END")


# ---------------------------------------------------------------
# Find Node Nearest Beginning and Ending Points of Arcs
# ---------------------------------------------------------------
arcpy.AddMessage("---> Finding Node Nearest Beginning and Ending Points of Arcs")
arcpy.SelectLayerByAttribute_management(railnet_node, "CLEAR_SELECTION", "")
arcpy.Identity_analysis(temp_arcstart_shp, railnet_node, temp_start_join_shp, "ALL", "", "NO_RELATIONSHIPS")
arcpy.Identity_analysis(temp_arcend_shp, railnet_node, temp_end_join_shp, "ALL", "", "NO_RELATIONSHIPS")


# ---------------------------------------------------------------
# Update Arc Anode and Bnode Values
# ---------------------------------------------------------------
arcpy.AddMessage("---> Updating Arc Anode and Bnode Values")
arcpy.JoinField_management(railnet_arc, "OBJECTID", temp_start_join_shp, "ORIG_FID", "node")
arcpy.SelectLayerByAttribute_management(railnet_arc, "CLEAR_SELECTION", "")
arcpy.CalculateField_management(railnet_arc, "ANODE", "!node!", "PYTHON", "")
arcpy.DeleteField_management(railnet_arc, "node")
arcpy.JoinField_management(railnet_arc, "OBJECTID", temp_end_join_shp, "ORIG_FID", "node")
arcpy.SelectLayerByAttribute_management(railnet_arc, "CLEAR_SELECTION", "")
arcpy.CalculateField_management(railnet_arc, "BNODE", "!node!", "PYTHON", "")
arcpy.DeleteField_management(railnet_arc, "node")


# ---------------------------------------------------------------
# Update Itineraries if needed
# ---------------------------------------------------------------
if os.path.exists(new_mile_dbf):
    env.workspace = "C:/Master_Rail/mrn.gdb/railnet"             ## point inside feature dataset
    fcs = arcpy.ListFeatureClasses('',"arc")
    fcs.remove("railnet_arc")
    i = 0
    for fc in fcs:
        arcpy.AddMessage("---> Updating " + fcs[i] + " Itinerary with New Node Numbers for Split Links ...")
        itinerary = d + "\\mrn.gdb\\" + fc + "_itin"
        orig_itinerary_dbf = d + "\\" + fc + "_itin_" + x1 + ".dbf"
        
        ## Store copy of current itinerary coding for safekeeping ##
        if os.path.exists(orig_itinerary_dbf):
            arcpy.Delete_management(orig_itinerary_dbf, "DbaseTable")
        arcpy.TableSelect_analysis(itinerary, orig_itinerary_dbf, "\"OBJECTID\" >= 1")
        
        ## Run SAS to Update Itineraries ##
        # -- finish set up to run SAS
        y = c + "$" + orig_itinerary_dbf
        cmd = [ bat, z, y, sas_log_file, sas_list_file ]
        subprocess.call(cmd)
        if os.path.exists(sas_list_file):
            arcpy.AddMessage("---> SAS Processing Error!! Review the List File: " + sas_list_file)
            arcpy.AddMessage("---> If there is an Errorlevel Message, Review the Log File: " + sas_log_file)
            arcpy.AddMessage("-------------------------------------------------------------------")
            sys.exit[1]

        ## Update Itinerary Table in Geodatabase ##
        if os.path.exists(new_segments_dbf):
            arcpy.AddMessage("---> Updating " + fcs[i] + " Itinerary Table in Geodatabase")
              ## Note: Testing showed it takes less processing time (and fewer scripting commands) to delete the table contents
              ##       and append the entire .dbf file, than to selectively delete records from the table and only append the changes.
            arcpy.DeleteRows_management(itinerary)
            arcpy.Append_management(new_segments_dbf, itinerary, "NO_TEST")
            arcpy.Delete_management(new_segments_dbf, "DbaseTable")
        i += 1   
        

# ---------------------------------------------------------------
# Cleanup files 
# ---------------------------------------------------------------
arcpy.AddMessage("---> Removing Temporary Files")
if os.path.exists(temp_arcstart_shp):
    arcpy.Delete_management(temp_arcstart_shp, "ShapeFile")
if os.path.exists(temp_arcend_shp):
    arcpy.Delete_management(temp_arcend_shp, "ShapeFile")
if os.path.exists(temp_start_join_shp):
    arcpy.Delete_management(temp_start_join_shp, "ShapeFile")
if os.path.exists(temp_end_join_shp):
    arcpy.Delete_management(temp_end_join_shp, "ShapeFile")
if os.path.exists(new_mile_dbf):
    arcpy.Delete_management(new_mile_dbf, "DbaseTable")
