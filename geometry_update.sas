 /* Geometry_update.SAS
    Craig Heither, revised 08/07/2012


   Program uses arc geometry to re-build rail routes so they are always coincident with arcs. This
   program is called by IMPORT_ROUTES.PY and by UPDATE_NETWORK_EDITS.PY. It:

     - SECTION 1 - Reads a file of arc geometry and attaches the vertex coordinates so they can be used later to 
                   create the itinerary coding that will be coincident with the arcs when the new routes are built
                   in the geodatabase.

     - SECTION 2 - Error checks current itinerary data and drops coding for routes deleted from the route feature class.

     - SECTION 3 - Specialized processing based on the input parameter provided:
          -> 1 - Call read_rail_spreadsheet.sas to import & format regular spreadsheet rail coding.
          -> 2 - Call read_rail_feed_data.sas to import & format GTFS rail coding.
                 If there are itinerary gaps:
                    * Master_Rail\mrn_programs\write_dictionary.sas writes a Python dictionary
                         of network links and their lengths.
                    * Master_Rail\mrn_programs\find_shortest_path.py determines the shortest network path.
                    * Master_Rail\mrn_programs\read_path_output.sas updates the itineraries as needed.
          -> 3 - Call itinerary_node_update.sas to insert split-link updates into itineraries and assign temporary node numbers.

     - SECTION 4 - Calculates itinerary F_MEAS and T_MEAS values to allow for displaying the data as Route Events.

     - SECTION 5 - Creates final files for input into geodatabase.


__________________________________________________________________________________________________________________________  */

%let dir=%scan(&sysparm,1,$);           ***shapefile storage directory;
%let origitin=%scan(&sysparm,2,$);      ***original itinerary .dbf file (entire path);
%let rtefile=%scan(&sysparm,3,$);       ***name of spreadsheet for importing new routes or GTFS route file (entire path);
%let code=%scan(&sysparm,4,$);          ***choice flag for Section 3 processing;
%let segfile=%scan(&sysparm,5,$);       ***name of GTFS segment file (entire path);
%let use900=%scan(&sysparm,6,$);        ***use new station itinerary during GTFS import;


%let tot=0;
%let keeporig=0;


filename in1 "&dir.\Temp\geom_out.txt";
filename out1 "&dir.\Temp\geom_in.txt";
filename out2 "&dir.\Temp\dropped_routes.txt";

*================================================================*;
   *** SECTION 1.  READ IN AND FORMAT ARC GEOMETRY DATA ***;
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
   *** SECTION 2. ERROR CHECK CURRENT ITINERARY & ROUTE DATA ***;
*================================================================*;
%macro errorchk;
    %if &code ne 2 %then %do;
        proc import datafile="&origitin" dbms=dbf out=sec replace;  
        proc sort data=sec; by tr_line;


        proc import datafile="&dir.\Temp\temp_route.dbf" dbms=dbf out=rt replace;  
        proc sort data=rt; by tr_line;


        %macro goodrte;
            %if &code=1 %then %do;
                data r(keep=tr_line action); set rt;    ***only keep action if importing future route coding;
            %end;
            %else %do; 
                data r(keep=tr_line); set rt;
            %end;
        %mend goodrte;
        %goodrte
        /* end of macro*/
        run; 

        * --> verify routes in route and itinerary tables *;
        data good remove; merge sec (in=hit1) r (in=hit2); by tr_line;
            if hit1 & hit2 then output good; else output remove;

        proc sort data=good; by itin_a itin_b;


        %macro ordcheck;
            %if &code ne 1 %then %do;
                * --> QC check on itineraries *;
                data chk2; set good; proc sort; by tr_line it_order;
                data chk2; set chk2;
                    z=lag(itin_b); ln=lag(tr_line);
                    if tr_line=ln & itin_a ne z then output;
                proc print; var tr_line itin_a itin_b it_order z;
                    title "Gap in Itinerary: z is itin_b of Previous Segment";
            %end;
        %mend ordcheck;
        %ordcheck
        /* end of macro*/
        run; 


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
        run;
    %end; 
%mend errorchk;
%errorchk
run;

*================================================================*;
 ***SECTION 3. based on input parameter this will call script to
       1) import spreadsheet coding, 
       2) read_rail_feed_data or 
       3) update itinerary for split links.
 [these are mutually exclusive categories];
*================================================================*;

