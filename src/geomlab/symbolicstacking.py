import numpy as np
import math
import random
import copy

color1PIL = "rgb(254, 201, 201)"  # blau
color2PIL = "rgb(249, 102, 94)"  # rot
color3PIL = "rgb(100, 100, 100)"  # grau
color4PIL = "rgb(200, 239, 245)"  # grün

color1 = [254, 201, 201]  # blau
color2 = [249, 102, 94]  # rot
color3 = [100, 100, 100]  # grau
color4 = [200, 239, 245]  # grün


def calculatePointOnCircle(c, angle):
    cosangle = np.cos(angle)
    sinangle = np.sin(angle)
    return cosangle * c[2] + c[0], sinangle * c[2] + c[1]


#############################################################################
###############caculating of the occluded circumference of a Circle##########
###################given the circles which lie above it######################
#############################################################################

# calculates Intersection of to circles (if they exist!!) p,q=(x,y,r)
def calcIntersectionPoints(p, q):
    int1 = np.array([0.0, 0.0])
    int2 = np.array([0.0, 0.0])
    d = np.sqrt((p[0] - q[0]) * (p[0] - q[0]) + (p[1] - q[1]) * (p[1] - q[1]))

    ex = (q[0] - p[0]) / d
    ey = (q[1] - p[1]) / d
    x = (p[2] * p[2] - q[2] * q[2] + d * d) / (2 * d)
    y = np.sqrt(p[2] * p[2] - x * x)

    int1[0] = p[0] + x * ex - y * ey
    int1[1] = p[1] + x * ey + y * ex

    int2[0] = p[0] + x * ex + y * ey
    int2[1] = p[1] + x * ey - y * ex

    return int1, int2


# calculates Intersection of to circles and returns relative state (one inside the other
# or intersecting or far apart
def calculateCircleIntersection(p, q):
    d = np.sqrt((p[0] - q[0]) * (p[0] - q[0]) + (p[1] - q[1]) * (p[1] - q[1]))

    if d > (p[2] + q[2]):
        return None, None, 3
    if d + q[2] < p[2]:
        return None, None, 2
    if d == 0:
        return None, None, 4
    if d + p[2] < q[2]:
        return None, None, 1
    x, y = calcIntersectionPoints(p, q)
    return x, y, 0


# calculates the relative angle of to points on a circle
def calculateRelativeAngle(p, q):
    x = q[0] - p[0]
    y = q[1] - p[1]
    angle = np.arctan2(y, x)
    if angle < 0:
        return 2 * np.pi + angle
    return angle


# given to points on a circle calculate the intervall which lies between them
def calculateSingleCoverInterval(p, q):
    p1, p2, check = calculateCircleIntersection(p, q)
    if check == 0:
        a1 = calculateRelativeAngle(p, p1)
        a2 = calculateRelativeAngle(p, p2)
        aMiddle = calculateRelativeAngle(p, q)
        if (a1 < aMiddle and aMiddle < a2) or (aMiddle < a2 and a2 < a1):
            return a1, a2
        else:
            return a2, a1, True
    if check == 1:
        return 0, 2 * np.pi, True

    if check == 4:
        return 0, 2 * np.pi, True
    if check == 2 or check == 3:
        return None, None, False


# test if a circle is completly covered by the intervals I
def testCompletlyCovered(I):
    a0 = 2 * np.pi + I[0][0]
    x = I[0][1]
    i = 0
    while x < a0:
        if I[i][1] < I[i][0]:
            I[i][1] = I[i][1] + 2 * np.pi
        if I[i][0] < x:
            x = np.max([x, I[i][1]])
        else:
            return False
        i = i + 1
        if i == len(I):
            if x >= a0:
                return True
            else:
                return False
    return True


# if the interval is not completely covered there exist a point relative to which
# all intervalls lie in [0,2pi]
def findStartingPoint(I):
    c = 0
    minimum = float('inf')
    minindex = 0
    for i in range(0, len(I)):
        if I[i][1] == 0:
            c = c + 1
        else:
            c = c - 1
            if c == minimum:
                minindex = i
            else:
                if c < minimum:
                    minimum = c
                    minindex = i
    if minimum == 0:
        return 0

    if minindex == len(I) - 1:
        return 0
    else:
        return minindex + 1


# calculates the maximal non intersecting intervals covered by the Interval
# given the shift that all intervals lie in [0,2pi]
def calculateMaxIntervalsWithShift(I, shift):
    n = len(I)
    c = 0
    resultArray = []
    for i in range(0, n):
        ind = (shift + i) % n
        if c == 0:
            resultArray.append(I[ind][0])
            c = c + 1
        else:
            if I[ind][1] == 0:
                c = c + 1
            else:
                c = c - 1
                if c == 0:
                    resultArray.append(I[ind][0])

    return resultArray


# given disjoint intervals on a circle calculates the covered Circumference
def calcCirc(Arr):
    result = 0
    for i in range(0, int(len(Arr) / 2)):
        x = Arr[2 * i + 1] - Arr[2 * i]
        if x < 0:
            x = x + 2 * np.pi
        result = result + x

    return result


# given a circle and all circles N which lie above it calculates the covered circumference
def calculateCoveredCircumference(c, N):
    CoverIntervals1D = []
    CoverIntervals2D = []
    for n in N:
        #generate all covering intervalls (may not be disjoint)
        a, b, bo = calculateSingleCoverInterval(c, n)
        if bo is True:
            CoverIntervals2D.append([a, b])
            CoverIntervals1D.append([a, 0])
            CoverIntervals1D.append([b, 1])
    CoverIntervals1D.sort()
    CoverIntervals2D.sort()

    if len(CoverIntervals1D) == 0:
        return 0
    if not testCompletlyCovered(CoverIntervals2D):
        #calculate the disjoint intervalls if not fully covered
        shift = findStartingPoint(CoverIntervals1D)
        CoverArray = calculateMaxIntervalsWithShift(CoverIntervals1D, shift)
        return calcCirc(CoverArray)
    else:
        return 2 * np.pi


#############################################################################
################Different utilitys and costs for circles####################
#############################################################################


def calculateAbsoluteBoundaryUtility(circle, Neighbours):
    x = 2 * np.pi - calculateCoveredCircumference(circle, Neighbours)
    return x * circle[2]


def calculateRelativeBoundaryUtility(circle, Neighbours):
    x = 2 * np.pi - calculateCoveredCircumference(circle, Neighbours)
    return x


#############################################################################
################Pie Charts####################
#############################################################################


