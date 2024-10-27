import os
import unittest
import logging
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin, getNode
import numpy as np 

import ManageSlicer as ms
import ManageUI as ui
from Viewpoint import ViewpointLogic, ViewpointInstance

from ManageRegistration import registration as register
from ManageReconstruction import resection as resect
from ManageReconstruction import reconstruction as vsp


class GuideSegmentCuts(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "5. Guide Segment Cuts"
        self.parent.categories = ["Mandibular Reconstruction"]
        self.parent.dependencies = []
        self.parent.contributors = ["Melissa Yu (UBC)"]
        self.parent.helpText = ""
        self.parent.acknowledgementText = ""

class GuideSegmentCutsWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)
        self.logic = None
        self.nodeInstanceDictionary = {}

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.logic = GuideSegmentCutsLogic()

        #Set slicer scene layout 
        self.set_scene_layout()
        self.number_of_segments = int(getNode("NumOfSegs").GetText())
        self.get_nodes()
        self.set_transform_hierarchy()

        #Show segment label at the top 
        self.segment_count = 1
        self.segment_count_label = qt.QLabel(f'Segment {self.segment_count}')
        self.segment_count_label.setStyleSheet("font-size: 9pt; font-weight: bold; padding: 7px")
        #SegmentCount_Label.setStyleSheet("font-weight: bold")
        self.layout.addWidget(self.segment_count_label)

        #CONNECT HELPING HANDS UI: Connect the helping hands to the fibula length and update the 
        #transform hierarchy accordingly
        connect_hands_tab = qt.QWidget()
        connect_hands_tab_layout = qt.QFormLayout(connect_hands_tab)
        connect_hands_tab_layout.setAlignment(qt.Qt.AlignTop)
        connect_hands_instructions = \
            qt.QLabel("Secure the bone clamps along the length of the fibula, ensuring bone pins are engaged and there "+
            "is no movement between the clamp and bone. Place each bone clamp in the centre of the fibula segment shown on "+
            "screen. Before pressing the “Update Transforms” button below, ensure that the reference frames for the helping "+
            "hands and the fibula can be seen by the optical tracker. If they are not in view, a warning will appear. When ready, "+
            "press “Update Transforms” and proceed to the next module. \n")
        connect_hands_instructions.setWordWrap(True)
        connect_hands_tab_layout.addWidget(connect_hands_instructions)

        update_transforms_button = ui.create_button("Update Transforms")
        #UpdateTransforms_Button.connect('clicked(bool)', self.createCutPlanes)
        update_transforms_button.connect('clicked(bool)', self.on_update_transforms)
        connect_hands_tab_layout.addWidget(update_transforms_button)

        #CUT 1 UI: Position the cutting guide relative to the desired cut plane 
        '''When at this tab, surgeons must position the cutting guide relative to the desired cut plane. 
        The key functions on this tab are to: Show the correct cut plane and cutting guide, Show the live angle error between 
        the desired cut plane and the cutting guide. Once it is position. '''

        cut1_tab = qt.QWidget()
        cut1_tab_layout = qt.QGridLayout(cut1_tab)
        cut1_tab_layout.setAlignment(qt.Qt.AlignTop)
        cut1_tab_layout.setColumnStretch(1, 1)

        cut1_title = qt.QLabel("Cut 1")
        cut1_title.setStyleSheet("font-size: 9pt; font-weight: bold; padding: 3px")
        cut1_tab_layout.addWidget(cut1_title, 0, 0, 1, 2)

        cut1_instructions = qt.QLabel("Position the cutting guide so that the cut plane aligns with the target plane. "+
                "Use the position and angle error measurements to determine when it is at a good location. Once in position, "+
                "use the oscillating saw to perform the cut. ")
        cut1_instructions.setWordWrap(True)
        cut1_instructions.setStyleSheet("padding: 3px")
        cut1_tab_layout.addWidget(cut1_instructions, 1, 0, 1, 2)

        self.cut1_position_error_label = qt.QLabel("Position Error (mm): ")
        self.cut1_position_error_label.setStyleSheet("padding:3px")
        self.cut1_position_error_label.setWordWrap(True)
        cut1_tab_layout.addWidget(self.cut1_position_error_label, 2, 0, 1, 1)

        self.cut1_position_error_value = qt.QLabel("")
        cut1_tab_layout.addWidget(self.cut1_position_error_value, 2, 1, 1, 1)

        self.cut1_angle_error_label = qt.QLabel("Angle Error (°): ")
        self.cut1_angle_error_label.setStyleSheet("padding: 3px")
        self.cut1_angle_error_label.setWordWrap(True)
        cut1_tab_layout.addWidget(self.cut1_angle_error_label, 3, 0, 1, 1)

        self.cut1_angle_error_value = qt.QLabel("")
        cut1_tab_layout.addWidget(self.cut1_angle_error_value, 3, 1, 1, 1)

        cut1_observer_section = ctk.ctkCollapsibleButton()
        cut1_observer_section.collapsed=1
        cut1_observer_section.text = "Observers"
        cut1_tab_layout.addWidget(cut1_observer_section, 6, 0, 1, 2)
        cut1_observer_layout = qt.QHBoxLayout(cut1_observer_section)
        cut1_observer_layout.setMargin(2)

        cut1_add_observer_button = ui.create_button("Add Observers")
        cut1_add_observer_button.connect('clicked(bool)', self.on_cut1_add_observer)
        cut1_observer_layout.addWidget(cut1_add_observer_button)

        cut1_remove_observer_button = ui.create_button("Remove Observers")
        cut1_remove_observer_button.connect('clicked(bool)', self.on_cut1_remove_observer)
        cut1_observer_layout.addWidget(cut1_remove_observer_button)

        #REGISTER CUT 1 UI: Record the position of the cutting guide and calculate the error 
        register_cut1_tab = qt.QWidget()
        register_cut1_tab_layout = qt.QGridLayout(register_cut1_tab)
        register_cut1_tab_layout.setAlignment(qt.Qt.AlignTop)

        register_cut1_title = qt.QLabel("Register Cut 1")
        register_cut1_title.setStyleSheet("font-size: 9pt; font-weight: bold; padding: 3px")
        register_cut1_tab_layout.addWidget(register_cut1_title, 0, 0, 1, 4)

        register_cut1_instructions = qt.QLabel("Position the flag on the cutting guide attachment against the surface of "+
                "the fibula cut to register the cut plane. Once it is in place, press the button below to record the plane "+
                "position.")
        register_cut1_instructions.setWordWrap(True)
        register_cut1_instructions.setStyleSheet("padding: 3px; padding-bottom: 15px")
        register_cut1_tab_layout.addWidget(register_cut1_instructions, 1, 0, 1, 4)

        # self.cut1_fid_count = qt.QLabel("Number of fiducials placed: ")
        # self.cut1_fid_count.setStyleSheet("padding-left: 3px")
        # register_cut1_tab_layout.addWidget(self.cut1_fid_count, 2, 0, 1, 4)

        # place_cut1_fids = ui.create_button("Place Plane Fiducial")
        # place_cut1_fids.connect('clicked(bool)',  self.on_place_cut1_fids)
        # register_cut1_tab_layout.addWidget(place_cut1_fids, 3, 0, 1, 3)

        # delete_cut1_fids = ui.create_button("🗑 Delete all")
        # delete_cut1_fids.connect('clicked(bool)', self.on_delete_cut1_fids)
        # register_cut1_tab_layout.addWidget(delete_cut1_fids, 3, 3, 1, 1)

        # space = qt.QLabel("")
        # space.setStyleSheet("padding-top: 10px")
        # register_cut1_tab_layout.addWidget(space, 4, 0, 1, 4)

        self.register_cut1_error = qt.QLabel(f'Position error: \nAngle error:')
        self.register_cut1_error.setWordWrap(True)
        self.register_cut1_error.setStyleSheet("padding: 3px; padding-bottom: 8px")
        self.register_cut1_error.setVisible(False)
        register_cut1_tab_layout.addWidget(self.register_cut1_error, 5, 0, 1, 4)

        register_cut1_button = ui.create_button("Register Cut 1")
        register_cut1_button.connect('clicked(bool)', self.on_register_cut1)
        register_cut1_tab_layout.addWidget(register_cut1_button, 6, 0, 1, 2)

        self.delete_cut1_button = ui.create_button("Delete Cut 1")
        self.delete_cut1_button.connect('clicked(bool)', self.on_delete_cut1)
        self.delete_cut1_button.setEnabled(0)
        register_cut1_tab_layout.addWidget(self.delete_cut1_button, 6, 2, 2, 2)

        #CUT 2 UI: Position the cutting guide relative to the desired cut plane 
        cut2_tab = qt.QWidget()
        cut2_tab_layout = qt.QGridLayout(cut2_tab)
        cut2_tab_layout.setAlignment(qt.Qt.AlignTop)
        cut2_tab_layout.setColumnStretch(1, 1)

        cut2_title = qt.QLabel("Guide Cut 2")
        cut2_title.setStyleSheet("font-size: 9pt; font-weight: bold; padding: 3px")
        cut2_tab_layout.addWidget(cut2_title, 0, 0, 1, 2)

        cut2_instructions = qt.QLabel("Position the cutting guide so that the cut plane aligns with the target plane. "+
                "Use the position and angle error measurements to determine when it is at a good location. Once in position, "+
                "use the oscillating saw to perform the cut. ")
        cut2_instructions.setWordWrap(True)
        cut2_instructions.setStyleSheet("padding: 3px")
        cut2_tab_layout.addWidget(cut2_instructions, 1, 0, 1, 2)

        self.cut2_position_error_label = qt.QLabel("Position Error (mm): ")
        self.cut2_position_error_label.setStyleSheet("padding: 3px")
        cut2_tab_layout.addWidget(self.cut2_position_error_label, 2, 0, 1, 1)

        self.cut2_position_error_value = qt.QLabel("")
        cut2_tab_layout.addWidget(self.cut2_position_error_value, 2, 1, 1, 1)

        self.cut2_angle_error_label = qt.QLabel("Angle Error (°): ")
        self.cut2_angle_error_label.setStyleSheet("padding: 3px")
        cut2_tab_layout.addWidget(self.cut2_angle_error_label, 3, 0, 1, 1)

        self.cut2_angle_error_value = qt.QLabel("")
        cut2_tab_layout.addWidget(self.cut2_angle_error_value, 3, 1, 1, 1)

        cut2_observer_section = ctk.ctkCollapsibleButton()
        cut2_observer_section.collapsed=1
        cut2_observer_section.text = "Observers"
        cut2_tab_layout.addWidget(cut2_observer_section, 4, 0, 1, 2)
        cut2_observer_layout = qt.QHBoxLayout(cut2_observer_section)
        cut2_observer_layout.setMargin(2)

        cut2_add_observer_button = ui.create_button("Add Observers")
        cut2_add_observer_button.connect('clicked(bool)', self.on_cut2_add_observer)
        cut2_observer_layout.addWidget(cut2_add_observer_button)

        cut2_remove_observer_button = ui.create_button("Remove Observers")
        cut2_remove_observer_button.connect('clicked(bool)', self.on_cut2_remove_observer)
        cut2_observer_layout.addWidget(cut2_remove_observer_button)

        #REGISTER CUT 2 UI: Record the position of the cutting guide and calculate the error 
        register_cut2_tab = qt.QWidget()
        register_cut2_tab_layout = qt.QGridLayout(register_cut2_tab)
        register_cut2_tab_layout.setAlignment(qt.Qt.AlignTop)

        register_cut2_title = qt.QLabel("Register Cut 2")
        register_cut2_title.setStyleSheet("font-size: 9pt; font-weight: bold; padding: 3px")
        register_cut2_tab_layout.addWidget(register_cut2_title, 0, 0, 1, 4)
        
        register_cut2_instructions = qt.QLabel("Position the flag on the cutting guide attachment against the surface of "+
                "the fibula cut to register the cut plane. Once it is in place, press the button below to record the plane "+
                "position.")
        register_cut2_instructions.setWordWrap(True)
        register_cut2_instructions.setStyleSheet("padding: 3px; padding-bottom: 15px")
        register_cut2_tab_layout.addWidget(register_cut2_instructions, 1, 0, 1, 4)

        # self.cut2_fid_count = qt.QLabel("Number of fiducials placed: ")     
        # self.cut2_fid_count.setStyleSheet("padding-left: 3px")
        # register_cut2_tab_layout.addWidget(self.cut2_fid_count, 2, 0, 1, 4)

        # place_cut2_fids = ui.create_button("Place Plane Fiducial")
        # place_cut2_fids.connect('clicked(bool)',  self.on_place_cut2_fids)
        # register_cut2_tab_layout.addWidget(place_cut2_fids, 3, 0, 1, 3)

        # delete_cut2_fids = ui.create_button("🗑 Delete all")
        # delete_cut2_fids.connect('clicked(bool)', self.on_delete_cut2_fids)
        # register_cut2_tab_layout.addWidget(delete_cut2_fids, 3, 3, 1, 1)

        # space2 = qt.QLabel("")
        # space2.setStyleSheet("padding-top: 10px")
        # register_cut2_tab_layout.addWidget(space2, 4, 0, 1, 4)

        self.register_cut2_error = qt.QLabel(f'Position error: \nAngle error:')
        self.register_cut2_error.setWordWrap(True)
        self.register_cut2_error.setStyleSheet("padding: 3px; padding-bottom: 8px")
        self.register_cut2_error.setVisible(False)
        register_cut2_tab_layout.addWidget(self.register_cut2_error, 5, 0, 1, 4)

        self.segment_length_error_label = qt.QLabel("Segment length error: \n")
        self.segment_length_error_label.setStyleSheet("padding-top: 5px; padding-bottom: 5px")
        self.segment_length_error_label.setVisible(0)
        register_cut2_tab_layout.addWidget(self.segment_length_error_label, 6, 0, 1, 4)

        register_cut2_button = ui.create_button("Register Cut 2")
        register_cut2_button.connect('clicked(bool)', self.on_register_cut2)
        register_cut2_tab_layout.addWidget(register_cut2_button, 7, 0, 1, 2)

        self.delete_cut2_button = ui.create_button("Delete Cut 2")
        self.delete_cut2_button.connect('clicked(bool)', self.on_delete_cut2)
        self.delete_cut2_button.setEnabled(0)
        register_cut2_tab_layout.addWidget(self.delete_cut2_button, 7, 2, 1, 2)

        self.next_step_instructions = qt.QLabel("If the cut is accurate, proceed with the current plan to the next segment. "+
                                           "Otherwise, press recalculate to update the remainder of the plan as needed.")
        self.next_step_instructions.setStyleSheet("padding-top: 10px; padding-bottom: 15px")
        self.next_step_instructions.setWordWrap(1)
        register_cut2_tab_layout.addWidget(self.next_step_instructions, 8, 0, 1, 4)

        self.recalculate_plan = ui.create_button("Recalculate Plan")
        self.recalculate_plan.connect('clicked(bool)', self.on_go_recalculate)
        register_cut2_tab_layout.addWidget(self.recalculate_plan, 9, 0, 1, 2)

        self.proceed_with_plan = ui.create_button("Proceed with Plan")
        self.proceed_with_plan.connect('clicked(bool)', self.on_next_guide_cuts_tab)
        register_cut2_tab_layout.addWidget(self.proceed_with_plan, 9, 2, 1, 2)

        # space3 = qt.QLabel("")
        # space3.setStyleSheet('margin-bottom: -10px')
        # register_cut2_tab_layout.addWidget(space3, 8, 0, 1, 4)

        #RECALCULATE VSP
        recalculate_VSP_tab = qt.QWidget()
        # recalculate_VSP_tab_layout = qt.QGridLayout(recalculate_VSP_tab)
        # recalculate_VSP_tab_layout.setAlignment(qt.Qt.AlignTop)

        # self.recalculate_VSP = ctk.ctkCollapsibleButton()
        # self.recalculate_VSP.collapsed = 0
        # self.recalculate_VSP.text = "Recalculate VSP"
        # recalculate_VSP_tab_layout.addWidget(self.recalculate_VSP, 9, 0, 1, 4)
        # self.recalculate_VSP.setStyleSheet("padding: 3px")
        recalculate_VSP_layout = qt.QFormLayout(recalculate_VSP_tab)
        recalculate_VSP_layout.setAlignment(qt.Qt.AlignTop)

        recalculate_VSP_title = qt.QLabel("Recalculate VSP")
        recalculate_VSP_title.setStyleSheet("font-size: 9pt; font-weight: bold")
        recalculate_VSP_layout.addRow(recalculate_VSP_title)

        recalculate_VSP_instructions = qt.QLabel("To recalculate the plan, place another start fiducial at the beginning of "+
                                                 "the next segment and on the same fibula face as the initial point."+
                                                 "To keep the total number of segments the same, reduce the maximum segments accordingly.")
        recalculate_VSP_instructions.setWordWrap(True)
        recalculate_VSP_layout.addRow(recalculate_VSP_instructions)

        self.min_segment_length_input = qt.QLineEdit()
        self.min_segment_length_input.setText(20.)
        recalculate_VSP_layout.addRow("Minimum Segment Length (mm)", self.min_segment_length_input)

        self.segment_separation_input = qt.QLineEdit()
        self.segment_separation_input.setText(15.)
        recalculate_VSP_layout.addRow("Minimum Segment Separation (mm)", self.segment_separation_input)
  
        self.max_segments_input = qt.QLineEdit()
        self.max_segments_input.setText(3)
        recalculate_VSP_layout.addRow("Maximum Segments", self.max_segments_input)

        update_fibula_fiducial = ui.create_button("Update start point")
        update_fibula_fiducial.connect('clicked(bool)', self.on_update_fibula_fiducial)
        recalculate_VSP_layout.addRow(update_fibula_fiducial)

        recalculate_VSP_button = ui.create_button("Recalculate VSP")
        recalculate_VSP_button.connect('clicked(bool)', self.on_recalculate_VSP)
        recalculate_VSP_layout.addRow(recalculate_VSP_button)

        self.delete_recalc_VSP_button = ui.create_button("Delete Recalculated VSP")
        recalculate_VSP_layout.addRow(self.delete_recalc_VSP_button)
        self.delete_recalc_VSP_button.enabled = 0
        self.delete_recalc_VSP_button.connect('clicked(bool)', self.on_delete_recalc_VSP)

        self.compare_VSP_box = qt.QGroupBox("Compare VSP")
        #self.compare_VSP_box.setVisible(False)
        #self.compare_VSP_box.setVisible(True)
        recalculate_VSP_layout.addRow(self.compare_VSP_box)
        compare_VSP_layout = qt.QGridLayout(self.compare_VSP_box)

        self.compare_VSP_label = qt.QLabel("Compare the initial and VSP plan. Select the one you would like to proceed with.")
        self.compare_VSP_label.setWordWrap(True)
       # self.compare_VSP_label.setVisible(False)
        compare_VSP_layout.addWidget(self.compare_VSP_label, 0, 0, 1, 2)

        self.initial_radiobutton = qt.QRadioButton("Initial Plan")
        self.initial_radiobutton.toggled.connect(self.toggle_initial)
        #self.initial_radiobutton.setVisible(False)
        compare_VSP_layout.addWidget(self.initial_radiobutton, 1, 0, 1, 2)

        self.recalc_radiobutton = qt.QRadioButton("Recalculated Plan")
        self.recalc_radiobutton.setChecked(True)
        self.recalc_radiobutton.toggled.connect(self.toggle_recalc)
        #self.recalc_radiobutton.setVisible(False)
        compare_VSP_layout.addWidget(self.recalc_radiobutton, 2, 0, 1, 2)

        # self.compare_VSP_button_box = qt.QGroupBox()
        # self.compare_VSP_button_box.setVisible(False)
        # recalculate_VSP_layout.addRow(self.compare_VSP_button_box)
        # compare_VSP_button_layout = qt.QGridLayout(self.compare_VSP_button_box)

        initial_VSP_button = ui.create_button("Initial VSP")
        compare_VSP_layout.addWidget(initial_VSP_button, 3, 0, 1, 1)
        initial_VSP_button.connect('clicked(bool)', self.on_select_initial)

        recalculated_VSP_button = ui.create_button("Recalculated VSP")
        compare_VSP_layout.addWidget(recalculated_VSP_button, 3, 1, 1, 1)
        recalculated_VSP_button.connect('clicked(bool)', self.on_select_recalculated)

        self.adjust_hand_instructions = qt.QLabel("If the newly planned segment is no longer centred around the "+
                                             "hand, move the hand to re-centre it. Then, press the corresponding "+
                                             "button below to update the associated transform.")
        self.adjust_hand_instructions.setStyleSheet("padding-top: 10px; padding-bottom: 10px")
        self.adjust_hand_instructions.setWordWrap(True)
        #self.adjust_hand_instructions.setVisible(False)
        compare_VSP_layout.addWidget(self.adjust_hand_instructions, 4, 0, 1, 2)

        # self.update_hand1 = ui.create_button("Update Hand 1")
        # compare_VSP_layout.addWidget(self.update_hand1, 5, 0, 1, 2)
        # #self.update_hand1.setVisible(False)
        # self.update_hand1.clicked.connect(lambda state, seg=0: self.logic.update_arm_transform(seg))

        self.update_hand2 = ui.create_button("Update Hand 2")
        compare_VSP_layout.addWidget(self.update_hand2, 6, 0, 1, 2)
        #self.update_hand2.setVisible(False)
        self.update_hand2.clicked.connect(lambda state, seg=1: self.logic.update_arm_transform(seg))

        # self.update_hand3 = ui.create_button("Update Hand 3")
        # #self.update_hand3.setVisible(False)
        # compare_VSP_layout.addWidget(self.update_hand3, 7, 0, 1,2)
        # self.update_hand3.clicked.connect(lambda state, seg=2: self.logic.update_arm_transform(seg))

        # generate_VSP_segments_button = ui.create_button("Generate segments")
        # generate_VSP_segments_button.connect('clicked(bool)', self.on_generate_VSP_segments)
        # recalculate_VSP_layout.addRow(generate_VSP_segments_button)

        #Add to Tab Widget
        self.guide_cuts_tabs = qt.QTabWidget()
        self.guide_cuts_tabs.setElideMode(qt.Qt.ElideNone)
        self.guide_cuts_tabs.addTab(connect_hands_tab, "Connect Segments")
        self.guide_cuts_tabs.addTab(cut1_tab, "Guide Cut 1")
        self.guide_cuts_tabs.addTab(register_cut1_tab, "Register Cut 1")
        self.guide_cuts_tabs.addTab(cut2_tab, "Guide Cut 2")
        self.guide_cuts_tabs.addTab(register_cut2_tab, "Register Cut 2")
        self.guide_cuts_tabs.addTab(recalculate_VSP_tab, "Recalculate Plan")
        self.layout.addWidget(self.guide_cuts_tabs, 0, 0)
        self.guide_cuts_tab_state = self.guide_cuts_tabs.currentIndex
        self.change_cuts_tab_visibility(self.guide_cuts_tab_state)

        #Navigation Buttons
        navigation_button_box = qt.QGroupBox()
        self.layout.addWidget(navigation_button_box)
        navigation_button_layout = qt.QHBoxLayout(navigation_button_box)

        self.previous_button = ui.create_button("Previous")
        navigation_button_layout.addWidget(self.previous_button)
        self.previous_button.connect('clicked(bool)', self.on_previous_guide_cuts_tab)

        self.next_button = ui.create_button("Next")
        navigation_button_layout.addWidget(self.next_button)
        self.next_button.connect('clicked(bool)', self.on_next_guide_cuts_tab)

        save_box = qt.QGroupBox()
        save_button_layout = qt.QHBoxLayout(save_box)
        self.save_button = ui.create_button("Save scene")
        self.save_button.connect('clicked(bool)', self.on_save)
        save_button_layout.addWidget(self.save_button)
        self.layout.addWidget(save_box)
        self.save_count = 0

        updated_plane_position = 0
        #self.createCutPlanes()

        #self.actual_cut_planes = vtk.vtkPlaneCollection()

    def set_scene_layout(self):
        slicer.app.layoutManager().setLayout(19)

    def set_transform_hierarchy(self):
        '''Set the hierarchy to display the cutting guide's location relative to the fibula's reference frame.'''
        FibRefToFib = getNode('FibRefToFib')
        GuideRefToFibRef = getNode('GuideRefToFibRef')
        GuideToGuideRef = getNode('GuideToGuideRef')
        GuideToCut = getNode('GuideToCut')
        Guide = getNode('Guide')
        CutPlane1 = getNode('CutPlane1')
        CutPlane2 = getNode('CutPlane2')
        StylusRefToFibRef = getNode('StylusRefToFibRef')
        StylusTipToStylusRef = getNode('StylusTipToStylusRef')

        GuideRefToFibRef.SetAndObserveTransformNodeID(FibRefToFib.GetID())
        GuideToGuideRef.SetAndObserveTransformNodeID(GuideRefToFibRef.GetID())
        GuideToCut.SetAndObserveTransformNodeID(GuideToGuideRef.GetID())
        Guide.SetAndObserveTransformNodeID(GuideToGuideRef.GetID())
        CutPlane1.SetAndObserveTransformNodeID(GuideToGuideRef.GetID())
        CutPlane2.SetAndObserveTransformNodeID(GuideToGuideRef.GetID())

        StylusRefToFibRef.SetAndObserveTransformNodeID(FibRefToFib.GetID())
        StylusTipToStylusRef.SetAndObserveTransformNodeID(StylusRefToFibRef.GetID())

        for i in range(self.number_of_segments):
            HandRefToFibRef = getNode('Hand' + str(i + 1) + 'RefToFibRef')
            HandRefToFibRef.SetAndObserveTransformNodeID(FibRefToFib.GetID())
            HandRefToHand = getNode('Hand' + str(i + 1) + 'RefToHand' + str(i+1))
            Hand = getNode('Hand' + str(i + 1))
            Hand.SetAndObserveTransformNodeID(HandRefToHand.GetID())
            HandRefToHand.SetAndObserveTransformNodeID(HandRefToFibRef.GetID())
        print("Set hierarchy")

    def get_nodes(self):
        #Fiducial List
        self.number_of_segments = int(getNode("NumOfSegs").GetText())
        self.clipped_fibula = getNode('Clipped Fibula')
        self.GuideRefToFibRef = getNode('GuideRefToFibRef')
        self.WatchdogStylusFibula = getNode('Watchdog_StylusToFibula')
        self.WatchdogStylusFibula.SetDisplayVisibility(0)
        self.WatchdogHand1Fibula = getNode('Watchdog_Hand1ToFibula')
        self.WatchdogHand2Fibula = getNode('Watchdog_Hand2ToFibula')
        self.WatchdogHand3Fibula = getNode('Watchdog_Hand3ToFibula')
        self.WatchdogGuideFibula = getNode('Watchdog_GuideFibula')
        self.WatchdogHand1Guide = getNode('Watchdog_GuideHand1')
        self.WatchdogHand2Guide = getNode('Watchdog_GuideHand2')
        self.WatchdogHand3Guide = getNode('Watchdog_GuideHand3')
        self.GuideToGuideRef = getNode('GuideToGuideRef')
        self.GuideRefToHand1Ref = getNode('GuideRefToHand1Ref')
        self.Hand1RefToFibRef = getNode('Hand1RefToFibRef')

    def on_previous_guide_cuts_tab(self):
        if self.guide_cuts_tab_state > 1:
            self.guide_cuts_tab_state = self.guide_cuts_tab_state - 1
            self.change_cuts_tab_visibility(self.guide_cuts_tab_state)
            print(self.guide_cuts_tab_state)
        elif self.guide_cuts_tab_state == 1 and self.segment_count > 1: 
            self.guide_cuts_tab_state = 4
            self.segment_count = self.segment_count - 1
            self.change_cuts_tab_visibility(self.guide_cuts_tab_state)
            print(self.segment_count)
            self.segment_count_label.setText(f'Segment {self.segment_count}')
            self.cut1_angle_error_label.setText(f'Angle error: ')
            self.cut1_position_error_label.setText(f'Position error: ')
            self.cut2_angle_error_label.setText(f'Angle error: ')
            self.cut2_position_error_label.setText(f'Position error: ')
            self.segment_length_error_label.setText(f'Segment Length Error: ')
        elif self.guide_cuts_tab_state == 1 and self.segment_count == 1: 
            self.guide_cuts_tab_state = self.guide_cuts_tab_state - 1
            self.change_cuts_tab_visibility(self.guide_cuts_tab_state)
            print(self.guide_cuts_tab_state)
        elif self.guide_cuts_tab_state == 0 and self.segment_count == 1:
            slicer.util.selectModule('CalculateVSP')

    def on_next_guide_cuts_tab(self):
        if self.segment_count <= self.number_of_segments and self.guide_cuts_tab_state < 4: 
            self.guide_cuts_tab_state = self.guide_cuts_tab_state + 1
            self.change_cuts_tab_visibility(self.guide_cuts_tab_state)
            print(self.guide_cuts_tab_state)
        elif self.segment_count < self.number_of_segments and self.guide_cuts_tab_state >= 4:
            self.guide_cuts_tab_state = 1
            print(self.guide_cuts_tab_state)
            self.segment_count = self.segment_count + 1
            self.change_cuts_tab_visibility(self.guide_cuts_tab_state)
            print(self.segment_count)
            self.segment_count_label.setText(f'Segment {self.segment_count}')
            self.cut1_angle_error_label.setText(f'Angle error: ')
            self.cut1_position_error_label.setText(f'Position error: ')
            self.cut2_angle_error_label.setText(f'Angle error: ')
            self.cut2_position_error_label.setText(f'Position error: ')
            self.segment_length_error_label.setText(f'Segment Length Error: ')
            self.register_cut1_error.setVisible(0)
            self.register_cut2_error.setVisible(0)
            self.segment_length_error_label.setVisible(0)
            dir = os.path.dirname(getNode('MandiblePath').GetText())+"\\SlicerFiles"
            # ms.save_scene(dir, "6_SegCut"+str(self.segment_count - 1))
        elif self.segment_count == self.number_of_segments and self.guide_cuts_tab_state >= 4:
            slicer.util.selectModule('PlaceSegments')
            self.WatchdogHand1Fibula.SetDisplayVisibility(0)
            self.WatchdogHand2Fibula.SetDisplayVisibility(0)
            self.WatchdogHand3Fibula.SetDisplayVisibility(0)
            self.WatchdogGuideFibula.SetDisplayVisibility(0)

    def on_go_recalculate(self):
        self.change_cuts_tab_visibility(5)
        self.guide_cuts_tab_state = 5

    def on_save(self):
        dir = os.path.dirname(getNode('MandiblePath').GetText())+"\\SlicerFiles"
        ms.save_scene(dir, "5_GuideSegmentCuts"+str(self.guide_cuts_tab_state)+"_"+str(self.save_count))
        self.save_count += 1 

    #Control tab visibility and page state
    def change_cuts_tab_visibility(self, state):
        self.guide_cuts_tabs.setCurrentIndex(state)
        if state == 0:
            self.on_connect_hands_tab()
        elif state == 1:
            self.on_cut1_tab()
        elif state == 2:
            #self.prev_button.setEnabled(1)
            self.on_register_cut1_tab()
        elif state == 3:
            self.on_cut2_tab()
        elif state == 4: 
            self.on_register_cut2_tab()
        elif state == 5: 
            self.on_recalculate_tab()

    #SET TAB STATES
    def on_connect_hands_tab(self):
        for i in range(self.number_of_segments):
            getNode('Hand'+str(i+1)).SetDisplayVisibility(1)  #Make hand models visible to visualize placement along fibula length
            getNode('VSPMandSeg'+str(i+1)).SetDisplayVisibility(0)    #Make planned mandible segments invisible 
            getNode('Watchdog_Hand'+str(i+1)+'ToFibula').SetDisplayVisibility(1)
        getNode('NonResected').SetDisplayVisibility(0)      #Make resected mandible invisible
        getNode('RDP').SetDisplayVisibility(0)
        getNode('StartPoint').SetDisplayVisibility(0)
        self.WatchdogGuideFibula.SetDisplayVisibility(0)

    def on_cut1_tab(self):
        self.GuideRefToHandRef = getNode('GuideRefToHand'+str(self.segment_count)+'Ref')
        self.HandRefToFibRef = getNode('Hand'+str(self.segment_count)+'RefToFibRef')
        self.GuideToGuideRef.SetAndObserveTransformNodeID(self.GuideRefToHandRef.GetID())
        self.GuideRefToHandRef.SetAndObserveTransformNodeID(self.HandRefToFibRef.GetID())

        self.WatchdogHand1Fibula.SetDisplayVisibility(0)
        self.WatchdogHand2Fibula.SetDisplayVisibility(0)
        self.WatchdogHand3Fibula.SetDisplayVisibility(0)
        self.WatchdogGuideFibula.SetDisplayVisibility(0)

        getNode('Watchdog_GuideHand'+str(self.segment_count)).SetDisplayVisibility(1)
        getNode('Watchdog_Hand'+str(self.segment_count)+'ToFibula').SetDisplayVisibility(1)

        self.on_cut1_add_observer()
        self.set_scene_layout()
        print("Set slicer scene")
        try:
            getNode('Plane1Seg'+str(self.segment_count-1)).SetDisplayVisibility(0)
            getNode('Plane0Seg'+str(self.segment_count-1)).SetDisplayVisibility(0)
        except slicer.util.MRMLNodeNotFoundException:
            print("No previous node")
        getNode('Plane0Seg'+str(self.segment_count)).SetDisplayVisibility(1)
        getNode('Guide').SetDisplayVisibility(0)
        getNode('SawBlade').SetDisplayVisibility(1)
        
        view_node = getNode('View1')
        viewpoint = ViewpointLogic.getViewpointForViewNode(self, view_node)

        view1 = getNode('View1')
        viewpoint.setViewNode(view1)
        view1_transform = getNode(str(self.segment_count)+'Cut0View1')
        viewpoint.bullseyeSetTransformNode(view1_transform)
        viewpoint.bullseyeStart()
        viewpoint.bullseyeStop()

        view2 = getNode('View2')
        viewpoint.setViewNode(view2)
        view2_transform = getNode(str(self.segment_count)+'Cut0View2')
        viewpoint.bullseyeSetTransformNode(view2_transform)
        viewpoint.bullseyeStart()
        viewpoint.bullseyeStop()

        view3 = getNode('View3')
        viewpoint.setViewNode(view3)
        view3_transform = getNode(str(self.segment_count)+'Cut0View3')
        viewpoint.bullseyeSetTransformNode(view3_transform)
        viewpoint.bullseyeStart()
        viewpoint.bullseyeStop()


    def on_cut2_tab(self):
        self.GuideRefToHandRef = getNode('GuideRefToHand'+str(self.segment_count)+'Ref')
        self.HandRefToFibRef = getNode('Hand'+str(self.segment_count)+'RefToFibRef')
        self.GuideToGuideRef.SetAndObserveTransformNodeID(self.GuideRefToHandRef.GetID())
        self.GuideRefToHandRef.SetAndObserveTransformNodeID(self.HandRefToFibRef.GetID())

        self.WatchdogHand1Fibula.SetDisplayVisibility(0)
        self.WatchdogHand2Fibula.SetDisplayVisibility(0)
        self.WatchdogHand3Fibula.SetDisplayVisibility(0)
        self.WatchdogGuideFibula.SetDisplayVisibility(0)

        getNode('Watchdog_GuideHand'+str(self.segment_count)).SetDisplayVisibility(1)
        getNode('Watchdog_Hand'+str(self.segment_count)+'ToFibula').SetDisplayVisibility(1)

        self.on_cut2_add_observer()
        try:
            getNode('Plane0Seg'+str(self.segment_count-1)).SetDisplayVisibility(0)
            getNode('Plane1Seg'+str(self.segment_count-1)).SetDisplayVisibility(0)
        except slicer.util.MRMLNodeNotFoundException:
            print("No previous node")
        getNode('Plane1Seg'+str(self.segment_count)).SetDisplayVisibility(1)
        getNode('Plane0Seg'+str(self.segment_count)).SetDisplayVisibility(0)
        getNode('Guide').SetDisplayVisibility(0)
        getNode('SawBlade').SetDisplayVisibility(1)

        view_node = getNode('View1')
        viewpoint = ViewpointLogic.getViewpointForViewNode(self, view_node)

        view1 = getNode('View1')
        viewpoint.setViewNode(view1)
        view1_transform = getNode(str(self.segment_count)+'Cut1View1')
        viewpoint.bullseyeSetTransformNode(view1_transform)
        viewpoint.bullseyeStart()
        viewpoint.bullseyeStop()

        view2 = getNode('View2')
        viewpoint.setViewNode(view2)
        view2_transform = getNode(str(self.segment_count)+'Cut1View2')
        viewpoint.bullseyeSetTransformNode(view2_transform)
        viewpoint.bullseyeStart()
        viewpoint.bullseyeStop()

        view3 = getNode('View3')
        viewpoint.setViewNode(view3)
        view3_transform = getNode(str(self.segment_count)+'Cut1View3')
        viewpoint.bullseyeSetTransformNode(view3_transform)
        viewpoint.bullseyeStart()
        viewpoint.bullseyeStop()

    def on_register_cut1_tab(self):
        self.WatchdogHand1Fibula.SetDisplayVisibility(0)
        self.WatchdogHand2Fibula.SetDisplayVisibility(0)
        self.WatchdogHand3Fibula.SetDisplayVisibility(0)
        self.WatchdogGuideFibula.SetDisplayVisibility(0)

        getNode('Watchdog_GuideHand'+str(self.segment_count)).SetDisplayVisibility(1)
        getNode('Watchdog_Hand'+str(self.segment_count)+'ToFibula').SetDisplayVisibility(1)
        self.on_cut1_remove_observer()

        StylusRefToFibRef = getNode('StylusRefToFibRef')
        StylusTipToStylusRef = getNode('StylusTipToStylusRef')
        StylusTipToStylusRef.SetAndObserveTransformNodeID(StylusRefToFibRef.GetID())

    def on_register_cut2_tab(self):
        self.WatchdogHand1Fibula.SetDisplayVisibility(0)
        self.WatchdogHand2Fibula.SetDisplayVisibility(0)
        self.WatchdogHand3Fibula.SetDisplayVisibility(0)
        self.WatchdogGuideFibula.SetDisplayVisibility(0)

        getNode('Watchdog_GuideHand'+str(self.segment_count)).SetDisplayVisibility(1)
        getNode('Watchdog_Hand'+str(self.segment_count)+'ToFibula').SetDisplayVisibility(1)

        self.on_cut2_remove_observer()
        self.GuideToGuideRef.SetAndObserveTransformNodeID(getNode('GuideRefToHand'+str(self.segment_count)+'Ref').GetID())
        # getNode('GuideRefToHand'+str(self.segment_count)+'Ref').SetAndObserveTransformNodeID(getNode('Hand'+str(self.segment_count)+'RefToFibRef').GetID())
        getNode('VSPFibSeg'+str(self.segment_count)).SetAndObserveTransformNodeID(getNode('Hand'+str(self.segment_count)+'RefToSeg'+str(self.segment_count)).GetID())

        StylusRefToFibRef = getNode('StylusRefToFibRef')
        StylusTipToStylusRef = getNode('StylusTipToStylusRef')
        StylusTipToStylusRef.SetAndObserveTransformNodeID(StylusRefToFibRef.GetID())

        self.next_step_instructions.setVisible(0)
        self.recalculate_plan.setVisible(0)
        self.proceed_with_plan.setVisible(0)
        
    def on_recalculate_tab(self):
        pass

    #Update transforms
    def on_update_transforms(self):
        for i in range(self.number_of_segments):
            self.logic.update_arm_transform(i)
            #getNode('Seg'+str(i)+'CutPlane1').SetDisplayVisibility(0)
            #getNode('Seg'+str(i)+'CutPlane0').SetDisplayVisibility(0)
        #self.clipped_fibula.GetModelDisplayNode().SetOpacity(0.7)

    def on_place_cut1_fids(self):
        StylusTipToStylusRef = getNode('StylusTipToStylusRef')
        self.cut1fids = ui.import_node(str(self.segment_count)+'Cut1Fids')
        register.place_patient_fiducial(self.cut1fids, StylusTipToStylusRef)
        self.cut1fids.SetNthControlPointLocked(self.cut1fids.GetNumberOfFiducials()-1, 1)
        self.cut1_fid_count.text = (f'Number of fiducials placed: {self.cut1fids.GetNumberOfFiducials()}')

    def on_delete_cut1_fids(self):
        StylusRefToFibRef = getNode('StylusRefToFibRef')
        StylusTipToStylusRef = getNode('StylusTipToStylusRef')
        self.cut1fids = ui.import_node(str(self.segment_count)+'Cut1Fids')
        register.remove_patient_fiducials(self.cut1fids, StylusRefToFibRef)
        StylusTipToStylusRef.SetAndObserveTransformNodeID(StylusRefToFibRef.GetID())
        self.cut1_fid_count.text = (f'Number of fiducials placed: {self.cut1fids.GetNumberOfFiducials()}')

    def on_register_cut1(self): 
        markupsplane1 = ui.clone_plane(getNode('CutPlane1'), str(self.segment_count)+"Cut1")
        # self.cut1fids = ui.import_node(str(self.segment_count)+'Cut1Fids')
        # markupsplane1 = ms.makePlaneMarkupFromFiducial(self.cut1fids, str(self.segment_count)+"Cut1")
        markupsplane1.SetDisplayVisibility(0)

        vtkplane1 = ms.get_vtkplane_from_markup_plane(markupsplane1, 1)
        actual_segment_endpoints = ui.import_node('ActualSegEndpoints', 'vtkMRMLMarkupsFiducialNode')
        self.logic.find_segment_endpoint(vtkplane1, self.clipped_fibula, actual_segment_endpoints)
        print("Registered cut 1")
        #Then advise the user to continue to the next 
        self.delete_cut1_button.setEnabled(1)
        
        # Calculate angle error
        angle_deg = self.logic.calculate_angle_error(vtkplane1.GetNormal(), self.cut1_target_normal)
        # Calculate position error
        contour = ms.get_intersection_contour(vtkplane1, self.clipped_fibula)
        current_centre = ms.get_centroid(contour)
        position_error = self.logic.calculate_position_error(self.segment_count, getNode('VSPSegEndpoints'), current_centre, 1)
        # Display position and angle error 
        self.register_cut1_error.setText(f'Position error: {np.round(position_error, 1)} mm\n'+
                                         f'Angle error: {np.round(180-angle_deg, 1)}°')
        self.register_cut1_error.setVisible(1)
        
        getNode('Plane0Seg'+str(self.segment_count)).SetDisplayVisibility(0)

    def on_delete_cut1(self):
        slicer.mrmlScene.RemoveNode(getNode(str(self.segment_count)+'Cut1'))
        getNode('ActualSegEndpoints').RemoveMarkup((self.segment_count-1)*2)
        self.cut1_angle_error_label.setText(f'Angle error: ')
        self.cut1_position_error_label.setText(f'Position error: ')
        self.register_cut1_error.setVisible(0)
        self.delete_cut1_button.setEnabled(0)

    #TEST FUNCTION
    def update_plane_position(self):
        pass
        #if position error was greater than 1 and you want to adjust the second plane accordingly 
        #Get Seg # Plane 2
        #Get the direction of position error for the first cut and get the value of error
        #Create a transform with this translation along the s-axis
        #Move this transform into the transform hierarchy for this cut plane
        #plane2 = getNode(str(self.segment_count)+)

    def on_place_cut2_fids(self):
        StylusTipToStylusRef = getNode('StylusTipToStylusRef')
        self.cut2fids = ui.import_node(str(self.segment_count)+'Cut2Fids')
        register.place_patient_fiducial(self.cut2fids, StylusTipToStylusRef)
        self.cut2fids.SetNthControlPointLocked(self.cut2fids.GetNumberOfFiducials()-1, 1)
        self.cut2_fid_count.text = (f'Number of fiducials placed: {self.cut2fids.GetNumberOfFiducials()}')

    def on_delete_cut2_fids(self):
        StylusRefToFibRef = getNode('StylusRefToFibRef')
        StylusTipToStylusRef = getNode('StylusTipToStylusRef')
        self.cut2fids = ui.import_node(str(self.segment_count)+'Cut2Fids')
        register.remove_patient_fiducials(self.cut2fids, StylusRefToFibRef)
        StylusTipToStylusRef.SetAndObserveTransformNodeID(StylusRefToFibRef.GetID())
        self.cut2_fid_count.text = (f'Number of fiducials placed: {self.cut2fids.GetNumberOfFiducials()}')

    def on_register_cut2(self):        
        #Clone plane 2 to save the cut plane
        markupsplane2 = ui.clone_plane(getNode('CutPlane2'), str(self.segment_count)+"Cut2")
        # self.cut2fids = ui.import_node(str(self.segment_count)+'Cut2Fids')
        # markupsplane2 = ms.makePlaneMarkupFromFiducial(self.cut2fids, str(self.segment_count)+"Cut2")
        markupsplane2.SetDisplayVisibility(0)

        #Apply transform to move the plane from segment space into donor/fibula space
        HandRefToFibRef = getNode('Hand'+str(self.segment_count)+'RefToSeg'+str(self.segment_count))
        transform_matrix = vtk.vtkMatrix4x4()
        HandRefToFibRef.GetMatrixTransformToWorld(transform_matrix)
        transform_matrix.Invert()
        transform = vtk.vtkTransform()
        transform.SetMatrix(transform_matrix)
        print(f'Transform {transform_matrix}')
        markupsplane2.ApplyTransform(transform)

        #Convert both planes to vtk and add both to a plane collection for segment clipping 
        self.actual_cut_planes = vtk.vtkPlaneCollection()   
        vtkplane1 = ms.get_vtkplane_from_markup_plane(getNode(str(self.segment_count)+"Cut1"), 1)
        vtkplane2 = ms.get_vtkplane_from_markup_plane(markupsplane2, 2)
        self.actual_cut_planes.AddItem(vtkplane1)
        self.actual_cut_planes.AddItem(vtkplane2)
        self.create_actual_segment(markupsplane2)

        #Add fiducial for segment endpoint for cut 2 to the node
        actual_segment_endpoints = ui.import_node('ActualSegEndpoints', 'vtkMRMLMarkupsFiducialNode')
        centre = self.logic.find_segment_endpoint(vtkplane2, self.clipped_fibula, actual_segment_endpoints)
        print("Registered cut 2")

        # Calculate angle error of cut 2
        angle_deg = self.logic.calculate_angle_error(vtkplane2.GetNormal(), self.cut2_target_normal)
        # Calculate position error of cut 2
        # contour = ms.get_intersection_contour(vtkplane2, self.clipped_fibula)
        # current_centre = ms.get_centroid(contour)
        #position_error = self.logic.calculate_position_error(self.segment_count, getNode('VSPSegEndpoints'), current_centre, 1)
        position_error = self.logic.calculate_position_error(self.segment_count, getNode("VSPSegEndpoints"), centre, 2)
        # Display position and angle error 
        self.register_cut2_error.setText(f'Position error: {np.round(position_error, 1)} mm\n'+
                                         f'Angle error: {np.round(angle_deg, 1)}°')
        self.register_cut2_error.setVisible(1)

        #Calculate and display length error of overall segment 
        length_error = self.get_length_error()
        self.segment_length_error_label.setText(f'Segment Length Error: {np.round(length_error, 1)} mm')
        self.segment_length_error_label.setVisible(1)

        #If the length error is greater than 1mm, show recalculation section. 
        # if self.segment_count < self.number_of_segments:
        #     if length_error > 1: 
        #         self.recalculate_VSP.collapsed = 0
        #     else: 
        #         self.recalculate_VSP.collapsed = 1
        # else:
        #     self.recalculate_VSP.enabled = 0
        self.delete_cut2_button.setEnabled(1)
        if self.segment_count < self.number_of_segments:
            self.next_step_instructions.setVisible(1)
            self.recalculate_plan.setVisible(1)
            self.proceed_with_plan.setVisible(1)

        getNode('Plane1Seg'+str(self.segment_count)).SetDisplayVisibility(0)

    def on_delete_cut2(self):
        slicer.mrmlScene.RemoveNode(getNode(str(self.segment_count)+'Cut2'))
        getNode('ActualSegEndpoints').RemoveMarkup((self.segment_count-1) * 2 + 1)
        self.cut2_angle_error_label.setText(f'Angle error:')
        self.cut2_position_error_label.setText(f'Position error: ')
        self.segment_length_error_label.setText(f'Segment Length Error: ')
        self.register_cut2_error.setVisible(0)
        self.segment_length_error_label.setVisible(0)
        self.delete_cut2_button.setEnabled(0)

    def create_actual_segment(self, vtkplane2):
        #1. Create actual segment in donor 
        self.logic.create_actual_donor_segment(self.segment_count, self.actual_cut_planes, self.clipped_fibula)
        #2. Create actual segment in mandible
        self.logic.create_actual_mandible_segment(self.segment_count, getNode("ActualFibSeg"+str(self.segment_count)))
        #3. Update the mandible resection plane 
        #Transform cut plane to world
        TDM = vsp.transform_donor_to_mandible(getNode('TSWDSeg'+str(self.segment_count)), 
                                              getNode('TSWMSeg'+str(self.segment_count)))    
        #Update left mandible resection plane
        right_resection_slice = getNode('vtkMRMLSliceNodeGreen')
        resect.update_mandible_slice_plane(TDM, vtkplane2, right_resection_slice)

    '''Observers 
       The observer for cut 1 will be used to calculate the angle error between the cutting guide and the desired cut plane.
       The observer for cut 2 will be used to calculate angle error between the cutting guide and the desired cut plane AND the segment 
       length error between the current segment and the planned segment. Both are watch for changes in Guide Ref to Fib Ref '''

    def on_cut1_add_observer(self):
        self.GuideRefToHandRef = getNode('GuideRefToHand'+str(self.segment_count)+'Ref')
        self.cut1_observer = self.GuideRefToHandRef.AddObserver(slicer.vtkMRMLTransformNode.TransformModifiedEvent, self.on_cut1_guide_movement)
        print("Cut 1 observer added")
        cut1_target_plane = ms.get_vtkplane_from_transform(getNode('TPS0Seg'+str(self.segment_count)))
        self.cut1_target_normal = cut1_target_plane.GetNormal()
        self.cut1_target_normal = [-self.cut1_target_normal[0], -self.cut1_target_normal[1], -self.cut1_target_normal[2]]

        plane1 = ms.get_vtkplane_from_markup_plane(getNode('CutPlane1'), 1)
        angle_deg = self.logic.calculate_angle_error(plane1.GetNormal(), self.cut1_target_normal)
        self.cut1_angle_error_value.setText(f'{np.round(180-angle_deg, 1)}')

        contour = ms.get_intersection_contour(plane1, self.clipped_fibula)
        current_centre = ms.get_centroid(contour)
        position_error = self.logic.calculate_position_error(self.segment_count, getNode('VSPSegEndpoints'), current_centre, 1)
        self.cut1_position_error_value.setText(f'{np.round(position_error, 1)}')
        
    def on_cut1_remove_observer(self):
        self.GuideRefToHandRef.RemoveObserver(self.cut1_observer)
        print("Cut 1 observer removed")

    def on_cut1_guide_movement(self, caller, eventID):
        #Convert markups plane to vtk plane
        plane1 = ms.get_vtkplane_from_markup_plane(getNode('CutPlane1'), 1)
        
        #Calculate angle error
        angle_deg = self.logic.calculate_angle_error(plane1.GetNormal(), self.cut1_target_normal)
        #self.cut1_angle_error_label.setText(f'Angle error: {np.round(180-angle_deg, 1)}°')
        ui.update_label(self.cut1_angle_error_value, np.round(180-angle_deg, 1), 0.2)
        # print(f'Angle error: {np.round(180-angle_deg, 0.2)}°')
        
        #Calculate position error
        contour = ms.get_intersection_contour(plane1, self.clipped_fibula)
        current_centre = ms.get_centroid(contour)
        position_error = self.logic.calculate_position_error(self.segment_count, getNode('VSPSegEndpoints'), current_centre, 1)
        #self.cut1_position_error_label.setText(f'Position error: {np.round(position_error, 1)} mm')
        ui.update_label(self.cut1_position_error_value, np.round(position_error, 1), 0.2)
        # print(f'Position error: {np.round(position_error, 0.2)} mm')

    def on_cut2_add_observer(self):
        self.GuideRefToHandRef = getNode('GuideRefToHand'+str(self.segment_count)+'Ref')
        self.cut2_observer = self.GuideRefToHandRef.AddObserver(slicer.vtkMRMLTransformNode.TransformModifiedEvent, self.on_cut2_guide_movement)
        cut2_target_plane = ms.get_vtkplane_from_transform(getNode('TPS1Seg'+str(self.segment_count)))
        self.cut2_target_normal = cut2_target_plane.GetNormal()
        #print("Cut 2 observer added")

        plane2 = ms.get_vtkplane_from_markup_plane(getNode('CutPlane2'), 2)
        #Calculate angle error 
        angle_deg = self.logic.calculate_angle_error(plane2.GetNormal(), self.cut2_target_normal)
        self.cut2_angle_error_value.setText(f'{np.round(angle_deg, 1)}')
        #print(f'Cut 2 angle: {np.round(angle_deg, 1)}°')

        ##Get the intersection of the plane with the fibula length and the centre of the intersection contour
        contour = ms.get_intersection_contour(plane2, self.clipped_fibula)
        current_centre = ms.get_centroid(contour)
        position_error = self.logic.calculate_position_error(self.segment_count, getNode('VSPSegEndpoints'), current_centre, 2)
        self.cut2_position_error_value.setText(f'{np.round(position_error, 1)}')
        

    def on_cut2_remove_observer(self):
        self.GuideRefToHandRef.RemoveObserver(self.cut2_observer)
        print("Cut 2 observer removed")

    def on_cut2_guide_movement(self, caller, eventID):
        #Convert markups plane to vtk plane
        plane2 = ms.get_vtkplane_from_markup_plane(getNode('CutPlane2'), 2)

        #Calculate angle error 
        angle_deg = self.logic.calculate_angle_error(plane2.GetNormal(), self.cut2_target_normal)
        #self.cut2_angle_error_label.setText(f'Angle error: {np.round(angle_deg, 1)}°')
        ui.update_label(self.cut2_angle_error_value, np.round(angle_deg, 1), 0.2)
        #print(f'Cut 2 angle: {np.round(angle_deg, 1)}°')

        ##Get the intersection of the plane with the fibula length and the centre of the intersection contour
        contour = ms.get_intersection_contour(plane2, self.clipped_fibula)
        current_centre = ms.get_centroid(contour)
        position_error = self.logic.calculate_position_error(self.segment_count, getNode('VSPSegEndpoints'), current_centre, 2)
        #self.cut2_position_error_label.setText(f'Position error: {np.round(position_error, 1)} mm')
        ui.update_label(self.cut2_position_error_value, np.round(position_error, 1), 0.2)

    def on_select_initial(self):
        self.on_next_guide_cuts_tab()

    def on_select_recalculated(self):
        num_of_segs = int(getNode("NumOfSegs(Recalc)").GetText())
        for i in range(num_of_segs - self.segment_count):
            #try:
            getNode('VSPMandSeg'+str(i+1+self.segment_count)).SetName('VSPMandSeg'+str(i+1+self.segment_count)+'(Original)')
            getNode('VSPFibSeg'+str(i+1+self.segment_count)).SetName('VSPFibSeg'+str(i+1+self.segment_count)+'(Original)')
            getNode('TPS0Seg'+str(i+1+self.segment_count)).SetName('TPS0Seg'+str(i+1+self.segment_count)+'(Original)')
            getNode('TPS1Seg'+str(i+1+self.segment_count)).SetName('TPS1Seg'+str(i+1+self.segment_count)+'(Original)')
            getNode('TSWDSeg'+str(i+1+self.segment_count)).SetName('TSWDSeg'+str(i+1+self.segment_count)+'(Original)')
            getNode('TSWMSeg'+str(i+1+self.segment_count)).SetName('TSWMSeg'+str(i+1+self.segment_count)+'(Original)')
            getNode('Plane0Seg'+str(i+1+self.segment_count)).SetName('Plane0Seg'+str(i+1+self.segment_count)+'(Original)')
            getNode('Plane1Seg'+str(i+1+self.segment_count)).SetName('Plane1Seg'+str(i+1+self.segment_count)+'(Original)')

            getNode('VSPMandSeg'+str(i+1+self.segment_count)+'(Recalc)').SetName('VSPMandSeg'+str(i+1+self.segment_count))
            getNode('VSPFibSeg'+str(i+1+self.segment_count)+'(Recalc)').SetName('VSPFibSeg'+str(i+1+self.segment_count))
            getNode('TPS0Seg'+str(i+1+self.segment_count)+'(Recalc)').SetName('TPS0Seg'+str(i+1+self.segment_count))
            getNode('TPS1Seg'+str(i+1+self.segment_count)+'(Recalc)').SetName('TPS1Seg'+str(i+1+self.segment_count))
            getNode('TSWDSeg'+str(i+1+self.segment_count)+'(Recalc)').SetName('TSWDSeg'+str(i+1+self.segment_count))
            getNode('TSWMSeg'+str(i+1+self.segment_count)+'(Recalc)').SetName('TSWMSeg'+str(i+1+self.segment_count))
            getNode('Plane0Seg'+str(i+1+self.segment_count)+'(Recalc)').SetName('Plane0Seg'+str(i+1+self.segment_count))
            getNode('Plane1Seg'+str(i+1+self.segment_count)+'(Recalc)').SetName('Plane1Seg'+str(i+1+self.segment_count))
            #except slicer.util.MRMLNodeNotFoundException:
            #    print("Node not found")
        try: 
            getNode('RDPPoints').SetName('RDPPoints(Original)')
            getNode('RDPPoints(Recalc)').SetName('RDPPoints')
            getNode('RDP').SetName('RDP(Original)')
            getNode('RDP(Recalc)').SetName('RDP')
            getNode('VSPSegEndpoints').SetName('VSPSegEndpoints(Original)')
            getNode('VSPSegEndpoints(Recalc)').SetName('VSPSegEndpoints')
            getNode('NumOfSegs').SetName('NumOfSegs(Original)')
            getNode('NumOfSegs(Recalc)').SetName('NumOfSegs')
        except slicer.util.MRMLNodeNotFoundException:
            print("Node not found")

        self.adjust_hand_instructions.setVisible(True)
        if self.segment_count == 1: 
            self.update_hand2.setVisible(True)
            if num_of_segs == 3:
                self.update_hand3.setVisible(True)
        elif self.segment_count == 2:
            self.update_hand3.setVisible(True)
        print("Proceed with Recalculated")


        #self.on_next_guide_cuts_tab()

    def toggle_initial(self, selected):
        if selected:
            slicer.modules.models.logic().SetAllModelsVisibility(0)
            getNode('NonResected').SetDisplayVisibility(1)
            for i in range(self.segment_count):
                getNode('ActualMandSeg'+str(i+1)).SetDisplayVisibility(1)
            for i in range(self.number_of_segments-self.segment_count):
                getNode('VSPMandSeg'+str(i+1+self.segment_count)).SetDisplayVisibility(1)

    def toggle_recalc(self, selected):
       if selected:
           slicer.modules.models.logic().SetAllModelsVisibility(0)
           getNode('NonResected').SetDisplayVisibility(1)
           for i in range(self.segment_count):
                getNode('ActualMandSeg'+str(i+1)).SetDisplayVisibility(1)
           for i in range(self.number_of_segments-self.segment_count):
                getNode('VSPMandSeg'+str(i+1+self.segment_count)+'(Recalc)').SetDisplayVisibility(1)

    def get_length_error(self):
        index_start = (self.segment_count * 2) - 2
        index_end = index_start + 1

        ActualSegment = getNode('ActualSegEndpoints')
        actual_start = [0,0,0]
        ActualSegment.GetNthControlPointPosition(index_start, actual_start)
        actual_end = [0,0,0]
        ActualSegment.GetNthControlPointPosition(index_end, actual_end)
        actual_length = self.logic.calculate_segment_length(actual_start, actual_end)
        print(f'Actual segment length: {actual_length}')

        VSPSegment = getNode('VSPSegEndpoints') 
        target_start =[0,0,0] 
        VSPSegment.GetNthControlPointPosition(index_start, target_start)
        target_end = [0,0,0]
        VSPSegment.GetNthControlPointPosition(index_end, target_end)
        target_length = self.logic.calculate_segment_length(target_start, target_end)
        print(f'Target segment length: {target_length}')

        length_error = actual_length - target_length
        #self.logic.calculate_length_error(target_length, actual_length)
        # self.segment_length_error_label.setText(f'Segment Length Error: {np.round(length_error, 1)} mm')
        return length_error 
        #self.segment_length_error_label.setText(f'Actual segment length: {actual_length} mm\n' +  
        #                                        f'Target segment length: {target_length} mm\n' +
        #                                        f'Segment Length Error: {np.round(length_error, 1)} mm')

    def on_update_fibula_fiducial(self):
        FibFid = getNode('StartPoint')
        FibFid.SetDisplayVisibility(1)
        slicer.modules.markups.logic().SetActiveListID(FibFid)
        # FibFid.RemoveAllMarkups()
        slicer.modules.markups.logic().StartPlaceMode(0)
        FibFid.SetNthControlPointLocked(0, 1)

    def on_recalculate_VSP(self):   
        genVSP = vsp.connect_JVM()

        minSegLength = float(self.min_segment_length_input.text)
        maxSegments = int(self.max_segments_input.text)
        segSeparation = float(self.segment_separation_input.text)

        contour = getNode('Contour')
        fibfid = getNode('StartPoint')
        fibPathNode = getNode('FibulaPath')
        mandPathNode = getNode('MandiblePath')
        TCW = getNode('TCW')

        #hf.checkPlaneNormalDirection(getNode('vtkMRMLSliceNodeGreen'), getNode('vtkMRMLSliceNodeYellow')

        rightVTKPlane = ms.get_vtkplane_from_slice(getNode('vtkMRMLSliceNodeGreen'))
        leftVTKPlane = ms.get_vtkplane_from_slice(getNode('vtkMRMLSliceNodeYellow'))

        fibula_segments = vsp.run_VSP(genVSP, segSeparation, minSegLength, maxSegments, contour, fibPathNode, mandPathNode,
                                     leftVTKPlane, rightVTKPlane, fibfid, TCW, False, "(Recalc)")
        vsp.generate_segment_transforms(genVSP, fibula_segments, self.segment_count, "(Recalc)")
        self.on_generate_VSP_segments()

        getNode('RDPPoints(Recalc)').SetDisplayVisibility(0)
        getNode('VSPSegEndpoints(Recalc)').SetDisplayVisibility(0)
        getNode('vtkMRMLSliceNodeGreen').SetSliceVisible(0)
        # self.compare_VSP_label.setVisible(True)
        # self.initial_radiobutton.setVisible(True)
        # self.recalc_radiobutton.setVisible(True)
        # self.compare_VSP_button_box.setVisible(True)
        self.compare_VSP_box.setVisible(True)
        self.delete_recalc_VSP_button.enabled = 1

    def on_generate_VSP_segments(self):
        numOfSegs = int(getNode('NumOfSegs').GetText()) - self.segment_count
        clipped_fibula = getNode('Clipped Fibula')
        vsp.create_donor_segments(clipped_fibula, numOfSegs, self.segment_count, "(Recalc)")
        vsp.create_mandible_segments(numOfSegs, self.segment_count, "(Recalc)")
        vsp.create_cut_plane_model(numOfSegs, self.segment_count, "(Recalc)")

    def on_delete_recalc_VSP(self):
        for i in range(self.number_of_segments - self.segment_count): #if you had 3 segments and on segment 1, you would need to iterate through the remaining 2
            ui.remove_node('TPS0Seg'+ str(i + 1 + self.segment_count) + '(Recalc)')
            ui.remove_node('TPS1Seg'+ str(i + 1 + self.segment_count) + '(Recalc)')
            ui.remove_node('TSWMSeg'+ str(i + 1 + self.segment_count) + '(Recalc)')
            ui.remove_node('TSWDSeg'+ str(i + 1 + self.segment_count) + '(Recalc)')
            ui.remove_node('VSPFibSeg'+ str(i + 1 + self.segment_count) + '(Recalc)')
            ui.remove_node('VSPMandSeg'+ str(i + 1 + self.segment_count) + '(Recalc)')
            ui.remove_node('Plane0Seg'+str(i+1+self.segment_count)+'(Recalc)')
            ui.remove_node('Plane1Seg'+str(i+1+self.segment_count)+'(Recalc)')
            getNode(str(i + 1 + self.segment_count)+"Cut0View1").SetAndObserveTransformNodeID(getNode('TPS0Seg'+str(i + 1 + self.segment_count)).GetID())
            getNode(str(i + 1 + self.segment_count)+"Cut0View2").SetAndObserveTransformNodeID(getNode('TPS0Seg'+str(i + 1 + self.segment_count)).GetID())
            getNode(str(i + 1 + self.segment_count)+"Cut0View3").SetAndObserveTransformNodeID(getNode('TPS0Seg'+str(i + 1 + self.segment_count)).GetID())
            getNode(str(i + 1 + self.segment_count)+"Cut1View1").SetAndObserveTransformNodeID(getNode('TPS1Seg'+str(i + 1 + self.segment_count)).GetID())
            getNode(str(i + 1 + self.segment_count)+"Cut1View2").SetAndObserveTransformNodeID(getNode('TPS1Seg'+str(i + 1 + self.segment_count)).GetID())
            getNode(str(i + 1 + self.segment_count)+"Cut1View3").SetAndObserveTransformNodeID(getNode('TPS1Seg'+str(i + 1 + self.segment_count)).GetID())
        ui.remove_node('RDPPoints(Recalc)')
        ui.remove_node('RDP(Recalc)')
        ui.remove_node('VSPSegEndpoints(Recalc)')
        self.delete_recalc_VSP_button.enabled = 0
        self.compare_VSP_box.setVisible(False)

    # def on_update_hand1(self):
    #     self.logic.update_arm_transform(0)

    

class GuideSegmentCutsLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)

    def update_arm_transform(self, seg):
        HandRefToFibRef = getNode('Hand' + str(seg + 1) + 'RefToFibRef')
        Segment = getNode('VSPFibSeg' + str(seg+1))
        HandRefToFibRef_mat = vtk.vtkMatrix4x4()
        HandRefToFibRef.GetMatrixTransformFromWorld(HandRefToFibRef_mat)
        #HandRefToFibRef_Node = ui.create_linear_transform(HandRefToFibRef_Mat, 'Hand' + str(seg+1) + 'RefToSeg'+ str(seg+1))
        #HandRefToSeg = ui.import_node('Hand' + str(seg+1) + 'RefToSeg'+ str(seg+1), 'vtkMRMLLinearTransformNode')
        HandRefToSeg = ui.update_transform(vtk.vtkMatrix4x4(), 'Hand' + str(seg+1) + 'RefToSeg'+ str(seg+1))
        HandRefToSeg.SetMatrixTransformToParent(HandRefToFibRef_mat)
        HandRefToSeg.SetAndObserveTransformNodeID(HandRefToFibRef.GetID())
        #Segment.SetAndObserveTransformNodeID(HandRefToSeg.GetID())
        print(f"Hand {seg + 1} transform updated")

    def create_actual_donor_segment(self, segment_number, plane_collection, fibula):
        #clipping_planes = vtk.vtkPlaneCollection()
        #clipping_planes.AddItem(plane_collection.GetItem(0))
        #clipping_planes.AddItem(plane_collection.GetItem(1))
        print(plane_collection)
        clipped_act_seg = ms.clip_polydata(plane_collection, fibula.GetPolyData())
        print(clipped_act_seg)
        actual_segment = ms.create_model(clipped_act_seg, "ActualFibSeg"+str(segment_number), [1, (segment_number-1)/2, 0])
        print(f'Segment_number: {segment_number}')

        #Update hierarchy so the actual segment replaces the planned segment 
        #HandRefToSegRef = getNode('Hand'+str(segment_number)+'RefToSeg'+str(segment_number))    #GetParentTransformNode()
        #parent_transform = getNode('VSPFibSeg' + str(segment_number)).GetParentTransformNode()
        actual_segment.SetAndObserveTransformNodeID(getNode('Hand'+str(segment_number)+'RefToSeg'+str(segment_number)).GetID())

        #Turn visibility planned segment off and show the actual segment instead
        getNode('VSPFibSeg' + str(segment_number)).SetDisplayVisibility(0)
        actual_segment.SetDisplayVisibility(1)

    def create_actual_mandible_segment(self, segment_number, donor_segment):
        donor_polydata = donor_segment.GetPolyData()
        TSWD = getNode("TSWDSeg"+str(segment_number)) #Want the inverse
        TDW_mat = vtk.vtkMatrix4x4()  #TDW = Transform Donor to World
        TSWD.GetMatrixTransformFromParent(TDW_mat)

        TSWM = getNode("TSWMSeg"+str(segment_number)) 
        TWM_mat = vtk.vtkMatrix4x4() #TWM = Transform World to Mandible
        TSWM.GetMatrixTransformToParent(TWM_mat) 

        TDM = vtk.vtkTransform() #TDM = Transform Donor to Mandible (Concatenated TDW and TWM)
        TDM.SetMatrix(TWM_mat)
        TDM.Concatenate(TDW_mat)

        if segment_number == 2: 
            TDM_inv = vtk.vtkMatrix4x4()
            TDM.GetInverse(TDM_inv)
            ui.create_linear_transform(TDM_inv, "MandToFibModelTransform")

        transform_filter = vtk.vtkTransformPolyDataFilter()
        mandible_segment_polydata = ms.transform_polydata(transform_filter, donor_polydata, TDM)
        
        mandible_segment = ms.create_model(mandible_segment_polydata, "ActualMandSeg"+ str(segment_number), [1, (segment_number-1)/2, 0])
        #mandible_segment.GetModelDisplayNode().SetColor(1, 0.66666, 0)
        mandible_segment.GetModelDisplayNode().VisibilityOn()

        #if you are on the last segment, copy all the mandible segments and apply the mand to fib model transform to them
        #so they centre around the second, middle second segment.

    def calculate_segment_length(self, start_point, end_point):
        if (end_point[2]-start_point[2]) <= 0:
            distance = np.sqrt(((end_point[0]-start_point[0])**2) + ((end_point[1]-start_point[1])**2) + ((end_point[2]-start_point[2])**2))
        else: 
            distance = - np.sqrt(((end_point[0]-start_point[0])**2) + ((end_point[1]-start_point[1])**2) + ((end_point[2]-start_point[2])**2))
        return distance

    def find_segment_endpoint(self, plane, model, fiducial_list):
        contour = ms.get_intersection_contour(plane, model)
        centre = ms.get_centroid(contour)
        slicer.modules.markups.logic().SetActiveListID(fiducial_list)
        slicer.modules.markups.logic().AddFiducial(centre[0], centre[1], centre[2])
        return centre 

    def calculate_angle_error(self, plane1_normal, plane2_normal):
        angle_rad = vtk.vtkMath.AngleBetweenVectors(plane1_normal, plane2_normal)
        angle_deg = vtk.vtkMath.DegreesFromRadians(angle_rad)
        return angle_deg

    def calculate_position_error(self, segment_number, target_markup, current_centre, cut_no):
        VSP_segment_endpoints = slicer.util.arrayFromMarkupsControlPoints(target_markup)
        index = (segment_number * 2) - 2 + (cut_no - 1)
        target_centre = VSP_segment_endpoints[index]
        print(target_centre)
        print(current_centre)
        position_error = np.sqrt((target_centre[0] - current_centre[0])**2 + 
                                 (target_centre[1] - current_centre[1])**2 + 
                                 (target_centre[2] - current_centre[2])**2)
        return position_error


class GuideSegmentCutsTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.delayDisplay("Start test")
        logic = GuideSegmentCutsLogic()
        self.delayDisplay("Test passed")
