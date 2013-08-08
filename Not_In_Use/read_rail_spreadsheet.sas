
filename innew "&rtefile";




      *** Read in and Format Spreadsheet Coding ***;
       %if %sysfunc(fexist(innew)) %then %do;
             ** READ IN CODING FOR RAIL ITINERARIES **;
            proc import out=section datafile="&rtefile" dbms=xls replace; 
             sheet="itinerary"; getnames=yes; mixed=yes;
               proc sort data=section; by line order;
       %end;
       %else %do;
         data null;
           file "&dir.\Temp\rail_path.lst";
           put "File not found: &rtefile";
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
       proc import out=rte datafile="&rtefile" dbms=xls replace; sheet="header"; getnames=yes;

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