# given a circle and some angles for the deviding lines of the pies and the
# circles that lie above the circle calculates all disjoint Intervals in which
# the first deviding line can be positioned
def caculateFeasibleIntervall(c, piePiecesC, N):
    #calculate the cover intervals of the boundary
    CoverIntervals1D = []
    CoverIntervals2D = []
    for n in N:
        a, b, bo = calculateSingleCoverInterval(c, n)
        if bo is True:
            CoverIntervals2D.append([a, b])
            CoverIntervals1D.append([a, 0])
            CoverIntervals1D.append([b, 1])
    CoverIntervals1D.sort()
    CoverIntervals2D.sort()

    if len(CoverIntervals1D) == 0:
        return [[0, 2 * np.pi]]

    if not testCompletlyCovered(CoverIntervals2D):
        #if not completely covered we generate all the of the intervals discussed in the lab notes (Lemma1)
        shift = findStartingPoint(CoverIntervals1D)
        CoverArray = calculateMaxIntervalsWithShift(CoverIntervals1D, shift)

        coverArray2D = []
        for i in range(0, int((len(CoverArray) / 2))):
            coverArray2D.append([CoverArray[2 * i], CoverArray[2 * i + 1]])

        distances = []

        for j in range(0, len(piePiecesC)):
            distances.append(piePiecesC[j])
        for d in distances:
            for intervall in coverArray2D:
                a = intervall[0] - d  # -0.1
                if a < 0:
                    a = a + 2 * np.pi
                b = intervall[1] - d  # +0.1
                if b < 0:
                    b = b + 2 * np.pi
                CoverIntervals2D.append([a, b])
                CoverIntervals1D.append([a, 0])
                CoverIntervals1D.append([b, 1])
        CoverIntervals1D.sort()
        CoverIntervals2D.sort()

        #calculate the visible intervals from the covered ones
        if not testCompletlyCovered(CoverIntervals2D):
            shift = findStartingPoint(CoverIntervals1D)
            CoverArray = calculateMaxIntervalsWithShift(CoverIntervals1D, shift)

            result = []
            result.append([CoverArray[len(CoverArray) - 1], CoverArray[0]])
            for i in range(0, int((len(CoverArray) / 2) - 1)):
                result.append([CoverArray[2 * i + 1], CoverArray[2 * i + 2]])

            return result
        else:
            return None

    else:
        return None


# calculates the angle of the first deviding line given the feasible intervals
# output (angle, length of visibility thingy)
def calculateAngle(intervals):
    val = -1
    result = 0
    if intervals is None:
        return None, None
    for i in intervals:
        a = i[0]
        b = i[1]
        if a > b:
            b = b + 2 * np.pi
        length = np.absolute(b - a)
        if length > val:
            val = length
            result = a + length / 2
    return result, val


# given a circle and dividinglines and the circles that lie above it
# calculates the postion and value of the deviding line
def caculateOneAnglePie(c, piePiecesC, N):
    tmp = caculateFeasibleIntervall(c, piePiecesC, N)
    if tmp is None:
        return None, None
    else:
        angle, value = calculateAngle(tmp)
        if angle is None:
            return None, None
        else:
            return angle, value


# calculates for an arrangement of Pies the pie which should be the lowest one
# in the stacking returns the index of the circle in the list and the angle
# of the first devidingline
def calculateLowestPie(circles, piePieces):
    locPiePieces = copy.deepcopy(piePieces)

    hasFound = False
    resultIndex = 0
    resultMax = -1
    resultAngle = 0
    while hasFound is False:
        
        #find the max value 
        for i in range(0, len(circles)):
            tmpC = circles[i]
            tmpPieces = locPiePieces[i]
            tmpN = circles[:i] + circles[i + 1:]
            angle, value = caculateOneAnglePie(tmpC, tmpPieces, tmpN)
            if not angle == None:
                hasFound = True
                if value * tmpC[2] > resultMax:
                    resultAngle = angle
                    resultMax = value * tmpC[2]
                    resultIndex = i

        if hasFound is True:
            return resultIndex, resultAngle

        if len(locPiePieces[0]) == 0:
            break
        if len(locPiePieces) == 0:
            break
        #heuristic just ignores the last line
        for p in locPiePieces:
            p.pop(len(p) - 1)
    return 0, 0


#############################################################################
##########################Stacking algorithms################################
#############################################################################


# calculates best pie stacking
# input circles: [[x,y,r]...] piePieces [[p1,p2,...]...] 0 is always a deviding line 
# every circle has to have at least 1 more deviding line!
# output:
# resultOrder new Stackingorder
# resultPieces the pieces in the same order as the circles
# resultAngles for every pie the angle of the 0 devidingline
def algorithmPieChartsStacking(circles, piePieces):
    resultAngles = []
    resultOrder = []
    resultPieces = []
    localCircles = circles.copy()
    localPiePieces = piePieces.copy()
    while len(localCircles) > 0:
        ind, angle = calculateLowestPie(localCircles, localPiePieces)
        tmpCircle = localCircles.pop(ind)
        tmpPieces = localPiePieces.pop(ind)
        resultAngles.append(angle)
        resultOrder.append(tmpCircle)
        resultPieces.append(tmpPieces)

    return resultOrder, resultPieces, resultAngles


# calculates the value largest visible CONTINUOUS Interval
def calculateLargestContinousCirc(circle, neighbours):
    x = caculateVisibleIntervall(circle, neighbours)
    maximum = -1

    if x is None:
        return 0

    for i in x:
        if i[0] > i[1]:
            i[1] = i[1] + 2 * np.pi
        tmpvalue = i[1] - i[0]
        if maximum < tmpvalue:
            maximum = tmpvalue
    return maximum

#calculate maximum with respect to the largest visible CONTINUOUS Interval
def calculateLowestHawaiian(Circles):
    maximum = -1
    index = -1
    for i in range(0, len(Circles)):
        tmp = Circles[:i] + Circles[i + 1:]
        tmpValue = calculateLargestContinousCirc(Circles[i], tmp)
        if tmpValue * Circles[i][2] > maximum:
            index = i
            maximum = tmpValue * Circles[i][2]
    return index, maximum


