import pickle
import cv2 as cv
import numpy as np
from numpy import pi

def GetCameraParameters(file_path):
    try:
        with open(file_path, 'rb') as file:
            data = pickle.load(file)
            return data[0],data[1]
    except Exception as e:
        print(f"An error occurred: {e}")

def rot_params_rv(R):
    sy = np.sqrt(R[0,0]**2+R[1,0]**2)

    singular = sy < 1e-6

    if not singular:
        yaw_thetax = 180*np.arctan2(R[2][1], R[2][2])/pi
        pitch_thetay = 180*np.arctan2(-R[2][0],sy)/pi
        roll_thetaz = 180*np.arctan2(R[1][0], R[0][0])/pi
    else:
        yaw_thetax = 180*np.arctan2(R[1][2], R[1][1])/pi
        pitch_thetay = 180*np.arctan2(-R[2][0],sy)/pi
        roll_thetaz = 0
    rot_params= np.array([round(yaw_thetax,2),round(pitch_thetay,2),round(roll_thetaz,2)])
    return rot_params

def imageMerger(image_list):
    if not image_list:
        return None

    # Filter out None elements from the list
    valid_images = [img for img in image_list if img is not None]

    if not valid_images:
        return None

    # Start with the first valid image in the list as the base
    result = valid_images[0]

    # Iterate through the rest of the valid images and merge them
    for img in valid_images[1:]:
        # Create mask
        mask = cv.inRange(result, (255, 255, 255), (255, 255, 255))

        # Create inverse mask
        mask_inv = cv.bitwise_not(mask)

        # Mask the second image (background)
        img_bg = cv.bitwise_and(img, img, mask=mask)

        # Mask the current result image (foreground)
        result_fg = cv.bitwise_and(result, result, mask=mask_inv)

        # Combine foreground and background
        result = cv.add(result_fg, img_bg)

    return result

def readConfig(file_path):
    with open(file_path, 'r') as file:
        integer_list = [int(line.strip()) for line in file if line.strip().isdigit()]
    return integer_list


def create_function(a, b, c, d):
    def transform(tup):
        x, y = tup
        return ((x - b) / a, (y - d) / c)
    return transform

def readMap(file_path):
    data_dict = {}

    with open(file_path, 'r') as file:
        lines = file.readlines()

    for line in lines:
        parts = line.split()
        key = int(parts[0])
        a, b, c, d = map(float, parts[1:])
        print(a, b, c, d)
        data_dict[key] = create_function(a, b, c, d)

    return data_dict