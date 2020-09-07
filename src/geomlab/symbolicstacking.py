from PIL import Image
import numpy as np
import time
import cv2
import math
import random
import copy
from PIL import Image, ImageDraw

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
    min = 0
    minindex = 0
    for i in range(0, len(I)):
        if I[i][1] == 0:
            c = c + 1
        else:
            c = c - 1
            if c == min:
                minindex = i
            else:
                if c < min:
                    min = c
                    minindex = i
    if min == 0:
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
        a, b, bo = calculateSingleCoverInterval(c, n)
        if bo == True:
            CoverIntervals2D.append([a, b])
            CoverIntervals1D.append([a, 0])
            CoverIntervals1D.append([b, 1])
    CoverIntervals1D.sort()
    CoverIntervals2D.sort()

    if len(CoverIntervals1D) == 0:
        return 0
    if not testCompletlyCovered(CoverIntervals2D):
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
    CoverIntervals1D = []
    CoverIntervals2D = []
    for n in N:
        a, b, bo = calculateSingleCoverInterval(c, n)
        if bo == True:
            CoverIntervals2D.append([a, b])
            CoverIntervals1D.append([a, 0])
            CoverIntervals1D.append([b, 1])
    CoverIntervals1D.sort()
    CoverIntervals2D.sort()

    if len(CoverIntervals1D) == 0:
        return [[0, 2 * np.pi]]

    if not testCompletlyCovered(CoverIntervals2D):
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
    if intervals == None:
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


# given a circle and devidinglines and the circles that lie above it
# calculates the postion and value of the deviding line
def caculateOneAnglePie(c, piePiecesC, N):
    tmp = caculateFeasibleIntervall(c, piePiecesC, N)
    if tmp == None:
        return None, None
    else:
        angle, value = calculateAngle(tmp)
        if angle == None:
            return None, None
        else:
            return angle, value


# calculates for an arrangement of Pies the pie which should be the lowest one
# in the stacking returns the index of the circle in the list and the angle
# of the first devidingline
def calculateLowestPie(circles, piePieces):
    locPiePieces = []
    for p in piePieces:
        locPiePieces.append([p[0], p[1]])

    hasFound = False
    resultIndex = 0
    resultMax = -1
    resultAngle = 0
    while hasFound == False:

        for i in range(0, len(circles)):
            tmpC = circles[i]
            tmpPieces = locPiePieces[i]
            tmpN = circles[:i] + circles[i + 1 :]
            angle, value = caculateOneAnglePie(tmpC, tmpPieces, tmpN)
            if not angle == None:
                hasFound = True
                if value * tmpC[2] > resultMax:
                    resultAngle = angle
                    resultMax = value * tmpC[2]
                    resultIndex = i

        if hasFound == True:
            return resultIndex, resultAngle

        if len(locPiePieces[0]) == 0:
            break
        if len(locPiePieces) == 0:
            break
        for p in locPiePieces:
            p.pop(len(p) - 1)
    return 0, 0


#############################################################################
##########################Stacking algorithms################################
#############################################################################


# calculates best pie stacking
# input circles: [[x,y,r]...] piePieces [[p1,p2,...]...] 0 is always a deviding line is
# every circle has to have at least 1 more deviding line!
# output:
# resultOrder new Stackingorder
# resultPieces the pieces in the same order as the circles
# for every pie the angle of the 0 devidingline
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


# used for Hawaiian
def calculateLargestContinousCirc(circle, neighbours):
    x = caculateVisibleIntervall(circle, neighbours)
    maximum = -1

    if x == None:
        return 0

    for i in x:
        if i[0] > i[1]:
            i[1] = i[1] + 2 * np.pi
        tmpvalue = i[1] - i[0]
        if maximum < tmpvalue:
            maximum = tmpvalue
    return maximum


