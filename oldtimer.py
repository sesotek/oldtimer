#!/usr/bin/python
# oldtimer.py
# Analyzes ChaNGa logs, prints statistics, and plots.
# Author: Ian Smith
# 2011-08-22

# TODO: curses interface or GUI

import sys
import re
import numpy
import pylab as py
#import matplotlib.pyplot

# Regex constants to search for key words in logfile
RE_RUNG_DISTRIBUTION = 'Rung distribution'
RE_DONE = 'Done.'
RE_BIG_STEP_LINE = 'Big step'
# Find number between 'took' and 'seconds'
RE_TOOK_SECONDS = '(?<=took.)([0-9]*\.?[0-9]+).(?=seconds)'
RE_BALANCER = 'Load balancer'
RE_BUILD_TREES = 'Building trees'
RE_GRAVITY = 'Calculating gravity'
RE_DENSITY = 'Calculating densities'
RE_MARK_NEIGHBOR = 'Marking Neighbors'
RE_DENSITY_OF_NEIGHBOR = 'Density of Neighbors'
RE_PRESSURE_GRADIENT = 'Calculating pressure gradients'
RE_DOMAIN_DECOMP = 'Domain decomposition'
# Step as first word on line
RE_SUB_STEP = '^Step:'

# List of Axes
AXES_LIST = [ 'Step', 'TotalStepTime', 'DomainDecompTimes', 'BalancerTimes', 'BuildTreesTimes', 'GravityTimes', 'DensityTimes', 'MarkNeighborTimes', 'DensityOfNeighborTimes', 'PressureGradientTimes', 'RungIndexes' ]

# List of logs
logList = {}

# Class RungIndex keeps info about a step on a rung, such as
# the rung number from and to which the step is calculated, and the
# line numbers of beginning and end of rung step in the log.
class RungIndex:
    def __init__(self):
        self.fromRung = -1
        self.toRung = -1
        self.fromIndex = -1
    def __repr__(self):
        return "rung: " + str(self.fromRung) + " to " + str(self.toRung) + " at index " + str(self.fromIndex)

# Adds a log to the logList, asking the user for a name
# list log: log
def addLogToList(log):
    uniq = False
    logName = ""
    while not uniq:
        logName = raw_input("Enter log name: ")
        if logName in logList:
            print 'Name already exists. Choose a unique name.'
        else:
            uniq = True
    logList[logName] = log



# Begins the parsing of a log file
# list fullLog: list of lines in logfile
# string logName: name of log
def parseLog(fullLog):
    # Break up log into list of Big steps
    # Each bigStep is a dictionary, where 'logLines' contains all the text lines in that step
    bigSteps = []

    for bigStepText in getBigStepsLines(fullLog):
        bigSteps.append( { 'LogLines' : bigStepText } )
    
    # Dictionary of stats and info calculated now, and stored for later use
    for index, bigStep in enumerate(bigSteps):
        bigStep['StepNumber'] = index
        bigStep['TotalStepTime'] = getStepTime(bigStep)
        bigStep['DomainDecompTimes'] = getStepKeywordTimes(bigStep, RE_DOMAIN_DECOMP)  # below are lists of numbers
        bigStep['BalancerTimes'] = getStepKeywordTimes(bigStep, RE_BALANCER)
        bigStep['BuildTreesTimes'] = getStepKeywordTimes(bigStep, RE_BUILD_TREES)
        bigStep['GravityTimes'] = getStepKeywordTimes(bigStep, RE_GRAVITY)
        bigStep['DensityTimes'] = getStepKeywordTimes(bigStep, RE_DENSITY)
        bigStep['MarkNeighborTimes'] = getStepKeywordTimes(bigStep, RE_MARK_NEIGHBOR)
        bigStep['DensityOfNeighborTimes'] = getStepKeywordTimes(bigStep, RE_DENSITY_OF_NEIGHBOR)
        bigStep['PressureGradientTimes'] = getStepKeywordTimes(bigStep, RE_PRESSURE_GRADIENT)
        # Rung indexes stored as a list of rung objects
        bigStep['RungIndexes'] = getRungIndexes(bigStep)    
    
    # Add this log to the logList
    addLogToList(bigSteps)

    printStats(bigSteps)

    return

# TODO: this is very dirty, clean up rung search
def getRungIndexes(bigStep):
    rungIndexes = []
    lastIdx = -1
    for i, line in enumerate(bigStep['LogLines']):
        if "Rungs" in line:
            # dirty part to fix
            s, rungLine = line.split("Rungs")
            rungLine.strip()
            firstRung, secRung = rungLine.split("to")
            secRung, s = secRung.split(".")
            firstRung = int(firstRung)
            secRung = int(secRung)
            idx = RungIndex()
            idx.fromRung = firstRung
            idx.toRung = secRung
            idx.fromIndex = i
            rungIndexes.append(idx)
    return rungIndexes

        
    

