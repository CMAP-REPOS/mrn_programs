/*
    Revisions
    ---------
    NRF 8/29/17: Reads updated future coding that includes new TOD field.
*/

options noxwait;

%let maxzn=3632;                                    ** highest zone09 POE;
%let tothold=0;
%let ctafix=0;
%let metrafix=0;
%let count=1;

/*-------------------------------------------------------------*/
filename innew "&rtefile";
filename in4 "&dir.\short_path.txt";
filename out4 "&dir.\link_dictionary.txt";
/*-------------------------------------------------------------*/

%macro getdata;

    *** Read in and Format Spreadsheet Coding ***;
    %if %sysfunc(fexist(innew)) %then %do;
        ** READ IN CODING FOR RAIL ITINERARIES **;
        proc import datafile="&rtefile" out=section dbms=xlsx replace;
		  sheet="itinerary";
		  getnames=yes;
        data section;
		  set section(where=(tr_line is not null));
		  tr_line=lowcase(tr_line);
		proc sort;
		  by tr_line order;
    %end;
    %else %do;
        data null;
        file "&dir.\rail_path.lst";
        put "File not found: &rtefile";
        endsas;
    %end;
	
%mend getdata;
%getdata
/* end macro */


      ** READ IN ROUTE TABLE CODING **;
proc import out=rte datafile="&rtefile" dbms=xlsx replace;
    sheet="header";
    getnames=yes;
    run;
data rte(drop=TOD SCENARIO RSP_ID rename=(TOD1=TOD SCENARIO1=SCENARIO RSP_ID1=RSP_ID)); set rte;
    TOD1=left(put(TOD,10.));
    SCENARIO1=left(put(SCENARIO,10.));
    RSP_ID1=left(put(RSP_ID, 3.));
    run;

data rte(drop=i); set rte(where=(tr_line is not null & action>=1));
  tr_line=lowcase(tr_line);
  description=upcase(compress(description,"'")); len=min(20,length(description)); description=substr(description,1,len);
  notes=upcase(compress(notes,"'")); len=min(30,length(notes)); notes=substr(notes,1,len);
    array zero(*) _numeric_;
      do i=1 to dim(zero);
       if zero(i)=. then zero(i)=0;
      end;
   proc sort nodupkey; by tr_line;
data action(keep=tr_line action); set rte;

data section; merge section action; by tr_line;

data section(drop=layover i); set section(where=(tr_line is not null & order=int(order)));
 length lo $8.;
    array zero(*) _numeric_;
      do i=1 to dim(zero);
       if zero(i)=. then zero(i)=0;
      end;
  if dw_code='1' then dw_time=0; else dw_time=0.01;
  trv_time=round(trv_time,.1);
  group=lag(tr_line);
  if layover>0 then lo=put(layover,8.0); else lo='';

**=====================================================================================**;
  *** VERIFY ITINERARIES HAVE HEADERS AND VICE-VERSA ***;
data r(keep=tr_line r); set rte; r=1;
data s(keep=tr_line i); set section; i=1; proc sort nodupkey; by tr_line;
data s; merge s r; by tr_line;
data check; set s; if r=1 & i=.; proc print; title "Route with no Itinerary";
data check; set s; if i=1 & r=.; proc print; title "Itinerary with no Header";

  *** VERIFY ITINERARY CODING MATCHES NETWORK LINKS ***;
data verify; set section; proc sort; by itin_a itin_b;
data ver1; set verify(where=(action not in (2,3,6,7)));
data check; merge ver1 (in=hit) mi; by itin_a itin_b; if hit;
   if miles>0 then delete;
     proc print; var itin_a itin_b tr_line order;
     title 'MIS-CODED ANODE-BNODE OR DIRECTIONAL PROBLEM ON THESE LINKS';

  *** VERIFY ITINERARY CODING APPROPRIATE FOR ACTION CODE ***;
data ver1; set verify(where=(action=1 & ((itin_b>38999 & itin_b<40000) | (itin_b>48999 & itin_b<50000)) & dw_code='0'));
   proc print; title 'BAD DWELL CODE AT JUNCTION FOR ACTION=1';

data ver2; set verify(where=(action=2 & trv_time=0));
   proc print; title 'BAD TRAVEL TIME REDUCTION VALUE FOR ACTION=2';

data ver3; set verify(where=(action=3 & lo=''));
   proc print; title 'NO NEW STATION CODED FOR ACTION=3';

data ver5; set verify(where=(action=5 & (lo='' or order not in (1,2,6))));
   proc print; title 'NO NEW NODE NUMBER OR BAD NODE IDENTIFIER FOR ACTION=5';

data ver6; set verify(where=(action=6 & trv_time ne 0));
   proc print; title 'NONZERO TRAVEL TIME REDUCTION VALUE FOR ACTION=6';

data ver7; set verify(where=(action=7 & lo=''));
   proc print; title 'NO CONSOLIDATED STATION CODED FOR ACTION=7';

  *** VERIFY SCENARIO IS CODED ***;
data check; set rte(where=(scenario=''));
     proc print; title 'BAD SCENARIO CODING';

  *** VERIFY ONLY ONE MODE IS CODED ***;
data check; set rte(where=(length(mode)>1));
     proc print; title 'BAD MODE CODING';

  ** REPORT LAYOVER PROBLEMS (MAX. OR 2 PER LINE) **;
data check; set verify(where=(action=1 & lo ne ''));
   proc freq; tables tr_line / noprint out=check;
data check; set check(where=(count>2));
   proc print; var tr_line count; Title 'Too Many Layovers Coded';
