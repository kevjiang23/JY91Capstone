import os
import unittest
import logging
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin, getNode

import ManageSlicer as ms
import ManageUI as ui

from ManageRegistration import registration as register


class RegisterMandible(ScriptedLoadableModule):
    def __init__(self, parent):
        #COMMENT: initialize module's meta-data
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "1. Register Mandible"
        self.parent.categories = ["Mandibular Reconstruction"]
        self.parent.dependencies = []
        self.parent.contributors = ["Melissa Yu (UBC)"]
        self.parent.helpText = ""
        self.parent.acknowledgementText = ""

         # COMMENT: initialize UI component - inherits from "ScriptedLoadableModuleWidget, VTKObservationMixin"; basically use this module for every .py to create a UI element for it
class RegisterMandibleWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)
        self.logic = None

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.logic = RegisterMandibleLogic()
        slicer.app.layoutManager().setLayout(4)

        self.getNodes()

        #MANDIBLE FIXATION INSTRUCTIONS: VIEW
        # RegisterMandible_TabLayout = qt.QGridLayout(RegisterMandible_Tabs)

        #COMMENT: below is just the UI structuring, spacing, text etc. - QWidget is the main container of the tab
        mandible_fixation_tab = qt.QWidget()
        mandible_fixation_tab_layout = qt.QVBoxLayout(mandible_fixation_tab)
        mandible_fixation_tab_layout.setAlignment(qt.Qt.AlignTop)
        #mandible_fixation_tab_layout.setVerticalSpacing(5)

        mandible_fixation_title = qt.QLabel(f'Fixate the Mandible')
        mandible_fixation_title.setStyleSheet("font-weight:bold; padding-bottom: 8px; padding-top: 10px")
        mandible_fixation_tab_layout.addWidget(mandible_fixation_title, 0, 0)
        mandible_fixation_instructions = \
            qt.QLabel("To attach the mandible fixation device: \n"
                      "► Check the shorter mandible bone clamp is on the upper fixator bar. \n"
                      "► Make sure the fixation lever is facing towards the patient's feet. \n"
                      "► Place the mandible bone clamps outside the tumour boundary leaving access to make the mandible osteotomies. \n"
                      "► Pre-drill  a 1/16th hole and attach both mandible bone clamps, ensuring they are perpendicular to the jawline. \n"
                      "► Ensure all bone pins are embedded in the bone and the clamp does not move relative to the bone. \n"
                      "► Before locking, ensure the fixator rotation joint teeth are aligned. \n"
                      "► Lock the fixator and check that it remains rigid.")
        mandible_fixation_instructions.setWordWrap(True)
        mandible_fixation_instructions.setStyleSheet('padding-left: 1px')
        mandible_fixation_tab_layout.addWidget(mandible_fixation_instructions, 0, 1)

        #MANDIBLE PAIRED-POINT REGISTRATION: VIEW
        #Place Mandible Registration Patient Fiducials
        mandible_registration_tab = qt.QWidget()
        mandible_registration_tab_layout = qt.QGridLayout(mandible_registration_tab)
        mandible_registration_tab_layout.setAlignment(qt.Qt.AlignTop)
        mandible_registration_tab_layout.setContentsMargins(12, 5, 10, 10)

        mandible_registration_title = qt.QLabel(f'Register the Mandible: Paired Point')
        mandible_registration_title.setStyleSheet("font-weight:bold; padding-bottm: 15px; padding-left: 1px; padding-top: 10px")
        mandible_registration_tab_layout.addWidget(mandible_registration_title, 0, 0, 1, 4)

        mandible_CT_fiducial_instructions = qt.QLabel(f"Place Virtual Fiducials: Identify a minimum of three visually distinct "+
                                                       "points on the mandible that are apparent on both the patient’s mandible "+
                                                       "and the virtual mandible model. Using the mouse, place a fiducial at each "+
                                                       "of those points. ")
        mandible_CT_fiducial_instructions.setStyleSheet("padding-bottom: 10px; padding-top: 5px")
        mandible_CT_fiducial_instructions.setWordWrap(True)
        mandible_registration_tab_layout.addWidget(mandible_CT_fiducial_instructions, 1, 0, 1, 4)

        # Count Number of Mandible CT fiducials Placed
        self.mandible_CT_fiducials_label = qt.QLabel(f'Number of fiducials placed: {self.mandible_CT_fiducials.GetNumberOfFiducials()}')
        self.mandible_CT_fiducials_label.setStyleSheet("padding-bottom: 7px")
        mandible_registration_tab_layout.addWidget(self.mandible_CT_fiducials_label, 2, 0, 1, 4)

        # Place Mandible Registration CT fiducials
        self.place_mandible_CT_fiducials = ui.create_button("Place Virtual Fiducial", "Place fiducials on mandible model", True)
        #self.place_virtual_mandible_fiducials_button.setStyleSheet("padding: 5px")
        mandible_registration_tab_layout.addWidget(self.place_mandible_CT_fiducials, 3, 0, 1, 3)
        self.place_mandible_CT_fiducials.connect('clicked(bool)', self.on_place_mandible_CT_fiducial) 
        # COMMENT: aside from the UI elements, here we connect the button to a method "on_place_mandible_CT_fiducial". This method uses "register" to 
        # call a back-end function to place fiducial points and then dynamically update the number of fiducials that have been placed as a result

        #Remove Mandible Registration CT fiducials
        self.remove_mandible_CT_fiducials = ui.create_button("🗑 Delete all", "Delete all Mandible CT fiducials", True)
        mandible_registration_tab_layout.addWidget(self.remove_mandible_CT_fiducials, 3, 3, 1, 1)
        self.remove_mandible_CT_fiducials.connect('clicked(bool)', self.on_remove_mandible_CT_fiducial)

        physical_fiducial_instructions = qt.QLabel(f'Place Physical Fiducials: Using the NDI pointer, place a fiducial at each of '+
                                                    'the corresponding locations on the patient in the same order as the virtual '+
                                                    'fiducials were placed (where possible, place the pointer perpendicular to the '+
                                                    'bone surface). ')
        physical_fiducial_instructions.setStyleSheet("padding-top: 10px; padding-bottom: 7px")
        physical_fiducial_instructions.setWordWrap(True)
        mandible_registration_tab_layout.addWidget(physical_fiducial_instructions, 4, 0, 1, 4)

        #Count Number of Mandible Patient Fiducials Placed
        self.physical_mandible_fiducials_label = qt.QLabel(f'Number of fiducials placed: {self.mandible_patient_fiducials.GetNumberOfFiducials()}')
        self.physical_mandible_fiducials_label.setStyleSheet("padding-bottom: 7px")
        mandible_registration_tab_layout.addWidget(self.physical_mandible_fiducials_label, 5, 0, 1, 4)

        #Place Mandible Registration Patient Fiducials
        self.place_physical_mandible_fiducials_button = ui.create_button("Place Patient Fiducial", "Place fiducials on patient's mandible", True)
        mandible_registration_tab_layout.addWidget(self.place_physical_mandible_fiducials_button, 6, 0, 1, 3)
        self.place_physical_mandible_fiducials_button.connect('clicked(bool)', self.on_place_mandible_patient_fiducial)

        #Remove Mandible Registration Patient Fiducials
        self.remove_physical_mandible_fiducials_button = ui.create_button("🗑 Delete all", "Delete all patient fiducials")
        mandible_registration_tab_layout.addWidget(self.remove_physical_mandible_fiducials_button, 6, 3, 1, 1)
        self.remove_physical_mandible_fiducials_button.connect('clicked(bool)', self.on_remove_mandible_patient_fiducial)

        #mandible_registration_tab_layout.setVerticalSpacing(10)
        #spacing_label = qt.QLabel("\n")
        #mandible_registration_tab_layout.addWidget(spacing_label, 7, 0, 1, 4)

        register_mandible_error_instructions = qt.QLabel("Register: Run the paired-point registration and evaluate the error. If it is "+
                                                         "greater than 10, delete the registration and repeat the paired-point registration "+
                                                         "steps. ")
        register_mandible_error_instructions.setWordWrap(True)                                        
        register_mandible_error_instructions.setStyleSheet("padding-top: 10px; font-weight: normal")
        mandible_registration_tab_layout.addWidget(register_mandible_error_instructions, 8, 0, 1, 4)

        self.register_mandible_error = qt.QLabel("Root-mean square error:")
        self.register_mandible_error.setStyleSheet("padding-bottom: 7px; font-weight: normal")
        mandible_registration_tab_layout.addWidget(self.register_mandible_error, 9, 0, 1, 4)

        # Calculate Initial Mandible Registration
        self.register_mandible_button = ui.create_button("Register Mandible", "Run Paired Point Registration", True)
        mandible_registration_tab_layout.addWidget(self.register_mandible_button, 10, 0, 1, 3)
        self.register_mandible_button.setStyleSheet("font-weight: normal")
        self.register_mandible_button.connect('clicked(bool)', self.register_mandible_paired_point)
        # COMMENT: run paired point mandible registration to see how current mandible fiducial matches the intended positions; if bad, delete using the button below

        self.delete_registration_button = ui.create_button("🗑 Delete", "Delete Paired Point Registration", True)
        mandible_registration_tab_layout.addWidget(self.delete_registration_button, 10, 3, 1, 1)
        self.delete_registration_button.connect('clicked(bool)', self.delete_mandible_paired_point)

        #group_box = qt.QGroupBox("Run Registration")
        ##group_box.setAlignment(qt.Qt.AlignHCenter)
        ##group_box.setStyleSheet("padding-left: 5px")
        
        #group_box_layout = qt.QVBoxLayout()
        #group_box_layout.addWidget(register_mandible_error_instructions)
        #group_box_layout.addWidget(self.register_mandible_error)
        #group_box_layout.addWidget(self.register_mandible_button)
        #group_box.setLayout(group_box_layout)
        #mandible_registration_tab_layout.addWidget(group_box, 13, 0, 1, 4)

        # Show Initial Mandible Registration Error

        # MANDIBLE SURFACE REGISTRATION: VIEW
        # Place Mandible Registration Patient Fiducials
        mandible_surface_registration_tab = qt.QWidget()
        mandible_surface_registration_tab_layout = qt.QGridLayout(mandible_surface_registration_tab)
        mandible_surface_registration_tab_layout.setAlignment(qt.Qt.AlignTop)
        mandible_surface_registration_tab_layout.setContentsMargins(12, 5, 10, 10)

        mandible_surface_registration_title = qt.QLabel(f'Register the Mandible: Surface')
        mandible_surface_registration_title.setStyleSheet("font-weight:bold; padding-bottom: 8px; padding-top: 10px")
        mandible_surface_registration_tab_layout.addWidget(mandible_surface_registration_title, 0, 0, 1, 4)

        mandible_surface_fiducial_instructions = qt.QLabel("Place the tip of the pointer against the surface of the patient’s "+
                                                           "mandible. When ready, press “Start collecting.” This will begin placing "+
                                                           "fiducials at the pointer’s tip. Drag the NDI pointer along the surface "+
                                                           "of the mandible until a minimum of 75 fiducials are collected (where possible, "+
                                                           "keep the pointer perpendicular to the bone surface). When done, press “Stop collecting” "+
                                                           "to stop the collection of surface fiducials. ")
        mandible_surface_fiducial_instructions.setWordWrap(True)
        mandible_surface_fiducial_instructions.setStyleSheet("padding-bottom: 10px")
        mandible_surface_registration_tab_layout.addWidget(mandible_surface_fiducial_instructions, 1, 0, 1, 4)

        # Count Number of Surface fiducials Collected on the Mandible
        self.mandible_surface_count_label = qt.QLabel("Number of surface fiducials placed: 0")
        self.mandible_surface_count_label.setStyleSheet("padding-bottom:10px")
        mandible_surface_registration_tab_layout.addWidget(self.mandible_surface_count_label, 2, 0, 1, 4)

        # Start Mandible Surface Registration fiducial Collection
        self.mandible_start_surface = ui.create_button("Start collecting surface fiducials", "Drag pointer along mandible surface", True)
        mandible_surface_registration_tab_layout.addWidget(self.mandible_start_surface, 3, 0, 1, 2)
        self.mandible_start_surface.connect('clicked(bool)', self.on_mandible_start_surface)

        # Stop Mandible Surface Registration fiducial Collection
        self.mandible_stop_surface = ui.create_button("Stop collecting surface fiducials", "Pause collection", True)
        mandible_surface_registration_tab_layout.addWidget(self.mandible_stop_surface, 3, 2, 1, 2)
        self.mandible_stop_surface.connect('clicked(bool)', self.on_mandible_stop_surface)

        space = qt.QLabel("")
        space.setStyleSheet('margin-bottom: -10px')
        mandible_surface_registration_tab_layout.addWidget(space, 4, 0, 1, 4)

        # Remove Mandible Registration Surface fiducials
        self.remove_mandible_surface_fiducials = ui.create_button("🗑 Delete all", "Delete surface fiducials", True)
        mandible_surface_registration_tab_layout.addWidget(self.remove_mandible_surface_fiducials, 5, 0, 1, 4)
        self.remove_mandible_surface_fiducials.connect('clicked(bool)', self.on_remove_mandible_surface_fiducials)

        register_mandible_surface_error_instructions = qt.QLabel("Run Surface Registration: Press “Register Mandible” to run surface registration. If the "+
                                                                "error is greater than 1, delete the registration and repeat the above steps. ")
        register_mandible_surface_error_instructions.setWordWrap(True)
        register_mandible_surface_error_instructions.setStyleSheet("padding-top: 10px; font-weight: normal")
        mandible_surface_registration_tab_layout.addWidget(register_mandible_surface_error_instructions, 6, 0, 1, 4)

        # Show Mandible Surface Registration Error
        self.mandible_surface_error = qt.QLabel("Root mean square error: 0")
        self.mandible_surface_error.setStyleSheet('padding-bottom: 10px')
        mandible_surface_registration_tab_layout.addWidget(self.mandible_surface_error, 7, 0, 1, 4)

        # Calculate Mandible Surface Registration
        self.register_mandible_surface = ui.create_button("Register Mandible", "Run Surface Registration", True)
        mandible_surface_registration_tab_layout.addWidget(self.register_mandible_surface, 8, 0, 1, 3)
        self.register_mandible_surface.connect('clicked(bool)', self.on_register_mandible_surface)

        self.delete_mandible_surface = ui.create_button("🗑 Delete", "Delete Surface Registration", True)
        mandible_surface_registration_tab_layout.addWidget(self.delete_mandible_surface, 8, 3, 1, 1)
        self.delete_mandible_surface.connect('clicked(bool)', self.on_delete_mandible_surface)

        # VISUALLY VERIFY QUALITY OF MANDIBLE REGISTRATION
        # Place Mandible Registration Patient Fiducials
        mandible_registration_quality_tab = qt.QWidget()
        mandible_registration_quality_tab_layout = qt.QFormLayout(mandible_registration_quality_tab)

        mandible_registration_quality_title = qt.QLabel(f'Check Mandible Registration')
        mandible_registration_quality_title.setStyleSheet("font-weight:bold; padding-bottom: 8px; padding-top: 10px")
        mandible_registration_quality_tab_layout.addRow(mandible_registration_quality_title)

        self.check_mandible_registration_label = qt.QLabel("Check mandible registration by moving the probe over the surface "+
                                                           "of the mandible and verifying that the pointer model on screen is in "+
                                                           "the correct corresponding location. ")
        self.check_mandible_registration_label.setWordWrap(True)
        self.check_mandible_registration_label.setStyleSheet("padding-bottom: 10px")
        mandible_registration_quality_tab_layout.addRow(self.check_mandible_registration_label)


        self.good_mandible_registration = ui.create_button("✓ Good Registration")
        mandible_registration_quality_tab_layout.addRow(self.good_mandible_registration)
        self.good_mandible_registration.connect('clicked(bool)', self.on_next_module)

        self.redo_mandible_registration = ui.create_button("⭯ Redo Registration")
        mandible_registration_quality_tab_layout.addRow(self.redo_mandible_registration)
        self.redo_mandible_registration.connect('clicked(bool)', self.on_redo_mandible_registration)

        #Add to Tab Widget
        self.register_mandible_tabs = qt.QTabWidget()
        self.register_mandible_tabs.addTab(mandible_fixation_tab, "Mandible Fixation")
        self.register_mandible_tabs.addTab(mandible_registration_tab, "Register Mandible: Paired Point")
        self.register_mandible_tabs.addTab(mandible_surface_registration_tab, "Register Mandible: Surface")
        self.register_mandible_tabs.addTab(mandible_registration_quality_tab, "Quality of Mandible Registration")
        self.layout.addWidget(self.register_mandible_tabs, 0, 0)
        #self.mandreg_tab_state = self.RegisterMandible_Tabs.currentIndex()
        self.mandreg_tab_state = 0
        self.change_mandible_registration_tab_visibility(self.mandreg_tab_state)
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

        save_box = qt.QGroupBox()
        save_button_layout = qt.QHBoxLayout(save_box)
        self.save_button = ui.create_button("Save scene")
        self.save_button.connect('clicked(bool)', self.on_save)
        save_button_layout.addWidget(self.save_button)
        self.layout.addWidget(save_box)

        # COMMENT: retrieve/import the nodes for fiducials for CT scan and patient data 
    def getNodes(self):
        #Fiducial List
        self.mandible_CT_fiducials = ui.import_node('VirtualFidsM', 'vtkMRMLMarkupsFiducialNode')
        self.mandible_patient_fiducials = ui.import_node('PhysicalFidsM', 'vtkMRMLMarkupsFiducialNode')
        self.mandible_surface_fiducials = ui.import_node('SurfaceFidsM', 'vtkMRMLMarkupsFiducialNode')

        self.mandible_registration = ui.import_node('MandibleRegistration', 'vtkMRMLFiducialRegistrationWizardNode')
        self.mandible_surface_registration = ui.import_node('SurfaceRegistrationM', 'vtkMRMLLinearTransformNode')

        self.StylusTipToStylusRef = getNode('StylusTipToStylusRef')
        self.StylusRefToMandRef = ui.import_node('StylusRefToMandRef', 'vtkMRMLLinearTransformNode')
        self.MandRefToMand = ui.import_node('MandRefToMand', 'vtkMRMLLinearTransformNode')

        self.Mandible = getNode('Mandible')
        self.Fibula = getNode('Fibula')
        self.Pointer = getNode('Pointer')
        self.Contour = getNode('Contour')

        self.WatchdogStylusMandible = getNode('Watchdog_StylusToMandible')

    #Control tab visibility and page state
    def change_mandible_registration_tab_visibility(self, state):
        self.register_mandible_tabs.setCurrentIndex(state)
        if state == 0:
            self.on_mandible_fixation_tab()
        elif state == 1:
            #self.prev_button.setEnabled(1)
            #self.RegisterMandible_Tabs.setCurrentIndex(1)
            self.on_mandible_registration_tab()
        elif state == 2:
            self.on_mandible_surface_registration_tab()
        elif state == 3:
            self.on_mandible_registration_quality_tab()

    #SET TAB STATES
    def on_mandible_fixation_tab(self):
        self.register_mandible_tabs.setTabEnabled(0, True)
        self.register_mandible_tabs.setTabEnabled(1, False)
        self.register_mandible_tabs.setTabEnabled(2, False)
        self.register_mandible_tabs.setTabEnabled(3, False)
        slicer.modules.models.logic().SetAllModelsVisibility(0)
        self.Mandible.SetDisplayVisibility(1)
        self.mandible_CT_fiducials.SetDisplayVisibility(0)
        self.mandible_patient_fiducials.SetDisplayVisibility(0)
        self.mandible_surface_fiducials.SetDisplayVisibility(0)
        self.Contour.SetDisplayVisibility(0)

    def on_mandible_registration_tab(self):
        self.register_mandible_tabs.setTabEnabled(0, False)
        self.register_mandible_tabs.setTabEnabled(1, True)
        self.register_mandible_tabs.setTabEnabled(2, False)
        self.register_mandible_tabs.setTabEnabled(3, False)
        slicer.modules.models.logic().SetAllModelsVisibility(0)
        self.Mandible.SetDisplayVisibility(1)
        self.Pointer.SetDisplayVisibility(1)
        self.mandible_CT_fiducials.SetDisplayVisibility(1)
        self.mandible_patient_fiducials.SetDisplayVisibility(1)
        self.mandible_surface_fiducials.SetDisplayVisibility(0)
        self.StylusTipToStylusRef.SetAndObserveTransformNodeID(self.StylusRefToMandRef.GetID())
        self.Pointer.SetAndObserveTransformNodeID(self.StylusTipToStylusRef.GetID())
        self.WatchdogStylusMandible.SetDisplayVisibility(1)

    def on_mandible_surface_registration_tab(self):
        self.register_mandible_tabs.setTabEnabled(0, False)
        self.register_mandible_tabs.setTabEnabled(1, False)
        self.register_mandible_tabs.setTabEnabled(2, True)
        self.register_mandible_tabs.setTabEnabled(3, False)
        slicer.modules.models.logic().SetAllModelsVisibility(0)
        self.Mandible.SetDisplayVisibility(1)
        self.Pointer.SetDisplayVisibility(1)
        self.mandible_CT_fiducials.SetDisplayVisibility(0)
        self.mandible_patient_fiducials.SetDisplayVisibility(0)
        self.mandible_surface_fiducials.SetDisplayVisibility(1)
        self.WatchdogStylusMandible.SetDisplayVisibility(1)

    def on_mandible_registration_quality_tab(self):
        self.register_mandible_tabs.setTabEnabled(0, False)
        self.register_mandible_tabs.setTabEnabled(1, False)
        self.register_mandible_tabs.setTabEnabled(2, False)
        self.register_mandible_tabs.setTabEnabled(3, True)
        slicer.modules.models.logic().SetAllModelsVisibility(0)
        self.Mandible.SetDisplayVisibility(1)
        self.Pointer.SetDisplayVisibility(1)
        self.mandible_CT_fiducials.SetDisplayVisibility(0)
        self.mandible_patient_fiducials.SetDisplayVisibility(0)
        self.mandible_surface_fiducials.SetDisplayVisibility(0)
        self.WatchdogStylusMandible.SetDisplayVisibility(1)

    def on_next_module(self):
        if self.mandreg_tab_state < 3:
            self.mandreg_tab_state = self.mandreg_tab_state + 1
            self.change_mandible_registration_tab_visibility(self.mandreg_tab_state)
            print(self.mandreg_tab_state)
        else:
            self.WatchdogStylusMandible.SetDisplayVisibility(0)
            slicer.util.selectModule('ResectMandible')
            

    def on_previous_module(self):
        if self.mandreg_tab_state > 0:
            self.mandreg_tab_state = self.mandreg_tab_state - 1
            self.change_mandible_registration_tab_visibility(self.mandreg_tab_state)
            print(self.mandreg_tab_state)
        elif self.mandreg_tab_state == 0:
            self.WatchdogStylusMandible.SetDisplayVisibility(0)
            slicer.util.selectModule('ReconstructionWorkflow')

    
    def on_save(self):
        dir = os.path.dirname(getNode('MandiblePath').GetText())+"\\SlicerFiles"
        ms.save_scene(dir, "1_RegisterMandible"+str(self.mandreg_tab_state))

    #CONTROLLER
    def on_place_mandible_CT_fiducial(self):
        register.place_CT_fiducial(self.mandible_CT_fiducials)
        self.mandible_CT_fiducials_label.text = (f'Number of fiducials placed: '
                                           f'{self.mandible_CT_fiducials.GetNumberOfFiducials()+1}')

    # Remove Mandible CT fiducial
    def on_remove_mandible_CT_fiducial(self):
        register.remove_CT_fiducials(self.mandible_CT_fiducials)
        self.mandible_CT_fiducials_label.text = (f'Number of fiducials placed: '
                                           f'{self.mandible_CT_fiducials.GetNumberOfFiducials()}')

    # Place Mandible Patient fiducial
    def on_place_mandible_patient_fiducial(self):
        register.place_patient_fiducial(self.mandible_patient_fiducials, self.StylusTipToStylusRef)
        self.mandible_patient_fiducials.SetNthControlPointLocked(self.mandible_patient_fiducials.GetNumberOfFiducials()-1, 1)
        self.physical_mandible_fiducials_label.text = (f'Number of fiducials placed: '
                                                f'{self.mandible_patient_fiducials.GetNumberOfFiducials()}')

    # Remove Mandible Patient fiducial
    def on_remove_mandible_patient_fiducial(self):
        register.remove_patient_fiducials(self.mandible_patient_fiducials, self.StylusRefToMandRef)
        self.physical_mandible_fiducials_label.text = (f'Number of fiducials placed: '
                                                        f'{self.mandible_patient_fiducials.GetNumberOfFiducials()}')

    def register_mandible_paired_point(self):
        error = register.run_registration(self.mandible_registration,
                                    self.mandible_CT_fiducials,
                                    self.mandible_patient_fiducials,
                                    self.MandRefToMand,
                                    self.StylusRefToMandRef)
        self.register_mandible_error.setText(f'Root mean square error: {error}')

    def delete_mandible_paired_point(self):
        delete = register.delete_registration(self.StylusRefToMandRef)
        if delete: 
            self.register_mandible_error.setText(f'Root mean square error: ')
            print("Deleted registration")

    # Start timer for collecting surface points every n seconds
    def on_mandible_start_surface(self):
        self.m_lastFid = 0
        self.m_timer = qt.QTimer()
        self.m_timer.timeout.connect(self.collect_surface_fiducials_timer)
        self.m_timer.setInterval(100)
        self.m_timer.start()
        print("Started")

    # Link between logic to place fiducial and timer starter
    def collect_surface_fiducials_timer(self):
        self.m_currentFid = self.m_lastFid + 1
        register.place_patient_fiducial(self.mandible_surface_fiducials, self.StylusTipToStylusRef)
        self.m_lastFid = self.m_currentFid
        self.mandible_surface_count_label.setText(f'Number of surface fiducials placed: {self.mandible_surface_fiducials.GetNumberOfFiducials()}')
        return self.m_currentFid

    # Stop timer for collecting surface points every n seconds
    def on_mandible_stop_surface(self):
        self.m_timer.stop()
        print("Paused")
        self.mandible_surface_count_label.setText(f'Number of surface fiducials placed: {self.mandible_surface_fiducials.GetNumberOfFiducials()}')

    # Remove Mandible Surface fiducial
    def on_remove_mandible_surface_fiducials(self):
        register.remove_surface_fiducials(self.mandible_surface_fiducials)
        self.mandible_surface_count_label.setText(f'Number of surface fiducials placed: {self.mandible_surface_fiducials.GetNumberOfFiducials()}')

    def on_register_mandible_surface(self):
        max_iterations = 100
        register.run_surface_registration(self.mandible_surface_fiducials,
                                          self.Mandible, self.mandible_surface_registration, max_iterations)
        surf_error = register.compute_mean_distance(self.mandible_surface_fiducials,
                                              self.Mandible, self.mandible_surface_registration,
                                              self.MandRefToMand)
        self.mandible_surface_error.setText(f'Root mean square error: {surf_error}')

    def on_delete_mandible_surface(self):
        delete = register.delete_surface_registration(self.MandRefToMand)
        if delete:
            self.mandible_surface_error.setText(f'Root mean square error:')
            print("Registration deleted")

    def on_redo_mandible_registration(self):
        self.mandreg_tab_state=1
        self.change_mandible_registration_tab_visibility(self.mandreg_tab_state)
        self.on_remove_mandible_CT_fiducial()
        self.on_remove_mandible_patient_fiducial()
        self.on_remove_mandible_surface_fiducials()
        self.delete_mandible_paired_point()
        self.on_delete_mandible_surface()

class RegisterMandibleLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        # self.markupsLogic = slicer.modules.markups.logic()
        # self.fiducialRegistrationLogic = slicer.modules.fiducialregistrationwizard.logic()


class RegisterMandibleTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.test_RegisterMandible1()

    def test_RegisterMandible1(self):
        self.delayDisplay("Start test")
        logic = RegisterMandibleLogic()
        self.delayDisplay("Test passed")
