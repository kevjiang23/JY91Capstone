"""
Module: Main

Overview:
This module is the main entry point for this program. Used for detecting pose of multiple LentiMarks in
live video steams, with an optional calibration mode 
for registering different LentiMarks. The module leverages OpenCV for image 
processing, ArUco marker detection, and pose estimation, along with concurrent 
processing to efficiently handle real-time video streams.

To run the program in calibration mode, include the arguments "-c True", otherwise include "-c false", or
no additional arguments. An example of correctly calling the program in calibration mode is given below:
python3 Main.py -c True

"""
import argparse
import sys
import numpy as np
import cv2 as cv
from pypylon import pylon
from ArucoSetting import ARUCO_DICT
from ArucoSetting import Marker_Length
from PnPSolver import EstimatePoseSingleMarkers
from ReferencePointsDetectionV2 import RPDetectionImage
from Utility import *
from Refinement import getExistenceRegionFromImage
from VMPDetectionFxns import blackPeakDetection, warp
import concurrent.futures
import time
from datetime import datetime
import random

import streamTest # import the streamTest.py command function

# import slicer
#import vtk

# create a node for transformation matrix
#transformNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLTransformNode')

VMP_SLOPE = 0.345
    
def DetectLentiMarkTask(frame, given_id, calibrationFlag):
        """
        Detects the LentiMark in a given image frame using ArUco markers.
        
        Args:
            frame (np.array): The image frame where the detection is performed.
            given_id (int): The ID of the ArUco marker to detect.
            calibrationFlag (bool): Flag indicating if the system is in calibration mode.

        Returns:
            tuple: A tuple containing the output image, bird-view image, distance, center detection status, and the marker ID.
        """
        crop, masked_crop, backup_points, aruco_corners, translation_matrix, rotation_matrix, centerDetected = DetectLentiMarkFromImageObject(frame.copy(), given_id, detector, intrinsic_camera, distortion, calibrationFlag)
        clear_crop = crop.copy()

        if backup_points is not None:
            output, output_points = RPDetectionImage(crop, masked_crop)

            if len(output_points) == 4:
                img_birdview = warp(output_points,aruco_corners,frame.copy())
                distance = blackPeakDetection(img_birdview)

                return output, centerDetected, distance, translation_matrix, rotation_matrix
            elif len(backup_points) == 1:
                img_birdview = warp(backup_points,aruco_corners,frame.copy())
                distance = blackPeakDetection(img_birdview)

                for point in backup_points[0]:
                        cv.circle(clear_crop, (point[0], point[1]), 2, color=(0, 0, 255), thickness=2)

                return clear_crop, centerDetected, distance, translation_matrix, rotation_matrix
        return None, centerDetected, (0,0), None, None, None
        

    
