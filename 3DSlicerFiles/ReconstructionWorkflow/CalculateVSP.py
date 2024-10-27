import os
import unittest
import logging
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin, getNode, resetSliceViews
import numpy as np
try: 
    import jpype
    import jpype.imports 
    from jpype.types import *
except ImportError as e: 
    slicer.util.pip_install('JPype1')
    import jpype
    import jpype.imports 
    from jpype.types import *

import ManageSlicer as ms
import ManageUI as ui

from ManageRegistration import registration as register
from ManageReconstruction import resection as resect
from ManageReconstruction import reconstruction as vsp

class CalculateVSP(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "4. Calculate VSP"
        self.parent.categories = ["Mandibular Reconstruction"]
        self.parent.dependencies = []
        self.parent.contributors = ["Melissa Yu (UBC)"]
        self.parent.helpText = ""
        self.parent.acknowledgementText = ""

class CalculateVSPWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)
        self.logic = None

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.logic = CalculateVSPLogic()

        #CLIP FIBULA
        # clip_fibula_tab = qt.QWidget()
        # clip_fibula_tab_layout = qt.QGridLayout(clip_fibula_tab)
        # clip_fibula_tab_layout.setAlignment(qt.Qt.AlignTop)

        # clip_fibula_title = qt.QLabel("Clip Fibula")
        # clip_fibula_title.setStyleSheet("font-weight: bold; padding: 2px; margin-top: 5px")
        # clip_fibula_tab_layout.addWidget(clip_fibula_title, 0, 0, 1, 4)

        # clip_fibula_instructions = qt.QLabel("Set the parameters below according to the length of fibula clipped from each end.")
        # clip_fibula_instructions.setStyleSheet("padding-bottom: 2px")
        # clip_fibula_instructions.setWordWrap(True)
        # clip_fibula_tab_layout.addWidget(clip_fibula_instructions, 1, 0, 1, 4)

        # self.knee_joint_end = ui.create_text_input(clip_fibula_tab, clip_fibula_tab_layout, "Distance from knee joint (mm)   ", 80, 2, 0)
        # self.ankle_joint_end = ui.create_text_input(clip_fibula_tab, clip_fibula_tab_layout, "Distance from ankle joint (mm)  ", 80, 3, 0)

        # self.clip_fibula = ui.create_button("Clip Fibula")
        # clip_fibula_tab_layout.addWidget(self.clip_fibula, 4, 0, 1, 4)
        # self.clip_fibula.connect('clicked(bool)', self.on_clip_fibula)

        #PLACE FIBULA FIDUCIAL
        place_fibfid = qt.QWidget()
        place_fibfid_tab_layout = qt.QGridLayout(place_fibfid)
        place_fibfid_tab_layout.setAlignment(qt.Qt.AlignTop)


        place_fibfid_title = qt.QLabel("Place Fibula Fiducial")
        place_fibfid_title.setStyleSheet("font-weight: bold; padding: 2px; margin-top: 10px")
        place_fibfid_tab_layout.addWidget(place_fibfid_title, 0, 0, 1, 4)

        place_fibfid_instructions = qt.QLabel("Using the mouse, place a fiducial on the fibula to indicate the start point "+
                                              "for osteotomy cuts and the anterior face for reconstruction. This fiducial will "+
                                              "be on the “Superior” (S) end of the fibula and on the surface that will become "+
                                              "the anterior surface of the mandible reconstruction.  ")
        place_fibfid_instructions.setStyleSheet("padding-left: 2px; padding-bottom: 8px")
        place_fibfid_instructions.setWordWrap(True)
        place_fibfid_tab_layout.addWidget(place_fibfid_instructions, 1, 0, 1, 4)

        self.place_fibfid = ui.create_button("Place Fibula Fiducial")
        place_fibfid_tab_layout.addWidget(self.place_fibfid, 2, 0, 1, 4)
        self.place_fibfid.connect('clicked(bool)', self.on_place_fibfid)

        #RUN VSP
        run_VSP_tab = qt.QWidget()
        run_VSP_tab_layout = qt.QGridLayout(run_VSP_tab)
        run_VSP_tab_layout.setAlignment(qt.Qt.AlignTop)
        run_VSP_tab_layout.setContentsMargins(12, 5, 10, 10)

        run_VSP_title = qt.QLabel("Calculate VSP")
        run_VSP_title.setStyleSheet("font-weight: bold; margin-top: 10px; margin-bottom: 5px") #padding: 2px; 
        run_VSP_tab_layout.addWidget(run_VSP_title, 0, 0, 1, 4)

        run_VSP_instructions = qt.QLabel("Enter your parameters for reconstruction into the corresponding boxes below. "+
                                         "When ready, press “Plan Reconstruction.” It may take a few moments for the "+
                                         "reconstruction to be generated. Once the screen updates with the reconstruction, "+
                                         "planning is complete. Visually evaluate the quality of the reconstruction. "+
                                         "If the reconstruction needs to be re-done, press “Delete Reconstruction” and adjust "+
                                         "the location of the “Start point” fiducial or the reconstruction parameters as desired. "+
                                         "Press “Plan Reconstruction” when ready. ")
        run_VSP_instructions.setStyleSheet("padding: 2px; padding-bottom: 10px")
        run_VSP_instructions.setWordWrap(True)
        run_VSP_tab_layout.addWidget(run_VSP_instructions, 1, 0, 1, 4)

        min_length_label = qt.QLabel("Minimum Segment Length (mm)")
        min_length_label.setStyleSheet("padding-bottom: 8px")
        run_VSP_tab_layout.addWidget(min_length_label, 2, 0, 1, 2)
        self.min_length_input = qt.QLineEdit()
        self.min_length_input.setText(20.)
        run_VSP_tab_layout.addWidget(self.min_length_input, 2, 2, 1, 2)

        seg_sep_label = qt.QLabel("Segment Separation (mm)")
        seg_sep_label.setStyleSheet("padding-bottom: 8px")
        run_VSP_tab_layout.addWidget(seg_sep_label, 3, 0, 1, 2)
        self.seg_sep_input = qt.QLineEdit()
        self.seg_sep_input.setText(15.)
        run_VSP_tab_layout.addWidget(self.seg_sep_input, 3, 2, 1, 2)
  
        max_seg_label = qt.QLabel("Maximum Segments")
        max_seg_label.setStyleSheet("padding-bottom: 8px")
        run_VSP_tab_layout.addWidget(max_seg_label, 4, 0, 1, 2)
        self.max_segs_input = qt.QLineEdit()
        self.max_segs_input.setText(3)
        run_VSP_tab_layout.addWidget(self.max_segs_input, 4, 2, 1, 2)


        self.left_to_right = qt.QCheckBox("Create reconstruction from left to right")
        self.left_to_right.setChecked(False)
        run_VSP_tab_layout.addWidget(self.left_to_right, 6, 0, 1, 4)

        space1 = qt.QLabel("")
        space1.setStyleSheet('margin-bottom: -10px')
        run_VSP_tab_layout.addWidget(space1, 5, 0, 1, 4)

        self.run_VSP = ui.create_button("Plan Reconstruction")
        run_VSP_tab_layout.addWidget(self.run_VSP, 7, 0, 1, 4)
        self.run_VSP.connect('clicked(bool)', self.on_run_VSP)

        #self.delete_VSP = ui.create_button("Delete Reconstruction", "Delete Reconstruction", 0)
        self.delete_VSP = ui.create_button("Delete Reconstruction", "Delete Reconstruction", 1)
        run_VSP_tab_layout.addWidget(self.delete_VSP, 8, 0, 1, 4)
        self.delete_VSP.connect('clicked(bool)', self.on_delete_VSP)


        space2 = qt.QLabel("")
        space2.setStyleSheet('margin-bottom: -10px')
        run_VSP_tab_layout.addWidget(space2, 9, 0, 1, 4)

        manage_reconstruction = ctk.ctkCollapsibleButton()
        manage_reconstruction.collapsed = 1 
        manage_reconstruction.text = "Manage Reconstruction"
        run_VSP_tab_layout.addWidget(manage_reconstruction, 10, 0, 1, 4)
        manage_reconstruction_layout = qt.QHBoxLayout(manage_reconstruction)
        manage_reconstruction_layout.setMargin(2)

        self.create_segments = ui.create_button("Visualize Reconstruction Plan")
        manage_reconstruction_layout.addWidget(self.create_segments)
        self.create_segments.connect('clicked(bool)', self.on_visualize_VSP)

        #self.setSpline = ui.create_button("Create Donor Curve")
        #RunVSP_TabLayout.addRow(self.setSpline)
        #self.setSpline.connect('clicked(bool)', self.createDonorCurve)

        #self.testDonorMarch = ui.create_button("Test Donor March")
        #RunVSP_TabLayout.addRow(self.testDonorMarch)
        #self.testDonorMarch.connect('clicked(bool)', self.onTestDonorMarch)

        #self.computeCentroid = ui.create_button("Compute Centroid")
        #RunVSP_TabLayout.addRow(self.computeCentroid)
        #self.computeCentroid.connect('clicked(bool)', self.onComputeCentroid)

        self.calculate_VSP_tabs = qt.QTabWidget()
        self.calculate_VSP_tabs.setElideMode(qt.Qt.ElideNone)
        #self.calculate_VSP_tabs.addTab(clip_fibula_tab, "Clip Fibula")
        self.calculate_VSP_tabs.addTab(place_fibfid, "Place Fiducial")
        self.calculate_VSP_tabs.addTab(run_VSP_tab, "Run VSP")
        self.layout.addWidget(self.calculate_VSP_tabs, 0, 0)
        self.VSP_tab_state = self.calculate_VSP_tabs.currentIndex

        #Navigation Buttons
        navigation_button_box = qt.QGroupBox()
        self.layout.addWidget(navigation_button_box)
        navigation_button_layout = qt.QHBoxLayout(navigation_button_box)

        self.previous_button = ui.create_button("Previous")
        navigation_button_layout.addWidget(self.previous_button)
        self.previous_button.connect('clicked(bool)', self.on_previous_module)

        self.next_button = ui.create_button("Next")
        navigation_button_layout.addWidget(self.next_button)
        self.next_button.connect('clicked(bool)', self.on_next_module)

        save_box = qt.QGroupBox()
        save_button_layout = qt.QHBoxLayout(save_box)
        self.save_button = ui.create_button("Save scene")
        self.save_button.connect('clicked(bool)', self.on_save)
        save_button_layout.addWidget(self.save_button)
        self.layout.addWidget(save_box)

        self.get_nodes()
        self.change_VSP_tab_visibility(self.calculate_VSP_tabs.currentIndex)
        #self.CalculateVSP_Tabs.setCurrentIndex(self.CalculateVSP_Tabs.currentIndex)

    def get_nodes(self): 
        self.Fibula = getNode('Fibula')
        self.FibFid = ui.import_node('StartPoint')
        self.Contour = getNode('Contour')
        self.GreenSlice = getNode('vtkMRMLSliceNodeGreen')
        self.YellowSlice = getNode('vtkMRMLSliceNodeYellow')
        #Should not have to do this to get the normal and origin. Can also just convert to vtk plane
        #
        #self.GreenNormal, self.GreenOrigin, self.YellowNormal, self.YellowOrigin = \
        #    hf.checkPlaneNormalDirection(self.GreenSlice, self.YellowSlice)
        self.GreenVTK = ms.get_vtkplane_from_slice(self.GreenSlice)
        self.GreenNormal = self.GreenVTK.GetNormal()
        self.GreenOrigin = self.GreenVTK.GetOrigin()
        self.YellowVTK = ms.get_vtkplane_from_slice(self.YellowSlice)
        self.YellowNormal = self.YellowVTK.GetNormal()
        self.YellowOrigin = self.YellowVTK.GetOrigin()
        self.fibula_path = getNode('FibulaPath')

    def on_previous_module(self):
        if self.VSP_tab_state > 0:
            self.VSP_tab_state = self.VSP_tab_state - 1
            self.change_VSP_tab_visibility(self.VSP_tab_state)
            print(self.VSP_tab_state)
        elif self.VSP_tab_state == 0:
            slicer.util.selectModule('RegisterFibula')

    def on_next_module(self):
        if self.VSP_tab_state < 1:
            self.VSP_tab_state = self.VSP_tab_state + 1
            self.change_VSP_tab_visibility(self.VSP_tab_state)
            print(self.calculate_VSP_tabs.currentIndex)
        else:
            slicer.util.selectModule('GuideSegmentCuts')
            
    def on_save(self):
        dir = os.path.dirname(getNode('MandiblePath').GetText())+"\\SlicerFiles"
        ms.save_scene(dir, "4_CalculateVSP"+str(self.VSP_tab_state))


    #Control tab visibility and page state
    def change_VSP_tab_visibility(self, state):
        self.calculate_VSP_tabs.setCurrentIndex(state)
        if state == 0:
            self.on_place_fibfid_tab()
        elif state == 1:
            self.on_run_VSP_tab()
            

    #Set UI for each tab 
    def on_clip_fibula_tab(self):
        slicer.modules.models.logic().SetAllModelsVisibility(0)
        self.Fibula.SetDisplayVisibility(1)
        #self.FibFid.SetDisplayVisibility(0)

    def on_place_fibfid_tab(self):
        self.FibFid.SetDisplayVisibility(1)
        self.Fibula.SetDisplayVisibility(1)
        dir = os.path.dirname(getNode('MandiblePath').GetText())+"\\SlicerFiles"
        # ms.save_scene(dir, "4_ClipFib")
        try:
            getNode('Clipped Fibula').SetDisplayVisibility(1)
        except slicer.util.MRMLNodeNotFoundException: 
            print("Clipped Fibula node not found. Please import clipped fibula model or check node name.")

    def on_run_VSP_tab(self):
        self.FibFid.SetDisplayVisibility(0)
        self.Fibula.SetDisplayVisibility(1)

    #TAB 1 LOGIC: CLIP FIBULA
    def on_clip_fibula(self):
        self.logic.delayDisplay("Clipping Fibula")
        self.genVSP = vsp.connect_JVM()
        input_path = self.fibula_path.GetText()
        self.output_path = os.path.dirname(input_path)+"\\ClippedFibula_Donor.stl"
        self.TCW_Transform = self.genVSP.prepareFibula(input_path, self.output_path, 80, 80)
        print(self.TCW_Transform)
        self.TCW_arr = self.genVSP.changeTransformToArray(self.TCW_Transform)
        #self.createSegmentTransform(self.TCW_arr, "TCW")
        ms.arraylist_to_transform(self.TCW_arr, "TCW")
        print("TCW transform created")
        clipped_fibula = slicer.modules.models.logic().AddModel(self.output_path, slicer.vtkMRMLStorageNode.CoordinateSystemRAS)
        clipped_fibula.SetName("Clipped Fibula")
        if clipped_fibula.GetModelDisplayNode() is None: 
            modelDisplay = slicer.vtkMRMLModelDisplayNode()
            modelDisplay.SetBackfaceCulling(0)
            modelDisplay.SetColor(0.33333, 0.33333333, 0)
            modelDisplay.SetScene(slicer.mrmlScene)
            modelDisplay.SetScalarVisibility(1)
            slicer.mrmlScene.AddNode(modelDisplay)
            clipped_fibula.SetAndObserveDisplayNodeID(modelDisplay.GetID())
            #print("Model display")
        clipped_fibula.GetModelDisplayNode().SetColor(1, 0.333333333, 1)
        clipped_fibula.GetModelDisplayNode().VisibilityOn()
        print("Imported fibula")
        self.TCW = getNode("TCW")
        clipped_fibula.SetAndObserveTransformNodeID(self.TCW.GetID())
        slicer.vtkSlicerTransformLogic().hardenTransform(clipped_fibula)
        getNode('Fibula').GetDisplayNode().SetVisibility(False)
        self.on_next_module()

    #TAB 2 LOGIC: PLACE FIB FID
    def on_place_fibfid(self):
        register.place_CT_fiducial(self.FibFid)
        #print(f'FibFid: {slicer.util.arrayFromMarkupsControlPoints(temp, world=False)}')

    #TAB 3 LOGIC: CALCULATE VSP
    def on_run_VSP(self): 
        self.logic.delayDisplay ("Running VSP...")
        genVSP = vsp.connect_JVM()

        minSegLength = float(self.min_length_input.text)
        maxSegments = int(self.max_segs_input.text)
        segSeparation = float(self.seg_sep_input.text)

        contour = getNode('Contour')
        start_point = getNode('StartPoint')
        fibPathNode = getNode('FibulaPath')
        mandPathNode  = getNode('MandiblePath')
        TCW = getNode('TCW')

        rightVTKPlane = ms.get_vtkplane_from_slice(getNode('vtkMRMLSliceNodeGreen'))
        leftVTKPlane = ms.get_vtkplane_from_slice(getNode('vtkMRMLSliceNodeYellow'))

        if self.left_to_right.isChecked():
            left_to_right = True
        else:
            left_to_right = False

        fibula_segments = vsp.run_VSP(genVSP, segSeparation, minSegLength, maxSegments, contour, fibPathNode, mandPathNode,
                                     leftVTKPlane, rightVTKPlane, start_point, TCW, left_to_right)
        # fibula_segments = vsp.run_VSP(genVSP, segSeparation, minSegLength, maxSegments, contour, fibPathNode, mandPathNode,
        #                              rightVTKPlane, leftVTKPlane, start_point, TCW)

        vsp.generate_segment_transforms(genVSP, fibula_segments)
        self.on_visualize_VSP()
        self.delete_VSP.setEnabled(1)
        #print(fibula_segments)
   
    def on_visualize_VSP(self):
        self.numOfSegs = int(getNode('NumOfSegs').GetText())
        clipped_fibula = getNode('Clipped Fibula')
        resected_mandible = getNode('NonResected')
        resected_mandible.SetDisplayVisibility(1)
        rdp_points = getNode('RDPPoints')
        rdp_points.SetDisplayVisibility(0)
        vsp.create_donor_segments(clipped_fibula, self.numOfSegs)
        vsp.create_mandible_segments(self.numOfSegs)
        vsp.create_cut_plane_model(self.numOfSegs)
        endpoints = getNode('VSPSegEndpoints')
        endpoints.SetDisplayVisibility(0)
        #self.createDonorSegs(numOfSegs)
        #self.createMandibleSegs(numOfSegs)

    def on_delete_VSP(self):
        #for i in self.numOfSegs-1:
        for i in range(int(getNode('NumOfSegs').GetText())):
            ui.remove_node('TPS0Seg'+str(i+1))
            ui.remove_node('TPS1Seg'+str(i+1))
            ui.remove_node('TSWMSeg'+str(i+1))
            ui.remove_node('TSWDSeg'+str(i+1))
            ui.remove_node('VSPFibSeg'+str(i+1))
            ui.remove_node('VSPMandSeg'+str(i+1))
            ui.remove_node('Plane0Seg'+str(i+1))
            ui.remove_node('Plane1Seg'+str(i+1))
            ui.remove_node(str(i+1)+'Cut0View1')
            ui.remove_node(str(i+1)+'Cut0View2')
            ui.remove_node(str(i+1)+'Cut0View3')
            ui.remove_node(str(i+1)+'Cut1View1')
            ui.remove_node(str(i+1)+'Cut1View2')
            ui.remove_node(str(i+1)+'Cut1View3')
        ui.remove_node('VSPSegEndpoints')
        ui.remove_node('RDP')
        ui.remove_node('RDPPoints')
        ui.remove_node('NumOfSegs')
        getNode('NonResected').SetDisplayVisibility(0)
        getNode('StartPoint').SetDisplayVisibility(1)
        self.delete_VSP.setEnabled(0)
        print("Deleted reconstruction")


            # slicer.mrmlScene.RemoveNode(getNode('TPS0Seg'+str(i+1)))
            # slicer.mrmlScene.RemoveNode(getNode('TPS1Seg'+str(i+1)))
            # slicer.mrmlScene.RemoveNode(getNode('TSWMSeg'+str(i+1)))
            # slicer.mrmlScene.RemoveNode(getNode('TSWDSeg'+str(i+1)))
            # slicer.mrmlScene.RemoveNode(getNode('VSPFibSeg'+str(i+1)))
            # slicer.mrmlScene.RemoveNode(getNode('VSPMandSeg'+str(i+1)))
            # slicer.mrmlScene.RemoveNode(getNode('Plane0Seg'+str(i+1)))
            # slicer.mrmlScene.RemoveNode(getNode('Plane1Seg'+str(i+1)))
            # slicer.mrmlScene.RemoveNode(getNode(str(i+1)+'Cut0View1'))
            # slicer.mrmlScene.RemoveNode(getNode(str(i+1)+'Cut0View2'))
            # slicer.mrmlScene.RemoveNode(getNode(str(i+1)+'Cut0View3'))
            # slicer.mrmlScene.RemoveNode(getNode(str(i+1)+'Cut1View1'))
            # slicer.mrmlScene.RemoveNode(getNode(str(i+1)+'Cut1View2'))
            # slicer.mrmlScene.RemoveNode(getNode(str(i+1)+'Cut1View3'))

    #FOR TESTING PURPOSES
    #def onTestDonorMarch(self):
    #    self.setUserInputs()
    #    self.setFibulaPath()
    #    #Should use the fibula in donor space with the transform to world
    #    point = self.genVSP.findNextDonorPointTest(self.donorMarkers, self.segSeparation, self.fibula_path, self.spline, self.TCW)
    #    print(point)
    #    slicer.modules.markups.logic().AddFiducial(-point.x, -point.y, point.z)
    #    self.donorMarkers = self.genVSP.setPoint3d(-point.x, -point.y, float(point.z))

    #def createDonorCurve(self):
    #    self.connectJVM()
    #    self.setFibulaPath()
    #    self.spline = self.genVSP.findDonorCurve(self.fibula_path, self.TCW, 80, 80)
    #    print(self.spline)
    #    for i in range(self.spline.size()):
    #        slicer.modules.markups.logic().AddFiducial(self.spline[i].x, self.spline[i].y, self.spline[i].z)

    #def onComputeCentroid(self):
    #    self.connectJVM()
    #    self.full_fibula_path = "C:\\Users\\Melissa\\Desktop\\UBC\\ISTAR\\Runthrough\\Artisynth Practice File\\StepVSP8\\centered_fibula.stl"
    #    self.fib_centroid = self.genVSP.getCentroid(self.full_fibula_path)
    #    print(self.fib_centroid)
    #    trans = np.identity(4)
    #    trans[0, 3]=self.fib_centroid.x
    #    trans[1, 3]=self.fib_centroid.y
    #    trans[2, 3]=self.fib_centroid.z


class CalculateVSPLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)

class ResectMandibleTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.test_ResectMandible1()

    def test_ResectMandible1(self):
        self.delayDisplay("Start test")
        logic = ResectMandibleLogic()
        self.delayDisplay("Test passed")