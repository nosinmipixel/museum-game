"""
exhibition_button.py

Manages the close button for the exhibition interface with optimized image handling.

This script handles the visual interaction (hover, click) and functionality
of the exhibition close button, including hiding exhibition images and cleaning up
exhibition state when closed.

Main Features:
    1. Ray casting based mouse detection with exhibition state filtering
    2. Visual effects (scale, tint) for idle, hover, and click states
    3. HUD positioning system to show/hide exhibition interface
    4. Optimized image hiding via parent-child relationship
    5. Complete exhibition resource cleanup
    6. Integration with game_access architecture

Setup:
    Connect to Logic Bricks as Python controller with module 'exhibition_button.main'
    Button requires property: 'Button.Close.Exhibition'

Configurable Variables:
    DEBUG (bool): Enable debug logging (default: True)
    HOVER_SCALE (float): Scale factor when mouse is over button (default: 1.2)
    NORMAL_SCALE (float): Normal button scale (default: 1.0)
    IDLE_TINT (tuple): RGBA color for idle state (default: (1.00, 1.00, 1.00, 1.0))
    OVER_TINT (tuple): RGBA color for hover state (default: (0.82, 0.82, 0.82, 1.0))
    CLICK_TINT (tuple): RGBA color for click state (default: (0.68, 0.68, 0.68, 1.0))
    EXHIBITION_MAIN (str): Main exhibition HUD object (default: 'Empty.Exhibition.Main')
    EXHIBITION_POS_OUT (str): Position when hidden (default: 'Empty.Exhibition.Out')
    IMAGE_PARENT_EMPTY (str): Empty containing all exhibition images (default: 'Empty.Img.Exhib')
    IMAGE_OBJECT_PREFIX (str): Prefix for image objects (default: 'Img.')
    RAY_CAMERA_NAME (str): Camera for ray casting (default: 'Camera.Hud')
    RAY_DISTANCE (float): Maximum ray casting distance (default: 10000.0)

Notes:
    - Ray casting filters objects when exhibition is open to prevent world object detection
    - Images are hidden via parent-child relationship for efficiency
    - Requires game_access module for HUD text clearing
    - Global flags 'exhibition_open' and 'current_exhibition_id' are cleaned up on close
    - Button should only be visible/active when exhibition is open

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
__description__ = "Manages the close button for the exhibition interface"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic

try:
    import game_access
    HAS_GAME_ACCESS = True
except ImportError:
    HAS_GAME_ACCESS = False

# =============================================================================
# LOGGING
# =============================================================================
def _log(*args):
    print("[exhibition_button]", *args)

# =============================================================================
# CONFIGURATION
# =============================================================================
DEBUG = True

# Visual effects
HOVER_SCALE = 1.2
NORMAL_SCALE = 1.0
IDLE_TINT = (1.00, 1.00, 1.00, 1.0)
OVER_TINT = (0.82, 0.82, 0.82, 1.0)
CLICK_TINT = (0.68, 0.68, 0.68, 1.0)

# Positioning objects
EXHIBITION_MAIN = "Empty.Exhibition.Main"
EXHIBITION_POS_OUT = "Empty.Exhibition.Out"

# Optimization: Search images as children of this empty
IMAGE_PARENT_EMPTY = "Empty.Img.Exhib"
IMAGE_OBJECT_PREFIX = "Img."

# Camera for ray casting
RAY_CAMERA_NAME = "Camera.Hud"
RAY_DISTANCE = 10000.0

# =============================================================================
# RAY CASTING SYSTEM - SOLUTION POINT 2
# =============================================================================
def _hit_under_mouse():
    """Detects which object is under the mouse using ray casting
    Filters objects when exhibition is open to prevent detection
    of objects behind the UI
    """
    scn = logic.getCurrentScene()
    cam = scn.objects.get(RAY_CAMERA_NAME)
    if not cam:
        return None
    
    try:
        mx, my = logic.mouse.position
        
        # Get object hit by ray cast
        hit_obj = cam.getScreenRay(mx, my, RAY_DISTANCE, "")
        
        # NEW VERIFICATION - FILTERING
        # If exhibition is open, we only want to detect the close button
        if hit_obj and logic.globalDict.get("exhibition_open", False):
            # Check if object is the close button
            # The close button should be named "Button.Close.Exhibition"
            if hit_obj.name == "Button.Close.Exhibition":
                return hit_obj
            # If not the close button, ignore it (it was a world object)
            return None
        # END NEW VERIFICATION
        
        # Normal behavior when no exhibition is open
        return hit_obj
        
    except:
        try:
            # Fallback for older UPBGE versions
            return cam.getScreenRay(mx, my, RAY_DISTANCE)
        except:
            return None

def _belongs_to(hit_obj, owner):
    """Checks if the hit object belongs to this button"""
    if not hit_obj:
        return False
    if hit_obj == owner:
        return True
    try:
        parent = hit_obj.parent
        while parent:
            if parent == owner:
                return True
            parent = parent.parent
    except:
        pass
    return False

def _is_mouse_over(cont, own):
    """Checks if the mouse is over this button"""
    hit_obj = _hit_under_mouse()
    return _belongs_to(hit_obj, own)

# =============================================================================
# POSITIONING SYSTEM
# =============================================================================
def _move_to_position(object_name, target_name):
    """Moves an object to the position of another object"""
    scene = logic.getCurrentScene()
    obj = scene.objects.get(object_name)
    target = scene.objects.get(target_name)
    
    if obj and target:
        _log(f"Moving {object_name} to {target_name}")
        obj.worldPosition = target.worldPosition.copy()
        obj.worldOrientation = target.worldOrientation.copy()
        return True
    else:
        _log(f"Could not move {object_name}")
        return False

def _hide_exhibition_hud():
    """Hides the exhibition HUD interface"""
    return _move_to_position(EXHIBITION_MAIN, EXHIBITION_POS_OUT)

# =============================================================================
# VISUAL EFFECTS
# =============================================================================
def _apply_tint(owner, rgba):
    """Applies a color/tint to the object"""
    try:
        r, g, b, a = rgba
        owner.color = [r, g, b, a]
    except:
        pass

def _apply_scale(owner, scale_factor):
    """Applies scale to the object"""
    try:
        if "_base_scale" not in owner:
            owner["_base_scale"] = tuple(owner.localScale)
        
        base_scale = owner["_base_scale"]
        owner.localScale = [
            base_scale[0] * scale_factor, 
            base_scale[1] * scale_factor, 
            base_scale[2] * scale_factor
        ]
    except:
        pass

def _reset_scale(owner):
    """Restores normal scale"""
    try:
        if "_base_scale" in owner:
            base_scale = owner["_base_scale"]
            owner.localScale = list(base_scale)
    except:
        pass

def _apply_visual_state(owner, state):
    """Applies visual effects according to state"""
    if state == "idle":
        _apply_tint(owner, IDLE_TINT)
        _reset_scale(owner)
    elif state == "over":
        _apply_tint(owner, OVER_TINT)
        _apply_scale(owner, HOVER_SCALE)
    elif state == "click":
        _apply_tint(owner, CLICK_TINT)
        _apply_scale(owner, HOVER_SCALE * 0.9)

# =============================================================================
# OPTIMIZED VISIBILITY SYSTEM (child-based search)
# =============================================================================

def _get_image_parent():
    """Gets Empty.Img.Exhib object that groups all images"""
    scene = logic.getCurrentScene()
    return scene.objects.get(IMAGE_PARENT_EMPTY)

def _hide_all_exhibition_images():
    """Hides all Img.* objects that are children of Empty.Img.Exhib"""
    img_parent = _get_image_parent()
    if not img_parent:
        if DEBUG: _log(f"Could not find {IMAGE_PARENT_EMPTY}")
        return False
    
    hidden_count = 0
    for child in img_parent.children:
        if child.name.startswith(IMAGE_OBJECT_PREFIX):
            try:
                child.visible = False
                hidden_count += 1
            except:
                pass
    
    if DEBUG and hidden_count > 0:
        _log(f"Hidden {hidden_count} image objects (children of {IMAGE_PARENT_EMPTY})")
    return hidden_count > 0

# =============================================================================
# CLEAR EXHIBITION TEXT
# =============================================================================
def _clear_exhibition_text():
    """Clears exhibition text from HUD"""
    _log("Clearing exhibition text")
    try:
        if HAS_GAME_ACCESS:
            game = game_access.get_game()
            if game and hasattr(game, 'hud_text'):
                game.hud_text.exhibition_text = ""
                _log("Exhibition text cleared (new architecture)")
            else:
                _log("game.hud_text not available")
        else:
            scene = logic.getCurrentScene()
            game_controller = scene.objects.get("Game.Controller")
            if game_controller:
                hud_text = game_controller.get("hud_text", None)
                if hud_text:
                    hud_text.exhibition_text = ""
                    _log("Exhibition text cleared (compatibility)")
                else:
                    _log("hud_text not available")
            else:
                _log("Game.Controller not found")
    except Exception as e:
        _log("Error clearing text:", e)

# =============================================================================
# COMPLETE EXHIBITION CLEANUP (OPTIMIZED)
# =============================================================================
def _cleanup_exhibition():
    """Cleans up all exhibition resources"""
    try:
        _log("Cleaning up exhibition completely")
        
        # 1. Clear text
        _clear_exhibition_text()
        
        # 2. Hide all images (searching as children)
        _hide_all_exhibition_images()
        
        # 3. Clear global flags
        keys_to_remove = ["exhibition_open", "current_exhibition_id"]
        for key in keys_to_remove:
            if key in logic.globalDict:
                del logic.globalDict[key]
                _log(f"Flag '{key}' removed")
        
        return True
        
    except Exception as e:
        _log(f"Error in cleanup_exhibition: {e}")
        return False

# =============================================================================
# MAIN BUTTON FUNCTION
# =============================================================================
def main(cont):
    """Handles the exhibition close button"""
    own = cont.owner
    
    # Additional verification: if no exhibition is open, button should do nothing
    if not logic.globalDict.get("exhibition_open", False):
        # Optionally hide the button or leave it inactive
        return
    
    mouse_over = _is_mouse_over(cont, own)
    
    mouse_click = False
    if mouse_over:
        mouse_click = logic.mouse.events.get(bge.events.LEFTMOUSE) == logic.KX_INPUT_JUST_ACTIVATED
    
    previous_state = own.get("_button_state", "idle")
    current_state = "over" if mouse_over else "idle"
    
    if mouse_over and mouse_click:
        current_state = "click"
    
    if current_state != previous_state:
        _apply_visual_state(own, current_state)
        own["_button_state"] = current_state
    
    if mouse_over and mouse_click:
        _log("EXHIBITION CLOSE BUTTON PRESSED")
        bge.logic.sendMessage("sound_fx.play", "sound_fx.play|mouse-click.ogg|volume=1.0")
        
        _apply_visual_state(own, "idle")
        own["_button_state"] = "idle"
        
        cleanup_success = _cleanup_exhibition()
        hide_success = _hide_exhibition_hud()
        
        if cleanup_success and hide_success:
            _log("Exhibition closed successfully")
        else:
            _log("Exhibition closed with some errors")

# =============================================================================
# INITIALIZATION
# =============================================================================
def init(cont):
    """Initializes the button"""
    own = cont.owner
    
    own["_base_scale"] = tuple(own.localScale)
    own["_button_state"] = "idle"
    _apply_visual_state(own, "idle")
    
    _log(f"Exhibition button initialized: {own.name}")