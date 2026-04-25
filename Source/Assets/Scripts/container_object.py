"""
container_object.py

Manages interactive container objects with proximity detection and V2 inventory system.

This script handles container interaction including proximity detection, mouse over effects,
keyboard input (I key), and opening the V2 inventory interface with proper validation.

Main Features:
    1. Proximity detection using Near sensor
    2. Mouse over/click detection with dedicated sensors
    3. Keyboard I key detection for interaction
    4. Automatic V2 inventory opening with container data
    5. Object validation (type matching, restoration status, space availability)
    6. Visual feedback via mouse over object positioning
    7. V2 context management and reset functionality
    8. Support for Box, Exhibition, and Restoration container types

Setup:
    Connect to Logic Bricks as Python controller with module 'container_object.handle'
    Required sensors: Near, Mouse.Over, Mouse.Click, Key.I
    Required actuators: Message.Info, Message.Inventory2, Message.Inventory

Configurable Variables:
    DEBUG_DEFAULT (int): Debug level (0=off, 1=events, 2=detailed)
    RADIUS (float): Detection radius for proximity (default: 2.0)
    PLAYER_NAME (str): Name of player object (default: 'Player')
    NEAR_SENSOR_NAME (str): Name of Near sensor (default: 'Near')
    MOUSE_OVER_SENSOR_NAME (str): Name of Mouse Over sensor (default: 'Mouse.Over')
    MOUSE_CLICK_SENSOR_NAME (str): Name of Mouse Click sensor (default: 'Mouse.Click')
    KEY_I_SENSOR_NAME (str): Name of Keyboard I sensor (default: 'Key.I')
    I_BLOCK_SECONDS (float): Anti-rebounce time for I key (default: 0.20)
    CLICK_BLOCK_SECONDS (float): Anti-rebounce time for mouse click (default: 0.20)
    MOUSE_OVER_OBJ_NAME (str): Object for mouse over effect (default: 'Container.Mouse.Over')
    V1_ROOT (str): V1 root empty name (default: 'Empty.View.1')
    V2_ROOT (str): V2 root empty name (default: 'Empty.View.2')
    POS_IN (str): Position for visible state (default: 'Empty.Pos.Inv.In')
    POS_OUT (str): Position for hidden state (default: 'Empty.Pos.Inv.Out')

Notes:
    - Requires objects with container properties: box_id, exhibition_id, or is_restor
    - Container types supported: box (storage), exhib (exhibition), restor (restoration)
    - Type validation checks period compatibility (pal, neo, bronze, iberian, roman)
    - V2 context is automatically reset when exiting proximity
    - Mouse over object is repositioned to provide visual feedback
    - All logs can be suppressed with SUPPRESS_ALL_LOGS = True

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
__description__ = "Manages interactive container objects with proximity detection and V2 inventory"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic, events
import bpy
import time

# =============================================================================
# CONFIGURATION
# =============================================================================
DEBUG_DEFAULT   = 1       # 0=off, 1=events, 2=detailed
RADIUS          = 2.0
PLAYER_NAME     = "Player"

# Sensor configuration
NEAR_SENSOR_NAME = "Near"                    # Player proximity sensor
MOUSE_OVER_SENSOR_NAME = "Mouse.Over"        # Mouse sensor with 'Mouse Over' option
MOUSE_CLICK_SENSOR_NAME = "Mouse.Click"      # Mouse sensor with 'Left Button' option
KEY_I_SENSOR_NAME = "Key.I"                  # Keyboard sensor for I key
SUPPRESS_ALL_LOGS = False                    # Log control

# Message actuator names in container object
ACT_INFO = "Message.Info"          # subject='add_info_text'
ACT_INV2 = "Message.Inventory2"    # subject='inventory2'
ACT_INV  = "Message.Inventory"     # subject='inventory' (used for inventory.show/hide)

# Subjects / bodies
SUBJ_INFO       = "add_info_text"
SUBJ_INV2       = "inventory2"
SUBJ_INV        = "inventory"
INFO_BODY_ENTER = "info.show|info_text|6|field=info_text"  # "You are facing a shelf..."
INFO_BODY_CLEAR = "info.show|info_text|0|field=info_text"  # clear (line 0)

# Information messages for cases without object
INFO_NO_OBJECT = "info.show|info_text|18|field=info_text"  # "You have no object to deposit"
INFO_TYPE_MISMATCH = "info.show|info_text|19|field=info_text"  # "This shelf is not from the correct period"

# Message repeat time (sec) and I key anti-rebounce
INFO_REPEAT_SECONDS = 0
I_BLOCK_SECONDS     = 0.20
CLICK_BLOCK_SECONDS = 0.20

# Object for mouse over effect
MOUSE_OVER_OBJ_NAME = "Container.Mouse.Over"
MOUSE_OVER_HIDDEN_POS = (0, 500, 0)  # Position outside camera

# Positioning empties
V1_ROOT = "Empty.View.1"
V2_ROOT = "Empty.View.2"
POS_IN  = "Empty.Pos.Inv.In"
POS_OUT = "Empty.Pos.Inv.Out"

# =============================================================================
# PROXIMITY DETECTION SYSTEM USING SENSORS
# =============================================================================

def _update_from_near_sensor(near_sensor):
    """Updates proximity state based on Near sensor
    
    Args:
        near_sensor: Near sensor configured in the controller
    
    Returns:
        tuple: (in_range, cached_player) - Proximity state and cached player reference
    """
    if not near_sensor:
        return False, None
    
    # Variables to store previous state
    if not hasattr(_update_from_near_sensor, '_prev_range_state'):
        _update_from_near_sensor._prev_range_state = False
        _update_from_near_sensor._cached_player = None
    
    current_state = near_sensor.positive
    
    # Detect transitions
    if current_state and not _update_from_near_sensor._prev_range_state:
        # Player ENTERED range
        # Search for player among objects activated by sensor
        for obj in near_sensor.hitObjectList:
            if hasattr(obj, 'get') and obj.get('player', False):
                _update_from_near_sensor._cached_player = obj
                break
        
        if not SUPPRESS_ALL_LOGS and DEBUG_DEFAULT >= 2:
            print(f"[container] SENSOR: Player entered range (Distance=2.0)")
        
        _update_from_near_sensor._prev_range_state = True
        return True, _update_from_near_sensor._cached_player
        
    elif not current_state and _update_from_near_sensor._prev_range_state:
        # Player EXITED range
        if not SUPPRESS_ALL_LOGS and DEBUG_DEFAULT >= 2:
            print(f"[container] SENSOR: Player exited range (Reset Distance=4.0)")
        
        _update_from_near_sensor._prev_range_state = False
        # Keep player cache in case it returns soon
        return False, _update_from_near_sensor._cached_player
    
    # Maintain current state
    _update_from_near_sensor._prev_range_state = current_state
    return current_state, _update_from_near_sensor._cached_player

# =============================================================================
# MOUSE DETECTION SYSTEM USING SENSORS
# =============================================================================

def _update_mouse_sensors(cont, own):
    """Updates mouse state based on sensors
    
    Args:
        cont: Object controller
        own: Object owner
    
    Returns:
        tuple: (mouse_over, mouse_click) - Mouse over and click state
    """
    mouse_over = False
    mouse_click = False
    
    # Mouse.Over sensor (Mouse type with 'Mouse Over' option)
    mouse_over_sensor = cont.sensors.get(MOUSE_OVER_SENSOR_NAME)
    if mouse_over_sensor and mouse_over_sensor.positive:
        mouse_over = True
        
        # Mouse.Click sensor (Mouse type with 'Left Button' option)
        mouse_click_sensor = cont.sensors.get(MOUSE_CLICK_SENSOR_NAME)
        if mouse_click_sensor and mouse_click_sensor.positive:
            mouse_click = True
    
    return mouse_over, mouse_click

# =============================================================================
# KEYBOARD DETECTION SYSTEM USING SENSORS
# =============================================================================

def _update_keyboard_sensors(cont):
    """Detects if I key has been pressed via sensor
    
    Args:
        cont: Object controller
    
    Returns:
        bool: True if I key detected, False otherwise
    """
    # Key.I sensor (Keyboard type for I key)
    key_i_sensor = cont.sensors.get(KEY_I_SENSOR_NAME)
    if key_i_sensor and key_i_sensor.positive:
        return True
    
    return False

def _get_player_reference():
    """Gets player reference (optimized with cache)
    
    Returns:
        KX_GameObject: Player reference or None
    """
    # 1. Try to use sensor cache
    cached_player = getattr(_update_from_near_sensor, '_cached_player', None)
    if cached_player:
        # Verify that cached object still exists and is valid
        try:
            if cached_player.invalid:
                _update_from_near_sensor._cached_player = None
            else:
                return cached_player
        except:
            _update_from_near_sensor._cached_player = None
    
    # 2. Fallback: search in scene (only if no cache)
    try:
        scene = logic.getCurrentScene()
        player = scene.objects.get(PLAYER_NAME)
        if player:
            _update_from_near_sensor._cached_player = player
        return player
    except:
        return None

def _dbg_level(own=None):
    try:
        if own is not None and "debug" in own: return int(own["debug"])
    except: pass
    try: return int(getattr(logic, "_container_debug", DEBUG_DEFAULT))
    except: return DEBUG_DEFAULT

def _log(own, lvl, *a):
    if not SUPPRESS_ALL_LOGS and _dbg_level(own) >= lvl: 
        print("[container]", *a)

def _act(cont, name, subj, body, own=None):
    try:
        a = cont.actuators[name]; a.subject=subj; a.body=body; cont.activate(a)
        _log(own, 1, f"ACT[{name}] -> {subj} :: {body}"); return True
    except Exception:
        try: logic.sendMessage(subj, body); _log(own, 2, f"sendMessage {subj} :: {body}"); return True
        except Exception as e2:
            if _dbg_level(own)>=1 and not SUPPRESS_ALL_LOGS: 
                print("[container] sendMessage ERR:", e2)
            return False

# Replace _player() with optimized cached version
def _player():
    return _get_player_reference()

def _dist(a,b):
    try: return (a.worldPosition - b.worldPosition).length
    except: return 1e9

# --------------------------------------------------------------------------
# V1/V2 movement by displacement
# --------------------------------------------------------------------------
def _move_root_to(name_root, name_target):
    scn = logic.getCurrentScene()
    if not scn: return False
    root = scn.objects.get(name_root)
    target = scn.objects.get(name_target)
    if not root: return False
    try:
        if target:
            root.worldTransform = target.worldTransform
        else:
            if name_target == POS_OUT:
                root.worldPosition = (1e6, 1e6, 1e6)
        return True
    except Exception:
        return False

def _view_set_v1_in():
    _move_root_to(V1_ROOT, POS_IN)
    _move_root_to(V2_ROOT, POS_OUT)
    try:
        logic.v1_is_in = True; logic.v2_is_in = False
    except: pass

def _view_set_v2_in():
    _move_root_to(V2_ROOT, POS_IN)
    _move_root_to(V1_ROOT, POS_OUT)
    try:
        logic.v2_is_in = True; logic.v1_is_in = False
    except: pass

# --------------------------------------------------------------------------
# Function to get/move mouse over object
# --------------------------------------------------------------------------
def _get_mouse_over_object():
    """Gets Container.Mouse.Over object from scene"""
    scene = logic.getCurrentScene()
    if not scene:
        return None
    
    mouse_over_obj = scene.objects.get(MOUSE_OVER_OBJ_NAME)
    if mouse_over_obj:
        return mouse_over_obj
    
    # Search by alternate name or create reference
    _log(None, 2, f"Object '{MOUSE_OVER_OBJ_NAME}' not found")
    return None

def _move_mouse_over_to_object(target_obj):
    """Moves mouse over object to target object's position"""
    mouse_over = _get_mouse_over_object()
    if not mouse_over or not target_obj:
        return False
    
    try:
        # Copy full transformation of target object
        mouse_over.worldTransform = target_obj.worldTransform
        _log(target_obj, 2, f"Mouse over moved to {target_obj.name}")
        return True
    except Exception as e:
        _log(target_obj, 1, f"Error moving mouse over: {e}")
        return False

