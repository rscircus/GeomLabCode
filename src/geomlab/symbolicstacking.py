from PIL import Image
import numpy as np
import time
import cv2
import math
import random
from PIL import Image, ImageDraw

color3PIL = "rgb(100, 100, 100)"  # grau
color2PIL = "rgb(249, 102, 94)"  # rot
color1PIL = "rgb(254, 201, 201)"  # blau
color4PIL = "rgb(200, 239, 245)"  # grün

color3 = [100, 100, 100]  # grau
color2 = [249, 102, 94]  # rot
color1 = [254, 201, 201]  # blau
color4 = [200, 239, 245]  # grün


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
def pieStacking(circles, piePieces):
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


# given some circles of the form (x,y,r1,r2,...) where r1>r2>...
# returns a hawaiianStacking
# form: for each circle with subcircles there are now multiple circles
# output has form [[x1,y1,r1],[x2,y2,r2],....,[x1',y1',r1'],[x2',y2'.r2']...]
def hawaiianStacking(circles):
    local = circles.copy()
    stacking = []
    stackingAllCircles = []
    for i in range(0, len(circles)):
        index, value = calculateLowestCircleMaxMin(local, "absolute")
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
def calculateLowestCircleMaxMinMinK(Circles, mode):
    maximum = -1
    maximumNonZero = -1
    for i in range(0, len(Circles)):
        tmp = Circles[:i] + Circles[i + 1 :]
        tmp = np.array(tmp)
        if not len(tmp) == 0:
            tmp = tmp[:, :3]
        tmpMin = 100000000000
        tmpMinNonZero = 1000000000
        for k in range(0, len(Circles[0]) - 2):
            tmpCircle = [Circles[i][0], Circles[i][1], Circles[i][2 + k]]
            if mode == "absolute":
                tmpValue = calculateAbsoluteBoundaryUtility(tmpCircle, tmp)
            elif mode == "relative":
                tmpValue = calculateRelativeBoundaryUtility(tmpCircle, tmp)
            else:
                print("You shouldn't see this")  # TODO

            if tmpValue < tmpMin:
                tmpMin = tmpValue
            if tmpValue < tmpMin and tmpValue > 0:
                tmpMinNonZero = tmpValue

        if tmpMinNonZero > maximumNonZero:
            indexNonZero = i
            maximumNonZero = tmpMinNonZero
        if tmpMin > maximum:
            index = i
            maximum = tmpMin

    if maximum == 0 and maximumNonZero > 0 and mode == "absolute":
        return indexNonZero, maximumNonZero

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
def maxMinMinKStacking(circles, mode):
    local = circles.copy()
    solution = []
    for i in range(0, len(circles)):
        index, value = calculateLowestCircleMaxMinMinK(local, mode)
        tmp = local.pop(index)
        solution.append(tmp)
    return solution


# input: circles nested-List [[x,y,r1,r2,r3....][x',y',r1',....],...]   r1>r2>...
# output: nested-List [[x,y,r1,r2,r3....][x',y',r1',....],...]   r1>r2>...
# maximizes minimum of sum of the subcircles
def maxMinSumKStacking(circles, mode):
    local = circles.copy()
    solution = []
    for i in range(0, len(circles)):
        index, value = calculateLowestCircleMaxMinSumK(local, mode)
        tmp = local.pop(index)
        solution.append(tmp)
    return solution


# painter only defined for circles without subcircles
def painterAlgorithm(circles):
    local = circles.copy()
    local.sort(key=lambda x: x[2], reverse=True)
    return local


################################################################################
###############################draw functions ###############################


def drawPieSolution(circles, cPieces, angles, image):
    for i in range(0, len(circles)):
        tmpC = circles[i]
        tmpPieces = cPieces[i]
        tmpAngle = angles[i]
        drawPie(tmpC, tmpPieces, tmpAngle, image)


# only for 4 colors
def drawPieSolution2(circles, cPieces, angles, image):
    for i in range(0, len(circles)):
        tmpC = circles[i]
        tmpPieces = cPieces[i]
        tmpAngle = angles[i]
        drawPie2(tmpC, tmpPieces, tmpAngle, image)


def drawSolution(stacking, image):
    numberOfRadi = len(stacking[0]) - 2
    for i in range(0, len(stacking)):
        tmp = stacking[i]
        for k in range(0, numberOfRadi):
            colorValue = 200 - (150 * ((k + 1) / numberOfRadi))
            x = int(tmp[1])
            y = int(tmp[0])
            r = int(tmp[2 + k])
            cv2.circle(
                image,
                (x, y),
                r,
                [colorValue, colorValue, colorValue],
                thickness=-1,
                lineType=8,
                shift=0,
            )
            cv2.circle(
                image,
                (x, y),
                r,
                [colorValue - 19, colorValue - 19, colorValue - 19],
                thickness=2,
                lineType=8,
                shift=0,
            )
        cv2.circle(
            image,
            (int(tmp[1]), int(tmp[0])),
            int(tmp[2]),
            [0, 0, 0],
            thickness=2,
            lineType=8,
            shift=0,
        )


