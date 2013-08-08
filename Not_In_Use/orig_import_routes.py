#############################################################################
# IMPORT_ROUTES.PY                                                          #
#  Craig Heither, last revised 02/25/2010                                   #
#                                                                           #
#    This program is used to import new or revised rail route coding into   #
#    "railnet_route_rail_lines".  The "xls" variable listed below should be #
#    updated to identify the spreadsheet in the Import\ directory that      #
#    holds the coding.                                                      # 
#                                                                           # 
#############################################################################

# ---------------------------------------------------------------
# Import System Modules, Load Toolboxes, etc.
# ---------------------------------------------------------------
import sys, string, os, arcgisscripting, subprocess, time, platform, datetime
from datetime import date
gp = arcgisscripting.create(9.3)
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

xls = "ctr001.xls"                       # Excel file in Import\ storing rail route coding (extension must be .XLS not .XLSX)

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
temp_arc_shp = e + os.sep + os.sep + "temp_arc.shp"
new_itin_shp = e + os.sep + os.sep + "new_itin.shp"
Temp = e
t = date.today()
x = date.__str__(t)
x1 = string.replace(x, "-", "")
orig_itinerary_dbf = d + os.sep + os.sep + "itin_" + x1 + ".dbf"
itinerary = d + os.sep + os.sep + "mrn.gdb" + os.sep + os.sep + "itinerary"
new_segments_dbf = e + "\\new_segments.dbf"
dupl_rte_dbf = e + "\\dupl_rte.dbf"
junk_cov = e + "\\junk"
junk_route_tranpath = junk_cov + "\\route.tranpath"

##set up to run SAS program 1
bat = f + "/sasrun.bat"                                      # batch file name
fl = "rail_path"                                             # SAS file name
z = f + "/" + fl + ".sas"
y = c + "$" + xls
sas_log_file = d + "\\Temp\\" + fl + ".log"
sas_list_file = d + "\\Temp\\" + fl + ".lst"
if platform.release() == "XP":
    sascall = "C:/Program Files/SAS/SAS 9.1/sas.exe"
else:
    sascall = "C:/Program Files/SAS/SASFoundation/9.2/sas.exe"
cmd = [ bat, sascall, z, y, sas_log_file, sas_list_file ] 

##set up to run AML
afl = "make_route"                                           # AML file name
az = "&run " + f + "/" + afl + ".aml"
aml_message_txt = e + os.sep + os.sep + "aml_message.txt"    # AML Error file
watch_txt = e + os.sep + os.sep + "watch.txt"                # AML Watch file
cmd2 = [ u'arc', az, e ] 

##set up to run SAS program 2
fl2 = "update_import_routes"                                 # SAS file name
z2 = f + "/" + fl2 + ".sas"
y2 = c + "$" + x1
sas_log_file2 = d + "\\Temp\\" + fl2 + ".log"
sas_list_file2 = d + "\\Temp\\" + fl2 + ".lst"
cmd3 = [ bat, sascall, z2, y2, sas_log_file2, sas_list_file2 ] 

# ---------------------------------------------------------------
# Cleanup files if needed
# ---------------------------------------------------------------
if os.path.exists(temp_arc_shp):
    gp.Delete_management(temp_arc_shp, "ShapeFile")
if os.path.exists(new_itin_shp):
    gp.Delete_management(new_itin_shp, "ShapeFile")
if os.path.exists(orig_itinerary_dbf):
    gp.Delete_management(orig_itinerary_dbf, "DbaseTable")
if os.path.exists(new_segments_dbf):
    gp.Delete_management(new_segments_dbf, "DbaseTable")
if os.path.exists(dupl_rte_dbf):
    gp.Delete_management(dupl_rte_dbf, "DbaseTable")
if os.path.exists(sas_list_file):
    os.remove(sas_list_file)
if os.path.exists(sas_list_file2):
    os.remove(sas_list_file2)
if os.path.exists(aml_message_txt):
    os.remove(aml_message_txt)
if os.path.exists(watch_txt):
    os.remove(watch_txt)

try:
    gp.DeleteField_management(railnet_route_rail_lines, "dupl")
except:
    print gp.GetMessages(2)

