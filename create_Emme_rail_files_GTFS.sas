/* CREATE_EMME_RAIL_FILES_GTFS.SAS
    Craig Heither & Nick Ferguson, last rev. 02/01/2016

-------------                                                             -------------
   PROGRAM CREATES TIME-OF-DAY RAIL TRANSIT NETWORK BATCHIN FILES. 

     Action=1: Entire itinerary coded. Route and itinerary are appended to base year tables for processing.
               Routes and headways are applied to TOD periods according to coding in HEADWAY and TOD fields.


     Revisions:
        04-26-2012: CT-RAMP output argument added to apply expanded transit vehicle
                    types if desired.
        05-09-2012: Logic revised to process updated future route coding procedures.
        06-19-2013: Added logic to choose people mover links.
        08-07-2014: Added check for stops at junctions before itinerary batchin creation
        01-08-2016: Corrected itinerary batchin formatting
        02-01-2016: Metra headways coded as '99' are replaced by the TOD period duration.
        12-20-2016: Updated 'basescen' variable to '200' after base year moved to 2015.
        NRF 8/23/2017: Added support for updated future coding of additional service (action = 1)
                       to include appropriate additional service in all TOD periods.
        12/9/2019 NRF: hardcoded OHare Express layover in TOD itinerary file.
        12/10/2019 NRF: updated itinerary file formatting for case where there is only one itinerary segment.

-------------                                                             -------------
__________________________________________________________________________________________________________________________  */

%let inpath=%scan(&sysparm,1,$);
%let outpath=%scan(&sysparm,2,$);
%let sc=%scan(&sysparm,3,$);
%let ct_ramp=%scan(&sysparm,4,$);
%let scen=%eval(&sc/100);
%let reportpath=&outpath.\&scen.00\rail_changes.txt;
%let maxzone=3649;                                                        *** highest zone17 POE zone number;
%let dropnode=48007;                                                      *** Exclude South Bend station until zone system expands to include it;
%let basescen=100;                                                        *** base year scenario;
%let counter=1;
%let tod=0;
%let a1=0;%let a2=0;%let a3=0;%let a4=0;%let a5=0;%let a7=0;                        *** initialize action code counts;

data __null__;
    file "&reportpath";
    put "REPORT OF SCENARIO &sc RAIL CHANGES"/;

     *** READ IN RAIL HEADER INFORMATION ***;
  proc import datafile="&inpath.\Temp\temp_route.dbf" out=routes1 replace;

    *** READ IN RAIL ITINERARY INFORMATION ***;
  proc import datafile="&inpath.\Temp\scen_itin.dbf" out=itins1 replace;
  proc sort data=itins1; by tr_line;

       *** READ IN NODE INFORMATION ***;
  proc import datafile="&inpath.\Temp\temp_rlnode_zone.dbf" out=nodes replace; 
  data nodes(keep=node label pspace pcost ftr_pspace ftr_pcost point_x point_y zone); set nodes; 
    rename zone17=zone;

      *** READ IN LINK INFORMATION ***;
  proc import datafile="&inpath.\Temp\temp_arc.dbf" out=network replace;

      *** READ IN PEOPLE MOVER INFORMATION AND REMOVE APPROPRIATE LINKS ***;
  proc import datafile="&inpath.\Temp\temp_ppl_mvr.dbf" out=people_mover replace;

  data remove; set people_mover(where=(not(scenario ? "&scen")));
  proc sort data=remove; by anode bnode;
  proc sort data=network; by anode bnode;

    data __null__;
        file "&reportpath" mod;
        put "### O'HARE PEOPLE MOVER EXTENSION ###";

  data network(drop=scenario notes); merge network remove(in=hit); by anode bnode;
      if hit then delete;
    
    data __null__; set remove;
        file "&reportpath" mod;
        put "--> removed scenario = " scenario "people mover link anode = " anode "bnode = " bnode "from network";

*---------------------------------------------------------------*;
    *** READ IN FUTURE CODING DATA FOR SCENARIOS 200 - 700 ***;