def drawSolutionWeighted(stacking, image):
    numberOfRadi = len(stacking[0]) - 2
    for i in range(0, len(stacking)):
        tmp = stacking[i]
        for k in range(0, numberOfRadi):
            colorValue = 200 - (150 * (k / numberOfRadi))
            x = int(tmp[1])
            y = int(tmp[0])
            r = int(tmp[2 + k])
            cv2.circle(
                image,
                (x, y),
                r,
                [colorValue, colorValue, colorValue],
                thickness=-1,
                lineType=8,
                shift=0,
            )
            cv2.circle(
                image,
                (x, y),
                r,
                [colorValue - 10, colorValue - 10, colorValue - 10],
                thickness=1,
                lineType=8,
                shift=0,
            )
        cv2.circle(
            image,
            (int(tmp[1]), int(tmp[0])),
            int(tmp[2]),
            [0, 0, 0],
            thickness=1,
            lineType=8,
            shift=0,
        )


# only for 4 colors
def drawing4H(stacking, image):
    bo = False
    j = 0
    for i in range(0, len(stacking)):
        tmp = stacking[i]
        x = int(tmp[1])
        y = int(tmp[0])
        r = int(tmp[2])

        if j == 0:
            color = color1
        if j == 1:
            color = color2
        if j == 2:
            color = color3
            j = -1
        if j == 3:
            color = color4
            j = -1
            bo = True
        j = j + 1

        cv2.circle(image, (x, y), r, color, thickness=-1, lineType=8, shift=0)
        if j == 1:
            cv2.circle(
                image,
                (x, y),
                r,
                [22 - 19, 22 - 19, 22 - 19],
                thickness=2,
                lineType=8,
                shift=0,
            )
            bo = False


# only for 4 colors
def drawing4Normal(stacking, image):

    for i in range(0, len(stacking)):
        tmp = stacking[i]
        x = int(tmp[1])
        y = int(tmp[0])
        r = int(tmp[2])

        cv2.circle(image, (x, y), tmp[2], color1, thickness=-1, lineType=8, shift=0)
        cv2.circle(image, (x, y), tmp[3], color2, thickness=-1, lineType=8, shift=0)
        cv2.circle(image, (x, y), tmp[4], color3, thickness=-1, lineType=8, shift=0)
        cv2.circle(image, (x, y), r, [0, 0, 0], thickness=2, lineType=8, shift=0)


# only for 4 colors
def drawing4Pie(circles, cPieces, angles, image):
    for i in range(0, len(circles)):
        tmpC = circles[i]
        tmpPieces = cPieces[i]
        tmpAngle = angles[i]
        drawPie2(tmpC, tmpPieces, tmpAngle, image)
    return image


def drawPie(circle, pieces, angle, image):
    c = circle
    cPieces = pieces
    x = int(c[0])
    y = int(c[1])
    r = int(c[2])
    colorValue = 100

    cv2.circle(
        data1,
        (y, x),
        r,
        [colorValue, colorValue, colorValue],
        thickness=-1,
        lineType=8,
        shift=0,
    )
    cv2.circle(
        data1,
        (y, x),
        r,
        [colorValue - 19, colorValue - 19, colorValue - 19],
        thickness=2,
        lineType=8,
        shift=0,
    )
    x, y = calculatePointOnCircle(c, angle)

    cv2.line(data1, (int(y), int(x)), (int(c[1]), int(c[0])), (0, 0, 255), thickness=2)
    for p in cPieces:
        x, y = calculatePointOnCircle(c, angle + p)
        cv2.line(
            data1, (int(y), int(x)), (int(c[1]), int(c[0])), (0, 255, 0), thickness=2
        )


# only for 4 colors
def drawPie2(circle, pieces, angle, image):
    img1 = ImageDraw.Draw(image)

    x = circle[0]
    y = circle[1]
    r = circle[2]
    shape = [y - r - 4, x - r - 4, y + r + 4, x + r + 4]

    anglesClock = [0, 0, 0, 0, 0]
    anglesClock[0] = -angle * 360 / (2 * np.pi) + 90
    anglesClock[3] = 360 - angle * 360 / (2 * np.pi) + 90
    anglesClock[1] = 360 - (pieces[1] + angle) * 360 / (2 * np.pi) + 90
    anglesClock[2] = 360 - (pieces[0] + angle) * 360 / (2 * np.pi) + 90

    img1.ellipse(shape, fill=(0, 0, 0))

    shape = [y - r, x - r, y + r, x + r]
    img1.pieslice(
        shape, start=anglesClock[0], end=anglesClock[1], fill=color1PIL, outline="black"
    )

    img1.pieslice(
        shape, start=anglesClock[1], end=anglesClock[2], fill=color2PIL, outline="black"
    )

    img1.pieslice(
        shape, start=anglesClock[2], end=anglesClock[3], fill=color3PIL, outline="black"
    )
