#!/usr/bin/python
# oldtimer.py
# Analyzes ChaNGa logs, prints statistics, and plots.
# Author: Ian Smith
# 2011-08-22

import pdb

import sys
import re
import os
import platform

import matplotlib

import numpy as np
import pylab as py

# PySide imports
from PySide.QtGui import *
from ui_oldtimer import *

#### begin GUI ####

class MainWindow(QMainWindow, Ui_MainWindow):
    DEFAULT_LOGNAME = "Log"

    def __init__(self, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)
     
        # List of openLog objects
        self.openLogs = []

        # List of bar plots, because py.bar() doesn't draw new bars next to preexisting data
        self.barPlots = []
        
        # Setup menu actions
        self.action_Open.triggered.connect(self.openFile)

        # Setup button actions
        self.buttonPlot.clicked.connect(self.plot)

        # Set disabled plot button
        self.buttonPlot.setEnabled(False)

    def openFile(self):
        filename, filtr = QtGui.QFileDialog.getOpenFileName(self)
        if filename:
            self.loadFile(filename)

    def loadFile(self, filename):
        print "Opening %s..." % filename
        try:
            f = open(filename, 'r')
        except IOError:
            print "Cannot open %s" % filename
        else:
            logLines = f.readlines()
            f.close()
            # Create ChangaLog
            logobject = ChangaLog(logLines)
            # Add ChangaLog and other metadata to openLogs
            self.openLogs.append( openLog(filename, self.getLogName(filename), logobject) )
            # Update the mainwindow widgets to reflect new log
            self.updateAxes()
            self.buttonPlot.setEnabled(True)
           
            # 
            # TODO: Make a new textEdit for each opened log
        #    self.textEdit1.insertPlainText(''.join(logLines))


    def updateAxes(self):
        self.comboYAxis.clear()
        self.comboYLog.clear()
        self.comboResolution.clear()

        for log in self.openLogs:
            self.comboYLog.addItem(log.logname)
        
        self.comboYAxis.addItems(ChangaLog.AXES_LIST)
        self.comboResolution.addItems(ChangaLog.RESOLUTION_LIST)
    

    def getLogName(self, filename):
        goodname = False
        while not goodname:
            prompt = os.path.basename(filename) + "\n\n" + 'Enter a name for this log: '
            name, ok = QInputDialog.getText(self, 'Log name', prompt)
            if ok and name:
                if name in [log.logname for log in self.openLogs]:
                    msgBox = QMessageBox()
                    msgBox.setText('Choose a unique name')
                    msgBox.exec_()
                else:
                    goodname = True
        return name
    
    def plot(self):
        # Call createPlot with data points from logs and axes specified by comboboxes
        points = [] 
        resolution = self.comboResolution.currentText()
        axisYName = self.comboYAxis.currentText()
        logYName = self.comboYLog.currentText()
        pdb.set_trace()
        if resolution == 'Big step' or resolution == 'Sub step':
            for log in self.openLogs:
                if log.logname == logYName:
                    points = log.logobject.getData(axisYName, resolution)

#            if len(pointsY) != len(pointsX):
#                msgBox = QMessageBox()
#                msgBox.setText("Y and X axis data not of equal length\n\nY: " + str(len(pointsY)) + "\nX: " + str(len(pointsX)))
#                msgBox.exec_()
#                return

            createPlot(points['yData'], points['xData'], logYName + '.' + axisYName, resolution, self.checkBoxConnect.isChecked())

        elif resolution == 'Summed rungs':
            for log in self.openLogs:
                if log.logname == logYName:
                    points = log.logobject.getSummedRungs(axisYName)

            createBarPlot(self.barPlots, points['yData'], points['xData'], logYName + '.' + axisYName, resolution)



#### end GUI ####
# Class RungIndex keeps info about a step on a rung, such as
# the rung number from and to which the step is calculated, and the
# line numbers of beginning and end of rung step in the log.
class RungIndex:
    def __init__(self):
        self.fromRung = -1
        self.toRung = -1
        self.fromIndex = -1
        self.toIndex = -1
        self.gravityActive = -1
        self.gasActive = -1
    def __repr__(self):
        return "rung: " + str(self.fromRung) + " to " + str(self.toRung) + " from index " + str(self.fromIndex) + " to " + str(self.toIndex) + "(Gravity: " + str(self.gravityActive) + ")"

# Struct containing metadata about an open log
class openLog():
    def __init__(self, filename, logname, logobject):
        self.filename = filename
        self.logname = logname
        self.logobject = logobject

