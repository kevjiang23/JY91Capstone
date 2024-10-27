import math
import os
import numpy as np
import math
from __main__ import vtk, qt, ctk, slicer
from slicer.util import VTKObservationMixin, getNode

import ManageSlicer as ms
import ManageUI as ui
from ManageRegistration import registration as register

try: 
    import jpype
    import jpype.imports 
    from jpype.types import *
except ImportError as e: 
    slicer.util.pip_install('JPype1')
    import jpype
    import jpype.imports 
    from jpype.types import *

#Move to manage slicer
def place_CT_fiducial(CT_fiducial_list, placeModePersistence=0):
    slicer.modules.markups.logic().SetActiveListID(CT_fiducial_list)
    #placeModePersistence = 0
    slicer.modules.markups.logic().StartPlaceMode(placeModePersistence)
    CT_fiducial_list.SetNthControlPointLocked(CT_fiducial_list.GetNumberOfFiducials()-1, 1)

#Move to manage slicer
def remove_CT_fiducials(CT_fiducial_list):
    slicer.modules.markups.logic().SetActiveListID(CT_fiducial_list)
    CT_fiducial_list.RemoveAllMarkups()
    print("CT Fiducials Removed")

#Move to manage slicer
def place_patient_fiducial(patient_fiducial_list, StylusTipToStylusRef):
    slicer.modules.markups.logic().SetActiveListID(patient_fiducial_list)
    fiducial_matrix = vtk.vtkMatrix4x4()
    StylusTipToStylusRef.GetMatrixTransformToWorld(fiducial_matrix)
    slicer.modules.markups.logic().AddFiducial(fiducial_matrix.GetElement(0, 3),
                                               fiducial_matrix.GetElement(1, 3),
                                               fiducial_matrix.GetElement(2, 3))
    #patient_fiducial_list.SetNthControlPointLocked(patient_fiducial_list.GetNumberOfFiducials()-1, 1)
    #return fiducial count

#def remove_patient_fiducials(patient_fiducial_list, StylusRefToAnatomyRef):
#    slicer.modules.markups.logic().SetActiveListID(patient_fiducial_list)
#    patient_fiducial_list.RemoveAllMarkups()
#    StylusRefToAnatomyRef.SetAndObserveTransformNodeID(None)
#    print("Patient Fiducials Removed")
#    #return fiducial count

#Move to manage slicer
def remove_patient_fiducials(patient_fiducial_list, StylusRefToAnatomyRef):
    slicer.modules.markups.logic().SetActiveListID(patient_fiducial_list)
    patient_fiducial_list.RemoveAllMarkups()
    #StylusRefToAnatomyRef.SetAndObserveTransformNodeID(None)
    print("Patient Fiducials Removed")
    #return fiducial count

    #Move to manage slicer
def run_registration(registration_node, CT_fiducials, patient_fiducials, AnatomyRefToAnatomy, StylusRefToAnatomyRef):
    registration_node.SetAndObserveFromFiducialListNodeId(patient_fiducials.GetID())
    registration_node.SetAndObserveToFiducialListNodeId(CT_fiducials.GetID())
    registration_node.SetOutputTransformNodeId(AnatomyRefToAnatomy.GetID())
    registration_node.SetRegistrationModeToRigid()
    registration_node.SetUpdateModeToManual()
    slicer.modules.fiducialregistrationwizard.logic().UpdateCalibration(registration_node)
    registration_error = registration_node.GetCalibrationError()
    StylusRefToAnatomyRef.SetAndObserveTransformNodeID(AnatomyRefToAnatomy.GetID())
    return registration_error

#def place_surface_fiducial(surface_fiducials, StylusTipToStylusRef):
#    slicer.modules.markups.logic().SetActiveListID(surface_fiducials)
#    surface_fiducial_matrix = vtk.vtkMatrix4x4()
#    StylusTipToStylusRef.GetMatrixTransformToWorld(surface_fiducial_matrix)
#    slicer.modules.markups.logic().AddFiducial(surface_fiducial_matrix.GetElement(0, 3),
#                                             surface_fiducial_matrix.GetElement(1, 3),
#                                             surface_fiducial_matrix.GetElement(2, 3))

