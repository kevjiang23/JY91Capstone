import pyigtl
import time

def send_coors(coor1, coor2, coor3):
    # Create a server to send data
    server = pyigtl.OpenIGTLinkServer(port=18944)
    num = 0
    while True:
        # Example RAS marker position
        ras_position = [num, num+1, num+2]
        # Create a TransformMessage to send the marker position
        message = pyigtl.TransformMessage(device_name="Marker", matrix=[
            [1, 0, 0, coor1],  # Rotation and translation in RAS
            [0, 1, 0, coor2],
            [0, 0, 1, coor3],
            [0, 0, 0, 1]
        ])
        server.send_message(message)
        print(f"Sent RAS position: {ras_position}")
        num+=1
        time.sleep(1)  # Send updates every 3s