*---------------------------------------------------------------*;
%macro future;
  %if &sc>&basescen %then %do;
        proc import datafile="&inpath.\Temp\temp_route_ftr.dbf" out=ftrrte replace;    *** future routes, limited to specified scenario;
        data ftrrte(rename=(descriptio=descr)); set ftrrte(where=(scenario ? "&scen")); 
           length actcode$2.; actcode=compress('a'||action); it_order=0;
            proc sort; by tr_line;

        proc freq data=ftrrte noprint; tables actcode / out=ftract;
        data _null_; set ftract; call symputx(actcode,count); run;                     *** store count of action codes as macro variables;


        proc import datafile="&inpath.\Temp\ftr_itin.dbf" out=ftritin replace;         *** corresponding future itineraries;
          proc sort data=ftritin; by tr_line;
          data temprte(keep=tr_line); set ftrrte;
        data ftritin; merge ftritin temprte(in=hit); by tr_line; if hit;

        proc import datafile="&inpath.\Temp\temp_arc_ftr.dbf" out=ftrarc replace;      *** future links;
        data network; set network ftrarc; proc sort nodupkey; by anode bnode;          *** add future links to base links;

  %end;
%mend future;
%future
 /* end of macro*/
run;


*-----------------------------------------------*;
    *** PROCESS TIME-OF-DAY NETWORKS ***;
*-----------------------------------------------*;
%macro getdata;
  %if &ct_ramp=1 %then %do;
      data routes1(drop=ct_veh); set routes1; veh_type=ct_veh;            *** set expanded vehicle types for CT-RAMP ***;

   *** add for future service ******;
  %end;


  %do %while (&counter le 9);
     *** set time-of-day selection criteria ***;
   %if &counter=1 %then %let select=strthour ge 20 or strthour le 5;                      
   %else %if &counter=2 %then %let select=strthour eq 6;
   %else %if &counter=3 %then %let select=strthour ge 7 & strthour le 8;
   %else %if &counter=4 %then %let select=strthour eq 9;
   %else %if &counter=5 %then %let select=strthour ge 10 & strthour le 13;
   %else %if &counter=6 %then %let select=strthour ge 14 & strthour le 15;
   %else %if &counter=7 %then %let select=strthour ge 16 & strthour le 17;
   %else %if &counter=8 %then %let select=strthour ge 18 & strthour le 19;
   %else %let select=am_share ge 0.5;

   %if &counter<9 %then %let tod=&counter; %else %let tod=am;                                 *** Set time-of-day value ***;

