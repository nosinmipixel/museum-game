"""
quiz_button_logic.py

Manages quiz button interaction with ray casting, visual effects, and answer handling.

This script handles the interactive buttons for the quiz system, detecting mouse
hover and click, applying visual effects, and sending the selected answer to
quiz_module for processing.

Main Features:
    1. Ray casting based mouse detection using Camera.Hud
    2. Visual effects (scale, tint) for idle, hover, and click states
    3. Warmup timer to prevent accidental clicks immediately after display
    4. Mutual exclusion (only one button can be clicked per quiz)
    5. Automatic disabling of all buttons after a selection
    6. Integration with quiz_module for answer processing
    7. Answer ID mapping (1, 2, 3) for true/false or multiple choice

Setup:
    Connect to Logic Bricks as Python controller with module 'quiz_button_logic.main'
    Requires three buttons named: Button.Quiz.True, Button.Quiz.False.1, Button.Quiz.False.2
    Each button must have an 'answer_id' property (1, 2, or 3)

Configurable Variables:
    DEBUG (bool): Enable debug logging (default: False)
    WARMUP_TIME (float): Seconds to wait before accepting clicks (default: 0.5)
    HOVER_SCALE (float): Scale factor when mouse is over (default: 1.1)
    BASE_SCALE (float): Normal scale (default: 1.0)
    RAY_CAMERA_NAME (str): Camera for ray casting (default: 'Camera.Hud')
    RAY_DISTANCE (float): Maximum ray casting distance (default: 1000.0)
    IDLE_TINT (tuple): RGBA color for idle state (default: (1.00, 1.00, 1.00, 1.0))
    OVER_TINT (tuple): RGBA color for hover state (default: (0.50, 1.00, 0.00, 1.0))
    CLICK_TINT (tuple): RGBA color for click state (default: (0.68, 0.68, 0.68, 1.0))

Notes:
    - Buttons are automatically disabled after one is clicked
    - Answer IDs: 1 = True/Correct, 2 = False/Incorrect, 3 = False/Incorrect
    - Uses logic.globalDict to cache quiz_module reference
    - Reset_all_buttons function is called by npc_dialog_module_a.py
    - Click sound is played via 'sound_fx.play' message

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
__description__ = "Manages quiz button interaction with ray casting and visual effects"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic
from bge import events
import math

# =============================================================================
# CONFIGURATION
# =============================================================================
DEBUG = False  # Can be enabled if debugging is needed
WARMUP_TIME = 0.5  # Seconds to wait before accepting clicks

# Visual effects
HOVER_SCALE = 1.1
BASE_SCALE = 1.0
RAY_CAMERA_NAME = "Camera.Hud" 
RAY_DISTANCE = 1000.0

# Tinting system (from first script)
IDLE_TINT = (1.00, 1.00, 1.00, 1.0)
OVER_TINT = (0.50, 1.00, 0.00, 1.0)
CLICK_TINT = (0.68, 0.68, 0.68, 1.0)

# Quiz button configuration
QUIZ_BUTTON_NAMES = ["Button.Quiz.False.1", "Button.Quiz.False.2", "Button.Quiz.True"]

# =============================================================================
# RAY CASTING SYSTEM
# =============================================================================
def _is_mouse_over(owner):
    """
    Detects if camera ray hits 'owner' object or one of its children,
    using 'Camera.Hud' camera.
    """
    # If ANY button has been clicked, do not detect hover on ANY
    if _is_any_button_clicked():
        return False
        
    scn = logic.getCurrentScene()
    cam = scn.objects.get(RAY_CAMERA_NAME)
    if not cam:
        # This indicates a scene configuration error
        print(f"[QUIZ BUTTON] Error: Camera '{RAY_CAMERA_NAME}' not found.")
        return False
        
    # Get mouse coordinates (normalized 0.0 to 1.0)
    mx, my = logic.mouse.position
    
    # Ray casting
    try:
        # Try with property filter
        hit_obj = cam.getScreenRay(mx, my, RAY_DISTANCE, "")
    except:
        try:
            # Alternative version without filter
            hit_obj = cam.getScreenRay(mx, my, RAY_DISTANCE)
        except:
            return False
    
    if hit_obj == owner:
        return True
    
    # Check if hit object is a child (support for nested objects)
    try:
        parent = hit_obj.parent
        while parent:
            if parent == owner:
                return True
            parent = parent.parent
    except:
        pass
        
    return False

def _is_any_button_clicked():
    """Checks if ANY quiz button has been clicked."""
    scn = logic.getCurrentScene()
    for button_name in QUIZ_BUTTON_NAMES:
        button = scn.objects.get(button_name)
        if button and button.get("_button_clicked", False):
            return True
    return False

def _check_mouse_click(cont):
    """Checks if left mouse button was just clicked."""
    # If ANY button has already been clicked, do not detect clicks
    if _is_any_button_clicked():
        return False
        
    mouse = bge.logic.mouse
    # BEFORE (deprecated):
    # return mouse.events.get(bge.events.LEFTMOUSE) == bge.logic.KX_INPUT_JUST_ACTIVATED    
    # AFTER (corrected):
    try:
        left_mouse_input = mouse.inputs.get(bge.events.LEFTMOUSE)
        if left_mouse_input and left_mouse_input.activated:
            return True
    except:
        try:
            return mouse.events.get(bge.events.LEFTMOUSE, 0) == bge.logic.KX_INPUT_JUST_ACTIVATED
        except:
            pass
                
    return False

# =============================================================================
# WARMUP TIME MANAGEMENT
# =============================================================================
def _update_warmup(owner):
    """Updates warmup timer. Returns True if ready."""
    if "_warmup_timer" not in owner:
        owner["_warmup_timer"] = 0.0
        
    # Assuming 60 ticks per second (approximately 0.016s per frame)
    if owner["_warmup_timer"] < WARMUP_TIME:
        owner["_warmup_timer"] += 0.017 
        return False
    return True

# =============================================================================
# VISUAL EFFECTS
# =============================================================================
def _apply_tint(owner, rgba):
    """Applies color/tint to the object"""
    try:
        owner.color = list(rgba)
    except Exception as e:
        if DEBUG:
            print(f"[QUIZ BUTTON] Error applying tint: {e}")

def _apply_scale(owner, scale_factor):
    """Applies scale to the object while preserving base scale"""
    try:
        if "_base_scale" not in owner:
            owner["_base_scale"] = tuple(owner.localScale)
        base = owner["_base_scale"]
        owner.localScale = [base[0]*scale_factor, base[1]*scale_factor, base[2]*scale_factor]
    except Exception as e:
        if DEBUG:
            print(f"[QUIZ BUTTON] Error applying scale: {e}")

def _reset_scale(owner):
    """Restores original object scale"""
    try:
        if "_base_scale" in owner:
            owner.localScale = list(owner["_base_scale"])
    except Exception as e:
        if DEBUG:
            print(f"[QUIZ BUTTON] Error restoring scale: {e}")

def _apply_visual_state(owner, state):
    """Applies full visual state (tint + scale) according to state"""
    if state == "idle":
        _apply_tint(owner, IDLE_TINT)
        _reset_scale(owner)
    elif state == "over":
        _apply_tint(owner, OVER_TINT)
        _apply_scale(owner, HOVER_SCALE)
    elif state == "click":
        _apply_tint(owner, CLICK_TINT)
        _apply_scale(owner, HOVER_SCALE * 0.9)
    elif state == "clicked":
        _apply_tint(owner, CLICK_TINT)
        _reset_scale(owner)

def _perform_click_action(owner):
    """Calls the answer handling function in quiz_module.py."""
    
    # Mark THIS button as clicked
    owner["_button_clicked"] = True
    owner["_button_state"] = "clicked"
    _apply_visual_state(owner, "clicked")
    
    # Play click sound
    bge.logic.sendMessage("sound_fx.play", "sound_fx.play|mouse-click.ogg|volume=1.0")
    
    # Disable hover and clicks on ALL buttons
    _disable_all_buttons()
    
    # Use logic.globalDict to avoid reloading modules and access quiz_module
    if "quiz_module" not in logic.globalDict:
         try:
             # Dynamic module loading and injection into globalDict
             import quiz_module
             logic.globalDict["quiz_module"] = quiz_module
         except Exception as e:
             print(f"[QUIZ BUTTON] Error: Could not load quiz_module: {e}")
             return

    quiz_module_ref = logic.globalDict["quiz_module"]
    
    # The answer ID (1, 2 or 3) is injected by quiz_module when the quiz is shown.
    answer_id = owner.get("answer_id")
    
    if answer_id in [1, 2, 3]:
        # Call the new function in quiz_module to process the answer
        if isinstance(quiz_module_ref, dict) and "handle_quiz_choice_by_id" in quiz_module_ref:
            quiz_module_ref["handle_quiz_choice_by_id"](answer_id)
        elif hasattr(quiz_module_ref, "handle_quiz_choice_by_id"):
             quiz_module_ref.handle_quiz_choice_by_id(answer_id)
        else:
             print("[QUIZ BUTTON] Error: 'handle_quiz_choice_by_id' not found in quiz_module.")
        
    else:
        print(f"[QUIZ BUTTON] Error: Button {owner.name} without valid 'answer_id'. Click ignored.")

def _disable_all_buttons():
    """Disables all quiz buttons."""
    scn = logic.getCurrentScene()
    for button_name in QUIZ_BUTTON_NAMES:
        button = scn.objects.get(button_name)
        if button:
            # Only mark as clicked if not already clicked (to avoid resetting animations)
            if not button.get("_button_clicked", False):
                button["_button_clicked"] = True
                button["_button_state"] = "clicked"
                # Apply visual state with tint
                _apply_visual_state(button, "clicked")

def _reset_all_buttons():
    """Resets the state of ALL buttons (called when hidden/moved off screen)."""
    scn = logic.getCurrentScene()
    for button_name in QUIZ_BUTTON_NAMES:
        button = scn.objects.get(button_name)
        if button:
            button["_button_clicked"] = False
            button["_button_state"] = "idle"
            button["_warmup_timer"] = 0.0  # Reset timer
            # Apply visual state with tint
            _apply_visual_state(button, "idle")

# =============================================================================
# MAIN LOGIC (Executed in loop as Module)
# =============================================================================
def main(cont):
    owner = cont.owner
    
    # --- Initialization ---
    if "_base_scale" not in owner:
        owner["_base_scale"] = tuple(owner.localScale)
        owner["_button_state"] = "idle"
        owner["_button_clicked"] = False
        owner["_warmup_timer"] = 0.0
        _apply_visual_state(owner, "idle")
        
    # --- Guard: If button is invisible (moved to 'Out'), reset state ---
    if not owner.visible:
        # Only reset if this specific button needs reset
        if owner.get("_button_clicked", True):
            pass  # Reset is handled in npc_dialog_module_a.py
        return

    # --- Guard: If ANY button has already been clicked, do not process input ---
    if _is_any_button_clicked():
        # If this button is not marked as clicked but ANOTHER is,
        # ensure this one also shows the correct state
        if not owner.get("_button_clicked", False):
            owner["_button_clicked"] = True
            owner["_button_state"] = "clicked"
            _apply_visual_state(owner, "clicked")
        return

    # --- Input detection (only if no button has been clicked) ---
    
    # 1. Update safety timer
    is_ready = _update_warmup(owner)
    
    mouse_over = _is_mouse_over(owner)
    mouse_click = False
    
    if mouse_over and is_ready:
        mouse_click = _check_mouse_click(cont)
    
    # --- Apply visual effects (only if no button has been clicked) ---
    previous_state = owner.get("_button_state", "idle")
    current_state = "over" if mouse_over else "idle"
    if mouse_over and mouse_click: 
        current_state = "click"
    
    if current_state != previous_state:
        _apply_visual_state(owner, current_state)
        owner["_button_state"] = current_state
    
    # --- Handle click (only if no button has been previously clicked) ---
    if mouse_over and mouse_click and not _is_any_button_clicked():
        _perform_click_action(owner)