def calculateLowestHawaiian(Circles):
    maximum = -1
    for i in range(0, len(Circles)):
        tmp = Circles[:i] + Circles[i + 1 :]
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
    for i in range(0, len(circles)):
        index, value = calculateLowestHawaiian(local)
        # index,value=calculateLowestCircleMaxMin(local,"absolute")
        tmp = local.pop(index)
        stacking.append(tmp)

    for i in range(0, len(stacking)):
        N = stacking[i + 1 :]
        visbleInt = caculateVisibleIntervall(stacking[i], N)
        maximum = -1
        angle = 0

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
        deltaX = deltaX / stacking[i][2]  # (np.sqrt(deltaX*deltaX +deltaY*deltaY))
        deltaY = deltaY / stacking[i][2]  # (np.sqrt(deltaX*deltaX +deltaY*deltaY))

        for j in range(2, len(stacking[i])):
            offSet = 0

            x0 = onCircleX + deltaX * (stacking[i][j] - offSet)
            y0 = onCircleY + deltaY * (stacking[i][j] - offSet)
            r0 = stacking[i][j]
            stackingAllCircles.append([x0, y0, r0])

    return stackingAllCircles


# [for hawaiian] calculates the visible parts of a circle und the circles N
def caculateVisibleIntervall(c, N):
    CoverIntervals1D = []
    CoverIntervals2D = []
    for n in N:
        a, b, bo = calculateSingleCoverInterval(c, n)
        if bo == True:
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
# for the cost Max the Min of visible area
def calculateLowestCircleMaxMin(Circles, mode):
    maximum = -1
    for i in range(0, len(Circles)):
        tmp = Circles[:i] + Circles[i + 1 :]
        if mode == "absolute":
            tmpValue = calculateAbsoluteBoundaryUtility(Circles[i], tmp)
        else:
            tmpValue = calculateRelativeBoundaryUtility(Circles[i], tmp)
        if tmpValue > maximum:
            index = i
            maximum = tmpValue
    return index, maximum


# calculates the lowest circle (for circles with subcircles)
# for the cost: Max the Min of the minimal subcircle of visible area
# mode:"absolute" or "relative"
def calculateLowestCircleMaxMinMinK(realCircles, mode):
    Circles = copy.deepcopy(realCircles)
    maximum = -1
    maximumNonZero = -1
    while maximum <= 0:
        for i in range(0, len(Circles)):
            tmp = Circles[:i] + Circles[i + 1 :]
            tmp = np.array(tmp)
            if not len(tmp) == 0:
                tmp = tmp[:, :3]
            tmpMin = 100000000000
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

        if maximum <= 0:
            for i in range(0, len(Circles)):
                if Circles[i][2] > maximum:
                    index = i
                    maximum = Circles[i][2]
            return index, maximum


# calculates the lowest circle (for circles with subcircles)
# for the cost: Max the Min of the sum of the subcircle of visible area
# mode:"absolute" or "relative"
def calculateLowestCircleMaxMinSumK(Circles, mode):
    maximum = -1
    for i in range(0, len(Circles)):
        tmpSum = 0
        tmp = Circles[:i] + Circles[i + 1 :]
        tmp = np.array(tmp)
        if not len(tmp) == 0:
            tmp = tmp[:, :3]
        for k in range(0, len(Circles[0]) - 2):
            tmpCircle = [Circles[i][0], Circles[i][1], Circles[i][2 + k]]
            if mode == "absolute":
                tmpValue = calculateAbsoluteBoundaryUtility(tmpCircle, tmp)
                tmpSum = tmpSum + tmpValue
            if mode == "relative":
                tmpValue = calculateRelativeBoundaryUtility(tmpCircle, tmp)  #!!!!!!!!
                tmpSum = tmpSum + tmpValue
            if mode == "weighted":
                tmpValue = calculateAbsoluteBoundaryUtility(tmpCircle, tmp)
                tmpSum = tmpSum + (1 / (((len(Circles[0]) - 1) - k) ** 2) * tmpValue)

        if tmpSum > maximum:
            index = i
            maximum = tmpSum
    return index, maximum


# input: circles nested-List [[x,y,r1,r2,r3....][x',y',r1',....],...]   r1>r2>...
# output: nested-List [[x,y,r1,r2,r3....][x',y',r1',....],...]   r1>r2>...
# maximizes minimum of minimal subcircles
def algorithmNestedDisksStackingMinMin(circles, mode):
    local = circles.copy()
    solution = []
    objective = 0
    cur_objective = 0

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
    cur_objective = 0

    for i in range(0, len(circles)):
        index, cur_objective = calculateLowestCircleMaxMinSumK(local, mode)
        tmp = local.pop(index)
        solution.append(tmp)
        objective += cur_objective
    return solution, objective


