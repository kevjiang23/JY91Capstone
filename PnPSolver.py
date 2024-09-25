import numpy as np
import cv2 as cv

def EstimatePoseSingleMarkers(corners, marker_size, mtx, distortion):
    '''
    This will estimate the rvec and tvec for each of the marker corners detected by:
    corners, ids, rejectedImgPoints = detector.detectMarkers(image)
    corners - is an array of detected corners for each detected marker in the image
    marker_size - is the size of the detected markers. Normally, unit is millimeters. 
    mtx - is the camera matrix
    distortion - is the camera distortion matrix
    RETURN list of rvecs, tvecs, and trash
    '''
    object_points = np.array([[-marker_size / 2, -marker_size / 2, 0],
                              [marker_size / 2, -marker_size / 2, 0],
                              [marker_size / 2, marker_size / 2, 0],
                              [-marker_size / 2, marker_size / 2, 0]], dtype=np.float32)
    
    # corners w.r.t carmera coordinate 
    # object_points w.r.t object coordinate 
    _, R, T = cv.solvePnP(object_points, corners[0], mtx, distortion, False, cv.SOLVEPNP_IPPE_SQUARE)
    return R, T, object_points