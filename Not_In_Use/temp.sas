/* TEMP.SAS
    Craig Heither, last rev. 05/14/10

-------------                                   -------------
   TEMPORARY FIX. 
-------------                                   -------------
                                                                      */

%let inpath=%scan(&sysparm,1,$);


   *** READ IN ROUTES ***;
proc import datafile="&inpath.\Temp\temp_route.dbf" dbms=dbf out=rte replace; 
 proc sort data=rte; by tr_line;


   *** READ IN ITINERARY INFORMATION ***;
proc import datafile="&inpath.\Temp\temp2.dbf" dbms=dbf out=itin replace;  
  proc sort data=itin; by tr_line;

data itin; merge itin rte (in=hit); by tr_line; if hit;
data itin(keep=anode bnode);  set itin;
  anode=itin_a; bnode=itin_b;

data itin(drop=c); set itin;
  output;
  c=anode; anode=bnode; bnode=c;
  output;
   proc sort nodupkey; by anode bnode;


  *** READ IN ARC INFORMATION ***;
proc import datafile="&inpath.\Temp\temp3.dbf" dbms=dbf out=arc replace;  
data arc; set arc;
    proc sort; by anode bnode;
  

data all(keep=orig_fid inscen); merge arc (in=hit1) itin (in=hit2); by anode bnode;
 if hit1 & hit2;
  inscen=1;


proc export data=all outfile="&inpath.\Temp\temp4.dbf" dbms=dbf replace;


run;