class ChangaLog():

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
    RE_GRAVITY_ACTIVE = '(?<=Gravity Active:.)([0-9]*\.?[0-9]+).'

    # List of Axes
    AXES_LIST = ['TotalStepTime', 'DomainDecompTimes', 'BalancerTimes', 'BuildTreesTimes', 'GravityTimes', 'DensityTimes', 'MarkNeighborTimes', 'DensityOfNeighborTimes', 'PressureGradientTimes']

    # List of resolutions
    RESOLUTION_LIST = ['Big step', 'Sub step', 'Summed rungs']

    def __init__(self, loglines):
        self.parselog(loglines)


    # Begins the parsing of a log file
    # list fullLog: list of lines in logfile
    # string logName: name of log
    def parselog(self, loglines):
        # Break up log into list of Big steps
        # Each bigStep is a dictionary, where 'logLines' contains all the text lines in that step
        self.bigSteps = []
        
        for bigStepText in self.getBigStepsLines(loglines):
            self.bigSteps.append( { 'LogLines' : bigStepText } )
        
        # Dictionary of stats and info calculated now, and stored for later use
        for index, bigStep in enumerate(self.bigSteps):
            bigStep['StepNumber'] = index + 1 # First big step is #1, not #0
            bigStep['TotalStepTime'] = self.getStepTime(bigStep)
            bigStep['DomainDecompTimes'] = self.getStepKeywordTimes(bigStep, ChangaLog.RE_DOMAIN_DECOMP)
            bigStep['BalancerTimes'] = self.getStepKeywordTimes(bigStep, ChangaLog.RE_BALANCER)
            bigStep['BuildTreesTimes'] = self.getStepKeywordTimes(bigStep, ChangaLog.RE_BUILD_TREES)
            bigStep['GravityTimes'] = self.getStepKeywordTimes(bigStep, ChangaLog.RE_GRAVITY)
            bigStep['DensityTimes'] = self.getStepKeywordTimes(bigStep, ChangaLog.RE_DENSITY)
            bigStep['MarkNeighborTimes'] = self.getStepKeywordTimes(bigStep, ChangaLog.RE_MARK_NEIGHBOR)
            bigStep['DensityOfNeighborTimes'] = self.getStepKeywordTimes(bigStep, ChangaLog.RE_DENSITY_OF_NEIGHBOR)
            bigStep['PressureGradientTimes'] = self.getStepKeywordTimes(bigStep, ChangaLog.RE_PRESSURE_GRADIENT)
            # Rung indexes stored as a list of rung objects
            bigStep['RungIndexes'] = self.getRungIndexes(bigStep)    
            print bigStep['RungIndexes']
