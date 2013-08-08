/* CREATE_EMME_RAIL_FILES_GTFS.SAS
    Craig Heither, last rev. 01/27/2012

-------------                                   -------------
   PROGRAM CREATES RAIL TRANSIT NETWORK BATCHIN FILES. 
-------------                                   -------------
                                                                      */

%let inpath=%scan(&sysparm,1,$);
%let outpath=%scan(&sysparm,2,$);
%let sc=%scan(&sysparm,3,$);
%let scen=%eval(&sc/100);

%let maxzone=1961;                                                        ***highest zn09 POE zone number;
%let dropnode=48007;                                                      ***Exclude South Bend station until zone system expands to include it;


       /* ------------------------------------------------------------------------------ */
                      *** OUTPUT FILES ***;
         filename out1 "&outpath.\&scen.00\rail.itinerary";
	 filename out2 "&outpath.\&scen.00\railseg.extatt";
         filename out3 "&outpath.\&scen.00\railnode.extatt";
         filename out4 "&outpath.\&scen.00\rail.network";
       /* ------------------------------------------------------------------------------ */

   *** READ IN RAIL HEADER INFORMATION ***;
proc import datafile="&inpath.\Temp\temp_route.dbf" out=routes replace;  
data routes(rename=(descriptio=descr));  set routes;
  it_order=0;
/* **
   if ftr_headwa=' ' then ftr_headwa='0:0';
    c=count(ftr_headwa,':'); if c>0 then c=c+1; s=0;
     if c>0 then do; 
        do i=1 to c by 2;
	    s1=scan(ftr_headwa,i,':');
	    h1=scan(ftr_headwa,i+1,':');
	     if s1<=&scen and s1>s then do; headway=h1; s=s1; end;
	end;
     end;
** */
  proc freq; tables tr_line / noprint out=keep;


  *** READ IN RAIL ITINERARY INFORMATION ***;
proc import datafile="&inpath.\Temp\scen_itin.dbf" out=itins replace;  
  proc sort data=itins; by tr_line;

data itins(drop=f_meas t_meas count percent); merge itins(in=hit1) keep(in=hit2); by tr_line; if hit1 & hit2;
  if layover='' then layover='0'; l=input(layover,best4.);
  if dw_code=1 then dw_time=0; else dw_time=0.01;

       * - - - - - - - - - - - - - - - - - *;
            **REPORT LAYOVER PROBLEMS**;
         data check; set itins; if l>0; 
            proc freq; tables tr_line / noprint out=check;
         data check; set check;
            if count>2;
            proc print; 
            title 'Too Many Layovers Coded';

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
%include "&inpath.\Programs\collapse_CTA_runs.sas";


 ** Update Runs **;
data rtem rtec; set routes;
  if mode='M' then output rtem; else output rtec;

proc sort data=rtec; by tr_line;
data rtec(drop=hdwy group runs); merge rtec keepc(in=hit); by tr_line; if hit;
  headway=hdwy;
  
data routes; set rtec rtem; 
 length ds $20.;
  descr=compress(descr,"'"); ds=substr(descr,1,20);
  proc sort; by tr_line;
data rte(drop=it_order); set routes;

data itins; merge itins rte(in=hit); by tr_line; if hit; proc sort; by tr_line it_order;
data itins; set itins(where=(itin_a not in (&dropnode) & itin_b not in (&dropnode))); by tr_line it_order;
  if last.tr_line then layover='3';


data combine; set routes itins;
    proc sort; by tr_line it_order;
data combine; set combine; by tr_line;
  format headway speed trv_time zn_fare best9.2;
  length desc $22 d $9;
    layov=lag(layover); 
    tr_line=substr(tr_line,1,6);
    name="'"||compress(tr_line," ")||"'";
    desc="'"||ds||"'";
    if dw_code=1 then d=compress('dwt=#'||dw_time,' ');
    else if dw_code=2 then d=compress('dwt=>'||dw_time,' ');
    else if dw_code=3 then d=compress('dwt=<'||dw_time,' ');
    else if dw_code=4 then d=compress('dwt=+'||dw_time,' ');
    else if dw_code=5 then d=compress('dwt=*'||dw_time,' ');
    else d=compress('dwt='||dw_time,' ');

   file out1;
   if _n_=1 then put "c RAIL TRANSIT BATCHIN FILE FOR SCENARIO &scen.00" /
          "c  &sysdate" / 't lines init';
   if first.tr_line then put 'a' +0 name +2 mode +2 veh_type +2 headway +2 speed
           +2 desc / +2 'path=no';
   else if last.tr_line then put +4 itin_a d +1 'ttf=1' / +4 itin_b +2 'lay=' +0 layover;
   else if dw_code=1 then put +4 itin_a +7 d +4 'ttf=1';
   else if (layov ne '0' and layov ne '') then put +4 itin_a d +1 'ttf=1' +2 'lay=' +0 layov;
   else put +4 itin_a d +1 'ttf=1';

