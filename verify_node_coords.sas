/* VERIFY_NODE_COORDS.SAS
   Nick Ferguson
   Created 05/01/13
   Last Revised 05/01/13

   INPUT:
   - Reads temp_arcstart.dbf to get updated anode coordinates.
   - Reads temp_arcend.dbf to get updated bnode coordinates.

   OUTPUT:
   - If there are nodes with multiple coordinate pairs,
     verify_node_coords.lst is created to list them.

   REVISIONS:

---------------------------------------------------------------*/

%let dir=&sysparm;    ***shapefile storage directory;

    *** READ IN BEGINNING NODES ***;
proc import datafile="&dir.\Temp\temp_arcstart.dbf" out=a0 replace; 
data a(keep=anode bnode point_x point_y); set a0; 

    *** READ IN ENDING NODES ***;
proc import datafile="&dir.\Temp\temp_arcend.dbf" out=b0 replace;
data b(keep=anode bnode point_x point_y); set b0; 

    *** VERIFY EACH NODE HAS ONLY ONE SET OF COORDINATES ***;
data chk1; set a; node=anode;
data chk2; set b; node=bnode;
data chk3; set chk1 chk2;

proc summary nway; class node point_x point_y; output out=chk; 
proc freq data=chk; tables node / noprint out=chk0;

data chk0; set chk0(where=(count>1));
proc print;
    title "These Nodes Have Multiple Coordinate Pairs";
    title2 "Edit the Network and Snap them Together";