# Prints statistics for entire log
def printStats(bigSteps):
    # individual step stats
    for bigStep in bigSteps:
        if bigStep['StepNumber'] == 0:
            print "Init:"
        else:
            print "Big step: ", bigStep['StepNumber']
 
        print "  Domain Decomp time:      ", 
        printListStats(bigStep['DomainDecompTimes'])
        
        print "  LB time:                 ", 
        printListStats(bigStep['BalancerTimes'])
        
        print "  Build trees time:        ", 
        printListStats(bigStep['BuildTreesTimes'])

        print "  Gravity time:            ",
        printListStats(bigStep['GravityTimes'])
 
        print "  Density time:            ",
        printListStats(bigStep['DensityTimes'])
   
        print "  Mark Neighbor time:      ",
        printListStats(bigStep['MarkNeighborTimes'])
        
        print "  Density of Neighbor time:",
        printListStats(bigStep['DensityOfNeighborTimes'])
        
        print "  Pressure Gradient time:  ",
        printListStats(bigStep['PressureGradientTimes'])
        
        print "  Big step time (r):       ", bigStep['TotalStepTime']

    # total stats
    print " - - - - - - - - - -"
    # subtract one for init
    print "Total Big steps: ", getNumBigSteps(bigSteps) - 1

    print "Total Domain Decomp times:      ", 
    printListStats(getAllStepsKeywordTimes(bigSteps, 'DomainDecompTimes'))
        
    print "Total LB times:                 ", 
    printListStats(getAllStepsKeywordTimes(bigSteps, 'BalancerTimes'))
        
    print "Total Build trees times:        ", 
    printListStats(getAllStepsKeywordTimes(bigSteps, 'BuildTreesTimes'))

    print "Total Gravity times:            ",
    printListStats(getAllStepsKeywordTimes(bigSteps, 'GravityTimes'))
 
    print "Total Density times:            ",
    printListStats(getAllStepsKeywordTimes(bigSteps, 'DensityTimes'))
   
    print "Total Mark Neighbor times:      ",
    printListStats(getAllStepsKeywordTimes(bigSteps, 'MarkNeighborTimes'))
        
    print "Total Density of Neighbor times:",
    printListStats(getAllStepsKeywordTimes(bigSteps, 'DensityOfNeighborTimes'))
        
    print "Total Pressure Gradient times:  ",
    printListStats(getAllStepsKeywordTimes(bigSteps, 'PressureGradientTimes'))
    
    print "Total Big Step (r) times:       ",
    printListStats(getAllStepsTimes(bigSteps))

    return

def getStepKeywordTimes(step, keyword):
    timeList = []
    for line in step['LogLines']:
        if keyword in line:
            p = re.search(RE_TOOK_SECONDS, line)
            if p is not None:
                timeList.append(float(p.group()))
    return timeList

# Returns the total time reported for a single big step ('Big step 1 took 10.0 seconds')
def getStepTime(step):
    for line in step['LogLines']:
        if RE_BIG_STEP_LINE in line:
            p = re.search(RE_TOOK_SECONDS, line)
            if p is not None:
                return float(p.group())
    return 0.0


## LOGFILE ALL STEPS TOTALS ##
    
# Returns total balancer time for list of steps                
def getAllStepsKeywordTimes(bigSteps, keyword):
    timeList = []
    for step in bigSteps:
        timeList.append(calcSum(step[keyword]))
    return timeList

def getAllStepsTimes(bigSteps):
    timeList = []
    for step in bigSteps:
        timeList.append(getStepTime(step))
    return timeList

def getRungStepsKeywordTimes(bigSteps, keyword):
    timeList = []
    for step in bigSteps:
        for e in step[keyword]:
            timeList.append(e)
    return timeList


## CALCULATIONS ##

# Prints a line with stats about the numbers in the list
#   min, max, avg, sigma
# list : a list of floats
def printListStats(list):
    print calcSum(list),
    print "avg:", calcAverage(list),
    print "min:", calcMin(list),
    print "max:", calcMax(list),
    print "std:", calcStd(list)
    return

# Returns average of a list of floats
def calcAverage(list):
    if not list:
        return 0.0
    return numpy.mean(list)

def calcSum(list):
    if not list:
        return 0.0
    return sum(list)

def calcMin(list):
    if not list:
        return 0.0
    return min(list)

