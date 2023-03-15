"""
IMPORT_RAIL_CODING.PY
Heither
N. Ferguson

This program is used to import new or revised rail route coding into the
MRN geodatabase.  Input parameters, including the spreadsheet that holds
the coding, are specified when run as an ArcGIS script tool.

All routes are re-built based on the arc geometry to ensure they are
coincident with the underlying links.

Change log:
    06-03-2010  Added coding to update route geometry when run.
    09-14-2010  Updated for ArcMap 10 (arcgisscripting replaced by
                arcpy & revised cursor coding based on ESRI changes).
    04-05-2011  SAS call moved to sasrun.bat.
    09-26-2011  For Route table update: Index and Table join procedures
                replaced by more efficient Search and Update cursor code.
    01-24-2012  Revised to accept GTFS or spreadsheet coding.
    08-22-2017  Updates new future coding TOD field.
"""

# Import system modules.
import sys, os, arcpy, subprocess, time, platform, datetime, fileinput
from datetime import date
from arcpy import env
arcpy.OverwriteOutput = 1

# Local variables.
progdir = os.path.dirname(__file__)
mrndir = os.path.realpath(os.path.join(progdir, '..'))  # Working directory.
gdb = arcpy.GetParameterAsText(0)
tempdir = os.path.join(mrndir, 'temp')
link_fc = 'railnet_arc'
railnet = os.path.join(gdb, 'railnet')
t = date.today()
x = date.__str__(t)
x1 = str.replace(x, "-", "")
new_segments_dbf = os.path.join(tempdir, 'new_segments.dbf')
temp_route_shp = os.path.join(tempdir,'temp_route.shp')
outFl = os.path.join(tempdir,'geom_out.txt')
infl = os.path.join(tempdir,'geom_in.txt')
rte_updt = os.path.join(tempdir,'rte_updt.dbf')
test = os.path.join(railnet, 'test')
outRtFl = os.path.join(tempdir,'rte_out.txt')

# Read script arguments: coding input files.
param1 = arcpy.GetParameterAsText(1)  # future rail coding spreadsheet
param2 = arcpy.GetParameterAsText(2)  # transit feed route file
param3 = arcpy.GetParameterAsText(3)  # transit feed itinerary file
param4 = arcpy.GetParameterAsText(4)  # feature class to update

rail_routes = param4
railrt = os.path.join(railnet, param4)
itinerary = os.path.join(gdb, param4 + '_itin')
orig_itinerary_dbf = os.path.join(mrndir, param4 + '_itin_' + x1 + '.dbf')

if param1 != '':
    arcpy.AddMessage("---> Input Rail Coding Spreadsheet is " + param1 +" ..." )
    flag = "1"
    y = mrndir + "$" + orig_itinerary_dbf + "$" + param1 + "$" + flag + "$X"  # SAS -sysparm parameters
elif param2 != '' and param3 != '':
    arcpy.AddMessage("---> Transit Feed Input Route File is " + param2 +" ..." )
    arcpy.AddMessage("---> Transit Feed Input Itinerary File is " + param3 +" ..." )
    flag = "2"
    y = mrndir + "$" + orig_itinerary_dbf + "$" + param2 + "$" + flag + "$" + param3  # SAS -sysparm parameters
else:
    arcpy.AddMessage("---> You Must Enter the Appropriate Input File(s) to Run this Script!!!" )
    sys.exit([1])

# Set up to run SAS program
bat = os.path.join(progdir, 'sasrun.bat')  # batch file name
fl = 'geometry_update'  # SAS file name
z = os.path.join(progdir, fl + '.sas')
sas_log_file = os.path.join(tempdir, fl + '.log')
sas_list_file = os.path.join(tempdir, fl + '.lst')
cmd = [bat, z, y, sas_log_file, sas_list_file]  # SAS call

# Cleanup files if needed.
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

# Store a copy of current route and itinerary coding.
arcpy.AddMessage("---> Getting Current Itinerary and Route Data")
arcpy.TableSelect_analysis(itinerary, orig_itinerary_dbf, "\"OBJECTID\" >= 1")
arcpy.SelectLayerByAttribute_management(rail_routes, "CLEAR_SELECTION", "")
arcpy.FeatureClassToFeatureClass_conversion(rail_routes, tempdir, "temp_route.shp", "", "", "")

# Write current arc & route geometry to files.
arcpy.SelectLayerByAttribute_management(link_fc, "CLEAR_SELECTION", "")
outFile = open(outFl, "w")

f = 1  # row id number
for row in arcpy.SearchCursor(link_fc):  # loop through rows (features)
    for part in row.Shape:  # loop through feature parts
        pnt = part.next()
        while pnt:  # loop through vertices
            outFile.write(str(row.getValue("Anode")) + ";"
                          + str(row.getValue("Bnode")) + ";"
                          + str(row.getValue("Directions")) + ";"
                          + str(row.getValue("Miles")) + ";"
                          + row.getValue("Modes1") + ";"
                          + row.getValue("Modes2") + ";"
                          + str(f) + ";"
                          + str(pnt.X) + ";"
                          + str(pnt.Y) + "\n")
            pnt = part.next()
            if not pnt:
                pnt = part.next()

    f += 1

f -= 1
arcpy.AddMessage("---> Geometry Written for " + str(f) + " Arcs")
outFile.close()

