/* Geometry_update.SAS
    Craig Heither, revised 06/01/10

   Program uses arc geometry to re-build rail routes so they are always coincident with arcs.

  */

%let dir=%scan(&sysparm,1,$);     ***shapefile storage directory;
%let dt=%scan(&sysparm,2,$);      ***date of itinerary .dbf file;
%let tot=0;


filename in1 "&dir.\Temp\geom_out.txt";
filename out1 "&dir.\Temp\geom_in.txt";
filename out2 "&dir.\Temp\dropped_routes.txt";

*================================================================*;
   *** READ IN AND FORMAT ARC GEOMETRY DATA ***;
*================================================================*;
data arcs; infile in1 missover dlm=";";
 format x 14.6 y 14.5;
  input itin_a itin_b dir miles mode1 $ mode2 $ id x y;
    miles=round(miles,.01);

   * --> rail coding will run only on rail links *;
data arcs; set arcs(where=(mode1 ? 'C' or mode1 ? 'M'));
  tid=lag(id);

   * --> order vertices within links *;
data arcs(drop=tid); set arcs;
  retain ord 1;
    ord+1;
    if id ne tid then ord=1;
    output; 

   * --> order vertices within links for second direction ... *;
data a2(drop=c); set arcs(where=(dir=2 and (mode2 ? 'C' or mode2 ? 'M')));
 c=itin_a; itin_a=itin_b; itin_b=c;
 mode1=mode2;
 id=id+1000;
   proc sort; by id descending ord;

data a2(drop=ord); set a2; tid=lag(id);
data a2(drop=tid); set a2;
  retain ord 1;
    ord+1;
    if id ne tid then ord=1;
    output; 

   * --> ... and combine for a complete dataset of both directions *;
data arcs; set arcs a2; proc sort; by itin_a itin_b ord;

data mi(keep=itin_a itin_b miles); set arcs; proc sort nodupkey; by itin_a itin_b;

*================================================================*;
   *** READ IN AND FORMAT ITINERARY DATA ***;
*================================================================*;
proc import datafile="&dir.\itin_&dt..dbf" dbms=dbf out=sec replace;  
  proc sort data=sec; by tr_line;


proc import datafile="&dir.\Temp\temp_route.dbf" dbms=dbf out=rt replace;  
  proc sort data=rt; by tr_line;

data r(keep=tr_line); set rt;

   * --> verify routes in route and itinerary tables *;
data good remove; merge sec (in=hit1) r (in=hit2); by tr_line;
  if hit1 & hit2 then output good; else output remove;

proc sort data=good; by itin_a itin_b;

   * --> QC check on itineraries *;
data chk2; set good; proc sort; by tr_line it_order;
data chk2; set chk2;
  z=lag(itin_b); ln=lag(tr_line);
  if tr_line=ln & itin_a ne z then output;
    proc print; var tr_line itin_a itin_b it_order z;
     title "Gap in Itinerary: z is itin_b of Previous Segment";

   * --> identify routes dropped from coding, if any exist *;
data t; set remove nobs=totobs; call symput('tot',left(put(totobs,8.))); run;   **store number of dropped routes in global variable;

%macro delroute;
 %if &tot>0 %then %do;  
     data remove(keep=tr_line); set remove; proc sort nodupkey; by tr_line;
     data print; set remove; file out2; 
       if _n_=1 then put "&sysdate - Routes Deleted from Coding:";
       put tr_line;
 %end;
%mend delroute;
%delroute
 /* end of macro*/


   * --> recalculate itinerary f_meas & t_meas using link miles *;
data sec; merge good (in=hit) mi; by itin_a itin_b; if hit;
  proc sort; by tr_line it_order;

   * --> QC check on itineraries *;
data chk; set sec(where=(miles=.)); proc print; title "No Coded Length: Means Link is Not in Network";

data sec; set sec; by tr_line it_order;
  retain x 0;
   if first.tr_line then x=0;
   output;
   x=x+miles;

data sec(drop=x); set sec;
  f_meas=x; t_meas=f_meas+miles; 

data sec1(drop=miles); set sec;
proc export data=sec1 outfile="&dir.\Temp\new_segments.dbf" dbms=dbf replace;

*================================================================*;
   *** COMBINE GEOMETRY AND ITINERARY DATA TO BUILD ROUTES ***;
*================================================================*;
   * --> attach arc vertices to itinerary coding *;
data sec; set sec; by tr_line it_order;
  retain rte 0;
    if first.tr_line then rte+1;

proc sql noprint;
 create table vert as
  select sec.tr_line, sec.itin_a, sec.itin_b, it_order, rte, sec.miles, t_meas,
         arcs.x, y, ord
  from sec,arcs
  where sec.itin_a=arcs.itin_a & sec.itin_b=arcs.itin_b;
 proc sort data=vert; by rte it_order ord;

   * --> calculate m values for each vertex (so route events can be plotted in ArcGIS) *;
data vert; set vert;
 vx=lag(x); vy=lag(y); ito=lag(it_order);
 if (vx=. and vy=.) or it_order ne ito then segdist=0; else segdist=round(sqrt((x-vx)**2+(y-vy)**2)/5280,.0001);

  proc summary nway; var segdist; class rte it_order; output out=segtot sum=linktot;
data vert(drop=_type_ _freq_ vx vy ito); merge vert segtot; by rte it_order;
  proc sort; by rte it_order ord;

data vert; set vert; by rte it_order ord;
  retain m 0;
   if first.rte then m=0;
   m=m+round(segdist/linktot*miles,.0001);
     output;

   * --> remove duplicate coordinates within routes (end of segment 1 & beginning of segment 2 have the same coordinates) *;
data vert; set vert;
 format x1 14.6 y1 14.5;
 r1=lag(rte); x1=lag(x); y1=lag(y);
 if rte=r1 & x=x1 & y=y1 then delete;

data print; set vert; file out1 dlm=';';
 put rte x y m;


data rt(drop=shape_leng); set rt; id=_n_; 
  rename tr_line=line1 descriptio=desc1 mode=mode1 veh_type=type1 headway=hdwy1 speed=speed1
         scenario=scen1 ftr_headwa=fhdwy1 rockford=rock1 notes=notes1; 


proc export data=rt outfile="&dir.\Temp\rte_updt.dbf" dbms=dbf replace;


run;
