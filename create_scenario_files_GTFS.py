#############################################################################
# CREATE_SCENARIO_FILES_GTFS.PY                                             #
#  Craig Heither & Nick Ferguson, last revised 07/18/2013                   #
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
#  Revision summary:                                                        #
#   04-26-2012: Revised script & tool so that CT-RAMP output flag is        # 
#               available to use expanded list of transit vehicle types.    #
#   06-19-2013: Added code to create temporary copy of people mover table.  #
#   07-18-2013: Added ability to create link shape file by calling the      #
#               create function from the linkshape module.                  #
#                                                                           # 
#############################################################################

# ---------------------------------------------------------------
# Import System Modules
# ---------------------------------------------------------------
import sys, string, os, arcpy, subprocess, time, platform, fileinput, linkshape
from arcpy import env
arcpy.OverwriteOutput = 1


##======================================================================##

## scenario options: beginning with c10q3 
## --------------------------------------
##            100 - 2010 network
##            200 - 2015 network
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
bool = arcpy.GetParameterAsText(2)
if bool == "true":
    ct_ramp = "1"
else:
    ct_ramp = "0"

arcpy.AddMessage("---> ct_ramp is " + ct_ramp)


# ---------------------------------------------------------------
# Local variables
# ---------------------------------------------------------------
c = "C:\Secure\Master_Rail"                            # working directory
d = string.replace(c, "\\", '\\\\')
f = string.replace(c, "\\", '/') + "/mrn_programs"
newdir = path + "\\" + scenario
current = "all_runs"                                   # current routes
if scenario in ("100","900"):
    current = "all_runs_base"                          # base year routes
future = "future"                                      # future coding
rail_routes = current
rail_routes_ftr = future
railnet_arc = "railnet_arc"
railnet_node = "railnet_node"
Temp = d + "\\Temp"
temp_route_shp = Temp + "\\temp_route.shp"
temp_route_ftr_shp = Temp + "\\temp_route_ftr.shp"
temp_arc_shp = Temp + "\\temp_arc.shp"
temp_arc_ftr_shp = Temp + "\\temp_arc_ftr.shp"
temp_ppl_mvr_dbf = Temp + "\\temp_ppl_mvr.dbf"
itinerary = d + "\\mrn.gdb\\" + current + "_itin"
itinerary_ftr = d + "\\mrn.gdb\\" + future + "_itin"
people_mover = d + "\\mrn.gdb\\" + "people_mover"
scen_itin_dbf = d + "\\Temp\\scen_itin.dbf"
ftr_itin_dbf = d + "\\Temp\\ftr_itin.dbf"
zones = d + "\\zones_2009\\polygon"
temp_rlnode_zone_shp = Temp + "\\temp_rlnode_zone.shp"
outFl = Temp + "\\rte_out.txt"
link_list = newdir + '\\rail_links_all.csv'
vertex_list = newdir + '\\railnet_vertex.csv'
linkshape_file = newdir + '\\rail.linkshape'

##set up to run SAS
bat = f + "/" + "sasrun.bat"                          # batch file name
fl = "create_Emme_rail_files_GTFS"                    # SAS file name
z = f + "/" + fl + ".sas"
y = c + "$" + path + "$" + scenario + "$" + ct_ramp
sas_log_file = c + "\\Temp\\" + fl + ".log"
sas_list_file = d + "\\Temp\\" + fl + ".lst"
cmd = [ bat, z, y, sas_log_file, sas_list_file ] 


# ---------------------------------------------------------------
# Cleanup files if needed
# ---------------------------------------------------------------
if os.path.exists(temp_route_shp):
    arcpy.Delete_management(temp_route_shp, "ShapeFile")
if os.path.exists(temp_route_ftr_shp):
    arcpy.Delete_management(temp_route_ftr_shp, "ShapeFile")
if os.path.exists(temp_arc_shp):
    arcpy.Delete_management(temp_arc_shp, "ShapeFile")
if os.path.exists(temp_arc_ftr_shp):
    arcpy.Delete_management(temp_arc_ftr_shp, "ShapeFile")
if os.path.exists(temp_rlnode_zone_shp):
    arcpy.Delete_management(temp_rlnode_zone_shp, "ShapeFile")
if os.path.exists(temp_ppl_mvr_dbf):
    arcpy.Delete_management(temp_ppl_mvr_dbf, "DbaseTable")
if os.path.exists(sas_list_file):
    os.remove(sas_list_file)
if os.path.exists(scen_itin_dbf):
    arcpy.Delete_management(scen_itin_dbf, "DbaseTable")
if os.path.exists(ftr_itin_dbf):
    arcpy.Delete_management(ftr_itin_dbf, "DbaseTable")
if os.path.exists(outFl):
    os.remove(outFl)
if os.path.exists(link_list):
    os.remove(link_list)
if os.path.exists(vertex_list):
    os.remove(vertex_list)
if os.path.exists(linkshape_file):
    os.remove(linkshape_file)

