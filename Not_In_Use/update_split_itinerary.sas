/* UPDATE_SPLIT_ITINERARY.SAS
    Craig Heither, revised 07/13/10

   Program updates the values of itin_a and itin_b in the itinerary coding for rail routes whose links have been split.

  */

%let dir=%scan(&sysparm,1,$);     ***shapefile storage directory;
%let dt=%scan(&sysparm,2,$);      ***date of itinerary .dbf file;


   *** READ IN ITINERARY FILE ***;
proc import datafile="&dir.\itin_&dt..dbf" out=x replace;  
proc sort data=x; by itin_a itin_b; 

   *** READ IN FILE OF NEW ANODE VALUES ***;
proc import datafile="&dir.\Temp\temp_start_join.dbf" out=a replace;  
data a(keep=itin_a itin_b newa); set a; 
  rename anode=itin_a bnode=itin_b node=newa;
  proc sort; by itin_a itin_b; 

   *** READ IN FILE OF NEW BNODE VALUES ***;
proc import datafile="&dir.\Temp\temp_end_join.dbf" out=b replace;  
data b(keep=itin_a itin_b newb); set b; 
  rename anode=itin_a bnode=itin_b node=newb;
  proc sort; by itin_a itin_b;

   *** LIMIT TO LINKS NEEDING UPDATE ***;
data a; merge a b; by itin_a itin_b;
  if itin_a=newa and itin_b=newb then delete;
data a(drop=c newc); set a;
  output;
  c=itin_a; itin_a=itin_b; itin_b=c; newc=newa; newa=newb; newb=newc;
  output;
  proc sort data=a; by itin_a itin_b; 

   *** UPDATE ITINERARY CODING ***;
data itin(drop=newa newb); merge x (in=hit) a; by itin_a itin_b; if hit;
  if newa>0 then itin_a=newa;
  if newb>0 then itin_b=newb;
   proc sort; by tr_line it_order;

   *** RE-ORDER VARIABLES ***;
data final; retain tr_line f_meas t_meas itin_a itin_b it_order layover dw_code dw_time zn_fare trv_time; set itin;

proc export data=final outfile="&dir.\Temp\new_segments.dbf" dbms=dbf replace;

run;