def DetectLentiMarkFromImageObject(frame, given_id, detector, intrinsic_camera, distortion, calibrationFlag):
        """
        Detects the Lenti Mark from an image object using the given ArUco marker.

        Args:
            frame (np.array): The image frame for detection.
            given_id (int): The ID of the ArUco marker to detect.
            detector: The ArUco marker detector.
            intrinsic_camera (np.array): The intrinsic camera parameters.
            distortion (np.array): The distortion coefficients.
            calibrationFlag (bool): Flag indicating if the system is in calibration mode.

        Returns:
            tuple: A tuple containing the output image, masked output, backup coordinates, designated corners, center detection status, and marker ID.
        """

        centerDetected = False
        gray = cv.cvtColor(frame, cv.COLOR_RGB2GRAY)

        markerCorners, markerIds, _ = detector.detectMarkers(gray)

        if markerIds is not None:
            for i, id in enumerate(markerIds):
                if id == given_id or calibrationFlag == True:    
                    designated_corners =  [markerCorners[i]]
                    designated_id = np.array([markerIds[i]])

                    rvec, tvec, _ = EstimatePoseSingleMarkers(designated_corners, Marker_Length, intrinsic_camera, distortion)

                    cv.aruco.drawDetectedMarkers(frame, designated_corners, designated_id)
                    cv.drawFrameAxes(frame, intrinsic_camera,distortion, rvec, tvec, 10)

                    # from R-vector to R-matrix
                    R, _ = cv.Rodrigues(rvec)

                    if calibrationFlag == True:
                        # Printed Aids
                        xA,yA,zA,xP,yP,zP = "", "", "", "", "", ""

                        if(rot_params_rv(R)[0] < -0.5):
                            xA = "Angle Down"
                        elif(rot_params_rv(R)[0] > 0.5):
                            xA = "Angle Up"
                        else:
                            xA = "Good!"

                        if(rot_params_rv(R)[1] < -0.5):
                            yA = "Angle Right"
                        elif(rot_params_rv(R)[1] > 0.5):
                            yA = "Angle Left"
                        else:
                            yA = "Good!"

                        if(rot_params_rv(R)[2] > 1):
                            zA = "Turn Clockwise"
                        elif(rot_params_rv(R)[2] < -1):
                            zA = "Turn Counter-Clockwise"
                        else:
                            zA = "Good!"

                        if(tvec[0][0] < -1):
                            xP = "Move Left"
                        elif(tvec[0][0] > 1):
                            xP = "Move Right"
                        else:
                            xP = "Good!"

                        if(tvec[1][0] < -1):
                            yP = "Move Down"
                        elif(tvec[1][0] > 1):
                            yP = "Move Up"
                        else:
                            yP = "Good!"

                        if(tvec[2][0] > 100):
                            zP = "Move Closer"
                        else:
                            zP = "Good!"

                        print(f"{xA}, {yA}, {zA}, {xP}, {yP}, {zP}") 

                        if(abs(rot_params_rv(R)[0]) < 0.5 and abs(rot_params_rv(R)[1]) < 0.5 and abs(rot_params_rv(R)[2]) < 1 and abs(tvec[0][0]) < 1 and abs(tvec[1][0]) < 1 and tvec[2][0] < 100):
                            centerDetected = True
                            print("calibration is successful")
                    
                    # else:
                    #     print(f"World Coordinate of marker {given_id}: {(tvec[0][0], tvec[1][0], tvec[2][0])}")
                    #     print(f"Bryan Angle (XYZ) of marker {given_id}:  {rot_params_rv(R)}")

                    # Get existence region code
                    # fill imgArray with all existence regions
                    output, masked_output, coords_backup = getExistenceRegionFromImage(designated_corners[0], frame)
                    return output, masked_output, coords_backup, designated_corners, tvec, rot_params_rv(R), centerDetected
                        
        return frame, frame.copy(), None, None, None, None, centerDetected

def calculate_average_with_outlier_removal(values):
    """
    Calculates the average of a list of values after removing outliers.
    
    Args:
        values (list): A list of numeric values.
    
    Returns:
        float: The average of the values with outliers removed.
    """
    # Convert the list to a NumPy array for convenience
    values_array = np.array(values)
    
    # Calculate the mean and standard deviation
    mean = np.mean(values_array)
    std_dev = np.std(values_array)
    
    # Calculate Z-scores to identify outliers
    z_scores = (values_array - mean) / std_dev
    
    # Define a threshold for identifying outliers (e.g., Z-score > 2 or < -2)
    threshold = 2
    filtered_values = values_array[np.abs(z_scores) < threshold]
    
    # Recalculate mean and standard deviation after removing outliers
    filtered_mean = np.mean(filtered_values)
    filtered_std_dev = np.std(filtered_values)
    
    # Print the results
    print(f"Standard Deviation (after removing outliers): {filtered_std_dev}")
    print(f"Average (after removing outliers): {filtered_mean}")
    
    # Return the average
    return filtered_mean

