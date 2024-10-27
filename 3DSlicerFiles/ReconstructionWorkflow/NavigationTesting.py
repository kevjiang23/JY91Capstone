import os
import unittest
import logging
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin, getNode
import _HelperFile as hf
import numpy as np 
import math

import ManageSlicer as ms
import ManageUI as ui


class NavigationTesting(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Navigation Testing"
        self.parent.categories = ["Feature Testing"]
        self.parent.dependencies = []
        self.parent.contributors = ["Melissa Yu (UBC)"]
        self.parent.helpText = ""
        self.parent.acknowledgementText = ""

class NavigationTestingWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.logic = NavigationTestingLogic()
        self.layout.setAlignment(qt.Qt.AlignTop)
        self.clipNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLClipModelsNode')
        self.modelLogic = slicer.vtkSlicerModelsLogic()
        # self.plane_collection = vtk.vtkPlaneCollection()

        analyze_recon = ctk.ctkCollapsibleButton()
        analyze_recon.text = "Analyze Recon"
        analyze_recon_layout = qt.QFormLayout(analyze_recon)
        self.layout.addWidget(analyze_recon)

        plane1 = qt.QLabel("Plane 1")
        self.select_plane1 = slicer.qMRMLNodeComboBox()
        self.select_plane1.nodeTypes = ["vtkMRMLMarkupsPlaneNode"]
        self.select_plane1.noneEnabled = True
        self.select_plane1.setMRMLScene(slicer.mrmlScene)
        analyze_recon_layout.addRow(plane1, self.select_plane1)

        plane2 = qt.QLabel("Plane 2")
        self.select_plane2 = slicer.qMRMLNodeComboBox()
        self.select_plane2.nodeTypes = ["vtkMRMLMarkupsPlaneNode"]
        self.select_plane2.noneEnabled = True
        self.select_plane2.setMRMLScene(slicer.mrmlScene)
        analyze_recon_layout.addRow(plane2, self.select_plane2)

        clip_models = ui.create_button("Clip Models")
        clip_models.connect('clicked(bool)', self.on_clip_models)
        analyze_recon_layout.addWidget(clip_models)

    def on_clip_models(self):
        model = getNode('reconstruction')
        if self.select_plane1.currentNode() != None:
            markupplane1 = self.select_plane1.currentNode()
            vtkplane1 = self.get_vtkplane_from_markup_plane(markupplane1)
        if self.select_plane2.currentNode() != None: 
            markupplane2 = self.select_plane2.currentNode()
            vtkplane2 = self.get_vtkplane_from_markup_plane(markupplane2)

        plane_collection_right = vtk.vtkPlaneCollection()
        plane_collection_right.AddItem(vtkplane1)
        right_segment_poly = ms.clip_polydata(plane_collection_right, model.GetPolyData())
        right_segment = ms.create_model(right_segment_poly, "Right Segment")

        plane_collection_left = vtk.vtkPlaneCollection()
        plane_collection_left.AddItem(vtkplane2)
        left_segment_poly = ms.clip_polydata(plane_collection_left, model.GetPolyData())
        left_segment = ms.create_model(left_segment_poly, "Left Segment")

        temp_normal1 = vtkplane1.GetNormal()
        vtkplane1.SetNormal(-temp_normal1[0], -temp_normal1[1], -temp_normal1[2])
        temp_normal2 = vtkplane2.GetNormal()
        vtkplane2.SetNormal(-temp_normal2[0], -temp_normal2[1], -temp_normal2[2])

        plane_collection3 = vtk.vtkPlaneCollection()
        plane_collection3.AddItem(vtkplane1)
        plane_collection3.AddItem(vtkplane2)
        segment3_poly = ms.clip_polydata(plane_collection3, model.GetPolyData())
        segment3 = ms.create_model(segment3_poly, "Middle Segment")



    def get_vtkplane_from_markup_plane(self, markups_plane):
        plane = vtk.vtkPlane()
        normal = [0,0,0]
        origin = [0,0,0]
        markups_plane.GetNormalWorld(normal)
        markups_plane.GetOriginWorld(origin)
        plane.SetNormal(normal)
        plane.SetOrigin(origin)
        return plane


class NavigationTestingLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)

class NavigationTestingTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.test_NavigationTesting()

    def test_NavigationTesting(self):
        self.delayDisplay("Start test")
        logic = NavigationTestingLogic()
        self.delayDisplay("Test Passed")