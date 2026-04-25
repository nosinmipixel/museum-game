"""
death_button.py

Manages restart button functionality for death screen with coordinated game restart.

This script handles the visual appearance, text localization, and click detection
for the restart button that appears when the player dies, coordinating with the
player_death system for a smooth restart experience.

Main Features:
    1. Multi-language text support (Spanish/English)
    2. Visual effects (scale, tint) for idle, hover, and click states
    3. Screen-space button positioning independent of 3D world
    4. Coordinated restart with player_death system
    5. Automatic text reset on button activation
    6. Synchronized text object visibility and state

Setup:
    Connect to Logic Bricks as Python controller with module 'death_button.main'
    Button requires a child text object named 'Button.Restart.Text'

Configurable Variables:
    DEBUG (bool): Enable debug logging (default: True)
    HOVER_SCALE (float): Scale factor when mouse is over button (default: 1.2)
    IDLE_TINT (tuple): RGBA color for idle state (default: (1.00, 1.00, 1.00, 1.0))
    OVER_TINT (tuple): RGBA color for hover state (default: (0.82, 0.82, 0.82, 1.0))
    CLICK_TINT (tuple): RGBA color for click state (default: (0.68, 0.68, 0.68, 1.0))
    TEXT_TINT (tuple): RGBA color for button text (default: (1.00, 1.00, 1.00, 1.0))
    BUTTON_SCREEN_POS_X (float): X position in screen coordinates (default: 0.50)
    BUTTON_SCREEN_POS_Y (float): Y position in screen coordinates (default: 0.722)
    BUTTON_SCREEN_SIZE (float): Button size in screen coordinates (default: 0.06)

Notes:
    - Button uses screen-space detection, not ray casting
    - Text is automatically localized based on game language
    - Requires game_access module for language detection
    - Coordinated restart with player_death system for smooth transition
    - Button is hidden during restart to prevent double-clicks
    - Text object visibility is synchronized with button visibility

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
__description__ = "Manages restart button functionality for death screen"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic

# =============================================================================
# LOGGING
# =============================================================================
def _log(*args):
    print("[death_button]", *args)

# =============================================================================
# CONFIGURATION
# =============================================================================
DEBUG = True

# Visual effects for button only
HOVER_SCALE = 1.2
IDLE_TINT = (1.00, 1.00, 1.00, 1.0)
OVER_TINT = (0.82, 0.82, 0.82, 1.0)
CLICK_TINT = (0.68, 0.68, 0.68, 1.0)

# Text tint (ALWAYS white)
TEXT_TINT = (1.00, 1.00, 1.00, 1.0)

# Texts by language
TEXTS = {
    'es': "Reiniciar",
    'en': "Restart"
}

# Screen position
BUTTON_SCREEN_POS_X = 0.50
BUTTON_SCREEN_POS_Y = 0.722
BUTTON_SCREEN_SIZE = 0.06

# =============================================================================
# ENHANCED TEXT FUNCTIONS
# =============================================================================
def _get_button_text():
    """Gets text according to current language"""
    try:
        from game_access import get_game
        game = get_game()
        if game and hasattr(game.state, 'language'):
            language = game.state.language
        else:
            scene = logic.getCurrentScene()
            game_controller = scene.objects.get("Game.Controller")
            language = game_controller.get("language", "es") if game_controller else "es"
        
        return TEXTS.get(language, TEXTS['es'])
        
    except Exception:
        return TEXTS['es']

def _reset_button_text(button):
    """FULLY RESETS button text"""
    try:
        scene = logic.getCurrentScene()
        button_text = scene.objects.get("Button.Restart.Text")
        
        if not button_text:
            return False
        
        # 1. Get text according to CURRENT language
        text_content = _get_button_text()
        
        # 2. Set text
        button_text["Text"] = text_content
        
        # 3. Force visibility (same as button)
        button_text.visible = button.visible
        
        # 4. Force color (white)
        button_text.color = [1.0, 1.0, 1.0, 1.0]
        
        # 5. Clickable state (same as button)
        button_text["clickable"] = button.get("clickable", False)
        
        if DEBUG and button.visible:
            _log(f"Text RESET: '{text_content}' (visible: {button_text.visible})")
            
        return True
        
    except Exception as e:
        if DEBUG:
            _log(f"Error resetting text: {e}")
        return False

def _sync_text_with_button(button):
    """Synchronizes text with button (run each frame)"""
    try:
        # Only synchronize if button is active
        if not button.get("clickable", False) or not button.visible:
            return
        
        scene = logic.getCurrentScene()
        button_text = scene.objects.get("Button.Restart.Text")
        
        if not button_text:
            return
        
        # 1. Synchronize visibility
        if button_text.visible != button.visible:
            button_text.visible = button.visible
            if DEBUG:
                _log(f"Synchronizing text visibility: {button_text.visible}")
        
        # 2. Clickable state
        button_text["clickable"] = button.get("clickable", False)
        
    except Exception:
        pass

# =============================================================================
# SCREEN SPACE DETECTION
# =============================================================================
def _is_mouse_over(own):
    if not own.get("clickable", False) or not own.visible:
        return False
    
    try:
        mx, my = logic.mouse.position
        
        button_x = BUTTON_SCREEN_POS_X
        button_y = BUTTON_SCREEN_POS_Y
        
        left = button_x - BUTTON_SCREEN_SIZE
        right = button_x + BUTTON_SCREEN_SIZE
        bottom = button_y - BUTTON_SCREEN_SIZE
        top = button_y + BUTTON_SCREEN_SIZE
        
        return (left <= mx <= right) and (bottom <= my <= top)
        
    except Exception:
        return False

# =============================================================================
# VISUAL EFFECTS
# =============================================================================
def _apply_tint(owner, rgba):
    try:
        r, g, b, a = rgba
        owner.color = [r, g, b, a]
    except:
        pass

def _apply_scale(owner, scale_factor):
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
    try:
        if "_base_scale" in owner:
            base_scale = owner["_base_scale"]
            owner.localScale = list(base_scale)
    except:
        pass

def _apply_visual_state(owner, state):
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
# CLICK DETECTION
# =============================================================================
def _is_mouse_click():
    try:
        mouse_inputs = logic.mouse.inputs
        left_mouse = mouse_inputs.get(bge.events.LEFTMOUSE)
        return left_mouse and left_mouse.activated
    except:
        try:
            return logic.mouse.events.get(bge.events.LEFTMOUSE) == logic.KX_INPUT_JUST_ACTIVATED
        except:
            return False

# =============================================================================
# COORDINATED GAME RESTART
# =============================================================================
def _initiate_restart_from_button():
    """Initiates restart process from button - coordinated with player_death"""
    _log("=== INITIATING COORDINATED RESTART ===")
    
    try:
        # 1. Hide button immediately
        scene = logic.getCurrentScene()
        button = scene.objects.get("Button.Restart")
        if button:
            button.visible = False
            button["clickable"] = False
            button.worldPosition = (0, 0, -10000)
            
            _reset_scale(button)
            _apply_tint(button, IDLE_TINT)
            
            # Clear variables
            if "_button_state" in button:
                del button["_button_state"]
            if "_text_initialized" in button:
                del button["_text_initialized"]
        
        # 2. Hide text
        button_text = scene.objects.get("Button.Restart.Text")
        if button_text:
            button_text.visible = False
            button_text.color = [1.0, 1.0, 1.0, 1.0]
            button_text["clickable"] = False
        
        # 3. Notify death system to initiate restart effects
        try:
            import player_death
            if hasattr(player_death.DeathSystem, 'init_restart_from_button'):
                player_death.DeathSystem.init_restart_from_button()
                _log("Death system notified to start effects")
            else:
                # Fallback if method doesn't exist
                _log("Death system does not have init_restart_from_button method")
                _perform_restart_now()  # Immediate restart
        except Exception as e:
            _log(f"Error notifying death system: {e}")
            _perform_restart_now()  # Immediate restart
        
        return True
        
    except Exception as e:
        _log(f"Error initiating restart: {e}")
        return False

def _perform_restart_now():
    """Performs full game restart (when no coordination is available)"""
    _log("Performing immediate restart...")
    
    try:
        scene = logic.getCurrentScene()
        
        # 1. Restore player
        player = scene.objects.get("Player")
        if player:
            player.worldPosition = [0, 0, 0.7]
            player.worldOrientation = [0, 0, 0]
            player['on_dialog'] = False
        
        # 2. Restore animation
        rig = scene.objects.get("charA_metarig.001")
        if not rig:
            for obj in scene.objects:
                if "charA_metarig" in obj.name:
                    rig = obj
                    break
        
        if rig:
            rig.stopAction(1)
            rig.playAction("Idle", 1, 13, layer=0, priority=0, blendin=5, play_mode=2, speed=1.0)
        
        # 3. Restore health
        try:
            from game_access import get_game
            game = get_game()
            if game and hasattr(game, 'player'):
                game.player.health = 100
                _log("Health restored to 100")
        except:
            _log("Could not restore health")
        
        # 4. Reset death system
        try:
            import player_death
            if hasattr(player_death.DeathSystem, 'reset_all'):
                player_death.DeathSystem.reset_all()
                _log("Death system reset")
        except:
            pass
        
        _log("Immediate restart completed")
        return True
        
    except Exception as e:
        _log(f"Error in immediate restart: {e}")
        return False

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main(cont):
    own = cont.owner
    
    # ***** RESET TEXT IF BUTTON JUST BECAME ACTIVE *****
    if own.get("clickable", False) and own.visible:
        # Check if text needs reset
        if "_text_initialized" not in own or not own["_text_initialized"]:
            _reset_button_text(own)
            own["_text_initialized"] = True
            if DEBUG:
                _log("Text initialized/reset")
    
    # Synchronize text each frame
    _sync_text_with_button(own)
    
    # Only process interaction if active
    if not own.get("clickable", False) or not own.visible:
        if own.get("_button_state", "idle") != "idle":
            _apply_visual_state(own, "idle")
            own["_button_state"] = "idle"
        return
    
    # Detect mouse
    mouse_over = _is_mouse_over(own)
    mouse_click = False
    if mouse_over:
        mouse_click = _is_mouse_click()
    
    # State
    previous_state = own.get("_button_state", "idle")
    current_state = "over" if mouse_over else "idle"
    
    if mouse_over and mouse_click:
        current_state = "click"
    
    # Apply visual effects
    if current_state != previous_state:
        _apply_visual_state(own, current_state)
        own["_button_state"] = current_state
        
        if DEBUG and current_state != previous_state:
            _log(f"Button: {previous_state} -> {current_state}")
    
    # Handle click
    if mouse_over and mouse_click:
        _log("CLICK on restart button!")
        
        # Initiate coordinated restart with effects
        _initiate_restart_from_button()

# =============================================================================
# INITIALIZATION
# =============================================================================
def init(cont):
    own = cont.owner
    
    # Basic properties
    if "_base_scale" not in own:
        own["_base_scale"] = tuple(own.localScale)
    
    # Initial state
    own["_button_state"] = "idle"
    _apply_visual_state(own, "idle")
    
    # Initialize text (only if button is active on load)
    if own.get("clickable", False) and own.visible:
        _reset_button_text(own)
        own["_text_initialized"] = True
    else:
        own["_text_initialized"] = False
    
    if DEBUG:
        status = "ACTIVE" if own.get("clickable", False) and own.visible else "INACTIVE"
        text_status = "WITH TEXT" if own.get("_text_initialized", False) else "WITHOUT TEXT"
        _log(f"Button initialized: {own.name} ({status}, {text_status})")