%put #### ------------------------------------ ####;                  
%put #### counter= &counter | TOD period= &tod ####;
%put #### ------------------------------------ ####;
         /* ------------------------------------------------------------------------------ */
                        *** OUTPUT FILES ***;
           filename out1 "&outpath.\&scen.00\rail.itinerary_&tod";
           filename out2 "&outpath.\&scen.00\railnode.extatt_&tod";
           filename out3 "&outpath.\&scen.00\rail.network_&tod";
           filename out4 "&outpath.\&scen.00\rail_summary_&tod..csv";
         /* ------------------------------------------------------------------------------ */

  
  data routes(rename=(descriptio=descr)); set routes1(where=(&select)); it_order=0; acthdwy=.;
     %if &a1>0 %then %do;
            
            data __null__;
                file "&reportpath" mod;
                put /"### NEW ROUTES &tod ###";
            
            *** -- Include Full Future Routes (Action=1) in processing -- ***; 
            data frte2(drop=actcode headway c rename=(phdwy=headway));
                set ftrrte(where=(action=1 and (tod ? "&tod")));
                c=count(headway,':');
                if c>0 then c=c+1;
                if c>0 then do; 
                    do i=1 to c by 2;
                        p1=scan(headway,i,':');
                        h1=scan(headway,i+1,':');
                        if find(p1,"&tod")>0 then phdwy=input(h1, 8.);
                        end;
                    end;
                else if c=0 then phdwy=input(headway, 8.);
                acthdwy=phdwy;
            
            data __null__; set frte2;
                file "&reportpath" mod;
                put "--> " descr ": added route " tr_line;
            
            data routes; set routes frte2;
            proc sort nodupkey; by tr_line;

            data itins1; set itins1 ftritin; proc sort nodupkey; by tr_line it_order;
     %end;
   proc freq data=routes; tables tr_line / noprint out=keep;


  data itins(drop=f_meas t_meas count percent); merge itins1(in=hit1) keep(in=hit2); by tr_line; if hit1 & hit2;
    if layover='' then layover='0'; l=input(layover,best4.);
    if dw_code=1 then dw_time=0; else dw_time=0.01;



   *** IF APPLICABLE, PROCESS FUTURE ROUTE ACTION CODES ***; 
   %if &a2>0 or &a3>0 or &a4>0 or &a5>0 or &a7>0 %then %do; %include "&inpath.\mrn_programs\apply_future_rail_actions.sas"; %end; run;

 
         * - - - - - - - - - - - - - - - - - *;
              **REPORT LAYOVER PROBLEMS**;
           data check; set itins(where=(l>0)); 
              proc freq; tables tr_line / noprint out=check;
           data check; set check(where=(count>2));
              proc print; title 'Too Many Layovers Coded';

              **REPORT ITINERARY GAPS**;
           data check; set itins; proc sort; by tr_line it_order;
           data check; set check;
             z=lag(itin_b); ln=lag(tr_line);
             if tr_line=ln & itin_a ne z then output;
              proc print; var tr_line itin_a itin_b it_order z;
               title "Gap in Itinerary: z is itin_b of Previous Segment";
         * - - - - - - - - - - - - - - - - - *;

    *** COLLAPSE CTA RAIL INTO GENERALIZED SERVICE ***;
  data itinc; set itins(where=(substr(tr_line,1,1)='c'));
  %include "&inpath.\mrn_programs\collapse_CTA_runs.sas"; run;


   ** Update Runs **;
  data rtem rtec; set routes;
    if mode='M' then output rtem; else output rtec;

  proc sort data=rtec; by tr_line;
  data rtec(drop=hdwy group runs); merge rtec keepc(in=hit); by tr_line; if hit;
    if acthdwy>0 then headway=acthdwy; else headway=hdwy;
    
  data rtem;
    set rtem;
    if headway=99 then do;
      if &tod=1 then headway=600;
      else if &tod=2 or &tod=4 then headway=60;
      else if &tod=5 then headway=240;
      else headway=120;
      end;
    run;

  data routes; set rtec rtem; 
   length ds $20.;
    descr=compress(descr,"'"); ds=substr(descr,1,20);
    proc sort; by tr_line;
  data rte(drop=it_order); set routes;

  data itins; merge itins rte(in=hit); by tr_line; if hit; proc sort; by tr_line it_order;
  data itins;
      set itins(where=(itin_a not in (&dropnode) & itin_b not in (&dropnode)));
      by tr_line it_order;
      retain o 1;
      it_order=o;
      o=o+1;
      if first.tr_line then do;
          o=1;
          it_order=o;
          o=o+1;
          end;
      if last.tr_line then layover='3';
      if (last.tr_line & substr(tr_line, 1, 3) = 'oes') then layover='0';    *** hardcoded layover for OHare Express - needs better solution ***;


  data combine; set routes itins; proc sort; by tr_line it_order;
  
       * - - - - - - - - - - - - - - - - - - - - - - - - - - *;
             **VERIFY THAT ITINERARIES DO NOT STOP AT JUNCTIONS**;
        data check; set combine(where=(((itin_b>39000 & itin_b<40000) | (itin_b>49000 & itin_b<50000)) & dw_code=0));
            proc print; title "NETWORK &scen.00 ITINERARY SEGMENTS THAT STOP AT A JUNCTION";
       * - - - - - - - - - - - - - - - - - - - - - - - - - - *;
  
  data combine; set combine; by tr_line;
    format headway speed trv_time zn_fare best9.2;
    length desc $22 d $9;
      layov=lag(layover); 
      tr_line=substr(tr_line,1,6);
      name="'"||compress(tr_line)||"'";
      desc="'"||ds||"'";
      if dw_code=1 then d=compress('dwt=#'||dw_time);
      else if dw_code=2 then d=compress('dwt=>'||dw_time);
      else if dw_code=3 then d=compress('dwt=<'||dw_time);
      else if dw_code=4 then d=compress('dwt=+'||dw_time);
      else if dw_code=5 then d=compress('dwt=*'||dw_time);
      else d=compress('dwt='||dw_time);
      lag_d=lag(d);
      

     file out1;
     if _n_=1 then put "c RAIL TRANSIT BATCHIN FILE FOR SCENARIO &scen.00 TOD &tod" / "c &sysdate" / "c us1 holds segment travel time, us2 holds zone fare" / "t lines init";
     if first.tr_line then put 'a' +1 name +2 mode +2 veh_type +2 headway +2 speed +2 desc / +2 'path=no';
     else if (it_order=1 & last.tr_line) then put +4 'dwt=0.01' +3 itin_a +2 'ttf=1' +3 'us1=' +0 trv_time +(6-length(left(trim(trv_time)))) 'us2=' +0 zn_fare / +4 'dwt=0.01' +3 itin_b +2 'lay=' +0 layover;
     else if it_order=1 then put +4 'dwt=0.01' +3 itin_a +2 'ttf=1' +3 'us1=' +0 trv_time +(6-length(left(trim(trv_time)))) 'us2=' +0 zn_fare;
     else if last.tr_line then put +4 lag_d +(10-length(left(trim(lag_d)))) itin_a +2 'ttf=1' +3 'us1=' +0 trv_time +(6-length(left(trim(trv_time)))) 'us2=' +0 zn_fare / +4 'dwt=0.01' +3 itin_b +2 'lay=' +0 layover;
     else if (layov ne '0' and layov ne '') then put +4 lag_d +(10-length(left(trim(lag_d)))) itin_a +2 'ttf=1' +3 'us1=' +0 trv_time +(6-length(left(trim(trv_time)))) 'us2=' +0 zn_fare +2 'lay=' +0 layov;
     else put +4 lag_d +(10-length(left(trim(lag_d)))) itin_a +2 'ttf=1' +3 'us1=' +0 trv_time +(6-length(left(trim(trv_time)))) 'us2=' +0 zn_fare;
    
     %if &scen=9 %then %do;
         proc export data=combine outfile="&outpath.\&scen.00\rail_itinerary_&tod..dbf" dbms=dbf replace;
     %end; 

      *** UPDATE LINK INFORMATION ***;
  data network1(drop=modes2 c); set network;
     output;
     if directions=2 then do;
       c=anode; anode=bnode; bnode=c;
       modes1=modes2;
       output;
     end;
      proc sort; by anode bnode;

      * - - - - - - - - - - - - - - - - - - - - - - - - - - *;
             **VERIFY THAT EACH LINK HAS A LENGTH**;
        data check; set network1(where=(miles=0));
           proc print; title "NETWORK &scen.00 LINKS WITHOUT A CODED LENGTH";

             **VERIFY THAT EACH LINK HAS A MODE**;
        data check; set network1(where=(modes1 is null));
           proc print; title "NETWORK &scen.00 LINKS WITHOUT A CODED MODE";
       * - - - - - - - - - - - - - - - - - - - - - - - - - - *;

      *** NETWORK LINKS ***;
      *** PART 1. LIMIT LINKS TO THOSE IN ITINERARIES ***;
  data used(keep=anode bnode); set itins;
    anode=itin_a; bnode=itin_b;
      proc sort nodupkey; by anode bnode;
  data net1; merge network1 used (in=hit); by anode bnode; if hit;  *** keep only mainline links with service;

      *** PART 2. LIMIT AUXILIARY LINKS TO THOSE CONNECTED TO SERVICE ***;
  data auxlink; set network1(where=(modes1 not ? 'C' and modes1 not ? 'M'));

  data test; set net1 auxlink;
    node=anode; output;
    node=bnode; output;
     proc freq; tables node / noprint out=test0;
   data test1(keep=anode acount); set test0; anode=node; acount=count;
   data test2(keep=bnode bcount); set test0; bnode=node; bcount=count;   

   proc sort data=auxlink; by anode;
  data auxlink; merge auxlink (in=hit) test1; by anode; if hit; proc sort; by bnode;
  data auxlink; merge auxlink (in=hit) test2; by bnode; if hit; 
    if anode<=&maxzone then acount=max(acount,4);
    if bnode<=&maxzone then bcount=max(bcount,4);
    if acount>3 and bcount>3 then output;               *** keep only auxiliary links connected to service;

  data network1; set net1 auxlink;
   format miles best9.2;
   proc sort; by anode bnode;


       *** UPDATE NODE INFORMATION ***;
  data netnodes; set network1;
   node=anode; output;
   node=bnode; output;
    proc freq; tables node / noprint out=netnodes;
  data netnodes(keep=node); set netnodes(where=(node>&maxzone));            *** note: zone centroids batched into Emme network in bus.network files;

  proc sort data=nodes; by node;
  proc sort data=netnodes; by node;
  data nodes1; merge nodes netnodes (in=hit); by node; if hit;
    format point_x point_y best15.6;
      if ftr_pspace='' then ftr_pspace='0:0';
      if ftr_pcost='' then ftr_pcost='0:0';
       c=count(ftr_pspace,':'); if c>0 then c=c+1; s=0;
       if c>0 then do; 
          do i=1 to c by 2;
          s1=scan(ftr_pspace,i,':');
          h1=scan(ftr_pspace,i+1,':');
                if s1<=&scen and s1>s then do; pspace=h1; s=s1; end;
          end;
       end;
      c=count(ftr_pcost,':'); if c>0 then c=c+1; s=0;
       if c>0 then do; 
          do i=1 to c by 2;
          s1=scan(ftr_pcost,i,':');
          h1=scan(ftr_pcost,i+1,':');
               if s1<=&scen and s1>s then do; pcost=h1; s=s1; end;
        end;
       end;
      proc sort; by node;

      * - - - - - - - - - - - - - - - - - - - - - - - - - - *;
          **VERIFY THAT EACH NODE HAS COORDINATES**;
          data check; set nodes1; if point_x='.' or point_y='.';
           proc print; title "NETWORK &scen.00 NODES WITH NO COORDINATES";

          **VERIFY THAT EACH NODE HAS A UNIQUE NUMBER**;
           proc freq data=nodes1; tables node / noprint out=check;
          data check; set check(where=(count>1));
           proc print noobs; var node count;
           title "NETWORK &scen.00 NODES WITH DUPLICATE NUMBERS";
       * - - - - - - - - - - - - - - - - - - - - - - - - - - *;

      *** WRITE OUT NODE EXTRA ATTRIBUTE BATCHIN FILE ***;
  data _null_; set nodes1;
    format zone 4.;
    file out2;
     if _n_=1 then put "  inode  @pspace  @pcost  @zone - &sysdate - NODE EXTRA ATTRIBUTES FOR SCENARIO &scen.00 TOD &tod";
     put +2 node +2 pspace +2 pcost +2 zone;

      *** WRITE OUT NETWORK BATCHIN FILE ***;
  data _null_; set nodes1;
    file out3;
    if _n_= 1 then put "c RAIL NETWORK BATCHIN FILE FOR TRANSIT SCENARIO &scen.00 TOD &tod." /
         "c  &sysdate" /  'c a  node  x  y ui1 ui2 ui3 label' / 't nodes';
    put 'a' +2 node +1 point_x  point_y +2 '0  0  0' +1 label;

  data _null_; set network1;
    file out3 mod;
     if _n_= 1 then put  / 't links';
     put 'a' +3 anode +2 bnode +2 miles +2 modes1 +2 '1  0  1';
  run;
      
      *** WRITE OUT ALL LINKS FOR LINKSHAPE FILE CREATION ***;
  %if &tod=1 %then %do;
      data all_links; set network1;
  %end;
  %else %do;
      proc append base=all_links data=network1;
  %end;
  
  %if &tod=am %then %do;
      proc sort data=all_links (keep=anode bnode) nodupkey; by anode bnode;
      proc export data=all_links dbms=csv outfile="&outpath.\&scen.00\rail_links_all.csv" replace; putnames=no;
  %end;

