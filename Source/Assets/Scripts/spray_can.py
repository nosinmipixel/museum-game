"""
spray_can.py

Rechargeable spray can interaction control

This script manages collectible spray cans that refill the player's spray resource.
It handles mouse interaction, visual feedback, sound effects, and game state updates
when cans are collected or when the spray is already full.

Main Features:
    1. Mouse-over detection with hover scaling effect
    2. Click interaction to collect spray cans
    3. Updates game state (spray_total and spray_cans counters)
    4. Plays sound effect on collection
    5. Shows info text when spray is already full
    6. Manages Info.Effect.Over visual indicator
    7. Debounced input to prevent rapid multiple collections

Setup:
    Owner: 'Spray.Can' in 'SprayCanObject' collection (hidden to allow the option 'Add object')
    Logic Bricks: Always (True) connected to a Python controller/module 'spray_can.main'
    Mouse sensors connected to a same Python controller/module 'spray_can.main':
        - Mouse.Over (for hover detection)
        - Mouse.Click (for click detection)

Configurable Variables:
    DEBUG (bool): Enable debug messages (default: False)
    MAX_SPRAY_VALUE (int): Maximum spray capacity (default: 100)
    EFFECT_HIDE_POSITION (list): Position to hide visual effects (default: [0, -500, 0])
    REQUIRED_CONSECUTIVE_FRAMES (int): Frames needed for stable detection (default: 3)

Notes:
    - Requires game_access module for game state management
    - Requires aud module for sound playback
    - Uses message system for info text display
    - Supports multiple can instances without visual effect conflict
    - Object is destroyed after collection

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
__description__ = "Rechargeable spray can interaction with mouse detection and sound"

# =============================================================================
# IMPORTS AND CONFIGURATION
# =============================================================================
import bge
from bge import logic
import aud
import game_access

MAX_SPRAY_VALUE = 100
EFFECT_HIDE_POSITION = [0, -500, 0]
REQUIRED_CONSECUTIVE_FRAMES = 3
DEBUG = False

def debug_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

# =============================================================================
# SOUND SYSTEM
# =============================================================================
def init_sound_system():
    try:
        device = aud.Device()
        def _load_sound(rel_path):
            if not rel_path.startswith("//"):
                rel_path = "//" + rel_path
            return aud.Sound.file(bge.logic.expandPath(rel_path))
        sound_pop = _load_sound("Assets/Sounds/pop.ogg")
        debug_print("Sound system initialized correctly")
        return device, sound_pop
    except Exception as e:
        print(f"Error initializing sound system: {e}")
        return None, None

# =============================================================================
# GAME STATE ACCESSORS
# =============================================================================
def get_spray_total():
    try:
        game = game_access.get_game()
        if game:
            return game.state.spray_total
    except Exception as e:
        debug_print(f"Error getting spray_total: {e}")
    return 100

def is_active():
    """Check if spray can is collectible (spray not full)"""
    current_spray = get_spray_total()
    return current_spray < MAX_SPRAY_VALUE

def update_spray_total():
    try:
        game = game_access.get_game()
        if game:
            game.state.spray_total = MAX_SPRAY_VALUE
            debug_print(f"Spray restored to {MAX_SPRAY_VALUE}")
            return True
    except Exception as e:
        debug_print(f"Error restoring spray: {e}")
    return False

def update_spray_cans_count(delta=-1):
    try:
        game = game_access.get_game()
        if game:
            new_count = max(0, game.state.spray_cans + delta)
            game.state.spray_cans = new_count
            debug_print(f"Can counter updated: {game.state.spray_cans - delta} -> {new_count}")
            return new_count
    except Exception as e:
        debug_print(f"Error updating can counter: {e}")
    return 0

# =============================================================================
# MOUSE DETECTION
# =============================================================================
def update_mouse_sensors(cont, own):
    mouse_over = False
    mouse_click = False

    mouse_over_sensor = cont.sensors.get("Mouse.Over")
    if mouse_over_sensor and mouse_over_sensor.positive:
        mouse_over = True
        mouse_click_sensor = cont.sensors.get("Mouse.Click")
        if mouse_click_sensor and mouse_click_sensor.positive:
            mouse_click = True

    # Check if any HUD is open
    if getattr(logic, "hud_pause_open", False) or \
       getattr(logic, "hud_inventory_open", False) or \
       getattr(logic, "hud_inventory_v2_open", False):
        return False, False

    return mouse_over, mouse_click

# =============================================================================
# VISUAL EFFECTS
# =============================================================================
def play_pop_sound(own):
    try:
        if "_sound_device" not in own or "_sound_pop" not in own:
            device, sound_pop = init_sound_system()
            if device and sound_pop:
                own["_sound_device"] = device
                own["_sound_pop"] = sound_pop
        
        if "_sound_device" in own and "_sound_pop" in own:
            handle = own["_sound_device"].play(own["_sound_pop"])
            if handle:
                try: 
                    handle.loop_count = 0
                    handle.volume = 0.7
                except Exception: 
                    pass
                debug_print("Pop sound played")
                return True
    except Exception as e:
        debug_print(f"Error playing pop sound: {e}")
    return False

def reset_can_effects(own, force=False):
    if not force and own.get("_mouse_over", False):
        return
    if "_original_scale" in own:
        own.localScale = own["_original_scale"]

def apply_mouse_enter_effects(own):
    if own.get("_mouse_over", False):
        if "_original_scale" not in own:
            own["_original_scale"] = own.localScale.copy()
        original_scale = own.get("_original_scale", [1.0, 1.0, 1.0])
        own.localScale = [s * 1.1 for s in original_scale]

# =============================================================================
# INFO EFFECT MANAGEMENT
# =============================================================================
def update_info_effect(scene, own, mouse_over, spray_available):
    """
    CRITICAL FIX: Only this instance manages the effect if it has mouse_over
    Instances WITHOUT mouse_over do NOT touch the effect (avoids competition)
    """
    info_effect = scene.objects.get('Info.Effect.Over')
    if not info_effect:
        return
    
    # Only show when: mouse_over=True AND spray NOT available
    if mouse_over and not spray_available:
        info_effect.worldPosition = own.worldPosition.copy()
        info_effect.visible = True
        own["_info_effect_visible"] = True  # Mark that THIS instance is showing it
        debug_print(f"[{own.name}] Info.Effect.Over: SHOWING")
    else:
        # FIX: Only hide if THIS instance was showing it before
        # Instances without mouse_over do NOT hide the effect (could be from another can)
        if own.get("_info_effect_visible", False):
            info_effect.worldPosition = EFFECT_HIDE_POSITION
            info_effect.visible = False
            own["_info_effect_visible"] = False
            debug_print(f"[{own.name}] Info.Effect.Over: HIDDEN")

# =============================================================================
# MOUSE OVER EFFECTS WITH DEBOUNCE
# =============================================================================
def handle_mouse_over_effects_stable(own, current_mouse_over, cont):
    if "_mouse_over_counter" not in own:
        own["_mouse_over_counter"] = 0
    if "_mouse_out_counter" not in own:
        own["_mouse_out_counter"] = 0
    
    previous_mouse_over = own.get("_mouse_over", False)

    if current_mouse_over:
        own["_mouse_out_counter"] = 0
        if not previous_mouse_over:
            own["_mouse_over_counter"] += 1
            if own["_mouse_over_counter"] >= REQUIRED_CONSECUTIVE_FRAMES:
                own["_mouse_over"] = True
                apply_mouse_enter_effects(own)
                own["_mouse_over_counter"] = 0
    else:
        own["_mouse_over_counter"] = 0
        if previous_mouse_over:
            own["_mouse_out_counter"] += 1
            if own["_mouse_out_counter"] >= REQUIRED_CONSECUTIVE_FRAMES:
                own["_mouse_over"] = False
                reset_can_effects(own)
                own["_mouse_out_counter"] = 0

# =============================================================================
# CORE INTERACTION HANDLER
# =============================================================================
def handle_can_interaction(cont, own, scene):
    if getattr(logic, "hud_pause_open", False) or \
       getattr(logic, "hud_inventory_open", False) or \
       getattr(logic, "hud_inventory_v2_open", False):
        if own.get("_mouse_over", False):
            reset_can_effects(own)
        return

    mouse_over, mouse_click = update_mouse_sensors(cont, own)
    handle_mouse_over_effects_stable(own, mouse_over, cont)

    if mouse_over and mouse_click:
        # Debounce check
        try:
            if float(getattr(logic, "_click_block_until", 0.0)) > float(logic.getRealTime()):
                return
        except:
            pass
        
        debug_print("Click on spray can!")
        
        # Check if spray is already full (NOT collectible)
        if not is_active():
            # Show message when cannot collect (spray full)
            own.sendMessage("add_info_text", "info.show|info_text|31|field=info_text", "Game.Controller")
            
            # FIX: Only hide if THIS instance had the effect visible
            if own.get("_info_effect_visible", False):
                info_effect = scene.objects.get('Info.Effect.Over')
                if info_effect:
                    info_effect.worldPosition = EFFECT_HIDE_POSITION
                    info_effect.visible = False
                own["_info_effect_visible"] = False
            return
        
        play_pop_sound(own)
        own["_mouse_over"] = False
        reset_can_effects(own, force=True)
        
        if update_spray_total():
            update_spray_cans_count()
            try:
                own.endObject()
            except:
                try:
                    scene.removeObject(own)
                except:
                    own.visible = False
                    own["_marked_for_deletion"] = True
            debug_print("Spray can collected and destroyed")
            return

# =============================================================================
# CLEANUP AND DELETION
# =============================================================================
def cleanup_marked_cans(own):
    if own.get("_marked_for_deletion", False):
        try:
            scene = logic.getCurrentScene()
            try:
                scene.removeObject(own)
            except:
                try:
                    own.endObject()
                except:
                    pass
        except Exception as e:
            debug_print(f"Error deleting marked can: {e}")

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main():
    cont = logic.getCurrentController()
    own = cont.owner
    scene = logic.getCurrentScene()
    
    if own.get("_marked_for_deletion", False):
        cleanup_marked_cans(own)
        return

    # Initialize variables
    if "_mouse_over" not in own:
        own["_mouse_over"] = False
    if "_mouse_over_counter" not in own:
        own["_mouse_over_counter"] = 0
    if "_mouse_out_counter" not in own:
        own["_mouse_out_counter"] = 0
    if "_original_scale" not in own:
        own["_original_scale"] = own.localScale.copy()
    if "_info_effect_visible" not in own:
        own["_info_effect_visible"] = False  # New tracking

    # Detect mouse state
    mouse_over_sensor = cont.sensors.get("Mouse.Over")
    mouse_over = mouse_over_sensor.positive if mouse_over_sensor else False
    
    # Check spray availability
    spray_available = is_active()
    
    # Update Info.Effect.Over (FIXED for multiple instances)
    update_info_effect(scene, own, mouse_over, spray_available)

    # Manage active state
    if not spray_available:
        own["_active"] = False
        if own.get("_mouse_over", False) and not mouse_over:
            reset_can_effects(own)
    else:
        own["_active"] = True

    # Handle interaction
    handle_can_interaction(cont, own, scene)

main()