# _HelperFile.py
Contains a collection of helper functions designed to facilitate workflow using 3D Slicer and Artisynth. It provides utilities for fiducial management, registration processes, model manipulation, plane handling for mandible resection, and interaction with Java-based VSP methods

## Overall Workflow
- Updated fiducial lists with added or removed points
- Registration transforms and calculated registration errors
- Clipped mandible models representing resected and non-resected bone
- Plane normals and origins saved to a text file
- Visual representations of RDP lines and segments with Slicer scene
- Transform nodes and model nodes for each bone segment
- Updated slice views displaying resection planes and anatomical structures

# _LengthErrorCode.py
This module provides functions for calculating geometric properties and errors related to bone segments in a surgical planning context, particularly focusing on length and angle measurements. It includes methods to find intersections between planes and 3D models, compute centroids, calculate segment lengths, and determine discrepancies between actual measurements and target values.

## Overall Workflow
- Segment point is calculated
- Segment length is calculated
- Error is analyzed to help identify misalignment

# CalculateResults.py
The module is designed to evaluate the accuracy of surgeries by comparing the planned surgical models and fiducials with the actual postoperative results. It provides tools for placing fiducials at specific anatomical landmarks, calculating measurements such as intercondylar width, mandible projection, and interangle width, and computing registration errors, Dice coefficient, Hausdorff distance, and plate-to-bone distances. This module is implemented within the 3D Slicer environment and leverages its visualization and computation capabilities to aid surgeons and researchers in assessing surgical outcomes.

## Overal Workflow
- Users interactively place fiducials on specific anatomical landmarks on both the planned and actual models
- The module calculates average points for each group of fiducials to obtain precise locations for measurements
- Intercondylar width, mandible projection, and interangle width are calculated
- Fidicial and model-to-model registrations are performed
- Converts the registered plan and actual models to segmentation nodes and computes the Dice coefficient and the 95th percentile Hausdorff distance to evaluate volumetric overlap and surface distance
- Calculates plate-to-bone distance
- Presents results

# CalculateVSP.py
The module is designed for planning mandibular reconstruction surgeries using Virtual Surgical Planning (VSP) techniques within the 3D Slicer environment. It integrates with Java-based Artisynth methods to automate the reconstruction process, allowing users to define resection planes, place fiducials on the fibula, and compute the optimal placement of fibula segments to reconstruct the mandible. The module provides an interactive user interface for setting parameters, running the VSP computation, visualizing the planned reconstruction, and managing the generated segments.

## Overall Workflow
- Placing fiducial to fibula to mark starting point of reconstruction
- Input reconstruction parameters are minimum segment length, segment separation, maximum number of segments, and (optionally) direction of reconstruction
- Run VSP by connection JVM and use Artisynth classes for calculations
- Use visualization to generate and display in 3D scene (with color)
- Manage reconstruction with deletions or saves
- Navigate between tabs or modules for other tasks

# CutPlaneTesting.py
The module is a feature testing tool within the 3D Slicer environment designed to facilitate the exploration and validation of model registration, fiducial placement, and model clipping functionalities. It provides an interactive interface for users to perform paired point and surface registrations between physical and virtual models, define cut planes based on fiducial points or real-time tracking data, and generate clipped models by applying these planes. The module is particularly useful for applications that require precise alignment and manipulation of 3D models, such as surgical planning, simulation, and educational purposes.

# DecomposeTransforms.py
The module is a feature testing tool within the 3D Slicer environment designed to calculate and decompose the transformation between two 3D models. It allows users to select a source model and a target model, compute the transformation that aligns the source model to the target model using the Iterative Closest Point (ICP) algorithm, and then decompose this transformation into its constituent translation and rotation components, including Euler angles. This module is particularly useful for quantifying the differences between models, such as preoperative and postoperative anatomical structures, or assessing the accuracy of registration and alignment processes.

# DisplacementKevin.py
The module is designed to capture and record the displacement (both translation and rotation) between two objects over time within the 3D Slicer environment. This is particularly useful in scenarios involving real-time tracking and navigation, such as surgical navigation systems or motion analysis. The module allows users to select an event transform (representing the movement or event of interest) and an object transform (representing the object being tracked), compute the relative displacement between them using the Iterative Closest Point (ICP) algorithm, and record this displacement over a specified duration. The displacement data is saved to output files in both full transformation matrix form and decomposed into translation and rotation components for further analysis.

# GuideSegmentCuts.py
This module assists in aligning cutting guides with planned cut planes, registering actual cuts, calculating errors, and adjusting the surgical plan if necessary. It integrates with optical tracking systems to provide real-time feedback and ensures that the bone segments are accurately prepared for transplantation.

