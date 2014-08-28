/* UPDATE_NODES.SAS
    Craig Heither, revised 07/13/10

   Program updateS rail network nodes. 

   Program reads:   temp_arcstart.dbf to get updated anode coordinates.
                    temp_arcend.dbf to get updated bnode coordinates.
                    temp_node.dbf to get current railnode attribute information.

    Possible changes: 
      1. deleted nodes - arc deleted so node will not be in new database 
      2. moved nodes (existing) - new XY coordinates will be calculated automatically  
      3. new nodes due to added link - new XY coordinates will be calculated automatically, will need node number  
      4. new nodes due to split links - extra processing required to determine which node(s) are new because arc
                                        table will show duplicate entries of original link with anode & bnode values.
  */


%let tot=0;
%let delndtot=0;
%let dir=&sysparm;     ***shapefile storage directory;

   *** READ IN BEGINNING NODES ***;
proc import datafile="&dir.\Temp\temp_arcstart.dbf" out=a0 replace; 
data a(keep=anode bnode point_x point_y); set a0; 

   *** READ IN ENDING NODES ***;
proc import datafile="&dir.\Temp\temp_arcend.dbf" out=b0 replace;
data b(keep=anode bnode point_x point_y); set b0; 

   *** CHECK FOR SPLIT LINKS ***;
data temp1; set a b;
  proc summary nway; class anode bnode; output out=spl; 

data spl2(where=(_freq_>2)); set spl;                                          **frequency greater than 2 means link was split;
  data t; set spl2 nobs=totobs; call symput('tot',left(put(totobs,8.))); run;   **store number of split links in global variable;

%macro split;
 %if &tot>0 %then %do;  
     proc sort data=temp1; by anode bnode;
     data limit(drop=_type_ _freq_); merge temp1 spl2 (in=hit); by anode bnode; 
       if hit; 
        /*dist=sqrt((point_x**2)+(point_y**2));                                  **longest & shortest distances must be original end points;
           proc summary nway; var dist; class anode bnode; output out=mid min=mindist max=maxdist;
    
     data limit(keep=anode bnode point_x point_y split); merge limit mid; by anode bnode;
       if dist=mindist or dist=maxdist then delete;                            **leave only new points;
        split=1;*/

     proc import datafile="&dir.\Temp\temp_node.dbf" out=c replace;
     
        *** leave only new points ***;
     proc sql noprint;
         create table limit2 as
	 select *
	 from limit
	 where (point_x not in (
                 select point_x
                 from c))
               & (point_y not in (
                 select point_y
                 from c));
     data limit; set limit2;
         split=1;

     proc sort nodupkey; by anode bnode point_x point_y;

        *** zero out new node on split link ***;
     proc sort data=a; by anode bnode point_x point_y;
     data a; merge a limit; by anode bnode point_x point_y;
       if split=1 then anode=0;    
     proc sort data=b; by anode bnode point_x point_y;
     data b; merge b limit; by anode bnode point_x point_y;
       if split=1 then bnode=0;  

  
      *** write out file of split links to update miles field in arc table ***;
     data limit; set limit; proc sort nodupkey; by anode bnode;
     data all0; set a0 b0; proc sort nodupkey; by anode bnode orig_fid;
     data all0(keep=anode bnode orig_fid miles shape_leng); merge all0 limit (in=hit); by anode bnode; if hit; 
         proc summary nway; class anode bnode; var shape_leng; output out=newleng sum=totlen;
     data all(keep=anode bnode orig_fid newmile); merge all0 newleng; by anode bnode;
       newmile=round(shape_leng/totlen*miles,.01);
        proc sort; by orig_fid;
        *** attach link coordinates ***;
     data ax(keep=orig_fid ax ay); set a0; rename point_x=ax point_y=ay; proc sort; by orig_fid;
     data bx(keep=orig_fid bx by); set b0; rename point_x=bx point_y=by; proc sort; by orig_fid;
     data all; merge all (in=hit) ax bx; by orig_fid; if hit; proc sort; by ax ay;
        *** create temporary node numbers for new nodes to maintain unique anode-bnode combos *** ;
        *** and attach to split links: ensures itinerary will be updated OK                   ***;
     data one; set a(where=(anode=0)); rename point_x=x point_y=y;
     data two; set b(where=(bnode=0)); rename point_x=x point_y=y;
     data onetwo(drop=anode bnode split); set one two; proc sort nodupkey; by x y;
     data onetwo; set onetwo; retain nd 90000; nd+1;
     data ot1(rename=(nd=tempa x=ax y=ay)); set onetwo;
     data ot2(rename=(nd=tempb x=bx y=by)); set onetwo; 
     data all; merge all (in=hit) ot1; by ax ay; if hit; proc sort; by bx by;
     data all(drop=ax ay bx by); merge all (in=hit) ot2; by bx by; if hit; 
       if tempa=. then tempa=anode; if tempb=. then tempb=bnode;
         proc sort; by orig_fid;

     proc export data=all outfile="&dir.\Temp\new_mile.dbf" dbms=dbf replace;   

 %end;
%mend split;
%split
 /* end macro*/

   *** COMBINE NODES AND CREATE TEMPLATE OF FINAL NODES ***;
data a(keep=node point_x point_y); set a; rename anode=node;
data b(keep=node point_x point_y); set b; rename bnode=node;
data all; set a b; 
  proc summary nway; var node; class point_x point_y; output out=keepnodes max=;
proc sort data=keepnodes; by node;

   *** READ IN CURRENT NODE DATA AND ATTACH ATTRIBUTE DATA TO NEW NODE DATASET ***;
proc import datafile="&dir.\Temp\temp_node.dbf" out=c replace;
data c(drop=point_x point_y); set c; proc sort; by node;
data keepnodes(drop=_type_ _freq_); merge keepnodes (in=hit) c; by node; if hit;
  if pspace=. then pspace=0; if pcost=. then pcost=0;


   *** RE-ORDER VARIABLES TO MATCH FEATURE CLASS ORDER ***;
data final; retain node label pspace pcost ftr_pspace ftr_pcost point_x point_y; set keepnodes;

proc export data=final outfile="&dir.\Temp\new_node.dbf" dbms=dbf replace;

    *** CHECK FOR DELETED NODES ***;
%macro delndchk;
    data delnd(keep=node label); merge c(in=hit1) final(in=hit2); by node;
        if (hit1 & not(hit2));
	data delndt; set delnd nobs=totobs; call symput('delndtot',left(put(totobs,8.)));run;
	%if &delndtot>0 %then %do;
        proc export data=delnd outfile="&dir.\Temp\deleted_node.dbf" dbms=dbf replace;
	%end;
%mend delndchk;
%delndchk

run;
