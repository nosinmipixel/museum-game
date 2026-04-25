"""
game_achievements.py

Manages game achievements, inventory tracking, and collection item progression.

This script handles the acquisition and state management of collection items,
general items, restoration tracking, shelving, exhibition, and quiz-related
achievements using the game_access layer.

Main Features:
    1. Track collection item acquisition by period (pal, neo, bronze, iberian, roman)
    2. Manage general items with damage and budget penalties
    3. Handle restoration submission and completion events
    4. Track shelving (storage boxes) and exhibition (display cases)
    5. Process quiz completion and skill increase achievements
    6. Load object descriptions from JSON files
    7. Synchronize inventory with game_state and Game.Controller
    8. Trigger NPC11 activation when items need restoration

Setup:
    Connect to Logic Bricks as Python controller with module 'game_achievements.handle'
    Required message sensor with subject 'achievement'

Configurable Variables:
    PREFERRED_MESSAGE_SENSOR (str): Message sensor name (default: 'Message.Achievements')
    DEFAULT_SUBJECT (str): Default message subject (default: 'achievement')
    MAX_PER_TYPE (int): Maximum items per collection period (default: 2)
    HEALTH_MIN (int): Minimum player health (default: 0)
    HEALTH_MAX (int): Maximum player health (default: 100)
    BASE_TEXT_PATH (str): Path to JSON text files (default: '//Assets/Texts/')
    OBJTEXT_PREFIX (str): Prefix for object text JSON files (default: 'objects_text_')
    FALLBACK_LANG (str): Fallback language (default: 'es')

Notes:
    - Requires game_access module for game state and player data
    - JSON file named 'objects_text_{lang}.json' in BASE_TEXT_PATH
    - JSON structure requires 'collection_items' with periods and items
    - Inventory is stored in game_state.inventory with collection_items, boxes, exhibitions
    - Restoration of items (restored=0) triggers NPC11 activation
    - Critical damage (general_items_total <= 0) resets to 100 and deducts 1000 budget

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
__description__ = "Manages game achievements, inventory tracking, and collection progression"

# =============================================================================
# IMPORTS
# =============================================================================
import os
import json
import bge
from bge import logic
import game_access

# =============================================================================
# CONFIGURATION
# =============================================================================
PREFERRED_MESSAGE_SENSOR = "Message.Achievements"
DEFAULT_SUBJECT = "achievement"

MAX_PER_TYPE = 2
HEALTH_MIN, HEALTH_MAX = 0, 100

# =============================================================================
# JSON LOADING (defaults)
# =============================================================================
BASE_TEXT_PATH = "//Assets/Texts/"
OBJTEXT_PREFIX = "objects_text_"   # => objects_text_<lang>.json
FALLBACK_LANG  = "es"

def _expand(rel):
    if not rel.startswith("//"):
        rel = "//" + rel
    return logic.expandPath(rel)

def _get_lang():
    """Gets language using game_access"""
    try:
        state = game_access.get_state()
        if state and hasattr(state, 'language'):
            return state.language
    except Exception:
        pass
    return FALLBACK_LANG

def _load_object_defs():
    """Loads and caches objects_text_<lang>.json"""
    if hasattr(logic, "_objects_text_cache"):
        return logic._objects_text_cache
    
    lang = _get_lang()
    tried = []
    raw_json = None
    
    for cand in (lang, FALLBACK_LANG):
        fname = f"{OBJTEXT_PREFIX}{cand}.json"
        path  = _expand(os.path.join(BASE_TEXT_PATH, fname))
        tried.append(path)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    raw_json = json.load(f)
                break
            except Exception as e:
                print("[achv] ERROR reading", path, e)

    if raw_json is None:
        print("[achv] Could not load objects_text JSON. Tried:", tried)
        logic._objects_text_cache = {}
        return {}

    # Index descriptions by object (period, id) -> description
    idx_texts = {}
    data = raw_json.get("collection_items", {}) or {}
    
    for period, items in data.items():
        tb = {}
        for it in (items or []):
            try:
                iid = int(it.get("id", 0) or 0)
            except Exception:
                iid = 0
            if iid <= 0:
                continue
            desc = (it.get("description") or it.get("desc") or it.get("text") or "").strip()
            tb[iid] = desc
        idx_texts[period] = tb

    logic._objects_text_cache = idx_texts
    
    # Also put in globalDict for compatibility
    if hasattr(logic, "globalDict"):
        logic.globalDict["objects_text"] = idx_texts
    
    print("[achv] objects_text cache OK -> periods:", list(idx_texts.keys()))
    return idx_texts

def _defaults_for(item_type, item_id):
    defs = _load_object_defs()
    try:
        d = defs.get(item_type, {}).get(int(item_id), None)
        if d:
            return {
                "restored":   int(d.get("restored",   0)),
                "ubication":  int(d.get("ubication",  0)),
                "exhibition": int(d.get("exhibition", 0)),
            }
    except Exception:
        pass
    # hard fallback if not in JSON
    return {"restored": 0, "ubication": 0, "exhibition": 0}

# =============================================================================
# BASE STRUCTURES
# =============================================================================
def _ensure_inventory():
    """Ensures inventory exists in game state"""
    try:
        state = game_access.get_state()
        if not state:
            return
            
        if not hasattr(state, 'inventory') or not isinstance(state.inventory, dict):
            state.inventory = {
                "collection_items": { "pal":[], "neo":[], "bronze":[], "iberian":[], "roman":[] },
                "general_items_total": 0,
                "boxes": {},
                "exhibitions": {}
            }
            print("[achv] Inventory initialized in game_state")
            
        # Maintain compatibility with logic.inventory temporarily
        if not hasattr(logic, "inventory") or not isinstance(logic.inventory, dict):
            logic.inventory = state.inventory
    except Exception as e:
        print(f"[achv] Error ensuring inventory: {e}")

def _get_msg_sensor(cont):
    s = cont.sensors.get(PREFERRED_MESSAGE_SENSOR)
    if s and s.positive and getattr(s, "subject", "") == DEFAULT_SUBJECT:
        return s
    for sen in cont.sensors:
        if getattr(sen, "positive", False) and sen.__class__.__name__.endswith("MessageSensor"):
            if getattr(sen, "subject", "") == DEFAULT_SUBJECT:
                return sen
    return None

def _parse_body(body):
    body = body.strip()
    if body.startswith("{") and body.endswith("}"):
        try:
            d = json.loads(body)
            return d if isinstance(d, dict) else {}
        except Exception:
            return {}
    # optional pipe format
    parts = [t.strip() for t in body.split("|") if t.strip()]
    if parts and parts[0].lower() == "achievement":
        parts = parts[1:]
    out = {}
    for t in parts:
        if "=" in t:
            k,v = t.split("=",1)
            out[k.strip()] = v.strip()
    return out

def _collection_bucket(item_type):
    """Gets collection bucket from inventory"""
    _ensure_inventory()
    
    # Try to get from game_state first
    try:
        state = game_access.get_state()
        if state and hasattr(state, 'inventory'):
            inv = state.inventory
            if item_type not in inv["collection_items"]:
                inv["collection_items"][item_type] = []
            return inv["collection_items"][item_type]
    except Exception:
        pass
    
    # Fallback to logic.inventory
    inv = logic.inventory
    if item_type not in inv["collection_items"]:
        inv["collection_items"][item_type] = []
    return inv["collection_items"][item_type]

def _find_item(bucket, item_id):
    for it in bucket:
        if it.get("item_id") == item_id:
            return it
    return None

def _add_general(qty):
    """Adds general items to inventory"""
    _ensure_inventory()
    
    try:
        # Use game_state first
        state = game_access.get_state()
        if state and hasattr(state, 'inventory'):
            inv = state.inventory
            current = int(inv.get("general_items_total", 0))
            inv["general_items_total"] = max(0, current + int(qty))
        else:
            # Fallback to logic.inventory
            inv = logic.inventory
            current = int(inv.get("general_items_total", 0))
            inv["general_items_total"] = max(0, current + int(qty))
    except Exception as e:
        print(f"[achv] Error adding general items: {e}")

def _add_health(delta):
    """Adds or removes player health using game_access"""
    try:
        player = game_access.get_player()
        if player:
            player.health = int(max(HEALTH_MIN, min(HEALTH_MAX, player.health + int(delta))))
            if player.health <= 0:
                player.is_alive = False
                print("[achv] Player has died!")
    except Exception as e:
        print(f"[achv] Error modifying health: {e}")

# =============================================================================
# STORAGE / EXHIBITION VALIDATIONS
# =============================================================================
def _get_box(box_id):
    _ensure_inventory()
    
    try:
        state = game_access.get_state()
        if state and hasattr(state, 'inventory'):
            return state.inventory["boxes"].get(int(box_id))
    except Exception:
        pass
    
    return logic.inventory["boxes"].get(int(box_id))

def _get_exhibition(exh_id):
    _ensure_inventory()
    
    try:
        state = game_access.get_state()
        if state and hasattr(state, 'inventory'):
            return state.inventory["exhibitions"].get(int(exh_id))
    except Exception:
        pass
    
    return logic.inventory["exhibitions"].get(int(exh_id))

def _validate_box(item_type, box_id):
    box = _get_box(box_id)
    if not box: return False, "no_box"
    if box.get("box_type") != item_type: return False, "type_mismatch"
    if int(box.get("box_total",0)) >= int(box.get("box_max",0)): return False, "full"
    return True, ""

def _validate_exhibition(item, item_type, exh_id):
    exh = _get_exhibition(exh_id)
    if not exh: return False, "no_exh"
    if exh.get("exhibition_type") != item_type: return False, "type_mismatch"
    if int(exh.get("exhibition_total",0)) >= int(exh.get("exhibition_max",0)): return False, "full"
    if int(item.get("ubication",0)) == 0: return False, "not_shelved"
    if int(item.get("restored",0)) not in (1,2): return False, "not_restored"
    return True, ""

# =============================================================================
# EVENT HANDLERS
# =============================================================================
def _on_collection_item_acquired(e):
    item_id   = int(e.get("item_id", 0))
    item_type = e.get("item_type", "")
    source    = e.get("source", "").lower()
    
    # Get properties from message if they exist
    restored_from_msg = int(e.get("restored", -1))  # -1 means "not specified"
    ubication_from_msg = int(e.get("ubication", -1))
    exhibition_from_msg = int(e.get("exhibition", -1))
    
    if source == "quiz" and "world" not in source:
        print(f"[achv] Ignoring QUIZ collection: {item_type}#{item_id}")
        return
    
    if not item_id or not item_type:
        return
    bucket = _collection_bucket(item_type)

    # Max 2 per type
    if len(bucket) >= MAX_PER_TYPE and not _find_item(bucket, item_id):
        return

    meta = _find_item(bucket, item_id)
    if not meta:
        # 1) If properties come from message, use them
        if restored_from_msg != -1:
            # Use message properties (from World object)
            meta = {
                "item_id":   item_id,
                "item_type": item_type,
                "restored":  restored_from_msg,
                "ubication": ubication_from_msg if ubication_from_msg != -1 else 0,
                "exhibition": exhibition_from_msg if exhibition_from_msg != -1 else 0,
            }
            print(f"[achv] ADD {item_type}#{item_id} -> restored={restored_from_msg} (from World)")
        else:
            # 2) Search for card object properties in scene
            try:
                scn = logic.getCurrentScene()
                cap = item_type.capitalize() if item_type != "bronze" else "Bronze"
                guess_names = (f"Object.{cap}.{item_id}", f"Card.{cap}.{item_id}")
                
                restored_val = 0
                ubication_val = 0
                exhibition_val = 0
                
                for name in guess_names:
                    ob = scn.objects.get(name)
                    if ob:
                        restored_val = int(ob.get("restored", 0))
                        ubication_val = int(ob.get("ubication", 0))
                        exhibition_val = int(ob.get("exhibition", 0))
                        break
                
                meta = {
                    "item_id":   item_id,
                    "item_type": item_type,
                    "restored":  restored_val,
                    "ubication": ubication_val,
                    "exhibition": exhibition_val,
                }
                print(f"[achv] ADD {item_type}#{item_id} -> restored={restored_val} (from card object)")
                
            except Exception:
                # 3) Fallback to JSON defaults
                ds = _defaults_for(item_type, item_id)
                meta = {
                    "item_id":   item_id,
                    "item_type": item_type,
                    "restored":  int(ds.get("restored", 0)),
                    "ubication": int(ds.get("ubication", 0)),
                    "exhibition": int(ds.get("exhibition", 0)),
                }
                print(f"[achv] ADD {item_type}#{item_id} -> restored={meta['restored']} (from JSON)")

        bucket.append(meta)
    else:
        print(f"[achv] {item_type}#{item_id} already exists; no changes")
    
    # ACTIVATE NPC11 IF OBJECT NEEDS RESTORATION
    if meta.get("restored", 0) == 0:
        print(f"[achv] Object {item_type}#{item_id} needs restoration - Activating NPC11")
        
        # Send message to restoration system
        try:
            body = f"restoration_npc|activate|item_type={item_type}|item_id={item_id}"
            bge.logic.sendMessage("achievement", body)
        except Exception as e:
            print(f"[achv] Error activating NPC11: {e}")

def _on_general_item_acquired(e):
    qty = int(e.get("qty", 1))
    _add_general(qty)

def _on_general_item_damaged(e):
    dmg = int(e.get("damage", 1))
    _add_general(-dmg)
    
    # If reaches 0, apply rule: reset to 100 and -1000 budget
    try:
        state = game_access.get_state()
        if state:
            inv = state.inventory
            if int(inv.get("general_items_total",0)) <= 0:
                inv["general_items_total"] = 100
                
                # Reduce budget
                state.budget -= 1000
                print(f"[achv] Critical damage: -1000 budget. New budget: {state.budget}")
                
                # Synchronize with Game.Controller for compatibility
                try:
                    gc = logic.getCurrentScene().objects.get("Game.Controller")
                    if gc:
                        gc['budget'] = state.budget
                except Exception:
                    pass
    except Exception as e:
        print(f"[achv] Error in general_item_damaged: {e}")

def _on_restoration_submit(e):
    item_id   = int(e.get("item_id", 0))
    item_type = e.get("item_type", "")
    if not item_id or not item_type: return
    bucket = _collection_bucket(item_type)
    it = _find_item(bucket, item_id)
    if it:
        it["restored"] = 3  # in progress

def _on_restoration_complete(e):
    item_id   = int(e.get("item_id", 0))
    item_type = e.get("item_type", "")
    result    = int(e.get("result", 1))  # 1=restored, 2=no restoration needed
    if not item_id or not item_type: return
    bucket = _collection_bucket(item_type)
    it = _find_item(bucket, item_id)
    if it:
        it["restored"] = result if result in (1,2) else 1

def _on_shelved(e):
    item_id   = int(e.get("item_id", 0))
    item_type = e.get("item_type", "")
    box_id    = int(e.get("box_id", 0))
    if not item_id or not item_type or not box_id: return
    bucket = _collection_bucket(item_type)
    it = _find_item(bucket, item_id)
    if not it: return
    
    # validations
    if int(it.get("restored",0)) not in (1,2): return
    ok, _ = _validate_box(item_type, box_id)
    if not ok: return
    
    it["ubication"] = box_id
    
    # update box counters
    box = _get_box(box_id)
    if box: 
        box["box_total"] = int(box.get("box_total",0)) + 1
        print(f"[achv] Item {item_type}#{item_id} stored in box {box_id}")

def _on_exhibited(e):
    item_id   = int(e.get("item_id", 0))
    item_type = e.get("item_type", "")
    exh_id    = int(e.get("exhibition_id", 0))
    if not item_id or not item_type or not exh_id: return
    bucket = _collection_bucket(item_type)
    it = _find_item(bucket, item_id)
    if not it: return
    
    ok, _ = _validate_exhibition(it, item_type, exh_id)
    if not ok: return
    
    it["exhibition"] = exh_id
    
    # exhibition case counters
    ex = _get_exhibition(exh_id)
    if ex: 
        ex["exhibition_total"] = int(ex.get("exhibition_total",0)) + 1
        print(f"[achv] Item {item_type}#{item_id} exhibited in case {exh_id}")

def _handle_quiz_action(data):
    """Handles specific QUIZ system actions"""
    action = data.get("action", "")
    
    if action == "quiz_completed":
        # Only log the event, without affecting inventory
        npc_id = data.get("npc_id", 0)
        quiz_id = data.get("quiz_id", "")
        print(f"[achv] QUIZ completed: NPC {npc_id}, Quiz {quiz_id}")
        
    elif action == "skills_increased":
        # Skill increase is already handled in quiz_module.py and game_access
        amount = int(data.get("amount", 1))
        print(f"[achv] Skills increased by {amount}")
        
    else:
        print(f"[achv] Unknown QUIZ action: {action}")

ACTIONS = {
    "collection_item_acquired": _on_collection_item_acquired,
    "general_item_acquired":    _on_general_item_acquired,
    "general_item_damaged":     _on_general_item_damaged,
    "restoration_submit":       _on_restoration_submit,
    "restoration_complete":     _on_restoration_complete,
    "shelved":                  _on_shelved,
    "exhibited":                _on_exhibited,
}

# =============================================================================
# MAIN HANDLER FUNCTION
# =============================================================================
def handle():
    cont = logic.getCurrentController()
    sen = _get_msg_sensor(cont)
    if not (sen and sen.bodies):
        return

    _ensure_inventory()

    # List of allowed QUIZ actions
    QUIZ_ALLOWED_ACTIONS = ["quiz_completed", "skills_increased"]
    
    # Process ALL messages received this frame
    dirty = False
    for body in sen.bodies:
        data = _parse_body(body)
        action = data.get("action","")
        
        # NEW VERIFICATION: If QUIZ action, process specially
        if action in QUIZ_ALLOWED_ACTIONS:
            _handle_quiz_action(data)
            continue
            
        fn = ACTIONS.get(action)
        if fn:
            fn(data)
            dirty = True

    if dirty:
        # Update collection statistics in game_state
        try:
            state = game_access.get_state()
            if state and hasattr(state, 'update_collection_stats'):
                state.update_collection_stats()
        except Exception as e:
            print(f"[achv] Error updating statistics: {e}")
            
        # Synchronize with Game.Controller for compatibility
        try:
            game_access.sync_to_controller(logic.getCurrentScene().objects.get("Game.Controller"))
        except Exception as e:
            print(f"[achv] Error synchronizing with Game.Controller: {e}")

# =============================================================================
# HELPER FUNCTIONS FOR OTHER SCRIPTS
# =============================================================================
def get_item_description(item_type, item_id):
    """Gets item description for UI display"""
    _load_object_defs()
    try:
        return logic.objects_text.get(item_type, {}).get(item_id, "")
    except Exception:
        return ""

def get_inventory():
    """Gets current inventory"""
    _ensure_inventory()
    try:
        state = game_access.get_state()
        if state and hasattr(state, 'inventory'):
            return state.inventory
    except Exception:
        pass
    return logic.inventory