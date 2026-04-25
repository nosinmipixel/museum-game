"""
sound_context.py

# Sound zone switch system for UPBGE

This script manages zone-based background music switching using collision triggers.
When the player enters a zone, it activates a specific music context; when leaving,
it reverts to the previous context.

Main Features:
    1. Collision detection for zone entry/exit
    2. Activates sound contexts via sound_background module
    3. Updates player position for distance-based switch management
    4. Uses object properties for configuration
    5. One-time initialization per switch object

Setup:
    Owners: Area objects (e.g., "Sound.Storage")
    Connect an Always sensor (True Level) to a Python Module controller: sound_context.main
    Object must have a Property 'sound_context' (string) with context name (e.g., "library", "quiz")

Configurable Variables:
    None (uses object properties)

Notes:
    - Requires sound_background module with add_switch_context() and update_player_position()
    - Switch activation is temporary - returns to previous context when exiting
    - Property 'sound_context' must match a valid context in sound_background

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
__description__ = "Zone-based sound context switching using collision triggers"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main(cont):
    """Main function for switch objects"""
    owner = cont.owner
    
    # Initialization
    if "sound_switch_initialized" not in owner:
        owner["sound_switch_initialized"] = True
        owner["sound_switch_active"] = False
        # Ensure context property exists
        if "sound_context" not in owner:
            owner["sound_context"] = "exploration"
        return
    
    # Find collision sensor (similar to message_area_info)
    coll_sensor = None
    for sensor in cont.sensors:
        if hasattr(sensor, 'positive'):
            coll_sensor = sensor
            break
    
    if not coll_sensor:
        return
    
    # Detect player collision
    player_colliding = coll_sensor.positive
    
    # State change detection
    if player_colliding and not owner["sound_switch_active"]:
        owner["sound_switch_active"] = True
        # Activate switch
        context = owner.get("sound_context", "exploration")
        try:
            from sound_background import get_manager, add_switch_context
            manager = get_manager()
            add_switch_context(context, owner)
            # Update player position
            from sound_background import update_player_position
            scene = logic.getCurrentScene()
            player = scene.objects.get("Player")
            if player:
                update_player_position(player.worldPosition.copy())
        except Exception as e:
            print(f"[SoundSwitch] Error activating sound: {e}")
    
    elif not player_colliding and owner["sound_switch_active"]:
        owner["sound_switch_active"] = False