# given some circles of the form (x,y,r1,r2,...) where r1>r2>...
# returns a algorithmHawaiianStacking
# form: for each circle with subcircles there are now multiple circles
# output has form [[x1,y1,r1],[x2,y2,r2],....,[x1',y1',r1'],[x2',y2'.r2']...]
def algorithmHawaiianStacking(circles):
    local = circles.copy()
    stacking = []
    stackingAllCircles = []
    
    #calculate stacking
    for i in range(0, len(circles)):
        index, value = calculateLowestHawaiian(local)
        tmp = local.pop(index)
        stacking.append(tmp)

    
    #calculates the new postions
    for i in range(0, len(stacking)):
        N = stacking[i + 1:]
        visbleInt = caculateVisibleIntervall(stacking[i], N)
        maximum = -1
        angle = 0

        if visbleInt is None:
            angle = 0

        else:
        #calculation of the anchor point
            for interval in visbleInt:
                if interval[1] < interval[0]:
                    interval[1] = interval[1] + 2 * np.pi
                tmp = np.absolute(interval[1] - interval[0])
                if tmp > maximum:
                    maximum = tmp

                angle = interval[0] + (interval[1] - interval[0]) / 2


        onCircleX, onCircleY = calculatePointOnCircle(
            [int(stacking[i][0]), int(stacking[i][1]), int(stacking[i][2])], angle
        )

        deltaX = stacking[i][0] - onCircleX
        deltaY = stacking[i][1] - onCircleY
        deltaX = deltaX / stacking[i][2]  
        deltaY = deltaY / stacking[i][2]  

        #calculates the new centers of the subcircles
        for j in range(2, len(stacking[i])):
            offSet = 0

            x0 = onCircleX + deltaX * (stacking[i][j] - offSet)
            y0 = onCircleY + deltaY * (stacking[i][j] - offSet)
            r0 = stacking[i][j]
            stackingAllCircles.append([x0, y0, r0])

    return stackingAllCircles


# [for hawaiian] calculates the visible parts of a circle and the circles N
#which lie above it
def caculateVisibleIntervall(c, N):
    CoverIntervals1D = []
    CoverIntervals2D = []
    for n in N:
        a, b, bo = calculateSingleCoverInterval(c, n)
        if bo is True:
            CoverIntervals2D.append([a, b])
            CoverIntervals1D.append([a, 0])
            CoverIntervals1D.append([b, 1])
    CoverIntervals1D.sort()
    CoverIntervals2D.sort()
    if len(CoverIntervals1D) == 0:
        return [[0, 0]]
    if not testCompletlyCovered(CoverIntervals2D):
        shift = findStartingPoint(CoverIntervals1D)
        CoverArray = calculateMaxIntervalsWithShift(CoverIntervals1D, shift)
        visibleArray2D = []
        visibleArray2D.append([CoverArray[len(CoverArray) - 1], CoverArray[0]])
        for i in range(0, int((len(CoverArray) / 2)) - 1):
            visibleArray2D.append([CoverArray[2 * i + 1], CoverArray[2 * i + 2]])
        return visibleArray2D


# calculates the lowest circle (for circles without subcircles)
# for the maximizing the minimum of the visible area
def calculateLowestCircleMaxMin(Circles, mode):
    maximum = -1
    index = -1
    for i in range(0, len(Circles)):
        tmp = Circles[:i] + Circles[i + 1:]
        if mode == "absolute":
            tmpValue = calculateAbsoluteBoundaryUtility(Circles[i], tmp)
        else:
            tmpValue = calculateRelativeBoundaryUtility(Circles[i], tmp)
        if tmpValue > maximum:
            index = i
            maximum = tmpValue
    return index, maximum


# calculates the lowest circle (for circles with subcircles)
## for maximizing the minimum of the visible area of the minimal subcircle 
# mode:"absolute" or "relative"
def calculateLowestCircleMaxMinMinK(realCircles, mode):
    Circles = copy.deepcopy(realCircles)
    maximum = -1
    index = -1
    while maximum <= 0:
        for i in range(0, len(Circles)):
            tmp = Circles[:i] + Circles[i + 1:]
            tmp = np.array(tmp)
            if not len(tmp) == 0:
                tmp = tmp[:, :3]
            tmpMin = float("inf")
            for k in range(0, len(Circles[0]) - 2):

                tmpCircle = [Circles[i][0], Circles[i][1], Circles[i][2 + k]]
                if mode == "absolute":
                    tmpValue = calculateAbsoluteBoundaryUtility(tmpCircle, tmp)
                else:
                    tmpValue = calculateRelativeBoundaryUtility(tmpCircle, tmp)
                if tmpValue < tmpMin:
                    tmpMin = tmpValue

            if tmpMin > maximum:
                index = i
                maximum = tmpMin

        if maximum > 0:
            return index, maximum

        #heuristic just pops the innermost circles
        if maximum <= 0:
            for i in range(0, len(Circles)):
                Circles[i].pop(len(Circles[i]) - 1)


# calculates the lowest circle (for circles with subcircles)
# for maximizing the sum of the visible areas of the minimal subcircle 
# mode:"absolute" or "relative"
def calculateLowestCircleMaxMinSumK(Circles, mode):
    maximum = -1
    index = -1
    for i in range(0, len(Circles)):
        tmpSum = 0
        tmp = Circles[:i] + Circles[i + 1:]
        tmp = np.array(tmp)
        if not len(tmp) == 0:
            tmp = tmp[:, :3]
        for k in range(0, len(Circles[0]) - 2):
            tmpCircle = [Circles[i][0], Circles[i][1], Circles[i][2 + k]]
            if mode == "absolute":
                tmpValue = calculateAbsoluteBoundaryUtility(tmpCircle, tmp)
                tmpSum = tmpSum + tmpValue
            if mode == "relative":
                tmpValue = calculateRelativeBoundaryUtility(tmpCircle, tmp)  
                tmpSum = tmpSum + tmpValue  
        if tmpSum > maximum:
            index = i
            maximum = tmpSum
    return index, maximum



# input: circles nested-List [[x,y,r1,r2,r3....][x',y',r1',....],...]   r1>r2>...
# output: nested-List [[x,y,r1,r2,r3....][x',y',r1',....],...]   r1>r2>...
# maximizes minimum of minimal subcircles
def algorithmNestedDisksStackingMinMin(circles, mode):
    local = copy.deepcopy(circles)
    solution = []
    objective = 0

    for i in range(0, len(circles)):
        index, cur_objective = calculateLowestCircleMaxMinMinK(local, mode)
        tmp = local.pop(index)
        solution.append(tmp)
        objective += cur_objective
    return solution, objective


# input: circles nested-List [[x,y,r1,r2,r3....][x',y',r1',....],...]   r1>r2>...
# output: nested-List [[x,y,r1,r2,r3....][x',y',r1',....],...]   r1>r2>...
# maximizes minimum of sum of the subcircles
def algorithmNestedDisksStackingMinSum(circles, mode):
    local = circles.copy()
    solution = []
    objective = 0

    for i in range(0, len(circles)):
        index, cur_objective = calculateLowestCircleMaxMinSumK(local, mode)
        tmp = local.pop(index)
        solution.append(tmp)
        objective += cur_objective
    return solution, objective


