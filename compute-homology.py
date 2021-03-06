#!/usr/bin/python3

import sys
import numpy as np
from collections import OrderedDict
from sortedcontainers import SortedList
from sortedcontainers import SortedDict
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

#DEBUG: It's too slow so let's just keep the first 20 points for the begining :v
points = points[:100]

#NB: we cannot use float variables for computing persistence.
#    The reason is that additions add errors in the coefficients
#    because of the precision of float representation.
#    TODO: maybe we could actually still use float by being carefull
#          and relying on homogeneity.
FACTOR = 100000000

#Reverse densities. This code is not needeed, we use it so that we can take
# the sup-levelsets for density, because our imput file have
# outliers with low densities and interesting points at high densities.
# Then, convert to integer.
max_density = max(densities)
for i in range(0, len(densities)):
    densities[i] = int(FACTOR*(max_density - densities[i]))
    
points = np.array(points)
densities = np.array(densities)
nb_pts = len(points)
    
###
## Utilitary function that allow accessing informations
## about simplexes (mostly edges)
###

#Fast distance computation (euclidean) in integer
def distance(i, j):
    return int(FACTOR * np.linalg.norm(points[i] - points[j]))

#Return the pair of time where the segment appear in the filtration.
def seg_time(i, j):
    #We compute the bifiltration index of the current simplex
    #stored in the tuple: (x, y)
    x = distance(i, j) # the two point should be close to each other: rips filtration
    y = max(densities[i], densities[j]) # the two points should be in the set
    return (x, y)

#Return the index, in our order, for the segment made of points
# i and j.
# Warning: It suppose i < j!
def seg_index(i, j):
    # This map is precomputed right after the definition of this function
    return seg_index_map[(i, j)]
seg_index_map = {}
seg_index_to_time = {}
counter = 0
for i in range(nb_pts):
    for j in range(i + 1, nb_pts):
        seg_index_map[(i, j)] = counter
        seg_index_to_time[counter] = seg_time(i, j)
        counter += 1

###
## The main algorithm that compute our matrices
###

### As in "Computing multidimensional persistence",
### we compute over Z2, where -1 = 1, so we forget about the sign.
### We also use the position over term order.

#Now we compute bondary matrix \delta_1
#It is stored in a sparse format (list of non zero coefs)
print("Compute transposed matrix From C_1 to C_0...")

d1 = []
for i in range(nb_pts):
    for j in range(i + 1, nb_pts):
        col = SortedDict()
        (x, y) = seg_time(i, j)
        #We simply compute the bondary opperator applied to this simplex.
        #Then, we store a polynomial coefficient in front of each
        #element of the cycle expression wich induce the right
        #grading degree of the expression ; the simplex connect in (x, y).
        #The output is x^distances * y^density = (distance, density)
        #In a rips filtration, all the points are present at the initial time
        col[i] = (x, y - densities[i])
        col[j] = (x, y - densities[j])
        d1 += [col]

#print(d1)

#Then the bondary matrix \delta_2
print("Compute the transposed matrix From C_2 to C_1:")

d2 = []
for i in range(nb_pts):
    for j in range(i + 1, nb_pts):
        for k in range(j + 1, nb_pts):
            col = SortedDict()
            # the two point should be close to each other: rips filtration
            x = max(distance(i, j),
                    distance(i, k),
                    distance(j, k))
            # the two points should be in the set
            y = max(densities[i], densities[j], densities[k])
            #Remember seg_index(x, y) require x < y!
            (sx, sy) = seg_time(i, j)
            col[seg_index(i, j)] = (x - sx, y - sy)
            (sx, sy) = seg_time(j, k)
            col[seg_index(j, k)] = (x - sx, y - sy)
            (sx, sy) = seg_time(i, k)
            col[seg_index(i, k)] = (x - sx, y - sy)
            d2 += [col]
#print(d2)

########### Butchberger implementation
###
### We use a slightly modified version of butcher to compute
### division on polynomial vectors instead of just polynoms.
###

#add two tuple
def tuple_plus(a, b):
    return (a[0] + b[0], a[1] + b[1])

#substract b to a
def tuple_minus(a, b):
    return (a[0] - b[0], a[1] - b[1])

# A vector has type SortedDict{line index : (x power, y power)}
def LM(vec):
    return vec.items()[0]

# In Z2, LT = ML :)
def LT(vec):
    return LM(vec)

#Return true if u divides v (partial order on N^2)
def divides(v, u):
    if (u[0] != v[0]):
        return False
    return v[1][0] <= u[1][0] and v[1][1] <= u[1][1]

def LCM_poly(p, q):
    #print("LCM_poly p: ", p, " q: ", q)
    return (max(p[0], q[0]), max(p[1], q[1]))

# A vector has type SortedDict{line index : (x power, y power)}
# Return the pair (line index, (x power,y power)) or (0, 0)
def LCM(vec1, vec2):
    l1 = LM(vec1)
    l2 = LM(vec2)
    #print("LM Vec1:",l1)
    #print("LM Vec2:",l2)
    if l1[0] != l2[0]:
        return (0, 0)
    else:
        return (l1[0], LCM_poly(l1[1], l2[1]))
#Debug: should return (8, 10)
#print(LCM(SortedDict({0:(8, 8), 1:(10, 10), 2:(5, 5)}),
#          SortedDict({0:(0, 10), 1:(1, 10), 2:(2, 10)}))[1])

