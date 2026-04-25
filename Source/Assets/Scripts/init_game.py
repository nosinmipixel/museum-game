"""
init_game.py

Unified game initialization script for single state management.

This script handles complete game initialization including GameManager setup,
language loading, saved game loading, and component activation.

Main Features:
    1. Initialize GameManager singleton from game_data.py
    2. Load language from globalDict if available
    3. Check for and load saved games via save_system
    4. Set initial game values for new games
    5. Synchronize properties to Game.Controller for compatibility
    6. Activate game components (HUD, sound, NPCs, quiz system)
    7. Provide debug info function for runtime inspection

Setup:
    Connect to Logic Bricks as Python controller with module 'init_game.init_game'
    Optional: Connect debug_info to a keyboard sensor for debugging

Configurable Variables:
    None (all configuration is handled internally)

Notes:
    - Requires game_data.py with GameManager class
    - Requires save_system.py with check_saved_game_exists() and load_game()
    - Requires game_access.py for get_game() function
    - Initialization runs only once (guarded by owner flag)
    - Synchronizes key properties to Game.Controller object
    - Debug info can be triggered by connected keyboard sensor

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
__description__ = "Unified game initialization script for single state management"

# =============================================================================
# IMPORTS
# =============================================================================
from bge import logic

# =============================================================================
# MAIN INITIALIZATION FUNCTION
# =============================================================================
def init_game(cont):
    """Complete game initialization - Single state"""
    owner = cont.owner
    
    # Only execute once
    if "game_initialized" in owner and owner["game_initialized"]:
        return
    
    print("Initializing game (unified architecture)...")
    
    try:
        # 1. Initialize GameManager (new architecture)
        from game_data import GameManager
        game = GameManager.get()
        
        # 2. Load language from globalDict if exists
        if 'language' in logic.globalDict:
            game.state.language = logic.globalDict.get('language')
            print(f"Language: {game.state.language}")
        
        # 3. Load saved game IF EXISTS
        from save_system import check_saved_game_exists, load_game
        if check_saved_game_exists():
            print("Loading saved game...")
            load_game()  # This will overwrite default values
        else:
            print("Starting new game")
            # Set initial values
            game.state.budget = 100000
            game.player.skills = 1
            game.state.quiz_active = True
            game.state.task_quiz = False
            game.state.task_quiz_total = 0
        
        # 4. Synchronize properties for compatibility
        owner['is_initialized'] = True
        owner['game_version'] = '3.0-unified'
        owner['budget'] = game.state.budget
        owner['skills'] = game.player.skills
        owner['quiz_active'] = game.state.quiz_active
        owner['task_quiz'] = game.state.task_quiz
        owner['task_quiz_total'] = game.state.task_quiz_total
        owner['language'] = game.state.language
        
        # 5. Mark as initialized
        owner["game_initialized"] = True
        logic.game_initialized = True
        
        print(f"Game initialized successfully")
        print(f"   - Budget: {game.state.budget}")
        print(f"   - Skills: {game.player.skills}")
        print(f"   - Quiz active: {game.state.quiz_active}")
        
        # 6. Optional: Activate game components
        activate_game_components(owner)
        
    except Exception as e:
        print(f"Error in initialization: {e}")
        import traceback
        traceback.print_exc()
        owner['initialization_error'] = str(e)

# =============================================================================
# GAME COMPONENTS ACTIVATION
# =============================================================================
def activate_game_components(owner):
    """Activate game systems after initialization"""
    print("Activating game components...")
    
    # Example: Activate dialog system if NPCs exist
    from game_access import get_game
    game = get_game()
    if game and game.state.quiz_active:
        print("   - QUIZ system activated")
    
    # Additional activations can be added here

# =============================================================================
# DEBUG INFORMATION FUNCTION
# =============================================================================
def debug_info(cont):
    """Display debug information"""
    if cont.sensors[0].positive:
        import game_access
        game = game_access.get_game()
        if game:
            print("=== DEBUG INFO ===")
            print(f"Budget: {game.state.budget}")
            print(f"Health: {game.player.health}")
            print(f"Skills: {game.player.skills}")
            print(f"NPC Turn: {game.state.npc_turn}")
            print(f"Dialog active: {game.state.dialog_active}")
            print(f"Quiz active: {game.state.quiz_active}")
            print(f"Task quiz total: {game.state.task_quiz_total}")
            print("==================")