########################################################################
#####Algorithms for comparison##########################################
########################################################################
# input: circles nested-List [[x,y,r1,r2,r3....][x',y',r1',....],...]   r1>r2>...


def algorithmNestedDisksPainter(circles):
    """Sorts circles by outer radius which is at index 2 in ascending order."""
    local = circles.copy()
    local.sort(key=lambda x: x[2], reverse=True)
    return local


def algorithmNestedDisksLeftToRight(circles):
    """Sorts circles by y-value at index 1 that is left to right on most screens in ascending order."""
    local = circles.copy()
    local.sort(key=lambda x: x[1], reverse=False)
    return local


def algorithmNestedDisksRightToLeft(circles):
    """Sorts circles by y-value at index 1 that is left to right on most screens in descending order."""
    local = circles.copy()
    local.sort(key=lambda x: x[1], reverse=True)
    return local


def algorithmNestedDisksRandom(circles):
    """A monkey shakes a box filled with circles and returns it."""
    local = circles.copy()
    random.shuffle(local)
    return local


def algorithmHawaiianLeftToRight(circles):
    """Sorts circles by y-value at index 1 that is left to right on most screens in ascending order and shifts the
    inner circles by a delta and returns all circles in the format [x0, y0, r0]."""
    local = circles.copy()
    stackingAllCircles = []

    stacking = local
    stacking.sort(key=lambda x: x[1], reverse=False)

    for i in range(0, len(stacking)):
        onCircleX = stacking[i][0]
        onCircleY = stacking[i][1] - stacking[i][2]
        deltaX = stacking[i][0] - onCircleX
        deltaY = stacking[i][1] - onCircleY
        deltaX = deltaX / stacking[i][2]
        deltaY = deltaY / stacking[i][2]

        for j in range(2, len(stacking[i])):
            x0 = onCircleX + deltaX * (stacking[i][j])
            y0 = onCircleY + deltaY * (stacking[i][j])
            r0 = stacking[i][j]
            stackingAllCircles.append([x0, y0, r0])
    return stackingAllCircles


def algorithmHawaiianRightToLeft(circles):
    """Sorts circles by y-value at index 1 that is left to right on most screens in descending order and shifts the
    inner circles by a delta and returns all circles in the format [x0, y0, r0]."""
    local = circles.copy()
    stackingAllCircles = []

    stacking = local
    stacking.sort(key=lambda x: x[1], reverse=True)

    for i in range(0, len(stacking)):
        onCircleX = stacking[i][0]
        onCircleY = stacking[i][1] + stacking[i][2]
        deltaX = stacking[i][0] - onCircleX
        deltaY = stacking[i][1] - onCircleY
        deltaX = deltaX / stacking[i][2]
        deltaY = deltaY / stacking[i][2]

        for j in range(2, len(stacking[i])):
            x0 = onCircleX + deltaX * (stacking[i][j])
            y0 = onCircleY + deltaY * (stacking[i][j])
            r0 = stacking[i][j]
            stackingAllCircles.append([x0, y0, r0])
    return stackingAllCircles


def algorithmHawaiianRandom(circles):
    """A monkey shakes a box filled with circles and returns them all in pieces a [x0, y0, z0]."""
    local = circles.copy()
    stackingAllCircles = []

    stacking = local
    random.shuffle(stacking)

    for i in range(0, len(stacking)):
        N = stacking[i + 1:]
        visbleInt = caculateVisibleIntervall(stacking[i], N)
        maximum = -1
        angle = 0

        if visbleInt is None:
            onCircleX = stacking[i][0] + 2
            onCircleY = stacking[i][1] + 2

        else:
            for interval in visbleInt:
                if interval[1] < interval[0]:
                    interval[1] = interval[1] + 2 * np.pi
                tmp = np.absolute(interval[1] - interval[0])
                if tmp > maximum:
                    maximum = tmp

                    angle = interval[0] + (interval[1] - interval[0]) / 2

            onCircleX, onCircleY = calculatePointOnCircle(
                [int(stacking[i][0]), int(stacking[i][1]), int(stacking[i][2])], angle
            )

        deltaX = stacking[i][0] - onCircleX
        deltaY = stacking[i][1] - onCircleY
        deltaX = deltaX / stacking[i][2]
        deltaY = deltaY / stacking[i][2]

        for j in range(2, len(stacking[i])):
            x0 = onCircleX + deltaX * (stacking[i][j])
            y0 = onCircleY + deltaY * (stacking[i][j])
            r0 = stacking[i][j]
            stackingAllCircles.append([x0, y0, r0])

    return stackingAllCircles


def algorithmHawaiianPainter(circles):
    """Shifts subcircles on longest outer visible perimeter and returns all circles."""
    local = circles.copy()
    stackingAllCircles = []

    stacking = local
    stacking.sort(key=lambda x: x[2], reverse=True)

    #moving the centers with respect to the anchorpoint
    for i in range(0, len(stacking)):
        N = stacking[i + 1:]
        visbleInt = caculateVisibleIntervall(stacking[i], N)
        maximum = -1
        angle = 0

        if visbleInt is None:
            onCircleX = stacking[i][0] + 2
            onCircleY = stacking[i][1] + 2
        else:
            for interval in visbleInt:
                if interval[1] < interval[0]:
                    interval[1] = interval[1] + 2 * np.pi
                tmp = np.absolute(interval[1] - interval[0])
                if tmp > maximum:
                    maximum = tmp
                    angle = interval[0] + (interval[1] - interval[0]) / 2

            onCircleX, onCircleY = calculatePointOnCircle(
                [int(stacking[i][0]), int(stacking[i][1]), int(stacking[i][2])], angle
            )

        deltaX = stacking[i][0] - onCircleX
        deltaY = stacking[i][1] - onCircleY
        deltaX = deltaX / stacking[i][2]
        deltaY = deltaY / stacking[i][2]

        for j in range(2, len(stacking[i])):
            x0 = onCircleX + deltaX * (stacking[i][j])
            y0 = onCircleY + deltaY * (stacking[i][j])
            r0 = stacking[i][j]
            stackingAllCircles.append([x0, y0, r0])

    return stackingAllCircles


