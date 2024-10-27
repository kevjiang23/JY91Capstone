import os
import unittest
import logging
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin, getNode

import numpy as np 
import math

import ManageSlicer as ms
import ManageUI as ui
from InverseKin import InverseKin
from ManageRegistration import registration as register

class PlaceSegments(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "6. Place Segments"
        self.parent.categories = ["Mandibular Reconstruction"]
        self.parent.dependencies = []
        self.parent.contributors = ["Melissa Yu (UBC)"]
        self.parent.helpText = ""
        self.parent.acknowledgementText = ""

class PlaceSegmentsWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)
        self.logic = None

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.logic = PlaceSegmentsLogic()
        self.layout.setAlignment(qt.Qt.AlignTop)
        self.guidance_method = ""

        #Select method of guidance
        guidance_method_tab = qt.QWidget()
        guidance_method_tab_layout = qt.QGridLayout(guidance_method_tab)
        guidance_method_tab_layout.setAlignment(qt.Qt.AlignTop)

        guidance_method_title = qt.QLabel(f'Select a Guidance Method')
        guidance_method_title.setStyleSheet("font-size: 9pt; font-weight: bold; padding: 5px; padding-bottom: 10px")
        guidance_method_tab_layout.addWidget(guidance_method_title, 0, 0, 1, 2)

        guidance_method_instructions = qt.QLabel("Select the desired method of guidance. The freehand method allows you to visualize "+
                                                "the segments placed in the scene. The guided method provides visual guidance for "+
                                                "macro-positioning then instructions for micro-positioning. ")
        guidance_method_instructions.setWordWrap(True)
        guidance_method_instructions.setStyleSheet("padding: 5px; padding-bottom: 10px")
        guidance_method_tab_layout.addWidget(guidance_method_instructions, 1, 0, 1, 2)

        freehand_method_button = ui.create_button("Freehand Positioning")
        freehand_method_button.connect('clicked(bool)', self.on_freehand_button)
        guidance_method_tab_layout.addWidget(freehand_method_button, 2, 0, 1, 2)

        guided_method_button = ui.create_button("Guided Positioning")
        guided_method_button.connect('clicked(bool)', self.on_guided_button)
        guidance_method_tab_layout.addWidget(guided_method_button, 3, 0, 1, 2)

        #Freehand Reconstruction
        self.freehand_method_tab = qt.QWidget()
        freehand_tab_layout = qt.QGridLayout(self.freehand_method_tab)
        freehand_tab_layout.setAlignment(qt.Qt.AlignTop)

        freehand_title = qt.QLabel(f'Freehand Positioning')
        freehand_title.setStyleSheet('font-size: 9pt; font-weight: bold')
        freehand_tab_layout.addWidget(freehand_title, 0, 0, 1, 2)

        freehand_instructions = qt.QLabel("Position the fibula segments relative to each other without the use of guidance."+
                                          "The virtual models of each segment can be seen. However, the planned segments"+
                                          " are not shown with this method. To view the planned segments during positioning, "+
                                          "return to the previous page and select the Guided approach.")
        freehand_instructions.setWordWrap(True)
        freehand_tab_layout.addWidget(freehand_instructions, 1, 0, 1, 2)

        #Position Segment 1
        self.segment1_position_tab = qt.QWidget()
        segment1_position_tab_layout = qt.QGridLayout(self.segment1_position_tab)
        segment1_position_tab_layout.setAlignment(qt.Qt.AlignTop)

        segment1_position_macro_title = qt.QLabel("Macro- Positioning")
        segment1_position_macro_title.setStyleSheet("font-size: 9pt; font-weight: bold")
        segment1_position_tab_layout.addWidget(segment1_position_macro_title, 1, 0, 1, 2)

        segment1_position_macro_instructions = qt.QLabel("Use the visual guidance to place the segment close to the desired position. Once "+
                                         "it is close, press “Start Guidance” to begin micro-positioning the segment. \n")
        segment1_position_macro_instructions.setWordWrap(True)
        segment1_position_tab_layout.addWidget(segment1_position_macro_instructions, 2, 0, 1, 2)

        segment1_position_micro_title = qt.QLabel("Micro- Positioning")
        segment1_position_micro_title.setStyleSheet("font-size: 9pt; font-weight: bold")
        segment1_position_tab_layout.addWidget(segment1_position_micro_title, 3, 0, 1, 2)

        segment1_position_micro_instructions = qt.QLabel("Micro-positioning guidance gives you the precise adjustments that must be made "+
                                         "to get the segment into final position. When finished positioning, press “Positioning Complete” to "+
                                         "finalize its position. Then, continue to the next module. \n")
        segment1_position_micro_instructions.setWordWrap(True)
        segment1_position_tab_layout.addWidget(segment1_position_micro_instructions, 4, 0, 1, 2)

        segment1_position_micro_button = ui.create_button("Start Guidance")
        segment1_position_micro_button.connect('clicked(bool)', self.on_segment1_start_micro)
        segment1_position_tab_layout.addWidget(segment1_position_micro_button, 5, 0, 1, 1)

        segment1_remove_observer = ui.create_button("Pause Guidance")
        segment1_remove_observer.connect('clicked(bool)', self.on_segment1_remove_observer)
        segment1_position_tab_layout.addWidget(segment1_remove_observer, 5, 1, 1, 1)

        segment1_navigation = qt.QGroupBox("Navigation Instructions")
        segment1_navigation.setAlignment(qt.Qt.AlignHCenter)
        segment1_navigation_layout = qt.QGridLayout(segment1_navigation)
        segment1_navigation_layout.setColumnStretch(1, 1)
        segment1_navigation_layout.setColumnStretch(3, 1)

        seg1_length1 = qt.QLabel("Length 1")
        seg1_length1.setStyleSheet("font-size: 9pt; font-weight: bold; padding-right: 20px; padding-left: 10px")
        segment1_navigation_layout.addWidget(seg1_length1, 0, 0)

        self.seg1_value1 = qt.QLabel("0")
        self.seg1_value1.setStyleSheet("font-size: 10pt")
        segment1_navigation_layout.addWidget(self.seg1_value1, 0, 1, 1, 1)

        seg1_length2 = qt.QLabel("Length 2")
        seg1_length2.setStyleSheet("font-size: 9pt; font-weight: bold; padding-right: 20px; padding-left: 10px")
        segment1_navigation_layout.addWidget(seg1_length2, 1, 0, 1, 1)

        self.seg1_value2 = qt.QLabel("0")
        segment1_navigation_layout.addWidget(self.seg1_value2, 1, 1, 1, 1)

        seg1_length3 = qt.QLabel("Length 3")
        seg1_length3.setStyleSheet("font-size: 9pt; font-weight: bold; padding-right: 20px; padding-left: 10px")
        seg1_length3.setAlignment(qt.Qt.AlignCenter)
        segment1_navigation_layout.addWidget(seg1_length3, 2, 0, 1, 1)

        self.seg1_value3 = qt.QLabel("0")
        segment1_navigation_layout.addWidget(self.seg1_value3, 2, 1, 1, 1)

        seg1_length4 = qt.QLabel("Length 4")
        seg1_length4.setStyleSheet("font-size: 9pt; font-weight: bold; padding-right: 20px; padding-left: 10px")
        seg1_length4.setAlignment(qt.Qt.AlignCenter)
        segment1_navigation_layout.addWidget(seg1_length4, 3, 0, 1, 1)

        self.seg1_value4 = qt.QLabel("0")
        segment1_navigation_layout.addWidget(self.seg1_value4, 3, 1, 1, 1)

        seg1_zpos = qt.QLabel("Z Position")
        seg1_zpos.setStyleSheet("font-size: 9pt; font-weight: bold; padding-right: 20px; padding-left: 10px")
        segment1_navigation_layout.addWidget(seg1_zpos, 0, 2, 1, 1)
        self.seg1_zvalue = qt.QLabel("0")
        segment1_navigation_layout.addWidget(self.seg1_zvalue, 0, 3, 1, 1)

        seg1_zrot = qt.QLabel("Z Rotation")
        seg1_zrot.setStyleSheet("font-size: 9pt; font-weight: bold; padding-right: 20px; padding-left: 10px")
        segment1_navigation_layout.addWidget(seg1_zrot, 1, 2, 1, 1)
        self.seg1_zrotvalue = qt.QLabel("0")
        segment1_navigation_layout.addWidget(self.seg1_zrotvalue, 1, 3, 1, 1)

        segment1_position_tab_layout.addWidget(segment1_navigation, 7, 0, 1, 2)

        space3 = qt.QLabel("")
        space3.setStyleSheet("margin-bottom: -10px")
        segment1_position_tab_layout.addWidget(space3, 8, 0, 1, 2)

        segment1_complete = ui.create_button("Positioning Complete")
        segment1_position_tab_layout.addWidget(segment1_complete, 9, 0, 1, 2)
        segment1_complete.connect('clicked(bool)', self.on_seg1_positioning_complete)

        #Position Segment 3
        self.segment3_position_tab = qt.QWidget()
        segment3_position_tab_layout = qt.QGridLayout(self.segment3_position_tab)
        segment3_position_tab_layout.setAlignment(qt.Qt.AlignTop)
       
        segment3_position_macro_title = qt.QLabel("Macro- Positioning")
        segment3_position_macro_title.setStyleSheet("font-size: 9pt; font-weight: bold")
        segment3_position_tab_layout.addWidget(segment3_position_macro_title, 1, 0, 1, 2)

        segment3_position_macro_instructions = qt.QLabel("Use the visual guidance to place the segment in the "+
                                                         "desired position. When finished positioning, press “Positioning Complete” to "+
                                                         "finalize its position. Then, continue to the next module.  \n")
        segment3_position_macro_instructions.setWordWrap(True)
        segment3_position_tab_layout.addWidget(segment3_position_macro_instructions, 2, 0, 1, 2)

        # segment3_position_micro_title = qt.QLabel("Micro- Positioning")
        # segment3_position_micro_title.setStyleSheet("font-size: 9pt; font-weight: bold")
        # segment3_position_tab_layout.addWidget(segment3_position_micro_title, 3, 0, 1, 2)

        # segment3_position_micro_instructions = qt.QLabel("Micro-positioning guidance gives you the precise adjustments that must be made "+
        #                                  "to get the segment into final position. When finished positioning, press “Positioning Complete” to "+
        #                                  "finalize its position. Then, continue to the next module. \n")
        # segment3_position_micro_instructions.setWordWrap(True)
        # segment3_position_tab_layout.addWidget(segment3_position_micro_instructions, 4, 0, 1, 2)

        # segment3_position_micro_button = ui.create_button("Start Guidance")
        # segment3_position_micro_button.connect('clicked(bool)', self.on_segment3_start_micro)
        # segment3_position_tab_layout.addWidget(segment3_position_micro_button, 5, 0, 1, 1)

        # segment3_remove_observer = ui.create_button("Pause Guidance")
        # segment3_remove_observer.connect('clicked(bool)', self.on_segment3_remove_observer)
        # segment3_position_tab_layout.addWidget(segment3_remove_observer, 5, 1, 1, 1)

        # space = qt.QLabel("")
        # space.setStyleSheet("margin-bottom: -10px")
        # segment3_position_tab_layout.addWidget(space, 6, 0, 1, 2)

        # segment3_navigation = qt.QGroupBox("Navigation Instructions")
        # segment3_navigation.setAlignment(qt.Qt.AlignHCenter)
        # segment3_navigation_layout = qt.QGridLayout(segment3_navigation)
        # segment3_navigation_layout.setColumnStretch(1, 1)
        # segment3_navigation_layout.setColumnStretch(3, 1)

        # seg3_length1 = qt.QLabel("Length 1")
        # seg3_length1.setStyleSheet("font-size: 9pt; font-weight: bold; padding-right: 20px; padding-left: 10px")
        # # seg3_length1.setAlignment(qt.Qt.AlignCenter)
        # segment3_navigation_layout.addWidget(seg3_length1, 0, 0)
        # self.seg3_value1 = qt.QLabel("0")
        # self.seg3_value1.setStyleSheet("font-size: 10pt")
        # segment3_navigation_layout.addWidget(self.seg3_value1, 0, 1, 1, 1)

        # seg3_length2 = qt.QLabel("Length 2")
        # seg3_length2.setStyleSheet("font-size: 9pt; font-weight: bold; padding-right: 20px; padding-left: 10px")
        # seg3_length2.setAlignment(qt.Qt.AlignCenter)
        # segment3_navigation_layout.addWidget(seg3_length2, 1, 0, 1, 1)
        # self.seg3_value2 = qt.QLabel("0")
        # segment3_navigation_layout.addWidget(self.seg3_value2, 1, 1, 1, 1)

        # seg3_length3 = qt.QLabel("Length 3")
        # seg3_length3.setStyleSheet("font-size: 9pt; font-weight: bold; padding-right: 20px; padding-left: 10px")
        # seg3_length3.setAlignment(qt.Qt.AlignCenter)
        # segment3_navigation_layout.addWidget(seg3_length3, 2, 0, 1, 1)
        # self.seg3_value3 = qt.QLabel("0")
        # segment3_navigation_layout.addWidget(self.seg3_value3, 2, 1, 1, 1)

        # seg3_length4 = qt.QLabel("Length 4")
        # seg3_length4.setStyleSheet("font-size: 9pt; font-weight: bold; padding-right: 20px; padding-left: 10px")
        # seg3_length4.setAlignment(qt.Qt.AlignCenter)
        # segment3_navigation_layout.addWidget(seg3_length4, 3, 0, 1, 1)
        # self.seg3_value4 = qt.QLabel("0")
        # segment3_navigation_layout.addWidget(self.seg3_value4, 3, 1, 1, 1)

        # seg3_zpos = qt.QLabel("Z Position")
        # seg3_zpos.setStyleSheet("font-size: 9pt; font-weight: bold; padding-right: 20px; padding-left: 10px")
        # # seg3_zpos.setAlignment(qt.Qt.AlignRight)
        # segment3_navigation_layout.addWidget(seg3_zpos, 0, 2, 1, 1)
        # self.seg3_zvalue = qt.QLabel("0")
        # # self.seg3_zvalue.setAlignment(qt.Qt.AlignRight)
        # segment3_navigation_layout.addWidget(self.seg3_zvalue, 0, 3, 1, 1)

        # seg3_zrot = qt.QLabel("Z Rotation")
        # seg3_zrot.setStyleSheet("font-size: 9pt; font-weight: bold; padding-right: 20px; padding-left: 10px")
        # # seg3_length2.setAlignment(qt.Qt.AlignLeft)
        # segment3_navigation_layout.addWidget(seg3_zrot, 1, 2, 1, 1)
        # self.seg3_zrotvalue = qt.QLabel("0")
        # segment3_navigation_layout.addWidget(self.seg3_zrotvalue, 1, 3, 1, 1)

        # segment3_position_tab_layout.addWidget(segment3_navigation, 7, 0, 1, 2)

        # space2 = qt.QLabel("")
        # space2.setStyleSheet("margin-bottom: -10px")
        # segment3_position_tab_layout.addWidget(space2, 8, 0, 1, 2)

        segment3_complete = ui.create_button("Positioning Complete")
        segment3_position_tab_layout.addWidget(segment3_complete, 9, 0, 1, 2)
        segment3_complete.connect('clicked(bool)', self.on_seg3_positioning_complete)

        #Position in Mandible
        self.position_mandible_tab = qt.QWidget()
        position_mandible_tab_layout = qt.QGridLayout(self.position_mandible_tab)
        position_mandible_tab_layout.setAlignment(qt.Qt.AlignTop)

        self.register_hand2 = ctk.ctkCollapsibleButton()
        self.register_hand2.text = "Register Hand 2"
        position_mandible_tab_layout.addWidget(self.register_hand2, 0, 0, 1, 4)
        register_hand2_layout = qt.QGridLayout(self.register_hand2)

        register_segments_title = qt.QLabel("Paired Point Registration")
        register_segments_title.setStyleSheet("font-weight:bold;  padding-left: 1px; padding-top: 10px; padding-bottom: 10px")
        register_hand2_layout.addWidget(register_segments_title, 0, 0, 1, 4)
         
        virtual_fiducial_instructions = qt.QLabel(f"Place Virtual Fiducials: Identify a minimum of three visually distinct points on Hand 2 that are "+
                            "apparent on both the patient’s mandible and the virtual mandible model. Using the mouse, place a "+
                            "fiducial at each of those points. ")
        virtual_fiducial_instructions.setStyleSheet("padding-bottom: 10px")
        virtual_fiducial_instructions.setWordWrap(True)
        register_hand2_layout.addWidget(virtual_fiducial_instructions, 1, 0, 1, 4)

        # Count Number of Mandible CT fiducials Placed
        self.virtual_tool_fiducials_label = qt.QLabel(f'Number of fiducials placed: ')
        self.virtual_tool_fiducials_label.setStyleSheet("padding-bottom: 12px")
        register_hand2_layout.addWidget(self.virtual_tool_fiducials_label, 2, 0, 1, 4)

        # Place Mandible Registration CT fiducials
        self.place_virtual_tool_fiducials_button = ui.create_button("Place Virtual Fiducial", "Place fiducials on mandible model", True)
        self.place_virtual_tool_fiducials_button.setStyleSheet("padding: 5px")
        register_hand2_layout.addWidget(self.place_virtual_tool_fiducials_button, 3, 0, 1, 3)
        self.place_virtual_tool_fiducials_button.connect('clicked(bool)', self.on_place_virtual_hand_fiducial)

        #Remove Mandible Registration CT fiducials
        self.remove_virtual_tool_fiducials_button = ui.create_button("🗑 Delete all", "Delete all Mandible CT fiducials", True)
        register_hand2_layout.addWidget(self.remove_virtual_tool_fiducials_button, 3, 3, 1, 1)
        self.remove_virtual_tool_fiducials_button.connect('clicked(bool)', self.on_remove_virtual_hand_fiducial)

        physical_fiducial_instructions = qt.QLabel(f"Place Physical Fiducials: Using the NDI pointer, place a fiducial at each "+
                "of the corresponding locations on the patient in the same order as the virtual fiducials were placed. ")
        physical_fiducial_instructions.setStyleSheet("padding-top: 15px; padding-bottom: 7px")
        physical_fiducial_instructions.setWordWrap(True)
        register_hand2_layout.addWidget(physical_fiducial_instructions, 4, 0, 1, 4)

        #Count Number of Mandible Patient Fiducials Placed
        self.physical_tool_fiducials_label = qt.QLabel(f'Number of fiducials placed:')
        self.physical_tool_fiducials_label.setStyleSheet("padding-bottom: 12px")
        register_hand2_layout.addWidget(self.physical_tool_fiducials_label, 5, 0, 1, 4)

        #Place Mandible Registration Patient Fiducials
        self.place_physical_tool_fiducials_button = ui.create_button("Place Patient Fiducial", "Place fiducials on patient's mandible", True)
        register_hand2_layout.addWidget(self.place_physical_tool_fiducials_button, 6, 0, 1, 3)
        self.place_physical_tool_fiducials_button.connect('clicked(bool)', self.on_place_physical_tool_fiducial)

        #Remove Mandible Registration Patient Fiducials
        self.remove_physical_tool_fiducials_button = ui.create_button("🗑 Delete all", "Delete all patient fiducials")
        register_hand2_layout.addWidget(self.remove_physical_tool_fiducials_button, 6, 3, 1, 1)
        self.remove_physical_tool_fiducials_button.connect('clicked(bool)', self.on_remove_mandible_patient_fiducial)

        register_hand2_error_instructions = qt.QLabel("Register: Run the paired-point registration and evaluate the error. "+
                        "If it is greater than 1, delete the tool registration and repeat the paired-point registration steps. ")
        register_hand2_error_instructions.setWordWrap(True)
        register_hand2_error_instructions.setStyleSheet("padding-top: 15px; padding-bottom: 7px")
        register_hand2_layout.addWidget(register_hand2_error_instructions, 7, 0, 1, 4)

        self.register_tool_error = qt.QLabel("Root-mean square error: ")
        self.register_tool_error.setStyleSheet("padding-top: 10px; padding-bottom: 5px")
        register_hand2_layout.addWidget(self.register_tool_error, 8, 0, 1, 4)

        self.register_pp = ui.create_button("Register Paired Point")
        self.register_pp.connect('clicked(bool)', self.run_paired_point)
        register_hand2_layout.addWidget(self.register_pp, 9, 0, 1, 3)

        self.delete_registration_button = ui.create_button("🗑 Delete", "Delete Tool Registration", True)
        register_hand2_layout.addWidget(self.delete_registration_button, 9, 3, 1, 1)
        self.delete_registration_button.connect('clicked(bool)', self.on_delete_reg)

        surface_fiducial_instructions = qt.QLabel("Surface Registration")
        surface_fiducial_instructions.setStyleSheet("font-weight: bold; padding-bottom:5px; padding-top: 10px")
        register_hand2_layout.addWidget(surface_fiducial_instructions, 10, 0, 1, 4)
        
        self.surface_count = qt.QLabel("Number of surface fiducials placed: ")
        self.surface_count.setStyleSheet("padding-left: 3px")
        register_hand2_layout.addWidget(self.surface_count, 11, 0, 1, 4)

        self.start_collection = ui.create_button("Start Collection")
        self.start_collection.connect('clicked(bool)', self.on_place_surface)
        register_hand2_layout.addWidget(self.start_collection, 12, 0, 1, 2)

        self.pause_collection = ui.create_button("Pause Collection")
        self.pause_collection.connect('clicked(bool)', self.on_stop_surface)
        register_hand2_layout.addWidget(self.pause_collection, 12, 2, 1, 2)

        self.surface_tool_error = qt.QLabel("Root-mean square error: ")
        self.surface_tool_error.setStyleSheet("padding-top: 15px; padding-bottom: 7px")
        register_hand2_layout.addWidget(self.surface_tool_error, 13, 0, 1, 4)        

        self.register_surface = ui.create_button("Register Surface")
        self.register_surface.connect('clicked(bool)', self.run_surface_registration)
        register_hand2_layout.addWidget(self.register_surface, 14, 0, 1, 4)



        self.guide_position = ctk.ctkCollapsibleButton()
        self.guide_position.text = "Position the Segments"
        self.guide_position.collapsed = 1
        self.guide_position.setVisible(False)
        print(self.guide_position.visible)
        position_mandible_tab_layout.addWidget(self.guide_position, 1, 0, 1, 4)
        guide_position_layout = qt.QGridLayout(self.guide_position)

        position_instructions = qt.QLabel("Attach the middle bone clamp to the articulating arm on the mandible fixation "+
                                "device. Place the segments into mandible gap, following the visual guidance on screen and "+
                                "ensuring bony contact is present. Once in place, lock the articulating arm and use miniplates "+
                                "to secure the segments in the mandible gap. Remove the middle bone clamp and mandible fixator. "+
                                "The reconstruction is complete!")
        position_instructions.setWordWrap(True)
        guide_position_layout.addWidget(position_instructions, 0, 0, 1, 4)

        #Add to Tab Widget
        self.place_segments_tabs = qt.QTabWidget()
        self.place_segments_tabs.setElideMode(qt.Qt.ElideNone)
        self.place_segments_tabs.addTab(guidance_method_tab, "Guidance options")
        self.layout.addWidget(self.place_segments_tabs, 0, 0)

        self.place_segments_tab_state = self.place_segments_tabs.currentIndex
        #self.guidesegcuts_tab_state = 0
        # self.changeMandRegTabVisibility(self.mandreg_tab_state)
        # print(RegisterMandible_Tabs.currentIndex)

        #Navigation Buttons
        navigation_button_box = qt.QGroupBox()
        self.layout.addWidget(navigation_button_box)
        navigation_button_layout = qt.QHBoxLayout(navigation_button_box)

        self.previous_button = ui.create_button("Previous")
        navigation_button_layout.addWidget(self.previous_button)
        self.previous_button.connect('clicked(bool)', self.on_previous_tab_place_segments)
        self.previous_button.setVisible(False)

        self.next_button = ui.create_button("Next")
        navigation_button_layout.addWidget(self.next_button)
        self.next_button.connect('clicked(bool)', self.on_next_tab_place_segments)
        self.next_button.setVisible(False)

        save_box = qt.QGroupBox()
        save_button_layout = qt.QHBoxLayout(save_box)
        self.save_button = ui.create_button("Save scene")
        self.save_button.connect('clicked(bool)', self.on_save)
        save_button_layout.addWidget(self.save_button)
        self.layout.addWidget(save_box)

        self.get_nodes()
        self.logic.on_update_transform_hierarchy(self.number_of_segments)
        # qt.QScrollBar.setMinimum(.QScrollBar)
    def on_previous_tab_place_segments(self):
        if self.place_segments_tab_state == 0:
            slicer.util.selectModule('GuideSegmentCuts')
        elif self.place_segments_tab_state > 0:
            if self.place_segments_tab_state == (self.place_segments_tabs.count - 1) and self.guide_position.visible == True:
                self.guide_position.setVisible(False)
                self.register_hand2.setVisible(True)
                self.virtual_hand_fiducials.SetDisplayVisibility(True)
                self.physical_hand_fiducials.SetDisplayVisibility(True)
                self.update_place_segments_tab_visibility(self.place_segments_tab_state)
            else:
                self.place_segments_tab_state = self.place_segments_tab_state - 1
                self.update_place_segments_tab_visibility(self.place_segments_tab_state)

    def on_next_tab_place_segments(self):
        if self.place_segments_tab_state < (self.place_segments_tabs.count - 1):
            self.place_segments_tab_state = self.place_segments_tab_state + 1
            self.update_place_segments_tab_visibility(self.place_segments_tab_state)
        elif self.place_segments_tab_state == (self.place_segments_tabs.count - 1) and self.guide_position.visible == False:
            self.guide_position.setVisible(True)
            self.guide_position.collapsed = 0
            self.register_hand2.setVisible(False)
            self.virtual_hand_fiducials.SetDisplayVisibility(False)
            self.physical_hand_fiducials.SetDisplayVisibility(False)
            self.set_scene_for_positioning()
        else:
            print("You have completed the reconstruction!")

    def on_save(self):
        dir = os.path.dirname(getNode('MandiblePath').GetText())+"\\SlicerFiles"
        ms.save_scene(dir, "6_PlaceSegments"+str(self.place_segments_tab_state))
     
    def get_nodes(self):
        self.number_of_segments = int(getNode("NumOfSegs").GetText())
        #self.hand2_fiducials = getNode('Hand2Fids')
        self.Hand1RefToHand2Ref = getNode('Hand1RefToHand2Ref')
        self.StylusTipToStylusRef = getNode('StylusTipToStylusRef')
        self.Pointer = getNode("Pointer")

        self.Hand2RefToHand2 = ui.import_node('Hand2RefToHand2', 'vtkMRMLLinearTransformNode')
        self.StylusRefToHand2Ref = ui.import_node('StylusRefToHand2Ref', 'vtkMRMLLinearTransformNode')
        self.virtual_hand_fiducials = ui.import_node('VirtualFids_Hand2', 'vtkMRMLMarkupsFiducialNode')
        self.physical_hand_fiducials = ui.import_node('PhysicalFids_Hand2', 'vtkMRMLMarkupsFiducialNode')
        self.hand_registration =ui.import_node('HandRegistration', 'vtkMRMLFiducialRegistrationWizardNode')

        self.WatchdogHand2Mandible = ui.create_watchdog_node('Watchdog_Hand2Mandible', 'Hand2RefToMandRef', "Segments or Mandible is not in view.")
        try: getNode('Watchdog_GuideHand1').SetDisplayVisibility(0)
        except slicer.util.MRMLNodeNotFoundException: pass 
        try: getNode('Watchdog_GuideHand2').SetDisplayVisibility(0)
        except slicer.util.MRMLNodeNotFoundException: pass 
        try: getNode('Watchdog_GuideHand3').SetDisplayVisibility(0)
        except slicer.util.MRMLNodeNotFoundException: pass 

        try: 
            getNode('ActualSegEndpoints').SetDisplayVisibility(0)
        except slicer.util.MRMLNodeNotFoundException: 
            print("Actual seg endpoints - node not found")

        try: getNode('Watchdog_Hand1Hand2').SetDisplayVisibility(0)
        except slicer.util.MRMLNodeNotFoundException: pass

        if self.number_of_segments == 2:
            self.ActualFibSeg1 = getNode('ActualFibSeg1')
            self.ActualMandSeg1 = getNode('ActualMandSeg1')
            
        if self.number_of_segments == 3:
            self.ActualFibSeg1 = getNode('ActualFibSeg1')
            self.ActualMandSeg1 = getNode('ActualMandSeg1')
            self.ActualFibSeg3 = getNode('ActualFibSeg3')
            self.ActualMandSeg3 = getNode('ActualMandSeg3')
            self.Hand3RefToHand2Ref = getNode('Hand3RefToHand2Ref')

    ##Control tab visibility and page state
    def update_place_segments_tab_visibility(self, state):
        self.place_segments_tabs.setCurrentIndex(state)
        if state == 0:
            self.on_guidance_options_tab()
        if self.guidance_method == "Freehand":
            if state == 1:
                self.on_freehand_tab()
            elif state == 2: 
                self.on_position_mandible_tab()
        elif self.guidance_method == "Guided":
            if self.number_of_segments == 1: 
                if state == 1: 
                    self.on_position_mandible_tab()
            elif self.number_of_segments == 2: 
                if state == 1: 
                    self.on_segment1_position_tab()
                elif state == 2: 
                    self.on_position_mandible_tab()
            elif self.number_of_segments == 3: 
                if state == 1: 
                    self.on_segment1_position_tab()
                elif state == 2: 
                    self.on_segment3_position_tab()
                elif state == 3: 
                    self.on_position_mandible_tab()

    #Set tab states 
    def on_guidance_options_tab(self):
        slicer.modules.models.logic().SetAllModelsVisibility(0)
        getNode('NonResected').SetAndObserveTransformNodeID(getNode('MandToFibModelTransform').GetID())
        getNode('NonResected').SetDisplayVisibility(1)
        self.WatchdogHand2Mandible.SetDisplayVisibility(0)
        for i in range(self.number_of_segments):
            ActualFibSeg = getNode('ActualFibSeg'+str(i+1)).SetDisplayVisibility(1)
            ActualMandSeg = getNode('ActualMandSeg'+str(i+1)).SetDisplayVisibility(1)
        #Display mandible gap here and actual segments

    def on_freehand_tab(self):
        slicer.app.layoutManager().setLayout(19)
        slicer.modules.models.logic().SetAllModelsVisibility(0)
        self.WatchdogHand2Mandible.SetDisplayVisibility(0)
        for i in range(self.number_of_segments):
            ActualFibSeg = getNode('ActualFibSeg'+str(i+1))
            ActualFibSeg.SetDisplayVisibility(1)

    def on_position_mandible_tab(self):
        slicer.app.layoutManager().setLayout(4)
        slicer.modules.models.logic().SetAllModelsVisibility(0)
        self.Pointer.SetDisplayVisibility(1)
        Hand2 = getNode('Hand2')
        Hand2.SetDisplayVisibility(1)
        Hand2.SetAndObserveTransformNodeID(None)
        self.WatchdogHand2Mandible.SetDisplayVisibility(0)
        self.StylusTipToStylusRef.SetAndObserveTransformNodeID(self.StylusRefToHand2Ref.GetID())
        self.StylusRefToHand2Ref.SetAndObserveTransformNodeID(None)
        self.virtual_hand_fiducials.SetDisplayVisibility(True)
        self.physical_hand_fiducials.SetDisplayVisibility(True)

    def set_scene_for_positioning(self):
        #Set Slicer scene for positioning in mandible
        # self.register_hand2.collapsed = 1
        self.guide_position.collapsed = 0
        slicer.app.layoutManager().setLayout(19)
        slicer.modules.models.logic().SetAllModelsVisibility(0)
        self.Pointer.SetDisplayVisibility(0)
        getNode('Watchdog_Hand2Mandible').SetDisplayVisibility(1)
        getNode('NonResected').SetDisplayVisibility(1)
        getNode('NonResected').SetAndObserveTransformNodeID(None)
        for i in range(self.number_of_segments):
            getNode('ActualFibSeg'+str(i+1)).SetDisplayVisibility(1)
            ActualMandSeg = getNode('ActualMandSeg'+str(i+1))
            ActualMandSeg.SetDisplayVisibility(1)
            ActualMandSeg.SetAndObserveTransformNodeID(None)
            ActualMandSeg.GetModelDisplayNode().SetOpacity(0.6)

    def on_segment1_position_tab(self): 
        self.WatchdogHand2Mandible.SetDisplayVisibility(0)
        slicer.app.layoutManager().setLayout(19)
        slicer.modules.models.logic().SetAllModelsVisibility(0)
        self.get_coordinate_frames()
        self.ActualFibSeg1.GetModelDisplayNode().SetOpacity(0.8)
        self.ActualMandSeg1.GetModelDisplayNode().SetOpacity(0.4)
        getNode('NonResected').SetAndObserveTransformNodeID(getNode('MandToFibModelTransform').GetID())
        getNode('Hand2').SetAndObserveTransformNodeID(getNode('Hand2RefToHand2').GetID())
        self.watchdog1 = ui.create_watchdog_node("Watchdog_Hand1Hand2", getNode('Hand1RefToHand2Ref'), 'Hand1 or Hand2 is not in view.')
        self.watchdog1.SetDisplayVisibility(1)
        try: 
            getNode('Watchdog_Hand3Hand2').SetDisplayVisibility(0)
        except slicer.util.MRMLNodeNotFoundException: 
            pass

    def on_segment3_position_tab(self):
        self.WatchdogHand2Mandible.SetDisplayVisibility(0)
        # self.on_segment1_remove_observer()
        slicer.app.layoutManager().setLayout(19)
        slicer.modules.models.logic().SetAllModelsVisibility(0)
        self.get_coordinate_frames()
        self.ActualFibSeg3.GetModelDisplayNode().SetOpacity(0.8)
        self.ActualMandSeg3.GetModelDisplayNode().SetOpacity(0.4)
        getNode('NonResected').SetAndObserveTransformNodeID(getNode('MandToFibModelTransform').GetID())
        getNode('Hand2').SetAndObserveTransformNodeID(getNode('Hand2RefToHand2').GetID())
        self.watchdog3 = ui.create_watchdog_node("Watchdog_Hand3Hand2", getNode('Hand3RefToHand2Ref'), 'Hand3 or Hand2 is not in view.')
        self.watchdog3.SetDisplayVisibility(1)
        try: 
            getNode('Watchdog_Hand1Hand2').SetDisplayVisibility(0)
        except slicer.util.MRMLNodeNotFoundException: 
            pass

    #Functions
    def get_coordinate_frames(self): 
        #Adds coordinate frames and updates visibility 
        for i in range(self.number_of_segments):
            ActualFibSeg = getNode('ActualFibSeg'+str(i+1))
            ActualMandSeg = getNode('ActualMandSeg'+str(i+1))
            ActualFibSeg.SetDisplayVisibility(1)
            ActualMandSeg.SetDisplayVisibility(1)
            fib_coordinate_model = self.add_coordinate_frame("CoordFibSeg"+str(i+1), getNode('Hand'+str(i+1)+'RefToSeg'+str(i+1)), ActualFibSeg)
            mand_coordinate_model = self.add_coordinate_frame("CoordMandSeg"+str(i+1), getNode('MandToFibModelTransform'), ActualFibSeg, ActualMandSeg)

    def add_coordinate_frame(self, node_name, transform, fib_model, mand_model=None):
        try:
            getNode(node_name).SetDisplayVisibility(1)
        except slicer.util.MRMLNodeNotFoundException:
            print("Created coordinate model with name, "+str(node_name))
            if mand_model != None:
                #Get the transform between the current segment location (fib_model) and the target (mand_model)
                rotation = ms.get_transformation_matrix(fib_model.GetPolyData(), mand_model.GetPolyData(), vtk.vtkLandmarkTransform())
                #Get the transformation for the mandible segment 
                coordinate_matrix = ms.generate_coordinate_matrix(mand_model, rotation)
            else:
                #Get the translation for the fibula segment
                coordinate_matrix = ms.generate_coordinate_matrix(fib_model)
            #Create the coordinate model with the translation above applied
            coordinate_model = ui.create_coordinate_model(node_name, coordinate_matrix)
            #Place the coordinate model under the correct transform so its position updates as the segment moves
            coordinate_model.SetAndObserveTransformNodeID(transform.GetID())

    def on_freehand_button(self):
        if self.guidance_method == "Guided": 
            self.place_segments_tabs.removeTab(1)
            self.place_segments_tabs.removeTab(1)
            self.place_segments_tabs.removeTab(1)
        self.guidance_method = "Freehand"
        self.place_segments_tabs.addTab(self.freehand_method_tab, "Freehand")
        self.place_segments_tabs.addTab(self.position_mandible_tab, "Position in Mandible")
        count = self.place_segments_tabs.count
        print(count)
        self.on_next_tab_place_segments()
        self.previous_button.setVisible(True)
        self.next_button.setVisible(True)

    def on_guided_button(self):
        if self.guidance_method == "Freehand":
            self.place_segments_tabs.removeTab(1)
            self.place_segments_tabs.removeTab(1)
        self.guidance_method = "Guided"
        if self.number_of_segments == 2:
            self.place_segments_tabs.addTab(self.segment1_position_tab, "Place Segment 1")
        elif self.number_of_segments == 3: 
            self.place_segments_tabs.addTab(self.segment1_position_tab, "Place Segment 1")
            self.place_segments_tabs.addTab(self.segment3_position_tab, "Place Segment 3")
        self.place_segments_tabs.addTab(self.position_mandible_tab, "Position in Mandible")
        self.on_next_tab_place_segments()
        self.previous_button.setVisible(True)
        self.next_button.setVisible(True)

    def on_segment1_start_micro(self):
        print("Guide segment 1")
        #Get transform to put the target segment in world coordinates
        self.actual_mand_seg1_polydata = ms.harden_transform_polydata(self.ActualMandSeg1)
        self.on_segment1_update_guidance()
        self.on_segment1_add_observer()

    def on_segment1_add_observer(self):
        self.segment1_observer = self.Hand1RefToHand2Ref.AddObserver(slicer.vtkMRMLTransformNode.TransformModifiedEvent, self.on_segment1_on_observer)
        print("Added observer")

    def on_segment1_remove_observer(self):
        self.Hand1RefToHand2Ref.RemoveObserver(self.segment1_observer)
        print("Removed observer")

    def on_segment1_on_observer(self, caller, eventID):
        self.on_segment1_update_guidance()

    def on_segment1_update_guidance(self):
        #Compute adjustments
        deltaL1, deltaL2, deltaL3, deltaL4, deltaZ, deltaPhiZ = self.logic.update_guidance(self.ActualFibSeg1, self.actual_mand_seg1_polydata, getNode('Hand1Coords'), 1)

        #Display the equation outputs in Slicer
        ui.update_label(self.seg1_value1, np.abs(np.round(deltaL1, 1)), 0.4, self.check_direction(deltaL1))
        ui.update_label(self.seg1_value2, np.abs(np.round(deltaL2, 1)), 0.4, self.check_direction(deltaL2))
        ui.update_label(self.seg1_value3, np.abs(np.round(deltaL3, 1)), 0.4, self.check_direction(deltaL3))
        ui.update_label(self.seg1_value4, np.abs(np.round(deltaL4, 1)), 0.4, self.check_direction(deltaL4))
        ui.update_label(self.seg1_zvalue, np.abs(np.round(deltaZ, 1)), 0.4, self.check_direction(deltaZ))
        # if deltaZ <= 0: 
        #     ui.update_label(self.seg1_zvalue, np.abs(np.round(deltaZ, 1)), 0.4, "CW rotations")
        # else: 
        #     ui.update_label(self.seg1_zvalue, np.abs(np.round(deltaZ, 1)), 0.4, "CCW rotations")

        zrots = math.degrees(deltaPhiZ)/360
        if deltaPhiZ <= 0:
            ui.update_label(self.seg1_zrotvalue, np.abs(np.round(zrots, 1)), 0.2, " CW rotations")
        else: 
            ui.update_label(self.seg1_zrotvalue, np.abs(np.round(zrots, 1)), 0.2, " CCW rotations")

    def check_direction(self, L):
        if L >= 0: 
            return " CW rotations"
        else: 
            return " CCW rotations"

    def on_segment3_start_micro(self):
        print("Guide segment 3")
        #Apply the transforms to segment 3 polydata
        self.actual_mand_seg3_polydata = ms.harden_transform_polydata(self.ActualMandSeg3)
        self.on_segment3_update_guidance()
        self.on_segment3_add_observer()

    def on_segment3_add_observer(self):
        self.segment3_observer = self.Hand3RefToHand2Ref.AddObserver(slicer.vtkMRMLTransformNode.TransformModifiedEvent, self.on_segment3_on_observer)
        print("Added observer")

    def on_segment3_remove_observer(self):
       self.Hand3RefToHand2Ref.RemoveObserver(self.segment3_observer)
       print("Removed observer")

    def on_segment3_on_observer(self, caller, eventID):
        self.on_segment3_update_guidance()

    def on_segment3_update_guidance(self):
        #Compute adjustments
        deltaL1, deltaL2, deltaL3, deltaL4, deltaZ, deltaPhiZ = self.logic.update_guidance(self.ActualFibSeg3, self.actual_mand_seg3_polydata, getNode('Hand3Coords'), 3)
        #Display the equation outputs in Slicer
        if deltaL1 >= 0: 
            ui.update_label(self.seg3_value1, np.round(deltaL1, 1), 0.4, "CW")
        else: 
            ui.update_label(self.seg3_value1, np.round(deltaL1, 1), 0.4, "CCW")

        ui.update_label(self.seg3_value2, np.round(deltaL2, 1), 0.4)
        ui.update_label(self.seg3_value3, np.round(deltaL3, 1), 0.4)
        ui.update_label(self.seg3_value4, np.round(deltaL4, 1), 0.4)
        ui.update_label(self.seg3_zvalue, np.round(deltaZ, 1), 0.4)
        ui.update_label(self.seg3_zrotvalue, np.round(math.degrees(deltaPhiZ), 2), 0.2)

    def on_seg1_positioning_complete(self):
        #SEGMENT 1: Update Hand 1 
        Hand1RefToHand2Ref = getNode('Hand1RefToHand2Ref')
        Hand1RefToHand2RefMatrix = vtk.vtkMatrix4x4()
        Hand1RefToHand2Ref.GetMatrixTransformToWorld(Hand1RefToHand2RefMatrix)
        Hand1RefToHand2RefClone = ui.update_transform(Hand1RefToHand2RefMatrix, 'Hand1RefToHand2Ref(Clone)')
        getNode('Hand1RefToSeg1').SetAndObserveTransformNodeID(Hand1RefToHand2RefClone.GetID())
        getNode('Hand1RefToHand1').SetAndObserveTransformNodeID(Hand1RefToHand2RefClone.GetID())
        # try: 
        #     #If the node already exists, just update the transform
        #     Hand1RefToHand2RefClone = getNode('Hand1RefToHand2Ref(Clone)')
        #     Hand1RefToHand2RefClone.SetMatrixTransformToParent(Hand1RefToHand2RefMatrix)
        #     print("Updated node")
        # except slicer.util.MRMLNodeNotFoundException:
        #     #If it does not exist yet, then update it
        #     Hand1RefToHand2RefClone = ui.create_linear_transform(Hand1RefToHand2RefMatrix, 'Hand1RefToHand2Ref(Clone)')
        #     print("Created node")
        # getNode('Hand1RefToSeg1').SetAndObserveTransformNodeID(Hand1RefToHand2RefClone.GetID())
        # getNode('Hand1RefToHand1').SetAndObserveTransformNodeID(Hand1RefToHand2RefClone.GetID())
        # # HandRefToHand2RefClone.SetAndObserveTransformNodeID(Hand2RefToHand2Inv.GetID())
        # HandRefToSeg.SetAndObserveTransformNodeID(HandRefToHand2RefClone.GetID())

        # seg2_to_seg1 = self.get_seg2_to_seg(1)
        # getNode('ActualFibSeg1').SetAndObserveTransformNodeID(seg2_to_seg1.GetID())
        # getNode('VSPFibSeg1').SetAndObserveTransformNodeID(seg2_to_seg1.GetID())
        
    def on_seg3_positioning_complete(self):
        #SEGMENT 3: Update Hand 3
        Hand3RefToHand2Ref = getNode('Hand3RefToHand2Ref')
        Hand3RefToHand2RefMatrix = vtk.vtkMatrix4x4()
        Hand3RefToHand2Ref.GetMatrixTransformToWorld(Hand3RefToHand2RefMatrix)
        Hand3RefToHand2RefClone = ui.update_transform(Hand3RefToHand2RefMatrix, 'Hand3RefToHand2Ref(Clone)')
        getNode('Hand3RefToSeg3').SetAndObserveTransformNodeID(Hand3RefToHand2RefClone.GetID())
        getNode('Hand3RefToHand3').SetAndObserveTransformNodeID(Hand3RefToHand2RefClone.GetID())
        # try: 
        #     #If the node already exists, just update the transform
        #     Hand3RefToHand2RefClone = getNode('Hand3RefToHand2Ref(Clone)')
        #     Hand3RefToHand2RefClone.SetMatrixTransformToParent(Hand3RefToHand2RefMatrix)
        #     print("Updated cloned node")
        # except slicer.util.MRMLNodeNotFoundException:
        #     #If it does not exist yet, then update it
        #     Hand3RefToHand2RefClone = ui.create_linear_transform(Hand3RefToHand2RefMatrix, 'Hand3RefToHand2Ref(Clone)')
        #     print("Created cloned node")
        
        #SEGMENT 1: Update Hand 1 (in case anything has changed or moved)
        # Hand1RefToHand2Ref = getNode('Hand1RefToHand2Ref')
        # Hand1RefToHand2RefMatrix = vtk.vtkMatrix4x4()
        # Hand1RefToHand2Ref.GetMatrixTransformToWorld(Hand1RefToHand2RefMatrix)
        # Hand1RefToHand2RefClone = ui.update_transform(Hand3RefToHand2RefMatrix, 'Hand1RefToHand2Ref(Clone)')
        # getNode('Hand1RefToSeg1').SetAndObserveTransformNodeID(Hand1RefToHand2RefClone.GetID())
        # getNode('Hand1RefToHand1').SetAndObserveTransformNodeID(Hand1RefToHand2RefClone.GetID())
        # try: 
        #     #If the node already exists, just update the transform
        #     Hand1RefToHand2RefClone = getNode('Hand1RefToHand2Ref(Clone)')
        #     Hand1RefToHand2RefClone.SetMatrixTransformToParent(Hand1RefToHand2RefMatrix)
        # except slicer.util.MRMLNodeNotFoundException:
        #     #If it does not exist yet, then update it
        #     Hand1RefToHand2RefClone = ui.create_linear_transform(Hand1RefToHand2RefMatrix, 'Hand1RefToHand2Ref(Clone)')
        

    #Tool Registration before Positioning Segments in Mandible
    def on_place_virtual_hand_fiducial(self):
        register.place_CT_fiducial(self.virtual_hand_fiducials)
        self.virtual_tool_fiducials_label.text = (f'Number of fiducials placed: {self.virtual_hand_fiducials.GetNumberOfFiducials()+1}')
        
    def on_remove_virtual_hand_fiducial(self):
        register.remove_CT_fiducials(self.virtual_hand_fiducials)
        self.virtual_tool_fiducials_label.text = (f'Number of fiducials placed: {self.virtual_hand_fiducials.GetNumberOfFiducials()}')

    def on_place_physical_tool_fiducial(self):
        register.place_patient_fiducial(self.physical_hand_fiducials, self.StylusTipToStylusRef)
        self.physical_tool_fiducials_label.text = (f'Number of fiducials placed: {self.physical_hand_fiducials.GetNumberOfFiducials()}')

    def on_remove_mandible_patient_fiducial(self):
        register.remove_patient_fiducials(self.physical_hand_fiducials, self.StylusRefToHand2Ref)
        self.physical_tool_fiducials_label.text = (f'Number of fiducials placed: {self.physical_hand_fiducials.GetNumberOfFiducials()}')

    def run_paired_point(self):
        self.hand2_pp = ui.update_transform(vtk.vtkMatrix4x4(), "hand2_pp(new)")
        #self.hand2_pp = ui.import_node("hand2_pp(new)", 'vtkMRMLLinearTransformNode')
        error = register.run_registration(self.hand_registration, self.virtual_hand_fiducials, self.physical_hand_fiducials,
                                          self.hand2_pp, self.StylusRefToHand2Ref)
        self.register_tool_error.setText(f'Root mean square error: {error}')

    def on_place_surface(self):
        self.surf_fids = ui.import_node('hand2_surffids(new)')
        self.lastfid = 0
        self.timer = qt.QTimer()
        self.timer.timeout.connect(self.collect_surface_fiducials_timer)
        self.timer.setInterval(100)
        self.timer.start()
        print("Started")
    
    def collect_surface_fiducials_timer(self):
        self.currentfid = self.lastfid + 1
        register.place_patient_fiducial(self.surf_fids, self.StylusTipToStylusRef)
        self.lastfid = self.currentfid
        self.surface_count.setText(f'Number of surface fiducials placed: {self.surf_fids.GetNumberOfFiducials()}')
        return self.currentfid

    def on_stop_surface(self):
        self.timer.stop()
        print("Paused")
    
    def run_surface_registration(self):
        self.hand2_pp = getNode("hand2_pp(new)")
        self.surf_fids = getNode('hand2_surffids(new)')
        surf_reg = ui.import_node("hand2_surfreg(new)", "vtkMRMLLinearTransformNode")
        max_iterations = 100
        register.run_surface_registration(self.surf_fids, getNode('Hand2'), surf_reg, max_iterations)
        error = register.compute_mean_distance(self.surf_fids, getNode('Hand2'), surf_reg, self.hand2_pp)
        self.surface_tool_error.setText(f'Root mean square error: {error}')

        # pp = getNode(self.select_model.currentNode().GetName()+"_pp")
        pp_inv = vtk.vtkMatrix4x4()
        self.hand2_pp.GetMatrixTransformFromParent(pp_inv)

        # surf = getNode(self.select_model.currentNode().GetName()+"_surfacereg")
        surf_inv = vtk.vtkMatrix4x4()
        surf_reg.GetMatrixTransformFromParent(surf_inv)

        reg_mat = vtk.vtkMatrix4x4()
        vtk.vtkMatrix4x4.Multiply4x4(pp_inv, surf_inv, reg_mat)

        # reg_transform = ui.update_transform(reg_mat, self.output_transform.currentNode().GetName())
        # print("Tool registration updated")

        Hand2RefToHand2Alt = ui.update_transform(reg_mat, "Hand2RefToHand2(Alt)")
        # error = register.run_registration(self.hand_registration, self.physical_hand_fiducials,  self.virtual_hand_fiducials, 
        #                                   Hand2RefToHand2Alt, self.StylusRefToHand2Ref)
        # self.register_tool_error.setText(f'Root mean square error: {error}')
        print("Tool registration updated")
        if self.number_of_segments > 1: 
            MandRefToMand = getNode('MandRefToMand')
            Hand2RefToMandRef = getNode('Hand2RefToMandRef')
            Hand2RefToSeg2 = getNode('Hand2RefToSeg2')
            Hand2RefToHand2 = getNode('Hand2RefToHand2')

            Hand2RefToHand2InvMatrix = vtk.vtkMatrix4x4()
            Hand2RefToHand2.GetMatrixTransformToParent(Hand2RefToHand2InvMatrix)
            Hand2RefToHand2InvMatrix.Invert()
            Hand2RefToHand2Inv = ui.update_transform(Hand2RefToHand2InvMatrix, "Hand2RefToHand2(Inv)")

            Hand2RefToMandRef.SetAndObserveTransformNodeID(MandRefToMand.GetID())
            Hand2RefToHand2Alt.SetAndObserveTransformNodeID(Hand2RefToMandRef.GetID())
            Hand2RefToHand2Inv.SetAndObserveTransformNodeID(Hand2RefToHand2Alt.GetID())
            Hand2RefToSeg2.SetAndObserveTransformNodeID(Hand2RefToHand2Inv.GetID())

            #Might need to move this section earlier (to when they say they finish positioning segments relative to each other)
            for i in range(self.number_of_segments):
                if (i + 1) != 2:
                    HandRefToHand2RefClone = getNode('Hand' + str(i+1) + 'RefToHand2Ref(Clone)')
                    HandRefToHand2RefClone.SetAndObserveTransformNodeID(Hand2RefToHand2Inv.GetID())
                    HandRefToSeg = getNode('Hand'+str(i+1)+'RefToSeg'+str(i+1))
                    HandRefToSeg.SetAndObserveTransformNodeID(HandRefToHand2RefClone.GetID())
        else:
            Hand1RefToSeg1 = getNode('Hand1RefToSeg1')
            Hand1RefToMandRef = getNode('Hand1RefToMandRef')
            Hand1RefToSeg1.SetAndObserveTransformNodeID(Hand1RefToMandRef.GetID())

    def on_delete_reg(self):
        self.register_tool_error.setText(f'Root mean square error: ')
        if self.number_of_segments > 1: 
            ui.remove_node('Hand2RefToHand2(Inv)')
            ui.remove_node('Hand2RefToHand2(Alt)')
            getNode('Hand2RefToMandRef').SetAndObserveTransformNodeID(None)
            getNode('Hand2RefToSeg2').SetAndObserveTransformNodeID(None)
            getNode('Hand2').SetAndObserveTransformNodeID(None)
            register.delete_registration(self.StylusRefToHand2Ref)


class PlaceSegmentsLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)
        #self.widget = PlaceSegmentsWidget()
        
        X1 = 15
        X2 = -X1
        X3 = 24
        X4 = -X3

        Y1 = -math.sqrt(30**2 - 15**2)
        Y2 = Y1
        Y3 = Y2 - 16
        Y4 = Y2 - 16

        H = 40
        D = 46
        self.ik = InverseKin(X1, X2, X3, X4, Y1, Y2, Y3, Y4, H, D)

    def on_update_transform_hierarchy(self, number_of_segments):
        Hand2RefToSeg2 = getNode('Hand2RefToSeg2')
        Hand2RefToSeg2.SetAndObserveTransformNodeID(None)

        MandToFibModelTransform = getNode('MandToFibModelTransform')
        MandToFibModelTransform.SetAndObserveTransformNodeID(Hand2RefToSeg2.GetID())

        ActualMandSeg2 = getNode('ActualMandSeg2')
        ActualMandSeg2.SetAndObserveTransformNodeID(MandToFibModelTransform.GetID())

        ActualFibSeg2 = getNode('ActualFibSeg2')
        ActualFibSeg2.SetAndObserveTransformNodeID(Hand2RefToSeg2.GetID())
        #if there are three segments: 
        for i in range(number_of_segments):
            if (i+1) != 2:
                HandRefToHand2Ref = getNode('Hand'+str(i+1)+'RefToHand2Ref')
                HandRefToSegRef = getNode('Hand'+str(i+1)+'RefToSeg'+str(i+1))
                HandRefToSegRef.SetAndObserveTransformNodeID(HandRefToHand2Ref.GetID())
                HandToHandRef = getNode('Hand'+str(i+1)+'RefToHand'+str(i+1))
                HandToHandRef.SetAndObserveTransformNodeID(HandRefToHand2Ref.GetID())

                ActualFibSeg = getNode('ActualFibSeg'+str(i+1))
                ActualFibSeg.SetAndObserveTransformNodeID(HandRefToSegRef.GetID())

                ActualMandSeg = getNode('ActualMandSeg'+str(i + 1))
                MandToFibModelTransform = getNode('MandToFibModelTransform')
                ActualMandSeg.SetAndObserveTransformNodeID(MandToFibModelTransform.GetID())


    def update_guidance(self, actual_fib_model, actual_mand_polydata, hand_coords, hand):
        #Harden transform on actual fibula segment
        actual_fib_polydata = ms.harden_transform_polydata(actual_fib_model)
        #Get transform between fibula and mandible segment 
        fib_to_mand = self.get_transform_between_fibula_and_mandible_seg(hand_coords, actual_fib_polydata, actual_mand_polydata)
        #Extract TRANSLATION adjustments from resulting transform
        x,y,z = self.get_translation(fib_to_mand)
        print(f'X: {np.round(x, 2)}, Y: {np.round(y,2)}, Z: {np.round(z,2)}')
        #Extract ROTATION adjustments from resulting transform
        axis, angle = self.get_rotation_axis_angle(fib_to_mand)
        print(f'Axis: {axis} \nAngle: {angle}\n\n')
        #Input translation and rotation into IK equations to compute 
        #def compute_adjustments(self, x, y, z, axis, angle)
        delta_L1, delta_L2, delta_L3, delta_L4, delta_L5Z, delta_phiZ = self.compute_adjustments(x, y, z, axis, angle, hand)
        return delta_L1, delta_L2, delta_L3, delta_L4, delta_L5Z, delta_phiZ

    def get_transform_between_fibula_and_mandible_seg(self, hand_coords, fibula_polydata, mandible_polydata):
        #Get transform from fibula segment's local system to RAS (Slicer's global coordinate system)
        local_to_global = vtk.vtkMatrix4x4()
        hand_coords.GetMatrixTransformFromWorld(local_to_global)
        local_to_global_transform = vtk.vtkTransform()
        local_to_global_transform.SetMatrix(local_to_global)

        #Apply transform to fibula and mandible segment to put it into global coordinates
        global_fib = ms.transform_polydata(vtk.vtkTransformPolyDataFilter(), fibula_polydata, local_to_global_transform)
        global_mand = ms.transform_polydata(vtk.vtkTransformPolyDataFilter(), mandible_polydata, local_to_global_transform)

        fib_to_mand_transform = ms.get_transformation_matrix_with_centroids(global_fib, global_mand, vtk.vtkLandmarkTransform())
        print(f'Fibula to Mandible Transform: {fib_to_mand_transform}')
        return fib_to_mand_transform

    def get_translation(self, matrix):
        x = matrix.GetElement(0,3)
        y = matrix.GetElement(1,3)
        z = matrix.GetElement(2,3)
        return x, y, z

    def get_rotation_euler(self, matrix):
        r31 = matrix.GetElement(2, 0)
        r32 = matrix.GetElement(2, 1)
        r33 = matrix.GetElement(2, 2)
        r21 = matrix.GetElement(1, 0)
        r11 = matrix.GetElement(0, 0)
        #Euler angles for ZYX
        theta_x = math.atan2(r32, r33)
        theta_y = math.atan2(-r31, math.sqrt(math.pow(r32, 2) + math.pow(r33, 2)))
        theta_z = math.atan2(r21, r11)
        return theta_x, theta_y, theta_z

    def get_rotation_axis_angle(self, matrix):
        rotation = ms.isolate_rotation_matrix(ms.vtkmatrix4x4_to_numpy(matrix))
        axis, angle = ms.R_to_axis_angle(rotation)
        return axis, angle

    def compute_adjustments(self, x, y, z, axis, angle, hand):
        zvec = self.ik.get_zvec(axis, angle)
        phi_x = self.ik.get_phi_x(zvec)
        phi_y = self.ik.get_phi_y(zvec)

        zrot = self.ik.get_zrot(axis, angle)
        phi_z = self.ik.get_phi_z(zrot)

        #TODO: Generalize so it is applicable for arm 1 and 3. Currently specialized to arm 3
        phi_z_act = self.ik.get_phi_z_act3(phi_z, x, y, hand)

        L1, L2, L3, L4, L5Z, input_phi_z_rot = self.ik.calculate_lengths_absolute(x, y, z, phi_x, phi_y, phi_z_act)
        print(f'Absolute lengths L1: {L1}, L2 {L2} L3 {L3} L4 {L4} L5Z {L5Z} PHI Z {math.degrees(input_phi_z_rot)}')

        DL1, DL2, DL3, DL4, DL5Z, Dinput_phi_z_rot = self.ik.calculate_lengths_change(L1, L2, L3, L4, L5Z, input_phi_z_rot)
        print(f'Delta lengths DL1: {DL1}, DL2 {DL2}, DL3 {DL3}, DL4 {DL4}, DL5Z {DL5Z} DPHI Z {math.degrees(Dinput_phi_z_rot)}')

        return DL1, DL2, DL3, DL4, DL5Z, Dinput_phi_z_rot
        #L1 = self.ik.calculateL1(x, y, z, theta_x, theta_y, theta_z)
        #L2 = self.ik.calculateL2(x, y, z, theta_x, theta_y, theta_z)
        #L3 = self.ik.calculateL3(x, y, z, theta_x, theta_y, theta_z)
        #L4 = self.ik.calculateL4(x, y, z, theta_x, theta_y, theta_z)
        #input_rot_z = self.ik.calculateInputRotZ(x, y, z, theta_x, theta_y, theta_z)
        #rot_z = self.ik.calculateRotZ(x, y, z, theta_x, theta_y, theta_z)
        

class PlaceSegmentsTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.delayDisplay("Start test")
        logic = PlaceSegmentsLogic()
        self.delayDisplay("Test passed")