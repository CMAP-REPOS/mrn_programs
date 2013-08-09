/* read_rail_feed_data.sas
   Craig Heither, last revised 03/08/2012

--------------                          --------------
   PROGRAM IS CALLED BY  AND
   FORMATS RAIL ITINERARIES TO BUILD IN GEODATABASE.


    revised  03-08-2012: calculate AM share after all other processing finished.
--------------                          --------------   */

options noxwait;

%let maxzn=1961;                                    ** highest zone09 POE;
%let peakst=25200;                                  ** 7:00 AM in seconds;
%let peakend=32400;                                 ** 9:00 AM in seconds;
%let tothold=0;
%let ctafix=0;
%let metrafix=0;
%let count=1;
%let nostop=48006;                                  ** Metra Ravinia Park stop - allow no stops ;
%let samenode=0;

/*-------------------------------------------------------------*/
filename in4 "&dir.\import\short_path.txt";
filename out4 "&dir.\import\link_dictionary.txt";
filename nwstatin "&dir.\ScenarioNetworkRail_forEmme\900\new_station_rail_itinerary.csv";
/*-------------------------------------------------------------*/


*=======================================================================*;
 *** INPUT METRA AND SOUTH SHORE MONTHLY PASS COST TO CALCULATE ZONE FARE ***;
   * - COSTS AS OF FEBRUARY 2012 (reflect Metra increase) -;
   * - SOUTH SHORE: USE ZN 1-3 COST FOR ZNS 1 & 2 (DO NOT STOP AT ME STATIONS) -;
*=======================================================================*;
data zf1; infile datalines missover dsd;    **** METRA MONTHLY PASS ;
  input zone $ cost_a;
  datalines;
   A,78.25
   B,85.50
   C,121.00
   D,135.25
   E,149.50
   F,163.75
   G,178.00
   H,192.25
   I,206.50
   J,220.75
   K,235.00
   M,263.50
   ;
data zf1(drop=zone); set zf1; length zone_id_a $3.; zone_id_a=zone; proc sort; by zone_id_a;

data zf1b; infile datalines missover dsd;    **** SOUTH SHORE MONTHLY PASS ;
  input zone $ cost_a;
  datalines;
   1,135.25
   2,135.25
   3,135.25
   4,147.85
   5,165.95
   6,197.35
   7,223.05
   8,232.70
   10,286.70
   11,315.65
   ;
data zf1b(drop=zone); set zf1b; length zone_id_a $3.; zone_id_a=zone; proc sort; by zone_id_a;


*-----------------------------------*;
   *** BEGIN PROCESSING RUN DATA ***;
*-----------------------------------*;
proc import out=route datafile="&rtefile" dbms=csv replace; getnames=yes; guessingrows=15000;
 data route(drop=line shape_id); set route; length ln $20.;
  if length(line)<20 then ln=line; else ln=substr(line,1,20);
  proc sort; by ln;
 data route; set route; rename ln=line;

proc import out=sec1 datafile="&segfile" dbms=csv replace; getnames=yes; guessingrows=300000;  
 data sec1(drop=line shape_id); set sec1; length ln $20.;
  if length(line)<20 then ln=line; else ln=substr(line,1,20);
  proc sort; by ln;
 data sec1; set sec1; rename ln=line;
 data sec1; length zone_id_a $3. zone_id_b $3.; set sec1;

 *** IDENTIFY & REMOVE ROUTES WITH ONLY ONE ITINERARY SEGMENT WHERE ITINA=ITINB ***;
data sec1; set sec1; if line='' then delete;               
data check; set sec1; proc summary nway; class line; output out=chk1;
data sec1; merge sec1 chk1; by line; 
data sec1(drop=_type_ _freq_) bad; set sec1;
  if _freq_=1 & itinerary_a=itinerary_b then output bad; else output sec1;

data bad; set bad; proc print; title "Bad Itinerary Coding";

data keeprte(keep=line); set sec1; proc sort nodupkey; by line;

*-----------------------------------*;
   *** FORMAT ROUTE HEADER DATA ***;
