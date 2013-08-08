/* read_future_path_output.sas
   Craig Heither, 04/26/2012

-------------                                                             -------------
   This SAS program reads the shortest path data written by find_shortest_path.py
   and inserts it into the transit itineraries of future routes.  
   The data are used to create the string of vertex coordinates to build the routes 
   in the geodatabase - it is not necessary to recalculate or interpolate itinerary
   attributes.
-------------                                                             -------------    */
options linesize=120;

 *** RE-FORMAT PATH DATA AS ITINERARY SEGMENTS ***;
data read(keep=newb set i); infile in4 length=reclen lrecl=1000;
  input alldata $varying1000. reclen;
   set=_n_; 
   alldata=compress(alldata,"[] ()");
   c=count(alldata,",");
      *** format itinerary segments ***;
   do i=1 to c;
      newb=input(scan(alldata,i+1,","),best5.); output;
   end;
  proc sort; by set i;

data first; set read; by set i;
 if first.set then itin_a=newb;
 if last.set then itin_b=newb;
   proc summary nway; class set; var itin_a itin_b; output out=ends max=;

data read(drop=_type_ _freq_ grp); merge read ends; by set;
  newa=lag(newb); grp=lag(set); impute=1;
  if set=grp;
   proc sort; by newa newb;


 *** MERGE NEW SEGMENTS INTO TRANSIT RUN ITINERARIES ***;
proc sql noprint;
  create table newitin as
      select sect2.*,
             read.newa,newb,set,i,impute
      from sect2 left join read
      on sect2.itin_a=read.itin_a & sect2.itin_b=read.itin_b
      order by tr_line,set,i;

data newitin(drop=tr_line); set newitin; 
  length ln $8.; 
   orig_a=itin_a; itin_a=newa; orig_b=itin_b; itin_b=newb; group=lag(tr_line); ln=tr_line;
data newitin(drop=order newa newb set i impute); set newitin;
   retain it_order 1;
   it_order+1;
   if ln ne group then it_order=1;
   output;
   rename ln=tr_line lo=layover;

run;