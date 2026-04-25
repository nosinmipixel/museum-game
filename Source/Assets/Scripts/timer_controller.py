"""
timer_controller.py

Timer controller for quiz system (not NPCs)

This script manages a timer for the quiz system, tracking elapsed time through
the game state system.

Main Features:
    1. Tracks quiz timer using game state system
    2. Updates timer based on delta time each frame
    3. Provides debug output at configurable intervals

Setup:
    Owner: 'Task.Controller'
    Logic Bricks: Always (True) sensor connected to Python controller/module 'timer_controller.main'
    Should be called every frame for continuous timer updates

Configurable Variables:
    DEBUG_TIMER (bool): Enable debug output (default: False)
    DEBUG_INTERVAL (float): Seconds between debug messages (default: 2.0)

Notes:
    - Requires game_access module for state management
    - Timer is stored in game state as 'timer_quiz'
    - Timer increments by delta time each frame

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
__description__ = "Quiz timer controller with game state integration"

# =============================================================================
# IMPORTS AND CONFIGURATION
# =============================================================================
import bge
from bge import logic
import game_access

DEBUG_TIMER = False
DEBUG_INTERVAL = 2.0

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main(cont):
    """Main function using game_access exclusively"""
    # Get delta time
    delta_time = 1.0 / logic.getLogicTicRate() if logic.getLogicTicRate() > 0 else 0.016
    
    # Get game state via game_access
    state = game_access.get_state()
    
    # Ensure game state is available
    if not state:
        error_msg = "ERROR: game_access.get_state() returned None. Timer cannot function."
        if DEBUG_TIMER:
            print(error_msg)
        return
    
    # Increment timer in game_state
    state.timer_quiz += delta_time
    
    # DEBUG: Show progress
    if DEBUG_TIMER:
        if not hasattr(logic, 'last_debug_time'):
            logic.last_debug_time = 0
            
        current_time = logic.getRealTime()
        if current_time - logic.last_debug_time > DEBUG_INTERVAL:
            print(f"Timer_quiz (GameState): {state.timer_quiz:.1f}s")
            logic.last_debug_time = current_time