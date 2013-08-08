#############################################################################
# CREATE_EMME_SCENARIO_FILES.PY                                             #
#  Craig Heither, last revised 04/26/2010                                   #
#                                                                           # 
#    This program creates the Emme batchin files needed to model a scenario #
#    network.  The "Scenario" and "Path" variables listed below should be   #
#    updated for each set of scenario network files. The following files    #
#    created:                                                               #
#         - rail.itinerary                                                  #
#         - rail.network                                                    #
#         - railnode.extatt                                                 #
#         - railseg.extatt                                                  #
#                                                                           # 
#                                                                           #
#  revision summary:                                                        #
#   4-26-10: updated scenario values & selection logic for c10q3 scenarios. #
#                                                                           #
#                                                                           #
#############################################################################

# ---------------------------------------------------------------
# Import System Modules, Load Toolboxes, etc.
# ---------------------------------------------------------------
import sys, string, os, arcgisscripting, subprocess, time, platform
gp = arcgisscripting.create(9.3)
if platform.release() == "XP":
    # Toolbox path for Windows XP
    gp.AddToolbox("C:/Program Files/ArcGIS/ArcToolbox/Toolboxes/Conversion Tools.tbx")
    gp.AddToolbox("C:/Program Files/ArcGIS/ArcToolbox/Toolboxes/Data Management Tools.tbx")
    gp.AddToolbox("C:/Program Files/ArcGIS/ArcToolbox/Toolboxes/Analysis Tools.tbx")
else:
    # Toolbox path for Windows 7
    gp.AddToolbox("C:/Program Files (x86)/ArcGIS/ArcToolbox/Toolboxes/Conversion Tools.tbx")
    gp.AddToolbox("C:/Program Files (x86)/ArcGIS/ArcToolbox/Toolboxes/Data Management Tools.tbx")
    gp.AddToolbox("C:/Program Files (x86)/ArcGIS/ArcToolbox/Toolboxes/Analysis Tools.tbx")


##======================================================================##
               ##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##
               ##       CHANGE VARIABLES HERE      ##
               ##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##
scenario = "100"                         # scenario network to create
path = r"V:\Secure\Master_Rail\ScenarioNetworkRail_forEmme"     # file storage directory (leave the r before the quotes)

## scenario options: beginning with c10q3 
## --------------------------------------
##            100 - 2010 network
##            200 - 2016 network
##            300 - 2020 network
##            400 - 2025 network [not for c10q3]
##            500 - 2030 network
##            600 - 2040 network

##======================================================================##


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
temp1 = Temp + os.sep + os.sep + "temp1"
temp2 = Temp + os.sep + os.sep + "temp2.dbf"
temp3 = Temp + os.sep + os.sep + "temp3.shp"
temp4 = Temp + os.sep + os.sep + "temp4.dbf"

##set up to run SAS
bat = f + "/" + "sasrun.bat"                          # batch file name
fl = "create_Emme_rail_files"                         # SAS file name
z = f + "/" + fl + ".sas"
fl2 = "temp"                                          # SAS file name
z2 = f + "/" + fl2 + ".sas"
y = c + "$" + path + "$" + scenario
sas_log_file = c + "\\Temp\\" + fl + ".log"
sas_list_file = d + "\\Temp\\" + fl + ".lst"
sas_log_file2 = c + "\\Temp\\" + fl2 + ".log"
sas_list_file2 = d + "\\Temp\\" + fl2 + ".lst"
if platform.release() == "XP":
    sascall = "C:/Program Files/SAS/SAS 9.1/sas.exe"
else:
    sascall = "C:/Program Files/SAS/SASFoundation/9.2/sas.exe"
cmd = [ bat, sascall, z, y, sas_log_file, sas_list_file ] 

cmd2 = [ bat, sascall, z2, y, sas_log_file2, sas_list_file2 ]

# ---------------------------------------------------------------
# Cleanup files if needed
# ---------------------------------------------------------------
if os.path.exists(temp_route_shp):
    gp.Delete_management(temp_route_shp, "ShapeFile")
if os.path.exists(temp_arc_shp):
    gp.Delete_management(temp_arc_shp, "ShapeFile")
if os.path.exists(temp_node_shp):
    gp.Delete_management(temp_node_shp, "ShapeFile")
if os.path.exists(sas_list_file):
    os.remove(sas_list_file)
if os.path.exists(scen_itin_dbf):
    gp.Delete_management(scen_itin_dbf, "DbaseTable")
if os.path.exists(temp1):
    gp.Delete_management(temp1)
if os.path.exists(temp2):
    gp.Delete_management(temp2)
if os.path.exists(temp3):
    gp.Delete_management(temp3)
if os.path.exists(temp4):
    gp.Delete_management(temp4)

try:
    gp.DeleteField_management(railnet_arc, "inscen")
except:
    print gp.GetMessages(2)




