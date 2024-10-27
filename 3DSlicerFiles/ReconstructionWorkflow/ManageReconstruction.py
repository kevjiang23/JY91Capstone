import math
import os
import numpy as np
import math
from __main__ import vtk, qt, ctk, slicer
from slicer.util import VTKObservationMixin, getNode

import ManageSlicer as ms
import ManageUI as ui
try: 
    import jpype
    import jpype.imports 
    from jpype.types import *
except ImportError as e: 
    slicer.util.pip_install('JPype1')
    import jpype
    import jpype.imports 
    from jpype.types import *

class resection:
    def __init__():
        pass

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

    def update_mandible_slice_plane(TDM, plane, slice_to_update):
        #Normalize the normal
        n = [0,0,0]
        plane.GetNormal(n)
        n_w = TDM.MultiplyPoint([n[0], n[1], n[2], 0])
        print(f'n_w: {n_w}')
        normal = n_w/np.linalg.norm(n_w)

        #Get and normalize the transverse
        t = np.cross([0, 0, 1], n_w[:-1])
        transverse = t/np.linalg.norm(t)

        #Get origin to set position
        o = [0,0,0]
        plane.GetOrigin(o)
        origin = TDM.MultiplyPoint([o[0], o[1], o[2], 1])
        print(f'origin {origin}')
        #Check: Should normal be positive or negative?     
        slice_to_update.SetSliceToRASByNTP(-normal[0], -normal[1], -normal[2], 
                                           transverse[0], transverse[1], transverse[2], 
                                           origin[0], origin[1], origin[2], 0)
        print("Mandible slice plane updated")

