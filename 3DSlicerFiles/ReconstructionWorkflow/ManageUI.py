import numpy as np
from slicer.util import VTKObservationMixin, getNode
from __main__ import vtk,qt,ctk, slicer

def create_button(button_text="Default text", tooltip="", enabled=True):
    button = qt.QPushButton()
    button.setText(button_text)
    button.setEnabled(enabled)
    button.setToolTip(tooltip)
    return button

def create_collapsible_button(collapsible_text="Collapsible section", collapsed_state=False):
    collapsible_button = ctk.ctkCollapsibleButton()
    collapsible_button.text = collapsible_text
    #collapsed_state.collapsed = collapsed_state
    return collapsible_button

def create_label(label_text="Default label"):
    label = qt.QLabel(label_text)
    return label

def update_label(text_label, value, threshold=1, units=""):
    curr_value = text_label.text.split(" ")
    curr_value = curr_value[0]
    text_value = float(curr_value)
    if abs(text_value - value) > threshold: 
        text_label.setText(f'{value} {units}')
        return True
    else: 
        return False

def clone_plane(markups_plane, name="Plane node"):
    origin = [0,0,0]
    normal = [0,0,0]
    markups_plane.GetOriginWorld(origin)
    markups_plane.GetNormalWorld(normal)
    plane = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLMarkupsPlaneNode', name)
    plane.SetNormalWorld(normal)
    plane.SetOriginWorld(origin)
    return plane

def create_translate_transform(translate):
    transform = vtk.vtkTransform()
    transform.Translate(translate[0], translate[1], translate[2])
    return transform.GetMatrix()

def create_linear_transform(matrix, name="DefaultNode"):
    transformNode = slicer.vtkMRMLLinearTransformNode()
    transformNode.SetName(name)
    transformNode.SetMatrixTransformToParent(matrix)
    slicer.mrmlScene.AddNode(transformNode)
    return transformNode

def update_transform(matrix, node_name):
    try:
        node = getNode(node_name)
        node.SetMatrixTransformToParent(matrix)
        print("Updated cloned node")
    except slicer.util.MRMLNodeNotFoundException:
        node = create_linear_transform(matrix, node_name)
        print("Created cloned node")
    return node

def import_node(node_name, node_type='vtkMRMLMarkupsFiducialNode'):
    try:
        node = getNode(node_name)
        print(f'Retrieved {node_name}')
    except slicer.util.MRMLNodeNotFoundException: 
        node = slicer.mrmlScene.AddNewNodeByClass(node_type, node_name)
        print(f'Created {node_name}')
    return node

def remove_node(node_name):
    try: 
        node = getNode(node_name)
        slicer.mrmlScene.RemoveNode(node)
    except slicer.util.MRMLNodeNotFoundException:
        pass

def check_node_exists(scene_node):
    if slicer.mrmlScene.GetNodeByID(scene_node) != None:
        return True     #Node already exists in the scene
    else: 
        return False    #Node does not exist 

def retrieve_node(node_name):
    try:
        node = getNode(node_name)
        return node
    except slicer.util.MRMLNodeNotFoundException:
        print(f'{node_name} not found.')

def create_watchdog_node(node_name, observed_transform, message):
    try: 
        watchdog = getNode(node_name)
    except slicer.util.MRMLNodeNotFoundException:
        watchdog = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLWatchdogNode', node_name)
        watchdog.AddWatchedNode(observed_transform, message)
        print(f'Created watchdog node')
    return watchdog

def create_text_input(parentCollapsibleButton, parentGridLayout, labelText, editText, row=0, column=0):
    frame = qt.QFrame(parentCollapsibleButton)
    frame.setLayout(qt.QHBoxLayout())
    parentGridLayout.addWidget(frame, row, column, 1, 4)
    textInputLabel = qt.QLabel(labelText, frame)
    frame.layout().addWidget(textInputLabel)
    textInput = qt.QLineEdit()
    frame.layout().addWidget(textInput)
    validator = qt.QDoubleValidator()
    validator.setNotation(0)
    textInput.setValidator(validator)
    textInput.setText(editText)
    return textInput
    
def create_coordinate_model(name, matrix):
    coordinate_model = slicer.modules.createmodels.logic().CreateCoordinate(20, 1)
    coordinate_model.SetName(name)
    transform = vtk.vtkTransform()
    transform.SetMatrix(matrix)
    coordinate_model.ApplyTransform(transform)
    return coordinate_model