arcpy.SelectLayerByAttribute_management(rail_routes, "CLEAR_SELECTION", "")
arcpy.SelectLayerByAttribute_management(railnet_arc, "CLEAR_SELECTION", "")
arcpy.SelectLayerByAttribute_management(railnet_node, "CLEAR_SELECTION", "")
arcpy.SelectLayerByAttribute_management(rail_routes_ftr, "CLEAR_SELECTION", "")


# ---------------------------------------------------------------
# Extract Data for Scenario Network
# ---------------------------------------------------------------
arcpy.AddMessage("---> Getting data for scenario " + scenario)
arcpy.AddMessage("   * Obtaining Rail Routes...")
arcpy.FeatureClassToFeatureClass_conversion(rail_routes, Temp, "temp_route.shp", "", "", "")

## select the related arcs and add transfer & access/egress links
arcpy.AddMessage("   * Obtaining Rail Network Arcs...")
arcpy.SelectLayerByLocation_management(railnet_arc, "SHARE_A_LINE_SEGMENT_WITH", rail_routes, "", "NEW_SELECTION")
arcpy.SelectLayerByAttribute_management(railnet_arc, "ADD_TO_SELECTION", "\"MODES1\" <> 'C' AND \"MODES1\" <> 'M'")
arcpy.FeatureClassToFeatureClass_conversion(railnet_arc, Temp, "temp_arc.shp", "", "", "")

## select ALL nodes & intersect with zones
arcpy.AddMessage("   * Obtaining Rail Network Nodes...")
arcpy.SpatialJoin_analysis(railnet_node, zones, temp_rlnode_zone_shp, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "INTERSECT", "", "")

## Make a copy of the Itinerary coding to use
arcpy.AddMessage("   * Obtaining Rail Itinerary Data...")
arcpy.TableSelect_analysis(itinerary, scen_itin_dbf, "\"OBJECTID\" >= 1")

## Make a copy of the people mover coding to use
arcpy.TableSelect_analysis(people_mover, temp_ppl_mvr_dbf, "\"OBJECTID\" >= 1")

## obtain extra data for future scenarios
if scenario != "100":
    arcpy.AddMessage("   * Obtaining Additional Data for Scenario " + scenario + " ...")
    arcpy.FeatureClassToFeatureClass_conversion(rail_routes_ftr, Temp, "temp_route_ftr.shp", "", "", "")
    arcpy.SelectLayerByLocation_management(railnet_arc, "SHARE_A_LINE_SEGMENT_WITH", rail_routes_ftr, "", "NEW_SELECTION")
    arcpy.FeatureClassToFeatureClass_conversion(railnet_arc, Temp, "temp_arc_ftr.shp", "", "", "")
    arcpy.TableSelect_analysis(itinerary_ftr, ftr_itin_dbf, "\"OBJECTID\" >= 1")
    ## Write Route Geometry File - Used for Processing Action=2
    outFile = open(outFl, "w")
    f = 1                                             # row id number
    for row in arcpy.SearchCursor(rail_routes_ftr):   # loop through rows (features)
        for part in row.Shape:                        # loop through feature parts
            pnt = part.next()
            while pnt:                                # loop through vertices
                outFile.write(str(f) + ";" + str(row.getValue("TR_LINE")) + ";" + str(row.getValue("ACTION")) + ";" +  str(pnt.X) + ";" + str(pnt.Y) + "\n")
                pnt = part.next()
                if not pnt:
                    pnt = part.next()
        f += 1      
    f -= 1
    arcpy.AddMessage("---> Geometry Written for " + str(f) + " Routes")
    outFile.close()


## Create Storage Folder if it does not exist
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
    sys.exit([1])       

## create linkshape file
arcpy.SelectLayerByAttribute_management(railnet_arc, 'CLEAR_SELECTION')
linkshape.create(railnet_arc, link_list, vertex_list, linkshape_file, scenario)

# ---------------------------------------------------------------
# Cleanup files
# ---------------------------------------------------------------
arcpy.AddMessage("---> Removing Temporary Files")
if os.path.exists(temp_route_shp):
    arcpy.Delete_management(temp_route_shp, "ShapeFile")
if os.path.exists(temp_route_ftr_shp):
    arcpy.Delete_management(temp_route_ftr_shp, "ShapeFile")
if os.path.exists(temp_arc_shp):
    arcpy.Delete_management(temp_arc_shp, "ShapeFile")
if os.path.exists(temp_arc_ftr_shp):
    arcpy.Delete_management(temp_arc_ftr_shp, "ShapeFile")
if os.path.exists(temp_rlnode_zone_shp):
    arcpy.Delete_management(temp_rlnode_zone_shp, "ShapeFile")
if os.path.exists(temp_ppl_mvr_dbf):
    arcpy.Delete_management(temp_ppl_mvr_dbf, "DbaseTable")
if os.path.exists(scen_itin_dbf):
    arcpy.Delete_management(scen_itin_dbf, "DbaseTable")
if os.path.exists(ftr_itin_dbf):
    arcpy.Delete_management(ftr_itin_dbf, "DbaseTable")
if os.path.exists(outFl):
    os.remove(outFl)
if os.path.exists(link_list):
    os.remove(link_list)
if os.path.exists(vertex_list):
    os.remove(vertex_list)
