"""
pause_window.py

Manages pause menu window visibility, text updates, and keyboard input.

This script handles the pause menu system including showing/hiding the menu,
managing pause state, updating localized texts, and toggling sound/language
buttons with mesh swapping.

Main Features:
    1. Show/hide pause menu with ESC or P key
    2. Send suspend/resume messages to game systems
    3. Hide inventory views when pausing
    4. Load localized texts from JSON files
    5. Update button texts dynamically on language change
    6. Toggle sound button mesh (On/Off)
    7. Toggle language button mesh (Spanish/English)
    8. Automatic save text clearing after timeout

Setup:
    Connect to Logic Bricks as Python controller with module 'pause_window.main'
    Required objects: Empty.Pause, Empty.Hud.Pos, Empty.Pause.Pos.Out
    Required text objects: Text.Pause.Quit, Text.Pause.Resume, Text.Pause.Save,
                           Text.Pause.Sound, Text.Pause.Language
    Required button meshes: Button.Sound.On, Button.Sound.Off,
                            Button.Lan.Es, Button.Lan.En

Configurable Variables:
    PAUSE_ROOT_NAME (str): Root empty for pause menu (default: 'Empty.Pause')
    PAUSE_POS_IN (str): Position when visible (default: 'Empty.Hud.Pos')
    PAUSE_POS_OUT (str): Position when hidden (default: 'Empty.Pause.Pos.Out')

Notes:
    - Requires game_access module for game state and language
    - Sends suspend/resume messages to 'suspend_logic' subject
    - Pause menu blocks BLF text display when active
    - Includes debounce to prevent rapid pause/unpause
    - Save confirmation text clears after 2 seconds
    - Inventory views (V1/V2) are automatically hidden when pausing

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
__description__ = "Manages pause menu window visibility, text updates, and keyboard input"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic, events
import game_access

# =============================================================================
# CONFIGURATION
# =============================================================================
PAUSE_ROOT_NAME = "Empty.Pause"
PAUSE_POS_IN = "Empty.Hud.Pos"
PAUSE_POS_OUT = "Empty.Pause.Pos.Out"

# Corrected text IDs
TEXT_IDS = {
    "quit": 8,      # "Quit game"
    "resume": 9,    # "Resume"  
    "save": 10,     # "Save"
    "sound": 11,    # "Background sound"
    "language": 12  # "Language"
}

# =============================================================================
# SUSPENSION MESSAGE SYSTEM
# =============================================================================
def _send_suspend_message(action):
    """Sends message to collection suspension system"""
    try:
        logic.sendMessage("suspend_logic", f"pause|{action}")
        logic.sendMessage("suspend_nav_chars") # Message to npc chars in NavMesh       
        print(f"[Pause] Suspension message sent: {action}")
        return True
    except Exception as e:
        print(f"[Pause] Error sending suspension message: {e}")
        return False

# =============================================================================
# POSITION MANAGEMENT
# =============================================================================
def _move_pause_to_position(scene, position_name):
    """Moves pause empty to the specified position"""
    try:
        pause_root = scene.objects.get(PAUSE_ROOT_NAME)
        target_pos = scene.objects.get(position_name)
        
        if pause_root and target_pos:
            pause_root.worldPosition = target_pos.worldPosition.copy()
            pause_root.visible = (position_name == PAUSE_POS_IN)
            return True
    except Exception as e:
        print(f"[Pause] Error moving to {position_name}: {e}")
    return False

def _show_pause_menu(scene):
    """Shows the pause menu"""
    # 1. Update state
    logic.hud_pause_open = True
    
    # 2. Send suspension message
    _send_suspend_message("suspend")
    
    # 3. Hide other open windows
    if getattr(logic, "hud_inventory_open", False):
        logic.hud_inventory_open = False
        _hide_inventory_view(scene)
    
    if getattr(logic, "hud_inventory_v2_open", False):
        logic.hud_inventory_v2_open = False
        _hide_inventory_view(scene)
    
    # 4. Hide BLF column
    logic.blf_hidden = True
    
    # 5. Move pause to visible position
    success = _move_pause_to_position(scene, PAUSE_POS_IN)
    
    if success:
        # 6. Update texts and buttons
        _update_pause_texts()
        _update_toggle_buttons()
        
        print("[Pause] Pause menu shown")
    else:
        print("[Pause] Error showing pause menu")

def _hide_pause_menu(scene):
    """Hides the pause menu"""
    # 1. Send resume message
    _send_suspend_message("resume")
    
    # 2. Move pause out of view
    _move_pause_to_position(scene, PAUSE_POS_OUT)
    
    # 3. Show BLF column if no other window is open
    if not getattr(logic, "hud_inventory_open", False) and not getattr(logic, "hud_inventory_v2_open", False):
        logic.blf_hidden = False
    
    # 4. Update state
    logic.hud_pause_open = False
    
    print("[Pause] Pause menu hidden")

def _hide_inventory_view(scene):
    """Hides the inventory view"""
    try:
        # Hide V1 and V2
        v1_root = scene.objects.get("Empty.View.1")
        v2_root = scene.objects.get("Empty.View.2")
        pos_out = scene.objects.get("Empty.Pos.Inv.Out")
        
        if v1_root and pos_out:
            v1_root.worldPosition = pos_out.worldPosition.copy()
            v1_root.visible = False
        
        if v2_root and pos_out:
            v2_root.worldPosition = pos_out.worldPosition.copy()
            v2_root.visible = False
            
    except Exception as e:
        print(f"[Pause] Error hiding inventory: {e}")

# =============================================================================
# KEYBOARD HANDLING
# =============================================================================
def _handle_pause_key():
    """Handles ESC/P key to pause/resume"""
    keyboard = logic.keyboard
    esc_input = keyboard.inputs.get(events.ESCKEY)
    p_input = keyboard.inputs.get(events.PKEY)
    
    esc_pressed = esc_input and esc_input.activated
    p_pressed = p_input and p_input.activated
    
    if not (esc_pressed or p_pressed):
        return False
    
    # Debounce
    current_time = logic.getRealTime()
    if hasattr(logic, "_last_pause_time"):
        if current_time - logic._last_pause_time < 0.3:
            return False
    
    logic._last_pause_time = current_time
    
    scene = logic.getCurrentScene()
    
    if getattr(logic, "hud_pause_open", False):
        _hide_pause_menu(scene)
    else:
        _show_pause_menu(scene)
    
    return True

# =============================================================================
# TEXT UPDATE FUNCTIONS
# =============================================================================
def _load_texts():
    """Loads texts from JSON"""
    import json
    import os
    
    lang = _get_language()
    texts_path = f"//Assets/Texts/general_text_{lang}.json"
    
    try:
        full_path = logic.expandPath(texts_path)
        if os.path.exists(full_path):
            with open(full_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"[Pause] Error loading texts: {e}")
    
    # Fallback to Spanish
    try:
        fallback_path = logic.expandPath("//Assets/Texts/general_text_es.json")
        with open(fallback_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def _get_language():
    """Gets current language using new architecture"""
    game = game_access.get_game()
    if game:
        return game.state.language
    return "es"

def _update_pause_texts():
    """Updates pause menu texts"""
    texts = _load_texts()
    info_texts = texts.get("info_text", [])
    
    scene = logic.getCurrentScene()
    
    # Corrected mapping
    text_mappings = {
        "quit": ("Text.Pause.Quit", 8),
        "resume": ("Text.Pause.Resume", 9),
        "save": ("Text.Pause.Save", 10),
        "sound": ("Text.Pause.Sound", 11),
        "language": ("Text.Pause.Language", 12)
    }
    
    for key, (obj_name, text_index) in text_mappings.items():
        if 0 <= text_index < len(info_texts):
            text_content = info_texts[text_index]
            obj = scene.objects.get(obj_name)
            if obj:
                try:
                    obj["Text"] = text_content
                except:
                    try:
                        obj.text = text_content
                    except:
                        pass

# =============================================================================
# TOGGLE BUTTONS
# =============================================================================
def _update_toggle_buttons():
    """Updates toggle buttons"""
    scene = logic.getCurrentScene()
    _update_sound_button_mesh()
    _update_language_button_mesh()

def _update_sound_button_mesh():
    """Swaps sound button mesh using new architecture"""
    scene = logic.getCurrentScene()
    
    game = game_access.get_game()
    if not game:
        return
        
    sound_enabled = game.state.sound_background
    
    # Find both buttons
    btn_on = scene.objects.get("Button.Pause.Sound.Back.On")
    btn_off = scene.objects.get("Button.Pause.Sound.Back.Off")
    
    if btn_on and btn_off:
        try:
            if sound_enabled:
                btn_on.replaceMesh("Button.Sound.On", True, True)
                btn_off.replaceMesh("Button.Sound.Off", True, True)
            else:
                btn_on.replaceMesh("Button.Sound.Off", True, True)
                btn_off.replaceMesh("Button.Sound.On", True, True)
        except Exception as e:
            print(f"[Pause] Error swapping sound meshes: {e}")

def _update_language_button_mesh():
    """Swaps language button mesh"""
    scene = logic.getCurrentScene()
    current_lang = _get_language()
    
    btn_es = scene.objects.get("Button.Pause.Lan.Es")
    btn_en = scene.objects.get("Button.Pause.Lan.En")
    
    if btn_es and btn_en:
        try:
            if current_lang == "es":
                btn_es.replaceMesh("Button.Lan.Es", True, True)
                btn_en.replaceMesh("Button.Lan.En", True, True)
            else:
                btn_es.replaceMesh("Button.Lan.En", True, True)
                btn_en.replaceMesh("Button.Lan.Es", True, True)
        except Exception as e:
            print(f"[Pause] Error swapping language meshes: {e}")

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main():
    """Main function called each frame"""
    if not hasattr(logic, "hud_pause_open"):
        logic.hud_pause_open = False
    
    # One-time initialization
    if not hasattr(logic, "_pause_initialized"):
        logic._pause_initialized = True
        # Ensure pause menu is hidden at start
        scene = logic.getCurrentScene()
        _move_pause_to_position(scene, PAUSE_POS_OUT)
        print("[Pause] System initialized")
    
    # Process input
    if not getattr(logic, "_game_completely_paused", False):
        _handle_pause_key()
    
    # Clear save text
    if hasattr(logic, "_clear_save_text_time"):
        if logic.getRealTime() > logic._clear_save_text_time:
            game = game_access.get_game()
            if game:
                game.hud_text.center_text = ""
            delattr(logic, "_clear_save_text_time")