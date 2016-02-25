''' LINKSHAPE.PY
    Nick Ferguson
    Created 07/16/2013
    Last Revised 02/25/2016

    PURPOSE:
    This module is called by
    create_scenario_files_GTFS.py to create
    link shape batchin files for each scenario

    REVISIONS:
    - NRF 02/25/2016: Added a sort to the write_vertices function to solve a batchin problem
      related to reverse direction vertices being listed in order from last to first. Emme expects
      them to be ordered from first to last.
    
----------------------------------------------------------------------------'''
# -----------------------------------------------------------------------------
# Initiate Module
# -----------------------------------------------------------------------------
import arcpy, csv, time

# -----------------------------------------------------------------------------
# Write Arc Vertices to File
# -----------------------------------------------------------------------------
def write_vertices(in_arcs, out_vertices):    # parameters: (arc feature class [str], vertex file path [str])
    with open(out_vertices, 'wb') as vrtxfile:
        vrtxwriter = csv.writer(vrtxfile)
        with arcpy.da.SearchCursor(in_arcs, ['SHAPE@','ANODE','BNODE']) as cursor:
            f = 0    # feature count
            for row in cursor:    # loop through features
                arc = row[0]
                v1 = 0    # vertex id in direction 1
                v2 = 1    # vertex id in direction 2
                for part in arc:
                    vertex = part.next()
                    while vertex:
                        v2 += 1    # count number of vertices
                        vertex = part.next()
                    if not vertex:
                        vertex = part.next
                for part in arc:    # loop through feature parts
                    vertex = part.next()
                    while vertex:    # loop through vertices
                        v1 += 1
                        v2 -= 1
                        vrtxwriter.writerow([row[1], row[2], v1, vertex.X, vertex.Y])    # reference for anode-bnode direction
                        vrtxwriter.writerow([row[2], row[1], v2, vertex.X, vertex.Y])    # reference for bnode-anode direction
                        vertex = part.next()
                    if not vertex:
                        vertex = part.next()

                f += 1

            arcpy.AddMessage("---> Vertices Written for " + str(f) + " Arcs")
            
    with open(out_vertices, 'rb') as vrtxfile:
        vrtxcsv = csv.reader(vrtxfile, delimiter = ',')
        for col in (2, 1, 0):
            vrtxcsv = sorted(vrtxcsv, key = lambda row: int(row[col]))    # results in records sorted by from node, then by to node, then by vertex order
    
    with open(out_vertices, 'wb') as vrtxfile:
        vrtxwriter = csv.writer(vrtxfile)
        for row in vrtxcsv:
            vrtxwriter.writerow([row[0], row[1], row[2], row[3], row[4]])    # overwrite vertex file with sorted records

# -----------------------------------------------------------------------------
# Create Link Shape File
# -----------------------------------------------------------------------------
def create(in_arcs, in_links, vertices, out_linkshape, scenario):    # parameters: (arc feature class [str], scenario link file path [str], vertex file path [str], scenario linkshape file path [str], scenario number [str])
    with open(out_linkshape, 'w') as lnkshpfile:
        lnkshpfile.write('c RAIL LINK SHAPE FILE FOR SCENARIO {0}\n'.format(scenario))
        lnkshpfile.write('c {0}\n'.format(time.strftime('%d%b%y', time.localtime()).upper()))
        lnkshpfile.write('t linkvertices\n')

        write_vertices(in_arcs, vertices)

        with open(in_links, 'rb') as lnkfile:
            lnkreader = csv.reader(lnkfile)
            l = 0    # link counter
            for link in lnkreader:    # loop through scenario links
                fnode = link[0]
                tnode = link[1]
                lnkshpfile.write(' '.join(['r', fnode, tnode]) + '\n')
                with open(vertices, 'rb') as vrtxfile:
                    vrtxreader = csv.reader(vrtxfile)
                    for vertex in vrtxreader:    # loop through vertices
                        if vertex[0] == fnode and vertex[1] == tnode: # where vertex reference matches link
                            lnkshpfile.write(' '.join(['a', fnode, tnode, vertex[2], vertex[3], vertex[4]]) + '\n')

                l += 1

        arcpy.AddMessage("---> Shapes Written for " + str(l) + " Links")                    