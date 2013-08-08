*================================================================*;
   *** UPDATE ITINERARY TO REFLECT SPLIT LINKS W/ TEMPORARY ANODE-BNODE VALUES (ONLY IF NEW_MILE.DBF EXISTS) ***;
*================================================================*;


filename nwmi "&dir.\Temp\new_mile.dbf";


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