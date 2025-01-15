import pyigtl
import time
import numpy as np

def euler_to_rotation_matrix(roll, pitch, yaw):
    # Create individual rotation matrices for each axis
    R_x = np.array([[1, 0, 0],
                    [0, np.cos(roll), -np.sin(roll)],
                    [0, np.sin(roll), np.cos(roll)]])
    
    R_y = np.array([[np.cos(pitch), 0, np.sin(pitch)],
                    [0, 1, 0],
                    [-np.sin(pitch), 0, np.cos(pitch)]])
    
    R_z = np.array([[np.cos(yaw), -np.sin(yaw), 0],
                    [np.sin(yaw), np.cos(yaw), 0],
                    [0, 0, 1]])
    
    # Combine rotations (R_z * R_y * R_x)
    R = np.dot(R_z, np.dot(R_y, R_x))
    return R

def send_coors(xcoor, ycoor, zcoor, xangle, yangle, zangle):
    # Create a server to send data
    server = pyigtl.OpenIGTLinkServer(port=18944)
    num = 0
    while True:
        # Example RAS marker position
        ras_position = [num, num+1, num+2]
        # Create a TransformMessage to send the marker position
        
        # compute transformation matrix
        rotation_matrix = euler_to_rotation_matrix(xangle, yangle, zangle)

        transformation_matrix = np.eye(4)
        transformation_matrix[:3, :3] = rotation_matrix
        transformation_matrix[:3, 3] = [xcoor, ycoor, zcoor]

        message = pyigtl.TransformMessage(device_name="Marker", matrix=transformation_matrix)
        server.send_message(message)
        print(f"Sent RAS position: {ras_position}")
        num+=1
        time.sleep(1)  # Send updates every 1s