########################################################################
#####Algorithms for comparison##########################################
########################################################################


def algorithmNestedDisksPainter(circles):
    local = circles.copy()
    local.sort(key=lambda x: x[2], reverse=True)
    return local


def algorithmNestedDisksLeftToRight(circles):
    local = circles.copy()
    local.sort(key=lambda x: x[1], reverse=False)
    return local


def algorithmNestedDisksRightToLeft(circles):
    local = circles.copy()
    local.sort(key=lambda x: x[1], reverse=True)
    return local


def algorithmNestedDisksRandom(circles):
    local = circles.copy()
    random.shuffle(local)
    return local


def algorithmHawaiianLeftToRight(circles):
    local = circles.copy()
    stacking = []
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
    local = circles.copy()
    stacking = []
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
    N = []
    local = circles.copy()
    stacking = []
    stackingAllCircles = []

    stacking = local
    random.shuffle(stacking)

    for i in range(0, len(stacking)):
        N = stacking[i + 1 :]
        visbleInt = caculateVisibleIntervall(stacking[i], N)  #########
        maximum = -1
        angle = 0

        if visbleInt == None:
            print("asd")
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
    local = circles.copy()
    stacking = []
    stackingAllCircles = []

    stacking = local
    stacking.sort(key=lambda x: x[2], reverse=True)

    for i in range(0, len(stacking)):
        N = stacking[i + 1 :]
        visbleInt = caculateVisibleIntervall(stacking[i], N)  #########
        maximum = -1
        angle = 0

        if visbleInt == None:

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
    n = len(piepieces[0])
    localPies = []
    localPiePieces = []
    localAngles = []
    local = np.concatenate((pies, piepieces), axis=1)
    print(type(local))
    local = sorted(local, key=lambda x: x[2], reverse=True)
    for l in local:
        localPies.append([l[0], l[1], l[2]])
        tmp = []
        for i in range(1, n + 1):
            tmp.append(l[2 + i])
        localPiePieces.append(tmp)

    for i in range(0, len(localPies)):
        angle, value = caculateOneAnglePie(
            localPies[i], localPiePieces[i], localPies[i + 1 :]
        )
        if angle == None:
            x = localPiePieces[i].copy()
            while angle == None:
                if len(x) == 0:
                    angle = 0
                    break
                x.pop(len(x) - 1)
                print(x)
                angle, value = caculateOneAnglePie(localPies[i], x, localPies[i + 1 :])

        localAngles.append(angle)

    return localPies, localPiePieces, localAngles


def algorithmPieChartsRandom(pies, piepieces):

    n = len(piepieces[0])
    localPies = []
    localPiePieces = []
    localAngles = []
    local = np.concatenate((pies, piepieces), axis=1)
    random.shuffle(local)
    for l in local:
        localPies.append([l[0], l[1], l[2]])
        tmp = []
        for i in range(1, n + 1):
            tmp.append(l[2 + i])
        localPiePieces.append(tmp)

    for i in range(0, len(localPies)):
        angle, value = caculateOneAnglePie(
            localPies[i], localPiePieces[i], localPies[i + 1 :]
        )
        if angle == None:
            x = localPiePieces[i].copy()
            while angle == None:
                if len(x) == 0:
                    angle = 0
                    break
                x.pop(len(x) - 1)
                print(x)
                angle, value = caculateOneAnglePie(localPies[i], x, localPies[i + 1 :])

        localAngles.append(angle)

    return localPies, localPiePieces, localAngles


def algorithmPieChartsLeftToRight(pies, piepieces):
    n = len(piepieces[0])
    localPies = []
    localPiePieces = []
    localAngles = []
    local = np.concatenate((pies, piepieces), axis=1)
    print(type(local))
    local = sorted(local, key=lambda x: x[1], reverse=False)
    for l in local:
        localPies.append([l[0], l[1], l[2]])
        tmp = []
        for i in range(1, n + 1):
            tmp.append(l[2 + i])
        localPiePieces.append(tmp)

    for i in range(0, len(localPies)):
        angle, value = caculateOneAnglePie(
            localPies[i], localPiePieces[i], localPies[i + 1 :]
        )
        if angle == None:
            x = localPiePieces[i].copy()
            while angle == None:
                if len(x) == 0:
                    angle = 0
                    break
                x.pop(len(x) - 1)
                print(x)
                angle, value = caculateOneAnglePie(localPies[i], x, localPies[i + 1 :])

        localAngles.append(angle)

    return localPies, localPiePieces, localAngles


