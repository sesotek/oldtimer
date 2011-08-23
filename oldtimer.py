#!/usr/bin/python


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
RE_TOOK_SECONDS = '(?<=took.)([0-9]*\.?[0-9]+).(?=seconds)'
RE_BALANCER = 'Load balancer'
RE_BUILD_TREES = 'Building trees'
RE_GRAVITY = 'Calculating gravity'
RE_DENSITY = 'Calculating densities'
RE_MARK_NEIGHBOR = 'Marking Neighbors'
RE_DENSITY_OF_NEIGHBOR = 'Density of Neighbors'
RE_PRESSURE_GRADIENT = 'Calculating pressure gradients'
RE_DOMAIN_DECOMP = 'Domain decomposition'
RE_SUB_STEP = '^Step:'

# List of Axes
AXES_LIST = [ 'Step', 'TotalStepTime', 'DomainDecompTimes', 'BalancerTimes', 'BuildTreesTimes', 'GravityTimes', 'DensityTimes', 'MarkNeighborTimes', 'DensityOfNeighborTimes', 'PressureGradientTimes' ]

# Begins the parsing of a log file
# list fullLog: list of lines in logfile
def parseLog(fullLog):
    # Break up log into list of Big steps
    # Each bigStep is a dictionary, where 'logLines' contains all the text lines in that step
    bigSteps = []
    for bigStepText in getBigStepsLines(fullLog):
        bigSteps.append( { 'LogLines' : bigStepText } )
    
    for index, bigStep in enumerate(bigSteps):
        bigStep['StepNumber'] = index
        bigStep['TotalStepTime'] = getStepTime(bigStep)
        bigStep['DomainDecompTimes'] = getStepKeywordTimes(bigStep, RE_DOMAIN_DECOMP)
        bigStep['BalancerTimes'] = getStepKeywordTimes(bigStep, RE_BALANCER)
        bigStep['BuildTreesTimes'] = getStepKeywordTimes(bigStep, RE_BUILD_TREES)
        bigStep['GravityTimes'] = getStepKeywordTimes(bigStep, RE_GRAVITY)
        bigStep['DensityTimes'] = getStepKeywordTimes(bigStep, RE_DENSITY)
        bigStep['MarkNeighborTimes'] = getStepKeywordTimes(bigStep, RE_MARK_NEIGHBOR)
        bigStep['DensityOfNeighborTimes'] = getStepKeywordTimes(bigStep, RE_DENSITY_OF_NEIGHBOR)
        bigStep['PressureGradientTimes'] = getStepKeywordTimes(bigStep, RE_PRESSURE_GRADIENT)
    
    
    printStats(bigSteps)

    getCommand(bigSteps)

    return

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
    

def createPlot(yAxis, xAxis, bigSteps, plotNum):
    colorList = ['r', 'g', 'b', 'c', 'm', 'y', 'k']
    print  yAxis, "is", colorList[plotNum%7]
    plot_line_style = "None"

    if yAxis == 'Step':
        yData = range(len(bigSteps))
    elif yAxis == 'TotalStepTime':
        yData = getAllStepsTimes(bigSteps)
    else:
        yData = getAllStepsKeywordTimes(bigSteps, yAxis)
    
    if xAxis == 'Step':
        xData = range(len(bigSteps))
        plot_line_style = '-'
    elif xAxis == 'TotalStepTime':
        xData = getAllStepsTimes(bigSteps)
    else:
        xData = getAllStepsKeywordTimes(bigSteps, xAxis)

    plot = py.plot(xData, yData, color=colorList[plotNum%7], marker='o', ms=5.0, linestyle=plot_line_style)
    #leg = py.DraggableLegend([plot], [yAxis])
    #leg.draggable()
    py.xlabel(xAxis)
    py.ylabel(yAxis)
    py.show()

    
    return
    
    
def printAxesList():
    print "Axes: ", AXES_LIST
    return

def getCommand(bigSteps):
    print
    print
    printAxesList()
    print
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
   
            if (xAxis not in AXES_LIST) or (yAxis not in AXES_LIST):
                print "Error: Unrecognized axis"
            else:
                createPlot(yAxis, xAxis, bigSteps, plotNum)
                plotNum += 1
    return

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


if __name__ == '__main__':
    sys.exit(main(*sys.argv))