def _hide_mouse_over():
    """Moves mouse over object outside camera view"""
    mouse_over = _get_mouse_over_object()
    if not mouse_over:
        return False
    
    try:
        mouse_over.worldPosition = MOUSE_OVER_HIDDEN_POS
        _log(None, 2, "Mouse over hidden")
        return True
    except Exception as e:
        _log(None, 1, f"Error hiding mouse over: {e}")
        return False

# --------------------------------------------------------------------------
# Detection and rules
# --------------------------------------------------------------------------
def _detect_kind(own):
    """Gets FRESH data from current container - WITH DETAILED DEBUGGING"""
    if not SUPPRESS_ALL_LOGS:
        print(f"\n[container] CONTAINER DETECTION: {own.name}")
    
    # List ALL object properties
    if not SUPPRESS_ALL_LOGS and _dbg_level(own) >= 3:
        print(f"[container] Properties of {own.name}:")
        for prop in own.getPropertyNames():
            value = own[prop]
            print(f"  * {prop}: {value} (type: {type(value).__name__})")
    
    # Search for SPECIFIC PROPERTIES
    box_id = int(own.get("box_id", 0))
    box_type = str(own.get("box_type", "")).strip()
    
    exhib_id = int(own.get("exhibition_id", 0))
    exhib_type = str(own.get("exhibition_type", "")).strip()
    
    is_restor = int(own.get("is_restor", 0))
    restor_id = int(own.get("restor_id", 0))
    restor_type = str(own.get("restor_type", "")).strip()
    
    if not SUPPRESS_ALL_LOGS and _dbg_level(own) >= 2:
        print(f"\n[container] Key values:")
        print(f"  * box_id: {box_id}, box_type: '{box_type}'")
        print(f"  * exhibition_id: {exhib_id}, exhibition_type: '{exhib_type}'")
        print(f"  * is_restor: {is_restor}, restor_id: {restor_id}, restor_type: '{restor_type}'")
    
    # ENHANCED DETECTION
    if box_id > 0 and box_type:
        box_type_lower = box_type.lower()
        box_total = int(own.get("box_total", 0))
        box_max = int(own.get("box_max", 0))
        if not SUPPRESS_ALL_LOGS:
            print(f"[container] BOX detection: id={box_id}, type={box_type_lower}")
        return ("box", box_id, box_type_lower, box_total, box_max)
        
    elif exhib_id > 0 and exhib_type:
        exhib_type_lower = exhib_type.lower()
        exhib_total = int(own.get("exhibition_total", 0))
        exhib_max = int(own.get("exhibition_max", 0))
        if not SUPPRESS_ALL_LOGS:
            print(f"[container] EXHIB detection: id={exhib_id}, type={exhib_type_lower}")
        return ("exhib", exhib_id, exhib_type_lower, exhib_total, exhib_max)
        
    elif is_restor == 1:
        restor_type_lower = restor_type.lower() if restor_type else ""
        if not SUPPRESS_ALL_LOGS:
            print(f"[container] RESTOR detection: id={restor_id}, type={restor_type_lower}")
        return ("restor", restor_id, restor_type_lower, 0, 0)
    
    # FALLBACK DETECTION BY NAME
    name_lower = own.name.lower()
    if not SUPPRESS_ALL_LOGS and _dbg_level(own) >= 2:
        print(f"[container] Analyzing name: '{name_lower}'")
    
    # Keyword to type mapping
    keywords_to_type = {
        "pal": "pal", "paleo": "pal", "paleolithic": "pal",
        "neo": "neo", "neolithic": "neo",
        "bronze": "bronze", "bronce": "bronze",
        "iberian": "iberian", "iberico": "iberian", "iber": "iberian",
        "roman": "roman", "romano": "roman", "roma": "roman"
    }
    
    for keyword, period_type in keywords_to_type.items():
        if keyword in name_lower:
            if not SUPPRESS_ALL_LOGS:
                print(f"[container] Name detection: keyword '{keyword}' -> type '{period_type}'")
            
            # Determine kind by keywords in name
            if "box" in name_lower or "shelf" in name_lower or "estanter" in name_lower:
                return ("box", 1, period_type, 0, 10)
            elif "exhib" in name_lower or "vitrina" in name_lower or "exposition" in name_lower:
                return ("exhib", 1, period_type, 0, 10)
            elif "restor" in name_lower or "laboratorio" in name_lower or "lab" in name_lower:
                return ("restor", 1, period_type, 0, 0)
    
    if not SUPPRESS_ALL_LOGS:
        print(f"[container] Could not detect container type")
    return ("", 0, "", 0, 0)

