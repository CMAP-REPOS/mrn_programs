#############################################################################
# CREATE_EMME_SCENARIO_FILES.PY                                             #
#  Craig Heither, last revised 01/19/2012                                   #
#                                                                           # 
#    This program creates the Emme batchin files needed to model a scenario #
#    network.  The "Scenario" and "Path" variables are passed to the script #
#    as arguments from the tool. The following files are created:           #
#         - rail.itinerary                                                  #
#         - rail.network                                                    #
#         - railnode.extatt                                                 #
#         - railseg.extatt                                                  #
#                                                                           # 
#                        -------------------------                          #
#                                                                           # 
#  revision summary:                                                        #
#   04-26-2010: updated scenario values/logic for c10q3 scenarios.          #
#   09-10-2010: updated for ArcMap 10 (arcgisscripting replaced by arcpy).  #
#   04-05-2011: SAS call moved to sasrun.bat.                               #
#   04-07-2011: Extra step added to intersect nodes with zone system to     #
#               create correspondence so zone canbe imported into Emme.     #
#   01-19-2012: Revised script & tool so that scenario and path variables   #
#               are passed to the script as arguments. It is no longer      #
#               necessary to manually change these values in the script.    #
#                                                                           # 
#############################################################################

# ---------------------------------------------------------------
# Import System Modules
# ---------------------------------------------------------------
import sys, string, os, arcpy, subprocess, time, platform


##======================================================================##

## scenario options: beginning with c10q3 
## --------------------------------------
##            100 - 2010 network
##            200 - 2016 network
##            300 - 2020 network
##            400 - 2025 network 
##            500 - 2030 network
##            600 - 2040 network

##======================================================================##

# ---------------------------------------------------------------
# Read Script Arguments
# ---------------------------------------------------------------
scenario = arcpy.GetParameterAsText(0)
path = arcpy.GetParameterAsText(1)


# ---------------------------------------------------------------
# Local variables
# ---------------------------------------------------------------
c = "V:\Secure\Master_Rail"                            # working directory

d = string.replace(c, "\\", '\\\\')
f = string.replace(c, "\\", '/') + "/Programs"
newdir = path + "/" + scenario
railnet_route_rail_lines = "railnet_route_rail_lines"
railnet_arc = "railnet_arc"
railnet_node = "railnet_node"
Temp = d + os.sep + os.sep + "Temp"
temp_route_shp = Temp + os.sep + os.sep + "temp_route.shp"
temp_arc_shp = Temp + os.sep + os.sep + "temp_arc.shp"
temp_node_shp = Temp + os.sep + os.sep + "temp_node.shp"
itinerary = d + os.sep + os.sep + "mrn.gdb" + os.sep + os.sep + "itinerary"
scen_itin_dbf = d + "\\Temp\\scen_itin.dbf"
zones = d + "\\zones_2009\\polygon"
temp_rlnode_zone_shp = Temp + "\\temp_rlnode_zone.shp"

##set up to run SAS
bat = f + "/" + "sasrun.bat"                          # batch file name
fl = "create_Emme_rail_files"                         # SAS file name
z = f + "/" + fl + ".sas"
y = c + "$" + path + "$" + scenario
sas_log_file = c + "\\Temp\\" + fl + ".log"
sas_list_file = d + "\\Temp\\" + fl + ".lst"
cmd = [ bat, z, y, sas_log_file, sas_list_file ] 


# ---------------------------------------------------------------
# Cleanup files if needed
# ---------------------------------------------------------------
if os.path.exists(temp_route_shp):
    arcpy.Delete_management(temp_route_shp, "ShapeFile")
if os.path.exists(temp_arc_shp):
    arcpy.Delete_management(temp_arc_shp, "ShapeFile")
if os.path.exists(temp_node_shp):
    arcpy.Delete_management(temp_node_shp, "ShapeFile")
if os.path.exists(temp_rlnode_zone_shp):
    arcpy.Delete_management(temp_rlnode_zone_shp, "ShapeFile")
if os.path.exists(sas_list_file):
    os.remove(sas_list_file)
if os.path.exists(scen_itin_dbf):
    arcpy.Delete_management(scen_itin_dbf, "DbaseTable")

arcpy.SelectLayerByAttribute_management(railnet_route_rail_lines, "CLEAR_SELECTION", "")
arcpy.SelectLayerByAttribute_management(railnet_arc, "CLEAR_SELECTION", "")
arcpy.SelectLayerByAttribute_management(railnet_node, "CLEAR_SELECTION", "")


