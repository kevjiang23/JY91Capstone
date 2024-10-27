import os
import logging
import numpy as np
import math
import time
from __main__ import vtk, slicer

import ManageUI as ui

#Slicer operations
def get_centroid(polydata):
    center_of_mass = vtk.vtkCenterOfMass()
    center_of_mass.SetInputData(polydata)
    center_of_mass.Update()
    return center_of_mass.GetCenter()

def get_intersection_contour(plane, model):
    cutter = vtk.vtkCutter()
    cutter.SetInputData(model.GetPolyData())
    cutter.SetCutFunction(plane)
    cutter.Update()
    return cutter.GetOutput()

#Matrix operations
def vtkmatrix4x4_to_numpy(matrix):
    """
    Copies the elements of a vtkMatrix4x4 into a numpy array.
    :param matrix: The matrix to be copied into an array.
    :type matrix: vtk.vtkMatrix4x4
    :rtype: numpy.ndarray
    """
    m = np.ones((4, 4))
    for i in range(4):
        for j in range(4):
            m[i, j] = matrix.GetElement(i,j)
    return m

def vtkmatrix3x3_to_numpy(matrix):
    """
    Copies the elements of a vtkMatrix4x4 into a numpy array.
    :param matrix: The matrix to be copied into an array.
    :type matrix: vtk.vtkMatrix4x4
    :rtype: numpy.ndarray
    """
    m = np.ones((3, 3))
    for i in range(3):
        for j in range(3):
            m[i, j] = matrix.GetElement(i,j)
    return m

def numpy4x4_to_vtk(mat):
    matrix = vtk.vtkMatrix4x4()
    for i in range(4): 
        for j in range(4):
            matrix.SetElement(i, j, mat[i][j])
    return matrix

def arraylist_to_numpy(arr_list):
    numpy4x4 = np.array([[arr_list[0], arr_list[1], arr_list[2], arr_list[3]], 
                       [arr_list[4], arr_list[5], arr_list[6], arr_list[7]], 
                       [arr_list[8], arr_list[9], arr_list[10], arr_list[11]], 
                       [arr_list[12], arr_list[13], arr_list[14], arr_list[15]]])
    return numpy4x4

def multiply_vtkmatrix(A, B, AxB):
    vtk.vtkMatrix4x4.Multiply4x4(A, B, AxB)
    return AxB

def arraylist_to_transform(arraylist, name):
    arr_np = arraylist_to_numpy(arraylist)
    arr_vtk = numpy4x4_to_vtk(arr_np)
    ui.create_linear_transform(arr_vtk, name)

def R_to_axis_angle(matrix):
    """Convert the rotation matrix into the axis-angle notation.
    Conversion equations
    ====================
    From Wikipedia (http://en.wikipedia.org/wiki/Rotation_matrix), the conversion is given by::
        x = Qzy-Qyz
        y = Qxz-Qzx
        z = Qyx-Qxy
        r = hypot(x,hypot(y,z))
        t = Qxx+Qyy+Qzz
        theta = atan2(r,t-1)
    @param matrix:  The 3x3 rotation matrix to update.
    @type matrix:   3x3 numpy array
    @return:    The 3D rotation axis and angle.
    @rtype:     numpy 3D rank-1 array, float
    """
    #Axes 
    axis = np.zeros(3, np.float64)
    axis[0] = matrix[2, 1] - matrix[1, 2]
    axis[1] = matrix[0, 2] - matrix[2, 0]
    axis[2] = matrix[1, 0] - matrix[0, 1]

    #Angle
    r = np.hypot(axis[0], np.hypot(axis[1], axis[2]))
    t = matrix[0,0] + matrix[1,1] + matrix[2,2]
    theta = np.arctan2(r, t-1)

    #Normalise the axis
    axis = axis / r

    #Return the data
    return axis, theta

def get_rotation_euler(matrix):
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

#Model and polydata operations
def fiducials_to_polydata(fiducials, polydata):
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