def algorithmPieChartsRightToLeft(pies, piepieces):
    n = len(piepieces)
    localPies = []
    localPiePieces = []
    local = np.concatenate((pies, piepieces), axis=1)
    local = sorted(local, key=lambda x: x[1], reverse=True)
    n = len(piepieces[0])
    localPies = []
    localPiePieces = []
    localAngles = []
    local = np.concatenate((pies, piepieces), axis=1)
    print(type(local))
    local = sorted(local, key=lambda x: x[1], reverse=True)
    for l in local:
        localPies.append([l[0], l[1], l[2]])
        tmp = []
        for i in range(1, n + 1):
            tmp.append(l[2 + i])
        localPiePieces.append(tmp)

    for i in range(0, len(localPies)):
        angle, value = caculateOneAnglePie(
            localPies[i], localPiePieces[i], localPies[i + 1 :]
        )
        if angle == None:
            x = localPiePieces[i].copy()
            while angle == None:
                if len(x) == 0:
                    angle = 0
                    break
                x.pop(len(x) - 1)
                print(x)
                angle, value = caculateOneAnglePie(localPies[i], x, localPies[i + 1 :])
        localAngles.append(angle)
    return localPies, localPiePieces, localAngles


################################################################################
##################comparisons###################################################


def formatChangeNestedDisks(circles):
    n = len(circles[0]) - 2
    result = []

    for c in circles:

        for i in range(2, len(c)):
            result.append([c[0], c[1], c[i]])

    return result, n


def circumferenceValuesNestedDisks(circles, numberOfNestings):
    j = 0
    resultArray = []
    resultCovered = 0
    coverCircles = []
    for i in range(0, int(len(circles) / numberOfNestings)):
        coverCircles.append(circles[i * numberOfNestings])
    tmp = []
    for i in range(0, len(circles)):
        tmpvis = caculateVisibleIntervall(
            circles[i], coverCircles[(math.floor(i / numberOfNestings) + 1) :]
        )
        tmpValue = 0
        # print(math.floor(i/3)+1)
        if tmpvis == None:
            resultCovered = resultCovered + 1
            tmp.append(0)
        else:
            # print(tmpvis)
            for i in tmpvis:
                if i[1] <= i[0]:
                    i[1] = i[1] + 2 * np.pi
                tmpValue = tmpValue + (i[1] - i[0])
            tmp.append(tmpValue)
        if j == numberOfNestings - 1:
            resultArray.append(tmp)
            j = -1
            tmp = []
        j = j + 1
    return resultArray, resultCovered


def utilitysNestedDisks(circles):
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
    relativeVis, covered = circumferenceValuesNestedDisks(circles, numberOfNestings)
    absoluteVis = copy.deepcopy(relativeVis)
    percentageRelative = 0
    percentageAbsolute = 0
    minRelativeNonZero = 200000000
    minAbsoluteNonZero = 200000000
    minAbsoluteAvg = 20000000

    sumOfCirc = 0

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

    print("Some statistics:")
    print("minSum: ", minAbsoluteAvg)
    print("relPerc: ", percentageRelative)
    print("absPerc: ", percentageAbsolute)
    print("minRelNonZero: ", minRelativeNonZero)
    print("minAbsNoneZero: ", minAbsoluteNonZero)
    print("coveredCircles: ", covered)
    print(" ")
    minAvgOnSingleGlyph = minAbsoluteAvg

    return (
        minAvgOnSingleGlyph,
        percentageRelative,
        percentageAbsolute,
        minRelativeNonZero,
        minAbsoluteNonZero,
        covered,
    )


