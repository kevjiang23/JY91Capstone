import os
import unittest
import logging
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin
from slicer.util import getNode, getNodesByClass, getNodes, resetSliceViews
import numpy as np
import time
import math

#
# CalculateResults
#

class CalculateResults(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "CalculateResults"  # TODO: make this more human readable by adding spaces
    self.parent.categories = ["Mandibular Reconstruction"]  # TODO: set categories (folders where the module shows up in the module selector)
    self.parent.dependencies = []  # TODO: add here list of module names that this module requires
    self.parent.contributors = ["M M Stewart UBC"]  # TODO: replace with "Firstname Lastname (Organization)"
    # TODO: update with short description of the module and a link to online module documentation
    self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
See more information in <a href="https://github.com/organization/projectname#CalculateResults">module documentation</a>.
"""
    # TODO: replace with organization, grant and thanks
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
"""

    # Additional initialization step after application startup is complete
    # slicer.app.connect("startupCompleted()", registerSampleData)


#-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-#
#---------------------------------------------------------------------------------------------------------------------------------#
# CalculateResultsWidget
#---------------------------------------------------------------------------------------------------------------------------------#
#-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-#
class CalculateResultsWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent=None):
    ScriptedLoadableModuleWidget.__init__(self, parent)
    VTKObservationMixin.__init__(self)  # needed for parameter node observation
    self.logic = None

  def setup(self):
    ScriptedLoadableModuleWidget.setup(self)
    self.logic = CalculateResultsLogic()

  #---------------------------------------------------------------------------------------------------------------------------------#
  # Parameters Area
  #---------------------------------------------------------------------------------------------------------------------------------#

    #### Place Fidutials
    self.fidsCollapsibleButton = ctk.ctkCollapsibleButton()
    self.fidsCollapsibleButton.text = "Place Fidutials"
    self.layout.addWidget(self.fidsCollapsibleButton)

    fidsFormLayout = qt.QFormLayout(self.fidsCollapsibleButton)
    self.linesA = qt.QLabel("--------------------------------------------------------------------------------------------------------------------------")
    self.linesB = qt.QLabel("--------------------------------------------------------------------------------------------------------------------------")
    self.linesC = qt.QLabel("--------------------------------------------------------------------------------------------------------------------------")
    self.linesD = qt.QLabel("--------------------------------------------------------------------------------------------------------------------------")
    self.linesE = qt.QLabel("--------------------------------------------------------------------------------------------------------------------------")
    self.linesF = qt.QLabel("--------------------------------------------------------------------------------------------------------------------------")
    self.linesG = qt.QLabel("--------------------------------------------------------------------------------------------------------------------------")
    self.linesH = qt.QLabel("--------------------------------------------------------------------------------------------------------------------------")
    self.linesI = qt.QLabel("--------------------------------------------------------------------------------------------------------------------------")
    self.linesJ = qt.QLabel("--------------------------------------------------------------------------------------------------------------------------")
    self.linesK = qt.QLabel("--------------------------------------------------------------------------------------------------------------------------")
    self.linesL = qt.QLabel("--------------------------------------------------------------------------------------------------------------------------")
    self.linesM = qt.QLabel("--------------------------------------------------------------------------------------------------------------------------")
    self.linesN = qt.QLabel("--------------------------------------------------------------------------------------------------------------------------")
    self.linesO = qt.QLabel("--------------------------------------------------------------------------------------------------------------------------")
    self.linesP = qt.QLabel("--------------------------------------------------------------------------------------------------------------------------")
    self.linesQ = qt.QLabel("--------------------------------------------------------------------------------------------------------------------------")
    self.linesR = qt.QLabel("--------------------------------------------------------------------------------------------------------------------------")

    # Condyle fids Plan
    fidsFormLayout.addRow(self.linesA)

    self.conFidPButton = qt.QPushButton("Place PLAN Condyle Fidutial")
    self.conFidPButton.toolTip = "Place 1 fidutial on each condyle."
    self.conFidPButton.enabled = True
    fidsFormLayout.addRow(self.conFidPButton)

    self.conRFidPButton = qt.QPushButton("Delete ALL Plan Condyle Fidutials")
    self.conRFidPButton.toolTip = "This will delete all plan condyl fiducials."
    self.conRFidPButton.enabled = True
    fidsFormLayout.addRow(self.conRFidPButton)

    self.conFidPsCountLable = qt.QLabel("Number of Fidutials Placed:")
    self.conFidPsCount = qt.QLabel("0")
    self.conFidPsCountNote = qt.QLabel("6 Points Required")
    fidsFormLayout.addRow(self.conFidPsCountLable, self.conFidPsCount)
    fidsFormLayout.addRow(self.conFidPsCountNote)

    fidsFormLayout.addRow(self.linesB)

    # Projected fid Plan
    self.proFidPButton = qt.QPushButton("Place PLAN Projection Fidutial")
    self.proFidPButton.toolTip = "Place 1 fidutial on the most anterior point on the reconstruction."
    self.proFidPButton.enabled = True
    fidsFormLayout.addRow(self.proFidPButton)

    self.proRFidPButton = qt.QPushButton("Delete Plan Projection Fidutial")
    self.proRFidPButton.toolTip = "This will delete all plan projection fiducials."
    self.proRFidPButton.enabled = True
    fidsFormLayout.addRow(self.proRFidPButton)

    self.proFidPsCountLable = qt.QLabel("Number of Fidutials Placed:")
    self.proFidPsCount = qt.QLabel("0")
    self.proFidPsCountNote = qt.QLabel("3 Points Required")
    fidsFormLayout.addRow(self.proFidPsCountLable, self.proFidPsCount)
    fidsFormLayout.addRow(self.proFidPsCountNote)

    fidsFormLayout.addRow(self.linesC)

    # Angle fids Plan
    self.angFidPButton = qt.QPushButton("Place PLAN Angle Fidutial")
    self.angFidPButton.toolTip = "Place 1 fidutial on each mandible angel."
    self.angFidPButton.enabled = True
    fidsFormLayout.addRow(self.angFidPButton)

    self.angRFidPButton = qt.QPushButton("Delete ALL Plan Angle Fidutials")
    self.angRFidPButton.toolTip = "This will delete all plan angle fiducials."
    self.angRFidPButton.enabled = True
    fidsFormLayout.addRow(self.angRFidPButton)

    self.angFidPsCountLable = qt.QLabel("Number of Fidutials Placed:")
    self.angFidPsCount = qt.QLabel("0")
    self.angFidPsCountNote = qt.QLabel("6 Points Required")
    fidsFormLayout.addRow(self.angFidPsCountLable, self.angFidPsCount)
    fidsFormLayout.addRow(self.angFidPsCountNote)

    fidsFormLayout.addRow(self.linesP)

    # Condyle fids ACtual CT
    self.conFidAButton = qt.QPushButton("Place CT Condyle Fidutial")
    self.conFidAButton.toolTip = "Place 1 fidutial on each condyle."
    self.conFidAButton.enabled = True
    fidsFormLayout.addRow(self.conFidAButton)

    self.conRFidAButton = qt.QPushButton("Delete ALL CT Condyle Fidutials")
    self.conRFidAButton.toolTip = "This will delete all CT condyl fiducials."
    self.conRFidAButton.enabled = True
    fidsFormLayout.addRow(self.conRFidAButton)

    self.conFidAsCountLable = qt.QLabel("Number of Fidutials Placed:")
    self.conFidAsCount = qt.QLabel("0")
    self.conFidAsCountNote = qt.QLabel("6 Points Required")
    fidsFormLayout.addRow(self.conFidAsCountLable, self.conFidAsCount)
    fidsFormLayout.addRow(self.conFidAsCountNote)

    fidsFormLayout.addRow(self.linesK)

    # Projected fid Actual CT
    self.proFidAButton = qt.QPushButton("Place CT Projection Fidutial")
    self.proFidAButton.toolTip = "Place 1 fidutial on the most anterior point on the reconstruction."
    self.proFidAButton.enabled = True
    fidsFormLayout.addRow(self.proFidAButton)

    self.proRFidAButton = qt.QPushButton("Delete CT Projection Fidutial")
    self.proRFidAButton.toolTip = "This will delete all CT projection fiducials."
    self.proRFidAButton.enabled = True
    fidsFormLayout.addRow(self.proRFidAButton)

    self.proFidAsCountLable = qt.QLabel("Number of Fidutials Placed:")
    self.proFidAsCount = qt.QLabel("0")
    self.proFidAsCountNote = qt.QLabel("3 Points Required")
    fidsFormLayout.addRow(self.proFidAsCountLable, self.proFidAsCount)
    fidsFormLayout.addRow(self.proFidAsCountNote)

    fidsFormLayout.addRow(self.linesL)

    # Angle fids ACtual CT
    self.angFidAButton = qt.QPushButton("Place CT Angle Fidutial")
    self.angFidAButton.toolTip = "Place 1 fidutial on each mandible angle."
    self.angFidAButton.enabled = True
    fidsFormLayout.addRow(self.angFidAButton)

    self.angRFidAButton = qt.QPushButton("Delete ALL CT Angle Fidutials")
    self.angRFidAButton.toolTip = "This will delete all CT angle fiducials."
    self.angRFidAButton.enabled = True
    fidsFormLayout.addRow(self.angRFidAButton)

    self.angFidAsCountLable = qt.QLabel("Number of Fidutials Placed:")
    self.angFidAsCount = qt.QLabel("0")
    self.angFidAsCountNote = qt.QLabel("6 Points Required")
    fidsFormLayout.addRow(self.angFidAsCountLable, self.angFidAsCount)
    fidsFormLayout.addRow(self.angFidAsCountNote)

    fidsFormLayout.addRow(self.linesQ)

    # Fids for plate/mandible gap
    self.plateFidButton = qt.QPushButton("Place Plate Fidutial")
    self.plateFidButton.toolTip = "Place 10 fidutials along the inside surface of the plate."
    self.plateFidButton.enabled = True
    fidsFormLayout.addRow(self.plateFidButton)

    self.plateRFidButton = qt.QPushButton("Delete ALL Plate Fidutials")
    self.plateRFidButton.toolTip = "This will delete all condyl fiducials."
    self.plateRFidButton.enabled = True
    fidsFormLayout.addRow(self.plateRFidButton)

    self.plateFidsCountLable = qt.QLabel("Number of Fidutials Placed:")
    self.plateFidsCount = qt.QLabel("0")
    self.plateFidsCountNote = qt.QLabel("10 Points Required")
    fidsFormLayout.addRow(self.plateFidsCountLable, self.plateFidsCount)
    fidsFormLayout.addRow(self.plateFidsCountNote)

    fidsFormLayout.addRow(self.linesD)

    #### Calculate accuracies
    self.calcButton = qt.QPushButton("Calculate Accuricies")
    self.calcButton.toolTip = "Press here to calculate all accuracy measurments - results will be displayed below."
    self.calcButton.enabled = True
    fidsFormLayout.addRow(self.calcButton)

    fidsFormLayout.addRow(self.linesE)

    #### Accuracies Results
    # Width
    self.widthPAcuLable = qt.QLabel("Plan Intercondyle Width:")
    self.widthPAcu = qt.QLabel("0")
    fidsFormLayout.addRow(self.widthPAcuLable, self.widthPAcu)

    self.widthAAcuLable = qt.QLabel("Actual Intercondyle Width:")
    self.widthAAcu = qt.QLabel("0")
    fidsFormLayout.addRow(self.widthAAcuLable, self.widthAAcu)

    self.widthDAcuLable = qt.QLabel("Differenece in Intercondyle Width:")
    self.widthDAcu = qt.QLabel("0")
    fidsFormLayout.addRow(self.widthDAcuLable, self.widthDAcu)

    fidsFormLayout.addRow(self.linesN)

    self.AwidthPAcuLable = qt.QLabel("Plan Interangle Width:")
    self.AwidthPAcu = qt.QLabel("0")
    fidsFormLayout.addRow(self.AwidthPAcuLable, self.AwidthPAcu)

    self.AwidthAAcuLable = qt.QLabel("Actual Interangle Width:")
    self.AwidthAAcu = qt.QLabel("0")
    fidsFormLayout.addRow(self.AwidthAAcuLable, self.AwidthAAcu)

    self.AwidthDAcuLable = qt.QLabel("Differenece in Interangle Width:")
    self.AwidthDAcu = qt.QLabel("0")
    fidsFormLayout.addRow(self.AwidthDAcuLable, self.AwidthDAcu)

    fidsFormLayout.addRow(self.linesR)

    # Projection
    self.projPAcuLable = qt.QLabel("Plan Mandible Projection:")
    self.projPAcu = qt.QLabel("0")
    fidsFormLayout.addRow(self.projPAcuLable, self.projPAcu)

    self.projAAcuLable = qt.QLabel("Actual Mandible Projection:")
    self.projAAcu = qt.QLabel("0")
    fidsFormLayout.addRow(self.projAAcuLable, self.projAAcu)

    self.projDAcuLable = qt.QLabel("Difference in Mandible Projection:")
    self.projDAcu = qt.QLabel("0")
    fidsFormLayout.addRow(self.projDAcuLable, self.projDAcu)

    fidsFormLayout.addRow(self.linesO)

    # Registration accuracy
    self.regAcuLable = qt.QLabel("Fidutial Registration Accuracy:")
    self.regAcu = qt.QLabel("0")
    # self.regAcuNote = qt.QLabel("Note??")
    fidsFormLayout.addRow(self.regAcuLable, self.regAcu)
    # fidsFormLayout.addRow(self.regAcuNote)

    fidsFormLayout.addRow(self.linesF)

    # Model to Model accuracy
    self.modAcuLable = qt.QLabel("ICP Accuracy:")
    self.modAcu = qt.QLabel("0")
    # self.modAcuNote = qt.QLabel("Note??")
    fidsFormLayout.addRow(self.modAcuLable, self.modAcu)
    # fidsFormLayout.addRow(self.modAcuNote)

    fidsFormLayout.addRow(self.linesM)

    #Dice Score
    self.diceAcuLable = qt.QLabel("Dice Score:")
    self.diceAcu = qt.QLabel("0")
    # self.diceAcuNote = qt.QLabel("Note??")
    fidsFormLayout.addRow(self.diceAcuLable, self.diceAcu)
    # fidsFormLayout.addRow(self.diceAcuNote)

    fidsFormLayout.addRow(self.linesG)

    #95 Hof distance
    self.hofAcuLable = qt.QLabel("Hausdorff Distance:")
    self.hofAcu = qt.QLabel("0")
    # self.hofAcuNote = qt.QLabel("Note??")
    fidsFormLayout.addRow(self.hofAcuLable, self.hofAcu)
    # fidsFormLayout.addRow(self.hofAcuNote)

    fidsFormLayout.addRow(self.linesH)

    #Average Plate Distance
    self.plateAcuLable = qt.QLabel("Average Plate Distance:")
    self.plateAcu = qt.QLabel("0")
    self.plateAcuNote = qt.QLabel("Average Distance Between Plate and Recon Surface")
    fidsFormLayout.addRow(self.plateAcuLable, self.plateAcu)
    fidsFormLayout.addRow(self.plateAcuNote)

    fidsFormLayout.addRow(self.linesI)

    #Plate distance range
    self.min_plateAcuLable = qt.QLabel("Minimum Plate Distance:")
    self.min_plateAcu = qt.QLabel("0")
    # self.min_plateAcuNote = qt.QLabel("Note??")
    fidsFormLayout.addRow(self.min_plateAcuLable, self.min_plateAcu)
    # fidsFormLayout.addRow(self.min_plateAcuNote)

    self.max_plateAcuLable = qt.QLabel("Maximum Plate Distance:")
    self.max_plateAcu = qt.QLabel("0")
    # self.max_plateAcuNote = qt.QLabel("Note??")
    fidsFormLayout.addRow(self.max_plateAcuLable, self.max_plateAcu)
    # fidsFormLayout.addRow(self.max_plateAcuNote)

    fidsFormLayout.addRow(self.linesJ)

  #---------------------------------------------------------------------------------------------------------------------------------#
  # Connections
  #---------------------------------------------------------------------------------------------------------------------------------#
    self.conFidPButton.connect('clicked(bool)', self.onConFidPButton)
    self.conRFidPButton.connect('clicked(bool)', self.onConRFidPButton)
    self.conFidAButton.connect('clicked(bool)', self.onConFidAButton)
    self.conRFidAButton.connect('clicked(bool)', self.onConRFidAButton)
    self.proFidPButton.connect('clicked(bool)', self.onProFidPButton)
    self.proRFidPButton.connect('clicked(bool)', self.onProRFidPButton)
    self.proFidAButton.connect('clicked(bool)', self.onProFidAButton)
    self.proRFidAButton.connect('clicked(bool)', self.onProRFidAButton)
    self.angFidPButton.connect('clicked(bool)', self.onAngFidPButton)
    self.angRFidPButton.connect('clicked(bool)', self.onAngRFidPButton)
    self.angFidAButton.connect('clicked(bool)', self.onAngFidAButton)
    self.angRFidAButton.connect('clicked(bool)', self.onAngRFidAButton)
    self.plateFidButton.connect('clicked(bool)', self.onPlateFidButton)
    self.plateRFidButton.connect('clicked(bool)', self.onPlateRFidButton)
    self.calcButton.connect('clicked(bool)', self.onCalcButton)

    self.layout.addStretch(1)

  def cleanup(self):
    self.removeObservers()

  # def exit(self):
  #   self.removeObserver()

  #---------------------------------------------------------------------------------------------------------------------------------#
  # Button Actions (connect button to relevent logic)
  #---------------------------------------------------------------------------------------------------------------------------------#
  def onConFidPButton (self):
      try:
          Fid = getNode('ConFidPlan')
      except:
          Fid = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'ConFidPlan')
      self.logic.runPlaceFid(Fid)
      self.conFidPsCount.text = str(Fid.GetNumberOfFiducials())

  def onConRFidPButton (self):
      try:
          Fid = getNode('ConFidPlan')
      except:
          Fid = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'ConFidPlan')
      self.logic.runDeleteFid(Fid)
      self.conFidPsCount.text = str(Fid.GetNumberOfFiducials())

  def onConFidAButton (self):
      try:
          Fid = getNode('ConFidActual')
      except:
          Fid = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'ConFidActual')
      self.logic.runPlaceFid(Fid)
      self.conFidAsCount.text = str(Fid.GetNumberOfFiducials())

  def onConRFidAButton (self):
      try:
          Fid = getNode('ConFidActual')
      except:
          Fid = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'ConFidActual')
      self.logic.runDeleteFid(Fid)
      self.conFidAsCount.text = str(Fid.GetNumberOfFiducials())

  def onProFidPButton (self):
      try:
          Fid = getNode('ProFidPlan')
      except:
          Fid = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'ProFidPlan')
      self.logic.runPlaceFid(Fid)
      self.proFidPsCount.text = str(Fid.GetNumberOfFiducials())

  def onProRFidPButton (self):
      try:
          Fid = getNode('ProFidPlan')
      except:
          Fid = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'ProFidPlan')
      self.logic.runDeleteFid(Fid)
      self.proFidPsCount.text = str(Fid.GetNumberOfFiducials())

  def onProFidAButton (self):
      try:
          Fid = getNode('ProFidActual')
      except:
          Fid = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'ProFidActual')
      self.logic.runPlaceFid(Fid)
      self.proFidAsCount.text = str(Fid.GetNumberOfFiducials())

  def onProRFidAButton (self):
      try:
          Fid = getNode('ProFidActual')
      except:
          Fid = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'ProFidActual')
      self.logic.runDeleteFid(Fid)
      self.proFidAsCount.text = str(Fid.GetNumberOfFiducials())

  def onPlateFidButton (self):
      try:
          Fid = getNode('PlateFid')
      except:
          Fid = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'PlateFid')
      self.logic.runPlaceFid(Fid)
      self.plateFidsCount.text = str(Fid.GetNumberOfFiducials())

  def onAngFidPButton (self):
      try:
          Fid = getNode('AngFidPlan')
      except:
          Fid = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'AngFidPlan')
      self.logic.runPlaceFid(Fid)
      self.angFidPsCount.text = str(Fid.GetNumberOfFiducials())

  def onAngRFidPButton (self):
      try:
          Fid = getNode('AngFidPlan')
      except:
          Fid = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'AngFidPlan')
      self.logic.runDeleteFid(Fid)
      self.angFidPsCount.text = str(Fid.GetNumberOfFiducials())

  def onAngFidAButton (self):
      try:
          Fid = getNode('AngFidActual')
      except:
          Fid = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'AngFidActual')
      self.logic.runPlaceFid(Fid)
      self.angFidAsCount.text = str(Fid.GetNumberOfFiducials())

  def onAngRFidAButton (self):
      try:
          Fid = getNode('AngFidActual')
      except:
          Fid = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'AngFidActual')
      self.logic.runDeleteFid(Fid)
      self.angFidAsCount.text = str(Fid.GetNumberOfFiducials())

  def onPlateRFidButton (self):
      try:
          Fid = getNode('PlateFid')
      except:
          Fid = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'PlateFid')
      self.logic.runDeleteFid(Fid)
      self.plateFidsCount.text = str(Fid.GetNumberOfFiducials())

  def onCalcButton (self):
      results = self.logic.runCalculate()
      self.widthPAcu.text = str(round(results[0],2)) + " mm"
      self.widthAAcu.text = str(round(results[1],2)) + " mm"
      self.widthDAcu.text = str(round(results[2],2)) + " mm"
      self.projPAcu.text = str(round(results[3],2)) + " mm"
      self.projAAcu.text = str(round(results[4],2)) + " mm"
      self.projDAcu.text = str(round(results[5],2)) + " mm"
      self.regAcu.text = str(round(results[6],2)) + " mm"
      self.modAcu.text = str(round(results[7],2)) + " mm"
      self.diceAcu.text = str(round(results[8],2))
      self.hofAcu.text = str(round(results[9],2)) + " mm"
      self.plateAcu.text = str(round(results[10],2)) + " mm"
      self.min_plateAcu.text = str(round(results[11],2)) + " mm"
      self.max_plateAcu.text = str(round(results[12],2)) + " mm"
      self.AwidthPAcu.text = str(round(results[13],2)) + " mm"
      self.AwidthAAcu.text = str(round(results[14],2)) + " mm"
      self.AwidthDAcu.text = str(round(results[15],2)) + " mm"


