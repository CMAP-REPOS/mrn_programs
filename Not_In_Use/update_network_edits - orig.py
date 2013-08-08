#############################################################################
# UPDATE_NETWORK_EDITS.PY                                                   #
#  Craig Heither, last revised 06/03/2010                                   #
#                                                                           #
#    This program updates the location of rail network nodes after any of   # 
#    the following edits have been made to the arcs:                        #
#         - arcs deleted,                                                   #
#         - existing arc ends moved,                                        #
#         - new arcs digitized or                                           #
#         - existing arcs split (no more than 2 splits per link).           #
#                                                                           #
#    It also re-builds all routes based on the arc geometry to ensure they  #
#    are coincident with the underlying links. Additionally, the itinerary  #
#    table coding is updated to remove the segments of routes that have     #
#    been deleted from the route feature class.                             #
#                                                                           #
#                        -------------------------                          #
#  revision summary:                                                        #
#     rev. 05-18-2010: topology validation dropped from script.             #
#     rev. 06-03-2010: added coding to update route geometry when run.      #
#                                                                           #
#############################################################################

# ---------------------------------------------------------------
# Import System Modules, Load Toolboxes, etc.
# ---------------------------------------------------------------
import sys, string, os, arcgisscripting, subprocess, time, platform, datetime, fileinput
from datetime import date
gp = arcgisscripting.create(9.3)
gp.OverwriteOutput = 1
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
if platform.release() == "XP":
    sascall = "C:/Program Files/SAS/SAS 9.1/sas.exe"
else:
    sascall = "C:/Program Files/SAS/SASFoundation/9.2/sas.exe"
cmd = [ bat, sascall, z, c, sas_log_file, sas_list_file ] 
fl2 = "geometry_update"                               # SAS file name
z2 = f + "/" + fl2 + ".sas"
y2 = c + "$" + x1 + "$skip$0"
sas_log_file2 = c + "\\Temp\\" + fl2 + ".log"
sas_list_file2 = d + "\\Temp\\" + fl2 + ".lst"
cmd2 = [ bat, sascall, z2, y2, sas_log_file2, sas_list_file2 ] 


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
if os.path.exists(orig_itinerary_dbf):
    gp.Delete_management(orig_itinerary_dbf, "DbaseTable")
if os.path.exists(new_segments_dbf):
    gp.Delete_management(new_segments_dbf, "DbaseTable")
if os.path.exists(rte_updt_dbf):
    gp.Delete_management(rte_updt_dbf, "DbaseTable")
if os.path.exists(temp_route_shp):
    gp.Delete_management(temp_route_shp, "ShapeFile")
if os.path.exists(test):
    gp.Delete_management(test)
if os.path.exists(temp):
    gp.Delete_management(temp)
if os.path.exists(rte_updt_View):
    gp.Delete_management(rte_updt_View)
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
    gp.DeleteField_management(railnet_arc, "newmile;tempa;tempb")
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
gp.FeatureClassToFeatureClass_conversion(temp_node_Layer, mrn_gdb, "temp")
gp.SelectLayerByAttribute_management(railnet_node, "CLEAR_SELECTION", "")
gp.DeleteRows_management(railnet_node)
gp.Append_management(temp, railnet_node, "TEST", "", "") 
gp.Delete_management(temp)
gp.FeatureClassToFeatureClass_conversion(railnet_node, mrn_gdb, "temp")
gp.Delete_management(railnet_node)
gp.AddXY_management(temp)
gp.FeatureClassToFeatureClass_conversion(temp, railnet, "railnet_node")
gp.Delete_management(temp)


# ---------------------------------------------------------------
# Update Miles Value for Split Links and Assign Temporary
# Node Values to Maintain Unique Anode-Bnode Combinations
# ---------------------------------------------------------------   
if os.path.exists(new_mile_dbf):
    gp.AddMessage("---> Updating Miles Value for Split Links")
    gp.JoinField_management(railnet_arc, "OBJECTID", new_mile_dbf, "ORIG_FID", "newmile;tempa;tempb")
    gp.SelectLayerByAttribute_management(railnet_arc, "NEW_SELECTION", "\"newmile\" > 0")
    gp.CalculateField_management(railnet_arc, "MILES", "!newmile!", "PYTHON", "")
    gp.AddMessage("---> Assigning Temporary Anode/Bnode Value for Split Links")
    gp.CalculateField_management(railnet_arc, "ANODE", "!tempa!", "PYTHON", "")
    gp.CalculateField_management(railnet_arc, "BNODE", "!tempb!", "PYTHON", "")
    gp.DeleteField_management(railnet_arc, "newmile;tempa;tempb")
