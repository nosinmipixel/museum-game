"""
intro_buttons.py

Manages introductory menu buttons with ray casting, visual effects, and sound.

This script handles button interactions on the intro/menu screen including
hover effects, click detection via ray casting, Z-position displacement for
proper layering, and click sound playback.

Main Features:
    1. Ray casting based mouse detection for buttons
    2. Visual effects (scale) for idle and hover states
    3. Z-position displacement for visible/invisible buttons
    4. Click sound playback using aud module
    5. Button action routing to Game.Controller
    6. Support for start, continue, reset, language selection buttons

Setup:
    Connect to Logic Bricks as Python controller with module 'intro_buttons.main'
    Requires 'Camera' object for ray casting

Configurable Variables:
    DEBUG (bool): Enable debug logging (default: False)
    HOVER_SCALE (float): Scale factor when mouse is over (default: 1.2)
    Z_OFFSET_VISIBLE (float): Z displacement for visible buttons (default: 0.1)
    RAY_CAMERA_NAME (str): Camera name for ray casting (default: 'Camera')
    RAY_DISTANCE (float): Maximum ray casting distance (default: 10000.0)
    CLICK_SOUND_PATH (str): Path to click sound file (default: '//Sounds/mouse-click.ogg')

Notes:
    - Buttons require proper naming: Button.Start, Button.Continue, Button.Reset,
      Button.Accept, Button.Cancel, Button.Lan.Es, Button.Lan.En, Button.Forward
    - Ray casting uses camera.getScreenRay for accurate mouse detection
    - Z-position is automatically managed based on button visibility
    - Sound uses aud module with fallback to logic.startSound
    - Button actions are stored in Game.Controller['button_action']

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
__description__ = "Manages introductory menu buttons with ray casting, visual effects, and sound"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic
from bge import events
import aud

# =============================================================================
# LOGGING
# =============================================================================
def _log(*args):
    """Logging function for debugging"""
    print("[intro_buttons]", *args)

# =============================================================================
# CONFIGURATION
# =============================================================================
DEBUG = False  # Keep True to see sound errors

# Visual effects
HOVER_SCALE = 1.2

# Z offset for ray casting
Z_OFFSET_VISIBLE = 0.1

# Camera for ray casting
RAY_CAMERA_NAME = "Camera"
RAY_DISTANCE = 10000.0

# Click sound
CLICK_SOUND_PATH = "//Sounds/mouse-click.ogg"

# =============================================================================
# Z POSITION MANAGEMENT
# =============================================================================
def _update_z_position(owner):
    """Updates object Z position based on visibility"""
    try:
        if "_original_z" not in owner:
            # Save original Z position
            owner["_original_z"] = owner.worldPosition.z
            owner["_z_displaced"] = False
            if DEBUG: _log(f"Saving original Z for {owner.name}: {owner['_original_z']}")
        
        if owner.visible:
            if not owner["_z_displaced"]:
                # Displace forward when visible
                original_z = owner["_original_z"]
                new_z = original_z + Z_OFFSET_VISIBLE
                owner.worldPosition.z = new_z
                owner["_z_displaced"] = True
                if DEBUG: _log(f"Displacing {owner.name} to Z={new_z}")
        else:
            if owner["_z_displaced"]:
                # Restore original position when invisible
                original_z = owner["_original_z"]
                owner.worldPosition.z = original_z
                owner["_z_displaced"] = False
                if DEBUG: _log(f"Restoring {owner.name} to Z={original_z}")
                
    except Exception as e:
        if DEBUG: _log(f"Error updating Z for {owner.name}: {e}")

# =============================================================================
# RAY CASTING SYSTEM
# =============================================================================
def _get_hit_object():
    """Detects which object is under the mouse using ray casting"""
    scene = logic.getCurrentScene()
    
    # Get camera
    camera = scene.objects.get(RAY_CAMERA_NAME)
    if not camera:
        if DEBUG: _log(f"Camera '{RAY_CAMERA_NAME}' not found")
        return None
    
    try:
        # Get mouse position
        mouse_pos = logic.mouse.position
        
        # Use getScreenRay which is more reliable for this task
        hit_obj = camera.getScreenRay(mouse_pos[0], mouse_pos[1], RAY_DISTANCE)
        
        if DEBUG and hit_obj:
            _log(f"Raycast hit: {hit_obj.name}")
        
        return hit_obj
        
    except Exception as e:
        if DEBUG: _log(f"Raycast error: {e}")
        return None

def _belongs_to(hit_obj, owner):
    """Checks if the hit object belongs to this button"""
    if not hit_obj:
        return False
    
    # Check if it's the object itself
    if hit_obj == owner:
        if DEBUG: _log(f"Direct hit on {owner.name}")
        return True
    
    # Check parent hierarchy
    try:
        parent = hit_obj.parent
        while parent:
            if parent == owner:
                if DEBUG: _log(f"Hit on child of {owner.name}")
                return True
            parent = parent.parent
    except Exception as e:
        if DEBUG: _log(f"Hierarchy error: {e}")
    
    return False

def _is_mouse_over(owner):
    """Checks if mouse is over this button"""
    hit_obj = _get_hit_object()
    belongs = _belongs_to(hit_obj, owner)
    
    if DEBUG and belongs:
        _log(f"Mouse OVER {owner.name}")
    
    return belongs

# =============================================================================
# CORRECTED SOUND SYSTEM
# =============================================================================
def _play_click_sound():
    """Plays mouse click sound"""
    try:
        # Get expanded sound path
        sound_path = logic.expandPath(CLICK_SOUND_PATH)
        
        if DEBUG: _log(f"Attempting to play sound: {sound_path}")
        
        # Load sound
        sound = aud.Sound.file(sound_path)
        
        if DEBUG: _log(f"Sound loaded: {sound}")
        
        # Create audio device and play
        # NOTE: Use aud.Device() with capital D as in intro_sequence.py
        device = aud.Device()
        
        # Play sound once (no loop)
        handle = device.play(sound)
        
        # Adjust volume (0.8 = 80% volume)
        handle.volume = 0.8
        
        if DEBUG: _log(f"Click sound played, handle: {handle}")
        
        # Keep reference to handle so it's not garbage collected
        # Important for short sounds in BGE
        scene = logic.getCurrentScene()
        game_controller = scene.objects.get("Game.Controller")
        if game_controller:
            game_controller['_last_click_sound'] = handle
        
        return handle
        
    except Exception as e:
        if DEBUG: _log(f"Error playing sound: {e}")
        # Try alternative method
        try:
            _log("Attempting alternative method...")
            # Alternative method using logic
            sound_path = logic.expandPath(CLICK_SOUND_PATH)
            import os
            if os.path.exists(sound_path):
                _log(f"File exists at: {sound_path}")
            # Use startSound
            logic.startSound(CLICK_SOUND_PATH)
            _log("Sound played with startSound")
        except Exception as e2:
            if DEBUG: _log(f"Alternative method error: {e2}")
        return None

# =============================================================================
# VISUAL EFFECTS
# =============================================================================
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
    except Exception as e:
        if DEBUG: _log(f"Error applying scale: {e}")

def _reset_scale(owner):
    """Restores normal scale"""
    try:
        if "_base_scale" in owner:
            base_scale = owner["_base_scale"]
            owner.localScale = list(base_scale)
    except Exception as e:
        if DEBUG: _log(f"Error restoring scale: {e}")

def _apply_visual_state(owner, state):
    """Applies visual effects according to state"""
    if state == "idle":
        _reset_scale(owner)
    elif state == "over":
        _apply_scale(owner, HOVER_SCALE)
    elif state == "click":
        _apply_scale(owner, HOVER_SCALE * 0.9)

# =============================================================================
# MOUSE CLICK DETECTION
# =============================================================================
def _check_mouse_click():
    """Checks if left mouse button was clicked"""
    try:
        mouse = logic.mouse.inputs
        left_mouse = events.LEFTMOUSE in mouse and mouse[events.LEFTMOUSE].activated
        
        if DEBUG and left_mouse:
            _log("CLICK detected")
            
        return left_mouse
    except Exception as e:
        if DEBUG: _log(f"Error in check_mouse_click: {e}")
        return False

# =============================================================================
# BUTTON ACTIONS
# =============================================================================
def _perform_button_action(own):
    """Executes the corresponding button action"""
    scene = logic.getCurrentScene()
    game_controller = scene.objects.get("Game.Controller")
    
    if not game_controller:
        _log("Game.Controller not found")
        return
    
    # Play click sound (FIRST, before anything else)
    _play_click_sound()
    
    # Determine action based on object name
    obj_name = own.name
    
    if DEBUG: _log(f"Button action: {obj_name}")
    
    # Main menu buttons
    if "Button.Start" in obj_name:
        _log("Start game")
        game_controller['button_action'] = 'start'
        
    elif "Button.Continue" in obj_name:
        _log("Continue game")
        game_controller['button_action'] = 'continue'
        
    elif "Button.Reset" in obj_name:
        _log("Reset game")
        game_controller['button_action'] = 'reset'
        
    elif "Button.Accept" in obj_name:
        _log("Accept reset")
        game_controller['button_action'] = 'accept_reset'
        
    elif "Button.Cancel" in obj_name:
        _log("Cancel reset")
        game_controller['button_action'] = 'cancel_reset'
    
    # Language selection buttons
    elif "Button.Lan.Es" in obj_name:
        _log("Select Spanish")
        game_controller['button_action'] = 'select_es'
        
    elif "Button.Lan.En" in obj_name:
        _log("Select English")
        game_controller['button_action'] = 'select_en'
    
    # Forward button (equivalent to Space)
    elif "Button.Forward" in obj_name:
        _log("Forward (Space)")
        game_controller['button_action'] = 'forward'

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main(cont):
    """Handles button interaction"""
    own = cont.owner
    
    if DEBUG: _log(f"Processing {own.name} (visible: {own.visible})")
    
    # Apply Z displacement based on visibility
    _update_z_position(own)
    
    # Only process if object is visible
    if not own.visible:
        own["_button_state"] = "idle"
        return
    
    # Detect mouse state - use ray casting
    mouse_over = _is_mouse_over(own)
    
    # Detect click
    mouse_click = False
    if mouse_over:
        mouse_click = _check_mouse_click()
    
    # Previous and current state
    previous_state = own.get("_button_state", "idle")
    current_state = "over" if mouse_over else "idle"
    
    if mouse_over and mouse_click:
        current_state = "click"
    
    # Apply visual effects if state changed
    if current_state != previous_state:
        if DEBUG: _log(f"{own.name}: {previous_state} -> {current_state}")
        _apply_visual_state(own, current_state)
        own["_button_state"] = current_state
    
    # Handle click - ONLY if over the button
    if mouse_over and mouse_click:
        _log(f"Button CLICKED: {own.name}")
        
        # Restore visual state immediately
        _apply_visual_state(own, "idle")
        own["_button_state"] = "idle"
        
        # Execute button action with sound
        _perform_button_action(own)

# =============================================================================
# INITIALIZATION
# =============================================================================
def init(cont):
    """Initializes the button"""
    own = cont.owner
    
    # Save base scale
    own["_base_scale"] = tuple(own.localScale)
    
    # Save original Z position
    own["_original_z"] = own.worldPosition.z
    own["_z_displaced"] = False
    
    # Initial state
    own["_button_state"] = "idle"
    _apply_visual_state(own, "idle")
    
    # Verify camera exists
    scene = logic.getCurrentScene()
    camera = scene.objects.get(RAY_CAMERA_NAME)
    if not camera and DEBUG:
        _log(f"Warning: Camera '{RAY_CAMERA_NAME}' not found")
    
    if DEBUG: _log(f"Button initialized: {own.name} (Z: {own['_original_z']})")