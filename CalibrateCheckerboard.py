import numpy
import cv2 as cv
import pickle
import glob
from pypylon import pylon
#import pyttsx3

def photograph():
    #engine = pyttsx3.init()
    cv.startWindowThread()

    # open webcam video stream
    # cap = cv.VideoCapture(0)
    # cap.set(cv.CAP_PROP_FRAME_WIDTH, 1920)
    # cap.set(cv.CAP_PROP_FRAME_HEIGHT, 1080)
    cap = pylon.InstantCamera(pylon.TlFactory.GetInstance().CreateFirstDevice())
    cap.Open()
    cap.StartGrabbing(pylon.GrabStrategy_LatestImageOnly)
    
    i = 1
    #engine.say('Start calibration process')
    #engine.runAndWait()

    while cap.IsGrabbing():
        # Capture frame-by-frame
        # ret, frame = cap.read()
        grab_result = cap.RetrieveResult(5000, pylon.TimeoutHandling_ThrowException)
        if grab_result.GrabSucceeded():
            frame = cv.cvtColor(grab_result.Array, cv.COLOR_BGR2RGB)
            ret = True
            
            if(ret):
                # Display the resulting frame
                cv.imshow('frame',frame)
                key = cv.waitKey(1)
                if key == ord('q'):
                    #engine.say('Quit.')
                    #engine.runAndWait()
                    break
                    # exit()
                if key == ord('p'):
                    name = "chessboard-" + str(i) + ".png"
                    cv.imwrite("./images/" + name, frame)
                    if(i == 16):
                        #engine.say('Photo' + str(i) + 'has been taken.')
                        #engine.say('All works done!')
                        #engine.runAndWait()
                        break
                    #engine.say('Photo' + str(i) + 'has been taken.')
                    #engine.runAndWait()
                    i += 1
        grab_result.Release()

    # When everything done, release the capture
    # cap.release()
    cap.StopGrabbing()
    cap.Close()
    cv.destroyAllWindows()

def calibration():
    #engine = pyttsx3.init()
    # Create arrays you'll use to store object points and image points from all images processed
    objpoints = [] # 3D point in real world space where chess squares are
    imgpoints = [] # 2D point in image plane, determined by CV2

    # Chessboard variables (row and colunm)
    CHESSBOARD_CORNERS_ROWCOUNT = 8
    CHESSBOARD_CORNERS_COLCOUNT = 5


    # The following line generates all the tuples needed at (0, 0, 0)
    objp = numpy.zeros((CHESSBOARD_CORNERS_ROWCOUNT*CHESSBOARD_CORNERS_COLCOUNT,3), numpy.float32)
    # The following line fills the tuples just generated with their values (0, 0, 0), (1, 0, 0), ...
    objp[:,:2] = numpy.mgrid[0:CHESSBOARD_CORNERS_ROWCOUNT,0:CHESSBOARD_CORNERS_COLCOUNT].T.reshape(-1, 2)

    images = glob.glob('./images/chessboard-*.png')
    imageSize = None

    for iname in images:
        img = cv.imread(iname)
        gray = cv.cvtColor(img, cv.COLOR_BGR2GRAY)

        # Find chessboard in the image, its size is (#rows, #columns)
        board, corners = cv.findChessboardCorners(gray, (CHESSBOARD_CORNERS_ROWCOUNT,CHESSBOARD_CORNERS_COLCOUNT), None)

        # If a chessboard was found, let's collect image/corner points
        if board == True:
            # Add the points in 3D that we just discovered
            objpoints.append(objp)
            
            # Enhance corner accuracy with cornerSubPix
            corners_acc = cv.cornerSubPix(
                    image=gray, 
                    corners=corners, 
                    winSize=(11, 11), 
                    zeroZone=(-1, -1),
                    criteria=(cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 30, 0.001)) # Last parameter is about termination critera
            imgpoints.append(corners_acc)

            # If our image size is unknown, set it now
            if not imageSize:
                imageSize = gray.shape[::-1]
        
            # Draw the corners to a new image to show whoever is performing the calibration
            img = cv.drawChessboardCorners(img, (CHESSBOARD_CORNERS_ROWCOUNT, CHESSBOARD_CORNERS_COLCOUNT), corners_acc, board)

            cv.imshow('Chessboard', img)
            cv.waitKey(0)
        else:
            print("Not able to detect a chessboard in image: {}".format(iname))

    # Destroy any open CV windows
    cv.destroyAllWindows()

    # Make sure at least one image was found
    if len(images) < 1:
        print("Calibration was unsuccessful.")
        exit()

    # Make sure we were able to calibrate on at least one chessboard by checking
    if not imageSize:
        print("Calibration was unsuccessful.")
        exit()

    # Perform the camera calibration
    calibration, cameraMatrix, distCoeffs, rvecs, tvecs = cv.calibrateCamera(
            objectPoints=objpoints,
            imagePoints=imgpoints,
            imageSize=imageSize,
            cameraMatrix=None,
            distCoeffs=None)
        
    # Print matrix and distortion coefficient to the console
    print(cameraMatrix)
    print(distCoeffs)
        
    f = open('calibration.pckl', 'wb')
    pickle.dump((cameraMatrix, distCoeffs, rvecs, tvecs), f)
    f.close()
        
    print('Calibration successful. Calibration file used: {}'.format('calibration.pckl'))
    #engine.say('Calibration process done!')
    #engine.runAndWait()


if(__name__ == '__main__'):
    photograph()
    calibration()