def _active_item():
    """Gets current active item - CORRECTED VERSION"""
    
    # FIRST: Try to get from active_collection_item
    it = getattr(logic, "active_collection_item", None)
    if isinstance(it, dict) and it.get("item_type") and it.get("item_id"): 
        if not SUPPRESS_ALL_LOGS:
            print(f"[container] Active object from logic.active_collection_item: {it.get('item_type')}#{it.get('item_id')}")
        return it
    
    # SECOND: Search in REAL inventory using game_access
    try:
        import game_access
        game = game_access.get_game()
        if not game:
            if not SUPPRESS_ALL_LOGS:
                print(f"[container] Game not found")
            return None
            
        state = game.state
        inventory = state.inventory
        collection_items = inventory.get("collection_items", {})
        
        if not SUPPRESS_ALL_LOGS and _dbg_level(None) >= 2:
            print(f"[container] Searching for active object in inventory...")
        
        # Option A: Latest acquired object (without storing)
        all_objects = []
        for period, items in collection_items.items():
            for item in items:
                # Create copy to not modify original
                item_copy = item.copy()
                item_copy["item_type"] = period  # Ensure type
                all_objects.append(item_copy)
                if not SUPPRESS_ALL_LOGS and _dbg_level(None) >= 3:
                    print(f"[container]   * {period}#{item.get('item_id', 0)} - restored={item.get('restored', 0)}, ubication={item.get('ubication', 0)}")
        
        if all_objects:
            # Filter objects NOT stored (ubication == 0)
            available_objects = [obj for obj in all_objects if int(obj.get("ubication", 0)) == 0]
            
            if available_objects:
                # Use latest available object (not stored)
                latest_available = available_objects[-1]
                if not SUPPRESS_ALL_LOGS:
                    print(f"[container] Latest available object: {latest_available.get('item_type')}#{latest_available.get('item_id', 0)}")
                return latest_available
            else:
                # If all are stored, use latest acquired
                latest_all = all_objects[-1]
                if not SUPPRESS_ALL_LOGS:
                    print(f"[container] All stored, using latest: {latest_all.get('item_type')}#{latest_all.get('item_id', 0)}")
                return latest_all
        
        if not SUPPRESS_ALL_LOGS:
            print(f"[container] No objects in inventory")
        return None
        
    except Exception as e:
        if not SUPPRESS_ALL_LOGS:
            print(f"[container] Error in _active_item: {e}")
        return None

