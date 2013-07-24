GOTO2040 / mrn_programs
=======================
The MRN Programs repository is a collection of (mostly) Python scripts used to administer the [Chicago Metropolitan Agency for Planning (CMAP)](http://www.cmap.illinois.gov)'s Master Rail Network [geodatabase](http://www.esri.com/software/arcgis/geodatabase). This geodatabase is used, in conjunction with the Master Highway Network, to generate travel demand modeling networks, which we use for all of our modeling needs, including [transportation conformity](http://www.cmap.illinois.gov/conformity-analysis).

The MRN itself contains information about all of the passenger rail lines within the 21-county CMAP modeling area, as well as all planned lines between now and 2040, all current CTA and Metra train runs, and planned future train service.

The scripts in this repository are used to import new GTFS rail data, maintain the integrity of the network after geometric edits have been made, and export data in a format suitable for input into [Emme](http://www.inrosoftware.com/en/products/emme/) modeling networks.
