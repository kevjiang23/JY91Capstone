import os
import unittest
import logging
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
from slicer.util import VTKObservationMixin, getNode
import _HelperFile as hf
import numpy as np 
import math

class CutPlaneTesting(ScriptedLoadableModule):
    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Cut Plane Testing"
        self.parent.categories = ["Feature Testing"]
        self.parent.dependencies = []
        self.parent.contributors = ["Melissa Yu (UBC)"]
        self.parent.helpText = ""
        self.parent.acknowledgementText = ""

class CutPlaneTestingWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    def __init__(self, parent=None):
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        self.logic = CutPlaneTestingLogic()
        self.clipNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLClipModelsNode')
        self.modelLogic = slicer.vtkSlicerModelsLogic()
        self.plane_collection = vtk.vtkPlaneCollection()

        self.layoutManager = slicer.app.layoutManager()
        self.mandLayout = ("<layout type=\"horizontal\" split=\"true\" >"
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
        self.mandLayoutId=705
        self.layoutManager.layoutLogic().GetLayoutNode().AddLayoutDescription(self.mandLayoutId, self.mandLayout)
        self.layoutManager.setLayout(self.mandLayoutId)
        slicer.app.layoutManager().setLayout(4)
        
        #Will use FIBULA tracker
        RegisterSection = ctk.ctkCollapsibleButton()
        RegisterSection.text = "Register Model"
        RegisterLayout = qt.QFormLayout(RegisterSection)
        self.layout.addWidget(RegisterSection)

        #CreateNodes = self.createButton("Create Nodes")
        #RegisterLayout.addRow(CreateNodes)
        #CreateNodes.connect('clicked(bool)', self.onCreateNodes)

        RegisterTitlePP = qt.QLabel("Register Model: Paired Point")
        RegisterTitlePP.setStyleSheet('font-size:10pt; font-weight: bold')
        #RegisterTitle.setAlignment(qt.Qt.AlignCenter)
        RegisterTitlePP.setAlignment(qt.Qt.AlignTop)
        RegisterLayout.addRow(RegisterTitlePP)

        PlaceVirtualFiducial = self.createButton("Place Virtual Fiducial")
        RegisterLayout.addWidget(PlaceVirtualFiducial)
        #PlaceVirtualFiducial.setStyleSheet('font-size:10pt')
        PlaceVirtualFiducial.connect('clicked(bool)', self.onPlaceVirtualFiducial)

        PlacePhysicalFiducial = self.createButton("Place Physical Fiducial")
        RegisterLayout.addWidget(PlacePhysicalFiducial)
        #PlacePhysicalFiducial.setStyleSheet('font-size: 10pt')
        PlacePhysicalFiducial.connect('clicked(bool)', self.onPlacePhysicalFiducial)

        RegisterPairedPoint = self.createButton("Complete Paired Point Registration")
        RegisterLayout.addWidget(RegisterPairedPoint)
        #RegisterPairedPoint.setStyleSheet('font-size: 10pt')
        RegisterPairedPoint.connect('clicked(bool)', self.onRegisterPairedPoint)

        self.PPErrorLabel = qt.QLabel(f'Paired point RMS error: ')
        RegisterLayout.addRow(self.PPErrorLabel)

        RegisterTitleSurface = qt.QLabel("\nRegister Model: Surface")
        RegisterTitleSurface.setStyleSheet('font-size:10pt; font-weight: bold')
        RegisterLayout.addRow(RegisterTitleSurface)

        PlaceSurfaceFiducials = self.createButton("Collect Surface Fiducials")
        RegisterLayout.addWidget(PlaceSurfaceFiducials)
        #PlacePhysicalFiducial.setStyleSheet('font-size: 10pt')
        PlaceSurfaceFiducials.connect('clicked(bool)', self.onCollectSurfaceFiducials)

        StopSurfaceFiducials = self.createButton("Stop Collecting Surface Fiducials")
        RegisterLayout.addWidget(StopSurfaceFiducials)
        #PlacePhysicalFiducial.setStyleSheet('font-size: 10pt')
        StopSurfaceFiducials.connect('clicked(bool)', self.onStopCollectingSurfaceFiducials)

        self.SurfaceFiducialsLabel = qt.QLabel("Surface fiducials placed: 0")
        RegisterLayout.addRow(self.SurfaceFiducialsLabel)

        RegisterSurface = self.createButton('Complete Surface Registration')
        RegisterLayout.addWidget(RegisterSurface)
        RegisterSurface.connect('clicked(bool)', self.onRegisterSurface)

        self.SurfaceErrorLabel = qt.QLabel(f'Surface RMS error: ')
        RegisterLayout.addRow(self.SurfaceErrorLabel)

        ##CUT PLANE SECTION
        CutPlaneSection = ctk.ctkCollapsibleButton()
        CutPlaneSection.text = "Cut Planes"
        CutPlaneLayout = qt.QFormLayout(CutPlaneSection)
        self.layout.addWidget(CutPlaneSection)

        CutPlaneTitle = qt.QLabel("Cut Planes")
        CutPlaneTitle.setStyleSheet('font-size:10pt; font-weight: bold')
        CutPlaneTitle.setAlignment(qt.Qt.AlignTop)
        CutPlaneLayout.addRow(CutPlaneTitle)

        #PlacePlanePoint = self.createButton("Place Plane Fiducial")
        #CutPlaneLayout.addWidget(PlacePlanePoint)
        #PlacePlanePoint.connect('clicked(bool)', self.onPlacePlanePoint)

        UpdateSlicePlane = self.createButton("Register Slice Plane")
        CutPlaneLayout.addWidget(UpdateSlicePlane)
        UpdateSlicePlane.connect('clicked(bool)', self.onUpdateSlicePlane)

        FlipNormal = self.createButton("Flip Normal")
        CutPlaneLayout.addWidget(FlipNormal)
        FlipNormal.connect('clicked(bool)', self.onFlipNormal)

        #ClipPlane = self.createButton("Clip")
        #CutPlaneLayout.addWidget(ClipPlane)
        #ClipPlane.connect('clicked(bool)', self.onClipPlane)

        GenerateModels = self.createButton("Generate Clipped Models")
        CutPlaneLayout.addWidget(GenerateModels)
        GenerateModels.connect('clicked(bool)', self.onGenerateModels)

        DeleteSlicePlane = self.createButton("Delete Slice Plane")
        CutPlaneLayout.addWidget(DeleteSlicePlane)
        DeleteSlicePlane.connect('clicked(bool)', self.onDeleteSlicePlane)

        ExportModels = self.createButton("Export Models")
        CutPlaneLayout.addWidget(ExportModels)
        ExportModels.connect('clicked(bool)', self.onExportModels)

        self.getNodes()
        self.StylusTipToStylusRef.SetAndObserveTransformNodeID(self.StylusRefToBlockRef.GetID())
        self.Pointer.SetAndObserveTransformNodeID(self.StylusTipToStylusRef.GetID())

        self.volumeResliceLogic = slicer.modules.volumereslicedriver.logic()
        #self.connectPlaneToProbe(self.StylusTipToStylusRef, self.Red)
        #self.Green.Normal.SetDisplayVisibility(1)

    #def onCreateNodes(self):
    #    #Virtual fiducials 
    #    self.VirtualFiducials = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'VirtualFiducials')
    #    self.VirtualFiducials.SetDisplayVisibility(1)
    #    #Physical fiducials
    #    self.PhysicalFiducials = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'PhysicalFiducials')
    #    self.PhysicalFiducials.SetDisplayVisibility(1)
    #    #Paired point registration
    #    self.PairedPointRegistration = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLFiducialRegistrationWizardNode',
    #                                                                 'PairedPointRegistration')
    #    #Surface fiducials
    #    self.SurfaceFiducials = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'SurfaceFiducials')
    #    #Surface registration
    #    self.SurfaceRegistration = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLFiducialRegistrationWizardNode', 
    #                                                             'SurfaceRegistration')
    #    #Plane fiducials
    #    self.PlaneFiducials = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'PlaneFiducials')
    #    print("Nodes created")

    def getNodes(self):
        self.StylusTipToStylusRef = getNode('StylusTipToStylusRef')
        #self.StylusRefToBlockRef = getNode('StylusRefToBlockRef')
        #self.BlockRefToBlock = getNode('BlockRefToBlock')
        self.Block = getNode('Block')
        self.BlockDisp = self.Block.GetModelDisplayNode()
        self.BlockDisp.SetClipping(1)
        self.Pointer = getNode('Pointer')
        self.CutPlane = getNode('CutPlane')
        self.Green = getNode('vtkMRMLSliceNodeGreen')
        self.Yellow = getNode('vtkMRMLSliceNodeYellow')
        self.Red = getNode('vtkMRMLSliceNodeRed')
        #self.GreenDisp = self.Green.GetSliceDisplayNode()
        greenDisplay = slicer.app.layoutManager().sliceWidget("Green").mrmlSliceNode()

        self.VirtualFiducials = self.checkNode('VirtualFiducials', 'vtkMRMLMarkupsFiducialNode')
        self.PhysicalFiducials = self.checkNode('PhysicalFiducials', 'vtkMRMLMarkupsFiducialNode')
        self.PairedPointRegistration = self.checkNode('PairedPointRegistration', 'vtkMRMLFiducialRegistrationWizardNode')
        self.SurfaceFiducials = self.checkNode('SurfaceFiducials', 'vtkMRMLMarkupsFiducialNode')
        self.SurfaceRegistration = self.checkNode('SurfaceRegistration', 'vtkMRMLLinearTransformNode')
        self.PlaneFiducials = self.checkNode('PlaneFiducials', 'vtkMRMLMarkupsFiducialNode')
        self.StylusRefToBlockRef = self.checkNode('StylusRefToBlockRef', 'vtkMRMLLinearTransformNode')
        self.BlockRefToBlock = self.checkNode('BlockRefToBlock', 'vtkMRMLLinearTransformNode')
        #if getNode('PlaneFiducials') is None: 
        #    self.PlaneFiducials = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'PlaneFiducials')
        #    print('successful1')
        #else: 
        #    self.PlaneFiducials = getNode('PlaneFiducials')
        #    print('successful2')

    def checkNode(self, node_name, node_type='vtkMRMLMarkupsFiducialNode'):
        try: 
            node = getNode(node_name)
            print(f'Retrieved {node_name}')
        except slicer.util.MRMLNodeNotFoundException:
            node = slicer.mrmlScene.AddNewNodeByClass(node_type, node_name)
            print(f'Created {node_name}')
        return node
        #if getNode(node_name) is None: 
        #    node = slicer.mrmlScene.AddNewNodeByClass(node_type, node_name)
        #    print(f'Created {node_name}')
        #else:
        #    node = getNode(node_name)
        #    print(f'Retrived {noode_name}')
        #return node_name


    def onPlaceVirtualFiducial(self):
        slicer.modules.markups.logic().SetActiveListID(self.VirtualFiducials)
        placeModePersistence = 0
        slicer.modules.markups.logic().StartPlaceMode(placeModePersistence)
        self.VirtualFiducials.SetNthControlPointLocked(self.VirtualFiducials.GetNumberOfFiducials()-1, 1)

    def onPlacePhysicalFiducial(self):
        slicer.modules.markups.logic().SetActiveListID(self.PhysicalFiducials)
        fiducial_matrix = vtk.vtkMatrix4x4()
        self.StylusTipToStylusRef.GetMatrixTransformToWorld(fiducial_matrix)
        slicer.modules.markups.logic().AddFiducial(fiducial_matrix.GetElement(0, 3),
                                                   fiducial_matrix.GetElement(1, 3),
                                                   fiducial_matrix.GetElement(2, 3))

    def onRegisterPairedPoint(self):
        self.PairedPointRegistration.SetAndObserveFromFiducialListNodeId(self.PhysicalFiducials.GetID())
        self.PairedPointRegistration.SetAndObserveToFiducialListNodeId(self.VirtualFiducials.GetID())
        self.PairedPointRegistration.SetOutputTransformNodeId(self.BlockRefToBlock.GetID())
        self.PairedPointRegistration.SetRegistrationModeToRigid()
        self.PairedPointRegistration.SetUpdateModeToManual()
        slicer.modules.fiducialregistrationwizard.logic().UpdateCalibration(self.PairedPointRegistration)
        registration_error = self.PairedPointRegistration.GetCalibrationError()
        self.StylusRefToBlockRef.SetAndObserveTransformNodeID(self.BlockRefToBlock.GetID())
        self.PPErrorLabel.setText(f'Paired point RMS error: {registration_error}')
        #return registration_error

    def onCollectSurfaceFiducials(self):
        self.LastFid = 0
        self.Timer = qt.QTimer()
        self.Timer.timeout.connect(self.CollectSurfFidsTimer)
        self.Timer.setInterval(100)
        self.Timer.start()
        print("Started")

    # Link between logic to place fiducial and timer starter
    def CollectSurfFidsTimer(self):
        self.CurrentFid = self.LastFid + 1
        slicer.modules.markups.logic().SetActiveListID(self.SurfaceFiducials)
        fiducial_matrix = vtk.vtkMatrix4x4()
        self.StylusTipToStylusRef.GetMatrixTransformToWorld(fiducial_matrix)
        slicer.modules.markups.logic().AddFiducial(fiducial_matrix.GetElement(0, 3),
                                                   fiducial_matrix.GetElement(1, 3),
                                                   fiducial_matrix.GetElement(2, 3))
        self.LastFid = self.CurrentFid
        self.SurfaceFiducialsLabel.setText(f'Number of surface fiducials placed: {self.SurfaceFiducials.GetNumberOfFiducials()}')
        return self.CurrentFid

    # Stop timer for collecting surface points every n seconds
    def onStopCollectingSurfaceFiducials(self):
        self.Timer.stop()
        print("Paused")
        self.SurfaceFiducialsLabel.setText(f'Number of surface fiducials placed: {self.SurfaceFiducials.GetNumberOfFiducials()}')

    # Remove Fibula Surface fiducial
    def onRemoveFibulaSurfaceFid(self):
        slicer.modules.markups.logic().SetActiveListID(self.SurfaceFiducials)
        self.SurfaceFiducials.RemoveAllMarkups()
        #self.BlockRefToBlock.SetAndObserveTransformNodeID(None)
        print("Removed all surface fiducials")
        self.SurfaceFiducialsLabel.setText(f'Number of surface fiducials placed: {self.SurfaceFiducials.GetNumberOfFiducials()}')

    def onRegisterSurface(self):
        max_iterations = 100
        print("Running iterative closest point registration")
        fiducials_polydata = vtk.vtkPolyData()
        self.fiducials_to_polydata(self.SurfaceFiducials, fiducials_polydata)
        icp_transform = vtk.vtkIterativeClosestPointTransform()
        icp_transform.SetSource(fiducials_polydata)
        icp_transform.SetTarget(self.Block.GetPolyData())
        icp_transform.GetLandmarkTransform().SetModeToRigidBody()
        icp_transform.SetMaximumNumberOfIterations(max_iterations)
        icp_transform.Modified()
        icp_transform.Update()

        self.SurfaceRegistration.SetMatrixTransformToParent(icp_transform.GetMatrix())
        if slicer.app.majorVersion >= 5 or (slicer.app.majorVersion >= 4 and slicer.app.minorVersion >= 11):
            self.SurfaceRegistration.AddNodeReferenceID(slicer.vtkMRMLTransformNode.GetMovingNodeReferenceRole(),
                                                        self.SurfaceFiducials.GetID())
            self.SurfaceRegistration.AddNodeReferenceID(slicer.vtkMRMLTransformNode.GetFixedNodeReferenceRole(),
                                                       self.Block.GetID())
        surf_error = self.compute_mean_distance(self.SurfaceFiducials, self.Block, self.SurfaceRegistration,
                                                self.BlockRefToBlock)
        self.SurfaceErrorLabel.setText(f'Surface RMS error: {surf_error}')


    def onPlacePlanePoint(self):
        #slicer.modules.markups.logic().SetActiveListID(self.PlaneFiducials)
        #placeModePersistence = 0
        #slicer.modules.markups.logic().StartPlaceMode(placeModePersistence)
        #self.PlaneFiducials.SetNthControlPointLocked(self.PlaneFiducials.GetNumberOfFiducials()-1, 1)
        slicer.modules.markups.logic().SetActiveListID(self.PlaneFiducials)
        fiducial_matrix = vtk.vtkMatrix4x4()
        self.StylusTipToStylusRef.GetMatrixTransformToWorld(fiducial_matrix)
        slicer.modules.markups.logic().AddFiducial(fiducial_matrix.GetElement(0, 3),
                                                   fiducial_matrix.GetElement(1, 3),
                                                   fiducial_matrix.GetElement(2, 3))

    #def onUpdateSlicePlane__(self):
    #    self.Green.SetSliceVisible(1)
    #    self.UpdateSlicePlane(self.PlaneFiducials, self.Green)
        #self.Green.SetOpacity(0.8)
        #self.Green.Normal.SetDisplayVisibility(1)

    def onUpdateSlicePlane(self):
        self.plane_collection = vtk.vtkPlaneCollection()
        #CutPlane = getNode('CutPlane')
        self.plane = vtk.vtkPlane()
        normal = [0,0,0]
        origin = [0,0,0]
        self.CutPlane.GetNormalWorld(normal)
        self.CutPlane.GetOriginWorld(origin)
        self.plane.SetNormal(normal)
        self.plane.SetOrigin(origin)
        self.plane_collection.AddItem(self.plane)
        print("Updated slice plane")

    def onFlipNormal(self):
        current_normal = self.plane.GetNormal()
        self.plane.SetNormal(-current_normal[0], -current_normal[1], -current_normal[2])
        print("Flipped normal")
        #GreenNormal_Flipped = np.negative(np.asarray(self.getVTKPlaneFromSlice(self.Green).GetNormal()))
        #slicer.modules.reformat.logic().SetSliceNormal(self.Green, 1, 1, 1)
        #slicer.modules.reformat.logic().SetSliceNormal(self.Green, GreenNormal_Flipped)
        #print('Green flipped')

    #def onClipPlane(self):
    #    self.clipNode.SetGreenSliceClipState(2)
    #    self.clipNode.SetRedSliceClipState(0)

    def onDeleteSlicePlane(self):
        clipped = getNode('Clipped Block')
        slicer.mrmlScene.RemoveNode(clipped)
        self.plane_collection = vtk.vtkPlaneCollection()
        #self.Green.SetSliceVisible(0)
        #slicer.modules.markups.logic().SetActiveListID(self.PlaneFiducials)
        #self.PlaneFiducials.RemoveAllMarkups()
        #StylusRefToAnatomyRef.SetAndObserveTransformNodeID(None)
        print("Plane Fiducials Removed")

    def onGenerateModels(self):
        self.generateModel(self.Block, slicer.vtkSlicerModelsLogic())

    def onExportModels(self):
        model_export_path = "C:\\Users\\Melissa\\Desktop\\UBC\\ISTAR\\MandibleReconstruction\\modeloutput\\Mandible.stl"
        writer = vtk.vtkSTLWriter()
        writer.SetInputData(self.Block.GetPolyData())
        writer.SetFileName(model_export_path)
        writer.Update()
        print("Exported mandible model")

    def generateModel(self, block, modelLogic):
        clipper = vtk.vtkClipClosedSurface()
        clipper.SetClippingPlanes(self.plane_collection)
        clipper.SetInputData(block.GetPolyData())
        clipper.SetGenerateFaces(1)
        clipper.SetGenerateOutline(1)
        print(clipper.GetGenerateFaces())
        clipper.Update()
        clipped_polydata = clipper.GetOutput()

        clipped_block = slicer.vtkMRMLModelNode()
        slicer.mrmlScene.AddNode(clipped_block)
        clipped_block.SetName("Clipped Block")
        clipped_block.SetAndObservePolyData(clipped_polydata)
        if clipped_block.GetModelDisplayNode() is None: 
            modelDisplay = slicer.vtkMRMLModelDisplayNode()
            modelDisplay.SetBackfaceCulling(0)
            modelDisplay.SetColor(0, 0.33333333, 0)
            modelDisplay.SetScene(slicer.mrmlScene)
            modelDisplay.SetScalarVisibility(1)
            slicer.mrmlScene.AddNode(modelDisplay)
            clipped_block.SetAndObserveDisplayNodeID(modelDisplay.GetID())
            print("Model display")
        clipped_block.GetModelDisplayNode().SetColor(0, 0.333333333, 0)
        clipped_block.GetModelDisplayNode().VisibilityOn()
        #greenPlane = self.getVTKPlaneFromSlice(self.Green)

        ### Green
        ##planeCollectionGreen = vtk.vtkPlaneCollection()
        ##planeCollectionGreen.AddItem(greenPlane)
        ##normalGreen = -np.asarray(planeCollectionGreen.GetItem(0).GetNormal())
        ##planeCollectionGreen.GetItem(0).SetNormal(normalGreen)
        #clipper = vtk.vtkClipPolyData()
        #clipper.SetClipFunction(greenPlane)
        #clipper.SetInputData(block.GetPolyData())
        ##clipper.SetClipFunction(greenPlane)
        #clipper.InsideOutOn()
        ##clipper.SetGenerateFaces(1)
        #clipper.Update()
        ##polyDataNewGreen = clipper.GetClippedOutput()
        #polyDataNewGreen = clipper.GetOutput()
        #print(polyDataNewGreen)
        #polyDataNewGreen = self.polydataClean(polyDataNewGreen)
        #print(polyDataNewGreen)

        #ClippedBlock = slicer.vtkMRMLModelNode()
        ##if ClippedBlock is None:
        ##    ClippedBlock = slicer.vtkMRMLModelNode()
        #ClippedBlock.SetAndObservePolyData(polyDataNewGreen)
        #slicer.mrmlScene.AddNode(ClippedBlock)
        #print("Updated")

        #if ClippedBlock.GetModelDisplayNode() is None:
        #    modelDisplay = slicer.vtkMRMLModelDisplayNode()
        #    modelDisplay.SetColor(1, 0, 1)
        #    modelDisplay.SetBackfaceCulling(0)
        #    modelDisplay.SetScene(slicer.mrmlScene)
        #    slicer.mrmlScene.AddNode(modelDisplay)
        #    ClippedBlock.SetAndObserveDisplayNodeID(modelDisplay.GetID())

        #ClippedBlock.SetName("Clipped Block")
        ##modelLogic.SetAllModelsVisibility(0)
        ##ClippedBlock.GetModelDisplayNode().VisibilityOn()

        #planeCollection = vtk.vtkPlaneCollection()
        #planeCollection.AddItem(greenPlane)

        #clipper = vtk.vtkClipClosedSurface()
        #clipper.SetClippingPlanes(planeCollection)
        #clipper.SetInputData(block.GetPolyData())
        #clipper.SetGenerateFaces(1)
        ##clipper.GenerateFacesOn()
        #clipper.Update()
        
        #polyDataNewGreen = clipper.GetOutput()
        
        #ClippedBlock = slicer.vtkMRMLModelNode() 
        #ClippedBlock.SetAndObservePolyData(polyDataNewGreen)
        #slicer.mrmlScene.AddNode(ClippedBlock)
        #ClippedBlock.SetName("Clipped Block-Updated")

        #if ClippedBlock.GetModelDisplayNode() is None:
        #    modelDisplay = slicer.vtkMRMLModelDisplayNode()
        #    modelDisplay.SetColor(1, 0, 1)
        #    modelDisplay.SetBackfaceCulling(0)
        #    modelDisplay.SetScene(slicer.mrmlScene)
        #    slicer.mrmlScene.AddNode(modelDisplay)
        #    ClippedBlock.SetAndObserveDisplayNodeID(modelDisplay.GetID())

        #return ClippedBlock

    def polydataClean(self, polydata):
        holes = vtk.vtkFillHolesFilter()
        clean = vtk.vtkCleanPolyData()
        triangle = vtk.vtkTriangleFilter()
        sinc = vtk.vtkWindowedSincPolyDataFilter()
        sinc.NormalizeCoordinatesOn()
        sinc.BoundarySmoothingOff()
        sinc.NonManifoldSmoothingOn()
        for i in clean, triangle, holes:
            i.SetInputData(polydata)
            i.Update()
            polydata = i.GetOutput()
        return polydata

    def createButton(self, button_text="Default Text", tooltip="", enabled=True):
        button = qt.QPushButton()
        button.setText(button_text)
        button.setToolTip(tooltip)
        button.setEnabled(enabled)
        return button

    #def UpdateSlicePlane(self, fiducials_list, slice_node, param1=None, param2=None):
    #    nOfFiduciallPoints = fiducials_list.GetNumberOfFiducials()
    #    points = np.zeros([3,nOfFiduciallPoints])
    #    for i in range(0, nOfFiduciallPoints):
    #        fiducials_list.GetNthFiducialPosition(i, points[:,i])
    #    planePosition = points.mean(axis=1)
    #    planeNormal = np.cross(points[:,1] - points[:,0], points[:,2] - points[:,0])
    #    planeX = points[:,1] - points[:,0]
    #    slice_node.SetSliceToRASByNTP(planeNormal[0], planeNormal[1], planeNormal[2],
    #                                 planeX[0], planeX[1], planeX[2],
    #                                 planePosition[0], planePosition[1], planePosition[2], 0)

    #def getVTKPlaneFromSlice(self, slice):
    #    mat = slice.GetSliceToRAS()
    #    m = np.array([[mat.GetElement(0, 0), mat.GetElement(0, 1), mat.GetElement(0, 2), mat.GetElement(0, 3)],
    #                  [mat.GetElement(1, 0), mat.GetElement(1, 1), mat.GetElement(1, 2), mat.GetElement(1, 3)],
    #                  [mat.GetElement(2, 0), mat.GetElement(2, 1), mat.GetElement(2, 2), mat.GetElement(2, 3)],
    #                  [mat.GetElement(3, 0), mat.GetElement(3, 1), mat.GetElement(3, 2), mat.GetElement(3, 3)]])
    #    nvec = np.array((0, 0, 1, 0))
    #    pvec = np.array((0, 0, 0, 1))
    #    normal = np.dot(m, nvec)
    #    point = np.dot(m, pvec)
    #    plane = vtk.vtkPlane()
    #    plane.SetNormal(normal[0], normal[1], normal[2])
    #    plane.SetOrigin(point[0], point[1], point[2])
    #    return plane

    def compute_mean_distance(self, surface_fiducials, model, surface_registration, modelRefToModel):
        surface_points = vtk.vtkPoints()
        cellId = vtk.mutable(0)
        subId = vtk.mutable(0)
        dist2 = vtk.mutable(0.0)
        locator = vtk.vtkCellLocator()
        locator.SetDataSet(model.GetPolyData())
        locator.SetNumberOfCellsPerBucket(1)
        locator.BuildLocator()
        total_distance = 0.0

        num_of_fiducials = surface_fiducials.GetNumberOfFiducials()
        m = vtk.vtkMath()
        for fiducial_index in range(0, num_of_fiducials):
            original_point = [0, 0, 0]
            surface_fiducials.GetNthFiducialPosition(fiducial_index, original_point)
            transformed_point = [0, 0, 0, 1]
            original_point.append(1)
            surface_registration.GetTransformToParent().MultiplyPoint(original_point, transformed_point)
            surface_point = [0, 0, 0]
            transformed_point.pop()
            locator.FindClosestPoint(transformed_point, surface_point, cellId, subId, dist2)
            total_distance = total_distance + math.sqrt(dist2)
            surface_error = (total_distance/num_of_fiducials)
        modelRefToModel.SetAndObserveTransformNodeID(surface_registration.GetID())
        return surface_error

    def fiducials_to_polydata(self, fiducials, polydata):
        points = vtk.vtkPoints()
        num_of_fiducials = fiducials.GetNumberOfFiducials()
        for index in range(0, num_of_fiducials):
            p = [0, 0, 0]
            fiducials.GetNthFiducialPosition(index, p)
            points.InsertNextPoint(p)

        temp_polydata = vtk.vtkPolyData()
        temp_polydata.SetPoints(points)

        vertex = vtk.vtkVertexGlyphFilter()
        vertex.SetInputData(temp_polydata)
        vertex.Update()

        polydata.ShallowCopy(vertex.GetOutput())

class CutPlaneTestingLogic(ScriptedLoadableModuleLogic):
    def __init__(self):
        ScriptedLoadableModuleLogic.__init__(self)

class CutPlaneTestingTest(ScriptedLoadableModuleTest):
    def setUp(self):
        slicer.mrmlScene.Clear()

    def runTest(self):
        self.setUp()
        self.test_CutPlaneTesting()

    def test_CutPlaneTesting(self):
        self.delayDisplay("Start test")
        logic = CutPlaneTestingLogic()
        self.delayDisplay("Test Passed")