gp.SelectLayerByAttribute_management(railnet_route_rail_lines, "CLEAR_SELECTION", "")
gp.SelectLayerByAttribute_management(railnet_arc, "CLEAR_SELECTION", "")
gp.SelectLayerByAttribute_management(railnet_node, "CLEAR_SELECTION", "")


# ---------------------------------------------------------------
# Extract Data for Scenario Network
# ---------------------------------------------------------------
## select rail routes operating in the desired scenario
if scenario == "600":
    gp.SelectLayerByAttribute_management(railnet_route_rail_lines, "NEW_SELECTION", "\"SCENARIO\" LIKE '%6%'")
elif scenario == "500":
    gp.SelectLayerByAttribute_management(railnet_route_rail_lines, "NEW_SELECTION", "\"SCENARIO\" LIKE '%5%'")                                         
elif scenario == "400":
    gp.SelectLayerByAttribute_management(railnet_route_rail_lines, "NEW_SELECTION", "\"SCENARIO\" LIKE '%4%'")
elif scenario == "300":
    gp.SelectLayerByAttribute_management(railnet_route_rail_lines, "NEW_SELECTION", "\"SCENARIO\" LIKE '%3%'")
elif scenario == "200":
    gp.SelectLayerByAttribute_management(railnet_route_rail_lines, "NEW_SELECTION", "\"SCENARIO\" LIKE '%2%'")
elif scenario == "100":
    gp.SelectLayerByAttribute_management(railnet_route_rail_lines, "NEW_SELECTION", "\"SCENARIO\" LIKE '%1%'")
else:
    gp.AddMessage("---> You entered an invalid scenario!! Try 100, 200, 300, 400, 500, 600 - not " + scenario)
    gp.AddMessage("-------------------------------------------------------------------")
    sys.exit[1]                                     

gp.AddMessage("---> Getting data for scenario " + scenario)
gp.FeatureClassToFeatureClass_conversion(railnet_route_rail_lines, Temp, "temp_route.shp", "", "", "")

gp.TableSelect_analysis(itinerary, temp2)
gp.FeatureVerticesToPoints_management(railnet_arc, temp3, "START")

subprocess.call(cmd2)
gp.JoinField_management(railnet_arc, "OBJECTID", temp4, "ORIG_FID", "inscen")
gp.SelectLayerByAttribute_management(railnet_arc, "NEW_SELECTION", "\"inscen\" = 1")


## select the related arcs and add transfer & access/egress links
## ***gp.SelectLayerByLocation_management(railnet_arc, "SHARE_A_LINE_SEGMENT_WITH", railnet_route_rail_lines, "", "NEW_SELECTION")
gp.SelectLayerByAttribute_management(railnet_arc, "ADD_TO_SELECTION", "\"MODES1\" <> 'C' AND \"MODES1\" <> 'M'")
gp.FeatureClassToFeatureClass_conversion(railnet_arc, Temp, "temp_arc.shp", "", "", "")

## select the related nodes
gp.SelectLayerByLocation_management(railnet_node, "WITHIN_A_DISTANCE", railnet_arc, "10 Feet", "NEW_SELECTION")
gp.FeatureClassToFeatureClass_conversion(railnet_node, Temp, "temp_node.shp", "", "", "")

gp.DeleteField_management(railnet_arc, "inscen")



## Make a copy of the Itinerary coding to use
gp.TableSelect_analysis(itinerary, scen_itin_dbf, "\"OBJECTID\" >= 1")

if not os.path.exists(newdir):
    gp.AddMessage("---> Directory created: " + newdir)
    os.mkdir(newdir)


# ---------------------------------------------------------------
# Create Emme Batchin Files
# ---------------------------------------------------------------
## run SAS to create files
gp.AddMessage("---> Creating Emme batchin files for scenario " + scenario)
subprocess.call(cmd)
if os.path.exists(sas_list_file):
    gp.AddMessage("---> SAS Processing Error!! Review the List File: " + sas_list_file)
    gp.AddMessage("---> If there is an Errorlevel Message, Review the Log File: " + sas_log_file)
    gp.AddMessage("-------------------------------------------------------------------")
    sys.exit[1]                                     


# ---------------------------------------------------------------
# Cleanup files
# ---------------------------------------------------------------
gp.AddMessage("---> Removing Temporary Files")
if os.path.exists(temp_route_shp):
    gp.Delete_management(temp_route_shp, "ShapeFile")
if os.path.exists(temp_arc_shp):
    gp.Delete_management(temp_arc_shp, "ShapeFile")
if os.path.exists(temp_node_shp):
    gp.Delete_management(temp_node_shp, "ShapeFile")
if os.path.exists(scen_itin_dbf):
    gp.Delete_management(scen_itin_dbf, "DbaseTable")
if os.path.exists(temp1):
    gp.Delete_management(temp1)
if os.path.exists(temp2):
    gp.Delete_management(temp2)
if os.path.exists(temp3):
    gp.Delete_management(temp3)
if os.path.exists(temp4):
    gp.Delete_management(temp4)