def _eval_for_kind(kind, ctype, tot, mx):
    """Evaluates if active item can interact with this container - WITH DIAGNOSTICS"""
    it = _active_item() or {}
    item_type = str(it.get("item_type", "")).lower().strip()
    restored  = int(it.get("restored", 0))
    ubication = int(it.get("ubication", 0))
    exhibition = int(it.get("exhibition", 0))
    
    ctype_clean = str(ctype).lower().strip()
    
    reasons = []
    ok = True
    
    if not SUPPRESS_ALL_LOGS and _dbg_level(None) >= 2:
        print(f"[container] EVALUATION {kind.upper()}:")
        print(f"  * Container type: '{ctype_clean}'")
        print(f"  * Object type: '{item_type}'")
        print(f"  * Restored: {restored}")
        print(f"  * Ubication: {ubication}")
        print(f"  * Exhibition: {exhibition}")
        print(f"  * Space: {tot}/{mx}")
    
    if kind == "box":
        if item_type != ctype_clean: 
            reasons.append("type_mismatch")
            if not SUPPRESS_ALL_LOGS and _dbg_level(None) >= 2:
                print(f"  TYPE MISMATCH: '{item_type}' != '{ctype_clean}'")
        elif not SUPPRESS_ALL_LOGS and _dbg_level(None) >= 2:
            print(f"  TYPE MATCH: '{item_type}' == '{ctype_clean}'")
            
        if tot >= mx:          
            reasons.append("no_space")
            if not SUPPRESS_ALL_LOGS and _dbg_level(None) >= 2:
                print(f"  NO SPACE: {tot}/{mx}")
        elif not SUPPRESS_ALL_LOGS and _dbg_level(None) >= 2:
            print(f"  HAS SPACE: {tot}/{mx}")
            
        if restored == 0:      
            reasons.append("need_restore")
            if not SUPPRESS_ALL_LOGS and _dbg_level(None) >= 2:
                print(f"  NEEDS RESTORATION: restored={restored}")
        elif not SUPPRESS_ALL_LOGS and _dbg_level(None) >= 2:
            print(f"  RESTORED: restored={restored}")
            
        ok = not reasons
        
    elif kind == "exhib":
        if item_type != ctype_clean:     
            reasons.append("type_mismatch")
            if not SUPPRESS_ALL_LOGS and _dbg_level(None) >= 2:
                print(f"  TYPE MISMATCH: '{item_type}' != '{ctype_clean}'")
        elif not SUPPRESS_ALL_LOGS and _dbg_level(None) >= 2:
            print(f"  TYPE MATCH: '{item_type}' == '{ctype_clean}'")
            
        if tot >= mx:              
            reasons.append("no_space")
            if not SUPPRESS_ALL_LOGS and _dbg_level(None) >= 2:
                print(f"  NO SPACE: {tot}/{mx}")
        elif not SUPPRESS_ALL_LOGS and _dbg_level(None) >= 2:
            print(f"  HAS SPACE: {tot}/{mx}")
            
        if ubication == 0:         
            reasons.append("not_inventoried")
            if not SUPPRESS_ALL_LOGS and _dbg_level(None) >= 2:
                print(f"  NOT INVENTORIED: ubication={ubication}")
        elif not SUPPRESS_ALL_LOGS and _dbg_level(None) >= 2:
            print(f"  INVENTORIED: ubication={ubication}")
            
        if restored not in (1,2):  
            reasons.append("not_restored")
            if not SUPPRESS_ALL_LOGS and _dbg_level(None) >= 2:
                print(f"  NOT RESTORED: restored={restored}")
        elif not SUPPRESS_ALL_LOGS and _dbg_level(None) >= 2:
            print(f"  RESTORED: restored={restored}")
            
        ok = not reasons
        
    elif kind == "restor":
        if restored != 0:          
            reasons.append("no_need")
            if not SUPPRESS_ALL_LOGS and _dbg_level(None) >= 2:
                print(f"  DOES NOT NEED RESTORATION: restored={restored}")
        elif not SUPPRESS_ALL_LOGS and _dbg_level(None) >= 2:
            print(f"  NEEDS RESTORATION: restored={restored}")
            
        ok = not reasons
    
    if not SUPPRESS_ALL_LOGS and _dbg_level(None) >= 2:
        print(f"  RESULT: {'OK' if ok else 'FAILED'}, Reasons: {reasons}")
    
    return ok, reasons

