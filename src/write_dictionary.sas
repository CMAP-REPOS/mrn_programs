/* write_dictionary.sas
   Craig Heither, 09/28/2011

-------------                                                             -------------
   This SAS program creates a Python dictionary file of MHN (or MRN) links and their
   length, and is used to find the shortest path fix correct itinerary gaps.  
-------------                                                             -------------    */

data dict(keep=itinerary_a itinerary_b miles); set net1(where=(itinerary_a>&maxzn & itinerary_b>&maxzn));
  if base=1 then miles=int(mhnmi*100); 
  else miles=int(mhnmi*100)+500;                     *** add penalty of 5 miles to skeleton links to prohibit selection;
            
data dict; set dict; by itinerary_a;
 file out4;
  if first.itinerary_a then do;
    if last.itinerary_a then put itinerary_a +0 "${" +0 itinerary_b +0 ":" miles +0 "}";
    else put itinerary_a +0 "${" +0 itinerary_b +0 ":" miles @;
  end;
  else if last.itinerary_a then put +0 "," itinerary_b +0 ":" miles +0 "}";
  else put +0 "," itinerary_b +0 ":" miles @;

run;