"""
Module: VMPDetectionFxns.py

Overview:
This module provides the supporting functions necessary
for analyzing and extractring black peak position from 
VMP rectangles of the LentiMark.

"""

import cv2 as cv
import numpy as np
import math
import matplotlib.pyplot as plt

""" 
PARAMS:                                                                                        
  anchoring points - np array of shape (1,4,2) contianing anchoring points of the lentimark.   
  These points may be in the incorrect order for the perspective transform,                    
  so we reorder them in this function. If shape is incorrect the program will return NULL.    
                                                                                               
  lentimark_img - image containing lentimark.                                                  
RETURNS:                                                                                       
  img_birdseye - birdseye view image of lentimark                                             
                                                                                              
"""
def warp(anchoring_points,marker_corners,lentimark_img):
    marker_corners = np.array(marker_corners[0]).reshape(4, 2)
    anchoring_points = np.array(anchoring_points).reshape(4, 2)
    #print("anchoring_points: ", anchoring_points)

    def get_closest_point(aruco_corner, points, used_indices):
        distances = np.linalg.norm(points - aruco_corner, axis=1)
        for idx in np.argsort(distances):
            if idx not in used_indices:
                return points[idx], idx
        return None, None

    ordered_points = np.zeros((4, 2))
    used_indices = []

    for i in range(4):
        closest_point, closest_idx = get_closest_point(marker_corners[i], anchoring_points, used_indices)
        ordered_points[i] = closest_point
        used_indices.append(closest_idx)
    
    #print("ordered_points: ", ordered_points)
    # Expand Ordered Points to Include more of the VMP
    #print(ordered_points[0][0])
    #print(ordered_points[1][0] - ordered_points[0][0])
    
    def scale_square(points, scale_factor):
        # Calculate the center of the square
        center = np.mean(points, axis=0)

        # Scale each point
        scaled_points = []
        for point in points:
            scaled_point = center + scale_factor * (point - center)
            scaled_points.append(np.round(scaled_point).astype(int))

        return np.array(scaled_points)

    scaled_points = scale_square(ordered_points, 34/32)

    #print("Original Points:")
    #print(ordered_points)
    #print("Scaled Points:")
    #print(scaled_points)
    
    ordered_points[0][0] = ordered_points[0][0] - 0
    ordered_points[1][0] = ordered_points[1][0] + 0
    ordered_points[2][0] = ordered_points[2][0] + 0
    ordered_points[3][0] = ordered_points[3][0] - 0

    ordered_points[0][1] = ordered_points[0][1] - 0
    ordered_points[1][1] = ordered_points[1][1] - 0
    ordered_points[2][1] = ordered_points[2][1] + 0
    ordered_points[3][1] = ordered_points[3][1] + 0

    width, height = 640,640
    pts1 = np.float32(scaled_points)

    pts2 = np.float32([[0, 0], [width, 0], [width, height], [0, height]])
    matrix = cv.getPerspectiveTransform(pts1, pts2)
    img_birdview = cv.warpPerspective(lentimark_img, matrix, (width, height))
    
    return img_birdview


"""
PARAMS: 
    img_birdview - a birdseye image of lentimark of predefined size.
    Image provided must be already upright:
         1.) upper rectangle is y-axis VMP, bottom is y-axis FDP 
         2.) right rectangle is x-axis VMP, left is x-axis FDP 
         
RETURNS:
    tuple - proportion of black peak in x and y direction in mm.

"""

def blackPeakDetection(img):
    #Lentimark Distances
    d1,d2 = 4,34 #mm

    #Convert to Greyscale
    # height = width
    height = img.shape[0]
    img_birdview_greyscale = cv.cvtColor(img,cv.COLOR_BGR2GRAY)

    # Greyscale image for FDP detection. Binary Threshold for VMP detection.
    d = round(height/d2) #number of vertical pixels corresponding to 1 mm

    # Use NumPy slicing and mean to vectorize the operations
    y_axis_vmp_luminance = np.mean(img_birdview_greyscale[:2*d, :], axis=0)
    y_axis_vmp_luminance = np.round(y_axis_vmp_luminance).astype(int)

    x_axis_vmp_luminance = np.mean(img_birdview_greyscale[:, -2*d:], axis=1)
    x_axis_vmp_luminance = np.round(x_axis_vmp_luminance).astype(int)

    #Find distance from edge of VMP rectange to  middle of the black peak.
    #Start with y-axis
    def find_vmp_proportion(array, start, height):
        sub_array = array[start:-start]
        
        # increase contrast using gamma curve and normalization 
        img_norm = sub_array/255.0
        img_gamma = np.power(img_norm,2.2)*255.0
        img_gamma = img_gamma.astype(np.uint8)
        img_norm = cv.normalize(img_gamma, dst=None, alpha=350,beta=10, norm_type=cv.NORM_MINMAX)

        _, thresh_image = cv.threshold(img_norm, 200, 255, cv.THRESH_BINARY+cv.THRESH_OTSU)
        min_index_in_sub_array = find_middle_index_of_zeros(thresh_image)
        min_index_in_original_array = min_index_in_sub_array + start
        return min_index_in_original_array / height
    
    def find_middle_index_of_zeros(arr):
        zero_indices = np.where(arr == [0])[0]
    
        if len(zero_indices) == 0:
            return len(arr)//2 # No zeros found in the array
        
        middle_index = zero_indices[len(zero_indices) // 2]
        return middle_index

    # Assuming d1, d, y_axis_vmp_luminance, x_axis_vmp_luminance, and height are already defined
    start = round(d1 * d)

    # Check with Eddy + Yifeng Later
    y_axis_peak_proportion = find_vmp_proportion(y_axis_vmp_luminance, start, height)
    y_axis_peak = y_axis_peak_proportion * (d2 - d1*2)
    #print(f"Y-Axis VMP proportion: {y_axis_peak_proportion}")
    #print(f"Y-Axis VMP Peak: {y_axis_peak}")

    x_axis_peak_proportion = find_vmp_proportion(x_axis_vmp_luminance, start, height) 
    x_axis_peak = x_axis_peak_proportion  * (d2 - d1*2)
    #print(f"X-Axis VMP proportion: {x_axis_peak_proportion}")
    #print(f"X-Axis VMP Peak: {x_axis_peak}")


    ################# for test only ###################
    # Calculate the coordinates for the starting points
    x_start = int(x_axis_peak_proportion * height) - 5
    y_start = int(y_axis_peak_proportion * height) - 5

    # Create the color array
    color = np.array([20, 255, 57])

    # Update the img array using broadcasting and slicing
    img[x_start:x_start+10, -10:] = color
    img[:10, y_start:y_start+10] = color
    ################# for test only ###################
    
    return (y_axis_peak, x_axis_peak)
