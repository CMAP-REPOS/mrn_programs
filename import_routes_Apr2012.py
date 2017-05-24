#############################################################################
# IMPORT_ROUTES.PY                                                          #
#  Craig Heither, last revised 05/17/2012                                   #
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
#   09-26-2011: For Route table update: Index and Table join procedures     #
#               replaced by more efficient Search and Update cursor code.   #
#   01-24-2012: Revised to accept GTFS or spreadsheet coding.
#                                                                           #
#############################################################################


# ---------------------------------------------------------------------------

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
c = "C:\Master_Rail"                                                                                      # working directory
d = string.replace(c, "\\", '\\\\')
e = d + "\\Temp"
f = string.replace(c, "\\", '/') + "/mrn_programs"
rail_test = e
railnet_arc = "railnet_arc"
mrn_gdb = d + "\\mrn.gdb"
railnet = mrn_gdb + "\\railnet"
Temp = e
t = date.today()
x = date.__str__(t)
x1 = string.replace(x, "-", "")
new_segments_dbf = e + "\\new_segments.dbf"
temp_route_shp = e + "\\temp_route.shp"
outFl = e + "\\geom_out.txt"
infl = e + "\\geom_in.txt"
rte_updt = e + "\\rte_updt.dbf"
test = railnet + "\\test"
outRtFl = e + "\\rte_out.txt"


# ---------------------------------------------------------------
# Read Script Arguments: Coding Input Files
# ---------------------------------------------------------------
param1 = arcpy.GetParameterAsText(0)
param2 = arcpy.GetParameterAsText(1)
param3 = arcpy.GetParameterAsText(2)
param4 = arcpy.GetParameterAsText(3)
param5 = arcpy.GetParameterAsText(5)

rail_routes = param4
railrt = railnet + "\\" + param4
itinerary = d + "\\mrn.gdb\\" + param4 + "_itin"
orig_itinerary_dbf = d + "\\" + param4 + "_itin_" + x1 + ".dbf"


if param1 != '':
    arcpy.AddMessage("---> Input Rail Coding Spreadsheet is " + param1 +" ..." )
    flag = "1"
    y = c + "$" + orig_itinerary_dbf + "$" + param1 + "$" + flag + "$X"                                           # SAS -sysparm parameters
elif param2 != '' and param3 != '':
    arcpy.AddMessage("---> Transit Feed Input Route File is " + param2 +" ..." )
    arcpy.AddMessage("---> Transit Feed Input Itinerary File is " + param3 +" ..." )
    flag = "2"
    y = c + "$" + orig_itinerary_dbf + "$" + param2 + "$" + flag + "$" + param3 + "$" + param5                                  # SAS -sysparm parameters
else:
    arcpy.AddMessage("---> You Must Enter the Appropriate Input File(s) to Run this Script!!!" )
    sys.exit([1])


## -- set up to run SAS program --
bat = f + "/sasrun.bat"                                                                                           # batch file name
fl = "geometry_update"                                                                                            # SAS file name
z = f + "/" + fl + ".sas"
sas_log_file = d + "\\Temp\\" + fl + ".log"
sas_list_file = d + "\\Temp\\" + fl + ".lst"
cmd = [ bat, z, y, sas_log_file, sas_list_file ]                                                                  # SAS call



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
if os.path.exists(test):
    arcpy.Delete_management(test)
if os.path.exists(sas_list_file):
    os.remove(sas_list_file)
if os.path.exists(outFl):
    os.remove(outFl)
if os.path.exists(infl):
    os.remove(infl)
if os.path.exists(outRtFl):
    os.remove(outRtFl)


# ---------------------------------------------------------------
# Store a Copy of Current Route and Itinerary Coding
# ---------------------------------------------------------------
arcpy.AddMessage("---> Getting Current Itinerary and Route Data")
arcpy.TableSelect_analysis(itinerary, orig_itinerary_dbf, "\"OBJECTID\" >= 1")
arcpy.SelectLayerByAttribute_management(rail_routes, "CLEAR_SELECTION", "")
arcpy.FeatureClassToFeatureClass_conversion(rail_routes, e, "temp_route.shp", "", "", "")


# ---------------------------------------------------------------
# Write Current Arc & Route Geometry to Files
# ---------------------------------------------------------------   
arcpy.SelectLayerByAttribute_management(railnet_arc, "CLEAR_SELECTION", "")
outFile = open(outFl, "w")

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

