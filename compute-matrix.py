#!/usr/bin/python3
import sys
import numpy as np
from scipy import spatial

# Input: The input file should contain on each line
# a n+1 vector containing the coordinatesof a point in dimension n
# and a value between 0 and 1 coresponding to it's filtration by density.
#
# Output: The output are the bondary matrices between chain complex,
# where vector basis in dimension one are the points kept in order.
# In higher dimension, simplex are constructed in lexicographic order.
# For example, 3 points will give rise to the basis :
# (0), (1), (2), (0, 1), (0, 2), (0, 1, 2).
#
if len(sys.argv) < 2:
    print("%s points-and-density" % sys.argv[0])
    exit(42)

# Read file
file=open(sys.argv[1])
points = []
densities = []
#distances = []

for line in file:
    vector = [float(x) for x in line.split()]
    coordinates = vector[:-1]
    density = vector[-1]
    points += [coordinates]
    densities += [density]

points = np.array(points)
densities = np.array(densities)
nb_pts = len(points)
max_density = max(densities)

#Reverse densities. This code is not needeed, we use it so that we can take
# the sup-levelsets for density, because our imput file have
# outliers with low densities and interesting points at high densities.
for i in range(0, len(densities)):
    densities[i] = max_density - densities[i]

###
## Utilitary function that allow accessing informations
## about simplexes (mostly edges)
###

#Fast distance computation (euclidean)
def distance(i, j):
    return np.linalg.norm(points[i] - points[j])

#Return the index, in our order, for the segment made of points
# i and j.
# Warning: It suppose i < j!
def seg_index(i, j):
    # This is computed in the first matrix pass...
    # Yes, it's an ugly hack. Should be fixed one day
    # by precalculating it at the begining of the program...
    return seg_index_map[(i, j)]
seg_index_map = {}
counter = 0
for i in range(nb_pts):
    for j in range(i + 1, nb_pts):
        seg_index_map[(i, j)] = counter


#Return the pair of time where the segment appear in the filtration.
def seg_time(i, j):
    #We compute the bifiltration index of the current simplex
    #stored in the tuple: (x, y)
    x = distance(i, j) # the two point should be close to each other: rips filtration
    y = max(densities[i], densities[j]) # the two points should be in the set
    return (x, y)

###
## The main algorithm that compute our matrices
###


#Now we compute bondary matrix \delta_1
print("Transposed matrix From C_1 to C_0:")

for i in range(nb_pts):
    for j in range(i + 1, nb_pts):
        col = np.array(np.zeros(nb_pts, dtype=np.int8), dtype='U20')
        (x, y) = seg_time(i, j)
        #Now we output the collumn of the matrix.
        #We simply compute the bondary opperator applied to this simplex.
        #Then, we output a polynomial coefficient in front of each
        #element of the cycle expression wich induce the right
        #grading degree of the expression ; the simplex connect in (x, y).
        #The output is x^distances * y^density = (distance, density)
        #In a rips filtration, all the points are present at the initial time
        col[i] = "-x^%f y^%f" % (x, y - densities[i])
        col[j] = "x^%f y^%f" % (x, y - densities[j])
        print(" ".join(col.tolist()))


#Then the bondary matrix \delta_2
print("Transposed matrix From C_2 to C_1:")

for i in range(nb_pts):
    for j in range(i + 1, nb_pts):
        for k in range(j + 1, nb_pts):
            col = np.array(np.zeros(nb_pts*(nb_pts - 1)/2, dtype=np.int8), dtype='U20')
            # the two point should be close to each other: rips filtration
            x = max(distance(i, j),
                    distance(i, k),
                    distance(j, k))
            # the two points should be in the set
            y = max(densities[i], densities[j], densities[k])
            #Remember seg_index(x, y) require x < y!
            (sx, sy) = seg_time(i, j)
            col[seg_index(i, j)] = "x^%f y^%f" % (x - sx, y - sy)
            (sx, sy) = seg_time(j, k)
            col[seg_index(j, k)] = "x^%f y^%f" % (x - sx, y - sy)
            (sx, sy) = seg_time(i, k)
            col[seg_index(i, k)] = "-x^%f y^%f" % (x - sx, y - sy)
            print(" ".join(col.tolist()))