#            print bigStep['GravityTimes']

        self.printStats()
    
        #self.getCommand(bigSteps)
    
        return

    # TODO: this is very dirty, clean up rung search
    def getRungIndexes(self, bigStep):
        rungIndexes = []
        lastIdx = None
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
                # Set active gravity particles
                # ex:  Gravity Active: 1021611, Gas Active: 1021610
                grav, gas = s.split(",")
                s, grav = grav.split(":")
                grav.strip()
                idx.gravityActive = int(grav)
                # TODO: set active gas particles
                # Set the toIndex of the last RungIndex
                if lastIdx is not None:
                    lastIdx.toIndex = idx.fromIndex - 1
                rungIndexes.append(idx)
                lastIdx = idx
            # If this is the last line then set the toIndex
            if lastIdx is not None:
                lastIdx.toIndex = i
        return rungIndexes

    # Returns a list of axis names that this log recognizes as plottable
    def getAxes(self):
        return ChangaLog.AXES_LIST

    # Returns a dictionary of 4 lists, 'yData' is Y axis points, 
    #                                  'xData' is X axis points, 
    #                                  'xLabels' is X axis tick labels, 
    #                                  'annotations' is point annotations, 
    # for this log for the specified axis
    def getData(self, axis, resolution):
        yData = []
        xData = []
        xLabels = []
        annotations = []
        if resolution == 'Big step':
            if axis == 'TotalStepTime':
                yData = self.getAllStepsTimes()
            else:
                yData = self.getAllStepsKeywordTimes(axis)
            xData = np.arange(1, len(yData) + 1)
        elif resolution == 'Sub step':
            yData = self.getSubStepsKeywordTimes(axis)
            xData = np.arange(1, len(yData) + 1)
        return {'yData': yData, 'xData': xData, 'xLabels': xLabels, 'annotations': annotations}

    # Returns [y, x],  where:
    #   y ~= [
    #   x ~= ['Rung 3 to 4']
    def getSummedRungs(self, axis):
        y = []
        x = []
        rungsTimes = []
        for step in self.bigSteps:
            rungTime = {}
            for rung in step['RungIndexes']:
                if not rung.fromRung in rungTime:
                    rungTime[rung.fromRung] = []
                rungTime[rung.fromRung].append(self.getStepAxisTotalTimeBetweenIndexes(step, axis, rung.fromIndex, rung.toIndex))
            print rungTime
            #print step[axis]
            #print step['RungIndexes']
            for key in rungTime:
                y.append(sum(rungTime[key]))
                x.append('Rung ' + str(key))
        print [y, x]
        return {'yData': y, 'xData': x}
    
    def getStepAxisTotalTimeBetweenIndexes(self, step, axis, fromIndex, toIndex):
        time = 0
        print 'From', fromIndex, 'to', toIndex
        for idx, subStepTime in step[axis]:
            if idx >= fromIndex and idx <= toIndex:
                time += subStepTime
                print 'time:', time
        return time

    # Prints statistics for entire log
    def printStats(self):
        # individual step stats
        for bigStep in self.bigSteps:
            if bigStep['StepNumber'] == 0:
                print "Init:"
            else:
                print "Big step: ", bigStep['StepNumber']
     
            print "  Domain Decomp time:      ", 
            printListStats([num for idx, num in bigStep['DomainDecompTimes']])
            
            print "  LB time:                 ", 
            printListStats([num for idx, num in bigStep['BalancerTimes']])
            
            print "  Build trees time:        ", 
            printListStats([num for idx, num in bigStep['BuildTreesTimes']])
    
            print "  Gravity time:            ",
            printListStats([num for idx, num in bigStep['GravityTimes']])
     
            print "  Density time:            ",
            printListStats([num for idx, num in bigStep['DensityTimes']])
       
            print "  Mark Neighbor time:      ",
            printListStats([num for idx, num in bigStep['MarkNeighborTimes']])
            
            print "  Density of Neighbor time:",
            printListStats([num for idx, num in bigStep['DensityOfNeighborTimes']])
            
            print "  Pressure Gradient time:  ",
            printListStats([num for idx, num in bigStep['PressureGradientTimes']])
            
            print "  Big step time (r):       ", bigStep['TotalStepTime']
    
        # total stats
        print " - - - - - - - - - -"
        # subtract one for init
        print "Total Big steps: ", self.getNumBigSteps()
    
        print "Total Domain Decomp times:      ", 
        printListStats(self.getAllStepsKeywordTimes('DomainDecompTimes'))
            
        print "Total LB times:                 ", 
        printListStats(self.getAllStepsKeywordTimes('BalancerTimes'))
            
        print "Total Build trees times:        ", 
        printListStats(self.getAllStepsKeywordTimes('BuildTreesTimes'))
    
        print "Total Gravity times:            ",
        printListStats(self.getAllStepsKeywordTimes('GravityTimes'))
     
        print "Total Density times:            ",
        printListStats(self.getAllStepsKeywordTimes('DensityTimes'))
       
        print "Total Mark Neighbor times:      ",
        printListStats(self.getAllStepsKeywordTimes('MarkNeighborTimes'))
            
        print "Total Density of Neighbor times:",
        printListStats(self.getAllStepsKeywordTimes('DensityOfNeighborTimes'))
            
        print "Total Pressure Gradient times:  ",
        printListStats(self.getAllStepsKeywordTimes('PressureGradientTimes'))
        
        print "Total Big Step (r) times:       ",
        printListStats(self.getAllStepsTimes())
    
        return
    
    def getStepKeywordTimes(self, step, keyword):
        timeList = []
        for index, line in enumerate(step['LogLines']):
            if keyword in line:
                p = re.search(ChangaLog.RE_TOOK_SECONDS, line)
                if p is not None:
                    timeList.append([index, float(p.group())])
        return timeList
    
    # Returns the total time reported for a single big step ('Big step 1 took 10.0 seconds')
    def getStepTime(self, step):
        for line in step['LogLines']:
            if ChangaLog.RE_BIG_STEP_LINE in line:
                p = re.search(ChangaLog.RE_TOOK_SECONDS, line)
                if p is not None:
                    return float(p.group())
        return 0.0
    
    
    ## LOGFILE ALL STEPS TOTALS ##
        
    # Returns total balancer time for list of steps                
    def getAllStepsKeywordTimes(self, keyword):
        timeList = []
        for step in self.bigSteps:
            timeList.append(calcSum([num for idx, num in step[keyword]]))
        return timeList
 
    def getSubStepsKeywordTimes(self, keyword):
        timeList = []
        for step in self.bigSteps:
            for e in [num for idx, num in step[keyword]]:      # time is [1]
                timeList.append(e)
        return timeList
   
    def getAllStepsTimes(self):
        timeList = []
        for step in self.bigSteps:
            timeList.append(self.getStepTime(step))
        return timeList
    



    # Returns the number of big steps in the list of big steps
    # list bigSteps: list of big step dictionaries
    def getNumBigSteps(self):
        return len(self.bigSteps)

    def getNumSubSteps(self):
        steps = 0
        for step in self.bigSteps:
            for e in step['GravityTimes']:
                steps += 1
        return steps
    
    # Returns a list of file objects where each object is a Big step
    # list fullLog: list of lines in logfile
    def getBigStepsLines(self, fullLog):
        # bigSteps is a list of big steps
        bigStepsLines = []
        # bigStep is a list of lines in a single step
        bigStep = []
        
        # TODO: add in small big step 0 (which is only rungs 0 to x)

        for line in fullLog:
            bigStep.append(line)
            
            if ChangaLog.RE_BIG_STEP_LINE in line:
                bigStepsLines.append(tuple(bigStep))
                bigStep = []
            
    
            # "Done." signals the proper exit of ChaNGa
            if ChangaLog.RE_DONE in line:
                return bigStepsLines
        
        return bigStepsLines
    
    def printAxesList(self):
        print "Axes: ", ChangaLog.AXES_LIST
        return
  
    
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
    

