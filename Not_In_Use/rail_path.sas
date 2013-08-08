/* rail_path.sas
   Craig Heither, last revised 02/09/10

--------------                     --------------
   PROGRAM IS CALLED BY IMPORT_ROUTES.PY AND
   FORMATS RAIL ITINERARIES TO BUILD IN ARC.
   STEP 2 OF PROCESS.
--------------                     --------------   */

%let inpath=%scan(&sysparm,1,$);
%let xls=%scan(&sysparm,2,$);
%let maxzn=1961;                  **highest zone09 POE;

/*-------------------------------------------------------------*/
                   * INPUT FILES *;
filename in1 "&inpath.\Import\&xls";
                   * OUTPUT FILES *;
filename out1 "&inpath.\Temp\itin.txt";
filename out2 "&inpath.\Temp\path.txt";
filename out3 "&inpath.\Temp\route.txt";
/*-------------------------------------------------------------*/

%macro getdata;
  %if %sysfunc(fexist(in1)) %then %do;
        ** READ IN CODING FOR RAIL ITINERARIES **;
       proc import out=section datafile="&inpath.\Import\&xls" dbms=xls replace; sheet="itinerary"; getnames=yes; mixed=yes;
          proc sort data=section; by line order;
  %end;
  %else %do;
   data null;
    file "&inpath.\Temp\rail_path.lst";
     put "File not found: &inpath.\Import\&xls";
  %end;      
%mend getdata;
%getdata
  /* end macro */


data section; set section;
  if order ne int(order) then delete;   ** drop skeleton link coding accidentally left in;
  if line='' then delete;               ** drop blank rows in spreadsheet;
  line=lowcase(line);
  if layover='.' or layover='' then layover=0;
  if dwell_code='.' or dwell_code='' then dwell_code=0;
  if dwell_time='.' or dwell_time='' then do;
      if dwell_code=0 then dwell_time=0.01;
      else dwell_time=0;
  end;
  if zone_fare='.' or zone_fare='' then zone_fare=0;
  if line_time='.' or line_time='' then line_time=0;
  line_time=round(line_time,.1);
  group=lag(line);

data verify; set section; proc sort; by itinerary_a itinerary_b;


             ** READ IN ROUTE TABLE CODING **;
 proc import out=rte datafile="&inpath.\Import\&xls" dbms=xls replace; sheet="header"; getnames=yes;

data rte; set rte;
 length des $22. n $32.;
  if line='' then delete;               ** drop blank rows in spreadsheet;
  line=lowcase(line); 
  if scenario='.' or scenario='' then scenario=0;
  if future_headway='' then future_headway='X';
  if rockford='' then rockford='X';
  if notes='' then notes='X';
  description=upcase(description); d=compress(description,"'"); d1=input(d,$20.); des="'"||trim(d1)||"'";
  nt=compress(notes,"'"); n1=input(nt,$30.); n="'"||trim(n1)||"'"; 
      proc sort nodupkey; by line;

    ** Create Route File for ARC **;
data rte; set rte;
   file out3 dsd;
     put line des mode type headway speed scenario future_headway rockford n;

 *** VERIFY ITINERARIES HAVE HEADERS AND VICE-VERSA ***;
data rte; set rte; r=1;
data s(drop=line); set section;
 length ln $8.;
   ln=line;
   i=1; 

data s(rename=(ln=line)); set s;
   proc sort nodupkey; by line;

data rte(drop=line); set rte;
 length ln $8.;
   ln=line;
data rte(rename=(ln=line)); set rte;
   proc sort; by line;

data s(drop=description d group); merge s rte; by line;
data check; set s; if r=1 & i='.'; proc print; title "Route with no Itinerary";
data check; set s; if i=1 & r='.'; proc print; title "Itinerary with no Header";

******************************;
          *-----------------------------------*;
                   ** VERIFY CODING **;
          *-----------------------------------*;     
** Read in MHN Links **;
proc import datafile="&inpath.\Temp\temp_arc.dbf" dbms=dbf out=mh replace;  
data mhn(keep=itinerary_a itinerary_b match); set mh;
  itinerary_a=anode; itinerary_b=bnode;
  match=1;
   output;
    if directions>1 then do;
      c=itinerary_a; itinerary_a=itinerary_b; itinerary_b=c;
      output;
    end;
   proc sort nodupkey; by itinerary_a itinerary_b;

** Find Unmatched Links **;
data check; merge verify (in=hit) mhn; by itinerary_a itinerary_b;
  if hit;
   if match=1 then delete;
     proc print; var itinerary_a itinerary_b line order; 
     title 'MIS-CODED ANODE-BNODE OR DIRECTIONAL PROBLEM ON THESE LINKS';

** Ensure Transit Not Coded on Centroid Links **;
data bad; set verify;
  if itinerary_a le &maxzn or itinerary_b le &maxzn;
     proc print; var itinerary_a itinerary_b line order; 
     title 'TRANSIT CODING ON CENTROID CONNECTORS';
******************************;

          *-----------------------------------*;
              ** FORMAT ITINERARY DATASET **;
          *-----------------------------------*;
data section(drop=order); set section;
   retain ordnew 1;
      ordnew+1;
      if line ne group then ordnew=1;
     output;

data section; set section;
   retain route 0;
     if line ne group then route+1;
     output;
     
data section; set section;
   place=_n_;     
     proc sort; by itinerary_a itinerary_b;

data arcs(keep=itinerary_a itinerary_b true); set mh; 
  itinerary_a=anode; itinerary_b=bnode;
  true=1; 
  proc sort; by itinerary_a itinerary_b;

  ** Find True Arc Direction in MHN **;
data section; merge section (in=hit) arcs; by itinerary_a itinerary_b;
   if hit;
    if true=1 then abnode=itinerary_a*100000+itinerary_b;
    else abnode=itinerary_b*100000+itinerary_a;
      proc sort; by line ordnew; 
 
     *---------------------------------*;
        ** WRITE ITINERARY FILE **
     *---------------------------------*;
data writeout; set section;
  file out1 dsd;
    put line itinerary_a itinerary_b layover dwell_code dwell_time zone_fare line_time 
             ordnew route place abnode;

       * - - - - - - - - - - - - - - - - - *;
            **REPORT ITINERARY GAPS**;
   **THESE ARE MIS-CODED LINKS OR SKELETONS THAT NEED CODING**;
         data check; set section;
           z=lag(itinerary_b);
            if itinerary_a ne z and ordnew>1 then output;
            proc print; var line ordnew itinerary_a itinerary_b z;
            title 'Itinerary Gaps';
       * - - - - - - - - - - - - - - - - - *;

       * - - - - - - - - - - - - - - - - - *;
            **REPORT LAYOVER PROBLEMS**;
   **A MAXIMUM OF TWO LAYOVERS ARE ALLOWED PER TRANSIT LINE **;
         data check; set section; if layover>0;
            proc freq; tables line / noprint out=check;
         data check; set check;
            if count>2;
            proc print; var line count;
            title 'Too Many Layovers Coded';
       * - - - - - - - - - - - - - - - - - *;

     *---------------------------------------*;
      ** FORMAT PATH-BUILDING FILE FOR ARC **
     *---------------------------------------*;
data path(keep=node route); set section; by line ordnew;
   node=itinerary_a; output;
   if last.line then do;
     node=itinerary_b; output;
   end;

data path; set path;
 rank=_n_;

     *---------------------------------*;
        ** WRITE PATH FILE **
     *---------------------------------*;
data write2; set path;
  file out2 dsd;
    put node rank route;
   
run;
