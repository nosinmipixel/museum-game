"""
npc_mouse.py

Mouse NPC with synchronized animation and movement

This script controls mouse enemy behavior including intelligent navigation,
attack handling, 3D audio, death effects, and suspension system.

Main Features:
    1. State machine with SPAWN, APPROACH, RETREAT, IDLE, DEATH, STUCK_NAV states
    2. Smart obstacle avoidance with ray detection and dodge mechanics
    3. Cardinal direction navigation for grid-based movement
    4. Attack animation with movement pause during attack
    5. Player damage application with cooldown
    6. 3D positional audio with player-based listener
    7. Death sprite effect with animation
    8. Suspension system for UI/menu blocking
    9. Shot collision detection for player attacks

Setup:
    Connect in Logic Bricks as Python controller/module 'npc_mouse.main'
    Object requires sensors:
        - CollisionPlayer (for player damage)
        - CollisionShot (for damage from attacks)
        - CollisionObstacle (for wall collision)
        - Ray (for obstacle detection)
        - Message.Suspend (for suspension messages)

Configurable Variables:
    DEBUG_MODE (bool): Enable debug messages (default: True)
    SOUNDS_ENABLED (bool): Enable sound effects (default: True)
    SOUND_VOLUME (float): Master volume (default: 0.7)
    SOUND_3D_ENABLED (bool): Enable 3D positional audio (default: True)
    MOUSE_DAMAGE_TO_PLAYER (int): Damage dealt to player (default: 21)
    ATTACK_ANIMATION_DISTANCE (float): Distance to start attack (default: 3.0)
    CONTACT_DISTANCE (float): Distance for collision fallback (default: 1.0)
    GRID_NAVIGATION (bool): Enable 90-degree navigation (default: True)

Notes:
    - Requires game_access module for game state and player health
    - Uses aud module for 3D audio positioning
    - Listener follows player position, not camera
    - Death sprite appears at mouse position on death
    - Obstacle avoidance uses multi-ray detection for better navigation

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
__description__ = "Mouse NPC with synchronized animation, obstacle avoidance, and 3D audio"

# =============================================================================
# IMPORTS AND CONFIGURATION
# =============================================================================
import bge
import math
import random
import aud
from mathutils import Vector, Euler
import game_access

# SUSPENSION SYSTEM CONFIGURATION
SUSPEND_MESSAGE_SENSOR_NAME = "Message.Suspend"
SUSPEND_MESSAGE_SUBJECT = "suspend_logic"

# ATTACK AND DISTANCE CONFIGURATION
ATTACK_ANIMATION_DISTANCE = 3.0
CONTACT_DISTANCE = 1.0
MIN_ATTACK_DURATION = 0.5
ATTACK_MOVEMENT_PAUSE = 0.1

# ENHANCED NAVIGATION CONFIGURATION
OBSTACLE_DETECTION_RANGE = 3.0
OBSTACLE_CHECK_FREQUENCY = 30
GRID_NAVIGATION = True
EVASION_90_DURATION = 2.5
STUCK_DISTANCE_THRESHOLD = 0.02
STUCK_TIME_THRESHOLD = 1.5
WALL_MEMORY_DURATION = 5.0

# GLOBAL CONFIGURATION
DEBUG_MODE = True
SOUNDS_ENABLED = True
SOUND_VOLUME = 0.7
SOUND_3D_ENABLED = True
SOUND_MIN_DISTANCE = 2.0
SOUND_MAX_DISTANCE = 15.0
MOUSE_DAMAGE_TO_PLAYER = 21

# SENSOR NAMES
COLLISION_PLAYER_SENSOR_NAME = "CollisionPlayer"
COLLISION_SHOT_SENSOR_NAME = "CollisionShot"
COLLISION_OBSTACLE_SENSOR_NAME = "CollisionObstacle"

# DEATH SPRITE
DEATH_SPRITE_NAME = "Death.Bug.Effect"

# Global variables for sound management
sound_device = None
sound_handles = {}

# =============================================================================
# DEBUG AND UTILITY FUNCTIONS
# =============================================================================
def debug_print(message):
    """Controlled debug print function"""
    if DEBUG_MODE:
        print(message)

def get_sound_device():
    """Get or create audio device using aud"""
    global sound_device
    if sound_device is None:
        try:
            sound_device = aud.Device()
            sound_device.distance_model = aud.DISTANCE_MODEL_LINEAR
            debug_print("[SOUND] 3D audio device created")
        except Exception as e:
            debug_print(f"[SOUND] Error creating device: {e}")
            return None
    return sound_device

def find_player_robust():
    """Find player object robustly"""
    scene = bge.logic.getCurrentScene()
    if not scene:
        return None

    player = scene.objects.get("Player")
    if player:
        return player

    for obj in scene.objects:
        try:
            if bool(obj.get("player", False)):
                return obj
        except:
            pass

    return None

# =============================================================================
# 3D AUDIO SYSTEM
# =============================================================================
def check_sound_distances(listener_position):
    """Stop sounds that are too far from the player"""
    if not SOUND_3D_ENABLED:
        return

    sounds_to_stop = []

    for sound_key, handle in sound_handles.items():
        if not handle or handle.status != aud.STATUS_PLAYING:
            continue

        if '_' in sound_key:
            try:
                sound_pos_tuple = handle.location
                sound_position = Vector(sound_pos_tuple)
                listener_pos = Vector(listener_position)
                distance = (sound_position - listener_pos).length

                if distance > SOUND_MAX_DISTANCE + 5.0:
                    sounds_to_stop.append(sound_key)
            except Exception as e:
                pass

    for sound_key in sounds_to_stop:
        try:
            sound_handles[sound_key].stop()
            sound_handles[sound_key] = None
        except:
            pass

def update_sound_3d_listener():
    """Use player position instead of camera for listener"""
    if not SOUND_3D_ENABLED:
        return

    try:
        player = find_player_robust()
        if not player:
            return

        device = get_sound_device()
        if not device:
            return

        listener_position = Vector(player.worldPosition)
        device.listener_location = listener_position
        device.listener_orientation = player.worldOrientation.to_quaternion()
        check_sound_distances(listener_position)

    except Exception as e:
        pass

def play_sound_3d(sound_file, owner, loop=False):
    """Play 3D positional sound relative to player"""
    if not SOUNDS_ENABLED or not SOUND_3D_ENABLED:
        return None

    try:
        player = find_player_robust()
        if player:
            distance = (Vector(owner.worldPosition) -
                        Vector(player.worldPosition)).length
            if distance > SOUND_MAX_DISTANCE + 10.0:
                return None

        sound_key = f"{sound_file}_{owner.name}"

        if sound_key in sound_handles and sound_handles[sound_key]:
            if sound_handles[sound_key].status == aud.STATUS_PLAYING:
                try:
                    sound_handles[sound_key].location = tuple(
                        owner.worldPosition)
                except:
                    pass
                return sound_handles[sound_key]

        device = get_sound_device()
        if not device:
            return None

        sound_path = bge.logic.expandPath("//Assets/Sounds/") + sound_file
        sound = aud.Sound(sound_path)
        handle = device.play(sound)

        handle.relative = False
        handle.volume = SOUND_VOLUME
        handle.loop_count = -1 if loop else 0
        handle.distance_maximum = SOUND_MAX_DISTANCE
        handle.distance_reference = SOUND_MIN_DISTANCE
        handle.location = tuple(owner.worldPosition)

        sound_handles[sound_key] = handle
        return handle

    except Exception as e:
        return None

def play_sound_2d(sound_file, loop=False):
    """Maintain compatibility with 2D sound"""
    if not SOUNDS_ENABLED:
        return None

    try:
        if sound_file in sound_handles and sound_handles[sound_file]:
            if sound_handles[sound_file].status == aud.STATUS_PLAYING:
                return sound_handles[sound_file]

        device = get_sound_device()
        if not device:
            return None

        sound_path = bge.logic.expandPath("//Assets/Sounds/") + sound_file
        sound = aud.Sound(sound_path)
        handle = device.play(sound)

        handle.relative = True
        handle.volume = SOUND_VOLUME
        handle.loop_count = -1 if loop else 0

        sound_handles[sound_file] = handle
        return handle

    except Exception as e:
        return None

def play_sound(sound_file, owner=None, loop=False):
    """Main enhanced sound function"""
    if owner and SOUND_3D_ENABLED:
        return play_sound_3d(sound_file, owner, loop)
    else:
        return play_sound_2d(sound_file, loop)

def stop_sound(handle):
    """Stop a sound"""
    if handle:
        try:
            handle.stop()
        except:
            pass

def stop_sound_by_name(sound_file, owner=None):
    """Stop specific sound by name"""
    if owner and SOUND_3D_ENABLED:
        sound_key = f"{sound_file}_{owner.name}"
    else:
        sound_key = sound_file

    if sound_key in sound_handles and sound_handles[sound_key]:
        try:
            sound_handles[sound_key].stop()
            sound_handles[sound_key] = None
        except:
            pass

def cleanup_sounds():
    """Clean up sounds that have finished playing"""
    global sound_handles
    sounds_to_remove = []

    for sound_file, handle in sound_handles.items():
        if handle and handle.status != aud.STATUS_PLAYING:
            sounds_to_remove.append(sound_file)

    for sound_file in sounds_to_remove:
        sound_handles[sound_file] = None

# =============================================================================
# DEATH SPRITE FUNCTIONS
# =============================================================================
def show_death_sprite(owner):
    """Show death sprite at mouse position"""
    try:
        scene = bge.logic.getCurrentScene()
        death_sprite = scene.objects.get(DEATH_SPRITE_NAME)

        if not death_sprite:
            debug_print(f"[MOUSE] Death sprite not found: {DEATH_SPRITE_NAME}")
            return None

        # Position sprite at same location as mouse
        death_sprite.worldPosition = owner.worldPosition.copy()
        death_sprite.worldOrientation = [math.radians(45), 0, math.radians(45)]
        
        # Adjust height
        death_sprite.worldPosition.z += 0.1
        
        # Ensure visible
        death_sprite.visible = True
        
        # Start animation
        try:
            death_sprite.playAction("Sprite_Bug_Anim_UV", 1, 9,
                                   play_mode=bge.logic.KX_ACTION_MODE_PLAY, speed=1.0)
            debug_print(f"[MOUSE] Death sprite shown")
        except:
            pass
            
        return death_sprite
        
    except Exception as e:
        debug_print(f"[MOUSE] Error showing sprite: {e}")
        return None

def hide_death_sprite():
    """Hide death sprite"""
    try:
        scene = bge.logic.getCurrentScene()
        death_sprite = scene.objects.get(DEATH_SPRITE_NAME)
        
        if death_sprite:
            death_sprite.visible = False
            debug_print(f"[MOUSE] Death sprite hidden")
    except:
        pass

# =============================================================================
# ENHANCED NAVIGATION FUNCTIONS
# =============================================================================
def get_cardinal_direction(angle_rad):
    """Convert angle to nearest cardinal direction"""
    angle_deg = math.degrees(angle_rad) % 360
    cardinals = [0, 90, 180, 270]
    closest = min(cardinals, key=lambda x: abs((x - angle_deg + 180) % 360 - 180))
    return math.radians(closest)

def check_obstacles_ahead_improved(owner, mouse_data):
    """
    Detect obstacles ahead with multiple rays
    Returns (obstacle_detected, distance, object, hit_point)
    """
    current_angle = owner.worldOrientation.to_euler().z
    dir_vec = Vector([math.sin(current_angle), math.cos(current_angle), 0])
    
    target = owner.worldPosition.copy() + dir_vec * OBSTACLE_DETECTION_RANGE
    target.z += 0.1
    
    hit_object, hit_point, hit_normal = owner.rayCast(
        target, None, OBSTACLE_DETECTION_RANGE
    )
    
    if hit_object and (hit_object.get('col', False) or hit_object.get('wall', False)):
        distance = (Vector(hit_point) - owner.worldPosition).length
        return (True, distance, hit_object, hit_point)
    
    for offset in [-0.2, 0, 0.2]:
        side_target = owner.worldPosition.copy() + dir_vec * OBSTACLE_DETECTION_RANGE
        side_target += Vector([-dir_vec.y, dir_vec.x, 0]) * offset
        side_target.z += 0.1
        
        side_hit, side_point, side_normal = owner.rayCast(
            side_target, None, OBSTACLE_DETECTION_RANGE
        )
        
        if side_hit and (side_hit.get('col', False) or side_hit.get('wall', False)):
            distance = (Vector(side_point) - owner.worldPosition).length
            return (True, distance, side_hit, side_point)
    
    return (False, 0, None, None)

def find_best_cardinal_direction(owner, mouse_data, avoid_last_hit=True):
    """
    Find best cardinal direction
    """
    current_pos = owner.worldPosition.copy()
    player = mouse_data.get("player")
    
    if not player:
        return math.radians(0)
    
    to_player = player.worldPosition - current_pos
    to_player.z = 0
    
    if to_player.length > 0:
        player_angle = math.atan2(to_player.y, to_player.x) - math.pi/2
    else:
        player_angle = 0
    
    cardinals = [0, 90, 180, 270]
    cardinals.sort(key=lambda x: abs(math.radians(x) - player_angle))
    
    last_hit_wall = mouse_data.get("last_hit_wall", None)
    last_hit_time = mouse_data.get("last_hit_time", 0)
    current_time = bge.logic.getRealTime()
    
    for angle_deg in cardinals:
        angle_rad = math.radians(angle_deg)
        
        if (avoid_last_hit and last_hit_wall and 
            (current_time - last_hit_time) < WALL_MEMORY_DURATION):
            dir_vec = Vector([math.sin(angle_rad), math.cos(angle_rad), 0])
            target = current_pos + dir_vec * OBSTACLE_DETECTION_RANGE
            target.z += 0.1
            
            hit_object, hit_point, hit_normal = owner.rayCast(
                target, None, OBSTACLE_DETECTION_RANGE
            )
            
            if hit_object == last_hit_wall:
                continue
        
        dir_vec = Vector([math.sin(angle_rad), math.cos(angle_rad), 0])
        target = current_pos + dir_vec * OBSTACLE_DETECTION_RANGE
        target.z += 0.1
        
        hit_object, hit_point, hit_normal = owner.rayCast(
            target, None, OBSTACLE_DETECTION_RANGE
        )
        
        if not hit_object:
            return angle_rad
        else:
            if not (hit_object.get('col', False) or hit_object.get('wall', False)):
                return angle_rad
    
    best_angle = math.radians(cardinals[0])
    max_distance = 0
    
    for angle_deg in cardinals:
        angle_rad = math.radians(angle_deg)
        dir_vec = Vector([math.sin(angle_rad), math.cos(angle_rad), 0])
        target = current_pos + dir_vec * OBSTACLE_DETECTION_RANGE
        target.z += 0.1
        
        hit_object, hit_point, hit_normal = owner.rayCast(
            target, None, OBSTACLE_DETECTION_RANGE
        )
        
        if hit_object:
            distance = (Vector(hit_point) - current_pos).length
            if distance > max_distance:
                max_distance = distance
                best_angle = angle_rad
    
    return best_angle

# =============================================================================
# OBSTACLE COLLISION HANDLING
# =============================================================================
def handle_obstacle_collision_smart(owner, mouse_data, sensor):
    """
    Smart obstacle collision handling.
    On impact activates 'dodge' state plus cardinal system to go around obstacle.
    """
    if mouse_data["obstacle_cooldown"] > 0:
        return

    closest_obstacle = None
    closest_distance = float('inf')

    for obj in sensor.hitObjectList:
        if obj.get('col', False) or obj.get('wall', False):
            distance = (obj.worldPosition - owner.worldPosition).length
            if distance < closest_distance:
                closest_distance = distance
                closest_obstacle = obj

    if not closest_obstacle:
        return

    debug_print(f"[MOUSE] COLLISION with {closest_obstacle.name}")

    mouse_data["last_hit_wall"] = closest_obstacle
    mouse_data["last_hit_time"] = bge.logic.getRealTime()
    mouse_data["hit_count"] = mouse_data.get("hit_count", 0) + 1

    if mouse_data.get("hit_count", 0) > 3:
        debug_print("[MOUSE] Many hits in a row, changing strategy")
        mouse_data["force_random_turn"] = True
        mouse_data["hit_count"] = 0

    # Calculate best cardinal direction to go around obstacle
    if mouse_data.get("force_random_turn", False):
        new_angle = math.radians(random.choice([0, 90, 180, 270]))
        mouse_data["force_random_turn"] = False
        debug_print("[MOUSE] Random turn forced")
    else:
        new_angle = find_best_cardinal_direction(owner, mouse_data, True)

    current_angle = owner.worldOrientation.to_euler().z
    rotation_needed = new_angle - current_angle
    rotation_90 = round(rotation_needed / math.radians(90)) * math.radians(90)
    owner.applyRotation([0, 0, rotation_90], True)
    debug_print(f"[MOUSE] Turn applied: {math.degrees(rotation_90):.0f} deg")

    mouse_data["last_90_direction"] = new_angle

    # Small step back to separate from obstacle
    backward_vec = owner.getAxisVect(Vector([0, -1, 0]))
    if backward_vec.length > 0:
        backward_vec.normalize()
        owner.worldPosition += backward_vec * 0.5

    # Activate dodge to maintain autonomous pathfinding
    euler_z = owner.worldOrientation.to_euler().z
    forward = Vector((math.sin(euler_z), math.cos(euler_z), 0.0))
    if forward.length > 0.001:
        forward.normalize()
    mouse_data["dodge_direction"] = forward.copy()
    mouse_data["dodge_timer"]     = 0.8
    mouse_data["dodge_cooldown"]  = 0.0

    # Activate cardinal mode as backup
    mouse_data["90_evasion_mode"]  = True
    mouse_data["90_evasion_timer"] = EVASION_90_DURATION

    mouse_data["obstacle_cooldown"] = 1.2
    mouse_data["stuck_timer"] = 0
    mouse_data["last_position"] = owner.worldPosition.copy()

    if mouse_data["state"] not in ["RETREAT", "DEATH", "STUCK_NAV"]:
        mouse_data["previous_state"] = mouse_data["state"]
        mouse_data["state"] = "STUCK_NAV"
        mouse_data["stuck_nav_timer"] = EVASION_90_DURATION * 2.0
        debug_print("[MOUSE] Switching to STUCK_NAV mode")

# =============================================================================
# STUCK DETECTION
# =============================================================================
def check_stuck_smart(owner, mouse_data):
    """
    Enhanced stuck detection.
    When prolonged immobility is detected, forces emergency dodge.
    """
    current_pos   = owner.worldPosition.copy()
    distance_moved = (current_pos - mouse_data["last_position"]).length

    if distance_moved < STUCK_DISTANCE_THRESHOLD:
        mouse_data["stuck_timer"] += 1 / 60.0

        if mouse_data["stuck_timer"] > STUCK_TIME_THRESHOLD:
            debug_print(f"[MOUSE] STUCK DETECTED (movement: {distance_moved:.4f}m)")

            obstacle_detected, distance, obstacle, hit_point = check_obstacles_ahead_improved(owner, mouse_data)

            if obstacle_detected and distance < 1.0:
                debug_print(f"[MOUSE] Obstacle confirmed at {distance:.2f}m - backing up")
                backward_vec = owner.getAxisVect(Vector([0, -1, 0]))
                if backward_vec.length > 0:
                    backward_vec.normalize()
                    owner.worldPosition += backward_vec * 0.5
                mouse_data["stuck_timer"] = STUCK_TIME_THRESHOLD - 0.5
            else:
                if random.random() < 0.7:
                    turn_angle = math.radians(90 * random.choice([-1, 1]))
                else:
                    turn_angle = math.radians(180)

                owner.applyRotation([0, 0, turn_angle], True)
                debug_print(f"[MOUSE] Stuck turn: {math.degrees(turn_angle):.0f} deg")

                backward_vec = owner.getAxisVect(Vector([0, -1, 0]))
                if backward_vec.length > 0:
                    backward_vec.normalize()
                    owner.worldPosition += backward_vec * 0.8

                # Force dodge in resulting direction
                euler_z  = owner.worldOrientation.to_euler().z
                fwd = Vector((math.sin(euler_z), math.cos(euler_z), 0.0))
                if fwd.length > 0.001:
                    fwd.normalize()
                mouse_data["dodge_direction"] = fwd.copy()
                mouse_data["dodge_timer"]     = 1.0
                mouse_data["dodge_cooldown"]  = 0.0

                mouse_data["90_evasion_mode"]  = True
                mouse_data["90_evasion_timer"] = EVASION_90_DURATION * 2.0
                mouse_data["last_90_direction"] = owner.worldOrientation.to_euler().z
                mouse_data["stuck_timer"] = 0

                if mouse_data["state"] not in ["RETREAT", "DEATH"]:
                    mouse_data["previous_state"] = mouse_data["state"]
                    mouse_data["state"] = "STUCK_NAV"
                    mouse_data["stuck_nav_timer"] = EVASION_90_DURATION * 2.5
                    debug_print("[MOUSE] Switching to STUCK_NAV due to stuck")

                return True
    else:
        mouse_data["stuck_timer"] = max(0, mouse_data["stuck_timer"] - 0.1)

    mouse_data["last_position"] = current_pos
    return False

# =============================================================================
# PLAYER COLLISION AND DAMAGE
# =============================================================================
def handle_player_collision(owner, mouse_data, sensor):
    """Handle collision with player to apply immediate damage"""
    if mouse_data.get("attack_cooldown", 0) > 0:
        return
    
    player_detected = False
    
    # Search for player property in collision list
    for obj in sensor.hitObjectList:
        if obj.get('player', False) or obj.name == "Player":
            player_detected = True
            debug_print(f"[MOUSE] PLAYER COLLISION detected: {obj.name}")
            
            # Apply immediate damage
            apply_player_damage(owner)
            
            # Start attack animation if not active
            if not mouse_data.get("attack_animation_started", False):
                rig = mouse_data.get("rig")
                if rig:
                    play_animation(rig, "Mouse.Attack")
                    mouse_data["attack_animation_started"] = True
                    mouse_data["attack_animation_timer"] = MIN_ATTACK_DURATION
                    mouse_data["attack_movement_pause"] = ATTACK_MOVEMENT_PAUSE
                
                # Play attack sound
                play_sound("rat_attack.ogg", owner, False)
            
            break

def apply_player_damage(owner):
    """Apply damage to player and set cooldown"""
    debug_print(f"[MOUSE] Applying damage to player")
    
    # Apply damage to player
    game = game_access.get_game()
    if game:
        old_health = game.player.health
        game.player.take_damage(MOUSE_DAMAGE_TO_PLAYER)
        debug_print(f"[MOUSE] Damage applied: {old_health} -> {game.player.health}")
    else:
        # Fallback for compatibility
        scene = bge.logic.getCurrentScene()
        game_controller = scene.objects.get("Game.Controller")
        if game_controller:
            old_health = game_controller.get('health', 100)
            game_controller['health'] = max(0, old_health - MOUSE_DAMAGE_TO_PLAYER)
    
    # Change to RETREAT state after attack
    if "mouse_data" in owner:
        mouse_data = owner["mouse_data"]
        mouse_data["state"] = "RETREAT"
        mouse_data["retreat_timer"] = mouse_data.get("retreat_duration", 3.0)
        mouse_data["attack_cooldown"] = 1.0
        mouse_data["attack_animation_started"] = False
        mouse_data["attack_movement_pause"] = 0

# =============================================================================
# SUSPENSION SYSTEM
# =============================================================================
def handle_suspend_messages(cont, owner):
    """Handle suspension messages"""
    try:
        suspend_sensor = cont.sensors.get(SUSPEND_MESSAGE_SENSOR_NAME)
        if not suspend_sensor or not suspend_sensor.positive:
            return

        if getattr(suspend_sensor, 'subject', '') != SUSPEND_MESSAGE_SUBJECT:
            return

        for body in suspend_sensor.bodies:
            process_suspend_message(owner, body)

    except Exception as e:
        debug_print(f"[MOUSE] Error handling suspension messages: {e}")

def process_suspend_message(owner, body):
    """Process a specific suspension message"""
    try:
        parts = [p.strip() for p in body.split("|")]
        if len(parts) < 2:
            return

        action = parts[1].lower()

        if action == "suspend":
            suspend_enemy(owner)
        elif action == "resume":
            resume_enemy(owner)

    except Exception as e:
        debug_print(f"[MOUSE] Error processing message '{body}': {e}")

def suspend_enemy(owner):
    """Suspend this specific mouse"""
    if owner.get('suspended', False):
        return

    owner['suspended'] = True
    owner['suspended_time'] = bge.logic.getRealTime()
    owner.suspendDynamics()

    if "mouse_data" in owner:
        mouse_data = owner["mouse_data"]
        if mouse_data.get("current_sound"):
            stop_sound(mouse_data["current_sound"])
            mouse_data["current_sound"] = None
        stop_sound_by_name("rat_squeak.ogg", owner)

        if mouse_data.get("rig"):
            try:
                mouse_data["rig"].stopAction(0)
            except:
                pass

    debug_print(f"[MOUSE] Mouse {owner.name} SUSPENDED")

def resume_enemy(owner):
    """Resume this specific mouse"""
    if not owner.get('suspended', False):
        return

    owner['suspended'] = False
    owner.restoreDynamics()

    if "mouse_data" in owner:
        mouse_data = owner["mouse_data"]
        state = mouse_data.get("state", "IDLE")

        if state in ["APPROACH", "RETREAT", "IDLE", "STUCK_NAV"]:
            mouse_data["current_sound"] = play_sound(
                "rat_squeak.ogg", owner, True)

        if mouse_data.get("rig"):
            rig = mouse_data["rig"]
            if state == "DEATH":
                play_animation(rig, "Mouse.Death")
            elif state == "RETREAT":
                play_animation(rig, "Mouse.Attack")
            elif state == "IDLE":
                play_animation(rig, "Mouse.Idle")
            else:
                play_animation(rig, "Mouse.Walk",
                               mouse_data["walk_animation_speed"])

    debug_print(f"[MOUSE] Mouse {owner.name} RESUMED")

# =============================================================================
# INITIALIZATION AND SETUP
# =============================================================================
def main(cont):
    """Main mouse script"""
    owner = cont.owner

    handle_suspend_messages(cont, owner)

    if owner.get('suspended', False):
        return

    cleanup_sounds()
    update_sound_3d_listener()

    if "object_added" not in owner:
        handle_new_object(owner, cont)
        return

    if not owner.get('active_mouse', False):
        return

    if not owner.visible:
        owner['active_mouse'] = False
        return

    if "initialized" not in owner:
        if not initialize_mouse(owner, cont):
            return

    mouse_data = owner["mouse_data"]
    
    # Process player collision sensor
    collision_player_sensor = cont.sensors.get(COLLISION_PLAYER_SENSOR_NAME)
    if collision_player_sensor and collision_player_sensor.positive:
        handle_player_collision(owner, mouse_data, collision_player_sensor)
    
    # Update timers
    if "90_evasion_timer" in mouse_data and mouse_data["90_evasion_timer"] > 0:
        mouse_data["90_evasion_timer"] -= 1/60.0
        if mouse_data["90_evasion_timer"] <= 0:
            mouse_data["90_evasion_mode"] = False
    
    if "stuck_nav_timer" in mouse_data:
        mouse_data["stuck_nav_timer"] -= 1/60.0
    
    # Update attack pause timer
    if "attack_movement_pause" in mouse_data and mouse_data["attack_movement_pause"] > 0:
        mouse_data["attack_movement_pause"] -= 1/60.0

    # Process collision sensors
    collision_shot_sensor = cont.sensors.get(COLLISION_SHOT_SENSOR_NAME)
    collision_obstacle_sensor = cont.sensors.get(COLLISION_OBSTACLE_SENSOR_NAME)

    if collision_shot_sensor and collision_shot_sensor.positive:
        handle_shot_collision(owner, mouse_data, collision_shot_sensor)

    if collision_obstacle_sensor and collision_obstacle_sensor.positive:
        if GRID_NAVIGATION:
            handle_obstacle_collision_smart(owner, mouse_data, collision_obstacle_sensor)

    if owner['health_mouse'] <= 0 and mouse_data["state"] != "DEATH":
        handle_death(owner, cont)
        return

    if mouse_data["state"] == "DEATH":
        handle_death_animation(owner, mouse_data)
        return

    update_cooldowns(mouse_data)
    process_state_machine(owner, mouse_data, cont=cont)

def initialize_mouse(owner, cont):
    """Complete mouse initialization"""
    debug_print(f"[MOUSE] Initializing {owner.name}")

    player = find_player_robust()
    if not player:
        debug_print("[MOUSE] Player not found")
        return False

    rig = find_mouse_rig(owner)

    if 'health_mouse' not in owner:
        owner['health_mouse'] = 3

    mouse_data = {
        "state": "SPAWN",
        "speed": 0.05,
        "walk_animation_speed": 6.0,
        "retreat_timer": 0,
        "idle_timer": 0,
        "collision_cooldown": 0,
        "obstacle_cooldown": 0,
        "retreat_duration": random.uniform(3.0, 5.0),
        "idle_duration": random.uniform(1.0, 3.0),
        "player": player,
        "rig": rig,
        "frame_count": 0,
        "last_position": owner.worldPosition.copy(),
        "stuck_timer": 0,
        "turn_direction": random.choice([-1, 1]),
        "death_animation_timer": 0,
        "death_animation_duration": 2.0,
        "attack_animation_started": False,
        "attack_animation_timer": 0,
        "attack_cooldown": 0,
        "attack_movement_pause": 0,
        "current_sound": None,
        "last_state": None,
        "90_evasion_mode": False,
        "90_evasion_timer": 0,
        "last_90_direction": 0,
        "previous_state": None,
        "stuck_nav_timer": 0,
        "last_hit_wall": None,
        "last_hit_time": 0,
        "hit_count": 0,
        "force_random_turn": False,
        "is_moving_backward": False,
        "last_movement_direction": Vector([0, 1, 0]),
        "sprite_shown": False,
        "dodge_timer": 0.0,
        "dodge_direction": None,
        "dodge_cooldown": 0.0,
    }
    owner["mouse_data"] = mouse_data
    owner["initialized"] = True

    play_animation(rig, "Mouse.Walk", mouse_data["walk_animation_speed"])

    distance = (owner.worldPosition - player.worldPosition).length
    debug_print(
        f"[MOUSE] Initialized - Health: {owner['health_mouse']} - Distance: {distance:.2f}")
    return True

def find_mouse_rig(owner):
    """Find mouse animation rig"""
    for child in owner.children:
        if "Rig" in child.name:
            return child
    return None

def play_animation(rig, animation_name, speed=1.0):
    """Play animation on rig with configurable speed"""
    if not rig:
        return False

    try:
        if animation_name == "Mouse.Walk":
            rig.playAction(animation_name, 1, 26,
                           play_mode=bge.logic.KX_ACTION_MODE_LOOP, speed=speed)
        elif animation_name == "Mouse.Idle":
            rig.playAction(animation_name, 1, 30,
                           play_mode=bge.logic.KX_ACTION_MODE_LOOP, speed=speed)
        elif animation_name == "Mouse.Attack":
            rig.playAction(animation_name, 1, 15,
                           play_mode=bge.logic.KX_ACTION_MODE_PLAY, speed=speed)
        elif animation_name == "Mouse.Death":
            rig.playAction(animation_name, 1, 15,
                           play_mode=bge.logic.KX_ACTION_MODE_PLAY, speed=speed)

        return True
    except Exception as e:
        return False

# =============================================================================
# COLLISION HANDLERS
# =============================================================================
def update_cooldowns(mouse_data):
    """Update timers and cooldowns"""
    if mouse_data["collision_cooldown"] > 0:
        mouse_data["collision_cooldown"] -= 1/60.0
    if mouse_data["obstacle_cooldown"] > 0:
        mouse_data["obstacle_cooldown"] -= 1/60.0
    if mouse_data["attack_cooldown"] > 0:
        mouse_data["attack_cooldown"] -= 1/60.0

def handle_shot_collision(owner, mouse_data, sensor):
    """Handle collision with shots"""
    if mouse_data["collision_cooldown"] > 0:
        return

    for obj in sensor.hitObjectList:
        if obj.get('shot', False):
            old_health = owner['health_mouse']
            owner['health_mouse'] -= 1
            mouse_data["collision_cooldown"] = 0.2

            debug_print(
                f"[MOUSE] Shot hit - Health: {old_health} -> {owner['health_mouse']}")

            if owner['health_mouse'] > 0:
                apply_hit_effect(owner, mouse_data)

            break

def apply_hit_effect(owner, mouse_data):
    """Apply visual/temporal effect when taking damage"""
    player = mouse_data["player"]
    if player:
        direction = owner.worldPosition - player.worldPosition
        direction.z = 0
        if direction.length > 0:
            direction.normalize()
            owner.worldPosition += direction * 0.3

def handle_player_contact(owner, mouse_data):
    """Handle real contact with player (fallback for compatibility)"""
    if mouse_data["attack_cooldown"] > 0:
        return

    debug_print(f"[MOUSE] CONTACT with player")

    game = game_access.get_game()
    if game:
        old_health = game.player.health
        game.player.take_damage(MOUSE_DAMAGE_TO_PLAYER)
        debug_print(
            f"[MOUSE] Contact damage: {old_health} -> {game.player.health}")
    else:
        scene = bge.logic.getCurrentScene()
        game_controller = scene.objects.get("Game.Controller")
        if game_controller:
            old_health = game_controller.get('health', 100)
            game_controller['health'] = max(
                0, old_health - MOUSE_DAMAGE_TO_PLAYER)

    mouse_data["state"] = "RETREAT"
    mouse_data["retreat_timer"] = mouse_data["retreat_duration"]
    mouse_data["attack_cooldown"] = 1.0
    mouse_data["attack_animation_started"] = False
    mouse_data["attack_movement_pause"] = 0

    rig = mouse_data.get("rig")
    if rig and rig.getActionFrame() is None:
        play_animation(rig, "Mouse.Walk", mouse_data["walk_animation_speed"])

    play_sound("rat_squeak.ogg", owner, False)

# =============================================================================
# DEATH HANDLING
# =============================================================================
def handle_death(owner, cont):
    """Handle death start"""
    debug_print("[MOUSE] Starting death")

    mouse_data = owner["mouse_data"]
    mouse_data["state"] = "DEATH"
    mouse_data["death_animation_timer"] = mouse_data["death_animation_duration"]

    owner.suspendDynamics()

    if mouse_data["current_sound"]:
        stop_sound(mouse_data["current_sound"])
        mouse_data["current_sound"] = None

    stop_sound_by_name("rat_squeak.ogg", owner)

    # SHOW DEATH SPRITE
    show_death_sprite(owner)
    mouse_data["sprite_shown"] = True
    
    if mouse_data.get("rig"):
        play_animation(mouse_data["rig"], "Mouse.Death")
    play_sound("rat_death.ogg", owner, False)

def handle_death_animation(owner, mouse_data):
    """Handle death animation"""
    mouse_data["death_animation_timer"] -= 1/60.0

    animation_finished = False
    rig = mouse_data.get("rig")

    if rig:
        current_frame = rig.getActionFrame()
        if current_frame is None or current_frame >= 15:
            animation_finished = True
    else:
        if mouse_data["death_animation_timer"] <= 0:
            animation_finished = True

    if animation_finished:
        debug_print("[MOUSE] Death animation completed")
        
        # HIDE SPRITE IF SHOWN
        if mouse_data.get("sprite_shown", False):
            hide_death_sprite()

        try:
            import game_access
            game = game_access.get_game()
            if game and hasattr(game.state, 'bugs_total'):
                old_value = game.state.bugs_total
                game.state.bugs_total += 2
                debug_print(
                    f"[MOUSE] Bug counter: {old_value} -> {game.state.bugs_total} (+2)")
        except Exception as e:
            debug_print(f"[MOUSE] Error updating bug counter: {e}")

        scene = bge.logic.getCurrentScene()
        pest_manager = scene.objects.get("Empty.Pest.Manager")
        if pest_manager and "notify_mouse_death" in pest_manager:
            pest_manager["notify_mouse_death"](pest_manager, owner)
        else:
            owner.endObject()

# =============================================================================
# STATE MACHINE
# =============================================================================
def process_state_machine(owner, mouse_data, cont=None):
    """State machine"""
    old_state = mouse_data["last_state"]
    new_state = mouse_data["state"]

    if old_state != new_state:
        if new_state != "APPROACH":
            mouse_data["attack_animation_started"] = False
            mouse_data["attack_movement_pause"] = 0

        handle_state_change(owner, mouse_data, old_state, new_state)
        mouse_data["last_state"] = new_state

    if new_state == "SPAWN":
        handle_spawn_state(owner, mouse_data)
    elif new_state == "APPROACH":
        handle_approach_state_smart(owner, mouse_data, cont=cont)
    elif new_state == "RETREAT":
        handle_retreat_state_smart(owner, mouse_data)
    elif new_state == "IDLE":
        handle_idle_state(owner, mouse_data)
    elif new_state == "STUCK_NAV":
        handle_stuck_nav_state(owner, mouse_data)

def handle_state_change(owner, mouse_data, old_state, new_state):
    """Handle state changes"""
    debug_print(f"[MOUSE] State: {old_state} -> {new_state}")

    if mouse_data["current_sound"]:
        stop_sound(mouse_data["current_sound"])
        mouse_data["current_sound"] = None

    stop_sound_by_name("rat_squeak.ogg", owner)

    if new_state in ["APPROACH", "RETREAT", "STUCK_NAV"]:
        mouse_data["current_sound"] = play_sound("rat_squeak.ogg", owner, True)
        if new_state in ["RETREAT", "STUCK_NAV"]:
            play_animation(mouse_data["rig"], "Mouse.Walk",
                           mouse_data["walk_animation_speed"])
    elif new_state == "IDLE":
        mouse_data["current_sound"] = play_sound("rat_squeak.ogg", owner, True)

def handle_spawn_state(owner, mouse_data):
    """SPAWN state -> APPROACH"""
    mouse_data["state"] = "APPROACH"
    play_animation(mouse_data["rig"], "Mouse.Walk",
                   mouse_data["walk_animation_speed"])

# =============================================================================
# STATE HANDLERS
# =============================================================================
def handle_approach_state_smart(owner, mouse_data, cont=None):
    """Enhanced APPROACH state with animation/movement sync"""
    player = mouse_data["player"]
    if not player:
        return

    mouse_data["frame_count"] += 1

    # Proactive obstacle detection
    if mouse_data["frame_count"] % 40 == 0 and not mouse_data.get("90_evasion_mode", False):
        obstacle_detected, distance, obstacle, hit_point = check_obstacles_ahead_improved(owner, mouse_data)
        
        if obstacle_detected and distance < 1.5:
            debug_print(f"[MOUSE] Obstacle nearby at {distance:.2f}m")
            
            new_angle = find_best_cardinal_direction(owner, mouse_data, False)
            current_angle = owner.worldOrientation.to_euler().z
            
            if abs(new_angle - current_angle) > math.radians(30):
                rotation_90 = round((new_angle - current_angle) / math.radians(90)) * math.radians(90)
                owner.applyRotation([0, 0, rotation_90], True)
                debug_print(f"[MOUSE] Preventive dodge: {math.degrees(rotation_90):.0f} deg")
                
                mouse_data["90_evasion_mode"] = True
                mouse_data["90_evasion_timer"] = 1.0

    # Distance to player
    distance_to_player = (owner.worldPosition - player.worldPosition).length

    # Attack logic - WITH MOVEMENT PAUSE
    if distance_to_player <= ATTACK_ANIMATION_DISTANCE and not mouse_data["attack_animation_started"]:
        debug_print(f"[MOUSE] Attack (distance: {distance_to_player:.2f})")
        play_animation(mouse_data["rig"], "Mouse.Attack")
        mouse_data["attack_animation_started"] = True
        mouse_data["attack_animation_timer"] = MIN_ATTACK_DURATION
        mouse_data["attack_movement_pause"] = ATTACK_MOVEMENT_PAUSE
        play_sound("rat_attack.ogg", owner, False)

    if mouse_data["attack_animation_started"]:
        mouse_data["attack_animation_timer"] -= 1/60.0
        if mouse_data["attack_animation_timer"] <= 0:
            mouse_data["attack_animation_started"] = False

    # Player contact (fallback - primary detection is via collision)
    if (distance_to_player <= CONTACT_DISTANCE and 
        mouse_data["attack_cooldown"] <= 0 and 
        not mouse_data.get("attack_animation_started", False)):
        handle_player_contact(owner, mouse_data)
        return

    # MOVEMENT - ONLY IF NOT IN ATTACK PAUSE
    if mouse_data.get("attack_movement_pause", 0) <= 0:
        if mouse_data.get("90_evasion_mode", False):
            move_in_cardinal_direction_synced(owner, mouse_data)
        else:
            move_toward_player_synced(owner, mouse_data, player, cont=cont)
    else:
        # During attack pause, only update animation if needed
        rig = mouse_data.get("rig")
        if rig and rig.getActionName(0) != "Mouse.Attack":
            play_animation(rig, "Mouse.Walk", mouse_data["walk_animation_speed"])

    # Check stuck
    if check_stuck_smart(owner, mouse_data):
        debug_print("[MOUSE] Stuck detected")

    # Maintain appropriate animation
    rig = mouse_data.get("rig")
    if rig and not mouse_data["attack_animation_started"]:
        current_action = rig.getActionName(0)
        if current_action != "Mouse.Walk" and current_action != "Mouse.Attack":
            play_animation(rig, "Mouse.Walk", mouse_data["walk_animation_speed"])

def get_ray_sensor_hit(cont):
    """
    Read frontal Ray sensor ('Ray'; property 'col'; +Y axis; range 0.5).
    Returns True if obstacle ahead, False otherwise.
    """
    ray = cont.sensors.get("Ray")
    if ray is None:
        return False
    return ray.positive

def move_toward_player_synced(owner, mouse_data, player, cont=None):
    """
    Smart movement toward player WITH SYNCHRONIZATION and proactive evasion.

    Three-layer system:
      1. Frontal Ray sensor -> detects obstacle before impact and diverts.
      2. 'dodge' state -> maintains lateral evasion (dodge_timer seconds)
                         mixing player direction with lateral to go around.
      3. check_stuck_smart() -> fallback if Ray and collision aren't enough.
    """
    direction = player.worldPosition - owner.worldPosition
    direction.z = 0

    if direction.length < 0.1:
        return

    direction.normalize()

    # Calculate angle toward player
    player_angle = math.atan2(direction.y, direction.x) - math.pi / 2

    # 1. READ RAY SENSOR
    ray_blocked = False
    if cont is not None:
        ray_blocked = get_ray_sensor_hit(cont)

    # 2. DODGE STATE MANAGEMENT
    dodge_timer   = mouse_data.get("dodge_timer", 0.0)
    dodge_dir_raw = mouse_data.get("dodge_direction", None)

    if ray_blocked and dodge_timer <= 0.0 and mouse_data.get("dodge_cooldown", 0.0) <= 0.0:
        # Start new dodge maneuver
        side = mouse_data.get("turn_direction", 1)
        perp = Vector((-direction.y * side, direction.x * side, 0.0))
        perp.normalize()
        mouse_data["dodge_direction"] = perp.copy()
        mouse_data["dodge_timer"]     = 0.7
        mouse_data["dodge_cooldown"]  = 0.4
        mouse_data["turn_direction"] *= -1
        # Cancel 90_evasion mode so it doesn't interfere
        mouse_data["90_evasion_mode"]  = False
        mouse_data["90_evasion_timer"] = 0.0
        dodge_timer   = mouse_data["dodge_timer"]
        dodge_dir_raw = perp
        debug_print("[MOUSE] Ray blocked -> starting dodge")

    # Decrement dodge timers
    if dodge_timer > 0.0:
        mouse_data["dodge_timer"] = max(0.0, dodge_timer - 1 / 60.0)
    dodge_cooldown = mouse_data.get("dodge_cooldown", 0.0)
    if dodge_cooldown > 0.0:
        mouse_data["dodge_cooldown"] = max(0.0, dodge_cooldown - 1 / 60.0)

    # 3. CALCULATE FINAL MOVEMENT DIRECTION
    if mouse_data.get("dodge_timer", 0.0) > 0.0 and dodge_dir_raw is not None:
        # Smooth mix: 40% player + 60% lateral
        dodge_dir = Vector(dodge_dir_raw)
        move_vec  = direction * 0.4 + dodge_dir * 0.6
        move_vec.z = 0
        if move_vec.length > 0.001:
            move_vec.normalize()
        target_angle = math.atan2(move_vec.y, move_vec.x) - math.pi / 2

    elif mouse_data.get("90_evasion_mode", False) and mouse_data.get("90_evasion_timer", 0) > 0:
        # Previous cardinal system (middle layer)
        cardinal_angle = get_cardinal_direction(player_angle)
        move_vec = Vector([math.sin(cardinal_angle), math.cos(cardinal_angle), 0])
        target_angle = cardinal_angle
    else:
        move_vec     = direction
        target_angle = player_angle

    if move_vec.length > 0:
        move_vec.normalize()

        # Check backward movement
        forward_vec = owner.getAxisVect(Vector([0, 1, 0]))
        dot_product = move_vec.dot(forward_vec)
        mouse_data["is_moving_backward"] = dot_product < -0.5

        # Apply movement
        owner.worldPosition += move_vec * mouse_data["speed"]

    # Sync rotation - ONLY IF NOT ATTACKING
    if not mouse_data["attack_animation_started"]:
        owner.worldOrientation = [0, 0, target_angle]

    # Save last direction
    mouse_data["last_movement_direction"] = move_vec.copy()

def move_in_cardinal_direction_synced(owner, mouse_data):
    """Move mouse in cardinal direction WITH SYNCHRONIZATION"""
    current_angle = owner.worldOrientation.to_euler().z
    cardinal_angle = get_cardinal_direction(current_angle)
    
    # Calculate movement direction
    move_vec = Vector([math.sin(cardinal_angle), math.cos(cardinal_angle), 0])
    if move_vec.length > 0:
        move_vec.normalize()
    
    # Check if moving backward
    forward_vec = owner.getAxisVect(Vector([0, 1, 0]))
    dot_product = move_vec.dot(forward_vec)
    
    if dot_product < -0.5:  # Significant backward movement
        if not mouse_data.get("is_moving_backward", False):
            debug_print("[MOUSE] Backward movement detected")
            mouse_data["is_moving_backward"] = True
    else:
        mouse_data["is_moving_backward"] = False
    
    # Apply movement
    owner.worldPosition += move_vec * mouse_data["speed"]
    
    # Sync rotation with movement direction
    owner.worldOrientation = [0, 0, cardinal_angle]
    
    # Save last movement direction
    mouse_data["last_movement_direction"] = move_vec.copy()

def handle_retreat_state_smart(owner, mouse_data):
    """Enhanced RETREAT state with synchronization"""
    mouse_data["retreat_timer"] -= 1/60.0

    if mouse_data["retreat_timer"] <= 0:
        mouse_data["state"] = "IDLE"
        mouse_data["idle_timer"] = mouse_data["idle_duration"]
        mouse_data["attack_animation_started"] = False
        mouse_data["attack_movement_pause"] = 0
        play_animation(mouse_data["rig"], "Mouse.Idle")
        debug_print("[MOUSE] Retreat ended, returning to IDLE")
    else:
        player = mouse_data["player"]
        if player:
            # Synced retreat movement
            direction = owner.worldPosition - player.worldPosition
            direction.z = 0
            
            if direction.length > 0.1:
                direction.normalize()
                
                # Convert to cardinal direction for ordered retreat
                retreat_angle = math.atan2(direction.y, direction.x) - math.pi/2
                cardinal_angle = get_cardinal_direction(retreat_angle)
                
                move_vec = Vector([math.sin(cardinal_angle), math.cos(cardinal_angle), 0])
                
                # Check backward movement
                forward_vec = owner.getAxisVect(Vector([0, 1, 0]))
                dot_product = move_vec.dot(forward_vec)
                
                if dot_product < -0.3:  # Lower threshold for retreat
                    # During retreat, moving "backward" is more likely
                    pass
                
                # Apply movement
                owner.worldPosition += move_vec * mouse_data["speed"] * 1.2
                
                # Sync rotation
                owner.worldOrientation = [0, 0, cardinal_angle]
                
                # Save direction
                mouse_data["last_movement_direction"] = move_vec.copy()

        # Keep walk animation for retreat
        rig = mouse_data.get("rig")
        if rig and rig.getActionFrame() is None:
            play_animation(rig, "Mouse.Walk", mouse_data["walk_animation_speed"] * 1.2)

def handle_idle_state(owner, mouse_data):
    """IDLE state"""
    mouse_data["idle_timer"] -= 1/60.0

    if mouse_data["idle_timer"] <= 0:
        mouse_data["state"] = "APPROACH"
        play_animation(mouse_data["rig"], "Mouse.Walk",
                       mouse_data["walk_animation_speed"])

def handle_stuck_nav_state(owner, mouse_data):
    """STUCK_NAV state with synchronization"""
    if "stuck_nav_timer" in mouse_data:
        mouse_data["stuck_nav_timer"] -= 1/60.0
    
    if mouse_data.get("stuck_nav_timer", 0) <= 0:
        previous_state = mouse_data.get("previous_state", "APPROACH")
        mouse_data["state"] = previous_state
        mouse_data["90_evasion_mode"] = False
        mouse_data["hit_count"] = 0
        mouse_data["attack_movement_pause"] = 0
        debug_print(f"[MOUSE] STUCK_NAV ended, returning to {previous_state}")
    else:
        # During STUCK_NAV: synced movement
        current_angle = owner.worldOrientation.to_euler().z
        cardinal_angle = get_cardinal_direction(current_angle)
        
        # Check if path is still clear
        dir_vec = Vector([math.sin(cardinal_angle), math.cos(cardinal_angle), 0])
        target = owner.worldPosition.copy() + dir_vec * OBSTACLE_DETECTION_RANGE
        target.z += 0.1
        
        hit_object, hit_point, hit_normal = owner.rayCast(
            target, None, OBSTACLE_DETECTION_RANGE
        )
        
        if hit_object and (hit_object.get('col', False) or hit_object.get('wall', False)):
            debug_print("[MOUSE] Path blocked in STUCK_NAV, changing direction")
            new_angle = find_best_cardinal_direction(owner, mouse_data, True)
            rotation_90 = round((new_angle - cardinal_angle) / math.radians(90)) * math.radians(90)
            owner.applyRotation([0, 0, rotation_90], True)
            mouse_data["stuck_nav_timer"] += 1.0
        else:
            # Path clear, advance synced
            move_vec = dir_vec
            if move_vec.length > 0:
                move_vec.normalize()
                
                # Check backward movement
                forward_vec = owner.getAxisVect(Vector([0, 1, 0]))
                dot_product = move_vec.dot(forward_vec)
                
                if dot_product < -0.5:
                    mouse_data["is_moving_backward"] = True
                else:
                    mouse_data["is_moving_backward"] = False
                
                owner.worldPosition += move_vec * mouse_data["speed"] * 0.8
            
            # Sync rotation
            owner.worldOrientation = [0, 0, cardinal_angle]
            
            # Save direction
            mouse_data["last_movement_direction"] = move_vec.copy()
        
        # Keep appropriate animation
        rig = mouse_data.get("rig")
        if rig and rig.getActionFrame() is None:
            play_animation(rig, "Mouse.Walk", mouse_data["walk_animation_speed"] * 0.8)

# =============================================================================
# AUXILIARY FUNCTIONS FOR COMPATIBILITY
# =============================================================================
def handle_new_object(owner, cont):
    """Handle newly added object via Add Object"""
    debug_print(f"[MOUSE] New object added: {owner.name}")

    owner["object_added"] = True

    spawn_point = owner.get("last_spawn_point")
    if spawn_point:
        owner.worldPosition = spawn_point.worldPosition.copy()
        owner.worldOrientation = spawn_point.worldOrientation.copy()

    owner['active_mouse'] = True
    owner['health_mouse'] = 3

    if 'last_spawn_point' in owner:
        del owner['last_spawn_point']
    if 'last_spawn_id' in owner:
        del owner['last_spawn_id']

    owner.setVisible(True)
    owner.restoreDynamics()

    scene = bge.logic.getCurrentScene()
    pest_manager = scene.objects.get("Empty.Pest.Manager")
    if pest_manager and "notify_mouse_activation" in pest_manager:
        pest_manager["notify_mouse_activation"](pest_manager, owner)

    initialize_mouse(owner, cont)