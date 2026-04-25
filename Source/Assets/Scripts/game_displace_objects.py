"""
game_displace_objects.py

Manages inventory card placement and movement between slots and out positions.

This script handles the displacement of inventory cards between array slots
and out positions, synchronizing with game state and ensuring proper
clickability of inventory objects while excluding world objects.

Main Features:
    1. Place inventory cards on array slots when inventory is open
    2. Move inventory cards to out position when inventory is closed
    3. Exclude world objects (Object.World.*) from displacement operations
    4. Manage card clickability based on visibility and position
    5. Synchronize with game_state inventory data
    6. Support for quiz success events to add items
    7. Collision mask management for click detection
    8. Position restoration for slots

Setup:
    Connect to Logic Bricks as Python controller with module 'game_displace_objects.handle_objects'
    and 'game_displace_objects.handle_inventory' as needed

Configurable Variables:
    DEBUG (int): Debug level (0-2, default: 2)
    SUBJ_OBJECTS (str): Message subject for objects (default: 'displace_objects')
    SUBJ_INVENTORY (str): Message subject for inventory (default: 'inventory')
    MOVE_SLOT_TO_OUT (bool): Enable moving slots to out position (default: False)
    OUT_POS_OBJECT_NAME (str): Name of out position empty (default: 'Object.Pos.Out')
    V1_ROOT (str): Name of V1 root empty (default: 'Empty.View.1')

Notes:
    - World objects (Object.World.*) are completely ignored and never displaced
    - Inventory objects (Object.*) are displaced to slots or out positions
    - Slots are named 'Array.{Period}.{id}' (e.g., 'Array.Pal.1')
    - Cards are named 'Object.{Period}.{id}' (e.g., 'Object.Pal.1')
    - When MOVE_SLOT_TO_OUT is False, slots remain visible for debugging
    - Clickability is enforced via collision masks and _is_clickable property
    - Requires game_access module for inventory data

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
__description__ = "Manages inventory card placement and movement"

# =============================================================================
# IMPORTS
# =============================================================================
import json
from bge import logic
import time
import game_access

# =============================================================================
# CONFIGURATION
# =============================================================================
DEBUG = 2  # 0-2
SUBJ_OBJECTS   = "displace_objects"   
SUBJ_INVENTORY = "inventory"          

# KEY CHANGE: Disable moving slots to OUT for debugging
MOVE_SLOT_TO_OUT = False  # Changed to False to keep arrays visible

OUT_POS_OBJECT_NAME = "Object.Pos.Out"
V1_ROOT = "Empty.View.1"

_CAP = {"pal":"Pal", "neo":"Neo", "bronze":"Bronze", "iberian":"Iberian", "roman":"Roman"}

# =============================================================================
# LOGGING
# =============================================================================
def _log(*a, lvl=1):
    if DEBUG >= lvl:
        print("[displace]", *a)

# =============================================================================
# OBJECT TYPE DETECTION
# =============================================================================
def _is_world_object(obj):
    """Checks if it's a World object (Object.World.*) - MUST BE IGNORED"""
    if not obj:
        return False
    return obj.name.startswith("Object.World.")

def _is_inventory_object(obj):
    """Checks if it's an Inventory object (Object.* but NOT Object.World.*)"""
    if not obj:
        return False
    # It's an Inventory object if it starts with "Object." but NOT with "Object.World."
    return obj.name.startswith("Object.") and not obj.name.startswith("Object.World.")

# =============================================================================
# MESSAGE HANDLING HELPERS
# =============================================================================
def _any_message_sensor_with_subject(cont, subject: str):
    for sen in cont.sensors:
        if getattr(sen, "positive", False) and sen.__class__.__name__.endswith("MessageSensor"):
            if getattr(sen, "subject", "") == subject:
                return sen
    return None

def _parse_body(body: str):
    body = (body or "").strip()
    if not body:
        return {}
    parts = [t.strip() for t in body.split("|") if t.strip()]
    out = {}
    if parts:
        out["cmd"] = parts[0]
        for p in parts[1:]:
            if "=" in p:
                k, v = p.split("=", 1)
                out[k.strip()] = v.strip()
    return out

