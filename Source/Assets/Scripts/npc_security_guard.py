"""
npc_security_guard.py

Dialog control for Security Guard NPC (NPC13)

This script manages dialog interactions with the Security Guard NPC, including
proximity detection, mouse input handling, random scene selection, animations,
sound effects, cooldown system, and rotation toward player.

Main Features:
    1. Proximity-based dialog activation with mouse click
    2. Random scene selection from available scenes (scene105, scene106)
    3. Multi-step dialog flow with NPC and player dialogue lines
    4. Mouse-over visual feedback with material switching
    5. Character animations (Talking, Idle) with skeleton rig
    6. Voice sound playback during NPC dialogue
    7. Cooldown system (60 seconds) between conversations
    8. Rotation toward player when player is in animation range
    9. Post-dialog idle animation while player remains nearby

Setup:
    Connect in Logic Bricks as Python controller/module 'npc_security_guard.main'
    NPC object requires sensors:
        - Near_Anim (proximity for animation activation and rotation)
        - Near_Dialog (proximity for dialog activation)
        - Mouse.Over (for hover detection)
        - Mouse.Click (for click detection)

Configurable Variables:
    DEBUG (bool): Enable debug messages (default: False)
    DEBUG_LEVEL (int): 1=info, 2=detailed, 3=very detailed (default: 1)
    COOLDOWN_TIME (float): Seconds between conversations (default: 60.0)
    ROTATION_SPEED (float): Rotation speed in radians per second (default: 2.0)
    ROTATION_TOLERANCE (float): Tolerance for rotation completion (default: 0.05)

Notes:
    - Requires game_access module for game state management
    - Dialog text loaded from JSON files: dialogs_{lang}.json
    - Sound files expected in //Assets/Sounds/npc13.ogg
    - Rig structure: npc13 > security_guard_metarig > security_guard_object
    - Uses aud module for audio playback

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
__description__ = "Security Guard NPC dialog system with rotation toward player"

# =============================================================================
# IMPORTS AND CONFIGURATION
# =============================================================================
import bge
from bge import logic
import time
import random
import aud
import math

DEBUG = False
DEBUG_LEVEL = 1  # 1=info, 2=detailed, 3=very detailed
SCENES = ["scene105", "scene106"]  # Possible scenes

# Object names
PLAYER_NAME = "Player"
RIG_NAME = "security_guard_metarig"
MESH_NAME = "security_guard_object"  # Mesh child of rig
GAME_CONTROLLER_NAME = "Game.Controller"

# Material names for highlighting
MATERIAL_HIGHLIGHT = "White_Backface_Culling"
MATERIAL_NORMAL = "Black_Backface_Culling"

# Animation names
ANIM_TALKING = "Talking"
ANIM_IDLE = "Idle"

# Wait duration after dialog (seconds)
POST_DIALOG_DELAY = 3.0
# Cooldown time between conversations (1 minute = 60 seconds)
COOLDOWN_TIME = 60.0

# Rotation configuration
ROTATION_SPEED = 2.0  # Rotation speed (radians per second)
ROTATION_TOLERANCE = 0.05  # Tolerance to consider already rotated

# =============================================================================
# LOGGING SYSTEM
# =============================================================================
def debug_log(level, *args):
    """Logging system controlled by level"""
    if DEBUG and level <= DEBUG_LEVEL:
        print(f"[NPC13-L{level}]", *args)


# =============================================================================
# MAIN SECURITY GUARD DIALOG SYSTEM CLASS
# =============================================================================
class SecurityGuardDialogSystem:
    def __init__(self, owner):
        self.owner = owner
        self.npc_id = 13
        
        # States
        self.current_state = "IDLE"  # IDLE, NEAR_PLAYER, DIALOG_ACTIVE, DIALOG_ENDING, COOLDOWN, COOLDOWN_NEAR_PLAYER
        self.dialog_step = 0
        
        # Proximity and mouse control
        self.player_in_anim_range = False
        self.player_in_dialog_range = False
        self.mouse_over = False
        self.mouse_clicked = False
        self.mouse_over_active = False  # For material change control
        self.was_mouse_over = False     # Previous mouse over state
        
        # Cooldown system
        self.cooldown_end_time = 0
        self.in_cooldown = False
        
        # Cache
        self.cached_player = None
        self.rig_object = None
        self.mesh_object = None  # Mesh for material change
        self.game_controller = None
        
        # Animation control
        self.current_animation = None
        
        # Text cleanup system
        self.cleaning_previous = False
        self.text_to_clean = ""
        
        # Sound system
        self.sound_device = None
        self.sound_talking = None
        self.sound_handle = None
        
        # Post-dialog timer
        self.dialog_end_time = 0
        self.waiting_for_animation = False
        
        # Random scene
        self.current_scene = None
        
        # Rotation control
        self.is_rotating = False
        
        # Initialize
        self.setup_references()
        self.setup_sound_system()
        self.select_random_scene()
        self.setup_properties()
        
        debug_log(1, f"NPC13 initialized - Scene: {self.current_scene}")
    
    def setup_references(self):
        """Get references to important objects"""
        try:
            scene = logic.getCurrentScene()
            self.cached_player = scene.objects.get(PLAYER_NAME)
            self.game_controller = scene.objects.get(GAME_CONTROLLER_NAME)
            
            # Find rig and mesh (structure: npc13 > security_guard_metarig > security_guard_object)
            for child in self.owner.children:
                if child.name == RIG_NAME:
                    self.rig_object = child
                    debug_log(2, f"Rig found: {child.name}")
                    
                    # Find mesh child of rig
                    for subchild in child.children:
                        if subchild.name == MESH_NAME:
                            self.mesh_object = subchild
                            debug_log(2, f"Mesh found: {subchild.name}")
                            break
                    break
                    
        except Exception as e:
            debug_log(1, f"Error getting references: {e}")
    
    def get_mesh_child(self):
        """Get mesh child object"""
        return self.mesh_object
    
    def change_mesh_material(self, material_name):
        """Change material on mesh"""
        mesh = self.get_mesh_child()
        if not mesh:
            return False
        
        try:
            import bpy
            mat = bpy.data.materials.get(material_name)
            if mat is None:
                return False

            materials_list = mesh.blenderObject.data.materials
            while len(materials_list) < 2:
                materials_list.append(None)
            
            if len(materials_list) > 1:
                materials_list[1] = mat
                return True
            else:
                return False
                
        except Exception as e:
            debug_log(1, f"Error changing material: {e}")
            return False
    
    def rotate_towards_player(self):
        """Rotate NPC toward player"""
        if not self.cached_player or not self.rig_object:
            return
        
        try:
            # Get positions
            npc_pos = self.rig_object.worldPosition
            player_pos = self.cached_player.worldPosition
            
            # Calculate direction to player (only in XZ plane)
            direction = player_pos - npc_pos
            direction.z = 0  # Ignore height difference
            
            if direction.length_squared > 0.001:  # Avoid division by zero
                direction.normalize()
                
                # Calculate target angle (in radians)
                # In Blender, Y axis is forward by default
                target_angle = math.atan2(-direction.x, direction.y)
                
                # Get current rig rotation
                current_rotation = self.rig_object.worldOrientation.to_euler()
                current_angle = current_rotation.z
                
                # Calculate angle difference (minimum)
                angle_diff = target_angle - current_angle
                
                # Normalize angle to [-pi, pi]
                while angle_diff > math.pi:
                    angle_diff -= 2 * math.pi
                while angle_diff < -math.pi:
                    angle_diff += 2 * math.pi
                
                # If already close to target angle
                if abs(angle_diff) < ROTATION_TOLERANCE:
                    self.is_rotating = False
                    return
                
                # Apply smooth rotation
                self.is_rotating = True
                rotation_step = ROTATION_SPEED * logic.getClockTime()
                
                if abs(angle_diff) < rotation_step:
                    # Rotate directly to target angle
                    new_angle = target_angle
                else:
                    # Rotate in correct direction
                    new_angle = current_angle + (rotation_step if angle_diff > 0 else -rotation_step)
                
                # Apply new rotation
                self.rig_object.worldOrientation = [0, 0, new_angle]
                
                debug_log(3, f"Rotating: diff={angle_diff:.3f}, new_angle={new_angle:.3f}")
                
        except Exception as e:
            debug_log(1, f"Rotation error: {e}")
            self.is_rotating = False
    
    def handle_mouse_over(self):
        """Handle mouse over/out events"""
        # If in cooldown, do not show mouse over effect
        if self.in_cooldown:
            if self.mouse_over_active or self.was_mouse_over:
                # Ensure material returns to normal during cooldown
                self.change_mesh_material(MATERIAL_NORMAL)
                self.mouse_over_active = False
                self.was_mouse_over = False
            return
        
        # Only process if player is in dialog range (to avoid changes at distance)
        if not self.player_in_dialog_range:
            if self.mouse_over_active or self.was_mouse_over:
                # Restore normal material if player is far
                self.change_mesh_material(MATERIAL_NORMAL)
                self.mouse_over_active = False
                self.was_mouse_over = False
            return
        
        # Detect mouse over transitions
        if self.mouse_over and not self.was_mouse_over:
            # Mouse entered NPC
            if self.change_mesh_material(MATERIAL_HIGHLIGHT):
                self.mouse_over_active = True
                self.was_mouse_over = True
                debug_log(3, "Mouse Over - Material highlight")
        
        elif not self.mouse_over and self.was_mouse_over:
            # Mouse exited NPC
            if self.change_mesh_material(MATERIAL_NORMAL):
                self.mouse_over_active = False
                self.was_mouse_over = False
                debug_log(3, "Mouse Out - Material normal")
    
    def setup_sound_system(self):
        """Initialize sound system"""
        try:
            self.sound_device = aud.Device()
            
            def _load_sound(rel_path):
                if not rel_path.startswith("//"):
                    rel_path = "//" + rel_path
                return aud.Sound(bge.logic.expandPath(rel_path))
            
            sound_path = f"Assets/Sounds/npc{self.npc_id}.ogg"
            self.sound_talking = _load_sound(sound_path)
            debug_log(2, "Sound system initialized")
            
        except Exception as e:
            debug_log(1, f"Error initializing sound: {e}")
    
    def play_talking_sound(self):
        """Play NPC talking sound"""
        try:
            if self.sound_device and self.sound_talking:
                if self.sound_handle and self.sound_handle.status:
                    self.sound_handle.stop()
                
                self.sound_handle = self.sound_device.play(self.sound_talking)
                if self.sound_handle:
                    try: 
                        self.sound_handle.loop_count = -1
                        self.sound_handle.volume = 1.0
                    except: 
                        pass
        except Exception as e:
            debug_log(1, f"Error playing sound: {e}")
    
    def stop_talking_sound(self):
        """Stop NPC talking sound"""
        try:
            if self.sound_handle and self.sound_handle.status:
                self.sound_handle.stop()
                self.sound_handle = None
        except Exception as e:
            debug_log(1, f"Error stopping sound: {e}")
    
    def select_random_scene(self):
        """Select random scene"""
        self.current_scene = random.choice(SCENES)
        self.owner["current_scene"] = self.current_scene
        debug_log(2, f"Scene selected: {self.current_scene}")
    
    def setup_properties(self):
        """Initialize NPC properties"""
        self.owner["npc_id"] = self.npc_id
        self.owner["npc"] = True
        self.owner["npc_talking"] = False
        self.owner["current_scene"] = self.current_scene
        self.owner["in_cooldown"] = False  # Property visible in Blender
    
    # =========================================================================
    # ANIMATIONS
    # =========================================================================
    
    def play_animation(self, animation_name, loop=True):
        """Play animation (avoid repetitions)"""
        if not self.rig_object:
            return
        
        if self.current_animation == animation_name:
            return
        
        try:
            if animation_name == ANIM_TALKING:
                start, end = 1, 13
            elif animation_name == ANIM_IDLE:
                start, end = 1, 13
            else:
                return
            
            play_mode = bge.logic.KX_ACTION_MODE_LOOP if loop else bge.logic.KX_ACTION_MODE_PLAY
            
            self.rig_object.playAction(
                animation_name, start, end,
                layer=0, priority=1, blendin=5,
                play_mode=play_mode, speed=1.0
            )
            
            self.current_animation = animation_name
            debug_log(3, f"Animation '{animation_name}' started")
            
        except Exception as e:
            debug_log(1, f"Animation error: {e}")
    
    def stop_animation(self):
        """Stop current animation"""
        if self.rig_object:
            try:
                self.rig_object.stopAction(0)
                self.current_animation = None
            except:
                pass
    
    # =========================================================================
    # MESSAGES
    # =========================================================================
    
    def send_message(self, subject, body):
        """Send message"""
        if self.game_controller:
            self.game_controller.sendMessage(subject, body)
            debug_log(2, f"Message: {subject}|{body}")
    
    def set_property(self, obj_name, prop, value):
        """Set property on object"""
        obj = logic.getCurrentScene().objects.get(obj_name)
        if obj:
            obj[prop] = value
    
    def set_speaker_states(self, speaker):
        """Configure who is speaking"""
        is_player = (speaker == "player")
        is_npc = (speaker == "npc")
        
        self.set_property("Player", "player_talking", is_player)
        self.set_property(self.owner.name, "npc_talking", is_npc)
    
    def clean_previous_text(self):
        """Clean previous text"""
        if self.cleaning_previous and self.text_to_clean:
            self.send_message('add_text', f'{self.text_to_clean}|empty')
            self.cleaning_previous = False
            self.text_to_clean = ""
            debug_log(2, f"Text cleaned: {self.text_to_clean}")
            return True
        return False
    
    def get_dialog_path(self, speaker, step):
        """Build dialog path"""
        if speaker == "player":
            return f"dialogs.{self.current_scene}.player.{step}"
        else:
            return f"dialogs.{self.current_scene}.npc13.{step}"
    
    # =========================================================================
    # COOLDOWN
    # =========================================================================
    
    def start_cooldown(self):
        """Start cooldown period"""
        self.in_cooldown = True
        self.cooldown_end_time = time.time() + COOLDOWN_TIME
        self.owner["in_cooldown"] = True
        
        # Ensure material returns to normal during cooldown
        if self.mouse_over_active or self.was_mouse_over:
            self.change_mesh_material(MATERIAL_NORMAL)
            self.mouse_over_active = False
            self.was_mouse_over = False
        
        debug_log(1, f"Cooldown started - {COOLDOWN_TIME} seconds")
    
    def update_cooldown(self):
        """Update cooldown state"""
        if self.in_cooldown:
            current_time = time.time()
            if current_time >= self.cooldown_end_time:
                self.in_cooldown = False
                self.owner["in_cooldown"] = False
                debug_log(1, "Cooldown finished - NPC available")
    
    # =========================================================================
    # DIALOG
    # =========================================================================
    
    def start_dialog(self):
        """Start dialog"""
        debug_log(1, "Starting dialog")
        
        # Restore normal material when starting dialog
        if self.mouse_over_active or self.was_mouse_over:
            self.change_mesh_material(MATERIAL_NORMAL)
            self.mouse_over_active = False
            self.was_mouse_over = False
        
        self.select_random_scene()
        
        self.set_property("Player", "on_dialog", True)
        self.set_speaker_states("none")
        
        self.current_state = "DIALOG_ACTIVE"
        self.dialog_step = 0
        self.cleaning_previous = False
        
        # Show first NPC line
        self.show_npc_line(0)
    
    def show_npc_line(self, step):
        """Show NPC line"""
        path = self.get_dialog_path("npc", step)
        self.send_message('add_text', f'char1_text|{path}')
        self.set_speaker_states("npc")
        
        self.play_animation(ANIM_TALKING, loop=True)
        self.play_talking_sound()
        
        # Schedule cleanup of player field for next frame
        self.cleaning_previous = True
        self.text_to_clean = "player_text"
        
        debug_log(2, f"NPC line {step}: {path}")
    
    def show_player_line(self, step):
        """Show player line"""
        path = self.get_dialog_path("player", step)
        self.send_message('add_text', f'player_text|{path}')
        self.set_speaker_states("player")
        
        self.play_animation(ANIM_IDLE, loop=True)
        self.stop_talking_sound()
        
        # Schedule cleanup of NPC field for next frame
        self.cleaning_previous = True
        self.text_to_clean = "char1_text"
        
        debug_log(2, f"Player line {step}: {path}")
    
    def end_dialog(self):
        """End dialog and start cooldown"""
        debug_log(1, "Ending dialog")
        
        self.send_message('add_text', 'char1_text|empty')
        self.send_message('add_text', 'player_text|empty')
        
        self.set_property("Player", "on_dialog", False)
        self.set_speaker_states("none")
        
        self.stop_talking_sound()
        
        # Start cooldown
        self.start_cooldown()
        
        # Determine cooldown state based on player proximity
        if self.player_in_anim_range:
            self.current_state = "COOLDOWN_NEAR_PLAYER"
            # Keep Idle animation during cooldown if player is nearby
            self.play_animation(ANIM_IDLE, loop=True)
        else:
            self.current_state = "COOLDOWN"
            self.stop_animation()
            self.current_animation = None
        
        self.dialog_end_time = time.time()
        self.waiting_for_animation = False
        self.cleaning_previous = False
    
    # =========================================================================
    # INPUT
    # =========================================================================
    
    def handle_input(self):
        """Handle user input"""
        # Do not process input during cooldown
        if self.in_cooldown:
            return False
        
        if not (self.mouse_over and self.mouse_clicked):
            return False
        
        debug_log(2, f"Click - State: {self.current_state}, Step: {self.dialog_step}")
        
        if self.current_state == "DIALOG_ACTIVE":
            if self.dialog_step == 0:
                # NPC line 0 -> Player line 0
                self.show_player_line(0)
                self.dialog_step = 1
                return True
                
            elif self.dialog_step == 1:
                # Player line 0 -> NPC line 1
                self.show_npc_line(1)
                self.dialog_step = 2
                return True
                
            elif self.dialog_step == 2:
                # NPC line 1 -> End
                self.end_dialog()
                return True
        
        return False
    
    def should_start_dialog(self):
        """Determine if dialog can be started"""
        # Do not start during cooldown
        if self.in_cooldown:
            return False
        
        return (self.player_in_dialog_range and 
                self.mouse_over and 
                self.mouse_clicked and 
                self.current_state in ["IDLE", "NEAR_PLAYER"])
    
    # =========================================================================
    # MAIN UPDATE
    # =========================================================================
    
    def update(self):
        """Update per frame"""
        try:
            # Update cooldown
            self.update_cooldown()
            
            # Handle mouse over (material change) - respects cooldown internally
            self.handle_mouse_over()
            
            # First: clean previous text if needed
            if self.cleaning_previous:
                self.clean_previous_text()
                # Do not process more this frame if cleaning
            
            # PROXIMITY MANAGEMENT (for all non-active states)
            if self.current_state not in ["DIALOG_ACTIVE", "DIALOG_ENDING"]:
                if self.player_in_anim_range:
                    # Player is nearby - rotate toward player and Idle animation
                    
                    # Rotate toward player
                    self.rotate_towards_player()
                    
                    # Update state based on whether in cooldown or not
                    if self.in_cooldown:
                        if self.current_state != "COOLDOWN_NEAR_PLAYER":
                            self.current_state = "COOLDOWN_NEAR_PLAYER"
                            self.play_animation(ANIM_IDLE, loop=True)
                    else:
                        if self.current_state != "NEAR_PLAYER":
                            self.current_state = "NEAR_PLAYER"
                            self.play_animation(ANIM_IDLE, loop=True)
                else:
                    # Player is far - stop rotation
                    self.is_rotating = False
                    
                    # Update state based on whether in cooldown or not
                    if self.in_cooldown:
                        if self.current_state != "COOLDOWN":
                            self.current_state = "COOLDOWN"
                            self.stop_animation()
                            self.current_animation = None
                    else:
                        if self.current_state != "IDLE":
                            self.current_state = "IDLE"
                            self.stop_animation()
                            self.current_animation = None
            
            # DIALOG START
            if self.should_start_dialog():
                self.start_dialog()
                return
            
            # ACTIVE DIALOG
            if self.current_state == "DIALOG_ACTIVE":
                self.handle_input()
            
            # ENDING (post-dialog immediate)
            elif self.current_state == "DIALOG_ENDING":
                # This state is no longer used, but kept just in case
                pass
            
        except Exception as e:
            debug_log(1, f"Update error: {e}")


# =============================================================================
# GLOBAL INSTANCE
# =============================================================================
_dialog_systems = {}


# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main(cont):
    """Main function called from Blender"""
    owner = cont.owner
    obj_key = owner.name
    
    # Initialize
    if obj_key not in _dialog_systems:
        try:
            _dialog_systems[obj_key] = SecurityGuardDialogSystem(owner)
        except Exception as e:
            print(f"[NPC13] Initialization error: {e}")
            return
    
    system = _dialog_systems[obj_key]
    
    # Get sensors
    near_anim = cont.sensors.get("Near_Anim")
    near_dialog = cont.sensors.get("Near_Dialog")
    mouse_over = cont.sensors.get("Mouse.Over")
    mouse_click = cont.sensors.get("Mouse.Click")
    
    # Update sensor states
    if near_anim:
        system.player_in_anim_range = near_anim.positive
    if near_dialog:
        system.player_in_dialog_range = near_dialog.positive
    if mouse_over:
        system.mouse_over = mouse_over.positive
    if mouse_click:
        system.mouse_clicked = mouse_click.positive
    
    # Process messages
    msg_sensor = cont.sensors.get("Message")
    if msg_sensor and msg_sensor.positive:
        for body in msg_sensor.bodies:
            debug_log(2, f"Message received: {body}")
    
    # Update
    system.update()