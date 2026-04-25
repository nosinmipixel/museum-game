"""
pause_buttons.py

Manages pause menu button interactions with visual effects.

This script handles the pause menu buttons including resume, save, quit,
sound toggle, and language selection with proper visual feedback.

Main Features:
    1. Ray casting based mouse detection for buttons
    2. Visual effects (scale, tint) for idle, hover, and click states
    3. Resume game functionality
    4. Save game functionality with visual feedback
    5. Quit game with auto-save before exit
    6. Sound toggle with visual feedback
    7. Language switching between Spanish and English
    8. Integration with pause_window for menu visibility control

Setup:
    Connect to Logic Bricks as Python controller with module 'pause_buttons.handle_pause_buttons'
    Requires buttons with names containing: resume, save, quit, sound, lan.es, lan.en

Configurable Variables:
    RAY_CAMERA_NAME (str): Camera for ray casting (default: 'Camera.Hud')
    RAY_DISTANCE (float): Maximum ray casting distance (default: 10000.0)
    IDLE_TINT (tuple): RGBA color for idle state (default: (1.00, 1.00, 1.00, 1.0))
    OVER_TINT (tuple): RGBA color for hover state (default: (0.82, 0.82, 0.82, 1.0))
    CLICK_TINT (tuple): RGBA color for click state (default: (0.68, 0.68, 0.68, 1.0))
    HOVER_SCALE (float): Scale factor for hover (default: 1.06)
    CLICK_SCALE (float): Scale factor for click (default: 0.96)

Notes:
    - Requires game_access module for game state and language
    - Requires save_system module for save_game function
    - Requires pause_window module for menu visibility control
    - Plays click sound on button press via 'sound_fx.play' message
    - Save confirmation text appears for 2 seconds after saving
    - Language change triggers button mesh and text updates

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
__description__ = "Manages pause menu button interactions with visual effects"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic, events
import game_access

# =============================================================================
# CONFIGURATION
# =============================================================================
RAY_CAMERA_NAME = "Camera.Hud"
RAY_DISTANCE = 10000.0

# Visual effects
IDLE_TINT = (1.00, 1.00, 1.00, 1.0)
OVER_TINT = (0.82, 0.82, 0.82, 1.0)
CLICK_TINT = (0.68, 0.68, 0.68, 1.0)
HOVER_SCALE = 1.06
CLICK_SCALE = 0.96

# =============================================================================
# VISUAL EFFECTS
# =============================================================================
def _apply_button_effects(owner, state):
    """Applies visual effects to pause buttons"""
    if state == "idle":
        owner.color = IDLE_TINT
        _reset_scale(owner)
    elif state == "over":
        owner.color = OVER_TINT
        _set_scale(owner, HOVER_SCALE)
    elif state == "click":
        owner.color = CLICK_TINT
        _set_scale(owner, CLICK_SCALE)

def _set_scale(owner, scale):
    try:
        if "_base_scale" not in owner:
            owner["_base_scale"] = owner.localScale.copy()
        base_scale = owner["_base_scale"]
        owner.localScale = [base_scale[0] * scale, base_scale[1] * scale, base_scale[2] * scale]
    except:
        pass

def _reset_scale(owner):
    try:
        if "_base_scale" in owner:
            owner.localScale = owner["_base_scale"]
    except:
        pass

# =============================================================================
# MOUSE DETECTION
# =============================================================================
def _is_mouse_over(owner):
    """Detects if mouse is over the button"""
    scene = logic.getCurrentScene()
    cam = scene.objects.get(RAY_CAMERA_NAME) or scene.active_camera
    if not cam:
        return False
    
    try:
        mx, my = logic.mouse.position
        hit = cam.getScreenRay(mx, my, RAY_DISTANCE, "")
        return _is_hit_part_of_button(hit, owner)
    except:
        return False

def _is_hit_part_of_button(hit, owner):
    if not hit:
        return False
    
    current = hit
    while current:
        if current == owner:
            return True
        current = current.parent
    return False

# =============================================================================
# BUTTON FUNCTIONALITIES
# =============================================================================
def _handle_resume_button():
    """Handles Resume button"""
    from pause_window import _hide_pause_menu
    scene = logic.getCurrentScene()
    _hide_pause_menu(scene)

def _handle_save_button():
    """Handles Save button"""
    try:
        print("[Pause] Saving game...")
        
        # Import and use save system
        from save_system import save_game
        
        if save_game():
            # Visual feedback using new architecture
            game = game_access.get_game()
            if game:
                game.hud_text.center_text = "Juego guardado" if _get_language() == "es" else "Game saved"
                logic._clear_save_text_time = logic.getRealTime() + 2.0
                
            print("[Pause] Game saved successfully")
        else:
            print("[Pause] Error saving game")
            
    except Exception as e:
        print(f"[Pause] Error saving game: {e}")

def _handle_quit_button():
    """Handles Quit button"""
    try:
        print("[Pause] Saving before quit...")
        
        # Save before quitting
        from save_system import save_game
        save_game()
        
        print("[Pause] Game saved, quitting...")
        logic.endGame()
        
    except Exception as e:
        print(f"[Pause] Error: {e}")
        logic.endGame()

def _handle_sound_button():
    """Toggles background sound using new architecture"""
    game = game_access.get_game()
    if game:
        current_state = game.state.sound_background
        new_state = not current_state
        game.state.sound_background = new_state
        
        # Update meshes
        from pause_window import _update_sound_button_mesh
        _update_sound_button_mesh()
        
        print(f"[Pause] Background sound: {'Enabled' if new_state else 'Disabled'}")

def _handle_language_button():
    """Toggles game language using new architecture"""
    try:
        game = game_access.get_game()
        if not game:
            return
            
        current_lang = game.state.language
        new_lang = "en" if current_lang == "es" else "es"
        game.state.language = new_lang
        
        # Update meshes and texts
        from pause_window import _update_language_button_mesh, _update_pause_texts
        _update_language_button_mesh()
        _update_pause_texts()
        
        print(f"[Pause] Language changed to: {new_lang}")
    except Exception as e:
        print(f"[Pause] Error changing language: {e}")

def _get_language():
    """Gets current language using new architecture"""
    game = game_access.get_game()
    if game:
        return game.state.language
    return "es"

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def handle_pause_buttons():
    """Handles pause button interaction"""
    cont = logic.getCurrentController()
    owner = cont.owner
    
    # Only process if pause menu is open
    if not getattr(logic, "hud_pause_open", False):
        return
    
    # Detect mouse state
    mouse_over = _is_mouse_over(owner)
    mouse = logic.mouse
    left_mouse_input = mouse.inputs.get(events.LEFTMOUSE)
    mouse_click = left_mouse_input and left_mouse_input.activated
    
    # Determine button state
    current_state = owner.get("_button_state", "idle")
    new_state = "idle"
    
    if mouse_over:
        if mouse_click:
            new_state = "click"
        else:
            new_state = "over"
    
    # Apply effects if state changed
    if new_state != current_state:
        _apply_button_effects(owner, new_state)
        owner["_button_state"] = new_state
    
    # Handle click
    if mouse_over and mouse_click:
        bge.logic.sendMessage("sound_fx.play", "sound_fx.play|clic.ogg") 
        button_name = owner.name.lower()
                
        if "resume" in button_name:
            _handle_resume_button()
        elif "save" in button_name:
            _handle_save_button()
        elif "quit" in button_name:
            _handle_quit_button()
        elif "sound" in button_name:
            _handle_sound_button()
        elif "lan.es" in button_name or "lan.en" in button_name:
            _handle_language_button()