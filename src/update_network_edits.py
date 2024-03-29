###############################################################################
# UPDATE_NETWORK_EDITS.PY                                                     #
# Craig Heither                                                               #
# Last revised 6/23/2017                                                      #
#                                                                             #
# This program updates the location of rail network nodes after any of        #
# the following edits have been made to the arcs:                             #
#     - arcs deleted,                                                         #
#     - existing arc ends moved,                                              #
#     - new arcs digitized or                                                 #
#     - existing arcs split (no more than 2 splits per link at 1 time).       #
#                                                                             #
# It also re-builds all routes based on the arc geometry to ensure they       #
# are coincident with the underlying links. Additionally, the itinerary       #
# table coding is updated to remove the segments of routes that have          #
# been deleted from the route feature class.                                  #
#                        -------------------------                            #
# Revision summary:                                                           #
#     05-18-2010: topology validation dropped from script.                    #
#     06-03-2010: added coding to update route geometry when run.             #
#     09-14-2010: updated for ArcMap 10 (arcgisscripting replaced by arcpy &  #
#                 revised cursor coding based on ESRI changes).               #
#     04-05-2011: SAS call moved to sasrun.bat.                               #
#     09-26-2011: For Route table update: Index and Table join procedures     #
#                 replaced by more efficient Search and Update cursor code.   #
#     01-23-2012: y2 variable for cmd2 re-written for new required parameters.#
#     08-07-2012: Revised to iterate through & update all route systems.      #
#     05-30-2017: revised to pass future route action codes to SAS for        #
#                 processing split links.                                     #
#     06-23-2017: revised to remove point_x0 and point_y0 fields from final   #
#                 node feature class.                                         #
###############################################################################

# ---------------------------------------------------------------
# Import System Modules
# ---------------------------------------------------------------
import sys, string, os, arcpy, subprocess, time, platform, datetime, fileinput
from datetime import date
from arcpy import env
arcpy.OverwriteOutput = 1

# Read script arguments.
param0 = arcpy.GetParameterAsText(0)  # geodatabase

# ---------------------------------------------------------------
# Local variables
# ---------------------------------------------------------------
srcdir = os.path.dirname(__file__)
tempdir = os.path.realpath(os.path.join(srcdir, '../temp'))
railnet_arc = "railnet_arc"
railnet_node = "railnet_node"
railnet_route_rail_lines = "railnet_route_rail_lines"
temp_arcstart_shp = os.path.join(tempdir, 'temp_arcstart.shp')
temp_arcend_shp = os.path.join(tempdir, 'temp_arcend.shp')
temp_node_shp = os.path.join(tempdir, 'temp_node.shp')
new_node_dbf = os.path.join(tempdir, 'new_node.dbf')
temp_node_Layer = os.path.join(tempdir, 'temp_node_Layer')
mrn_gdb = param0
temp = mrn_gdb + "\\temp"
railnet = mrn_gdb + "\\railnet"
railnd = railnet + "\\railnet_node"
new_mile_dbf = os.path.join(tempdir, 'new_mile.dbf')
deleted_node_dbf = os.path.join(tempdir, 'deleted_node.dbf')
test = railnet + "\\test"
rte_updt = os.path.join(tempdir, 'rte_updt.dbf')
t = date.today()
x = date.__str__(t)
x1 = string.replace(x, "-", "")
new_segments_dbf = os.path.join(tempdir, 'new_segments.dbf')
rte_updt_dbf = os.path.join(tempdir, 'rte_updt.dbf')
outFl = os.path.join(tempdir, 'geom_out.txt')
infl = os.path.join(tempdir, 'geom_in.txt')
outRtFl = os.path.join(tempdir, 'rte_out.txt')
dropped_rtes = os.path.join(tempdir, 'dropped_routes.txt')
temp_route_shp = os.path.join(tempdir, 'temp_route.shp')

