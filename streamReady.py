import pyigtl
import time

# Create a server to send data
server = pyigtl.OpenIGTLinkServer(port=18944) # allows our script to send messages to connected clients like 3D Slicer
num = 0
while True: # continously sends marker positions to the server
    # Example RAS marker position
    ras_position = [num, num+1, num+2] # Creates an example RAS position
    # Create a TransformMessage to send the marker position
    message = pyigtl.TransformMessage(device_name="Marker", matrix=[
        [1, 0, 0, ras_position[0]],  # Rotation and translation in RAS for x axis
        [0, 1, 0, ras_position[1]],  # Rotation and translation in RAS for y axis
        [0, 0, 1, ras_position[2]],  # Rotation and translation in RAS for z axis
        [0, 0, 0, 1] #Homogenous transformation
    ])
    # The 4X4 matrix combines rotation (top-left 3X3) and translation (last column) in 3D space
    # No rotation on the X-axis, translation is in ras_position[0]
    # No rotation on the Y-axis , translation is in ras_position [1]
    # No rotation on the Z-axis, translation is ras_position [2]
    # Identity matrix means "no rotation" , it keeps the marker aligned with the default coordinate system

    #X Axis (Right) : How far marker is to the right.
    #Y Axis (Anterior) : How far forward (toward the front).
    #Z Axis (Superior): How high up (toward the top.
    
    server.send_message(message)
    print(f"Sent RAS position: {ras_position}")
    num+=1
    time.sleep(3)  # Send updates every 3s