#Move to manage slicer
def remove_surface_fiducials(surface_fiducials, modelRefToModel):
    slicer.modules.markups.logic().SetActiveListID(surface_fiducials)
    surface_fiducials.RemoveAllMarkups()
    modelRefToModel.SetAndObserveTransformNodeID(None)
    print("Removed all surface fiducials")

    #Move to manage slicer
def run_surface_registration(surface_fiducial_list, model, surface_registration, max_iterations):
    print("Running iterative closest point registration")

    fiducials_polydata = vtk.vtkPolyData()
    ms.fiducials_to_polydata(surface_fiducial_list, fiducials_polydata)

    icp_transform = vtk.vtkIterativeClosestPointTransform()
    icp_transform.SetSource(fiducials_polydata)
    icp_transform.SetTarget(model.GetPolyData())
    icp_transform.GetLandmarkTransform().SetModeToRigidBody()
    icp_transform.SetMaximumNumberOfIterations(max_iterations)
    icp_transform.Modified()
    icp_transform.Update()

    surface_registration.SetMatrixTransformToParent(icp_transform.GetMatrix())
    if slicer.app.majorVersion >= 5 or (slicer.app.majorVersion >= 4 and slicer.app.minorVersion >= 11):
        surface_registration.AddNodeReferenceID(slicer.vtkMRMLTransformNode.GetMovingNodeReferenceRole(),
                                                surface_fiducial_list.GetID())
        surface_registration.AddNodeReferenceID(slicer.vtkMRMLTransformNode.GetFixedNodeReferenceRole(),
                                                   model.GetID())
    #Can we return error instead?
    return True

#Move to manage slicer
def compute_mean_distance(surface_fiducials, model, surface_registration, modelRefToModel):
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

#MANDIBLE RESECTION
def check_plane_normal_direction(green_plane, yellow_plane):
    #yellow = slicer.util.getNode('vtkMRMLSliceNodeYellow')
    #yellowPlane = getVTKPlaneFromSlice(yellow)
    yellowPlane = ms.get_vtkplane_from_slice(yellow_plane)
    yellowNormal = yellowPlane.GetNormal()
    yellowOrigin = yellowPlane.GetOrigin()
    print(f'Yellow normals: {yellowNormal}')
    print(f'Yellow origins: {yellowOrigin}')

    #green = slicer.util.getNode('vtkMRMLSliceNodeGreen')
    #greenPlane = getVTKPlaneFromSlice(green)
    greenPlane = ms.get_vtkplane_from_slice(green_plane)
    greenNormal = greenPlane.GetNormal()
    greenOrigin = greenPlane.GetOrigin()
    print(f'Green normals: {greenNormal}')
    print(f'Green origins: {greenOrigin}')

    delta = [yellowOrigin[0] - greenOrigin[0], 
             yellowOrigin[1] - greenOrigin[1], 
             yellowOrigin[2] - greenOrigin[2]]
    print(f'Green check: {np.dot(delta, greenNormal)}')
    print(f'Yellow check: {np.dot(delta, yellowNormal)}')
    print(f'Delta: {delta}')
    print(f'Dot delta green: {np.dot(delta, greenNormal)}')
    print(f'Dot delta yellow: {np.dot(delta, yellowNormal)}')
    green_check2 = np.dot(delta, greenNormal)/(np.linalg.norm(delta)*np.linalg.norm(greenNormal))
    print(f'Green input: {green_check2}')
    green_angle = math.acos(green_check2)
    print(f'Green angle: {green_angle}')
    yellow_check2 = np.dot(delta, yellowNormal)/(np.linalg.norm(delta)*np.linalg.norm(yellowNormal))
    print(f'Yellow input: {yellow_check2}')
    yellow_angle = math.acos(yellow_check2)
    print(f'Yellow angle: {yellow_angle}')

    if np.dot(delta, greenNormal) < 0: 
        greenNormal_flipped = np.negative(np.asarray(greenNormal))
        slicer.modules.reformat.logic().SetSliceNormal(green_plane, 1, 1, 1)
        slicer.modules.reformat.logic().SetSliceNormal(green_plane, greenNormal_flipped)
        greenNormal = greenNormal_flipped
        print('Green flipped')
    else:
        print("Did not flip green")
    if np.dot(delta, yellowNormal) > 0:
        yellowNormal_flipped = np.negative(np.asarray(yellowNormal))
        slicer.modules.reformat.logic().SetSliceNormal(yellow_plane, 1, 1, 1)
        slicer.modules.reformat.logic().SetSliceNormal(yellow_plane, yellowNormal_flipped)
        print('Yellow flipped')
        yellowNormal = yellowNormal_flipped
    else:
       print('Did not flip yellow')
    return greenNormal, greenOrigin, yellowNormal, yellowOrigin

