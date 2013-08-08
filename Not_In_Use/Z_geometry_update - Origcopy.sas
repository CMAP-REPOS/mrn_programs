/* Geometry_update.SAS
    Craig Heither, revised 07/13/10


   Program uses arc geometry to re-build rail routes so they are always coincident with arcs. This
   program is called by IMPORT_ROUTES.PY and by UPDATE_NETWORK_EDITS.PY. It:
     - Reads a file of arc geometry and attaches the vertex coordinates to the itinerary coding to create a
       new route file ArcGIS uses to rebuild the routes.

     - Updates all itinerary coding by recalculating the f_meas and t_meas values, and removes segments of
       routes that have been deleted from the route feature class.

     - Imports new/revised route coding and incorporates it into the geodatabase (when IMPORT_ROUTES.PY 
       calls the program).

   ----------------------------------------------------------------
   NOTE: A FILE NAMED SKIP.XLS MUST EXIST IN THE IMPORT\ DIRECTORY.
   ----------------------------------------------------------------

    This program incorporates portions of two SAS programs no longer being used (RAIL_PATH.SAS and
    UPDATE_IMPORT_ROUTES.SAS).

  */

%let dir=%scan(&sysparm,1,$);     ***shapefile storage directory;
%let dt=%scan(&sysparm,2,$);      ***date of itinerary .dbf file;
%let xls=%scan(&sysparm,3,$);     ***name of spreadsheet for importing new routes;
%let code=%scan(&sysparm,4,$);    ***flag if SAS program called by IMPORT_ROUTES.PY;

%let tot=0;


filename in1 "&dir.\Temp\geom_out.txt";
filename innew "&dir.\Import\&xls";
filename nwmi "&dir.\Temp\new_mile.dbf";
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
   *** ERROR CHECK CURRENT ITINERARY & ROUTE DATA ***;
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

* - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - *;
*================================================================*;
   *** IMPORT NEW ROUTE & ITINERARY CODING (ONLY IF CALLED BY IMPORT_ROUTES.PY) ***;