# --------------------------------------------------------------------------
# Overlay state/flags helpers
# --------------------------------------------------------------------------
def _set_overlay_flags(inv_open_v2: bool):
    try:
        logic.hud_inventory_v2_open = bool(inv_open_v2)
        logic.hud_inventory_open    = False if inv_open_v2 else bool(getattr(logic, "hud_inventory_open", False))
        logic._force_inventory_open = bool(inv_open_v2)
        logic._auto_v2_active       = bool(inv_open_v2)
        _log(None, 2, f"Flags: v2_open={inv_open_v2}, auto_active={inv_open_v2}")
    except Exception as e:
        _log(None, 1, f"Error setting overlay flags: {e}")

def _block_global_I(dt=I_BLOCK_SECONDS):
    try: logic._i_block_until = float(logic.getRealTime()) + float(dt)
    except: pass

def _block_global_click(dt=CLICK_BLOCK_SECONDS):
    try: logic._click_block_until = float(logic.getRealTime()) + float(dt)
    except: pass

# --------------------------------------------------------------------------
# Mouse over handling with object (REPLACES MATERIAL LOGIC)
# --------------------------------------------------------------------------
def _handle_mouse_over_object(cont, own, current_mouse_over):
    """Handles mouse over object positioning - REPLACES MATERIAL LOGIC"""
    previous_mouse_over = own.get("_was_mouse_over", False)
    
    # When mouse enters object (mouse over) and we are in range
    if current_mouse_over and not previous_mouse_over and own["_in_range"]:
        # Move Container.Mouse.Over object to container position
        if _move_mouse_over_to_object(own):
            own["_was_mouse_over"] = True
            _log(own, 1, "MOUSE_OVER - Object positioned")
    
    # When mouse exits object (mouse out)
    elif not current_mouse_over and previous_mouse_over:
        # Hide Container.Mouse.Over object
        if _hide_mouse_over():
            own["_was_mouse_over"] = False
            _log(own, 1, "MOUSE_EXITED - Object hidden")
    
    # When exiting container range
    elif not own["_in_range"] and previous_mouse_over:
        # Hide Container.Mouse.Over object
        if _hide_mouse_over():
            own["_was_mouse_over"] = False
            _log(own, 1, "Out of range - Object hidden")