def on_export_planes(path, greenNormal, greenOrigin, yellowNormal, yellowOrigin):
    try: 
        os.chdir(path)
        with open('planeValues.txt', 'w') as f: 
            f.write(f'{greenNormal[0]} {greenNormal[1]} {greenNormal[2]}\n'
                    f'{greenOrigin[0]} {greenOrigin[1]} {greenOrigin[2]}\n'
                    f'{yellowNormal[0]} {yellowNormal[1]} {yellowNormal[2]}\n'
                    f'{yellowOrigin[0]} {yellowOrigin[1]} {yellowOrigin[2]}')
            print(f'Text file was written to {path}')
    except OSError: 
        print("The directory does not exist.")

def clip_mandible_button_clicked(mandibleModelInput, modelLogic):
    #print "Begin Resection..."
    mandiblePolyData = mandibleModelInput.GetPolyData()
    # ----------Smoothing-------------
    sinc = vtk.vtkWindowedSincPolyDataFilter()
    sinc.SetInputData(mandiblePolyData)
    sinc.NormalizeCoordinatesOn()
    sinc.BoundarySmoothingOn()
    sinc.NonManifoldSmoothingOn()
    sinc.SetNumberOfIterations(20)
    sinc.Update()
    mandiblePolyData = sinc.GetOutput()
    # --------------------------------
    mandiblePolyData = ms.polydata_clean(mandiblePolyData)

    planeCollection = vtk.vtkPlaneCollection()
    # if greenCheck.isChecked():
    green = slicer.util.getNode('vtkMRMLSliceNodeGreen')
    greenPlane = ms.get_vtkplane_from_slice(green)
    planeCollection.AddItem(greenPlane)
    # if redCheck.isChecked():
    #     red = slicer.util.getNode('vtkMRMLSliceNodeRed')
    #     redPlane = getVTKPlaneFromSlice(red)
    #     planeCollection.AddItem(redPlane)
    # if yellowCheck.isChecked():
    yellow = slicer.util.getNode('vtkMRMLSliceNodeYellow')
    yellowPlane = ms.get_vtkplane_from_slice(yellow)
    planeCollection.AddItem(yellowPlane)

    clipper = vtk.vtkClipClosedSurface()
    clipper.SetClippingPlanes(planeCollection)
    clipper.SetInputData(mandiblePolyData)
    clipper.SetGenerateFaces(1)
    clipper.Update()
    polyDataNew = clipper.GetOutput()
    polyDataNew = ms.polydata_clean(polyDataNew)

    mandibleClippingPlanes = vtk.vtkPlaneCollection()
    mandibleClippingPlanes.AddItem(greenPlane)
    mandibleClippingPlanes.AddItem(yellowPlane)  # should be yellow here

    resection = slicer.vtkMRMLModelNode()
    resection.SetAndObservePolyData(polyDataNew)
    slicer.mrmlScene.AddNode(resection)
    resection.SetName("Resection")

    if resection.GetModelDisplayNode() is None:
        modelDisplay = slicer.vtkMRMLModelDisplayNode()
        modelDisplay.SetColor(1, 1, 0)  # yellow
        modelDisplay.SetBackfaceCulling(0)
        modelDisplay.SetScene(slicer.mrmlScene)
        slicer.mrmlScene.AddNode(modelDisplay)
        resection.SetAndObserveDisplayNodeID(modelDisplay.GetID())

    # Green
    planeCollectionGreen = vtk.vtkPlaneCollection()
    planeCollectionGreen.AddItem(greenPlane)
    normalGreen = -np.asarray(planeCollectionGreen.GetItem(0).GetNormal())
    planeCollectionGreen.GetItem(0).SetNormal(normalGreen)
    clipper = vtk.vtkClipClosedSurface()
    clipper.SetClippingPlanes(planeCollectionGreen)
    clipper.SetInputData(mandiblePolyData)
    clipper.SetGenerateFaces(1)
    clipper.Update()
    polyDataNewGreen = clipper.GetOutput()
    polyDataNewGreen = ms.polydata_clean(polyDataNewGreen)

    # Yellow
    planeCollectionYellow = vtk.vtkPlaneCollection()
    planeCollectionYellow.AddItem(yellowPlane)
    normalYellow = -np.asarray(planeCollectionYellow.GetItem(0).GetNormal())
    planeCollectionYellow.GetItem(0).SetNormal(normalYellow)
    clipper = vtk.vtkClipClosedSurface()
    clipper.SetClippingPlanes(planeCollectionYellow)
    clipper.SetInputData(mandiblePolyData)
    clipper.SetGenerateFaces(1)
    clipper.Update()
    polyDataNewYellow = clipper.GetOutput()
    polyDataNewYellow = ms.polydata_clean(polyDataNewYellow)

    append = vtk.vtkAppendPolyData()
    append.AddInputData(polyDataNewYellow)
    append.AddInputData(polyDataNewGreen)
    append.Update()
    polydataNonResected = append.GetOutput()

    nonResectedModelOverall = slicer.vtkMRMLModelNode()
    if nonResectedModelOverall is None:
        nonResectedModelOverall = slicer.vtkMRMLModelNode()
    nonResectedModelOverall.SetAndObservePolyData(polydataNonResected)
    slicer.mrmlScene.AddNode(nonResectedModelOverall)

    if nonResectedModelOverall.GetModelDisplayNode() is None:
        modelDisplay = slicer.vtkMRMLModelDisplayNode()
        modelDisplay.SetColor(1, 0, 1)
        modelDisplay.SetBackfaceCulling(0)
        modelDisplay.SetScene(slicer.mrmlScene)
        slicer.mrmlScene.AddNode(modelDisplay)
        nonResectedModelOverall.SetAndObserveDisplayNodeID(modelDisplay.GetID())

    nonResectedModelOverall.SetName("NonResected")

    modelLogic.SetAllModelsVisibility(0)
    resection.GetModelDisplayNode().VisibilityOn()

    return mandibleClippingPlanes, resection, nonResectedModelOverall