def _obj(scene, name):
    return scene.objects.get(name)

# =============================================================================
# SLOT AND CARD NAMING
# =============================================================================
def _slot_name(item_type, idx):
    t = _CAP.get(item_type, item_type.capitalize())
    return f"Array.{t}.{idx}"

def _card_name(item_type, idx):
    t = _CAP.get(item_type, item_type.capitalize())
    return f"Object.{t}.{idx}"

# =============================================================================
# SLOT POSITION MANAGEMENT
# =============================================================================
def _save_slot_transform(slot):
    if "_orig_pos" not in slot:
        slot["_orig_pos"] = slot.worldPosition.copy()
    if "_orig_scale" not in slot:
        slot["_orig_scale"] = slot.worldScale.copy()

def _restore_slot(slot):
    if "_orig_pos" in slot:
        slot.worldPosition = slot["_orig_pos"]
        slot.visible = True  # Ensure slot visibility
        _log(f"Slot {slot.name} restored and visible", lvl=2)
    if "_orig_scale" in slot:
        slot.worldScale = slot["_orig_scale"]

def _restore_all_slots():
    sc = logic.getCurrentScene()
    slots_restored = 0
    for o in sc.objects:
        if o.name.startswith("Array.") and ("_orig_pos" in o or "_orig_scale" in o):
            _restore_slot(o)
            slots_restored += 1
    _log(f"Slots restored: {slots_restored}", lvl=1)

def _move_slot_to_out(slot):
    # KEY CHANGE: Only move if enabled, otherwise keep visible
    if not MOVE_SLOT_TO_OUT:
        slot.visible = True  # Keep slot visible
        _log(f"Slot {slot.name} kept visible (MOVE_SLOT_TO_OUT=False)", lvl=2)
        return
        
    sc = logic.getCurrentScene()
    _save_slot_transform(slot)
    out = _obj(sc, OUT_POS_OBJECT_NAME)
    if out:
        slot.worldPosition = out.worldPosition.copy()
        _log("slot -> OUT", slot.name, "->", out.name, lvl=2)
    else:
        p = slot.worldPosition
        slot.worldPosition = [p.x, p.y, p.z + 100000.0]
        _log("slot -> farZ (no OUT found):", slot.name, lvl=2)

