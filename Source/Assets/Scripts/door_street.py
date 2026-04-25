"""
door_street.py

Manages street door opening/closing with proximity detection using Near sensor.

This script handles automatic door operation (open when player approaches,
close when player leaves) using a Near sensor for efficient proximity detection,
with support for animations and sound effects.

Main Features:
    1. Automatic door opening when player approaches (Near sensor)
    2. Automatic door closing when player leaves
    3. Animation support for opening and closing
    4. Sound effects for door sliding
    5. Physics suspension/restoration via parent operations
    6. Efficient sensor-based detection (no manual distance calculation)
    7. Configurable debug logging

Setup:
    Connect to Logic Bricks as Python controller with module 'door_street.main'
    Required sensor: 'Near' (property: 'player', Distance: 2, Reset distance: 4)
    Required child objects: Door.Street (mesh)
    Required animation actions: 'Anim_Door_Street' or 'DoorOpen'

Configurable Variables:
    _DEBUG_MODE (bool): Global debug flag (default: False)

Notes:
    - Requires Near sensor configured on the door object
    - Door mesh object must be named 'Door.Street'
    - Animation frames: 1-25 for opening, 25-50 for closing
    - Physics are suspended during opening using setParent()
    - Physics are restored during closing using removeParent()
    - Sound effects are sent via 'sound_fx.play' messages

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
__description__ = "Manages street door opening/closing with proximity detection"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic as gl

# =============================================================================
# DEBUG CONFIGURATION
# =============================================================================
_DEBUG_MODE = False  # Global variable for debug message control

def set_debug_mode(enabled):
    """Activates or deactivates debug messages"""
    global _DEBUG_MODE
    _DEBUG_MODE = enabled

def debug_print(*args, **kwargs):
    """Prints messages only if debug mode is enabled"""
    if _DEBUG_MODE:
        print("[DOOR_STREET]", *args, **kwargs)

# =============================================================================
# DOOR CONTROLLER CLASS
# =============================================================================
class DoorController:
    def __init__(self, owner):
        self.owner = owner
        self.scene = gl.getCurrentScene()
        
        # Door states
        self.is_open = False
        self.is_animating = False
        self.player_near = False
        
        # Reference to child object 'Door.Street' (the mesh)
        self.door_mesh = self.get_door_mesh()
        
        debug_print(f"DoorController initialized for {owner.name}")
        
    def get_door_mesh(self):
        """Gets reference to child object 'Door.Street'"""
        # Search in childrenRecursive first
        for child in self.owner.childrenRecursive:
            if child.name == 'Door.Street' or 'Door.Street' in child.name:
                debug_print(f"Found Door.Street: {child.name}")
                return child
        
        # If not found in children, search entire scene
        door_mesh = self.scene.objects.get('Door.Street')
        if door_mesh:
            debug_print(f"Found Door.Street in scene: {door_mesh.name}")
        
        return door_mesh
    
    def check_sensor_near(self, cont):
        """Checks 'Near' sensor instead of manually calculating distance"""
        # The 'Near' sensor is already configured in the logic controller
        # with property: 'player', Distance: 2, Reset distance: 4
        # We just need to read its state
        
        near_sensor = cont.sensors.get("Near")
        if near_sensor:
            return near_sensor.positive
        
        # debug_print("Warning: 'Near' sensor not found")  # Commented by default
        return False
    
    def suspend_dynamics(self):
        """Suspends dynamics using setParent() as in reference script"""
        if not self.door_mesh:
            debug_print("Error: Door.Street not found to suspend dynamics")
            return
            
        try:
            # Create or get an empty object for parenting
            empty_obj = self.scene.objects.get('Empty.Door.Parent')
            
            # If it doesn't exist, use the rig itself
            if not empty_obj:
                empty_obj = self.owner
            
            # Parent Door.Street to empty object/rig
            self.door_mesh.setParent(empty_obj)
            
            debug_print("Dynamics suspended - Door.Street parented")
            
        except Exception as e:
            debug_print(f"Error suspending dynamics with setParent: {e}")
    
    def restore_dynamics(self):
        """Restores dynamics using removeParent() as in reference script"""
        if not self.door_mesh:
            debug_print("Error: Door.Street not found to restore dynamics")
            return
            
        try:
            # Remove parent to restore original properties
            self.door_mesh.removeParent()
            
            debug_print("Dynamics restored - parent removed")
            
        except Exception as e:
            debug_print(f"Error restoring dynamics with removeParent: {e}")
    
    def open_door(self):
        """Opens the door"""
        if self.is_animating or self.is_open:
            return
            
        self.is_animating = True
        debug_print("Starting door opening...")
        
        # Suspend dynamics
        self.suspend_dynamics()
        
        # Play opening animation (frames 1-25)
        try:
            self.owner.playAction('Anim_Door_Street', 1, 25, 
                                 play_mode=gl.KX_ACTION_MODE_PLAY,
                                 speed=1.0, layer=0)
            debug_print("Opening animation started (frames 1-25)")
        except Exception as e:
            debug_print(f"Error in opening animation: {e}")
            # Try with different animation name
            try:
                self.owner.playAction('DoorOpen', 1, 25, 
                                     play_mode=gl.KX_ACTION_MODE_PLAY,
                                     speed=1.0, layer=0)
                debug_print("Opening animation started with alternative name")
            except:
                debug_print("Could not play opening animation")
        
        # Play opening sound
        try:
            bge.logic.sendMessage("sound_fx.play", "sound_fx.play|door_sliding_open.ogg|volume=1.0")
            debug_print("Opening sound played")
        except Exception as e:
            debug_print(f"Error playing opening sound: {e}")
        
        # Update state
        self.is_open = True
        self.is_animating = False
        debug_print("Door fully open")
    
    def close_door(self):
        """Closes the door"""
        if self.is_animating or not self.is_open:
            return
            
        self.is_animating = True
        debug_print("Starting door closing...")
        
        # Restore dynamics
        self.restore_dynamics()
        
        # Play closing animation (frames 25-50)
        try:
            self.owner.playAction('Anim_Door_Street', 25, 50, 
                                 play_mode=gl.KX_ACTION_MODE_PLAY,
                                 speed=1.0, layer=0)
            debug_print("Closing animation started (frames 25-50)")
        except Exception as e:
            debug_print(f"Error in closing animation: {e}")
            # Try with different animation name
            try:
                self.owner.playAction('DoorOpen', 25, 50, 
                                     play_mode=gl.KX_ACTION_MODE_PLAY,
                                     speed=1.0, layer=0)
                debug_print("Closing animation started with alternative name")
            except:
                debug_print("Could not play closing animation")
        
        # Play closing sound
        try:
            bge.logic.sendMessage("sound_fx.play", "sound_fx.play|door_sliding_close.ogg|volume=1.0")
            debug_print("Closing sound played")
        except Exception as e:
            debug_print(f"Error playing closing sound: {e}")
        
        # Update state
        self.is_open = False
        self.is_animating = False
        debug_print("Door fully closed")
    
    def update(self, cont):
        """Updates door state using 'Near' sensor"""
        # Check 'Near' sensor (optimized over distance calculation)
        player_currently_near = self.check_sensor_near(cont)
        
        # Debug: show sensor state
        if hasattr(self, '_last_near_state') and self._last_near_state != player_currently_near:
            debug_print(f"Near sensor: {'ACTIVATED' if player_currently_near else 'DEACTIVATED'}")
        self._last_near_state = player_currently_near
        
        # If player just approached and door is closed
        if player_currently_near and not self.player_near and not self.is_open:
            debug_print("Near sensor detected player - Opening door")
            self.player_near = True
            self.open_door()
        
        # If player just left and door is open
        elif not player_currently_near and self.player_near and self.is_open:
            debug_print("Near sensor lost player - Closing door")
            self.player_near = False
            self.close_door()
        
        # Update state if no change (for initial case)
        elif player_currently_near != self.player_near:
            self.player_near = player_currently_near

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main(cont):
    """Main function called by UPBGE"""
    owner = cont.owner
    
    # Initialize controller if it doesn't exist
    if 'door_controller' not in owner:
        debug_print(f"Initializing DoorController for {owner.name}...")
        owner['door_controller'] = DoorController(owner)
    
    # Update controller with logic controller reference
    try:
        door_controller = owner['door_controller']
        door_controller.update(cont)
    except Exception as e:
        debug_print(f"Error in DoorController update: {e}")

# =============================================================================
# PUBLIC FUNCTION FOR DEBUG CONTROL
# =============================================================================

def set_debug(enabled):
    """Activates or deactivates debug messages globally"""
    set_debug_mode(enabled)