def createPlot(dataY, dataX, axisY, axisX, connect):
    if connect:
        plot_line_style = '-'
    else:
        plot_line_style = "None"

    py.plot(dataX, dataY, marker='o', ms=5.0, linestyle=plot_line_style, label=axisY)
    leg = py.legend()
    leg.draggable()
    py.xlabel(axisX)
    py.ylabel('time (s)')

    # Set X axis tick labels as rungs
    py.xticks(np.arange(len(dataX)), np.arange(10))
    print zip(dataX, dataY)
  
    py.draw()
    py.show()
    
    return

def createBarPlot(plotList, dataY, dataX, axisY, axisX):
    colorList = ['b', 'g', 'y', 'r', 'm', 'c', 'k']
    width = 0.35
    x = np.arange(len(dataY))
    thisColor = colorList[len(plotList)%len(colorList)]
    py.bar(x+(width-0.1)*len(plotList), dataY, width, color=thisColor, label=axisY)
    py.xticks(x, dataX, rotation=30, size='small')
    py.xlabel(axisX)
    py.ylabel('time (s)')
    leg = py.legend()
    leg.draggable()
    plotList.append([dataY, dataX, axisY, axisX])
    py.draw()
    py.show()
#    py.close()
    

#def getCommand(bigSteps):
#    print
#    print
#    printAxesList()
#    print
#    print "Ready to plot."
#    ri = ""
#    plotNum = 0
#    while True:
#        
#        ri = raw_input("Choose your axes (y, x) or type exit: ")
#        if (ri == 'exit') or (ri == 'quit'):
#            break
#        try:
#            yAxis, xAxis = ri.split(',')
#        except ValueError: 
#            # TODO: loop on bad input
#            print "Error: Bad formatting"
#        else: 
#            yAxis = yAxis.strip()
#            xAxis = xAxis.strip()
#   
#            if (xAxis not in ChangaLog.AXES_LIST) or (yAxis not in ChangaLog.AXES_LIST):
#                print "Error: Unrecognized axis"
#            else:
#                createPlot(yAxis, xAxis, bigSteps, plotNum)
#                plotNum += 1
#    return

## CALCULATIONS ##

# Prints a line with stats about the numbers in the list
#   min, max, avg, sigma
# list : a list of floats
def printListStats(flist):
    if len(flist) == 0:
        print "No data"
        return
    else:
        print calcSum(flist),
        print "avg:", calcAverage(flist),
        print "min:", calcMin(flist),
        print "max:", calcMax(flist),
        print "std:", calcStd(flist)

# Returns average of a list of floats
def calcAverage(flist):
    if not list:
        return 0.0
    return np.mean(flist)

def calcSum(flist):
    if not list:
        return 0.0
    return sum(flist)

def calcMin(flist):
    if not list:
        return 0.0
    return min(flist)

def calcMax(flist):
    if not list:
        return 0.0
    return max(flist)

def calcStd(flist):
    if not list:
        return 0.0
    return np.std(flist)

#### MAIN ####

def main(*args):
    app = QApplication(sys.argv)
    mw = MainWindow()
    mw.show()
    app.exec_()

   # # get logfile names list from command line
   # logFiles = args[1:]

   # for logFile in logFiles:
   #     try:
   #         f = open(logFile, 'r')
   #     except IOError:
   #         print 'Cannot open', logFile
   #     else:
   #         printTitle(f)
   #         fullLog = f.readlines()
   #         f.close()
   #         
   #         parseLog(fullLog)


if __name__ == '__main__':
    sys.exit(main(*sys.argv))