# =============================================================================
# CARD POSITION MANAGEMENT
# =============================================================================
def _move_card_to_out(item_type, item_id):
    """Moves card to OUT position and marks as NOT clickable"""
    sc = logic.getCurrentScene()
    card = _obj(sc, _card_name(item_type, item_id))
    out  = _obj(sc, OUT_POS_OBJECT_NAME)
    if not card or not out:
        _log("no OUT or card not found:", _card_name(item_type, item_id), lvl=1)
        return False

    # CRITICAL: Completely IGNORE World objects
    if _is_world_object(card):
        _log(f"IGNORING World object: {card.name} (not part of inventory)", lvl=1)
        return False

    # Ensure object is NOT clickable when out
    # 1. Move to distant position
    card.worldPosition = out.worldPosition.copy()
    
    # 2. Move even further for safety (extreme coordinates)
    # This guarantees the ray won't reach there
    if out.worldPosition.length < 1000:  # If OUT is close
        card.worldPosition = (1e6, 1e6, 1e6)
        _log(f"Card {card.name} moved to extreme position", lvl=2)
    
    # 3. Temporarily disable collisions
    try:
        # Save original collision state if not saved
        if "_collision_original" not in card:
            # Try to save current physics state
            try:
                card["_collision_original"] = {
                    "visible": card.visible,
                    "position": tuple(card.worldPosition),
                    "has_physics": hasattr(card, 'getPhysicsId')
                }
            except:
                card["_collision_original"] = "default"
        
        # Disable physics for this object
        try:
            card.suspendDynamics()
        except:
            pass
            
        # Disable collision mask
        try:
            card.setCollisionMask([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
            _log(f"Collisions disabled for {card.name}", lvl=3)
        except Exception as e:
            _log(f"Error adjusting collisions for {card.name}: {e}", lvl=2)
    except Exception as e:
        _log(f"Error preparing collisions for {card.name}: {e}", lvl=2)

    # 4. Ensure invisibility
    try:
        card.visible = False
        _log(f"Card {card.name} invisible at OUT", lvl=2)
    except Exception as e:
        _log(f"Error setting visibility for {card.name}: {e}", lvl=2)

    # Mark specifically as not clickable
    card["_is_clickable"] = False
    card["_at_array"] = False
    
    _log("card -> OUT (and disabled):", card.name, lvl=2)
    return True

def _place_card_on_slot(item_type, item_id):
    """Places card on slot and marks as clickable"""
    sc = logic.getCurrentScene()
    slot = _obj(sc, _slot_name(item_type, item_id))
    card = _obj(sc, _card_name(item_type, item_id))
    
    if not card:
        _log("card NOT found:", _card_name(item_type, item_id), lvl=1)
        return False
    if not slot:
        _log("slot NOT found:", _slot_name(item_type, item_id), lvl=1)
        return False

    # CRITICAL: Completely IGNORE World objects
    if _is_world_object(card):
        _log(f"IGNORING World object: {card.name} (not part of inventory)", lvl=1)
        return False

    # STEP 1: Ensure slot is visible and in correct position
    try:
        slot.visible = True
        _log(f"Slot {slot.name} visible = True", lvl=2)
    except Exception as e:
        _log(f"Error making slot visible {slot.name}: {e}", lvl=1)

    # STEP 2: Small delay to ensure slot is ready
    try:
        time.sleep(0.02)
    except:
        pass

    # STEP 3: Position card on slot
    card.worldPosition = slot.worldPosition.copy()
    card.worldScale    = slot.worldScale.copy()
    
    # Restore clickability
    # 1. Mark as clickable
    card["_is_clickable"] = True
    
    # 2. Restore collisions if saved
    try:
        if "_collision_original" in card:
            _log(f"Restoring collisions for {card.name}", lvl=3)
            # Reactivate dynamics
            try:
                card.restoreDynamics()
            except:
                pass
                
            # Restore default collision mask
            try:
                card.setCollisionMask([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
                _log(f"Collisions restored for {card.name}", lvl=3)
            except Exception as e:
                _log(f"Error restoring collision mask: {e}", lvl=2)
    except Exception as e:
        _log(f"Error restoring collisions for {card.name}: {e}", lvl=2)
    
    # STEP 4: Ensure card visibility
    try:
        card.visible = True
        _log(f"Card {card.name} visible = True (on slot {slot.name})", lvl=2)
    except Exception as e:
        _log(f"Error setting card visibility: {e}", lvl=1)

    card["_at_array"] = True

    # STEP 5: Optionally move slot to OUT
    if MOVE_SLOT_TO_OUT:
        _move_slot_to_out(slot)
    else:
        _log(f"Slot {slot.name} kept in position (debug)", lvl=2)

    _log(f"OK card->{card.name} on slot->{slot.name} (clickable)", lvl=1)
    return True

# =============================================================================
# INVENTORY SYNCHRONIZATION
# =============================================================================
def _ensure_v1_visible():
    """Ensures Empty.View.1 is visible and in correct position"""
    sc = logic.getCurrentScene()
    if not sc:
        return False
        
    v1_root = sc.objects.get(V1_ROOT)
    pos_in = sc.objects.get("Empty.Pos.Inv.In")
    
    if v1_root and pos_in:
        # Ensure position
        v1_root.worldPosition = pos_in.worldPosition.copy()
        # Ensure visibility - THIS IS KEY
        v1_root.visible = True
        _log(f"Empty.View.1 visible = True, position = {v1_root.worldPosition}", lvl=1)
        return True
    
    _log("Could not ensure V1 visibility", lvl=1)
    return False

def _iter_acquired():
    """Iterates over acquired items from game_access, EXCLUDING World objects"""
    game = game_access.get_game()
    if not game:
        return
        
    inv = game.state.inventory
    col = inv.get("collection_items", {})
    for itype, lst in col.items():
        for it in lst:
            iid = int(it.get("item_id", 0))
            if iid:
                # Check if corresponding object is a World object
                card_name = _card_name(itype, iid)
                sc = logic.getCurrentScene()
                card = sc.objects.get(card_name) if sc else None
                
                # Only yield if NOT a World object (is an Inventory object)
                if not card or not _is_world_object(card):
                    yield itype, iid
                else:
                    _log(f"Skipping World object from inventory: {card_name}", lvl=2)

def _force_all_cards_visible():
    """Forces visibility of acquired cards, EXCLUDING World objects"""
    sc = logic.getCurrentScene()
    if not sc:
        return
        
    cards_processed = 0
    for itype, iid in _iter_acquired():
        card_name = _card_name(itype, iid)
        card = sc.objects.get(card_name)
        if card and not _is_world_object(card):
            try:
                card.visible = True
                cards_processed += 1
                _log(f"Card forced visible: {card_name}", lvl=2)
            except Exception as e:
                _log(f"Error forcing visibility {card_name}: {e}", lvl=1)
    
    _log(f"Inventory cards forced visible: {cards_processed}", lvl=1)

def _ensure_all_cards_unclickable_when_hidden():
    """Ensures all cards not in inventory are not clickable"""
    sc = logic.getCurrentScene()
    if not sc:
        return
    
    # Check inventory state
    v1_open = bool(getattr(logic, "hud_inventory_open", False))
    v2_open = bool(getattr(logic, "hud_inventory_v2_open", False))
    
    _log(f"Checking clickability: V1={v1_open}, V2={v2_open}", lvl=2)
    
    # Only if both views are closed
    if not v1_open and not v2_open:
        cards_processed = 0
        for obj in sc.objects:
            # Look for objects that look like inventory cards
            if obj.name.startswith("Object.") and not obj.name.startswith("Object.World."):
                # If too far or not visible, mark as not clickable
                if obj.worldPosition.length > 1000 or not obj.visible:
                    obj["_is_clickable"] = False
                    try:
                        # Ensure invisibility
                        obj.visible = False
                        
                        # Disable collisions
                        obj.setCollisionMask([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
                        _log(f"Disabled clickability for {obj.name} (position: {obj.worldPosition.length})", lvl=3)
                        cards_processed += 1
                    except Exception as e:
                        _log(f"Error disabling {obj.name}: {e}", lvl=2)
        
        if cards_processed > 0:
            _log(f"Cards disabled for clicking: {cards_processed}", lvl=1)
    else:
        # If any view is open, ensure visible cards are clickable
        cards_processed = 0
        for obj in sc.objects:
            if obj.name.startswith("Object.") and not obj.name.startswith("Object.World."):
                # If close and visible, mark as clickable
                if obj.worldPosition.length < 1000 and obj.visible:
                    obj["_is_clickable"] = True
                    try:
                        obj.setCollisionMask([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])
                        _log(f"Enabled clickability for {obj.name}", lvl=3)
                        cards_processed += 1
                    except:
                        pass
        
        if cards_processed > 0:
            _log(f"Cards enabled for clicking: {cards_processed}", lvl=2)

def _sync_all_to_inventory():
    """Synchronizes cards to inventory - ONLY Inventory cards (not World)"""
    _log("Synchronizing Inventory cards to inventory (excluding World objects)", lvl=1)
    
    # 1. Ensure Empty.View.1 is visible
    if not _ensure_v1_visible():
        _log("ERROR: Could not make Empty.View.1 visible", lvl=1)
        return
    
    # 2. Restore all slots
    _restore_all_slots()
    
    # 3. Small delay for synchronization
    try:
        time.sleep(0.03)
    except:
        pass
    
    # 4. Force visibility of Inventory cards (excluding World)
    _force_all_cards_visible()
    
    # 5. Another small delay
    try:
        time.sleep(0.02)
    except:
        pass
    
    # 6. Place each card on its slot (only Inventory objects)
    successful_placements = 0
    for itype, iid in _iter_acquired():
        success = _place_card_on_slot(itype, iid)
        if success:
            successful_placements += 1
        else:
            _log(f"Error placing Inventory card {itype}#{iid}", lvl=1)
    
    # 7. Ensure clickability of visible cards
    _ensure_all_cards_unclickable_when_hidden()
    
    _log(f"Synchronization completed: {successful_placements} Inventory cards placed and clickable", lvl=1)

def _sync_all_to_out():
    """Moves cards to OUT - ONLY Inventory cards (not World)"""
    _log("Synchronizing Inventory cards to OUT (excluding World objects)", lvl=1)
    
    # Restore slots first
    _restore_all_slots()
    
    # Move Inventory cards to OUT
    moved_cards = 0
    for itype, iid in _iter_acquired():
        if _move_card_to_out(itype, iid):
            moved_cards += 1
    
    # Ensure all are not clickable
    _ensure_all_cards_unclickable_when_hidden()
    
    _log(f"Synchronization to OUT completed: {moved_cards} cards moved and disabled", lvl=1)

# =============================================================================
# MAIN HANDLER FUNCTIONS
# =============================================================================
def handle_objects():
    """Handles object messages (quiz success, etc.)"""
    cont = logic.getCurrentController()
    sen  = _any_message_sensor_with_subject(cont, SUBJ_OBJECTS)
    if not (sen and sen.bodies):
        return
        
    for body in sen.bodies:
        d = _parse_body(body)
        cmd = (d.get("cmd") or "").lower()
        _log("OBJ MSG:", d, lvl=2)

        if cmd == "on_quiz_success":
            item_type = str(d.get("item_type", ""))
            try:
                item_id = int(d.get("slot_index", d.get("item_id", 0)))
            except Exception:
                item_id = 0
            if not (item_type and item_id):
                continue
            
            _log(f"Quiz success: {item_type}#{item_id}")
            
            # Check if corresponding object is World and skip it
            sc = logic.getCurrentScene()
            card_name = _card_name(item_type, item_id)
            card = sc.objects.get(card_name) if sc else None
            
            if card and _is_world_object(card):
                _log(f"Ignoring World object for quiz: {card_name}")
                continue
            
            # If V1 is open, place on slot
            if bool(getattr(logic, "hud_inventory_open", False)):
                if not _place_card_on_slot(item_type, item_id):
                    _log(f"Failed slot placement", lvl=1)
            else:
                _move_card_to_out(item_type, item_id)

def handle_inventory():
    """Handles inventory messages (show/hide)"""
    cont = logic.getCurrentController()
    sen  = _any_message_sensor_with_subject(cont, SUBJ_INVENTORY)
    if not (sen and sen.bodies):
        return

    for body in sen.bodies:
        d = _parse_body(body)
        cmd = (d.get("cmd") or "").lower()
        view = str(d.get("view", ""))
        _log("INV MSG:", d, lvl=2)

        if cmd == "inventory.show" and view == "1":
            _log("Showing inventory V1 - Inventory cards to slots", lvl=1)
            _sync_all_to_inventory()
            
        elif cmd == "inventory.hide" and view == "1":
            _log("Hiding inventory V1 - Inventory cards to OUT", lvl=1)
            _sync_all_to_out()
            
            # Ensure all are not clickable
            _ensure_all_cards_unclickable_when_hidden()

# =============================================================================
# MAIN FUNCTION (optional periodic check)
# =============================================================================
def main():
    """Main function that can be called each frame to check state"""
    # Only check in debug mode or every certain time
    current_time = getattr(logic, "_last_clicability_check", 0)
    real_time = logic.getRealTime()
    
    if real_time - current_time > 2.0:  # Check every 2 seconds
        logic._last_clicability_check = real_time
        _ensure_all_cards_unclickable_when_hidden()