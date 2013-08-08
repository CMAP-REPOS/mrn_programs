#############################################################################
# UPDATE_NETWORK_EDITS.PY                                                   #
#  Craig Heither, last revised 04/05/2011                                   #
#                                                                           #
#    This program updates the location of rail network nodes after any of   # 
#    the following edits have been made to the arcs:                        #
#         - arcs deleted,                                                   #
#         - existing arc ends moved,                                        #
#         - new arcs digitized or                                           #
#         - existing arcs split (no more than 2 splits per link at 1 time). #
#                                                                           #
#    It also re-builds all routes based on the arc geometry to ensure they  #
#    are coincident with the underlying links. Additionally, the itinerary  #
#    table coding is updated to remove the segments of routes that have     #
#    been deleted from the route feature class.                             #
#                                                                           #
#                        -------------------------                          #
#  revision summary:                                                        #
#   05-18-2010: topology validation dropped from script.                    #
#   06-03-2010: added coding to update route geometry when run.             #
#   09-14-2010: updated for ArcMap 10 (arcgisscripting replaced by arcpy &  #
#               revised cursor coding based on ESRI changes).               #
#   04-05-2011: SAS call moved to sasrun.bat.                               #
#                                                                           #
#############################################################################

# ---------------------------------------------------------------
# Import System Modules
# ---------------------------------------------------------------
import sys, string, os, arcpy, subprocess, time, platform, datetime, fileinput
from datetime import date
from arcpy import env
arcpy.OverwriteOutput = 1


# ---------------------------------------------------------------
# Local variables
# ---------------------------------------------------------------
c = "V:\Secure\Master_Rail"                            # working directory

d = string.replace(c, "\\", '\\\\')
e = d + os.sep + os.sep + "Temp"
f = string.replace(c, "\\", '/') + "/Programs"
railnet_arc = "railnet_arc"
railnet_node = "railnet_node"
railnet_route_rail_lines = "railnet_route_rail_lines"

rail_test = e
temp_arcstart_shp = e + os.sep + os.sep + "temp_arcstart.shp"
temp_arcend_shp = e + os.sep + os.sep + "temp_arcend.shp"
temp_node_shp = e + os.sep + os.sep + "temp_node.shp"
new_node_dbf = e + os.sep + os.sep + "new_node.dbf"
temp_node_Layer = e + os.sep + os.sep + "temp_node_Layer"
temp = d + os.sep + os.sep + "mrn.gdb\\temp"
mrn_gdb = d + os.sep + os.sep + "mrn.gdb"
railnet = mrn_gdb + os.sep + os.sep + "railnet"
railnd = railnet + "\\railnet_node"
railrt = railnet + "\\railnet_route_rail_lines"
new_mile_dbf = e + os.sep + os.sep + "new_mile.dbf"
infl = e + os.sep + os.sep + "geom_in.txt"
test = railnet + os.sep + os.sep + "test"
rte_updt = e + os.sep + os.sep + "rte_updt.dbf"
rte_updt_View = "rte_updt_View"
t = date.today()
x = date.__str__(t)
x1 = string.replace(x, "-", "")
orig_itinerary_dbf = d + os.sep + os.sep + "itin_" + x1 + ".dbf"
itinerary = d + os.sep + os.sep + "mrn.gdb" + os.sep + os.sep + "itinerary"
new_segments_dbf = e + "\\new_segments.dbf"
rte_updt_dbf = e + "\\rte_updt.dbf"
outFl = e + os.sep + os.sep + "geom_out.txt"
infl = e + os.sep + os.sep + "geom_in.txt"
dropped_rtes = e + os.sep + os.sep + "dropped_routes.txt"
temp_route_shp = e + os.sep + os.sep + "temp_route.shp"

##set up to run SAS
bat = f + "/" + "sasrun.bat"                          # batch file name
fl = "update_nodes"                                   # SAS file name
z = f + "/" + fl + ".sas"
sas_log_file = c + "\\Temp\\" + fl + ".log"
sas_list_file = d + "\\Temp\\" + fl + ".lst"
cmd = [ bat, z, c, sas_log_file, sas_list_file ] 
fl2 = "geometry_update"                               # SAS file name
z2 = f + "/" + fl2 + ".sas"
y2 = c + "$" + x1 + "$skip$0"
sas_log_file2 = c + "\\Temp\\" + fl2 + ".log"
sas_list_file2 = d + "\\Temp\\" + fl2 + ".lst"
cmd2 = [ bat, z2, y2, sas_log_file2, sas_list_file2 ] 


# ---------------------------------------------------------------
# Cleanup files if needed
# ---------------------------------------------------------------
if os.path.exists(temp_arcend_shp):
    arcpy.Delete_management(temp_arcend_shp, "ShapeFile")