if param1 != '':
    outFile = open(outRtFl, "w")
    f = 1                                             # row id number
    for row in arcpy.SearchCursor(rail_routes):       # loop through rows (features)
        for part in row.Shape:                        # loop through feature parts
            pnt = part.next()
            while pnt:                                # loop through vertices
                outFile.write(str(f) + ";" + str(row.getValue("TR_LINE")) + ";" +  str(pnt.X) + ";" + str(pnt.Y) + ";" + str(pnt.M) +"\n")
                pnt = part.next()
                if not pnt:
                    pnt = part.next()
        f += 1      
    f -= 1
    arcpy.AddMessage("---> Geometry Written for " + str(f) + " Future Routes")
    outFile.close()

# ---------------------------------------------------------------
# Process Data to Create New Route Coding and Update Geometry
# ---------------------------------------------------------------   
arcpy.AddMessage("---> Creating Route Coding")
subprocess.call(cmd)
if os.path.exists(sas_list_file):
    arcpy.AddMessage("---> SAS Processing Error!! Review the List File: " + sas_list_file)
    arcpy.AddMessage("---> If there is an Errorlevel Message, Review the Log File: " + sas_log_file)
    arcpy.AddMessage("-------------------------------------------------------------------")
    sys.exit([1])                                     


# ---------------------------------------------------------------
# Rebuild All Routes with Updated Geometry and Coding
# ---------------------------------------------------------------
if os.path.exists(rte_updt):
    arcpy.AddMessage("---> Writing New Route Geometry")
    arcpy.DeleteRows_management(rail_routes)
    cur = arcpy.InsertCursor(rail_routes)
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
    del cur                                                      # delete cursor to remove data locks

    blankcur = arcpy.UpdateCursor(rail_routes) 
    datacur = arcpy.SearchCursor(rte_updt) 
    arcpy.AddMessage("---> Updating Rail Line Data")
    for d_row in datacur:
        b_row = blankcur.next()
        b_row.TR_LINE = d_row.getValue("line1")
        b_row.DESCRIPTION = d_row.getValue("desc1")
        b_row.MODE = d_row.getValue("mode1")
        b_row.VEH_TYPE = d_row.getValue("type1")
        b_row.HEADWAY = d_row.getValue("hdwy1")
        b_row.SPEED = d_row.getValue("speed1")
        if flag == "1":                                          # update variables unique to future rail coding
            b_row.SCENARIO = string.strip(d_row.getValue("scen1"))
            b_row.ACTION = d_row.getValue("action1")
            b_row.NOTES = d_row.getValue("notes1")
        elif flag == "2":                                        # update variables unique to all_runs
            b_row.FEEDLINE = d_row.getValue("fdline")
            b_row.ROUTE_ID = d_row.getValue("r_id")
            b_row.LONGNAME = d_row.getValue("rln")
            b_row.DIRECTION = d_row.getValue("dir")
            b_row.TERMINAL = d_row.getValue("term")            
            b_row.START = d_row.getValue("start")
            b_row.STRTHOUR = d_row.getValue("strthour")
            b_row.AM_SHARE = d_row.getValue("ampct")
            b_row.CT_VEH = d_row.getValue("vehicle")
            
        blankcur.updateRow(b_row)

    del blankcur, datacur, b_row, d_row                          # delete cursor to remove data locks

    arcpy.FeatureClassToFeatureClass_conversion(rail_routes, railnet, "test")
    arcpy.Delete_management(railrt)
    arcpy.FeatureClassToFeatureClass_conversion(test, railnet, rail_routes)
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
    arcpy.Compact_management(mrn_gdb)    # reset OBJECTID to start at 1
    arcpy.Append_management(new_segments_dbf, itinerary, "NO_TEST")
    arcpy.CalculateField_management(itinerary, "LAYOVER", "!LAYOVER!.strip()", "PYTHON")
else:
    arcpy.AddMessage("---> ERROR: Itinerary Coding Not Updated!!")
    sys.exit[1]


# ---------------------------------------------------------------
# Cleanup files if needed
# ---------------------------------------------------------------
# if os.path.exists(temp_route_shp):
    # arcpy.Delete_management(temp_route_shp, "ShapeFile")
# if os.path.exists(new_segments_dbf):
    # arcpy.Delete_management(new_segments_dbf, "DbaseTable")
# if os.path.exists(rte_updt):
    # arcpy.Delete_management(rte_updt, "DbaseTable")
# if os.path.exists(test):
    # arcpy.Delete_management(test)
# if os.path.exists(outFl):
    # os.remove(outFl)
# if os.path.exists(infl):
    # os.remove(infl)
# if os.path.exists(outRtFl):
    # os.remove(outRtFl)