# --------------------------------------------------------------------------
# MANUAL V2 CONTEXT RESET
# --------------------------------------------------------------------------
def _force_v2_context_reset():
    """Manually resets V2 context"""
    _log(None, 1, "MANUAL RESET OF V2 CONTEXT (WITH ACTIVE CLEANUP)")
    
    try:
        if hasattr(logic, "active_collection_item"):
            old_value = logic.active_collection_item
            logic.active_collection_item = None
            _log(None, 2, f"active_collection_item removed: {old_value}")
        
        if hasattr(logic, "v2ctx"):
            logic.v2ctx.update({
                "open": False,
                "kind": "",
                "origin": "",
                "box_id": 0,
                "box_type": "",
                "room_total": 0,
                "room_max": 0,
                "item_dict": None,
                "kx_item": None,
                "card_obj": None,
                "_card_parent": None,
                "_card_matrix": None,
            })
            _log(None, 2, "V2 context reset")
        
        logic.hud_inventory_v2_open = False
        logic._auto_v2_active = False
        logic._force_inventory_open = False
        
        try:
            import game_access
            game = game_access.get_game()
            if game and hasattr(game, 'hud_text'):
                game.hud_text.info_text_v2 = ""
                game.hud_text.item_desc_text = ""
                _log(None, 2, "HUD texts cleared")
        except:
            pass
        
        _log(None, 1, "Manual V2 reset completed with full cleanup")
        
    except Exception as e:
        _log(None, 1, f"Error in manual V2 reset: {e}")

# --------------------------------------------------------------------------
# SIMPLIFIED LOGIC: Check if object available
# --------------------------------------------------------------------------
def _show_info_message_and_return(cont, own, message_body):
    """
    Shows an info message and does NOT open any view.
    Returns True to indicate interaction was handled.
    """
    _act(cont, ACT_INFO, SUBJ_INFO, message_body, own=own)
    _log(own, 1, f"Message shown: {message_body}")
    _block_global_I()
    _block_global_click()
    return True

