from __main__ import vtk, qt, ctk, slicer
import logging
import time

class ViewpointLogic:

  def __init__(self):
    self.nodeInstanceDictionary = {}

  def getViewpointForViewNode(self, viewNode):
    if (viewNode == None):
      logging.error("viewNode given to Viewpoint logic is None. Aborting operation.")
      return
    if (not viewNode in self.nodeInstanceDictionary):
      self.nodeInstanceDictionary[viewNode] = ViewpointInstance()
    return self.nodeInstanceDictionary[viewNode]

#
# Viewpoint Instance
# Each view is associated with its own viewpoint instance,
# this allows support of multiple views with their own
# viewpoint parameters and settings.
#

class ViewpointInstance:
  def __init__(self):
    # global
    self.viewNode = None

    self.currentMode = 0
    self.currentModeOFF = 0
    self.currentModeBULLSEYE = 1
    self.currentModeAUTOCENTER = 2

    # BULLSEYE
    self.bullseyeTransformNode = None
    self.bullseyeTransformNodeObserverTags = []
    self.bullseyeCameraXPosMm =  0.0
    self.bullseyeCameraYPosMm =  0.0
    self.bullseyeCameraZPosMm =  0.0

    self.bullseyeCameraParallelProjection = False # False = perspective, True = parallel. This is consistent with the
                                          # representation in the vtkCamera class and documentation

    self.bullseyeForcedUpDirection = False # False = if the user rotates the tool, then the camera rotates with it
                                   # True = the up direction is fixed according to this next variable:
    self.bullseyeUpDirectionRAS = [0,1,0] # Anterior by default
    self.bullseyeUpDirectionRASRight = [1,0,0]
    self.bullseyeUpDirectionRASLeft = [-1,0,0]
    self.bullseyeUpDirectionRASAnterior = [0,1,0]
    self.bullseyeUpDirectionRASPosterior = [0,-1,0]
    self.bullseyeUpDirectionRASSuperior = [0,0,1]
    self.bullseyeUpDirectionRASInferior = [0,0,-1]

    self.bullseyeForcedTarget = False # False = camera points the direction the user is pointing it
                              # True = camera always points to the target model
    self.bullseyeTargetModelNode = None
    self.bullseyeTargetModelMiddleInRASMm = [0,0,0]

    self.bullseyeCameraViewAngleDeg  =  30.0
    self.bullseyeCameraParallelScale = 1.0

    # AUTO-CENTER
    #inputs
    self.autoCenterSafeXMinimumNormalizedViewport = -1.0
    self.autoCenterSafeXMaximumNormalizedViewport = 1.0
    self.autoCenterSafeYMinimumNormalizedViewport = -1.0
    self.autoCenterSafeYMaximumNormalizedViewport = 1.0
    self.autoCenterSafeZMinimumNormalizedViewport = -1.0
    self.autoCenterSafeZMaximumNormalizedViewport = 1.0

    self.autoCenterAdjustX = True
    self.autoCenterAdjustY = True
    self.autoCenterAdjustZ = False

    self.autoCenterModelNode = None

    self.autoCenterTimeUnsafeToAdjustMaximumSeconds = 1
    self.autoCenterTimeAdjustToRestMaximumSeconds = 0.2
    self.autoCenterTimeRestToSafeMaximumSeconds = 1

    self.autoCenterUpdateRateSeconds = 0.02

    # current state
    self.autoCenterSystemTimeAtLastUpdateSeconds = 0
    self.autoCenterTimeInStateSeconds = 0
    self.autoCenterState = 0 # 0 = in safe zone (initial state), 1 = in unsafe zone, 2 = adjusting, 3 = resting
    self.autoCenterStateSAFE = 0
    self.autoCenterStateUNSAFE = 1
    self.autoCenterStateADJUST = 2
    self.autoCenterStateREST = 3
    self.autoCenterBaseCameraTranslationRas = [0,0,0]
    self.autoCenterBaseCameraPositionRas = [0,0,0]
    self.autoCenterBaseCameraFocalPointRas = [0,0,0]
    self.autoCenterModelInSafeZone = True

    self.autoCenterModelTargetPositionViewport = [0,0,0]

  def setViewNode(self, node):
    self.viewNode = node

  def getCurrentMode(self):
    return self.currentMode

  def isCurrentModeOFF(self):
    return (self.currentMode == self.currentModeOFF)

  def isCurrentModeBullseye(self):
    return (self.currentMode == self.currentModeBULLSEYE)

  def isCurrentModeAutoCenter(self):
    return (self.currentMode == self.currentModeAUTOCENTER)

  def getCameraNode(self, viewName):
    """
    Get camera for the selected 3D view
    """
    camerasLogic = slicer.modules.cameras.logic()
    camera = camerasLogic.GetViewActiveCameraNode(slicer.util.getNode(viewName))
    return camera

  def convertRasToViewport(self, positionRas):
    """Computes normalized view coordinates from RAS coordinates
    Normalized view coordinates origin is in bottom-left corner, range is [-1,+1]
    """
    x = vtk.mutable(positionRas[0])
    y = vtk.mutable(positionRas[1])
    z = vtk.mutable(positionRas[2])
    view = slicer.app.layoutManager().threeDWidget(self.getThreeDWidgetIndex()).threeDView()
    renderer = view.renderWindow().GetRenderers().GetItemAsObject(0)
    renderer.WorldToView(x,y,z)
    return [x.get(), y.get(), z.get()]

  def convertViewportToRas(self, positionViewport):
    x = vtk.mutable(positionViewport[0])
    y = vtk.mutable(positionViewport[1])
    z = vtk.mutable(positionViewport[2])
    view = slicer.app.layoutManager().threeDWidget(self.getThreeDWidgetIndex()).threeDView()
    renderer = view.renderWindow().GetRenderers().GetItemAsObject(0)
    renderer.ViewToWorld(x,y,z)
    return [x.get(), y.get(), z.get()]

  def convertPointRasToCamera(self, positionRas):
    viewName = self.viewNode.GetName()
    cameraNode = self.getCameraNode(viewName)
    cameraObj = cameraNode.GetCamera()
    modelViewTransform = cameraObj.GetModelViewTransformObject()
    positionRasHomog = [positionRas[0], positionRas[1], positionRas[2], 1] # convert to homogeneous
    positionCamHomog = [0,0,0,1] # to be filled in
    modelViewTransform.MultiplyPoint(positionRasHomog, positionCamHomog)
    positionCam = [positionCamHomog[0], positionCamHomog[1], positionCamHomog[2]] # convert from homogeneous
    return positionCam

  def convertVectorCameraToRas(self, positionCam):
    viewName = self.viewNode.GetName()
    cameraNode = self.getCameraNode(viewName)
    cameraObj = cameraNode.GetCamera()
    modelViewTransform = cameraObj.GetModelViewTransformObject()
    modelViewMatrix = modelViewTransform.GetMatrix()
    modelViewInverseMatrix = vtk.vtkMatrix4x4()
    vtk.vtkMatrix4x4.Invert(modelViewMatrix, modelViewInverseMatrix)
    modelViewInverseTransform = vtk.vtkTransform()
    modelViewInverseTransform.DeepCopy(modelViewTransform)
    modelViewInverseTransform.SetMatrix(modelViewInverseMatrix)
    positionCamHomog = [positionCam[0], positionCam[1], positionCam[2], 0] # convert to homogeneous
    positionRasHomog = [0,0,0,0] # to be filled in
    modelViewInverseTransform.MultiplyPoint(positionCamHomog, positionRasHomog)
    positionRas = [positionRasHomog[0], positionRasHomog[1], positionRasHomog[2]] # convert from homogeneous
    return positionRas

  def resetCameraClippingRange(self):
    view = slicer.app.layoutManager().threeDWidget(self.getThreeDWidgetIndex()).threeDView()
    renderer = view.renderWindow().GetRenderers().GetItemAsObject(0)
    renderer.ResetCameraClippingRange()

  def getThreeDWidgetIndex(self):
    if (not self.viewNode):
      logging.error("Error in getThreeDWidgetIndex: No View node selected. Returning 0.");
      return 0
    layoutManager = slicer.app.layoutManager()
    for threeDViewIndex in range(layoutManager.threeDViewCount):
      threeDViewNode = layoutManager.threeDWidget(threeDViewIndex).threeDView().mrmlViewNode()
      if (threeDViewNode == self.viewNode):
        return threeDViewIndex
    logging.error("Error in getThreeDWidgetIndex: Can't find the index. Selected View does not exist? Returning 0.");
    return 0

  # TRACK VIEW

  def bullseyeStart(self):
    logging.debug("Start Bullseye Mode")
    if (self.currentMode != self.currentModeOFF):
      logging.error("Cannot activate viewpoint until the current mode is set to off!")
      return

    if (not self.viewNode):
      logging.warning("A node is missing. Nothing will happen until the comboboxes have items selected.")
      return

    if (not self.bullseyeTransformNode):
      logging.warning("Transform node is missing. Nothing will happen until a transform node is provided as input.")
      return

    if (self.bullseyeForcedTarget and not self.bullseyeTargetModelNode):
      logging.error("Error in bullseyeSetTargetModelNode: No targetModelNode provided as input when forced target is set. Check input parameters.")
      return

    self.currentMode = self.currentModeBULLSEYE
    self.bullseyeAddObservers()
    self.bullseyeUpdate()

  def bullseyeStop(self):
    logging.debug("Stop Viewpoint Mode")
    if (self.currentMode != self.currentModeBULLSEYE):
      logging.error("bullseyeStop was called, but viewpoint mode is not BULLSEYE. No action performed.")
      return
    self.currentMode = self.currentModeOFF
    self.bullseyeRemoveObservers();

  def bullseyeUpdate(self):
    # no logging - it slows Slicer down a *lot*

    # Need to set camera attributes according to the concatenated transform
    toolCameraToRASTransform = vtk.vtkGeneralTransform()
    self.bullseyeTransformNode.GetTransformToWorld(toolCameraToRASTransform)

    cameraOriginInRASMm = self.bullseyeComputeCameraOriginInRASMm(toolCameraToRASTransform)
    focalPointInRASMm = self.bullseyeComputeCameraFocalPointInRASMm(toolCameraToRASTransform)
    upDirectionInRAS = self.bullseyeComputeCameraUpDirectionInRAS(toolCameraToRASTransform,cameraOriginInRASMm,focalPointInRASMm)

    self.bullseyeSetCameraParameters(cameraOriginInRASMm,focalPointInRASMm,upDirectionInRAS)

  def bullseyeAddObservers(self): # mostly copied from PositionErrorMapping.py in PLUS
    logging.debug("Adding observers...")
    transformModifiedEvent = 15000
    transformNode = self.bullseyeTransformNode
    while transformNode:
      logging.debug("Add observer to {0}".format(transformNode.GetName()))
      self.bullseyeTransformNodeObserverTags.append([transformNode, transformNode.AddObserver(transformModifiedEvent, self.bullseyeOnTransformModified)])
      transformNode = transformNode.GetParentTransformNode()
    logging.debug("Done adding observers")

  def bullseyeRemoveObservers(self):
    logging.debug("Removing observers...")
    for nodeTagPair in self.bullseyeTransformNodeObserverTags:
      nodeTagPair[0].RemoveObserver(nodeTagPair[1])
    logging.debug("Done removing observers")

  def bullseyeOnTransformModified(self, observer, eventid):
    # no logging - it slows Slicer down a *lot*
    self.bullseyeUpdate()

  def bullseyeSetTransformNode(self, transformNode):
    self.bullseyeTransformNode = transformNode

  def bullseyeSetTargetModelNode(self, targetModelNode):
    if (self.bullseyeForcedTarget and not targetModelNode):
      logging.error("Error in bullseyeSetTargetModelNode: No targetModelNode provided as input. Check input parameters.")
      return
    self.bullseyeTargetModelNode = targetModelNode
    targetModel = targetModelNode.GetPolyData()
    targetModelBoundingBox = targetModel.GetBounds()
    # find the middle of the target model
    middleXInTumorMm = ( targetModelBoundingBox[0] + targetModelBoundingBox[1]) / 2
    middleYInTumorMm = ( targetModelBoundingBox[2] + targetModelBoundingBox[3]) / 2
    middleZInTumorMm = ( targetModelBoundingBox[4] + targetModelBoundingBox[5]) / 2
    middlePInTumorMm = 1 # represent as a homogeneous point
    middlePointInTumorMm3 = [middleXInTumorMm,middleYInTumorMm,middleZInTumorMm]
    middlePointInRASMm3 = [0,0,0]; # placeholder values
    targetModelNode.TransformPointToWorld(middlePointInTumorMm3,middlePointInRASMm3)
    # reduce dimensionality back to 3
    self.bullseyeTargetModelMiddleInRASMm = middlePointInRASMm3

  def bullseyeChangeTo3DOFMode(self):
    self.bullseyeForcedUpDirection = True
    self.bullseyeForcedTarget = True

  def bullseyeChangeTo5DOFMode(self):
    self.bullseyeForcedUpDirection = True
    self.bullseyeForcedTarget = False

  def bullseyeChangeTo6DOFMode(self):
    self.bullseyeForcedUpDirection = False
    self.bullseyeForcedTarget = False

  def bullseyeIsUpDirectionEqualTo(self, compareDirection):
    if (compareDirection[0]*self.bullseyeUpDirectionRAS[0]+
        compareDirection[1]*self.bullseyeUpDirectionRAS[1]+
        compareDirection[2]*self.bullseyeUpDirectionRAS[2] > 0.9999): # dot product close to 1
      return True;
    return False;

  def bullseyeSetCameraParallelProjection(self,newParallelProjectionState):
    logging.debug("bullseyeSetCameraParallelProjection")
    self.bullseyeCameraParallelProjection = newParallelProjectionState

  def bullseyeSetCameraViewAngleDeg(self,valueDeg):
    logging.debug("bullseyeSetCameraViewAngleDeg")
    self.bullseyeCameraViewAngleDeg = valueDeg
    if (self.currentMode == self.currentModeBULLSEYE):
      self.bullseyeUpdate()

  def bullseyeSetCameraParallelScale(self,newScale):
    logging.debug("bullseyeSetCameraParallelScale")
    self.bullseyeCameraParallelScale = newScale
    if (self.currentMode == self.currentModeBULLSEYE):
      self.bullseyeUpdate()

  def bullseyeSetCameraXPosMm(self,valueMm):
    logging.debug("bullseyeSetCameraXPosMm")
    self.bullseyeCameraXPosMm = valueMm
    if (self.currentMode == self.currentModeBULLSEYE):
      self.bullseyeUpdate()

  def bullseyeSetCameraYPosMm(self,valueMm):
    logging.debug("bullseyeSetCameraYPosMm")
    self.bullseyeCameraYPosMm = valueMm
    if (self.currentMode == self.currentModeBULLSEYE):
      self.bullseyeUpdate()

  def bullseyeSetCameraZPosMm(self,valueMm):
    logging.debug("bullseyeSetCameraZPosMm")
    self.bullseyeCameraZPosMm = valueMm
    if (self.currentMode == self.currentModeBULLSEYE):
      self.bullseyeUpdate()

  def bullseyeSetUpDirectionRAS(self,vectorInRAS):
    logging.debug("bullseyeSetUpDirectionRAS")
    self.bullseyeUpDirectionRAS = vectorInRAS
    if (self.currentMode == self.currentModeBULLSEYE):
      self.bullseyeUpdate()

  def bullseyeComputeCameraOriginInRASMm(self, toolCameraToRASTransform):
    # Need to get camera origin and axes from camera coordinates into Slicer RAS coordinates
    cameraOriginInToolCameraMm = [self.bullseyeCameraXPosMm,self.bullseyeCameraYPosMm,self.bullseyeCameraZPosMm]
    cameraOriginInRASMm = [0,0,0] # placeholder values
    toolCameraToRASTransform.TransformPoint(cameraOriginInToolCameraMm,cameraOriginInRASMm)
    return cameraOriginInRASMm

  def bullseyeComputeCameraFocalPointInRASMm(self, toolCameraToRASTransform):
    focalPointInRASMm = [0,0,0]; # placeholder values
    if (self.bullseyeForcedTarget == True):
      focalPointInRASMm = self.bullseyeTargetModelMiddleInRASMm
    else:
      # camera distance depends on slider, but lies in -z (which is the direction that the camera is facing)
      focalPointInToolCameraMm = [self.bullseyeCameraXPosMm,self.bullseyeCameraYPosMm,self.bullseyeCameraZPosMm-200] # The number 200 mm is arbitrary. TODO: Change so that this is the camera-tumor distance
      focalPointInRASMm = [0,0,0] # placeholder values
      toolCameraToRASTransform.TransformPoint(focalPointInToolCameraMm,focalPointInRASMm)
    return focalPointInRASMm

  def bullseyeComputeCameraProjectionDirectionInRAS(self, cameraOriginInRASMm, focalPointInRASMm):
    math = vtk.vtkMath()
    directionFromOriginToFocalPointRAS = [0,0,0] # placeholder values
    math.Subtract(focalPointInRASMm,cameraOriginInRASMm,directionFromOriginToFocalPointRAS)
    math.Normalize(directionFromOriginToFocalPointRAS)
    numberDimensions = 3;
    lengthMm = math.Norm(directionFromOriginToFocalPointRAS,numberDimensions)
    epsilon = 0.0001
    if (lengthMm < epsilon):
      logging.warning("Warning: bullseyeComputeCameraProjectionDirectionInRAS() is computing a zero vector. Check target model? Using [0,0,-1] as target direction.")
      directionFromOriginToFocalPointRAS = [0,0,-1];
    return directionFromOriginToFocalPointRAS

  def bullseyeComputeCameraUpDirectionInRAS(self, toolCameraToRASTransform, cameraOriginInRASMm, focalPointInRASMm):
    upDirectionInRAS = [0,0,0] # placeholder values
    if (self.bullseyeForcedUpDirection == True):
      math = vtk.vtkMath()
      # cross product of forwardDirectionInRAS vector with upInRAS vector is the rightDirectionInRAS vector
      upInRAS = self.bullseyeUpDirectionRAS
      forwardDirectionInRAS = self.bullseyeComputeCameraProjectionDirectionInRAS(cameraOriginInRASMm, focalPointInRASMm)
      rightDirectionInRAS = [0,0,0] # placeholder values
      math.Cross(forwardDirectionInRAS,upInRAS,rightDirectionInRAS)
      numberDimensions = 3;
      lengthMm = math.Norm(rightDirectionInRAS,numberDimensions)
      epsilon = 0.0001
      if (lengthMm < epsilon): # must check for this case
        logging.warning("Warning: length of cross product in bullseyeComputeCameraUpDirectionInRAS is zero. Workaround used")
        backupUpDirectionInRAS = [1,1,1] # if the previous cross product was zero, then this shouldn't be
        math.Normalize(backupUpDirectionInRAS)
        upInRAS = backupUpDirectionInRAS
        math.Cross(forwardDirectionInRAS,upInRAS,rightDirectionInRAS)
      math.Normalize(rightDirectionInRAS)
      # now compute the cross product between the rightDirectionInRAS and forwardDirectionInRAS directions to get a corrected up vector
      upDirectionInRAS = [0,0,0] # placeholder values
      math.Cross(rightDirectionInRAS,forwardDirectionInRAS,upDirectionInRAS)
      math.Normalize(upDirectionInRAS)
    else:
      upDirectionInToolCamera = [0,1,0] # standard up direction in OpenGL
      dummyPoint = [0,0,0] # Needed by the TransformVectorAtPoint function
      toolCameraToRASTransform.TransformVectorAtPoint(dummyPoint,upDirectionInToolCamera,upDirectionInRAS)
    return upDirectionInRAS

  def bullseyeSetCameraParameters(self,cameraOriginInRASMm,focalPointInRASMm,upDirectionInRAS):
    viewName = self.viewNode.GetName()
    cameraNode = self.getCameraNode(viewName)
    camera = cameraNode.GetCamera()
    if (self.bullseyeCameraParallelProjection == False):
      camera.SetViewAngle(self.bullseyeCameraViewAngleDeg)
    elif (self.bullseyeCameraParallelProjection == True):
      camera.SetParallelScale(self.bullseyeCameraParallelScale)
    else:
      logging.error("Error in Viewpoint: cameraParallelProjection is not 0 or 1. No projection mode has been set! No updates are being performed.")
      return
    # Parallel (a.k.a. orthographic) / perspective projection mode is stored in the view node.
    # Change it in the view node instead of directly in the camera VTK object
    # (if we changed the projection mode in the camera VTK object then the next time the camera is updated from the view node
    # the rendering mode is reset to the value stored in the view node).
    viewNode = slicer.mrmlScene.GetNodeByID(cameraNode.GetActiveTag())
    viewNodeParallelProjection = (viewNode.GetRenderMode() == slicer.vtkMRMLViewNode.Orthographic)
    if viewNodeParallelProjection != self.bullseyeCameraParallelProjection:
      viewNode.SetRenderMode(slicer.vtkMRMLViewNode.Orthographic if self.bullseyeCameraParallelProjection else slicer.vtkMRMLViewNode.Perspective)

    camera.SetPosition(cameraOriginInRASMm)
    camera.SetFocalPoint(focalPointInRASMm)
    camera.SetViewUp(upDirectionInRAS)

    self.resetCameraClippingRange() # without this line, some objects do not appear in the 3D view

  # AUTO-CENTER

  def autoCenterStart(self):
    if (self.currentMode != self.currentModeOFF):
      logging.error("Viewpoints is already active! Can't activate auto-center mode until the current mode is off!")
      return
    if not self.viewNode:
      logging.warning("View node not set. Will not proceed until view node is selected.")
      return
    if not self.autoCenterModelNode:
      logging.warning("Model node not set. Will not proceed until model node is selected.")
      return
    self.autoCenterSetModelTargetPositionViewport()
    self.autoCenterSystemTimeAtLastUpdateSeconds = time.time()
    nextUpdateTimerMilliseconds = self.autoCenterUpdateRateSeconds * 1000
    qt.QTimer.singleShot(nextUpdateTimerMilliseconds ,self.autoCenterUpdate)

    self.currentMode = self.currentModeAUTOCENTER

  def autoCenterStop(self):
    logging.debug("autoCenterStop")
    if (self.currentMode != self.currentModeAUTOCENTER):
      logging.error("autoCenterStop was called, but viewpoint mode is not AUTOCENTER. No action performed.")
      return
    self.currentMode = self.currentModeOFF

  def autoCenterUpdate(self):
    if (self.currentMode != self.currentModeAUTOCENTER):
      return

    deltaTimeSeconds = time.time() - self.autoCenterSystemTimeAtLastUpdateSeconds
    self.autoCenterSystemTimeAtLastUpdateSeconds = time.time()

    self.autoCenterTimeInStateSeconds = self.autoCenterTimeInStateSeconds + deltaTimeSeconds

    self.autoCenterUpdateModelInSafeZone()
    self.autoCenterApplyStateMachine()

    nextUpdateTimerMilliseconds = self.autoCenterUpdateRateSeconds * 1000
    qt.QTimer.singleShot(nextUpdateTimerMilliseconds ,self.autoCenterUpdate)

  def autoCenterApplyStateMachine(self):
    if (self.autoCenterState == self.autoCenterStateUNSAFE and self.autoCenterModelInSafeZone):
      self.autoCenterState = self.autoCenterStateSAFE
      self.autoCenterTimeInStateSeconds = 0
    if (self.autoCenterState == self.autoCenterStateSAFE and not self.autoCenterModelInSafeZone):
      self.autoCenterState = self.autoCenterStateUNSAFE
      self.autoCenterTimeInStateSeconds = 0
    if (self.autoCenterState == self.autoCenterStateUNSAFE and self.autoCenterTimeInStateSeconds >= self.autoCenterTimeUnsafeToAdjustMaximumSeconds):
      self.autoCenterSetCameraTranslationParameters()
      self.autoCenterState = self.autoCenterStateADJUST
      self.autoCenterTimeInStateSeconds = 0
    if (self.autoCenterState == self.autoCenterStateADJUST):
      self.autoCenterTranslateCamera()
      if (self.autoCenterTimeInStateSeconds >= self.autoCenterTimeAdjustToRestMaximumSeconds):
        self.autoCenterState = self.autoCenterStateREST
        self.autoCenterTimeInStateSeconds = 0
    if (self.autoCenterState == self.autoCenterStateREST and self.autoCenterTimeInStateSeconds >= self.autoCenterTimeRestToSafeMaximumSeconds):
      self.autoCenterState = self.autoCenterStateSAFE
      self.autoCenterTimeInStateSeconds = 0

  def autoCenterUpdateModelInSafeZone(self):
    if (self.autoCenterState == self.autoCenterStateADJUST or
        self.autoCenterState == self.autoCenterStateREST):
      return
    pointsRas = self.autoCenterGetModelCurrentBoundingBoxPointsRas()
    # Assume we are safe, until shown otherwise
    foundSafe = True
    for pointRas in pointsRas:
      coordsNormalizedViewport = self.convertRasToViewport(pointRas)
      XNormalizedViewport = coordsNormalizedViewport[0]
      YNormalizedViewport = coordsNormalizedViewport[1]
      ZNormalizedViewport = coordsNormalizedViewport[2]
      if ( XNormalizedViewport > self.autoCenterSafeXMaximumNormalizedViewport or
           XNormalizedViewport < self.autoCenterSafeXMinimumNormalizedViewport or
           YNormalizedViewport > self.autoCenterSafeYMaximumNormalizedViewport or
           YNormalizedViewport < self.autoCenterSafeYMinimumNormalizedViewport or
           ZNormalizedViewport > self.autoCenterSafeZMaximumNormalizedViewport or
           ZNormalizedViewport < self.autoCenterSafeZMinimumNormalizedViewport ):
        foundSafe = False
        break
    self.autoCenterModelInSafeZone = foundSafe

  def autoCenterSetModelTargetPositionViewport(self):
    self.autoCenterModelTargetPositionViewport = [(self.autoCenterSafeXMinimumNormalizedViewport + self.autoCenterSafeXMaximumNormalizedViewport)/2.0,
                                        (self.autoCenterSafeYMinimumNormalizedViewport + self.autoCenterSafeYMaximumNormalizedViewport)/2.0,
                                        (self.autoCenterSafeZMinimumNormalizedViewport + self.autoCenterSafeZMaximumNormalizedViewport)/2.0]

  def autoCenterSetCameraTranslationParameters(self):
    viewName = self.viewNode.GetName()
    cameraNode = self.getCameraNode(viewName)
    cameraPosRas = [0,0,0]
    cameraNode.GetPosition(cameraPosRas)
    self.autoCenterBaseCameraPositionRas = cameraPosRas
    cameraFocRas = [0,0,0]
    cameraNode.GetFocalPoint(cameraFocRas)
    self.autoCenterBaseCameraFocalPointRas = cameraFocRas

    # find the translation in RAS
    modelCurrentPositionCamera = self.autoCenterGetModelCurrentCenterCamera()
    modelTargetPositionCamera = self.autoCenterGetModelTargetPositionCamera()
    cameraTranslationCamera = [0,0,0]
    if self.autoCenterAdjustX:
      cameraTranslationCamera[0] = modelCurrentPositionCamera[0] - modelTargetPositionCamera[0]
    if self.autoCenterAdjustY:
      cameraTranslationCamera[1] = modelCurrentPositionCamera[1] - modelTargetPositionCamera[1]
    if self.autoCenterAdjustZ:
      cameraTranslationCamera[2] = modelCurrentPositionCamera[2] - modelTargetPositionCamera[2]
    self.autoCenterBaseCameraTranslationRas = self.convertVectorCameraToRas(cameraTranslationCamera)

  def autoCenterTranslateCamera(self):
    # linear interpolation between base and target positions, based on the timer
    weightTarget = 1 # default value
    if (self.autoCenterTimeAdjustToRestMaximumSeconds != 0):
      weightTarget = self.autoCenterTimeInStateSeconds / self.autoCenterTimeAdjustToRestMaximumSeconds
    if (weightTarget > 1):
      weightTarget = 1
    cameraNewPositionRas = [0,0,0]
    cameraNewFocalPointRas = [0,0,0]
    for i in range(3):
      translation = weightTarget * self.autoCenterBaseCameraTranslationRas[i]
      cameraNewPositionRas[i] = translation + self.autoCenterBaseCameraPositionRas[i]
      cameraNewFocalPointRas[i] = translation + self.autoCenterBaseCameraFocalPointRas[i]
    viewName = self.viewNode.GetName()
    cameraNode = self.getCameraNode(viewName)
    cameraNode.SetPosition(cameraNewPositionRas)
    cameraNode.SetFocalPoint(cameraNewFocalPointRas)
    self.resetCameraClippingRange()

  def autoCenterGetModelCurrentCenterRas(self):
    modelBoundsRas = [0,0,0,0,0,0]
    self.autoCenterModelNode.GetRASBounds(modelBoundsRas)
    modelCenterX = (modelBoundsRas[0] + modelBoundsRas[1]) / 2
    modelCenterY = (modelBoundsRas[2] + modelBoundsRas[3]) / 2
    modelCenterZ = (modelBoundsRas[4] + modelBoundsRas[5]) / 2
    modelPosRas = [modelCenterX, modelCenterY, modelCenterZ]
    return modelPosRas

  def autoCenterGetModelCurrentCenterCamera(self):
    modelCenterRas = self.autoCenterGetModelCurrentCenterRas()
    modelCenterCamera = self.convertPointRasToCamera(modelCenterRas)
    return modelCenterCamera

  def autoCenterGetModelCurrentBoundingBoxPointsRas(self):
    pointsRas = []
    boundsRas = [0,0,0,0,0,0]
    self.autoCenterModelNode.GetRASBounds(boundsRas)
    # permute through the different combinations of x,y,z; min,max
    for x in [0,1]:
      for y in [0,1]:
        for z in [0,1]:
          pointRas = []
          pointRas.append(boundsRas[0+x])
          pointRas.append(boundsRas[2+y])
          pointRas.append(boundsRas[4+z])
          pointsRas.append(pointRas)
    return pointsRas

  def autoCenterGetModelTargetPositionRas(self):
    return self.convertViewportToRas(self.autoCenterModelTargetPositionViewport)

  def autoCenterGetModelTargetPositionCamera(self):
    modelTargetPositionRas = self.autoCenterGetModelTargetPositionRas()
    modelTargetPositionCamera = self.convertPointRasToCamera(modelTargetPositionRas)
    return modelTargetPositionCamera

  def autoCenterSetSafeXMinimum(self, val):
    self.autoCenterSafeXMinimumNormalizedViewport = val

  def autoCenterSetSafeXMaximum(self, val):
    self.autoCenterSafeXMaximumNormalizedViewport = val

  def autoCenterSetSafeYMinimum(self, val):
    self.autoCenterSafeYMinimumNormalizedViewport = val

  def autoCenterSetSafeYMaximum(self, val):
    self.autoCenterSafeYMaximumNormalizedViewport = val

  def autoCenterSetSafeZMinimum(self, val):
    self.autoCenterSafeZMinimumNormalizedViewport = val

  def autoCenterSetSafeZMaximum(self, val):
    self.autoCenterSafeZMaximumNormalizedViewport = val

  def autoCenterSetAdjustX(self, val):
    self.autoCenterAdjustX = val

  def autoCenterSetAdjustY(self, val):
    self.autoCenterAdjustY = val

  def autoCenterSetAdjustZ(self, val):
    self.autoCenterAdjustZ = val

  def autoCenterSetAdjustXTrue(self):
    self.autoCenterAdjustX = True

  def autoCenterSetAdjustXFalse(self):
    self.autoCenterAdjustX = False

  def autoCenterSetAdjustYTrue(self):
    self.autoCenterAdjustY = True

  def autoCenterSetAdjustYFalse(self):
    self.autoCenterAdjustY = False

  def autoCenterSetAdjustZTrue(self):
    self.autoCenterAdjustZ = True

  def autoCenterSetAdjustZFalse(self):
    self.autoCenterAdjustZ = False

  def autoCenterSetTimeUnsafeToAdjustMaximumSeconds(self, val):
    self.autoCenterTimeUnsafeToAdjustMaximumSeconds = val

  def autoCenterSetTimeAdjustToRestMaximumSeconds(self, val):
    self.autoCenterTimeAdjustToRestMaximumSeconds = val

  def autoCenterSetTimeRestToSafeMaximumSeconds(self, val):
    self.autoCenterTimeRestToSafeMaximumSeconds = val

  def autoCenterSetUpdateRateSeconds(self, val):
    self.autoCenterUpdateRateSeconds = val

  def autoCenterSetModelNode(self, node):
    self.autoCenterModelNode = node