%macro choice;

  %if &code=1 %then %do; %include "&dir.\mrn_programs\read_rail_spreadsheet_Apr2012.sas"; %end;    *** call program to import & format spreadsheet rail coding ***;
  %if &code=2 %then %do; %include "&dir.\mrn_programs\read_rail_feed_data.sas"; %end;              *** call program to import & format GTFS rail coding ***;
  %if &code=3 %then %do; %include "&dir.\mrn_programs\itinerary_node_update_Aug2012.sas"; %end;    *** call program to insert split-link updates into itineraries ***;  

%mend choice;
%choice
  /* end macro */
run;


*================================================================*;
   *** SECTION 4. CREATE ITINERARY F_MEAS AND T_MEAS VALUES ***;
*================================================================*;
 ** If future coding is being processed and action in (2,3,5,6,7): the itinerary data must be handled differently. **;

%macro meas(dsn);

     *** -- PROCESSING FOR IMPORTING FUTURE ROUTES ONLY -- ***;
  %if &code=1 %then %do; 
      %if %sysfunc(exist(&dsn)) %then %do;                                                  *** FUTURE CODING WITH ACTION=(2 OR 3) ***;
          data sectmi(drop=tr_line); set sect1 sect4; length ln $8.; ln=tr_line;
          data sectmi(rename=(ln=tr_line lo=layover)); set sectmi; 
          data sectmi; set sectmi newitin; proc sort; by itin_a itin_b;
      %end;
      %else %do;
          data sectmi; set section; proc sort; by itin_a itin_b;                            *** FUTURE CODING WITHOUT ACTION=(2 OR 3) ***;
      %end;

            * --> recalculate itinerary f_meas & t_meas using link miles *;
          data sec; merge sectmi (in=hit) mi; by itin_a itin_b; if hit;
            if it_order=. then it_order=order;
            proc sort; by tr_line it_order;

            * --> QC check on itineraries *;
          data chk; set sec(where=(miles=.)); 
           if &code=1 then do; if action in (2,3,6,7) then delete; end;
             proc print; title "No Coded Length: Means Link is Not in Network";

          data sec; set sec; by tr_line it_order;
            retain x 0;
             if first.tr_line then x=0;
             output;
             x=x+miles;

          data sec(drop=x); set sec;
            f_meas=x; t_meas=f_meas+miles; 
              proc sort; by tr_line it_order f_meas;
          data sec1(drop=miles); set sec;

         *** WRITE .DBF OF DATA THAT WILL BE STORED IN GEODATABASE ITINERARY TABLE ***;
      %if %sysfunc(exist(&dsn)) %then %do; 
          data s1(drop=x); set sec1(rename=(DW_TIME=x) where=(action not in (2,3,5,6,7)));    *** NO CHANGES;
              DW_TIME=input(x,13.11);
          data s2; set sec1(where=(action in (2,3,5,6,7)));      *** CONVERT BACK TO SPREADSHEET CODING ***;
             itin_a=orig_a; itin_b=orig_b;
             if action=5 then do; layover=orig_lo; order=it_order; end;
             else order=0;

            proc summary nway; class tr_line itin_a itin_b; id layover;
               output out=s2b min(f_meas)= max(t_meas)= sum(order)=it_order mean(trv_time)=;
          data s1(drop=_type_ _freq_ orig_a orig_b orig_lo action group order); set good s1 s2b; proc sort; by tr_line f_meas;
          proc export data=s1 outfile="&dir.\Temp\new_segments.dbf" dbms=dbf replace;                    
      %end;
      %else %do;
          data sec1(drop=orig_a orig_b orig_lo action group); set good sec1; proc sort; by tr_line f_meas;
          proc export data=sec1 outfile="&dir.\Temp\new_segments.dbf" dbms=dbf replace;       
      %end;
   %end;
   %else %if &code=2 %then %do;
     *** -- PROCESSING FOR IMPORTING GTFS ROUTES ONLY ... -- ***;

            * --> recalculate itinerary f_meas & t_meas using link miles *;
          data good; merge good (in=hit) mi; by itin_a itin_b; if hit; proc sort; by tr_line it_order;

          data good; set good; by tr_line it_order;
            retain x 0;
             if first.tr_line then x=0;
             output;
             x=x+miles;

          data sec(drop=x); set good;
            f_meas=x; t_meas=f_meas+miles; 
              proc sort; by tr_line it_order f_meas;
          data sec1(drop=miles); set sec; proc sort; by tr_line f_meas;        
          proc export data=sec1 outfile="&dir.\Temp\new_segments.dbf" dbms=dbf replace;
   %end;
   %else %if &code=3 %then %do;
       *** -- PROCESSING FOR LINK SPLITS ONLY ... -- ***;
       data sec;
	   merge good(in=hit) mi;
	   by itin_a itin_b;
	   if hit;
       proc sort;
	   by tr_line it_order;
   %end;

