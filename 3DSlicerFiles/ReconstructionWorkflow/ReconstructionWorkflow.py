import os
import unittest
import logging
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin, getNode
from DICOMLib import DICOMUtils

from ManageRegistration import registration as register
import ManageSlicer as ms
import ManageUI as ui
#
# ReconstructionWorkflow
#

class ReconstructionWorkflow(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent)
    self.parent.title = "0. Set-up and Instructions"  # TODO: make this more human readable by adding spaces
    self.parent.categories = ["Mandibular Reconstruction"]  # TODO: set categories (folders where the module shows up in the module selector)
    self.parent.dependencies = []  # TODO: add here list of module names that this module requires
    self.parent.contributors = ["Melissa Yu (UBC)"]  # TODO: replace with "Firstname Lastname (Organization)"
    # TODO: update with short description of the module and a link to online module documentation
    self.parent.helpText = """
This is an example of scripted loadable module bundled in an extension.
See more information in <a href="https://github.com/organization/projectname#ReconstructionWorkflow">module documentation</a>.
"""
    # TODO: replace with organization, grant and thanks
    self.parent.acknowledgementText = """
This file was originally developed by Jean-Christophe Fillion-Robin, Kitware Inc., Andras Lasso, PerkLab,
and Steve Pieper, Isomics, Inc. and was partially funded by NIH grant 3P41RR013218-12S1.
"""

#
# ReconstructionWorkflowWidget
#

class ReconstructionWorkflowWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)  # needed for parameter node observation

    def setup(self):
        """
        Called when the user opens the module the first time and the widget is initialized.
        """
        ScriptedLoadableModuleWidget.setup(self)
        self.logic = ReconstructionWorkflowLogic()
        
        setup_tab = qt.QWidget()
        setup_tab_layout = qt.QVBoxLayout(setup_tab)
        setup_tab_layout.setAlignment(qt.Qt.AlignTop)
        slicer.app.layoutManager().setLayout(4)
        #Setup_TabLayout.setVerticalSpacing(7)
        #Setup_Title = qt.QLabel("Import Models")
        #Setup_TabLayout.addWidget(Setup_Title)

        #IMPORT MANDIBLE
        mandible_groupbox = qt.QGroupBox("Mandible")
        #MGroupBox.setStyleSheet("font-size: 9pt")
        mandible_groupbox_layout = qt.QFormLayout()
        self.mandible_path = ctk.ctkPathLineEdit()
        import_mandible_button = ui.create_button("Import Mandible")
        import_mandible_button.connect('clicked(bool)', self.on_import_mandible)

        #Mandible_Layout.addRow(ImportMandible)
        mandible_groupbox_layout.addRow("Input mandible path  ", self.mandible_path)
        mandible_groupbox_layout.addRow(import_mandible_button)
        mandible_groupbox.setLayout(mandible_groupbox_layout)
        setup_tab_layout.addWidget(mandible_groupbox)

        self.mandible_path_node = ui.import_node("MandiblePath", "vtkMRMLTextNode")

        fibula_groupbox = qt.QGroupBox("Fibula")
        #MGroupBox.setStyleSheet("font-size: 9pt")
        fibula_groupbox_layout = qt.QFormLayout()
        self.fibula_path = ctk.ctkPathLineEdit()
        import_fibula_button = ui.create_button("Import Fibula")
        import_fibula_button.connect('clicked(bool)', self.on_import_fibula)

        #Fibula_Layout.addRow(ImportFibula)
        fibula_groupbox_layout.addRow("Input fibula path  ", self.fibula_path)
        fibula_groupbox_layout.addRow(import_fibula_button)
        fibula_groupbox.setLayout(fibula_groupbox_layout)
        setup_tab_layout.addWidget(fibula_groupbox)

        self.fibula_path_node = ui.import_node("FibulaPath", "vtkMRMLTextNode")

        #CT SCAN GROUPBOX
        CT_groupbox = qt.QGroupBox("CT Scans")
        CT_layout = qt.QFormLayout()
        self.CT_path = ctk.ctkPathLineEdit()
        #self.CT_path.filters = ctk.ctkPathLineEdit.Dirs
        import_CT_button = ui.create_button("Import CT Scans")
        import_CT_button.connect('clicked(bool)', self.on_import_scans)

        CT_layout.addRow("Input CT Path ", self.CT_path)
        CT_layout.addRow(import_CT_button)
        CT_groupbox.setLayout(CT_layout)
        setup_tab_layout.addWidget(CT_groupbox)

        select_side_button_box = qt.QGroupBox("Fibula Side")
        select_side_layout = qt.QHBoxLayout(select_side_button_box)
        self.left_radiobutton = qt.QRadioButton("Left Fibula")
        select_side_layout.addWidget(self.left_radiobutton)
        self.right_radiobutton = qt.QRadioButton("Right Fibula")
        self.right_radiobutton.setChecked(True)
        select_side_layout.addWidget(self.right_radiobutton)
        setup_tab_layout.addWidget(select_side_button_box)

        import_models_button = ui.create_button("Import Device Models")
        import_models_button.connect('clicked(bool)', self.on_import_models)
        setup_tab_layout.addWidget(import_models_button)

        #CONTOUR_TAB
        contour_tab = qt.QWidget()
        contour_tab_layout = qt.QGridLayout(contour_tab)
        contour_tab_layout.setAlignment(qt.Qt.AlignTop)

        contour_title = qt.QLabel(f'Contour the Mandible')
        contour_title.setStyleSheet("font-weight:bold; padding-bottom: 8px; padding-top: 10px")
        contour_tab_layout.addWidget(contour_title, 0, 0, 1, 2)

        contour_instruction_label = \
            qt.QLabel("Starting on the anatomical right side of the mandible, "+
            "place a minimum of 15 fiducials (ideally 30) along the external face "+
            "of the mandible model. Follow the mandible curvature from the right side "+
            "of the patient’s mandible to the left, including each ramus. \n")
        contour_instruction_label.setWordWrap(True)
        contour_tab_layout.addWidget(contour_instruction_label, 1, 0, 1, 2)

        contour_button = ui.create_button("Contour Mandible")
        contour_button.connect('clicked(bool)', self.on_contour_mandible)
        contour_tab_layout.addWidget(contour_button, 2, 0, 1, 1)

        delete_contour_button = ui.create_button("Delete Contour")
        contour_tab_layout.addWidget(delete_contour_button, 2, 1, 1, 1)
        delete_contour_button.connect('clicked(bool)', self.on_delete_contour_button)

        self.launch = qt.QTabWidget()
        self.launch.addTab(setup_tab, "Import Models")
        self.launch.addTab(contour_tab, "Contour Mandible")
        self.layout.addWidget(self.launch)
        self.setup_tab_state = self.launch.currentIndex

        #Navigation Buttons
        navigation_button_box = qt.QGroupBox()
        navigation_button_layout = qt.QHBoxLayout(navigation_button_box)
        self.layout.addWidget(navigation_button_box)
        
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

        self.models_path = os.path.dirname(os.path.abspath(self.resourcePath("Models")))+"\\Models"
        #os.getcwd()+"\\Models"

        viewNodes = slicer.util.getNodesByClass("vtkMRMLAbstractViewNode")
        for viewNode in viewNodes:
            viewNode.SetOrientationMarkerType(slicer.vtkMRMLAbstractViewNode.OrientationMarkerTypeAxes)

    def cleanup(self):
        """
        Called when the application closes and the module widget is destroyed.
        """
        #slicer.qSlicerWidget.QScrollArea.QScrollBar.setMinimum()
        pass

    def enter(self):
        """
        Called each time the user opens this module.
        """
        # Make sure parameter node exists and observed
        pass

    def exit(self):
        """
        Called each time the user opens a different module.
        """
        # Do not react to parameter node changes (GUI wlil be updated when the user enters into the module)
        pass

    def onSceneStartClose(self, caller, event):
        """
        Called just before the scene is closed.
        """
        # Parameter node will be reset, do not use it anymore
        pass

    def onSceneEndClose(self, caller, event):
        """
        Called just after the scene is closed.
        """
        # If this module is shown while the scene is closed then recreate a new parameter node immediately
        pass

    #Control tab visibility and page state
    def change_setup_tab_visibility(self, state):
        self.launch.setCurrentIndex(state)
        if state == 0:
            self.on_setup_tab()
        elif state == 1:
            self.on_contour_tab()

    #SET TAB STATES
    def on_setup_tab(self):
        self.launch.setTabEnabled(0, True)
        self.launch.setTabEnabled(1, False)

    def on_contour_tab(self):
        slicer.modules.models.logic().SetAllModelsVisibility(0)
        self.Contour = ui.import_node('Contour', 'vtkMRMLMarkupsFiducialNode')
        self.Contour.SetDisplayVisibility(1)
        getNode('Mandible').SetDisplayVisibility(1)
        #self.Mandible = getNode('Mandible')
        #self.Fibula = getNode('Fibula')
        #self.Mandible.SetDisplayVisibility(1)
        #self.Fibula.SetDisplayVisibility(0)
        self.launch.setTabEnabled(0, False)
        self.launch.setTabEnabled(1, True)

    def on_next_module(self):
        
        if self.setup_tab_state < 1:
            self.setup_tab_state = self.setup_tab_state + 1
            self.change_setup_tab_visibility(self.setup_tab_state)
            print(self.setup_tab_state)
        else:
            slicer.util.selectModule('RegisterMandible')
            # dir = os.path.dirname(getNode('MandiblePath').GetText())+"\\SlicerFiles"
            # # ms.save_scene(dir, "0_Setup")

    def on_previous_module(self):
        if self.setup_tab_state > 0:
            self.setup_tab_state = self.setup_tab_state - 1
            self.change_setup_tab_visibility(self.setup_tab_state)
            print(self.setup_tab_state)

    def on_save(self):
        dir = os.path.dirname(getNode('MandiblePath').GetText())+"\\SlicerFiles"        
        ms.save_scene(dir, "0_ReconstructionWorkflow"+str(self.setup_tab_state))

    def on_import_mandible(self):
        mandible = slicer.modules.models.logic().AddModel(self.mandible_path.currentPath, slicer.vtkMRMLStorageNode.CoordinateSystemLPS)
        mandible.SetName("Mandible")
        transform_to_centre = vtk.vtkTransform()
        transform_to_centre.RotateX(180)
        transform_to_centre.RotateY(180)
        com_M = ms.get_centroid(mandible.GetPolyData())
        transform_to_centre.Translate(-com_M[0], -com_M[1], -com_M[2])
        mandible.ApplyTransform(transform_to_centre)
        print(transform_to_centre)
        mand_path = os.path.dirname(self.mandible_path.currentPath)+"\\CenteredMandible.stl"
        ms.export_mesh(mandible.GetPolyData(), mand_path)
        self.mandible_path_node.SetText(mand_path)
        self.mandible_to_centre = ui.create_linear_transform(transform_to_centre.GetMatrix(), "MandibleToCentre")
        #slicer.util.loadModel(self.Mandible_PathLineEdit.currentPath())
        #print(self.Mandible_PathLineEdit.currentPath)
        #print(modelNode )

    def on_import_fibula(self):
        #fibula = slicer.modules.models.logic().AddModel(self.FibulaPath.currentPath, slicer.vtkMRMLStorageNode.CoordinateSystemRAS)
        fibula = slicer.modules.models.logic().AddModel(self.fibula_path.currentPath, slicer.vtkMRMLStorageNode.CoordinateSystemLPS)
        fibula.SetName("Fibula")
        transform_F = vtk.vtkTransform()
        transform_F.RotateX(180)
        transform_F.RotateY(180)
        com_F = ms.get_centroid(fibula.GetPolyData())
        transform_F.Translate(-com_F[0], -com_F[1], -com_F[2])
        fibula.ApplyTransform(transform_F)
        input_path = os.path.dirname(self.fibula_path.currentPath)+"\\CenteredFibula.stl"
        ms.export_mesh(fibula.GetPolyData(), input_path)
        self.fibula_path_node.SetText(input_path)

    def on_import_scans(self):
        CT_scans = slicer.util.loadVolume(self.CT_path.currentPath, {"singleFile": False})
        to_centre = vtk.vtkTransform()
        mandible_to_centre_matrix = vtk.vtkMatrix4x4()
        try: 
            getNode('MandibleToCentre').GetMatrixTransformToParent(mandible_to_centre_matrix)
            to_centre.SetMatrix(mandible_to_centre_matrix)
            CT_scans.ApplyTransform(to_centre)
            print("Import complete")
        except slicer.util.MRMLNodeNotFoundException: 
            print("Import mandible model before CT scans.")

    def on_import_models(self):
        Pointer = self.import_models("Pointer", self.models_path+"\\Pointer.stl")
        Pointer.GetModelDisplayNode().SetColor([0.33, 1, 1])
        Pointer.SetDisplayVisibility(1)
        Guide = self.import_models("Guide", self.models_path+"\\Guide.stl")
        Guide.GetModelDisplayNode().SetColor([0.66, 0.66, 0.66])
        SawBlade = self.import_models("SawBlade", self.models_path+"\\SawBlade.stl")
        SawBlade.GetModelDisplayNode().SetColor([0.35, 0.42, 0.84])
        Hand1 = self.import_models("Hand1", self.models_path+"\\Hand1.stl")
        Hand1.GetModelDisplayNode().SetColor([1, 0, 0])
        Hand2 = self.import_models("Hand2", self.models_path+"\\Hand2.stl")
        Hand2.GetModelDisplayNode().SetColor([1, 0.5, 0])
        Hand3 = self.import_models("Hand3", self.models_path+"\\Hand3.stl")
        Hand3.GetModelDisplayNode().SetColor([1, 1, 0])
        
        CutPlane1 = self.import_plane("CutPlane1", self.models_path+"\\CutPlane1.mrk.json")
        CutPlane2 = self.import_plane("CutPlane2", self.models_path+"\\CutPlane2.mrk.json")

        GuideToCut = self.import_transforms("GuideToCut", self.models_path+"\\GuideToCut.h5")
        GuideToGuideRef = self.import_transforms("GuideToGuideRef", self.models_path+"\\GuideToGuideRef.h5")
        Hand1RefToHand1 = self.import_transforms("Hand1RefToHand1", self.models_path+"\\Hand1RefToHand1.h5")
        Hand2RefToHand2 = self.import_transforms("Hand2RefToHand2", self.models_path+"\\Hand2RefToHand2.h5")
        Hand3RefToHand3 = self.import_transforms("Hand3RefToHand3", self.models_path+"\\Hand3RefToHand3.h5")
        StylusRefToTracker = self.import_transforms("StylusRefToTracker", self.models_path+"\\StylusRefToTracker.h5")
        StylusTipToStylusRef = self.import_transforms("StylusTipToStylusRef", self.models_path+"\\StylusTipToStylusRef.h5")
        Hand1Coords = self.import_transforms("Hand1Coords", self.models_path+"\\Hand1Coords.h5")
        Hand1Coords.SetAndObserveTransformNodeID(Hand1RefToHand1.GetID())
        Hand3Coords = self.import_transforms("Hand3Coords", self.models_path+"\\Hand3Coords.h5")
        Hand3Coords.SetAndObserveTransformNodeID(Hand3RefToHand3.GetID())

        StylusRefToMandRef = ui.import_node('StylusRefToMandRef', 'vtkMRMLLinearTransformNode')
        StylusRefToFibRef = ui.import_node('StylusRefToFibRef', 'vtkMRMLLinearTransformNode')
        StylusRefToGuideRef = ui.import_node('StylusRefToGuideRef', 'vtkMRMLLinearTransformNode')
        StylusRefToHand1Ref = ui.import_node('StylusRefToHand1Ref', 'vtkMRMLLinearTransformNode')
        StylusRefToHand2Ref = ui.import_node('StylusRefToHand2Ref', 'vtkMRMLLinearTransformNode')
        StylusRefToHand3Ref = ui.import_node('StylusRefToHand3Ref', 'vtkMRMLLinearTransformNode')
        Hand1RefToFibRef = ui.import_node('Hand1RefToFibRef', 'vtkMRMLLinearTransformNode')
        Hand1RefToHand2Ref = ui.import_node('Hand1RefToHand2Ref', 'vtkMRMLLinearTransformNode')
        Hand1RefToMandRef = ui.import_node('Hand1RefToMandRef', 'vtkMRMLLinearTransformNode')
        Hand2RefToFibRef = ui.import_node('Hand2RefToFibRef', 'vtkMRMLLinearTransformNode')
        Hand2RefToMandRef = ui.import_node('Hand2RefToMandRef', 'vtkMRMLLinearTransformNode')
        Hand3RefToFibRef = ui.import_node('Hand3RefToFibRef', 'vtkMRMLLinearTransformNode')
        Hand3RefToHand2Ref = ui.import_node('Hand3RefToHand2Ref', 'vtkMRMLLinearTransformNode')
        Hand3RefToMandRef = ui.import_node('Hand3RefToMandRef', 'vtkMRMLLinearTransformNode')
        GuideRefToHand1Ref = ui.import_node('GuideRefToHand1Ref', 'vtkMRMLLinearTransformNode')
        GuideRefToHand2Ref = ui.import_node('GuideRefToHand2Ref', 'vtkMRMLLinearTransformNode')
        GuideRefToHand3Ref = ui.import_node('GuideRefToHand3Ref', 'vtkMRMLLinearTransformNode')

        FibRefToFib = ui.import_node('FibRefToFib', 'vtkMRMLLinearTransformNode')
        MandRefToMand = ui.import_node('MandRefToMand', 'vtkMRMLLinearTransformNode')

        GuideRefToFibRef = ui.import_node('GuideRefToFibRef', 'vtkMRMLLinearTransformNode')

        Pointer.SetAndObserveTransformNodeID(StylusTipToStylusRef.GetID())
        SawBlade.SetAndObserveTransformNodeID(GuideToCut.GetID())
        Hand1.SetAndObserveTransformNodeID(Hand1RefToHand1.GetID())
        Hand2.SetAndObserveTransformNodeID(Hand2RefToHand2.GetID())
        # Hand2Fids.SetAndObserveTransformNodeID(Hand2RefToHand2.GetID())
        Hand3.SetAndObserveTransformNodeID(Hand3RefToHand3.GetID())

        StylusMandible = ui.create_watchdog_node("Watchdog_StylusToMandible", StylusRefToMandRef, "Stylus or Mandible is not visible")  #For registration
        StylusMandible.SetDisplayVisibility(0)
        StylusFibula = ui.create_watchdog_node("Watchdog_StylusToFibula", StylusRefToFibRef, "Stylus or Fibula is not visible") #For registration
        StylusFibula.SetDisplayVisibility(0)
        Hand1Fibula = ui.create_watchdog_node("Watchdog_Hand1ToFibula", Hand1RefToFibRef, "Hand 1 or Fibula is not visible")    #For placing hands along fib length
        Hand1Fibula.SetDisplayVisibility(0)
        Hand2Fibula = ui.create_watchdog_node("Watchdog_Hand2ToFibula", Hand2RefToFibRef, "Hand 2 or Fibula is not visible")
        Hand2Fibula.SetDisplayVisibility(0)
        Hand3Fibula = ui.create_watchdog_node("Watchdog_Hand3ToFibula", Hand3RefToFibRef, "Hand3 or Fibula is not visible")
        Hand3Fibula.SetDisplayVisibility(0)
        GuideFibula = ui.create_watchdog_node("Watchdog_GuideFibula", GuideRefToFibRef, "Guide or Fibula is not visible")             #For placing guide to cut
        GuideFibula.SetDisplayVisibility(0)
        GuideHand1 = ui.create_watchdog_node("Watchdog_GuideHand1", GuideRefToHand1Ref, "Guide or Hand 1 is not visible")
        GuideHand1.SetDisplayVisibility(0)
        GuideHand2 = ui.create_watchdog_node("Watchdog_GuideHand2", GuideRefToHand2Ref, "Guide or Hand 2 is not visible")
        GuideHand2.SetDisplayVisibility(0)
        GuideHand3 = ui.create_watchdog_node("Watchdog_GuideHand3", GuideRefToHand3Ref, "Guide or Hand 3 is not visible")
        GuideHand3.SetDisplayVisibility(0)
        Hand2Mandible = ui.create_watchdog_node("Watchdog_Hand2Mandible", Hand2RefToMandRef, "Hand 2 or Mandible is not visible")   #For positioning in mandible
        Hand2Mandible.SetDisplayVisibility(0)

        print(f'Left: {self.left_radiobutton.isChecked()}')
        if (self.left_radiobutton.isChecked()):
            Hand1 = getNode('Hand1').SetName("tmp")
            Hand3 = getNode('Hand3').SetName('Hand1')
            tmp = getNode('tmp').SetName('Hand3')
            getNode('Hand1').GetModelDisplayNode().SetColor([1, 0, 0])
            getNode('Hand3').GetModelDisplayNode().SetColor([1, 1, 0])
        print("Updated hierarchy")

    
    def import_models(self, node_name, node_path):
        try:
            node = getNode(node_name)
            print(f'Retrieved {node_name}')
        except slicer.util.MRMLNodeNotFoundException:
            node = slicer.modules.models.logic().AddModel(node_path, slicer.vtkMRMLStorageNode.CoordinateSystemRAS)
            node.SetName(node_name)
            node.SetDisplayVisibility(0)
            print(f'Imported {node_name} model')
        return node

    def import_transforms(self, node_name, node_path):
        try:
            node = getNode(node_name)
            print(f'Retrieved {node_name}')
        except slicer.util.MRMLNodeNotFoundException:
            node = slicer.util.loadNodeFromFile(node_path, filetype="TransformFile") 
            #https://slicer.readthedocs.io/en/latest/developer_guide/slicer.html#module-slicer.util
            node.SetName(node_name)
            print(f'Imported {node_name} transform')
        return node

    def import_plane(self, node_name, node_path):
        try:
            node = getNode(node_name)
            print(f'Retrieved {node_name}')
        except slicer.util.MRMLNodeNotFoundException:
            node = slicer.util.loadNodeFromFile(node_path, filetype="MarkupsFile") 
            #https://slicer.readthedocs.io/en/latest/developer_guide/slicer.html#module-slicer.util
            node.SetName(node_name)
            node.SetDisplayVisibility(0)
            print(f'Imported {node_name} plane')
        return node

    def on_contour_mandible(self):
        register.place_CT_fiducial(self.Contour, 1)

    def on_delete_contour_button(self):
        register.remove_CT_fiducials(getNode('Contour'))

# ReconstructionWorkflowLogic
#

class ReconstructionWorkflowLogic(ScriptedLoadableModuleLogic):
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

#
# ReconstructionWorkflowTest
#

class ReconstructionWorkflowTest(ScriptedLoadableModuleTest):
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
    self.test_ReconstructionWorkflow1()

  def test_ReconstructionWorkflow1(self):
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


    # Test the module logic

    logic = ReconstructionWorkflowLogic()

    self.delayDisplay('Test passed')
