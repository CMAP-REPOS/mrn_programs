###############################################################################
# FIND_SHORTEST_PATH.PY                                                       #
#  Craig Heither, rev. 07-24-2012                                             #
#                                                                             #
#  This script finds the shortest path between two nodes, given the available #
#  network. The source of the shortest path function is:                      #
#      http://rebrained.com/?p=392 (accessed September 2011) - author unknown #
#                                                                             #
#  The function uses a brute force method to determine the shortest path: a   #
#  bit inelegant but effective.                                               #
#                                                                             #
#    Revisions:                                                               #
#      - 07-24-2012: updated for Python 3.2 (print now function, sys.maxint   #
#                    replaced with sys.maxsize)                               #
#                                                                             #
###############################################################################

# ---------------------------------------------------------------
# Import System Modules and Set Variables.
# ---------------------------------------------------------------
import sys, os, csv

input = os.path.join(sys.argv[3], "link_dictionary.txt")            ## input file with distance dictionary
short = os.path.join(sys.argv[3], "short_path.txt")                  ## shortest path output file
sys.setrecursionlimit(6000)                                     ## max. times function will call itself (default=1000)
##======================================================================##

# ---------------------------------------------------------------
#
# ---------------------------------------------------------------
graph={}
reader = csv.reader(open(input), delimiter='$')
for row in reader:
    graph[eval(row[0])]=eval(row[1])    ### assigns key (first object in row [0]) & value (2nd object in row [1]) pair
                                        ### eval function converts from string to integers


## function written by unknown author to find shortest path between 2 nodes in a graph; implementation of Dijkstra's algorithm
def shortestpath(graph,start,end,visited=[],distances={},predecessors={}):
    if not visited: distances[start]=0                         # set distance to 0 for first pass
    if start==end:                                             # we've found our end node, now find the path to it, and return
        path=[]
        while end != None:
            path.append(end)
            end=predecessors.get(end,None)
        return distances[start], path[::-1]
    for neighbor in graph[start]:                              # process neighbors as per algorithm, keep track of predecessors
        if neighbor not in visited:
            neighbordist = distances.get(neighbor,sys.maxsize)
            tentativedist = distances[start] + graph[start][neighbor]
            if tentativedist < neighbordist:
                distances[neighbor] = tentativedist
                predecessors[neighbor]=start
    visited.append(start)                                      # mark the current node as visited
    unvisiteds = dict((k, distances.get(k,sys.maxsize)) for k in graph if k not in visited)  # finds the closest unvisited node to the start
    closestnode = min(unvisiteds, key=unvisiteds.get)
    return shortestpath(graph,closestnode,end,visited,distances,predecessors)      # start processing the closest node

print(str(sys.argv[1]) + "," + str(sys.argv[2]))

outFile = open(short, 'a')
outFile.write(str(shortestpath(graph,eval(sys.argv[1]),eval(sys.argv[2]))))
outFile.write("\n")
outFile.close()
print('DONE')
