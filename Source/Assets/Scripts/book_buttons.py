"""
book_buttons.py

Manages book interface buttons with ray casting system.

This script handles the visual interaction (hover, click) and functionality
of book UI buttons (close, forward, backward) using ray casting for mouse detection.

Main Features:
    1. Ray casting based mouse detection over book UI buttons
    2. Visual effects (scale, tint) for idle, hover, and click states
    3. HUD positioning system to show/hide book interface
    4. Book page navigation (forward/backward)
    5. Integration with BookManager for book state management

Setup:
    Connect each button as a Python controller with module 'book_buttons.handle_close_button',
    'book_buttons.handle_forward_button', or 'book_buttons.handle_backward_button'

Configurable Variables:
    RAY_CAMERA_NAME (str): Name of camera used for ray casting (default: 'Camera.Hud')
    RAY_DISTANCE (float): Maximum distance for ray casting (default: 10000.0)
    HOVER_SCALE (float): Scale factor when mouse is over button (default: 1.2)
    NORMAL_SCALE (float): Normal button scale (default: 1.0)
    IDLE_TINT (tuple): RGBA color for idle state (default: (1.00, 1.00, 1.00, 1.0))
    OVER_TINT (tuple): RGBA color for hover state (default: (0.82, 0.82, 0.82, 1.0))
    CLICK_TINT (tuple): RGBA color for click state (default: (0.68, 0.68, 0.68, 1.0))
    HUD_MAIN (str): Main HUD object name (default: 'Empty.Book.Main')
    HUD_POS_IN (str): Target position when HUD is visible (default: 'Empty.Hud.Pos')
    HUD_POS_OUT (str): Target position when HUD is hidden (default: 'Empty.Book.Pos.Out')

Notes:
    - Uses mouse.inputs instead of deprecated mouse.events
    - Compatible with new game_data.py / init_game.py architecture
    - Requires BookManager instance in logic.book_manager

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
__description__ = "Manages book interface buttons with ray casting system"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic

# Import game_access for new architecture
try:
    import game_access
    HAS_GAME_ACCESS = True
except ImportError:
    HAS_GAME_ACCESS = False

# =============================================================================
# LOGGING
# =============================================================================
def _log(*args):
    print("[book_buttons]", *args)

# =============================================================================
# CONFIGURATION
# =============================================================================
DEBUG = False
RAY_CAMERA_NAME = "Camera.Hud"
RAY_DISTANCE = 10000.0

# Visual effects
HOVER_SCALE = 1.2
NORMAL_SCALE = 1.0
IDLE_TINT = (1.00, 1.00, 1.00, 1.0)
OVER_TINT = (0.82, 0.82, 0.82, 1.0)
CLICK_TINT = (0.68, 0.68, 0.68, 1.0)

# Positioning objects
HUD_MAIN = "Empty.Book.Main"
HUD_POS_IN = "Empty.Hud.Pos"          # Position when visible
HUD_POS_OUT = "Empty.Book.Pos.Out"    # Position when hidden

# =============================================================================
# POSITIONING SYSTEM
# =============================================================================
def _move_to_position(object_name, target_name):
    """Moves an object to the position of another object"""
    scene = logic.getCurrentScene()
    obj = scene.objects.get(object_name)
    target = scene.objects.get(target_name)
    
    if obj and target:
        _log(f"Moving {object_name} from {obj.worldPosition} to {target.worldPosition}")
        obj.worldPosition = target.worldPosition.copy()
        obj.worldOrientation = target.worldOrientation.copy()
        _log(f"Success: {object_name} moved to {target_name}")
        return True
    else:
        _log(f"Failed: Cannot move {object_name} - obj={obj}, target={target}")
        return False

def _show_book_hud():
    """Shows the book HUD interface - Moves to Empty.Hud.Pos"""
    return _move_to_position(HUD_MAIN, HUD_POS_IN)

def _hide_book_hud():
    """Hides the book HUD interface - Moves to Empty.Book.Pos.Out"""
    return _move_to_position(HUD_MAIN, HUD_POS_OUT)

# =============================================================================
# RAY CASTING SYSTEM
# =============================================================================
def _hit_under_mouse():
    """Detects which object is under the mouse using ray casting"""
    scn = logic.getCurrentScene()
    
    cam = scn.objects.get(RAY_CAMERA_NAME)
    if not cam:
        return None
    
    try:
        mx, my = logic.mouse.position
        hit_obj = cam.getScreenRay(mx, my, RAY_DISTANCE, "")
        return hit_obj
    except:
        try:
            hit_obj = cam.getScreenRay(mx, my, RAY_DISTANCE)
            return hit_obj
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
        owner.localScale = [base_scale[0] * scale_factor, 
                           base_scale[1] * scale_factor, 
                           base_scale[2] * scale_factor]
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
        
def send_message(cont):
    own = cont.owner
    _log(f"Sending message 'unlock_background' to Lock.Main.Scene")
    
    # Simple format - only what's needed
    bge.logic.sendMessage("unlock_background", "unlock_background", "Lock.Main.Scene")
    _log("Message sent successfully")
    return True  

# =============================================================================
# BOOK SYSTEM FUNCTIONS
# =============================================================================
def _update_book_display():
    """Updates the book text display - ADAPTED FOR NEW ARCHITECTURE"""
    if not hasattr(logic, "book_manager") or not logic.book_manager.is_open:
        _log("Cannot update display - book_manager not available")
        return
    
    page_text = logic.book_manager.get_current_page_text()
    page_info = logic.book_manager.get_page_info()
    
    _log(f"Updating page: {page_info}")
    _log(f"Current state: page {logic.book_manager.current_page + 1}/{logic.book_manager.total_pages}")
    _log(f"Book type: {logic.book_manager.current_book_type}")
    
    # Update properties for BLF_module
    try:
        if HAS_GAME_ACCESS:
            game = game_access.get_game()
            if game and hasattr(game, 'hud_text'):
                game.hud_text.book_text = page_text
                game.hud_text.info_text = f"Page {page_info}"
                _log(f"Text updated - Page {page_info}")
            else:
                _log("game.hud_text not available")
        else:
            # Fallback for compatibility
            scene = logic.getCurrentScene()
            game_controller = scene.objects.get("Game.Controller")
            if game_controller:
                hud_text = game_controller.get("hud_text", None)
                if hud_text:
                    hud_text.book_text = page_text
                    hud_text.info_text = f"Page {page_info}"
                    _log(f"Text updated - Page {page_info}")
                else:
                    _log("hud_text not found in Game.Controller")
            else:
                _log("Game.Controller not found")
    except Exception as e:
        _log("Error updating display:", e)

def _clear_book_hud_text():
    """Clears the book text from HUD - ADAPTED FOR NEW ARCHITECTURE"""
    try:
        if HAS_GAME_ACCESS:
            game = game_access.get_game()
            if game and hasattr(game, 'hud_text'):
                game.hud_text.book_text = ""
                game.hud_text.info_text = ""
                _log("Text cleared (new architecture)")
        else:
            # Fallback for compatibility
            scene = logic.getCurrentScene()
            game_controller = scene.objects.get("Game.Controller")
            if game_controller:
                hud_text = game_controller.get("hud_text", None)
                if hud_text:
                    hud_text.book_text = ""
                    hud_text.info_text = ""
                    _log("Text cleared (compatibility)")
                else:
                    _log("hud_text not available")
            else:
                _log("Game.Controller not found")
    except Exception as e:
        _log("Error clearing text:", e)

# =============================================================================
# BUTTON HANDLERS
# =============================================================================
def handle_close_button():
    """Handles the close book button"""
    cont = logic.getCurrentController()
    own = cont.owner
    
    # Detect mouse state - ONLY use ray casting
    mouse_over = _is_mouse_over(cont, own)
    
    # Only detect click if mouse is over the button
    mouse_click = False
    if mouse_over:
        try:
            mouse_left_input = logic.mouse.inputs.get(bge.events.LEFTMOUSE)
            if mouse_left_input and mouse_left_input.activated:
                mouse_click = True
        except (AttributeError, KeyError):
            # Fallback
            _log("mouse.inputs not available, using fallback")
            if logic.mouse.events.get(bge.events.LEFTMOUSE) == logic.KX_INPUT_JUST_ACTIVATED:
                mouse_click = True
    
    # Previous and current state
    previous_state = own.get("_button_state", "idle")
    current_state = "over" if mouse_over else "idle"
    
    if mouse_over and mouse_click:
        current_state = "click"
    
    # Apply visual effects if state changed
    if current_state != previous_state:
        _apply_visual_state(own, current_state)
        own["_button_state"] = current_state
    
    # Handle click - ONLY if over the button
    if mouse_over and mouse_click:
        _log("CLOSE BUTTON PRESSED - Starting closing process")
        
        # Restore visual state immediately
        _apply_visual_state(own, "idle")
        own["_button_state"] = "idle"

        # 1. SEND MESSAGE FIRST
        message_sent = send_message(cont)
        _log(f"Send result: {'SUCCESS' if message_sent else 'FAILED'}")
        
        # 2. Set flag to prevent immediate reopening
        logic.globalDict["book_closing"] = True
        _log("Activated book_closing flag to prevent reopening")
        
        # 3. Clear HUD text first
        _log("Clearing HUD text")
        _clear_book_hud_text()
        
        # 4. Close book using book_manager
        if hasattr(logic, "book_manager"):
            _log("Closing book via book_manager")
            logic.book_manager.close_book()
        else:
            _log("book_manager not available")
            
        # 5. Hide HUD
        _log("Ensuring HUD is hidden")
        _hide_book_hud()

def handle_forward_button():
    """Handles the next page button - IMPROVED VERSION"""
    cont = logic.getCurrentController()
    own = cont.owner
    
    # Detect mouse state
    mouse_over = _is_mouse_over(cont, own)
    
    # Only detect click if mouse is over the button
    mouse_click = False
    if mouse_over:
        try:
            mouse_left_input = logic.mouse.inputs.get(bge.events.LEFTMOUSE)
            if mouse_left_input and mouse_left_input.activated:
                mouse_click = True
        except (AttributeError, KeyError):
            # Fallback
            _log("mouse.inputs not available, using fallback")
            if logic.mouse.events.get(bge.events.LEFTMOUSE) == logic.KX_INPUT_JUST_ACTIVATED:
                mouse_click = True
    
    # Previous and current state
    previous_state = own.get("_button_state", "idle")
    current_state = "over" if mouse_over else "idle"
    
    if mouse_over and mouse_click:
        current_state = "click"
    
    # Apply visual effects if state changed
    if current_state != previous_state:
        _apply_visual_state(own, current_state)
        own["_button_state"] = current_state
    
    # Handle click
    if mouse_over and mouse_click:
        _log("FORWARD BUTTON PRESSED")
        
        # Detailed logging of current state
        if hasattr(logic, "book_manager") and logic.book_manager.is_open:
            _log(f"State before forward: page {logic.book_manager.current_page + 1}/{logic.book_manager.total_pages}")
            _log(f"Book type: {logic.book_manager.current_book_type}")
        
        # Restore visual state immediately
        _apply_visual_state(own, "idle")
        own["_button_state"] = "idle"
        
        # Play click sound
        bge.logic.sendMessage("sound_fx.play", "sound_fx.play|mouse-click.ogg")         
        
        # Go to next page
        if hasattr(logic, "book_manager") and logic.book_manager.is_open:
            _log("Attempting to go to next page")
            if logic.book_manager.next_page():
                _log("Page forward successful")
                _update_book_display()
            else:
                _log("Cannot go to next page (last page?)")
        else:
            _log("book_manager not available or book not open")

def handle_backward_button():
    """Handles the previous page button - IMPROVED VERSION"""
    cont = logic.getCurrentController()
    own = cont.owner
    
    # Detect mouse state
    mouse_over = _is_mouse_over(cont, own)
    
    # Only detect click if mouse is over the button
    mouse_click = False
    if mouse_over:
        try:
            mouse_left_input = logic.mouse.inputs.get(bge.events.LEFTMOUSE)
            if mouse_left_input and mouse_left_input.activated:
                mouse_click = True
        except (AttributeError, KeyError):
            # Fallback
            _log("mouse.inputs not available, using fallback")
            if logic.mouse.events.get(bge.events.LEFTMOUSE) == logic.KX_INPUT_JUST_ACTIVATED:
                mouse_click = True
    
    # Previous and current state
    previous_state = own.get("_button_state", "idle")
    current_state = "over" if mouse_over else "idle"
    
    if mouse_over and mouse_click:
        current_state = "click"
    
    # Apply visual effects if state changed
    if current_state != previous_state:
        _apply_visual_state(own, current_state)
        own["_button_state"] = current_state
    
    # Handle click
    if mouse_over and mouse_click:
        _log("BACKWARD BUTTON PRESSED")
        
        # Detailed logging of current state
        if hasattr(logic, "book_manager") and logic.book_manager.is_open:
            _log(f"State before backward: page {logic.book_manager.current_page + 1}/{logic.book_manager.total_pages}")
            _log(f"Book type: {logic.book_manager.current_book_type}")
        
        # Restore visual state immediately
        _apply_visual_state(own, "idle")
        own["_button_state"] = "idle"
        
        # Play click sound
        bge.logic.sendMessage("sound_fx.play", "sound_fx.play|mouse-click.ogg")             
        
        # Go to previous page
        if hasattr(logic, "book_manager") and logic.book_manager.is_open:
            _log("Attempting to go to previous page")
            if logic.book_manager.prev_page():
                _log("Page backward successful")
                _update_book_display()
            else:
                _log("Cannot go to previous page (first page?)")
        else:
            _log("book_manager not available or book not open")

# =============================================================================
# INITIALIZATION
# =============================================================================
def init_button(cont):
    """Initializes the button with normal scale"""
    own = cont.owner
    
    # Save base scale
    own["_base_scale"] = tuple(own.localScale)
    
    # Initial state
    own["_button_state"] = "idle"
    _apply_visual_state(own, "idle")
    
    _log(f"Button initialized: {own.name}")