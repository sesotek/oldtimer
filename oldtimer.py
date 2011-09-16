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

import numpy
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
            # Make a new textEdit for each opened log
            self.textEdit1.insertPlainText(''.join(logLines))


    def updateAxes(self):
        self.comboYAxis.clear()
        self.comboXAxis.clear()
        self.comboYLog.clear()
        self.comboXLog.clear()
        
        for log in self.openLogs:
            self.comboYLog.addItem(log.logname)
            self.comboXLog.addItem(log.logname)
        
        self.comboYAxis.addItems(ChangaLog.AXES_LIST)
        self.comboXAxis.addItems(ChangaLog.AXES_LIST)
        self.comboYResolution.addItems(ChangaLog.RESOLUTION_LIST)
        self.comboXResolution.addItems(ChangaLog.RESOLUTION_LIST)
    

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
        pointsY = [] 
        pointsX = []
        resolutionY = self.comboYResolution.currentText()
        resolutionX = self.comboXResolution.currentText()
        for log in self.openLogs:
            if log.logname == self.comboYLog.currentText():
                pointsY = log.logobject.getData(self.comboYAxis.currentText(), resolutionY)
            if log.logname == self.comboXLog.currentText():
                pointsX = log.logobject.getData(self.comboYAxis.currentText(), resolutionX)

        createPlot(pointsY, pointsX, 'y axis', 'x axis')


#### end GUI ####
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
    
    # List of Axes
    AXES_LIST = ['Step', 'TotalStepTime', 'DomainDecompTimes', 'BalancerTimes', 'BuildTreesTimes', 'GravityTimes', 'DensityTimes', 'MarkNeighborTimes', 'DensityOfNeighborTimes', 'PressureGradientTimes']

    # List of resolutions
    RESOLUTION_LIST = ['Big step', 'Sub step']

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
            bigStep['StepNumber'] = index
            bigStep['TotalStepTime'] = self.getStepTime(bigStep)
            bigStep['DomainDecompTimes'] = self.getStepKeywordTimes(bigStep, ChangaLog.RE_DOMAIN_DECOMP)
            bigStep['BalancerTimes'] = self.getStepKeywordTimes(bigStep, ChangaLog.RE_BALANCER)
            bigStep['BuildTreesTimes'] = self.getStepKeywordTimes(bigStep, ChangaLog.RE_BUILD_TREES)
            bigStep['GravityTimes'] = self.getStepKeywordTimes(bigStep, ChangaLog.RE_GRAVITY)
            bigStep['DensityTimes'] = self.getStepKeywordTimes(bigStep, ChangaLog.RE_DENSITY)
            bigStep['MarkNeighborTimes'] = self.getStepKeywordTimes(bigStep, ChangaLog.RE_MARK_NEIGHBOR)
            bigStep['DensityOfNeighborTimes'] = self.getStepKeywordTimes(bigStep, ChangaLog.RE_DENSITY_OF_NEIGHBOR)
            bigStep['PressureGradientTimes'] = self.getStepKeywordTimes(bigStep, ChangaLog.RE_PRESSURE_GRADIENT)
        
#        self.printStats()
    
        #self.getCommand(bigSteps)
    
        return

    # Returns a list of axis names that this log recognizes as plottable
    def getAxes(self):
        return ChangaLog.AXES_LIST

    # Returns a list of data points for this log for the specified axis
    def getData(self, axis, resolution):