class reconstruction:
    def __init__():
        pass

    def connect_JVM():
        if jpype.isJVMStarted():
            genVSP = jpype.JClass("artisynth.istar.Mel.GenerateVSP")()
            print("JVM is already running.")
        else:
            user_path = os.path.expanduser('~')
            print(f'User path: {user_path}')
            jpype.startJVM(classpath=[user_path+"\\git\\artisynth_istar\\classes", 
                                      user_path+"\\git\\artisynth_core\\classes", 
                                      user_path+"\\git\\artisynth_core\\lib\\*"]) 
            print (f'JVM path: {jpype.getDefaultJVMPath()}')
            genVSP = jpype.JClass("artisynth.istar.Mel.GenerateVSP")()
        return genVSP

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

    def display_RDP(RDP_lines, recalc=""):
        rdp_markups = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsFiducialNode', 'RDPPoints'+recalc)
        slicer.modules.markups.logic().SetActiveListID(rdp_markups)
        for i in range(RDP_lines.size()):
            slicer.modules.markups.logic().AddFiducial(RDP_lines[i].x, RDP_lines[i].y, RDP_lines[i].z)
        return rdp_markups

    def create_RDP_model(RDP_lines, recalc=""):
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
        RDP_model.SetName("RDP"+recalc)
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
                left_vtkplane, right_vtkplane, fibfid, TCW_node, left_to_right=False, recalc=""):
        #Set start point for VSP using the fib fid node 
        ras = vtk.vtkVector3d(0,0,0)
        index = fibfid.GetNumberOfControlPoints()-1
        fibfid.GetNthControlPointPosition(index, ras)
        start_point = JVM.setPoint3d(ras[0], ras[1], ras[2])

        #Set cut planes 
        left_plane = reconstruction.set_resection_plane(JVM, left_vtkplane)
        right_plane = reconstruction.set_resection_plane(JVM, right_vtkplane)

        #Compute RDP
        RDP = reconstruction.compute_RDP(JVM, contour, left_plane, right_plane, min_seg_length, max_segs)
        RDP_markups = reconstruction.display_RDP(RDP, recalc)
        RDP_model = reconstruction.create_RDP_model(RDP, recalc)
        #return RDP
        #Get path to mandible and clipped fibula models
        clipped_fibula = os.path.dirname(fibula_path.GetText())+"\\ClippedFibula_Donor.stl"
        mandible = mandible_path.GetText()

        #Get TCW 
        TCW = reconstruction.vtkmatrix4x4_to_rigid3d(JVM, TCW_node)

        #Calculate VSP 
        fibula_segments = JVM.findDonorCutPlanes(seg_separation, min_seg_length, max_segs,
                                                 RDP, clipped_fibula, mandible, left_plane, right_plane,
                                                 start_point, TCW, left_to_right)
        return fibula_segments

    def generate_segment_transforms(JVM, segment, segno=0, recalc=""):
        number_of_segments = ui.import_node("NumOfSegs"+recalc, "vtkMRMLTextNode")
        number_of_segments.SetText(str(segment.size() + segno))
        for i in range(segment.size()):
            #Segment {i} TPS0
            print(f'Segment {i + 1 + segno} TPS0: {JVM.getTPS0(segment[i])}')
            TPS0 = JVM.getTPS0_Array(segment[i])
            ms.arraylist_to_transform(TPS0, "TPS0Seg"+str(i+1+segno)+recalc)
            #Segment {i} TPS1
            print(f'Segment {i + 1 + segno} TPS1: {JVM.getTPS1(segment[i])}')
            TPS1 = JVM.getTPS1_Array(segment[i])
            ms.arraylist_to_transform(TPS1, "TPS1Seg"+str(i+1+segno)+recalc)
            #Segment {i} TSW_M
            print(f'Segment {i + 1+ segno} TSW_M: {JVM.getTSWM(segment[i])}')
            TSWM = JVM.getTSWM_Array(segment[i])
            ms.arraylist_to_transform(TSWM, "TSWMSeg"+str(i+1+segno)+recalc)
            #Segment {i} TSW_D
            print(f'Segment {i + 1+ segno} TSW_D: {JVM.getTSWD(segment[i])}')
            TSWD = JVM.getTSWD_Array(segment[i])
            ms.arraylist_to_transform(TSWD, "TSWDSeg"+str(i+1+segno)+recalc)

    def create_donor_segments(clipped_fibula, segment_size, existing_segno=0, recalc=""):
        for i in range(segment_size):
            #Get nodes and set transform hierarchy 
            TPS0 = getNode("TPS0Seg"+str(i+1+existing_segno)+recalc)
            TPS1 = getNode("TPS1Seg"+str(i+1+existing_segno)+recalc)
            TSWD = getNode("TSWDSeg"+str(i+1+existing_segno)+recalc)
            TPS0.SetAndObserveTransformNodeID(TSWD.GetID())
            TPS1.SetAndObserveTransformNodeID(TSWD.GetID())

            plane1 = ms.get_vtkplane_from_transform(TPS0)
            plane2 = ms.get_vtkplane_from_transform(TPS1)

            segment_planes = vtk.vtkPlaneCollection()
            segment_planes.AddItem(plane1)
            segment_planes.AddItem(plane2)

            clipped_polydata = ms.clip_polydata(segment_planes, clipped_fibula.GetPolyData())
            segD = ms.create_model(clipped_polydata, "VSPFibSeg"+ str(i+1+existing_segno)+recalc, [1, (i+existing_segno)/2, 0])
            #segD.GetModelDisplayNode().SetColor(1, i*1.0/(segment_size - 1), 0)
            if recalc != "":
                segment_length_fids = ui.import_node('VSPSegEndpoints'+recalc, 'vtkMRMLMarkupsFiducialNode')
                slicer.modules.markups.logic().SetActiveListID(segment_length_fids)
                VSP_endpoints = getNode('VSPSegEndpoints')
                for i in range(existing_segno*2):
                    fid = [0,0,0] 
                    VSP_endpoints.GetNthControlPointPosition(i, fid)
                    slicer.modules.markups.logic().AddFiducial(fid[0], fid[1], fid[2])
            reconstruction.get_segment_length(plane1, clipped_fibula, recalc)
            reconstruction.get_segment_length(plane2, clipped_fibula, recalc)

    def create_mandible_segments(segment_size, existing_segno=0, recalc=""):
        for i in range(segment_size): #segment.size()
            segD_polydata = getNode("VSPFibSeg"+ str(i+1+existing_segno)+recalc).GetPolyData()

            TSWD = getNode("TSWDSeg"+str(i+1+existing_segno)+recalc) #Want the inverse
            TDW_mat = vtk.vtkMatrix4x4()  #TDW = Transform Donor to World
            TSWD.GetMatrixTransformFromParent(TDW_mat)

            TSWM = getNode("TSWMSeg"+str(i+1+existing_segno)+recalc) 
            TWM_mat = vtk.vtkMatrix4x4() #TWM = Transform World to Mandible
            TWM = TSWM.GetMatrixTransformToParent(TWM_mat) 

            TDM = vtk.vtkTransform() #TDM = Transform Donor to Mandible (Concatenated TDW and TWM)
            TDM.SetMatrix(TWM_mat)
            TDM.Concatenate(TDW_mat)

            transform_filter = vtk.vtkTransformPolyDataFilter()
            segM_polydata = ms.transform_polydata(transform_filter, segD_polydata, TDM)
        
            segM = ms.create_model(segM_polydata, "VSPMandSeg"+ str(i+1+existing_segno)+recalc, [1, (i+existing_segno)/2, 0])

    def get_segment_length(plane, model, recalc=""):
        contour = ms.get_intersection_contour(plane, model)
        #intersection = slicer.vtkMRMLModelNode()
        #intersection.SetAndObservePolyData(contour)
        #intersection.SetName('TargetContour'+str(segment_number))
        #slicer.mrmlScene.AddNode(intersection)
        centre = ms.get_centroid(contour)
        segment_length_fids = ui.import_node('VSPSegEndpoints'+recalc, 'vtkMRMLMarkupsFiducialNode')
        slicer.modules.markups.logic().SetActiveListID(segment_length_fids)
        slicer.modules.markups.logic().AddFiducial(centre[0], centre[1], centre[2])
        print(f'Intersection contour centre: {centre}')

    def create_cut_plane_model(number_of_segments, existing_segno=0, recalc=""):
        for i in range(number_of_segments):
            try:
                CutPlane0 = getNode('Plane0Seg'+str(i+1+existing_segno)+recalc)
                slicer.mrmlScene.RemoveNode(CutPlane0)
            except slicer.util.MRMLNodeNotFoundException: 
                print("No plane nodes were removed")
            CutPlane0 = ms.create_cut_plane('Plane0Seg'+str(i+1+existing_segno)+recalc, 0)
            CutPlane0.SetAndObserveTransformNodeID(getNode('TPS0Seg'+str(i+1+existing_segno)+recalc).GetID())
            CutPlane0.SetDisplayVisibility(0)
            
            if recalc=="":
                cut0view1 = reconstruction.create_view1(str(i+1+existing_segno)+"Cut0View1")
                cut0view2 = reconstruction.create_view2(str(i+1+existing_segno)+"Cut0View2")
                cut0view3 = reconstruction.create_view3(str(i+1+existing_segno)+"Cut0View3")

            # cut0view1 = reconstruction.create_view1(str(i+1+existing_segno)+"Cut0View1")
            getNode(str(i+1+existing_segno)+'Cut0View1').SetAndObserveTransformNodeID(getNode('TPS0Seg'+str(i+1+existing_segno)+recalc).GetID())
            # cut0view2 = reconstruction.create_view2(str(i+1+existing_segno)+"Cut0View2")
            getNode(str(i+1+existing_segno)+'Cut0View2').SetAndObserveTransformNodeID(getNode('TPS0Seg'+str(i+1+existing_segno)+recalc).GetID())
            # cut0view3 = reconstruction.create_view3(str(i+1+existing_segno)+"Cut0View3")
            getNode(str(i+1+existing_segno)+'Cut0View3').SetAndObserveTransformNodeID(getNode('TPS0Seg'+str(i+1+existing_segno)+recalc).GetID())
            
            try: 
                CutPlane1 = getNode('Plane1Seg'+str(i+1+existing_segno)+recalc)
                slicer.mrmlScene.RemoveNode(CutPlane1)
            except slicer.util.MRMLNodeNotFoundException: 
                print("No plane nodes were removed")
            CutPlane1 = ms.create_cut_plane('Plane1Seg'+str(i+1+existing_segno)+recalc, 0)
            CutPlane1.SetAndObserveTransformNodeID(getNode('TPS1Seg'+str(i+1+existing_segno)+recalc).GetID())
            CutPlane1.SetDisplayVisibility(0)
            
            if recalc=="":
                cut1view1 = reconstruction.create_view1(str(i+1+existing_segno)+"Cut1View1")
                cut1view2 = reconstruction.create_view2(str(i+1+existing_segno)+"Cut1View2")
                cut1view3 = reconstruction.create_view3(str(i+1+existing_segno)+"Cut1View3")            

            #cut1view1 = reconstruction.create_view1(str(i+1+existing_segno)+"Cut1View1")
            getNode(str(i+1+existing_segno)+'Cut1View1').SetAndObserveTransformNodeID(getNode('TPS1Seg'+str(i+1+existing_segno)+recalc).GetID())
            #cut1view2 = reconstruction.create_view2(str(i+1+existing_segno)+"Cut1View2")
            getNode(str(i+1+existing_segno)+'Cut1View2').SetAndObserveTransformNodeID(getNode('TPS1Seg'+str(i+1+existing_segno)+recalc).GetID())
            #cut1view3 = reconstruction.create_view3(str(i+1+existing_segno)+"Cut1View3")
            getNode(str(i+1+existing_segno)+'Cut1View3').SetAndObserveTransformNodeID(getNode('TPS1Seg'+str(i+1+existing_segno)+recalc).GetID())

    def create_view1(transform_name):
        view1_matrix = vtk.vtkMatrix4x4()
        view1_matrix.Zero()
        view1_matrix.SetElement(0, 2, -1)
        view1_matrix.SetElement(1, 1, 1)
        view1_matrix.SetElement(2, 0, 1)
        view1_matrix.SetElement(3, 3, 1)
        view1_transform = ui.create_linear_transform(view1_matrix, transform_name)
        return view1_transform

    def create_view2(transform_name):
        view2_matrix = vtk.vtkMatrix4x4()
        view2_matrix.Zero()
        view2_matrix.SetElement(0, 0, 1)
        view2_matrix.SetElement(1, 2, -1)
        view2_matrix.SetElement(2, 1, 1)
        view2_matrix.SetElement(3, 3, 1)
        view2_transform = ui.create_linear_transform(view2_matrix, transform_name)
        return view2_transform

    def create_view3(transform_name):
        view3_matrix = vtk.vtkMatrix4x4()
        view3_transform = ui.create_linear_transform(view3_matrix, transform_name)
        return view3_transform

    def transform_donor_to_mandible(TSWD, TSWM):
        #Transform cut plane from donor space to mandible space 
        TDW = vtk.vtkMatrix4x4()    #transform donor to world
        TSWD.GetMatrixTransformFromParent(TDW)
        print(f'TDW {TDW}')

        TWM = vtk.vtkMatrix4x4()    #transform world to mandible
        TSWM.GetMatrixTransformToParent(TWM)
        print(f'TWM {TWM}')

        TDM = vtk.vtkMatrix4x4()
        vtk.vtkMatrix4x4.Multiply4x4(TWM, TDW, TDM)
        print(f'TDM {TDM}')
        return TDM
