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

	%if %index(&origitin,all_runs) %then %do;
	    data fix1(drop=anode bnode tempa tempb o x _type_ _freq_ newmile totmile t);
		set fix1;
		by tr_line it_order;
		retain t;
                if first.it_order then do;
		    itin_b=tempb;
		    t_meas=round(f_meas+newmile,.01);
		    trv_time=round(trv_time*(newmile/totmile),.01);
		    layover='0';
		    arr_time=round(dep_time+(trv_time*60),1);
  		    t=arr_time;
		end;
            	else if last.it_order then do;
		    itin_a=tempa;
		    f_meas=round(f_meas+x,.01);
		    zn_fare=0;
		    trv_time=round(trv_time*(newmile/totmile),.01);
		    dep_time=t;
		end;
            	else do;
		    itin_a=tempa;
		    itin_b=tempb;
		    f_meas=round(f_meas+x,.01);
		    t_meas=round(f_meas+newmile,.01);
		    zn_fare=0;
		    trv_time=round(trv_time*(newmile/totmile),.01);
		    layover='0';
		    dep_time=t;
		    arr_time=round(dep_time+(trv_time*60),1);
		    t=arr_time;
		end; 
	%end;

	%else %if %index(&origitin,future) %then %do;
	    data fix1(drop=anode bnode tempa tempb o x _type_ _freq_ newmile totmile);
		set fix1;
		by tr_line it_order;
		if first.it_order then do;
		    itin_b=tempb;
		    t_meas=round(f_meas+newmile,.01);
		    trv_time=round(trv_time*(newmile/totmile),.01);
		    layover='';
		end;
                else if last.it_order then do;
		    itin_a=tempa;
		    f_meas=round(f_meas+x,.01);
		    zn_fare=0;
		    trv_time=round(trv_time*(newmile/totmile),.01);
		end;
                else do;
		    itin_a=tempa;
		    itin_b=tempb;
		    f_meas=round(f_meas+x,.01);
		    t_meas=round(f_meas+newmile,.01);
		    zn_fare=0;
		    trv_time=round(trv_time*(newmile/totmile),.01);
		    layover='';
		end; 
	%end;
	

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
       
	data goodout;
	    set good;
	proc sort;
	    by tr_line it_order;
	proc export data=goodout outfile="&dir.\Temp\new_segments.dbf" dbms=dbf replace;
       


  %end;

%mend split;
%split
  /* end macro */

* - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - *;

*add code to handle rebuilding future routes;
*put all coding here;

%macro create_future_rtes;

    %if (&code=3 & %index(&origitin,future)) %then %do;
        data rte_geo;
            infile "&dir.\Temp\rte_out.txt" missover dlm=";";
            input line_num tr_line $ x y m;
        
        proc import datafile="&dir.\Temp\temp_node.dbf" out=rail_nodes replace;
        data rail_nodes(keep=node point_x point_y); set rail_nodes;
        data rail_nodes(drop=point_x point_y); set rail_nodes;
            x=point_x;
	    y=point_y;

	proc sql noprint;
	    create table rte_nodes as
	    select rte_geo.line_num,rte_geo.tr_line,rte_geo.x,rte_geo.y,rte_geo.m,rail_nodes.node
	    from rte_geo,rail_nodes
	    where rte_geo.x=rail_nodes.x & rte_geo.y=rail_nodes.y;
	proc sort data=rte_nodes;
	    by line_num m;

	data rte_itin (where=(line_num=tline_num));
	    set rte_nodes;
            itin_a=lag(node);
	    itin_b=node;
	    tline_num=lag(line_num);

	%if %sysfunc(fexist(nwmi)) %then %do;
	    data new_itin (drop=anode bnode x);
	        set tmpnode;
	        itin_a=anode;
	        itin_b=bnode;

	    proc sort data=rte_itin;
	        by itin_a itin_b;
	    proc sort data=new_itin;
	        by itin_a itin_b;
	    data new_rte_itin;
	        merge rte_itin(in=hit) new_itin;
	        by itin_a itin_b;
	        if hit;
        %end;
        %else %do;
            data new_rte_itin;
                set rte_itin;
                o=.;
        %end;

	proc sort data=new_rte_itin;
	    by line_num m o;
	data new_rte_itin (keep=line_num tr_line it_order itin_a itin_b);
	    set new_rte_itin;
	    by line_num m o;
            retain it_order 1;
	    it_order+1;
	    if first.line_num then it_order=1;
            if tempa ne . then itin_a=tempa;
	    if tempb ne . then itin_b=tempb;

	proc sql noprint;
	    create table new_rte_geo as
	    select new_rte_itin.line_num,new_rte_itin.tr_line,new_rte_itin.itin_a,new_rte_itin.itin_b,new_rte_itin.it_order,arcs.x,arcs.y,arcs.miles,arcs.ord
	    from new_rte_itin,arcs
	    where new_rte_itin.itin_a=arcs.itin_a & new_rte_itin.itin_b=arcs.itin_b;

	proc sort data=new_rte_geo;
	    by tr_line it_order ord;
	data new_rte_geo;
	    set new_rte_geo;
	    by tr_line it_order ord;
	    vx=lag(x);
            vy=lag(y);
	    ito=lag(it_order);
	    if (vx=. and vy=.) or it_order ne ito then segdist=0;
            else segdist=sqrt((x-vx)**2+(y-vy)**2)/5280;

	proc summary nway;
            var segdist;
            class tr_line it_order;
            output out=segtot sum=linktot;

	data new_rte_geo(drop=_type_ _freq_ vx vy ito);
            merge new_rte_geo segtot;
            by tr_line it_order;

	proc sort;
            by tr_line it_order ord;
        data new_rte_geo;
	    set new_rte_geo;
	    by tr_line it_order ord;
            retain m 0;
	    if first.tr_line then m=0;
	    m=m+round(segdist/linktot*miles,.00001);
	    output;

	data new_rte_geo;
            set new_rte_geo;
            format x1 14.6 y1 14.5;
            r1=lag(tr_line);
            x1=lag(x);
            y1=lag(y);
            if tr_line=r1 & x=x1 & y=y1 then delete;

	data print;
	    set new_rte_geo;
	    file out1 dlm=';';
    	    put line_num x y m;
	
    %end;

%mend create_future_rtes;
%create_future_rtes
run;