def algorithmPieChartsPainter(pies, piepieces):
    """Performas a painter on outer circle-radius at index 2 and moves the inner pieces according to heuristic."""
    n = len(piepieces[0])
    localPies = []
    localPiePieces = []
    localAngles = []

    local = np.concatenate((pies, piepieces), axis=1)
    local = sorted(local, key=lambda x: x[2], reverse=True)

    for l in local:
        localPies.append([l[0], l[1], l[2]])
        tmp = []
        for i in range(1, n + 1):
            tmp.append(l[2 + i])
        localPiePieces.append(tmp)

    for i in range(0, len(localPies)):
        angle, value = caculateOneAnglePie(
            localPies[i], localPiePieces[i], localPies[i + 1:]
        )
        if angle is None:
            x = localPiePieces[i].copy()
            while angle is None:
                if len(x) == 0:
                    angle = 0
                    break
                x.pop(len(x) - 1)
                angle, value = caculateOneAnglePie(localPies[i], x, localPies[i + 1:])

        localAngles.append(angle)

    return localPies, localPiePieces, localAngles


def algorithmPieChartsPainterRandom(pies, piepieces):
    """Performas a painter on outer circle-radius at index 2 and rotates the pie pieces randomly."""
    n = len(piepieces[0])
    localPies = []
    localPiePieces = []

    local = np.concatenate((pies, piepieces), axis=1)
    local = sorted(local, key=lambda x: x[2], reverse=True)

    for l in local:
        localPies.append([l[0], l[1], l[2]])
        tmp = []
        for i in range(1, n + 1):
            tmp.append(l[2 + i])
        localPiePieces.append(tmp)

    localAngles = randomAngles(len(pies))

    return localPies, localPiePieces, localAngles


def algorithmPieChartsRandom(pies, piepieces):
    """Shuffles outer discs and moves all pie pieces with respect to our algorithm."""
    n = len(piepieces[0])
    localPies = []
    localPiePieces = []
    localAngles = []

    localNp = np.concatenate((pies, piepieces), axis=1)
    local = list(localNp)
    random.shuffle(local)
    print(local)

    for l in local:
        localPies.append([l[0], l[1], l[2]])
        tmp = []
        for i in range(1, n + 1):
            tmp.append(l[2 + i])
        localPiePieces.append(tmp)

    for i in range(0, len(localPies)):
        angle, value = caculateOneAnglePie(
            localPies[i], localPiePieces[i], localPies[i + 1:]
        )
        if angle is None:
            x = localPiePieces[i].copy()
            while angle is None:
                if len(x) == 0:
                    angle = 0
                    break
                x.pop(len(x) - 1)
                angle, value = caculateOneAnglePie(localPies[i], x, localPies[i + 1:])

        localAngles.append(angle)

    return localPies, localPiePieces, localAngles


def algorithmPieChartsLeftToRight(pies, piepieces):
    """Outer circles are sorted in ascending order and the pieces according to heuristics."""
    n = len(piepieces[0])
    localPies = []
    localPiePieces = []
    localAngles = []
    local = np.concatenate((pies, piepieces), axis=1)
    local = sorted(local, key=lambda x: x[1], reverse=False)
    for l in local:
        localPies.append([l[0], l[1], l[2]])
        tmp = []
        for i in range(1, n + 1):
            tmp.append(l[2 + i])
        localPiePieces.append(tmp)

    for i in range(0, len(localPies)):
        angle, value = caculateOneAnglePie(
            localPies[i], localPiePieces[i], localPies[i + 1:]
        )
        if angle is None:
            x = localPiePieces[i].copy()
            while angle is None:
                if len(x) == 0:
                    angle = 0
                    break
                x.pop(len(x) - 1)
                angle, value = caculateOneAnglePie(localPies[i], x, localPies[i + 1:])

        localAngles.append(angle)

    return localPies, localPiePieces, localAngles


def algorithmPieChartsRightToLeft(pies, piepieces):
    """Outer circles are sorted in descending order and the pieces according to heuristics."""
    local = np.concatenate((pies, piepieces), axis=1)
    local = sorted(local, key=lambda x: x[1], reverse=True)
    n = len(piepieces[0])

    localPies = []
    localPiePieces = []
    localAngles = []

    local = np.concatenate((pies, piepieces), axis=1)
    local = sorted(local, key=lambda x: x[1], reverse=True)

    for l in local:
        localPies.append([l[0], l[1], l[2]])
        tmp = []
        for i in range(1, n + 1):
            tmp.append(l[2 + i])
        localPiePieces.append(tmp)

    for i in range(0, len(localPies)):
        angle, value = caculateOneAnglePie(
            localPies[i], localPiePieces[i], localPies[i + 1:]
        )
        if angle is None:
            x = localPiePieces[i].copy()
            while angle is None:
                if len(x) == 0:
                    angle = 0
                    break
                x.pop(len(x) - 1)
                angle, value = caculateOneAnglePie(localPies[i], x, localPies[i + 1:])
        localAngles.append(angle)

    return localPies, localPiePieces, localAngles


################################################################################
##################comparisons###################################################


def formatChangeNestedDisks(circles):
    """Extracts circles and number of nestings and returns them."""
    n = len(circles[0]) - 2
    result = []
    for c in circles:
        for i in range(2, len(c)):
            result.append([c[0], c[1], c[i]])

    return result, n


def circumferenceValuesNestedDisks(circles, numberOfNestings):
    """Return relative visibility and number of covered circles."""
    j = 0
    resultArray = []
    resultCovered = 0
    coverCircles = []
    tmp = []

    for i in range(0, int(len(circles) / numberOfNestings)):
        coverCircles.append(circles[i * numberOfNestings])

    for i in range(0, len(circles)):

        tmpvis = caculateVisibleIntervall(
            circles[i], coverCircles[(math.floor(i / numberOfNestings) + 1):]
        )

        tmpValue = 0
        if tmpvis is None:
            resultCovered = resultCovered + 1
            tmp.append(0)
        else:
            # print(tmpvis)
            for k in tmpvis:
                if k[1] <= k[0]:
                    k[1] = k[1] + 2 * np.pi
                tmpValue = tmpValue + (k[1] - k[0])
            tmp.append(tmpValue)

        if j == numberOfNestings - 1:
            resultArray.append(tmp)
            j = -1
            tmp = []
        j = j + 1

    return resultArray, resultCovered


def utilitysNestedDisks(circles):
    """Calculate utilities for nested disk case."""
    x, y = formatChangeNestedDisks(circles)
    (
        minAvgOnSingleGlyph,
        percentageRelative,
        percentageAbsolute,
        minRelativeNonZero,
        minAbsoluteNonZero,
        covered,
    ) = utilitysHawaiian(x, y)
    return (
        minAvgOnSingleGlyph,
        percentageRelative,
        percentageAbsolute,
        minRelativeNonZero,
        minAbsoluteNonZero,
        covered,
    )


