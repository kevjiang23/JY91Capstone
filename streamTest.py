import pyigtl
import time

# Create a server to send data
server = pyigtl.OpenIGTLinkServer(port=18944)
num = 0
while True:
    # Example RAS marker position
    ras_position = [num, num+1, num+2]
    # Create a TransformMessage to send the marker position
    message = pyigtl.TransformMessage(device_name="Marker", matrix=[
        [1, 0, 0, ras_position[0]],  # Rotation and translation in RAS
        [0, 1, 0, ras_position[1]],
        [0, 0, 1, ras_position[2]],
        [0, 0, 0, 1]
    ])
    server.send_message(message)
    print(f"Sent RAS position: {ras_position}")
    num+=1
    time.sleep(3)  # Send updates every 3s
