"""
inventory_view2.py

Manages the V2 inventory view for object details, shelving, exhibition, and restoration.

This script handles the detailed view of collection objects, allowing users to
shelve items in boxes, exhibit them in display cases, or send them for restoration.
It manages context state, card positioning, text displays, and button enable/disable logic.

Main Features:
    1. Display detailed object information (description, ID, restoration status)
    2. Position 3D card object on anchor point for visual reference
    3. Enable/disable action buttons based on object and container state
    4. Handle shelving (box), exhibition, and restoration actions
    5. Manage V2 context with full reset capabilities
    6. Synchronize changes with game_state inventory
    7. Support readonly mode (from V1 click) and interactive mode (from containers)
    8. Hide/restore other inventory cards during V2 operation

Setup:
    Connect to Logic Bricks as Python controller with module 'inventory_view2.handle_message'
    Message sensor with subject 'inventory2' required for open/apply/close commands

Configurable Variables:
    VERBOSE (bool): Enable verbose logging (default: False)
    ROOT_V2 (str): V2 root empty name (default: 'Empty.View.2')
    OBJ_IMAGE_POS (str): Anchor for card positioning (default: 'Object.Image.Pos')
    OBJ_TEXT_BOX_ID (str): Box ID text object (default: 'Text.Inv.Box.Id')
    OBJ_TEXT_EXHIB_ID (str): Exhibition ID text object (default: 'Text.Inv.Exhib.Id')
    OBJ_TEXT_RESTOR (str): Restoration text object (default: 'Text.Inv.Restor')
    BTN_BOX (str): Box button name (default: 'Button.To.Box')
    BTN_EXHIB (str): Exhibition button name (default: 'Button.To.Exhib')
    BTN_REST (str): Restoration button name (default: 'Button.To.Restor')

Notes:
    - Requires game_access module for inventory and game state
    - Requires game_achievements.py for object description cache
    - V2 context is stored in logic.v2ctx with open, kind, origin, box_id, box_type
    - Supports two modes: readonly (from V1 click) and interactive (from containers)
    - Sends suspend/resume messages to 'suspend_logic' subject
    - Object descriptions are loaded from JSON files in //Assets/Texts/objects_text_{lang}.json

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
__description__ = "Manages V2 inventory view for object details and actions"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic
import game_access

# =============================================================================
# DEBUG CONFIGURATION
# =============================================================================
VERBOSE = False  # Set to True for debugging
def _log(*a):
    if VERBOSE: print("[v2] ", *a)

# =============================================================================
# CONSTANTS
# =============================================================================
ROOT_V2       = "Empty.View.2"
OBJ_IMAGE_POS = "Object.Image.Pos"

OBJ_TEXT_BOX_ID    = "Text.Inv.Box.Id"
OBJ_TEXT_EXHIB_ID  = "Text.Inv.Exhib.Id"
OBJ_TEXT_RESTOR    = "Text.Inv.Restor"

BTN_BOX   = "Button.To.Box"
BTN_EXHIB = "Button.To.Exhib"
BTN_REST  = "Button.To.Restor"

# =============================================================================
# TEXT HELPERS
# =============================================================================
def _gt(section: str, idx: int, fallback: str = "") -> str:
    try:
        # Get texts from general_text.py cache
        if not hasattr(logic, "_general_cache"):
            return fallback
        G = logic._general_cache.get(_get_lang(), {})
        return str(G.get(section, [])[idx]) or fallback
    except Exception:
        return fallback

def _get_lang():
    """Get language from game_access"""
    try:
        game = game_access.get_game()
        if game and hasattr(game.state, 'language'):
            return game.state.language
    except Exception:
        pass
    return "es"

TXT_NO_OBJECT   = _gt("inventory_text", 21, "You have no object to deposit.")
TXT_TYPE_MIS    = _gt("inventory_text", 7,  "This shelf is not from the correct period.")
TXT_NO_SPACE    = _gt("inventory_text", 8,  "This shelf does not have enough space.")
TXT_VIT_MIS     = _gt("inventory_text", 10, "This display case is not from the correct period.")
TXT_VIT_NOSPACE = _gt("inventory_text", 11, "This display case does not have enough space.")
TXT_NEED_REST   = _gt("inventory_text", 20, "You need to restore the object before shelving it.")
PFX_BOX_ID      = _gt("inventory_text", 22, "Shelf number:")
PFX_EXHIB_ID    = _gt("inventory_text", 23, "Display case number:")

# =============================================================================
# V2 CONTEXT INITIALIZATION
# =============================================================================
if not hasattr(logic, "v2ctx"):
    logic.v2ctx = {
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
    }

# =============================================================================
# SCENE HELPERS
# =============================================================================
def _scn():
    try: return logic.getCurrentScene()
    except: return None

def _get(scene, name):
    try: return scene.objects.get(name)
    except: return None

def _set_visible_branch(root, visible=True):
    if not root: return
    try:
        root.visible = bool(visible)
    except Exception:
        try: root.setVisible(bool(visible), True)
        except: pass
    try:
        for ch in root.childrenRecursive:
            try: ch.visible = bool(visible)
            except Exception:
                try: ch.setVisible(bool(visible), True)
                except: pass
    except: pass

def _force_all_children_visible(root_name):
    scn = _scn()
    if not scn: return
    root = scn.objects.get(root_name)
    if root:
        _set_visible_branch(root, True)

def _set_text(obj_name: str, value: str):
    sc = _scn()
    if not sc: return False
    ob = _get(sc, obj_name)
    if not ob:
        _log("TXT obj not found:", obj_name); return False
    ok = False
    try:
        ob["Text"] = str(value); ok = True
    except Exception: pass
    if not ok:
        try: ob.text = str(value); ok = True
        except Exception: ok = False
    _log(f"TXT set {obj_name} = '{str(value)[:40]}{'...' if len(str(value))>40 else ''}' ok={ok}")
    return ok

def _set_button_disabled(name: str, disabled=True):
    sc = _scn()
    if not sc: return
    b = _get(sc, name)
    if not b: return
    b["button_disabled"] = bool(disabled)

def _enable_only_buttons(box=False, exhib=False, restor=False):
    _set_button_disabled(BTN_BOX,   not box)
    _set_button_disabled(BTN_EXHIB, not exhib)
    _set_button_disabled(BTN_REST,  not restor)
    _log("BTN enable:", f"box={box} exhib={exhib} restor={restor}")

# =============================================================================
# DESCRIPTION FROM CACHE
# =============================================================================
def _desc_from_cache(item_type: str, item_id: int) -> str:
    """Gets description from game_achievements.py cache"""
    
    # First attempt: direct cache
    if hasattr(logic, "_objects_text_cache"):
        cache = logic._objects_text_cache
        try:
            bucket = cache.get(item_type, {}) or cache.get(str(item_type), {}) or {}
            desc = bucket.get(int(item_id), "") or bucket.get(str(int(item_id)), "")
            if desc:
                return desc
        except Exception:
            pass
    
    # Second attempt: globalDict
    if hasattr(logic, "globalDict") and "objects_text" in logic.globalDict:
        try:
            cache = logic.globalDict["objects_text"]
            bucket = cache.get(item_type, {}) or cache.get(str(item_type), {}) or {}
            desc = bucket.get(int(item_id), "") or bucket.get(str(int(item_id)), "")
            if desc:
                return desc
        except Exception:
            pass
    
    # Third: Load directly from JSON if not cached
    try:
        import json, os
        lang = _get_lang()
        fname = f"objects_text_{lang}.json"
        path = logic.expandPath(f"//Assets/Texts/{fname}")
        
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            items = data.get("collection_items", {}).get(item_type, [])
            for item in items:
                if item.get("id") == item_id:
                    return item.get("description", "")
    except Exception:
        pass
    
    return f"Description not available for {item_type}#{item_id}"

# =============================================================================
# ACTIVE ITEM FUNCTIONS
# =============================================================================
def _active_item_dict():
    """Get active item - IMPROVED VERSION USING CONTAINER TYPE"""
    # FIRST: If V2 is in interactive mode, look for object matching container type
    ctx = logic.v2ctx
    
    if ctx.get("open") and ctx.get("kind") in ["box", "exhib", "restor"]:
        container_type = ctx.get("box_type", "")
        if container_type:
            print(f"[V2] active_item_dict: Mode {ctx.get('kind')}, looking for object type '{container_type}'")
            item = _find_item_by_type(container_type)
            if item:
                print(f"[V2] active_item_dict: Found {container_type}#{item.get('item_id')}")
                return item
    
    # SECOND: For readonly mode, use context
    if ctx.get("kind") == "readonly" and ctx.get("item_dict"):
        print(f"[V2] active_item_dict: Using item from readonly context")
        return ctx["item_dict"]
    
    # THIRD: Fallback to general search
    print(f"[V2] active_item_dict: Using general search")
    
    game = game_access.get_game()
    if not game:
        print(f"[V2] active_item_dict: Game not found")
        return None
        
    inv = game.state.inventory
    collection_items = inv.get("collection_items", {})
    
    # Find latest acquired object of any type
    all_items = []
    for period, lst in collection_items.items():
        for item in lst:
            item_copy = item.copy()
            item_copy["item_type"] = period
            all_items.append(item_copy)
    
    if all_items:
        latest_item = all_items[-1]
        print(f"[V2] active_item_dict: Latest acquired object: {latest_item.get('item_type')}#{latest_item.get('item_id')}")
        return latest_item
    
    print(f"[V2] active_item_dict: No objects in inventory")
    return None

def _cap(period: str) -> str:
    p = str(period or "").lower()
    return "Bronze" if p == "bronze" else p.capitalize()

def _find_kx_item(period: str, item_id: int):
    """Find KX object in scene - IMPROVED VERSION"""
    sc = _scn()
    if not sc: 
        print(f"[V2] _find_kx_item: No scene")
        return None
    
    cap = _cap(period)
    
    print(f"[V2] Searching for KX object: period={period}, id={item_id}, cap={cap}")
    
    # FIRST: Search by exact names
    possible_names = [
        f"Object.{cap}.{item_id}",
        f"Card.{cap}.{item_id}",
        f"Object.{period.capitalize()}.{item_id}",
        f"Card.{period.capitalize()}.{item_id}",
        f"Object.World.{cap}.{item_id}",  # In case it's a world object
    ]
    
    for name in possible_names:
        obj = sc.objects.get(name)
        if obj:
            print(f"[V2] Found by name: {name}")
            return obj
    
    # SECOND: Search by properties
    print(f"[V2] Searching by properties in {len(sc.objects)} objects...")
    
    for obj in sc.objects:
        try:
            obj_period = str(obj.get("item_type", "")).lower()
            obj_id = int(obj.get("item_id", 0))
            
            if obj_period == period and obj_id == item_id:
                print(f"[V2] Found by properties: {obj.name}")
                return obj
        except Exception:
            continue
    
    # THIRD: Search objects containing ID in name
    for obj in sc.objects:
        if str(item_id) in obj.name and period.lower() in obj.name.lower():
            print(f"[V2] Possible match by name: {obj.name}")
            return obj
    
    print(f"[V2] KX object not found for {period}#{item_id}")
    return None

def _find_item_by_type(item_type, exclude_ubication=0, exclude_exhibition=0):
    """Finds an object of the specified type that is not shelved/exhibited"""
    try:
        game = game_access.get_game()
        if not game:
            print(f"[V2] _find_item_by_type: Game not found")
            return None
            
        inv = game.state.inventory
        items_of_type = inv.get("collection_items", {}).get(item_type, [])
        
        print(f"[V2] _find_item_by_type: Searching for '{item_type}' (excluding ubication={exclude_ubication})")
        print(f"[V2]   * Total objects type '{item_type}': {len(items_of_type)}")
        
        # Priority 1: Objects not shelved or exhibited
        for item in items_of_type:
            ubication = int(item.get("ubication", 0))
            exhibition = int(item.get("exhibition", 0))
            restored = int(item.get("restored", 0))
            item_id = item.get("item_id", 0)
            
            print(f"[V2]   * {item_type}#{item_id}: ubication={ubication}, exhibition={exhibition}, restored={restored}")
            
            if ubication == exclude_ubication and exhibition == exclude_exhibition:
                item_copy = item.copy()
                item_copy["item_type"] = item_type
                print(f"[V2] _find_item_by_type: Found {item_type}#{item_id} (not shelved)")
                return item_copy
        
        print(f"[V2] _find_item_by_type: No unshelved objects of type '{item_type}'")
        
        # Priority 2: Any object of this type (even shelved)
        if items_of_type:
            last_item = items_of_type[-1].copy()
            last_item["item_type"] = item_type
            item_id = last_item.get("item_id", 0)
            ubication = int(last_item.get("ubication", 0))
            print(f"[V2] _find_item_by_type: Using last object {item_type}#{item_id} (ubication={ubication})")
            return last_item
        
        print(f"[V2] _find_item_by_type: No objects of type '{item_type}'")
        return None
        
    except Exception as e:
        print(f"[V2] Error in _find_item_by_type: {e}")
        return None

# =============================================================================
# CARD POSITIONING
# =============================================================================
def _place_card(kx_item):
    """Positions the card at Object.Image.Pos - IMPROVED VERSION"""
    sc = _scn()
    anchor = _get(sc, OBJ_IMAGE_POS) if sc else None
    
    print(f"[V2] _place_card: kx_item={kx_item}, anchor={anchor}")
    
    if not sc or not anchor:
        print(f"[V2] No scene or anchor")
        return
    
    if not kx_item:
        print(f"[V2] No card to position")
        return
    
    ctx = logic.v2ctx
    
    # SAVE ORIGINAL POSITION BEFORE MOVING
    if ctx["_card_parent"] is None and ctx["_card_matrix"] is None:
        try:
            ctx["_card_parent"] = kx_item.parent
            ctx["_card_matrix"] = kx_item.worldTransform.copy()
            print(f"[V2] Saved original position of {kx_item.name}")
        except Exception as e:
            ctx["_card_parent"] = None
            ctx["_card_matrix"] = None
            print(f"[V2] Error saving position: {e}")
    
    # MOVE CARD TO ANCHOR
    try:
        # 1. Remove current parent
        kx_item.removeParent()
        
        # 2. Set new parent (anchor)
        kx_item.setParent(anchor, compound=False, ghost=False)
        
        # 3. Reset local transform to use anchor's transform
        kx_item.localPosition = (0.0, 0.0, 0.0)
        kx_item.localOrientation = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
        kx_item.localScale = (1, 1, 1)
        
        # 4. Ensure visibility
        kx_item.visible = True
        
        print(f"[V2] Card {kx_item.name} positioned at anchor")
        print(f"[V2] Final position: {kx_item.worldPosition}")
        
    except Exception as e:
        print(f"[V2] Error positioning card: {e}")
        
        # Fallback: copy anchor position
        try:
            kx_item.worldPosition = anchor.worldPosition.copy()
            kx_item.worldOrientation = anchor.worldOrientation.copy()
            print(f"[V2] Fallback: Position copied manually")
        except Exception as e2:
            print(f"[V2] Fallback error: {e2}")

def _restore_card():
    """Restores card to its original position"""
    ctx = logic.v2ctx
    obj = ctx.get("card_obj")
    if obj:
        try:
            # Remove current parent
            obj.removeParent()
            
            # Restore original matrix if exists
            if ctx.get("_card_matrix") is not None:
                obj.worldTransform = ctx["_card_matrix"]
                print(f"[V2] Matrix restored for {obj.name}")
            
            # Restore original parent if exists
            if ctx.get("_card_parent") is not None:
                obj.setParent(ctx["_card_parent"], compound=False, ghost=False)
                print(f"[V2] Parent restored for {obj.name}")
            
            _log("Card restored to its original parent/matrix")
        except Exception as e:
            print(f"[V2] Error unparenting card: {e}")
    
    # Clear references
    ctx["card_obj"] = None
    ctx["_card_parent"] = None
    ctx["_card_matrix"] = None

# =============================================================================
# CARD VISIBILITY MANAGEMENT FOR V1 TRANSITION
# =============================================================================
def _hide_other_cards_from_v1(target_type, target_id):
    """Hides all cards except the specified one (for V1->V2 transition)"""
    sc = _scn()
    if not sc:
        return
    
    print(f"[V2] Hiding other V1 cards except {target_type}#{target_id}")
    
    out_pos = sc.objects.get("Object.Pos.Out")
    if not out_pos:
        out_pos = sc.objects.get("Empty.Pos.Inv.Out")
    
    cards_hidden = 0
    
    for obj in sc.objects:
        # Look for objects that look like inventory cards
        if obj.name.startswith("Object.") and not obj.name.startswith("Object.World."):
            # Check if it has card properties
            obj_type = str(obj.get("item_type", "")).lower()
            obj_id = int(obj.get("item_id", 0))
            
            # If it's a valid card and NOT the target card
            if obj_type and obj_id > 0:
                if not (obj_type == target_type.lower() and obj_id == target_id):
                    # Move to OUT position
                    if out_pos:
                        obj.worldPosition = out_pos.worldPosition.copy()
                    else:
                        obj.worldPosition = (1e6, 1e6, 1e6)  # Extreme position
                    
                    # Ensure invisibility and not clickable
                    obj.visible = False
                    obj["_is_clickable"] = False
                    cards_hidden += 1
                    
                    print(f"[V2] Card hidden: {obj.name}")
    
    if cards_hidden > 0:
        print(f"[V2] {cards_hidden} cards hidden for V2 mode")
    else:
        print(f"[V2] No other cards found to hide")

def _restore_cards_to_v1():
    """Restores all cards to V1 after closing V2 (only if coming from V1)"""
    sc = _scn()
    if not sc:
        return
    
    print(f"[V2] Restoring cards to V1...")
    
    # Import game_displace_objects to use its functions
    try:
        import game_displace_objects as gdo
        
        game = game_access.get_game()
        if game:
            inv = game.state.inventory
            collection_items = inv.get("collection_items", {})
            
            cards_restored = 0
            
            for period, items in collection_items.items():
                for item in items:
                    item_id = int(item.get("item_id", 0))
                    if item_id > 0:
                        # Find card
                        card_name = gdo._card_name(period, item_id)
                        card = sc.objects.get(card_name)
                        
                        if card:
                            # Find corresponding slot
                            slot_name = gdo._slot_name(period, item_id)
                            slot = sc.objects.get(slot_name)
                            
                            if slot:
                                # Position card on slot
                                card.worldPosition = slot.worldPosition.copy()
                                card.worldScale = slot.worldScale.copy()
                                card.visible = True
                                card["_is_clickable"] = True
                                cards_restored += 1
                                
                                print(f"[V2] Card restored to slot: {card.name}")
                            else:
                                # If no slot, move to general V1 position
                                v1_root = sc.objects.get("Empty.View.1")
                                if v1_root:
                                    card.worldPosition = v1_root.worldPosition.copy()
                                    card.visible = True
                                    card["_is_clickable"] = True
                                    cards_restored += 1
                                    
                                    print(f"[V2] Card restored to V1: {card.name}")
            
            print(f"[V2] {cards_restored} cards restored to V1")
            
    except Exception as e:
        print(f"[V2] Error restoring cards to V1: {e}")

# =============================================================================
# SUSPENSION SYSTEM
# =============================================================================
def _send_suspend_message(action):
    """Sends message to suspension system"""
    try:
        logic.sendMessage("suspend_logic", f"v2|{action}")
        print(f"[V2] Suspension {action} for V2")
    except Exception as e:
        print(f"[V2] Error sending suspension: {e}")

# =============================================================================
# V2 CONTEXT RESET
# =============================================================================
def _reset_v2_context():
    """Completely resets V2 context - CRITICAL to prevent persistence between containers"""
    _log("EXECUTING _reset_v2_context() - FULL VERSION")
    
    ctx = logic.v2ctx
    
    # Save previous values for logging
    old_kind = ctx.get("kind", "")
    old_box_id = ctx.get("box_id", 0)
    old_origin = ctx.get("origin", "")
    
    # 1. CLEAR ACTIVE_COLLECTION_ITEM FIRST
    if hasattr(logic, "active_collection_item"):
        _log(f"Removing active_collection_item: {logic.active_collection_item}")
        logic.active_collection_item = None
    
    # 2. CLEAR ANY OTHER REFERENCES
    logic._last_active_item = None
    
    # 3. Reset all context properties
    ctx.update({
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
    
    # 4. Clear text object texts
    _set_text(OBJ_TEXT_BOX_ID, "")
    _set_text(OBJ_TEXT_EXHIB_ID, "")
    _set_text(OBJ_TEXT_RESTOR, "")
    
    # 5. Clear HUD texts in GameManager
    game, hud = _hud()
    if hud:
        hud.info_text_v2 = ""
        hud.item_desc_text = ""
        # Also clear other related texts
        if hasattr(hud, "info_text"):
            hud.info_text = ""
    
    # 6. Disable all buttons
    _set_button_disabled(BTN_BOX, True)
    _set_button_disabled(BTN_EXHIB, True)
    _set_button_disabled(BTN_REST, True)
    
    # 7. Restore card if exists
    _restore_card()
    
    _log(f"V2 context completely reset and cleaned (previously: {old_kind}#{old_box_id} from {old_origin})")
    return True

# =============================================================================
# RULES AND VALIDATION
# =============================================================================
_REASON_MAP = {
    "type_mismatch":   TXT_TYPE_MIS,
    "no_space":        TXT_NO_SPACE,
    "vit_mismatch":    TXT_VIT_MIS,
    "vit_no_space":    TXT_VIT_NOSPACE,
    "need_restore":    TXT_NEED_REST,
    "no_object":       TXT_NO_OBJECT,
    "not_inventoried": "You must inventory the object before exhibiting it.",
    "not_restored":    "You must restore the object before exhibiting it.",
    "no_box":          "Shelf not available.",
    "no_exh":          "Display case not available.",
    "no_need":         "Restoration not required.",
}

def _warn_from_reasons(reasons_csv: str) -> str:
    if not reasons_csv: return ""
    out = []
    for r in (reasons_csv or "").split(","):
        r = r.strip().lower()
        if not r: continue
        out.append(_REASON_MAP.get(r, r))
    return "\n".join(out)

def _is_in_lab(ctx, item) -> bool:
    try:
        if logic.globalDict.get("inventory_in_lab", False): return True
    except Exception: pass
    try:
        for k in ("at_lab","in_lab","near_restoration","lab"):
            if item and bool(item.get(k, False)): return True
    except Exception: pass
    try:
        sc=_scn(); la = sc.objects.get("Lab.Anchor") if sc else None
        if la and "active" in la and bool(la["active"]): return True
    except Exception: pass
    return False

def _rules_enable(ctx, item):
    if not item: return (False, False, False)
    itype = str(item.get("item_type","")).lower()
    restored = int(item.get("restored", 0))
    ubi = int(item.get("ubication", 0))
    exhib = int(item.get("exhibition", 0))
    ctype = str(ctx.get("box_type","")).lower()
    room_t = int(ctx.get("room_total", 0))
    room_m = int(ctx.get("room_max", 0))
    kind = str(ctx.get("kind","")).lower()
    ok_box   = (kind == "box")   and (itype == ctype) and (room_t < room_m) and (restored in (1,2)) and (ubi == 0)
    ok_exhib = (kind == "exhib") and (itype == ctype) and (room_t < room_m) and (restored in (1,2)) and (ubi > 0) and (exhib == 0)
    ok_rest  = (restored == 0) and _is_in_lab(ctx, item)
    return (ok_box, ok_exhib, ok_rest)

# =============================================================================
# HUD AND TEXT UPDATE FUNCTIONS
# =============================================================================
def _hud():
    """Get HUD from game_access (NEW ARCHITECTURE)"""
    game = game_access.get_game()
    if not game:
        return None, None
        
    hud = game.hud_text
    if not hasattr(hud, "item_desc_text"): 
        hud.item_desc_text = ""
    if not hasattr(hud, "info_text_v2"):   
        hud.info_text_v2 = ""
    return game, hud

def _set_blf_warn(text: str):
    gm, hud = _hud()
    if hud is None: return
    hud.info_text_v2 = text or ""

def _set_blf_desc(text: str):
    gm, hud = _hud()
    if hud is None: return
    hud.item_desc_text = text or ""

def _update_texts(ctx, item, warn=""):
    if item:
        desc = item.get("description","") or _desc_from_cache(str(item.get("item_type","")), int(item.get("item_id",0)))
    else:
        desc = ""
    _set_blf_desc(desc or "")
    _set_blf_warn(warn or "")

    if item:
        ub  = int(item.get("ubication", 0))
        ex  = int(item.get("exhibition", 0))
        rs  = int(item.get("restored", 0))
        _set_text(OBJ_TEXT_BOX_ID,   (f"{PFX_BOX_ID} {ub}"   if ub > 0 else ""))
        _set_text(OBJ_TEXT_EXHIB_ID, (f"{PFX_EXHIB_ID} {ex}" if ex > 0 else ""))
        _set_text(OBJ_TEXT_RESTOR,   ("OK" if rs in (1,2) else ""))
    else:
        _set_text(OBJ_TEXT_BOX_ID, ""); _set_text(OBJ_TEXT_EXHIB_ID, ""); _set_text(OBJ_TEXT_RESTOR, "")

# =============================================================================
# EVENT HANDLERS
# =============================================================================
def _on_open(params):
    """Handles V2 opening - FULL CORRECTED VERSION"""
    ctx = logic.v2ctx
    
    # GET AND CLEAN KEY PARAMETERS
    force_reset = params.get("force_reset", "false").lower() == "true"
    new_kind = params.get("kind", "").lower().strip()
    new_id = int(params.get("id", "0") or 0)
    new_origin = params.get("origin", "").strip()
    container_type = params.get("type", "").lower().strip()  # CONTAINER TYPE
    
    print(f"[V2] _on_open RECEIVED:")
    print(f"  * kind: '{new_kind}'")
    print(f"  * type: '{container_type}' (container)")
    print(f"  * id: {new_id}")
    print(f"  * origin: '{new_origin}'")
    print(f"  * force_reset: {force_reset}")
    print(f"  * Full parameters: {params}")
    
    # SAVE CURRENT CONTEXT BEFORE CHANGES
    current_context = {
        "open": ctx.get("open", False),
        "kind": ctx.get("kind", ""),
        "origin": ctx.get("origin", ""),
        "box_type": ctx.get("box_type", "")
    }
    
    print(f"[V2] Current context: open={current_context['open']}, kind='{current_context['kind']}', origin='{current_context['origin']}'")
    
    # DECIDE WHETHER TO RESET CONTEXT
    should_reset = False
    
    if force_reset:
        should_reset = True
        print(f"[V2] Reset forced (force_reset=true)")
    
    elif current_context["open"]:
        # If already open but with different data
        if current_context["origin"] != new_origin:
            should_reset = True
            print(f"[V2] Reset due to different origin: '{current_context['origin']}' != '{new_origin}'")
        
        elif current_context["kind"] != new_kind:
            should_reset = True
            print(f"[V2] Reset due to different kind: '{current_context['kind']}' != '{new_kind}'")
        
        elif current_context["kind"] == new_kind and current_context["origin"] == new_origin:
            print(f"[V2] Ignoring duplicate open of same context")
            return  # EXIT WITHOUT DOING ANYTHING
    
    # EXECUTE RESET IF NECESSARY
    if should_reset:
        _reset_v2_context()
        ctx = logic.v2ctx  # Update reference after reset
        print(f"[V2] Context completely reset")
    
    # PREVENT RE-OPENING WITH SAME DATA
    if ctx.get("open", False) and ctx.get("kind") == new_kind and ctx.get("origin") == new_origin:
        print(f"[V2] Ignoring duplicate open of same context")
        return
    
    # UPDATE CONTEXT STATE WITH NEW DATA
    ctx["open"] = True
    ctx["kind"] = new_kind
    ctx["origin"] = new_origin
    ctx["box_type"] = container_type  # CRITICAL: Save container type
    
    print(f"[V2] Context updated:")
    print(f"  * open: {ctx['open']}")
    print(f"  * kind: '{ctx['kind']}'")
    print(f"  * origin: '{ctx['origin']}'")
    print(f"  * box_type: '{ctx['box_type']}' (container type)")
    
    # NEW: If coming from V1 (readonly), hide other cards
    if ctx["kind"] == "readonly" and ctx["origin"] == "v1_click":
        # Get target card information
        target_type = str(params.get("item_type", "")).lower()
        try:
            target_id = int(params.get("item_id", "0") or 0)
        except:
            target_id = 0
        
        if target_type and target_id > 0:
            _hide_other_cards_from_v1(target_type, target_id)
        else:
            print(f"[V2] Could not identify target card to hide others")
    
    # FORCE VISIBILITY OF ALL V2 OBJECTS
    _force_all_children_visible(ROOT_V2)
    print(f"[V2] Forced visibility for {ROOT_V2}")
    
    # SUSPEND SYSTEM (only if not already suspended)
    current_v2 = getattr(logic, "_suspend_v2", False)
    if not current_v2:
        _send_suspend_message("suspend")
        print(f"[V2] System suspended for V2")
    else:
        print(f"[V2] V2 was already suspended")

    # SPECIAL HANDLING FOR "READONLY" MODE (from V1)
    if ctx["kind"] == "readonly":
        print(f"\n[V2] ===== READONLY MODE ACTIVATED from {ctx['origin']} =====")
        
        # Get object type and ID from parameters
        item_type = params.get("item_type", "").lower().strip()
        try: 
            item_id = int(params.get("item_id", "0") or 0)
        except: 
            item_id = 0
        
        print(f"[V2] READONLY target: {item_type}#{item_id}")
        
        if not item_type or item_id == 0:
            print(f"[V2] Incomplete data for readonly: type='{item_type}', id={item_id}")
            return
        
        # FIND OBJECT IN INVENTORY
        item = None
        game = game_access.get_game()
        if game:
            inv = game.state.inventory
            coll = inv.get("collection_items", {}).get(item_type, [])
            print(f"[V2] Searching inventory type '{item_type}' ({len(coll)} objects)")
            
            for it in coll:
                if int(it.get("item_id", 0)) == item_id:
                    item = it.copy()
                    item["item_type"] = item_type  # Ensure type
                    print(f"[V2] Found in inventory: {item_type}#{item_id}")
                    break
        
        # If not found in inventory, use context data
        if not item and ctx.get("item_dict"):
            item = ctx["item_dict"].copy()
            print(f"[V2] Using context data")
        
        # If still nothing, create minimal object
        if not item:
            item = {"item_type": item_type, "item_id": item_id}
            print(f"[V2] Creating minimal object")
        
        # GET DESCRIPTION FROM JSON
        desc = _desc_from_cache(item_type, item_id)
        item["description"] = desc
        
        if not desc:
            print(f"[V2] No description found for {item_type}#{item_id}")
            desc = f"Object {item_type.capitalize()} #{item_id}"
        
        ctx["item_dict"] = item
        
        # FIND KX OBJECT IN SCENE (THE CARD)
        kx_item = None
        
        # FIRST: Use reference saved from button_fx
        if "card_obj" in ctx and ctx["card_obj"]:
            kx_item = ctx["card_obj"]
            print(f"[V2] Using card from context: {kx_item.name}")
        
        # SECOND: Search by name
        if not kx_item:
            sc = _scn()
            if sc:
                cap = _cap(item_type)
                possible_names = [
                    f"Object.{cap}.{item_id}",
                    f"Card.{cap}.{item_id}",
                    f"Object.{item_type.capitalize()}.{item_id}",
                ]
                
                for name in possible_names:
                    kx_item = sc.objects.get(name)
                    if kx_item:
                        print(f"[V2] Found card by name: {name}")
                        break
        
        # THIRD: Search by properties
        if not kx_item:
            kx_item = _find_kx_item(item_type, item_id)
            if kx_item:
                print(f"[V2] Found card by search: {kx_item.name}")
        
        if not kx_item:
            print(f"[V2] KX object not found for {item_type}#{item_id}")
            print(f"[V2] Only description will be shown without 3D object")
        
        # SAVE REFERENCES
        ctx["kx_item"] = kx_item
        if kx_item:
            ctx["card_obj"] = kx_item
        
        # POSITION CARD AT Object.Image.Pos
        if kx_item:
            print(f"[V2] Positioning card {kx_item.name} at Object.Image.Pos")
            _place_card(kx_item)
        else:
            print(f"[V2] No card to position")
        
        # UPDATE TEXT IN HUD
        _update_texts(ctx, item, warn="")
        
        # FORCE DESCRIPTION UPDATE IN BLF
        _set_blf_desc(desc)
        
        # DISABLE ALL BUTTONS (readonly mode)
        _enable_only_buttons(box=False, exhib=False, restor=False)
        
        print(f"[V2] READONLY mode fully configured for {item_type}#{item_id}")
        print(f"[V2] ===== END READONLY MODE =====\n")
        return

    # HANDLING FOR INTERACTIVE MODES (box, exhib, restor) FROM CONTAINERS
    print(f"\n[V2] ===== INTERACTIVE MODE '{new_kind.upper()}' ACTIVATED =====")
    
    # GET CONTAINER DATA
    ctx["box_id"] = int(params.get("id", "0") or 0)
    ctx["box_type"] = container_type  # Already cleaned above
    ctx["room_total"] = int(params.get("room_total", "0") or 0)
    ctx["room_max"] = int(params.get("room_max", "0") or 0)

    print(f"[V2] Container data:")
    print(f"  * ID: {ctx['box_id']}")
    print(f"  * Type: '{ctx['box_type']}'")
    print(f"  * Space: {ctx['room_total']}/{ctx['room_max']}")
    print(f"  * Origin: '{ctx['origin']}'")

    # FIND OBJECT MATCHING CONTAINER TYPE
    item = None
    target_type = ctx["box_type"]
    
    print(f"[V2] Looking for object of type '{target_type}' for container...")
    
    if target_type:
        # Try to find object of correct type
        item = _find_item_by_type(target_type)
        
        if item:
            print(f"[V2] Found object by type: {target_type}#{item.get('item_id')}")
        else:
            print(f"[V2] No available object of type '{target_type}'")
            
            # Fallback: use _active_item_dict (which now searches by type)
            item = _active_item_dict()
            
            if item:
                item_type_found = item.get("item_type", "")
                print(f"[V2] Using alternative object: {item_type_found}#{item.get('item_id')}")
                
                # Check if type matches
                if item_type_found != target_type:
                    print(f"[V2] WARNING: Type mismatch ({item_type_found} != {target_type})")
    
    # If still no object, try last option
    if not item:
        print(f"[V2] Could not find appropriate object")
        # Create empty object to avoid errors
        item = {"item_type": target_type, "item_id": 0, "description": "No object available"}
    
    # ENSURE OBJECT HAS CORRECT TYPE
    if item and not item.get("item_type"):
        item["item_type"] = target_type
    
    ctx["item_dict"] = item
    
    print(f"[V2] Selected object for V2:")
    print(f"  * Type: {item.get('item_type', 'NO TYPE')}")
    print(f"  * ID: {item.get('item_id', 'NO ID')}")
    print(f"  * Restored: {item.get('restored', 0)}")
    print(f"  * Ubication: {item.get('ubication', 0)}")
    print(f"  * Exhibition: {item.get('exhibition', 0)}")

    # FIND KX OBJECT IN SCENE
    kx_item = None
    if item and item.get("item_type") and item.get("item_id"):
        item_type_kx = item.get("item_type", "")
        item_id_kx = int(item.get("item_id", 0))
        
        print(f"[V2] Looking for KX object for {item_type_kx}#{item_id_kx}")
        kx_item = _find_kx_item(item_type_kx, item_id_kx)
        
        if kx_item:
            print(f"[V2] KX object found: {kx_item.name}")
        else:
            print(f"[V2] KX object not found")
    
    ctx["kx_item"] = kx_item
    if kx_item:
        ctx["card_obj"] = kx_item

    # DETERMINE WARNING MESSAGES
    try: 
        ok = int(params.get("ok", "1"))
    except Exception: 
        ok = 1
        
    warn = ""
    if ok == 0:
        reasons = params.get("reasons", "")
        warn = _warn_from_reasons(reasons)
        print(f"[V2] Warnings: {reasons} -> '{warn}'")
    else:
        print(f"[V2] No warnings")

    # UPDATE INTERFACE
    _update_texts(ctx, item, warn)
    
    # POSITION CARD IF EXISTS
    if kx_item and item:
        print(f"[V2] Positioning card {kx_item.name} at Object.Image.Pos")
        _place_card(kx_item)
    else:
        print(f"[V2] No card to position")
        _place_card(None)  # Clear position

    # ENABLE BUTTONS ACCORDING TO RULES
    b = _rules_enable(ctx, item)
    print(f"[V2] Button rules: box={b[0]}, exhib={b[1]}, restor={b[2]}")
    _enable_only_buttons(box=b[0], exhib=b[1], restor=b[2])
    
    # UPDATE STATISTICS IMMEDIATELY
    try:
        game = game_access.get_game()
        if game and hasattr(game.state, 'update_collection_stats'):
            inventoried, restored, exhibited = game.state.update_collection_stats()
            print(f"[V2] Statistics updated: inventoried={inventoried}, restored={restored}, exhibited={exhibited}")
    except Exception as e:
        print(f"[V2] Error updating statistics: {e}")
    
    print(f"[V2] V2 fully opened in mode {ctx['kind']}")
    print(f"[V2] ===== END INTERACTIVE MODE =====\n")

def _on_apply(params):
    """Handles applying actions in V2 (shelve, exhibit, restore) - CORRECTED VERSION"""
    ctx = logic.v2ctx
    if not ctx.get("open"): 
        print(f"[V2] _on_apply: V2 is not open")
        return
        
    if ctx.get("kind") == "readonly":
        print(f"[V2] _on_apply: Readonly mode - no actions applied")
        _enable_only_buttons(False, False, False)
        return
        
    item = ctx.get("item_dict")
    if not item:
        print(f"[V2] _on_apply: No selected object")
        _set_blf_warn("")
        return
        
    action = params.get("action", "")
    kind = str(ctx.get("kind", "")).lower()
    
    print(f"[V2] _on_apply: action='{action}', kind='{kind}', object={item.get('item_type')}#{item.get('item_id')}")
    
    if action == "box":
        if kind != "box": 
            print(f"[V2] _on_apply: Action 'box' not valid for kind '{kind}'")
            return
            
        box_id = int(ctx.get("box_id", 0))
        if box_id <= 0:
            print(f"[V2] _on_apply: Invalid shelf ID: {box_id}")
            return
            
        print(f"[V2] Applying SHELVING in shelf {box_id}")
        
        # CRITICAL: Update FIRST in game_state inventory
        item["ubication"] = box_id
        print(f"[V2] Local inventory updated: ubication={box_id}")
        
        # IMMEDIATE UPDATE IN GAME_STATE
        try:
            game = game_access.get_game()
            if game:
                # Find object in inventory structure and update it
                inv = game.state.inventory
                item_type = item.get("item_type", "")
                item_id = int(item.get("item_id", 0))
                
                if item_type and item_id > 0:
                    coll = inv.get("collection_items", {}).get(item_type, [])
                    for inv_item in coll:
                        if int(inv_item.get("item_id", 0)) == item_id:
                            # UPDATE ALL RELEVANT PROPERTIES
                            inv_item["ubication"] = box_id
                            inv_item["restored"] = item.get("restored", 0)
                            inv_item["exhibition"] = item.get("exhibition", 0)
                            
                            print(f"[V2] Game_state updated: {item_type}#{item_id} -> ubication={box_id}")
                            break
        except Exception as e:
            print(f"[V2] Error updating game_state: {e}")
        
        # Update space counter
        ctx["room_total"] = int(ctx.get("room_total", 0)) + 1
        
        # Update interface text
        _set_text(OBJ_TEXT_BOX_ID, f"{PFX_BOX_ID} {box_id}")
        _set_blf_warn("")
        
        # Keep description updated
        current_desc = item.get("description", "") or _desc_from_cache(item.get("item_type", ""), int(item.get("item_id", 0)))
        _set_blf_desc(current_desc)
        
        # Disable shelving button
        _set_button_disabled(BTN_BOX, True)
        
        # SELECTIVE SYNCHRONIZATION WITH SCENE OBJECTS
        try:
            sync_data = {
                "ubication": box_id,
                "restored": item.get("restored", 0)  # Keep restoration state
            }
            
            success = game_access.find_and_update_object(
                item.get("item_type", ""), 
                int(item.get("item_id", 0)), 
                sync_data
            )
            
            if success:
                print(f"[V2] World object synchronization OK: ubication={box_id}")
            else:
                print(f"[V2] World object synchronization failed")
                
        except Exception as e:
            print(f"[V2] Error synchronizing world object: {e}")
        
        print(f"[V2] Object successfully stored in shelf {box_id}")
        
    elif action == "exhib":
        if kind != "exhib": 
            print(f"[V2] _on_apply: Action 'exhib' not valid for kind '{kind}'")
            return
            
        exhib_id = int(ctx.get("box_id", 0) or 0)
        if exhib_id <= 0:
            print(f"[V2] _on_apply: Invalid display case ID: {exhib_id}")
            return
            
        print(f"[V2] Applying EXHIBITION in display case {exhib_id}")
        
        # CRITICAL: Update FIRST in inventory
        item["exhibition"] = exhib_id
        print(f"[V2] Local inventory updated: exhibition={exhib_id}")
        
        # IMMEDIATE UPDATE IN GAME_STATE
        try:
            game = game_access.get_game()
            if game:
                inv = game.state.inventory
                item_type = item.get("item_type", "")
                item_id = int(item.get("item_id", 0))
                
                if item_type and item_id > 0:
                    coll = inv.get("collection_items", {}).get(item_type, [])
                    for inv_item in coll:
                        if int(inv_item.get("item_id", 0)) == item_id:
                            inv_item["exhibition"] = exhib_id
                            print(f"[V2] Game_state updated: exhibition={exhib_id}")
                            break
        except Exception as e:
            print(f"[V2] Error updating game_state: {e}")
        
        # Update interface text
        _set_text(OBJ_TEXT_EXHIB_ID, f"{PFX_EXHIB_ID} {exhib_id}")
        _set_blf_warn("")
        
        # Keep description updated
        current_desc = item.get("description", "") or _desc_from_cache(item.get("item_type", ""), int(item.get("item_id", 0)))
        _set_blf_desc(current_desc)
        
        # Disable exhibition button
        _set_button_disabled(BTN_EXHIB, True)
        
        # SELECTIVE SYNCHRONIZATION
        try:
            sync_data = {
                "exhibition": exhib_id,
                "ubication": item.get("ubication", 0),  # Keep current ubication
                "restored": item.get("restored", 0)     # Keep restoration state
            }
            
            game_access.find_and_update_object(
                item.get("item_type", ""), 
                int(item.get("item_id", 0)), 
                sync_data
            )
            
            print(f"[V2] Display case synchronization OK: exhibition={exhib_id}")
                
        except Exception as e:
            print(f"[V2] Error synchronizing world object: {e}")
            
        print(f"[V2] Object successfully exhibited in display case {exhib_id}")
        
    elif action == "restor":
        print(f"[V2] Applying RESTORATION")
        
        # Update restoration state
        item["restored"] = 1
        print(f"[V2] Local inventory updated: restored=1")
        
        # IMMEDIATE UPDATE IN GAME_STATE
        try:
            game = game_access.get_game()
            if game:
                inv = game.state.inventory
                item_type = item.get("item_type", "")
                item_id = int(item.get("item_id", 0))
                
                if item_type and item_id > 0:
                    coll = inv.get("collection_items", {}).get(item_type, [])
                    for inv_item in coll:
                        if int(inv_item.get("item_id", 0)) == item_id:
                            inv_item["restored"] = 1
                            print(f"[V2] Game_state updated: restored=1")
                            break
        except Exception as e:
            print(f"[V2] Error updating game_state: {e}")
        
        # Update interface text
        _set_text(OBJ_TEXT_RESTOR, "OK")
        _set_blf_warn("")
        
        # Keep description updated
        current_desc = item.get("description", "") or _desc_from_cache(item.get("item_type", ""), int(item.get("item_id", 0)))
        _set_blf_desc(current_desc)
        
        # Disable restoration button
        _set_button_disabled(BTN_REST, True)
        
        # SELECTIVE SYNCHRONIZATION
        try:
            sync_data = {
                "restored": 1,
                "ubication": item.get("ubication", 0),   # Keep ubication
                "exhibition": item.get("exhibition", 0)  # Keep exhibition
            }
            
            game_access.find_and_update_object(
                item.get("item_type", ""), 
                int(item.get("item_id", 0)), 
                sync_data
            )
            
            print(f"[V2] Restoration synchronization OK: restored=1")
                
        except Exception as e:
            print(f"[V2] Error synchronizing world object: {e}")
            
        print(f"[V2] Object successfully restored")
        
    else:
        print(f"[V2] _on_apply: Unknown action: '{action}'")
        return

    # UPDATE BUTTON ENABLE RULES
    b = _rules_enable(ctx, item)
    _enable_only_buttons(box=b[0], exhib=b[1], restor=b[2])
    
    # UPDATE COLLECTION STATISTICS IMMEDIATELY
    try:
        game = game_access.get_game()
        if game and hasattr(game.state, 'update_collection_stats'):
            inventoried, restored, exhibited = game.state.update_collection_stats()
            print(f"[V2] Statistics updated: inventoried={inventoried}, restored={restored}, exhibited={exhibited}")
    except Exception as e:
        print(f"[V2] Error updating statistics: {e}")
    
    print(f"[V2] _on_apply completed for action '{action}'")

def _on_close(_params):
    sc = _scn()
    
    print(f"[V2] Closing V2...")
    
    # FIRST: Save any pending changes from current context
    ctx = logic.v2ctx
    if ctx.get("open", False) and ctx.get("item_dict"):
        item = ctx["item_dict"]
        if item.get("item_type") and item.get("item_id"):
            print(f"[V2] Saving pending changes for {item['item_type']}#{item['item_id']}")
            
            try:
                import game_access
                
                game = game_access.get_game()
                if game:
                    inv = game.state.inventory
                    coll = inv.get("collection_items", {}).get(item["item_type"], [])
                    for inv_item in coll:
                        if int(inv_item.get("item_id", 0)) == int(item.get("item_id", 0)):
                            # Only update if there are real changes
                            for prop in ["ubication", "exhibition", "restored"]:
                                if prop in item:
                                    inv_item[prop] = item[prop]
                            print(f"[V2] Changes saved to inventory")
                            break
            except Exception as e:
                print(f"[V2] Error saving changes: {e}")
    
    # SECOND: Restore card BEFORE resuming
    _restore_card()
    
    # THIRD: If coming from V1 (readonly), restore all cards to V1
    if ctx.get("origin") == "v1_click":
        print(f"[V2] Restoring all cards to V1 from readonly mode...")
        _restore_cards_to_v1()
    
    # FOURTH: Hide V2 and prepare transition to HUD
    try:
        v2_root = sc.objects.get("Empty.View.2") if sc else None
        pos_out = sc.objects.get("Empty.Pos.Inv.Out") if sc else None
        
        if v2_root and pos_out:
            v2_root.worldPosition = pos_out.worldPosition.copy()
            v2_root.visible = False
            
    except Exception as e:
        _log("Error closing V2:", e)
    
    # FIFTH: RESET CONTEXT but do NOT force full synchronization
    _reset_v2_context()
    
    # SIXTH: Explicitly clear active item
    if hasattr(logic, "active_collection_item"):
        logic.active_collection_item = None
        print("[V2] Global active item cleared on close")
    
    # SEVENTH: SELECTIVE SYNCHRONIZATION (only if there are real changes)
    try:
        import game_access
        
        # Update only statistics, don't overwrite values
        game_access.get_game().state.update_collection_stats()
        print("[V2] Statistics updated")
        
    except:
        pass    
    
    # EIGHTH: Clear global states
    logic.hud_inventory_v2_open = False
    logic.hud_inventory_open = False
    logic._auto_v2_active = False
    logic._force_inventory_open = False
    
    # NINTH: RESUME logic when closing V2
    _send_suspend_message("resume")
    
    print(f"[V2] V2 closed - changes preserved, HUD activated")

# =============================================================================
# MESSAGE PARSING AND HANDLING
# =============================================================================
def _parse_params(body):
    out = {}
    parts = [t for t in (body or "").split("|") if t]
    if parts:
        head = parts[0]
        if "=" not in head:
            out["_verb"] = head
            parts = parts[1:]
    for p in parts:
        if "=" in p:
            k, v = p.split("=", 1)
            out[k.strip()] = v.strip()
    return out

def handle_message():
    cont = logic.getCurrentController()
    sc = _scn()
    if not sc: return

    for s in cont.sensors:
        if not getattr(s, "positive", False):
            continue
        if hasattr(s, "subjects") and hasattr(s, "bodies"):
            if "inventory2" not in list(getattr(s, "subjects", [])):
                continue
            _log("MSG received (", len(s.bodies), ") subject=inventory2")
            for body in list(s.bodies):
                _log("  body:\n", body)
                params = _parse_params(body)
                verb = params.get("_verb","")
                if verb == "open":
                    _on_open(params)
                elif verb == "apply":
                    _on_apply(params)
                elif verb == "close":
                    _on_close(params)