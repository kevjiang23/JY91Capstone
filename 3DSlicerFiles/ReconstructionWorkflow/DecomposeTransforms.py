import os
import unittest
import logging
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin, getNode

import math
import numpy as np

import ManageSlicer as ms
import ManageUI as ui

from ManageRegistration import registration as register


class DecomposeTransforms(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Decompose Transforms"
        self.parent.categories = ["Feature Testing"]
        self.parent.dependencies = []
        self.parent.contributors = ["Melissa Yu (UBC)"]
        self.parent.helpText = ""
        self.parent.acknowledgementText = ""

class DecomposeTransformsWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)
        self.logic = None
       

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.logic = DecomposeTransformsLogic()
        slicer.app.layoutManager().setLayout(4)
        self.layout.setAlignment(qt.Qt.AlignTop)

        model_transform = ctk.ctkCollapsibleButton()
        model_transform.text = "Transform Between Models"
        model_transform_layout = qt.QGridLayout(model_transform)
        model_transform_layout.setAlignment(qt.Qt.AlignTop)
        self.layout.addWidget(model_transform)

        source_label = qt.QLabel("Source Model: ")
        source_label.setStyleSheet("padding-left: 2px")
        model_transform_layout.addWidget(source_label, 0, 0, 1, 1)
        self.source_combo = slicer.qMRMLNodeComboBox()
        self.source_combo.nodeTypes = ["vtkMRMLModelNode"]
        self.source_combo.addEnabled = False
        self.source_combo.removeEnabled = False
        self.source_combo.setMRMLScene(slicer.mrmlScene)
        model_transform_layout.addWidget(self.source_combo, 0, 1, 1, 2)

        target_label = qt.QLabel("Target Model: ")
        target_label.setStyleSheet("padding-left: 2px")
        model_transform_layout.addWidget(target_label, 1, 0, 1, 1)
        self.target_combo = slicer.qMRMLNodeComboBox()
        self.target_combo.nodeTypes = ["vtkMRMLModelNode"]
        self.target_combo.addEnabled = False
        self.target_combo.removeEnabled = False
        self.target_combo.setMRMLScene(slicer.mrmlScene)
        model_transform_layout.addWidget(self.target_combo, 1, 1, 1, 2)

        self.get_transform = ui.create_button("Get Transform")
        self.get_transform.connect('clicked(bool)', self.on_get_transform)
        model_transform_layout.addWidget(self.get_transform, 2, 0, 1, 3)

 
    #CONTROLLER

    def on_get_transform(self):
        source = self.source_combo.currentNode()
        target = self.target_combo.currentNode()
        self.modTrans = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode', 'ModelToModel_Transform')

        self.runGetTrans(source, target, self.modTrans)
        transform = self.modTrans
        matrix = vtk.vtkMatrix4x4()
        transform.GetMatrixTransformToWorld(matrix)
        transform = matrix
        print(f'Model Transform: {transform}')

        translation = [transform.GetElement(0, 3), transform.GetElement(1, 3), transform.GetElement(2, 3)]
        print(f'Translation: {translation}')

        rotation =  transform
        print(f'Rotation: {rotation}')

        theta_x, theta_y, theta_z = ms.get_rotation_euler(transform)
        print(f'Theta X: {theta_x}\nTheta Y: {theta_y}\nTheta Z: {theta_z}')

    def runGetTrans(self, inputSourceModel, inputTargetModel, outputSourceToTargetTransform, transformType=0, numIterations=100 ):
      
         
      icpTransform = vtk.vtkIterativeClosestPointTransform()
      icpTransform.SetSource( inputSourceModel.GetPolyData() )
      icpTransform.SetTarget( inputTargetModel.GetPolyData() )
      icpTransform.GetLandmarkTransform().SetModeToRigidBody()
      icpTransform.SetMaximumNumberOfIterations( numIterations )
      icpTransform.Modified()
      icpTransform.Update()
      outputSourceToTargetTransform.SetMatrixTransformToParent( icpTransform.GetMatrix())
      print(outputSourceToTargetTransform)
      if slicer.app.majorVersion >= 5 or (slicer.app.majorVersion >= 4 and slicer.app.minorVersion >= 11):
        outputSourceToTargetTransform.AddNodeReferenceID(slicer.vtkMRMLTransformNode.GetMovingNodeReferenceRole(), inputSourceModel.GetID())
        outputSourceToTargetTransform.AddNodeReferenceID(slicer.vtkMRMLTransformNode.GetFixedNodeReferenceRole(), inputTargetModel.GetID())


class DecomposeTransformsLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        # self.markupsLogic = slicer.modules.markups.logic()
        # self.fiducialRegistrationLogic = slicer.modules.fiducialregistrationwizard.logic()


class DecomposeTransformsTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.test_DecomposeTransforms1()

    def test_DecomposeTransforms1(self):
        self.delayDisplay("Start test")
        logic = DecomposeTransformsLogic()
        self.delayDisplay("Test passed")