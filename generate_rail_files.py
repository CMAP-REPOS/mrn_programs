"""
GENERATE_RAIL_FILES.PY
Heither
N. Ferguson

This program creates the Emme batchin files needed to model a scenario
network.  The "scenario" and "path" variables are passed to the script
as arguments from the tool.  The following files are created:
    - rail.itinerary
    - rail.network
    - railnode.extatt
    - railseg.extatt

Scenario options beginning with OT2050 Update/C22Q2:
    100 - 2019 network
    200 - 2025 network
    300 - 2030 network
    400 - 2035 network
    500 - 2040 network
    600 - 2045 network
    700 - 2050 network

Change log:
    04-26-2012  Revised script & tool so that CT-RAMP output flag is
                available to use expanded list of transit vehicle types.
    06-19-2013  Added code to create temporary copy of people mover
                table.
    07-18-2013  Added ability to create link shape file by calling the
                create function from the linkshape module.
    12-20-2016  Updated to use 'all_runs_base' for scenario 200 after
                base year moved to 2015.
    06-28-2017  Updated to use ON TO 2050 scenario codes.
"""

import sys
import os
import subprocess
import time
import platform
import fileinput

import arcpy
from arcpy import env

import linkshape

arcpy.OverwriteOutput = 1

# Read arguments.
gdb = arcpy.GetParameterAsText(0)
scen_list = arcpy.GetParameterAsText(1).split(';')
outdir = arcpy.GetParameterAsText(2)
transitdir = os.path.join(outdir, 'transit')
if os.path.exists(transitdir):
    outdir = transitdir
else:
    os.mkdir(transitdir)
    outdir = transitdir

arcpy.AddMessage("---> gdb is " + gdb)

