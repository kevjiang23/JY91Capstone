#Finds intersection between plane and model. Takes a vtk plane.
def get_intersection_contour(plane, model):
    cutter = vtk.vtkCutter()
    cutter.SetInputData(model.GetPolyData())
    cutter.SetCutFunction(plane)
    cutter.Update()
    return cutter.GetOutput()

def get_centroid(model):
    center_of_mass = vtk.vtkCenterOfMass()
    center_of_mass.SetInputData(model.GetPolyData())
    center_of_mass.Update()
    return center_of_mass.GetCenter()

#Get segment point uses the cut plane and the fibula model to find their intersection contour. 
#It then finds the centroid of that intersection contour to find an approximation of the segment centre. 
#This is done for the start of the segment and the end to find its start_point and end_point, which is used
#in calculate_segment_length below. In my current implementation, I store these points in a fiducial list to 
#retrieve them later. It works, it just makes the transform hierarchy a little messy. 
def get_segment_point(plane, model, segment_number):
    contour = get_intersection_contour(plane, model)
    centre = get_centroid(contour)
    return centre

#Because the fibula length runs along the z-axis, I used the z-coordinates to add direction to the distance calculation
def calculate_segment_length(self, start_point, end_point):
    if (end_point[2]-start_point[2]) <= 0:
        distance = np.sqrt(((end_point[0]-start_point[0])**2) + ((end_point[1]-start_point[1])**2) + ((end_point[2]-start_point[2])**2))
    else: 
        distance = - np.sqrt(((end_point[0]-start_point[0])**2) + ((end_point[1]-start_point[1])**2) + ((end_point[2]-start_point[2])**2))
        return distance

 #Inputs are the segment lengths calculated using calculate_segment_length
def calculate_length_error(self, target_length, actual_length):
    length_error = actual_length - target_length
    return np.round(length_error, 5)


def calculate_angle_error(guide_normal, target_normal):
    angle_rad = vtk.vtkMath.AngleBetweenVectors(guide_normal, target_normal)
    angle_deg = vtk.vtkMath.DegreesFromRadians(angle_rad)
    return angle_deg