#VIRTUAL SURGICAL PLAN FUNCTIONS
def set_resection_plane(JVM, plane):      
    '''
    This converts the resection planes to the Java type, Plane, so that they can be used in the 
    VSP from Artisynth.
    '''
    plane_normal = plane.GetNormal()
    plane_origin = plane.GetOrigin()
    updated_plane_normal = JVM.setVector3d(plane_normal[0], plane_normal[1], plane_normal[2])
    updated_plane_origin = JVM.setVector3d(plane_origin[0], plane_origin[1], plane_origin[2])
    print(updated_plane_normal)
    print(updated_plane_origin)
    updated_plane = JVM.setPlane(updated_plane_normal, updated_plane_origin)
    return updated_plane

def vtkmatrix4x4_to_rigid3d(JVM, transform_node):
    '''
    Converts a vtkmatrix4x4 to a RigidTransform3d recognizable by Java
    '''
    trans_mat = transform_node.GetMatrixTransformToParent()
    trans_vec3d = JVM.setVector3d(trans_mat.GetElement(0, 3), trans_mat.GetElement(1, 3), trans_mat.GetElement(2, 3))
    trans_rot3d = JVM.setRotation3d(trans_mat.GetElement(0, 0), trans_mat.GetElement(0, 1), trans_mat.GetElement(0, 2),
                                            trans_mat.GetElement(1, 0), trans_mat.GetElement(1, 1), trans_mat.GetElement(1, 2),
                                            trans_mat.GetElement(2, 0), trans_mat.GetElement(2, 1), trans_mat.GetElement(2, 2))
    rigid3d = JVM.setRigidTransform3d(trans_vec3d, trans_rot3d)
    return rigid3d