*================================================================*;
%macro newdata;
 %if &code=1 %then %do;

      *** Read in and Format Spreadsheet Coding ***;
       %if %sysfunc(fexist(innew)) %then %do;
             ** READ IN CODING FOR RAIL ITINERARIES **;
            proc import out=section datafile="&dir.\Import\&xls" dbms=xls replace; 
             sheet="itinerary"; getnames=yes; mixed=yes;
               proc sort data=section; by line order;
       %end;
       %else %do;
         data null;
           file "&dir.\Temp\rail_path.lst";
           put "File not found: &dir.\Import\&xls";
         endsas;
       %end;

       data section(drop=layover); set section;
         if order ne int(order) then delete;   ** drop skeleton link coding accidentally left in;
         if line='' then delete;               ** drop blank rows in spreadsheet;
         line=lowcase(line);
         if layover='.' or layover='' then layover=0;
         if dwell_code='.' or dwell_code='' then dwell_code=0;
         if dwell_time='.' or dwell_time='' then do;
             if dwell_code=0 then dwell_time=0.01; else dwell_time=0;
         end;
         if zone_fare='.' or zone_fare='' then zone_fare=0;
         if line_time='.' or line_time='' then line_time=0;
         line_time=round(line_time,.1);
         group=lag(line);
         lo=input(layover,$8.);
           proc sort; by line order;

       data verify(rename=(itinerary_a=itin_a itinerary_b=itin_b)); set section; proc sort; by itin_a itin_b;

             ** READ IN ROUTE TABLE CODING **;
       proc import out=rte datafile="&dir.\Import\&xls" dbms=xls replace; sheet="header"; getnames=yes;

       data rte(drop=description d notes nt mode rockford); set rte;
         if line='' then delete;               ** drop blank rows in spreadsheet;
         line=lowcase(line); 
         if scenario='.' or scenario='' then scenario='';
         description=upcase(description); d=compress(description,"'"); d1=input(d,$20.); 
         m=input(mode,$1.);
         rock=input(rockford,$6.);
         nt=compress(notes,"'"); n1=input(nt,$30.); 
            proc sort nodupkey; by line;



       *** VERIFY ITINERARIES HAVE HEADERS AND VICE-VERSA ***;
       data rte(drop=line scenario); set rte; length ln $8.; ln=line; scen=left(put(scenario,8.0)); r=1;
       data rte(rename=(ln=line scen=scenario)); set rte; proc sort; by line;
       data s(drop=line); set section; length ln $8.; ln=line; i=1; 
       data s(rename=(ln=line)); set s; proc sort nodupkey; by line;
       data s(drop=group); merge s rte; by line;
       data check; set s; if r=1 & i='.'; proc print; title "Route with no Itinerary";
       data check; set s; if i=1 & r='.'; proc print; title "Itinerary with no Header";

       *** VERIFY ITINERARY CODING MATCHES NETWORK LINKS ***;   
       data check; merge verify (in=hit) mi; by itin_a itin_b; if hit;
          if miles>0 then delete;
            proc print; var itin_a itin_b line order; 
            title 'MIS-CODED ANODE-BNODE OR DIRECTIONAL PROBLEM ON THESE LINKS';

       *** RESET ITINERARY ORDER ***;   
       data section(drop=order); set section;
         retain ordnew 1;
          ordnew+1;
          if line ne group then ordnew=1;
          output;
       data section(rename=(lo=layover)); set section;

            ** REPORT ITINERARY GAPS (LINKS ARE MIS-CODED OR SKELETONS THAT NEED CODING **;
        data check; set section;
           z=lag(itinerary_b);
            if itinerary_a ne z and ordnew>1 then output;
            proc print; var line ordnew itinerary_a itinerary_b z; title "Gap in Itinerary: z is itin_b of Previous Segment";

            ** REPORT LAYOVER PROBLEMS (MAX. OR 2 PER LINE) **;
         data check; set section; if layover>0;
            proc freq; tables line / noprint out=check;
         data check; set check; if count>2;
            proc print; var line count; Title 'Too Many Layovers Coded';

       *** RENAME VARIABLES TO MATCH FIELDS IN CURRENT CODING ***;
       data section(drop=line); set section; length ln $8.; ln=line; 
       data section; set section;
         rename ln=tr_line itinerary_a=itin_a itinerary_b=itin_b ordnew=it_order dwell_code=dw_code
                dwell_time=dw_time zone_fare=zn_fare line_time=trv_time;
       data rte(drop=r); set rte;
         rename line=tr_line d1=descriptio m=mode type=veh_type future_headway=ftr_headwa rock=rockford n1=notes;

       *** REMOVE ALL ROUTES BEING IMPORTED FROM EXISTING CODING TABLES ***;
       data kill(keep=tr_line); set rte; proc sort nodupkey; by tr_line;
       data rt; merge rt kill (in=hit); by tr_line; if hit then delete;
       proc sort data=good; by tr_line;
       data good; merge good kill (in=hit); by tr_line; if hit then delete;

       *** COMBINE ALL CODING FOR FINAL PROCESSING ***;
       data rt; set rt rte; proc sort; by tr_line; 
       data good; set good section; proc sort; by itin_a itin_b;

 %end;   
%mend newdata;
%newdata
  /* end macro */
* - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - *;
*================================================================*;
   *** UPDATE ITINERARY TO REFLECT SPLIT LINKS W/ TEMPORARY ANODE-BNODE VALUES (ONLY IF NEW_MILE.DBF EXISTS) ***;
*================================================================*;
%macro split;
  %if %sysfunc(fexist(nwmi)) %then %do;

       * --> read in file of split links and re-order them to insert into itinerary *;
       proc import datafile="&dir.\Temp\new_mile.dbf" dbms=dbf out=tmpnode replace;  
         proc sort data=tmpnode; by anode bnode;
         proc summary nway data=tmpnode; class anode bnode; output out=d;
       data tmpnode(drop=_type_ _freq_ orig_fid); merge tmpnode d; by anode bnode;
         if tempa=anode then o=1;
         else if tempb=bnode then o=_freq_;
         else o=mean(1,_freq_);
           proc sort; by anode bnode o;

       * --> create a set of reverse-order links for itinerary & combine all *;
       data tmpnd2; set tmpnode; proc sort; by anode bnode descending o;
       data tmpnd2(drop=o c tempc); set tmpnd2;
         c=anode; anode=bnode; bnode=c; tempc=tempa; tempa=tempb; tempb=tempc;
         oa=lag(anode);
       data tmpnd2(drop=oa); set tmpnd2;
         retain o 1;
         o+1;
         if anode ne oa then o=1;
         output;
       data tmpnode; set tmpnode tmpnd2; proc sort; by anode bnode o;
       data tmpnode; set tmpnode;
         retain x 0;
         if o=1 then x=0;
         output;
         x=x+newmile;

         proc summary nway data=tmpnode; var newmile; class anode bnode; output out=y sum=totmile; 
         data y(rename=(anode=itin_a bnode=itin_b)); set y;
       
       * --> separate routes that need updating from those that do not *;
       data x1; merge good (in=hit1) y (in=hit2); by itin_a itin_b; if hit1 & hit2; 
          proc freq; tables tr_line / noprint out=match; 
          proc sort data=good; by tr_line it_order; 
       data good; merge good match; by tr_line; 
       data fix(drop=count percent) ok(drop=count percent); set good;
          if count>0 then output fix; else output ok;

       * --> update itineraries *;
       data fix; set fix; 
       proc sql noprint;
        create table fix1 as
         select *
          from fix,tmpnode
          where fix.itin_a=tmpnode.anode & fix.itin_b=tmpnode.bnode;
         proc sort data=fix1; by itin_a itin_b;

       data fix1; merge fix1 (in=hit) y; by itin_a itin_b; if hit;
         proc sort; by tr_line it_order o; 
       data fix1(drop=anode bnode tempa tempb o x _type_ _freq_ newmile totmile); set fix1; by tr_line it_order;
        if first.it_order then do; itin_b=tempb; t_meas=f_meas+newmile; trv_time=round(trv_time*newmile/totmile,.01); layover=''; end;
        else if last.it_order then do; itin_a=tempa; f_meas=f_meas+x; zn_fare=0; trv_time=round(trv_time*newmile/totmile,.01); end; 
        else do; itin_a=tempa; itin_b=tempb; f_meas=f_meas+x; t_meas=f_meas+newmile; zn_fare=0; trv_time=round(trv_time*newmile/totmile,.01); layover=''; end; 

       * --> put all itinerary coding back together *;
       proc summary nway data=fix1; class tr_line it_order; output out=y1; 
       data fix; merge fix y1 (in=hit); by tr_line it_order; if hit then delete; 
       data good(drop=_type_ _freq_ it_order); set ok fix fix1; proc sort; by tr_line f_meas; 
       data good; set good; group=lag(tr_line);
       data good(drop=group); set good; 
         retain it_order 1;
         it_order+1;
         if tr_line ne group then it_order=1;
          output;
         proc sort; by itin_a itin_b;

  %end;
%mend split;
%split
  /* end macro */
* - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - *;
*================================================================*;
   *** CREATE ITINERARY F_MEAS AND T_MEAS VALUES ***;
*================================================================*;
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
 if (vx=. and vy=.) or it_order ne ito then segdist=0; else segdist=sqrt((x-vx)**2+(y-vy)**2)/5280;

  proc summary nway; var segdist; class rte it_order; output out=segtot sum=linktot;
data vert(drop=_type_ _freq_ vx vy ito); merge vert segtot; by rte it_order;
  proc sort; by rte it_order ord;

data vert; set vert; by rte it_order ord;
  retain m 0;
   if first.rte then m=0;
   m=m+round(segdist/linktot*miles,.00001);
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
data rt; set rt;  keep line1 desc1 mode1 type1 hdwy1 speed1 scen1 fhdwy1 rock1 notes1 id; 
proc export data=rt outfile="&dir.\Temp\rte_updt.dbf" dbms=dbf replace;

run;