if os.path.exists(temp_arcstart_shp):
    arcpy.Delete_management(temp_arcstart_shp, "ShapeFile")
if os.path.exists(temp_node_shp):
    arcpy.Delete_management(temp_node_shp, "ShapeFile")
if os.path.exists(temp_node_Layer):
    arcpy.Delete_management(temp_node_Layer, "Layer")
if os.path.exists(new_node_dbf):
    arcpy.Delete_management(new_node_dbf, "DbaseTable")
if os.path.exists(new_mile_dbf):
    arcpy.Delete_management(new_mile_dbf, "DbaseTable")
if os.path.exists(orig_itinerary_dbf):
    arcpy.Delete_management(orig_itinerary_dbf, "DbaseTable")
if os.path.exists(new_segments_dbf):
    arcpy.Delete_management(new_segments_dbf, "DbaseTable")
if os.path.exists(rte_updt_dbf):
    arcpy.Delete_management(rte_updt_dbf, "DbaseTable")
if os.path.exists(temp_route_shp):
    arcpy.Delete_management(temp_route_shp, "ShapeFile")
if os.path.exists(test):
    arcpy.Delete_management(test)
if os.path.exists(temp):
    arcpy.Delete_management(temp)
if os.path.exists(rte_updt_View):
    arcpy.Delete_management(rte_updt_View)
if os.path.exists(sas_list_file):
    os.remove(sas_list_file)
if os.path.exists(sas_list_file2):
    os.remove(sas_list_file2)
if os.path.exists(outFl):
    os.remove(outFl)
if os.path.exists(infl):
    os.remove(infl)
if os.path.exists(dropped_rtes):
    os.remove(dropped_rtes)

try:
    arcpy.DeleteField_management(railnet_arc, "newmile;tempa;tempb")
except:
    print arcpy.GetMessages(2)


# ---------------------------------------------------------------
# Convert Arc Ends to Points & Add Coordinates
# ---------------------------------------------------------------
arcpy.AddMessage("---> Updating Node Locations")
arcpy.SelectLayerByAttribute_management(railnet_arc, "CLEAR_SELECTION", "")
arcpy.FeatureVerticesToPoints_management(railnet_arc, temp_arcstart_shp, "START")
arcpy.AddXY_management(temp_arcstart_shp)
arcpy.FeatureVerticesToPoints_management(railnet_arc, temp_arcend_shp, "END")
arcpy.AddXY_management(temp_arcend_shp)


# ---------------------------------------------------------------
# Make a Copy of Current Nodes and Run SAS to Process Changes
# ---------------------------------------------------------------
arcpy.FeatureClassToFeatureClass_conversion(railnet_node, rail_test, "temp_node.shp", "", "", "")
subprocess.call(cmd)
if os.path.exists(sas_list_file):
    arcpy.AddMessage("---> SAS Processing Error!! Review the List File: " + sas_list_file)
    arcpy.AddMessage("---> If there is an Errorlevel Message, Review the Log File: " + sas_log_file)
    arcpy.AddMessage("-------------------------------------------------------------------")
    sys.exit[1]                                     


# ---------------------------------------------------------------
# Update Node Feature Class Based on Changes
# ---------------------------------------------------------------
arcpy.AddMessage("---> Updating Node Feature Class")
arcpy.MakeXYEventLayer_management(new_node_dbf, "point_x", "point_y", temp_node_Layer, "PROJCS['NAD_1927_StatePlane_Illinois_East_FIPS_1201',GEOGCS['GCS_North_American_1927',DATUM['D_North_American_1927',SPHEROID['Clarke_1866',6378206.4,294.9786982]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Transverse_Mercator'],PARAMETER['False_Easting',500000.0],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',-88.33333333333333],PARAMETER['Scale_Factor',0.999975],PARAMETER['Latitude_Of_Origin',36.66666666666666],UNIT['Foot_US',0.3048006096012192]];IsHighPrecision")
arcpy.FeatureClassToFeatureClass_conversion(temp_node_Layer, mrn_gdb, "temp")
arcpy.SelectLayerByAttribute_management(railnet_node, "CLEAR_SELECTION", "")
arcpy.DeleteRows_management(railnet_node)
arcpy.Append_management(temp, railnet_node, "TEST", "", "") 
arcpy.Delete_management(temp)
arcpy.FeatureClassToFeatureClass_conversion(railnet_node, mrn_gdb, "temp")
arcpy.Delete_management(railnd)
arcpy.AddXY_management(temp)
arcpy.FeatureClassToFeatureClass_conversion(temp, railnet, "railnet_node")
arcpy.Delete_management(temp)