def utilitysHawaiian(circles, numberOfNestings):
    """Calculate utilities for hawaiian disk case."""
    percentageRelative = 0
    percentageAbsolute = 0


    minRelativeNonZero = float('inf')
    minAbsoluteNonZero = float('inf')
    minAbsoluteAvg = float('inf')
    sumOfCirc = 0

    relativeVis, covered = circumferenceValuesNestedDisks(circles, numberOfNestings)
    absoluteVis = copy.deepcopy(relativeVis)

    for i in range(0, len(absoluteVis)):
        for j in range(0, len(absoluteVis[0])):
            absoluteVis[i][j] = absoluteVis[i][j] * circles[i * numberOfNestings + j][2]
            sumOfCirc = 2 * np.pi * circles[i * numberOfNestings + j][2] + sumOfCirc

    for i in range(0, len(absoluteVis)):
        tmpForAvg = 0
        for j in range(0, len(absoluteVis[0])):
            tmpForAvg = tmpForAvg + absoluteVis[i][j]
            percentageRelative = relativeVis[i][j] + percentageRelative
            percentageAbsolute = absoluteVis[i][j] + percentageAbsolute
            if (not (absoluteVis[i][j] == 0)) and relativeVis[i][
                j
            ] < minRelativeNonZero:
                minRelativeNonZero = relativeVis[i][j]
            if (not (absoluteVis[i][j] == 0)) and absoluteVis[i][
                j
            ] < minAbsoluteNonZero:
                minAbsoluteNonZero = absoluteVis[i][j]
        if tmpForAvg < minAbsoluteAvg:
            minAbsoluteAvg = tmpForAvg

    percentageRelative = percentageRelative / (
            2 * np.pi * len(absoluteVis) * len(absoluteVis[0])
    )
    percentageAbsolute = percentageAbsolute / sumOfCirc


    minAvgOnSingleGlyph = minAbsoluteAvg

    return (
        covered,
        round(minRelativeNonZero, 3),
        round(minAbsoluteNonZero, 3),
        round(minAvgOnSingleGlyph, 3),
        round(percentageRelative, 3),
        round(percentageAbsolute, 3),
    )


def utilitysPieCharts(circles, piePieces, angles):
    """Calculate utilities for pie chart disk case."""
    absoluteSmallestOverall = float('inf')
    smallestOverall = float('inf')

    largestDist, smallestDist, occludedCounter = calculateAllPieDistances(
        circles, piePieces, angles
    )

    # Calculate absolute values
    for l in largestDist:
        if len(l) == 0:
            x = float('inf')
        else:
            x = min(l)

        if x < absoluteSmallestOverall:
            absoluteSmallestOverall = x
    
    for s in smallestDist:

        if len(s) == 0:
            x = float('inf')
        else:
            x = min(s)
        if x < smallestOverall:
            smallestOverall = x

    absoluteSmallestAvg = 0
    smallestAvg = 0
    k = 0
    j = 0

    # Calculate averages
    for l in largestDist:
        for tmp in l:
            absoluteSmallestAvg = absoluteSmallestAvg + tmp
            k = k + 1
    for s in smallestDist:
        for tmp in s:
            smallestAvg = smallestAvg + tmp
            j = j + 1

    absoluteSmallestAvg = absoluteSmallestAvg / k
    smallestAvg = smallestAvg / j

    sumOccluded = sum(occludedCounter)
    minimumNonZero = smallestOverall

    if sumOccluded > 0:
        minimum = 0
    else:
        minimum = smallestOverall

    minimum = round(minimum, 3)
    minimumNonZero = round(minimumNonZero, 3)
    smallestAvg = round(smallestAvg, 3)
    absoluteSmallestAvg = round(absoluteSmallestAvg, 3)
    sumOccluded = round(sumOccluded, 3)

    print([sumOccluded, minimum, minimumNonZero, smallestAvg, absoluteSmallestAvg])

    return [sumOccluded, minimum, minimumNonZero, smallestAvg, absoluteSmallestAvg]


def calculateAllPieDistances(circles, piePieces, angles):
    """Calculate largest, smallest arc and number occluded lines per circle."""
    largestDist = []
    smallestDist = []
    occludedCounter = []

    for i in range(0, len(circles)):
        adjustedAngles = []
        c = circles[i]
        visibleInt = caculateVisibleIntervall(c, circles[(i + 1):])
        if visibleInt is None:
            x = 2
        else:
            for Int in visibleInt:
                if Int[0] >= Int[1]:
                    Int[1] = Int[1] + np.pi * 2
                adjustedAngles.append(angles[i])
        for p in piePieces[i]:
            adjustedAngles.append(p + angles[i])

        tmpL = []
        tmpS = []
        tmpCounter = 0

        for angle in adjustedAngles:
            isVisible = False
            if visibleInt is None:
                tmpS.append(0)
                tmpL.append(0)
                tmpCounter = tmpCounter + 1
                continue
            for interval in visibleInt:

                if (
                        (interval[0] <= angle and interval[1] > angle)
                        or (
                        interval[0] <= -2 * np.pi + angle < interval[1]
                )
                        or (
                        interval[0] <= 2 * np.pi + angle < interval[1]
                )
                ):
                    if (
                            interval[0] <= -2 * np.pi + angle < interval[1]
                    ):
                        x = np.absolute(-2 * np.pi + angle - interval[0])
                        y = np.absolute(-2 * np.pi + angle - interval[1])
                    else:
                        if (
                                interval[0] <= 2 * np.pi + angle < interval[1]
                        ):
                            x = np.absolute(2 * np.pi + angle - interval[0])
                            y = np.absolute(2 * np.pi + angle - interval[1])
                        else:
                            x = np.absolute(angle - interval[0])
                            y = np.absolute(angle - interval[1])

                    isVisible = True
                    if x <= y:
                        tmpS.append(x)
                        tmpL.append(x * circles[i][2])
                    else:
                        tmpS.append(y)
                        tmpL.append(y * circles[i][2])
            if isVisible is False:
                tmpS.append(0)
                tmpL.append(0)
                tmpCounter = tmpCounter + 1

        largestDist.append(tmpL)
        smallestDist.append(tmpS)
        occludedCounter.append(tmpCounter)

    return largestDist, smallestDist, occludedCounter


################################squares#######################################

