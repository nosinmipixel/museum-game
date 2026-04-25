"""
inventory_module.py

Manages inventory display, text updates, and icon visibility for V1 inventory.

This script handles the V1 inventory view including text updates for item counts,
collection statistics, restoration alerts, and icon visibility based on item state.

Main Features:
    1. Update inventory text displays (totals by period, general items, collection items)
    2. Manage icon visibility for Box, Exhibition, and Restoration states
    3. Apply tint colors (red/gray) for inventory alerts
    4. Load localized text from JSON files
    5. Handle inventory show/hide with suspend/resume messaging
    6. Integrate with game_access for inventory data
    7. Initialize and manage icon visibility system

Setup:
    Connect to Logic Bricks as Python controller with module 'inventory_module.main'
    Message sensor with subject 'inventory' required for inventory.show/hide commands

Configurable Variables:
    INV_MESSAGE_SENSOR_NAME (str): Message sensor name (default: 'Message.Inventory')
    INV_MESSAGE_SUBJECT (str): Message subject (default: 'inventory')
    DEFAULT_TINT (tuple): Default gray tint for notices (default: (0.85, 0.85, 0.85, 1.00))
    ALERT_TINT (tuple): Red alert tint (default: (1.00, 0.00, 0.00, 1.00))
    FALLBACK_LANG (str): Fallback language (default: 'es')

Notes:
    - Requires game_access module for inventory data
    - JSON file named 'general_text_{lang}.json' in //Assets/Texts/ folder
    - Icons are named 'Icon.{Type}.{Period}.{Id}' (Type: Box, Exhib, Rest)
    - Icon visibility is derived from item properties (ubication, exhibition, restored)
    - Sends suspend/resume messages to 'suspend_logic' subject
    - V1 and V2 inventory states are mutually exclusive

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
__description__ = "Manages inventory display, text updates, and icon visibility for V1 inventory"

# =============================================================================
# IMPORTS
# =============================================================================
import json, os
import bge
from bge import logic
import game_access

# =============================================================================
# CONFIGURATION
# =============================================================================
INV_MESSAGE_SENSOR_NAME = "Message.Inventory"
INV_MESSAGE_SUBJECT     = "inventory"

# Text objects (summaries)
TXT_GENERAL_TOTAL    = "Text.Inv.Gen.Items"
TXT_COLLECTION_TOTAL = "Text.Inv.Col.Items"
TXT_EXHIB_TOTAL      = "Text.Inv.Exhib.Items"

# Titles by period
TXT_TITLES = (
    "Text.Title.Pal",
    "Text.Title.Neo",
    "Text.Title.Bronze",
    "Text.Title.Iberian",
    "Text.Title.Roman",
)

# Counters by period
TXT_TOTAL_BY_TYPE = {
    "pal":     "Text.Total.Pal",
    "neo":     "Text.Total.Neo",
    "bronze":  "Text.Total.Bronze",
    "iberian": "Text.Total.Iberian",
    "roman":   "Text.Total.Roman",
}

# Notices (ONLY these change color/material)
TXT_NEED_INVENT = "Text.Inv.Invent.Items"
TXT_NEED_RESTOR = "Text.Inv.Restored.Items"

# Tinting for notices (replaces material system)
DEFAULT_TINT = (0.85, 0.85, 0.85, 1.00)  # Light gray
ALERT_TINT   = (1.00, 0.00, 0.00, 1.00)  # Red

# Text JSON
TEXTS_BASE_PATH     = "//Assets/Texts/"
GENERAL_TEXT_PREFIX = "general_text_"
FALLBACK_LANG       = "es"

# =============================================================================
# ICON SYSTEM
# =============================================================================
ICON_TYPES = ["Box", "Exhib", "Rest"]
PERIODS = ["Pal", "Neo", "Bronze", "Iberian", "Roman"]
ITEM_COUNTS = [1, 2]  # For Pal, Neo, Bronze, Iberian, Roman

# Parent of all icons in V1
ICON_PARENT_NAME = "Empty.Icon.V1"

def _get_icon_name(icon_type, period, item_id):
    """Generates icon object name: Icon.Box.Pal.1, Icon.Exhib.Neo.2, etc."""
    return f"Icon.{icon_type}.{period}.{item_id}"

def _force_all_icons_invisible():
    """Forces ALL icons to be invisible - direct and safe method"""
    sc = logic.getCurrentScene()
    if not sc:
        return
        
    icons_processed = 0
    icons_with_errors = 0
    
    # Direct method: search for all objects starting with "Icon."
    for obj in sc.objects:
        if obj.name.startswith("Icon."):
            try:
                # Method 1: try to set visibility directly
                obj.visible = False
                icons_processed += 1
            except Exception as e:
                try:
                    # Method 2: alternative for UPBGE
                    obj.setVisible(False, True)
                    icons_processed += 1
                except Exception as e2:
                    icons_with_errors += 1
    
    if icons_with_errors > 0:
        print(f"[icons] Forced invisible: {icons_processed} icons, {icons_with_errors} errors")

def _initialize_icons():
    """Initializes all icons as invisible at game start"""
    sc = logic.getCurrentScene()
    if not sc:
        return
        
    # Initialize only once
    if hasattr(logic, "_icons_initialized"):
        return
    logic._icons_initialized = True
    
    # Force all icons invisible immediately
    _force_all_icons_invisible()
    
    # Get icon parent
    icon_parent = sc.objects.get(ICON_PARENT_NAME)
    if not icon_parent:
        return
    
    # Configure parent visibility
    try:
        icon_parent.visible = True
    except Exception as e:
        pass

def _safe_set_visibility(obj, visible):
    """Sets visibility safely, handling potential errors"""
    try:
        obj.visible = bool(visible)
        return True
    except Exception as e:
        try:
            obj.setVisible(bool(visible), True)
            return True
        except Exception as e2:
            return False

def _update_icon_visibility():
    """Updates visibility of all icons based on inventory state"""
    sc = logic.getCurrentScene()
    if not sc:
        return
        
    # Get inventory from game_access (NEW ARCHITECTURE)
    game = game_access.get_game()
    if not game:
        return
        
    collection_items = game.state.inventory.get("collection_items", {})
    icons_updated = 0
    
    # Period mapping to lowercase to match inventory
    period_map = {
        "Pal": "pal", "Neo": "neo", "Bronze": "bronze", 
        "Iberian": "iberian", "Roman": "roman"
    }
    
    # FIRST: ensure all icons are invisible by default
    for period in PERIODS:
        for item_id in ITEM_COUNTS:
            for icon_type in ICON_TYPES:
                icon_name = _get_icon_name(icon_type, period, item_id)
                icon_obj = sc.objects.get(icon_name)
                if icon_obj:
                    _safe_set_visibility(icon_obj, False)
    
    # THEN: make visible only those that meet conditions
    for period in PERIODS:
        period_lower = period_map.get(period, period.lower())
        items = collection_items.get(period_lower, [])
        
        for item in items:
            try:
                # Get item properties
                item_id = int(item.get("item_id", 0))
                if item_id == 0:
                    continue
                    
                ubication = int(item.get("ubication", 0))
                exhibition = int(item.get("exhibition", 0))
                restored = int(item.get("restored", 0))
                
                # BOX icon: visible if item has ubication > 0
                if ubication > 0:
                    box_icon_name = _get_icon_name("Box", period, item_id)
                    box_icon = sc.objects.get(box_icon_name)
                    if box_icon:
                        if _safe_set_visibility(box_icon, True):
                            icons_updated += 1
                
                # EXHIB icon: visible if item has exhibition > 0
                if exhibition > 0:
                    exhib_icon_name = _get_icon_name("Exhib", period, item_id)
                    exhib_icon = sc.objects.get(exhib_icon_name)
                    if exhib_icon:
                        if _safe_set_visibility(exhib_icon, True):
                            icons_updated += 1
                
                # REST icon: visible if item has restored != 0
                if restored != 0:
                    rest_icon_name = _get_icon_name("Rest", period, item_id)
                    rest_icon = sc.objects.get(rest_icon_name)
                    if rest_icon:
                        if _safe_set_visibility(rest_icon, True):
                            icons_updated += 1
                        
            except Exception as e:
                pass

# =============================================================================
# DEBUG
# =============================================================================
if not hasattr(logic, "_inv_debug"):
    logic._inv_debug = 0  # 0..3

def _log(level, *args):
    if getattr(logic, "_inv_debug", 0) >= level:
        print("[inv] ", *args)

def _set_debug_level(x):
    try: n = int(x)
    except: n = 0
    logic._inv_debug = max(0, min(n, 3))
    _log(1, "DEBUG =", logic._inv_debug)

# =============================================================================
# KX HELPERS
# =============================================================================
def _kx(obj_name):
    try:
        return logic.getCurrentScene().objects.get(obj_name)
    except:
        return None

def _set_text_kx(obj_name: str, text: str) -> bool:
    ob = _kx(obj_name)
    if not ob: return False
    try:
        ob["Text"] = text
        _log(2, f"set_text KX['Text'] OK -> {obj_name} = '{text}'")
        return True
    except Exception as e:
        _log(2, f"set_text KX['Text'] FAIL {obj_name}: {e}")
    try:
        ob.text = text
        _log(2, f"set_text KX OK -> {obj_name} = '{text}'")
        return True
    except Exception as e:
        _log(2, f"set_text KX FAIL {obj_name}: {e}")
    return False

def _set_color_kx(obj_name: str, rgba) -> bool:
    """Sets color/tint of a text object"""
    ob = _kx(obj_name)
    if not ob: return False
    try:
        r,g,b,a = (list(rgba)+[1.0])[:4]
        ob.color = [float(r), float(g), float(b), float(a)]
        _log(3, f"set_color KX OK -> {obj_name} = {ob.color}")
        return True
    except Exception as e:
        _log(3, f"set_color KX FAIL {obj_name}: {e}")
        return False

# =============================================================================
# NOTICE TINTING SYSTEM
# =============================================================================
def _set_notice_tint(obj_name: str, is_alert: bool):
    """Applies tint to notices (replaces material system)
    
    Args:
        obj_name: Name of the text object
        is_alert: True for red color (alert), False for gray (normal)
    """
    target_tint = ALERT_TINT if is_alert else DEFAULT_TINT
    ok = _set_color_kx(obj_name, target_tint)
    
    if ok:
        _log(2, f"Tint {'RED' if is_alert else 'GRAY'} -> {obj_name}")
    else:
        _log(1, f"Error applying tint to {obj_name}")

# =============================================================================
# JSON TEXTS
# =============================================================================
def _safe_expand(rel):
    if not rel.startswith("//"): rel = "//"+rel
    return logic.expandPath(rel)

def _get_lang():
    """Gets language from game_access (NEW ARCHITECTURE)"""
    try:
        game = game_access.get_game()
        if game and hasattr(game.state, 'language'):
            return game.state.language
    except Exception:
        pass
    return FALLBACK_LANG

def _load_general_texts(lang=None):
    if not hasattr(logic, "_general_texts_cache"):
        logic._general_texts_cache = {}
    if lang is None: lang = _get_lang()
    if lang in logic._general_texts_cache:
        return logic._general_texts_cache[lang]

    tried = []
    for cand in (lang, FALLBACK_LANG):
        fname = f"{GENERAL_TEXT_PREFIX}{cand}.json"
        path  = _safe_expand(os.path.join(TEXTS_BASE_PATH, fname))
        tried.append(path)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                logic._general_texts_cache[cand] = data
                _log(1, "Texts loaded:", path)
                return data
            except Exception as e:
                _log(1, "Error reading", path, e)
    _log(1, "Could not load texts. Tried:", tried)
    logic._general_texts_cache[lang] = {}
    return {}

def _get_inventory_text(idx, default=""):
    data = _load_general_texts() or {}
    arr  = data.get("inventory_text", [])
    i    = idx - 1
    if 0 <= i < len(arr):
        return str(arr[i])
    return default

# =============================================================================
# INVENTORY (derived state) - NEW ARCHITECTURE
# =============================================================================
def _ensure_inv():
    """Gets inventory from game_access"""
    game = game_access.get_game()
    if not game:
        return None
    
    # If inventory doesn't exist in state, initialize it
    if not hasattr(game.state, 'inventory') or not isinstance(game.state.inventory, dict):
        game.state.inventory = {
            "collection_items": {"pal":[], "neo":[], "bronze":[], "iberian":[], "roman":[]},
            "general_items_total": 0,
            "boxes": {},
            "exhibitions": {}
        }
    return game.state.inventory

def _derive(inv):
    if not inv:
        return {
            "by_type": {},
            "collection_items_total": 0,
            "inventoried_items": 0,
            "exhibited_items": 0,
            "restored_pending": False
        }
        
    coll = inv.get("collection_items", {})
    by_type = {k: len(v) for k, v in coll.items()}
    collection_total = sum(by_type.values())
    inventoried = 0
    exhibited   = 0
    restored_pending = False
    for bucket in coll.values():
        for it in bucket:
            try:
                if int(it.get("ubication",0)) > 0: inventoried += 1
                if int(it.get("exhibition",0))>0: exhibited   += 1
                if int(it.get("restored",0)) in (0,3): restored_pending = True
            except: pass
    return {
        "by_type": by_type,
        "collection_items_total": collection_total,
        "inventoried_items": inventoried,
        "exhibited_items": exhibited,
        "restored_pending": restored_pending
    }

# =============================================================================
# RENDER VIEW 1
# =============================================================================
def _update_view1():
    # Initialize icons if first time
    _initialize_icons()
    
    inv = _ensure_inv()
    if not inv:
        return
        
    d   = _derive(inv)

    # 1) Titles
    titles = (
        _get_inventory_text(2, "Paleolithic objects:"),
        _get_inventory_text(3, "Neolithic objects:"),
        _get_inventory_text(4, "Bronze Age objects:"),
        _get_inventory_text(5, "Iberian objects:"),
        _get_inventory_text(6, "Roman objects:"),
    )
    for name, txt in zip(TXT_TITLES, titles):
        _set_text_kx(name, txt)

    # 2) Totals by period
    by_type = d["by_type"]
    for period, obj_name in TXT_TOTAL_BY_TYPE.items():
        count = int(by_type.get(period, 0))
        _set_text_kx(obj_name, str(count))

    # 3) General totals
    gen_label = _get_inventory_text(18, "General objects:")
    col_label = _get_inventory_text(19, "Collection objects:")
    _set_text_kx(TXT_GENERAL_TOTAL,    f"{gen_label} {int(inv.get('general_items_total',0))}")
    _set_text_kx(TXT_COLLECTION_TOTAL, f"{col_label} {int(d['collection_items_total'])}")

    # 4) Exhibited
    exhib_label = _get_inventory_text(18, "Exhibited objects:")
    _set_text_kx(TXT_EXHIB_TOTAL, f"{exhib_label} {int(d['exhibited_items'])}")

    # 5) Notices (two lines) + red/gray tinting only for these two
    def _two_lines(s: str) -> str:
        if not s: return ""
        if ":" in s:
            a,b = s.split(":",1)
            return (a + ":\n" + b.strip()).strip()
        mid = len(s)//2
        L = s.rfind(" ", 0, mid)
        R = s.find(" ", mid)
        cut = L if L!=-1 and (R==-1 or mid-L <= R-mid) else R
        return s[:cut].rstrip()+"\n"+s[cut+1:].lstrip() if cut!=-1 else s

    need_invent = (d["inventoried_items"] != d["collection_items_total"])
    need_restor = d["restored_pending"]

    txt_invent = _two_lines(_get_inventory_text(13 if need_invent else 14, "You need to shelve an object."))
    txt_restor = _two_lines(_get_inventory_text(15 if need_restor else 16, "You need to restore an object."))
    _set_text_kx(TXT_NEED_INVENT, txt_invent)
    _set_text_kx(TXT_NEED_RESTOR, txt_restor)

    # Apply tinting instead of material change
    _set_notice_tint(TXT_NEED_INVENT, need_invent)
    _set_notice_tint(TXT_NEED_RESTOR, need_restor)
    
    # 6) UPDATE ICON VISIBILITY
    _update_icon_visibility()

# =============================================================================
# SUSPENSION SYSTEM
# =============================================================================
def _send_suspend_message(action):
    """Sends message to suspension system - WITH IMPROVED LOGGING"""
    try:
        # Add detailed logging
        v1_state = getattr(logic, "hud_inventory_open", False)
        v2_state = getattr(logic, "hud_inventory_v2_open", False)
        pause_state = getattr(logic, "hud_pause_open", False)
        
        print(f"[Inventory] Sending V1 suspension: {action.upper()}")
        print(f"[Inventory]   * V1 state: {v1_state}")
        print(f"[Inventory]   * V2 state: {v2_state}")
        print(f"[Inventory]   * Pause state: {pause_state}")
        
        # Send message
        logic.sendMessage("suspend_logic", f"v1|{action}")
        print(f"[Inventory] Message sent: v1|{action}")
        
    except Exception as e:
        print(f"[Inventory] Error sending suspension: {e}")

# =============================================================================
# MESSAGING
# =============================================================================
def _get_msg(cont):
    s = cont.sensors.get(INV_MESSAGE_SENSOR_NAME)
    if s and s.positive and getattr(s, "subject", "") == INV_MESSAGE_SUBJECT:
        return s
    for sen in cont.sensors:
        if getattr(sen, "positive", False) and sen.__class__.__name__.endswith("MessageSensor"):
            if getattr(sen, "subject","") == INV_MESSAGE_SUBJECT:
                return sen
    return None

def _parse(body):
    parts = [t.strip() for t in (body or "").split("|") if t.strip()]
    out = {"cmd": parts[0] if parts else "", "args": {}}
    for p in parts[1:]:
        if "=" in p:
            k, v = p.split("=", 1)
            out["args"][k.strip()] = v.strip()
    return out

def _notify_hud(state: str):
    state = "INV" if state.upper() == "INV" else "HUD"
    sc = logic.getCurrentScene()
    frm = "Game.Controller" if sc and "Game.Controller" in sc.objects else ""
    try:
        logic.sendMessage("hud", f"set|state={state}", "", frm)
    except Exception as e:
        _log(1, f"Error sending HUD message: {e}")

def handle_message():
    cont = logic.getCurrentController()
    sen  = _get_msg(cont)
    if not (sen and sen.bodies): return
    for body in sen.bodies:
        data = _parse(body)
        cmd  = (data.get("cmd") or "").lower()
        _log(2, "msg:", body)
        
        if cmd == "inventory.debug":
            _set_debug_level(data["args"].get("level","1"))
            
        elif cmd == "inventory.show":
            # KEEP ORIGINAL LOGIC, only add logging
            if bool(getattr(logic, "hud_inventory_v2_open", False)):
                _log(1, "V2 active -> ignoring inventory.show")
                return
            if bool(getattr(logic, "hud_inventory_open", False)):
                _log(1, "V1 already open -> ignoring duplicate inventory.show")
                return
                
            logic.hud_inventory_open = True
            _update_view1()
            _notify_hud("INV")
            _send_suspend_message("suspend")  # <- THIS IS ALREADY CORRECT
            
            # Add logging for debug
            print(f"[Inventory] V1 opened via message - suspend sent")
            
        elif cmd == "inventory.hide":
            # KEEP ORIGINAL LOGIC, only add logging
            if not bool(getattr(logic, "hud_inventory_v2_open", False)) and bool(getattr(logic, "hud_inventory_open", False)):
                logic.hud_inventory_open = False
                _notify_hud("HUD")
                _send_suspend_message("resume")  # <- THIS IS ALREADY CORRECT
                
                # Add logging for debug
                print(f"[Inventory] V1 closed via message - resume sent")

def handle_v1_open():
    """Handles V1 opening in a consistent manner"""
    print(f"\n[Inventory] === STARTING V1 OPENING ===")
    
    # Check current states
    v2_open = bool(getattr(logic, "hud_inventory_v2_open", False))
    v1_open = bool(getattr(logic, "hud_inventory_open", False))
    pause_open = bool(getattr(logic, "hud_pause_open", False))
    
    print(f"[Inventory] Initial state:")
    print(f"  * V1 current: {v1_open}")
    print(f"  * V2 current: {v2_open}")
    print(f"  * Pause current: {pause_open}")
    
    # DO NOT open if V2 or Pause are active
    if v2_open or pause_open:
        print(f"[Inventory] NOT opening V1 (V2={v2_open}, Pause={pause_open})")
        return False
    
    # If already open, just update
    if v1_open:
        print(f"[Inventory] V1 already open - updating view")
        _update_view1()
        return True
    
    # NORMAL V1 OPENING
    print(f"[Inventory] OPENING V1...")
    
    # 1. Update state
    logic.hud_inventory_open = True
    logic.hud_inventory_v2_open = False  # Ensure V2 is closed
    
    # 2. Update view
    _update_view1()
    
    # 3. Notify HUD
    _notify_hud("INV")
    
    # 4. CRITICAL SUSPEND
    _send_suspend_message("suspend")
    
    # 5. Clear any residual active item
    if hasattr(logic, "active_collection_item"):
        logic.active_collection_item = None
        print(f"[Inventory] Active item cleared")
    
    print(f"[Inventory] V1 OPENED CORRECTLY AND SUSPENDED")
    print(f"[Inventory] === END V1 OPENING ===\n")
    return True

def handle_v1_close():
    """Handles V1 closing in a consistent manner"""
    print(f"\n[Inventory] === STARTING V1 CLOSING ===")
    
    # Check states
    v1_open = bool(getattr(logic, "hud_inventory_open", False))
    v2_open = bool(getattr(logic, "hud_inventory_v2_open", False))
    
    print(f"[Inventory] Initial state:")
    print(f"  * V1 current: {v1_open}")
    print(f"  * V2 current: {v2_open}")
    
    # Only close if V1 is actually open
    if not v1_open:
        print(f"[Inventory] V1 is not open - nothing to close")
        return False
    
    # If V2 is open, close V2 first
    if v2_open:
        print(f"[Inventory] Closing V2 first...")
        try:
            sc = logic.getCurrentScene()
            frm = "Game.Controller" if sc and "Game.Controller" in sc.objects else ""
            logic.sendMessage("inventory2", "close|force_reset=true", "", frm)
        except Exception as e:
            print(f"[Inventory] Error closing V2: {e}")
        
        # Update states
        logic.hud_inventory_v2_open = False
    
    # V1 CLOSING
    print(f"[Inventory] CLOSING V1...")
    
    # 1. Update state
    logic.hud_inventory_open = False
    
    # 2. Notify HUD
    _notify_hud("HUD")
    
    # 3. CRITICAL RESUME
    _send_suspend_message("resume")
    
    # 4. Clear active item
    if hasattr(logic, "active_collection_item"):
        logic.active_collection_item = None
        print(f"[Inventory] Active item cleared")
    
    print(f"[Inventory] V1 CLOSED CORRECTLY AND RESUMED")
    print(f"[Inventory] === END V1 CLOSING ===\n")
    return True

# =============================================================================
# LOOP
# =============================================================================
def main():
    try: 
        sc = logic.getCurrentScene()
        if not sc: return
    except: return
        
    # Initialize icons at start (just in case)
    _initialize_icons()
    
    if bool(getattr(logic, "hud_inventory_open", False)):
        _update_view1()