"""
save_system.py

This script handles game save and load functionality using the centralized GameManager
architecture. It manages persistent storage of game state, player data, and progress.

Main Features:
    1. Saves complete game state to JSON file
    2. Loads game data from save file into GameManager
    3. Provides save file deletion functionality
    4. Checks for existing save files
    5. Retrieves save file information summary
    6. Includes version tracking and timestamp data

Setup:
    Connect in Logic Bricks as Python controller/module 'save_system.save_game' or 'save_system.load_game'
    Requires game_access module for GameManager instance

Configurable Variables:
    None (save path is hardcoded to '//savegame.json')

Notes:
    - Save file location is relative to the .blend file
    - Uses JSON format with UTF-8 encoding
    - Requires game_access.get_game() to return valid GameManager instance
    - Timestamp uses bge.logic.getRealTime()

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
__description__ = "Save/load system using centralized GameManager architecture"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic
import json
import os
import copy
import game_access

# =============================================================================
# FILE PATH UTILITIES
# =============================================================================
def get_save_path():
    """Return the save file path"""
    return logic.expandPath('//savegame.json')

# =============================================================================
# CORE SAVE/LOAD FUNCTIONS
# =============================================================================
def save_game():
    """Save the game using the new architecture"""
    
    # 1. Get GameManager instance
    game = game_access.get_game()
    if not game:
        print("Cannot save: GameManager not available")
        return False
    
    # 2. Get data using GameManager
    save_data = game.save_data()
    
    # 3. Add additional information
    save_data['version'] = '2.0'
    save_data['timestamp'] = logic.getRealTime()
    
    # 4. Save to file
    try:
        save_path = get_save_path()
        with open(save_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2, ensure_ascii=False)
        
        print(f"Game saved to: {save_path}")
        print(f"   - Budget: {game.state.budget}")
        print(f"   - Skill level: {game.player.skills}")
        print(f"   - NPC progress: {game.state.task_quiz_total}/{game.state.npc_turn}")
        
        return True
        
    except Exception as e:
        print(f"Error saving game: {e}")
        return False

def load_game():
    """Load the game using the new architecture"""
    
    save_path = get_save_path()
    
    # 1. Verify file exists
    if not os.path.exists(save_path):
        print(f"No save file found at: {save_path}")
        return False
    
    try:
        # 2. Read file
        with open(save_path, 'r', encoding='utf-8') as f:
            save_data = json.load(f)
        
        print(f"Loading game version: {save_data.get('version', 'unknown')}")
        
        # 3. Get GameManager instance
        game = game_access.get_game()
        if not game:
            print("Cannot load: GameManager not available")
            return False
        
        # 4. Load data into GameManager
        game.load_data(save_data)
        
        print("Game loaded successfully")
        print(f"   - Budget: {game.state.budget}")
        print(f"   - Skill level: {game.player.skills}")
        print(f"   - Progress: {game.state.task_quiz_total} tasks completed")
        
        return True
        
    except Exception as e:
        print(f"Error loading game: {e}")
        return False

# =============================================================================
# SAVE FILE MANAGEMENT
# =============================================================================
def delete_save():
    """Delete the save file"""
    try:
        save_path = get_save_path()
        if os.path.exists(save_path):
            os.remove(save_path)
            print("Save file deleted")
            return True
        else:
            print("No save file to delete")
            return False
    except Exception as e:
        print(f"Error deleting save file: {e}")
        return False

def check_saved_game_exists():
    """Check if a saved game exists"""
    return os.path.exists(get_save_path())

def get_save_info():
    """Get save file information"""
    if not check_saved_game_exists():
        return None
    
    try:
        with open(get_save_path(), 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return {
            'timestamp': data.get('timestamp', 0),
            'budget': data.get('state', {}).get('budget', 0),
            'skills': data.get('player', {}).get('skills', 1),
            'level': data.get('state', {}).get('current_level', 1),
            'tasks': data.get('state', {}).get('task_total', 0)
        }
    except:
        return None