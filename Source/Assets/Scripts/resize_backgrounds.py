"""
resize_backgrounds.py

Module for resizing background objects to fit the screen aspect ratio

This script adjusts the scale of UI background elements (such as vignettes and inventory backgrounds)
to match the current screen's aspect ratio, ensuring proper display across different resolutions.

Main Features:
    1. Detects current screen resolution and calculates aspect ratio
    2. Applies scaling factors for different aspect ratios (16:9, 4:3, 16:10)
    3. Adjusts vertical displacement for 4:3 aspect ratio
    4. Resizes specific background objects in the scene
    5. Uses Camera.Hud for orthographic scale reference

Setup:
    Connect in Logic Bricks as Python controller/module 'resize_backgrounds.resize_elements'
    Should be called every frame or on resolution change events

Configurable Variables:
    object_names (list): List of object names to resize (default: ["Vignette", "Background.Inventory"])
    scale_x (float): Horizontal scale multiplier (default: 1.0)
    scale_y (float): Vertical scale multiplier (default: 1.0)
    y_displacement (float): Vertical offset for 4:3 aspect ratio (default: 0.7)

Notes:
    - Requires Camera.Hud object to exist in the scene with ortho_scale > 0
    - Aspect ratio detection uses tolerance of 0.01 for floating point comparison
    - Only modifies worldScale property, not localScale
    - Default behavior for 16:9 and unknown aspect ratios applies no scaling

License: GPL-3.0-only (View LICENSE.txt)
UPBGE Compatible: 0.36, 0.44
"""

# =============================================================================
# METADATA
# =============================================================================
__author__ = "nosinmipixel"
__version__ = "0.1.0-alpha"
__license__ = "GPL-3.0-only"
__upbge_compatible__ = ["0.36", "0.44"]
__description__ = "Resizes background UI elements to match screen aspect ratio"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
import mathutils

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def resize_elements(cont):
    scene = bge.logic.getCurrentScene()
    
    camera_object = scene.objects.get("Camera.Hud")
    
    if camera_object and camera_object.ortho_scale > 0:
        res_x = bge.render.getWindowWidth()
        res_y = bge.render.getWindowHeight()
        
        # Calculate aspect ratio of current resolution
        aspect_ratio = res_x / res_y
        
        # Define original scale
        scale_x = 1.0
        scale_y = 1.0
        
        # Define original vertical offset
        y_displacement = 0.0
        
        # Conditional logic based on aspect ratio
        if abs(aspect_ratio - (16/9)) < 0.01:
            # Aspect ratio is 16:9, no action needed
            pass
        elif abs(aspect_ratio - (4/3)) < 0.01:
            # Aspect ratio is 4:3
            scale_y = 1.33
            y_displacement = 0.7
        elif abs(aspect_ratio - (16/10)) < 0.01:
            # Aspect ratio is 16:10
            scale_y = 1.13
            pass
        else:
            # For any other aspect ratio, do not adjust scale
            pass
            
        object_names = ["Vignette", "Background.Inventory"]
        
        for obj_name in object_names:
            target_object = scene.objects.get(obj_name)
            if target_object:
                target_object.worldScale = mathutils.Vector([scale_x, scale_y, 1.0])