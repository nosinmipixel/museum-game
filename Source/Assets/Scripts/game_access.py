"""
game_access.py

Provides a simplified access layer to GameManager for game state and player data.

This script offers convenience functions for accessing and modifying game state,
player statistics, inventory data, NPC management, quiz progress, and cat pet system.

Main Features:
    1. Access game, player, state, and inventory objects
    2. Manage player stamina with drain and restore functions
    3. Track collection statistics by historical period
    4. Manage quiz progress and NPC state synchronization
    5. Handle inventory object synchronization between systems
    6. Control cat pet system with food items and timer
    7. Force inventory sync and HUD cleanup utilities
    8. Task completion detection with win effects

Setup:
    Import and use functions directly: game_access.get_game(), game_access.get_state(), etc.

Configurable Variables:
    None (all functions are self-contained)

Notes:
    - Requires game_data.py with GameManager class
    - Uses global logic flags for inventory and overlay states
    - NPC11 is excluded from automatic progression (handled by restoration system)
    - Stamina drain rates: base_rate (default 1.0), doors_rate (default 50.0)
    - Cat food system includes visual HUD and spawn point management
    - Game completion triggers matrix effect and victory message

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
__description__ = "Simplified access layer to GameManager for game state and player data"

# =============================================================================
# IMPORTS
# =============================================================================
from bge import logic
import bge

# =============================================================================
# BASIC ACCESS FUNCTIONS
# =============================================================================
def get_game():
    """Get game instance (GameManager)"""
    try:
        from game_data import GameManager
        return GameManager.get()
    except ImportError as e:
        print(f"Error importing GameManager: {e}")
        return None

def get_player():
    """Get player data"""
    game = get_game()
    return game.player if game else None

def get_state():
    """Get game state"""
    game = get_game()
    return game.state if game else None

def get_inventory():
    """Get inventory"""
    state = get_state()
    return state.inventory if state else None

# =============================================================================
# QUICK ACCESS FUNCTIONS
# =============================================================================
def get_budget():
    """Get budget"""
    state = get_state()
    return state.budget if state else 0

def set_budget(value):
    """Set budget"""
    state = get_state()
    if state:
        state.budget = value

def get_skills():
    """Get player skills"""
    player = get_player()
    return player.skills if player else 1

def set_skills(value):
    """Set player skills"""
    player = get_player()
    if player:
        player.skills = value

# =============================================================================
# STAMINA SYSTEM FUNCTIONS
# =============================================================================
def get_stamina():
    """Get current player stamina"""
    player = get_player()
    return player.stamina if player else 100

def get_max_stamina():
    """Get maximum player stamina"""
    player = get_player()
    return player.max_stamina if player else 100

def modify_stamina(amount):
    """
    Modify stamina (positive to recover, negative to lose)
    Returns new stamina value
    """
    player = get_player()
    if player:
        player.stamina = max(0, min(player.max_stamina, player.stamina + amount))
        return player.stamina
    return 0

def get_stamina_percentage():
    """Get stamina percentage (0-100)"""
    player = get_player()
    if player and player.max_stamina > 0:
        return (player.stamina / player.max_stamina) * 100
    return 100

def get_stamina_drain_rates():
    """
    Get stamina drain rates
    Returns: {'base_rate': X, 'doors_rate': Y}
    """
    player = get_player()
    if player:
        return {
            'base_rate': getattr(player, 'stamina_drain_rate', 1.0),
            'doors_rate': getattr(player, 'stamina_drain_doors', 50.0)
        }
    return {'base_rate': 1.0, 'doors_rate': 50.0}

def set_stamina_drain_rates(base_rate=None, doors_rate=None):
    """Configure stamina drain rates"""
    player = get_player()
    if player:
        if base_rate is not None:
            player.stamina_drain_rate = base_rate
        if doors_rate is not None:
            player.stamina_drain_doors = doors_rate
        return True
    return False

def restore_stamina(amount=None, percentage=None):
    """
    Restore stamina
    - amount: fixed amount to restore
    - percentage: percentage of maximum to restore
    """
    player = get_player()
    if not player:
        return 0
    
    if percentage is not None:
        amount = (player.max_stamina * percentage) / 100.0
    elif amount is None:
        amount = player.max_stamina * 0.5  # Default: 50%
    
    current = player.stamina
    player.stamina = min(player.max_stamina, player.stamina + amount)
    recovered = player.stamina - current
    
    print(f"*** STAMINA RESTORED: +{recovered:.1f} ({player.stamina:.1f}/{player.max_stamina}) ***")
    return recovered

# =============================================================================
# NPC TURN FUNCTIONS
# =============================================================================
def get_npc_turn():
    """Get NPC turn"""
    state = get_state()
    return state.npc_turn if state else 1

def set_npc_turn(value):
    """Set NPC turn"""
    state = get_state()
    if state:
        state.npc_turn = value

# =============================================================================
# DIALOG FUNCTIONS
# =============================================================================
def get_dialog_active():
    """Get dialog active state"""
    state = get_state()
    return state.dialog_active if state else False

def set_dialog_active(value):
    """Set dialog active state"""
    state = get_state()
    if state:
        state.dialog_active = value

def get_current_npc_id():
    """Get current NPC ID"""
    state = get_state()
    return state.current_npc_id if state else 0

def set_current_npc_id(npc_id):
    """Set current NPC ID"""
    state = get_state()
    if state:
        state.current_npc_id = npc_id

# =============================================================================
# BUGS TOTAL FUNCTIONS
# =============================================================================
def get_bugs_total():
    """Get total bugs eliminated"""
    state = get_state()
    return state.bugs_total if state else 0

def set_bugs_total(value):
    """Set total bugs eliminated"""
    state = get_state()
    if state:
        state.bugs_total = value

# =============================================================================
# COLLECTION FUNCTIONS
# =============================================================================
def get_collection_stats():
    """Get collection statistics"""
    state = get_state()
    if not state:
        return {}
    
    inventoried, restored, exhibited = state.update_collection_stats()
    
    return {
        'total_items': state.collection_items_total,
        'inventoried': inventoried,
        'restored': restored,
        'exhibited': exhibited,
        'by_period': {
            'pal': state.total_pal,
            'neo': state.total_neo,
            'bronze': state.total_bronze,
            'iberian': state.total_iberian,
            'roman': state.total_roman
        }
    }

# =============================================================================
# HUD UTILITY FUNCTION
# =============================================================================
def update_hud_directly():
    """Update HUD directly from classes"""
    game = get_game()
    if not game:
        return None
    
    state = game.state
    player = game.player
    
    # Update HUD texts
    game.hud_text.budget_text = f"Budget: {state.budget}"
    game.hud_text.skills_text = f"Skills: {player.skills}"
    
    # Calculate statistics
    state.update_collection_stats()
    
    return game.hud_text

# =============================================================================
# GENERIC COMPATIBILITY FUNCTIONS
# =============================================================================
def get_game_property(prop_name):
    """Get any property by name"""
    state = get_state()
    player = get_player()
    
    # Search in state first
    if state and hasattr(state, prop_name):
        return getattr(state, prop_name)
    
    # Search in player
    if player and hasattr(player, prop_name):
        return getattr(player, prop_name)
    
    return None

def set_game_property(prop_name, value):
    """Set any property by name"""
    state = get_state()
    player = get_player()
    
    # Try in state
    if state and hasattr(state, prop_name):
        setattr(state, prop_name, value)
        return True
    
    # Try in player
    if player and hasattr(player, prop_name):
        setattr(player, prop_name, value)
        return True
    
    return False

# =============================================================================
# QUIZ FUNCTIONS
# =============================================================================
def update_quiz_progress(npc_id, quiz_success):
    """Updates quiz progress and task_quiz if needed"""
    if not quiz_success:
        return
    
    game = get_game()
    if not game:
        return
    
    state = game.state
    
    # Increment correct quiz counter
    current_total = getattr(state, 'task_quiz_total', 0)
    state.task_quiz_total = current_total + 1
    
    # Check if 70% (7 out of 10) is reached
    if state.task_quiz_total >= 7:
        state.task_quiz = True
        print(f"QUIZ completed: {state.task_quiz_total}/10 - task_quiz=True")
    
    print(f"[game_access] Quiz progress updated: {state.task_quiz_total}/10")

def get_quiz_result_for_npc(npc_id):
    """Gets quiz result for a specific NPC"""
    try:
        # 1. Find NPC object directly
        scene = logic.getCurrentScene()
        npc = scene.objects.get(f'npc{npc_id}')
        
        if npc:
            # Check object properties
            success = npc.get('quiz_success', False) or npc.get('_quiz_success', False)
            return success
    except Exception as e:
        print(f"[game_access] Error getting QUIZ result for NPC{npc_id}: {e}")
    
    return False

def mark_npc_quiz_completed(npc_id, success=True):
    """Marks an NPC as completed (success or failure)"""
    try:
        scene = logic.getCurrentScene()
        npc = scene.objects.get(f'npc{npc_id}')
        
        if npc:
            # Set properties
            npc['quiz_success'] = success
            npc['_quiz_success'] = success
            
            # If success, also mark as inactive
            if success:
                npc['active'] = False
            
            print(f"[game_access] NPC{npc_id} marked as {'COMPLETED (success)' if success else 'failure'}")
            return True
    except Exception as e:
        print(f"[game_access] Error marking NPC{npc_id}: {e}")
    
    return False

def mark_quiz_success(npc_id, item_type=None, item_id=None):
    """
    Marks a QUIZ as successful and updates all dependencies
    SIMPLIFIED VERSION: Only updates progress, NPC is handled in npc_logic
    """
    try:
        # EXCLUDE NPC11 - Do not process here
        if npc_id == 11:
            print(f"[game_access] NPC11 excluded from mark_quiz_success")
            return True
        
        # 1. Update quiz progress
        update_quiz_progress(npc_id, True)
        
        # 2. CRITICAL: Reset timer_quiz so next NPC waits for NPC_INTERVAL_TIME
        state = get_state()
        if state:
            state.timer_quiz = 0.0
            print(f"[game_access] Timer reset to 0.0 for next NPC")
        
        print(f"[game_access] QUIZ progress updated for NPC{npc_id}")
        return True
        
    except Exception as e:
        print(f"[game_access] Error in mark_quiz_success: {e}")
        return False

# =============================================================================
# OBJECT SYNCHRONIZATION FUNCTIONS (CRITICAL FOR INVENTORY)
# =============================================================================
def sync_object_properties(item_type, item_id):
    """
    Synchronizes object properties between all systems
    Ensures 'world' and 'card' objects have the same properties
    """
    try:
        game = get_game()
        if not game:
            return False
        
        # 1. Search in inventory
        inventory = game.state.inventory
        collection_items = inventory.get("collection_items", {})
        
        restored_value = 0
        ubication_value = 0
        exhibition_value = 0
        
        # Find object in inventory
        for item in collection_items.get(item_type, []):
            if item.get("item_id") == item_id:
                restored_value = item.get("restored", 0)
                ubication_value = item.get("ubication", 0)
                exhibition_value = item.get("exhibition", 0)
                break
        
        # 2. Synchronize with objects in scene
        scene = logic.getCurrentScene()
        if scene:
            # Find all objects with this item_type/item_id
            for obj in scene.objects:
                try:
                    if (obj.get("item_type", "") == item_type and 
                        obj.get("item_id", 0) == item_id):
                        
                        # Update all important properties
                        obj["restored"] = restored_value
                        obj["ubication"] = ubication_value
                        obj["exhibition"] = exhibition_value
                        
                        print(f"[game_access] Synchronized {obj.name}: "
                              f"restored={restored_value}, "
                              f"ubication={ubication_value}, "
                              f"exhibition={exhibition_value}")
                except Exception as e:
                    print(f"[game_access] Error synchronizing object {obj.name}: {e}")
        
        print(f"[game_access] Synchronization completed for {item_type}#{item_id}")
        return True
        
    except Exception as e:
        print(f"[game_access] Error in sync_object_properties: {e}")
        return False

def find_and_update_object(item_type, item_id, properties_dict):
    """
    Finds and updates ALL related objects (world and card)
    IMPROVED VERSION: Does not overwrite unspecified properties
    """
    try:
        scene = logic.getCurrentScene()
        if not scene:
            return False
        
        updated_count = 0
        
        # FIRST: Update object in game_state inventory
        game = get_game()
        if game:
            inv = game.state.inventory
            coll = inv.get("collection_items", {}).get(item_type, [])
            for item in coll:
                if item.get("item_id") == item_id:
                    # Update only specified properties
                    for prop, value in properties_dict.items():
                        item[prop] = value
                    print(f"[game_access] Inventory updated: {item_type}#{item_id} -> {properties_dict}")
                    break
        
        # SECOND: Update objects in scene
        # Search by exact name for world objects
        period_capitalized = item_type.capitalize() if item_type != 'bronze' else 'Bronze'
        world_obj_name = f"Object.World.{period_capitalized}.{item_id}"
        world_obj = scene.objects.get(world_obj_name)
        
        if world_obj:
            # Save current values first
            current_state = {
                'restored': world_obj.get("restored", 0),
                'ubication': world_obj.get("ubication", 0),
                'exhibition': world_obj.get("exhibition", 0)
            }
            
            # Apply only changes, preserve other values
            for prop, value in properties_dict.items():
                world_obj[prop] = value
            
            print(f"[game_access] World updated: {world_obj_name} ({current_state} -> {properties_dict})")
            updated_count += 1
        
        # Search by exact name for card objects
        card_obj_name = f"Object.{period_capitalized}.{item_id}"
        card_obj = scene.objects.get(card_obj_name)
        
        if card_obj:
            # Save current values first
            current_state = {
                'restored': card_obj.get("restored", 0),
                'ubication': card_obj.get("ubication", 0),
                'exhibition': card_obj.get("exhibition", 0)
            }
            
            # Apply only changes, preserve other values
            for prop, value in properties_dict.items():
                card_obj[prop] = value
            
            print(f"[game_access] Card updated: {card_obj_name} ({current_state} -> {properties_dict})")
            updated_count += 1
        
        # Search by properties item_type/item_id (for generic objects like Quiz)
        for obj in scene.objects:
            try:
                if (obj.get("item_type", "") == item_type and 
                    obj.get("item_id", 0) == item_id):
                    
                    # Avoid duplicates already updated
                    if obj not in [world_obj, card_obj]:
                        for prop, value in properties_dict.items():
                            obj[prop] = value
                        updated_count += 1
                        print(f"[game_access] Generic updated: {obj.name}")
            except:
                pass
        
        print(f"[game_access] {updated_count} objects synchronized for {item_type}#{item_id}")
        return updated_count > 0
        
    except Exception as e:
        print(f"[game_access] Error in find_and_update_object: {e}")
        return False

def get_object_state(item_type, item_id):
    """
    Gets current state of an object from inventory
    """
    try:
        game = get_game()
        if not game:
            return {}
        
        inventory = game.state.inventory
        collection_items = inventory.get("collection_items", {})
        
        for item in collection_items.get(item_type, []):
            if item.get("item_id") == item_id:
                return {
                    'restored': item.get("restored", 0),
                    'ubication': item.get("ubication", 0),
                    'exhibition': item.get("exhibition", 0),
                    'item_type': item.get("item_type", ""),
                    'item_id': item.get("item_id", 0)
                }
        
        return {}
        
    except Exception as e:
        print(f"[game_access] Error getting object state: {e}")
        return {}

def force_inventory_sync():
    """
    Forces complete inventory synchronization with all objects
    IMPROVED VERSION: Respects current object values
    """
    try:
        game = get_game()
        if not game:
            return False
        
        inventory = game.state.inventory
        collection_items = inventory.get("collection_items", {})
        
        total_synced = 0
        
        for period, items in collection_items.items():
            for item in items:
                item_type = item.get("item_type", period)
                item_id = item.get("item_id", 0)
                
                if item_type and item_id:
                    # Get CURRENT VALUES from objects in scene
                    scene = logic.getCurrentScene()
                    if scene:
                        period_capitalized = item_type.capitalize() if item_type != 'bronze' else 'Bronze'
                        
                        # Find world object
                        world_name = f"Object.World.{period_capitalized}.{item_id}"
                        world_obj = scene.objects.get(world_name)
                        
                        # Find card object
                        card_name = f"Object.{period_capitalized}.{item_id}"
                        card_obj = scene.objects.get(card_name)
                        
                        # Prioritize scene object values over inventory
                        final_ubication = item.get("ubication", 0)
                        final_exhibition = item.get("exhibition", 0)
                        final_restored = item.get("restored", 0)
                        
                        if world_obj:
                            world_ubication = world_obj.get("ubication", -1)
                            world_exhibition = world_obj.get("exhibition", -1)
                            world_restored = world_obj.get("restored", -1)
                            
                            if world_ubication != -1 and world_ubication != final_ubication:
                                print(f"[game_access] World has different ubication: {final_ubication} -> {world_ubication}")
                                final_ubication = world_ubication
                            
                            if world_exhibition != -1 and world_exhibition != final_exhibition:
                                final_exhibition = world_exhibition
                            
                            if world_restored != -1 and world_restored != final_restored:
                                final_restored = world_restored
                        
                        if card_obj:
                            card_ubication = card_obj.get("ubication", -1)
                            card_exhibition = card_obj.get("exhibition", -1)
                            card_restored = card_obj.get("restored", -1)
                            
                            if card_ubication != -1 and card_ubication != final_ubication:
                                print(f"[game_access] Card has different ubication: {final_ubication} -> {card_ubication}")
                                final_ubication = card_ubication
                        
                        # Update item in inventory with final values
                        item["ubication"] = final_ubication
                        item["exhibition"] = final_exhibition
                        item["restored"] = final_restored
                        
                        # Create properties dictionary for synchronization
                        properties = {
                            'ubication': final_ubication,
                            'exhibition': final_exhibition,
                            'restored': final_restored
                        }
                        
                        # Synchronize this object (only if changes)
                        if find_and_update_object(item_type, item_id, properties):
                            total_synced += 1
                            print(f"[game_access] Item synchronized: {item_type}#{item_id} -> ubication={final_ubication}")
        
        print(f"[game_access] Force sync completed: {total_synced} objects")
        
        # UPDATE COLLECTION STATISTICS
        if game and hasattr(game.state, 'update_collection_stats'):
            inventoried, restored, exhibited = game.state.update_collection_stats()
            print(f"[game_access] Statistics updated: inventoried={inventoried}, restored={restored}, exhibited={exhibited}")
        
        return True
        
    except Exception as e:
        print(f"[game_access] Error in force_inventory_sync: {e}")
        return False

def sync_to_controller(controller):
    """Synchronizes data with Game Controller"""
    game = get_game()
    return game.sync_to_controller(controller) if game else False

# =============================================================================
# TASK COMPLETION AND GAME FINALIZATION FUNCTIONS
# =============================================================================
def check_tasks_completion():
    """Checks status of all tasks and activates completion effects"""
    game = get_game()
    if not game:
        return {}
    
    # Get tasks from GameManager (without print)
    tasks = game.check_tasks()
    
    # Check if game is completed (3 main tasks)
    task_storage = getattr(game.state, 'task_storage', False)
    task_restoration = getattr(game.state, 'task_restoration', False)
    task_quiz = getattr(game.state, 'task_quiz', False)
    
    tasks_completed = sum([task_storage, task_restoration, task_quiz])
    game.state.task_total = tasks_completed
    
    # GAME COMPLETION DETECTION
    # Check if 3 tasks just completed (and was not already completed before)
    if tasks_completed >= 3 and not getattr(game.state, 'game_completed', False):
        # Mark game as completed (to prevent multiple triggers)
        game.state.game_completed = True
        game.state.game_completion_time = bge.logic.getRealTime()
        
        print("\n" + "= "*50)
        print("GAME COMPLETED! Activating special effects...")
        print("= "*50)
        
        # ACTIVATE EFFECT 1: Center message
        success_msg = _trigger_win_message()
        if success_msg:
            print("[game_access] Victory message sent")
        else:
            print("[game_access] Could not send victory message")
        
        # CHANGE BACKGROUND MUSIC
        #set_background_context("end_game")
        logic.sendMessage("sound_background.set_context", "sound_background.set_context|endgame")
        
        # ACTIVATE EFFECT 2: Matrix rain
        success_matrix = _trigger_matrix_effect()
        if success_matrix:
            print("[game_access] Matrix effect activated")
        else:
            print("[game_access] Could not activate matrix effect")
    
    # Synchronize with controller
    try:
        scn = bge.logic.getCurrentScene()
        gc = scn.objects.get("Game.Controller")
        if gc:
            game.sync_to_controller(gc)
            # Synchronize completion flags
            gc['game_completed'] = getattr(game.state, 'game_completed', False)
    except:
        pass
    
    return tasks

def _trigger_win_message():
    """Activates victory message in center of screen"""
    try:
        scene = bge.logic.getCurrentScene()
        
        # Find Game.Controller
        gc = scene.objects.get("Game.Controller")
        if gc:
            gc.sendMessage(
                "add_info_text",
                "info.show|center_text|6|field=center_text|text=GAME COMPLETED!\\nTasks: 3/3 | Level: Master",
                "Game.Controller"
            )
            return True
        
        # If no Game.Controller, find any object that can receive messages
        for obj in scene.objects:
            if "Controller" in obj.name or "Game" in obj.name:
                obj.sendMessage(
                    "add_info_text",
                    "info.show|center_text|6|field=center_text|text=GAME COMPLETED!\\nTasks: 3/3 | Level: Master",
                    "Game.Controller"
                )
                return True
        
        # Last resort: send from any object
        if scene.objects:
            scene.objects[0].sendMessage(
                "add_info_text",
                "info.show|center_text|6|field=center_text|text=GAME COMPLETED!\\nTasks: 3/3 | Level: Master",
                "Game.Controller"
            )
            return True
        
        return False
    except Exception as e:
        print(f"[game_access] Error sending victory message: {e}")
        return False

def _trigger_matrix_effect():
    """Activates Matrix background effect"""
    try:
        from bge import logic
        
        # Set global flag to activate Matrix
        logic.matrix_effect_active = True
        
        # Also save in game_state for persistence
        game = get_game()
        if game and hasattr(game, 'state'):
            game.state.matrix_effect_active = True
        
        # Verify that Matrix module is available
        try:
            import matrix_rain_screen
            # Force initialization
            if hasattr(matrix_rain_screen, 'init_matrix_effect'):
                matrix_rain_screen.init_matrix_effect()
        except ImportError:
            print("[game_access] matrix_rain_screen.py not found")
        
        return True
    except Exception as e:
        print(f"[game_access] Error activating Matrix effect: {e}")
        return False

# =============================================================================
# EXISTING FUNCTIONS (no changes)
# =============================================================================
def clear_active_item():
    """Explicitly clears global active item"""
    try:
        if hasattr(logic, "active_collection_item"):
            logic.active_collection_item = None
            print("[game_access] Global active item cleared")
            return True
        return False
    except Exception as e:
        print(f"[game_access] Error clearing active item: {e}")
        return False

def force_hud_cleanup():
    """Forces complete HUD and related state cleanup"""
    try:
        game = get_game()
        if not game:
            return False
        
        # Clear HUD texts
        game.hud_text.info_text_v2 = ""
        game.hud_text.item_desc_text = ""
        game.hud_text.info_text = ""
        
        # Clear active item
        clear_active_item()
        
        # Reset flags
        logic.hud_inventory_v2_open = False
        logic.hud_inventory_open = False
        logic._auto_v2_active = False
        
        print("[game_access] HUD completely cleared")
        return True
        
    except Exception as e:
        print(f"[game_access] Error in force_hud_cleanup: {e}")
        return False

def safe_update_object(item_type, item_id, updates_dict):
    """
    Safely updates an object without overwriting other values
    """
    try:
        # 1. Update in inventory
        game = get_game()
        if not game:
            return False
        
        inv = game.state.inventory
        coll = inv.get("collection_items", {}).get(item_type, [])
        
        for item in coll:
            if item.get("item_id") == item_id:
                # Apply updates
                for key, value in updates_dict.items():
                    item[key] = value
                print(f"[game_access] Inventory safely updated: {item_type}#{item_id} -> {updates_dict}")
                break
        
        # 2. Synchronize with scene objects
        return find_and_update_object(item_type, item_id, updates_dict)
        
    except Exception as e:
        print(f"[game_access] Error in safe_update_object: {e}")
        return False

def force_clean_active_item():
    """Forces cleanup of global active item and synchronization"""
    try:
        # 1. Clear active_collection_item
        if hasattr(logic, "active_collection_item"):
            print(f"[game_access] Clearing active_collection_item: {logic.active_collection_item}")
            logic.active_collection_item = None
        
        # 2. Force inventory synchronization
        force_inventory_sync()
        
        # 3. Clear HUD texts if GameManager is available
        game = get_game()
        if game and hasattr(game, 'hud_text'):
            game.hud_text.info_text_v2 = ""
            game.hud_text.item_desc_text = ""
        
        print("[game_access] Complete forced cleanup")
        return True
        
    except Exception as e:
        print(f"[game_access] Error in force_clean_active_item: {e}")
        return False

def get_sound_settings():
    """Get current sound settings"""
    state = get_state()
    if not state:
        return {
            'sound_main': True,
            'sound_background': True,
            'sound_volume': 1.0,
            'sound_context': 'exploration'
        }
    return {
        'sound_main': state.sound_main,
        'sound_background': state.sound_background,
        'sound_volume': state.sound_volume,
        'sound_context': state.sound_context
    }

def set_sound_settings(sound_main=None, sound_background=None, sound_volume=None):
    """Set sound settings"""
    state = get_state()
    if not state:
        return False
    
    if sound_main is not None:
        state.sound_main = sound_main
    if sound_background is not None:
        state.sound_background = sound_background
    if sound_volume is not None:
        state.sound_volume = max(0.0, min(1.0, sound_volume))
    
    return True

# =============================================================================
# NPC FLOW FUNCTIONS
# =============================================================================
def sync_npc_state(npc_id, quiz_success):
    """Synchronizes NPC state after a QUIZ"""
    try:
        # EXCLUDE NPC11 - Do not synchronize here
        if npc_id == 11:
            print(f"[game_access] NPC11 excluded from sync_npc_state")
            return True
        
        # Find NPC object
        scene = logic.getCurrentScene()
        npc = scene.objects.get(f'npc{npc_id}')
        
        if not npc:
            print(f"[game_access] NPC{npc_id} not found")
            return False
        
        # Update basic properties
        npc['quiz_success'] = quiz_success
        npc['quiz_reply'] = True
        
        print(f"[game_access] State synchronized for NPC{npc_id}: success={quiz_success}")
        return True
        
    except Exception as e:
        print(f"[game_access] Error synchronizing NPC{npc_id}: {e}")
        return False

def reset_npc_for_next_attempt(npc_id):
    """Prepares an NPC for a new attempt after a failure"""
    try:
        # EXCLUDE NPC11 - Do not reset here
        if npc_id == 11:
            print(f"[game_access] NPC11 excluded from reset_npc_for_next_attempt")
            return True
        
        scene = logic.getCurrentScene()
        npc = scene.objects.get(f'npc{npc_id}')
        
        if not npc:
            return False
        
        # Reset quiz-related properties
        npc['quiz_reply'] = False
        npc['quiz_success'] = False
        npc['quiz_on'] = False
        
        # Important: Allow NPC to remain active for new attempts
        npc['active'] = True
        
        # Reset dialog properties
        npc['_dialog_ended'] = False
        
        print(f"[game_access] NPC{npc_id} reset for new attempt")
        return True
        
    except Exception as e:
        print(f"[game_access] Error resetting NPC{npc_id}: {e}")
        return False

def get_timer_quiz():
    """Gets current timer_quiz value"""
    state = get_state()
    if state and hasattr(state, 'timer_quiz'):
        return state.timer_quiz
    return 0.0

def is_quiz_active():
    """Checks if quiz system is active"""
    state = get_state()
    if state and hasattr(state, 'quiz_active'):
        return state.quiz_active
    return True  # Active by default

def update_npc_scene_id(npc_id, scene_id):
    """Updates NPC scene_id"""
    try:
        # EXCLUDE NPC11 - Do not update scene_id here
        if npc_id == 11:
            print(f"[game_access] NPC11 excluded from update_npc_scene_id")
            return True
        
        scene = logic.getCurrentScene()
        npc = scene.objects.get(f'npc{npc_id}')
        
        if npc:
            npc['scene_id'] = scene_id
            print(f"[game_access] NPC{npc_id} scene_id updated to {scene_id}")
            return True
        return False
    except Exception as e:
        print(f"[game_access] Error updating scene_id: {e}")
        return False

def initialize_all_npcs():
    """Initializes all NPCs at game start"""
    try:
        scene = logic.getCurrentScene()
        
        # Initialize NPC1 as active
        npc1 = scene.objects.get("npc1")
        if npc1:
            npc1['active'] = True
            npc1['remaining_events'] = 3
            npc1['scene_id'] = 1  # scene1 for first attempt
            npc1['_base_scene_id'] = 1
            print(f"[game_access] NPC1 initialized as active")
        
        # Initialize NPCs 2-10 as inactive
        for i in range(2, 11):
            npc = scene.objects.get(f"npc{i}")
            if npc:
                npc['active'] = False
                npc['remaining_events'] = 3
                base_scene = (i - 1) * 3 + 1
                npc['scene_id'] = base_scene
                npc['_base_scene_id'] = base_scene
                print(f"[game_access] NPC{i} initialized as inactive (base_scene={base_scene})")
        
        # EXCLUDE NPC11 - Do not initialize here (handled by npc_restoration_logic.py)
        
        # Set initial turn
        state = get_state()
        if state:
            state.npc_turn = 1
            state.quiz_active = True
            state.timer_quiz = 0.0
            print(f"[game_access] Initial turn set: NPC1")
        
        return True
        
    except Exception as e:
        print(f"[game_access] Error initializing NPCs: {e}")
        return False

def activate_next_npc(current_npc_id):
    """Activates the next NPC after a success"""
    try:
        # EXCLUDE NPC11 - Do not activate next NPC here
        if current_npc_id == 11:
            print(f"[game_access] NPC11 excluded from activate_next_npc")
            return None
        
        scene = logic.getCurrentScene()
        
        # Search for next NPC with remaining attempts
        for next_id in range(current_npc_id + 1, 11):  # Only up to NPC10
            next_npc = scene.objects.get(f"npc{next_id}")
            
            if next_npc:
                remaining = next_npc.get('remaining_events', 3)
                
                if remaining > 0:
                    # Activate this NPC
                    next_npc['active'] = True
                    
                    # Update turn in state
                    state = get_state()
                    if state:
                        state.npc_turn = next_id
                    
                    print(f"[game_access] NPC{next_id} activated as next (remaining_events={remaining})")
                    return next_id
        
        # If not found, search from beginning
        for next_id in range(1, current_npc_id):
            next_npc = scene.objects.get(f"npc{next_id}")
            
            if next_npc:
                remaining = next_npc.get('remaining_events', 3)
                
                if remaining > 0:
                    next_npc['active'] = True
                    
                    state = get_state()
                    if state:
                        state.npc_turn = next_id
                    
                    print(f"[game_access] NPC{next_id} activated (full cycle)")
                    return next_id
        
        print(f"[game_access] No activatable next NPC found")
        return None
        
    except Exception as e:
        print(f"[game_access] Error activating next NPC: {e}")
        return None

def force_npcs_initialization():
    """Forces initialization of all NPCs"""
    try:
        scene = logic.getCurrentScene()
        
        # Initialize NPC1
        npc1 = scene.objects.get("npc1")
        if npc1:
            npc1['active'] = True
            npc1['remaining_events'] = 3
            npc1['scene_id'] = 1
            npc1['_base_scene_id'] = 1
            print(f"[game_access] NPC1 forced to active=True")
        
        # Initialize NPCs 2-10
        for i in range(2, 11):
            npc = scene.objects.get(f"npc{i}")
            if npc:
                npc['active'] = False  # Inactive at start
                npc['remaining_events'] = 3
                base_scene = (i - 1) * 3 + 1
                npc['scene_id'] = base_scene
                npc['_base_scene_id'] = base_scene
                print(f"[game_access] NPC{i} initialized (active=False, base_scene={base_scene})")
        
        # EXCLUDE NPC11 - Do not force initialization here
        
        # Set initial turn
        state = get_state()
        if state:
            state.npc_turn = 1
            state.quiz_active = True
            print(f"[game_access] Turn set to NPC1")
        
        return True
        
    except Exception as e:
        print(f"[game_access] Error forcing initialization: {e}")
        return False

# =============================================================================
# CAT PET SYSTEM FUNCTIONS
# =============================================================================
def get_cat_food_items():
    """Get number of cat food cans"""
    state = get_state()
    return state.cat_food_items if state else 0

def set_cat_food_items(value):
    """Set number of cat food cans"""
    state = get_state()
    if state:
        state.cat_food_items = max(0, value)
        return True
    return False

def add_cat_food(amount=1):
    """Add cat food cans"""
    state = get_state()
    if state:
        state.cat_food_items += amount
        print(f"[game_access] Cat food can(s) added: {state.cat_food_items}")
        return state.cat_food_items
    return 0

def consume_cat_food(amount=1):
    """Consume cat food cans"""
    state = get_state()
    if state and state.cat_food_items >= amount:
        state.cat_food_items -= amount
        print(f"[game_access] Cat food can(s) consumed: {state.cat_food_items}")
        return state.cat_food_items
    return 0

def is_cat_pet_active():
    """Check if cat is in pet mode"""
    state = get_state()
    return state.cat_pet_active if state else False

def set_cat_pet_active(active=True, duration=None):
    """Activate/deactivate cat pet mode"""
    state = get_state()
    if state:
        state.cat_pet_active = active
        if active and duration is not None:
            state.cat_pet_timer = duration
        elif not active:
            state.cat_pet_timer = 0.0
        return True
    return False

def get_cat_pet_timer():
    """Get remaining time as pet"""
    state = get_state()
    return state.cat_pet_timer if state else 0.0

def update_cat_pet_timer(dt):
    """Update pet timer (call each frame)"""
    state = get_state()
    if state and state.cat_pet_active:
        state.cat_pet_timer -= dt
        if state.cat_pet_timer <= 0:
            state.cat_pet_active = False
            state.cat_pet_timer = 0.0
            print("[game_access] Pet time expired")
            return False  # Time expired
        return True  # Still active
    return False

def set_cat_food_hud_visible(visible=True):
    """Control cat food HUD visibility"""
    state = get_state()
    if state:
        state.cat_food_hud_visible = visible
        try:
            scene = bge.logic.getCurrentScene()
            hud_obj = scene.objects.get("Cat.Food.Hud")
            if hud_obj:
                hud_obj.visible = visible
            print(f"[game_access] Cat food HUD: {'visible' if visible else 'hidden'}")
            return True
        except:
            pass
    return False

def get_cat_food_hud_visible():
    """Get HUD visibility state"""
    state = get_state()
    return state.cat_food_hud_visible if state else False

def get_cat_food_spawn_points():
    """Get number of food spawn points"""
    state = get_state()
    return state.cat_food_spawn_points if state else 3

def set_cat_food_spawn_points(value):
    """Set number of spawn points"""
    state = get_state()
    if state:
        state.cat_food_spawn_points = max(1, value)
        return True
    return False

def check_cat_food_in_scene():
    """Check if there is an active cat food can in scene"""
    try:
        scene = bge.logic.getCurrentScene()
        for obj in scene.objects:
            if obj.name == "Cat.Food" and obj.worldPosition.y > -100:  # Not hidden
                return True
        return False
    except:
        return False

def can_spawn_cat_food():
    """Check if new food can be spawned (none in scene and none in inventory)"""
    scene_has_food = check_cat_food_in_scene()
    state = get_state()
    inventory_has_food = state.cat_food_items > 0 if state else False
    return not scene_has_food and not inventory_has_food