def calcMax(list):
    if not list:
        return 0.0
    return max(list)

def calcStd(list):
    if not list:
        return 0.0
    return numpy.std(list)



# Returns the number of big steps in the list of big steps
# list bigSteps: list of big step dictionaries
def getNumBigSteps(bigSteps):
    return len(bigSteps)



# Print the filename and other file info:
#   number of lines
# Returns with the file position reset to 0
# file object f: file object
def printTitle(f):
    f.seek(0)
    print f.name, ':'
    print "Lines: ", repr(len(f.readlines())).rjust(3)
    
    print
    f.seek(0)
    return

# Returns a list of file objects where each object is a Big step
# list fullLog: list of lines in logfile
def getBigStepsLines(fullLog):
    # bigSteps is a list of big steps
    bigStepsLines = []
    # bigStep is a list of lines in a single step
    bigStep = []
    stepNum = 0
    # get init lines
    for line in fullLog:
        # find the rung distribution which marks the beginning of each big step
        if RE_RUNG_DISTRIBUTION in line:
            bigStepsLines.append(tuple(bigStep))
            bigStep = []
        
        bigStep.append(line)

        # "Done." signals the proper exit of ChaNGa
        if RE_DONE in line:
            bigStepsLines.append(tuple(bigStep))
            return bigStepsLines

    return bigStepsLines
    

def getDataForAxis(axis, bigSteps, sums):
    if sums:
        if axis == 'Step':
            return range(len(bigSteps))
        elif axis == 'TotalStepTime':
            return getAllStepsTimes(bigSteps)
        else:
            return getAllStepsKeywordTimes(bigSteps, axis)
    else:
        return getRungStepsKeywordTimes(bigSteps, axis)


def createPlot(yLogName, yAxis, xLogName, xAxis, plotNum, sums):
    colorList = ['r', 'g', 'b', 'c', 'm', 'y', 'k']
    print  yLogName + "." + yAxis, "is", colorList[plotNum%7]
   
    plot_line_style = "None"
    if yAxis.endswith("Step") or xAxis.endswith("Step"):
        plot_line_style = '-'
    
    # Set logs for each axis
    bigStepsY = logList[yLogName]
    bigStepsX = logList[xLogName]
    
    yData = getDataForAxis(yAxis, bigStepsY, sums)
    if xAxis == 'Step' and not sums:
        xData = range(len(yData))
    else:
        xData = getDataForAxis(xAxis, bigStepsX, sums)
    
    plot = py.plot(xData, yData, color=colorList[plotNum%7], marker='o', ms=5.0, linestyle=plot_line_style)
    #leg = py.DraggableLegend([plot], [yAxis])
    #leg.draggable()
    py.xlabel(xLogName + "." + xAxis)
    py.ylabel(yLogName + "." + yAxis)
    py.show()

    
    return
    
    
def printAxesList():
    print "Axes: ", AXES_LIST
    return

def getCommand():
    print
    print
    printAxesList()
    print
    print "Prefix exis name with <logname>. as in: <logname>.GravityTimes"
    print "Ready to plot."
    ri = ""
    plotNum = 0
    while True:
        ri = raw_input("Choose your axes (y, x) or type exit: ")
        if (ri == 'exit') or (ri == 'quit'):
            break
        try:
            yAxis, xAxis = ri.split(',')
        except ValueError: 
            # TODO: loop on bad input
            print "Error: Bad formatting"
        else: 
            yAxis = yAxis.strip()
            xAxis = xAxis.strip()
            yLogName, yAxis = yAxis.split(".")
            xLogName, xAxis = xAxis.split(".")
            if (xLogName in logList and yLogName in logList):
                if (xAxis not in AXES_LIST) or (yAxis not in AXES_LIST):
                    print "Error: Unrecognized axis"
                else:
                    sums = getyn("Sum for each big step? ")
                    createPlot(yLogName, yAxis, xLogName, xAxis, plotNum, sums)
                    plotNum += 1
            else:
                print "Unregognized log name"
    return

# TODO provide default value y or n
def getyn(prompt):
    ri = raw_input(prompt + "[Y/n]: ")
    if ri == "n":
        return False
    else:
        return True


def main(*args):
    # get logfile names list from command line
    logFiles = args[1:]

    for logFile in logFiles:
        try:
            f = open(logFile, 'r')
        except IOError:
            print 'Cannot open', logFile
        else:
            printTitle(f)
            fullLog = f.readlines()
            f.close()
            
            parseLog(fullLog)

    getCommand()

if __name__ == '__main__':
    sys.exit(main(*sys.argv))
