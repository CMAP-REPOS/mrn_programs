#############################################################################
# IMPORT_ROUTES.PY                                                          #
#  Craig Heither, last revised 04/05/2011                                   #
#                                                                           #
#    This program is used to import new or revised rail route coding into   #
#    "railnet_route_rail_lines".  The "xls" variable listed below should be #
#    updated to identify the spreadsheet in the Import\ directory that      #
#    holds the coding.                                                      # 
#                                                                           # 
#    All routes are re-built based on the arc geometry to ensure they are   #
#    coincident with the underlying links.                                  #
#                                                                           # 
#                        -------------------------                          #
#  revision summary:                                                        #
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


##======================================================================##
               ##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##
               ##       CHANGE FILE NAME HERE      ##
               ##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##

xls = "mupnXX_2_mupnXX_3.xls"                       # Excel file in Import\ storing rail route coding (extension must be .XLS not .XLSX)

##======================================================================##

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

##set up to run SAS program
bat = f + "/sasrun.bat"                                      # batch file name
fl = "geometry_update"                                       # SAS file name
z = f + "/" + fl + ".sas"
y = c + "$" + x1 + "$" + xls + "$" + "1"
sas_log_file = d + "\\Temp\\" + fl + ".log"
sas_list_file = d + "\\Temp\\" + fl + ".lst"
cmd = [ bat, z, y, sas_log_file, sas_list_file ] 


# ---------------------------------------------------------------
# Cleanup files if needed
# ---------------------------------------------------------------
if os.path.exists(temp_route_shp):
    arcpy.Delete_management(temp_route_shp, "ShapeFile")
if os.path.exists(orig_itinerary_dbf):
    arcpy.Delete_management(orig_itinerary_dbf, "DbaseTable")
if os.path.exists(new_segments_dbf):
    arcpy.Delete_management(new_segments_dbf, "DbaseTable")
if os.path.exists(rte_updt):
    arcpy.Delete_management(rte_updt, "DbaseTable")
if os.path.exists(rte_updt_View):
    arcpy.Delete_management(rte_updt_View)
if os.path.exists(test):
    arcpy.Delete_management(test)
if os.path.exists(sas_list_file):
    os.remove(sas_list_file)
if os.path.exists(outFl):
    os.remove(outFl)
if os.path.exists(infl):
    os.remove(infl)


# ---------------------------------------------------------------
# Store a Copy of Current Route and Itinerary Coding
# ---------------------------------------------------------------
arcpy.AddMessage("---> Getting Current Itinerary and Route Data")
arcpy.TableSelect_analysis(itinerary, orig_itinerary_dbf, "\"OBJECTID\" >= 1")
arcpy.SelectLayerByAttribute_management(railnet_route_rail_lines, "CLEAR_SELECTION", "")
arcpy.FeatureClassToFeatureClass_conversion(railnet_route_rail_lines, e, "temp_route.shp", "", "", "")


# ---------------------------------------------------------------
# Write Current Arc Geometry to File
# ---------------------------------------------------------------   
arcpy.SelectLayerByAttribute_management(railnet_arc, "CLEAR_SELECTION", "")
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


# ---------------------------------------------------------------
# Process Data to Create New Route Coding and Update Geometry
# ---------------------------------------------------------------   
subprocess.call(cmd)
if os.path.exists(sas_list_file):
    arcpy.AddMessage("---> SAS Processing Error!! Review the List File: " + sas_list_file)
    arcpy.AddMessage("---> If there is an Errorlevel Message, Review the Log File: " + sas_log_file)
    arcpy.AddMessage("-------------------------------------------------------------------")
    sys.exit[1]                                     


# ---------------------------------------------------------------
# Rebuild All Routes with Updated Geometry and Coding
# ---------------------------------------------------------------
if os.path.exists(rte_updt):
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
            feat = cur.newRow()                                  # create a new feature if ID ne pnt.id
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
    arcpy.CalculateField_management(test, "TR_LINE", "!line1!", "PYTHON_9.3")
    arcpy.DeleteField_management(test, "line1")
    arcpy.CalculateField_management(test, "DESCRIPTION", "!desc1!", "PYTHON_9.3")
    arcpy.DeleteField_management(test, "desc1")
    arcpy.AddMessage("     * attribute update 20% complete *")
    arcpy.CalculateField_management(test, "MODE", "!mode1!", "PYTHON_9.3")
    arcpy.DeleteField_management(test, "mode1")
    arcpy.CalculateField_management(test, "VEH_TYPE", "!type1!", "PYTHON_9.3")
    arcpy.DeleteField_management(test, "type1")
    arcpy.AddMessage("     * attribute update 40% complete *")
    arcpy.CalculateField_management(test, "HEADWAY", "!hdwy1!", "PYTHON_9.3")
    arcpy.DeleteField_management(test, "hdwy1")
    arcpy.CalculateField_management(test, "SPEED", "!speed1!", "PYTHON_9.3")
    arcpy.DeleteField_management(test, "speed1")
    arcpy.AddMessage("     * attribute update 60% complete *")
    arcpy.CalculateField_management(test, "SCENARIO", "!scen1!", "PYTHON_9.3")
    arcpy.DeleteField_management(test, "scen1")
    arcpy.CalculateField_management(test, "FTR_HEADWAY", "!fhdwy1!", "PYTHON_9.3")
    arcpy.DeleteField_management(test, "fhdwy1")
    arcpy.AddMessage("     * attribute update 80% complete *")
    arcpy.CalculateField_management(test, "ROCKFORD", "!rock1!", "PYTHON_9.3")
    arcpy.DeleteField_management(test, "rock1")
    arcpy.CalculateField_management(test, "NOTES", "!notes1!", "PYTHON_9.3")    
    arcpy.DeleteField_management(test, "notes1")
    arcpy.DeleteField_management(test, "id")
    arcpy.AddMessage("     * attribute update 100% complete *")
    arcpy.Delete_management(railrt)
    arcpy.FeatureClassToFeatureClass_conversion(test, railnet, "railnet_route_rail_lines")
    arcpy.Delete_management(test)
else:
    arcpy.AddMessage("---> ERROR: Route Coding Not Updated!!")
    sys.exit[1]


# ---------------------------------------------------------------
# Update Itinerary Table
# ---------------------------------------------------------------   
if os.path.exists(new_segments_dbf):
    arcpy.AddMessage("---> Updating Rail Itinerary Coding")
    arcpy.DeleteRows_management(itinerary)
    arcpy.Append_management(new_segments_dbf, itinerary, "NO_TEST")
else:
    arcpy.AddMessage("---> ERROR: Itinerary Coding Not Updated!!")
    sys.exit[1]


# ---------------------------------------------------------------
# Cleanup files if needed
# ---------------------------------------------------------------
if os.path.exists(temp_route_shp):
    arcpy.Delete_management(temp_route_shp, "ShapeFile")
if os.path.exists(new_segments_dbf):
    arcpy.Delete_management(new_segments_dbf, "DbaseTable")
if os.path.exists(rte_updt):
    arcpy.Delete_management(rte_updt, "DbaseTable")
if os.path.exists(rte_updt_View):
    arcpy.Delete_management(rte_updt_View)
if os.path.exists(test):
    arcpy.Delete_management(test)
if os.path.exists(outFl):
    os.remove(outFl)
if os.path.exists(infl):
    os.remove(infl)


