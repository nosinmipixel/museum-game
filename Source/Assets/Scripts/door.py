"""
door.py

Manages door opening/closing with animation, player proximity detection, and climate effects.

This script handles door interaction through mouse click or keyboard (E key),
with real-time player side detection, smooth rotation animations, and material
highlighting on mouse hover.

Main Features:
    1. Dual interaction methods (mouse click + E key)
    2. Real-time player side detection using Ray sensors
    3. Smooth rotation animation with configurable speed
    4. Material highlighting on mouse hover
    5. Climate effects tracking (door opening counter)
    6. Shadow displacement during door opening
    7. Cooldown system for stable proximity detection
    8. Message display for climate warnings

Setup:
    Connect to Logic Bricks as Python controller with module 'door.main'
    Required sensors: Near, RayFront, RayBack, Keyboard.E (optional)
    Required child objects: Door.Collision.L, Door.Collision.R, Door.Shadow

Configurable Variables:
    DEBUG (bool): Enable debug logging (default: False)
    MATERIAL_NORMAL (str): Normal material name (default: 'Door.Black')
    MATERIAL_HIGHLIGHT (str): Highlight material name (default: 'Door.White')
    MATERIAL_SLOT (int): Material slot index (default: 0)
    ANIMATION_SPEED (float): Rotation speed per frame (default: 0.06)
    ROTATION_THRESHOLD (float): Threshold to consider animation complete (default: 0.02)
    SHADOW_DISPLACEMENT (tuple): XYZ offset for shadow when door opens (default: (0, -500, 0))

Notes:
    - Door opens away from or towards player based on current side
    - Requires unique material copies per door to avoid shared material issues
    - Climate effects tracked when door_climate property is True
    - Uses game_access for game state management
    - E key detection works with or without Keyboard.E sensor (API fallback)
    - Ray sensors detect player position relative to door front/back

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
__description__ = "Manages door opening/closing with animation and proximity detection"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
import bpy
from bge import logic as gl
from bge import events
import math

# =============================================================================
# DEBUG CONFIGURATION
# =============================================================================
DEBUG = False

# Import game_access
try:
    import game_access
    HAS_GAME_ACCESS = True
except ImportError as e:
    HAS_GAME_ACCESS = False

def debug_print(*args, **kwargs):
    if DEBUG:
        print(*args, **kwargs)

# =============================================================================
# CONFIGURATION
# =============================================================================
MATERIAL_NORMAL = "Door.Black"
MATERIAL_HIGHLIGHT = "Door.White"
MATERIAL_SLOT = 0
ANIMATION_SPEED = 0.06
ROTATION_THRESHOLD = 0.02
SHADOW_DISPLACEMENT = (0, -500, 0)

# Direction configuration
DOOR_OPEN_DIRECTION = {
    'away_from_player': {
        'left': -math.pi / 2,
        'right': math.pi / 2
    },
    'towards_player': {
        'left': math.pi / 2,
        'right': -math.pi / 2
    }
}

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def _get_door_parts(own):
    """Gets door parts"""
    door_main = own
    collision_l = None
    collision_r = None
    door_shadow = None
    
    for child in door_main.children:
        if 'Door.Collision.L' in child.name:
            collision_l = child
        elif 'Door.Collision.R' in child.name:
            collision_r = child
        elif 'Door.Shadow' in child.name:
            door_shadow = child
    
    return door_main, collision_l, collision_r, door_shadow

def _make_material_unique(obj):
    """Creates a unique copy of mesh data"""
    if not obj:
        return
        
    try:
        b_obj = obj.blenderObject
        if hasattr(b_obj, 'data') and b_obj.data and b_obj.data.users > 1:
            new_mesh = b_obj.data.copy()
            b_obj.data = new_mesh
    except Exception as e:
        pass

def _apply_material_to_collision_objects(collision_l, collision_r, material_name):
    """Applies material using bpy"""
    success = True
    
    for coll_obj in [collision_l, collision_r]:
        if coll_obj:
            try:
                mat = bpy.data.materials.get(material_name)
                if mat is None:
                    success = False
                    continue

                blender_obj = coll_obj.blenderObject
                
                if blender_obj.data.materials:
                    if MATERIAL_SLOT < len(blender_obj.data.materials):
                        blender_obj.data.materials[MATERIAL_SLOT] = mat
                    else:
                        blender_obj.data.materials.append(mat)
                else:
                    blender_obj.data.materials.append(mat)
                    
            except Exception as e:
                success = False
    
    return success

def _is_mouse_over_door(cont, valid_objects):
    """Checks if mouse is over the door"""
    scene = gl.getCurrentScene()
    cam = scene.active_camera
    if not cam:
        return False

    try:
        mouse_pos = gl.mouse.position
        hit_obj = cam.getScreenRay(mouse_pos[0], mouse_pos[1], 1000.0, "")
        
        if hit_obj:
            if hit_obj in valid_objects:
                return True
            
            try:
                parent = hit_obj.parent
                while parent:
                    if parent in valid_objects:
                        return True
                    parent = parent.parent
            except:
                pass
        
        return False
        
    except Exception as e:
        return False

# =============================================================================
# DOOR CONTROLLER CLASS
# =============================================================================
class DoorController:
    def __init__(self, owner):
        self.owner = owner
        self.scene = gl.getCurrentScene()
        
        # Get references
        self.door_main, self.collision_l, self.collision_r, self.door_shadow = _get_door_parts(owner)
        
        # Make materials unique
        _make_material_unique(self.collision_l)
        _make_material_unique(self.collision_r)
        
        # Save original shadow position
        self.shadow_original_position = None
        if self.door_shadow:
            self.shadow_original_position = self.door_shadow.localPosition.copy()
        
        # States
        self.is_open = False
        self.is_animating = False
        self.mouse_over = False
        self.animation_frame = 0
        self.player_near = False
        
        # State for Ray sensors
        self.player_at_front = False
        self.player_at_back = False
        self.player_side = 'unknown'
        
        # COOLDOWN CONTROL
        self.near_cooldown_counter = 0
        self.near_cooldown_frames = 10
        self.stable_player_near = False
        self.pending_near_state = None
        
        # Material variables
        self._was_mouse_over = False
        self._highlight_active = False
        
        # Previous E key state for edge detection
        self._e_key_prev = False
        
        # Properties
        self.door_climate = owner.get('door_climate', False)
        
        # Game Access
        self.game = None
        self.game_controller = self.scene.objects.get('Game.Controller')
        if HAS_GAME_ACCESS:
            try:
                self.game = game_access.get_game()
            except: pass
        
        # Messages
        self.message_timer = 0
        self.showing_message = False
        
        # Initialize visual state
        _apply_material_to_collision_objects(self.collision_l, self.collision_r, MATERIAL_NORMAL)
        self._reset_to_closed_position()
        
        # Initialize shadow
        if self.door_shadow and self.shadow_original_position:
            self.door_shadow.localPosition = self.shadow_original_position.copy()
        
        # Cache valid objects
        self.valid_collision_objects = []
        if self.collision_l: self.valid_collision_objects.append(self.collision_l)
        if self.collision_r: self.valid_collision_objects.append(self.collision_r)
        
        # Find player
        self.player = self.scene.objects.get('Player')
        if not self.player:
            for obj in self.scene.objects:
                if 'player' in obj.getPropertyNames():
                    self.player = obj
                    debug_print(f"Player found: {obj.name}")
                    break

    def _reset_to_closed_position(self):
        """Resets doors to closed position"""
        if self.collision_l:
            rot = self.collision_l.localOrientation.to_euler()
            rot.z = 0
            self.collision_l.localOrientation = rot.to_matrix()
        if self.collision_r:
            rot = self.collision_r.localOrientation.to_euler()
            rot.z = 0
            self.collision_r.localOrientation = rot.to_matrix()
    
    def _handle_mouse_over_materials(self, cont):
        """Handles highlights based on mouse position"""
        if not self.stable_player_near:
            if self._highlight_active:
                _apply_material_to_collision_objects(self.collision_l, self.collision_r, MATERIAL_NORMAL)
                self._highlight_active = False
                self._was_mouse_over = False
            return

        current_mouse_over = _is_mouse_over_door(cont, self.valid_collision_objects)
        
        if current_mouse_over and not self._was_mouse_over:
            self.mouse_over = True
            if _apply_material_to_collision_objects(self.collision_l, self.collision_r, MATERIAL_HIGHLIGHT):
                self._highlight_active = True
        
        elif not current_mouse_over and self._was_mouse_over:
            self.mouse_over = False
            if _apply_material_to_collision_objects(self.collision_l, self.collision_r, MATERIAL_NORMAL):
                self._highlight_active = False
        
        self._was_mouse_over = current_mouse_over
    
    def handle_near_sensor(self, cont):
        """Handles Near sensor with cooldown"""
        near_sensor = cont.sensors.get('Near')
        if not near_sensor:
            return
        
        if near_sensor.positive != self.player_near:
            self.pending_near_state = near_sensor.positive
            self.near_cooldown_counter = self.near_cooldown_frames
        
        self.player_near = near_sensor.positive
        
        if self.near_cooldown_counter > 0:
            self.near_cooldown_counter -= 1
            
            if self.near_cooldown_counter <= 0 and self.pending_near_state is not None:
                old_stable = self.stable_player_near
                self.stable_player_near = self.pending_near_state
                
                if old_stable != self.stable_player_near:
                    if self.stable_player_near:
                        debug_print(f"Player NEAR (stable) {self.owner.name}")
                    else:
                        debug_print(f"Player FAR (stable) {self.owner.name}")
                        self.player_at_front = False
                        self.player_at_back = False
                        self.player_side = 'unknown'
                
                self.pending_near_state = None
    
    def handle_ray_sensors(self, cont):
        """
        Handles two Ray sensors and updates player_side EVERY FRAME.
        """
        if not self.stable_player_near or not self.player:
            return
        
        ray_front = cont.sensors.get('RayFront')
        ray_back = cont.sensors.get('RayBack')
        
        front_detected = ray_front and ray_front.positive and ray_front.hitObject
        back_detected = ray_back and ray_back.positive and ray_back.hitObject
        
        old_side = self.player_side
        
        if front_detected and not back_detected:
            self.player_side = 'front'
            self.player_at_front = True
            self.player_at_back = False
        elif back_detected and not front_detected:
            self.player_side = 'back'
            self.player_at_front = False
            self.player_at_back = True
        elif front_detected and back_detected:
            self.player_side = 'front'
            self.player_at_front = True
            self.player_at_back = True
        else:
            self.player_side = self._determine_side_by_position()
            self.player_at_front = False
            self.player_at_back = False
        
        if old_side != self.player_side:
            debug_print(f"Current side: {self.player_side.upper()}")
    
    def _determine_side_by_position(self):
        """Determines side by player position when rays don't detect."""
        try:
            if not self.player or not self.door_main:
                return 'unknown'
            
            door_pos = self.door_main.worldPosition
            player_pos = self.player.worldPosition
            to_player = player_pos - door_pos
            door_forward = self.door_main.getAxisVect([0, 1, 0])
            
            if to_player.length_squared > 0:
                to_player.normalize()
            if door_forward.length_squared > 0:
                door_forward.normalize()
            
            dot = to_player.dot(door_forward)
            
            if dot > 0.2:
                return 'front'
            elif dot < -0.2:
                return 'back'
            else:
                return 'unknown'
                
        except Exception as e:
            return 'unknown'
    
    def _get_current_side(self):
        """Returns CURRENT player side."""
        if self.player_side != 'unknown':
            return self.player_side
        
        side = self._determine_side_by_position()
        if side != 'unknown':
            return side
        
        return 'front'
    
    def _determine_open_direction(self):
        """Determines opening direction based on CURRENT position."""
        side = self._get_current_side()
        
        if side == 'front':
            return 'away_from_player'
        elif side == 'back':
            return 'towards_player'
        else:
            return 'away_from_player'
    
    # -------------------------------------------------------------------------
    # MODIFIED METHOD: handle_interaction
    #   • Mouse click -> requires mouse_over + proximity (Near)
    #   • E key      -> requires only proximity (Near)
    #   E key detection uses 'Keyboard.E' sensor (logic bricks) with edge detection,
    #   or keyboard API (.activated) as fallback.
    # -------------------------------------------------------------------------
    def handle_interaction(self, cont):
        """Interaction with CURRENT side detection.
        
        Left click: opens/closes if cursor is over door and player is near.
        E key:      opens/closes if player is near (no mouse aiming required).
        """
        # Global locks
        if getattr(gl, "hud_pause_open", False) or \
           getattr(gl, "hud_inventory_open", False) or \
           getattr(gl, "hud_inventory_v2_open", False):
            return
        
        # Do not interact while animating or player not near
        if self.is_animating or not self.stable_player_near:
            return

        mouse = gl.mouse
        keyboard = gl.keyboard
        
        # -- Mouse click (requires mouse_over) --
        left_mouse = mouse.inputs.get(events.LEFTMOUSE)
        mouse_click = left_mouse and left_mouse.activated
        
        # -- E key (requires only proximity) --
        e_key_pressed = False
        
        # 1) Logic bricks 'Keyboard.E' sensor with edge detection
        e_sensor = cont.sensors.get('Keyboard.E')
        if e_sensor:
            e_current = e_sensor.positive
            if e_current and not self._e_key_prev:
                e_key_pressed = True
            self._e_key_prev = e_current
        else:
            # 2) Fallback: keyboard API (.activated = single press)
            e_key = keyboard.inputs.get(events.EKEY)
            if e_key and e_key.activated:
                e_key_pressed = True
            # Keep flag coherent when no sensor
            self._e_key_prev = bool(
                e_key and (bge.logic.KX_INPUT_ACTIVE in e_key.status
                           or bge.logic.KX_INPUT_JUST_ACTIVATED in e_key.status)
            ) if e_key else False
        
        # -- Decide whether to interact --
        interact = False
        if mouse_click and self.mouse_over:      # Click requires mouse_over
            interact = True
        if e_key_pressed:                         # E key only proximity
            interact = True
        
        if interact:
            direction = self._determine_open_direction()
            side_used = self._get_current_side()
            
            self.current_open_direction = direction
            debug_print(f"Interaction: {direction} (CURRENT side: {side_used})")
            self.toggle_door()
    
    def toggle_door(self):
        if self.is_animating: return
        if self.is_open:
            self.close_door()
        else:
            self.open_door()
    
    def open_door(self):
        self.is_animating = True
        self.animation_frame = 0
        debug_print(f"OPENING ({self.current_open_direction})")
        try:
            bge.logic.sendMessage("sound_fx.play", "sound_fx.play|door_opened.ogg|volume=1.0")
        except: pass
        if self.door_climate:
            self.handle_climate_effects(True)
        
        if self.door_shadow:
            current_pos = self.door_shadow.localPosition
            displaced_pos = (current_pos[0] + SHADOW_DISPLACEMENT[0],
                           current_pos[1] + SHADOW_DISPLACEMENT[1],
                           current_pos[2] + SHADOW_DISPLACEMENT[2])
            self.door_shadow.localPosition = displaced_pos
    
    def close_door(self):
        self.is_animating = True
        self.animation_frame = 0
        debug_print("CLOSING")
        try:
            bge.logic.sendMessage("sound_fx.play", "sound_fx.play|door_closed.ogg|volume=1.0")
        except: pass
        if self.door_climate:
            self.handle_climate_effects(False)
        
        if self.door_shadow and self.shadow_original_position:
            self.door_shadow.localPosition = self.shadow_original_position.copy()
    
    def update_animation(self):
        if not self.is_animating: return
        
        animation_complete = True
        direction = self.current_open_direction if not self.is_open else 'away_from_player'
        
        if not self.is_open:  # Opening
            target_l = DOOR_OPEN_DIRECTION[direction]['left']
            target_r = DOOR_OPEN_DIRECTION[direction]['right']
        else:  # Closing
            target_l = 0
            target_r = 0
        
        if self.collision_l:
            curr = self.collision_l.localOrientation.to_euler().z
            diff = target_l - curr
            if abs(diff) > ROTATION_THRESHOLD:
                animation_complete = False
                speed = ANIMATION_SPEED if abs(diff) > ANIMATION_SPEED * 2 else abs(diff) / 2
                self.collision_l.applyRotation((0, 0, speed if diff > 0 else -speed), True)
        
        if self.collision_r:
            curr = self.collision_r.localOrientation.to_euler().z
            diff = target_r - curr
            if abs(diff) > ROTATION_THRESHOLD:
                animation_complete = False
                speed = ANIMATION_SPEED if abs(diff) > ANIMATION_SPEED * 2 else abs(diff) / 2
                self.collision_r.applyRotation((0, 0, speed if diff > 0 else -speed), True)
        
        self.animation_frame += 1
        
        if animation_complete:
            self.finish_animation()
    
    def finish_animation(self):
        self.is_open = not self.is_open
        self._set_exact_rotations()
        self.is_animating = False
        debug_print(f"DOOR {'OPEN' if self.is_open else 'CLOSED'}")
        
        if self.door_climate:
            if self.is_open:
                self.showing_message = True
                self.message_timer = 180
            else:
                self.clear_info_message()
    
    def _set_exact_rotations(self):
        """Sets exact rotations"""
        if not self.is_open:
            if self.collision_l:
                rot = self.collision_l.localOrientation.to_euler()
                rot.z = 0
                self.collision_l.localOrientation = rot.to_matrix()
            if self.collision_r:
                rot = self.collision_r.localOrientation.to_euler()
                rot.z = 0
                self.collision_r.localOrientation = rot.to_matrix()
        else:
            direction = self.current_open_direction
            if self.collision_l:
                rot = self.collision_l.localOrientation.to_euler()
                rot.z = DOOR_OPEN_DIRECTION[direction]['left']
                self.collision_l.localOrientation = rot.to_matrix()
            if self.collision_r:
                rot = self.collision_r.localOrientation.to_euler()
                rot.z = DOOR_OPEN_DIRECTION[direction]['right']
                self.collision_r.localOrientation = rot.to_matrix()
    
    def update_message_timer(self):
        if self.message_timer > 0:
            self.message_timer -= 1
            if self.message_timer <= 0 and self.showing_message:
                self.clear_info_message()
    
    def handle_climate_effects(self, opening):
        if not self.game:
            if HAS_GAME_ACCESS:
                try: self.game = game_access.get_game()
                except: return
            else: return
        try:
            if opening:
                if not hasattr(self.game.state, 'doors_opened'):
                    self.game.state.doors_opened = 0
                self.game.state.doors_opened += 1
                self.show_info_message()
            else:
                if hasattr(self.game.state, 'doors_opened') and self.game.state.doors_opened > 0:
                    self.game.state.doors_opened -= 1
                self.clear_info_message()
        except Exception as e:
            pass
    
    def show_info_message(self):
        try:
            if self.game_controller:
                self.game_controller.sendMessage('add_info_text', 'info.show|info_text|1|field=info_text')
        except: pass
    
    def clear_info_message(self):
        try:
            if self.game_controller:
                self.game_controller.sendMessage('add_info_text', 'info.clear|field=info_text')
                self.showing_message = False
                self.message_timer = 0
        except: pass
    
    def update(self, cont):
        try:
            # 1. Near sensor
            self.handle_near_sensor(cont)
            
            # 2. Ray sensors (UPDATE player_side EVERY FRAME)
            self.handle_ray_sensors(cont)
            
            # 3. Materials and Mouse
            self._handle_mouse_over_materials(cont)
            
            # 4. Interaction
            self.handle_interaction(cont)
            
            # 5. Animation
            self.update_animation()
            self.update_message_timer()
            
        except Exception as e:
            debug_print(f"Update error: {e}")

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main(cont):
    owner = cont.owner
    
    if 'door_controller' not in owner:
        owner['door_controller'] = DoorController(owner)
    
    try:
        owner['door_controller'].update(cont)
    except Exception as e:
        debug_print(f"Main error: {e}")