def compute_RDP(JVM, contour, left_plane, right_plane, min_seg_length, max_segs):
    #Place contour node fiducial locations into a numpy array
    contour_array = []
    for i in range(contour.GetNumberOfControlPoints()):
        contour_array.append([contour.GetNthControlPointPositionVector(i)[0],
                              contour.GetNthControlPointPositionVector(i)[1], 
                              contour.GetNthControlPointPositionVector(i)[2]])
    print(contour_array)

    #Convert the numpy array to a Java type array list of Point3d (Arraylist[Point3d])
    float_array = JVM.changeFloatToArrayList(contour_array)
    contour_point3d = JVM.setArrayPoint3d(float_array)
    print(contour_point3d.size())
    #Compute RDP
    RDP_lines = JVM.computeRDPLine(contour_point3d, left_plane, right_plane, min_seg_length, max_segs)
    print(f'RDP lines: {RDP_lines}')
    print(f'RDP size: {RDP_lines.size()}')
    return RDP_lines

def display_RDP(RDP_lines):
    try:
        rdp_markups = getNode('RDP Line')
        slicer.mrmlScene.RemoveNode(rdp_markups)
    except slicer.util.MRMLNodeNotFoundException: 
        print("Created new RDP node")
    rdp_markups = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'RDP Line')
    slicer.modules.markups.logic().SetActiveListID(rdp_markups)
    for i in range(RDP_lines.size()):
        slicer.modules.markups.logic().AddFiducial(RDP_lines[i].x, RDP_lines[i].y, RDP_lines[i].z)
    return rdp_markups

def create_RDP_model(RDP_lines):
    RDP_points = vtk.vtkPoints()
    for i in range(RDP_lines.size()):
        RDP_points.InsertNextPoint(RDP_lines[i].x, RDP_lines[i].y, RDP_lines[i].z)

    RDP_lines = vtk.vtkLineSource()
    RDP_lines.SetPoints(RDP_points)

    tube_filter = vtk.vtkTubeFilter()
    tube_filter.SetInputConnection(RDP_lines.GetOutputPort())
    tube_filter.SetRadius(0.5)
    tube_filter.SetNumberOfSides(50)
    tube_filter.Update()

    #Make it into a model
    RDP_model = slicer.vtkMRMLModelNode()
    slicer.mrmlScene.AddNode(RDP_model)
    RDP_model.SetName("RDP Lines")
    RDP_model.SetAndObservePolyData(tube_filter.GetOutput())
    if RDP_model.GetModelDisplayNode() is None: 
        modelDisplay = slicer.vtkMRMLModelDisplayNode()
        modelDisplay.SetBackfaceCulling(0)
        modelDisplay.SetColor(0, 0.33333333, 0)
        modelDisplay.SetScene(slicer.mrmlScene)
        modelDisplay.SetScalarVisibility(1)
        slicer.mrmlScene.AddNode(modelDisplay)
        RDP_model.SetAndObserveDisplayNodeID(modelDisplay.GetID())
        print("Model display")
    RDP_model.GetModelDisplayNode().SetColor(0, 0.333333333, 0)
    RDP_model.GetModelDisplayNode().VisibilityOn()
    return RDP_model