# Divides the polynomial vector vec by
# the list of polynomial vectors veclist.
# Warning: We suppose all vector are homogeneous!!!
def DIVIDE(vec, f):
    p = vec
    r = SortedDict()
    #print("DIVIDE p:", p)
    q = {} #We use a dictionary for easy and fast acess to qi
    #while p != 0
    while len(p) != 0:
        we_did_something = False
        #for each fi
        for i in range(0, len(f)): 
            #DEBUG:print("f[", i, "]:", f[i])
            lt_fi = LT(f[i])
            lt_p = LT(p)
            (lt_p_key,  lt_p_value)  = lt_p
            (lt_fi_key, lt_fi_value) = lt_fi
            if divides(lt_fi, lt_p):
                #DEBUG:print("lt_fi", lt_fi, " divides ",lt_p)
                #ltp_over_ltfi = LT(p)/LT(fi)
                ltp_ltfi_value = tuple_minus(lt_p_value, lt_fi_value)
                ltp_ltfi = (lt_p_key, ltp_ltfi_value)
                #qi = qi + LT(p)/LT(fi)
                if i in q.keys():
                    q[i] += [ltp_ltfi]
                else:
                    q[i] = [ltp_ltfi]
                #p = p - (LT(p)/LT(fi))fi
                for term_idx, term_val in f[i].items():
                    product = tuple_plus(ltp_ltfi_value, f[i][term_idx])
                    if term_idx in p.keys():
                        #print("del",p[term_idx], "==", product, "key:", term_idx)
                        assert(p[term_idx] == product)
                        del p[term_idx]
                    else:
                        #print("write", product, "key:", term_idx)
                        p[term_idx] = product
                we_did_something = True
                #If p get set to 0
                if not p:
                    break
        if we_did_something == False:
            #r = r + LT(p)
            if lt_p_key in r.keys():
                assert(r[lt_p_key] == lt_p_value)
                del r[lt_p_key]
            else:
                r[lt_p_key] = lt_p_value
            #p = p - LT(p)
            del p[lt_p_key]
    return (q, r)

#Compute the S polynomial vectors f and g
#Warning:We suppose f and g homogeneous.
#The result is homogeneous of degree l where x^l = LCM(LM(f), LM(g))
# The simplex type is the type of simplex considered in the computation.
# The simplex_type variable contain the dimension of simplices aligned
# with lines.
def S(f, g, simplex_type=0):
    def get_uei(i):
        if simplex_type == 0:
            return (0, densities[i])
        elif simplex_type == 1:
            return seg_index_to_time[i]
        else:
            raise ValueError("Unhandled simplex type for S polynomials computation!")
    s = SortedDict()
    j, lcm = LCM(f, g)
    #Case LCM = 0
    if lcm == 0:
        return s
    uej = get_uei(j)
    l = tuple_plus(lcm, uej)
    #On Z2, cf and cg (the leading coefficients) are equal to = 1
    #Thus di = ci/cf - c'i/cg = ci - c'i
    # where S(f, g) = Sum di x^l/x^uei ei
    # and ci are coefficients of f, c'i coefficients of g.
    # So we need tto keep x^l / x^uei on each cell that is only
    # non zero in f or g
    for i in f:
        #print("f[", i, "]:", f[i])
        uei = get_uei(i)
        if i in s:
            #print("del i:", i, " value:", tuple_minus(l, uei))
            assert(s[i] == tuple_minus(l, uei))
            del s[i]
        else:
            #print("add i:", i, " value:", tuple_minus(l, uei))
            s[i] = tuple_minus(l, uei)
    for i in g:
        uei = get_uei(i)
        #print("g[", i, "]:", g[i])
        if i in s:
            #print("del i:", i, " value:", tuple_minus(l, uei))
            assert(s[i] == tuple_minus(l, uei))
            del s[i]
        else:
            #print("add i:", i, " value:", tuple_minus(l, uei))
            s[i] = tuple_minus(l, uei)
    return s

def BUTCHBERGER(F, simplex_type=0):
    #Make sure we work with set!
    #todo F = set(F)
    we_did_something = True
    while we_did_something:
        we_did_something = False
        size_f = len(F)
        #foreach pair f != g \in F
        for i in range(0, size_f):
            for j in range(i + 1, size_f):
                f=F[i]
                g=F[j]
                if (not f) or (not g):
                    print("Null vector found in BUTCHERGER set!!!")
                    assert(False)
                s = S(f, g, simplex_type)                
                #print("S(f,g):", S(f, g), f, g)
                if not s:
                    #print("S(f,g) == 0")
                    continue
                #print("LT(s):", LT(s))
                (_, r) = DIVIDE(s, F)
                if not(not r):
                    print("Grobner basis (new vector added):", r)
                    F = [r] + F
                    we_did_something = True
        print("While Loop!")
    return F

def reduce_basis(F):
    G = []
    l = len(F)
    for i in range(0, l):
        H = G + F[i + 1:]
        (_, r) = DIVIDE(F[i], H)
        if not (not r):
            G = [r] + G
    return G

print("Compute grobner basis...")
grobner_d1 = BUTCHBERGER(d1, 0);
print("Reduce grobner basis...")
grobner_d1 = reduce_basis(grobner_d1)

print("Reduced grobner basis for Im d_1:")
for vec in grobner_d1:
    print('{', end='')
    for key, val in vec.items():
        print(key, ":", val, end=' ')
    print('}')

print("Length:", len(grobner_d1))

print("GAP: HomalgMatrix(\n\"[")
for vec in grobner_d1:
    virg = False;
    for i in range(0, len(points)):
        if (virg):
            print(', ', end='')
        if i in vec.keys():
            print('x^%d * y^%d' % val, end='')
        else:
            print("0", end='')
        virg = True
print("]\",", len(grobner_d1), ",", len(points), ")")

