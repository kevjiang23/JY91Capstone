import pyigtl
import time
import math
import numpy as np

# Initialize the OpenIGTLink server
server = pyigtl.OpenIGTLinkServer(port=18944) 

num = 0
while True:
    # Define rotation angle in degrees
    angle = num * 5  # Rotate 5 degrees each iteration
    tx, ty, tz = num * 1, num * 1.5, num * 2  

    # Create rotation matrix around Z-axis using numpy for efficiency
    theta = np.radians(angle)
    rot_z = np.array([
        [np.cos(theta), -np.sin(theta), 0, 0],
        [np.sin(theta),  np.cos(theta), 0, 0],
        [0,              0,             1, 0],
        [0,              0,             0, 1]
    ])

    # Create translation matrix
    trans = np.array([
        [1, 0, 0, tx],
        [0, 1, 0, ty],
        [0, 0, 1, tz],
        [0, 0, 0, 1]
    ])

    # Combine rotation and translation
    transform = np.dot(rot_z, trans)

    # Convert the matrix to a 2D list
    matrix_2d = transform.tolist()

    # Create and send the TransformMessage
    message = pyigtl.TransformMessage(
        device_name="Mandible",  # Must match the device name in Slicer
        matrix=matrix_2d
    )
    server.send_message(message)
    print(f"Sent transformation with rotation {angle}° and translation [{tx}, {ty}, {tz}]")

    num += 1
    time.sleep(1)  # Wait for 1 second before sending the next transformation