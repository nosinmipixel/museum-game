"""
npc_cockroach.py

Cockroach NPC with collision detection for immediate damage

This script controls cockroach enemy behavior including movement, attack,
damage handling, death effects, sound management, and suspension system.

Main Features:
    1. State machine with SPAWN, APPROACH, RETREAT, IDLE, DEATH states
    2. 3D positional audio with player-based listener
    3. Obstacle avoidance with ray sensor and dodge mechanics
    4. Attack animation with proximity detection
    5. Player damage application with cooldown
    6. Death sprite effect with animation
    7. Suspension system for UI/menu blocking
    8. Shot collision detection for player attacks

Setup:
    Connect in Logic Bricks as Python controller/module 'npc_cockroach.main'
    Object requires sensors:
        - CollisionPlayer (for player damage)
        - CollisionShot (for damage from attacks)
        - CollisionObstacle (for wall collision)
        - Ray (for obstacle detection)
        - Message.Suspend (for suspension messages)

Configurable Variables:
    DEBUG_MODE (bool): Enable debug messages (default: False)
    SOUNDS_ENABLED (bool): Enable sound effects (default: True)
    SOUND_VOLUME (float): Master volume (default: 1.0)
    SOUND_3D_ENABLED (bool): Enable 3D positional audio (default: True)
    DAMAGE_TO_PLAYER (int): Damage dealt to player (default: 20)
    ATTACK_ANIMATION_DISTANCE (float): Distance to start attack (default: 2.5)
    CONTACT_DISTANCE (float): Distance for collision fallback (default: 0.8)

Notes:
    - Requires game_access module for game state and player health
    - Uses aud module for 3D audio positioning
    - Listener follows player position, not camera
    - Death sprite appears at cockroach position on death
    - Suspension system stops all behavior when UI is open

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
__description__ = "Cockroach NPC with collision detection, 3D audio, and state machine"

# =============================================================================
# IMPORTS AND CONFIGURATION
# =============================================================================
import bge
import math
import random
import aud
from mathutils import Vector
import game_access

# SUSPENSION SYSTEM CONFIGURATION
SUSPEND_MESSAGE_SENSOR_NAME = "Message.Suspend"
SUSPEND_MESSAGE_SUBJECT = "suspend_logic"

# GLOBAL CONFIGURATION
DEBUG_MODE = False
SOUNDS_ENABLED = True
SOUND_VOLUME = 1.0
SOUND_3D_ENABLED = True
SOUND_MIN_DISTANCE = 2.0
SOUND_MAX_DISTANCE = 15.0
DAMAGE_TO_PLAYER = 20

# ATTACK CONFIGURATIONS
ATTACK_ANIMATION_DISTANCE = 2.5
CONTACT_DISTANCE = 0.8
MIN_ATTACK_DURATION = 0.3

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
            debug_print("[COCKROACH] 3D audio device created")
        except Exception as e:
            debug_print(f"[COCKROACH] Error creating device: {e}")
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
            
        # Only check 3D sounds (have owner in key)
        if '_' in sound_key:
            try:
                # Get sound position (cockroach)
                sound_pos_tuple = handle.location
                sound_position = Vector(sound_pos_tuple)
                
                # Listener_position is already the player position
                listener_pos = Vector(listener_position)
                
                distance = (sound_position - listener_pos).length
                
                # If beyond maximum distance + margin, stop it
                if distance > SOUND_MAX_DISTANCE + 5.0:
                    sounds_to_stop.append(sound_key)
                    if DEBUG_MODE:
                        debug_print(f"[COCKROACH] Sound too far from player ({distance:.1f}m) - Stopping")
                    
            except Exception as e:
                if DEBUG_MODE:
                    debug_print(f"[COCKROACH] Error checking distance: {e}")
    
    # Stop distant sounds
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
        # Use player instead of camera
        player = find_player_robust()
        
        if not player:
            return
            
        device = get_sound_device()
        if not device:
            return
            
        # Listener at player, not camera
        listener_position = Vector(player.worldPosition)
        
        # Update listener with player position
        device.listener_location = listener_position
        device.listener_orientation = player.worldOrientation.to_quaternion()
        
        # Check distances and stop distant sounds
        check_sound_distances(listener_position)
        
        # Reduced debug
        if DEBUG_MODE and random.random() < 0.01:
            debug_print(f"[COCKROACH] Listener (PLAYER) updated: {listener_position}")
                        
    except Exception as e:
        debug_print(f"[COCKROACH] Error updating listener: {e}")

def play_sound_3d(sound_file, owner, loop=False):
    """Play 3D positional sound relative to player"""
    if not SOUNDS_ENABLED or not SOUND_3D_ENABLED:
        return None
        
    try:
        # Calculate distance to player, not camera
        player = find_player_robust()
        
        # Check distance before playing
        if player:
            distance = (Vector(owner.worldPosition) - Vector(player.worldPosition)).length
            if distance > SOUND_MAX_DISTANCE + 10.0:
                if DEBUG_MODE:
                    debug_print(f"[COCKROACH] Too far from player ({distance:.1f}m)")
                return None
        
        sound_key = f"{sound_file}_{owner.name}"
        
        # Avoid duplicate sounds for same owner
        if sound_key in sound_handles and sound_handles[sound_key]:
            if sound_handles[sound_key].status == aud.STATUS_PLAYING:
                # Update position of existing sound
                try:
                    sound_handles[sound_key].location = tuple(owner.worldPosition)
                except:
                    pass
                return sound_handles[sound_key]
            
        device = get_sound_device()
        if not device:
            return None
            
        sound_path = bge.logic.expandPath("//Assets/Sounds/") + sound_file
        sound = aud.Sound(sound_path)
        handle = device.play(sound)
        
        # 3D CONFIGURATION
        handle.relative = False
        handle.volume = SOUND_VOLUME
        handle.loop_count = -1 if loop else 0
        
        # Configure 3D distance properties
        handle.distance_maximum = SOUND_MAX_DISTANCE
        handle.distance_reference = SOUND_MIN_DISTANCE
        
        # Position sound at owner location
        handle.location = tuple(owner.worldPosition)
        
        sound_handles[sound_key] = handle
        
        # Debug with distance to player
        if player:
            distance = (Vector(owner.worldPosition) - Vector(player.worldPosition)).length
            if DEBUG_MODE:
                debug_print(f"[COCKROACH] 3D sound: {sound_file} at {distance:.1f}m from player")
        else:
            if DEBUG_MODE:
                debug_print(f"[COCKROACH] 3D sound: {sound_file}")
            
        return handle
        
    except Exception as e:
        debug_print(f"[COCKROACH] Error in 3D sound {sound_file}: {e}")
        return None

def play_sound_2d(sound_file, loop=False):
    """Maintain compatibility with 2D sound"""
    if not SOUNDS_ENABLED:
        return None
        
    try:
        # Avoid duplicate sounds
        if sound_file in sound_handles and sound_handles[sound_file]:
            if sound_handles[sound_file].status == aud.STATUS_PLAYING:
                return sound_handles[sound_file]
            
        device = get_sound_device()
        if not device:
            return None
            
        sound_path = bge.logic.expandPath("//Assets/Sounds/") + sound_file
        sound = aud.Sound(sound_path)
        handle = device.play(sound)
        
        # 2D configuration
        handle.relative = True
        handle.volume = SOUND_VOLUME
        handle.loop_count = -1 if loop else 0
        
        sound_handles[sound_file] = handle
        debug_print(f"[COCKROACH] 2D sound: {sound_file}")
        return handle
        
    except Exception as e:
        debug_print(f"[COCKROACH] Error in 2D sound {sound_file}: {e}")
        return None

def play_sound(sound_file, owner=None, loop=False):
    """Main enhanced sound function"""
    # If owner exists and 3D is enabled, use 3D sound
    if owner and SOUND_3D_ENABLED:
        return play_sound_3d(sound_file, owner, loop)
    else:
        # Fallback to 2D sound
        return play_sound_2d(sound_file, loop)

def stop_sound(handle):
    """Stop a sound"""
    if handle:
        try:
            handle.stop()
        except:
            pass

def stop_sound_by_name(sound_file, owner=None):
    """Now accepts owner for 3D sounds"""
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
# SUSPENSION SYSTEM
# =============================================================================
def handle_suspend_messages(cont, owner):
    """Handle suspension messages for this individual cockroach"""
    try:
        # Find message sensor
        suspend_sensor = cont.sensors.get(SUSPEND_MESSAGE_SENSOR_NAME)
        if not suspend_sensor or not suspend_sensor.positive:
            return
                    
        # Verify subject is correct
        if getattr(suspend_sensor, 'subject', '') != SUSPEND_MESSAGE_SUBJECT:
            return
            
        # Process each message
        for body in suspend_sensor.bodies:
            process_suspend_message(owner, body)
            
    except Exception as e:
        debug_print(f"[COCKROACH] Error handling suspension messages: {e}")

def process_suspend_message(owner, body):
    """Process a specific suspension message"""
    try:
        parts = [p.strip() for p in body.split("|")]
        if len(parts) < 2:
            return
            
        action = parts[1].lower()   # "suspend", "resume"
        
        # Apply action regardless of source
        if action == "suspend":
            suspend_enemy(owner)
        elif action == "resume":
            resume_enemy(owner)
            
    except Exception as e:
        debug_print(f"[COCKROACH] Error processing message '{body}': {e}")

def suspend_enemy(owner):
    """Suspend this specific cockroach"""
    if owner.get('suspended', False):
        return
        
    owner['suspended'] = True
    owner['suspended_time'] = bge.logic.getRealTime()
    
    # Stop physical movement
    owner.suspendDynamics()
    
    # Stop sounds
    if "cockroach_data" in owner:
        cockroach_data = owner["cockroach_data"]
        if cockroach_data.get("current_sound"):
            stop_sound(cockroach_data["current_sound"])
            cockroach_data["current_sound"] = None
        
        stop_sound_by_name("cockroach_walk.ogg", owner)
    
    # Pause animation
    if "cockroach_data" in owner and cockroach_data.get("rig"):
        try:
            cockroach_data["rig"].stopAction(0)
        except:
            pass
    
    debug_print(f"[COCKROACH] Cockroach {owner.name} SUSPENDED")

def resume_enemy(owner):
    """Resume this specific cockroach"""
    if not owner.get('suspended', False):
        return
        
    owner['suspended'] = False
    
    # Resume physics
    owner.restoreDynamics()
    
    # Resume sounds (if in a state that uses them)
    if "cockroach_data" in owner:
        cockroach_data = owner["cockroach_data"]
        state = cockroach_data.get("state", "IDLE")
        
        # Restore sound based on state
        if state in ["APPROACH", "RETREAT", "IDLE"]:
            cockroach_data["current_sound"] = play_sound("cockroach_walk.ogg", owner, True)
        
        # Resume animation
        if cockroach_data.get("rig"):
            rig = cockroach_data["rig"]
            if state == "DEATH":
                play_animation(rig, "Cockroach.Death")
            elif state == "RETREAT":
                play_animation(rig, "Cockroach.Attack")
            elif state == "IDLE":
                play_animation(rig, "Cockroach.Idle")
            else:
                play_animation(rig, "Cockroach.Walk", cockroach_data["walk_animation_speed"])
    
    debug_print(f"[COCKROACH] Cockroach {owner.name} RESUMED")

# =============================================================================
# DEATH SPRITE FUNCTIONS
# =============================================================================
def show_death_sprite(owner):
    """Show death sprite at cockroach position"""
    try:
        scene = bge.logic.getCurrentScene()
        death_sprite = scene.objects.get(DEATH_SPRITE_NAME)
        
        if not death_sprite:
            debug_print(f"[COCKROACH] Death sprite not found: {DEATH_SPRITE_NAME}")
            return None
        
        # Position sprite at same location as cockroach
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
            debug_print(f"[COCKROACH] Death sprite shown")
        except:
            pass
            
        return death_sprite
        
    except Exception as e:
        debug_print(f"[COCKROACH] Error showing sprite: {e}")
        return None

def hide_death_sprite():
    """Hide death sprite"""
    try:
        scene = bge.logic.getCurrentScene()
        death_sprite = scene.objects.get(DEATH_SPRITE_NAME)
        
        if death_sprite:
            death_sprite.visible = False
            debug_print(f"[COCKROACH] Death sprite hidden")
    except:
        pass

# =============================================================================
# DAMAGE AND COLLISION HANDLERS
# =============================================================================
def handle_player_collision(owner, cockroach_data, sensor):
    """Handle collision with player to apply immediate damage"""
    if cockroach_data.get("attack_cooldown", 0) > 0:
        return
    
    player_detected = False
    
    # Search for player property in collision list
    for obj in sensor.hitObjectList:
        # Check if object is player by property or name
        if obj.get('player', False) or obj.name == "Player":
            player_detected = True
            debug_print(f"[COCKROACH] PLAYER COLLISION detected: {obj.name}")
            
            # Apply immediate damage
            apply_player_damage(owner)
            
            # Start attack animation if not active
            if not cockroach_data.get("attack_animation_started", False):
                rig = cockroach_data.get("rig")
                if rig:
                    play_animation(rig, "Cockroach.Attack")
                    cockroach_data["attack_animation_started"] = True
                    cockroach_data["attack_animation_timer"] = MIN_ATTACK_DURATION
                
                # Play attack sound
                play_sound("cockroach_attack.ogg", owner, False)
            
            break
    
    # If no player collision but in close contact (fallback)
    if cockroach_data.get("state") == "APPROACH":
        player = cockroach_data.get("player")
        if player:
            distance = (owner.worldPosition - player.worldPosition).length
            if distance <= CONTACT_DISTANCE and cockroach_data.get("attack_cooldown", 0) <= 0:
                debug_print(f"[COCKROACH] Contact by distance: {distance:.2f}")
                apply_player_damage(owner)

def apply_player_damage(owner):
    """Apply damage to player and set cooldown"""
    debug_print(f"[COCKROACH] Applying damage to player")
    
    # Apply damage to player
    game = game_access.get_game()
    if game:
        old_health = game.player.health
        game.player.take_damage(DAMAGE_TO_PLAYER)
        debug_print(f"[COCKROACH] Damage applied: {old_health} -> {game.player.health}")
    else:
        # Fallback for compatibility
        scene = bge.logic.getCurrentScene()
        game_controller = scene.objects.get("Game.Controller")
        if game_controller:
            old_health = game_controller.get('health', 100)
            game_controller['health'] = max(0, old_health - DAMAGE_TO_PLAYER)
    
    # Change to RETREAT state after attack
    if "cockroach_data" in owner:
        cockroach_data = owner["cockroach_data"]
        cockroach_data["state"] = "RETREAT"
        cockroach_data["retreat_timer"] = cockroach_data.get("retreat_duration", 2.0)
        cockroach_data["attack_cooldown"] = 0.8

# =============================================================================
# INITIALIZATION AND SETUP
# =============================================================================
def handle_new_object(owner, cont):
    """Handle a newly added object"""
    debug_print(f"[COCKROACH] New object added: {owner.name}")
    
    # Mark as processed
    owner["object_added"] = True
    
    # GET SPAWN POINT FROM PROPERTY (NEW SYSTEM)
    spawn_point = owner.get("last_spawn_point")
    spawn_id = owner.get("last_spawn_id", 0)
    
    if spawn_point:
        owner.worldPosition = spawn_point.worldPosition.copy()
        owner.worldOrientation = spawn_point.worldOrientation.copy()
        debug_print(f"[COCKROACH] Positioned at spawn point: {spawn_point.name} (ID: {spawn_id})")
    
    # ACTIVATE the cockroach
    owner['active_cockroach'] = True
    owner['health_cockroach'] = 1
    owner['enemy'] = True
    
    # CLEAR temporary property
    if 'last_spawn_point' in owner:
        del owner['last_spawn_point']
    if 'last_spawn_id' in owner:
        del owner['last_spawn_id']
    
    # Make visible and activate physics
    owner.setVisible(True)
    owner.restoreDynamics()
    
    # Notify manager using global function
    scene = bge.logic.getCurrentScene()
    pest_manager = scene.objects.get("Empty.Pest.Manager")
    if pest_manager and "notify_cockroach_activation" in pest_manager:
        pest_manager["notify_cockroach_activation"](pest_manager, owner)
    
    # Initialize normally
    initialize_cockroach(owner, cont)

def initialize_cockroach(owner, cont):
    """Complete cockroach initialization"""
    debug_print(f"[COCKROACH] Initializing {owner.name}")
    
    player = find_player_robust()
    if not player:
        debug_print("[COCKROACH] Player not found")
        return False
    
    # Find rig for animations
    rig = find_cockroach_rig(owner)
    
    # Cockroach data - WITH NEW ATTACK PROPERTIES
    cockroach_data = {
        "state": "SPAWN",
        "speed": 0.07,
        "walk_animation_speed": 6.0,
        "retreat_timer": 0,
        "idle_timer": 0,
        "collision_cooldown": 0,
        "obstacle_cooldown": 0,
        "retreat_duration": random.uniform(1.5, 2.5),
        "idle_duration": random.uniform(0.5, 1.5),
        "player": player,
        "rig": rig,
        "frame_count": 0,
        "last_position": owner.worldPosition.copy(),
        "stuck_timer": 0,
        "turn_direction": random.choice([-1, 1]),
        "death_animation_timer": 0,
        "death_animation_duration": 1.0,
        "current_sound": None,
        "last_state": None,
        "attack_animation_started": False,
        "attack_animation_timer": 0,
        "attack_cooldown": 0,
        "sprite_shown": False,
        # Obstacle avoidance
        "dodge_timer": 0.0,
        "dodge_direction": None,
        "dodge_cooldown": 0.0,
    }
    owner["cockroach_data"] = cockroach_data
    owner["initialized"] = True
    
    # Start spawn animation
    play_animation(rig, "Cockroach.Walk", cockroach_data["walk_animation_speed"])
    
    distance = (owner.worldPosition - player.worldPosition).length
    debug_print(f"[COCKROACH] Initialized - Health: {owner['health_cockroach']} - Distance: {distance:.2f}")
    return True

def find_cockroach_rig(owner):
    """Find cockroach animation rig"""
    for child in owner.children:
        if "Rig" in child.name:
            debug_print(f"[COCKROACH] Rig found: {child.name}")
            return child
    
    debug_print("[COCKROACH] Animation rig not found")
    return None

def play_animation(rig, animation_name, speed=1.0):
    """Play animation on rig"""
    if not rig:
        return False
    
    try:
        if animation_name == "Cockroach.Walk":
            rig.playAction(animation_name, 1, 49, play_mode=bge.logic.KX_ACTION_MODE_LOOP, speed=speed)
        elif animation_name == "Cockroach.Idle":
            rig.playAction(animation_name, 1, 10, play_mode=bge.logic.KX_ACTION_MODE_LOOP, speed=speed)
        elif animation_name == "Cockroach.Attack":
            rig.playAction(animation_name, 1, 15, play_mode=bge.logic.KX_ACTION_MODE_PLAY, speed=speed)
        elif animation_name == "Cockroach.Death":
            rig.playAction(animation_name, 1, 10, play_mode=bge.logic.KX_ACTION_MODE_PLAY, speed=speed)
        
        debug_print(f"[COCKROACH] Animation: {animation_name} (speed: {speed})")
        return True
    except Exception as e:
        debug_print(f"[COCKROACH] Animation error {animation_name}: {e}")
        return False

# =============================================================================
# COLLISION HANDLERS
# =============================================================================
def update_cooldowns(cockroach_data):
    """Update timers and cooldowns"""
    if cockroach_data["collision_cooldown"] > 0:
        cockroach_data["collision_cooldown"] -= 1/60.0
    if cockroach_data["obstacle_cooldown"] > 0:
        cockroach_data["obstacle_cooldown"] -= 1/60.0
    if cockroach_data["attack_cooldown"] > 0:
        cockroach_data["attack_cooldown"] -= 1/60.0

def handle_shot_collision(owner, cockroach_data, sensor):
    """Handle collision with shots"""
    if cockroach_data["collision_cooldown"] > 0:
        return
    
    for obj in sensor.hitObjectList:
        if obj.get('shot', False):
            old_health = owner['health_cockroach']
            owner['health_cockroach'] -= 1
            cockroach_data["collision_cooldown"] = 0.2
            
            debug_print(f"[COCKROACH] Shot hit - Health: {old_health} -> {owner['health_cockroach']}")
            
            break

def handle_obstacle_collision(owner, cockroach_data, sensor):
    """
    Handle collision with obstacles.
    Instead of simple point turn, activate dodge state to go around obstacle.
    """
    if cockroach_data["obstacle_cooldown"] > 0:
        return
    
    obstacle_detected = False
    for obj in sensor.hitObjectList:
        if obj.get('col', False):
            obstacle_detected = True
            break
    
    if not obstacle_detected:
        return

    debug_print("[COCKROACH] Obstacle collision -> activating dodge")

    # Apply immediate turn to separate from obstacle
    owner.applyRotation([0, 0, math.radians(45 * cockroach_data["turn_direction"])], True)

    # Calculate perpendicular direction (dodge) from new orientation
    euler_z = owner.worldOrientation.to_euler().z
    forward = Vector((math.sin(euler_z), math.cos(euler_z), 0.0))
    if forward.length > 0.001:
        forward.normalize()

    # Activate dodge for 0.7 seconds
    cockroach_data["dodge_direction"] = forward.copy()
    cockroach_data["dodge_timer"]     = 0.7
    cockroach_data["dodge_cooldown"]  = 0.0

    # Alternate side and apply cooldown
    cockroach_data["turn_direction"]   *= -1
    cockroach_data["obstacle_cooldown"] = 0.4
    cockroach_data["stuck_timer"]       = 0

# =============================================================================
# DEATH HANDLING
# =============================================================================
def handle_death(owner, cont):
    """Handle death start"""
    debug_print("[COCKROACH] Starting death")
    
    cockroach_data = owner["cockroach_data"]
    cockroach_data["state"] = "DEATH"
    cockroach_data["death_animation_timer"] = cockroach_data["death_animation_duration"]
    
    # Stop any physical movement
    owner.suspendDynamics()
    
    # Stop current sound
    if cockroach_data["current_sound"]:
        stop_sound(cockroach_data["current_sound"])
        cockroach_data["current_sound"] = None
    
    # Stop walk sound
    stop_sound_by_name("cockroach_walk.ogg", owner)
    
    # SHOW DEATH SPRITE
    show_death_sprite(owner)
    cockroach_data["sprite_shown"] = True
    
    # Play death animation and 3D sound
    if cockroach_data.get("rig"):
        play_animation(cockroach_data["rig"], "Cockroach.Death")
    play_sound("cockroach_death.ogg", owner, False)
    
    debug_print(f"[COCKROACH] Death animation started with sprite")

def handle_death_animation(owner, cockroach_data):
    """Handle death animation"""
    cockroach_data["death_animation_timer"] -= 1/60.0
    
    animation_finished = False
    rig = cockroach_data.get("rig")
    
    # ENHANCED ANIMATION CHECK
    if rig:
        current_frame = rig.getActionFrame()
        # Check if animation ended (None) or is at LAST frame
        if current_frame is None:  # Animation ended completely
            animation_finished = True
        elif current_frame >= 10:  # At last frame
            if cockroach_data["death_animation_timer"] <= 0.5:  # Wait extra half second
                animation_finished = True
    else:
        # Fallback: use timer only if no rig
        if cockroach_data["death_animation_timer"] <= 0:
            animation_finished = True
    
    if animation_finished:
        debug_print("[COCKROACH] Death animation completed - Deleting object")
        
        # Hide sprite if shown
        if cockroach_data.get("sprite_shown", False):
            hide_death_sprite()
        
        # INCREMENT BUG COUNTER (COCKROACH COUNTS AS 1)
        try:
            import game_access
            game = game_access.get_game()
            if game and hasattr(game.state, 'bugs_total'):
                old_value = game.state.bugs_total
                game.state.bugs_total += 1
                debug_print(f"[COCKROACH] Bug counter: {old_value} -> {game.state.bugs_total} (+1)")
        except Exception as e:
            debug_print(f"[COCKROACH] Error updating bug counter: {e}")
        
        # Notify manager using global function
        scene = bge.logic.getCurrentScene()
        pest_manager = scene.objects.get("Empty.Pest.Manager")
        if pest_manager and "notify_cockroach_death" in pest_manager:
            pest_manager["notify_cockroach_death"](pest_manager, owner)
        else:
            owner.endObject()

# =============================================================================
# STATE MACHINE
# =============================================================================
def process_state_machine(owner, cockroach_data, cont=None):
    """Main state machine"""
    old_state = cockroach_data["last_state"]
    new_state = cockroach_data["state"]
    
    # Detect state change for sound management
    if old_state != new_state:
        # If state changed, reset attack flag
        if new_state != "APPROACH":
            cockroach_data["attack_animation_started"] = False
        
        handle_state_change(owner, cockroach_data, old_state, new_state)
        cockroach_data["last_state"] = new_state
    
    # Execute current state
    if new_state == "SPAWN":
        handle_spawn_state(owner, cockroach_data)
    elif new_state == "APPROACH":
        handle_approach_state(owner, cockroach_data, cont=cont)
    elif new_state == "RETREAT":
        handle_retreat_state(owner, cockroach_data)
    elif new_state == "IDLE":
        handle_idle_state(owner, cockroach_data)

def handle_state_change(owner, cockroach_data, old_state, new_state):
    """Handle state changes"""
    debug_print(f"[COCKROACH] State: {old_state} -> {new_state}")
    
    # Stop previous sound
    if cockroach_data["current_sound"]:
        stop_sound(cockroach_data["current_sound"])
        cockroach_data["current_sound"] = None
    
    stop_sound_by_name("cockroach_walk.ogg", owner)
    
    # Start sounds based on new state
    if new_state in ["APPROACH", "RETREAT"]:
        cockroach_data["current_sound"] = play_sound("cockroach_walk.ogg", owner, True)
        # Set walk animation for both states
        if new_state == "RETREAT":
            play_animation(cockroach_data["rig"], "Cockroach.Walk", cockroach_data["walk_animation_speed"])
    elif new_state == "IDLE":
        cockroach_data["current_sound"] = play_sound("cockroach_walk.ogg", owner, True)

def handle_spawn_state(owner, cockroach_data):
    """SPAWN state -> APPROACH"""
    cockroach_data["state"] = "APPROACH"
    play_animation(cockroach_data["rig"], "Cockroach.Walk", cockroach_data["walk_animation_speed"])

def handle_approach_state(owner, cockroach_data, cont=None):
    """APPROACH state with early attack logic"""
    player = cockroach_data["player"]
    if not player:
        return
    
    cockroach_data["frame_count"] += 1
    
    # Calculate distance to player
    distance_to_player = (owner.worldPosition - player.worldPosition).length
    
    # Start attack animation if in range but NO active collision
    if (distance_to_player <= ATTACK_ANIMATION_DISTANCE and 
        not cockroach_data["attack_animation_started"] and
        cockroach_data.get("attack_cooldown", 0) <= 0):
        
        # Start attack animation when close
        debug_print(f"[COCKROACH] Starting attack animation (distance: {distance_to_player:.2f})")
        play_animation(cockroach_data["rig"], "Cockroach.Attack")
        cockroach_data["attack_animation_started"] = True
        cockroach_data["attack_animation_timer"] = MIN_ATTACK_DURATION
        
        # Play attack sound
        play_sound("cockroach_attack.ogg", owner, False)
    
    # Update attack animation timer
    if cockroach_data["attack_animation_started"]:
        cockroach_data["attack_animation_timer"] -= 1/60.0
        if cockroach_data["attack_animation_timer"] <= 0:
            cockroach_data["attack_animation_started"] = False
    
    # Move toward player with obstacle avoidance (pass cont to read Ray sensor)
    move_toward_player(owner, cockroach_data, player, cont=cont)
    
    # Stuck fallback (acts if Ray and collision weren't enough)
    if check_stuck(owner, cockroach_data):
        debug_print("[COCKROACH] Emergency turn applied due to stuck")
    
    # Keep walk animation (except during attack)
    rig = cockroach_data.get("rig")
    if rig and rig.getActionFrame() is None and not cockroach_data["attack_animation_started"]:
        play_animation(rig, "Cockroach.Walk", cockroach_data["walk_animation_speed"])

def handle_retreat_state(owner, cockroach_data):
    """RETREAT state - Move away from player after attack"""
    cockroach_data["retreat_timer"] -= 1/60.0
    
    if cockroach_data["retreat_timer"] <= 0:
        # End of retreat, return to IDLE or APPROACH
        cockroach_data["state"] = "IDLE"
        cockroach_data["idle_timer"] = cockroach_data["idle_duration"]
        cockroach_data["attack_animation_started"] = False
        play_animation(cockroach_data["rig"], "Cockroach.Idle")
        debug_print("[COCKROACH] Retreat ended, returning to IDLE")
    else:
        # During retreat: move away from player
        player = cockroach_data["player"]
        if player:
            move_away_from_player(owner, cockroach_data, player)
        
        # Keep walk animation during retreat
        rig = cockroach_data.get("rig")
        if rig and rig.getActionFrame() is None:
            play_animation(rig, "Cockroach.Walk", cockroach_data["walk_animation_speed"])

def handle_idle_state(owner, cockroach_data):
    """IDLE state - Wait"""
    cockroach_data["idle_timer"] -= 1/60.0
    
    if cockroach_data["idle_timer"] <= 0:
        cockroach_data["state"] = "APPROACH"
        play_animation(cockroach_data["rig"], "Cockroach.Walk", cockroach_data["walk_animation_speed"])

# =============================================================================
# MOVEMENT FUNCTIONS
# =============================================================================
def get_ray_sensor_hit(cont):
    """
    Read frontal Ray sensor ('Ray'; property 'col'; +Y axis; range 0.5).
    Returns True if obstacle ahead, False otherwise.
    """
    ray = cont.sensors.get("Ray")
    if ray is None:
        return False
    return ray.positive

def _set_orientation_from_direction(owner, direction):
    """Orient object in movement direction (+Y axis forward)."""
    angle = math.atan2(direction.y, direction.x) - math.pi / 2
    owner.worldOrientation = [0, 0, angle]

def move_toward_player(owner, cockroach_data, player, cont=None):
    """
    Move cockroach toward player with obstacle avoidance.

    Three-layer system:
      1. Frontal Ray sensor -> detects obstacle before impact and diverts.
      2. 'dodging' state -> maintains lateral deviation during dodge_timer
         seconds to go around obstacle.
      3. check_stuck() -> fallback if previous layers fail
    """
    direction_to_player = player.worldPosition - owner.worldPosition
    direction_to_player.z = 0

    if direction_to_player.length < 0.1:
        return

    direction_to_player.normalize()

    # 1. READ RAY SENSOR
    ray_blocked = False
    if cont is not None:
        ray_blocked = get_ray_sensor_hit(cont)

    # 2. DODGE STATE MANAGEMENT
    dodge_timer   = cockroach_data.get("dodge_timer", 0.0)
    dodge_dir_raw = cockroach_data.get("dodge_direction", None)

    if ray_blocked and dodge_timer <= 0.0:
        # Start new dodge maneuver
        # Choose perpendicular side (±90° relative to player direction)
        side = cockroach_data.get("turn_direction", 1)
        perp = Vector((-direction_to_player.y * side,
                        direction_to_player.x * side,
                        0.0))
        perp.normalize()
        cockroach_data["dodge_direction"] = perp.copy()
        cockroach_data["dodge_timer"]     = 0.6          # seconds of dodge
        cockroach_data["dodge_cooldown"]  = 0.3          # minimum pause between dodges
        cockroach_data["turn_direction"] *= -1           # alternate side next time
        dodge_timer   = cockroach_data["dodge_timer"]
        dodge_dir_raw = perp
        debug_print("[COCKROACH] Ray blocked -> starting dodge")

    # Decrement dodge timers
    if dodge_timer > 0.0:
        cockroach_data["dodge_timer"] = max(0.0, dodge_timer - 1 / 60.0)

    dodge_cooldown = cockroach_data.get("dodge_cooldown", 0.0)
    if dodge_cooldown > 0.0:
        cockroach_data["dodge_cooldown"] = max(0.0, dodge_cooldown - 1 / 60.0)

    # 3. CALCULATE FINAL MOVEMENT DIRECTION
    if cockroach_data.get("dodge_timer", 0.0) > 0.0 and dodge_dir_raw is not None:
        # Mix: 40% toward player + 60% lateral to go around smoothly
        dodge_dir = Vector(dodge_dir_raw)
        move_dir  = (direction_to_player * 0.4 + dodge_dir * 0.6)
        move_dir.z = 0
        if move_dir.length > 0.001:
            move_dir.normalize()
    else:
        move_dir = direction_to_player

    # 4. APPLY MOVEMENT
    owner.worldPosition += move_dir * cockroach_data["speed"]
    _set_orientation_from_direction(owner, move_dir)

def move_away_from_player(owner, cockroach_data, player):
    """Move cockroach away from player."""
    direction = owner.worldPosition - player.worldPosition
    direction.z = 0

    if direction.length > 0.1:
        direction.normalize()
        owner.worldPosition += direction * cockroach_data["speed"]
        _set_orientation_from_direction(owner, direction)

def check_stuck(owner, cockroach_data):
    """
    Stuck detection fallback based on minimal movement.

    If cockroach hasn't moved for STUCK_THRESHOLD seconds,
    apply sharp turn and activate emergency dodge.
    """
    STUCK_THRESHOLD = 0.6   # seconds before considering stuck
    MIN_MOVEMENT    = 0.008 # movement threshold (Blender units)

    current_pos   = owner.worldPosition
    distance_moved = (current_pos - cockroach_data["last_position"]).length

    if distance_moved < MIN_MOVEMENT:
        cockroach_data["stuck_timer"] += 1 / 60.0

        if cockroach_data["stuck_timer"] > STUCK_THRESHOLD:
            # Random turn between 60 and 120 degrees to escape blocking angle
            angle_deg = random.uniform(60, 120) * cockroach_data["turn_direction"]
            owner.applyRotation([0, 0, math.radians(angle_deg)], True)
            cockroach_data["turn_direction"] *= -1

            # Force immediate dodge
            cockroach_data["dodge_timer"]     = 0.8
            cockroach_data["dodge_cooldown"]  = 0.0

            # Calculate perpendicular direction post-turn and store it
            forward = Vector((math.sin(owner.worldOrientation.to_euler().z),
                               math.cos(owner.worldOrientation.to_euler().z),
                               0.0))
            if forward.length > 0.001:
                forward.normalize()
            cockroach_data["dodge_direction"] = forward.copy()

            cockroach_data["stuck_timer"] = 0
            debug_print("[COCKROACH] Stuck detected -> emergency turn")
            return True
    else:
        cockroach_data["stuck_timer"] = 0

    cockroach_data["last_position"] = current_pos.copy()
    return False

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main(cont):
    """Main cockroach script"""
    owner = cont.owner
    
    # FIRST: Handle suspension messages
    handle_suspend_messages(cont, owner)
    
    # If suspended, do NOT process normal logic
    if owner.get('suspended', False):
        return
    
    # Clean up finished sounds
    cleanup_sounds()
    
    # Update 3D listener each frame (with PLAYER)
    update_sound_3d_listener()
    
    # NEW OBJECT DETECTION
    if "object_added" not in owner:
        handle_new_object(owner, cont)
        return
    
    # MAIN CONTROL: Only execute if cockroach is active
    if not owner.get('active_cockroach', False):
        return
    
    # If not visible, deactivate
    if not owner.visible:
        owner['active_cockroach'] = False
        return
    
    # Normal initialization
    if "initialized" not in owner:
        if not initialize_cockroach(owner, cont):
            return
    
    # References
    cockroach_data = owner["cockroach_data"]
    
    # Process player collision sensor
    collision_player_sensor = cont.sensors.get(COLLISION_PLAYER_SENSOR_NAME)
    if collision_player_sensor and collision_player_sensor.positive:
        handle_player_collision(owner, cockroach_data, collision_player_sensor)
    
    # Process collision sensors
    collision_shot_sensor = cont.sensors.get(COLLISION_SHOT_SENSOR_NAME)
    collision_obstacle_sensor = cont.sensors.get(COLLISION_OBSTACLE_SENSOR_NAME)
    
    if collision_shot_sensor and collision_shot_sensor.positive:
        handle_shot_collision(owner, cockroach_data, collision_shot_sensor)
    
    if collision_obstacle_sensor and collision_obstacle_sensor.positive:
        handle_obstacle_collision(owner, cockroach_data, collision_obstacle_sensor)
    
    # Check death
    if owner['health_cockroach'] <= 0 and cockroach_data["state"] != "DEATH":
        handle_death(owner, cont)
        return
    
    # If in DEATH state, handle death animation
    if cockroach_data["state"] == "DEATH":
        handle_death_animation(owner, cockroach_data)
        return
    
    # Update cooldowns and timers
    update_cooldowns(cockroach_data)
    
    # State machine
    process_state_machine(owner, cockroach_data, cont=cont)