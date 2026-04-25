"""
button_fx.py

Manages button system for Inventory windows (V1 and V2) in UPBGE.

This script handles button interactions including hover effects, click detection,
and visual feedback for inventory UI buttons using exclusive ray casting.

Main Features:
    1. Exclusive ray casting mouse detection (no mouse sensors)
    2. Visual effects (tint, scale) for idle, hover, click, and disabled states
    3. Hover animation control (disabled in V2)
    4. Support for close button functionality
    5. Card button handling with V2 transition
    6. View switching between inventory V1 and V2
    7. Mesh swapping for grayed out buttons
    8. Message passing system for inventory actions

Setup:
    Connect to Logic Bricks as Python controller with module 'button_fx.handle'
    Requires buttons with 'button_action' property or specific naming conventions

Configurable Variables:
    DEBUG (bool): Enable debug logging (default: False)
    RAY_CAMERA_NAME (str): Camera for ray casting (default: 'Camera.Inventory')
    RAY_DISTANCE (float): Maximum ray casting distance (default: 10000.0)
    IDLE_TINT (tuple): RGBA color for idle state (default: (1.00, 1.00, 1.00, 1.0))
    OVER_TINT (tuple): RGBA color for hover state (default: (0.82, 0.82, 0.82, 1.0))
    CLICK_TINT (tuple): RGBA color for click state (default: (0.68, 0.68, 0.68, 1.0))
    DISABLED_TINT (tuple): RGBA color for disabled state (default: (0.55, 0.55, 0.55, 1.0))
    HOVER_SCALE (float): Scale factor for hover (default: 1.06)
    CLICK_SCALE (float): Scale factor for click (default: 0.96)
    GRAY_MESH_NAME (str): Mesh name for disabled buttons (default: 'Button.Gray.Mesh')
    HOVER_ACTION_NAME (str): Action name for hover animation (default: 'Object.Hover')

Notes:
    - Uses mouse.inputs for click detection (compatible with UPBGE 0.44)
    - Cards (inventory items) use tint only, no scale effect
    - Hover animation is disabled when V2 inventory is active
    - Requires specific empty objects for positioning: Empty.View.1, Empty.View.2,
      Empty.Pos.Inv.In, Empty.Pos.Inv.Out
    - Uses message actuators for inter-module communication

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
__description__ = "Manages button system for Inventory windows with ray casting"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic, events

# =============================================================================
# CONFIGURATION
# =============================================================================
DEBUG = False

RAY_CAMERA_NAME = "Camera.Inventory"
RAY_DISTANCE    = 10000.0

# Basic tint
IDLE_TINT     = (1.00, 1.00, 1.00, 1.0)
OVER_TINT     = (0.82, 0.82, 0.82, 1.0)
CLICK_TINT    = (0.68, 0.68, 0.68, 1.0)
DISABLED_TINT = (0.55, 0.55, 0.55, 1.0)

# Scale effect for "normal" buttons (cards do not scale)
HOVER_SCALE = 1.06
CLICK_SCALE = 0.96

# Optional gray mesh
GRAY_MESH_NAME = "Button.Gray.Mesh"

# Messaging
SUBJECT_INV2 = "inventory2"
SUBJECT_INV = "inventory"  # To close V1
SUBJECT_INFO = "add_info_text"

# Roots and shared empties
V1_ROOT = "Empty.View.1"
V2_ROOT = "Empty.View.2"
POS_IN  = "Empty.Pos.Inv.In"
POS_OUT = "Empty.Pos.Inv.Out"

# Action for card hover
HOVER_ACTION_NAME = "Object.Hover"

# =============================================================================
# LOGGING
# =============================================================================
def _log(*a):
    if DEBUG: print("[button]", *a)

# =============================================================================
# RAY CAST DETECTION SYSTEM (no sensors)
# =============================================================================
def _is_mouse_over_button(cont):
    """Checks if mouse is over the button using raycast (UPBGE 0.44 compatible)"""
    scene = bge.logic.getCurrentScene()
    own = cont.owner
    
    # Check if object should NOT be clickable
    # 1. If not visible, not clickable
    if not own.visible:
        return False
    
    # 2. If it has specific property indicating not clickable
    if own.get("_is_clickable", True) == False:
        return False
    
    # 3. If too far from origin, not clickable
    if own.worldPosition.length > 100000:  # Object too far
        return False
    
    # Get camera - first specific, then active
    cam = scene.objects.get(RAY_CAMERA_NAME) or scene.active_camera
    if not cam:
        return False
    
    try:
        # Method for UPBGE 0.44 - use getScreenRay
        mouse_pos = bge.logic.mouse.position
        hit_obj = cam.getScreenRay(mouse_pos[0], mouse_pos[1], RAY_DISTANCE, "")
        
        if hit_obj:
            # Check if hit object is this button
            if hit_obj == own:
                return True
            
            # Check if hit object is clickable
            if hit_obj.get("_is_clickable", True) == False:
                return False
            
            # Check if it's a child object (button might have parts)
            try:
                parent = hit_obj.parent
                while parent:
                    if parent == own:
                        return True
                    # Check if parent is clickable
                    if parent.get("_is_clickable", True) == False:
                        return False
                    parent = parent.parent
            except:
                pass
        
        return False
        
    except Exception as e:
        if DEBUG: _log(f"Mouse detection error: {e}")
        return False

# --------------------------------------------------------------------------
# SIMPLIFIED FUNCTION: Hover animation control
# --------------------------------------------------------------------------
def _control_hover_animation(owner, activate: bool):
    """Controls hover animation, disabled in V2"""
    
    # Disable animation if in V2
    try:
        v2_root = owner.scene.objects.get("Empty.View.2")
        if v2_root and v2_root.visible:
            if activate and DEBUG: 
                _log(f"Hover disabled in V2: {owner.name}")
            return False
    except:
        pass
    
    try:
        if activate:
            owner.playAction(
                HOVER_ACTION_NAME, 1, 10, 
                play_mode=bge.logic.KX_ACTION_MODE_PLAY,
                blendin=5,
                layer=0
            )
            if DEBUG: _log(f"Hover ACTIVATED: {owner.name}")
        else:
            owner.stopAction(0)
            if DEBUG: _log(f"Hover STOPPED: {owner.name}")
        return True
    except Exception as e:
        if DEBUG: _log(f"Hover error: {e}")
        return False

# --------------------------------------------------------------------------
# Visual helpers
# --------------------------------------------------------------------------
def _tint_branch(root, rgba):
    if not root: return
    r,g,b,a = rgba
    try: root.color = [r,g,b,a]
    except: pass
    try:
        for ch in root.childrenRecursive:
            try: ch.color = [r,g,b,a]
            except: pass
    except: pass

def _set_scale(owner, s):
    try:
        if "_base_scale" not in owner:
            owner["_base_scale"] = tuple(owner.localScale)
        bs = owner["_base_scale"]
        owner.localScale = (bs[0]*s, bs[1]*s, bs[2]*s)
    except: pass

def _reset_scale(owner):
    try:
        if "_base_scale" in owner:
            owner.localScale = tuple(owner["_base_scale"])
    except: pass

def _cache_base_mesh(owner):
    try:
        if "_base_mesh" not in owner and owner.meshes:
            owner["_base_mesh"] = owner.meshes[0].name
    except: pass

def _replace_mesh(owner, mesh_name):
    try:
        owner.replaceMesh(mesh_name, True, False)
        return True
    except:
        return False

def _swap_children_over(owner, use_over: bool) -> bool:
    try:
        name = owner.name
        over = owner.scene.objects.get(name + ".Over")
        norm = owner.scene.objects.get(name + ".Normal")
        if over or norm:
            if over: over.visible = use_over
            if norm: norm.visible = not use_over
            return True
    except: pass
    return False

def _is_card_button(owner) -> bool:
    try:
        return str(owner.get("button_action","")).strip().lower() == "open_v2_item"
    except:
        return False

def _apply_visual(owner, state: str):
    owner["_button_state"] = state
    _cache_base_mesh(owner)
    is_card = _is_card_button(owner)

    if state == "disabled":
        if is_card:
            _tint_branch(owner, DISABLED_TINT); _reset_scale(owner); return
        ok = False
        try:
            if owner.meshes and owner.meshes[0].name != GRAY_MESH_NAME:
                ok = _replace_mesh(owner, GRAY_MESH_NAME)
            else:
                ok = True
        except: pass
        if not ok:
            _tint_branch(owner, DISABLED_TINT); _reset_scale(owner)
        return

    if not is_card:
        try:
            base = owner.get("_base_mesh", None)
            if base and owner.meshes and owner.meshes[0].name != base:
                _replace_mesh(owner, base)
        except: pass

    # Cards: no scale (only subtle tint)
    if is_card:
        if state == "idle":
            _tint_branch(owner, IDLE_TINT); _reset_scale(owner)
        elif state == "over":
            _tint_branch(owner, OVER_TINT)
        elif state == "click":
            _tint_branch(owner, CLICK_TINT)
        return

    # Normal buttons
    if state == "over":
        did = _swap_children_over(owner, True)
        if not did:
            _tint_branch(owner, OVER_TINT); _set_scale(owner, HOVER_SCALE)
        return

    if state == "click":
        did = _swap_children_over(owner, True)
        if not did:
            _tint_branch(owner, CLICK_TINT); _set_scale(owner, CLICK_SCALE)
        return

    did = _swap_children_over(owner, False)
    if not did:
        _tint_branch(owner, IDLE_TINT); _reset_scale(owner)

# --------------------------------------------------------------------------
# Ray (helper functions kept for compatibility)
# --------------------------------------------------------------------------
def _belongs_to(obj, root):
    if not obj: return False
    if obj == root: return True
    try:
        p = obj.parent
        while p:
            if p == root: return True
            p = p.parent
    except: pass
    return False

def _infer_action(owner):
    act = owner.get("button_action", "")
    if act: return str(act)
    n = owner.name.lower()
    if "close.view" in n or owner.get("is_close_button", False):
        return "close_view"
    if "exhib" in n: return "exhib"
    if "restor" in n: return "restor"
    return "box"

# --------------------------------------------------------------------------
# Messaging
# --------------------------------------------------------------------------
def _send_subject(cont, subj, body):
    msg = None
    for a in cont.actuators:
        if a.__class__.__name__ == "KX_MessageActuator" and a.subject == subj:
            msg = a; break
    if msg:
        msg.body = body
        cont.activate(msg)
        _log("MSG via actuator ->", subj, "::", body)
        return True
    try:
        bge.logic.sendMessage(subj, body)
        _log("MSG via sendMessage ->", subj, "::", body)
        return True
    except Exception as e:
        _log("ERROR sendMessage:", e)
        return False

# --------------------------------------------------------------------------
# Branch visibility
# --------------------------------------------------------------------------
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

# --------------------------------------------------------------------------
# Coordinated movement
# --------------------------------------------------------------------------
def _move_root_to(name_root, name_target):
    """Moves the empty to the target position"""
    scn = bge.logic.getCurrentScene()
    if not scn: return False
    root = scn.objects.get(name_root)
    target = scn.objects.get(name_target)
    if not root: return False
    try:
        if target:
            root.worldPosition = target.worldPosition.copy()
            if DEBUG: _log(f"Moved {name_root} -> {name_target}")
        else:
            if name_target == "Empty.Pos.Inv.Out":
                root.worldPosition = (1e6, 1e6, 1e6)
        return True
    except Exception as e:
        if DEBUG: _log(f"Error moving {name_root}: {e}")
        return False

def _view_set_v1_in():
    """Shows V1 - cards are handled separately"""
    scn = bge.logic.getCurrentScene()
    
    _move_root_to("Empty.View.1", "Empty.Pos.Inv.In")
    v1 = scn.objects.get("Empty.View.1") if scn else None
    if v1: 
        v1.visible = True
        if DEBUG: _log("V1 activated")
    
    _move_root_to("Empty.View.2", "Empty.Pos.Inv.Out")
    v2 = scn.objects.get("Empty.View.2") if scn else None
    if v2: 
        v2.visible = False
    
    try:
        bge.logic.hud_inventory_v2_open = False
        bge.logic.hud_inventory_open = True
    except: pass

def _view_set_v2_in():
    """Shows V2 - cards are handled separately"""
    scn = bge.logic.getCurrentScene()
    
    _move_root_to("Empty.View.2", "Empty.Pos.Inv.In")
    v2 = scn.objects.get("Empty.View.2") if scn else None
    if v2: 
        v2.visible = True
        if DEBUG: _log("V2 activated")
    
    _move_root_to("Empty.View.1", "Empty.Pos.Inv.Out")
    v1 = scn.objects.get("Empty.View.1") if scn else None
    if v1: 
        v1.visible = False
    
    try:
        bge.logic.hud_inventory_v2_open = True
        bge.logic.hud_inventory_open = False
    except: pass

# --- Cards -> open V2 (readonly) ---
def _open_v2_from_v1(cont, owner):
    """COMPLETE FUNCTION - Opens V2 from V1 card click"""
    try:
        if bool(getattr(bge.logic, "v2_is_in", False)):
            _log("V2 already active, ignoring click")
            return
    except: 
        pass

    # Get object properties
    itype = str(owner.get("item_type", "")).strip().lower()
    try:
        iid = int(owner.get("item_id", 0))
    except Exception:
        iid = 0

    if not itype or iid <= 0:
        _log("open_v2_item: missing item_type/item_id properties")
        return

    _log(f"Opening V2 for {itype}#{iid} from V1")

    # Move ALL other cards to OUT before opening V2
    sc = bge.logic.getCurrentScene()
    if sc:
        # Move all cards except the clicked one to OUT position
        for obj in sc.objects:
            if obj.name.startswith("Object.") and not obj.name.startswith("Object.World."):
                # Check if it's an inventory card
                if obj.get("item_type") and obj.get("item_id"):
                    # If NOT the clicked card, move it to OUT
                    if not (str(obj.get("item_type", "")).lower() == itype and 
                           int(obj.get("item_id", 0)) == iid):
                        _log(f"Moving other card to OUT: {obj.name}")
                        # Find OUT position
                        out_pos = sc.objects.get("Object.Pos.Out")
                        if out_pos:
                            obj.worldPosition = out_pos.worldPosition.copy()
                            obj.visible = False
                            # Mark as not clickable
                            obj["_is_clickable"] = False
                        else:
                            # Extreme position
                            obj.worldPosition = (1e6, 1e6, 1e6)
                            obj.visible = False
                            obj["_is_clickable"] = False

    # INITIALIZE V2 CONTEXT IF NOT EXISTS
    if not hasattr(bge.logic, "v2ctx"):
        bge.logic.v2ctx = {
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
    
    # SAVE DIRECT REFERENCE TO CLICKED OBJECT
    # This is CRITICAL for V2 to position the card
    bge.logic.v2ctx["card_obj"] = owner
    bge.logic.v2ctx["kx_item"] = owner
    
    # SAVE OBJECT DATA IN V2 CONTEXT
    bge.logic.v2ctx["item_dict"] = {
        "item_type": itype,
        "item_id": iid,
        "description": "",  # Will be filled in inventory_view2.py
        "restored": int(owner.get("restored", 0)),
        "ubication": int(owner.get("ubication", 0)),
        "exhibition": int(owner.get("exhibition", 0)),
        "name": owner.name  # Save name for debugging
    }
    
    # MARK CONTEXT AS "READONLY" FROM V1
    bge.logic.v2ctx["kind"] = "readonly"
    bge.logic.v2ctx["origin"] = "v1_click"
    
    print(f"[button] Saved reference to card: {owner.name} ({itype}#{iid})")

    # 1) Change view: V2(In) / V1(Out) + ensure V2 visibility
    _view_set_v2_in()

    # 2) Open V2 in readonly mode (detail view) with ALL necessary data
    body = f"open|kind=readonly|item_type={itype}|item_id={iid}|origin=v1_click|force_reset=true"
    _send_subject(cont, SUBJECT_INV2, body)

    # 3) Clear general info channel (does not affect info_text_v2)
    _send_subject(cont, SUBJECT_INFO, "info.show|info_text|0|field=info_text")
    
    # 4) Update global state
    try:
        bge.logic.hud_inventory_v2_open = True
        bge.logic.hud_inventory_open = False
        bge.logic._auto_v2_active = False
    except:
        pass
    
    _log(f"V2 opened for {itype}#{iid} from card click")
    print(f"[V2] V1->V2 transition initiated for {owner.name}")

# --- Close current view ---
def _close_current_view(cont, owner):
    """Closes the current view (V1 or V2) and returns to HUD"""
    scn = bge.logic.getCurrentScene()
    
    # Check which view is active
    v2_open = bool(getattr(bge.logic, "hud_inventory_v2_open", False))
    v1_open = bool(getattr(bge.logic, "hud_inventory_open", False))
    
    if DEBUG:
        _log(f"Close attempt: V1={v1_open}, V2={v2_open}")

    # Import game_access for complete cleanup
    try:
        import game_access
    except:
        pass
        
    if v2_open:
        # Close V2 and return to HUD
        body = "close|who=close_button"
        _send_subject(cont, SUBJECT_INV2, body)
        
        # Update states
        try:
            bge.logic.hud_inventory_v2_open = False
            bge.logic._auto_v2_active = False
        except:
            pass
        
        # Move both views out
        _move_root_to(V1_ROOT, POS_OUT)
        _move_root_to(V2_ROOT, POS_OUT)
        
        # Hide both views
        v1 = scn.objects.get(V1_ROOT) if scn else None
        v2 = scn.objects.get(V2_ROOT) if scn else None
        if v1: v1.visible = False
        if v2: v2.visible = False
        
        if DEBUG: _log("V2 closed (close button)")
        
    elif v1_open:
        # Close V1 and return to HUD
        body = "inventory.hide|view=1"
        _send_subject(cont, SUBJECT_INV, body)
        
        # Update state
        try:
            bge.logic.hud_inventory_open = False
        except:
            pass
        
        # Move V1 out and hide
        _move_root_to(V1_ROOT, POS_OUT)
        v1 = scn.objects.get(V1_ROOT) if scn else None
        if v1: v1.visible = False
        
        if DEBUG: _log("V1 closed (close button)")
    else:
        # Nothing open, just ensure hiding
        _move_root_to(V1_ROOT, POS_OUT)
        _move_root_to(V2_ROOT, POS_OUT)
        v1 = scn.objects.get(V1_ROOT) if scn else None
        v2 = scn.objects.get(V2_ROOT) if scn else None
        if v1: v1.visible = False
        if v2: v2.visible = False
        if DEBUG: _log("Views already closed")

# =============================================================================
# MAIN HANDLER FUNCTION
# =============================================================================
def handle():
    cont  = bge.logic.getCurrentController()
    owner = cont.owner

    disabled = bool(owner.get("button_disabled", False))

    # Disable card if V2 is already In (prevents redundant clicks)
    if _is_card_button(owner):
        try:
            if bool(getattr(bge.logic, "v2_is_in", False)):
                disabled = True
        except: pass

    # ===== MOUSE DETECTION BY RAYCAST (no sensors) =====
    # Detect mouse over using raycasting
    is_over = _is_mouse_over_button(cont)
    
    # Detect mouse click using the new inputs method
    mouse = bge.logic.mouse
    left_mouse_input = mouse.inputs.get(events.LEFTMOUSE)
    just_clicked = left_mouse_input and left_mouse_input.activated

    # Previous state to detect transitions
    previous_state = owner.get("_button_state", "idle")
    current_state = "idle"

    if DEBUG:
        _log(
            f"{owner.name} | dis={disabled} | over={is_over}",
            f"| LMB={left_mouse_input.activated if left_mouse_input else 'None'} | clickEdge={just_clicked} | action={owner.get('button_action','')}"
        )

    # Determine current state
    if disabled:
        current_state = "disabled"
    elif is_over:
        if just_clicked:
            current_state = "click"
        else:
            current_state = "over"
    else:
        current_state = "idle"

    # Apply visual effects and action if state changed
    if current_state != previous_state:
        _apply_visual(owner, current_state)
        
        # Control hover animation for cards (disabled in V2)
        if _is_card_button(owner):
            if current_state == "over" and previous_state != "over":
                _control_hover_animation(owner, True)
            elif current_state != "over" and previous_state == "over":
                _control_hover_animation(owner, False)
        
        # Update state
        owner["_button_state"] = current_state

    # Handle clicks (independent of state change)
    if is_over and just_clicked and not disabled:
        act = _infer_action(owner).lower()
        if act == "open_v2_item":
            bge.logic.sendMessage("sound_fx.play", "sound_fx.play|clic.ogg")              
            _open_v2_from_v1(cont, owner)
        elif act == "close_view":  # New case
            bge.logic.sendMessage("sound_fx.play", "sound_fx.play|clic.ogg")            
            _close_current_view(cont, owner)
        else:
            # Classic buttons (To.Box / To.Exhib / To.Restor) -> APPLY
            bge.logic.sendMessage("sound_fx.play", "sound_fx.play|insertion.ogg")
            body = "apply|action={}".format(act)
            _send_subject(cont, SUBJECT_INV2, body)