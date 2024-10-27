import os
import unittest
import logging
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin, getNode

import ManageSlicer as ms
import ManageUI as ui
from ManageRegistration import registration as register
from ManageReconstruction import reconstruction as vsp

class RegisterFibula(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "3. Register Fibula"
        self.parent.categories = ["Mandibular Reconstruction"]
        self.parent.dependencies = []
        self.parent.contributors = ["Melissa Yu (UBC)"]
        self.parent.helpText = ""
        self.parent.acknowledgementText = ""

class RegisterFibulaWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)
        self.logic = None

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.logic = RegisterFibulaLogic()
        slicer.app.layoutManager().setLayout(4)
        self.get_nodes()
        #slicer.app.layoutManager().setLayout(19)       #3 screen view
        slicer.app.layoutManager().setLayout(4)         #1 screen view

        #CLIP FIBULA
        clip_fibula_tab = qt.QWidget()
        clip_fibula_tab_layout = qt.QGridLayout(clip_fibula_tab)
        clip_fibula_tab_layout.setAlignment(qt.Qt.AlignTop)

        clip_fibula_title = qt.QLabel("Clip Fibula")
        clip_fibula_title.setStyleSheet("font-weight: bold; padding: 2px; margin-top: 5px")
        clip_fibula_tab_layout.addWidget(clip_fibula_title, 0, 0, 1, 4)

        clip_fibula_instructions = qt.QLabel("1. Dissect out the fibula, making the cut at least 50mm from the knee and ankle joint. \n"+
                                             "2. Record the distance the fibula was cut from the knee and ankle end by palpating the joints and measuring with a ruler. \n"+
                                             "3. Enter the distance in mm into the box below and press “Clip Fibula” to update the model accordingly. \n"+
                                             "4. Then, pre-drill a 1/16 in hole and attach the fibula optical reference frame to the superior "+
                                             "end of the fibula, facing medially. \n")
        clip_fibula_instructions.setStyleSheet("padding-bottom: 2px")
        clip_fibula_instructions.setWordWrap(True)
        clip_fibula_tab_layout.addWidget(clip_fibula_instructions, 1, 0, 1, 4)

        self.knee_joint_end = ui.create_text_input(clip_fibula_tab, clip_fibula_tab_layout, "Distance from knee joint (mm)   ", 50, 2, 0)
        self.ankle_joint_end = ui.create_text_input(clip_fibula_tab, clip_fibula_tab_layout, "Distance from ankle joint (mm)  ", 50, 3, 0)

        self.clip_fibula = ui.create_button("Clip Fibula")
        clip_fibula_tab_layout.addWidget(self.clip_fibula, 4, 0, 1, 4)
        self.clip_fibula.connect('clicked(bool)', self.on_clip_fibula)

        #FIBULA PAIRED-POINT REGISTRATION: VIEW
        #Place Fibula Registration Patient Fiducials
        fibula_registration_tab = qt.QWidget()
        fibula_registration_tab_layout = qt.QGridLayout(fibula_registration_tab)
        fibula_registration_tab_layout.setAlignment(qt.Qt.AlignTop)
        fibula_registration_tab_layout.setContentsMargins(12, 5, 10, 10)

        fibula_registration_title = qt.QLabel(f'Register the Fibula: Paired Point')
        fibula_registration_title.setStyleSheet("font-weight: bold; padding-bottom: 15px; padding-left: 1px; padding-top: 10px")
        fibula_registration_tab_layout.addWidget(fibula_registration_title, 0, 0, 1, 4)

        fibula_CT_fiducial_instructions = qt.QLabel(f"Place Virtual Fiducials: Identify a minimum of three visually distinct "+
                                                     "points on the fibula that are apparent on both the patient’s fibula "+
                                                     "and the virtual fibula model. Using the mouse, place a fiducial at each "+
                                                     "of those points. ")
        fibula_CT_fiducial_instructions.setStyleSheet('padding-bottom: 10px; padding-top: 5px')
        fibula_CT_fiducial_instructions.setWordWrap(True)
        fibula_registration_tab_layout.addWidget(fibula_CT_fiducial_instructions, 1, 0, 1, 4)

        #Count Number of Fibula CT fiducials Placed
        self.fibula_CT_fiducials_label = qt.QLabel(f'Number of fiducials placed: {self.fibula_CT_fiducials.GetNumberOfFiducials()}')
        self.fibula_CT_fiducials_label.setStyleSheet('padding-bottom: 7px')
        fibula_registration_tab_layout.addWidget(self.fibula_CT_fiducials_label, 2, 0, 1, 4)

        # Place Fibula Registration CT fiducials
        self.place_fibula_CT_fiducials = ui.create_button("Place Virtual Fiducial", "Place fiducial on fibula model", True)
        fibula_registration_tab_layout.addWidget(self.place_fibula_CT_fiducials, 3, 0, 1, 3)
        self.place_fibula_CT_fiducials.connect('clicked(bool)', self.on_place_fibula_CT_fiducial)

        #Remove Fibula Registration CT fiducials
        self.remove_fibula_CT_fiducials = ui.create_button("🗑 Delete all",  "Delete all virtual fibula fiducials", True)
        fibula_registration_tab_layout.addWidget(self.remove_fibula_CT_fiducials, 3, 3, 1, 1)
        self.remove_fibula_CT_fiducials.connect('clicked(bool)', self.on_remove_fibula_CT_fiducial)

        #
        physical_fiducial_instructions = qt.QLabel(f'Place Physical Fiducials: Using the NDI pointer, place a fiducial at each of '+
                                                    'the corresponding locations on the patient in the same order as the virtual '+
                                                    'fiducials were placed (where possible, place the pointer perpendicular to the '+
                                                    'bone surface). \n\nNote: If finding distinct locations is difficult, use a ruler to'+
                                                    ' measure down the length '+
                                                    'towards the center. This measurement can be used to define locations of both '+
                                                    'physical and virtual fiducials for the purpose of paired-point registration.')
        physical_fiducial_instructions.setStyleSheet('padding-top: 10px; padding-bottom: 7px')
        physical_fiducial_instructions.setWordWrap(True)
        fibula_registration_tab_layout.addWidget(physical_fiducial_instructions, 4, 0, 1, 4)

        self.physical_fibula_fiducials_label = qt.QLabel(f'Number of fiducials placed: {self.fibula_patient_fiducials.GetNumberOfFiducials()}')
        self.physical_fibula_fiducials_label.setStyleSheet('padding-bottom: 7px')
        fibula_registration_tab_layout.addWidget(self.physical_fibula_fiducials_label, 5, 0, 1, 4)

        #Place Fibula Registration Patient Fiducials
        self.place_physical_fibula_fiducials = ui.create_button("Place Patient Fiducial", "Place fiducials on patient's fibula", True)
        fibula_registration_tab_layout.addWidget(self.place_physical_fibula_fiducials, 6, 0, 1, 3)
        self.place_physical_fibula_fiducials.connect('clicked(bool)', self.on_place_fibula_patient_fiducial)

        #Remove Fibula Registration Patient Fiducials
        self.remove_physical_fibula_fiducials = ui.create_button("🗑 Delete all", "Delete all patient fiducials")
        fibula_registration_tab_layout.addWidget(self.remove_physical_fibula_fiducials, 6, 3, 1, 1)
        self.remove_physical_fibula_fiducials.connect('clicked(bool)', self.on_remove_fibula_patient_fiducial)

        register_fibula_error_instructions = qt.QLabel("Register: Run the paired-point registration and evaluate the error. If it is "+
                                                       "greater than 10, delete the registration and repeat the paired-point registration "+
                                                       "steps. ")
        register_fibula_error_instructions.setWordWrap(True)
        register_fibula_error_instructions.setStyleSheet("padding-top: 10px; font-weight: normal")
        fibula_registration_tab_layout.addWidget(register_fibula_error_instructions, 7, 0, 1, 4)

        self.register_fibula_error = qt.QLabel("Root-mean square error: ")
        self.register_fibula_error.setStyleSheet("padding-bottom: 7px; font-weight: normal")
        fibula_registration_tab_layout.addWidget(self.register_fibula_error, 8, 0, 1, 4)

        # Calculate Initial Fibula Registration
        self.register_fibula_button = ui.create_button("Register Fibula", "Run Paired Point Registration", True)
        fibula_registration_tab_layout.addWidget(self.register_fibula_button, 9, 0, 1, 3)
        self.register_fibula_button.connect('clicked(bool)', self.register_fibula_paired_point)

        self.delete_registration_button = ui.create_button("🗑 Delete", "Delete Paired Point Registration", True)
        fibula_registration_tab_layout.addWidget(self.delete_registration_button, 9, 3, 1, 1)
        self.delete_registration_button.connect('clicked(bool)', self.delete_fibula_paired_point)

        # FIBULA SURFACE REGISTRATION: VIEW
        # Place Fibula Registration Patient Fiducials
        fibula_surface_registration_tab = qt.QWidget()
        fibula_surface_registration_tab_layout = qt.QGridLayout(fibula_surface_registration_tab)
        fibula_surface_registration_tab_layout.setAlignment(qt.Qt.AlignTop)
        fibula_surface_registration_tab_layout.setContentsMargins(12, 5, 10, 10)

        fibula_surface_registration_title = qt.QLabel(f'Register the Fibula: Surface')
        fibula_surface_registration_title.setStyleSheet("font-weight:bold; padding-bottom: 8px; padding-top: 10px")
        fibula_surface_registration_tab_layout.addWidget(fibula_surface_registration_title, 0, 0, 1, 4)

        fibula_surface_fiducial_instructions = qt.QLabel("Place the tip of the pointer against the surface of the patient’s "+
                                                         "mandible. When ready, press Start to begin placing "+
                                                         "fiducials at the pointer’s tip. Drag the NDI pointer along the surface "+
                                                         "of the mandible until a minimum of 75 fiducials are collected (where possible, "+
                                                         "keep the pointer perpendicular to the bone surface). When done, press Stop"+
                                                         "to stop the collection of surface fiducials. ")
        fibula_surface_fiducial_instructions.setWordWrap(True)
        fibula_surface_fiducial_instructions.setStyleSheet("padding-bottom: 10px")
        fibula_surface_registration_tab_layout.addWidget(fibula_surface_fiducial_instructions, 1, 0, 1, 4)

        # Count Number of Surface fiducials Collected on the Fibula
        self.fibula_surface_count_label = qt.QLabel(f'Number of surface fiducials placed: {self.fibula_surface_fiducials.GetNumberOfFiducials()}')
        self.fibula_surface_count_label.setStyleSheet('padding-bottom: 10px')
        fibula_surface_registration_tab_layout.addWidget(self.fibula_surface_count_label, 2, 0, 1, 4)

        # Start Fibula Surface Registration fiducial Collection
        self.fibula_start_surface = ui.create_button("Start Collection", "Drag pointer along fibula surface", True)
        fibula_surface_registration_tab_layout.addWidget(self.fibula_start_surface, 3, 0, 1, 2)
        self.fibula_start_surface.connect('clicked(bool)', self.on_fibula_start_surface)

        # Stop Fibula Surface Registration fiducial Collection
        self.fibula_stop_surface = ui.create_button("Stop Collection", "Pause collection", True)
        fibula_surface_registration_tab_layout.addWidget(self.fibula_stop_surface, 3, 2, 1, 2)
        self.fibula_stop_surface.connect('clicked(bool)', self.on_fibula_stop_surface)

        space = qt.QLabel("")
        space.setStyleSheet('margin-bottom: -10px')
        fibula_surface_registration_tab_layout.addWidget(space, 4, 0, 1, 4)

        # Remove Fibula Registration Surface fiducials
        self.remove_fibula_surface_fiducials = ui.create_button("🗑 Delete all", "Delete surface fiducials", True)
        fibula_surface_registration_tab_layout.addWidget(self.remove_fibula_surface_fiducials, 5, 0, 1, 4)
        self.remove_fibula_surface_fiducials.connect('clicked(bool)', self.on_remove_fibula_surface_fiducials)

        register_fibula_surface_error_instructions = qt.QLabel("Run Surface Registration: Press “Register Fibula” to run surface registration. If the "+
                                                               "error is greater than 1, delete the registration and repeat the above steps. ")
        register_fibula_surface_error_instructions.setStyleSheet("padding-top: 10px; font-weight: normal")
        register_fibula_surface_error_instructions.setWordWrap(True)
        fibula_surface_registration_tab_layout.addWidget(register_fibula_surface_error_instructions, 6, 0, 1, 4)

        # Show Fibula Surface Registration Error
        self.fibula_surface_error = qt.QLabel("Root mean square error: 0")
        self.fibula_surface_error.setStyleSheet('padding-bottom: 10px')
        fibula_surface_registration_tab_layout.addWidget(self.fibula_surface_error, 7, 0, 1, 4)

        # Calculate Fibula Surface Registration
        self.register_fibula_surface = ui.create_button("Register Fibula", "Run Surface Registration", True)
        fibula_surface_registration_tab_layout.addWidget(self.register_fibula_surface, 8, 0, 1, 3)
        self.register_fibula_surface.connect('clicked(bool)', self.on_register_fibula_surface)

        self.delete_fibula_surface = ui.create_button("🗑 Delete", "Delete Surface Registration", True)
        fibula_surface_registration_tab_layout.addWidget(self.delete_fibula_surface, 8, 3, 1, 1)
        self.delete_fibula_surface.connect('clicked(bool)', self.on_delete_fibula_surface)

        # VISUALLY VERIFY QUALITY OF FIBULA REGISTRATION
        # Place Fibula Registration Patient Fiducials
        fibula_registration_quality_tab = qt.QWidget()
        fibula_registration_quality_tab_layout = qt.QFormLayout(fibula_registration_quality_tab)

        fibula_registration_quality_title = qt.QLabel(f'Check Fibula Registration')
        fibula_registration_quality_title.setStyleSheet("font-weight:bold; padding-bottom: 8px; padding-top: 10px")
        fibula_registration_quality_tab_layout.addRow(fibula_registration_quality_title)

        self.check_fibula_registration_label = qt.QLabel("Check fibula registration by moving the probe over the surface "+
                                                         "of the fibula and verifying that the pointer model on screen is in "+
                                                         "the correct corresponding location. ")
        self.check_fibula_registration_label.setWordWrap(True)
        self.check_fibula_registration_label.setStyleSheet("padding-bottom: 10px")
        fibula_registration_quality_tab_layout.addRow(self.check_fibula_registration_label)

        self.good_mandible_registration = ui.create_button("✓ Good Registration")
        fibula_registration_quality_tab_layout.addRow(self.good_mandible_registration)
        self.good_mandible_registration.connect('clicked(bool)', self.on_next_module)

        self.redo_fibula_registration = ui.create_button("⭯ Redo Registration")
        fibula_registration_quality_tab_layout.addRow(self.redo_fibula_registration)
        self.redo_fibula_registration.connect('clicked(bool)', self.on_redo_fibula_registration)

        #Add to Tab Widget
        self.register_fibula_tabs = qt.QTabWidget()
        self.register_fibula_tabs.addTab(clip_fibula_tab, "Clip Fibula")
        self.register_fibula_tabs.addTab(fibula_registration_tab, "Register Fibula: Paired Point")
        self.register_fibula_tabs.addTab(fibula_surface_registration_tab, "Register Fibula: Surface")
        self.register_fibula_tabs.addTab(fibula_registration_quality_tab, "Quality of Fibula Registration")
        self.layout.addWidget(self.register_fibula_tabs, 0, 0)
        self.fibreg_tab_state = 0
        self.change_fibula_registration_tab_visibility(self.fibreg_tab_state)
        # print(RegisterFibula_Tabs.currentIndex)

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

    def get_nodes(self):
        self.fibula_CT_fiducials = ui.import_node('VirtualFidsF', 'vtkMRMLMarkupsFiducialNode')
        self.fibula_patient_fiducials = ui.import_node('PhysicalFidsF', 'vtkMRMLMarkupsFiducialNode')
        self.fibula_surface_fiducials = ui.import_node('SurfaceFidsF', 'vtkMRMLMarkupsFiducialNode')

        self.fibula_registration = ui.import_node('FibulaRegistration', 'vtkMRMLFiducialRegistrationWizardNode')
        self.fibula_surface_registration = ui.import_node('SurfaceRegistrationF', 'vtkMRMLLinearTransformNode')

        self.StylusTipToStylusRef = getNode('StylusTipToStylusRef')
        self.StylusRefToFibRef = ui.import_node('StylusRefToFibRef', 'vtkMRMLLinearTransformNode')
        self.FibRefToFib = ui.import_node('FibRefToFib', 'vtkMRMLLinearTransformNode')

        self.Fibula = getNode('Fibula')
        self.Pointer = getNode('Pointer')

        # try: self.Contour = getNode('Contour') 
        # except slicer.util.MRMLNodeNotFoundException: pass           #Just to turn off visibility 
        self.Contour = ui.retrieve_node('Contour')
        self.Resected = ui.retrieve_node("Resected")
        self.NonResected = ui.retrieve_node('NonResected')
        # try: self.Resected = getNode('Resected') 
        # except slicer.util.MRMLNodeNotFoundException: pass       #Just to turn off visibility
        # try: self.NonResected = getNode('NonResected')
        # except slicer.util.MRMLNodeNotFoundException: pass   #Just to turn off visibility

        self.GreenSlice = getNode('vtkMRMLSliceNodeGreen')      #Just to turn off visiblity
        self.YellowSlice = getNode('vtkMRMLSliceNodeYellow')    #Just to turn off visibility 
        self.RedSlice = getNode('vtkMRMLSliceNodeRed')          #Just to turn off visibility 

        self.RightCutFids = ui.retrieve_node("RightCutFids")
        self.LeftCutFids = ui.retrieve_node("LeftCutFids")
        # try: self.RightCutFids = getNode('RightCutFids')
        # except slicer.util.MRMLNodeNotFoundException: pass 
        # try: self.LeftCutFids = getNode('LeftCutFids') 
        # except slicer.util.MRMLNodeNotFoundException: pass 

        self.fibula_path = getNode('FibulaPath')

        self.WatchdogStylusFibula = getNode('Watchdog_StylusToFibula')

    #Control tab visibility and page state
    def change_fibula_registration_tab_visibility(self, state):
        if state == 0:
            self.register_fibula_tabs.setCurrentIndex(0)
            self.on_clip_fibula_tab()
        elif state == 1:
            self.register_fibula_tabs.setCurrentIndex(1)
            self.on_fibula_registration_tab()
        elif state == 2:
            self.register_fibula_tabs.setCurrentIndex(2)
            self.on_fibula_surface_registration_tab()
        elif state == 3: 
            self.register_fibula_tabs.setCurrentIndex(3)
            self.on_fibula_registration_quality_tab()

    #SET TAB STATES
    def on_clip_fibula_tab(self):
        self.register_fibula_tabs.setTabEnabled(0, True)
        self.register_fibula_tabs.setTabEnabled(1, False)
        self.register_fibula_tabs.setTabEnabled(2, False)
        self.register_fibula_tabs.setTabEnabled(3, False)
        self.GreenSlice.SetSliceVisible(0)
        self.YellowSlice.SetSliceVisible(0)
        self.RedSlice.SetSliceVisible(0)
        slicer.modules.models.logic().SetAllModelsVisibility(0)
        self.Fibula.SetDisplayVisibility(1)

    def on_fibula_registration_tab(self):
        self.register_fibula_tabs.setTabEnabled(0, False)
        self.register_fibula_tabs.setTabEnabled(1, True)
        self.register_fibula_tabs.setTabEnabled(2, False)
        self.register_fibula_tabs.setTabEnabled(3, False)
        slicer.modules.models.logic().SetAllModelsVisibility(0)
        self.GreenSlice.SetSliceVisible(0)
        self.YellowSlice.SetSliceVisible(0)
        self.RedSlice.SetSliceVisible(0)
        self.RightCutFids.SetDisplayVisibility(0)
        self.LeftCutFids.SetDisplayVisibility(0)

        getNode('Clipped Fibula').SetDisplayVisibility(1)
        self.Pointer.SetDisplayVisibility(1)
        self.fibula_CT_fiducials.SetDisplayVisibility(1)
        self.fibula_patient_fiducials.SetDisplayVisibility(1)
        self.fibula_surface_fiducials.SetDisplayVisibility(0)
        self.StylusTipToStylusRef.SetAndObserveTransformNodeID(self.StylusRefToFibRef.GetID())
        self.Pointer.SetAndObserveTransformNodeID(self.StylusTipToStylusRef.GetID())
        self.WatchdogStylusFibula.SetDisplayVisibility(1)

    def on_fibula_surface_registration_tab(self):
        self.register_fibula_tabs.setTabEnabled(0, False)
        self.register_fibula_tabs.setTabEnabled(1, False)
        self.register_fibula_tabs.setTabEnabled(2, True)
        self.register_fibula_tabs.setTabEnabled(3, False)

        slicer.modules.models.logic().SetAllModelsVisibility(0)
        self.Pointer.SetDisplayVisibility(1)
        getNode('Clipped Fibula').SetDisplayVisibility(1)
        self.GreenSlice.SetSliceVisible(0)
        self.YellowSlice.SetSliceVisible(0)
        self.RedSlice.SetSliceVisible(0)
        self.fibula_CT_fiducials.SetDisplayVisibility(0)
        self.fibula_patient_fiducials.SetDisplayVisibility(0)
        self.fibula_surface_fiducials.SetDisplayVisibility(1)

        self.WatchdogStylusFibula.SetDisplayVisibility(1)

    def on_fibula_registration_quality_tab(self):
        self.register_fibula_tabs.setTabEnabled(0, False)
        self.register_fibula_tabs.setTabEnabled(1, False)
        self.register_fibula_tabs.setTabEnabled(2, False)
        self.register_fibula_tabs.setTabEnabled(3, True)
        slicer.modules.models.logic().SetAllModelsVisibility(0)
        getNode('Clipped Fibula').SetDisplayVisibility(1)
        self.Pointer.SetDisplayVisibility(1)
        self.GreenSlice.SetSliceVisible(0)
        self.YellowSlice.SetSliceVisible(0)
        self.RedSlice.SetSliceVisible(0)
        self.fibula_CT_fiducials.SetDisplayVisibility(0)
        self.fibula_patient_fiducials.SetDisplayVisibility(0)
        self.fibula_surface_fiducials.SetDisplayVisibility(0)

        self.WatchdogStylusFibula.SetDisplayVisibility(1)

    def on_next_module(self):
        if self.fibreg_tab_state < 3:
            self.fibreg_tab_state = self.fibreg_tab_state + 1
            self.change_fibula_registration_tab_visibility(self.fibreg_tab_state)
            print(self.fibreg_tab_state)
        else:
            slicer.util.selectModule('CalculateVSP')
            dir = os.path.dirname(getNode('MandiblePath').GetText())+"\\SlicerFiles"
            # ms.save_scene(dir, "3_RegFib")
            self.WatchdogStylusFibula.SetDisplayVisibility(0)

    def on_previous_module(self):
        if self.fibreg_tab_state > 0:
            self.fibreg_tab_state = self.fibreg_tab_state - 1
            self.change_fibula_registration_tab_visibility(self.fibreg_tab_state)
            print(self.fibreg_tab_state)
        elif self.fibreg_tab_state == 0:
            slicer.util.selectModule('ResectMandible')
            #self.prev_button.setEnabled(0)

    def on_save(self):
        dir = os.path.dirname(getNode('MandiblePath').GetText())+"\\SlicerFiles"
        ms.save_scene(dir, "3_RegisterFibula"+str(self.fibreg_tab_state))

    def on_clip_fibula(self):
        self.logic.delayDisplay("Clipping Fibula")
        self.genVSP = vsp.connect_JVM()
        input_path = self.fibula_path.GetText()
        self.output_path = os.path.dirname(input_path)+"\\ClippedFibula_Donor.stl"
        self.TCW_Transform = self.genVSP.prepareFibula(input_path, self.output_path, int(self.knee_joint_end.text), int(self.ankle_joint_end.text))
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
        clipped_fibula.GetModelDisplayNode().SetColor(1, 0.9569, 0.8196)
        clipped_fibula.GetModelDisplayNode().VisibilityOn()
        print("Imported fibula")
        self.TCW = getNode("TCW")
        clipped_fibula.SetAndObserveTransformNodeID(self.TCW.GetID())
        slicer.vtkSlicerTransformLogic().hardenTransform(clipped_fibula)
        getNode('Fibula').GetDisplayNode().SetVisibility(False)
        self.on_next_module()

    #CONTROLLER
    def on_place_fibula_CT_fiducial(self):
        register.place_CT_fiducial(self.fibula_CT_fiducials)
        self.fibula_CT_fiducials_label.text = (f'Number of fiducials placed: '
                                        f'{self.fibula_CT_fiducials.GetNumberOfFiducials() + 1}')

    # Remove Fibula CT fiducial
    def on_remove_fibula_CT_fiducial(self):
        register.remove_CT_fiducials(self.fibula_CT_fiducials)
        self.fibula_CT_fiducials_label.text = (f'Number of fiducials placed: '
                                        f'{self.fibula_CT_fiducials.GetNumberOfFiducials()}')

    # Place Fibula Patient fiducial
    def on_place_fibula_patient_fiducial(self):
        register.place_patient_fiducial(self.fibula_patient_fiducials, self.StylusTipToStylusRef)
        self.physical_fibula_fiducials_label.text = (f'Number of fiducials placed: '
                                              f'{self.fibula_patient_fiducials.GetNumberOfFiducials()}')

    # Remove Fibula Patient fiducial
    def on_remove_fibula_patient_fiducial(self):
        register.remove_patient_fiducials(self.fibula_patient_fiducials, self.StylusRefToFibRef)
        self.physical_fibula_fiducials_label.text = (f'Number of fiducials placed: '
                                              f'{self.fibula_patient_fiducials.GetNumberOfFiducials()}')

    def register_fibula_paired_point(self):
        error = register.run_registration(self.fibula_registration,
                                    self.fibula_CT_fiducials,
                                    self.fibula_patient_fiducials,
                                    self.FibRefToFib,
                                    self.StylusRefToFibRef)
        self.register_fibula_error.setText(f'Root mean square error: {error}')

    def delete_fibula_paired_point(self):
        delete = register.delete_registration(self.StylusRefToFibRef)
        if delete:
            self.register_fibula_error.setText(f'Root mean square error: ')
            print("Deleted registration")

    # Start timer for collecting surface points every n seconds
    def on_fibula_start_surface(self):
        self.f_lastFid = 0
        self.f_timer = qt.QTimer()
        self.f_timer.timeout.connect(self.collect_fibula_surface_fiducials_timer)
        self.f_timer.setInterval(100)
        self.f_timer.start()
        print("Started")

    # Link between logic to place fiducial and timer starter
    def collect_fibula_surface_fiducials_timer(self):
        self.f_currentFid = self.f_lastFid + 1
        register.place_patient_fiducial(self.fibula_surface_fiducials, self.StylusTipToStylusRef)
        self.f_lastFid = self.f_currentFid
        self.fibula_surface_count_label.setText(f'Number of surface fiducials placed: {self.fibula_surface_fiducials.GetNumberOfFiducials()}')
        return self.f_currentFid

    # Stop timer for collecting surface points every n seconds
    def on_fibula_stop_surface(self):
        self.f_timer.stop()
        print("Paused")
        self.fibula_surface_count_label.setText(f'Number of surface fiducials placed: {self.fibula_surface_fiducials.GetNumberOfFiducials()}')

    # Remove Fibula Surface fiducial
    def on_remove_fibula_surface_fiducials(self):
        register.remove_surface_fiducials(self.fibula_surface_fiducials)
        self.fibula_surface_count_label.setText(f'Number of surface fiducials placed: {self.fibula_surface_fiducials.GetNumberOfFiducials()}')

    def on_register_fibula_surface(self):
        max_iterations = 100
        register.run_surface_registration(self.fibula_surface_fiducials, self.Fibula, 
                                          self.fibula_surface_registration, max_iterations)
        surf_error = register.compute_mean_distance(self.fibula_surface_fiducials,
                                                    self.Fibula, self.fibula_surface_registration,
                                                    self.FibRefToFib)
        self.fibula_surface_error.setText(f'Root mean square error: {surf_error}')

    def on_delete_fibula_surface(self):
        delete = register.delete_surface_registration(self.FibRefToFib)
        if delete:
            self.fibula_surface_error.setText(f'Root mean square error: ')
            print("Registration deleted")

    def on_redo_fibula_registration(self):
        self.fibreg_tab_state=1
        self.change_fibula_registration_tab_visibility(self.fibreg_tab_state)
        self.on_remove_fibula_CT_fiducial()
        self.on_remove_fibula_patient_fiducial()
        self.on_remove_fibula_surface_fiducials()
        self.fibula_surface_count_label.setText(f'Number of surface fiducials placed: {self.fibula_surface_fiducials.GetNumberOfFiducials()}')
        self.delete_fibula_paired_point()
        self.on_delete_fibula_surface()

class RegisterFibulaLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)

class RegisterFibulaTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.test_RegisterFibula1()

    def test_RegisterFibula1(self):
        self.delayDisplay("Start test")
        logic = RegisterFibulaLogic()
        self.delayDisplay("Test passed")