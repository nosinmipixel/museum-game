"""
format_hud_data.py

Manages HUD overlay state, inventory switching, and data formatting for display.

This script handles the transition between HUD and inventory overlays,
formats player statistics and game state data for display, and manages
visibility of UI elements and collections.

Main Features:
    1. Format HUD text data (budget, skills, temperature, humidity)
    2. Switch between HUD and inventory overlays (V1 and V2)
    3. Manage collection visibility for different camera views
    4. Control balloon visibility for dialog states
    5. Cache overlay state to prevent redundant switching
    6. Track task completion status via game_access

Setup:
    Connect to Logic Bricks as Python controller with module 'format_hud_data.main'
    Requires proper collection setup: CollectionHud, CollectionInventory, CollectionObjects

Configurable Variables:
    HUD_COLLECTION_NAME (str): HUD collection name (default: 'CollectionHud')
    HUD_CAMERA_NAME (str): HUD camera name (default: 'Camera.Hud')
    INV_COLLECTION_NAME (str): Inventory collection name (default: 'CollectionInventory')
    INV_CAMERA_NAME (str): Inventory camera name (default: 'Camera.Inventory')
    OBJECTS_COLLECTION_NAME (str): Objects collection name (default: 'CollectionObjects')
    ROOT_V1 (str): V1 root empty name (default: 'Empty.View.1')
    ROOT_V2 (str): V2 root empty name (default: 'Empty.View.2')
    V2_SHARED (str): V2 shared elements empty (default: 'Empty.View.2.Shared')
    V2_ADD_BOX (str): V2 add to box empty (default: 'Empty.View.2.Add.To.Box')
    V2_ADD_EXHIB (str): V2 add to exhibition empty (default: 'Empty.View.2.Add.To.Exhib')
    V2_ADD_RESTOR (str): V2 add to restoration empty (default: 'Empty.View.2.Add.To.Restor')

Notes:
    - Requires game_access module for game state and player data
    - Object collection is added once to both cameras and never removed
    - Inventory V1 and V2 states are managed via global flags
    - Balloon visibility is controlled through positioning anchors
    - Task completion is verified via check_tasks_completion()

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
__description__ = "Manages HUD overlay state, inventory switching, and data formatting"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic
import math
import bpy
from bge import render
import game_access

# =============================================================================
# DATA FORMATTING FUNCTION
# =============================================================================
def format_hud_data():
    # Get data directly using game_access
    game = game_access.get_game()
    if not game:
        print("Error: Could not get game via game_access.")
        return
        
    player_stats = game.player
    game_state = game.state
    hud_text = game.hud_text
    
    # All data is obtained directly from game_access
    
    # Initialize quiz_active if it doesn't exist
    if not hasattr(game_state, 'quiz_active'):
        game_state.quiz_active = True  # By default, QUIZ system is active
        
    # Format HUD text
    hud_text.budget_text = f"{game_state.budget}€"
    
    # Calculate task_total using task_quiz (completed) not quiz_active
    task_total = 0
    if getattr(game_state, 'task_quiz', False):  # Use task_quiz (completed)
        task_total += 1
    if getattr(game_state, 'task_storage', False):
        task_total += 1
    if getattr(game_state, 'task_exhibition', False):
        task_total += 1
    if getattr(game_state, 'task_conservation', False):
        task_total += 1
    if getattr(game_state, 'task_restoration', False):
        task_total += 1
    
    # Ensure task_total is not negative
    task_total = max(0, task_total)
    
    # Update task_total in state
    game_state.task_total = task_total
    
    # Use player.skills directly
    skills_value = getattr(player_stats, 'skills', 1)
    
    # Limit to maximum 5 levels
    skills_level = min(skills_value, 5)
        
    skills_map = {
        'es': {
            0: "0. Sin calificar",
            1: "1. Novato", 
            2: "2. Senior", 
            3: "3. Experto", 
            4: "4. Master", 
            5: "5. Director"
        },
        'en': {
            0: "0. Unrated",
            1: "1. Novice", 
            2: "2. Senior", 
            3: "3. Expert", 
            4: "4. Master", 
            5: "5. Director"
        }
    }
    
    lang = game_state.language
    hud_text.skills_text = skills_map.get(lang, {}).get(skills_level, f"Skills: {skills_level}")

    # Temperature and humidity - obtained directly from game_state
    raw_temp = getattr(game_state, 'temp_raw', 21.0)
    raw_hr   = getattr(game_state, 'hr_raw', 50.0)
    temp_ok  = getattr(game_state, 'temp_ok', True)
    hr_ok    = getattr(game_state, 'hr_ok', True)
    
    try:
        hud_text.temp_mus = f"Temp: {raw_temp:.1f} C"
        hud_text.hr_mus   = f"H.R: {raw_hr:.1f} %"
    except (ValueError, TypeError) as e:
        print(f"Error formatting temperature/humidity: {e}")
        hud_text.temp_mus = "Temp: ERROR"
        hud_text.hr_mus   = "H.R: ERROR"

# =============================================================================
# COLLECTION AND CAMERA CONSTANTS
# =============================================================================
HUD_COLLECTION_NAME       = "CollectionHud"
HUD_CAMERA_NAME           = "Camera.Hud"
INV_COLLECTION_NAME       = "CollectionInventory"
INV_CAMERA_NAME           = "Camera.Inventory"
OBJECTS_COLLECTION_NAME   = "CollectionObjects"

ROOT_V1           = "Empty.View.1"
ROOT_V2           = "Empty.View.2"
V2_SHARED         = "Empty.View.2.Shared"
V2_ADD_BOX        = "Empty.View.2.Add.To.Box"
V2_ADD_EXHIB      = "Empty.View.2.Add.To.Exhib"
V2_ADD_RESTOR     = "Empty.View.2.Add.To.Restor"

BALLOON_L_NAME        = "Balloon.L"
BALLOON_R_NAME        = "Balloon.R"
BALLOON_MAIN_NAME     = "Balloon.Main"
BALLOON_POS_VISIBLE   = "Pos.Info.Balloon"
BALLOON_POS_HIDDEN    = "Pos.Info.Balloon.Out"

# =============================================================================
# GLOBAL FLAGS INITIALIZATION
# =============================================================================
if not hasattr(logic, "hud_inventory_open"):    logic.hud_inventory_open = False
if not hasattr(logic, "hud_inventory_v2_open"): logic.hud_inventory_v2_open = False
if not hasattr(logic, "_hud_overlay_ready"):    logic._hud_overlay_ready = False
if not hasattr(logic, "blf_hidden"):            logic.blf_hidden = False
if not hasattr(logic, "_last_overlay"):         logic._last_overlay = ""

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def _get_collection(name):
    col = bpy.data.collections.get(name)
    if not col: print(f"[HUD] Collection not found: {name}")
    return col

def _get_camera(scene, name):
    cam = scene.objects.get(name)
    if not cam: print(f"[HUD] Camera not found: {name}")
    return cam

def _add_overlay(scene, cam_name, col_name):
    cam = _get_camera(scene, cam_name)
    col = _get_collection(col_name)
    if cam and col:
        try: scene.addOverlayCollection(cam, col)
        except Exception: pass

def _remove_overlay(scene, col_name):
    col = _get_collection(col_name)
    if col:
        try: scene.removeOverlayCollection(col)
        except Exception: pass

def _set_branch_visible(root_name, vis):
    for sc in logic.getSceneList():
        root = sc.objects.get(root_name)
        if not root: continue
        try: root.visible = bool(vis)
        except: pass
        try:
            for ch in root.childrenRecursive:
                try: ch.visible = bool(vis)
                except: pass
        except: pass

def _set_v2_only(shared=True, box=False, exhib=False, restor=False):
    _set_branch_visible(V2_SHARED, False)
    _set_branch_visible(V2_ADD_BOX, False)
    _set_branch_visible(V2_ADD_EXHIB, False)
    _set_branch_visible(V2_ADD_RESTOR, False)
    if shared: _set_branch_visible(V2_SHARED, True)
    if box:    _set_branch_visible(V2_ADD_BOX, True)
    if exhib:  _set_branch_visible(V2_ADD_EXHIB, True)
    if restor: _set_branch_visible(V2_ADD_RESTOR, True)

def _balloons_to_state(scene, state: str):
    anchor = BALLOON_POS_VISIBLE if state == 'visible' else BALLOON_POS_HIDDEN
    def _mv(n):
        obj = scene.objects.get(n); anc = scene.objects.get(anchor)
        if obj and anc:
            try:
                obj.worldPosition    = anc.worldPosition.copy()
                obj.worldOrientation = anc.worldOrientation.copy()
                obj.worldScale       = anc.worldScale.copy()
            except Exception:
                obj.worldPosition    = anc.worldPosition
                obj.worldOrientation = anc.worldOrientation
                obj.worldScale       = anc.worldScale
    _mv(BALLOON_L_NAME); _mv(BALLOON_R_NAME)
    try: scene.objects[BALLOON_MAIN_NAME].visible = (state != 'visible')
    except: pass

def _want_inventory_overlay():
    if bool(getattr(logic, "hud_inventory_v2_open", False)): return True
    if bool(getattr(logic, "hud_inventory_open",   False)): return True
    return False

def _ensure_overlay_state(scene):
    want_inv = _want_inventory_overlay()
    new_state = "INV" if want_inv else "HUD"
    if getattr(logic, "_last_overlay", "") == new_state:
        logic.blf_hidden = (new_state == "INV")
        return

    if want_inv:
        # HUD -> INVENTORY
        _remove_overlay(scene, HUD_COLLECTION_NAME)
        _add_overlay(scene,  INV_CAMERA_NAME, INV_COLLECTION_NAME)
        # OBJECTS: Always active on both cameras (added in init and never removed)
        logic.blf_hidden = True

        if bool(getattr(logic, "hud_inventory_v2_open", False)):
            _set_branch_visible(ROOT_V1, False)
            _set_branch_visible(ROOT_V2, True)
            _set_v2_only(shared=True, box=False, exhib=False, restor=False)
        else:
            _set_branch_visible(ROOT_V1, True)
            _set_branch_visible(ROOT_V2, False)
            _set_v2_only(shared=False, box=False, exhib=False, restor=False)
    else:
        # INVENTORY -> HUD
        _remove_overlay(scene, INV_COLLECTION_NAME)
        _add_overlay(scene,  HUD_CAMERA_NAME, HUD_COLLECTION_NAME)
        logic.blf_hidden = False

    logic._last_overlay = new_state

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main():
    format_hud_data()

    # Verify tasks after updating data to know if they have been completed
    try:
        import game_access
        game_access.check_tasks_completion()
    except Exception as e:
        print(f"Error verifying tasks: {e}")
    
    scene = bge.logic.getCurrentScene()

    if not logic._hud_overlay_ready:
        # 1) Initial config: HUD + OBJECTS on both cameras
        _remove_overlay(scene, INV_COLLECTION_NAME)
        _add_overlay(scene, HUD_CAMERA_NAME, HUD_COLLECTION_NAME)

        # OBJECTS to BOTH cameras: done once and never removed
        _add_overlay(scene, HUD_CAMERA_NAME, OBJECTS_COLLECTION_NAME)
        _add_overlay(scene, INV_CAMERA_NAME, OBJECTS_COLLECTION_NAME)

        logic.hud_inventory_open    = False
        logic.hud_inventory_v2_open = False
        logic.blf_hidden            = False
        logic._last_overlay         = "HUD"

        _set_branch_visible(ROOT_V2, False)
        _set_v2_only(shared=False, box=False, exhib=False, restor=False)
        _set_branch_visible(ROOT_V1, True)

        logic._hud_overlay_ready = True

    # Each frame: only converge to HUD or INV based on flags (I and V2 already update flags)
    _ensure_overlay_state(scene)