"""
message_area_info.py

Manages area-based info messages triggered by player collision with trigger zones.

This script detects when the player enters or exits specific areas and displays
appropriate informational messages on the HUD.

Main Features:
    1. Collision detection with area trigger zones
    2. Automatic message display when player enters an area
    3. Message clearing when player exits an area
    4. Configurable line numbers per area type
    5. Integration with add_info_text messaging system

Setup:
    Connect to Logic Bricks as Python controller with module 'message_area_info.main'
    Requires a Collision sensor (any type) on the trigger object
    Requires 'area' property on the trigger object with valid area name

Configurable Variables:
    areas (dict): Mapping of area names to line numbers in the text JSON

Notes:
    - Area names: restoration, exhibition, library, storage, reception,
      service_entrance, main_entrance
    - Sends messages to 'add_info_text' subject with Game.Controller as target
    - Uses 'clear_info_text' message to clear info when exiting
    - Message format: 'info.show|info_text|{line_num}|field=info_text'

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
__description__ = "Manages area-based info messages triggered by player collision"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main(cont):
    owner = cont.owner
    
    # Initialization
    if "initialized" not in owner:
        owner["initialized"] = True
        owner["player_inside"] = False
        # print(f"[AreaInfo] {owner.name} ready - Area: {owner.get('area', 'unknown')}")
        return
    
    # Find Collision sensor
    coll_sensor = None
    for sensor in cont.sensors:
        # In UPBGE 0.44, check like this:
        if hasattr(sensor, 'positive'):
            coll_sensor = sensor
            break
    
    if not coll_sensor:
        return
    
    # Detect player
    player_colliding = coll_sensor.positive
    
    # State change
    if player_colliding and not owner["player_inside"]:
        owner["player_inside"] = True
        show_info(owner, True)
        # print(f"[AreaInfo] Player ENTERED {owner.name}")
    
    elif not player_colliding and owner["player_inside"]:
        owner["player_inside"] = False
        show_info(owner, False)
        # print(f"[AreaInfo] Player EXITED {owner.name}")

# =============================================================================
# INFO DISPLAY FUNCTIONS
# =============================================================================
def show_info(owner, show):
    """Shows or hides information"""
    if show:
        area = owner.get("area", "")
        if area:
            line_num = get_line_number(area)
            message = f"info.show|info_text|{line_num}|field=info_text"
            owner.sendMessage("add_info_text", message, "Game.Controller")
    else:
        owner.sendMessage("clear_info_text", "", "Game.Controller")

def get_line_number(area):
    """Line numbers by area"""
    areas = {
        'restoration': 23,
        'exhibition': 24,
        'library': 25,
        'storage': 26,
        'reception': 27,
        'service_entrance': 28,
        'main_entrance': 29
    }
    return areas.get(area, 0)