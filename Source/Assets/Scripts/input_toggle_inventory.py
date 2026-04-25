"""
input_toggle_inventory.py

Manages inventory toggling with I key and handles V1/V2 state transitions.

This script handles the logic for toggling inventory views (V1 and V2) using
the I key, with proper state management, debouncing, and suspension/resume
messaging for game systems.

Main Features:
    1. I key detection with debounce mechanism
    2. Block inventory opening during dialog
    3. Toggle between HUD, V1 inventory, and V2 inventory
    4. Context-aware opening (V2 near shelves, V1 elsewhere)
    5. Send suspend/resume messages for game systems
    6. Force reset V2 context when closing
    7. Position and visibility management for view roots

Setup:
    Connect to Logic Bricks as Python controller with module 'input_toggle_inventory.main'
    Requires no sensors (uses direct keyboard input via API)

Configurable Variables:
    None (all configuration is handled internally)

Notes:
    - Uses keyboard.inputs API (UPBGE 0.44 compatible)
    - I key detection includes debounce via _i_block_until
    - Dialog detection uses player_object.get('on_dialog')
    - near_shelf property determines V2 vs V1 opening
    - Sends suspend/resume messages to 'suspend_logic' subject
    - V2 close includes force_reset=true to clean context
    - Coordinates with format_hud_data.py for view visibility

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
__description__ = "Manages inventory toggling with I key and V1/V2 state transitions"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic, events

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def _send(subject, body, frm=""):
    try:
        logic.sendMessage(subject, body, "", frm)
    except Exception:
        pass

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main():
    # Global debounce
    if float(getattr(logic, "_i_block_until", 0.0)) > logic.getRealTime():
        return

    # BLOCK DURING DIALOGS
    sc = logic.getCurrentScene()
    player_object = sc.objects.get("Player") if sc else None
    if player_object and player_object.get("on_dialog", False):
        return

    keyboard = logic.keyboard
    i_key = keyboard.inputs.get(events.IKEY)
    if not i_key or not i_key.activated:
        return

    # CHECK IF V2 IS OPEN AND FORCE RESET IF NEEDED
    if bool(getattr(logic, "hud_inventory_v2_open", False)):
        # Close V2 with force_reset to clean context
        _send("inventory2", "close|who=toggle|force_reset=true", "Game.Controller" if "Game.Controller" in sc.objects else "")
        logic._i_block_until = logic.getRealTime() + 0.05
        
        # COMPLETE RESET OF SUSPENSION STATES
        logic.hud_inventory_v2_open = False
        logic.hud_inventory_open = False
        logic._auto_v2_active = False
        
        # SEND RESUME MESSAGE (IMPORTANT)
        try:
            logic.sendMessage("suspend_logic", "v2|resume")
            print("[toggle] Sent resume for V2")
        except Exception as e:
            print(f"[toggle] Error sending resume V2: {e}")
        
        # Hide views
        v1_root = sc.objects.get("Empty.View.1") if sc else None
        v2_root = sc.objects.get("Empty.View.2") if sc else None
        pos_out = sc.objects.get("Empty.Pos.Inv.Out") if sc else None
        
        if v1_root and pos_out:
            v1_root.worldPosition = pos_out.worldPosition.copy()
            v1_root.visible = False
        if v2_root and pos_out:
            v2_root.worldPosition = pos_out.worldPosition.copy()
            v2_root.visible = False
            
        print("[toggle] V2 -> HUD (manual) - States and context reset")
        return

    # 2) If V1 is manually open, close it and go to HUD
    if bool(getattr(logic, "hud_inventory_open", False)):
        _send("inventory", "inventory.hide|view=1", "Game.Controller" if "Game.Controller" in sc.objects else "")
        logic.hud_inventory_open = False
        logic._auto_v2_active = False
        
        # SEND RESUME MESSAGE FOR V1
        try:
            logic.sendMessage("suspend_logic", "v1|resume")
            print("[toggle] Sent resume for V1")
        except Exception as e:
            print(f"[toggle] Error sending resume V1: {e}")
        
        # Hide V1
        v1_root = sc.objects.get("Empty.View.1") if sc else None
        pos_out = sc.objects.get("Empty.Pos.Inv.Out") if sc else None
        if v1_root and pos_out:
            v1_root.worldPosition = pos_out.worldPosition.copy()
            v1_root.visible = False
            
        logic._i_block_until = logic.getRealTime() + 0.02
        print("[toggle] V1 -> HUD (manual) - States reset")
        return

    # 3) If in HUD, decide what to open based on proximity to display case
    try:
        # Detect if near a display case/shelf
        near_shelf = bool(getattr(logic, "near_shelf", False)) or bool(getattr(logic, "in_focus_area", False))
        
        if near_shelf:
            # Near display case: OPEN V2 directly
            _send("inventory2", "open|kind=interactive|force_reset=true", "Game.Controller" if "Game.Controller" in sc.objects else "")
            logic.hud_inventory_v2_open = True
            logic.hud_inventory_open = False
            logic._auto_v2_active = False
            
            # Show V2, hide V1
            v2_root = sc.objects.get("Empty.View.2") if sc else None
            v1_root = sc.objects.get("Empty.View.1") if sc else None
            pos_in = sc.objects.get("Empty.Pos.Inv.In") if sc else None
            pos_out = sc.objects.get("Empty.Pos.Inv.Out") if sc else None
            
            if v2_root and pos_in:
                v2_root.worldPosition = pos_in.worldPosition.copy()
                v2_root.visible = True
            if v1_root and pos_out:
                v1_root.worldPosition = pos_out.worldPosition.copy()
                v1_root.visible = False
                
            # SEND SUSPEND MESSAGE FOR V2
            try:
                logic.sendMessage("suspend_logic", "v2|suspend")
                print("[toggle] Sent suspend for V2")
            except Exception as e:
                print(f"[toggle] Error sending suspend V2: {e}")
                
            print("[toggle] HUD -> V2 (manual - near display case)")
        else:
            # Far from display case: OPEN V1 normally
            _send("inventory", "inventory.show|view=1", "Game.Controller" if "Game.Controller" in sc.objects else "")
            logic.hud_inventory_open = True
            logic.hud_inventory_v2_open = False
            logic._auto_v2_active = False
            
            # Show V1, hide V2
            v1_root = sc.objects.get("Empty.View.1") if sc else None
            v2_root = sc.objects.get("Empty.View.2") if sc else None
            pos_in = sc.objects.get("Empty.Pos.Inv.In") if sc else None
            pos_out = sc.objects.get("Empty.Pos.Inv.Out") if sc else None
            
            if v1_root and pos_in:
                v1_root.worldPosition = pos_in.worldPosition.copy()
                v1_root.visible = True
            if v2_root and pos_out:
                v2_root.worldPosition = pos_out.worldPosition.copy()
                v2_root.visible = False
            
            # SEND SUSPEND MESSAGE FOR V1
            try:
                logic.sendMessage("suspend_logic", "v1|suspend")
                print("[toggle] Sent suspend for V1")
            except Exception as e:
                print(f"[toggle] Error sending suspend V1: {e}")
                
            print("[toggle] HUD -> V1 (manual - far from display case)")
            
    except Exception as e:
        print(f"[toggle] Error detecting context: {e}")
        # Fallback: open V1
        _send("inventory", "inventory.show|view=1", "Game.Controller" if "Game.Controller" in sc.objects else "")
        logic.hud_inventory_open = True
        logic._auto_v2_active = False