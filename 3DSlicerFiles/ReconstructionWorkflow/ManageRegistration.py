import math
import os
import numpy as np
import math
from __main__ import vtk, qt, ctk, slicer
from slicer.util import VTKObservationMixin, getNode

import ManageSlicer as ms
import ManageUI as ui

class registration:
    def __init__():
        pass

    #MOVE TO GENERAL MANAGE SLICER
    def place_CT_fiducial(CT_fiducial_list, placeModePersistence=0):
        slicer.modules.markups.logic().SetActiveListID(CT_fiducial_list)
        slicer.modules.markups.logic().StartPlaceMode(placeModePersistence)
        #CT_fiducial_list.SetNthControlPointLocked(CT_fiducial_list.GetNumberOfFiducials()-1, 1)

    #MOVE TO GENERAL MANAGE SLICER
    def remove_CT_fiducials(CT_fiducial_list):
        slicer.modules.markups.logic().SetActiveListID(CT_fiducial_list)
        CT_fiducial_list.RemoveAllMarkups()
        print("CT Fiducials Removed")

    #MOVE TO GENERAL MANAGE SLICER
    def place_patient_fiducial(patient_fiducial_list, StylusTipToStylusRef):
        slicer.modules.markups.logic().SetActiveListID(patient_fiducial_list)
        fiducial_matrix = vtk.vtkMatrix4x4()
        StylusTipToStylusRef.GetMatrixTransformToWorld(fiducial_matrix)
        slicer.modules.markups.logic().AddFiducial(fiducial_matrix.GetElement(0, 3),
                                                   fiducial_matrix.GetElement(1, 3),
                                                   fiducial_matrix.GetElement(2, 3))

    #MOVE TO GENERAL MANAGE SLICER
    def remove_patient_fiducials(patient_fiducial_list, StylusRefToAnatomyRef):
        slicer.modules.markups.logic().SetActiveListID(patient_fiducial_list)
        patient_fiducial_list.RemoveAllMarkups()
        StylusRefToAnatomyRef.SetAndObserveTransformNodeID(None)
        print("Patient Fiducials Removed")
        #return fiducial count

    #MOVE TO GENERAL MANAGE SLICER
    def remove_surface_fiducials(surface_fiducials):
        slicer.modules.markups.logic().SetActiveListID(surface_fiducials)
        surface_fiducials.RemoveAllMarkups()
        # modelRefToModel.SetAndObserveTransformNodeID(None)
        print("Removed all surface fiducials")

    def run_registration(registration_node, to_fiducials, from_fiducials, ModelRefToModel, StylusRefToModelRef):
        registration_node.SetAndObserveFromFiducialListNodeId(from_fiducials.GetID())
        registration_node.SetAndObserveToFiducialListNodeId(to_fiducials.GetID())
        registration_node.SetOutputTransformNodeId(ModelRefToModel.GetID())
        registration_node.SetRegistrationModeToRigid()
        registration_node.SetUpdateModeToManual()
        slicer.modules.fiducialregistrationwizard.logic().UpdateCalibration(registration_node)
        registration_error = registration_node.GetCalibrationError()
        StylusRefToModelRef.SetAndObserveTransformNodeID(ModelRefToModel.GetID())
        return registration_error

    def delete_registration(StylusRefToModelRef):
        try:
            StylusRefToModelRef.SetAndObserveTransformNodeID(None)
            return True
        except slicer.util.MRMLNodeNotFoundException:
            return False

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

    def delete_surface_registration(modelRefToModel):
        try:
            modelRefToModel.SetAndObserveTransformNodeID(None)
            return True
        except slicer.util.MRMLNodeNotFoundException:
            return False

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


    ## Start timer for collecting surface points every n seconds
    #def onFibulaSurfStart(self):
    #    self.f_lastFid = 0
    #    self.f_timer = qt.QTimer()
    #    self.f_timer.timeout.connect(self.collectFibulaSurfFidsTimer)
    #    self.f_timer.setInterval(100)
    #    self.f_timer.start()
    #    print("Started")

    ## Link between logic to place fiducial and timer starter
    #def collectFibulaSurfFidsTimer(self):
    #    self.f_currentFid = self.f_lastFid + 1
    #    register.place_patient_fiducial(self.fibula_surface_fiducials, self.StylusTipToStylusRef)
    #    self.f_lastFid = self.f_currentFid
    #    self.FibulaSurfCount_Label.setText(f'Number of surface fiducials placed: {self.fibula_surface_fiducials.GetNumberOfFiducials()}')
    #    return self.f_currentFid

    ## Stop timer for collecting surface points every n seconds
    #def onFibulaSurfStop(self):
    #    self.f_timer.stop()
    #    print("Paused")
    #    self.FibulaSurfCount_Label.setText(f'Number of surface fiducials placed: {self.fibula_surface_fiducials.GetNumberOfFiducials()}')