%mend meas;
%meas(work.newitin)
  /* end macro */
run;


*================================================================*;
   *** SECTION 5. COMBINE GEOMETRY AND ITINERARY DATA TO BUILD ROUTES ***;
*================================================================*;
%macro create_rtes;

  %if not(&code=3 & %index(&origitin,future)) %then %do;

   %if &keeporig>0 %then %do;
       ** -- Re-use Route Structure for Lines Already Coded -- **;
        data exist; infile "&dir.\Temp\rte_out.txt" dlm=';' missover;
          input rte tr_line $ x y m; m=round(m,.00001);
            proc sort; by tr_line m;
        data exist; merge exist done(in=hit); by tr_line; if hit;

       ** -- Remove these Routes from Section Table -- **;
        data sec; merge sec done(in=hit); by tr_line; if hit then delete;
   %end;

   * --> attach arc vertices to itinerary coding *;
   data sec; set sec; by tr_line it_order;
     retain rte 0;
       if first.tr_line then rte+1;

   proc sql noprint;
    create table vert as
     select sec.tr_line, sec.itin_a, sec.itin_b, sec.it_order, sec.rte, sec.miles, sec.t_meas,
         arcs.x, y, ord
     from sec,arcs
     where sec.itin_a=arcs.itin_a & sec.itin_b=arcs.itin_b
     order by rte,it_order,ord;

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

   %if &keeporig>0 %then %do;
       ** -- Add Existing Routes -- **;
       data vert(drop=rte); set exist vert; proc sort; by tr_line m;
       data vert; set vert; by tr_line m;
         retain rte 0;
          if first.tr_line then rte+1;
   %end;

   * --> remove duplicate coordinates within routes (end of segment 1 & beginning of segment 2 have the same coordinates) *;
   data vert; set vert;
    format x1 14.6 y1 14.5;
    r1=lag(rte); x1=lag(x); y1=lag(y);
    if rte=r1 & x=x1 & y=y1 then delete;

   data print; set vert; file out1 dlm=';';
    put rte x y m;
  
  %end;

%mend create_rtes;
%create_rtes
  /* end macro */
run;


%macro rtes;

  %if &code=2 %then %do;                                                                       *** call block for GTFS rail coding ***;
      data route(keep=line1 desc1 mode1 type1 hdwy1 speed1 fdline r_id rln dir term start strthour ampct vehicle); 
          retain newline descr mode type headway speed fdline r_id rln dir term start strthour ampct vehicle;
	  set route;
          rename newline=line1 descr=desc1 mode=mode1 type=type1 headway=hdwy1 speed=speed1;
      proc export data=route outfile="&dir.\Temp\rte_updt.dbf" dbms=dbf replace;
  %end;
  %else %if &code=1 | (&code=3 & %index(&origitin,future)) %then %do;                                                                                   *** call block for future rail coding ***;
      data rt(drop=shape_leng);
	  set rt;
	  id=_n_;
	  if descriptio='' then descriptio=description;
          rename tr_line=line1 descriptio=desc1 mode=mode1 veh_type=type1 headway=hdwy1 speed=speed1 scenario=scen1 action=action1 notes=notes1; 
      data rt;
	  set rt;
	  keep line1 desc1 mode1 type1 hdwy1 speed1 scen1 action1 notes1 id; 
      proc export data=rt outfile="&dir.\Temp\rte_updt.dbf" dbms=dbf replace;
  %end;
  %else %if &code=3 & %index(&origitin,all_runs) %then %do;
      data route(keep=line1 desc1 mode1 type1 hdwy1 speed1 fdline r_id rln dir term start strthour ampct ct_veh1); 
          retain tr_line descriptio mode veh_type headway speed feedline route_id longname direction terminal start strthour am_share ct_veh;
	  set rt;
          rename tr_line=line1 descriptio=desc1 mode=mode1 veh_type=type1 headway=hdwy1 speed=speed1 feedline=fdline route_id=r_id longname=rln direction=dir terminal=term am_share=ampct ct_veh=ct_veh1;
      proc export data=route outfile="&dir.\Temp\rte_updt.dbf" dbms=dbf replace;
  %end;

%mend rtes;
%rtes
  /* end macro */
run;