*-----------------------------------*;
data route(drop=j1-j3); merge route keeprte (in=hit); by line; if hit;
  description=upcase(description); route_id=upcase(route_id);
  route_long_name=upcase(route_long_name);  direction=upcase(direction); terminal=upcase(terminal);
  if mode='C' then do;
    type=7; 
    if route_id='BLUE' then prefix='cbl';
    else if route_id='BROWN' then prefix='cbr';
    else if route_id='GREEN' then do;
       if index(description,'ASHLAND')>0 then prefix='cga'; else prefix='cgc'; end;   ***Differentiate between Ashland and Cottage Grove branches***;
    else if route_id='ORANGE' then prefix='cor';
    else if route_id='PINK' then prefix='cpk';
    else if route_id='PURPLE' then prefix='cpr';
    else if route_id='RED' then prefix='crd';
    else if route_id='YELLOW' then prefix='cye';
  end;
  else if mode='M' then do;
    type=8;
	*** strip out run number and store in route_id ***;
     if substr(line,1,5)="metra" then j3=scan(line,2,"_");
     else do; j1=length(line); j2=anydigit(line); j3=substr(line,j2,j1-j2+1); end;
     route_id=compress(j3,'ABCDEFGHIJKLMNOPQRSTUVWXYZ');
	*** create line name prefix ***;
     length a $5;
     if index(line,'BNSF_')>0 then do; prefix='mbn'; a='BNSF'; end;
     else if index(line,'HC_')>0 then do; prefix='mhc'; a='HC'; end;
     else if index(line,'MD-N_')>0 then do; prefix='mmn'; a='MD-N'; end;
     else if index(line,'MD-W_')>0 then do; prefix='mmw'; a='MD-W'; end;
     else if index(line,'ME_')>0 then do; prefix='mme'; a='ME'; end;
     else if index(line,'NCS_')>0 then do; prefix='mnc'; a='NCS'; end;
     else if index(line,'RI_')>0 then do; prefix='mri'; a='RI'; end;
     else if index(line,'SWS_')>0 then do; prefix='msw'; a='SWS'; end;
     else if index(line,'UP-NW_')>0 then do; prefix='mnw'; a='UP-NW'; end;
     else if index(line,'UP-N_')>0 then do; prefix='mun'; a='UP-N'; end;
     else if index(line,'UP-W_')>0 then do; prefix='muw'; a='UP-W'; end;
     else if index(line,'shore')>0 then do; prefix='mss'; a='SS'; end;
  end;
  speed=max(15,round(speed));
  headway=99;
   proc sort; by mode prefix line;

data route; set route; by mode prefix line; pr=lag(prefix);
%macro selseries;
    %if %index(&origitin,base) %then %do;
        data route; set route; by mode prefix line;
            retain q 0;
            q+1;
            if prefix ne pr then q=1;
            output;
    %end;
    %else %do;
        data route; set route; by mode prefix line;
            retain q 400;
            q+1;
            if prefix ne pr then q=401;
            output;
    %end;
%mend selseries;
%selseries
run;

data route(drop=q prefix pr temp1 description d a); set route;
 length newline $6. temp1 $3. descr d $50. fdline $20. r_id $10. rln dir term $32. ; 
  temp1=q;
  newline=tranwrd(prefix||temp1,'','0'); 
  if mode='C' then descr=description;
  else do;
    d=tranwrd(scan(description,2,'-'),' METRA ','');
    descr=trim(route_id)||" "||trim(a)||" -"||trim(d);
  end;
  if length(line)<20 then fdline=line; else fdline=substr(line,1,20);
  if length(route_id)<10 then r_id=route_id; else r_id=substr(route_id,1,10);
  if length(route_long_name)<32 then rln=route_long_name; else rln=substr(route_long_name,1,32); 
  if length(direction)<32 then dir=direction; else dir=substr(direction,1,32); 
  if length(terminal)<32 then term=terminal; else term=substr(terminal,1,32);
   proc sort; by newline;

*-----------------------------------*;
 *** FORMAT ITINERARY SEGMENT DATA ***;
*-----------------------------------*;
proc sql noprint;
  create table section as
      select sec1.*,
	       route.newline,mode
      from sec1,route
      where sec1.line=route.line;

data section(drop=shape_dist_trav_a shape_dist_trav_b); set section;
  ltime=round(ltime,.1); imputed=0; group=lag(line);
  rename skip_flag=dwcode;
   proc sort; by newline order;

  ** -- adjust itinerary coding if segment has same node at beginning and ending -- **;
data same section; set section;
    if itinerary_a=itinerary_b then output same;
    else output section;

data temp; set same nobs=smnode;
    call symput('samenode',left(put(smnode,8.)));
run;

