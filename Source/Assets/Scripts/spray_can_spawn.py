"""
spray_can_spawn.py

Random spray can spawn control

This script manages the automatic spawning of collectible spray cans at designated
spawn points in the scene. It maintains minimum and maximum can counts, uses
timed intervals with probability, and integrates with the game state system.

Main Features:
    1. Spawns spray cans at designated Empty.Spawn.Can objects
    2. Maintains configurable min/max can counts in scene
    3. Time-based spawning with probability chance
    4. Prevents spawning too close to existing cans
    5. Cleans up orphaned cans marked for deletion
    6. Integrates with game state for can counter
    7. Guarantees minimum cans at game start

Setup:
    Owner: Empties objects (e.g., 'Empty.Spawn.Can.1')
    Logic Bricks: Always (True) sensor connected to Python controller/module 'spray_can_spawn.main'
    Requires Empty.Spawn.Can objects in scene as spawn points
    Requires 'Spray.Can' object and 'SprayCanObject' collection instance in scene as template for duplication

Configurable Variables:
    DEBUG_MODE (bool): Enable debug messages (default: False)
    MAX_CANS_IN_SCENE (int): Maximum allowed cans in scene (default: 3)
    MIN_CANS_IN_SCENE (int): Minimum guaranteed cans in scene (default: 1)
    SPAWN_INTERVAL (float): Seconds between spawn attempts (default: 30.0)
    SPAWN_PROBABILITY (float): Spawn chance per interval (0.0-1.0, default: 0.8)

Notes:
    - Requires game_access module for game state management
    - Uses object duplication from template 'Spray.Can'
    - Spawn points must be named starting with 'Empty.Spawn.Can'
    - Distance check prevents spawning on top of existing cans
    - Force spawn occurs when can count falls below minimum

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
__description__ = "Random spray can spawn system with min/max control and timing"

# =============================================================================
# IMPORTS AND CONFIGURATION
# =============================================================================
import bge
from bge import logic
import random
import math
import game_access

MAX_CANS_IN_SCENE = 3  # Maximum cans allowed in scene
MIN_CANS_IN_SCENE = 1  # Minimum guaranteed cans in scene
SPAWN_INTERVAL = 30.0  # Seconds between spawn attempts
SPAWN_PROBABILITY = 0.8  # Spawn chance per interval (0.0 to 1.0)
DEBUG_MODE = False  # Enable to see debug messages

def debug_print(message):
    """Controlled debug print function"""
    if DEBUG_MODE:
        print(f"[SPAWN CAN] {message}")

# =============================================================================
# GAME STATE ACCESSORS
# =============================================================================
def get_spray_cans_count():
    """Get current can count using new architecture"""
    try:
        game = game_access.get_game()
        if game:
            return game.state.spray_cans
    except Exception as e:
        debug_print(f"Error getting can counter: {e}")
    return 0

def update_spray_cans_count(delta=1):
    """Update can counter using new architecture"""
    try:
        game = game_access.get_game()
        if game:
            game.state.spray_cans = max(0, game.state.spray_cans + delta)
            debug_print(f"Can counter updated: {game.state.spray_cans - delta} -> {game.state.spray_cans}")
            return game.state.spray_cans
    except Exception as e:
        debug_print(f"Error updating can counter: {e}")
    return 0

# =============================================================================
# SCENE OBJECT SEARCH FUNCTIONS
# =============================================================================
def find_all_spawn_points():
    """Find all Empty.Spawn.Can objects in scene"""
    try:
        scene = logic.getCurrentScene()
        spawn_points = []
        
        for obj in scene.objects:
            if obj.name.startswith("Empty.Spawn.Can"):
                spawn_points.append(obj)
        
        debug_print(f"Found {len(spawn_points)} spawn points")
        return spawn_points
        
    except Exception as e:
        debug_print(f"Error finding spawn points: {e}")
        return []

def find_existing_cans():
    """Find all existing spray cans in scene"""
    try:
        scene = logic.getCurrentScene()
        existing_cans = []
        
        for obj in scene.objects:
            if obj.name.startswith("Spray.Can"):
                existing_cans.append(obj)
        
        return existing_cans
        
    except Exception as e:
        debug_print(f"Error finding existing cans: {e}")
        return []

def count_real_cans_in_scene():
    """Count actual cans in scene (not counter)"""
    existing_cans = find_existing_cans()
    return len(existing_cans)

# =============================================================================
# SPAWN AND CLEANUP FUNCTIONS
# =============================================================================
def spawn_spray_can(spawn_point):
    """Create a new spray can at spawn point position"""
    try:
        scene = logic.getCurrentScene()
        
        # Check if a can already exists near this position
        existing_cans = find_existing_cans()
        for can in existing_cans:
            distance = (can.worldPosition - spawn_point.worldPosition).length
            if distance < 0.5:  # If a can is very close
                debug_print(f"Can already exists near {spawn_point.name}")
                return None
        
        # Create the spray can
        new_can = scene.addObject("Spray.Can", spawn_point)
        
        if new_can:
            # Position at spawn point location
            new_can.worldPosition = spawn_point.worldPosition
            
            # Ensure it has the correct material
            new_can["_spawned"] = True  # Mark as spawned
            
            # Update counter using new architecture
            update_spray_cans_count()
            
            debug_print(f"New can created at {spawn_point.name}")
            return new_can
        else:
            debug_print(f"Error: Could not create object 'Spray.Can'")
            return None
            
    except Exception as e:
        debug_print(f"Error creating spray can: {e}")
        return None

def cleanup_old_cans():
    """Remove cans that were collected but not properly deleted"""
    try:
        scene = logic.getCurrentScene()
        cans_to_remove = []
        
        for obj in scene.objects:
            if obj.name.startswith("Spray.Can"):
                # Check if object is marked for deletion
                if obj.get("_marked_for_deletion", False):
                    cans_to_remove.append(obj)
        
        for can in cans_to_remove:
            scene.endObject(can)
            debug_print(f"Can {can.name} removed during cleanup")
            
    except Exception as e:
        debug_print(f"Error during cleanup: {e}")

# =============================================================================
# SPAWN LOGIC
# =============================================================================
def try_spawn_random_can(force_spawn=False):
    """Attempt to spawn a can at a random spawn point"""
    # Get available spawn points
    spawn_points = find_all_spawn_points()
    
    if not spawn_points:
        debug_print("No spawn points available")
        return False
    
    # Count actual cans in scene
    real_can_count = count_real_cans_in_scene()
    
    # If maximum reached, do not spawn more
    if real_can_count >= MAX_CANS_IN_SCENE:
        debug_print(f"Maximum cans reached ({MAX_CANS_IN_SCENE})")
        return False
    
    # If below minimum guaranteed, force spawn
    if real_can_count < MIN_CANS_IN_SCENE:
        debug_print(f"Below {MIN_CANS_IN_SCENE} cans, forced spawn")
        force_spawn = True
    
    # If not forced spawn, apply probability
    if not force_spawn:
        if random.random() > SPAWN_PROBABILITY:
            debug_print("Spawn probability not met")
            return False
    
    # Select random spawn point
    spawn_point = random.choice(spawn_points)
    
    # Attempt to spawn
    spawned_can = spawn_spray_can(spawn_point)
    
    if spawned_can:
        debug_print(f"Spawn successful at {spawn_point.name}")
        return True
    else:
        debug_print(f"Spawn failed at {spawn_point.name}")
        return False

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main():
    cont = logic.getCurrentController()
    own = cont.owner
    
    # Initialize variables if not exist
    if "_last_spawn_time" not in own:
        own["_last_spawn_time"] = logic.getRealTime()
    
    if "_initialized" not in own:
        own["_initialized"] = True
        debug_print(f"Spawn system initialized on {own.name}")
        
        # Initial cleanup
        cleanup_old_cans()
        
        # Guaranteed initial spawn if no cans
        real_can_count = count_real_cans_in_scene()
        if real_can_count == 0:
            debug_print("No cans in scene, forced initial spawn")
            try_spawn_random_can(force_spawn=True)
    
    # Get current time
    current_time = logic.getRealTime()
    time_since_last_spawn = current_time - own["_last_spawn_time"]
    
    # Check if it's time to attempt spawn
    if time_since_last_spawn >= SPAWN_INTERVAL:
        own["_last_spawn_time"] = current_time
        
        debug_print(f"Spawn interval reached ({time_since_last_spawn:.1f}s)")
        
        # Attempt random spawn
        try_spawn_random_can()

# Execute
main()