/* APPLY_FUTURE_RAIL_ACTIONS.SAS
    Craig Heither & Nick Ferguson, last rev. 08-6-2013

-------------                                                             -------------
   PROGRAM APPLIES FUTURE RAIL CODING CHANGES TO ITINERARIES.  CALLED BY
   GENERATE_RAIL_FILES.SAS.
-------------                                                             -------------

   NRF 8/29/2017: Revised station consolidation processing to skip future itineraries that already have new station coded.
__________________________________________________________________________________________________________________________  */

filename inrte "&inpath.\rte_out.txt";

%macro changes;

    * APPLY ACTION CODE 5 (SHIFT TO DIFFERENT CBD STATION);
    %if &a5>0 %then %do;

        data __null__;
            file "&reportpath" mod;
            put /"### CBD TERMINUS SHIFT &tod ###";

        data rte5; set ftrrte(where=(action=5));
            proc sort; by tr_line;

        data __null__; set rte5;
            ln = substr(tr_line,1,3);
            file "&reportpath" mod;
            put "--> " descr ": shifted " ln "CBD terminus";

        data limit(keep=tr_line); set rte5;

        data itn5(keep=itin_a itin_b ln new nd); merge ftritin limit(in=hit); by tr_line;
            if hit;
            length ln $3.;
            ln=substr(tr_line,1,3);
            new=layover;
            nd=it_order;
            proc sort; by ln itin_a itin_b;

        data itins; set itins;
            length ln $3.;
            ln=substr(tr_line,1,3);
            proc sort; by ln itin_a itin_b;

        data itins(drop=ln new nd); merge itins(in=hit) itn5; by ln itin_a itin_b;
            if hit;
            if nd=1 then itin_a=new;
            else if nd=2 then itin_b=new;
            proc sort; by tr_line it_order;

        data zz5(keep=ln1 act1); set rte5;
            length ln1 $3.;
            ln1=substr(tr_line,1,3);
            rename action=act1;

        proc append base=rev data=zz5 force;  * Store for revised description;

        %end;

    * APPLY ACTION CODE 2 (TRAVEL TIME REDUCTION).;
    %if &a2>0 %then %do;

        data __null__;
            file "&reportpath" mod;
            put /"### TRAVEL TIME REDUCTIONS &tod ###";

        %let tot99=0;

        * Use geodatabase route coding to apply changes.;
        data ftnd(keep=node point_x point_y); set nodes;
            format point_x 14.6 point_y 14.5;
            point_x=round(point_x,.000001);
            point_y=round(point_y,.00001);
            proc sort; by point_x point_y;

        data rte2; infile inrte dlm=';' missover;
            format point_x 14.6 point_y 14.5;
            input link tr_line $ action point_x point_y;
            id=_n_;
            l=lag(link);

        data rte2; set rte2(where=(action=2));
            proc sort; by point_x point_y;

        data rte2(rename=(node=itin_b)); merge rte2(in=hit1) ftnd(in=hit2); by point_x point_y;
            if hit1 & hit2;
            length ln $3.;
            ln=substr(tr_line,1,3);
            proc sort; by tr_line id;

        data rte2(keep=tr_line itin_a itin_b ln); set rte2;
            itin_a=lag(itin_b);
            if link ne l then delete;

        data frte2(keep=tr_line action descr); set ftrrte(where=(action=2));
            proc sort; by tr_line;

        data itn2(keep=tr_line trv_time layover); merge ftritin frte2(in=hit); by tr_line;
            if hit;

        data a2rpt; merge ftritin frte2(in=hit); by tr_line;
            if hit;

        data __null__; set a2rpt(where=(layover ne '99'));
            ln=substr(tr_line,1,3);
            reduc=trv_time*100;
            file "&reportpath" mod;
            put "--> " descr ": reduced " ln "travel time from " itin_a "to " itin_b "by " reduc "percent";

        data a2rpt(keep=descr ln reduc); set a2rpt(where=(layover='99'));
            ln=substr(tr_line,1,3);
            reduc=trv_time*100;

        proc sort data=a2rpt nodupkey; by descr;

        data __null__; set a2rpt;
            file "&reportpath" mod;
            put "--> " descr ": reduced " ln "travel time along entire line by " reduc "percent";

        data allln(keep=ln ly); set itn2(where=(layover='99'));
            length ln $3.;
            ln=substr(tr_line,1,3);
            ly=layover;
            proc sort nodupkey; by ln;

        data _null_; set allln nobs=totobs;
            call symput('tot99',left(put(totobs,8.)));  * Number of lines with reduction for entire line.;

        data itn2(rename=(trv_time=reduc)); set itn2;
            drop layover;
            proc sort nodupkey; by tr_line;

        data rte2(drop=tr_line); merge rte2 itn2(in=hit); by tr_line;
            if hit;
            proc sort nodupkey; by ln itin_a itin_b;

        data itins; set itins;
            length ln $3.;
            ln=substr(tr_line,1,3);
            proc sort; by ln itin_a itin_b;

        data itins; merge itins(in=hit) rte2; by ln itin_a itin_b;
            if hit;
            if reduc>0 then do;
                if trv_time<0.6 then trv_time=round((1-reduc)*trv_time,0.01);
                else trv_time=round((1-reduc)*trv_time,0.1);
                end;

        %if &tot99>0 %then %do;

            data itins(drop=ly); merge itins(in=hit) allln; by ln;
                if hit;
                if ly='99' & reduc=. then do;
                    if trv_time<0.6 then trv_time=round((1-0.1)*trv_time,0.01);
                    else trv_time=round((1-0.1)*trv_time,0.1);
                    end;

            %end;

        data itins; set itins(drop=ln reduc);
            proc sort; by tr_line it_order;

        data zz2(keep=ln1 act1); set frte2;
            length ln1 $3.;
            ln1=substr(tr_line,1,3);
            rename action=act1;

        proc append base=rev data=zz2 force;  * Store for revised description;

        %end;

    * APPLY ACTION CODE 3 (NEW STATION).;
    %if &a3>0 %then %do;
        
        data __null__;
            file "&reportpath" mod;
            put /"### NEW STATIONS &tod ###";

        data rte3; set ftrrte(where=(action=3));
            proc sort; by tr_line;

        data limit(keep=tr_line); set rte3;

        data itn3(keep=itin_a itin_b ln new new_rate); merge ftritin limit(in=hit); by tr_line;
            if hit;
            length ln $3.;
            ln=substr(tr_line,1,3);
            new=layover;
            c=count(dw_code,':');
			if c>0 then c=c+1;
            if c>0 then do;
                do i=1 to c by 2;
                    p1=scan(dw_code,i,':');
                    d1=scan(dw_code,i+1,':');
                    if find(p1,"&tod")>0 then new_rate=input(d1, 8.);
                    end;
               end;
            else if c=0 then new_rate=input(dw_code, 8.);
            proc sort; by ln itin_a itin_b;run;

        data __null__; merge ftritin rte3(in=hit); by tr_line;
            if hit;
            ln=substr(tr_line,1,3);
            new=layover;
            file "&reportpath" mod;
            put "--> " descr ": added new " ln "station at " new "between itin_a = " itin_a "and itin_b = " itin_b;

        data itins; set itins;
            length ln $3.;
            ln=substr(tr_line,1,3);
            proc sort; by ln itin_a itin_b;

        data itins; merge itins(in=hit) itn3; by ln itin_a itin_b;
            if hit;

        data fix itins; set itins;
            if new>0 then output fix;
            else output itins;

        proc summary nway data=fix;
            class ln itin_a itin_b new new_rate;
            output out=station_freq;
            run;

        data station_freq; set station_freq;
		    stop_freq=round(_freq_ * new_rate);
			stop_interval=round(_freq_/stop_freq);
			run;

        * Insert new station into itinerary.;
        data fix; merge fix(in=hit) station_freq(drop=_type_ _freq_); by ln itin_a itin_b new;
            id=it_order;
            output;
            id=it_order+0.1;
            output;run;

        data fix; set fix;
		    group=ln||itin_a||itin_b||new;
			run;

        data fix; set fix;
            if id=int(id) then do;
                itin_b=new;
                layover='0';
                l=0;
                zn_fare=0;
                end;
            else do;
                itin_a=new;
                end;
            trv_time=round(trv_time/2+0.5,0.1);  * Add 0.5 minutes on each side of new station;
			proc sort; by group dep_time; run;

        data fix; set fix;
		    lag_group=lag(group);
			run;

        data fix; set fix;
            retain f 0;
			retain i 1;
			if group ne lag_group then do;
                f=0;
				i=1;
				end;
			if itin_b=new & stop_freq>0 & f<stop_freq & i=stop_interval then do;
			    dw_code=0;
				dw_time=0.01;
				f+1;
				i=1;
				end;
			else if itin_b=new & stop_freq>0 & (f>=stop_freq | i ne stop_interval) then do;
			    dw_code=1;
				dw_time=0.00;
				i+1;
				end;run;

        data itins; set itins fix;
            proc sort; by tr_line it_order id;

        data itins(drop=it_order new id ln new_rate stop_freq stop_interval lag_group f i); set itins;
            group=lag(tr_line);run;

        data itins; set itins;
            retain it_order 1;
            it_order+1;
            if tr_line ne group then it_order=1;
            output;

        data itins(drop=group); set itins;

        data zz3(keep=ln1 act1); set rte3;
            length ln1 $3.;
            ln1=substr(tr_line,1,3);
            rename action=act1;

        proc append base=rev data=zz3 force;  * Store for revised description;

        %end;

    * APPLY ACTION CODE 7 (NEW CONSOLIDATED STATION);
    %if &a7>0 %then %do;

        data __null__;
            file "&reportpath" mod;
            put /"### NEW CONSOLIDATED STATIONS &tod ###";

        data rte7; set ftrrte(where=(action=7));
            proc sort; by tr_line;

        data limit(keep=tr_line); set rte7;

        data itn7(keep=itin_a ln start end new); merge ftritin limit(in=hit); by tr_line;
            if hit;
            length ln $3. new 8.;
            ln=substr(tr_line,1,3);
            start=itin_a;
            end=itin_b;
            new=layover;

        data __null__; merge ftritin rte7(in=hit); by tr_line;
            if hit;
            ln=substr(tr_line,1,3);
            new=layover;
            file "&reportpath" mod;
            put "--> " descr ": consolidated " ln "stations between itin_a = " itin_a "and itin_b = " itin_b "into new station at " new;
            proc sort; by ln itin_a;

        proc sql;
            create table skip as
            select distinct tr_line, 1 as skip
            from itins left join itn7 on (itins.itin_a=itn7.new or itins.itin_b=itn7.new)
            where itn7.new > 0;
            quit;

        data itins; set itins;
            length ln $3.;
            ln=substr(tr_line,1,3);
            proc sort; by ln itin_a;

        data itins; merge itins(in=hit) itn7; by ln itin_a;
            if hit;
            proc sort; by tr_line it_order;

        data itins; merge itins(in=hit) skip; by tr_line;
            if hit;

        data itins (drop=skip); set itins;  * Remove matches where new station already in future itinerary;
            if skip=1 then do;
                start=.;
                end=.;
                new=.;
                end;

        data itins (drop=d); set itins;  * Remove false matches on 2-way routes;
            retain d;
            if it_order=1 then d=0;
            if start>0 and d=0 then d=1;
            else if start>0 and d=1 then do;
                start=.;
                end=.;
                new=.;
                end;

        data itins (drop=f n e t); set itins;
            retain f 0 n e t 0;
            if itin_a=start then do;
                f=1;
                n=new;
                e=end;
                end;
            flag=f;  * Flag affected links;
            if f=1 then t=trv_time+t;  * Sum travel time on affected links;
            if itin_b=e and f=1 then do;
                f=0;
                new=n;
                end=e;
                time=t;
                t=0;
                end;

        data itins (drop=start end new flag); set itins;  * Replace consolidating station itin with new station itin;
            if itin_a=start and flag=1 then itin_b=new;
            if flag=1 and not(new>0) then delete;
            if itin_b=end and flag=1 then itin_a=new;

        data time (keep=tr_line it_order t); set itins;
            tr_line=lag(tr_line);
            it_order=lag(it_order);
            t=time;

        data itins (drop=time t); merge itins(in=hit) time; by tr_line it_order;  * Adjust travel time for new itin;
            if hit;
            if t>0 then trv_time=round((t/2)-0.5,0.1);  * Since less 1 station subtract .5 mins from each side;
            if time>0 then trv_time=round((time/2)-0.5,0.1);

        data itins; set itins;
            group=lag(tr_line);

        data itins (drop=group o); set itins;  * Refresh itin order;
            retain o 1;
            o+1;
            if tr_line ne group then o=1;
            it_order=o;

        data zz7(keep=ln1 act1); set rte7;
            length ln1 $3.;
            ln1=substr(tr_line,1,3);
            rename action=act1;

        proc append base=rev data=zz7 force;  * Store for revised description;

        %end;

    * APPLY ACTION CODE 4 (LINE EXTENSION).;
    %if &a4>0 %then %do;

        data __null__;
            file "&reportpath" mod;
            put /"### LINE EXTENSIONS &tod ###";

        %let total=0;
        %let count=1;

        data rte4; set ftrrte(where=(action=4));
            id=_n_;

        data __null__; set rte4;
            ln=substr(tr_line,1,3);
            file "&reportpath" mod;
            put "--> " descr ": extended " ln;

        data _null_; set rte4 nobs=totobs;
            call symput('total',left(put(totobs,8.)));  * Store number of future lines;

       %do %while (&count le &total);  * Loop through future routes coded;

            data limit(keep=tr_line); set rte4(where=(id=&count));

            data itn4(drop=f_meas t_meas); merge ftritin limit(in=hit); by tr_line;
                if hit;
                length ln $3.;
                ln=substr(tr_line,1,3);
                if layover='' then layover='0';
                l=input(layover,best4.);
                proc sort; by ln it_order;

            data check4; set itn4(where=(it_order>-1 and it_order<1001));  * Check that it_order is valid;

            proc print;
                title 'BAD ITINERARY ORDER FOR ACTION=4';

            data itn4; set itn4;
                ord=lag(it_order);

            data itn4; set itn4;
                retain group 0;
                if (ord+1) ne it_order then group+1;
                output;
                proc sort; by ln group it_order;

            data part; set itn4; by ln group it_order;
                if (last.group & group=1) or (first.group & group=2) then output;

            data part; set part;
                if group=1 then node=itin_b;
                else if group=2 then node=itin_a;
                proc summary nway; class ln; var node; output out=junk min=node;

            data nwitn; set itins;
                length ln $3.;
                ln=substr(tr_line,1,3);

            data adj(drop=_type_ _freq_); merge nwitn(in=hit1) junk(in=hit2); by ln;
                if hit1 & hit2;
                proc sort; by tr_line it_order;

            data adj; set adj; by tr_line it_order;
                if first.tr_line & itin_a=node then beg=1;
                else beg=0;
                if last.tr_line & itin_b=node then end=1;
                else end=0;
                proc summary nway; class tr_line; id ln; var beg end; output out=cntl max=;

            data cntl(drop=_type_ _freq_); set cntl;
                num=_n_;

            %let cntl=0;
            %let cnter=1;

            data _null_; set cntl nobs=totobs;
                call symput('cntl',left(put(totobs,8.)));  * Store number of control lines;

            * Loop through Control Routes and add extension to beginning/end as appropriate.;
            %do %while (&cnter le &cntl);

                %let start=0;
                %let fin=0;
                %let rt=xxxxxx;
                %let ln3=xxx;

                data temp; set cntl(where=(num=&cnter));
                    call symput('rt',left(put(tr_line,$6.)));
                    call symput('start',left(put(beg,1.)));
                    call symput('fin',left(put(end,1.)));
                    call symput('ln3',left(put(ln,$3.)));

                data itn4a itn4b; set itins;
                    if tr_line="&rt" then output itn4a;
                    else output itn4b;

                %if &start=1 %then %do;  * Add extension to beginning of line;

                    data itn4a(drop=ln ord group); set itn4a itn4(where=(ln="&ln3" & it_order<0));
                        if count(tr_line,'*')>0 then tr_line="&rt";

                    %end;

                %if &fin=1 %then %do;  * Add extension to end of line;

                    data itn4a(drop=ln ord group); set itn4a itn4(where=(ln="&ln3" & it_order>1000));
                        if count(tr_line,'*')>0 then tr_line="&rt";
                        if l>0 & it_order<1000 then do;
                            l=0;
                            layover='0';
                            end;

                    %end;

                data itins; set itn4a itn4b;
                    proc sort; by tr_line it_order;

                %let cnter=%eval(&cnter+1);

                %end;

            %let count=%eval(&count+1);

            %end;

        data itins(drop=it_order); set itins;
            group=lag(tr_line);

        data itins(drop=group); set itins;
            retain it_order 1;
            it_order+1;
            if tr_line ne group then it_order=1;
            output;

        data zz4(keep=ln1 act1); set rte4;
            length ln1 $3.;
            ln1=substr(tr_line,1,3);
            rename action=act1;

        proc append base=rev data=zz4 force;  * Store for revised description;

        %end;

    * CREATE REVISED DESCRIPTION TO INDICATE ROUTE HAS CHANGED FROM BASE SCENARIO.;
    proc sort nodupkey data=rev; by ln1;

    data routes; set routes;
        length ln $3.;
        ln=substr(tr_line,1,3);

    proc sql noprint;
        create table sqltmp1 as
        select routes.*, rev.*
        from routes left join rev
        on routes.ln=rev.ln1
        order by tr_line;

    data routes(drop=ln ln1 act1 i a b c); set sqltmp1;
        length b $4.;
        if act1>0 & substr(tr_line,4,3)<900 then do;  * Apply description update but not to new runs.;
            i=index(descr,' -');
            a=substr(descr,1,i+1);
            b=compress("s"||&scen||"a"||act1);
            c=substr(descr,i+2,20-(i+5));
            descr=substr(a,1,i+1)||b||c;
            end;

    proc datasets; delete rev;

    %mend changes;

%changes
run;