# ---------------------------------------------------------------
# Update Miles Value for Split Links and Assign Temporary
# Node Values to Maintain Unique Anode-Bnode Combinations
# ---------------------------------------------------------------   
if os.path.exists(new_mile_dbf):
    arcpy.AddMessage("---> Updating Miles Value for Split Links")
    arcpy.JoinField_management(railnet_arc, "OBJECTID", new_mile_dbf, "ORIG_FID", "newmile;tempa;tempb")
    arcpy.SelectLayerByAttribute_management(railnet_arc, "NEW_SELECTION", "\"newmile\" > 0")
    arcpy.CalculateField_management(railnet_arc, "MILES", "!newmile!", "PYTHON", "")
    arcpy.AddMessage("---> Assigning Temporary Anode/Bnode Value for Split Links")
    arcpy.CalculateField_management(railnet_arc, "ANODE", "!tempa!", "PYTHON", "")
    arcpy.CalculateField_management(railnet_arc, "BNODE", "!tempb!", "PYTHON", "")
    arcpy.DeleteField_management(railnet_arc, "newmile;tempa;tempb")
else:
    arcpy.AddMessage("---> No Split Links to Update")


# ---------------------------------------------------------------
# Rebuild Routes Using Arc Geometry
# ---------------------------------------------------------------   
## << Part 1: Write Arc Geometry to File >> ##
arcpy.TableSelect_analysis(itinerary, orig_itinerary_dbf, "\"OBJECTID\" >= 1")
arcpy.SelectLayerByAttribute_management(railnet_route_rail_lines, "CLEAR_SELECTION", "")
arcpy.SelectLayerByAttribute_management(railnet_arc, "CLEAR_SELECTION", "")
arcpy.FeatureClassToFeatureClass_conversion(railnet_route_rail_lines, e, "temp_route.shp", "", "", "")
outFile = open(r"V:\Secure\Master_Rail\Temp\geom_out.txt", "w")

f = 1                                             # row id number
for row in arcpy.SearchCursor(railnet_arc):       # loop through rows (features)
    for part in row.Shape:                        # loop through feature parts
        pnt = part.next()
        while pnt:                                # loop through vertices
            outFile.write(str(row.getValue("Anode")) + ";" + str(row.getValue("Bnode")) + ";" + str(row.getValue("Directions")) + ";" + str(row.getValue("Miles")) + ";" + row.getValue("Modes1") + ";" + row.getValue("Modes2") + ";" + str(f) + ";" + str(pnt.X) + ";" + str(pnt.Y) + "\n")
            pnt = part.next()
            if not pnt:
                pnt = part.next()

    f += 1
    
f -= 1
arcpy.AddMessage("---> Geometry Written for " + str(f) + " Arcs")
outFile.close()

## << Part 2: Process Data to Create New Route Geometry >> ##
subprocess.call(cmd2)
if os.path.exists(sas_list_file2):
    arcpy.AddMessage("---> SAS Processing Error!! Review the List File: " + sas_list_file2)
    arcpy.AddMessage("---> If there is an Errorlevel Message, Review the Log File: " + sas_log_file2)
    arcpy.AddMessage("-------------------------------------------------------------------")
    sys.exit[1]                                     


## << Part 3: Create Routes with Updated Geometry >> ##
arcpy.DeleteRows_management(railnet_route_rail_lines)
arcpy.AddMessage("---> Writing New Route Geometry")
cur = arcpy.InsertCursor(railnet_route_rail_lines)
lineArray = arcpy.Array()
pnt = arcpy.Point()

ID = -1
for line in fileinput.input(infl):                           # open geometry file
    pnt.ID, pnt.X, pnt.Y, pnt.M = string.split(line,";")     # assign point properties
    if ID == -1:
        ID = pnt.ID
    if ID != pnt.ID:
        feat = cur.newRow()                                  # create a new feature if ID ne pnt.ID
        feat.shape = lineArray                               # set feature geometry to the array of points
        cur.insertRow(feat)                                  # insert the feature
        lineArray.removeAll()
            
    lineArray.add(pnt)
    ID = pnt.ID

feat = cur.newRow()                                          # add last feature
feat.shape = lineArray
cur.insertRow(feat)
lineArray.removeAll()
fileinput.close()
del cur