if param1 != '':
    outFile = open(outRtFl, "w")
    f = 1  # row id number
    for row in arcpy.SearchCursor(rail_routes):  # loop through rows (features)
        for part in row.Shape:  # loop through feature parts
            pnt = part.next()
            while pnt:  # loop through vertices
                outFile.write(str(f) + ";"
                              + str(row.getValue("TR_LINE")) + ";"
                              +  str(pnt.X) + ";"
                              + str(pnt.Y) + ";"
                              + str(pnt.M) +"\n")
                pnt = part.next()
                if not pnt:
                    pnt = part.next()
        f += 1
    f -= 1
    arcpy.AddMessage("---> Geometry Written for " + str(f) + " Future Routes")
    outFile.close()

# Process data to create new route coding and update geometry.
arcpy.AddMessage("---> Creating Route Coding")
subprocess.call(cmd)
if os.path.exists(sas_list_file):
    arcpy.AddMessage("---> SAS Processing Error!! Review the List File: " + sas_list_file)
    arcpy.AddMessage("---> If there is an Errorlevel Message, Review the Log File: " + sas_log_file)
    arcpy.AddMessage("-------------------------------------------------------------------")
    sys.exit([1])

# Rebuild all routes with updated geometry and coding.
if os.path.exists(rte_updt):
    arcpy.AddMessage("---> Writing New Route Geometry")
    arcpy.DeleteRows_management(rail_routes)
    cur = arcpy.InsertCursor(rail_routes)
    lineArray = arcpy.Array()
    pnt = arcpy.Point()

    ID = -1
    for line in fileinput.input(infl):  # open geometry file
        pnt.ID, pnt.X, pnt.Y, pnt.M = str.split(line,";")  # assign point properties
        if ID == -1:
            ID = pnt.ID
        if ID != pnt.ID:
            feat = cur.newRow()  # create a new feature if ID ne pnt.id
            feat.shape = lineArray  # set feature geometry to the array of points
            cur.insertRow(feat)  # insert the feature
            lineArray.removeAll()

        lineArray.add(pnt)
        ID = pnt.ID

    feat = cur.newRow()  # add last feature
    feat.shape = lineArray
    cur.insertRow(feat)
    lineArray.removeAll()
    fileinput.close()
    del cur  # delete cursor to remove data locks

    blankcur = arcpy.UpdateCursor(rail_routes)
    datacur = arcpy.SearchCursor(rte_updt)
    arcpy.AddMessage("---> Updating Rail Line Data")
    for d_row in datacur:
        #arcpy.AddMessage("'{}', '{}', '{}'".format(d_row.getValue("tipid1"), d_row.getValue("comp1"), d_row.getValue("rspid1")))
        b_row = blankcur.next()
        b_row.TR_LINE = d_row.getValue("line1")
        b_row.DESCRIPTION = d_row.getValue("desc1")
        b_row.MODE = d_row.getValue("mode1")
        b_row.VEH_TYPE = d_row.getValue("type1")
        b_row.HEADWAY = d_row.getValue("hdwy1")
        b_row.SPEED = d_row.getValue("speed1")
        if flag == "1":                                # update variables unique to future rail coding
            b_row.TOD = str.strip(str(d_row.getValue("tod1")))
            b_row.SCENARIO = str.strip(str(d_row.getValue("scen1")))
            b_row.ACTION = d_row.getValue("action1")
            b_row.TIP_ID = d_row.getValue("tipid1")
            b_row.RSP_ID = d_row.getValue("rspid1")
            if d_row.getValue("comp1") == 0:
                b_row.COMPLETION_YEAR = None
            else:
                b_row.COMPLETION_YEAR = d_row.getValue("comp1")
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

        blankcur.updateRow(b_row)

    del blankcur, datacur, b_row, d_row  # delete cursor to remove data locks

    arcpy.FeatureClassToFeatureClass_conversion(rail_routes, railnet, "test")
    arcpy.Delete_management(railrt)
    arcpy.FeatureClassToFeatureClass_conversion(test, railnet, rail_routes)
    arcpy.Delete_management(test)
else:
    arcpy.AddMessage("---> ERROR: Route Coding Not Updated!!")
    sys.exit[1]

# Update itinerary table.
if os.path.exists(new_segments_dbf):
    arcpy.AddMessage("---> Updating Rail Itinerary Coding")
    arcpy.DeleteRows_management(itinerary)
    arcpy.Compact_management(gdb)  # reset OBJECTID to start at 1
    arcpy.Append_management(new_segments_dbf, itinerary, "NO_TEST")
    arcpy.CalculateField_management(itinerary, "LAYOVER", "!LAYOVER!.strip()", "PYTHON")
else:
    arcpy.AddMessage("---> ERROR: Itinerary Coding Not Updated!!")
    sys.exit[1]

# Cleanup files if needed.
if os.path.exists(temp_route_shp):
    arcpy.Delete_management(temp_route_shp, "ShapeFile")
if os.path.exists(new_segments_dbf):
    arcpy.Delete_management(new_segments_dbf, "DbaseTable")
if os.path.exists(rte_updt):
    arcpy.Delete_management(rte_updt, "DbaseTable")
if os.path.exists(test):
    arcpy.Delete_management(test)
if os.path.exists(outFl):
    os.remove(outFl)
if os.path.exists(infl):
    os.remove(infl)
if os.path.exists(outRtFl):
    os.remove(outRtFl)