%macro segfix;
    %if &samenode>0 %then %do;
        proc sort data=same; by newline order;
        data same; set same; by newline order;
            nl=lag(newline);
            o=lag(order);
        data same; set same;
            retain g 0;
            if newline ne nl and order ne o+1 then g+1;
            output;

        proc summary nway; class g newline; var order dep_time arr_time ltime;
            output out=fixit max(order)=ordmax min(order)=ordmin min(dep_time)= max(arr_time)= sum(ltime)=addtime;
        proc summary nway data=section; class newline; var order;
            output out=lineend max=lnmax;
        data fixit(drop=_type_ _freq_); merge fixit lineend; by newline;
        data fix1(keep=newline order arr_time addtime); set fixit(where=(ordmax>lnmax));    *** adjust data if last entry in itinerary;
            order=ordmin-1;
        data fix2(keep=newline order dep_time addtime2); set fixit(where=(ordmax<=lnmax));    *** apply to subsequent segment;
            order=ordmax+1;
            rename addtime=addtime2;
        data section(drop=addtime addtime2); merge section (in=hit) fix1 fix2; by newline order; if hit;
            if addtime>0 or addtime2>0 then do;
                addtime=max(addtime,0);
                addtime2=max(addtime2,0);
                ltime=ltime+addtime+addtime2;
            end;
    %end;
%mend segfix;
%segfix
run;            

  ** -- zone fare calculation -- **;
data a b c; set section;
  if mode='C' then output a;
  else if mode='M' & substr(line,1,5)='metra' then output b;
  else output c;

  ** Metra **;
proc sort data=b; by zone_id_a;
data zf2(rename=(zone_id_a=zone_id_b cost_a=cost_b)); set zf1;
data b; merge b(in=hit) zf1; by zone_id_a; if hit;
  proc sort; by zone_id_b;
data b; merge b(in=hit) zf2; by zone_id_b; if hit;
  if cost_a=cost_b then zfare=0; else zfare=round(abs(cost_a-cost_b)/40*100,.01);

  ** South Shore **;
proc sort data=c; by zone_id_a;
data zf2b(rename=(zone_id_a=zone_id_b cost_a=cost_b)); set zf1b;
data c; merge c(in=hit) zf1b; by zone_id_a; if hit;
  proc sort; by zone_id_b;
data c; merge c(in=hit) zf2b; by zone_id_b; if hit;
  if cost_a=cost_b then zfare=0; else zfare=round(abs(cost_a-cost_b)/40*100,.01);

data section; set a b c; proc sort; by newline order;
  ** -- end zone fare calculation -- **;

*-----------------------------------*;
        *** VERIFY CODING ***;
*-----------------------------------*;
data verify; set section; proc sort; by itinerary_a itinerary_b;


%macro newstationlinks;
    
    %if %sysfunc(fexist(nwstatin)) & %index(&origitin,all_runs_itin) %then %do;
        
        proc import out=nwstatin1 datafile=nwstatin dbms=csv replace; getnames=yes; guessingrows=15000;
        data nwstalnks(keep=itin_a itin_b); set nwstatin1;
        proc sort data=nwstalnks nodupkey; by itin_a itin_b;
        
        proc sort data=mi; by itin_a itin_b;
        data mhn(rename=(miles=mhnmi itin_a=itinerary_a itin_b=itinerary_b)); merge nwstalnks(in=hit1) mi(in=hit2); by itin_a itin_b;
            if hit1 and hit2;
            match=1;
            base=1;
        proc sort; by itinerary_a itinerary_b;
    %end;
    %else %do;
        data mhn(rename=(miles=mhnmi itin_a=itinerary_a itin_b=itinerary_b)); set mi;
            match=1;
            base=1;
        proc sort; by itinerary_a itinerary_b;
    %end;

%mend newstationlinks;
%newstationlinks
run;


data verify; merge verify (in=hit) mhn; by itinerary_a itinerary_b; if hit;

** Hold Segments that Do Not Match MHN Links or are the Wrong Direction **;
** -- This file can be used for troubleshooting and verification -- **;
data hold(drop=group match); set verify(where=(match ne 1));
    proc export data=hold outfile="&dir.\import\hold_times.csv" dbms=csv replace;
data temp; set hold nobs=totobs; call symput('tothold',left(put(totobs,8.))); run;
data short(keep=itinerary_a itinerary_b mode); set hold; proc sort nodupkey; by itinerary_a itinerary_b;

       ** -- Iterate Through List of Itinerary Gaps to Find Shortest Path, If Necessary -- **;