**=====================================================================================**;

 *-----------------------------------------*;
 *** PREPARE ITINERARIES FOR GEODATABASE ***
 *-----------------------------------------*;
 * ##-- Action in (1,5) --##;
 * itinerary segments are coded to actual network links for these action codes ;
     *** RESET ITINERARY ORDER ***;
data sect1; set section(where=(action in (1,5)));
data sect1(drop=order); set sect1;
   retain it_order 1;
   it_order+1;
   if tr_line ne group then it_order=1;
   output;

data sect1(drop=x y); set sect1;
   ***-- swap in new node for action=5 so it will plot revised path in ArcMap -- ***;
   x=0; y=0;
   if action=5 then do;
      orig_a=itin_a; orig_b=itin_b; orig_lo=lo;
      if it_order=1 then do; x=itin_a; y=lo; itin_a=y; lo=put(x,5.0); end;
      if it_order=2 then do; x=itin_b; y=lo; itin_b=y; lo=put(x,5.0); end;
   end;

data sect4; set section(where=(action=4));    *** do not reorder segments;


  ** REPORT ITINERARY GAPS **;
data check; set sect1;
   z=lag(itin_b);
   if itin_a ne z and it_order>1 then output;
    proc print; var tr_line it_order itin_a itin_b z; title "Gap in Itinerary: z is itin_b of Previous Segment";

 * ##-- Action in (2,3,6,7) --##;
 * itinerary segments MAY NOT be coded to actual network links for these action codes, so they must be determined ;
data sect2; set section(where=(action in (2,3,6,7)));
data temp; set sect2 nobs=totobs; call symput('tothold',left(put(totobs,8.))); run;


       ** -- Find Shortest Path To Complete Itinerary Coding -- **;
%macro itinfix;
  %if &tothold>0 %then %do;

      data short(keep=itin_a itin_b tr_line); set sect2; proc sort nodupkey; by itin_a itin_b;

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
      data _null_; command="if exist &dir.\short_path.txt (del &dir.\short_path.txt /Q)" ; call system(command);

      *** -- PROCESS CTA SEGMENTS -- ***;
      data short1(drop=tr_line); set short(where=(substr(tr_line,1,1)='c')); num=_n_;
      data temp; set short1 nobs=fixobs; call symput('ctafix',left(put(fixobs,8.))); run;
      data railnet(rename=(itin_a=itinerary_a itin_b=itinerary_b miles=mhnmi)); set arcs; base=1;
           proc sort nodupkey; by itinerary_a itinerary_b;

      %if &ctafix>0 %then %do;
          *** -- SETUP AVAILABLE NETWORK -- ***;
          data net1; set railnet(where=(30000<=itinerary_a<=39999 & 30000<=itinerary_b<=39999));
          %include "&srcdir.\write_dictionary.sas";
      %end;
      %do %while (&count le &ctafix);
          data shrt; set short1(where=(num=&count));
             call symput('a',left(put(itin_a,5.))); call symput('b',left(put(itin_b,5.))); run;
          data _null_;
             command="%bquote(&runpython) &srcdir.\find_shortest_path.py &a &b &dir.\";
             call system(command);
         %let count=%eval(&count+1);
      %end;

      *** -- PROCESS METRA SEGMENTS -- ***;
      %let count=1;
      data short1(drop=tr_line); set short(where=(substr(tr_line,1,1)='m')); num=_n_;
      data temp; set short1 nobs=fixobs; call symput('metrafix',left(put(fixobs,8.))); run;

      %if &metrafix>0 %then %do;
          *** -- SETUP AVAILABLE NETWORK -- ***;
          data net1; set railnet(where=(40000<=itinerary_a<=49999 & 40000<=itinerary_b<=49999));
          %include "&srcdir.\write_dictionary.sas";
      %end;
      %do %while (&count le &metrafix);
          data shrt; set short1(where=(num=&count));
             call symput('a',left(put(itin_a,5.))); call symput('b',left(put(itin_b,5.))); run;
          data _null_;
             command="%bquote(&runpython) &srcdir.\find_shortest_path.py &a &b &dir.\";
             call system(command);
         %let count=%eval(&count+1);
      %end;


    %include "&srcdir.\read_future_path_output.sas";
  %end;
%mend itinfix;
%itinfix
 /* end macro*/
**=====================================================================================**;

  ** CREATE ONE SECTION FILE FOR STORING IN GEODATABASE **;
  **   (PLUS RENAME VARIABLES AND SET CONSISTENT LENGTHS) **;
data sect2(rename=(order=it_order)); set sect2;
data section(drop=tr_line); set sect1 sect2 sect4; length ln $8.; ln=tr_line;
data section(rename=(ln=tr_line lo=layover)); set section; proc sort; by tr_line;
data rte(drop=tr_line scenario mode); set rte; length ln scen $8. m $1.;  ln=tr_line; scen=put(scenario,8.0); m=substr(mode,1,1);
data rte(rename=(ln=tr_line scen=scenario m=mode)); set rte;


  *** DELETE APPROPRIATE ROUTES FROM EXISTING CODING TABLE SO THEY CAN BE UPDATED ***;
data kill(keep=tr_line); set rte; proc sort nodupkey; by tr_line;
data rt; merge rt kill (in=hit); by tr_line; if hit then delete;
data done; set rt;                                                                  *** existing routes that will be re-imported as-is;
   data _null_; set done nobs=totobs; call symput('keeporig',left(put(totobs,8.))); run;

data rt; set rt rte; proc sort; by tr_line;
proc sort data=good; by tr_line;
data good; merge good kill (in=hit); by tr_line; if hit then delete;
