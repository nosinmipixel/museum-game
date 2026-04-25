"""
temperature_controller.py

Temperature and humidity controller with trend analysis

This script manages climate simulation (temperature and humidity) in the game world.
It responds to door states, updates values over time, calculates trends, and
determines warning levels based on current conditions.

Main Features:
    1. Temperature and humidity simulation with realistic change rates
    2. Increases values when doors are opened, decreases when closed
    3. Tracks trends (increasing/decreasing) for each parameter
    4. Calculates climate warning levels (OK, improving, worsening)
    5. Validates if conditions are within ideal ranges
    6. Frame-based timing independent of frame rate
    7. Integration with game state for persistence

Setup:
    Owner: 'Game.Controller'
    Logic Bricks: Sensor Always (True) connected to Python controller/module 'temperature_controller.manage_climate'
    Should be called every frame for continuous climate simulation

Configurable Variables:
    temp_max (float): Maximum temperature limit (default: 35.0)
    hr_max (float): Maximum humidity limit (default: 75.0)
    temp_ideal (float): Ideal temperature target (default: 21.0)
    hr_ideal (float): Ideal humidity target (default: 50.0)

Notes:
    - Requires game_access module for state management
    - Uses state properties: doors_opened, temp_raw, hr_raw, temp_previous, hr_previous
    - Updates occur once per second (based on frame rate)
    - Ideal range: Temperature 20-22°C, Humidity 45-55%
    - Climate warning levels: 0=OK (green), 1=Improving (orange), 2=Worsening (red)

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
__description__ = "Climate controller for temperature and humidity with trend analysis"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic

# Import game_access for new architecture
try:
    import game_access
    HAS_GAME_ACCESS = True
except ImportError:
    HAS_GAME_ACCESS = False
    print("[temperature_controller] Error: game_access not found")

# =============================================================================
# MAIN CLIMATE MANAGEMENT FUNCTION
# =============================================================================
def manage_climate():
    if not HAS_GAME_ACCESS:
        print("[temperature_controller] ERROR: game_access not available")
        return
    
    game = game_access.get_game()
    if not game:
        print("[temperature_controller] ERROR: Could not get game instance")
        return
    
    state = game.state
    
    # Maximum limits
    temp_max = 35.0
    hr_max = 75.0
    
    # Ideal limits
    temp_ideal = 21.0
    hr_ideal = 50.0
    
    # Get properties from game state
    doors_opened = getattr(state, 'doors_opened', 0)
    temp_raw = getattr(state, 'temp_raw', 21.0)
    hr_raw = getattr(state, 'hr_raw', 50.0)
    
    # SAVE PREVIOUS VALUES BEFORE UPDATING
    temp_previous = state.temp_previous
    hr_previous = state.hr_previous
    
    # Frame-based timer logic
    if not hasattr(state, 'frame_counter'):
        state.frame_counter = 0
    
    frames_per_second = logic.getLogicTicRate()
    state.frame_counter += 1
    
    # Update every second (adjust based on frame rate)
    if state.frame_counter >= frames_per_second:
        state.frame_counter = 0
        
        # INCREASE LOGIC
        if doors_opened > 0:
            # Increase values and use min() to ensure they don't exceed limits
            temp_raw = min(temp_max, temp_raw + 0.1)
            hr_raw = min(hr_max, hr_raw + 0.1)
            
        # DECREASE LOGIC
        elif doors_opened == 0:
            if temp_raw > temp_ideal:
                temp_raw = max(temp_ideal, temp_raw - 0.1)
            
            if hr_raw > hr_ideal:
                hr_raw = max(hr_ideal, hr_raw - 0.1)
        
        # CALCULATE TREND (INCREASING/DECREASING)
        state.temp_trending_up = (temp_raw > temp_previous)
        state.hr_trending_up = (hr_raw > hr_previous)
        
        # CALCULATE CLIMATE WARNING LEVEL
        # 0 = OK (within range)
        # 1 = Out of range but decreasing (improving)
        # 2 = Out of range and increasing (worsening)
        temp_ok = 20.0 <= temp_raw <= 22.0
        hr_ok = 45.0 <= hr_raw <= 55.0
        
        if temp_ok and hr_ok:
            state.climate_warning_level = 0  # Green - OK
        elif not state.temp_trending_up and not state.hr_trending_up:
            state.climate_warning_level = 1  # Orange - Improving
        else:
            state.climate_warning_level = 2  # Red - Worsening
        
        # Update state properties
        state.temp_raw = temp_raw
        state.hr_raw = hr_raw
        state.temp_previous = temp_raw      # Save for next comparison
        state.hr_previous = hr_raw          # Save for next comparison
        
        # TEMPERATURE AND HUMIDITY VERIFICATION
        # Temperature: must be between 20°C and 22°C
        state.temp_ok = temp_ok
        
        # Relative humidity: must be between 45% and 55%
        state.hr_ok = hr_ok
        
        # Optional debug - uncomment to see values
        if hasattr(logic, 'DEBUG') and logic.DEBUG:
            print(f"[climate] Doors: {doors_opened}, "
                  f"Temp: {temp_raw:.1f}C ({'up' if state.temp_trending_up else 'down'}), "
                  f"HR: {hr_raw:.1f}% ({'up' if state.hr_trending_up else 'down'}), "
                  f"Warning: {state.climate_warning_level}")