##set up to run SAS
bat = os.path.join(srcdir, 'sasrun.bat')                          # batch file name
fl = "update_nodes"                                   # SAS file name
z = os.path.join(srcdir, fl + '.sas')
sas_log_file = os.path.join(tempdir, fl + '.log')
sas_list_file = os.path.join(tempdir, fl + '.lst')
cmd = [bat, z, tempdir, sas_log_file, sas_list_file]
fl2 = "geometry_update"                               # SAS file name
z2 = os.path.join(srcdir, fl2 + '.sas')
sas_log_file2 = os.path.join(tempdir, fl2 + '.log')
sas_list_file2 = os.path.join(tempdir, fl2 + '.lst')
fl3 = "verify_node_coords"
z3 = os.path.join(srcdir, fl3 + '.sas')
sas_log_file3 = os.path.join(tempdir, fl3 + '.log')
sas_list_file3 = os.path.join(tempdir, fl3 + '.lst')

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
if os.path.exists(deleted_node_dbf):
    arcpy.Delete_management(deleted_node_dbf, "DbaseTable")
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
if os.path.exists(sas_list_file):
    os.remove(sas_list_file)
if os.path.exists(sas_list_file2):
    os.remove(sas_list_file2)
if os.path.exists(sas_list_file3):
    os.remove(sas_list_file3)
if os.path.exists(outFl):
    os.remove(outFl)
if os.path.exists(infl):
    os.remove(infl)
if os.path.exists(outRtFl):
    os.remove(outRtFl)
if os.path.exists(dropped_rtes):
    os.remove(dropped_rtes)

try:
    arcpy.DeleteField_management(railnet_arc, "newmile;tempa;tempb")
except:
    print(arcpy.GetMessages(2))

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
arcpy.FeatureClassToFeatureClass_conversion(railnet_node, tempdir, "temp_node.shp", "", "", "")
subprocess.call(cmd)
if os.path.exists(sas_list_file):
    arcpy.AddMessage("---> SAS Processing Error!! Review the List File: " + sas_list_file)
    arcpy.AddMessage("---> If there is an Errorlevel Message, Review the Log File: " + sas_log_file)
    arcpy.AddMessage("-------------------------------------------------------------------")
    sys.exit([1])

# ---------------------------------------------------------------
# Verify node coordinates.
# ---------------------------------------------------------------
cmd3 = [ bat, z3, tempdir, sas_log_file3, sas_list_file3 ]
subprocess.call(cmd3)
if os.path.exists(sas_list_file3):
    arcpy.AddMessage("---> SAS Processing Error!! Review the List File: " + sas_list_file3)
    arcpy.AddMessage("---> If there is an Errorlevel Message, Review the Log File: " + sas_log_file3)
    arcpy.AddMessage("-------------------------------------------------------------------")
    sys.exit([1])

# ---------------------------------------------------------------
# Update Node Feature Class Based on Changes
# ---------------------------------------------------------------
arcpy.AddMessage("---> Updating Node Feature Class")
arcpy.MakeXYEventLayer_management(new_node_dbf, "point_x", "point_y", temp_node_Layer, "PROJCS['NAD_1927_StatePlane_Illinois_East_FIPS_1201',GEOGCS['GCS_North_American_1927',DATUM['D_North_American_1927',SPHEROID['Clarke_1866',6378206.4,294.9786982]],PRIMEM['Greenwich',0.0],UNIT['Degree',0.0174532925199433]],PROJECTION['Transverse_Mercator'],PARAMETER['False_Easting',500000.0],PARAMETER['False_Northing',0.0],PARAMETER['Central_Meridian',-88.33333333333333],PARAMETER['Scale_Factor',0.999975],PARAMETER['Latitude_Of_Origin',36.66666666666666],UNIT['Foot_US',0.3048006096012192]];IsHighPrecision")

fms = arcpy.FieldMappings()
fms.addTable(temp_node_Layer)
for i in ['pspace', 'pcost']:
    fm = fms.getFieldMap(fms.findFieldMapIndex(i))
    f_out = fm.outputField
    f_out.type = 'SmallInteger'
    fm.outputField = f_out
    fms.replaceFieldMap(fms.findFieldMapIndex(i), fm)
arcpy.FeatureClassToFeatureClass_conversion(temp_node_Layer, mrn_gdb, "temp", field_mapping=fms)

