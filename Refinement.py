import numpy as np
import cv2 as cv

#########################################################
# PARAMS: 
#   camera_img - image from camera.
#   
# RETURNS:
#   lentimark_img - an image of a predefined size that
#   contains lentimark. 
# 
##########################################################

def draw_square(frame, point1, point2):
    """
    Draws a square on the image using the two given points as opposite corners.

    Parameters:
    - frame: The image on which to draw the square (as a NumPy array).
    - point1: Tuple (x1, y1) representing the first corner of the square.
    - point2: Tuple (x2, y2) representing the opposite corner of the square.

    Returns:
    - The image with the square drawn.
    """

    # Calculate the width and height between the two points
    x1, y1 = point1
    x2, y2 = point2

    # Calculate the side length of the square
    side_length = max(abs(x2 - x1), abs(y2 - y1))

    # Determine the four corners of the square
    # We'll use point1 as one corner and calculate the other three
    if x2 > x1:
        new_x2 = x1 + side_length
    else:
        new_x2 = x1 - side_length

    if y2 > y1:
        new_y2 = y1 + side_length
    else:
        new_y2 = y1 - side_length

    # Draw the square using the two calculated corners
    top_left = (min(x1, new_x2), min(y1, new_y2))
    bottom_right = (max(x1, new_x2), max(y1, new_y2))

    # Draw the square in blue (BGR: [255, 0, 0])
    cv.rectangle(frame, top_left, bottom_right, (255, 0, 0), 1)

    return frame

def crop_squares(frame, square_coords):
    """
    Crops everything else in the image except for the regions inside the specified squares.
    The area outside the squares is set to white.

    Parameters:
    - frame: The original image (as a NumPy array).
    - square_coords: A list of tuples, where each tuple contains the top-left and bottom-right corners of a square.

    Returns:
    - The cropped image with only the regions inside the squares visible and the rest of the image set to white.
    """
    # Create a white mask with the same dimensions as the frame
    mask = np.ones_like(frame) * 255  # All white

    # Fill the mask with black in the areas corresponding to the squares
    for (top_left, bottom_right) in square_coords:
        cv.rectangle(mask, top_left, bottom_right, (0, 0, 0), -1)

    # Invert the mask to make the squares white and everything else black
    inverted_mask = cv.bitwise_not(mask)

    # Combine the original frame with the inverted mask
    cropped_frame = cv.bitwise_and(frame, inverted_mask)

    # Set the area outside the squares to white
    cropped_frame = cv.add(cropped_frame, mask)

    return cropped_frame

def detect_circle_centers(image, square_coords):
    """
    Detects the centers of black circles within the specified squares.

    Parameters:
    - image: The input image (as a NumPy array).
    - square_coords: A list of tuples, where each tuple contains the top-left and bottom-right corners of a square.

    Returns:
    - A list of (x, y) coordinates representing the centers of the circles.
    """
    circle_centers = []

    # Loop through each square
    for (top_left, bottom_right) in square_coords:
        # Extract the region of interest (ROI) corresponding to the square
        roi = image[top_left[1]:bottom_right[1], top_left[0]:bottom_right[0]]

        # Convert the ROI to grayscale
        gray_roi = cv.cvtColor(roi, cv.COLOR_BGR2GRAY)

        # Apply a Gaussian blur to reduce noise
        blurred_roi = cv.GaussianBlur(gray_roi, (9, 9), 2)

        # Detect circles using the HoughCircles method
        circles = cv.HoughCircles(blurred_roi, cv.HOUGH_GRADIENT, dp=1.2, minDist=30, param1=50, param2=30, minRadius=5, maxRadius=50)

        # If at least one circle is found
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (x, y, r) in circles:
                # Calculate the center of the circle in the context of the original image
                center_x = top_left[0] + x
                center_y = top_left[1] + y
                circle_centers.append((center_x, center_y))

                # Optionally draw the circle and center for visualization
                cv.circle(image, (center_x, center_y), r, (0, 255, 0), 2)  # Draw the circle
                cv.circle(image, (center_x, center_y), 3, (0, 0, 255), -1)  # Draw the center of the circle

    return circle_centers