def utilitysPieCharts(circles, piePieces, angles):
    largestDist, smallestDist, occludedCounter = calculateAllPieDistances(
        circles, piePieces, angles
    )

    largestOverall = 0
    smallestOverall = 200

    for l in largestDist:
        if len(l) == 0:
            x = 0
        else:
            x = max(l)

        if x > largestOverall:
            largestOverall = x
    for s in smallestDist:
        if type(s) == int:
            x = s
        else:
            if len(s) == 0:
                x = 222222222
            else:
                x = min(s)
        if x < smallestOverall:
            smallestOverall = x

    largestAvg = 0
    smallestAvg = 0
    k = 0
    j = 0
    for l in largestDist:
        for tmp in l:
            largestAvg = largestAvg + tmp
            k = k + 1
    for s in smallestDist:
        if type(s) == int:
            smallestAvg = smallestAvg + s
            j = j + 1
        else:
            for tmp in s:
                smallestAvg = smallestAvg + tmp
                j = j + 1
    largestAvg = largestAvg / k
    smallestAvg = smallestAvg / j

    sumOccluded = sum(occludedCounter)

    print("Some statistics:")
    print("maxDist: ", largestOverall)
    print("minDist: ", smallestOverall)
    print("AvgOfMax: ", largestAvg)
    print("smallestAvg: ", smallestAvg)
    print("numberOfOccLines: ", sumOccluded)
    print(" ")

    return largestOverall, smallestOverall, largestAvg, smallestAvg, sumOccluded


def calculateAllPieDistances(circles, piePieces, angles):

    largestDist = []
    smallestDist = []
    occludedCounter = []
    for i in range(0, len(circles)):
        adjustedAngles = []
        c = circles[i]
        visibleInt = caculateVisibleIntervall(c, circles[(i + 1) :])
        if visibleInt == None:
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
            if visibleInt == None:
                tmpCounter = tmpCounter + 1
                continue
            for interval in visibleInt:

                if (
                    (interval[0] <= angle and interval[1] > angle)
                    or (
                        interval[0] <= -2 * np.pi + angle
                        and interval[1] > -2 * np.pi + angle
                    )
                    or (
                        interval[0] <= 2 * np.pi + angle
                        and interval[1] > 2 * np.pi + angle
                    )
                ):
                    if (
                        interval[0] <= -2 * np.pi + angle
                        and interval[1] > -2 * np.pi + angle
                    ):
                        x = np.absolute(-2 * np.pi + angle - interval[0])
                        y = np.absolute(-2 * np.pi + angle - interval[1])
                    else:
                        if (
                            interval[0] <= 2 * np.pi + angle
                            and interval[1] > 2 * np.pi + angle
                        ):
                            x = np.absolute(2 * np.pi + angle - interval[0])
                            y = np.absolute(2 * np.pi + angle - interval[1])
                        else:
                            x = np.absolute(angle - interval[0])
                            y = np.absolute(angle - interval[1])

                    isVisible = True
                    if x <= y:
                        tmpS.append(x)
                        tmpL.append(y)
                    else:
                        tmpS.append(y)
                        tmpL.append(x)
            if isVisible == False:
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
        baseLine = [s[2][0], s[2][1]]  # base piePiece devidinglineAt0
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

        # we only want positive angles
        for a in tmpPiece:
            if a <= 0:
                a = a + 2 * np.pi
        baseAngles.append(baseAngle)
        circles.append([center[0], center[1], radius])
        piePieces.append(tmpPiece)
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


def algorithmSquaresStacking(squares):
    localCircles, localPiePieces, baseAngles = preparePies(squares)
    localSquares = copy.deepcopy(squares)
    angle = []
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


# euclidian distance
def distance(ax, ay, bx, by):
    return math.sqrt((by - ay) ** 2 + (bx - ax) ** 2)


# rotates point `A` about point `B` by `angle` radians counterclockwise.
def rotated_about(ax, ay, bx, by, angle):
    radius = distance(ax, ay, bx, by)
    angle += math.atan2(ay - by, ax - bx)
    return (round(bx - radius * math.cos(angle)), round(by - radius * math.sin(angle)))


