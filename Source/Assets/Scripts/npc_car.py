"""
npc_car.py

Manages NPC car movement, physics, and texture changes with spawn/despawn message control.

This script handles a car NPC that moves between two waypoints, detects player
presence, stops when player is in front, plays horn sounds, and changes texture
after completing each lap.

Main Features:
    1. Movement between two configurable waypoints (A and B)
    2. Player detection with front-facing sensor
    3. Automatic stop when player is in front and within stop zone
    4. Horn sound with cooldown when stopped
    5. Suspension animation effect (bouncing)
    6. Texture cycling after each completed lap
    7. Spawn/despawn control via messages (car_near, car_far)
    8. Support for multiple car instances

Setup:
    Connect to Logic Bricks as Python controller with module 'npc_car.main'
    Required sensors: Near.Stop, Message.Spawn, Message.Despawn
    Required child object: Car.2D (mesh object with material)

Configurable Variables:
    START_POS (Vector): Starting position (default: (34.0, 50.0, 0.0))
    END_POS (Vector): Ending position (default: (34.0, -40.0, 0.0))
    CAR_SPEED (float): Vehicle speed (default: 0.15)
    SUSPENSION_SPEED (float): Suspension effect speed (default: 0.1)
    SUSPENSION_AMPLITUDE (float): Maximum Z offset (default: 0.2)
    HONK_COOLDOWN_FRAMES (int): Frames between horn sounds (default: 45)
    FRONT_DETECTION_ANGLE (float): Front detection angle (default: 0.3)
    MAX_CAR_IMAGES (int): Number of available textures (default: 2)
    TEXTURE_PATH (str): Texture path pattern (default: '//Assets/Textures/car_{}.png')
    TEXTURE_NODE_NAME (str): Texture node name (default: 'Texture_Car')
    MATERIAL_SLOT (int): Material slot index (default: 0)
    DEBUG_MODE (bool): Enable debug messages (default: False)

Notes:
    - Requires car_{n}.png textures in //Assets/Textures/ folder
    - Texture changes after each completed lap, cycling through available images
    - Car must have a child mesh object named 'Car.2D' or similar
    - Near.Stop sensor should be configured to detect player
    - Car instances are stored globally and activated/deactivated via messages

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
__description__ = "Manages NPC car movement and texture changes with message control"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic
from mathutils import Vector
import math
import random

# =============================================================================
# GLOBAL VARIABLES
# =============================================================================
car_instances = {}
active_cars = []  # List to track cars activated by message

# =============================================================================
# EASILY MODIFIABLE CONFIGURATION
# =============================================================================

# --- WAYPOINTS ---
START_POS = Vector((34.0, 50.0, 0.0))    # Point A (x, y, z)
END_POS = Vector((34.0, -40.0, 0.0))     # Point B (x, y, z)

# --- SPEEDS ---
CAR_SPEED = 0.15                          # Vehicle speed
SUSPENSION_SPEED = 0.1                    # Suspension effect speed
SUSPENSION_AMPLITUDE = 0.2                 # Maximum Z offset amplitude

# --- BEHAVIOR ---
HONK_COOLDOWN_FRAMES = 45                  # Frames between horn sounds
FRONT_DETECTION_ANGLE = 0.3                 # Front detection angle

# --- TEXTURE CONFIGURATION ---
MAX_CAR_IMAGES = 2                          # Maximum number of available images
TEXTURE_PATH = "//Assets/Textures/car_{}.png"      # Texture name pattern
TEXTURE_NODE_NAME = "Texture_Car"            # Image node name
MATERIAL_SLOT = 0                            # Material slot

# --- DEBUG OPTIONS ---
DEBUG_MODE = False                          # Show debug messages

# =============================================================================
# NPC CAR CLASS
# =============================================================================
class NPCCar:
    def __init__(self, own):
        self.own = own
        
        # DEBUG - Initialize FIRST before any debug_print
        self.debug_mode = DEBUG_MODE
        
        # Waypoints
        self.point_a = START_POS.copy()
        self.point_b = END_POS.copy()
        
        # Initial position
        own.worldPosition = self.point_a.copy()
        
        # Speed configuration
        self.car_speed = CAR_SPEED
        self.suspension_speed = SUSPENSION_SPEED
        self.suspension_amplitude = SUSPENSION_AMPLITUDE
        
        # Detection states
        self.player_in_front = False
        self.player_near_stop = False
        
        # Movement control
        self.is_moving = True
        self.was_moving = True
        self.is_honking = False
        self.honk_cooldown = 0
        self.honk_cooldown_frames = HONK_COOLDOWN_FRAMES
        
        # Front detection angle
        self.front_angle = FRONT_DETECTION_ANGLE
        
        # Suspension effect variables
        self.z_offset = 0.0
        self.suspension_time = 0.0
        
        # Distance to player
        self.player_distance = 100.0
        self.player_object = None
        
        # Texture change system
        self.current_texture_index = 1        # Start with texture 1
        self.lap_count = 0                     # Completed laps counter
        
        # Find child object (Car.2D)
        self.car_mesh_obj = self._get_child_mesh_object()
        
        # Optimization
        self.update_counter = 0
        self.update_threshold = 5
        
        # Debug counter
        self.debug_counter = 0
        
        # NOW we can use debug_print (after initializing debug_mode)
        self.debug_print(f"NPC car initialized (waiting for message)")
        self.debug_print(f"Route: ({self.point_a.x}, {self.point_a.y}) -> ({self.point_b.x}, {self.point_b.y})")
        self.debug_print(f"Speed: {self.car_speed}")
        self.debug_print(f"Textures available: {MAX_CAR_IMAGES} (starting with car_1.png)")
        
        if self.car_mesh_obj:
            self.debug_print(f"Child object found: {self.car_mesh_obj.name}")
        else:
            self.debug_print("Child object Car.2D not found")
    
    def _get_child_mesh_object(self):
        """Gets the child object containing the mesh (Car.2D)"""
        try:
            if self.own.children and len(self.own.children) > 0:
                # Search specifically for Car.2D
                for child in self.own.children:
                    if "Car.2D" in child.name:
                        return child
                    if "car" in child.name.lower():
                        return child
                # If not found by name, return first child
                return self.own.children[0]
        except Exception as e:
            print(f"Error getting child: {e}")
        return None
    
    def _get_material_name(self, obj):
        """Gets the name of the material assigned to the object"""
        try:
            if not obj:
                return None
            
            import bpy
            blender_obj = obj.blenderObject
            
            if not blender_obj.data.materials:
                return None
            
            if MATERIAL_SLOT >= len(blender_obj.data.materials):
                return None
            
            current_material = blender_obj.data.materials[MATERIAL_SLOT]
            if current_material:
                return current_material.name
            
        except Exception as e:
            self.debug_print(f"Error getting material name: {e}")
        
        return None
    
    def change_car_texture(self, texture_number):
        """Changes the car texture (adapted from books_library.py)"""
        try:
            target_obj = self.car_mesh_obj
            if not target_obj:
                self.debug_print("No child object to change texture")
                return False
            
            texture_path = TEXTURE_PATH.format(texture_number)
            self.debug_print(f"Attempting to load: {texture_path}")
            
            import bpy
            blender_child = target_obj.blenderObject
            
            if not blender_child.data.materials:
                self.debug_print(f"Child object has no materials assigned")
                return False
            
            if MATERIAL_SLOT >= len(blender_child.data.materials):
                self.debug_print(f"No material in slot {MATERIAL_SLOT}")
                return False
            
            current_material = blender_child.data.materials[MATERIAL_SLOT]
            if not current_material:
                self.debug_print(f"Material in slot {MATERIAL_SLOT} is None")
                return False
            
            material_name = current_material.name
            self.debug_print(f"Material detected: {material_name}")
            
            mat = bpy.data.materials.get(material_name)
            if not mat:
                self.debug_print(f"Material not found: {material_name}")
                return False
            
            if not mat.use_nodes:
                mat.use_nodes = True
                self.debug_print(f"Nodes enabled for material: {material_name}")
            
            nodes = mat.node_tree.nodes
            
            texture_node = None
            texture_node = nodes.get(TEXTURE_NODE_NAME)
            
            if not texture_node:
                for node in nodes:
                    if node.type == 'TEX_IMAGE':
                        texture_node = node
                        texture_node.name = TEXTURE_NODE_NAME
                        texture_node.label = TEXTURE_NODE_NAME
                        self.debug_print(f"Texture node found by type: {node.name}")
                        break
            
            if not texture_node:
                self.debug_print(f"No texture node found in material")
                return False
            
            try:
                if not texture_path.startswith("//"):
                    texture_path = "//" + texture_path
                
                image = bpy.data.images.load(texture_path, check_existing=True)
                texture_node.image = image
                self.debug_print(f"Texture changed to: {texture_path}")
                return True
                
            except Exception as e:
                self.debug_print(f"Error loading texture {texture_path}: {e}")
                return False
                
        except Exception as e:
            self.debug_print(f"Error in change_car_texture: {e}")
            return False
    
    def debug_print(self, *args, **kwargs):
        """Prints debug messages if enabled"""
        if self.debug_mode:
            print("[NPCCar]", *args, **kwargs)
    
    def find_player(self):
        """Finds the player"""
        scene = bge.logic.getCurrentScene()
        for obj in scene.objects:
            if "player" in obj.getPropertyNames():
                self.debug_print(f"Player found: {obj.name}")
                return obj
            if "player" in obj.name.lower():
                self.debug_print(f"Player found by name: {obj.name}")
                return obj
        return None
    
    def get_sensor_range(self, sensor):
        """Gets sensor range/configuration for debug"""
        if not sensor:
            return "N/A"
        try:
            if hasattr(sensor, 'range'):
                return f"{sensor.range}"
            elif hasattr(sensor, 'distance'):
                return f"{sensor.distance}"
        except:
            pass
        return "unknown"
    
    def is_player_in_front(self):
        """Determines if player is in front of the car"""
        if not self.player_object or not self.own:
            return False
        
        to_player = self.player_object.worldPosition - self.own.worldPosition
        route_direction = (self.point_b - self.point_a).normalized()
        
        if to_player.length_squared > 0:
            to_player.normalize()
        
        dot_product = to_player.dot(route_direction)
        return dot_product > self.front_angle
    
    def update_sensors(self, cont):
        """Updates all sensors and states"""
        near_stop_sensor = cont.sensors.get('Near.Stop')
        self.player_near_stop = near_stop_sensor.positive if near_stop_sensor else False
        
        self.player_in_front = self.is_player_in_front()
        
        if self.debug_counter % 60 == 0:
            if near_stop_sensor:
                stop_dist = self.get_sensor_range(near_stop_sensor)
                self.debug_print(f"Near.Stop: distance={stop_dist}")
            
            self.debug_print(f"In front: {self.player_in_front}, Near.Stop: {self.player_near_stop}")
            if self.player_object:
                self.debug_print(f"Actual distance: {self.player_distance:.2f}")
    
    def should_stop(self):
        """Car stops when player is in front AND in stop zone"""
        return self.player_in_front and self.player_near_stop
    
    def update_suspension(self, own):
        """Controls Z-axis suspension effect"""
        if self.is_moving:
            self.suspension_time += self.suspension_speed
            z_offset = (math.sin(self.suspension_time) ** 2) * self.suspension_amplitude
            
            if random.random() < 0.05:
                z_offset += random.uniform(-0.02, 0.02)
            
            self.z_offset = max(0.0, min(self.suspension_amplitude, z_offset))
        else:
            if abs(self.z_offset) > 0.001:
                self.z_offset *= 0.95
            else:
                self.z_offset = 0.0
        
        own.worldPosition.z = self.z_offset
    
    # =============================================
    # NEW METHOD: Deactivate the car
    # =============================================
    def deactivate(self):
        """Resets the car when deactivated (car_far message)"""
        self.debug_print("Car DEACTIVATED (car_far)")
        
        # Reset position to start point
        self.own.worldPosition = self.point_a.copy()
        
        # Reset states
        self.is_moving = True
        self.is_honking = False
        self.honk_cooldown = 0
        self.z_offset = 0.0
        self.suspension_time = 0.0
        self.player_in_front = False
        self.player_near_stop = False
    
    def update(self):
        """Main update method"""
        try:
            controller = bge.logic.getCurrentController()
            own = controller.owner
            
            self.debug_counter += 1
            self.was_moving = self.is_moving
            
            # Find player
            if not self.player_object:
                self.player_object = self.find_player()
            
            # Update distance
            if self.player_object:
                self.player_distance = (own.worldPosition - self.player_object.worldPosition).length
            
            # Update sensors
            self.update_sensors(controller)
            
            # MOVEMENT CONTROL
            if self.should_stop():
                if self.is_moving:
                    self.debug_print(f"Car STOPPED")
                    self.is_moving = False
                
                if self.honk_cooldown <= 0:
                    if not self.is_honking:
                        self.debug_print("HONK! Horn sounding")
                        bge.logic.sendMessage("sound_fx.play", "sound_fx.play|car_horn_honking.ogg|volume=0.2")  
                        self.is_honking = True
                        self.honk_cooldown = self.honk_cooldown_frames
            else:
                if not self.is_moving:
                    self.debug_print("Car RESUMING movement")
                    self.is_honking = False
                    self.suspension_time = 0.0
                
                self.is_moving = True
            
            # Reduce cooldown
            if self.honk_cooldown > 0:
                self.honk_cooldown -= 1
            
            # MOVEMENT ALONG ROUTE
            if self.is_moving:
                route_direction = (self.point_b - self.point_a).normalized()
                own.worldPosition += route_direction * self.car_speed
                
                bge.logic.sendMessage("moving", "moving", "Car.Col")
                
                if self.debug_counter % 60 == 0:
                    self.debug_print(f"Car: ({own.worldPosition.x:.2f}, {own.worldPosition.y:.2f}, {own.worldPosition.z:.2f})")
                
                # Check if reached point B
                to_b = self.point_b - own.worldPosition
                if route_direction.dot(to_b) < 0:
                    own.worldPosition = self.point_a.copy()
                    self.lap_count += 1
                    
                    next_texture = (self.current_texture_index % MAX_CAR_IMAGES) + 1
                    
                    self.debug_print(f"Lap {self.lap_count} completed! Changing texture: car_{self.current_texture_index}.png -> car_{next_texture}.png")
                    
                    if self.change_car_texture(next_texture):
                        self.current_texture_index = next_texture
                        self.debug_print(f"Texture updated to car_{next_texture}.png")
                    else:
                        self.debug_print(f"Error changing texture")
                    
                    self.suspension_time = 0.0
            else:
                if self.debug_counter % 60 == 0:
                    self.debug_print(f"Car STOPPED")
            
            # UPDATE SUSPENSION
            self.update_suspension(own)
            
            self.update_counter += 1
            
        except Exception as e:
            print(f"Error: {e}")
            import traceback
            traceback.print_exc()

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main():
    controller = bge.logic.getCurrentController()
    own = controller.owner
    obj_id = id(own)
    
    # --- ACTIVATION SENSOR (car_near) ---
    spawn_sensor = controller.sensors.get('Message.Spawn')
    
    # --- DEACTIVATION SENSOR (car_far) ---
    despawn_sensor = controller.sensors.get('Message.Despawn')
    
    # =============================================
    # ACTIVATE CAR (car_near message)
    # =============================================
    if spawn_sensor and spawn_sensor.positive:
        if obj_id not in car_instances:
            # Create instance if it doesn't exist
            car_instances[obj_id] = NPCCar(own)
            active_cars.append(car_instances[obj_id])
            
            print("="*50)
            print("NPC CAR ACTIVATED BY MESSAGE (car_near)")
            print(f"{MAX_CAR_IMAGES} images available")
            print("="*50)
        else:
            # Instance already exists, reactivate if inactive
            if car_instances[obj_id] not in active_cars:
                active_cars.append(car_instances[obj_id])
                print("NPC CAR REACTIVATED (car_near)")
    
    # =============================================
    # DEACTIVATE CAR (car_far message)
    # =============================================
    if despawn_sensor and despawn_sensor.positive:
        if obj_id in car_instances:
            car = car_instances[obj_id]
            if car in active_cars:
                car.deactivate()          # Reset car state
                active_cars.remove(car)   # Remove from active list
                
                print("="*50)
                print("NPC CAR DEACTIVATED BY MESSAGE (car_far)")
                print("="*50)
    
    # Update only active cars
    for car in active_cars:
        car.update()

main()