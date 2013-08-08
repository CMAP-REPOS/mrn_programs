#############################################################################
# IMPORT_ROUTES.PY                                                          #
#  Craig Heither, last revised 06/03/2010                                   #
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


##======================================================================##
               ##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##
               ##       CHANGE FILE NAME HERE      ##
               ##~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~##

xls = "adg3.xls"                       # Excel file in Import\ storing rail route coding (extension must be .XLS not .XLSX)

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
if platform.release() == "XP":
    sascall = "C:/Program Files/SAS/SAS 9.1/sas.exe"
else:
    sascall = "C:/Program Files/SAS/SASFoundation/9.2/sas.exe"
cmd = [ bat, sascall, z, y, sas_log_file, sas_list_file ] 


# ---------------------------------------------------------------
# Cleanup files if needed
# ---------------------------------------------------------------
if os.path.exists(temp_route_shp):
    gp.Delete_management(temp_route_shp, "ShapeFile")
if os.path.exists(orig_itinerary_dbf):
    gp.Delete_management(orig_itinerary_dbf, "DbaseTable")
if os.path.exists(new_segments_dbf):
    gp.Delete_management(new_segments_dbf, "DbaseTable")
if os.path.exists(rte_updt):
    gp.Delete_management(rte_updt, "DbaseTable")
if os.path.exists(rte_updt_View):
    gp.Delete_management(rte_updt_View)
if os.path.exists(test):
    gp.Delete_management(test)
if os.path.exists(sas_list_file):
    os.remove(sas_list_file)
if os.path.exists(outFl):
    os.remove(outFl)
if os.path.exists(infl):
    os.remove(infl)


# ---------------------------------------------------------------
# Store a Copy of Current Route and Itinerary Coding
# ---------------------------------------------------------------
gp.AddMessage("---> Getting Current Itinerary and Route Data")
gp.TableSelect_analysis(itinerary, orig_itinerary_dbf, "\"OBJECTID\" >= 1")
gp.SelectLayerByAttribute_management(railnet_route_rail_lines, "CLEAR_SELECTION", "")
gp.FeatureClassToFeatureClass_conversion(railnet_route_rail_lines, e, "temp_route.shp", "", "", "")


# ---------------------------------------------------------------
# Write Current Arc Geometry to File
# ---------------------------------------------------------------   
gp.SelectLayerByAttribute_management(railnet_arc, "CLEAR_SELECTION", "")
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


# ---------------------------------------------------------------
# Process Data to Create New Route Coding and Update Geometry
# ---------------------------------------------------------------   
subprocess.call(cmd)
if os.path.exists(sas_list_file):
    gp.AddMessage("---> SAS Processing Error!! Review the List File: " + sas_list_file)
    gp.AddMessage("---> If there is an Errorlevel Message, Review the Log File: " + sas_log_file)
    gp.AddMessage("-------------------------------------------------------------------")
    sys.exit[1]                                     


# ---------------------------------------------------------------
# Rebuild All Routes with Updated Geometry and Coding
# ---------------------------------------------------------------
if os.path.exists(rte_updt):
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
else:
    gp.AddMessage("---> ERROR: Route Coding Not Updated!!")
    sys.exit[1]


# ---------------------------------------------------------------
# Update Itinerary Table
# ---------------------------------------------------------------   
if os.path.exists(new_segments_dbf):
    gp.AddMessage("---> Updating Rail Itinerary Coding")
    gp.DeleteRows_management(itinerary)
    gp.Append_management(new_segments_dbf, itinerary, "NO_TEST")
else:
    gp.AddMessage("---> ERROR: Itinerary Coding Not Updated!!")
    sys.exit[1]


# ---------------------------------------------------------------
# Cleanup files if needed
# ---------------------------------------------------------------
if os.path.exists(temp_route_shp):
    gp.Delete_management(temp_route_shp, "ShapeFile")
if os.path.exists(orig_itinerary_dbf):
    gp.Delete_management(orig_itinerary_dbf, "DbaseTable")
if os.path.exists(new_segments_dbf):
    gp.Delete_management(new_segments_dbf, "DbaseTable")
if os.path.exists(rte_updt):
    gp.Delete_management(rte_updt, "DbaseTable")
if os.path.exists(rte_updt_View):
    gp.Delete_management(rte_updt_View)
if os.path.exists(test):
    gp.Delete_management(test)
if os.path.exists(outFl):
    os.remove(outFl)
if os.path.exists(infl):
    os.remove(infl)