# generates the heuristic Piecharts for the squares
def preparePies(squares):
    circles = []
    piePieces = []
    baseAngles = []

    for s in squares:
        radius = 0
        tmpPiece = []
        center = [s[6][0], s[6][1]]
        baseLine = [s[2][0], s[2][1]]  # base piePiece devidinglineAt 0
        baseAngle = calculateRelativeAngle(center, baseLine)  # angle in the square

        # init the three(four) deviding lines which must be visible
        tmpAngle = calculateRelativeAngle(center, s[4]) - baseAngle
        tmpPiece.append(tmpAngle)
        tmpAngle = calculateRelativeAngle(center, s[5]) - baseAngle
        tmpPiece.append(tmpAngle)
        tmpAngle = calculateRelativeAngle(center, s[0]) - baseAngle
        tmpPiece.append(tmpAngle)

        # radius of the circle
        radius = distance(center[0], center[1], s[4][0], s[4][1]) + distance(
            center[0], center[1], s[5][0], s[5][1]
        )
        radius = radius / 2

        # we want positive angles only
        tmpPiece = [a + 2 * np.pi if a <= 0 else a for a in tmpPiece]

        baseAngles.append(baseAngle)
        circles.append([center[0], center[1], radius])
        piePieces.append(tmpPiece)

    for i in range(0, len(piePieces)):
        for j in range(0, len(piePieces[i])):
            if piePieces[i][j] < 0:
                piePieces[i][j] = piePieces[i][j] + 2 * np.pi
        piePieces[i].sort()

    return circles, piePieces, baseAngles


# rotates Squares such that the heuristic is maximized
def rotateTheSquares(squares, angles):
    for i in range(0, len(squares)):  #
        square_center = (squares[i][6][1], squares[i][6][0])
        for j in range(0, len(squares[i])):
            if not isinstance(squares[i][j][0], str):
                angle = angles[i]
                y = squares[i][j][0]
                x = squares[i][j][1]
                x1, x0 = rotated_about(x, y, square_center[0], square_center[1], angle)
                squares[i][j][0] = x0
                squares[i][j][1] = x1
    return squares


#maximizes heuristic for a given stacking
def heuristicRotationForStacking(squares):
    localCircles, localPiePieces, baseAngles = preparePies(squares)
    angle = 0
    resultAngles = []
    for i in range(0, len(squares)):
        angle, value = caculateOneAnglePie(
            localCircles[i], localPiePieces[i], localCircles[i + 1:]
        )

        if angle == None:
            angle = 0

        resultAngles.append(-baseAngles[i] + np.pi / 2 - angle)

    # rotates Squares such that the heuristic is maximized
    squares = rotateTheSquares(squares, resultAngles)

    return squares


def algorithmSquaresStacking(squares):
    localCircles, localPiePieces, baseAngles = preparePies(squares)
    localSquares = copy.deepcopy(squares)
    angle = 0
    resultOrder = []
    resultAngles = []
    resultAnglesForPies = []
    resultOrderForPies = []
    resultPiecesForPies = []

    while len(localCircles) > 0:
        # calculate next glyph
        ind, angle = calculateLowestPie(localCircles, localPiePieces)

        # get next glyph
        tmpCircle = localCircles.pop(ind)
        tmpPiece = localPiePieces.pop(ind)
        tmpSquare = localSquares.pop(ind)

        # input into new lists
        resultAngles.append(-baseAngles[ind] + np.pi / 2 - angle)
        resultOrder.append(tmpSquare)
        resultAnglesForPies.append(angle)
        resultOrderForPies.append(tmpCircle)
        resultPiecesForPies.append(tmpPiece)

    # rotates Squares such that the heuristic is maximized
    resultOrder = rotateTheSquares(resultOrder, resultAngles)

    return resultOrder, resultOrderForPies, resultPiecesForPies, resultAnglesForPies


#############################################################################
############ Square Comparison Algorithms ###################################
#############################################################################


# optimal rotations but ordered by painter's algorithm
def algorithmHeuristicPainterSquareStacking(squares):
    squares.sort(key=sideLength, reverse=True)
    return heuristicRotationForStacking(squares)


# random rotations and ordered by painter's algorithm
def algorithmRandomPainterSquareStacking(squares):
    squares.sort(key=sideLength, reverse=True)
    angles = randomAngles(len(squares))
    return rotateTheSquares(squares, angles)


# optimal rotations but ordered randomly
def algorithmHeuristicRandomSquareStacking(squares):
    random.shuffle(squares)
    return heuristicRotationForStacking(squares)


# random rotations and ordered randomly
def algorithmCompletelyRandomSquareStacking(squares):
    random.shuffle(squares)
    angles = randomAngles(len(squares))
    return rotateTheSquares(squares, angles)


# generate random angles
def randomAngles(length):
    return [random.random() * 2 * np.pi for i in range(length)]


# euclidian distance
def distance(ax, ay, bx, by):
    return math.sqrt((by - ay) ** 2 + (bx - ax) ** 2)


# rotates point `A` about point `B` by `angle` radians counterclockwise.
def rotated_about(ax, ay, bx, by, angle):
    radius = distance(ax, ay, bx, by)
    angle += math.atan2(ay - by, ax - bx)
    return (bx - radius * math.cos(angle), by - radius * math.sin(angle))


################################################################################
############################# square functions #################################


def utilitysSquares(squares):
    minimum = float("inf")
    minGreaterZero = float("inf")
    avg = 0

    for i, currentSquare in enumerate(squares):
        squaresAbove = squares[i + 1:]
        value = distanceToOcclusion(currentSquare, squaresAbove)
        avg = avg + value
        minimum = min(value, minimum)

        if value > 0:
            minGreaterZero = min(value, minGreaterZero)

    occludedCounter = numberOfOccludedPointsIn(squares)
    avg = avg / len(squares)
    return [round(occludedCounter), round(minGreaterZero, 3), round(avg, 3)]


def numberOfOccludedPointsIn(squares):
    counter = 0
    for i, square in enumerate(squares):
        squaresAbove = squares[i + 1:]
        occludedIntervals = occludedIntervalsPerSide(square, squaresAbove)
        counter += numberOfOccludedPointsOf(square, occludedIntervals)
    return counter


def distanceToOcclusion(square, squares):
    occludingIntervals = occludedIntervalsPerSide(square, squares)
    return minDistanceToOcclusion(square, occludingIntervals)


def numberOfOccludedPointsOf(square, occlusionsPerSide):
    counter = 0
    points = importantSquarePoints(square)
    for i, t in points:
        if isOccluded(t, occlusionsPerSide[i]):
            counter += 1
    return counter