arcpy.DeleteField_management(temp, ["point_x0", "point_y0"])
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

## << Part 2: Process Data to Create New Route Geometry >> ##
env.workspace = railnet             ## point inside feature dataset
fcs = arcpy.ListFeatureClasses('',"arc")
fcs.remove("railnet_arc")

i = 0
for fc in fcs:
    arcpy.AddMessage("---> Updating Geometry for " + fcs[i] + " Route System ...")
    itinerary = os.path.join(mrn_gdb, fc + '_itin')
    orig_itinerary_dbf = os.path.join(tempdir,  fc + '_itin_' + x1 + '.dbf')
    orig_future_routes_dbf = os.path.join(tempdir, 'future_routes_' + x1 + '.dbf')
    ## Store copy of current itinerary coding for safekeeping ##
    if os.path.exists(orig_itinerary_dbf):
        arcpy.Delete_management(orig_itinerary_dbf, "DbaseTable")
    arcpy.TableSelect_analysis(itinerary, orig_itinerary_dbf, "\"OBJECTID\" >= 1")
    if os.path.exists(temp_route_shp):
        arcpy.Delete_management(temp_route_shp, "ShapeFile")

    ## Write route geometry for future routes ##
    railrt = railnet + "\\" + fc
    rail_lines = fc
    arcpy.SelectLayerByAttribute_management(rail_lines, "CLEAR_SELECTION", "")
    arcpy.FeatureClassToFeatureClass_conversion(rail_lines, tempdir, "temp_route.shp", "", "", "")
    if fc == "future":
        if os.path.exists(orig_future_routes_dbf):
            arcpy.Delete_management(orig_future_routes_dbf, "DbaseTable")
        arcpy.TableSelect_analysis(railrt, orig_future_routes_dbf, "\"OBJECTID\" >= 1")
        outFile = open(outRtFl, "w")
        f = 1                                             # row id number
        for row in arcpy.SearchCursor(railrt):            # loop through rows (features)
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

    ## Run SAS to Update Itineraries ##
    # -- finish set up to run SAS
    y2 = srcdir + "$" + tempdir + "$" + orig_itinerary_dbf + "$X$3$X$" + orig_future_routes_dbf
    cmd2 = [ bat, z2, y2, sas_log_file2, sas_list_file2 ]
    subprocess.call(cmd2)
    if os.path.exists(sas_list_file2):
        arcpy.AddMessage("---> SAS Processing Error!! Review the List File: " + sas_list_file2)
        arcpy.AddMessage("---> If there is an Errorlevel Message, Review the Log File: " + sas_log_file2)
        arcpy.AddMessage("-------------------------------------------------------------------")
        sys.exit([1])


    ## << Part 3a: Create Routes with Updated Geometry >> ##
    arcpy.DeleteRows_management(railrt)
    arcpy.AddMessage("---> Writing New Route Geometry for " + fc)
    cur = arcpy.InsertCursor(railrt)
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
    del cur                                                      # delete cursor to remove data locks


    ## << Part 3b: Update Route Attributes Using Data in Rte_Updt.dbf >> ##
    ##      -- This is much faster than indexing and joining used in the previous version of the script. -- ##
    blankcur = arcpy.UpdateCursor(railrt)
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
        if fc == "future":                                          # update variables unique to future rail coding
            b_row.SCENARIO = string.strip(d_row.getValue("scen1"))
            b_row.ACTION = d_row.getValue("action1")
            b_row.NOTES = d_row.getValue("notes1")
            b_row.TOD = d_row.getValue("tod1")
            b_row.TIP_ID = d_row.getValue("tipid1")
            b_row.COMPLETION_YEAR = d_row.getValue("comp1")
            b_row.RSP_ID = d_row.getValue("rspid1")
        elif fc in ("all_runs", "all_runs_base"):                                      # update variables unique to all_runs
            b_row.FEEDLINE = d_row.getValue("fdline")
            b_row.ROUTE_ID = d_row.getValue("r_id")
            b_row.LONGNAME = d_row.getValue("rln")
            b_row.DIRECTION = d_row.getValue("dir")
            b_row.TERMINAL = d_row.getValue("term")
            b_row.START = d_row.getValue("start")
            b_row.STRTHOUR = d_row.getValue("strthour")
            b_row.AM_SHARE = d_row.getValue("ampct")
        b_row.CT_VEH = d_row.getValue("ct_veh1")
        blankcur.updateRow(b_row)
    del blankcur, datacur, b_row, d_row                             # delete cursor to remove data locks


    arcpy.FeatureClassToFeatureClass_conversion(railrt, railnet, "test")
    arcpy.Delete_management(railrt)
    arcpy.FeatureClassToFeatureClass_conversion(test, railnet, fc)
    arcpy.Delete_management(test)
    # if os.path.exists(rte_updt_dbf):
    #     arcpy.Delete_management(rte_updt_dbf, "DbaseTable")
    # if os.path.exists(test):
    #     arcpy.Delete_management(test)
    # if os.path.exists(outRtFl):
    #     os.remove(outRtFl)


    ## << Part 4: Update Itinerary Table >> ##
    if os.path.exists(new_segments_dbf):
        arcpy.AddMessage("---> Updating Rail Itinerary Coding")
        arcpy.DeleteRows_management(itinerary)
        arcpy.Append_management(new_segments_dbf, itinerary, "NO_TEST")
        arcpy.CopyRows_management(itinerary, itinerary + "_temp_reset_oids")
        arcpy.Delete_management(itinerary)
        arcpy.CopyRows_management(itinerary + "_temp_reset_oids", itinerary)
        arcpy.Delete_management(itinerary + "_temp_reset_oids")

    else:
        if os.path.exists(new_mile_dbf):
            arcpy.AddMessage("---> ERROR: Itinerary Coding Not Updated!!")
            sys.exit([1])
        else:
            arcpy.AddMessage("---> NOTE: No changes were made to itinerary coding.")


    ## << Part 5: Identify Routes Dropped From Geodatabase >> ##
    if os.path.exists(dropped_rtes):
        arcpy.AddMessage("---> ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! !")
        arcpy.AddMessage("---> Review " + dropped_rtes + " to see the list of routes deleted from the geodatabase.")
        arcpy.AddMessage("---> This is Not an Error - Just Information.")
        arcpy.AddMessage("---> ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! ! !")

    i += 1

