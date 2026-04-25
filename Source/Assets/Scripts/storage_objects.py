"""
storage_objects.py

Optimized storage objects system for collectible world objects

This script manages collectible objects in the game world, handling mouse
interaction, visual effects (hover, click, matrix effect), sound feedback,
and persistence of collected items. It supports object restoration states
and integrates with the achievement system.

Main Features:
    1. Mouse-over detection with hover scaling and tint effects
    2. Click interaction for collecting world objects
    3. Persistent storage of collected items using globalDict
    4. Matrix visual effect animation on collection
    5. Sound feedback for item pickup
    6. Restoration state tracking for collected items
    7. Achievement system integration via messages
    8. Debounced mouse detection to prevent flickering

Setup:
    Connect in Logic Bricks as Python controller/module 'storage_objects.handle'
    Owner Object must have:
        - Name starting with 'Object.World.'
        - Mouse.Over and Mouse.Click sensors connected
        - Properties: item_type, item_id, restored, ubication, exhibition

Configurable Variables:
    DEBUG (bool): Enable debug messages (default: False)
    INFO_MESSAGE_SUBJECT (str): Message subject for info text (default: "add_info_text")
    MATRIX_EFFECT_OBJECT_NAME (str): Matrix effect object name (default: "World.Matrix.Effect")
    UNCOLLECTED_EFFECT_NAME (str): Uncollected effect object name (default: "Uncollected.Effect")
    MATRIX_ANIMATION_NAME (str): Matrix animation name (default: "Sprite_Animation_UV")
    IDLE_TINT (tuple): Idle color tint (default: (1.00, 1.00, 1.00, 1.0))
    HOVER_TINT (tuple): Hover color tint (default: (2.00, 2.00, 2.00, 1.0))
    CLICK_TINT (tuple): Click color tint (default: (0.85, 0.85, 0.85, 1.0))
    HOVER_SCALE_FACTOR (float): Scale multiplier on hover (default: 1.1)

Notes:
    - Uses globalDict for persistent selection tracking across scenes
    - Matrix effect animation duration is 1.2 seconds
    - Objects are hidden and moved out of scene after collection
    - Requires game_access module for state management
    - Integration with restoration NPC for un-restored items

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
__description__ = "Collectible world objects system with mouse interaction and persistence"

# =============================================================================
# IMPORTS AND CONFIGURATION
# =============================================================================
import bge
from bge import events
import game_access

DEBUG = False
INFO_MESSAGE_SUBJECT = "add_info_text"
MATRIX_EFFECT_OBJECT_NAME = "World.Matrix.Effect"
UNCOLLECTED_EFFECT_NAME = "Uncollected.Effect"
MATRIX_ANIMATION_NAME = "Sprite_Animation_UV"
# OUT position for matrix effects (far from scene)
MATRIX_OUT_POSITION = (0, 0, -10000)
# OUT orientation (neutral)
MATRIX_OUT_ORIENTATION = (0, 0, 0)
# Visual effects
IDLE_TINT = (1.00, 1.00, 1.00, 1.0)
HOVER_TINT = (2.00, 2.00, 2.00, 1.0)
CLICK_TINT = (0.85, 0.85, 0.85, 1.0)
HOVER_SCALE_FACTOR = 1.1

# =============================================================================
# PERSISTENCE SYSTEM
# =============================================================================
WORLD_OBJECTS_SELECTED_KEY = "_world_objects_selected"

def _log(*args):
    if DEBUG:
        print("[world-obj]", *args)

def _init_selected_dict():
    if WORLD_OBJECTS_SELECTED_KEY not in bge.logic.globalDict:
        bge.logic.globalDict[WORLD_OBJECTS_SELECTED_KEY] = {}

def _mark_object_selected(item_type, item_id):
    _init_selected_dict()
    key = f"{item_type}{item_id}"
    bge.logic.globalDict[WORLD_OBJECTS_SELECTED_KEY][key] = True

def _is_object_selected(item_type, item_id):
    key = f"{item_type}{item_id}"
    d = bge.logic.globalDict.get(WORLD_OBJECTS_SELECTED_KEY)
    return d.get(key, False) if d else False

# =============================================================================
# SOUND EFFECTS
# =============================================================================
def _play_pickup_sound():
    """Play pickup sound effect"""
    try:
        bge.logic.sendMessage(
            "sound_fx.play",
            "sound_fx.play|pick_up.ogg|volume=0.7"
        )
        _log("Pickup sound played")
        return True
    except Exception:
        return False

# =============================================================================
# UNCOLLECTED EFFECT HANDLING
# =============================================================================
def _hide_uncollected_effect():
    """
    Move 'Uncollected.Effect' to y=-500 to hide it.
    Called when a collectible object is picked up.
    Animation is on the Uncollected.Effect object.
    """
    try:
        scene = bge.logic.getCurrentScene()
        effect_obj = scene.objects.get(UNCOLLECTED_EFFECT_NAME)

        if effect_obj:
            effect_obj.worldPosition = (
                effect_obj.worldPosition[0],
                -500.0,
                effect_obj.worldPosition[2]
            )
            effect_obj.visible = False
            effect_obj["_anim_playing"] = False

            try:
                effect_obj.stopAction(0)
            except Exception:
                pass

            _log("Uncollected effect hidden at y=-500")
            return True
    except Exception as e:
        if DEBUG:
            print(f"Error hiding effect: {e}")
    return False

# =============================================================================
# MATRIX EFFECT HANDLING
# =============================================================================
def _get_matrix_effect_obj(owner):
    """Return cached matrix object, searching only once"""
    if "_matrix_obj_cached" not in owner:
        scene = bge.logic.getCurrentScene()
        owner["_matrix_obj_cached"] = scene.objects.get(MATRIX_EFFECT_OBJECT_NAME)
    return owner["_matrix_obj_cached"]

def _activate_matrix_effect(owner, position, orientation=None):
    """Activate matrix effect animation with correct rotation"""
    try:
        matrix_effect = _get_matrix_effect_obj(owner)

        if not matrix_effect:
            _log("Matrix object not found")
            return False

        # 1. Save current rotation to restore later
        if "_original_orientation" not in matrix_effect:
            matrix_effect["_original_orientation"] = matrix_effect.worldOrientation.copy()

        # 2. Position with World object position and rotation
        matrix_effect.worldPosition = position.copy()

        if orientation:
            matrix_effect.worldOrientation = orientation.copy()
        else:
            matrix_effect.worldOrientation = (0, 0, 0)

        # 3. Make visible
        matrix_effect.visible = True

        # 4. Disable physics temporarily
        try:
            matrix_effect.suspendDynamics()
        except Exception:
            pass

        # 5. Setup timing
        matrix_effect["_playing_matrix_anim"] = True
        matrix_effect["_matrix_anim_start"] = bge.logic.getRealTime()
        matrix_effect["_matrix_anim_duration"] = 1.2

        # 6. Play animation
        try:
            matrix_effect.playAction(
                MATRIX_ANIMATION_NAME,
                1, 9,
                play_mode=bge.logic.KX_ACTION_MODE_PLAY,
                layer=0,
                priority=0,
                blendin=0
            )
            _log("Matrix animation started")
        except Exception as e:
            _log(f"Animation error: {e}")

        return True

    except Exception as e:
        _log(f"Error activating matrix effect: {e}")
        return False

def _handle_matrix_effects(owner):
    """
    Handle complete cleanup of matrix effects with rotation.
    Uses cache instead of iterating scene.objects every frame.
    """
    current_time = bge.logic.getRealTime()
    matrix_effect = _get_matrix_effect_obj(owner)

    if not matrix_effect:
        return

    if not matrix_effect.get("_playing_matrix_anim", False):
        return

    start_time = matrix_effect.get("_matrix_anim_start", 0)
    duration = matrix_effect.get("_matrix_anim_duration", 1.2)

    if current_time >= start_time + duration:
        # 1. Stop animation
        try:
            matrix_effect.stopAction(0)
        except Exception:
            pass

        # 2. Move to OUT position
        matrix_effect.worldPosition = MATRIX_OUT_POSITION
        matrix_effect.worldOrientation = MATRIX_OUT_ORIENTATION

        # 3. Restore original rotation if exists
        if "_original_orientation" in matrix_effect:
            try:
                matrix_effect.worldOrientation = matrix_effect["_original_orientation"]
            except Exception:
                pass

        # 4. Hide
        matrix_effect.visible = False

        # 5. Reactivate physics
        try:
            matrix_effect.restoreDynamics()
        except Exception:
            pass

        # 6. Clear state
        matrix_effect["_playing_matrix_anim"] = False
        _log("Matrix effect cleaned up")

# =============================================================================
# BASIC OBJECT FUNCTIONS
# =============================================================================
def _is_world_object(owner):
    return owner.name.startswith("Object.World.")

def _setup_object_properties(owner):
    """Simple property setup - executed only once per object"""
    if owner.get("_props_initialized", False):
        return

    if "item_type" not in owner or "item_id" not in owner:
        name_parts = owner.name.split(".")
        if len(name_parts) >= 4:
            period = name_parts[2].lower()
            owner["item_type"] = "bronze" if period == "bronze" else period
            try:
                owner["item_id"] = int(name_parts[3])
            except Exception:
                owner["item_id"] = 0

    if "collection_item" not in owner:
        owner["collection_item"] = True
    if "restored" not in owner:
        owner["restored"] = 0
    if "ubication" not in owner:
        owner["ubication"] = 0
    if "exhibition" not in owner:
        owner["exhibition"] = 0

    if "_original_scale" not in owner:
        owner["_original_scale"] = owner.localScale.copy()

    # Cache children once during setup
    owner["_children_cache"] = list(owner.childrenRecursive)

    owner["_props_initialized"] = True

    if DEBUG:
        _log(f"{owner.name}: type={owner.get('item_type', '?')}, id={owner.get('item_id', '?')}")

# =============================================================================
# COLLECTION VERIFICATION
# =============================================================================
def _can_collect_object(owner):
    """Simplified verification"""
    if not _is_world_object(owner):
        return False

    if not owner.visible:
        return False

    item_type = owner.get("item_type", "")
    item_id = owner.get("item_id", 0)

    if not item_type or item_id <= 0:
        return False

    if _is_object_selected(item_type, item_id):
        return False

    if owner.get("already_selected", False):
        return False

    if getattr(bge.logic, "hud_pause_open", False):
        return False
    if getattr(bge.logic, "hud_inventory_open", False):
        return False
    if getattr(bge.logic, "hud_inventory_v2_open", False):
        return False

    return True

# =============================================================================
# VISUAL EFFECTS
# =============================================================================
def _apply_tint_to_branch(owner, rgba):
    """
    Apply tint to object and its children.
    Uses cached children list from _setup_object_properties()
    """
    r, g, b, a = rgba
    try:
        owner.color = [r, g, b, a]
    except Exception:
        pass

    for child in owner.get("_children_cache", []):
        try:
            child.color = [r, g, b, a]
        except Exception:
            pass

    owner["_current_tint"] = rgba

def _apply_hover_effects(owner):
    """Complete hover effect"""
    if not owner.get("_mouse_over", False):
        owner["_mouse_over"] = True

        _apply_tint_to_branch(owner, HOVER_TINT)

        if "_original_scale" in owner:
            orig = owner["_original_scale"]
            owner.localScale = [s * HOVER_SCALE_FACTOR for s in orig]

def _apply_click_effect(owner):
    """Momentary click effect"""
    _apply_tint_to_branch(owner, CLICK_TINT)
    # Schedule restoration without blocking the engine
    owner["_click_restore_time"] = bge.logic.getRealTime() + 0.1

def _reset_visual_effects(owner):
    """Complete visual reset"""
    if owner.get("_mouse_over", False):
        owner["_mouse_over"] = False
        _apply_tint_to_branch(owner, IDLE_TINT)

        if "_original_scale" in owner:
            owner.localScale = owner["_original_scale"]

def _handle_click_restoration(owner):
    """Handle restoration after click"""
    if "_click_restore_time" in owner:
        current_time = bge.logic.getRealTime()
        if current_time >= owner["_click_restore_time"]:
            if owner.get("_mouse_over", False):
                _apply_tint_to_branch(owner, HOVER_TINT)
            del owner["_click_restore_time"]

# =============================================================================
# MOUSE DETECTION VIA SENSORS
# =============================================================================
def _update_mouse_sensors(cont, owner):
    """
    Update mouse state based on sensors.

    Returns:
        tuple: (mouse_over, mouse_click)
    """
    # Exclude matrix effects before reading sensors
    if MATRIX_EFFECT_OBJECT_NAME in owner.name:
        return False, False

    # Modals block interaction
    if getattr(bge.logic, "hud_pause_open", False) or \
       getattr(bge.logic, "hud_inventory_open", False) or \
       getattr(bge.logic, "hud_inventory_v2_open", False):
        return False, False

    mouse_over = False
    mouse_click = False

    mouse_over_sensor = cont.sensors.get("Mouse.Over")
    if mouse_over_sensor and mouse_over_sensor.positive:
        mouse_over = True

        mouse_click_sensor = cont.sensors.get("Mouse.Click")
        if mouse_click_sensor and mouse_click_sensor.positive:
            mouse_click = True

    return mouse_over, mouse_click

# =============================================================================
# COMPLETE COLLECTION PROCESS
# =============================================================================
def _collect_object(owner):
    """Collection with all effects"""
    if not _can_collect_object(owner):
        return False

    item_type = owner.get("item_type", "")
    item_id = owner.get("item_id", 0)

    if not item_type or item_id <= 0:
        return False

    current_restored = int(owner.get("restored", 0))
    current_ubication = int(owner.get("ubication", 0))
    current_exhibition = int(owner.get("exhibition", 0))

    object_position = owner.worldPosition.copy()
    object_orientation = owner.worldOrientation.copy()

    # 1. Mark in persistence (IMPORTANT: first)
    _mark_object_selected(item_type, item_id)
    owner["already_selected"] = True

    # 2. Hide object immediately
    owner.visible = False
    owner.worldPosition = (1e6, 1e6, 1e6)

    # 3. Reset visual effects
    _reset_visual_effects(owner)

    # 4. Hide uncollected effect
    _hide_uncollected_effect()

    # 5. Play pickup sound
    _play_pickup_sound()

    # 6. Activate matrix effect with rotation
    _activate_matrix_effect(owner, object_position, object_orientation)

    # 7. Show info text based on restoration state
    if current_restored == 0:
        bge.logic.sendMessage("add_info_text", "info.show|info_text|21|field=info_text")
        _log(f"Object needs restoration: {item_type}#{item_id}")

        try:
            bge.logic.sendMessage(
                "restoration_npc",
                f"activate|item_type={item_type}|item_id={item_id}|delay=3.0"
            )
        except Exception:
            pass

    elif current_restored == 2:
        bge.logic.sendMessage("add_info_text", "info.show|info_text|22|field=info_text")
        _log(f"Object already restored: {item_type}#{item_id}")

    # 8. Send message with all properties
    body = (
        f"action=collection_item_acquired|item_type={item_type}|item_id={item_id}"
        f"|source=world|restored={current_restored}"
        f"|ubication={current_ubication}|exhibition={current_exhibition}"
    )

    try:
        bge.logic.sendMessage("achievement", body)
        _log(f"Message sent: {item_type}#{item_id}")
    except Exception as e:
        _log(f"Error sending message: {e}")

    return True

# =============================================================================
# STABLE MOUSE OVER HANDLING
# =============================================================================
def _handle_mouse_over_stable(owner, current_mouse_over):
    """Stabilization to prevent flickering"""
    if "_mouse_over_counter" not in owner:
        owner["_mouse_over_counter"] = 0
    if "_mouse_out_counter" not in owner:
        owner["_mouse_out_counter"] = 0

    previous_mouse_over = owner.get("_mouse_over", False)

    if current_mouse_over:
        owner["_mouse_out_counter"] = 0

        if not previous_mouse_over:
            owner["_mouse_over_counter"] += 1

            if owner["_mouse_over_counter"] >= 2:
                _apply_hover_effects(owner)
                owner["_mouse_over_counter"] = 0
    else:
        owner["_mouse_over_counter"] = 0

        if previous_mouse_over:
            owner["_mouse_out_counter"] += 1

            if owner["_mouse_out_counter"] >= 2:
                _reset_visual_effects(owner)
                owner["_mouse_out_counter"] = 0

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def handle():
    """Main function with sensor-based detection"""
    cont = bge.logic.getCurrentController()
    owner = cont.owner

    # 1. Cleanup matrix effects
    _handle_matrix_effects(owner)

    # 2. Only World objects
    if not _is_world_object(owner):
        return

    # 3. Setup properties
    _setup_object_properties(owner)

    # 4. Initialize mouse state
    if "_mouse_over" not in owner:
        owner["_mouse_over"] = False

    # 5. Handle click restoration
    _handle_click_restoration(owner)

    # 6. Critical verification: if already collected
    item_type = owner.get("item_type", "")
    item_id = owner.get("item_id", 0)

    if item_type and item_id > 0:
        if _is_object_selected(item_type, item_id):
            owner.visible = False
            owner.worldPosition = (1e6, 1e6, 1e6)
            if owner.get("_mouse_over", False):
                _reset_visual_effects(owner)
            return

    # 7. If not visible, exit
    if not owner.visible:
        if owner.get("_mouse_over", False):
            _reset_visual_effects(owner)
        return

    # 8. Block during modals
    if getattr(bge.logic, "hud_pause_open", False) or \
       getattr(bge.logic, "hud_inventory_open", False) or \
       getattr(bge.logic, "hud_inventory_v2_open", False):
        if owner.get("_mouse_over", False):
            _reset_visual_effects(owner)
        return

    # 9. Check mouse over and click via sensors
    mouse_over, mouse_click = _update_mouse_sensors(cont, owner)

    # 10. Handle hover effects with stabilization
    _handle_mouse_over_stable(owner, mouse_over)

    # 11. Handle click from sensor
    if mouse_over and mouse_click:
        _apply_click_effect(owner)
        _log(f"CLICK on {owner.name} (sensor)")

        success = _collect_object(owner)

        if success:
            _log("Collection successful")
        else:
            _log("Collection failed")

    # 12. Periodic debug
    if DEBUG and owner.visible:
        if "_debug_counter" not in owner:
            owner["_debug_counter"] = 0

        owner["_debug_counter"] += 1
        if owner["_debug_counter"] >= 600:
            owner["_debug_counter"] = 0
            _log(f"{owner.name}: visible={owner.visible}, mouse_over={owner.get('_mouse_over', False)}")