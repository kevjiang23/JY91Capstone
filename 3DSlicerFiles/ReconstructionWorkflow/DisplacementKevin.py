import os
import unittest
import logging
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin, getNode
import _HelperFile as hf
import numpy as np
import math
import time
from vtk import vtkIterativeClosestPointTransform

import ManageSlicer as ms
import ManageUI as ui


class NavigationTestingKevin(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Live Track Displacement Kevin"
        self.parent.categories = ["Feature Testing"]
        self.parent.dependencies = []
        self.parent.contributors = ["Kevin Gilmore & Melissa Yu (UBC)"]
        self.parent.helpText = ""
        self.parent.acknowledgementText = ""

     #####################

    ##########


class NavigationTestingKevinWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)

        self.transform_node = None
        self.transTransform = None
        self.output_filename_matrix = 'output_data_matrix.csv'
        self.output_filename_decomposed = 'output_data_decomposed.csv'
        self.capture_duration = 80
        self.count = 0
        self.is_streaming = False

        self.hand1 = getNode('Hand1')
      
        

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.logic = NavigationTestingKevinLogic()
        self.layout.setAlignment(qt.Qt.AlignTop)
        self.modelLogic = slicer.vtkSlicerModelsLogic()

        #################################################3
        #New




        self.transform_selector_label = qt.QLabel("Event Transform (Hand2ReftoHand1Ref):")
        self.transform_selector = slicer.qMRMLNodeComboBox()
        self.transform_selector.nodeTypes = ['vtkMRMLLinearTransformNode']
        self.transform_selector.selectNodeUponCreation = True
        self.transform_selector.addEnabled = False
        self.transform_selector.removeEnabled = False
        self.transform_selector.noneEnabled = True
        self.transform_selector.showHidden = False
        self.transform_selector.showChildNodeTypes = False
        self.transform_selector.setMRMLScene(slicer.mrmlScene)

        self.objtransform_selector_label = qt.QLabel("Object Transform (Hand1ReftoHand1):")
        self.objtransform_selector = slicer.qMRMLNodeComboBox()
        self.objtransform_selector.nodeTypes = ['vtkMRMLLinearTransformNode']
        self.objtransform_selector.selectNodeUponCreation = True
        self.objtransform_selector.addEnabled = False
        self.objtransform_selector.removeEnabled = False
        self.objtransform_selector.noneEnabled = True
        self.objtransform_selector.showHidden = False
        self.objtransform_selector.showChildNodeTypes = False
        self.objtransform_selector.setMRMLScene(slicer.mrmlScene)

        self.start_button = ui.create_button("Start Streaming")
        self.stop_button = ui.create_button("Stop Streaming")

        self.timer_label = qt.QLabel("Elapsed Time: 0 sec")
        #font = self.timer_label.font()
        #font.setPointSize(12)
        #self.timer_label.setFont(font)

        self.filename_matrix_label = qt.QLabel("Matrix Output Filename:")
        self.filename_matrix_input = qt.QLineEdit()
        self.filename_matrix_input.setText(self.output_filename_matrix)

        self.filename_decomposed_label = qt.QLabel("Decomposed Output Filename:")
        self.filename_decomposed_input = qt.QLineEdit()
        self.filename_decomposed_input.setText(self.output_filename_decomposed)

        self.start_button.connect('clicked()', self.start_streaming)
        self.stop_button.connect('clicked()', self.stop_streaming)

        self.layout.addWidget(self.transform_selector_label)
        self.layout.addWidget(self.transform_selector)
        self.layout.addWidget(self.objtransform_selector_label)
        self.layout.addWidget(self.objtransform_selector)
        self.layout.addWidget(self.start_button)
        self.layout.addWidget(self.stop_button)
        self.layout.addWidget(self.timer_label)
        self.layout.addWidget(self.filename_matrix_label)
        self.layout.addWidget(self.filename_matrix_input)
        self.layout.addWidget(self.filename_decomposed_label)
        self.layout.addWidget(self.filename_decomposed_input)



        # Create a QTimer for updating the timer label
        self.timer = qt.QTimer(self.parent)
        self.timer.timeout.connect(self.update_timer_label)

    def start_streaming(self):
        if not self.is_streaming:
            self.is_streaming = True
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.start_time = time.time()
            self.prevtime = time.time() - self.start_time
            self.timer.start(1000)  # Update every 1000 milliseconds (1 second)

            # Get the selected transform node from the combo box
            transform_node = self.transform_selector.currentNode()
            self.transTransform = self.objtransform_selector.currentNode()

            # Get the output file names from the line edits
            self.output_filename_matrix = self.filename_matrix_input.text
            self.output_filename_decomposed = self.filename_decomposed_input.text

            # Start capturing and storing both types of transforms
            transform_node.AddObserver(slicer.vtkMRMLTransformNode.TransformModifiedEvent, self.onTransformNodeModified)


    def stop_streaming(self):
        if self.is_streaming:
            self.is_streaming = False
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.timer.stop()



    def onTransformNodeModified(self, transformNode, unusedArg2=None, unusedArg3=None):

        with open(self.output_filename_matrix, 'a') as file_matrix, open(self.output_filename_decomposed, 'a') as file_decomposed:

            if self.count == 0:
                file_matrix.write("Timestamp,MatrixTransform\n")
                file_decomposed.write("Timestamp,TranslationX,TranslationY,TranslationZ,RotationX,RotationY,RotationZ\n")
                self.modTrans = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLinearTransformNode', 'ModelToModel_Transform')
                self.count = self.count + 1

                cloned_hand = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
                original_poly_data = self.hand1.GetPolyData()
                cloned_poly_data = vtk.vtkPolyData()
                cloned_poly_data.DeepCopy(original_poly_data)
                cloned_hand.SetAndObservePolyData(cloned_poly_data)
                
                transMatrix = vtk.vtkMatrix4x4()
                self.transTransform.GetMatrixTransformToWorld(transMatrix)
                cloned_hand.SetAndObserveTransformNodeID(None)  
                cloned_hand.SetAndObserveTransformNodeID(self.transTransform.GetID())
                cloned_hand.HardenTransform()

            if time.time() - self.start_time < self.capture_duration and (time.time() - self.start_time) - self.prevtime > 1:
                if transformNode:

                    self.runGetTrans(self.hand1, cloned_hand, self.modTrans)
                    transform_node = self.modTrans
                    matrix = vtk.vtkMatrix4x4()
                    transform_node.GetMatrixTransformToWorld(matrix)
                    transform_node = matrix

                    timestamp = time.time() - self.start_time

                    # Capture matrix transform
                    matrix_transform_str = str(transform_node.GetElement(0,0)) \
                    + ", " + str(transform_node.GetElement(0,1)) \
                    + ", " + str(transform_node.GetElement(0,2)) \
                    + ", " + str(transform_node.GetElement(0,3)) \
                    + ", " + str(transform_node.GetElement(1,0)) \
                    + ", " + str(transform_node.GetElement(1,1)) \
                    + ", " + str(transform_node.GetElement(1,2)) \
                    + ", " + str(transform_node.GetElement(1,3)) \
                    + ", " + str(transform_node.GetElement(2,0)) \
                    + ", " + str(transform_node.GetElement(2,1)) \
                    + ", " + str(transform_node.GetElement(2,2)) \
                    + ", " + str(transform_node.GetElement(2,3)) \
                    + ", " + str(transform_node.GetElement(3,0)) \
                    + ", " + str(transform_node.GetElement(3,1)) \
                    + ", " + str(transform_node.GetElement(3,2)) \
                    + ", " + str(transform_node.GetElement(3,3)) +"\n"

                    file_matrix.write(str(timestamp))
                    file_matrix.write(matrix_transform_str)

                    # Capture decomposed transform
                    #translation = transform_matrix.GetTranslation()
                    #rotation = transform_matrix.GetOrientation()

                    translation = [transform_node.GetElement(0, 3), transform_node.GetElement(1, 3), transform_node.GetElement(2, 3)]
                    theta_x, theta_y, theta_z = ms.get_rotation_euler(transform_node)

                    file_decomposed.write(f"{timestamp},{translation[0]},{translation[1]},{translation[2]},"f"{theta_x},{theta_y},{theta_z}\n")

                    print(timestamp)
                    print(type(timestamp))
                    self.prevtime = time.time() - self.start_time

    def runGetTrans(self, inputSourceModel, inputTargetModel, outputSourceToTargetTransform, transformType=0, numIterations=100 ):
      
      cloned_source = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLModelNode')
      original_poly_data = inputSourceModel.GetPolyData()
      cloned_poly_data = vtk.vtkPolyData()
      cloned_poly_data.DeepCopy(original_poly_data)
      cloned_source.SetAndObservePolyData(cloned_poly_data)

      transMatrix = vtk.vtkMatrix4x4()
      self.transTransform.GetMatrixTransformToWorld(transMatrix)
      cloned_source.SetAndObserveTransformNodeID(None)  
      cloned_source.SetAndObserveTransformNodeID(self.transTransform.GetID())
      cloned_source.HardenTransform()

        
      icpTransform = vtk.vtkIterativeClosestPointTransform()
      icpTransform.SetSource( cloned_source.GetPolyData() )
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
    #def capture_and_store_transforms(self):
    #    print("entered")
    #    with open(self.output_filename_matrix, 'a') as file_matrix, open(self.output_filename_decomposed, 'a') as file_decomposed:
    #        file_matrix.write("Timestamp,MatrixTransform\n")
    #        file_decomposed.write("Timestamp,TranslationX,TranslationY,TranslationZ,RotationX,RotationY,RotationZ\n")

    #        if time.time() - self.start_time < self.capture_duration:
    #            if self.transform_node:
    #                transform_matrix = self.transform_node.GetMatrixTransformToParent()
    #                timestamp = time.time() - self.start_time
    #                print(timestamp)
    #                print(type(timestamp))
    #                # Capture matrix transform
    #                matrix_transform_str = str(transform_matrix.GetElement(0,0)) \
    #                + ", " + str(transform_matrix.GetElement(0,1)) \
    #                + ", " + str(transform_matrix.GetElement(0,2)) \
    #                + ", " + str(transform_matrix.GetElement(0,3)) \
    #                + ", " + str(transform_matrix.GetElement(1,0)) \
    #                + ", " + str(transform_matrix.GetElement(1,1)) \
    #                + ", " + str(transform_matrix.GetElement(1,2)) \
    #                + ", " + str(transform_matrix.GetElement(1,3)) \
    #                + ", " + str(transform_matrix.GetElement(2,0)) \
    #                + ", " + str(transform_matrix.GetElement(2,1)) \
    #                + ", " + str(transform_matrix.GetElement(2,2)) \
    #                + ", " + str(transform_matrix.GetElement(2,3)) \
    #                + ", " + str(transform_matrix.GetElement(3,0)) \
    #                + ", " + str(transform_matrix.GetElement(3,1)) \
    #                + ", " + str(transform_matrix.GetElement(3,2)) \
    #                + ", " + str(transform_matrix.GetElement(3,3)) +"\n"

    #                file_matrix.write(str(timestamp))
    #                file_matrix.write(matrix_transform_str)

    #                # Capture decomposed transform
    #                #translation = transform_matrix.GetTranslation()
    #                #rotation = transform_matrix.GetOrientation()

    #                translation = [transform_matrix.GetElement(0, 3), transform_matrix.GetElement(1, 3), transform_matrix.GetElement(2, 3)]
    #                theta_x, theta_y, theta_z = ms.get_rotation_euler(transform_matrix)

    #                file_decomposed.write(f"{timestamp},{translation[0]},{translation[1]},{translation[2]},"f"{theta_x},{theta_y},{theta_z}\n")



    def update_timer_label(self):
        elapsed_time = time.time() - self.start_time
        self.timer_label.setText(f"Elapsed Time: {int(elapsed_time)} sec")