# Set local variables.
progdir = os.path.dirname(__file__)
mrndir = os.path.realpath(os.path.join(progdir, '..'))  # Working directory.
for scenario in scen_list:
    arcpy.AddMessage("---> Processing scenario " + scenario)
    current = "all_runs"  # Current routes.
    # Do not use 'all_runs_base' (2015) for base scenario in C22Q2 and
    # later (2019) until 'all_runs_base' has been updated to 2019.
    #if scenario = '100':
    #    current = 'all_runs_base'  # Base year routes.
    future = 'future'  # Future coding.
    rail_routes = current
    rail_routes_ftr = future
    railnet_arc = 'railnet_arc'
    railnet_node = 'railnet_node'
    temp = os.path.join(mrndir, 'temp')
    temp_route_shp = os.path.join(temp, 'temp_route.shp')
    temp_route_ftr_shp = os.path.join(temp, 'temp_route_ftr.shp')
    temp_arc_shp = os.path.join(temp, 'temp_arc.shp')
    temp_arc_ftr_shp = os.path.join(temp, 'temp_arc_ftr.shp')
    temp_ppl_mvr_dbf = os.path.join(temp, 'temp_ppl_mvr.dbf')
    itinerary = os.path.join(gdb, current + '_itin')
    itinerary_ftr = os.path.join(gdb, future + '_itin')
    people_mover = os.path.join(gdb, 'people_mover')
    scen_itin_dbf = os.path.join(temp, 'scen_itin.dbf')
    ftr_itin_dbf = os.path.join(temp, 'ftr_itin.dbf')
    zones = r'V:\Secure\Master_Rail\zones17\zones17.shp'
    temp_rlnode_zone_shp = os.path.join(temp, 'temp_rlnode_zone.shp')
    outFl = os.path.join(temp, 'rte_out.txt')
    link_list = os.path.join(outdir, scenario, 'rail_links_all.csv')
    vertex_list = os.path.join(outdir, scenario, 'railnet_vertex.csv')
    linkshape_file = os.path.join(outdir, scenario, 'rail.linkshape')

    # Set up to run SAS.
    bat = os.path.join(progdir, 'sasrun.bat')  # Batch file.
    sas_name = 'generate_rail_files'  # SAS file name.
    sas = os.path.join(progdir, sas_name + '.sas')
    sas_args = mrndir + "$" + outdir + "$" + scenario
    sas_log = os.path.join(temp, sas_name + '.log')
    sas_lst = os.path.join(temp, sas_name + '.lst')
    cmd = [bat, sas, sas_args, sas_log, sas_lst]

    # Clean up files, if needed.
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
    if os.path.exists(sas_lst):
        os.remove(sas_lst)
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

    # Create temp folder, if it does not exist.
    if not os.path.exists(temp):
        arcpy.AddMessage("---> Directory created: " + temp)
        os.mkdir(temp)

    # Create output folder, if it does not exist.
    if not os.path.exists(os.path.join(mrndir, 'output')):
        arcpy.AddMessage("---> Directory created: " + os.path.join(mrndir, 'output'))
        os.mkdir(os.path.join(mrndir, 'output'))

    # Extract data for scenario network.
    arcpy.AddMessage("---> Getting data for scenario " + scenario)
    arcpy.AddMessage("   * Obtaining Rail Routes...")
    arcpy.FeatureClassToFeatureClass_conversion(rail_routes, temp, "temp_route.shp", "", "", "")

    # Select the related arcs and add transfer and access/egress links.
    arcpy.AddMessage("   * Obtaining Rail Network Arcs...")
    arcpy.SelectLayerByLocation_management(railnet_arc, "SHARE_A_LINE_SEGMENT_WITH", rail_routes, "", "NEW_SELECTION")
    arcpy.SelectLayerByAttribute_management(railnet_arc, "ADD_TO_SELECTION", "\"MODES1\" <> 'C' AND \"MODES1\" <> 'M'")
    arcpy.FeatureClassToFeatureClass_conversion(railnet_arc, temp, "temp_arc.shp", "", "", "")

    # Select all nodes and intersect with zones.
    arcpy.AddMessage("   * Obtaining Rail Network Nodes...")
    arcpy.SpatialJoin_analysis(railnet_node, zones, temp_rlnode_zone_shp, "JOIN_ONE_TO_ONE", "KEEP_ALL", "", "INTERSECT", "", "")

    # Make a copy of the itinerary coding to use.
    arcpy.AddMessage("   * Obtaining Rail Itinerary Data...")
    arcpy.TableSelect_analysis(itinerary, scen_itin_dbf, "\"OBJECTID\" >= 1")

    # Make a copy of the people mover coding to use.
    arcpy.TableSelect_analysis(people_mover, temp_ppl_mvr_dbf, "\"OBJECTID\" >= 1")

    # Obtain extra data for future scenarios.
    #Do not skip this step for the base scenario until 'all_runs_base' has
    #been updated to the base scenario year.
    #if scenario != "100":
    arcpy.AddMessage("   * Obtaining Additional Data for Scenario " + scenario + " ...")
    arcpy.FeatureClassToFeatureClass_conversion(rail_routes_ftr, temp, "temp_route_ftr.shp", "", "", "")
    arcpy.SelectLayerByLocation_management(railnet_arc, "SHARE_A_LINE_SEGMENT_WITH", rail_routes_ftr, "", "NEW_SELECTION")
    arcpy.FeatureClassToFeatureClass_conversion(railnet_arc, temp, "temp_arc_ftr.shp", "", "", "")
    arcpy.TableSelect_analysis(itinerary_ftr, ftr_itin_dbf, "\"OBJECTID\" >= 1")

    # Write route geometry file - used for processing action==2.
    outFile = open(outFl, "w")
    f = 1  # Row ID number.
    for row in arcpy.SearchCursor(rail_routes_ftr):  # Loop through rows (features).
        for part in row.Shape:  # Loop through feature parts.
            pnt = part.next()
            while pnt:  # Loop through vertices.
                outFile.write(str(f) + ";" + str(row.getValue("TR_LINE")) + ";" + str(row.getValue("ACTION")) + ";" +  str(pnt.X) + ";" + str(pnt.Y) + "\n")
                pnt = part.next()
                if not pnt:
                    pnt = part.next()
        f += 1
    f -= 1
    arcpy.AddMessage("---> Geometry Written for " + str(f) + " Routes")
    outFile.close()

    # Create storage folder, if it does not exist.
    if not os.path.exists(os.path.join(outdir, scenario)):
        arcpy.AddMessage("---> Directory created: " + os.path.join(outdir, scenario))
        os.mkdir(os.path.join(outdir, scenario))

    # Run SAS to create Emme batchin files.
    arcpy.AddMessage("---> Creating Emme batchin files for scenario " + scenario)
    subprocess.call(cmd)
    if os.path.exists(sas_lst):
        arcpy.AddMessage("---> SAS Processing Error!! Review the List File: " + sas_lst)
        arcpy.AddMessage("---> If there is an Errorlevel Message, Review the Log File: " + sas_log)
        arcpy.AddMessage("-------------------------------------------------------------------")
        sys.exit([1])

    # Create linkshape file.
    arcpy.SelectLayerByAttribute_management(railnet_arc, 'CLEAR_SELECTION')
    linkshape.create(railnet_arc, link_list, vertex_list, linkshape_file, scenario)

    # Clean up files.
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
