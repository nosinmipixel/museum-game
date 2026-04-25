"""
player_movement.py

Manages player movement, animations, sound effects, and stamina system.

This script handles all player movement mechanics including walking, rotation,
attacking with spray, stamina management, shadow following, and obstacle detection.

Main Features:
    1. Player movement with obstacle detection and stuck prevention
    2. Stamina system with constant drain and speed reduction at low stamina
    3. Spray attack system with visual effects and sound
    4. Player shadow following with scale animation during turns
    5. Animation management (Idle, Walk, Attack, Talk, Damage)
    6. Sound management for footsteps, spray, and damage
    7. Dialog mode with rotation toward NPC
    8. Health monitoring with damage animation
    9. Optimized caching system for performance

Setup:
    Connect to Logic Bricks as Python controller with module 'player_movement.main'
    Required sensors: Key.W/Up, Key.S/Down, Key.A/Left, Key.D/Right,
                      Key.Space, Mouse.Right, Near_npc, Ray

Configurable Variables:
    DEBUG_MODE (bool): Enable debug logging (default: False)
    MOVE_SPEED_BASE (float): Normal movement speed (default: 0.075)
    MOVE_SPEED_MIN (float): Minimum speed with low stamina (default: 0.030)
    ROTATION_SPEED (float): Rotation speed in radians (default: math.radians(5))
    STAMINA_DRAIN_INTERVAL (float): Stamina drain check interval in seconds (default: 1.0)
    STAMINA_SPEED_THRESHOLD (float): Stamina percentage below which speed is reduced (default: 30.0)
    STAMINA_CRITICAL_THRESHOLD (float): Stamina percentage for critical alert (default: 10.0)
    SHADOW_SCALE_TURNING (float): Shadow scale multiplier during turns (default: 1.1)
    SHADOW_SCALE_SPEED (float): Shadow scale transition speed (default: 0.15)

Notes:
    - Requires game_access module for player health and stamina
    - Requires sound_fx module for sound playback
    - Stamina drains constantly at base rate, accelerated when doors are open
    - Spray requires spray_total > 0 from game state
    - Obstacle detection uses Ray sensor named 'Ray'
    - NPC detection uses Near_npc sensor for dialog rotation
    - Player.Shadow object automatically follows player position

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
__description__ = "Manages player movement, animations, sound effects, and stamina system"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
import math
import aud

# Pre-import to avoid repeated imports in loop
try:
    from game_access import get_player, get_state, get_stamina, get_stamina_percentage, modify_stamina, get_stamina_drain_rates
except (ImportError, NameError):
    def get_player():
        class DummyPlayer:
            health = 100
            stamina = 100
            max_stamina = 100
        return DummyPlayer()
    def get_state():
        return None
    def get_stamina():
        return 100
    def get_stamina_percentage():
        return 100
    def modify_stamina(amount):
        return 100
    def get_stamina_drain_rates():
        return {'base_rate': 1.0, 'doors_rate': 50.0}

# =============================================================================
# CONFIGURATION
# =============================================================================
DEBUG_MODE = False

# Performance constants
CACHE_UPDATE_INTERVAL   = 0.5
NPC_CHECK_INTERVAL      = 0.2
ROTATION_CALC_INTERVAL  = 0.1
HEALTH_CHECK_INTERVAL   = 0.1
OBSTACLE_CHECK_INTERVAL = 0.1
ANIMATION_BLENDIN       = 2

# Movement constants
MOVE_SPEED_BASE        = 0.075  # Normal speed
MOVE_SPEED_MIN         = 0.030  # Minimum speed with low stamina
ROTATION_SPEED         = math.radians(5)
DIALOG_ROTATION_SPEED  = math.radians(3)

# Stamina constants
STAMINA_DRAIN_INTERVAL     = 1.0    # Check drain every 1 second
STAMINA_SPEED_THRESHOLD    = 30.0   # Below 30% stamina, reduce speed
STAMINA_CRITICAL_THRESHOLD = 10.0   # Below 10%, stamina critical

# =============================================================================
# SHADOW CONSTANTS
# =============================================================================
SHADOW_SCALE_NORMAL  = 1.0
SHADOW_SCALE_TURNING = 1.1   # 10% larger when turning
SHADOW_SCALE_SPEED   = 0.15  # Scale transition speed
SHADOW_SCALE_EPSILON = 0.001 # Minimum change threshold to avoid unnecessary writes

# =============================================================================
# GLOBAL VARIABLES
# =============================================================================
_object_cache        = None
_spray_objects_cache = None
_initialized         = False

# =============================================================================
# CLASSES
# =============================================================================

class ObjectCache:
    __slots__ = ['scene', 'player', 'game_controller', 'rig_object',
                 'camera', 'player_shadow', 'last_update', 'objects']
    
    def __init__(self):
        self.scene           = None
        self.player          = None
        self.game_controller = None
        self.rig_object      = None
        self.camera          = None
        self.player_shadow   = None
        self.last_update     = 0.0
        self.objects         = {}
    
    def update(self, current_time, force=False):
        if not force and current_time - self.last_update < CACHE_UPDATE_INTERVAL:
            return
        
        self.last_update = current_time
        self.scene = bge.logic.getCurrentScene()
        
        if self.scene:
            self.player          = self.scene.objects.get("Player")
            self.game_controller = self.scene.objects.get("Game.Controller")
            self.camera          = self.scene.active_camera
            self.player_shadow   = self.scene.objects.get("Player.Shadow")
            
            if self.rig_object is None:
                self.rig_object = self.scene.objects.get("charA_metarig")
                if self.rig_object is None:
                    for obj in self.scene.objects:
                        if "charA_metarig" in obj.name:
                            self.rig_object = obj
                            break
    
    def get(self, name):
        if name in self.objects:
            return self.objects[name]
        obj = self.scene.objects.get(name) if self.scene else None
        if obj:
            self.objects[name] = obj
        return obj

class SprayManager:
    OBJECTS_NAMES = ('charA_can', 'charA_spray_effect', 'charA_spray_effect.001')
    EFFECTS_NAMES = ('charA_spray_effect', 'charA_spray_effect.001')
    
    def __init__(self):
        self.objects      = {}
        self.effects_only = {}
        self.initialized  = False
    
    def initialize(self, scene):
        if self.initialized:
            return
        for name in self.OBJECTS_NAMES:
            obj = scene.objects.get(name)
            if obj:
                self.objects[name] = obj
                if name in self.EFFECTS_NAMES:
                    self.effects_only[name] = obj
        self.initialized = True
    
    def set_visibility(self, visible, effects_only=False):
        target = self.effects_only if effects_only else self.objects
        for obj in target.values():
            obj.visible = visible

class SoundManager:
    def __init__(self):
        self.device      = None
        self.handles     = {}
        self.sounds_path = None
    
    def get_device(self):
        if self.device is None:
            try:
                self.device = aud.Device()
                self.device.distance_model = aud.DISTANCE_MODEL_LINEAR
            except:
                pass
        return self.device
    
    def get_sounds_path(self):
        if self.sounds_path is None:
            self.sounds_path = bge.logic.expandPath("//Assets/Sounds/")
        return self.sounds_path
    
    def play(self, sound_file, loop=False, volume=1.0, is_3d=False):
        handle = self.handles.get(sound_file)
        if handle and handle.status == aud.STATUS_PLAYING:
            return
        try:
            device = self.get_device()
            if device:
                sound = aud.Sound(self.get_sounds_path() + sound_file)
                handle = device.play(sound)
                handle.relative     = not is_3d
                handle.volume       = volume
                handle.loop_count   = -1 if loop else 0
                self.handles[sound_file] = handle
        except:
            pass
    
    def stop(self, sound_file):
        handle = self.handles.get(sound_file)
        if handle:
            try:
                handle.stop()
                self.handles[sound_file] = None
            except:
                pass
    
    def stop_all(self, sound_list):
        for sound in sound_list:
            self.stop(sound)

class AnimationManager:
    __slots__ = ['current', 'layer', 'rig_object', '_speed', '_frames']
    
    def __init__(self):
        self.current    = None
        self.layer      = -1
        self.rig_object = None
        self._speed     = -1.0
        self._frames    = None
    
    def play(self, rig, animation_name, start_frame, end_frame,
             loop=True, speed=1.0, layer=0, blendin=ANIMATION_BLENDIN):
        if (self.current == animation_name
                and self.layer  == layer
                and self._speed == speed
                and self._frames == (start_frame, end_frame)):
            return
        
        try:
            self.current    = animation_name
            self.layer      = layer
            self._speed     = speed
            self._frames    = (start_frame, end_frame)
            self.rig_object = rig
            
            play_mode = bge.logic.KX_ACTION_MODE_LOOP if loop else bge.logic.KX_ACTION_MODE_PLAY
            rig.playAction(
                animation_name, start_frame, end_frame,
                layer=layer, priority=0, blendin=blendin,
                play_mode=play_mode, speed=speed
            )
        except:
            pass
    
    def stop(self, layer=0):
        if self.rig_object:
            try:
                self.rig_object.stopAction(layer)
            except:
                pass
    
    def invalidate(self):
        self.current = None

class NPCDetector:
    def __init__(self):
        self.last_check  = 0.0
        self.cached_npc  = None
    
    def find(self, controller, current_time, owner):
        if current_time - self.last_check < NPC_CHECK_INTERVAL:
            return self.cached_npc
        
        self.last_check  = current_time
        self.cached_npc  = None
        
        try:
            sensor = controller.sensors.get("Near_npc")
            # If the sensor is not active, no NPC is in range
            if not (sensor and sensor.positive):
                return None
            
            """
            # The Near sensor only exposes a single hitObject (the one that triggered
            # the most recent event), not a list. With multiple NPCs in range,
            # it might point to the
            # We iterate through the scene filtering by the 'npc' property and choose
            # the object closest to the player's current position.
            """
            scene        = bge.logic.getCurrentScene()
            player_pos   = owner.worldPosition
            closest_npc  = None
            closest_dist = float('inf')
            
            for obj in scene.objects:
                if not obj.get('npc', False):
                    continue
                dist = (obj.worldPosition - player_pos).length
                if dist < closest_dist:
                    closest_dist = dist
                    closest_npc  = obj
            
            self.cached_npc = closest_npc
        except:
            pass
        
        return self.cached_npc

class RotationController:
    def __init__(self):
        self.last_calc_time = 0.0
    
    def rotate_towards(self, owner, target, rotation_speed, current_time):
        if current_time - self.last_calc_time < ROTATION_CALC_INTERVAL:
            return False
        
        self.last_calc_time = current_time
        
        if not target:
            return False
        
        try:
            direction   = target.worldPosition - owner.worldPosition
            direction.z = 0
            
            if direction.length < 0.1:
                return True
            
            direction.normalize()
            forward   = owner.getAxisVect([0, 1, 0])
            forward.z = 0
            
            if forward.length == 0:
                return False
            
            forward.normalize()
            
            dot   = max(-1.0, min(1.0, forward.dot(direction)))
            angle = math.acos(dot)
            
            cross = forward.cross(direction)
            if cross.z < 0:
                angle = -angle
            
            max_angle = rotation_speed
            if abs(angle) > max_angle:
                angle = max_angle if angle > 0 else -max_angle
            
            owner.applyRotation([0, 0, angle], True)
            
            return abs(angle) < 0.05
        
        except:
            return False

class HealthMonitor:
    def __init__(self):
        self.last_check  = 0.0
        self.last_health = None
    
    def check(self, owner, rig_object, animation_manager, current_time):
        if current_time - self.last_check < HEALTH_CHECK_INTERVAL:
            return
        
        self.last_check = current_time
        
        current_health = owner.get('health', 100)
        try:
            player_data = get_player()
            if player_data:
                current_health = player_data.health
        except:
            pass
        
        if self.last_health is None:
            self.last_health = current_health
        
        if not owner.get('player_attacking', False):
            if current_health < self.last_health and current_health > 1:
                bge.logic.sendMessage("sound_fx.play", "sound_fx.play|damage_1.ogg")
                
                if rig_object:
                    try:
                        # Comment stopAction(0) to mantain walking animation after damage
                        # rig_object.stopAction(0)
                        rig_object.playAction(
                            'Damage', 1, 30,
                            layer=1, priority=0, blendin=ANIMATION_BLENDIN,
                            play_mode=bge.logic.KX_ACTION_MODE_PLAY, speed=3.0
                        )
                    except:
                        pass
                
                owner['health'] = current_health
        
        self.last_health = current_health

class ObstacleDetector:
    def __init__(self):
        self.last_check        = 0.0
        self.obstacle_detected = False
        self.stuck_frame_count = 0
        self.last_position     = None
    
    def check(self, controller, wants_forward, current_time):
        if current_time - self.last_check < OBSTACLE_CHECK_INTERVAL:
            return self.obstacle_detected
        
        self.last_check = current_time
        
        ray_sensor = controller.sensors.get('Ray')
        if not ray_sensor:
            self.obstacle_detected = False
            return False
        
        has_obstacle = ray_sensor.positive and wants_forward
        
        if has_obstacle != self.obstacle_detected:
            self.obstacle_detected = has_obstacle
            if not has_obstacle:
                self.stuck_frame_count = 0
                self.last_position     = None
        
        return self.obstacle_detected
    
    def update_stuck_detection(self, owner_position, is_moving):
        if is_moving:
            self.stuck_frame_count = 0
            self.last_position     = None
            return False
        
        if self.last_position is None:
            self.last_position = owner_position
            return False
        
        if (owner_position - self.last_position).length < 0.001:
            self.stuck_frame_count += 1
        else:
            self.stuck_frame_count = 0
            self.last_position     = owner_position
        
        return self.stuck_frame_count > 15

class InputHandler:
    SENSOR_KEYS = {
        'W': 'Key.W', 'UP': 'Key.Up',
        'S': 'Key.S', 'DOWN': 'Key.Down',
        'A': 'Key.A', 'LEFT': 'Key.Left',
        'D': 'Key.D', 'RIGHT': 'Key.Right',
        'SPACE': 'Key.Space',
        'MOUSE_RIGHT': 'Mouse.Right'
    }
    
    def __init__(self):
        self.sensor_cache      = {}
        self.obstacle_detector = ObstacleDetector()
        self._last_space_state = False
        self._last_mouse_right_state = False
        self._last_attack_state = False
    
    def update(self, owner, controller, on_dialog, current_time):
        if on_dialog:
            owner['moving_forward']    = False
            owner['moving_backward']   = False
            owner['rotating_left']     = False
            owner['rotating_right']    = False
            owner['attacking']         = False
            owner['player_attacking']  = False
            owner['obstacle_blocking'] = False
            self.obstacle_detector.obstacle_detected = False
            return
        
        sensors = controller.sensors
        
        wants_forward    = self._get_sensor_state(sensors, ['W', 'UP'])
        wants_backward   = self._get_sensor_state(sensors, ['S', 'DOWN'])
        wants_left       = self._get_sensor_state(sensors, ['A', 'LEFT'])
        wants_right      = self._get_sensor_state(sensors, ['D', 'RIGHT'])
        
        obstacle_blocking = self.obstacle_detector.check(controller, wants_forward, current_time)
        
        owner['obstacle_blocking'] = obstacle_blocking
        owner['moving_forward']    = wants_forward and not obstacle_blocking
        owner['moving_backward']   = wants_backward
        owner['rotating_left']     = wants_left
        owner['rotating_right']    = wants_right
        
        is_moving = (owner['moving_forward'] or owner['moving_backward'] or
                     owner['rotating_left'] or owner['rotating_right'])
        
        owner['player_stuck'] = self.obstacle_detector.update_stuck_detection(
            owner.worldPosition, is_moving
        ) if obstacle_blocking and wants_forward else False
        
        space_state      = self._get_sensor_state(sensors, ['SPACE'])
        mouse_right_state = self._get_sensor_state(sensors, ['MOUSE_RIGHT'])
        
        current_attack_state = space_state or mouse_right_state
        
        if current_attack_state != self._last_attack_state:
            owner['attacking']        = current_attack_state
            owner['player_attacking'] = current_attack_state
            self._last_attack_state   = current_attack_state
        
        self._last_space_state      = space_state
        self._last_mouse_right_state = mouse_right_state
    
    def _init_owner_properties(self, owner):
        """Initializes all necessary properties (called ONCE from main)"""
        props_to_init = {
            'moving_forward':       False,
            'moving_backward':      False,
            'rotating_left':        False,
            'rotating_right':       False,
            'attacking':            False,
            'player_attacking':     False,
            'obstacle_blocking':    False,
            'player_stuck':         False,
            'player_walking':       False,
            'player_idle':          False,
            'on_dialog':            False,
            'player_talking':       False,
            'player_talk_phone':    False,
            'dialog_rotation_done': False,
            'last_dialog_state':    False,
            'spray_sound_playing':  False,
            'spray_sound_started':  False,
            'last_attack_state':    False,
            'health':               100,
            'shadow_scale_current': SHADOW_SCALE_NORMAL,
            'was_turning':          False,
            'current_spray_sound':  None,
            'effects_visible':      False,
            'prev_animation':       None,
            # Stamina properties
            'stamina_last_drain':   0.0,
            'stamina_critical_alert': False,
        }
        for prop, default in props_to_init.items():
            if prop not in owner:
                owner[prop] = default
    
    def _get_sensor_state(self, sensors, key_names):
        for key in key_names:
            sensor_name = self.SENSOR_KEYS.get(key)
            if not sensor_name:
                continue
            sensor = self.sensor_cache.get(sensor_name)
            if sensor is None:
                sensor = sensors.get(sensor_name)
                if sensor:
                    self.sensor_cache[sensor_name] = sensor
            if sensor and sensor.positive:
                return True
        return False

# =============================================================================
# INITIALIZATION FUNCTIONS
# =============================================================================

def get_cache():
    global _object_cache
    if _object_cache is None:
        _object_cache = ObjectCache()
    return _object_cache

def get_spray_manager():
    global _spray_objects_cache
    if _spray_objects_cache is None:
        _spray_objects_cache = SprayManager()
    return _spray_objects_cache

def initialize_managers(scene):
    get_spray_manager().initialize(scene)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def debug_print(message):
    if DEBUG_MODE:
        print(f"[PLAYER] {message}")

# =============================================================================
# SHADOW SCALE UPDATE FUNCTION
# =============================================================================

def update_shadow_scale(shadow, is_turning, current_scale):
    """
    Updates shadow scale with smooth transition.
    SHADOW_SCALE_EPSILON threshold: if difference is insignificant,
    skip writing to localScale (avoids unnecessary C++ access each frame).
    """
    if not shadow:
        return current_scale
    
    target_scale = SHADOW_SCALE_TURNING if is_turning else SHADOW_SCALE_NORMAL
    diff         = target_scale - current_scale
    
    if abs(diff) < SHADOW_SCALE_EPSILON:
        return current_scale
    
    new_scale          = current_scale + diff * SHADOW_SCALE_SPEED
    shadow.localScale.x = new_scale
    shadow.localScale.y = new_scale
    return new_scale

# =============================================================================
# STAMINA SYSTEM
# =============================================================================

def update_stamina_system(owner, current_time):
    """
    Manages player stamina drain
    - Constant base drain
    - Accelerated drain when doors are open
    """
    # Initialize last drain timestamp
    if 'stamina_last_drain' not in owner:
        owner['stamina_last_drain'] = current_time
    
    # Check if it's time to apply drain
    if current_time - owner['stamina_last_drain'] < STAMINA_DRAIN_INTERVAL:
        return
    
    owner['stamina_last_drain'] = current_time
    
    # Get drain rates
    drain_rates = get_stamina_drain_rates()
    state = get_state()
    doors_opened = getattr(state, 'doors_opened', 0) if state else 0
    
    # Calculate loss per second (convert from %/minute to %/second)
    base_drain = drain_rates['base_rate'] / 60.0
    doors_drain = (drain_rates['doors_rate'] / 60.0) if doors_opened > 0 else 0
    
    total_drain = base_drain + doors_drain
    
    # Apply drain
    current_stamina = get_stamina()
    new_stamina = modify_stamina(-total_drain)
    
    # Optional debug
    if DEBUG_MODE:
        print(f"[STAMINA] Drain: {total_drain:.2f}% | Doors: {doors_opened} | Stamina: {new_stamina:.1f}%")
    
    # Check critical stamina for alerts
    if new_stamina <= STAMINA_CRITICAL_THRESHOLD:
        owner['stamina_critical_alert'] = True
    else:
        owner['stamina_critical_alert'] = False

def get_effective_speed():
    """
    Calculates effective player speed based on current stamina
    Returns: effective speed (between MOVE_SPEED_MIN and MOVE_SPEED_BASE)
    """
    stamina_percent = get_stamina_percentage()
    
    if stamina_percent <= STAMINA_SPEED_THRESHOLD:
        # Reduce speed proportionally
        speed_ratio = max(MOVE_SPEED_MIN / MOVE_SPEED_BASE,
                         stamina_percent / STAMINA_SPEED_THRESHOLD)
        effective_speed = MOVE_SPEED_BASE * speed_ratio
    else:
        effective_speed = MOVE_SPEED_BASE
    
    return effective_speed

# =============================================================================
# GLOBAL SINGLETON MANAGERS
# =============================================================================

_sound_manager       = None
_animation_manager   = None
_npc_detector        = None
_rotation_controller = None
_health_monitor      = None
_input_handler       = None

def get_managers():
    global _sound_manager, _animation_manager, _npc_detector
    global _rotation_controller, _health_monitor, _input_handler
    
    if _sound_manager is None: _sound_manager = SoundManager()
    if _animation_manager is None: _animation_manager = AnimationManager()
    if _npc_detector is None: _npc_detector = NPCDetector()
    if _rotation_controller is None: _rotation_controller = RotationController()
    if _health_monitor is None: _health_monitor = HealthMonitor()
    if _input_handler is None: _input_handler = InputHandler()
    
    return (_sound_manager, _animation_manager, _npc_detector,
            _rotation_controller, _health_monitor, _input_handler)

# =============================================================================
# MAIN FUNCTION
# =============================================================================

def main():
    controller = bge.logic.getCurrentController()
    owner      = controller.owner
    
    # CENTRALIZED: SINGLE getRealTime() call PER FRAME
    current_time = bge.logic.getRealTime()
    
    # Singleton managers
    sound_mgr, anim_mgr, npc_det, rot_ctrl, health_mon, input_hdl = get_managers()
    
    # Single initialization of owner properties
    if 'props_initialized' not in owner:
        input_hdl._init_owner_properties(owner)
        owner['props_initialized'] = True
    
    # Object cache (throttled)
    cache = get_cache()
    cache.update(current_time)
    
    # Initialize spray manager only once
    global _initialized
    if cache.scene and not _initialized:
        initialize_managers(cache.scene)
        _initialized = True
    
    # Critical cached references
    rig_object      = cache.rig_object
    spray_mgr       = get_spray_manager()
    
    # spray_available obtained exclusively from game_access.get_state()
    try:
        state = get_state()
        spray_available = state.spray_total > 0 if state else True
    except:
        spray_available = True
    
    # Basic state
    on_dialog = owner['on_dialog']
    
    # =======================================================================
    # SHADOW FOLLOWING — OPTIMIZED VERSION
    # =======================================================================
    player_shadow = cache.player_shadow
    if player_shadow and not on_dialog:
        # Position in a single list assignment (avoids .copy() + 3 writes)
        px, py, pz = owner.worldPosition
        player_shadow.worldPosition = [px + 0.05, py - 0.0, pz - 0.6]
        
        # Scale control based on turning
        is_turning = owner['rotating_left'] or owner['rotating_right']
        
        # update_shadow_scale now has internal threshold: only writes if changed
        owner['shadow_scale_current'] = update_shadow_scale(
            player_shadow,
            is_turning,
            owner.get('shadow_scale_current', SHADOW_SCALE_NORMAL)
        )
        owner['was_turning'] = is_turning
    
    # =======================================================================
    # DIALOG MODE (early return)
    # =======================================================================
    if on_dialog:
        owner.worldLinearVelocity  = [0, 0, 0]
        owner.worldAngularVelocity = [0, 0, 0]
        owner['player_walking']    = False

        # Detect transition into dialog mode: reset state and invalidate
        # AnimationManager so the rig always re-launches the correct action.
        if not owner.get('last_dialog_state', False):
            anim_mgr.invalidate()
            owner['dialog_rotation_done'] = False

        if not owner['dialog_rotation_done']:
            npc = npc_det.find(controller, current_time, owner)
            if npc:
                if rot_ctrl.rotate_towards(owner, npc, DIALOG_ROTATION_SPEED, current_time):
                    owner['dialog_rotation_done'] = True
            else:
                owner['dialog_rotation_done'] = True
        
        sound_mgr.stop_all(['footsteps-on-tiled-floor.ogg', 'spray.ogg', 'spray_wrong.ogg'])
        owner['spray_sound_playing'] = False
        
        if rig_object:
            if owner['player_talking']:
                anim_mgr.play(rig_object, 'Player.Talking', 1, 29, True, 1.0, layer=0)
                sound_mgr.play('blaba_bruno_curator.ogg', True, 1.0)
            else:
                spray_mgr.set_visibility(False)
                anim_mgr.play(rig_object, 'Player.Idle', 1, 13, True, 1.0, layer=0)
                sound_mgr.stop('blaba_bruno_curator.ogg')
        
        owner['last_dialog_state'] = True
        return
    
    # =======================================================================
    # MOVEMENT MODE
    # =======================================================================
    owner['last_dialog_state'] = False
    input_hdl.update(owner, controller, False, current_time)
    health_mon.check(owner, rig_object, anim_mgr, current_time)
    
    # === STAMINA SYSTEM ===
    update_stamina_system(owner, current_time)
    effective_speed = get_effective_speed()
    
    # Movement states as local variables (avoids multiple dict reads)
    moving_forward    = owner['moving_forward']
    moving_backward   = owner['moving_backward']
    rotating_left     = owner['rotating_left']
    rotating_right    = owner['rotating_right']
    obstacle_blocking = owner['obstacle_blocking']
    player_stuck      = owner['player_stuck']
    attacking         = owner['attacking']
    
    owner['player_attacking'] = attacking
    
    # Movement logic
    is_walking = False
    
    if obstacle_blocking:
        moving_forward         = False
        owner['moving_forward'] = False
        
        if moving_backward:
            owner.applyMovement([0, -effective_speed / 2, 0], True)
            is_walking = True
            if player_stuck:
                owner['player_stuck'] = False
        
        if player_stuck:
            is_walking = False
    else:
        if moving_forward:
            owner.applyMovement([0, effective_speed, 0], True)
            is_walking = True
        
        if moving_backward:
            owner.applyMovement([0, -effective_speed / 2, 0], True)
            is_walking = True
    
    if rotating_left:
        owner.applyRotation([0, 0, ROTATION_SPEED], True)
        is_walking = True
    
    if rotating_right:
        owner.applyRotation([0, 0, -ROTATION_SPEED], True)
        is_walking = True
    
    # =======================================================================
    # SPRAY SOUNDS AND EFFECTS
    # =======================================================================
    current_attack = owner['player_attacking']
    last_attack    = owner['last_attack_state']
    attack_started = current_attack and not last_attack
    attack_ended   = not current_attack and last_attack
    
    # Detect if spray_particle.py notified that spray ran out
    spray_just_emptied = owner.get('_spray_just_emptied', False)
    
    if spray_just_emptied:
        debug_print("Spray depleted detected by notification")
        owner['_spray_just_emptied'] = False
    
    if attack_started:
        # Invalidate AnimationManager cache at attack start
        anim_mgr.invalidate()
        
        # At attack start, choose correct sound
        sound_file = 'spray.ogg' if spray_available else 'spray_wrong.ogg'
        sound_mgr.play(sound_file, True, 0.7)
        owner['spray_sound_playing'] = True
        owner['spray_sound_started'] = True
        owner['current_spray_sound'] = sound_file
        
        # Set initial visibility of effects
        spray_mgr.set_visibility(spray_available, effects_only=True)
        owner['effects_visible'] = spray_available
    
    elif current_attack or spray_just_emptied:
        # DURING attack, check if spray state changed
        current_sound = owner.get('current_spray_sound', 'spray.ogg')
        
        # If spray ran out
        if not spray_available:
            if current_sound == 'spray.ogg':
                sound_mgr.stop('spray.ogg')
                sound_mgr.play('spray_wrong.ogg', True, 0.7)
                owner['current_spray_sound'] = 'spray_wrong.ogg'
                debug_print("Spray depleted! Switching to error sound")
            
            if owner.get('effects_visible', True):
                spray_mgr.set_visibility(False, effects_only=True)
                owner['effects_visible'] = False
                debug_print("Visual effects deactivated")
        
        # If spray was reloaded
        elif spray_available:
            if current_sound == 'spray_wrong.ogg':
                sound_mgr.stop('spray_wrong.ogg')
                sound_mgr.play('spray.ogg', True, 0.7)
                owner['current_spray_sound'] = 'spray.ogg'
                debug_print("Spray reloaded, switching to normal sound")
            
            if not owner.get('effects_visible', False):
                spray_mgr.set_visibility(True, effects_only=True)
                owner['effects_visible'] = True
                debug_print("Visual effects activated")
    
    elif attack_ended:
        # When attack ends, stop all sounds and hide effects
        sound_mgr.stop('spray.ogg')
        sound_mgr.stop('spray_wrong.ogg')
        spray_mgr.set_visibility(False, effects_only=True)
        
        owner['spray_sound_playing'] = False
        owner['spray_sound_started'] = False
        owner['current_spray_sound'] = None
        owner['effects_visible'] = False
    
    owner['last_attack_state'] = current_attack
    
    # =======================================================================
    # ANIMATIONS
    # =======================================================================
    if rig_object:
        animation = ""
        speed     = 1.0
        frames    = (1, 13)
        blendin   = ANIMATION_BLENDIN
        
        if owner['player_attacking']:
            if is_walking and not player_stuck:
                animation = 'Player.Attack.Walking'
                speed     = 3.5
            else:
                animation = 'Player.Attack'
                speed     = 1.0
            frames = (1, 13)
            
            can_object = cache.get('charA_can')
            if can_object:
                can_object.visible = True
            
            sound_mgr.stop('footsteps-on-tiled-floor.ogg')
        
        elif is_walking and not player_stuck:
            animation = 'Player.Walk'
            speed     = 3.5
            frames    = (1, 29)
            spray_mgr.set_visibility(False)
            
            if (moving_forward or moving_backward) and not obstacle_blocking:
                sound_mgr.play('footsteps-on-tiled-floor.ogg', True, 0.8)
            else:
                sound_mgr.stop('footsteps-on-tiled-floor.ogg')
            
            owner['prev_animation'] = animation
        
        else:
            # Walk->Idle transition uses blendin=4 for smoother transition
            prev_anim = owner.get('prev_animation')
            if prev_anim == 'Player.Walk':
                blendin = 4
            
            animation = 'Player.Idle'
            frames    = (1, 13)
            spray_mgr.set_visibility(False)
            sound_mgr.stop('footsteps-on-tiled-floor.ogg')
            
            owner['prev_animation'] = animation
        
        # Use anim_mgr.play() so AnimationManager state always reflects
        # what the rig is actually playing (fixes dialog Idle guard bug).
        anim_mgr.play(
            rig_object, animation, frames[0], frames[1],
            loop=True, speed=speed, layer=0, blendin=blendin
        )
    
    # =======================================================================
    # PHYSICS
    # =======================================================================
    if not (moving_forward or moving_backward):
        owner.worldLinearVelocity = [0, 0, 0]
    
    if not (rotating_left or rotating_right):
        owner.worldAngularVelocity = [0, 0, 0]
    
    # =======================================================================
    # FINAL STATES
    # =======================================================================
    if player_stuck or (obstacle_blocking and not moving_backward):
        owner['player_walking'] = False
    else:
        owner['player_walking'] = is_walking
    
    owner['player_idle'] = not owner['player_walking'] and not owner['player_attacking']