# Main entry point
if __name__ == "__main__":
    streaming_app = TransformDataStreaming()
    slicer.app.exec_()


        ##################################################









        # self.plane_collection = vtk.vtkPlaneCollection()

    #    track_object = ctk.ctkCollapsibleButton()
    #    track_object.text = "Track Object"
    #    track_object_layout = qt.QFormLayout(track_object)
    #    self.layout.addWidget(track_object)

    #    transform_to_track = qt.QLabel("Transform to track")
    #    self.select_transform_to_track = slicer.qMRMLNodeComboBox()
    #    self.select_transform_to_track.nodeTypes = ["vtkMRMLTransformNode"]
    #    self.select_transform_to_track.noneEnabled = True
    #    self.select_transform_to_track.setMRMLScene(slicer.mrmlScene)
    #    track_object_layout.addRow(transform_to_track, self.select_transform_to_track)

    #    start = ui.create_button("Start Tracking")
    #    start.connect('clicked(bool)', self.on_start)
    #    track_object_layout.addWidget(start)

    #    #stop = ui.create_button("Stop Tracking")
    #    #start.connect('clicked(bool)', self.on_stop)
    #    #track_object_layout.addWidget(stop)

    #def on_start(self):
    #    tracked_trans = self.select_transform_to_track.currentNode()
    #    print(tracked_trans.Elements())

    #    transformNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLTransformNode")
    #    transformNode.AddObserver(slicer.vtkMRMLTransformNode.TransformModifiedEvent, onTransformNodeModified)

    #def onTransformNodeModified(transformNode, unusedArg2=None, unusedArg3=None):
    #    transformMatrix = vtk.vtkMatrix4x4()
    #    transformNode.GetMatrixTransformToWorld(transformMatrix)
    #    print("Position: [{0}, {1}, {2}]".format(transformMatrix.GetElement(0,3), transformMatrix.GetElement(1,3), transformMatrix.GetElement(2,3)))


    ##def on_stop(self):
    ##   model = self.select_transform_to_track.currentNode()



class NavigationTestingKevinLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)

class NavigationTestingKevinTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.test_NavigationTesting()

    def test_NavigationTestingKevin(self):
        self.delayDisplay("Start test")
        logic = NavigationTestingLogic()
        self.delayDisplay("Test Passed")


#def capture_and_store_transforms(transform_node, output_filename_decomposed, output_filename_matrix, start_time, duration):
#        print("entered")
#        with open(output_filename_matrix, 'a') as file_matrix, open(output_filename_decomposed, 'a') as file_decomposed:
#            file_matrix.write("Timestamp,MatrixTransform\n")
#            file_decomposed.write("Timestamp,TranslationX,TranslationY,TranslationZ,RotationX,RotationY,RotationZ\n")

#            if time.time() - start_time < duration:
#                if transform_node:
#                    transform_matrix = transform_node.GetMatrixTransformToParent()
#                    timestamp = time.time() - start_time
#                    print(timestamp)
#                    print(type(timestamp))
#                    # Capture matrix transform
#                    matrix_transform_str = str(transform_matrix.GetElement(0,0)) \
#                    + ", " + str(transform_matrix.GetElement(0,1)) \
#                    + ", " + str(transform_matrix.GetElement(0,2)) \
#                    + ", " + str(transform_matrix.GetElement(0,3)) \
#                    + ", " + str(transform_matrix.GetElement(1,0)) \
#                    + ", " + str(transform_matrix.GetElement(1,1)) \
#                    + ", " + str(transform_matrix.GetElement(1,2)) \
#                    + ", " + str(transform_matrix.GetElement(1,3)) \
#                    + ", " + str(transform_matrix.GetElement(2,0)) \
#                    + ", " + str(transform_matrix.GetElement(2,1)) \
#                    + ", " + str(transform_matrix.GetElement(2,2)) \
#                    + ", " + str(transform_matrix.GetElement(2,3)) \
#                    + ", " + str(transform_matrix.GetElement(3,0)) \
#                    + ", " + str(transform_matrix.GetElement(3,1)) \
#                    + ", " + str(transform_matrix.GetElement(3,2)) \
#                    + ", " + str(transform_matrix.GetElement(3,3)) +"\n"

#                    file_matrix.write(str(timestamp))
#                    file_matrix.write(matrix_transform_str)

#                    # Capture decomposed transform
#                    #translation = transform_matrix.GetTranslation()
#                    #rotation = transform_matrix.GetOrientation()

#                    translation = [transform_matrix.GetElement(0, 3), transform_matrix.GetElement(1, 3), transform_matrix.GetElement(2, 3)]
#                    theta_x, theta_y, theta_z = ms.get_rotation_euler(transform_matrix)

#                    file_decomposed.write(f"{timestamp},{translation[0]},{translation[1]},{translation[2]},"f"{theta_x},{theta_y},{theta_z}\n")