#####dataPrep [should most likly be in main but can be used as refrence]######
"""
def prepData(data, maximalSize, scalingFactor, lowerBoundCases, height, width):
    # change data to a structure I can work with
    myData = []
    for case in data:
        tmp = []
        for slot in case:
            tmp.append(slot)
        myData.append(tmp)
    for case in list(myData):
        if case[4] < lowerBoundCases:
            myData.remove(case)

    # calculate secondminimum and prepare scaling of the circles
    maximum = 1
    maximumsecond = 1
    for case in myData:
        if case[4] < 1:
            tmp = 1
        else:
            tmp = case[4]
        if tmp > maximum:
            maximumsecond = maximum
            maximum = tmp
    multiplicativeconstant = maximalSize / np.log(1 + scalingFactor)

    circles = []
    pies = []
    piePieces = []
    squares = []

    # generating circles,pies and squares
    testMax = 0
    for case in myData:
    <<<<<<< HEAD
        lat = case[2]
        long = case[3]
        x, y = latLongToPoint(lat, long, height, width)


        # making sure data makes sense
        if case[4] < case[6]:
=======
        lat=case[2]
        long=case[3]
        x,y = latLongToPoint(lat, long, height, width)
        
        #making sure data makes sense
        case[4]=case[4]
        case[5]=case[5]
        case[6]=case[6]
        
            
        
        if(case[4]<case[6]):
>>>>>>> 61382e3... implement untested cost calculation
            continue
        if case[4] == 0:
            conf = 1
        else:
            conf = case[4]

        if case[5] == 0 or math.isnan(case[5]):
            dead = 1

        else:
            dead = case[5]
        if case[6] == 0 or math.isnan(case[6]):
            rec = 1
        else:
            rec = case[6]

        # nestedCircles
        confAdjusted = multiplicativeconstant * np.log(
            1 + scalingFactor * conf / maximumsecond
        )
        deadAdjusted = multiplicativeconstant * np.log(
            1 + scalingFactor * dead / maximumsecond
        )
        recAdjusted = multiplicativeconstant * np.log(
            1 + scalingFactor * (rec + dead) / maximumsecond
        )

        if conf < dead or conf < rec + dead:
            print(case)
            print(conf, dead, rec + dead)
            print("")
        if dead > rec + dead:
            print(case)

        r = confAdjusted
        rprime2 = deadAdjusted
        rprime1 = recAdjusted

        if r > testMax:
            testMax = r
        circles.append([int(y), int(x), int(r), int(rprime1), int(rprime2)])

        # pies
        pies.append([int(y), int(x), int(r)])
        p1 = (case[5] / case[4]) * 2 * np.pi
        p2 = (((case[6] / case[4])) * 2 * np.pi) + p1
        piePieces.append([p1, p2])

        # squares
        test = createOneSquare(r, case, height, width)
        squares.append(test)
    return circles, pies, piePieces, squares

def createOneSquare(size, case, heightOfImage, widthOfImage):
    square = []
    x, y = latLongToPoint(case[2], case[3], heightOfImage, widthOfImage)

    # corners and center of the square
    center = [y, x]
    x1 = [y + size, x - size]
    x2 = [y + size, x + size]
    x3 = [y - size, x + size]

    # special points and their represented "type"
    x4 = [y - size, x - size]
    x5 = [0, 0, " "]
    x6 = [0, 0, " "]
    last = [" "]

    # data
    allCases = case[4]
    dead = case[5]
    rec = case[6]
    rest = case[4] - dead - rec

    # checks which small square corresponds to which  "type"
    if dead >= rec and dead >= rest:
        perc = dead / allCases
        x5[0] = x1[0] + (x2[0] - x1[0]) * perc
        x5[1] = x1[1] + (x2[1] - x1[1]) * perc
        x5[2] = "dead"
        if rec > rest:
            perc = rec / (rec + rest)
            x6[0] = x2[0] + (x3[0] - x2[0]) * perc
            x6[1] = x2[1] + (x3[1] - x2[1]) * perc
            x6[2] = "rec"
            last = "rest"
        else:
            perc = rest / (rec + rest)
            x6[0] = x2[0] + (x3[0] - x2[0]) * perc
            x6[1] = x2[1] + (x3[1] - x2[1]) * perc
            x6[2] = "rest"
            last = "rec"

        square.append(x1)
        square.append(x2)
        square.append(x3)
        square.append(x4)
        square.append(x5)
        square.append(x6)
        square.append(center)
        square.append(last)
        return square

    if rec >= dead and rec >= rest:
        perc = rec / allCases
        x5[0] = x1[0] + (x2[0] - x1[0]) * perc
        x5[1] = x1[1] + (x2[1] - x1[1]) * perc
        x5[2] = "rec"
        if rest > dead:
            perc = rest / (rest + dead)
            x6[0] = x2[0] + (x3[0] - x2[0]) * perc
            x6[1] = x2[1] + (x3[1] - x2[1]) * perc
            x6[2] = "rest"
            last = "dead"
        else:
            perc = dead / (rest + dead)
            x6[0] = x2[0] + (x3[0] - x2[0]) * perc
            x6[1] = x2[1] + (x3[1] - x2[1]) * perc
            x6[2] = "dead"
            last = "rest"
        square.append(x1)
        square.append(x2)
        square.append(x3)
        square.append(x4)
        square.append(x5)
        square.append(x6)
        square.append(center)
        square.append(last)
        return square

    if rest >= dead and rest >= rec:
        perc = rest / allCases
        x5[0] = x1[0] + (x2[0] - x1[0]) * perc
        x5[1] = x1[1] + (x2[1] - x1[1]) * perc
        x5[2] = "rest"
        if rec > dead:
            perc = rec / (rec + dead)
            x6[0] = x2[0] + (x3[0] - x2[0]) * perc
            x6[1] = x2[1] + (x3[1] - x2[1]) * perc
            x6[2] = "rec"
            last = "dead"
        else:
            perc = dead / (rec + dead)
            x6[0] = x2[0] + (x3[0] - x2[0]) * perc
            x6[1] = x2[1] + (x3[1] - x2[1]) * perc
            x6[2] = "dead"
            last = "rec"

        # create the square
        square.append(x1)
        square.append(x2)
        square.append(x3)
        square.append(x4)
        square.append(x5)
        square.append(x6)
        square.append(center)
        square.append(last)
        return square"""