def getExistenceRegionFromImage(corners, frame):
    """ Get smaller region of image where aruco marker resides and set the rest of the image to green screen. 
        Used to highlight the region of interest, expanding the quadrilateral by a factor of 1.25.

    Keyword arguments:
    corners -- array containing the 4 corners of the detected aruco marker
    frame -- the image frame being analyzed
    """
    height, width, _ = frame.shape

    # Extract x and y coordinates from corners
    x_coords = [int(corners[0][i][0]) for i in range(4)]
    y_coords = [int(corners[0][i][1]) for i in range(4)]
    #print("x_coords ", x_coords)
    #print("y_coords ", y_coords)
    x_length = x_coords[1] - x_coords[0]
    y_length = y_coords[2] - y_coords[0]

    #frame[y_coords[0], x_coords[0]] = [255,0,0]
    #frame[y_coords[0] - int(y_length*0.35), x_coords[0] - int(x_length*0.35)] = [255,0,0]

    #frame = draw_square(frame, (x_coords[0], y_coords[0]), (x_coords[0] - int(x_length*0.35), y_coords[0] - int(y_length*0.35)))
    #frame = draw_square(frame, (x_coords[1], y_coords[1]), (x_coords[1] + int(x_length*0.35), y_coords[1] - int(y_length*0.35)))
    #frame = draw_square(frame, (x_coords[2], y_coords[2]), (x_coords[2] + int(x_length*0.35), y_coords[2] + int(y_length*0.35)))
    #frame = draw_square(frame, (x_coords[3], y_coords[3]), (x_coords[3] - int(x_length*0.35), y_coords[3] + int(y_length*0.35)))

    # Define the top-left and bottom-right corners of the squares
    square_coords = [
        ((x_coords[0] - int(x_length*(1/3)), y_coords[0] - int(y_length*(1/3))), (x_coords[0] - int(x_length*0.05), y_coords[0] - int(y_length*0.05))),
        ((x_coords[1] + int(x_length*0.05), y_coords[1] - int(y_length*(1/3))), (x_coords[1] + int(x_length*(1/3)), y_coords[1] - int(y_length*0.05))),
        ((x_coords[2] + int(x_length*0.05), y_coords[2] + int(y_length*0.05)), (x_coords[2] + int(x_length*(1/3)), y_coords[2] + int(y_length*(1/3)))),
        ((x_coords[3] - int(x_length*(1/3)), y_coords[3] + int(y_length*0.05)), (x_coords[3] - int(x_length*0.05), y_coords[3] + int(y_length*(1/3)))),
    ]

    # Crop everything else except for the regions inside the squares
    cropped_frame = crop_squares(frame, square_coords)

    # Save or display the cropped image
    # cv.imwrite('ref_testing/cropped_image.jpg', cropped_frame)

    '''frame[y_coords[1], x_coords[1]] = [255,0,0]
    frame[y_coords[2], x_coords[2]] = [255,0,0]
    frame[y_coords[3], x_coords[3]] = [255,0,0]
    
    frame[y_coords[1] - int(y_length*0.35), x_coords[1] + int(x_length*0.35)] = [255,0,0]
    frame[y_coords[2] + int(y_length*0.35), x_coords[2] + int(x_length*0.35)] = [255,0,0]
    frame[y_coords[3] + int(y_length*0.35), x_coords[3] - int(x_length*0.35)] = [255,0,0]'''

    # cv.imwrite("ref_testing/frame.jpg", frame)



    # Calculate the center of the quadrilateral
    center_x = sum(x_coords) / 4
    center_y = sum(y_coords) / 4

    # Scale factors
    scale_factors = [1.6, 1.1, 4/3]

    # Function to expand quadrilateral
    def expand_quadrilateral(scale_factor):
        return np.array([[
            [int(center_x + (x - center_x) * scale_factor), int(center_y + (y - center_y) * scale_factor)]
            for x, y in zip(x_coords, y_coords)
        ]], dtype=np.int32)

   # Expand the quadrilateral for each scale factor
    new_coords = [expand_quadrilateral(sf) for sf in scale_factors]

    # Assign to respective variables
    new_coords_outside, new_coords_inside, new_coords_backup = new_coords

    # Create a mask with the same dimensions as the frame
    mask = np.zeros((height, width), dtype=np.uint8)

    # Fill the expanded quadrilateral in the mask with white color
    cv.fillPoly(mask, new_coords_outside, 255)

    # Invert the mask to get the area outside the quadrilateral
    mask_inv = cv.bitwise_not(mask)

    # Create a green and white screen (RGB (0, 255, 0)) and (RGB (255, 255, 255))
    # green_screen = np.full(frame.shape, (0, 255, 0), dtype=np.uint8)
    white_screen = np.full(frame.shape, (255,255,255), dtype=np.uint8)

    # # Use the inverted mask to set the area outside the quadrilateral to green
    frame_outside_green = cv.bitwise_and(white_screen, white_screen, mask=mask_inv) ########
    frame_inside_original = cv.bitwise_or(frame, frame, mask=mask) ########

    # # Combine the two images
    result_frame = cv.add(frame_outside_green, frame_inside_original) ########

    #cv.imwrite("ref_testing/result_frame.jpg", result_frame)

    # frame_outside_green = cv.bitwise_and(white_screen, white_screen, mask=mask_inv)
    # frame_inside_original = cv.bitwise_or(frame, frame, mask=mask)

    # Combine the two images
    # result_frame = cv.add(frame_outside_green, frame_inside_original) ##################
    # cv.imwrite('2.png', test_frame)

    # Could be improved
    cv.fillPoly(mask_inv, new_coords_inside, 255)
    frame_outside_green = cv.bitwise_and(white_screen, white_screen, mask=mask_inv)



    frame_inside_original = cv.bitwise_or(frame, frame, mask=cv.bitwise_not(mask_inv))
    masked_frame = cv.add(frame_outside_green, frame_inside_original)
    

    # Lengthen the lines
    def lengthen_line_both_directions(start, end):
        direction = end - start
        new_start = start - direction * 1.5
        new_end = end + direction * 1.5
        return tuple(new_start.astype(int)), tuple(new_end.astype(int))

    new_line_coords = [
        lengthen_line_both_directions(new_coords_inside[0][i], new_coords_inside[0][(i + 1) % 4])
        for i in range(4)
    ]

    # Define the points of the polygon to fill
    point_sets = [
        np.array([new_line_coords[i][1], new_line_coords[i][0], new_line_coords[(i + 2) % 4][1], new_line_coords[(i + 2) % 4][0]])
        for i in range(2)
    ]

    # Fill the polygon with white
    for point_set in point_sets:
        cv.fillPoly(masked_frame, [point_set], (255,255,255))

    # cv.imwrite("ref_testing/masked_frame.jpg", masked_frame)
    # cv.imwrite("ref_testing/result_frame.jpg", result_frame)

    return result_frame, masked_frame, new_coords_backup