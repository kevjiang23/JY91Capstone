import pyigtl
import time
import numpy as np

server = pyigtl.OpenIGTLinkServer(port=18944) #allows script to send messages to connected clients like 3D Slicer

#Change between dot and square
TURN_SQUARE_ON = False

def euler_to_rotation_matrix(roll, pitch, yaw): #converts Euler angles into a 3X3 rotation matrix
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

def send_coors(xcoor, ycoor, zcoor, xangle, yangle, zangle, marker_id): #This function sends a transformation message to clients like 3D Slicer
    # Create a server to send data 
    global server
    
    # RAS marker position
    # ras_position = [xcoor, ycoor, zcoor]
    ras_position = [float(xcoor), float(ycoor), float(zcoor)] # Store the postion of the marker in RAS (Right , Anterior, Superior) coordinates as a list.

    # Compute transformation matrix
    rotation_matrix = euler_to_rotation_matrix(xangle + np.radians(90), yangle, zangle) #testing with x rotation to point in correct direction

    #converts euler angles to 3X3 rotation matrix
    transformation_matrix = np.eye(4) #initializes a 4X4 identity matrix
    transformation_matrix[:3, :3] = rotation_matrix # Assign the rotation matrix to the top-left 3X3 part.
    transformation_matrix[:3, 3] = [xcoor, ycoor, zcoor] #Sets the last column to the markers RAS position

    if TURN_SQUARE_ON:
        square_size = 10 
        square_corners = np.array([
            [-square_size, -square_size, 0, 1],
            [square_size, -square_size, 0, 1],
            [square_size, square_size, 0, 1],
            [-square_size, square_size, 0, 1]
        ])

        transformed_square = transformation_matrix @ square_corners
        for i, corner, in enumerate(transformed_square[:3,:].T):
            square_message = pyigtl.TransformMessage(
                device_name=f"Marker_{marker_id}_Corner_{i}",
                matrix=np.eye(4)
            )
            square_message.matrix[:3,3] = corner
            server.send_message(square_message)
    else: #default to else
        message = pyigtl.TransformMessage(device_name="Marker " + str(marker_id), matrix=transformation_matrix)  # Encodes the transformation matrix into a format that OpenIGTLink clients like 3D Slicer can interpret
        server.send_message(message) #Sends the encoded message to the connected client using the OpenIGTLink server
    print(f"Sent RAS position: {ras_position}")
    #time.sleep(3)  # for debugging