def transform_polydata(transform_filter, input_data, transform):
    transform_filter.SetInputData(input_data)
    transform_filter.SetTransform(transform)
    transform_filter.Update()
    return transform_filter.GetOutput()

def harden_transform_polydata(model):
    #Get transform to world coordinates
    parent_matrix = vtk.vtkMatrix4x4()
    model.GetParentTransformNode().GetMatrixTransformToWorld(parent_matrix)
    transform = vtk.vtkTransform()
    transform.SetMatrix(parent_matrix)
    #Apply transform to polydata
    polydata = model.GetPolyData()
    transformed_polydata = transform_polydata(vtk.vtkTransformPolyDataFilter(), polydata, transform)
    return transformed_polydata

def clean_polydata(polydata):
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

def clip_polydata(plane_collection, polydata):
    clipper = vtk.vtkClipClosedSurface()
    clipper.SetClippingPlanes(plane_collection)
    clipper.SetInputData(polydata)     
    clipper.SetGenerateFaces(1)
    clipper.Update()
    return clipper.GetOutput()

def polydata_clean(polydata):
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

def export_mesh(polydata, filepath):
    writer = vtk.vtkSTLWriter()
    writer.SetInputData(polydata)
    writer.SetFileName(filepath)
    writer.Update()

def create_cut_plane(name, visibility=1):
    cut_plane = slicer.modules.createmodels.logic().CreateCube(1, 100, 100)
    transform = vtk.vtkTransform()
    transform.RotateY(90)
    cut_plane.ApplyTransform(transform)
    cut_plane.SetName(name)
    cut_plane.SetDisplayVisibility(visibility)
    #slicer.mrmlScene.AddNode(cut_plane)
    return cut_plane

def create_model(polydata, name="Model", color=[0,0.33,0]):
    model = slicer.vtkMRMLModelNode()
    slicer.mrmlScene.AddNode(model)
    model.SetName(name)
    model.SetAndObservePolyData(polydata)
    if model.GetModelDisplayNode() is None: 
        modelDisplay = slicer.vtkMRMLModelDisplayNode()
        modelDisplay.SetBackfaceCulling(0)
        modelDisplay.SetColor(color)
        modelDisplay.SetScene(slicer.mrmlScene)
        modelDisplay.SetScalarVisibility(1)
        slicer.mrmlScene.AddNode(modelDisplay)
        model.SetAndObserveDisplayNodeID(modelDisplay.GetID())
    model.GetModelDisplayNode().SetColor(color)
    model.GetModelDisplayNode().VisibilityOn()
    return model

#Transform matrix operations
def get_transformation_matrix(initial_polydata, target_polydata, landmark_transform):
    #The landmark transform input is just an instance of vtk.vtkLandmarkTransform()
    landmark_transform.SetSourceLandmarks(initial_polydata.GetPoints())
    landmark_transform.SetTargetLandmarks(target_polydata.GetPoints())
    landmark_transform.SetModeToRigidBody()
    landmark_transform.Update()
    return landmark_transform.GetMatrix()

def get_transformation_matrix_with_centroids(initial_polydata, target_polydata, landmark_transform):
    initial_centroid = get_centroid(initial_polydata)
    target_centroid = get_centroid(target_polydata)
    translation = [target_centroid[0] - initial_centroid[0], target_centroid[1] - initial_centroid[1], target_centroid[2] - initial_centroid[2]]

    landmark_transform.SetSourceLandmarks(initial_polydata.GetPoints())
    landmark_transform.SetTargetLandmarks(target_polydata.GetPoints())
    landmark_transform.SetModeToRigidBody()
    landmark_transform.Update()

    transform_matrix = landmark_transform.GetMatrix()
    transform_matrix.SetElement(0, 3, translation[0])
    transform_matrix.SetElement(1, 3, translation[1])
    transform_matrix.SetElement(2, 3, translation[2])
    return transform_matrix

def isolate_rotation_matrix(transformation_matrix):
    rotation_matrix = transformation_matrix[:-1,:-1]
    return rotation_matrix

