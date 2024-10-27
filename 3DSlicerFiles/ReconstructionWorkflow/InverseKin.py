# import numpy as np
from slicer.util import VTKObservationMixin, getNode
from __main__ import vtk,qt,ctk, slicer
# import math
from numpy import cross, eye, dot, arccos, divide
from scipy.linalg import expm, norm
from math import sqrt, sin, tan, cos, pi

class InverseKin:    
    def __init__(self, X1, X2, X3, X4, Y1, Y2, Y3, Y4, H, D):
        self.BASE_X1 = X1
        self.BASE_X2 = X2
        self.BASE_X3 = X3 
        self.BASE_X4 = X4

        self.BASE_Y1 = Y1
        self.BASE_Y2 = Y2
        self.BASE_Y3 = Y3
        self.BASE_Y4 = Y4

        self.BASE_H = H 
        self.BASE_D = D

    def M(self, axis, theta):
        return expm(cross(eye(3), divide(axis,norm(axis))*theta)) #get rid of normalization for axis-angle since already unit vec

    def get_zvec(self, axis, theta):
        a = axis
        t = -theta 
        v = [0,0,1]

        temp = self.M(a, t)
        zvec = dot(temp, v)
        return zvec

    def get_phi_x(self, zvec):
        phi_x = arccos(zvec[2]/sqrt((zvec[2])**2 + (zvec[1])**2))
        if (zvec[2] > 0 and zvec[1] > 0) or (zvec[2] < 0 and zvec[1] < 0):
            phi_x = abs(phi_x)
        else:
            phi_x = -abs(phi_x)
        return phi_x

    def get_phi_y(self, zvec):
        phi_y = arccos(zvec[2]/sqrt((zvec[2])**2 + (zvec[0])**2))
        if (zvec[2] > 0 and zvec[0] > 0) or (zvec[2] < 0 and zvec[0] < 0):
            phi_y = abs(phi_y)
        else:
            phi_y = -abs(phi_y)
        return phi_y

    def get_zrot(self, axis, theta):
        a = axis
        t = -theta 
        v = [0, 1, 0]

        temp = self.M(a, t)
        zrot = dot(temp, v)
        return zrot

    def get_phi_z(self, zrot):
        phi_z = arccos(zrot[1]/sqrt((zrot[0])**2 + (zrot[1])**2))
        if ((zrot[0] > 0 and zrot[1] > 0) or (zrot[0] < 0 and zrot[1] < 0)):
            phi_z = abs(phi_z)
        else:
            phi_z = -abs(phi_z)
        return phi_z

    def get_phi_z_act3(self, phi_z, x, y, hand=1):
        if hand == 1:
            base_y = self.BASE_Y3
            base_x = self.BASE_X3
        elif hand == 3:
            base_y = self.BASE_Y4
            base_x = self.BASE_X4
        
        phi_zi = cos(-base_y/sqrt((base_y)**2 + (base_x)**2))
        if ((base_y > 0 and base_x > 0) or (base_y < 0 and base_x < 0)):
            phi_zi = abs(phi_zi)
        else:
            phi_zi = -abs(phi_zi)

        phi_zf = cos((y - base_y)/sqrt((y - base_y)**2 + (x - base_x)**2))
        if ((y - base_y > 0 and x - base_x > 0) or (y - base_y < 0 and x - base_x < 0)):
            phi_zf = abs(phi_zf)
        else:
            phi_zf = -abs(phi_zf)

        phi_z_delta = phi_zf - phi_zi
        phi_z_act = phi_z - phi_z_delta
        return phi_z_act
    
    def calculate_lengths_absolute(self, x, y, z, phi_x, phi_y, phi_z_act):
        L1 = sqrt(((x - self.BASE_D*sin(phi_y)) - self.BASE_X1)**2 + ((y - self.BASE_D*sin(phi_x)) - self.BASE_Y1)**2)
        L2 = sqrt(((x - self.BASE_D*sin(phi_y)) - self.BASE_X2)**2 + ((y - self.BASE_D*sin(phi_x)) - self.BASE_Y2)**2)
        L3 = sqrt(((x - self.BASE_H*tan(phi_y) - self.BASE_D*sin(phi_y)) - self.BASE_X3)**2 + ((y - self.BASE_H*tan(phi_x) - self.BASE_D*sin(phi_x)) - self.BASE_Y3)**2)
        L4 = sqrt(((x - self.BASE_H*tan(phi_y) - self.BASE_D*sin(phi_y)) - self.BASE_X4)**2 + ((y - self.BASE_H*tan(phi_x) - self.BASE_D*sin(phi_x)) - self.BASE_Y4)**2)  
        L5_z = z + (self.BASE_D - self.BASE_D*cos(max(phi_x,phi_y)))
        input_phi_z_rot = 20*phi_z_act
        return L1, L2, L3, L4, L5_z, input_phi_z_rot

    # def set_initial_lengths(self):
    #     #Set initial lengths
    #     L1i = sqrt(self.BASE_X1**2 + self.BASE_Y1**2)
    #     L2i = sqrt(self.BASE_X2**2 + self.BASE_Y2**2)    
    #     L3i = sqrt(self.BASE_X3**2 + self.BASE_Y3**2)
    #     L4i = sqrt(self.BASE_X4**2 + self.BASE_Y4**2)
    #     L5_Zi = 0
    #     Input_Rots_Phi_zi = 0

    def calculate_lengths_change(self, L1, L2, L3, L4, L5_z, input_phi_z_rot):
        L1i = sqrt(self.BASE_X1**2 + self.BASE_Y1**2)
        L2i = sqrt(self.BASE_X2**2 + self.BASE_Y2**2)    
        L3i = sqrt(self.BASE_X3**2 + self.BASE_Y3**2)
        L4i = sqrt(self.BASE_X4**2 + self.BASE_Y4**2)
        L5_Zi = 0
        input_phi_z_roti = 0

        delta_L1 = L1 - L1i
        L1_rots = delta_L1/0.5

        delta_L2 = L2 - L2i
        L2_rots = delta_L2/0.5

        delta_L3 = L3 - L3i
        L3_rots = delta_L3/0.5

        delta_L4 = L4 - L4i
        L4_rots = delta_L4/0.5

        delta_L5 = L5_z - L5_Zi
        L5_rots = delta_L5/(25.4*1/28)

        delta_phi_z = input_phi_z_rot - input_phi_z_roti
        return L1_rots, L2_rots, L3_rots, L4_rots, L5_rots, delta_phi_z

