import os
import unittest
import logging
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin, getNode

import ManageSlicer as ms
import ManageUI as ui

from ManageRegistration import registration as register


class RegisterTools(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "0. Register Tools"
        self.parent.categories = ["Mandibular Reconstruction"]
        self.parent.dependencies = []
        self.parent.contributors = ["Melissa Yu (UBC)"]
        self.parent.helpText = ""
        self.parent.acknowledgementText = ""

class RegisterToolsWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)
        self.logic = None

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.logic = RegisterToolsLogic()
        slicer.app.layoutManager().setLayout(4)
        self.layout.setAlignment(qt.Qt.AlignTop)

        register_tool = ctk.ctkCollapsibleButton()
        register_tool.text = "Register Tool"
        register_tool_layout = qt.QGridLayout(register_tool)
        register_tool_layout.setAlignment(qt.Qt.AlignTop)
        self.layout.addWidget(register_tool)

        select_model_label = qt.QLabel("Register Model: ")
        select_model_label.setStyleSheet("padding-left: 2px")
        register_tool_layout.addWidget(select_model_label, 0, 0, 1, 1)
        self.select_model = slicer.qMRMLNodeComboBox()
        self.select_model.nodeTypes = ["vtkMRMLModelNode"]
        self.select_model.addEnabled = False
        self.select_model.removeEnabled = False
        self.select_model.setMRMLScene(slicer.mrmlScene)
        register_tool_layout.addWidget(self.select_model, 0, 1, 1, 2)

        # temp = self.select_model.currentNode()
        # print(temp.GetName())

        paired_point_label = qt.QLabel("Paired Point Registration")
        paired_point_label.setStyleSheet("font-weight:bold; padding-top: 15px; padding-bottom: 8px")
        register_tool_layout.addWidget(paired_point_label, 1, 0, 1, 3)

        virtual_label = qt.QLabel("Virtual Fiducial")
        virtual_label.setStyleSheet("padding-left: 2px")
        register_tool_layout.addWidget(virtual_label, 2, 0, 1, 1)

        self.place_virtual_fid = ui.create_button("Place virtual fiducial")
        self.place_virtual_fid.connect('clicked(bool)', self.on_place_virtual_fiducial)
        register_tool_layout.addWidget(self.place_virtual_fid, 2, 1, 1, 2)

        physical_label = qt.QLabel("Physical Fiducial")
        physical_label.setStyleSheet("padding-left: 2px")
        register_tool_layout.addWidget(physical_label, 3, 0, 1, 1)

        self.place_physical_fid = ui.create_button("Place physical fiducial")
        self.place_physical_fid.connect('clicked(bool)', self.on_place_patient_fiducial)
        register_tool_layout.addWidget(self.place_physical_fid, 3, 1, 1, 2)

        space = qt.QLabel("")
        register_tool_layout.addWidget(space, 4, 0, 1, 3)

        self.run_paired_point = ui.create_button("Update paired point registration")
        self.run_paired_point.connect('clicked(bool)', self.register_paired_point)
        register_tool_layout.addWidget(self.run_paired_point, 5, 1, 1, 2)

        self.paired_point_error = qt.QLabel("Root mean square error: ")
        self.paired_point_error.setStyleSheet("padding-left: 2px")
        register_tool_layout.addWidget(self.paired_point_error, 6, 0, 1, 2)

        surface_label = qt.QLabel("Surface Registration")
        surface_label.setStyleSheet("font-weight:bold; padding-top: 15px; padding-bottom: 8px")
        register_tool_layout.addWidget(surface_label, 7, 0, 1, 3)

        surface_fids = qt.QLabel("Surface Fiducials")
        surface_fids.setStyleSheet("padding-left: 2px")
        register_tool_layout.addWidget(surface_fids, 8, 0, 1, 1)

        start_surface = ui.create_button("Start Surface")
        start_surface.connect('clicked(bool)', self.on_tool_start_surface)
        register_tool_layout.addWidget(start_surface, 8, 1, 1, 1)

        pause_surface = ui.create_button("Pause Surface")
        pause_surface.connect('clicked(bool)', self.on_tool_stop_surface)
        register_tool_layout.addWidget(pause_surface, 8, 2, 1, 1)

        self.surface_count = qt.QLabel("Number of fiducials placed: ")
        self.surface_count.setStyleSheet("padding-left: 2px")
        register_tool_layout.addWidget(self.surface_count, 9, 0, 1, 3)

        space_ = qt.QLabel("")
        register_tool_layout.addWidget(space_, 10, 0, 1, 3)

        self.run_surface = ui.create_button("Update surface registration")
        self.run_surface.connect('clicked(bool)', self.on_register_tool_surface)
        register_tool_layout.addWidget(self.run_surface, 11, 1, 1, 2)

        self.surface_error = qt.QLabel("Root mean square error: ")
        self.surface_error.setStyleSheet("padding-left: 2px")
        register_tool_layout.addWidget(self.surface_error, 12, 0, 1, 2)

        # self.virtual_label_count = qt.QLabel("Number of fiducials placed: ")
        # self.virtual_label_count.setStyleSheet("padding-left: 2px; padding-bottom: 5px")
        # register_tool_layout.addWidget(self.virtual_label_count, 3, 0, 1, 2)

        tool_label = qt.QLabel("Tool Registration")
        tool_label.setStyleSheet("font-weight:bold; padding-top: 15px; padding-bottom: 8px")
        register_tool_layout.addWidget(tool_label, 13, 0, 1, 3)

        output_transform_label = qt.QLabel("Output Transform: ")
        output_transform_label.setStyleSheet("padding-left: 2px")
        register_tool_layout.addWidget(output_transform_label, 14, 0, 1, 1)

        self.output_transform = slicer.qMRMLNodeComboBox()
        self.output_transform.nodeTypes = ["vtkMRMLLinearTransformNode"]
        self.output_transform.addEnabled = True
        self.output_transform.renameEnabled = True
        # self.output_transform.removeEnabled = False
        self.output_transform.setMRMLScene(slicer.mrmlScene)
        register_tool_layout.addWidget(self.output_transform, 14, 1, 1, 2)
        
        # print(self.output_transform.currentNode().GetName())

        space__ = qt.QLabel("")
        register_tool_layout.addWidget(space__, 15, 0, 1, 3)

        self.run_tool = ui.create_button("Update tool registration")
        self.run_tool.resize(100, 32)
        self.run_tool.connect('clicked(bool)', self.on_update_tool_registration)
        register_tool_layout.addWidget(self.run_tool, 16, 0, 1, 3)

        self.tool_registration = ui.import_node('ToolRegistration', 'vtkMRMLFiducialRegistrationWizardNode')
        self.StylusTipToStylusRef = getNode('StylusTipToStylusRef')

    #CONTROLLER
    def on_place_virtual_fiducial(self):
        virtual_fids = ui.import_node(self.select_model.currentNode().GetName()+"_virtualfids")
        register.place_CT_fiducial(virtual_fids)

    # Place Mandible Patient fiducial
    def on_place_patient_fiducial(self):
        physical_fids = ui.import_node(self.select_model.currentNode().GetName()+"_physicalfids")
        register.place_patient_fiducial(physical_fids, self.StylusTipToStylusRef)
        physical_fids.SetNthControlPointLocked(physical_fids.GetNumberOfFiducials()-1, 1)

    def register_paired_point(self):
        paired_point = ui.import_node(self.select_model.currentNode().GetName()+"_pp", 'vtkMRMLLinearTransformNode')
        # stylus_ref_to_tool_ref = getNode('StylusRefTo'+str(self.select_model.currentNode().GetName())+'Ref')
        if str(self.select_model.currentNode().GetName()) == 'ActualFibSeg1':
            stylus_ref_to_tool_ref = getNode('StylusRefToHand1Ref')
        elif str(self.select_model.currentNode().GetName()) == 'ActualFibSeg2':
            stylus_ref_to_tool_ref = getNode('StylusRefToHand2Ref')
        elif str(self.select_model.currentNode().GetName()) == 'ActualFibSeg3':
            stylus_ref_to_tool_ref = getNode('StylusRefToHand3Ref')
        else: 
            stylus_ref_to_tool_ref = getNode('StylusRefTo'+str(self.select_model.currentNode().GetName())+'Ref')
        error = register.run_registration(self.tool_registration,
                                          getNode(self.select_model.currentNode().GetName()+"_virtualfids"),
                                          getNode(self.select_model.currentNode().GetName()+"_physicalfids"),
                                          paired_point, stylus_ref_to_tool_ref)
        self.paired_point_error.setText(f'Root mean square error: {error}')

    # def delete_mandible_paired_point(self):
    #     delete = register.delete_registration(self.StylusRefToMandRef)
    #     if delete: 
    #         self.register_mandible_error.setText(f'Root mean square error: ')
    #         print("Deleted registration")

    # Start timer for collecting surface points every n seconds
    def on_tool_start_surface(self):
        self.surface_fids = ui.import_node(self.select_model.currentNode().GetName()+"_surfacefids")
        self.m_lastFid = 0
        self.m_timer = qt.QTimer()
        self.m_timer.timeout.connect(self.collect_surface_fiducials_timer)
        self.m_timer.setInterval(100)
        self.m_timer.start()
        print("Started")

    # Link between logic to place fiducial and timer starter
    def collect_surface_fiducials_timer(self):
        self.m_currentFid = self.m_lastFid + 1
        register.place_patient_fiducial(self.surface_fids, self.StylusTipToStylusRef)
        self.m_lastFid = self.m_currentFid
        self.surface_count.setText(f'Number of surface fiducials placed: {self.surface_fids.GetNumberOfFiducials()}')
        return self.m_currentFid

    # Stop timer for collecting surface points every n seconds
    def on_tool_stop_surface(self):
        self.m_timer.stop()
        print("Paused")
        self.surface_count.setText(f'Number of surface fiducials placed: {self.surface_fids.GetNumberOfFiducials()}')

    # # Remove Mandible Surface fiducial
    # def on_remove_mandible_surface_fiducials(self):
    #     register.remove_surface_fiducials(self.mandible_surface_fiducials)
    #     self.mandible_surface_count_label.setText(f'Number of surface fiducials placed: {self.mandible_surface_fiducials.GetNumberOfFiducials()}')

    def on_register_tool_surface(self):
        self.tool_surface_registration = ui.import_node(self.select_model.currentNode().GetName()+"_surfacereg", 'vtkMRMLLinearTransformNode')
        self.surface_fids = getNode(self.select_model.currentNode().GetName()+"_surfacefids")
        max_iterations = 100
        register.run_surface_registration(self.surface_fids, self.select_model.currentNode(), self.tool_surface_registration, max_iterations)
        surf_error = register.compute_mean_distance(self.surface_fids,self.select_model.currentNode(), 
                                                    self.tool_surface_registration, getNode(self.select_model.currentNode().GetName()+'_pp'))
        self.surface_error.setText(f'Root mean square error: {surf_error}')


    def on_update_tool_registration(self):
        pp = getNode(self.select_model.currentNode().GetName()+"_pp")
        pp_inv = vtk.vtkMatrix4x4()
        pp.GetMatrixTransformFromParent(pp_inv)

        surf = getNode(self.select_model.currentNode().GetName()+"_surfacereg")
        surf_inv = vtk.vtkMatrix4x4()
        surf.GetMatrixTransformFromParent(surf_inv)

        reg_mat = vtk.vtkMatrix4x4()
        vtk.vtkMatrix4x4.Multiply4x4(pp_inv, surf_inv, reg_mat)

        reg_transform = ui.update_transform(reg_mat, self.output_transform.currentNode().GetName())
        print("Tool registration updated")
        
        # stylus_ref_to_tool_ref = getNode('StylusRefTo'+str(self.select_model.currentNode().GetName())+'Ref')
        if str(self.select_model.currentNode().GetName()) == 'ActualFibSeg1':
            stylus_ref_to_tool_ref = getNode('StylusRefToHand1Ref')
        elif str(self.select_model.currentNode().GetName()) == 'ActualFibSeg2':
            stylus_ref_to_tool_ref = getNode('StylusRefToHand2Ref')
        elif str(self.select_model.currentNode().GetName()) == 'ActualFibSeg3':
            stylus_ref_to_tool_ref = getNode('StylusRefToHand3Ref')
        else: 
            stylus_ref_to_tool_ref = getNode('StylusRefTo'+str(self.select_model.currentNode().GetName())+'Ref')
        stylus_ref_to_tool_ref.SetAndObserveTransformNodeID(None)
        getNode('StylusTipToStylusRef').SetAndObserveTransformNodeID(None)

class RegisterToolsLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        # self.markupsLogic = slicer.modules.markups.logic()
        # self.fiducialRegistrationLogic = slicer.modules.fiducialregistrationwizard.logic()


class RegisterToolsTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.test_RegisterTools1()

    def test_RegisterTools1(self):
        self.delayDisplay("Start test")
        logic = RegisterToolsLogic()
        self.delayDisplay("Test passed")