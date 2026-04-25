"""
game_init.py

Initializes game with welcome messages and information display.

This script handles game initialization with delayed message sending,
including a central welcome message and informational text with timers.

Main Features:
    1. Send immediate central welcome message on game start
    2. Send delayed information message (0.5 seconds)
    3. Automatic clearing of central message after 3 seconds
    4. Timer system for delayed and scheduled actions
    5. Single initialization guard to prevent duplicate messages

Setup:
    Connect to Logic Bricks as Python controller with module 'game_init.main'
    Requires a Game.Controller object in the scene to receive messages

Configurable Variables:
    None (all timings are hardcoded: center_clear=3.0s, info_delay=0.5s)

Notes:
    - Messages are sent via 'add_info_text' subject to 'Game.Controller'
    - Center message uses line 1, info message uses line 3
    - Uses bge.logic.timers list for scheduling
    - Initialization only runs once per game session
    - Timer functions are executed automatically each frame

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
__description__ = "Initializes game with welcome messages and information display"

# =============================================================================
# IMPORTS
# =============================================================================
import bge

# =============================================================================
# GLOBAL STATE
# =============================================================================
# Variable to control if already initialized
initialized = False

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main(controller):
    """Combines initialization and timers in a single script"""
    global initialized
    
    # Initialization (only once)
    if not initialized:
        initialize_game(controller)
        initialized = True
    
    # Timer updates (each frame)
    update_timers()

# =============================================================================
# INITIALIZATION FUNCTIONS
# =============================================================================
def initialize_game(controller):
    """Initializes welcome messages with delay"""
    own = controller.owner
    
    print("Initializing messages...")
    
    # Message 1: Central welcome (immediate)
    own.sendMessage(
        "add_info_text",
        "info.show|center_text|1|field=center_text",
        "Game.Controller"
    )
    print("Central message sent (immediate)")
    
    # Initialize timer system
    if not hasattr(bge.logic, 'timers'):
        bge.logic.timers = []
    
    # Timer to clear central message after 3 seconds
    bge.logic.timers.append({
        'function': lambda: own.sendMessage(
            "add_info_text",
            "info.clear|field=center_text",
            "Game.Controller"
        ),
        'time': 3.0,
        'start_time': bge.logic.getRealTime(),
        'name': 'clear_center'
    })
    
    # Timer to SEND info message after 0.5 seconds
    bge.logic.timers.append({
        'function': lambda: send_info_message(own),
        'time': 0.5,  # 0.5 second delay
        'start_time': bge.logic.getRealTime(),
        'name': 'send_info'
    })

def send_info_message(own):
    """Sends the delayed information message"""
    own.sendMessage(
        "add_info_text",
        "info.show|info_text|3|field=info_text",
        "Game.Controller"
    )
    print("Info message sent (with delay)")
    

# =============================================================================
# TIMER UPDATE FUNCTION
# =============================================================================
def update_timers():
    """Updates timers each frame"""
    if hasattr(bge.logic, 'timers') and bge.logic.timers:
        current_time = bge.logic.getRealTime()
        active_timers = []
        
        for timer in bge.logic.timers:
            # Initialize start_time if it doesn't exist
            if 'start_time' not in timer:
                timer['start_time'] = current_time
            
            elapsed = current_time - timer['start_time']
            
            if elapsed >= timer['time']:
                try:
                    # Execute timer function
                    timer['function']()
                    print(f"Timer '{timer.get('name', 'unnamed')}' executed ({elapsed:.1f}s)")
                except Exception as e:
                    print(f"Error in timer: {e}")
            else:
                # Keep timer active
                active_timers.append(timer)
        
        bge.logic.timers = active_timers