#-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-#
#---------------------------------------------------------------------------------------------------------------------------------#
# CalculateResultsLogic
#---------------------------------------------------------------------------------------------------------------------------------#
#-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-X-#

class CalculateResultsLogic(ScriptedLoadableModuleLogic):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self):
    """
    Called when the logic class is instantiated. Can be used for initializing member variables.
    """
    ScriptedLoadableModuleLogic.__init__(self)
    self.markupsLogic = slicer.modules.markups.logic()
    self.fidutialRegLogic = slicer.modules.fiducialregistrationwizard.logic()

  def runPlaceFid(self, Fid):
      self.markupsLogic.SetActiveListID(Fid)
      placeModePersistence = 0
      self.markupsLogic.StartPlaceMode(placeModePersistence)
      Fid.SetNthControlPointLocked((Fid.GetNumberOfFiducials())-1,1)

  def runDeleteFid(self, Fid):
      self.markupsLogic.SetActiveListID(Fid)
      Fid.RemoveAllMarkups()

  def runCalculate(self):
      #copy plan model so w ecan move to registered location perminantly
      self.mandP = getNode('MandiblePlan')
      shNode = slicer.vtkMRMLSubjectHierarchyNode.GetSubjectHierarchyNode(slicer.mrmlScene)
      itemIDToClone = shNode.GetItemByDataNode(self.mandP)
      clonedItemID = slicer.modules.subjecthierarchy.logic().CloneSubjectHierarchyItem(shNode, itemIDToClone)
      clonedNode = shNode.GetItemDataNode(clonedItemID)
      #create and call nessasry nodes
      self.mandP = getNode('MandiblePlan Copy')
      self.mandA = getNode('MandibleActual')
      self.ConFidPlan = getNode('ConFidPlan')
      self.ConFidActual = getNode('ConFidActual')
      self.ProFidPlan = getNode('ProFidPlan')
      self.ProFidActual = getNode('ProFidActual')
      self.AngFidPlan = getNode('AngFidPlan')
      self.AngFidActual = getNode('AngFidActual')
      self.PlateFid = getNode('PlateFid')
      self.reg = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLFiducialRegistrationWizardNode', 'ICP_Reg')
      self.icpTrans = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode', 'ICP_Transform')
      self.modTrans = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode', 'ModelToModel_Transform')
      self.planFid = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'PlanRegFids')
      self.actFid = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'ActualRegFids')
      point = [0,0,0]

      #calculate average points
      self.point = self.runAveragePoint(self.ConFidPlan, 0, 0)
      self.ConFidPlan.AddFiducial(self.point[0],self.point[1],self.point[2])
      self.point = self.runAveragePoint(self.ConFidPlan, 1, 0)
      self.ConFidPlan.AddFiducial(self.point[0],self.point[1],self.point[2])
      self.point = self.runAveragePoint(self.ConFidActual, 0, 0)
      self.ConFidActual.AddFiducial(self.point[0],self.point[1],self.point[2])
      self.point = self.runAveragePoint(self.ConFidActual, 1, 0)
      self.ConFidActual.AddFiducial(self.point[0],self.point[1],self.point[2])
      self.point = self.runAveragePoint(self.ProFidPlan, 0, 1)
      self.ProFidPlan.AddFiducial(self.point[0],self.point[1],self.point[2])
      self.point = self.runAveragePoint(self.ProFidActual, 0, 1)
      self.ProFidActual.AddFiducial(self.point[0],self.point[1],self.point[2])
      self.point = self.runAveragePoint(self.AngFidPlan, 0, 0)
      self.AngFidPlan.AddFiducial(self.point[0],self.point[1],self.point[2])
      self.point = self.runAveragePoint(self.AngFidPlan, 1, 0)
      self.AngFidPlan.AddFiducial(self.point[0],self.point[1],self.point[2])
      self.point = self.runAveragePoint(self.AngFidActual, 0, 0)
      self.AngFidActual.AddFiducial(self.point[0],self.point[1],self.point[2])
      self.point = self.runAveragePoint(self.AngFidActual, 1, 0)
      self.AngFidActual.AddFiducial(self.point[0],self.point[1],self.point[2])

      self.ConFidPlan.GetNthFiducialPosition(6,point)
      self.pointA = np.array(point)
      self.ConFidPlan.GetNthFiducialPosition(7,point)
      self.pointB = np.array(point)
      self.ConFidActual.GetNthFiducialPosition(6,point)
      self.pointD = np.array(point)
      self.ConFidActual.GetNthFiducialPosition(7,point)
      self.pointE = np.array(point)
      self.ProFidPlan.GetNthFiducialPosition(3,point)
      self.pointC = np.array(point)
      self.ProFidActual.GetNthFiducialPosition(3,point)
      self.pointF = np.array(point)
      self.AngFidPlan.GetNthFiducialPosition(6,point)
      self.pointG = np.array(point)
      self.AngFidPlan.GetNthFiducialPosition(7,point)
      self.pointH = np.array(point)
      self.AngFidActual.GetNthFiducialPosition(6,point)
      self.pointJ = np.array(point)
      self.AngFidActual.GetNthFiducialPosition(7,point)
      self.pointK = np.array(point)

      #calc width
      self.planWidthLine = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsLineNode','PlanWidth')
      self.planWidthLine.AddControlPoint(self.pointToVec(self.pointA))
      self.planWidthLine.AddControlPoint(self.pointToVec(self.pointB))
      self.planWidth = self.planWidthLine.GetLineLengthWorld()
      self.actWidthLine = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsLineNode','ActualWidth')
      self.actWidthLine.AddControlPoint(self.pointToVec(self.pointD))
      self.actWidthLine.AddControlPoint(self.pointToVec(self.pointE))
      self.actWidth = self.actWidthLine.GetLineLengthWorld()
      self.diffWidth = self.actWidth - self.planWidth

      self.AplanWidthLine = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsLineNode','PlanAngleWidth')
      self.AplanWidthLine.AddControlPoint(self.pointToVec(self.pointG))
      self.AplanWidthLine.AddControlPoint(self.pointToVec(self.pointH))
      self.AplanWidth = self.AplanWidthLine.GetLineLengthWorld()
      self.AactWidthLine = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsLineNode','ActualAngleWidth')
      self.AactWidthLine.AddControlPoint(self.pointToVec(self.pointJ))
      self.AactWidthLine.AddControlPoint(self.pointToVec(self.pointK))
      self.AactWidth = self.AactWidthLine.GetLineLengthWorld()
      self.AdiffWidth = self.AactWidth - self.AplanWidth

      #calc projection
      AB = self.pointB - self.pointA
      base =  np.linalg.norm(AB)
      AC = self.pointC - self.pointA
      left =  np.linalg.norm(AC)
      BC = self.pointC - self.pointB
      right =  np.linalg.norm(BC)
      self.planProj = (0.5*math.sqrt((left+base+right)*((left*-1)+base+right)*(left-base+right)*(left+base-right)))/base
      DE = self.pointE - self.pointD
      base =  np.linalg.norm(DE)
      DF = self.pointF - self.pointD
      left =  np.linalg.norm(DF)
      EF = self.pointF - self.pointE
      right =  np.linalg.norm(EF)
      self.actProj = (0.5*math.sqrt((left+base+right)*((left*-1)+base+right)*(left-base+right)*(left+base-right)))/base
      self.diffProj = self.actProj - self.planProj

      #combine width and projection lists for registration
      self.planFid.AddFiducial(self.pointA[0],self.pointA[1],self.pointA[2])
      self.planFid.AddFiducial(self.pointB[0],self.pointB[1],self.pointB[2])
      self.planFid.AddFiducial(self.pointC[0],self.pointC[1],self.pointC[2])
      self.actFid.AddFiducial(self.pointD[0],self.pointD[1],self.pointD[2])
      self.actFid.AddFiducial(self.pointE[0],self.pointE[1],self.pointE[2])
      self.actFid.AddFiducial(self.pointF[0],self.pointF[1],self.pointF[2])
      #calculate initial registration
      self.reg.SetAndObserveFromFiducialListNodeId(self.planFid.GetID())
      self.reg.SetAndObserveToFiducialListNodeId(self.actFid.GetID())
      self.reg.SetOutputTransformNodeId(self.icpTrans.GetID())
      self.reg.SetRegistrationModeToRigid()
      self.reg.SetUpdateModeToManual()
      self.fidutialRegLogic.UpdateCalibration(self.reg)
      self.ICP_Error = self.reg.GetCalibrationError()
      #transform model
      #self.runTransMod(self.mandP, self.icpTrans)
      #model to model reg
      self.runGetTrans(self.mandA, self.mandP, self.modTrans)
      #report mod to mod error
      self.modAcu = self.ComputeMeanDistance(self.mandP, self.mandA, self.modTrans)
      #transform model
      #self.runTransMod(self.mandP, self.modTrans)
      #calculate dice and hof
      self.mandP_seg = self.runModToSeg(self.mandP)
      self.mandA_seg = self.runModToSeg(self.mandA)
      self.dice, self.hof = self.runCalcDice(self.mandP_seg,self.mandA_seg)
      #calulate plate distances
      distance = self.closestPoint(self.PlateFid, self.mandA)
      self.plateAve = sum(distance)/len(distance)
      self.plateMin = min(distance)
      self.plateMax = max(distance)
      #combine all results
      results = [self.planWidth, self.actWidth, self.diffWidth, self.planProj, self.actProj, self.diffProj, self.ICP_Error, self.modAcu, self.dice, self.hof, self.plateAve, self.plateMin, self.plateMax, self.AplanWidth, self.AactWidth, self.AdiffWidth]
      return results


  def closestPoint(self, markupsNode, modelNode):
    # Transform model polydata to world coordinate system
    if modelNode.GetParentTransformNode():
      transformModelToWorld = vtk.vtkGeneralTransform()
      slicer.vtkMRMLTransformNode.GetTransformBetweenNodes(modelNode.GetParentTransformNode(), None, transformModelToWorld)
      polyTransformToWorld = vtk.vtkTransformPolyDataFilter()
      polyTransformToWorld.SetTransform(transformModelToWorld)
      polyTransformToWorld.SetInputData(modelNode.GetPolyData())
      polyTransformToWorld.Update()
      surface_World = polyTransformToWorld.GetOutput()
    else:
      surface_World = modelNode.GetPolyData()
    distanceCol = []
    distanceFilter = vtk.vtkImplicitPolyDataDistance()
    distanceFilter.SetInput(surface_World);
    nOfFiduciallPoints = markupsNode.GetNumberOfFiducials()
    for i in range(0, nOfFiduciallPoints):
      point_World = [0,0,0]
      markupsNode.GetNthControlPointPositionWorld(i, point_World)
      closestPointOnSurface_World = [0,0,0]
      closestPointDistance = distanceFilter.EvaluateFunctionAndGetClosestPoint(point_World, closestPointOnSurface_World)
      print(closestPointOnSurface_World)
      print(closestPointDistance)
      distanceCol.append(closestPointDistance)
    return distanceCol


  def pointToVec (self, point):
      vec = vtk.vtkVector3d(point[0],point[1],point[2])
      return vec

  def runModToSeg(self, model):
    segNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentationNode", model.GetName() + '-segmentation')
    segLogic = slicer.modules.segmentations.logic()
    segLogic.ImportModelToSegmentationNode(model,segNode)
    return segNode

  def runAveragePoint (self, fids, first, type):
      if type == 0:
          i = 2
          j = 4
      else:
          i = 1
          j = 2
      point1 = [0,0,0]
      fids.GetNthFiducialPosition(first,point1)
      point2 = [0,0,0]
      fids.GetNthFiducialPosition((first+i),point2)
      point3 = [0,0,0]
      fids.GetNthFiducialPosition((first+j),point3)
      point = [0,0,0]
      point[0] = (point1[0]+point2[0]+point3[0])/3
      point[1] = (point1[1]+point2[1]+point3[1])/3
      point[2] = (point1[2]+point2[2]+point3[2])/3
      return point

  def applyTransform(self, transform, polydataSrc):
      transformFilter = vtk.vtkTransformPolyDataFilter()
      transformFilter.SetInputData(polydataSrc)
      transformFilter.SetTransform(transform)
      transformFilter.Update()
      transformedSource = transformFilter.GetOutput()
      return transformedSource

  def runTransMod(self, mod, trans):
      modPolyData = mod.GetPolyData()
      matrix = vtk.vtkMatrix4x4()
      trans.GetMatrixTransformToParent(matrix)
      transform = vtk.vtkTransform()
      transform.SetMatrix(matrix)
      modPolyData = self.applyTransform(transform, modPolyData)
      mod.SetAndObservePolyData(modPolyData)

  def runGetTrans(self, inputSourceModel, inputTargetModel, outputSourceToTargetTransform, transformType=0, numIterations=100 ):
    icpTransform = vtk.vtkIterativeClosestPointTransform()
    icpTransform.SetSource( inputSourceModel.GetPolyData() )
    icpTransform.SetTarget( inputTargetModel.GetPolyData() )
    icpTransform.GetLandmarkTransform().SetModeToRigidBody()
    icpTransform.SetMaximumNumberOfIterations( numIterations )
    icpTransform.Modified()
    icpTransform.Update()
    outputSourceToTargetTransform.SetMatrixTransformToParent( icpTransform.GetMatrix() )
    if slicer.app.majorVersion >= 5 or (slicer.app.majorVersion >= 4 and slicer.app.minorVersion >= 11):
      outputSourceToTargetTransform.AddNodeReferenceID(slicer.vtkMRMLTransformNode.GetMovingNodeReferenceRole(), inputSourceModel.GetID())
      outputSourceToTargetTransform.AddNodeReferenceID(slicer.vtkMRMLTransformNode.GetFixedNodeReferenceRole(), inputTargetModel.GetID())

  def ComputeMeanDistance(self, inputSourceModel, inputTargetModel, transform):
      sourcePolyData = inputSourceModel.GetPolyData()
      targetPolyData = inputTargetModel.GetPolyData()
      cellId = vtk.mutable(0)
      subId = vtk.mutable(0)
      dist2 = vtk.mutable(0.0)
      locator = vtk.vtkCellLocator()
      locator.SetDataSet( targetPolyData )
      locator.SetNumberOfCellsPerBucket( 1 )
      locator.BuildLocator()
      totalDistance = 0.0
      sourcePoints = sourcePolyData.GetPoints()
      n = sourcePoints.GetNumberOfPoints()
      m = vtk.vtkMath()
      for sourcePointIndex in range(n):
          sourcePointPos = [0, 0, 0]
          sourcePoints.GetPoint( sourcePointIndex, sourcePointPos )
          transformedSourcePointPos = [0, 0, 0, 1]
          #transform.GetTransformToParent().TransformVector( sourcePointPos, transformedSourcePointPos )
          sourcePointPos.append(1)
          transform.GetTransformToParent().MultiplyPoint( sourcePointPos, transformedSourcePointPos )
          #transformedPoints.InsertNextPoint( transformedSourcePointPos )
          surfacePoint = [0, 0, 0]
          transformedSourcePointPos.pop()
          locator.FindClosestPoint( transformedSourcePointPos, surfacePoint, cellId, subId, dist2 )
          totalDistance = totalDistance + math.sqrt(dist2)
      return ( totalDistance / n )

  def runCalcDice(self, plan, actual):
      slicer.util.selectModule(slicer.modules.segmentcomparison.name)
      slicer.util.selectModule(slicer.modules.calculateresults.name)
      segComp = getNode('SegmentComparison')
      segComp.SetAndObserveReferenceSegmentationNode(plan)
      segComp.SetAndObserveCompareSegmentationNode(actual)
      slicer.modules.segmentcomparison.logic().ComputeDiceStatistics(segComp)
      slicer.modules.segmentcomparison.logic().ComputeHausdorffDistances(segComp)
      dice = segComp.GetDiceCoefficient()
      hof = segComp.GetPercent95HausdorffDistanceForVolumeMm()
      return dice, hof

#
# CalculateResultsTest
#

class CalculateResultsTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear()

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()
    self.test_CalculateResults1()

  def test_CalculateResults1(self):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """

    self.delayDisplay("Starting the test")

    # Get/create input data

    import SampleData
    registerSampleData()
    inputVolume = SampleData.downloadSample('CalculateResults1')
    self.delayDisplay('Loaded test data set')

    inputScalarRange = inputVolume.GetImageData().GetScalarRange()
    self.assertEqual(inputScalarRange[0], 0)
    self.assertEqual(inputScalarRange[1], 695)

    outputVolume = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLScalarVolumeNode")
    threshold = 100

    # Test the module logic

    logic = CalculateResultsLogic()

    # Test algorithm with non-inverted threshold
    logic.process(inputVolume, outputVolume, threshold, True)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], threshold)

    # Test algorithm with inverted threshold
    logic.process(inputVolume, outputVolume, threshold, False)
    outputScalarRange = outputVolume.GetImageData().GetScalarRange()
    self.assertEqual(outputScalarRange[0], inputScalarRange[0])
    self.assertEqual(outputScalarRange[1], inputScalarRange[1])

    self.delayDisplay('Test passed')