def generate_translation_matrix(translation_vector):
    translation_matrix = vtk.vtkMatrix4x4().Identity()
    translation_vector.append(1)
    for i in range(0, 4):
        translation_matrix.SetElement(i, 3, translation_vector[i])
    return translation_matrix

def generate_coordinate_matrix(model, rotation=vtk.vtkMatrix4x4()):
    model_centroid = get_centroid(model.GetPolyData())
    coordinate_matrix = rotation
    coordinate_matrix.SetElement(0, 3, model_centroid[0])
    coordinate_matrix.SetElement(1, 3, model_centroid[1])
    coordinate_matrix.SetElement(2, 3, model_centroid[2])
    return coordinate_matrix

#Slice plane operations
def update_slice_plane(fiducials_list, slice_node, param1=None, param2=None):
    nOfFiduciallPoints = fiducials_list.GetNumberOfFiducials()
    points = np.zeros([3,nOfFiduciallPoints])
    for i in range(0, nOfFiduciallPoints):
        fiducials_list.GetNthFiducialPosition(i, points[:,i])
    planePosition = points.mean(axis=1)
    planeNormal = np.cross(points[:,1] - points[:,0], points[:,2] - points[:,0])
    planeX = points[:,1] - points[:,0]
    slice_node.SetSliceToRASByNTP(planeNormal[0], planeNormal[1], planeNormal[2],
                                 planeX[0], planeX[1], planeX[2],
                                 planePosition[0], planePosition[1], planePosition[2], 0)

def setSlicePoseFromSliceNormalAndPosition(sliceNode, sliceNormal, slicePosition, defaultViewUpDirection=None, backupViewRightDirection=None):
    """
    Set slice pose from the provided plane normal and position. View up direction is determined automatically,
    to make view up point towards defaultViewUpDirection.
    :param defaultViewUpDirection Slice view will be spinned in-plane to match point approximately this up direction. Default: patient superior.
    :param backupViewRightDirection Slice view will be spinned in-plane to match point approximately this right direction
        if defaultViewUpDirection is too similar to sliceNormal. Default: patient left.
    """
    # Fix up input directions
    if defaultViewUpDirection is None:
        defaultViewUpDirection = [0,0,1]
    if backupViewRightDirection is None:
        backupViewRightDirection = [-1,0,0]
    if sliceNormal[1]>=0:
        sliceNormalStandardized = sliceNormal
    else:
        sliceNormalStandardized = [-sliceNormal[0], -sliceNormal[1], -sliceNormal[2]]
    # Compute slice axes
    sliceNormalViewUpAngle = vtk.vtkMath.AngleBetweenVectors(sliceNormalStandardized, defaultViewUpDirection)
    angleTooSmallThresholdRad = 0.25 # about 15 degrees
    if sliceNormalViewUpAngle > angleTooSmallThresholdRad and sliceNormalViewUpAngle < vtk.vtkMath.Pi() - angleTooSmallThresholdRad:
        viewUpDirection = defaultViewUpDirection
        sliceAxisY = viewUpDirection
        sliceAxisX = [0, 0, 0]
        vtk.vtkMath.Cross(sliceAxisY, sliceNormalStandardized, sliceAxisX)
    else:
        sliceAxisX = backupViewRightDirection
    # Set slice axes
    sliceNode.SetSliceToRASByNTP(sliceNormalStandardized[0], sliceNormalStandardized[1], sliceNormalStandardized[2],
        sliceAxisX[0], sliceAxisX[1], sliceAxisX[2],
        slicePosition[0], slicePosition[1], slicePosition[2], 0)

def makePlaneMarkupFromFiducial(FNode, planeName):
    """Create MarkupsPlane using first three control points of the input fiducial node.
    source: https://discourse.slicer.org/t/defining-a-new-coordinate-system-using-markups-plane-node/19726/2
    """
    if FNode.GetNumberOfControlPoints()<3:
      logging.warning('Not enough control points to create plane markup!')
      return
    planeNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsPlaneNode', planeName)
    for cpIdx in range(3):
      pos = vtk.vtkVector3d()
      FNode.GetNthControlPointPositionWorld(cpIdx, pos)
      planeNode.AddControlPointWorld(pos)

    return planeNode