################################################################################
############################# square functions #################################


def valueOfSquareConfiguration(squares):
    minimum = float("inf")
    minGreaterZero = float("inf")

    for i, currentSquare in enumerate(squares):
        squaresAbove = squares[i + 1 :]
        value = distanceToOcclusion(currentSquare, squaresAbove)
        minimum = min(value, minimum)
        if value > 0:
            minGreaterZero = min(value, minGreaterZero)

    return [minimum, minGreaterZero]


def distanceToOcclusion(square, squares):
    occludingIntervals = occludedIntervalsPerSide(square, squares)
    return minDistanceToOcclusion(square, occludingIntervals)


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
        if interval != None:
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
    intervals.sort(key=leftIntervalBoundary)
    currentInterval = intervals[0]
    for inter in enumerate(intervals):
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

    return min(minDist, 4) * sideLen


def sideLength(square):
    a = square[0], b = square[1]
    diff = [a[0] - b[0], a[1] - b[1]]
    return math.sqrt(diff[0] * diff[0] + diff[1] * diff[1])


def importantSquarePoints(square):
    [a_index, a_param] = a_info = importantSquarePoint(square[5], square)
    b_info = [(a_index + 2) % 4, 1 - a_param]
    c_info = importantSquarePoint(square[6], square)
    return [a_info, b_info, c_info]


def importantSquarePoint(point, square):
    for i in range(4):
        t = calculateStepParam(square[i], square[(i + 1) % 4], point)
        if t != None:
            return [i, t]
    return None


def calculateStepParam(a, b, c):
    v = [], w = []
    v.insert(b[0] - a[0])
    v.insert(b[1] - a[1])
    w.insert(c[0] - a[0])
    w.insert(c[1] - a[1])
    q_0 = quotient(v[0], w[0])
    q_1 = quotient(v[1], w[1])
    if float("inf") in [q_0, q_1]:
        return None
    if None in [q_0, q_1]:
        return q_1 if q_0 == None else q_0
    if not math.isclose(q_0, q_1):
        return None
    return q_1


def quotient(a, b):
    if b == 0:
        return None if (a == 0) else float("inf")
    else:
        return a / b


def pointDistanceToOcclusion(point, intervals):
    [index, param] = point
    if isOccluded(param, intervals[index]):
        return 0
    else:
        if sum([len(sideIntervals) for sideIntervals in intervals]) == 0:
            return 4
        else:
            wrapped_intervals = wrapIntervals(index, intervals)
            [a, b] = visibleRegion(param, wrapped_intervals)
            return min(param - a, b - param)


def wrapIntervals(index, intervals):
    wrapped_intervals = []
    for i in range(-4, 5):
        wrapped_intervals.extend(shiftIntervals(i, intervals[(i + index) % 4]))
    return wrapped_intervals.sort(key=leftIntervalBoundary)


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
