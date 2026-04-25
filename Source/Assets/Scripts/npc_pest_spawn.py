"""
npc_pest_spawn.py

Enemy Pest spawn manager

This script manages the spawning of enemy pests (mice and cockroaches) in designated
spawn zones. It handles wave-based spawning with rest periods between waves,
global enemy limits, and zone state management.

Main Features:
    1. Zone-based spawning with activation/deactivation via messages
    2. Wave system with spawning phase and rest phase between waves
    3. Global enemy limits (max mice, max cockroaches)
    4. Automatic cleanup of destroyed enemies from zone lists
    5. Cooldown between individual spawns within a wave
    6. Death notification handling for proper enemy removal
    7. Support for multiple spawn points with configurable enemy types

Setup:
    Connect in Logic Bricks as Python controller/module 'npc_pest_spawn.main'
    Object requires sensors:
        - MsgOn (message sensor for zone activation)
        - MsgOff (message sensor for zone deactivation)
    Spawn points must:
        - Have name containing 'Spawn.Pest'
        - Have property 'spawn_id' (int) for identification
        - Optional property 'spawn_type' (0=random, 1=mouse, 2=cockroach)
        - Optional property 'max_enemies' (int, default: 3)

Configurable Variables:
    DEBUG_MODE (bool): Enable debug messages (default: True)
    SPAWN_COOLDOWN_DURATION (float): Seconds between individual spawns (default: 3.0)
    MAX_MICE (int): Global maximum active mice (default: 8)
    MAX_COCKROACHES (int): Global maximum active cockroaches (default: 12)
    REST_DURATION_MIN (float): Minimum rest between waves (default: 15.0)
    REST_DURATION_MAX (float): Maximum rest between waves (default: 25.0)

Notes:
    - Enemy objects must be named 'Pest.Mouse' and 'Pest.Cockroach'
    - Enemy scripts must set 'active_mouse' or 'active_cockroach' properties
    - Spawn zones receive spawn_id as message body (integer)
    - Death notifications are handled via notify_mouse_death and notify_cockroach_death

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
__description__ = "Pest spawn manager with wave-based spawning and zone control"

# =============================================================================
# IMPORTS AND CONFIGURATION
# =============================================================================
import bge
import random

DEBUG_MODE = True
SPAWN_COOLDOWN_DURATION = 3.0   # Seconds between individual spawns within a wave
MAX_MICE = 8
MAX_COCKROACHES = 12

# WAVE CONFIGURATION
REST_DURATION_MIN = 15.0   # Minimum seconds of rest between waves
REST_DURATION_MAX = 25.0   # Maximum seconds of rest between waves
HORDE_COMPLETE_THRESHOLD = 0.0  # Fraction of enemies that must die to consider wave completed (0.0 = all)

# Zone states
ZONE_STATE_SPAWNING = "spawning"
ZONE_STATE_RESTING  = "resting"

def debug_print(message):
    if DEBUG_MODE:
        print(message)

# =============================================================================
# ENTRY POINT
# =============================================================================
def main(cont):
    owner = cont.owner

    if "initialized" not in owner:
        initialize_pest_manager(owner)

    process_spawn_messages(cont, owner)
    process_active_zones(owner)
    update_timers(owner)
    restore_manager_position(owner)

# =============================================================================
# INITIALIZATION
# =============================================================================
def initialize_pest_manager(owner):
    owner["initialized"]             = True
    owner["mouse_total"]             = 0
    owner["cockroach_total"]         = 0
    owner["active_mice"]             = 0
    owner["active_cockroaches"]      = 0
    owner["max_mice"]                = MAX_MICE
    owner["max_cockroaches"]         = MAX_COCKROACHES
    owner["active_mouse_list"]       = []
    owner["active_cockroach_list"]   = []
    owner["active_spawn_zones"]      = {}
    owner["spawn_cooldown"]          = 0.0
    owner["spawn_cooldown_duration"] = SPAWN_COOLDOWN_DURATION
    debug_print("[PEST_MANAGER] Initialized")

# =============================================================================
# TIMERS
# =============================================================================
def update_timers(owner):
    delta = 1 / 60.0

    # Global cooldown between individual spawns
    if owner["spawn_cooldown"] > 0:
        owner["spawn_cooldown"] = max(0.0, owner["spawn_cooldown"] - delta)

    # Rest timers by zone
    for zone_data in owner["active_spawn_zones"].values():
        if zone_data["state"] == ZONE_STATE_RESTING:
            zone_data["rest_timer"] = max(0.0, zone_data["rest_timer"] - delta)
            if zone_data["rest_timer"] <= 0:
                _start_spawning_phase(zone_data)

# =============================================================================
# MESSAGE HANDLING
# =============================================================================
def process_spawn_messages(cont, owner):
    _process_sensor(cont, owner, sensor_name="MsgOn",  action=activate_spawn_zone)
    _process_sensor(cont, owner, sensor_name="MsgOff", action=deactivate_spawn_zone)

def _process_sensor(cont, owner, sensor_name, action):
    sensor = cont.sensors.get(sensor_name)
    if not sensor or not sensor.positive:
        return

    for body in sensor.bodies:
        try:
            spawn_id = int(body)
            action(owner, spawn_id)
        except (ValueError, TypeError) as e:
            debug_print(f"[PEST_MANAGER] Invalid body in {sensor_name}: '{body}': {e}")

# =============================================================================
# ZONE MANAGEMENT
# =============================================================================
def activate_spawn_zone(owner, spawn_id):
    scene       = bge.logic.getCurrentScene()
    spawn_key   = str(spawn_id)
    spawn_point = find_spawn_point_by_id(scene, spawn_id)

    if not spawn_point:
        debug_print(f"[PEST_MANAGER] Spawn point {spawn_id} not found")
        return

    if spawn_key in owner["active_spawn_zones"]:
        debug_print(f"[PEST_MANAGER] Zone {spawn_id} already active, ignoring")
        return

    owner["active_spawn_zones"][spawn_key] = {
        "spawn_point":      spawn_point,
        "max_enemies":      spawn_point.get("max_enemies", 3),
        "current_enemies":  [],
        "state":            ZONE_STATE_SPAWNING,  # Starts spawning
        "rest_timer":       0.0,
        "horde_count":      0,   # How many complete waves have been launched
        "horde_spawned_once": False,  # Flag to track if first wave started
    }
    debug_print(f"[PEST_MANAGER] Zone {spawn_id} ACTIVATED -- Phase: SPAWNING")

def deactivate_spawn_zone(owner, spawn_id):
    spawn_key = str(spawn_id)
    if spawn_key in owner["active_spawn_zones"]:
        del owner["active_spawn_zones"][spawn_key]
        debug_print(f"[PEST_MANAGER] Zone {spawn_id} DEACTIVATED")

def _start_rest_phase(zone_data, spawn_key):
    """Start rest period after completing a wave."""
    zone_data["state"]      = ZONE_STATE_RESTING
    zone_data["rest_timer"] = random.uniform(REST_DURATION_MIN, REST_DURATION_MAX)
    zone_data["horde_count"] += 1
    debug_print(
        f"[PEST_MANAGER] Zone {spawn_key} -- Wave {zone_data['horde_count']} completed. "
        f"Resting {zone_data['rest_timer']:.1f}s"
    )

def _start_spawning_phase(zone_data):
    """Reactivate spawning after rest."""
    zone_data["state"]      = ZONE_STATE_SPAWNING
    zone_data["rest_timer"] = 0.0
    debug_print("[PEST_MANAGER] Zone reactivated -- New wave starting")

# =============================================================================
# PERIODIC ZONE PROCESSING
# =============================================================================
def process_active_zones(owner):
    if owner["spawn_cooldown"] > 0:
        return

    if not owner["active_spawn_zones"]:
        return

    for spawn_key, zone_data in owner["active_spawn_zones"].items():

        # Zones in rest do not spawn
        if zone_data["state"] == ZONE_STATE_RESTING:
            continue

        # Clean up references to destroyed objects
        zone_data["current_enemies"] = [
            e for e in zone_data["current_enemies"]
            if e is not None and not e.invalid
        ]

        current_count = len(zone_data["current_enemies"])
        max_enemies   = zone_data["max_enemies"]

        # -- Wave completion detection --
        # Wave is considered completed when zone was full (at least once)
        # and now is empty: all enemies have died.
        if current_count == 0 and zone_data["horde_count"] >= 0:
            # Only enter rest if there was at least one previous spawn
            if zone_data.get("horde_spawned_once", False):
                _start_rest_phase(zone_data, spawn_key)
                continue

        if current_count >= max_enemies:
            # Zone full: mark that first wave is in progress
            zone_data["horde_spawned_once"] = True
            continue

        debug_print(
            f"[PEST_MANAGER] Zone {spawn_key} [{zone_data['state'].upper()}]: "
            f"{current_count}/{max_enemies} -> spawning..."
        )

        enemy = spawn_enemy_for_zone(owner, zone_data["spawn_point"], int(spawn_key))

        if enemy:
            zone_data["current_enemies"].append(enemy)
            zone_data["horde_spawned_once"] = True  # First wave in progress
            _register_enemy_globally(owner, enemy)
            owner["spawn_cooldown"] = owner["spawn_cooldown_duration"]
            return  # One spawn per tick

def _register_enemy_globally(owner, enemy):
    if enemy.get('active_mouse', False):
        if enemy.name not in owner["active_mouse_list"]:
            owner["active_mouse_list"].append(enemy.name)
            owner["active_mice"]  = len(owner["active_mouse_list"])
            owner["mouse_total"] += 1

    elif enemy.get('active_cockroach', False):
        if enemy.name not in owner["active_cockroach_list"]:
            owner["active_cockroach_list"].append(enemy.name)
            owner["active_cockroaches"] = len(owner["active_cockroach_list"])
            owner["cockroach_total"]   += 1

# =============================================================================
# SPAWN LOGIC
# =============================================================================
def spawn_enemy_for_zone(owner, spawn_point, spawn_id):
    scene      = bge.logic.getCurrentScene()
    enemy_type = determine_enemy_type(spawn_point)

    if enemy_type == "mouse" and owner["active_mice"] >= owner["max_mice"]:
        debug_print("[PEST_MANAGER] Global mouse limit reached")
        return None
    if enemy_type == "cockroach" and owner["active_cockroaches"] >= owner["max_cockroaches"]:
        debug_print("[PEST_MANAGER] Global cockroach limit reached")
        return None

    obj_name = "Pest.Mouse" if enemy_type == "mouse" else "Pest.Cockroach"

    try:
        enemy = scene.addObject(obj_name, spawn_point, 0)
        if not enemy:
            debug_print(f"[PEST_MANAGER] addObject returned None for '{obj_name}'")
            return None

        if enemy_type == "mouse":
            enemy['active_mouse'] = True
            enemy['health_mouse'] = 3
        else:
            enemy['active_cockroach'] = True
            enemy['health_cockroach'] = 1
            enemy['enemy']            = True

        enemy.setVisible(True)
        enemy.restoreDynamics()
        enemy.worldPosition    = spawn_point.worldPosition.copy()
        enemy.worldOrientation = spawn_point.worldOrientation.copy()
        enemy["last_spawn_id"] = spawn_id

        debug_print(f"[PEST_MANAGER] {enemy_type} created in zone {spawn_id}")
        return enemy

    except Exception as e:
        debug_print(f"[PEST_MANAGER] Error creating {enemy_type}: {e}")
        return None

# =============================================================================
# UTILITIES
# =============================================================================
def find_spawn_point_by_id(scene, spawn_id):
    for obj in scene.objects:
        if "Spawn.Pest" in obj.name:
            try:
                if obj.get("spawn_id", -1) == spawn_id:
                    return obj
            except Exception:
                continue
    return None

def determine_enemy_type(spawn_point):
    spawn_type = spawn_point.get("spawn_type", 0)
    if spawn_type == 1:
        return "mouse"
    if spawn_type == 2:
        return "cockroach"
    return random.choice(["mouse", "cockroach"])

# =============================================================================
# DEATH NOTIFICATIONS
# =============================================================================
def _remove_from_zone(owner, enemy):
    spawn_key = str(enemy.get("last_spawn_id", ""))
    zone = owner["active_spawn_zones"].get(spawn_key)
    if zone and enemy in zone["current_enemies"]:
        zone["current_enemies"].remove(enemy)

def notify_mouse_death(owner, mouse):
    try:
        if mouse.name in owner["active_mouse_list"]:
            owner["active_mouse_list"].remove(mouse.name)
            owner["active_mice"] = len(owner["active_mouse_list"])
        _remove_from_zone(owner, mouse)
        mouse.endObject()
        debug_print("[PEST_MANAGER] Mouse eliminated")
    except Exception as e:
        debug_print(f"[PEST_MANAGER] Error eliminating mouse: {e}")

def notify_cockroach_death(owner, cockroach):
    try:
        if cockroach.name in owner["active_cockroach_list"]:
            owner["active_cockroach_list"].remove(cockroach.name)
            owner["active_cockroaches"] = len(owner["active_cockroach_list"])
        _remove_from_zone(owner, cockroach)
        cockroach.endObject()
        debug_print("[PEST_MANAGER] Cockroach eliminated")
    except Exception as e:
        debug_print(f"[PEST_MANAGER] Error eliminating cockroach: {e}")

# =============================================================================
# COMPATIBILITY STUBS
# =============================================================================
def notify_mouse_activation(owner, cockroach):
    pass

def notify_cockroach_activation(owner, cockroach):
    pass

# =============================================================================
# RESTORE MANAGER POSITION
# =============================================================================
def restore_manager_position(owner):
    if not owner.get("restore_position", False):
        return

    pos = owner.get("original_position")
    ori = owner.get("original_orientation")
    if pos and ori:
        owner.worldPosition    = pos
        owner.worldOrientation = ori

    owner["restore_position"] = False
    owner.pop("original_position",    None)
    owner.pop("original_orientation", None)