#    if yAxis == 'Step':
#        yData = range(len(bigSteps))
#    elif yAxis == 'TotalStepTime':
#        yData = getAllStepsTimes(bigSteps)
#    else:
#        yData = getAllStepsKeywordTimes(bigSteps, yAxis)
       if axis == 'Step':
           if resolution == 'Big step':
               return range(self.getNumBigSteps())
           if resolution == 'Sub step':
               return self.getNumSubSteps()
       return range(100)

    # Prints statistics for entire log
    def printStats(self):
        # individual step stats
        for bigStep in self.bigSteps:
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
        print "Total Big steps: ", self.getNumBigSteps(self.bigSteps) - 1
    
        print "Total Domain Decomp times:      ", 
        printListStats(self.getAllStepsKeywordTimes(self.bigSteps, 'DomainDecompTimes'))
            
        print "Total LB times:                 ", 
        printListStats(self.getAllStepsKeywordTimes(self.bigSteps, 'BalancerTimes'))
            
        print "Total Build trees times:        ", 
        printListStats(self.getAllStepsKeywordTimes(self.bigSteps, 'BuildTreesTimes'))
    
        print "Total Gravity times:            ",
        printListStats(self.getAllStepsKeywordTimes(self.bigSteps, 'GravityTimes'))
     
        print "Total Density times:            ",
        printListStats(self.getAllStepsKeywordTimes(self.bigSteps, 'DensityTimes'))
       
        print "Total Mark Neighbor times:      ",
        printListStats(self.getAllStepsKeywordTimes(self.bigSteps, 'MarkNeighborTimes'))
            
        print "Total Density of Neighbor times:",
        printListStats(self.getAllStepsKeywordTimes(self.bigSteps, 'DensityOfNeighborTimes'))
            
        print "Total Pressure Gradient times:  ",
        printListStats(self.getAllStepsKeywordTimes(self.bigSteps, 'PressureGradientTimes'))
        
        print "Total Big Step (r) times:       ",
        printListStats(self.getAllStepsTimes(self.bigSteps))
    
        return
    
    def getStepKeywordTimes(self, step, keyword):
        timeList = []
        for line in step['LogLines']:
            if keyword in line:
                p = re.search(ChangaLog.RE_TOOK_SECONDS, line)
                if p is not None:
                    timeList.append(float(p.group()))
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
    def getAllStepsKeywordTimes(self, bigSteps, keyword):
        timeList = []
        for step in bigSteps:
            timeList.append(calcSum(step[keyword]))
        return timeList
    
    def getAllStepsTimes(self, bigSteps):
        timeList = []
        for step in bigSteps:
            timeList.append(self.getStepTime(step))
        return timeList
    



    # Returns the number of big steps in the list of big steps
    # list bigSteps: list of big step dictionaries
    def getNumBigSteps(self):
        return len(self.bigSteps)
    
    # Returns a list of file objects where each object is a Big step
    # list fullLog: list of lines in logfile
    def getBigStepsLines(self, fullLog):
        # bigSteps is a list of big steps
        bigStepsLines = []
        # bigStep is a list of lines in a single step
        bigStep = []
        stepNum = 0
        # get init lines
        for line in fullLog:
            # find the rung distribution which marks the beginning of each big step
            if ChangaLog.RE_RUNG_DISTRIBUTION in line:
                bigStepsLines.append(tuple(bigStep))
                bigStep = []
            
            bigStep.append(line)
    
            # "Done." signals the proper exit of ChaNGa
            if ChangaLog.RE_DONE in line:
                bigStepsLines.append(tuple(bigStep))
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
    
    

def createPlot(dataY, dataX, axisY, axisX):
    colorList = ['r', 'g', 'b', 'c', 'm', 'y', 'k']
#    print  yAxis, "is", colorList[plotNum%7]
    plot_line_style = "None"

#    if yAxis == 'Step':
#        yData = range(len(bigSteps))
#    elif yAxis == 'TotalStepTime':
#        yData = getAllStepsTimes(bigSteps)
#    else:
#        yData = getAllStepsKeywordTimes(bigSteps, yAxis)
#    
#    if xAxis == 'Step':
#        xData = range(len(bigSteps))
#        plot_line_style = '-'
#    elif xAxis == 'TotalStepTime':
#        xData = getAllStepsTimes(bigSteps)
#    else:
#        xData = getAllStepsKeywordTimes(bigSteps, xAxis)

#    plot = py.plot(xData, yData, color=colorList[plotNum%7], marker='o', ms=5.0, linestyle=plot_line_style)
    #py.close()


    plot = py.plot(dataX, dataY, marker='o', ms=5.0, linestyle=plot_line_style)
    #leg = py.DraggableLegend([plot], [yAxis])
    #leg.draggable()
    py.xlabel(axisX)
    py.ylabel(axisY)
    py.draw()
   # py.show()
    
    return
    
    

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
    return numpy.mean(flist)

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
    return numpy.std(flist)

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