gp.SelectLayerByAttribute_management(railnet_route_rail_lines, "CLEAR_SELECTION", "")
gp.SelectLayerByAttribute_management(railnet_arc, "CLEAR_SELECTION", "")


# ---------------------------------------------------------------
# Process Rail Coding and Build Routes in ARC
# ---------------------------------------------------------------
gp.FeatureClassToFeatureClass_conversion(railnet_arc, rail_test, "temp_arc.shp", "", "", "")
## Run SAS to Process/Re-format Rail Route Coding ##
subprocess.call(cmd)   
if os.path.exists(sas_list_file):
    gp.AddMessage("---> SAS Processing Error!! Review the List File: " + sas_list_file)
    gp.AddMessage("---> If there is an Errorlevel Message, Review the Log File: " + sas_log_file)
    gp.AddMessage("-------------------------------------------------------------------")
    sys.exit[1]                                     

## Build Routes in ARC ##
subprocess.call(cmd2)   
if os.path.exists(aml_message_txt):
    gp.AddMessage("---> AML Error!! Review the File " + aml_message_txt)
    gp.AddMessage("-------------------------------------------------------------------")
    sys.exit[1]


# ---------------------------------------------------------------
# Extract Current Itinerary Data
# ---------------------------------------------------------------
gp.AddMessage("---> Getting Current Itinerary Data")
gp.TableSelect_analysis(itinerary, orig_itinerary_dbf, "\"OBJECTID\" >= 1")     

      
# ---------------------------------------------------------------
# Process Changes and Update Rail Coding in Geodatabase
# ---------------------------------------------------------------
subprocess.call(cmd3)   
if os.path.exists(sas_list_file2):
    gp.AddMessage("---> SAS Processing Error!! Review the List File: " + sas_list_file2)
    gp.AddMessage("---> If there is an Errorlevel Message, Review the Log File: " + sas_log_file2)
    gp.AddMessage("-------------------------------------------------------------------")
    sys.exit[1]      

if os.path.exists(dupl_rte_dbf):
    gp.AddMessage("---> Removing Routes with Updated Coding from Rail Route Feature Class")
    gp.JoinField_management(railnet_route_rail_lines, "TR_LINE", dupl_rte_dbf, "TR_LINE", "dupl")
    gp.SelectLayerByAttribute_management(railnet_route_rail_lines, "NEW_SELECTION", "\"dupl\" = 1")
    gp.DeleteRows_management(railnet_route_rail_lines)
    gp.DeleteField_management(railnet_route_rail_lines, "dupl")
else:
    gp.AddMessage("---> No Routes to Remove from Rail Route Feature Class")
                             
if os.path.exists(junk_cov):
    gp.AddMessage("---> Appending New Routes to Rail Route Feature Class")
    gp.Append_management(junk_route_tranpath, railnet_route_rail_lines, "NO_TEST")
else:
    gp.AddMessage("---> New Route Coverage Does Not Exist!!")
    sys.exit[1]

if os.path.exists(new_segments_dbf):
    gp.AddMessage("---> Updating Rail Itinerary Coding")
    gp.DeleteRows_management(itinerary)
    gp.Append_management(new_segments_dbf, itinerary, "NO_TEST")
else:
    gp.AddMessage("---> No New Itinerary Coding Added!!")
  

# ---------------------------------------------------------------
# Cleanup files if needed
# ---------------------------------------------------------------
if os.path.exists(temp_arc_shp):
    gp.Delete_management(temp_arc_shp, "ShapeFile")
if os.path.exists(new_itin_shp):
    gp.Delete_management(new_itin_shp, "ShapeFile")
if os.path.exists(junk_cov):
    gp.Delete_management(junk_cov, "Coverage")
if os.path.exists(new_segments_dbf):
    gp.Delete_management(new_segments_dbf, "DbaseTable")
if os.path.exists(dupl_rte_dbf):
    gp.Delete_management(dupl_rte_dbf, "DbaseTable")
if os.path.exists(sas_list_file):
    os.remove(sas_list_file)
if os.path.exists(sas_list_file2):
    os.remove(sas_list_file2)
if os.path.exists(aml_message_txt):
    os.remove(aml_message_txt)
if os.path.exists(watch_txt):
    os.remove(watch_txt)
