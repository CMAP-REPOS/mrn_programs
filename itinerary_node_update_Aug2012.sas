/*
NRF 5/30/2017 - corrected future it_order overwrite issue using action codes to inform future it_order after split link.
NRF 6/2/2017 - corrected error in rebuilding future route geo. was not using node ID of 0 to find coordinates for new node.
NRF 6/23/2017 - corrected error in rebuiding future route geo. new node coordinates were being used to apply node ids to
                route geo based on original node coordinates when node is moved.
*/
*================================================================*;
   *** UPDATE ITINERARY TO REFLECT SPLIT LINKS W/ TEMPORARY ANODE-BNODE VALUES (ONLY IF NEW_MILE.DBF EXISTS) ***;
*================================================================*;


filename nwmi "&dir.\Temp\new_mile.dbf";
filename delndf "&dir.\Temp\deleted_node.dbf";

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
       %if %index(&origitin,future) %then %do;    *rewrite future it_order according to action codes;
	       proc import datafile="&origfrts" dbms=dbf out=frts replace;
           proc sort;
               by tr_line;
               run;
	       data actcodes(keep=tr_line action);
               set frts;
               run;
	       data good;
               merge good(in=hit) actcodes;
               by tr_line;
               if hit;
               run;
	       data act1 act2 act3;
               set good;
               if action in (1,5) then output act1;
		       else if action=4 then output act2;
		       else output act3;
               run;
	       data act1;
               set act1;
               group=lag(tr_line);
               run;
           data act1(drop=group);
               set act1;
               retain it_order 1;
               it_order+1;
               if tr_line ne group then it_order=1;
               output;
               run;
	       proc sql;
	           create table y3 as
		       select tr_line, count(tr_line) as itincnt
		       from act2
		       group by tr_line;
		       quit;
	       data act2;
               merge act2(in=hit) y3;
               by tr_line;
               if hit;
               run;
	       data act2(drop=itincnt n  i);
               set act2;
               by tr_line f_meas;
	           retain n i;
	           if first.tr_line then do;
                   n=itincnt;
			       i=itincnt+(itincnt/2);
			       end;
		       if i>n then do;
                   it_order=n-i;
			       i=i-1;
			       end;
		       if i<n then do;
		           it_order=(n-i)+1000;
			       i=i-1;
			       end;
			   if i=n then i=i-1;
		       run;
		   data act3;
		       set act3;
			   it_order=0;
			   run;
		   data good(drop=action);
		       set act1 act2 act3;
			   run;
		   proc sort;
		       by itin_a itin_b;
			   run;
		   %end;
	   %else %do;
	       data good;
               set good;
               group=lag(tr_line);
			   run;
           data good(drop=group);
               set good;
               retain it_order 1;
               it_order+1;
               if tr_line ne group then it_order=1;
               output;
			   run;
           proc sort;
               by itin_a itin_b;
			   run;
		   %end;

	data goodout;
	    set good;
	proc sort;
	    by tr_line it_order;
	proc export data=goodout outfile="&dir.\Temp\new_segments.dbf" dbms=dbf replace;



  %end;

%mend split;
%split
  /* end macro */