def run_VSP(JVM, seg_separation, min_seg_length, max_segs, contour, fibula_path, mandible_path, 
            left_vtkplane, right_vtkplane, fibfid, TCW_node):
    #Set start point for VSP using the fib fid node 
    ras = vtk.vtkVector3d(0,0,0)
    fibfid.GetNthControlPointPosition(0, ras)
    start_point = JVM.setPoint3d(ras[0], ras[1], ras[2])

    #Set cut planes 
    left_plane = set_resection_plane(JVM, left_vtkplane)
    right_plane = set_resection_plane(JVM, right_vtkplane)

    #Compute RDP
    RDP = compute_RDP(JVM, contour, left_plane, right_plane, min_seg_length, max_segs)
    RDP_markups = display_RDP(RDP)
    RDP_model = create_RDP_model(RDP)
    #return RDP
    #Get path to mandible and clipped fibula models
    clipped_fibula = os.path.dirname(fibula_path.GetText())+"\\ClippedFibula_Donor.stl"
    mandible = mandible_path.GetText()

    #Get TCW 
    TCW = vtkmatrix4x4_to_rigid3d(JVM, TCW_node)

    #Calculate VSP 
    fibula_segments = JVM.findDonorCutPlanes(seg_separation, min_seg_length, max_segs,
                                             RDP, clipped_fibula, mandible, left_plane, right_plane,
                                             start_point, TCW)
    return fibula_segments

def generate_segment_transforms(JVM, segment, segno=0):
    number_of_segments = ui.import_node("NumberOfSegments", "vtkMRMLTextNode")
    number_of_segments.SetText(str(segment.size() + segno))
    for i in range(segment.size()):
        #Segment {i} TPS0
        print(f'Segment {i + 1 + segno} TPS0: {JVM.getTPS0(segment[i])}')
        TPS0 = JVM.getTPS0_Array(segment[i])
        ms.arraylist_to_transform(TPS0, "Seg"+str(i+1+segno)+"_TPS0")
        #Segment {i} TPS1
        print(f'Segment {i + 1 + segno} TPS1: {JVM.getTPS1(segment[i])}')
        TPS1 = JVM.getTPS1_Array(segment[i])
        ms.arraylist_to_transform(TPS1, "Seg"+str(i+1+segno)+"_TPS1")
        #Segment {i} TSW_M
        print(f'Segment {i + 1+ segno} TSW_M: {JVM.getTSWM(segment[i])}')
        TSWM = JVM.getTSWM_Array(segment[i])
        ms.arraylist_to_transform(TSWM, "Seg"+str(i+1+segno)+"_TSWM")
        #Segment {i} TSW_D
        print(f'Segment {i + 1+ segno} TSW_D: {JVM.getTSWD(segment[i])}')
        TSWD = JVM.getTSWD_Array(segment[i])
        ms.arraylist_to_transform(TSWD, "Seg"+str(i+1+segno)+"_TSWD")


def connect_JVM():
    if jpype.isJVMStarted():
        genVSP = jpype.JClass("artisynth.istar.Mel.GenerateVSP")()
        print("JVM is already running.")
    else:
        jpype.startJVM(classpath=["C:\\Users\\Melissa\\git\\artisynth_istar\\classes", 
                                  "C:\\Users\\Melissa\\git\\artisynth_core\\classes", 
                                  "C:\\Users\\Melissa\\git\\artisynth_core\\lib\\*"])       #NEED TO FIX THIS HARD CODED PATH 
        print (f'JVM path: {jpype.getDefaultJVMPath()}')
        genVSP = jpype.JClass("artisynth.istar.Mel.GenerateVSP")()
    return genVSP