data combine; set combine(where=(it_order>0));
  file out2;
   if _n_=1 then put " line    inode  jnode  @ltime  @zfare - &sysdate - SEGMENT EXTRA ATTRIBUTES FOR SCENARIO &scen.00";
    put +1 tr_line +1 itin_a +1 itin_b +2 trv_time +2 zn_fare;



     *** READ IN NODE INFORMATION ***;
proc import datafile="&inpath.\Temp\temp_node.dbf" out=nodes replace;  
data nodes; set nodes;
   if node>&maxzone;
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

     *** LIMIT TO NODES USED BY ITINERARIES ***;   
data used(keep=node); set itins; node=itin_a; output; node=itin_b; output;
  proc sort nodupkey; by node;

data nodes1; merge nodes used (in=hit); by node; if hit;

       * - - - - - - - - - - - - - - - - - - - - - - - - - - *;
          **VERIFY THAT EACH NODE HAS A UNIQUE NUMBER**;
           proc freq; tables node / noprint out=check;
          data check; set check; if count>1;
           proc print noobs; var node count;
           title "NETWORK &scen.00 NODES WITH DUPLICATE NUMBERS";
       * - - - - - - - - - - - - - - - - - - - - - - - - - - *;

     *** ATTACH ZONE TO NODES ***;
proc import datafile="&inpath.\Temp\temp_rlnode_zone.dbf" out=ndzn replace; 
data ndzn(keep=node zone); set ndzn; rename zone09=zone; proc sort; by node;

data nodes1; merge nodes1 (in=hit) ndzn; by node; if hit;
data nodes1(keep=node label point_x point_y); set nodes1;
  format zone 4.;
  file out3;
   if _n_=1 then put "  inode  @pspace  @pcost  @zone - &sysdate - NODE EXTRA ATTRIBUTES FOR SCENARIO &scen.00";
   put +2 node +2 pspace +2 pcost +2 zone;



      *** READ IN LINK INFORMATION ***;
proc import datafile="&inpath.\Temp\temp_arc.dbf" out=network replace;  
data network(drop=modes2 c); set network;
   output;
   if directions=2 then do;
     c=anode; anode=bnode; bnode=c;
     modes1=modes2;
     output;
   end;
    proc sort; by anode bnode;

      * - - - - - - - - - - - - - - - - - - - - - - - - - - *;
             **VERIFY THAT EACH LINK HAS A LENGTH**;
        data check; set network; if miles=0;
         proc print; 
         title "NETWORK &scen.00 LINKS WITHOUT A CODED LENGTH";

             **VERIFY THAT EACH LINK HAS A MODE**;
        data check; set network; if modes1='';
         proc print; 
         title "NETWORK &scen.00 LINKS WITHOUT A CODED MODE";
       * - - - - - - - - - - - - - - - - - - - - - - - - - - *;

      *** NETWORK LINKS ***;
      *** PART 1. LIMIT LINKS TO THOSE IN ITINERARIES ***;
data used(keep=anode bnode); set itins;
  anode=itin_a; bnode=itin_b;
    proc sort nodupkey; by anode bnode;
data net1; merge network used (in=hit); by anode bnode; if hit;  *** keep only mainline links with service;

      *** PART 2. LIMIT AUXILIARY LINKS TO THOSE CONNECTED TO SERVICE ***;
data auxlink; set network(where=(modes1 not ? 'C' and modes1 not ? 'M'));

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

data network; set net1 auxlink;
format miles best9.2;
proc sort; by anode bnode;


data netnodes; set network;
 node=anode; output;
 node=bnode; output;
  proc freq; tables node / noprint out=netnodes;
data netnodes(keep=node); set netnodes;
  if node>&maxzone; 

data nodes; merge nodes netnodes (in=hit); by node;
  if hit;
  format point_x point_y best15.6;
      * - - - - - - - - - - - - - - - - - - - - - - - - - - *;
          **VERIFY THAT EACH NODE HAS COORDINATES**;
          data check; set nodes; if point_x='.' or point_y='.';
           proc print; 
           title "NETWORK &scen.00 NODES WITH NO COORDINATES";
       * - - - - - - - - - - - - - - - - - - - - - - - - - - *;

      *** WRITE OUT NETWORK BATCHIN FILE ***;
data nodes; set nodes;
  file out4;
  if _n_= 1 then put "c RAIL NETWORK BATCHIN FILE FOR TRANSIT SCENARIO &scen.00" /
         "c  &sysdate" /  'c a  node  x  y ui1 ui2 ui3 label' / 't nodes';
  put 'a' +2 node +1 point_x  point_y +2 '0  0  0' +1 label;

data network; set network;
  file out4 mod;
   if _n_= 1 then put  / 't links';
   put 'a' +3 anode +2 bnode +2 miles +2 modes1 +2 '1  0  1';

run;