%macro delete_node;
    %if %sysfunc(fexist(delndf)) %then %do;

	    * --> read in deleted node file *;
        proc import datafile="&dir.\Temp\deleted_node.dbf" dbms=dbf out=delnd replace;

	    * --> separate routes that need updating from those that do not *;
	    proc sql noprint; create table x1 as
	        select tr_line
	        from good,delnd
	        where itin_a=node or itin_b=node;
	    proc freq; tables tr_line / noprint out=match;
	    proc sort data=good; by tr_line it_order;
	    data good; merge good match; by tr_line;
	    data fix(drop=count percent) ok(drop=count percent); set good;
	        if count>0 then output fix;
			else output ok;

		* --> check that general future itinerary coding has already been updated manually *;
		data check; set fix(where=(indexc(tr_line,"*")>0));
        proc print; title "DELETED NODES SHOULD BE MANUALLY CODED IN GENERAL FUTURE ITINERARY CODING BEFORE RUNNING TOOL";

		* --> update itineraries *;
		proc sql noprint; create table fix1 as
		    select *
			from fix left join delnd on (itin_a=node or itin_b=node);
		proc sort; by tr_line it_order;

		%if %index(&origitin,all_runs) %then %do;
	        data fix1(drop=node label f a z t d); set fix1; by tr_line it_order;
		        retain f a z t d;
                if (first.tr_line & itin_a=node) then delete;
				else if (last.tr_line & itin_b=node) then delete;
            	else if itin_b=node then do;
		            f=f_meas;
					a=itin_a;
					z=zn_fare;
					t=trv_time;
					d=dep_time;
					delete;
				end;
				else if itin_a=node then do;
				    f_meas=f;
					itin_a=a;
					zn_fare=zn_fare+z;
					trv_time=trv_time+t;
					dep_time=d;
				end;

			data fix1(drop=m t o); set fix1; by tr_line it_order;
			    retain m t o;
                if first.tr_line then do;
				    m=t_meas-f_meas;
					f_meas=0;
					t_meas=m;
					t=t_meas;
					o=1;
					it_order=o;
				end;
				else do;
				    m=t_meas-f_meas;
					f_meas=t;
					t_meas=f_meas+m;
					t=t_meas;
					o=o+1;
					it_order=o;
					if last.tr_line then do;
					    layover='3';
						dw_code=0;
					end;
				end;
	    %end;

		%else %if %index(&origitin,future) %then %do;
	        data fix1(drop=node label f a z t); set fix1; by tr_line it_order;
		        retain f a z t;
                if ((first.tr_line & itin_a=node)||(last.tr_line & itin_b=node)) then delete;
            	else if itin_b=node then do;
		            f=f_meas;
					a=itin_a;
					z=zn_fare;
					t=trv_time;
					delete;
				end;
				else if itin_a=node then do;
				    f_meas=f;
					itin_a=a;
					zn_fare=zn_fare+z;
					trv_time=trv_time+t;
				end;

			data fix1(drop=m t o); set fix1; by tr_line it_order;
			    retain m t o;
                if first.tr_line then do;
				    m=t_meas-f_meas;
					f_meas=0;
					t_meas=m;
					t=t_meas;
					o=1;
					it_order=o;
				end;
				else do;
				    m=t_meas-f_meas;
					f_meas=t;
					t_meas=f_meas+m;
					t=t_meas;
					o=o+1;
					it_order=o;
					if last.tr_line then do;
					    layover='3';
						dw_code=0;
						dw_time=0.01;
					end;
				end;
		%end;

		* --> put all itinerary coding back together *;
		data good; set ok fix1;
		proc sort; by itin_a itin_b;
		data goodout; set good;
		proc sort; by tr_line it_order;
		proc export data=goodout outfile="&dir.\Temp\new_segments.dbf" dbms=dbf replace;
	%end;
%mend delete_node;
%delete_node

* - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - *;

*add code to handle rebuilding future routes;
*put all coding here;

%macro create_future_rtes;
    %if (&code=3 & %index(&origitin,future)) %then %do;
        data rte_geo;
            infile "&dir.\Temp\rte_out.txt" missover dlm=";";
            input line_num tr_line $ x y m;

        proc import datafile="&dir.\Temp\new_node.dbf" out=rail_nodes replace;
        data rail_nodes(keep=node point_x point_y point_x0 point_y0);
            set rail_nodes;
        data rail_nodes(drop=point_x point_y point_x0 point_y0);
            set rail_nodes;
            x=point_x;
	          y=point_y;
            x0=point_x0;
            y0=point_y0;
            run;

	      proc sql noprint;
	          create table rte_nodes as
	          select rte_geo.line_num,rte_geo.tr_line,rail_nodes.x,rail_nodes.y,rte_geo.m,rail_nodes.node
	          from rte_geo,rail_nodes
	          where rte_geo.x=rail_nodes.x0 & rte_geo.y=rail_nodes.y0;
	      proc sort data=rte_nodes;
	          by line_num m;

	      data rte_itin (where=(line_num=tline_num));
	          set rte_nodes;
            itin_a=lag(node);
	          itin_b=node;
	          tline_num=lag(line_num);
            run;

	      %if %sysfunc(fexist(nwmi)) %then %do;
            data new_itin (drop=anode bnode x);
                set tmpnode;
                itin_a=anode;
                itin_b=bnode;
                run;

            proc sort data=rte_itin;
                by itin_a itin_b;
            proc sort data=new_itin;
                by itin_a itin_b;
            data new_rte_itin;
                merge rte_itin(in=hit) new_itin;
                by itin_a itin_b;
                if hit;
                run;
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