# ---------------------------------------------------------------
# Extract Data for Scenario Network
# ---------------------------------------------------------------
## select rail routes operating in the desired scenario
if scenario == "600":
    arcpy.SelectLayerByAttribute_management(railnet_route_rail_lines, "NEW_SELECTION", "\"SCENARIO\" LIKE '%6%'")
elif scenario == "500":
    arcpy.SelectLayerByAttribute_management(railnet_route_rail_lines, "NEW_SELECTION", "\"SCENARIO\" LIKE '%5%'")                                         
elif scenario == "400":
    arcpy.SelectLayerByAttribute_management(railnet_route_rail_lines, "NEW_SELECTION", "\"SCENARIO\" LIKE '%4%'")
elif scenario == "300":
    arcpy.SelectLayerByAttribute_management(railnet_route_rail_lines, "NEW_SELECTION", "\"SCENARIO\" LIKE '%3%'")
elif scenario == "200":
    arcpy.SelectLayerByAttribute_management(railnet_route_rail_lines, "NEW_SELECTION", "\"SCENARIO\" LIKE '%2%'")
elif scenario == "100":
    arcpy.SelectLayerByAttribute_management(railnet_route_rail_lines, "NEW_SELECTION", "\"SCENARIO\" LIKE '%1%'")
else:
    arcpy.AddMessage("---> You entered an invalid scenario!! Try 100, 200, 300, 400, 500, 600 - not " + scenario)
    arcpy.AddMessage("-------------------------------------------------------------------")
    sys.exit[1]                                     

arcpy.AddMessage("---> Getting data for scenario " + scenario)
arcpy.FeatureClassToFeatureClass_conversion(railnet_route_rail_lines, Temp, "temp_route.shp", "", "", "")


## select the related arcs and add transfer & access/egress links
arcpy.SelectLayerByLocation_management(railnet_arc, "SHARE_A_LINE_SEGMENT_WITH", railnet_route_rail_lines, "", "NEW_SELECTION")
arcpy.SelectLayerByAttribute_management(railnet_arc, "ADD_TO_SELECTION", "\"MODES1\" <> 'C' AND \"MODES1\" <> 'M'")
arcpy.FeatureClassToFeatureClass_conversion(railnet_arc, Temp, "temp_arc.shp", "", "", "")

## select the related nodes
arcpy.SelectLayerByLocation_management(railnet_node, "WITHIN_A_DISTANCE", railnet_arc, "10 Feet", "NEW_SELECTION")
arcpy.FeatureClassToFeatureClass_conversion(railnet_node, Temp, "temp_node.shp", "", "", "")

## Make a copy of the Itinerary coding to use
arcpy.TableSelect_analysis(itinerary, scen_itin_dbf, "\"OBJECTID\" >= 1")

## intersect rail nodes with zones
arcpy.SpatialJoin_analysis(railnet_node, zones, temp_rlnode_zone_shp, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "INTERSECT", "", "")


if not os.path.exists(newdir):
    arcpy.AddMessage("---> Directory created: " + newdir)
    os.mkdir(newdir)


# ---------------------------------------------------------------
# Create Emme Batchin Files
# ---------------------------------------------------------------
## run SAS to create files
arcpy.AddMessage("---> Creating Emme batchin files for scenario " + scenario)
subprocess.call(cmd)
if os.path.exists(sas_list_file):
    arcpy.AddMessage("---> SAS Processing Error!! Review the List File: " + sas_list_file)
    arcpy.AddMessage("---> If there is an Errorlevel Message, Review the Log File: " + sas_log_file)
    arcpy.AddMessage("-------------------------------------------------------------------")
    sys.exit[1]                                     


# ---------------------------------------------------------------
# Cleanup files
# ---------------------------------------------------------------
arcpy.AddMessage("---> Removing Temporary Files")
if os.path.exists(temp_route_shp):
    arcpy.Delete_management(temp_route_shp, "ShapeFile")
if os.path.exists(temp_arc_shp):
    arcpy.Delete_management(temp_arc_shp, "ShapeFile")
if os.path.exists(temp_node_shp):
    arcpy.Delete_management(temp_node_shp, "ShapeFile")
if os.path.exists(temp_rlnode_zone_shp):
    arcpy.Delete_management(temp_rlnode_zone_shp, "ShapeFile")
if os.path.exists(scen_itin_dbf):
    arcpy.Delete_management(scen_itin_dbf, "DbaseTable")

