/* COLLAPSE_CTA_RUNS.SAS
   Craig Heither, last revised 02/06/2012

-------------                                          -------------
   Program reformats itinerary data to combine similar runs.
-------------                                          -------------              */

options noxwait;


%let outfl=oneline.txt;                                                   *** output file for python to process;

*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*;
filename in3 "&inpath.\Output\feed_groups.txt";
filename out5 "&inpath.\Output\&outfl";
*~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~*;

data sec; set itinc;
 length id $13.;
   id=compress(itin_a||"-"||itin_b||"-"||dw_code);
  proc sort; by tr_line it_order;


data rat; set routes;
 length moderte $13.; format start timeampm.;
   moderte=compress(substr(tr_line,1,3)||route_id);
    proc sort; by tr_line;


 *-------------------------------------------------------------------------------;
       **** Format data to analyze runs ***;
 *-------------------------------------------------------------------------------;
data s; merge sec(in=hit) rat; by tr_line; if hit;

 *** Write out 1 line for each Run ***;
data s; set s; by tr_line it_order;
 file out5 dsd lrecl=32767;
  if first.tr_line then do;
    if last.tr_line then put moderte tr_line id;               ** needed to correctly handle routes with only 1 segment **;
    else put moderte tr_line id @;
  end;
  else if last.tr_line then put id;
  else put id @;


 *-------------------------------------------------------------------------------;
       **** Run python script to collapse runs into TOD routes ***;
 *-------------------------------------------------------------------------------;
data _null_;
  command="if exist &inpath.\Temp\pypath.txt (del &inpath.\Temp\pypath.txt /Q)" ; call system(command);
  command="ftype Python.File >> &inpath.\Temp\pypath.txt" ; call system(command);

data null; infile "&inpath.\Temp\pypath.txt" length=reclen;
  input location $varying254. reclen; 
  loc=scan(location,2,'='); goodloc=substr(loc,1,index(loc,'.exe"')+4);
  call symput('runpython',trim(goodloc)); 
  run;

data _null_;
  command="%bquote(&runpython) &inpath.\mrn_programs\gtfs_collapse_routes.py &inpath.\Output\oneline.txt &inpath.\Output\feed_groups.txt"; call system(command);
  command="if exist &inpath.\Temp\pypath.txt (del &inpath.\Temp\pypath.txt /Q)" ; call system(command);
run;

 *-------------------------------------------------------------------------------;
       **** Create TOD routes ***;
 *-------------------------------------------------------------------------------;
data groups; infile in3 dsd missover;
  input tr_line $ group;
   proc sort; by tr_line;

 *** - IDENTIFY REPRESENTATIVE RUN: Longest (most segments), then starts earliest - ***;
data sec1; merge sec groups(in=hit); by tr_line; if hit;
proc summary nway; class tr_line; id group; var it_order; output out=segcount max=segs;

data segcount(keep=tr_line group segs start); merge segcount(in=hit) rat; by tr_line; if hit; 
 proc sort; by group descending segs start;

data rep(keep=tr_line group); set segcount; by group descending segs start;
  if first.group;    *** group representative for AM Peak network ***; 

 *** - CALCULATE AVERAGE HEADWAY & NUMBER OF RUNS REPRESENTED - ***;
proc summary nway data=segcount; class group; output out=cnt;
data hdwy(rename=(_freq_=runs)); merge segcount cnt; by group;

%macro headway;
  %if &tod=1 %then %do;
     data hdwy; set hdwy;
       ap=put(start,timeampm2.);
       if ap='PM' then priority=1; else priority=2;
       shr=hour(start);
         proc sort; by group priority shr start;
  %end;
  %else %do;
     proc sort data=hdwy; by group start;
  %end;
%mend headway;
%headway
run;

*****proc print data=hdwy;

data hdwy; set hdwy;
  format st timeampm.;
  st=lag(start); gp=lag(group);
  if runs>1 then do; if group ne gp then delete; end;

  if &tod=1 then maxtime=600;
  else if &tod=2 or &tod=4 then maxtime=60;
  else if &tod=5 then maxtime=240;
  else maxtime=120;

  if runs=1 then hdwy=maxtime;
  else hdwy=abs(start-st)/60;
  if hdwy>maxtime then hdwy=1440-hdwy;       ***adjust to calculate overnight times correctly if SAS assumes times cross days ***;
  if hdwy=0 then hdwy=maxtime;

  drop _type_;
***proc print;
proc summary nway; class group; var hdwy runs; output out=hdcnt mean=;

data keepc(drop=_type_ _freq_); merge rep hdcnt; by group;
 hdwy=round(hdwy,0.1);
  proc sort; by tr_line;

run;