arcpy.FeatureClassToFeatureClass_conversion(railnet_route_rail_lines, railnet, "test")
arcpy.AddMessage("---> Joining Data to Feature Class")
arcpy.MakeTableView_management(rte_updt, rte_updt_View)
arcpy.AddIndex_management(rte_updt_View, "id", "indx1", "UNIQUE", "ASCENDING")
arcpy.JoinField_management(test, "OBJECTID", rte_updt_View, "id")
arcpy.AddMessage("---> Updating Route Values")
arcpy.CalculateField_management(test, "TR_LINE", "!line1!", "PYTHON")
arcpy.DeleteField_management(test, "line1")
arcpy.CalculateField_management(test, "DESCRIPTION", "!desc1!", "PYTHON")
arcpy.DeleteField_management(test, "desc1")
arcpy.AddMessage("     * attribute update 20% complete *")
arcpy.CalculateField_management(test, "MODE", "!mode1!", "PYTHON")
arcpy.DeleteField_management(test, "mode1")
arcpy.CalculateField_management(test, "VEH_TYPE", "!type1!", "PYTHON")
arcpy.DeleteField_management(test, "type1")
arcpy.AddMessage("     * attribute update 40% complete *")
arcpy.CalculateField_management(test, "HEADWAY", "!hdwy1!", "PYTHON")
arcpy.DeleteField_management(test, "hdwy1")
arcpy.CalculateField_management(test, "SPEED", "!speed1!", "PYTHON")
arcpy.DeleteField_management(test, "speed1")
arcpy.AddMessage("     * attribute update 60% complete *")
arcpy.CalculateField_management(test, "SCENARIO", "!scen1!", "PYTHON")
arcpy.DeleteField_management(test, "scen1")
arcpy.CalculateField_management(test, "FTR_HEADWAY", "!fhdwy1!", "PYTHON")
arcpy.DeleteField_management(test, "fhdwy1")
arcpy.AddMessage("     * attribute update 80% complete *")
arcpy.CalculateField_management(test, "ROCKFORD", "!rock1!", "PYTHON")
arcpy.DeleteField_management(test, "rock1")
arcpy.CalculateField_management(test, "NOTES", "!notes1!", "PYTHON")    
arcpy.DeleteField_management(test, "notes1")
arcpy.DeleteField_management(test, "id")
arcpy.AddMessage("     * attribute update 100% complete *")
arcpy.Delete_management(railrt)
arcpy.FeatureClassToFeatureClass_conversion(test, railnet, "railnet_route_rail_lines")
arcpy.Delete_management(test)

## << Part 4: Update Itinerary Table >> ##
if os.path.exists(new_segments_dbf):
    arcpy.AddMessage("---> Updating Rail Itinerary Coding")
    arcpy.DeleteRows_management(itinerary)
    arcpy.Append_management(new_segments_dbf, itinerary, "NO_TEST")
else:
    arcpy.AddMessage("---> ERROR: Itinerary Coding Not Updated!!")
    sys.exit[1]

## << Part 5: Identify Routes Dropped From Geodatabase >> ##
if os.path.exists(dropped_rtes):
    arcpy.AddMessage("---> ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! !")
    arcpy.AddMessage("---> Review " + dropped_rtes + " to see the list of routes deleted from the geodatabase.")
    arcpy.AddMessage("---> This is Not an Error - Just Information.")
    arcpy.AddMessage("---> ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! !")


# ---------------------------------------------------------------
# Cleanup files
# ---------------------------------------------------------------
arcpy.AddMessage("---> Removing Temporary Files")
if os.path.exists(temp_arcend_shp):
    arcpy.Delete_management(temp_arcend_shp, "ShapeFile")
if os.path.exists(temp_arcstart_shp):
    arcpy.Delete_management(temp_arcstart_shp, "ShapeFile")
if os.path.exists(temp_node_shp):
    arcpy.Delete_management(temp_node_shp, "ShapeFile")
if os.path.exists(temp_node_Layer):
    arcpy.Delete_management(temp_node_Layer, "Layer")
if os.path.exists(new_node_dbf):
    arcpy.Delete_management(new_node_dbf, "DbaseTable")
if os.path.exists(new_segments_dbf):
    arcpy.Delete_management(new_segments_dbf, "DbaseTable")
if os.path.exists(rte_updt_dbf):
    arcpy.Delete_management(rte_updt_dbf, "DbaseTable")
if os.path.exists(temp_route_shp):
    arcpy.Delete_management(temp_route_shp, "ShapeFile")
if os.path.exists(test):
    arcpy.Delete_management(test)
if os.path.exists(temp):
    arcpy.Delete_management(temp)
if os.path.exists(rte_updt_View):
    arcpy.Delete_management(rte_updt_View)
if os.path.exists(sas_list_file):
    os.remove(sas_list_file)
if os.path.exists(sas_list_file2):
    os.remove(sas_list_file2)
if os.path.exists(outFl):
    os.remove(outFl)
if os.path.exists(infl):
    os.remove(infl)

try:
    arcpy.DeleteField_management(railnet_arc, "newmile;tempa;tempb")
except:
    print arcpy.GetMessages(2)