def create_donor_segments(clipped_fibula, segment_size, existing_segno=0):
    for i in range(segment_size):
        #Get nodes and set transform hierarchy 
        TPS0 = getNode("Seg"+str(i+1+existing_segno)+"_TPS0")
        TPS1 = getNode("Seg"+str(i+1+existing_segno)+"_TPS1")
        TSWD = getNode("Seg"+str(i+1+existing_segno)+"_TSWD")
        TPS0.SetAndObserveTransformNodeID(TSWD.GetID())
        TPS1.SetAndObserveTransformNodeID(TSWD.GetID())

        plane1 = ms.get_vtkplane_from_transform(TPS0)
        plane2 = ms.get_vtkplane_from_transform(TPS1)

        segment_planes = vtk.vtkPlaneCollection()
        segment_planes.AddItem(plane1)
        segment_planes.AddItem(plane2)

        clipped_polydata = ms.clip_polydata(segment_planes, clipped_fibula.GetPolyData())
        segD = ms.create_model(clipped_polydata, "Segment"+ str(i+1+existing_segno)+"_Donor", [1, i*1.0/(segment_size - 1), 0])
        #segD.GetModelDisplayNode().SetColor(1, i*1.0/(segment_size - 1), 0)

        get_segment_length(plane1, clipped_fibula, i+1)
        get_segment_length(plane2, clipped_fibula, i+1)


def create_mandible_segments(segment_size, existing_segno=0):
    for i in range(segment_size): #segment.size()
        segD_polydata = getNode("Segment"+ str(i+1+existing_segno)+"_Donor").GetPolyData()

        TSWD = getNode("Seg"+str(i+1+existing_segno)+"_TSWD") #Want the inverse
        TDW_mat = vtk.vtkMatrix4x4()  #TDW = Transform Donor to World
        TSWD.GetMatrixTransformFromParent(TDW_mat)

        TSWM = getNode("Seg"+str(i+1+existing_segno)+"_TSWM") 
        TWM_mat = vtk.vtkMatrix4x4() #TWM = Transform World to Mandible
        TWM = TSWM.GetMatrixTransformToParent(TWM_mat) 

        TDM = vtk.vtkTransform() #TDM = Transform Donor to Mandible (Concatenated TDW and TWM)
        TDM.SetMatrix(TWM_mat)
        TDM.Concatenate(TDW_mat)

        transform_filter = vtk.vtkTransformPolyDataFilter()
        segM_polydata = ms.transform_polydata(transform_filter, segD_polydata, TDM)
        
        segM = ms.create_model(segM_polydata, "Segment"+ str(i+1+existing_segno)+"_Mand", [1, i*1.0/(segment_size - 1), 0])
        #segM.GetModelDisplayNode().SetColor(1, i*1.0/(segment_size - 1), 0)
        #segM.GetModelDisplayNode().VisibilityOn()

def get_segment_length(plane, model, segment_number):
    contour = ms.get_intersection_contour(plane, model)
    #intersection = slicer.vtkMRMLModelNode()
    #intersection.SetAndObservePolyData(contour)
    #intersection.SetName('TargetContour'+str(segment_number))
    #slicer.mrmlScene.AddNode(intersection)
    centre = ms.get_centroid(contour)
    segment_length_fids = ui.import_node('VSPSegmentEndpoints', 'vtkMRMLMarkupsFiducialNode')
    slicer.modules.markups.logic().SetActiveListID(segment_length_fids)
    slicer.modules.markups.logic().AddFiducial(centre[0], centre[1], centre[2])
    print(f'Intersection contour centre: {centre}')

#def generate_segment_node(polydata, name, color=[0,0.33,0]):
#    segment = slicer.vtkMRMLModelNode()
#    slicer.mrmlScene.AddNode(segment)
#    #segment.SetName("Segment"+ str(segment_number)+"_Donor")
#    segment.SetName(name)
#    segment.SetAndObservePolyData(polydata)
#    if segment.GetModelDisplayNode() is None: 
#        modelDisplay = slicer.vtkMRMLModelDisplayNode()
#        modelDisplay.SetBackfaceCulling(0)
#        modelDisplay.SetColor(0, 0.33333333, 0)
#        modelDisplay.SetScene(slicer.mrmlScene)
#        modelDisplay.SetScalarVisibility(1)
#        slicer.mrmlScene.AddNode(modelDisplay)
#        segment.SetAndObserveDisplayNodeID(modelDisplay.GetID())
#        #print("Model display")
#    segment.GetModelDisplayNode().SetColor(color)
#    segment.GetModelDisplayNode().VisibilityOn()
#    return segment