else:
    gp.AddMessage("---> No Split Links to Update")


# ---------------------------------------------------------------
# Update Route Geometry Using Arc Geometry
# ---------------------------------------------------------------   
## Part 1: Write Arc Geometry to File ##
gp.TableSelect_analysis(itinerary, orig_itinerary_dbf, "\"OBJECTID\" >= 1")
gp.SelectLayerByAttribute_management(railnet_route_rail_lines, "CLEAR_SELECTION", "")
gp.SelectLayerByAttribute_management(railnet_arc, "CLEAR_SELECTION", "")
gp.FeatureClassToFeatureClass_conversion(railnet_route_rail_lines, e, "temp_route.shp", "", "", "")
outFile = open(r"V:\Secure\Master_Rail\Temp\geom_out.txt", "w")
rows = gp.SearchCursor(railnet_arc)
row = rows.Next()
f = 1                                   # row id number

while row:
    feat = row.Shape
    partnum = 0
    partcount = feat.PartCount

    while partnum < partcount:
        part = feat.GetPart(partnum)
        pnt = part.Next()
        pntcount = 0

        while pnt:
            outFile.write(str(row.getvalue("Anode")) + ";" + str(row.getvalue("Bnode")) + ";" + str(row.getvalue("Directions")) + ";" + str(row.getvalue("Miles")) + ";" + row.getvalue("Modes1") + ";" + row.getvalue("Modes2") + ";" + str(f) + ";" + str(pnt.x) + ";" + str(pnt.y) + "\n")
            pnt = part.Next()
            pntcount += 1
            if not pnt:
                pnt = part.Next()

        partnum += 1
        
    f += 1
    row = rows.Next()
    
f -= 1
gp.AddMessage("---> Geometry Written for " + str(f) + " Arcs")
outFile.close()

## Part 2: Process Data to Create New Route Geometry ##
subprocess.call(cmd2)
if os.path.exists(sas_list_file2):
    gp.AddMessage("---> SAS Processing Error!! Review the List File: " + sas_list_file2)
    gp.AddMessage("---> If there is an Errorlevel Message, Review the Log File: " + sas_log_file2)
    gp.AddMessage("-------------------------------------------------------------------")
    sys.exit[1]                                     


## Part 3: Create Routes with Updated Geometry ##
gp.DeleteRows_management(railnet_route_rail_lines)
gp.AddMessage("---> Writing New Route Geometry")
cur = gp.InsertCursor(railnet_route_rail_lines)
lineArray = gp.CreateObject("Array")
pnt = gp.CreateObject("Point")

ID = -1
for line in fileinput.input(infl):                           # open geometry file
    pnt.id, pnt.x, pnt.y, pnt.m = string.split(line,";")     # assign point properties
    if ID == -1:
        ID = pnt.id

    if ID != pnt.id:
        feat = cur.NewRow()                                  # create a new feature if ID ne pnt.id
        feat.shape = lineArray                               # set feature geometry to the array of points

        cur.InsertRow(feat)                                  # insert the feature
        lineArray.RemoveAll()
            
    lineArray.add(pnt)
    ID = pnt.id

feat = cur.NewRow()
feat.shape = lineArray
cur.InsertRow(feat)
lineArray.RemoveAll()
fileinput.close()
del cur

