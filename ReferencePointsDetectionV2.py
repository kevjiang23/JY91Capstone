"""
Module: ReferencePointsDetectionV2.py

Overview:
This function processes an image to detect reference points (RP) of the LentiMark
by identifying and analyzing contours in the masked frame. It applies thresholding and contour 
detection to locate points of interest, which are then marked on the original frame.

"""
from matplotlib import pyplot as plt
import numpy as np
import cv2 as cv

def RPDetectionImage(original_fram, masked_frame):
	"""
	Args:
    original_fram (np.array): The original image frame where reference points will be detected and marked.
    masked_frame (np.array): The masked version of the image where the detection process is performed.

	Returns:
		tuple: A tuple containing:
			- original_fram (np.array): The original image with reference points marked.
			- output_points (list): A list of coordinates (tuples) representing the detected reference points.
	"""
	# Threshold the image
	gray_image = cv.cvtColor(masked_frame, cv.COLOR_BGR2GRAY)
	hist = cv.calcHist([gray_image], [0], None, [256], [0, 256])

	color_substitution = 255
	for i in range(254, 10, -1):
		if (hist[i] >= 10):
			color_substitution = i
			break


	if(color_substitution != 255 ):
		gray_image[gray_image == 255] = color_substitution

	##################################################################################		
	# Apply a blur to reduce noise
	blurred = cv.GaussianBlur(gray_image, (9, 9), 0)
	_, thresh_image = cv.threshold(gray_image, 0, 255, cv.THRESH_BINARY+cv.THRESH_OTSU)
	swapped_image = np.logical_not(thresh_image)

	fillImage = (swapped_image * 255).astype(np.uint8)
	#cv.imwrite('ref_testing/fillImage.jpg', fillImage)

	contours, _ = cv.findContours(swapped_image.astype(np.uint8), cv.RETR_EXTERNAL,cv.CHAIN_APPROX_NONE)

	# A very small value to prevent division by zero
	small_value = np.finfo(float).eps

	output_points = []

	for _, contour in enumerate(contours):
		perimeter = cv.arcLength(contour, True) 
		area = cv.contourArea(contour)
		alpha = 4*np.pi*area/(perimeter**2 + small_value)
		# print('{0:>6} {1:>9,.0f} {2:>9,.2f} {3:>9,.3f}'.format(ind, area, perimeter, alpha))
		# Compute moments in order to find the centroid of objects
		moments = cv.moments(contour)
		cx = int(moments['m10'] / (moments['m00'] + small_value))
		cy = int(moments['m01'] / (moments['m00'] + small_value))
		# cv.putText(frame,str(ind),(cx,cy),cv.FONT_HERSHEY_SIMPLEX,0.5,color=(0,128,0),thickness=2)
		# Plot a red circle on the centroid of the round objects
		if alpha > 0.1:
			output_points.append((cx,cy))
	
	for point in output_points:
		cv.circle(original_fram,(point[0], point[1]),2,color=(0,0,255),thickness=2)
		# masked_frame[point[1], point[0]] = [255, 255, 255]
	
	# cv.imwrite('ref_testing/beforeBinarization.jpg', masked_frame)

	#print("output_points ", output_points)

	return original_fram, output_points