# InverseKin.py
The module calculates the necessary actuator lengths and rotations required for the manipulator to reach a desired position and orientation in 3D space. This module is particularly useful for controlling robotic arms or platforms, such as a Stewart platform, which are used in surgical navigation, robotic surgery, and other applications requiring precise movement and positioning.

# ManageReconstruction.py
This module provides functionalities for resecting the mandible model based on user-defined planes, computing the virtual surgical plan (VSP), generating the necessary transformations for positioning fibular segments, and integrating with external Java-based computational tools for advanced calculations. It handles the clipping of models, transformation of coordinate systems, and preparation of models and planes required for precise surgical reconstruction.

# ManageRegistration.py
The module provides functionalities for registering patient anatomy to preoperative imaging data, ensuring that virtual surgical plans align accurately with the patient's actual anatomy during surgery. This module focuses on fiducial-based and surface-based registration methods, enabling the transformation of coordinate systems between the patient's anatomy, surgical instruments, and preoperative models. By handling fiducial placement, registration computation, and error estimation, it plays a vital role in achieving precise surgical outcomes.

# ManageSlicer.py
The module is a utility script that provides a collection of functions to facilitate various operations within the 3D Slicer environment, specifically tailored for surgical planning and navigation workflows. It focuses on tasks such as manipulating polydata, handling transformations, converting between data types, and performing geometric computations. By abstracting common operations into reusable functions, this module aids in maintaining clean code, improving readability, and promoting code reuse across different modules in the surgical planning suite.

# ManageUI.py
The module provides a collection of functions to simplify the creation of commonly used UI components such as buttons, labels, collapsible sections, and text inputs. Additionally, it offers methods for handling MRML nodes, including creation, retrieval, updating, and deletion of various node types like transforms and fiducials. By encapsulating repetitive UI and node management tasks, this module enhances code readability, maintainability, and promotes consistent UI design across different modules in the surgical planning suite.

# NavigationTesting.py and NavigationTestingKevin.py
The module provides functionalities to clip 3D models using markup planes, allowing users to segment a model into different parts based on defined planes. This is particularly useful in scenarios where precise model segmentation is required for analysis, simulation, or validation purposes. By integrating with the 3D Slicer environment, the module leverages existing tools and libraries to manipulate and visualize 3D models effectively.

# PlaceSegments.py

# ReconstructionWorkflow.py
The module provides a user interface for importing essential models and scans, setting up the scene, and guiding the user through the initial steps of the process. The module allows users to import mandible and fibula models, load CT scans, select the side of the fibula to use, and import necessary device models. Additionally, it provides instructions and tools for contouring the mandible, which is a crucial step in defining the reconstruction plan.

# PlaceSegments.py
The module provides both freehand and guided positioning methods, enabling users to position bone segments relative to each other and within the mandible with the aid of visual and numerical guidance. It integrates inverse kinematics calculations to provide real-time adjustments required to achieve the desired alignment, enhancing the accuracy and efficiency of the surgical workflow

# RegisterFibula.py
This module focuses on registering the patient's fibula to a preoperative virtual model to ensure accurate placement and alignment during surgery. It provides functionalities for clipping the fibula model based on intraoperative measurements, performing paired-point and surface registrations, and verifying the registration quality. By integrating with other modules in the workflow, it facilitates a streamlined and precise surgical process.

# RegisterMandible.py
This module focuses on registering the patient's mandible to a preoperative virtual model to ensure precise alignment during surgery. It guides the user through attaching the mandible fixation device, performing both paired-point and surface registrations, and verifying the quality of the registration. By accurately registering the mandible, the module sets the foundation for subsequent surgical steps, such as osteotomy planning and fibula reconstruction.

# RegisterTools.py
This module provides functionalities for both paired-point and surface-based registration methods, allowing users to register any tool model by placing virtual and physical fiducials. It supports real-time tracking and updates to the tool's position and orientation, enhancing the precision and reliability of surgical navigation.

# ResectMandible.py
This module focuses on the resection of the mandible, allowing surgeons to plan and execute precise osteotomies (surgical bone cuts) based on patient-specific data. It provides tools to visualize and adjust the mandible contour, plan the osteotomy locations using CT scans, and register the actual cut planes to the virtual model. By enabling accurate resection planning and execution, this module lays the groundwork for subsequent reconstruction steps using fibula grafts or other reconstructive methods.

# Viewpoint.py
The module is a logic component within the 3D Slicer environment designed to dynamically control and adjust the camera view in 3D renderings. It allows for automatic camera adjustments based on the position and orientation of tracked tools or models, enhancing visualization during image-guided interventions or surgical navigation. The module provides bullseye mode and auto-center mode.

# Integration Notes
- Integration would likely go into RegisterMandible, RegisterTools, and RegisterFibula
- Output of CV code should be fiducial points or transform nodes
- Outputs must be RAS coordinate system