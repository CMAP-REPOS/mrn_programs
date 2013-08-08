/* UPDATE_IMPORT_ROUTES.SAS
    Craig Heither, last rev. 04/09/10

-------------                                   -------------
   PROGRAM CREATES FILES TO UPDATE RAILNET_ROUTE_RAIL_LINES 
   FEATURE CLASS AND ITINERARY TABLE WITH NEW ROUTE CODING.
   STEP 4 OF PROCESS.
-------------                                   -------------
                                                                      */
%let path=%scan(&sysparm,1,$);     ***shapefile storage directory;
%let dt=%scan(&sysparm,2,$);       ***date of itinerary .dbf file;
%let tot=0;

  *** READ IN CURRENT RAIL ITINERARY INFORMATION ***;
proc import datafile="&path.\itin_&dt..dbf" out=itins replace;  
proc sort data=itins; by tr_line;


  *** READ IN IMPORTED RAIL ITINERARY INFORMATION ***;
proc import datafile="&path.\Temp\new_itin.dbf" out=newitin replace;  
data newitin(keep=tr_line f_meas t_meas itin_a itin_b it_order layover dw_code dw_time zn_fare trv_time); set newitin;
  proc sort; by tr_line;


   *** DETERMINE IF NEW CODING IS REPLACING AN EXISTING ROUTE ... ***;
data x; set itins; proc sort nodupkey; by tr_line;
data y; set newitin; proc sort nodupkey; by tr_line;
data x; set x y;
  proc freq; tables tr_line / noprint out=check;
data check(keep=tr_line); set check; if count>1;
  data temp; set check nobs=totobs; call symput('tot',left(put(totobs,8.))); run;   ***count observations in dataset;

   *** ... IF SO, DELETE OLD CODING & CREATE FILE LISTING DUPLICATED ROUTES ***;
%macro dup;
  %if &tot>0 %then %do;
     data itins; merge itins check (in=hit); by tr_line; if hit then delete;

     data check; set check; dupl=1;
     proc export data=check outfile="&path.\Temp\dupl_rte.dbf" dbms=dbf replace;
  %end;
%mend dup;
%dup
 /* end macro*/


data itins; retain tr_line f_meas t_meas itin_a itin_b it_order layover dw_code dw_time zn_fare trv_time; set itins newitin; 
  proc sort nodupkey; by tr_line it_order;
 proc export data=itins outfile="&path.\Temp\new_segments.dbf" dbms=dbf replace;

run;
