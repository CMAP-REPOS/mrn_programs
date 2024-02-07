# -*- coding: utf-8 -*-

import arcpy


class Toolbox:
    def __init__(self):
        """Define the toolbox (the name of the toolbox is the name of the
        .pyt file)."""
        self.label = "MRN Tools"
        self.alias = "MasterRailNetworkTools"

        # List of tool classes associated with this toolbox
        self.tools = [ExportNetworkByYear]


class ExportNetworkByYear:
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Export Network By Year"
        self.description = "Exports links and nodes for a build year as an Emme base network transaction file."

    def getParameterInfo(self):
        """Define the tool parameters."""
        param0 = arcpy.Parameter(displayName='Network links',
                                 name='links',
                                 datatype='GPFeatureLayer',
                                 parameterType='Required',
                                 direction='Input')
        param1 = arcpy.Parameter(displayName='Network nodes',
                                 name='nodes',
                                 datatype='GPFeatureLayer',
                                 parameterType='Required',
                                 direction='Input')
        param2 = arcpy.Parameter(displayName='Output file',
                                 name='outfile',
                                 datatype='DETextfile',
                                 parameterType='Required',
                                 direction='Output')
        param3 = arcpy.Parameter(displayName='Build year',
                                 name='year',
                                 datatype='GPLong',
                                 parameterType='Required',
                                 direction='Input')
        params = [param0, param1, param2, param3]
        return params

    def isLicensed(self):
        """Set whether the tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        """Modify the values and properties of parameters before internal
        validation is performed.  This method is called whenever a parameter
        has been changed."""
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter. This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        replaced_links = [# 12-10-0002
                          (42472, 42473),
                          # 01-12-0008
                          (32099, 32100),
                          (32100, 32101),
                          (32101, 32092)]
        
        def select_links_by_year(links, year):
            """
            Select rail links to represent a build year.
            """
            # Select current links.
            arcpy.management.SelectLayerByLocation(links,
                                                   'SHARE_A_LINE_SEGMENT_WITH',
                                                   'all_runs')
            # Add completed links from future.
            arcpy.management.SelectLayerByAttribute('future',
                                                    where_clause=f"COMPLETION_YEAR <= {year} AND SCENARIO <> '9'")
            arcpy.management.SelectLayerByLocation(links,
                                                   'SHARE_A_LINE_SEGMENT_WITH',
                                                   'future',
                                                   selection_type='ADD_TO_SELECTION')
            # Remove links replaced by future.
            for ab in replaced_links:
                arcpy.management.SelectLayerByAttribute(links,
                                                        'REMOVE_FROM_SELECTION',
                                                        f'ANODE = {ab[0]} And BNODE = {ab[1]}')
            return
        
        def select_nodes_by_link(nodes, links):
            """
            Select nodes for a set of links.
            """
            # Select nodes of links.
            arcpy.management.SelectLayerByLocation(nodes,
                                                   'INTERSECT',
                                                   links)
            return
        
        def generate_transaction_file(nodes, links, outfile, max_zid=3649):
            """
            Generate an Emme base network transaction file from nodes and links.
            """
            node_fields = ['NODE', 'POINT_X', 'POINT_Y', 'LABEL']       
            link_fields = ['ANODE', 'BNODE', 'MILES', 'MODES1', 'MODES2', 'DIRECTIONS']
            with open(outfile, 'w') as f:
                # Write node section to file.
                f.write('t nodes\n')
                with arcpy.da.SearchCursor(nodes, node_fields) as cursor:
                    for row in cursor:
                        update_code = 'a'
                        if row[0] <= max_zid:
                            update_code += '*'
                        f.write(f'{update_code} i={row[0]} xi={row[1]} yi={row[2]} lab={row[3]}\n')            
                # Write link section to file.
                f.write('t links\n')
                with arcpy.da.SearchCursor(links, link_fields) as cursor:
                    constant_fields = 'type=1 lanes=0 vdf=1'
                    for row in cursor:
                        f.write(f'a i={row[0]} j={row[1]} length={row[2]} modes={row[3]} {constant_fields}\n')
                        if row[5] == 2:
                            f.write(f'a i={row[1]} j={row[0]} length={row[2]} modes={row[4]} {constant_fields}\n')
            return
        
        select_links_by_year(parameters[0].valueAsText, parameters[3].valueAsText)
        select_nodes_by_link(parameters[1].valueAsText, parameters[0].valueAsText)
        generate_transaction_file(parameters[1].valueAsText, parameters[0].valueAsText, parameters[2].valueAsText)
        return

    def postExecute(self, parameters):
        """This method takes place after outputs are processed and
        added to the display."""
        return
