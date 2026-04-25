"""
storage_spawn.py

Optimized storage spawn system with uncollected effect and reminder

This script manages the spawning of collectible world objects at designated spawn
points. It handles object visibility, uncollected visual effects, periodic reminders
when items remain uncollected, and integration with the persistence system.

Main Features:
    1. Spawns world objects at Empty.Objects.Spawn location
    2. Maintains list of uncollected items from persistence system
    3. Shows uncollected effect animation on visible objects
    4. Sends periodic reminders when items await collection
    5. Cleans up invalid or already collected objects
    6. Plays spawn sound effect on object appearance
    7. Cooldown system to prevent rapid spawning

Setup:
    Connect in Logic Bricks as Python controller/module 'storage_spawn.main'
    Requires Empty.Objects.Spawn object in scene as spawn point
    Requires Uncollected.Effect object with animation for visual feedback

Configurable Variables:
    DEBUG (bool): Enable debug messages (default: False)
    SPAWN_INTERVAL (float): Seconds between spawn checks (default: 8.0)
    SPAWN_COOLDOWN (float): Cooldown after spawn (default: 3.0)
    SPAWN_ROOT_NAME (str): Spawn point object name (default: "Empty.Objects.Spawn")
    UNCOLLECTED_EFFECT_NAME (str): Effect object name (default: "Uncollected.Effect")
    UNCOLLECTED_EFFECT_ANIM (str): Animation name (default: "Uncollected_EffectAction")
    REMINDER_INTERVAL (float): Seconds between reminder messages (default: 60.0)
    EFFECT_UPDATE_INTERVAL (float): Effect position update rate (default: 0.1)
    CLEANUP_INTERVAL (float): Cleanup execution interval (default: 2.0)

Notes:
    - Uses globalDict for persistent selection tracking across scenes
    - All world objects are hidden at initialization
    - Objects spawn at the root spawn point position
    - Effect animation loops while object is visible
    - Reminder only sent when an uncollected object exists

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
__description__ = "World object spawn system with uncollected effect and reminders"

# =============================================================================
# IMPORTS AND CONFIGURATION
# =============================================================================
import bge
import random
import game_access

DEBUG = False
SPAWN_INTERVAL = 10  #  8 (Testing); 10 (Production)
SPAWN_COOLDOWN = 10  #  3 (Testing); 10 (Production)
SPAWN_ROOT_NAME = "Empty.Objects.Spawn"
UNCOLLECTED_EFFECT_NAME = "Uncollected.Effect"
UNCOLLECTED_EFFECT_ANIM = "Uncollected_EffectAction"
UNCOLLECTED_EFFECT_ANIM_START = 1
UNCOLLECTED_EFFECT_ANIM_END = 9
REMINDER_INTERVAL = 60.0

# Effect update and cleanup intervals (in seconds)
EFFECT_UPDATE_INTERVAL = 0.1   # 10 times per second, sufficient for visual effects
CLEANUP_INTERVAL = 2.0          # Cleanup every 2 seconds, not every frame

# =============================================================================
# PERSISTENCE SYSTEM
# =============================================================================
WORLD_OBJECTS_SELECTED_KEY = "_world_objects_selected"

def _log(*args):
    if DEBUG:
        print("[spawn]", *args)

def _init_selected_dict():
    if WORLD_OBJECTS_SELECTED_KEY not in bge.logic.globalDict:
        bge.logic.globalDict[WORLD_OBJECTS_SELECTED_KEY] = {}

def _is_object_selected(item_type, item_id):
    key = f"{item_type}{item_id}"
    d = bge.logic.globalDict.get(WORLD_OBJECTS_SELECTED_KEY)
    return d.get(key, False) if d else False

# =============================================================================
# ITEM MANAGEMENT
# =============================================================================
def _get_available_items():
    """Get non-selected items"""
    all_items = [
        ("pal", 1), ("pal", 2),
        ("neo", 1), ("neo", 2),
        ("bronze", 1), ("bronze", 2),
        ("iberian", 1), ("iberian", 2),
        ("roman", 1), ("roman", 2)
    ]
    available = []
    for item_type, item_id in all_items:
        if not _is_object_selected(item_type, item_id):
            available.append((item_type, item_id))
    return available

def _get_world_object_name(item_type, item_id):
    type_cap = item_type.capitalize() if item_type != "bronze" else "Bronze"
    return f"Object.World.{type_cap}.{item_id}"

def _force_setup_world_object(obj, item_type, item_id):
    """Force setup of World object properties"""
    try:
        obj["item_type"] = item_type
        obj["item_id"] = item_id
        obj["collection_item"] = True
        obj["state"] = "world"
        obj["object_type"] = "world"

        if _is_object_selected(item_type, item_id):
            obj["already_selected"] = True
            return False
        else:
            obj["already_selected"] = False

        obj["restored"] = 0
        obj["ubication"] = 0
        obj["exhibition"] = 0

        return True

    except Exception:
        obj["item_type"] = item_type
        obj["item_id"] = item_id
        obj["collection_item"] = True
        obj["already_selected"] = False
        return True

# =============================================================================
# VISIBLE OBJECT CACHING
# =============================================================================
def _get_visible_world_object(owner):
    """
    Use cache to avoid iterating scene every frame.
    Returns cached visible World object, or searches if needed.
    """
    scene = bge.logic.getCurrentScene()
    current_time = bge.logic.getRealTime()

    cache_expiry = owner.get("_visible_obj_cache_expiry", 0)
    if current_time < cache_expiry:
        cached_name = owner.get("_visible_obj_cache_name", "")
        if cached_name:
            obj = scene.objects.get(cached_name)
            if obj and obj.visible:
                return obj
        else:
            return None

    spawn_root = scene.objects.get(SPAWN_ROOT_NAME)
    found_obj = None

    if spawn_root:
        spawn_pos = spawn_root.worldPosition
        for obj in scene.objects:
            if obj.name.startswith("Object.World.") and obj.visible:
                distance = (obj.worldPosition - spawn_pos).length
                if distance < 5.0:
                    found_obj = obj
                    break

    owner["_visible_obj_cache_expiry"] = current_time + EFFECT_UPDATE_INTERVAL
    owner["_visible_obj_cache_name"] = found_obj.name if found_obj else ""

    return found_obj

def _get_visible_world_objects_count(owner):
    """
    Reuse cache from _get_visible_world_object.
    Returns 1 if visible object exists, 0 otherwise.
    """
    obj = _get_visible_world_object(owner)
    return 1 if obj else 0

# =============================================================================
# UNCOLLECTED EFFECT MANAGEMENT
# =============================================================================
def _update_uncollected_effect(owner):
    """
    Update position and animation only when needed.
    - Uses cache to avoid iterating scene every frame.
    - Only plays animation once when object appears.
    - Only moves effect when reference object changes.
    """
    scene = bge.logic.getCurrentScene()
    effect_obj = scene.objects.get(UNCOLLECTED_EFFECT_NAME)

    if not effect_obj:
        return False

    visible_world_obj = _get_visible_world_object(owner)

    prev_tracked = owner.get("_effect_tracked_obj", "")
    current_tracked = visible_world_obj.name if visible_world_obj else ""

    if current_tracked == prev_tracked:
        return bool(visible_world_obj)

    owner["_effect_tracked_obj"] = current_tracked

    if visible_world_obj:
        effect_obj.worldPosition = visible_world_obj.worldPosition.copy()
        effect_obj.worldOrientation = visible_world_obj.worldOrientation.copy()
        effect_obj.visible = True
    else:
        pos = effect_obj.worldPosition.copy()
        effect_obj.worldPosition = (pos[0], -500.0, pos[2])
        effect_obj.visible = False

        if owner.get("_anim_playing", False):
            owner["_anim_playing"] = False
            try:
                effect_obj.stopAction(0)
            except Exception:
                pass

        return False

# =============================================================================
# REMINDER SYSTEM
# =============================================================================
def _send_reminder_message(owner):
    """Send reminder message to Game.Controller"""
    try:
        owner.sendMessage(
            "add_info_text",
            "info.show|info_text|33|field=info_text",
            "Game.Controller"
        )
        _log("Reminder sent: object waiting to be collected")
        return True
    except Exception as e:
        _log(f"Error sending reminder: {e}")
        return False

def _check_reminder(owner, current_time):
    """
    Check if reminder should be sent to player.
    Only sends if a visible object is waiting to be collected.
    """
    last_reminder = owner.get("_last_reminder_time", current_time)

    if current_time - last_reminder >= REMINDER_INTERVAL:
        if _get_visible_world_objects_count(owner) > 0:
            _send_reminder_message(owner)
            owner["_last_reminder_time"] = current_time

# =============================================================================
# SPAWN SOUND
# =============================================================================
def _play_spawn_sound():
    """Play spawn sound effect"""
    try:
        bge.logic.sendMessage(
            "sound_fx.play",
            "sound_fx.play|spawn.ogg|volume=0.7"
        )
        _log("Spawn sound played")
        return True
    except Exception:
        return False

# =============================================================================
# SPAWN LOGIC
# =============================================================================
def _can_spawn_new_item(owner):
    """Spawn logic with owner for cache access"""
    if getattr(bge.logic, "hud_inventory_v2_open", False):
        return False
    if getattr(bge.logic, "hud_inventory_open", False):
        return False
    if getattr(bge.logic, "hud_pause_open", False):
        return False

    if _get_visible_world_objects_count(owner) > 0:
        return False

    state = game_access.get_state()
    if not state:
        return False

    if getattr(state, 'dialog_active', False):
        return False

    inventoried, restored, exhibited = state.update_collection_stats()

    if state.collection_items_total == 0:
        return True

    if inventoried == state.collection_items_total:
        return True

    return False

def _spawn_world_object(item_type, item_id, owner):
    """Spawn object with forced configuration"""
    scene = bge.logic.getCurrentScene()
    spawn_root = scene.objects.get(SPAWN_ROOT_NAME)
    if not spawn_root:
        return None

    obj_name = _get_world_object_name(item_type, item_id)
    obj = scene.objects.get(obj_name)

    if not obj:
        return None

    try:
        if _is_object_selected(item_type, item_id):
            obj.visible = False
            obj.worldPosition = (1e6, 1e6, 1e6)
            return None

        if not _force_setup_world_object(obj, item_type, item_id):
            obj.visible = False
            return None

        obj.worldPosition = spawn_root.worldPosition.copy()
        obj.worldOrientation = spawn_root.worldOrientation.copy()
        obj.localScale = (1.0, 1.0, 1.0)
        obj.visible = True

        _play_spawn_sound()
        bge.logic.sendMessage("add_info_text", "info.show|info_text|7|field=info_text")

        if obj.parent:
            try:
                obj.removeParent()
            except Exception:
                pass

        # Invalidate cache to force immediate re-search after spawn
        owner["_visible_obj_cache_expiry"] = 0
        owner["_visible_obj_cache_name"] = ""
        owner["_effect_tracked_obj"] = ""

        # Update effect immediately after spawn
        _update_uncollected_effect(owner)

        return obj

    except Exception:
        return None

# =============================================================================
# CLEANUP SYSTEM
# =============================================================================
def _cleanup_invalid_objects(owner):
    """
    Periodic cleanup (not every frame).
    Only runs every CLEANUP_INTERVAL seconds.
    """
    current_time = bge.logic.getRealTime()
    last_cleanup = owner.get("_last_cleanup_time", 0)

    if current_time - last_cleanup < CLEANUP_INTERVAL:
        return 0

    owner["_last_cleanup_time"] = current_time

    try:
        scene = bge.logic.getCurrentScene()
        cleaned = 0

        for obj in scene.objects:
            if not obj.name.startswith("Object.World."):
                continue
            if not obj.visible:
                continue

            item_type = obj.get("item_type", "")
            item_id = obj.get("item_id", 0)

            if not item_type or item_id <= 0:
                obj.visible = False
                obj.worldPosition = (1e6, 1e6, 1e6)
                cleaned += 1
                continue

            if _is_object_selected(item_type, item_id):
                obj.visible = False
                obj.worldPosition = (1e6, 1e6, 1e6)
                cleaned += 1

        if cleaned > 0:
            owner["_visible_obj_cache_expiry"] = 0
            owner["_visible_obj_cache_name"] = ""
            _log(f"Cleaned {cleaned} invalid objects")

        return cleaned

    except Exception:
        return 0

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main():
    """Main function - OPTIMIZED SYSTEM"""
    cont = bge.logic.getCurrentController()
    owner = cont.owner
    current_time = bge.logic.getRealTime()

    # INITIALIZATION (only once)
    if not owner.get("_initialized", False):
        owner["_initialized"] = True
        owner["_last_check_time"] = current_time
        owner["_last_spawn_time"] = 0
        owner["_spawn_cooldown_until"] = 0
        owner["_last_reminder_time"] = current_time
        owner["_last_cleanup_time"] = 0

        # Visible object cache
        owner["_visible_obj_cache_expiry"] = 0
        owner["_visible_obj_cache_name"] = ""

        # Effect state
        owner["_effect_tracked_obj"] = ""
        owner["_anim_playing"] = False

        # Timer for visual effect throttle
        owner["_last_effect_update"] = 0

        _init_selected_dict()

        # Hide ALL World objects at start
        scene = bge.logic.getCurrentScene()
        for obj in scene.objects:
            if obj.name.startswith("Object.World."):
                obj.visible = False
                obj.worldPosition = (1e6, 1e6, 1e6)

        # Hide initial effect
        effect_obj = scene.objects.get(UNCOLLECTED_EFFECT_NAME)
        if effect_obj:
            effect_obj.visible = False
            pos = effect_obj.worldPosition.copy()
            effect_obj.worldPosition = (pos[0], -500.0, pos[2])
            owner["_anim_playing"] = False

        _log("Spawn system initialized")

    # PERIODIC OPERATIONS (not every frame)

    # Periodic cleanup of invalid objects
    _cleanup_invalid_objects(owner)

    # Effect update with explicit throttle
    last_effect_update = owner.get("_last_effect_update", 0)
    if current_time - last_effect_update >= EFFECT_UPDATE_INTERVAL:
        owner["_last_effect_update"] = current_time
        _update_uncollected_effect(owner)

    # Reminder check
    _check_reminder(owner, current_time)

    # SPAWN LOGIC

    # Active cooldown: do not process spawn
    if current_time < owner.get("_spawn_cooldown_until", 0):
        return

    # Interval between spawn checks
    if current_time - owner["_last_check_time"] < SPAWN_INTERVAL:
        return

    owner["_last_check_time"] = current_time

    # Attempt spawn
    if _can_spawn_new_item(owner):
        available_items = _get_available_items()

        if not available_items:
            return

        item_type, item_id = random.choice(available_items)
        obj = _spawn_world_object(item_type, item_id, owner)

        if obj:
            owner["_last_spawn_time"] = current_time
            owner["_spawn_cooldown_until"] = current_time + SPAWN_COOLDOWN
            owner["_last_reminder_time"] = current_time
            _log(f"Spawned: {item_type} {item_id}")