def Main(id_list, mapping, calibrationFlag):
    """
    Main function that performs the pose detection of LentiMarks from video stream.
    
    Args:
        id_list (list): List of ArUco marker IDs to be detected.
        mapping (dict): Mapping of marker IDs to corresponding functions.
        calibrationFlag (bool): Flag indicating if the system is in calibration mode.
    
    Returns:
        None
    """
    distanace_dict = [(0,0) for id in id_list]
    # open webcam video stream

    #cap = cv.VideoCapture(0) #instead, we're gonna use basler camera:
    camera = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())

    # camera.Width.Value = 1920
    # camera.Height.Value = 1080
        
    camera.Open()
    camera.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
    
    #cap.set(cv.CAP_PROP_FRAME_WIDTH, 1920)
    #cap.set(cv.CAP_PROP_FRAME_HEIGHT, 1080)
    # width = int(cap.get(cv.CAP_PROP_FRAME_WIDTH))
    # height = int(cap.get(cv.CAP_PROP_FRAME_HEIGHT))

    distanceArrayX = []
    distanceArrayY = []

    with concurrent.futures.ProcessPoolExecutor(max_workers=8) as executor:
    # Start grabbing frames for analysis
        while camera.IsGrabbing():
        # Retrieve a frame from the Basler camera
            grab_result = camera.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
        
            if grab_result.GrabSucceeded():
                # Convert grab result to an OpenCV image (as numpy array)
                # original_frame = grab_result.Array
                original_frame = cv.cvtColor(grab_result.Array, cv.COLOR_GRAY2RGB)
                
                # Submit task to the process pool
                futures = [executor.submit(DetectLentiMarkTask, original_frame.copy(), id, calibrationFlag) for id in id_list]
            
                # Release the grab result after processing to free memory
                grab_result.Release()
            
                # Get results from futures
                processed_frames = []
                distance = []
                translation = []
                rotation = []
            
                for future in futures:
                    result = future.result()
                    processed_frames.append(result[0])
                    distance.append(result[2])
                    translation.append(result[3])
                    rotation.append(result[4])
            else:
                break

            # Code for VMP Calibration, triggers when marker is centered and calibrationFlag is active
            if(future.result()[1] == True and calibrationFlag == True):
                AngleMapID = future.result()[4][0]
                distanceArrayX.append(distance[0][0])
                distanceArrayY.append(distance[0][1])
                print(f"# of Successful Readings: {len(distanceArrayX)}")
                if(len(distanceArrayX) == 30):
                    b_x = calculate_average_with_outlier_removal(distanceArrayX)
                    b_y = calculate_average_with_outlier_removal(distanceArrayY)
                    lines = []
                    filename = "angleMap"

			        # Read the current content of the file
                    with open(filename, 'r') as file:
                        lines = file.readlines()

			        # Flag to check if the ID was found and replaced
                    id_found = False

			        # Process each line and check if the ID matches
                    for i in range(len(lines)):
                        line_data = lines[i].split()
                        
                        if int(line_data[0]) == AngleMapID:
                            lines[i] = str(AngleMapID) + " " + str(VMP_SLOPE) + " " + str(b_x) + " " + str(VMP_SLOPE) + " " + str(b_y) + "\n"
                            id_found = True
                            
                    if not id_found:
                        lines.append(str(AngleMapID) + " " + str(VMP_SLOPE) + " " + str(b_x) + " " + str(VMP_SLOPE) + " " + str(b_y) + "\n")

			        # Write the updated content back to the file
                    with open(filename, 'w') as file:
                         file.writelines(lines)
                    break

            distanace_dict = [(0.9 * bx + 0.1 * ax, 0.9 * by + 0.1 * ay) if (bx, by) != (0, 0) else (ax, ay) for (ax, ay), (bx, by) in zip(distanace_dict, distance)]

            if(calibrationFlag == False):
                for markers in range(len(id_list)):
                    marker_id = id_list[markers]
                    func = mapping.get(marker_id, None)
                    if(func is not None):
                        if distance[markers] == (0, 0):
                            print(f"marker: {marker_id}, Result: Not detected")
                        else:
                            result = func(distanace_dict[markers])
                            timestamp = datetime.now().strftime('%H:%M:%S.%f')[:-3]  # Format to include milliseconds
                            # print(f"Timestamp: {timestamp}, Marker: {marker_id}, Coordinate: {translation[markers][0][0], translation[markers][1][0], translation[markers][2][0]}, Angle: {(result[0], result[1], rotation[markers][2])}")
                            print(f"Timestamp: {timestamp}, Marker: {marker_id}, Coordinate: ({float(translation[markers][0][0])}, {float(translation[markers][1][0])}, {float(translation[markers][2][0])}), Angle: ({float(result[0])}, {float(result[1])}, {float(rotation[markers][2])})")

                            #streamTest.send_coors(10, 10, 10, 0, 0, 0)
                            streamTest.send_coors(translation[markers][0][0], translation[markers][1][0], translation[markers][2][0], result[0], result[1], rotation[markers][2], marker_id)

                            #create 4x4 matrix:
                            #tx, ty, tz = translation[markers][0][0], translation[markers][1][0], translation[markers][2][0]
                            #angle_x, angle_y, angle_z = result[0],result[1],rotation[markers][2]
                            #rotation_matrix = euler_to_rotation_matrix(angle_x, angle_y, angle_z)

                            # transformation_matrix = np.eye(4)
                            # transformation_matrix[:3, :3] = rotation_matrix
                            # transformation_matrix[:3, 3] = [tx, ty, tz]
                            
                            # # create vtk 4x4 matrix and set it to calculated matrix
                            # vtk_matrix = vtk.vtkMatrix4x4()
                            # transformNode.SetMatrixTransformToParent(vtk_matrix)
                            # print(transformation_matrix)
                    else:
                        print(f"Can't find a valid mapping for marker: {marker_id}")
                
            result = imageMerger(processed_frames)
            if(result is None):
                cv.imshow('Processed Frame', original_frame)
            else:
                cv.imshow('Processed Frame', result)

            if cv.waitKey(1) & 0xFF == ord('q'):
                    break
    # When everything done, release the capture
    #cap.release() #replaced with below code for basler
    cv.destroyAllWindows()

    camera.StopGrabbing()
    camera.Close()



