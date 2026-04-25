"""
quiz_button_restoration.py

Manages restoration quiz button interaction with ray casting and answer processing.

This script handles the interactive buttons for the restoration quiz system,
detecting mouse hover and click, applying visual effects, and sending answers
to the restoration quiz system with NPC11 integration.

Main Features:
    1. Ray casting based mouse detection using Camera.Hud
    2. Visual effects (scale, tint) for idle, hover, and click states
    3. Warmup timer to prevent accidental clicks immediately after display
    4. Mutual exclusion (only one button can be clicked per quiz)
    5. Automatic disabling of all buttons after a selection
    6. Robust NPC11 search by name, npc_id property, or partial name matching
    7. Inventory update and task completion tracking for restoration
    8. World object synchronization after successful restoration

Setup:
    Connect to Logic Bricks as Python controller with module 'quiz_button_restoration.main'
    Requires three buttons named: Button.Restor.True, Button.Restor.False.1, Button.Restor.False.2
    Each button must have 'answer_id' and 'is_correct' properties

Configurable Variables:
    DEBUG_RESTOR (bool): Enable restoration-specific debug logging (default: True)
    DEBUG (bool): Enable general debug logging (default: False)
    WARMUP_TIME (float): Seconds to wait before accepting clicks (default: 0.5)
    HOVER_SCALE (float): Scale factor when mouse is over (default: 1.1)
    BASE_SCALE (float): Normal scale (default: 1.0)
    RAY_CAMERA_NAME (str): Camera for ray casting (default: 'Camera.Hud')
    RAY_DISTANCE (float): Maximum ray casting distance (default: 1000.0)
    IDLE_TINT (tuple): RGBA color for idle state (default: (1.00, 1.00, 1.00, 1.0))
    OVER_TINT (tuple): RGBA color for hover state (default: (0.50, 1.00, 0.00, 1.0))
    CLICK_TINT (tuple): RGBA color for click state (default: (0.68, 0.68, 0.68, 1.0))

Notes:
    - Buttons are automatically disabled after one is clicked
    - Requires NPC11 object in scene with restoration_item_type and restoration_item_id
    - Sends answer via 'add_text_restor' message
    - Updates game_state.task_restoration_total and task_restoration on success
    - Synchronizes World object restored property on success

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
__description__ = "Manages restoration quiz button interaction with answer processing"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic
from bge import events
import game_access

# =============================================================================
# CONFIGURATION
# =============================================================================
DEBUG_RESTOR = True
DEBUG = False
WARMUP_TIME = 0.5

# Visual effects
HOVER_SCALE = 1.1
BASE_SCALE = 1.0
RAY_CAMERA_NAME = "Camera.Hud" 
RAY_DISTANCE = 1000.0

# Tinting system
IDLE_TINT = (1.00, 1.00, 1.00, 1.0)
OVER_TINT = (0.50, 1.00, 0.00, 1.0)
CLICK_TINT = (0.68, 0.68, 0.68, 1.0)

# Restoration button configuration
RESTOR_BUTTON_NAMES = ["Button.Restor.False.1", "Button.Restor.False.2", "Button.Restor.True"]

# =============================================================================
# RAY CASTING SYSTEM
# =============================================================================
def _is_mouse_over(owner):
    """Detects if camera ray hits the object"""
    if _is_any_button_clicked():
        return False
        
    scn = logic.getCurrentScene()
    cam = scn.objects.get(RAY_CAMERA_NAME)
    if not cam:
        print(f"[RESTOR BUTTON] Error: Camera '{RAY_CAMERA_NAME}' not found.")
        return False
        
    mx, my = logic.mouse.position
    
    try:
        hit_obj = cam.getScreenRay(mx, my, RAY_DISTANCE, "")
    except:
        try:
            hit_obj = cam.getScreenRay(mx, my, RAY_DISTANCE)
        except:
            return False
    
    if hit_obj == owner:
        return True
    
    try:
        parent = hit_obj.parent
        while parent:
            if parent == owner:
                return True
            parent = parent.parent
    except:
        pass
        
    return False

def _is_any_button_clicked():
    """Checks if ANY restoration button has been clicked."""
    scn = logic.getCurrentScene()
    for button_name in RESTOR_BUTTON_NAMES:
        button = scn.objects.get(button_name)
        if button and button.get("_button_clicked", False):
            return True
    return False

def _check_mouse_click(cont):
    """Checks if left mouse button was just clicked"""
    if _is_any_button_clicked():
        return False
        
    mouse = bge.logic.mouse
    try:
        left_mouse_input = mouse.inputs.get(events.LEFTMOUSE)
        if left_mouse_input and left_mouse_input.activated:
            return True
    except:
        try:
            return mouse.events.get(events.LEFTMOUSE, 0) == logic.KX_INPUT_JUST_ACTIVATED
        except:
            pass
                
    return False

# =============================================================================
# WARMUP TIME MANAGEMENT
# =============================================================================
def _update_warmup(owner):
    """Updates warmup timer"""
    if "_warmup_timer" not in owner:
        owner["_warmup_timer"] = 0.0
        
    if owner["_warmup_timer"] < WARMUP_TIME:
        owner["_warmup_timer"] += 0.017 
        return False
    return True

# =============================================================================
# VISUAL EFFECTS
# =============================================================================
def _apply_tint(owner, rgba):
    """Applies color/tint to the object"""
    try:
        owner.color = list(rgba)
    except Exception as e:
        if DEBUG:
            print(f"[RESTOR BUTTON] Error applying tint: {e}")

def _apply_scale(owner, scale_factor):
    """Applies scale to the object while preserving base scale"""
    try:
        if "_base_scale" not in owner:
            owner["_base_scale"] = tuple(owner.localScale)
        base = owner["_base_scale"]
        owner.localScale = [base[0]*scale_factor, base[1]*scale_factor, base[2]*scale_factor]
    except Exception as e:
        if DEBUG:
            print(f"[RESTOR BUTTON] Error applying scale: {e}")

def _reset_scale(owner):
    """Restores original object scale"""
    try:
        if "_base_scale" in owner:
            owner.localScale = list(owner["_base_scale"])
    except Exception as e:
        if DEBUG:
            print(f"[RESTOR BUTTON] Error restoring scale: {e}")

def _apply_visual_state(owner, state):
    """Applies full visual state (tint + scale) according to state"""
    if state == "idle":
        _apply_tint(owner, IDLE_TINT)
        _reset_scale(owner)
    elif state == "over":
        _apply_tint(owner, OVER_TINT)
        _apply_scale(owner, HOVER_SCALE)
    elif state == "click":
        _apply_tint(owner, CLICK_TINT)
        _apply_scale(owner, HOVER_SCALE * 0.9)
    elif state == "clicked":
        _apply_tint(owner, CLICK_TINT)
        _reset_scale(owner)

# =============================================================================
# ENHANCED FUNCTION TO FIND NPC11
# =============================================================================
def _find_npc11():
    """Finds NPC11 object in a robust manner"""
    scn = logic.getCurrentScene()
    
    # List of possible names
    possible_names = ["NPC.11", "npc11", "NPC11", "NPC_11"]
    
    # 1. Try by direct name
    for name in possible_names:
        npc = scn.objects.get(name)
        if npc:
            if DEBUG_RESTOR:
                print(f"[RESTOR BUTTON] NPC found by name: {name}")
            return npc
    
    # 2. Search by npc_id property = 11
    for obj in scn.objects:
        try:
            if obj.get("npc_id") == 11:
                if DEBUG_RESTOR:
                    print(f"[RESTOR BUTTON] NPC found by npc_id: {obj.name}")
                return obj
        except:
            pass
    
    # 3. Search by name containing "npc" and "11"
    for obj in scn.objects:
        try:
            name_lower = obj.name.lower()
            if "npc" in name_lower and "11" in name_lower:
                if DEBUG_RESTOR:
                    print(f"[RESTOR BUTTON] NPC found by search: {obj.name}")
                return obj
        except:
            pass
    
    print(f"[RESTOR BUTTON] ERROR: Could not find NPC11 in scene")
    return None

# =============================================================================
# CLICK ACTION HANDLER
# =============================================================================
def _perform_click_action(owner):
    """Processes restoration button click - CORRECTED VERSION"""
    
    # Mark THIS button as clicked
    owner["_button_clicked"] = True
    owner["_button_state"] = "clicked"
    _apply_visual_state(owner, "clicked")
    
    # Determine if correct using is_correct property
    is_correct = owner.get("is_correct", False)
    
    if DEBUG_RESTOR:
        print(f"\n[RESTOR BUTTON] Click on {owner.name}")
        print(f"  answer_id: {owner.get('answer_id', 'NO')}")
        print(f"  is_correct: {is_correct}")
        print(f"  position: {owner.worldPosition}")
    
    # Play click sound
    bge.logic.sendMessage("sound_fx.play", "sound_fx.play|mouse-click.ogg|volume=1.0")
    
    # Disable hover and clicks on ALL buttons
    _disable_all_buttons()
    
    # FIND NPC11 ROBUSTLY
    npc11 = _find_npc11()
    
    if not npc11:
        print(f"[RESTOR BUTTON] CRITICAL: NPC11 not found - Cannot process answer")
        return
    
    if DEBUG_RESTOR:
        print(f"[RESTOR BUTTON] NPC found: {npc11.name}")
    
    # Get information about the object being restored
    item_type = npc11.get("restoration_item_type", "")
    item_id = npc11.get("restoration_item_id", 0)
    quiz_id = npc11.get("what_quiz", "q101")
    scene_id = npc11.get("scene_id", 31)
    answer_id = owner.get("answer_id", 1)
    
    if DEBUG_RESTOR:
        print(f"[RESTOR BUTTON] Quiz information:")
        print(f"  Object: {item_type}#{item_id}")
        print(f"  Quiz ID: {quiz_id}, Scene: {scene_id}")
        print(f"  answer_id pressed: {answer_id}")
        print(f"  Is correct? {is_correct}")
    
    # Send answer to quiz system
    try:
        bge.logic.sendMessage('add_text_restor',
            f'restor.answer|{quiz_id}|choice={answer_id}|options_text=restor_text|result_text=center_text')
        
        if DEBUG_RESTOR:
            print(f"[RESTOR BUTTON] Answer sent: choice={answer_id}")
    except Exception as e:
        print(f"[RESTOR BUTTON] Error sending answer: {e}")
    
    # CRITICAL: Configure NPC properties CORRECTLY
    print(f"[RESTOR BUTTON] Configuring NPC {npc11.name} properties (id={id(npc11)}):")
    print(f"  BEFORE: quiz_on={npc11.get('quiz_on', 'NO')}, quiz_reply={npc11.get('quiz_reply', 'NO')}, quiz_success={npc11.get('quiz_success', 'NO')}")
    
    npc11["quiz_reply"] = True
    npc11["quiz_on"] = False
    npc11["quiz_success"] = is_correct
    
    print(f"  AFTER: quiz_on={npc11['quiz_on']}, quiz_reply={npc11['quiz_reply']}, quiz_success={npc11['quiz_success']}")
    
    # IMMEDIATE VERIFICATION
    import time
    time.sleep(0.05)  # Wait 50ms
    print(f"  VERIFICATION (50ms later): quiz_on={npc11.get('quiz_on')}, quiz_reply={npc11.get('quiz_reply')}, quiz_success={npc11.get('quiz_success')}")
    
    # If correct, update the object
    if is_correct and item_type and item_id:
        game = game_access.get_game()
        if game:
            inventory = game.state.inventory
            collection_items = inventory.get("collection_items", {})
            
            item_updated = False
            for item in collection_items.get(item_type, []):
                if item.get("item_id") == item_id:
                    old_value = item.get("restored", 0)
                    item["restored"] = 1
                    item_updated = True
                    
                    print(f"[RESTOR BUTTON] Object {item_type}#{item_id} RESTORED: {old_value} -> 1")
                    
                    # Increment counter
                    game.state.task_restoration_total += 1
                    print(f"[RESTOR BUTTON] task_restoration_total: {game.state.task_restoration_total}/3")
                    
                    # Check if task is completed
                    if game.state.task_restoration_total >= 3:
                        game.state.task_restoration = True
                        print(f"[RESTOR BUTTON] RESTORATION task completed!")
                    
                    break
            
            if item_updated:
                # Update statistics
                game.state.update_collection_stats()
                
                # Synchronize with Game.Controller
                try:
                    gc = logic.getCurrentScene().objects.get("Game.Controller")
                    if gc:
                        gc['task_restoration_total'] = game.state.task_restoration_total
                        gc['task_restoration'] = game.state.task_restoration
                        print(f"[RESTOR BUTTON] Synchronized with Game.Controller")
                except Exception as e:
                    print(f"[RESTOR BUTTON] Error synchronizing: {e}")
                
                # Synchronize 3D objects
                try:
                    _sync_world_object_restoration(item_type, item_id, 1)
                except Exception as e:
                    print(f"[RESTOR BUTTON] Error synchronizing 3D objects: {e}")
    
    # Play result sound
    sound_name = "quiz_success.ogg" if is_correct else "quiz_wrong.ogg"
    bge.logic.sendMessage("sound_fx.play", 
                        f"sound_fx.play|{sound_name}|volume=0.7")
    
    if DEBUG_RESTOR:
        print(f"[RESTOR BUTTON] Sound played: {sound_name}")

def _disable_all_buttons():
    """Disables all restoration buttons."""
    scn = logic.getCurrentScene()
    for button_name in RESTOR_BUTTON_NAMES:
        button = scn.objects.get(button_name)
        if button:
            if not button.get("_button_clicked", False):
                button["_button_clicked"] = True
                button["_button_state"] = "clicked"
                _apply_visual_state(button, "clicked")

def _reset_all_buttons():
    """Resets the state of ALL buttons."""
    scn = logic.getCurrentScene()
    for button_name in RESTOR_BUTTON_NAMES:
        button = scn.objects.get(button_name)
        if button:
            button["_button_clicked"] = False
            button["_button_state"] = "idle"
            button["_warmup_timer"] = 0.0
            _apply_visual_state(button, "idle")
            
def _sync_world_object_restoration(item_type, item_id, restored_value):
    """Synchronizes restoration state with the corresponding World object"""
    try:
        scene = logic.getCurrentScene()
        
        # Find the corresponding World object
        period_capitalized = item_type.capitalize() if item_type != 'bronze' else 'Bronze'
        world_obj_name = f"Object.World.{period_capitalized}.{item_id}"
        world_obj = scene.objects.get(world_obj_name)
        
        if world_obj:
            world_obj["restored"] = restored_value
            print(f"[RESTOR BUTTON] World object updated: {world_obj_name} -> restored={restored_value}")
            return True
        else:
            print(f"[RESTOR BUTTON] World object not found: {world_obj_name}")
            return False
            
    except Exception as e:
        print(f"[RESTOR BUTTON] Error synchronizing World object: {e}")
        return False            

# =============================================================================
# MAIN LOGIC
# =============================================================================
def main(cont):
    owner = cont.owner
    
    # Initialization
    if "_base_scale" not in owner:
        owner["_base_scale"] = tuple(owner.localScale)
        owner["_button_state"] = "idle"
        owner["_button_clicked"] = False
        owner["_warmup_timer"] = 0.0
        _apply_visual_state(owner, "idle")
        
    # If button is invisible, do not process
    if not owner.visible:
        return

    # If ANY button has already been clicked, do not process input
    if _is_any_button_clicked():
        if not owner.get("_button_clicked", False):
            owner["_button_clicked"] = True
            owner["_button_state"] = "clicked"
            _apply_visual_state(owner, "clicked")
        return

    # Input detection
    is_ready = _update_warmup(owner)
    
    mouse_over = _is_mouse_over(owner)
    mouse_click = False
    
    if mouse_over and is_ready:
        mouse_click = _check_mouse_click(cont)
    
    # Apply visual effects
    previous_state = owner.get("_button_state", "idle")
    current_state = "over" if mouse_over else "idle"
    if mouse_over and mouse_click: 
        current_state = "click"
    
    if current_state != previous_state:
        _apply_visual_state(owner, current_state)
        owner["_button_state"] = current_state
    
    # Handle click
    if mouse_over and mouse_click and not _is_any_button_clicked():
        _perform_click_action(owner)