def get_vtkplane_from_slice(slice):
    mat = slice.GetSliceToRAS()
    m = np.array([[mat.GetElement(0, 0), mat.GetElement(0, 1), mat.GetElement(0, 2), mat.GetElement(0, 3)],
                  [mat.GetElement(1, 0), mat.GetElement(1, 1), mat.GetElement(1, 2), mat.GetElement(1, 3)],
                  [mat.GetElement(2, 0), mat.GetElement(2, 1), mat.GetElement(2, 2), mat.GetElement(2, 3)],
                  [mat.GetElement(3, 0), mat.GetElement(3, 1), mat.GetElement(3, 2), mat.GetElement(3, 3)]])
    nvec = np.array((0, 0, 1, 0))
    pvec = np.array((0, 0, 0, 1))
    normal = np.dot(m, nvec)
    point = np.dot(m, pvec)
    plane = vtk.vtkPlane()
    plane.SetNormal(normal[0], normal[1], normal[2])
    plane.SetOrigin(point[0], point[1], point[2])
    return plane

#Create vtk plane from transform 
def get_vtkplane_from_transform(TPSX):
    plane = vtk.vtkPlane()
    transform = vtk.vtkMatrix4x4()
    TPSX.GetMatrixTransformToWorld(transform)
    normal = [0,0,0,0]
    transform.MultiplyPoint([0,0,1,0], normal)
    origin = [0,0,0,0]
    transform.MultiplyPoint([0,0,0,1], origin)
    plane.SetNormal(normal[:-1])
    plane.SetOrigin(origin[:-1])
    return plane

#Create vtk plane from plane markups node (CutPlane1 and CutPlane2)
def get_vtkplane_from_markup_plane(markups_plane, plane_no):
    plane = vtk.vtkPlane()
    normal = [0,0,0]
    origin = [0,0,0]
    markups_plane.GetNormalWorld(normal)
    markups_plane.GetOriginWorld(origin)
    if plane_no == 1 and normal[2] > 0:
        plane.SetNormal(-normal[0], -normal[1], -normal[2])
    elif plane_no == 2 and normal[2] < 0:
        plane.SetNormal(-normal[0], -normal[1], -normal[2])
    else:
        plane.SetNormal(normal)
    plane.SetOrigin(origin)
    return plane

def get_normal_from_slice(slice):
    nvec = np.array((0, 0, 1, 0))
    pvec = np.array((0, 0, 0, 1))
    mat = slice.GetSliceToRAS()
    m = vtkMatrixToNumpy4x4(mat)
    normal = np.dot(m, nvec)
    point = np.dot(m, pvec)
    # d = normal[0] * point[0] + normal[1] * point[1] + normal[2] * point[2]
    normal = normalize(normal)
    return normal[:3], point[:3]

#Manage Scene 
def save_scene(file_path, file_name="Scene"):
    name = file_name + "_" + time.strftime("%Y%m%d") + ".mrb"
    dir = file_path + "\\" + name
    if not os.access(os.path.dirname(dir), os.F_OK):
        os.makedirs(os.path.dirname(dir))
    if slicer.util.saveScene(dir):
        logging.info("Scene saved to: {0}".format(dir))
    else:
        logging.error("Scene saving failed.")

def runCalcDice(self, plan, actual):
    slicer.util.selectModule(slicer.modules.segmentcomparison.name)
    # slicer.util.selectModule(slicer.modules.calculateresults.name)
    segComp = getNode('SegmentComparison')
    segComp.SetAndObserveReferenceSegmentationNode(plan)
    segComp.SetAndObserveCompareSegmentationNode(actual)
    slicer.modules.segmentcomparison.logic().ComputeDiceStatistics(segComp)
    slicer.modules.segmentcomparison.logic().ComputeHausdorffDistances(segComp)
    dice = segComp.GetDiceCoefficient()
    hof = segComp.GetPercent95HausdorffDistanceForVolumeMm()
    return dice, hof