%macro itinfix;
  %if &tothold>0 %then %do;

      *** SET UP PYTHON COMMANDS ***;
      data _null_;
         command="if exist pypath.txt (del pypath.txt /Q)" ; call system(command);
         command="ftype Python.File >> pypath.txt" ; call system(command);
      data null; infile "pypath.txt" length=reclen;
         input location $varying254. reclen; 
         loc=scan(location,2,'='); goodloc=substr(loc,1,index(loc,'.exe"')+4);
         call symput('runpython',trim(goodloc)); 
         run;
      data _null_; command="if exist pypath.txt (del pypath.txt /Q)" ; call system(command);
      data _null_; command="if exist &dir.\import\short_path.txt (del &dir.\import\short_path.txt /Q)" ; call system(command); 

      *** -- PROCESS CTA SEGMENTS -- ***;
      data short1; set short(where=(mode='C')); num=_n_;
      data temp; set short1 nobs=fixobs; call symput('ctafix',left(put(fixobs,8.))); run;

      data net1; set mhn(where=(30000<=itinerary_a<=39999 & 30000<=itinerary_b<=39999));
      %include "&dir.\mrn_programs\write_dictionary.sas";

      %do %while (&count le &ctafix);  
          data shrt; set short1(where=(num=&count));
             call symput('a',left(put(itinerary_a,5.))); call symput('b',left(put(itinerary_b,5.))); run;
          data _null_;
             command="%bquote(&runpython) &dir.\mrn_programs\find_shortest_path.py &a &b &dir.\";
             call system(command);
         %let count=%eval(&count+1);
      %end;

      *** -- PROCESS METRA SEGMENTS -- ***;
      %let count=1;
      data short1; set short(where=(mode='M')); num=_n_;
      data temp; set short1 nobs=fixobs; call symput('metrafix',left(put(fixobs,8.))); run;

      data net1; set mhn(where=(40000<=itinerary_a<=49999 & 40000<=itinerary_b<=49999));
      %include "&dir.\mrn_programs\write_dictionary.sas";

      %do %while (&count le &metrafix);  
          data shrt; set short1(where=(num=&count));
             call symput('a',left(put(itinerary_a,5.))); call symput('b',left(put(itinerary_b,5.))); run;
          data _null_;
             command="%bquote(&runpython) &dir.\mrn_programs\find_shortest_path.py &a &b &dir.\";
             call system(command);
         %let count=%eval(&count+1);
      %end;


    %include "&dir.\mrn_programs\read_path_output.sas";
  %end;
%mend itinfix;
%itinfix
 /* end macro*/


*-----------------------------------*;
 *** PREPARE ITINERARY SEGMENT DATA ***;
*-----------------------------------*;
data newitin(drop=order); set newitin;
   retain ordnew 1;
      ordnew+1;
      if line ne group then ordnew=1;
     output;
proc sort; by newline ordnew;


 *** CALCULATE AM SHARE ***;
data section; set newitin; by newline ordnew;
  if dep_time>=&peakst and arr_time<=&peakend then am=1;                      ** segment occurs during AM Peak;
   proc summary nway data=section; class newline; var am; output out=stats sum=;

** Get Run Start Time - Assume Zero is Incorrect **;
data sect1; set section; by newline ordnew;
 if dep_time=0 then start=arr_time; else start=min(dep_time,arr_time);
 if start=0 then delete;
data sect1(keep=newline start); set sect1; by newline ordnew; if first.newline;

data stats(keep=newline ampct); set stats; ampct=max(0,round(am/_freq_,.01));
proc sort data=route; by newline;
data route; merge route sect1 stats; by newline; 
  if start=. then start=0; strthour=int(start/3600);


data newitin(drop=zone_id_a zone_id_b cost_a cost_b match base mhnmi line mode group); set newitin; by newline ordnew;
  if last.newline then layover=3; else layover=0;
  zfare=max(0,zfare);
  if itinerary_b=&nostop then dwcode=1;
  rename itinerary_a=itin_a itinerary_b=itin_b newline=tr_line ordnew=it_order dwcode=dw_code zfare=zn_fare ltime=trv_time;

data good; retain tr_line itin_a itin_b it_order layover dw_code zn_fare trv_time dep_time arr_time imputed; set newitin;
 proc sort; by itin_a itin_b;

data check; set newitin(where=(itin_a=itin_b or itin_a<=&maxzn or itin_b<=&maxzn));
 proc sort nodupkey; by itin_a itin_b;
 proc print; var tr_line itin_a itin_b it_order trv_time;  title "Bad Itinerary Segments";

run;