gp.FeatureClassToFeatureClass_conversion(railnet_route_rail_lines, railnet, "test")
gp.AddMessage("---> Joining Data to Feature Class")
gp.MakeTableView_management(rte_updt, rte_updt_View)
gp.AddIndex_management(rte_updt_View, "id", "indx1", "UNIQUE", "ASCENDING")
gp.JoinField_management(test, "OBJECTID", rte_updt_View, "id")
gp.AddMessage("---> Updating Route Values")
gp.CalculateField_management(test, "TR_LINE", "!line1!", "PYTHON_9.3")
gp.DeleteField_management(test, "line1")
gp.CalculateField_management(test, "DESCRIPTION", "!desc1!", "PYTHON_9.3")
gp.DeleteField_management(test, "desc1")
gp.AddMessage("     * attribute update 20% complete *")
gp.CalculateField_management(test, "MODE", "!mode1!", "PYTHON_9.3")
gp.DeleteField_management(test, "mode1")
gp.CalculateField_management(test, "VEH_TYPE", "!type1!", "PYTHON_9.3")
gp.DeleteField_management(test, "type1")
gp.AddMessage("     * attribute update 40% complete *")
gp.CalculateField_management(test, "HEADWAY", "!hdwy1!", "PYTHON_9.3")
gp.DeleteField_management(test, "hdwy1")
gp.CalculateField_management(test, "SPEED", "!speed1!", "PYTHON_9.3")
gp.DeleteField_management(test, "speed1")
gp.AddMessage("     * attribute update 60% complete *")
gp.CalculateField_management(test, "SCENARIO", "!scen1!", "PYTHON_9.3")
gp.DeleteField_management(test, "scen1")
gp.CalculateField_management(test, "FTR_HEADWAY", "!fhdwy1!", "PYTHON_9.3")
gp.DeleteField_management(test, "fhdwy1")
gp.AddMessage("     * attribute update 80% complete *")
gp.CalculateField_management(test, "ROCKFORD", "!rock1!", "PYTHON_9.3")
gp.DeleteField_management(test, "rock1")
gp.CalculateField_management(test, "NOTES", "!notes1!", "PYTHON_9.3")    
gp.DeleteField_management(test, "notes1")
gp.DeleteField_management(test, "id")
gp.AddMessage("     * attribute update 100% complete *")
gp.Delete_management(railnet_route_rail_lines)
gp.FeatureClassToFeatureClass_conversion(test, railnet, "railnet_route_rail_lines")
gp.Delete_management(test)

## Part 4: Update Itinerary Table ##
if os.path.exists(new_segments_dbf):
    gp.AddMessage("---> Updating Rail Itinerary Coding")
    gp.DeleteRows_management(itinerary)
    gp.Append_management(new_segments_dbf, itinerary, "NO_TEST")
else:
    gp.AddMessage("---> ERROR: Itinerary Coding Not Updated!!")
    sys.exit[1]

## Part 5: Identify Routes Dropped From Geodatabase ##
if os.path.exists(dropped_rtes):
    gp.AddMessage("---> ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! !")
    gp.AddMessage("---> Review " + dropped_rtes + " to see the list of routes deleted from the geodatabase.")
    gp.AddMessage("---> This is Not an Error - Just Information.")
    gp.AddMessage("---> ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! !")


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
if os.path.exists(new_node_dbf):
    gp.Delete_management(new_node_dbf, "DbaseTable")
if os.path.exists(orig_itinerary_dbf):
    gp.Delete_management(orig_itinerary_dbf, "DbaseTable")
if os.path.exists(new_segments_dbf):
    gp.Delete_management(new_segments_dbf, "DbaseTable")
if os.path.exists(rte_updt_dbf):
    gp.Delete_management(rte_updt_dbf, "DbaseTable")
if os.path.exists(temp_route_shp):
    gp.Delete_management(temp_route_shp, "ShapeFile")
if os.path.exists(test):
    gp.Delete_management(test)
if os.path.exists(temp):
    gp.Delete_management(temp)
if os.path.exists(rte_updt_View):
    gp.Delete_management(rte_updt_View)
if os.path.exists(sas_list_file):
    os.remove(sas_list_file)
if os.path.exists(sas_list_file2):
    os.remove(sas_list_file2)
if os.path.exists(outFl):
    os.remove(outFl)
if os.path.exists(infl):
    os.remove(infl)

try:
    gp.DeleteField_management(railnet_arc, "newmile;tempa;tempb")
except:
    print gp.GetMessages(2)