def _try_open_v2_or_show_message(cont, own, trigger_source="proximity"):
    """CORRECTED LOGIC WITH COMPLETE DIAGNOSTICS"""
    if not SUPPRESS_ALL_LOGS:
        print(f"\n{'='*60}")
        print(f"[container] INTERACTION: {own.name} (trigger: {trigger_source})")
        print(f"{'='*60}")
    
    # Show container properties
    _debug_container_properties(own)
    
    # 1. Get active item
    it = _active_item()
    
    if not it:
        if not SUPPRESS_ALL_LOGS:
            print(f"[container] CASE 3: No active object")
            print(f"[container] Showing message: No object available")
        return _show_info_message_and_return(cont, own, INFO_NO_OBJECT)
    
    if not SUPPRESS_ALL_LOGS:
        print(f"[container] Active object detected:")
        print(f"  * Type: {it.get('item_type', 'NO TYPE')}")
        print(f"  * ID: {it.get('item_id', 'NO ID')}")
        print(f"  * Restored: {it.get('restored', 0)}")
        print(f"  * Ubication: {it.get('ubication', 0)}")
        print(f"  * Exhibition: {it.get('exhibition', 0)}")
    
    # 2. Get container data
    kind, cid, ctype, tot, mx = _detect_kind(own)
    
    if not kind:
        if not SUPPRESS_ALL_LOGS:
            print(f"[container] Could not detect container type")
        return False
    
    if not SUPPRESS_ALL_LOGS:
        print(f"[container] Container detected:")
        print(f"  * Type: {kind}")
        print(f"  * Period: '{ctype}'")
        print(f"  * ID: {cid}")
        print(f"  * Space: {tot}/{mx}")
    
    # 3. Verify type compatibility
    item_type = str(it.get("item_type", "")).lower().strip()
    ctype_clean = str(ctype).lower().strip()
    
    if not SUPPRESS_ALL_LOGS:
        print(f"[container] Type comparison:")
        print(f"  * Object: '{item_type}'")
        print(f"  * Container: '{ctype_clean}'")
        print(f"  * Match: {item_type == ctype_clean}")
    
    if item_type != ctype_clean:
        if not SUPPRESS_ALL_LOGS:
            print(f"[container] CASE 4b: Type mismatch ('{item_type}' != '{ctype_clean}')")
            
            # DIAGNOSTIC: Why doesn't it match?
            possible_matches = []
            if "pal" in item_type and "pal" in ctype_clean: possible_matches.append("pal")
            if "neo" in item_type and "neo" in ctype_clean: possible_matches.append("neo")
            if "bronze" in item_type and "bronze" in ctype_clean: possible_matches.append("bronze")
            if "iberian" in item_type and "iberian" in ctype_clean: possible_matches.append("iberian")
            if "roman" in item_type and "roman" in ctype_clean: possible_matches.append("roman")
            
            if possible_matches:
                print(f"[container] Possible partial matches: {possible_matches}")
        
        return _show_info_message_and_return(cont, own, INFO_TYPE_MISMATCH)
    
    if not SUPPRESS_ALL_LOGS:
        print(f"[container] CASE 4a: Types match ('{item_type}' == '{ctype_clean}')")
    
    # 4. Evaluate specific conditions for V2
    ok, reasons = _eval_for_kind(kind, ctype, tot, mx)
    
    # If object is already in THIS shelf
    current_ubication = int(it.get("ubication", 0))
    if kind == "box" and current_ubication == cid:
        if not SUPPRESS_ALL_LOGS:
            print(f"[container] Object ALREADY in this shelf ({cid})")
        body = "info.show|info_text|26|field=info_text"
        _act(cont, ACT_INFO, SUBJ_INFO, body, own=own)
        _block_global_I()
        _block_global_click()
        return True
    
    if not ok:
        if not SUPPRESS_ALL_LOGS:
            print(f"[container] Evaluation failed. Reasons: {reasons}")
        
        # Show specific message
        if "no_space" in reasons:
            body = "info.show|info_text|8|field=info_text" if kind == "box" else "info.show|info_text|11|field=info_text"
        elif "need_restore" in reasons or "not_restored" in reasons:
            body = "info.show|info_text|20|field=info_text"
        elif "not_inventoried" in reasons:
            body = "info.show|info_text|24|field=info_text"
        else:
            body = INFO_TYPE_MISMATCH
        
        _act(cont, ACT_INFO, SUBJ_INFO, body, own=own)
        _block_global_I()
        _block_global_click()
        return True
    
    # 5. If all OK, open V2
    if not SUPPRESS_ALL_LOGS:
        print(f"[container] ALL CONDITIONS MET -> Opening V2")
    
    # Ensure type is sent correctly
    container_type_clean = str(ctype).lower().strip()
    
    # Activate V2
    _set_overlay_flags(True)
    _act(cont, ACT_INV, SUBJ_INV, "inventory.show|view=2", own=own)
    _view_set_v2_in()
    
    # PREPARE MESSAGE WITH CORRECT TYPE
    body = f"open|kind={kind}|id={cid}|type={container_type_clean}|ok=1|reasons=|room_total={tot}|room_max={mx}|origin={trigger_source}|force_reset=true"
    
    if not SUPPRESS_ALL_LOGS:
        print(f"[container] Sending CONTAINER data {cid}: type={container_type_clean}, total={tot}/{mx}")
    
    _act(cont, ACT_INV2, SUBJ_INV2, body, own=own)
    _act(cont, ACT_INFO, SUBJ_INFO, INFO_BODY_CLEAR, own=own)
    _block_global_I()
    
    if not SUPPRESS_ALL_LOGS:
        print(f"[container] V2 OPEN ({trigger_source})")
        print(f"{'='*60}\n")
    
    return True


def _debug_container_properties(own):
    """Shows all container properties for debugging"""
    if SUPPRESS_ALL_LOGS or _dbg_level(own) < 2:
        return
        
    print(f"\n[DEBUG] CONTAINER PROPERTIES '{own.name}':")
    
    # Common container properties
    container_props = [
        "box_id", "box_type", "box_total", "box_max",
        "exhibition_id", "exhibition_type", "exhibition_total", "exhibition_max",
        "is_restor", "restor_id", "restor_type",
        "item_type", "period", "type", "container_type",
        "shelf_type", "exhib_type", "rack_type"
    ]
    
    found_props = []
    for prop in container_props:
        if prop in own:
            value = own[prop]
            print(f"  * {prop}: {repr(value)} (type: {type(value).__name__})")
            found_props.append(prop)
    
    # Also check all available properties
    all_props = list(own.getPropertyNames())
    other_props = [p for p in all_props if p not in container_props]
    
    if other_props:
        print(f"[DEBUG] Other properties:")
        for prop in other_props[:10]:  # Show only first 10
            value = own[prop]
            print(f"  * {prop}: {repr(value)}")
    
    if not found_props:
        print(f"  Warning: No container properties found")
    
    print()