# verify that the supplied ArUCo tag exists and is supported by
# OpenCV
if ARUCO_DICT.get("DICT_4X4_1000", None) is None: #args["type"]
    print("[INFO] ArUCo tag of '{}' is not supported".format("DICT_4X4_1000")) #args["type"]
    sys.exit(0)

# load the ArUCo dictionary, grab the ArUCo parameters, and detect
# the markers
arucoDict = cv.aruco.getPredefinedDictionary(ARUCO_DICT["DICT_4X4_1000"])  #args["type"]
arucoParams = cv.aruco.DetectorParameters()
arucoParams.adaptiveThreshWinSizeMin = 3
arucoParams.adaptiveThreshWinSizeMax = 53
arucoParams.adaptiveThreshWinSizeStep = 5
arucoParams.cornerRefinementMethod = cv.aruco.CORNER_REFINE_SUBPIX
detector = cv.aruco.ArucoDetector(arucoDict, arucoParams)

##########################################################################################
# Set parameters of the camera
intrinsic_camera, distortion = GetCameraParameters("calibration.pckl") #args["parameter"]
##########################################################################################

if(__name__ == '__main__'):
    ap = argparse.ArgumentParser()
    ap.add_argument("-c", "--calibrationFlag", type=str,
		default="False",
		help="used to confirm the angle mapping process")
    args = vars(ap.parse_args())
        
    id_list = readConfig("config")
    mapping = readMap("angleMap")

    if(args["calibrationFlag"] == "True"):
        Main(id_list, mapping, True)
    else:
        Main(id_list, mapping, False)
