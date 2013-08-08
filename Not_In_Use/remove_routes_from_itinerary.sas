/* REMOVE_ROUTES_FROM_ITINERARY.SAS
    Craig Heither, last rev. 02/01/10

-------------                                   -------------
   PROGRAM REMOVES ITINERARY CODING FROM ITINERARY .DBF FOR
   ROTUES NOT IN RAILNET_ROUTE_RAIL_LINES. 
-------------                                   -------------
                                                                      */
%let path=%scan(&sysparm,1,$);     ***shapefile storage directory;
%let dt=%scan(&sysparm,2,$);       ***date of itinerary .dbf file;


   *** READ IN RAIL HEADER INFORMATION ***;
proc import datafile="&path.\Temp\temp_route.dbf" out=routes replace;  
data routes(keep=tr_line); set routes; proc sort; by tr_line;  


  *** READ IN RAIL ITINERARY INFORMATION ***;
proc import datafile="&path.\itin_&dt..dbf" out=itins replace;  
  proc sort data=itins; by tr_line it_order;

data itins; merge itins routes (in=hit); by tr_line; if hit;

       * - - - - - - - - - - - - - - - - - *;
            **REPORT LAYOVER PROBLEMS**;
         data check; set itins; if layover='' then layover='0'; l=input(layover,best4.);
         data check; set check; if l>0; proc freq; tables tr_line / noprint out=check;
         data check; set check; if count>2; proc print; title 'Too Many Layovers Coded';
       * - - - - - - - - - - - - - - - - - *;

proc export data=itins outfile="&path.\Temp\new_segments.dbf" dbms=dbf replace;


run;
