"""
suspend_collections.py

Collection suspension system for Player and Pest during UI interaction

This script manages the suspension and resumption of game logic for player and enemy
collections when UI windows (inventory, pause menu) are open. It uses message-based
communication and actuator activation to control collection activity.

Main Features:
    1. Suspends Player and Pest collections when UI windows open
    2. Supports v1 inventory, v2 inventory, and pause menu states
    3. Message-based control system for external suspension requests
    4. Periodic update to ensure consistent state
    5. Global message broadcasting for individual object control
    6. Actuator activation for static collection management

Setup:
    Owner: 'Empty.Suspend.Manager'
    Logic Bricks: Message and Always (True) sensors connected to Python controller/module 'suspend_collections.main'
    Requires Collection actuators named:
        - SuspendPlayer / ResumePlayer
        - SuspendPest / ResumePest

Configurable Variables:
    COLLECTIONS_TO_MANAGE (list): Collections to control (default: ["Player", "Pest"])
    DEBUG_ENABLED (bool): Enable debug messages (default: False)

Notes:
    - Uses logic module attributes for state persistence: _suspend_v1, _suspend_v2, _suspend_pause
    - Sends global message "suspend_logic" with format "global|suspend" or "global|resume"
    - Message format for control: "v1|suspend", "v2|resume", "pause|suspend", etc.
    - Update occurs every 30 frames or immediately on message receipt

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
__description__ = "Collection suspension system for Player and Pest during UI interaction"

# =============================================================================
# IMPORTS AND CONFIGURATION
# =============================================================================
import bge
from bge import logic

COLLECTIONS_TO_MANAGE = [
    "Player",    # CollectionPlayer
    "Pest",      # CollectionPest (all enemies)
]

DEBUG_ENABLED = False  # Set to False to disable all debug messages

def debug_print(message, prefix="[Suspend]"):
    """Print debug messages only if system is enabled"""
    if DEBUG_ENABLED:
        print(f"{prefix} {message}")

# =============================================================================
# INITIALIZATION
# =============================================================================
def _initialize_suspend_system():
    """Initialize suspension system"""
    if not hasattr(logic, "_suspend_system_initialized"):
        logic._suspend_system_initialized = True
        
        # Initialize suspension states
        logic._suspend_v1 = False
        logic._suspend_v2 = False  
        logic._suspend_pause = False
        
        debug_print("System initialized")
        debug_print("  - Player: CollectionPlayer")
        debug_print("  - Enemies: CollectionPest (all)")
        
        return True
    return False

# =============================================================================
# SUSPENSION LOGIC
# =============================================================================
def _should_suspend_logic():
    """Determine if logic should be suspended"""
    # Get suspension states
    v1_suspended = getattr(logic, "_suspend_v1", False)
    v2_suspended = getattr(logic, "_suspend_v2", False)
    pause_suspended = getattr(logic, "_suspend_pause", False)
    
    # Get window states
    hud_open = getattr(logic, "hud_inventory_open", False)
    v2_open = getattr(logic, "hud_inventory_v2_open", False)
    pause_open = getattr(logic, "hud_pause_open", False)
    
    # CORRECTED logic: Suspend if any window is open
    # And its corresponding system is suspended
    should_suspend = (
        (pause_open and pause_suspended) or
        (v2_open and v2_suspended) or
        (hud_open and v1_suspended)
    )
    
    return should_suspend

def _update_collection_suspension():
    """Send suspension messages to all objects - SIMPLIFIED VERSION"""
    cont = logic.getCurrentController()
    should_suspend = _should_suspend_logic()
    
    # Determine action
    action = "suspend" if should_suspend else "resume"
    debug_print(f"SENDING {action.upper()}...")
    
    # 1. Send global message for individual enemies
    try:
        bge.logic.sendMessage("suspend_logic", f"global|{action}")
        debug_print(f"Global message sent: {action}")
    except Exception as e:
        if DEBUG_ENABLED:
            print(f"[Suspend] Error sending global message: {e}")
    
    # 2. Activate actuators for static collections
    for collection_name in ["Player", "Pest"]:
        actuator_name = f"{action.capitalize()}{collection_name}"
        actuator = cont.actuators.get(actuator_name)
        
        if actuator:
            try:
                cont.activate(actuator)
                debug_print(f"Activated: {actuator_name}")
            except Exception as e:
                if DEBUG_ENABLED:
                    print(f"[Suspend] Error with {actuator_name}: {e}")
        else:
            # Try alternate names
            alt_name = f"{action.capitalize()}Collection{collection_name}"
            alt_actuator = cont.actuators.get(alt_name)
            if alt_actuator:
                try:
                    cont.activate(alt_actuator)
                    debug_print(f"Activated (alt): {alt_name}")
                except Exception as e:
                    if DEBUG_ENABLED:
                        print(f"[Suspend] Error with {alt_name}: {e}")
            else:
                debug_print(f"Not found: {actuator_name} or {alt_name}")

# =============================================================================
# MESSAGE HANDLING
# =============================================================================
def _handle_suspend_messages():
    """Handle suspension messages"""
    cont = logic.getCurrentController()
    processed = False
    
    for sensor in cont.sensors:
        if hasattr(sensor, 'subject') and sensor.positive and sensor.subject == "suspend_logic":
            for body in sensor.bodies:
                if _process_suspend_message(body):
                    processed = True
    
    return processed

def _process_suspend_message(body):
    """Process suspension message body"""
    try:
        parts = body.split("|")
        if len(parts) < 2:
            return False
        
        source = parts[0].strip().lower()  # v1, v2, pause
        action = parts[1].strip().lower()  # suspend, resume
        
        # Validate
        if source not in ["v1", "v2", "pause"] or action not in ["suspend", "resume"]:
            return False
        
        var_name = f"_suspend_{source}"
        current = getattr(logic, var_name, False)
        new_value = (action == "suspend")
        
        if current != new_value:
            setattr(logic, var_name, new_value)
            debug_print(f"{source.upper()}: {action.upper()}")
            return True
            
    except Exception as e:
        if DEBUG_ENABLED:
            print(f"[Suspend] Error processing message: {e}")
    
    return False

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main():
    """Main function called every frame"""
    # Initialize
    _initialize_suspend_system()
    
    # Process messages
    if _handle_suspend_messages():
        _update_collection_suspension()
    
    # Periodic update (every 30 frames)
    if not hasattr(logic, "_suspend_frame_counter"):
        logic._suspend_frame_counter = 0
    
    logic._suspend_frame_counter += 1
    if logic._suspend_frame_counter >= 30:
        logic._suspend_frame_counter = 0
        _update_collection_suspension()