def create_cut_plane_model(number_of_segments):
    try: 
        for i in range(number_of_segments):
            CutPlane0 = getNode('Seg'+str(i+1)+'CutPlane0')
            CutPlane1 = getNode('Seg'+str(i+1)+'CutPlane1')
    except slicer.util.MRMLNodeNotFoundException: 
        for i in range(number_of_segments):
            CutPlane0 = ms.create_cut_plane('Seg'+str(i+1)+'CutPlane0', 0)
            CutPlane0.SetAndObserveTransformNodeID(getNode('Seg'+str(i+1)+'_TPS0').GetID())
            CutPlane0.SetDisplayVisibility(0)
            CutPlane1 = ms.create_cut_plane('Seg'+str(i+1)+'CutPlane1', 0)
            CutPlane1.SetAndObserveTransformNodeID(getNode('Seg'+str(i+1)+'_TPS1').GetID())
            CutPlane1.SetDisplayVisibility(0)

#GUIDE SEGMENT CUTS HELPER FUNCTIONS 
def transform_donor_to_mandible(cut_plane, TSWD, TSWM):
    TPD = vtk.vtkMatrix4x4()        #Transform from plane to donor
    transform_node = cut_plane.GetParentTransformNode()
    transform_node.GetMatrixTransformToWorld(TPD)
        #Update resection plane in case they want to update the reconstruction plan 
        
    #Transform cut plane from donor space to mandible space 
    TDW = vtk.vtkMatrix4x4()    #transform donor to world
    TWM = vtk.vtkMatrix4x4()    #transform world to mandible
    TSWD.GetMatrixTransformFromWorld(TDW)
    TSWM.GetMatrixTransformToWorld(TWM)

    TDM = vtk.vtkMatrix4x4()
    TPW = vtk.vtkMatrix4x4()

    vtk.vtkMatrix4x4.Multiply4x4(TDW, TPD, TPW)
    vtk.vtkMatrix4x4.Multiply4x4(TWM, TPW, TDM)
    print(f'TDM {TDM}')

    #TSWD = getNode("Seg"+str(i+1+existing_segno)+"_TSWD") #Want the inverse
    #TDW_mat = vtk.vtkMatrix4x4()  #TDW = Transform Donor to World
    #TSWD.GetMatrixTransformFromParent(TDW_mat)

    #TSWM = getNode("Seg"+str(i+1+existing_segno)+"_TSWM") 
    #TWM_mat = vtk.vtkMatrix4x4() #TWM = Transform World to Mandible
    #TWM = TSWM.GetMatrixTransformToParent(TWM_mat) 

    #TDM = vtk.vtkTransform() #TDM = Transform Donor to Mandible (Concatenated TDW and TWM)
    #TDM.SetMatrix(TWM_mat)
    #TDM.Concatenate(TDW_mat)

    return TDM

def update_mandible_slice_plane(TPM, cut_plane, slice_to_update):
    #Normalize the normal
    n = [TPM.GetElement(0,2), TPM.GetElement(1,2), TPM.GetElement(2,2)]
    normal = n/np.linalg.norm(n)

    #Get and normalize the transverse
    t = np.cross([0,0,1], n)
    transverse = t/np.linalg.norm(t)

    #Get origin to set position
    #Need to apply correction to account for the fact the plane origin is not at the world origin (Transform from world to guide)
    o = [0,0,0]
    cut_plane.GetOrigin(o)
    #origin = [TPM.GetElement(0,3)+o[0], TPM.GetElement(1,3)+o[1], TPM.GetElement(2,3)+o[2]]
    origin = TPM.MultiplyPoint([o[0], o[1], o[2], 1])
    #origin = [TPM.GetElement(0,3), TPM.GetElement(1,3), TPM.GetElement(2,3)]
    #Update slice
    slice_to_update.SetSliceToRASByNTP(normal[0], normal[1], normal[2], 
                                       transverse[0], transverse[1], transverse[2], 
                                       origin[0], origin[1], origin[2], 0)
    print("Mandible slice plane updated")