# =============================================================================
# MAIN FUNCTION WITH SENSORS (OPTIMIZED)
# =============================================================================
def handle():
    cont = logic.getCurrentController()
    own  = cont.owner

    # Get sensors
    near_sensor = cont.sensors.get(NEAR_SENSOR_NAME)
    
    # Update proximity state from sensor
    in_range, cached_player = _update_from_near_sensor(near_sensor)
    
    # Set global proximity flag
    try:
        logic.near_shelf = in_range
    except: pass

    # Debug: Show container properties if needed
    if _dbg_level(own) >= 2 and not SUPPRESS_ALL_LOGS:
        _debug_container_properties(own)

    # Proximity edge detection
    was = bool(own.get("_in_range", False))
    if in_range != was:
        own["_in_range"] = in_range
        _log(own, 1, "RANGE:", "ENTER" if in_range else "EXIT")

        if in_range:
            if not own.get("_info_sent", False):
#                _act(cont, ACT_INFO, SUBJ_INFO, INFO_BODY_ENTER, own=own) # commented to avoid message spam in storage
                own["_info_sent"]  = True
                own["_info_time"]  = float(logic.getRealTime())
        else:
            # Exited proximity
            if bool(getattr(logic, "_auto_v2_active", False)):
                _act(cont, ACT_INV2, SUBJ_INV2, "close|who=container_exit|force_reset=true", own=own)
                _set_overlay_flags(False)
                _act(cont, ACT_INV, SUBJ_INV, "inventory.hide|view=2", own=own)
                _force_v2_context_reset()
            
            # Hide mouse over object when exiting range
            if own.get("_was_mouse_over", False):
                _hide_mouse_over()
                own["_was_mouse_over"] = False
            
            _force_v2_context_reset()
            _view_set_v1_in()
            _act(cont, ACT_INFO, SUBJ_INFO, INFO_BODY_CLEAR, own=own)
            own["_info_sent"] = False
            own["_info_time"] = 0.0
            own["_current_container_id"] = 0
            own["_current_container_kind"] = ""
            
            return

    if not in_range:
        return

    # Periodic resend (optional)
    if INFO_REPEAT_SECONDS > 0:
        last = float(own.get("_info_time", 0.0)); now = float(logic.getRealTime())
        if now - last >= float(INFO_REPEAT_SECONDS):
            _act(cont, ACT_INFO, SUBJ_INFO, INFO_BODY_ENTER, own=own)
            own["_info_time"] = now

    # Check UI blocking
    if getattr(logic, "hud_pause_open", False) or \
       getattr(logic, "hud_inventory_open", False) or \
       getattr(logic, "hud_inventory_v2_open", False):
        return
    
    # Detect mouse over and click via sensors
    mouse_over, mouse_click = _update_mouse_sensors(cont, own)
    
    # Detect I key via sensor
    i_edge = _update_keyboard_sensors(cont)
    
    # Check I key anti-rebounce
    try:
        if float(getattr(logic, "_i_block_until", 0.0)) > float(logic.getRealTime()):
            i_edge = False
    except: pass
    
    # Handle mouse over with object (REPLACES MATERIAL LOGIC)
    _handle_mouse_over_object(cont, own, mouse_over)
    
    # Handle click: Use new simplified logic
    if mouse_over and mouse_click:
        try:
            if float(getattr(logic, "_click_block_until", 0.0)) > float(logic.getRealTime()):
                _log(own, 2, "Click blocked by anti-rebounce")
                return
        except: pass
        
        _log(own, 1, "CLICK on container (sensor)")
        _try_open_v2_or_show_message(cont, own, "mouse_click")
        _block_global_click()
        return

    # Do NOT auto-activate if user is interacting
    if bool(getattr(logic, "hud_inventory_open", False)):
        _log(own, 2, "User using V1 manually - ignoring auto activation")
        return

    # Handle I key (from sensor)
    if i_edge:
        _try_open_v2_or_show_message(cont, own, "proximity-I")
        return
    
    # Add diagnostics when interaction is detected
    if (i_edge or mouse_click) and not SUPPRESS_ALL_LOGS and _dbg_level(own) >= 1:
        print(f"\n[container] INTERACTION DETECTED on {own.name}:")
        print(f"  * Trigger: {'I key (sensor)' if i_edge else 'click (sensor)'}")
        print(f"  * In range: {in_range}")
        print(f"  * Mouse over: {mouse_over}")
        _debug_container_properties(own)