def occludedIntervalsPerSide(square, squares):
    relevant_squares = removeDistantSquares(square, squares)
    occluded_intervals = [
        occludedIntervalsForSide(square, i, relevant_squares) for i in range(4)
    ]
    return mergeAllIntervals(occluded_intervals)


def removeDistantSquares(square, squares):
    filteredSquares = []
    for sq in squares:
        if not haveDisjointBoundingBoxes(square, sq):
            filteredSquares.append(sq)
    return filteredSquares


def occludedIntervalsForSide(square, i, squares):
    occludedIntervals = []
    side = [square[i], square[(i + 1) % 4]]

    for sq in squares:
        interval = occludedIntervalsForSquare(side, sq)
        if interval is not None:
            occludedIntervals.append(interval)
        if interval == [0, 1]:
            break

    return occludedIntervals


def occludedIntervalsForSquare(side, square):
    if sideIsContainedInSquare(side, square):
        return [0, 1]

    intersections = determineIntersections(side, square)

    if len(intersections) == 1:
        t = intersections[0]
        result = []
        if liesWithin(side[0], square):
            result = [0, t]
        elif liesWithin(side[1], square):
            result = [t, 1]
        else:
            result = [t, t]
        return result

    if len(intersections) == 2:
        [a, b] = intersections
        return [a, b] if a < b else [b, a]

    return None


def sideIsContainedInSquare(side, square):
    return liesWithin(side[0], square) and liesWithin(side[1], square)


def liesWithin(p, square):
    numOfIntersections = 0
    q = [p[0] + 1, p[1]]
    for i in range(4):
        t, s = solveLinearEquation(p, q, square[i], square[(i + 1) % 4])
        if 0 <= t and s >= 0 and s < 1:
            numOfIntersections += 1
    return numOfIntersections % 2 == 1


def determineIntersections(side, square):
    intersections = []
    for index in range(4):
        t, s = solveLinearEquation(
            side[0], side[1], square[index], square[(index + 1) % 4]
        )
        if 0 <= t and t <= 1 and s <= 0 and s < 1:
            intersections.append(t)
    return intersections


def solveLinearEquation(A, B, C, D):
    [a, c] = [B[0] - A[0], D[0] - C[0]]
    [b, d] = [B[1] - A[1], D[1] - C[1]]
    det = a * d - c * b
    if det != 0:
        [e, f] = [C[0] - A[0], C[1] - A[1]]
        result = [e * d - f * c, e * b - f * a]
        return [result[0] / det, result[1] / det]
    return [-1, -1]


def mergeAllIntervals(intervalArray):
    return [mergeIntervals(intervals) for intervals in intervalArray]


def mergeIntervals(intervals):
    newIntervals = []

    if len(intervals) != 0:
        intervals.sort(key=leftIntervalBoundary)
        currentInterval = intervals[0]
        for inter in intervals:
            if inter[0] <= currentInterval[1]:
                currentInterval[1] = max(currentInterval[1], inter[1])
            else:
                newIntervals.append(currentInterval)
                currentInterval = inter
        newIntervals.append(currentInterval)
    return newIntervals


def leftIntervalBoundary(interval):
    return interval[0]


def minDistanceToOcclusion(square, intervals):
    sideLen = sideLength(square)
    minDist = float("inf")
    points = importantSquarePoints(square)
    for point in points:
        dist = pointDistanceToOcclusion(point, intervals)
        if dist < minDist:
            minDist = dist

    return min(minDist, 2) * sideLen


def sideLength(square):
    a = square[0]
    b = square[1]
    diff = [a[0] - b[0], a[1] - b[1]]
    return math.sqrt(diff[0] * diff[0] + diff[1] * diff[1])


def importantSquarePoints(square):
    A = importantSquarePoint(square[4], square)
    B = importantSquarePoint(square[5], square)
    C = [0, 0]
    D = [2, 0]
    return [A, B, C, D]


def importantSquarePoint(point, square):
    for i in range(4):
        t = calculateStepParam(square[i], square[(i + 1) % 4], point)
        if t is not None:
            return [i, t]
    return None


def calculateStepParam(a, b, c):
    v = []
    w = []

    v.append(b[0] - a[0])
    v.append(b[1] - a[1])
    w.append(c[0] - a[0])
    w.append(c[1] - a[1])

    if v[0] == 0 and v[1] == 0:
        return 0
    elif abs(v[0] * w[1] - v[1] * w[0]) <= 0.02:
        return w[0] / v[0] if v[0] != 0 else w[1] / v[1]
    else:
        return None


def pointDistanceToOcclusion(point, intervals):
    [index, param] = point
    if isOccluded(param, intervals[index]):
        return 0
    else:
        if sum([len(sideIntervals) for sideIntervals in intervals]) == 0:
            return 2
        else:
            wrapped_intervals = wrapIntervals(index, intervals)
            [a, b] = visibleRegion(param, wrapped_intervals)
            return min(param - a, b - param)


def wrapIntervals(index, intervals):
    wrapped_intervals = []
    for i in range(-4, 5):
        wrapped_intervals.extend(shiftIntervals(i, intervals[(i + index) % 4]))
    wrapped_intervals.sort(key=leftIntervalBoundary)
    return wrapped_intervals


def shiftIntervals(i, intervals):
    shifted_intervals = []
    for a, b in intervals:
        shifted_intervals.append([a - i, b - i])
    return shifted_intervals


def isOccluded(t, intervals):
    for [a, b] in intervals:
        if a <= t and t <= b:
            return True
    return False


def visibleRegion(t, intervals):
    lower = [inter for inter in intervals if inter[1] < t]
    higher = [inter for inter in intervals if inter[0] > t]
    a = -4 if len(lower) == 0 else lower[-1][1]
    b = 4 if len(higher) == 0 else higher[0][0]
    return [a, b]


def haveDisjointBoundingBoxes(sq1, sq2):
    bb1 = boundingBox(sq1[0:4])
    bb2 = boundingBox(sq2[0:4])
    return areDisjoint(bb1, bb2)


def boundingBox(points):
    x_coordinates = [point[0] for point in points]
    y_coordinates = [point[1] for point in points]

    left = min(x_coordinates)
    right = max(x_coordinates)
    bottom = min(y_coordinates)
    top = max(y_coordinates)

    return [left, right, bottom, top]


def areDisjoint(bba, bbb):
    return bba[1] < bbb[0] or bbb[1] < bba[0] or bba[3] < bbb[2] or bbb[3] < bba[2]
