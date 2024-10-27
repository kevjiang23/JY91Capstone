import os
import unittest
import logging
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin, getNode
import re

import ManageSlicer as ms
import ManageUI as ui

from ManageRegistration import registration as register
from ManageReconstruction import resection as resect

import numpy as np 

class ResectMandible(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "2. Resect Mandible"
        self.parent.categories = ["Mandibular Reconstruction"]
        self.parent.dependencies = []
        self.parent.contributors = ["Melissa Yu (UBC)"]
        self.parent.helpText = ""
        self.parent.acknowledgementText = ""

class ResectMandibleWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)
        self.logic = None

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.logic = ResectMandibleLogic()
        self.modelLogic = slicer.vtkSlicerModelsLogic()
        self.volumeResliceLogic = slicer.modules.volumereslicedriver.logic()

        self.get_nodes()
        self.set_slicer_scene()
        self.connectPlaneToProbe(self.StylusTipToStylusRef, self.RedSlice)

        #CONTOUR MANDIBLE
        # RegisterMandible_TabLayout = qt.QGridLayout(RegisterMandible_Tabs)
        mandible_contour_tab = qt.QWidget()
        mandible_contour_tab_layout = qt.QFormLayout(mandible_contour_tab)
        mandible_contour_tab_layout.setAlignment(qt.Qt.AlignTop)

        mandible_contour_title = qt.QLabel(f'Check Mandible Contour')
        mandible_contour_title.setStyleSheet("font-weight:bold; padding-bottom: 8px; padding-top: 10px")
        mandible_contour_tab_layout.addRow(mandible_contour_title)

        mandible_contour_instructions = \
            qt.QLabel("Move the pointer against the surface of the patient’s mandible to visualize the corresponding "+
                      "CT scans at each location. Rotate the pointer around its long axis to change the view angle. Adjust the "+
                      "contour fiducials, if necessary. Proceed to the next module when you are happy with the contour.  \n")
        #MandibleContour_InstructionLabel.setStyleSheet("font-size: 9pt")
        mandible_contour_instructions.setWordWrap(True)
        mandible_contour_tab_layout.addWidget(mandible_contour_instructions)

        contour_complete_button = ui.create_button("Contour Complete")
        mandible_contour_tab_layout.addRow(contour_complete_button)
        contour_complete_button.connect('clicked(bool)', self.on_next_module)

        #RESECT MANDIBLE
        #Place Mandible Registration Patient Fiducials
        mandible_resection_tab = qt.QWidget()
        mandible_resection_tab_layout = qt.QGridLayout(mandible_resection_tab)
        mandible_resection_tab_layout.setAlignment(qt.Qt.AlignTop)

        mandible_resection_title = qt.QLabel(f'Resect the Mandible')
        mandible_resection_title.setStyleSheet("font-weight:bold; padding-bottom: 8px; padding-top: 10px")
        mandible_resection_tab_layout.addWidget(mandible_resection_title)

        mandible_resection_instructions = \
            qt.QLabel("Plan the locations for the mandible osteotomies using the CT scans. When satisfied, resect the "+
                      "diseased portion of the patient’s mandible.\n")
        mandible_resection_instructions.setWordWrap(True)
        mandible_resection_tab_layout.addWidget(mandible_resection_instructions)

        complete_resection_button = ui.create_button("Resection Complete")
        mandible_resection_tab_layout.addWidget(complete_resection_button)
        complete_resection_button.connect('clicked(bool)', self.on_next_module)

        #REGISTER CUT PLANES
        register_cut_planes_tab = qt.QWidget()
        register_cut_planes_tab_layout = qt.QGridLayout(register_cut_planes_tab)
        register_cut_planes_tab_layout.setAlignment(qt.Qt.AlignTop)
        #scrollbar = qt.QScrollArea(widgetResizable=True)
        #scrollbar.setWidget(RegisterCutPlanes_Tab)

        register_planes_title = qt.QLabel(f'Register the Osteotomy Planes')
        register_planes_title.setStyleSheet("font-weight:bold; padding-bottom: 8px; padding-top: 10px")
        register_cut_planes_tab_layout.addWidget(register_planes_title, 0, 0, 1, 4)

        #RIGHT CUT FIDUCIALS
        right_cut_instructions = \
            qt.QLabel("Now that the mandible resection is complete, we must register those planes to the virtual "+
                      "model of the mandible. Starting with the right cut plane, place the tip of the pointer on "+
                      "the surface of the patient’s mandible osteotomy. Press the “Place Right Cut Fiducial” button "+
                      "to place a fiducial at the pointer tip. Move the pointer to another location on the cut surface "+
                      "and press the “Place Right Cut Fiducial” button. Repeat these steps until a minimum of three "+
                      "fiducials are placed on the right plane. Then, repeat these steps with the left cut plane.  \n\n"+
                      "Once all fiducials are placed, press “Register Cut Planes” to apply the planes to the mandible model. "+
                      "Verify that the purple portion represents the remaining mandible, and the yellow portion represents "+
                      "the removed mandible section.\n")
        right_cut_instructions.setWordWrap(True)
        right_cut_instructions.adjustSize()
        register_cut_planes_tab_layout.addWidget(right_cut_instructions, 1, 0, 1, 4)

        right_cut_title = qt.QLabel("Register Right Mandible Osteotomies")
        right_cut_title.setStyleSheet("font-weight: bold")
        register_cut_planes_tab_layout.addWidget(right_cut_title, 2, 0, 1, 4)

        self.right_fiducials_label = qt.QLabel(f'Number of fiducials placed: {self.RightCutFids.GetNumberOfFiducials()}')
        register_cut_planes_tab_layout.addWidget(self.right_fiducials_label, 3, 0, 1, 4)

        self.place_right_fiducials = ui.create_button("Place Right Cut Fiducial", "Place fiducial on osteotomy surface", True)
        register_cut_planes_tab_layout.addWidget(self.place_right_fiducials, 4, 0, 1, 4)
        self.place_right_fiducials.connect('clicked(bool)', self.on_place_right_cut_fiducials)

        self.remove_right_fiducials = ui.create_button("Delete Right Cut Fiducials", "Delete all fiducials", True)
        register_cut_planes_tab_layout.addWidget(self.remove_right_fiducials, 5, 0, 1, 4)
        self.remove_right_fiducials.connect('clicked(bool)', self.on_delete_right_cut_fiducials)

        self.show_right = qt.QCheckBox("Show Right Cut Plane")
        if self.GreenSlice.GetSliceVisible() != 0:
            self.show_right.setChecked(True)
        else: 
            self.show_right.setChecked(False)
        self.show_right.stateChanged.connect(lambda: self.on_show_right())
        register_cut_planes_tab_layout.addWidget(self.show_right, 6, 0, 1, 4)

        #LEFT CUT FIDUCIALS
        left_cut_title = qt.QLabel("Register Left Mandible Osteotomies")
        left_cut_title.setStyleSheet("font-weight: bold; padding-top: 15px")
        register_cut_planes_tab_layout.addWidget(left_cut_title, 7, 0, 1, 4)

        self.left_fiducials_label = qt.QLabel(f'Number of fiducials placed: {self.LeftCutFids.GetNumberOfFiducials()}')
        register_cut_planes_tab_layout.addWidget(self.left_fiducials_label, 8, 0, 1, 4)

        self.place_left_fiducials = ui.create_button("Place Left Cut Fiducial", "Place fiducial on osteotomy surface", True)
        register_cut_planes_tab_layout.addWidget(self.place_left_fiducials, 9, 0, 1, 4)
        self.place_left_fiducials.connect('clicked(bool)', self.on_place_left_cut_fiducials)

        self.remove_left_fiducials = ui.create_button("Delete Left Cut Fiducials", "Delete all fiducials", True)
        register_cut_planes_tab_layout.addWidget(self.remove_left_fiducials, 10, 0, 1, 4)
        self.remove_left_fiducials.connect('clicked(bool)', self.on_delete_left_cut_fiducials)

        self.show_left = qt.QCheckBox("Show Left Cut Plane")
        if self.YellowSlice.GetSliceVisible() != 0: 
            self.show_left.setChecked(True)
        else: 
            self.show_left.setChecked(False)
        self.show_left.stateChanged.connect(lambda: self.on_show_left())
        register_cut_planes_tab_layout.addWidget(self.show_left, 11, 0, 1, 4)

        space = qt.QLabel("")
        space.setStyleSheet("padding-top: 3px")
        register_cut_planes_tab_layout.addWidget(space, 12, 0, 1, 4)

        self.register_cut_planes = ui.create_button("Register Cut Planes", "Set Cut Planes", True)
        register_cut_planes_tab_layout.addWidget(self.register_cut_planes, 13, 0, 1, 4)
        self.register_cut_planes.connect('clicked(bool)', self.on_clip_mandible)

        self.delete_cut_planes = ui.create_button("Delete Resection", "Delete Cut Planes", True)
        register_cut_planes_tab_layout.addWidget(self.delete_cut_planes, 14, 0, 1, 4)
        self.delete_cut_planes.connect('clicked(bool)', self.on_delete_planes)

        normal_control = ctk.ctkCollapsibleButton()
        normal_control.collapsed = 1
        normal_control.text = "Control Slice Plane Normals"
        register_cut_planes_tab_layout.addWidget(normal_control, 15, 0, 1, 4)
        normal_layout = qt.QFormLayout(normal_control)

        self.autoflip_normal = qt.QCheckBox("Automatically check direction of slice normals")
        self.autoflip_normal.setChecked(True)
        self.autoflip_normal.stateChanged.connect(lambda: self.on_control_normal())
        normal_layout.addRow(self.autoflip_normal)

        green_normal = ms.get_vtkplane_from_slice(getNode('vtkMRMLSliceNodeGreen')).GetNormal()
        self.green_label = qt.QLabel(f'Right Cut Plane Normal     {np.round(green_normal[0],2), np.round(green_normal[1],2), np.round(green_normal[2],2)} ')
        self.green_label.setEnabled(False)

        self.flip_green = ui.create_button("Flip Right Cut Normal")
        self.flip_green.connect('clicked(bool)', self.on_flip_green)
        self.flip_green.setEnabled(False)
        normal_layout.addRow(self.green_label, self.flip_green)

        yellow_normal = ms.get_vtkplane_from_slice(getNode('vtkMRMLSliceNodeYellow')).GetNormal()
        self.yellow_label= qt.QLabel(f'Left Cut Plane Normal   {np.round(yellow_normal[0], 2), np.round(yellow_normal[1], 2), np.round(yellow_normal[2], 2)}')
        self.yellow_label.setEnabled(False)
        self.flip_yellow = ui.create_button("Flip Left Cut Normal")
        self.flip_yellow.connect('clicked(bool)', self.on_flip_yellow)
        self.flip_yellow.setEnabled(False)
        normal_layout.addRow(self.yellow_label, self.flip_yellow)

        update_green_plane = ui.create_button("Update green slice")
        update_green_plane.connect('clicked(bool)', self.on_update_green)
        normal_layout.addRow(update_green_plane)
        update_yellow_plane = ui.create_button("Update yellow slice")
        update_yellow_plane.connect('clicked(bool)', self.on_update_yellow)
        normal_layout.addRow(update_yellow_plane)

        plane_control = ctk.ctkCollapsibleButton()
        plane_control.collapsed = 1
        plane_control.text = "Import and export resection planes"
        register_cut_planes_tab_layout.addWidget(plane_control, 16, 0, 1, 4)
        plane_control_layout = qt.QFormLayout(plane_control)
        # qt.QFormLayout.FieldsStayAtSizeHint = 0
        
        self.plane_path = ctk.ctkPathLineEdit()
        import_planes = ui.create_button("Import Planes")
        #plane_control_layout.addRow(plane_path)
        plane_control_layout.addRow(self.plane_path, import_planes)
        import_planes.connect('clicked(bool)', self.on_import_planes)
        
        self.export_planes = ui.create_button("Export resection planes")
        plane_control_layout.addRow(self.export_planes)
        self.export_planes.connect('clicked(bool)', self.on_export_planes)

        #Add to Tab Widget
        self.resect_mandible_tabs = qt.QTabWidget()
        self.resect_mandible_tabs.setElideMode(qt.Qt.ElideNone)
        self.resect_mandible_tabs.addTab(mandible_contour_tab, "Contour Mandible")
        self.resect_mandible_tabs.addTab(mandible_resection_tab, "Resect Mandible")
        self.resect_mandible_tabs.addTab(register_cut_planes_tab, "Register Cut Planes")
        self.layout.addWidget(self.resect_mandible_tabs, 0, 0)
        self.resect_mandible_tab_state = self.resect_mandible_tabs.currentIndex
        # self.changeMandRegTabVisibility(self.mandreg_tab_state)
        # print(RegisterMandible_Tabs.currentIndex)

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

        self.on_contour_mandible_tab()

        save_box = qt.QGroupBox()
        save_button_layout = qt.QHBoxLayout(save_box)
        self.save_button = ui.create_button("Save scene")
        self.save_button.connect('clicked(bool)', self.on_save)
        save_button_layout.addWidget(self.save_button)
        self.layout.addWidget(save_box)

    def set_slicer_scene(self):
        self.layoutManager = slicer.app.layoutManager()
        self.resect_mandible_scene_layout = ("<layout type=\"horizontal\" split=\"true\" >"
          " <item splitSize=\"500\">"
          "  <view class=\"vtkMRMLViewNode\" singletontag=\"1\">"
          "   <property name=\"viewlabel\" action=\"default\">1</property>"
          "  </view>"
          " </item>"
          " <item splitSize=\"500\">"
          "  <view class=\"vtkMRMLSliceNode\" singletontag=\"Red\">"
          "    <property name=\"orientation\" action=\"default\">Axial</property>"
          "    <property name=\"viewlabel\" action=\"default\">R</property>"
          "    <property name=\"viewcolor\" action=\"default\">#F34A33</property>"
          "  </view>"
          " </item>"
          "</layout>")
        self.resect_layout_ID=705
        self.layoutManager.layoutLogic().GetLayoutNode().AddLayoutDescription(self.resect_layout_ID, self.resect_mandible_scene_layout)
        self.layoutManager.setLayout(self.resect_layout_ID)

    def get_nodes(self):
        self.ClipNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLClipModelsNode')
        #Fiducial List
        self.mandible_CT_fiducials = ui.import_node('VirtualFidsM', 'vtkMRMLMarkupsFiducialNode')
        self.mandible_patient_fiducials = ui.import_node('PhysicalFidsM', 'vtkMRMLMarkupsFiducialNode')
        self.mandible_surface_fiducials = ui.import_node('SurfaceFidsM', 'vtkMRMLMarkupsFiducialNode')

        #self.mandible_registration = getNode('MandibleRegistration')
        self.mandible_registration = ui.import_node('MandibleRegistration', 'vtkMRMLFiducialRegistrationWizardNode')
        self.mandible_surface_registration = ui.import_node('SurfaceRegistrationM', 'vtkMRMLLinearTransformNode')

        self.StylusTipToStylusRef = ui.import_node('StylusTipToStylusRef')
        self.StylusRefToMandRef = ui.import_node('StylusRefToMandRef', 'vtkMRMLLinearTransformNode')
        self.MandRefToMand = ui.import_node('MandRefToMand', 'vtkMRMLLinearTransformNode')
        self.Pointer = getNode('Pointer')
  
        try:
            self.Mandible = getNode('Mandible')
            self.MandibleDisp = self.Mandible.GetModelDisplayNode()
            self.MandibleDisp.SetClipping(1)
            print("Mandible retrieved")
        except slicer.util.MRMLNodeNotFoundException: 
            print("No Mandible in scene")    

        try: 
            self.Fibula = getNode('Fibula')
        except slicer.util.MRMLNodeNotFoundException: 
            print("No Fibula in scene")

        self.Contour = ui.import_node('Contour', 'vtkMRMLMarkupsFiducialNode')
        self.RightCutFids = ui.import_node('RightCutFids', 'vtkMRMLMarkupsFiducialNode')
        self.LeftCutFids = ui.import_node('LeftCutFids', 'vtkMRMLMarkupsFiducialNode')

        self.GreenSlice = getNode('vtkMRMLSliceNodeGreen')
        self.YellowSlice = getNode('vtkMRMLSliceNodeYellow')
        self.RedSlice = getNode('vtkMRMLSliceNodeRed')

        self.WatchdogStylusMandible = getNode('Watchdog_StylusToMandible')

    def connectPlaneToProbe(self, probe_transform, slice):
        slice.SetSliceVisible(1)
        self.volumeResliceLogic.SetDriverForSlice(probe_transform.GetID(), slice)
        self.volumeResliceLogic.SetModeForSlice(4, slice)
        self.volumeResliceLogic.SetRotationForSlice(-90, slice)
        self.volumeResliceLogic.SetFlipForSlice(False, slice)

    #Control tab visibility and page state
    def change_resect_mandible_tab_visibility(self, state):
        self.resect_mandible_tabs.setCurrentIndex(state)
        if state == 0:
            #self.RegisterMandible_Tabs.setCurrentIndex(0)
            self.on_contour_mandible_tab()
        elif state == 1:
            #self.prev_button.setEnabled(1)
            #self.RegisterMandible_Tabs.setCurrentIndex(1)
            self.on_resect_mandible_tab()
        elif state == 2:
            #self.RegisterMandible_Tabs.setCurrentIndex(2)
            self.on_register_cut_planes_tab()

    #SET TAB STATES
    def on_contour_mandible_tab(self):
        self.resect_mandible_tabs.setTabEnabled(0, True)
        self.resect_mandible_tabs.setTabEnabled(1, False)
        self.resect_mandible_tabs.setTabEnabled(2, False)
        self.resect_mandible_tabs.setTabEnabled(3, False)
        self.Contour.SetDisplayVisibility(1)
        self.Mandible.SetDisplayVisibility(1)
        self.Fibula.SetDisplayVisibility(0)
        self.mandible_CT_fiducials.SetDisplayVisibility(0)
        self.mandible_patient_fiducials.SetDisplayVisibility(0)
        self.mandible_surface_fiducials.SetDisplayVisibility(0)

    def on_resect_mandible_tab(self):
        self.resect_mandible_tabs.setTabEnabled(0, False)
        self.resect_mandible_tabs.setTabEnabled(1, True)
        self.resect_mandible_tabs.setTabEnabled(2, False)
        self.resect_mandible_tabs.setTabEnabled(3, False)
        self.Mandible.SetDisplayVisibility(1)
        #self.Pointer.SetDisplayVisibility(1)
        self.Contour.SetDisplayVisibility(0)
        self.mandible_CT_fiducials.SetDisplayVisibility(0)
        self.mandible_patient_fiducials.SetDisplayVisibility(0)
        self.mandible_surface_fiducials.SetDisplayVisibility(0)
        #self.StylusTipToStylusRef.SetAndObserveTransformNodeID(self.StylusRefToMandRef.GetID())
        self.Pointer.SetAndObserveTransformNodeID(self.StylusTipToStylusRef.GetID())
        self.RightCutFids.SetDisplayVisibility(0)
        self.LeftCutFids.SetDisplayVisibility(0)
        #slicer.app.layoutManager().setLayout(4)

    def on_register_cut_planes_tab(self):
        self.resect_mandible_tabs.setTabEnabled(0, False)
        self.resect_mandible_tabs.setTabEnabled(1, False)
        self.resect_mandible_tabs.setTabEnabled(2, True)
        self.resect_mandible_tabs.setTabEnabled(3, False)
        self.mandible_CT_fiducials.SetDisplayVisibility(0)
        self.mandible_patient_fiducials.SetDisplayVisibility(0)
        self.mandible_surface_fiducials.SetDisplayVisibility(0)
        self.Contour.SetDisplayVisibility(0)
        #self.StylusTipToStylusRef.SetAndObserveTransformNodeID(self.StylusRefToMandRef.GetID())
        self.RightCutFids.SetDisplayVisibility(1)
        self.LeftCutFids.SetDisplayVisibility(1)
        slicer.app.layoutManager().setLayout(4)
        self.WatchdogStylusMandible.SetDisplayVisibility(1)

    def on_next_module(self):
        if self.resect_mandible_tab_state < 2:
            print(self.resect_mandible_tab_state)
            self.resect_mandible_tab_state = self.resect_mandible_tab_state + 1
            self.change_resect_mandible_tab_visibility(self.resect_mandible_tab_state)
            print(self.resect_mandible_tab_state)
        else:
            self.WatchdogStylusMandible.SetDisplayVisibility(0)
            slicer.util.selectModule('RegisterFibula')
            

    def on_previous_module(self):
        if self.resect_mandible_tab_state > 0:
            self.resect_mandible_tab_state = self.resect_mandible_tab_state - 1
            self.change_resect_mandible_tab_visibility(self.resect_mandible_tab_state)
            print(self.resect_mandible_tab_state)
        elif self.resect_mandible_tab_state == 0:
            slicer.util.selectModule('RegisterMandible')

    def on_save(self):
        dir = os.path.dirname(getNode('MandiblePath').GetText())+"\\SlicerFiles"
        ms.save_scene(dir, "2_ResectMandible"+str(self.resect_mandible_tab_state))


    #CONTROLLER
    def on_place_right_cut_fiducials(self):
        #register.place_patient_fiducial(self.RightCutFids, self.StylusTipToStylusRef)
        register.place_patient_fiducial(self.RightCutFids, self.StylusTipToStylusRef)
        self.right_fiducials_label.setText(f'Number of fiducials placed: {self.RightCutFids.GetNumberOfFiducials()}')
        if self.RightCutFids.GetNumberOfFiducials() > 2:
            ms.update_slice_plane(self.RightCutFids, self.GreenSlice)
            # self.GreenSlice.SetSliceVisible(1)
            self.ClipNode.SetGreenSliceClipState(0)
            if self.LeftCutFids.GetNumberOfFiducials() > 2:
                if self.autoflip_normal.isChecked():
                    self.greenNormal, self.greenOrigin, self.yellowNormal, self.yellowOrigin = \
                        resect.check_plane_normal_direction(self.GreenSlice, self.YellowSlice)
                self.YellowSlice.SetSliceVisible(1)
                self.show_left.setChecked(1)
                self.GreenSlice.SetSliceVisible(1)
                self.show_right.setChecked(1)

    def on_delete_right_cut_fiducials(self):
        register.remove_patient_fiducials(self.RightCutFids, self.StylusRefToMandRef)
        self.right_fiducials_label.setText(f'Number of fiducials placed: {self.RightCutFids.GetNumberOfFiducials()}')
        self.StylusRefToMandRef.SetAndObserveTransformNodeID(self.MandRefToMand.GetID())
        self.GreenSlice.SetSliceVisible(0)
        self.show_right.setChecked(0)

    def on_update_green(self):
        ms.update_slice_plane(self.RightCutFids, self.GreenSlice)
        if self.autoflip_normal.isChecked():
            self.greenNormal, self.greenOrigin, self.yellowNormal, self.yellowOrigin = \
                    resect.check_plane_normal_direction(self.GreenSlice, self.YellowSlice)
        self.GreenSlice.SetSliceVisible(1)
        self.show_right.setChecked(1)

    def on_place_left_cut_fiducials(self):
        #register.place_patient_fiducial(self.LeftCutFids, self.StylusTipToStylusRef)
        register.place_patient_fiducial(self.LeftCutFids, self.StylusTipToStylusRef)
        self.left_fiducials_label.setText(f'Number of fiducials placed: {self.LeftCutFids.GetNumberOfFiducials()}')
        if self.LeftCutFids.GetNumberOfFiducials() > 2: 
            ms.update_slice_plane(self.LeftCutFids, self.YellowSlice)
            if self.RightCutFids.GetNumberOfFiducials() > 2:
                if self.autoflip_normal.isChecked():
                    self.greenNormal, self.greenOrigin, self.yellowNormal, self.yellowOrigin = \
                        resect.check_plane_normal_direction(self.GreenSlice, self.YellowSlice)
                self.YellowSlice.SetSliceVisible(1)
                self.show_left.setChecked(1)
                self.GreenSlice.SetSliceVisible(1)
                self.show_right.setChecked(1)
            #self.ClipNode.SetYellowSliceClipState(2)
            #self.ClipNode.SetGreenSliceClipState(2)
            
    def on_delete_left_cut_fiducials(self):
        register.remove_patient_fiducials(self.LeftCutFids, self.StylusRefToMandRef)
        self.left_fiducials_label.setText(f'Number of fiducials placed: {self.LeftCutFids.GetNumberOfFiducials()}')
        self.StylusRefToMandRef.SetAndObserveTransformNodeID(self.MandRefToMand.GetID())
        self.YellowSlice.SetSliceVisible(0)
        self.show_left.setChecked(0)

    def on_update_yellow(self):
        ms.update_slice_plane(self.LeftCutFids, self.YellowSlice)
        if self.autoflip_normal.isChecked():
            self.greenNormal, self.greenOrigin, self.yellowNormal, self.yellowOrigin = \
                    resect.check_plane_normal_direction(self.GreenSlice, self.YellowSlice)
        self.YellowSlice.SetSliceVisible(1)
        self.show_left.setChecked(1)

    def on_clip_mandible(self):
        #ms.update_slice_plane(self.RightCutFids, self.GreenSlice)
        #ms.update_slice_plane(self.LeftCutFids, self.YellowSlice)
        #self.greenNormal, self.greenOrigin, self.yellowNormal, self.yellowOrigin = \
        #    resect.checkPlaneNormalDirection(self.GreenSlice, self.YellowSlice)

        #self.mandibleClipPlanes, self.resection, self.nonresected = \
        #    resect.clip_mandible_button_clicked(self.Mandible, self.modelLogic)
        
        green_plane = ms.get_vtkplane_from_slice(self.GreenSlice)
        green_origin = green_plane.GetOrigin()
        yellow_plane = ms.get_vtkplane_from_slice(self.YellowSlice)
        yellow_origin = yellow_plane.GetOrigin()

        if green_origin[0] < 0 and yellow_origin[0] < 0:
            print('Lateral cut - Yellow')
            mid_plane = vtk.vtkPlane()
            mid_plane.SetOrigin(0,0,0)
            mid_plane.SetNormal(-1,0,0)
            self.lateral_clip_mandible(green_plane, yellow_plane, mid_plane)
        elif green_origin[0] > 0 and yellow_origin[0] > 0:
            print('Lateral cut - Green')
            mid_plane = vtk.vtkPlane()
            mid_plane.SetOrigin(0,0,0)
            mid_plane.SetNormal(1,0,0)
            self.lateral_clip_mandible(green_plane, yellow_plane, mid_plane)
        else: 
            print('Regular cut')
            self.alt_clip_mandible_fn(self.GreenSlice, self.YellowSlice)
        print("Resection Complete")
        self.RightCutFids.SetDisplayVisibility(0)
        self.LeftCutFids.SetDisplayVisibility(0)
        self.Mandible.SetDisplayVisibility(0)
        #self.export_button.setEnabled(True)
    
    def lateral_clip_mandible(self, green_plane, yellow_plane, mid_plane):
        #Resected Section
        lateral_collection = vtk.vtkPlaneCollection()
        lateral_collection.AddItem(mid_plane)
        lateral_collection.AddItem(green_plane)
        lateral_collection.AddItem(yellow_plane)

        lateral_clip = vtk.vtkClipClosedSurface()
        lateral_clip.SetClippingPlanes(lateral_collection)
        lateral_clip.SetInputData(getNode('Mandible').GetPolyData())
        lateral_clip.SetGenerateFaces(1)
        lateral_clip.Update()
        lateral_resected_section = lateral_clip.GetOutput()
        resection_model = ms.create_model(lateral_resected_section, "Resected", [1,1,0.5])
        
        #print(f'Green: {green_plane.GetNormal()}')
        #print(f'Yellow: {yellow_plane.GetNormal()}')
        #print(f'Mid: {mid_plane.GetNormal()}')
        #NonResected Section
        green_normal = green_plane.GetNormal()
        green_plane.SetNormal(-green_normal[0], -green_normal[1], -green_normal[2])
        yellow_normal = yellow_plane.GetNormal()
        yellow_plane.SetNormal(-yellow_normal[0], -yellow_normal[1], -yellow_normal[2])

        lateral_collection2 = vtk.vtkPlaneCollection()
        lateral_collection2.AddItem(green_plane)
        #lateral_collection2.AddItem(yellow_plane)
        lateral_collection2.AddItem(mid_plane)
        print(f'Green: {green_plane.GetNormal()}')
        print(f'Yellow: {yellow_plane.GetNormal()}')
        print(f'Mid: {mid_plane.GetNormal()}')

        lateral_clip2 = vtk.vtkClipClosedSurface()
        lateral_clip2.SetClippingPlanes(lateral_collection2)
        lateral_clip2.SetInputData(getNode('Mandible').GetPolyData())
        lateral_clip2.SetGenerateFaces(1)
        lateral_clip2.Update()
        nonresect1 = lateral_clip2.GetOutput()

        lateral_collection4 = vtk.vtkPlaneCollection()
        lateral_collection4.AddItem(yellow_plane)
        lateral_collection4.AddItem(mid_plane)

        lateral_clip4 = vtk.vtkClipClosedSurface()
        lateral_clip4.SetClippingPlanes(lateral_collection4)
        lateral_clip4.SetInputData(getNode('Mandible').GetPolyData())
        lateral_clip4.SetGenerateFaces(1)
        lateral_clip4.Update()
        nonresect3 = lateral_clip4.GetOutput()

        mid_normal = mid_plane.GetNormal()
        mid_plane.SetNormal(-mid_normal[0], -mid_normal[1], -mid_normal[2])
        lateral_collection3 = vtk.vtkPlaneCollection()
        lateral_collection3.AddItem(mid_plane)

        lateral_clip3 = vtk.vtkClipClosedSurface()
        lateral_clip3.SetClippingPlanes(lateral_collection3)
        lateral_clip3.SetInputData(getNode('Mandible').GetPolyData())
        lateral_clip3.SetGenerateFaces(1)
        lateral_clip3.Update()
        nonresect2 = lateral_clip3.GetOutput()

        append = vtk.vtkAppendPolyData()
        append.AddInputData(nonresect1)
        append.AddInputData(nonresect2)
        append.AddInputData(nonresect3)
        append.Update()
        nonresected = append.GetOutput()

        nonresected_model = ms.create_model(nonresected, "NonResected", [1,0,1])
        

    def alt_clip_mandible_fn(self, green_slice, yellow_slice):
        mandible = getNode('Mandible')
        green_plane = ms.get_vtkplane_from_slice(green_slice)
        print(f'Green origin: {green_plane.GetOrigin()}')
        yellow_plane = ms.get_vtkplane_from_slice(yellow_slice)
        print(f'Yellow origin: {yellow_plane.GetOrigin()}')

        #Get mid plane - (Temp mid plane - update with a better method later)
        green_origin = np.asarray(green_plane.GetOrigin())
        yellow_origin = np.asarray(yellow_plane.GetOrigin())
        mid_origin = (green_origin + yellow_origin)/2
        mid_normal = (green_origin - yellow_origin)/np.linalg.norm(green_origin - yellow_origin)
        mid_plane = vtk.vtkPlane()
        mid_plane.SetOrigin(mid_origin)
        mid_plane.SetNormal(mid_normal)

        #Get resected clip - Green 
        green_resected_collection = vtk.vtkPlaneCollection()
        green_resected_collection.AddItem(green_plane)
        green_resected_collection.AddItem(mid_plane)

        green_resected_clip = vtk.vtkClipClosedSurface()
        green_resected_clip.SetClippingPlanes(green_resected_collection)
        green_resected_clip.SetInputData(mandible.GetPolyData())
        green_resected_clip.SetGenerateFaces(1)
        green_resected_clip.Update()
        green_resected_section = green_resected_clip.GetOutput()

        #Get resected clip - Yellow
        mid_plane.SetNormal(-mid_normal[0],-mid_normal[1],-mid_normal[2])
        yellow_resected_collection = vtk.vtkPlaneCollection()
        yellow_resected_collection.AddItem(yellow_plane)
        yellow_resected_collection.AddItem(mid_plane)

        yellow_resected_clip = vtk.vtkClipClosedSurface()
        yellow_resected_clip.SetClippingPlanes(yellow_resected_collection)
        yellow_resected_clip.SetInputData(mandible.GetPolyData())
        yellow_resected_clip.SetGenerateFaces(1)
        yellow_resected_clip.Update()
        yellow_resected_section = yellow_resected_clip.GetOutput()

        #Append data
        append_resected = vtk.vtkAppendPolyData()
        append_resected.AddInputData(green_resected_section)
        append_resected.AddInputData(yellow_resected_section)
        append_resected.Update()
        resected = append_resected.GetOutput()
        resected_model = ms.create_model(resected, "Resected", [1,1,0.5])

        #Get non-resected clip - Green
        mid_plane.SetNormal(mid_normal[0], mid_normal[1], mid_normal[2])
        green_normal = green_plane.GetNormal()
        green_plane.SetNormal(-green_normal[0], -green_normal[1], -green_normal[2])
        green_collection = vtk.vtkPlaneCollection()
        green_collection.AddItem(green_plane)
        green_collection.AddItem(mid_plane)

        green_clip = vtk.vtkClipClosedSurface()
        green_clip.SetClippingPlanes(green_collection)
        green_clip.SetInputData(mandible.GetPolyData())
        green_clip.SetGenerateFaces(1)
        green_clip.Update()
        green_mandible_section = green_clip.GetOutput()

        #Get non-resected clip - Yellow
        mid_plane.SetNormal(-mid_normal[0], -mid_normal[1], -mid_normal[2])
        yellow_normal = yellow_plane.GetNormal()
        yellow_plane.SetNormal(-yellow_normal[0], -yellow_normal[1], -yellow_normal[2])
        yellow_collection = vtk.vtkPlaneCollection()
        yellow_collection.AddItem(mid_plane)
        yellow_collection.AddItem(yellow_plane)

        yellow_clip = vtk.vtkClipClosedSurface()
        yellow_clip.SetClippingPlanes(yellow_collection)
        yellow_clip.SetInputData(mandible.GetPolyData())
        yellow_clip.SetGenerateFaces(1)
        yellow_clip.Update()
        yellow_mandible_section = yellow_clip.GetOutput()

        #Append mandible sections
        append = vtk.vtkAppendPolyData()
        append.AddInputData(green_mandible_section)
        append.AddInputData(yellow_mandible_section)
        append.Update()
        nonresected = append.GetOutput()
        nonresected_model = ms.create_model(nonresected, "NonResected", [1,0,1])
        
        #nonresected_model = slicer.vtkMRMLModelNode()
        #nonresected_model.SetAndObservePolyData(nonresected)
        #nonresected_model.SetName("NonResected_Updated")
        #slicer.mrmlScene.AddNode(nonresected_model)

    def clip_nonresected(self, resection_plane, mid_plane):
        resection_normal = resection_plane.GetNormal()

    def on_delete_planes(self):
        try:
            slicer.mrmlScene.RemoveNode(getNode('Resected'))
            slicer.mrmlScene.RemoveNode(getNode('NonResected'))
        except slicer.util.MRMLNodeNotFoundException: 
            print("Resection nodes already removed")
        self.Mandible.SetDisplayVisibility(1)
        self.ClipNode.SetGreenSliceClipState(0)
        self.ClipNode.SetYellowSliceClipState(0)
        self.YellowSlice.SetSliceVisible(0)
        self.show_left.setChecked(0)
        self.GreenSlice.SetSliceVisible(0)
        self.show_right.setChecked(0)
   
    def on_flip_green(self):
        green_slice = ms.get_vtkplane_from_slice(getNode('vtkMRMLSliceNodeGreen'))
        green_normal = green_slice.GetNormal()
        greenNormal_flipped = np.negative(np.asarray(green_normal))
        slicer.modules.reformat.logic().SetSliceNormal(getNode('vtkMRMLSliceNodeGreen'), 1, 1, 1)
        slicer.modules.reformat.logic().SetSliceNormal(getNode('vtkMRMLSliceNodeGreen'), greenNormal_flipped)
        green_normal = greenNormal_flipped
        self.green_label.setText(f'Right Cut Plane Normal     {np.round(green_normal[0],2), np.round(green_normal[1],2), np.round(green_normal[2],2)} ')
        print("Green normal flipped")

    def on_flip_yellow(self):
        yellow_slice = ms.get_vtkplane_from_slice(getNode('vtkMRMLSliceNodeYellow'))
        yellow_normal = yellow_slice.GetNormal()
        yellowNormal_flipped = np.negative(np.asarray(yellow_normal))
        slicer.modules.reformat.logic().SetSliceNormal(getNode('vtkMRMLSliceNodeYellow'), 1, 1, 1)
        slicer.modules.reformat.logic().SetSliceNormal(getNode('vtkMRMLSliceNodeYellow'), yellowNormal_flipped)
        yellow_normal = yellowNormal_flipped
        self.yellow_label.setText(f'Left Cut Plane Normal   {np.round(yellow_normal[0], 2), np.round(yellow_normal[1], 2), np.round(yellow_normal[2], 2)}')
        print("Yellow normal flipped")

    def on_control_normal(self):
        print(self.autoflip_normal.isChecked())
        if self.autoflip_normal.isChecked():
            self.green_label.setEnabled(False)
            self.yellow_label.setEnabled(False)
            self.flip_green.setEnabled(False)
            self.flip_yellow.setEnabled(False)
        else: 
            self.green_label.setEnabled(True)
            self.yellow_label.setEnabled(True)
            self.flip_green.setEnabled(True)
            self.flip_yellow.setEnabled(True)

    def on_show_right(self):
        if self.show_right.isChecked():
            getNode('vtkMRMLSliceNodeGreen').SetSliceVisible(1)
        else:
            getNode('vtkMRMLSliceNodeGreen').SetSliceVisible(0)

    def on_show_left(self):
        if self.show_left.isChecked():
            getNode('vtkMRMLSliceNodeYellow').SetSliceVisible(1)
        else:
            getNode('vtkMRMLSliceNodeYellow').SetSliceVisible(0)

    def on_export_planes(self):
        green_normal, green_origin, yellow_normal, yellow_origin = resect.check_plane_normal_direction(getNode('vtkMRMLSliceNodeGreen'), 
                                                                                                   getNode('vtkMRMLSliceNodeYellow'))
        resect.on_export_planes("C:\\Users\\Melissa\\Downloads", yellow_normal, yellow_origin, green_normal, green_origin)

    def on_import_planes(self):
        print(self.plane_path.currentPath)
        plane_path = self.plane_path.currentPath
        delimiters = r'[ ,\n]'
        with open(plane_path, 'r') as file:
            #data = file.read().splitlines()
            data = re.split(delimiters, file.read())
        left_normal = np.asarray([float(data[0]), float(data[1]), float(data[2])])
        left_origin = np.asarray([float(data[3]), float(data[4]), float(data[5])])
        right_normal = np.asarray([float(data[6]), float(data[7]), float(data[8])])
        right_origin = np.asarray([float(data[9]), float(data[10]), float(data[11])])
        
        print(f'Left Normal: {left_normal}')
        print(f'Left Origin: {left_origin}')
        print(f'Right Normal: {right_normal}')
        print(f'Right Origin: {right_origin}')

        ms.setSlicePoseFromSliceNormalAndPosition(getNode('vtkMRMLSliceNodeGreen'), right_normal, right_origin)
        getNode('vtkMRMLSliceNodeGreen').SetSliceVisible(1)
        self.show_right.setChecked(1)
        ms.setSlicePoseFromSliceNormalAndPosition(getNode('vtkMRMLSliceNodeYellow'), left_normal, left_origin)
        getNode('vtkMRMLSliceNodeYellow').SetSliceVisible(1)
        self.show_left.setChecked(1)
        print("Slice planes updated")

class ResectMandibleLogic(ScriptedLoadableModuleLogic):
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