***CREATE SUMMARY FOR TOD PERIODS 3, 7, & AM***;
  %if &tod=3 or &tod=7 or &tod=am %then %do;
        
        ***NUMBER OF RUNS***;
        data cta metra; set combine;
            if mode='C' then output cta;
            else output metra;
        
        data cta_runs(keep=tr_line mode headway longname); set cta;
        proc sort data=cta_runs nodupkey; by tr_line;
        data cta_runs; set cta_runs;
            c_runs=120/headway;
        data metra_runs(keep=tr_line mode longname); set metra;
        proc sort data=metra_runs nodupkey; by tr_line;
        
        proc sql; create table c_run_sum as
            select mode, longname,sum(c_runs) as runs
            from cta_runs
            group by mode, longname;
        proc sql; create table m_run_sum as
            select mode, longname,count(tr_line) as runs
            from metra_runs
            group by mode, longname;
        proc sort data=m_run_sum; by mode longname;

        data run_sum; set c_run_sum;
        proc append base=run_sum data=m_run_sum;

        proc sort data=run_sum; by mode longname;

    ***DIRECTIONAL LINK MILES***;
    data dir_links(keep=mode longname itin_a itin_b); set combine;
    proc sort data=dir_links nodupkey; by longname itin_a itin_b;
    proc sort data=dir_links; by itin_a itin_b;

    data miles(keep=itin_a itin_b miles); set network1(rename=(anode=itin_a bnode=itin_b));
    proc sort data=miles; by itin_a itin_b;

    data dir_lnk_mi; merge dir_links(in=hit) miles; by itin_a itin_b; if hit;

    proc sql; create table dir_lnk_mi_sum as
        select mode, longname, sum(miles) as dir_lnk_mi
        from dir_lnk_mi
        group by mode, longname;

    proc sort data=dir_lnk_mi_sum; by mode longname;

    ***SERVICE MILES***;
    data c_itin m_itin; set combine;
        if mode='C' then output c_itin;
        else output m_itin;
    proc sort data=c_itin; by itin_a itin_b;
    proc sort data=m_itin; by itin_a itin_b;

    data c_itin_miles; merge c_itin(in=hit) miles; by itin_a itin_b; if hit;

    proc sql; create table c_run_miles as
        select tr_line,mode,longname, sum(miles) as run_mi
        from c_itin_miles
        group by tr_line, mode,longname;
    proc sort data=c_run_miles; by tr_line;

    data c_srvc_miles; merge c_run_miles(in=hit) cta_runs; by tr_line; if hit;
        all_run_mi=run_mi*c_runs;
        
    proc sql; create table c_srvc_mi_sum as
        select mode,longname, sum(all_run_mi) as srvc_mi
        from c_srvc_miles
        group by mode,longname;

    data m_itin_miles; merge m_itin(in=hit) miles; by itin_a itin_b; if hit;

    proc sql; create table m_srvc_mi_sum as
        select mode,longname,sum(miles) as srvc_mi
        from m_itin_miles
        group by mode,longname;

    data srvc_mi_sum; set c_srvc_mi_sum;
    proc append base=srvc_mi_sum data=m_srvc_mi_sum;
    proc sort data=srvc_mi_sum; by mode longname;

    ***SERVICE HOURS***;
        proc sql; create table c_times as
        select tr_line, mode, longname, sum(trv_time) as c_time
        from c_itin
        group by tr_line, mode,longname;
    proc sort data=c_times; by tr_line;

        data c_run_times; merge c_times(in=hit) cta_runs; by tr_line; if hit;
        c_run_hrs=(c_time*c_runs)/60;

    proc sql; create table c_srvc_hrs_sum as
        select mode,longname, sum(c_run_hrs) as srvc_hrs
        from c_run_times
        group by mode,longname;

    proc sql; create table m_srvc_hrs_sum as
        select mode,longname,sum(trv_time)/60 as srvc_hrs
        from m_itin
        group by mode,longname;

    data srvc_hrs_sum; set c_srvc_hrs_sum;

    proc append base=srvc_hrs_sum data=m_srvc_hrs_sum;
    proc sort data=srvc_hrs_sum; by mode longname;

    ***NUMBER OF STATIONS***;
        data stops(keep=tr_line mode longname itin_b); set combine;
            if dw_time>0 then output;

    proc sort data=stops out=stations nodupkey; by longname itin_b;

        proc sql; create table stations_sum as
        select mode, longname,count(itin_b) as stations
        from stations
        group by mode, longname;
        proc sort data=stations_sum; by mode longname;

    ***AVERAGE NUMBER OF STOPS***;
    proc sql; create table c_stops as
        select tr_line, mode, longname,count(itin_b) as stops
        from stops
        where mode = 'C'
        group by tr_line, mode, longname;
    proc sort data=c_stops; by tr_line;

    data c_tot_stops; merge c_stops(in=hit) cta_runs; by tr_line; if hit;
            tot_stops=stops*c_runs;

    proc sql; create table c_stops_sum as
            select mode, longname, sum(tot_stops) as stops, sum(c_runs) as runs
        from c_tot_stops
        group by mode, longname;

    data c_avg_stops_sum(keep=mode longname avg_stops); set c_stops_sum;
            avg_stops=stops/runs;

    proc sql; create table m_stops as
        select mode, longname, count(itin_b) as stops
        from stops
        where mode = 'M'
        group by mode, longname;
        proc sort data=m_stops; by mode longname;

    data m_avg_stops_sum(keep=mode longname avg_stops); merge m_stops(in=hit) m_run_sum; by mode longname;
        avg_stops=stops/runs;

    data avg_stops_sum; set c_avg_stops_sum;
    proc append base=avg_stops_sum data=m_avg_stops_sum;
    proc sort data=avg_stops_sum; by mode longname;

    data summaries; merge run_sum dir_lnk_mi_sum srvc_mi_sum srvc_hrs_sum stations_sum avg_stops_sum; by mode longname;
    proc export data=summaries outfile=out4 dbms=csv replace;
    run;
        
    %end;

   %let counter=%eval(&counter+1);
  %end;
%mend getdata;
%getdata
 /* end of macro*/

run;