# ---------------------------------------------------------------
# Cleanup files
# ---------------------------------------------------------------
# arcpy.AddMessage("---> Removing Temporary Files")
# if os.path.exists(temp_arcend_shp):
#     arcpy.Delete_management(temp_arcend_shp, "ShapeFile")
# if os.path.exists(temp_arcstart_shp):
#     arcpy.Delete_management(temp_arcstart_shp, "ShapeFile")
# if os.path.exists(temp_node_shp):
#     arcpy.Delete_management(temp_node_shp, "ShapeFile")
# if os.path.exists(temp_node_Layer):
#    arcpy.Delete_management(temp_node_Layer, "Layer")
# if os.path.exists(new_node_dbf):
#     arcpy.Delete_management(new_node_dbf, "DbaseTable")
# if os.path.exists(new_segments_dbf):
#     arcpy.Delete_management(new_segments_dbf, "DbaseTable")
# if os.path.exists(temp_route_shp):
#     arcpy.Delete_management(temp_route_shp, "ShapeFile")
# if os.path.exists(temp):
#     arcpy.Delete_management(temp)
# if os.path.exists(sas_list_file):
#    os.remove(sas_list_file)
# if os.path.exists(sas_list_file2):
#     os.remove(sas_list_file2)
# if os.path.exists(sas_list_file3):
#     os.remove(sas_list_file3)
# if os.path.exists(outFl):
#     os.remove(outFl)
# if os.path.exists(infl):
#     os.remove(infl)
#
# try:
#     arcpy.DeleteField_management(railnet_arc, "newmile;tempa;tempb")
# except:
#     print arcpy.GetMessages(2)

arcpy.Compact_management(mrn_gdb)  # Keep GDB's filesize minimized
