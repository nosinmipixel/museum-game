"""
intro_sequence.py

Manages the introductory sequence state machine for game startup.

This script handles the complete intro flow including language selection,
menu display, saved game detection, reset confirmation, and game loading.

Main Features:
    1. State machine for intro sequence (states 0-7)
    2. Language selection (Spanish/English) via keyboard or buttons
    3. Saved game detection and continue/reset options
    4. Information text progression with forward button/Space key
    5. Reset confirmation dialog with Accept/Cancel
    6. Background music playback during intro
    7. Curator character animation
    8. Game loading with delay and safety timeout

Setup:
    Connect to Logic Bricks as Python controller with module 'intro_sequence.main'
    Requires Game.Controller object with state and button_action properties

Configurable Variables:
    None (all configuration is handled internally)

Notes:
    - State 0: Initialization, music start
    - State 1: Title display (Spanish)
    - State 2: Title display (English) + Curator animation
    - State 3: Language selection
    - State 4: Main menu (Start/Continue/Reset)
    - State 5: Information text progression (lines 3-6)
    - State 6: Load game preparation (0.5s delay)
    - State 7: Loading in progress
    - Saved game detection only checks file existence (no data loading)
    - Sends 'load_game' message to transition to Main_Game.blend

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
__description__ = "Manages the introductory sequence state machine for game startup"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic
from bge import events
import aud
import os

# =============================================================================
# GLOBAL KEY STATE VARIABLES
# =============================================================================
_space_was_pressed = False
_key1_was_pressed = False
_key2_was_pressed = False

# =============================================================================
# KEY DETECTION FUNCTION
# =============================================================================
def check_key_press(key_code, key_was_pressed_var_name):
    """
    Function to detect a single key press.
    Returns True only on the frame the key was activated.
    """
    keyboard = logic.keyboard.inputs
    key_pressed = key_code in keyboard and keyboard[key_code].activated
    
    current_state = globals().get(key_was_pressed_var_name, False)
    
    if key_pressed and not current_state:
        globals()[key_was_pressed_var_name] = True
        return True
    elif not key_pressed:
        globals()[key_was_pressed_var_name] = False
    
    return False

# =============================================================================
# SAVE FILE FUNCTIONS (LOCAL)
# =============================================================================
def get_save_path():
    """Returns the save file path (for verification only)"""
    return logic.expandPath('//savegame.json')

def check_saved_game():
    """Checks if a saved game exists (file verification only)"""
    save_path = get_save_path()
    exists = os.path.exists(save_path)
    print(f"[intro] Checking savegame.json: {'EXISTS' if exists else 'DOES NOT EXIST'}")
    return exists

def delete_saved_game():
    """Deletes the saved game (file deletion only)"""
    try:
        save_path = get_save_path()
        if os.path.exists(save_path):
            os.remove(save_path)
            print("Save file deleted from intro")
            return True
        else:
            print("No save file to delete")
            return False
    except Exception as e:
        print(f"Error deleting save from intro: {e}")
        return False

# =============================================================================
# UI HELPER FUNCTIONS
# =============================================================================
def clear_blf_text():
    """Clears the BLF text displayed on screen"""
    try:
        # Send message to clear BLF text (empty string)
        scene = logic.getCurrentScene()
        game_controller = scene.objects.get("Game.Controller")
        if game_controller:
            game_controller.sendMessage('info_text', '')
            print("Debug: Sending empty message to clear BLF text")
    except Exception as e:
        print(f"Error clearing BLF text: {e}")

def show_buttons(scene, show_start=False, show_continue_reset=False):
    """Shows or hides buttons according to state"""
    # Hide all buttons first
    button_names = [
        'Button.Start', 'Button.Text.Start',
        'Button.Continue', 'Button.Text.Continue',
        'Button.Reset', 'Button.Text.Reset',
        'Button.Accept', 'Button.Text.Accept',
        'Button.Cancel', 'Button.Text.Cancel',
        'Button.Forward'
    ]
    
    for btn_name in button_names:
        if btn_name in scene.objects:
            btn = scene.objects[btn_name]
            btn.visible = False
            # Force Z position update
            if "_original_z" in btn:
                btn.worldPosition.z = btn["_original_z"]
                btn["_z_displaced"] = False
    
    # Show according to state
    if show_start:
        for btn_name in ['Button.Start', 'Button.Text.Start']:
            if btn_name in scene.objects:
                btn = scene.objects[btn_name]
                btn.visible = True
                # Displace Z for ray casting
                if "_original_z" in btn:
                    btn.worldPosition.z = btn["_original_z"] + 0.1
                    btn["_z_displaced"] = True
    
    if show_continue_reset:
        for btn_name in ['Button.Continue', 'Button.Text.Continue', 
                        'Button.Reset', 'Button.Text.Reset']:
            if btn_name in scene.objects:
                btn = scene.objects[btn_name]
                btn.visible = True
                # Displace Z for ray casting
                if "_original_z" in btn:
                    btn.worldPosition.z = btn["_original_z"] + 0.1
                    btn["_z_displaced"] = True

def show_confirmation_buttons(scene, show=True):
    """Shows or hides confirmation buttons"""
    for btn_name in ['Button.Accept', 'Button.Text.Accept', 
                    'Button.Cancel', 'Button.Text.Cancel']:
        if btn_name in scene.objects:
            btn = scene.objects[btn_name]
            btn.visible = show
            # Adjust Z position according to visibility
            if "_original_z" in btn:
                if show:
                    btn.worldPosition.z = btn["_original_z"] + 0.1
                    btn["_z_displaced"] = True
                else:
                    btn.worldPosition.z = btn["_original_z"]
                    btn["_z_displaced"] = False

def show_language_buttons(scene, show=True):
    """Shows or hides language selection buttons"""
    button_names = [
        'Button.Lan.En', 'Button.Text.Lan.En',
        'Button.Lan.Es', 'Button.Text.Lan.Es'
    ]
    
    for btn_name in button_names:
        if btn_name in scene.objects:
            btn = scene.objects[btn_name]
            btn.visible = show
            # Adjust Z position according to visibility
            if "_original_z" in btn:
                if show:
                    btn.worldPosition.z = btn["_original_z"] + 0.1
                    btn["_z_displaced"] = True
                else:
                    btn.worldPosition.z = btn["_original_z"]
                    btn["_z_displaced"] = False

def show_forward_button(scene, show=True):
    """Shows or hides the forward button"""
    if 'Button.Forward' in scene.objects:
        btn = scene.objects['Button.Forward']
        btn.visible = show
        # Adjust Z position according to visibility
        if "_original_z" in btn:
            if show:
                btn.worldPosition.z = btn["_original_z"] + 0.1
                btn["_z_displaced"] = True
            else:
                btn.worldPosition.z = btn["_original_z"]
                btn["_z_displaced"] = False

def update_button_texts(scene):
    """Updates button texts according to language"""
    language = logic.globalDict.get('language', 'es')
    
    # Text dictionary by language
    texts = {
        'start': {'es': 'Inicio', 'en': 'Start'},
        'continue': {'es': 'Continuar', 'en': 'Continue'},
        'reset': {'es': 'Reiniciar', 'en': 'Restart'},
        'accept': {'es': 'Aceptar', 'en': 'Accept'},
        'cancel': {'es': 'Cancelar', 'en': 'Cancel'},
        'forward': {'es': 'Continuar', 'en': 'Continue'},
        'language_es': {'es': 'Espanol', 'en': 'Spanish'},
        'language_en': {'es': 'Ingles', 'en': 'English'}
    }
    
    # Update texts if objects exist
    text_objects = {
        'Button.Text.Start': texts['start'][language],
        'Button.Text.Continue': texts['continue'][language],
        'Button.Text.Reset': texts['reset'][language],
        'Button.Text.Accept': texts['accept'][language],
        'Button.Text.Cancel': texts['cancel'][language],
        'Button.Text.Lan.Es': texts['language_es'][language],
        'Button.Text.Lan.En': texts['language_en'][language]
    }
    
    for obj_name, text in text_objects.items():
        if obj_name in scene.objects:
            text_obj = scene.objects[obj_name]
            # Assuming text object has a 'text' property
            try:
                text_obj['Text'] = text
            except:
                try:
                    text_obj.text = text
                except:
                    pass

# =============================================================================
# STATE TRANSITION HELPERS
# =============================================================================
def _advance_info_text(game_controller, scene):
    """Advances to next information text (state 5)"""
    current_line_index = game_controller.get('current_line_index', 3)
    
    print(f"Debug: _advance_info_text - Current line: {current_line_index}")
    
    # If all lines (3-6) are shown, send load signal
    if current_line_index >= 6:
        # Line 6 already shown, send load signal
        print("Debug: Last line shown, sending load signal...")
        _send_load_game_message(game_controller)
        return
    
    # Show next line
    next_line = current_line_index + 1
    game_controller.sendMessage('info_text', str(next_line))
    game_controller['current_line_index'] = next_line
    
    print(f"Debug: Showing line {next_line}.")
    
    # If we just showed line 6, prepare to load game on next click
    if next_line == 6:
        print("Debug: Last text shown. Next click will send load signal.")

def _send_load_game_message(game_controller, force=False):
    """Sends message to switch to main game"""
    if game_controller.get('game_loading_started', False) and not force:
        return  # Prevent multiple calls
    
    print("Debug: _send_load_game_message() - Sending 'load_game' message to switch to Main_Game.blend...")
    
    # Mark that loading has started
    game_controller['game_loading_started'] = True
    
    # Ensure language is in globalDict
    if 'language' not in logic.globalDict:
        logic.globalDict['language'] = 'es'  # Default value
    
    print(f"Debug: Language saved in globalDict: {logic.globalDict['language']}")
    
    # Hide all buttons
    scene = logic.getCurrentScene()
    show_buttons(scene, False, False)
    show_forward_button(scene, False)
    show_confirmation_buttons(scene, False)
    
    # Visual feedback
    language = logic.globalDict.get('language', 'es')
    if language == 'es':
        message = "Cargando juego principal..."
    else:
        message = "Loading main game..."
    
    # Send message to text system
    game_controller.sendMessage('info_text', message)
    
    # SEND THE MESSAGE THAT WILL ACTIVATE SCENE CHANGE
    # The message must match the Message sensor Subject in Game.Controller
    game_controller.sendMessage('load_game')
    
    # Change state to prevent multiple sends
    game_controller['state'] = 7  # "loading in progress" state
    
    print("Debug: 'load_game' message sent. Waiting for actuator activation...")
    print("Debug: Message sensor with Subject 'load_game' should activate:")
    print("       1. Load Main_Game.blend")
    print("       2. Actual data loading will be done in save_system.py inside Main_Game.blend")

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main():
    cont = logic.getCurrentController()
    game_controller = cont.owner
    scene = logic.getCurrentScene()
    
    # --- Game properties initialization ---
    if 'state' not in game_controller:
        game_controller['state'] = 0
    if 'prev_state' not in game_controller:
        game_controller['prev_state'] = -1
    if 'frame_counter' not in game_controller:
        game_controller['frame_counter'] = 0
    if 'curator_anim_played' not in game_controller:
        game_controller['curator_anim_played'] = False
    if 'reset_confirmation' not in game_controller:
        game_controller['reset_confirmation'] = False
    if 'current_line_index' not in game_controller:
        game_controller['current_line_index'] = 1

    state = game_controller['state']
    prev_state = game_controller['prev_state']

    # --- Enhanced key detection ---
    space_pressed = check_key_press(events.SPACEKEY, '_space_was_pressed')
    key_1_pressed = check_key_press(events.ONEKEY, '_key1_was_pressed')
    key_2_pressed = check_key_press(events.TWOKEY, '_key2_was_pressed')

    # --- State Machine ---
    if state != prev_state:
        print(f"Debug: State transition from {prev_state} to {state}.")
        game_controller['prev_state'] = state
        game_controller['frame_counter'] = 0
        
        # Initialize new state
        if state == 0:
            # Initial state - hide all buttons
            show_buttons(scene, False, False)
            show_confirmation_buttons(scene, False)
            show_language_buttons(scene, False)
            show_forward_button(scene, False)
            
        elif state == 3:
            # State 3: Show language selection text (line 2)
            print("Debug: State 3 - Showing language selection")
            
            # Configure to show line 2
            game_controller['current_line_index'] = 2  # Line 2 for language selection
            
            # Ensure language buttons are shown
            show_language_buttons(scene, True)
            
            # Hide other buttons
            show_buttons(scene, False, False)
            show_confirmation_buttons(scene, False)
            show_forward_button(scene, False)
            
            # Show text
            game_controller.sendMessage('info_text', '2')
            print("Debug: Sending message for line 2 (language selection).")
            
        elif state == 4:  # New state for main menu
            # Clear BLF text from previous state (state 3)
            clear_blf_text()
            
            # Hide language buttons
            show_language_buttons(scene, False)
            # Hide forward button
            show_forward_button(scene, False)
            
            # Check if there is a saved game (file verification only)
            has_save = check_saved_game()
            game_controller['has_saved_game'] = has_save
            
            # Update button texts according to language
            update_button_texts(scene)
            
            # Show buttons according to saved game existence
            if has_save:
                show_buttons(scene, False, True)
            else:
                show_buttons(scene, True, False)
            
            # Hide confirmation if exists
            game_controller['reset_confirmation'] = False
            show_confirmation_buttons(scene, False)
            
        elif state == 5:
            # State 5: Game information (previously state 4)
            # Show forward button to advance text
            show_forward_button(scene, True)
            # IMPORTANT: Clear any pending action when entering
            if 'button_action' in game_controller:
                del game_controller['button_action']
            print("Debug: Transition to State 5 (Game information).")
            
        elif state == 6:
            # State 6: Load game - INITIALIZATION
            # Show forward button to confirm load
            show_forward_button(scene, True)
            # IMPORTANT: Clear any pending action when entering
            if 'button_action' in game_controller:
                del game_controller['button_action']
            
            # Initialize timer for automatic load
            game_controller['load_timer'] = 0.0
            game_controller['load_delay'] = 0.5  # 0.5 second delay
            game_controller['load_triggered'] = False
            
            # Show "Loading..." message
            language = logic.globalDict.get('language', 'es')
            if language == 'es':
                loading_msg = "Preparando carga del juego..."
            else:
                loading_msg = "Preparing to load game..."
            
            # Send message to text system
            game_controller.sendMessage('info_text', loading_msg)
            
            print("Debug: Transition to State 6 (Load game). Starting load in 0.5s...")
            
        elif state == 7:
            # State 7: Loading in progress - only show message
            print("Debug: Transition to State 7 (Loading in progress)")
            # Hide all buttons
            show_buttons(scene, False, False)
            show_confirmation_buttons(scene, False)
            show_language_buttons(scene, False)
            show_forward_button(scene, False)
            
            # Initialize safety timer
            game_controller['safety_timer'] = 0.0
        
    game_controller['frame_counter'] += 1

    # --- LOGIC FOR EACH STATE ---
    if state == 0:
        if not game_controller.get('music_playing', False):
            try:
                sound_path = logic.expandPath('//Sounds/background_start_1.ogg')
                sound = aud.Sound.file(sound_path)
                game_controller['background_music_handle'] = aud.Device().play(sound.loop(-1).volume(0.5))
                game_controller['music_playing'] = True
            except Exception as e:
                print(f"Error playing sound: {e}")

        for obj_name in ['Text_Title_EN', 'Text_Title_EN_2', 'Filter_Dark']:
            if obj_name in scene.objects:
                scene.objects[obj_name].visible = False
        
        # Hide Curator initially
        if 'Curator' in scene.objects:
            scene.objects['Curator'].visible = False
        
        game_controller['frame_counter'] = 0
        game_controller['current_line_index'] = 1
        game_controller['state'] = 1
    
    elif state == 1:
        if 'Text_Title_ES' in scene.objects:
            scene.objects['Text_Title_ES'].visible = True

        if 'Text_Title_ES_2' in scene.objects:
            scene.objects['Text_Title_ES_2'].visible = True            
        
        if game_controller['frame_counter'] >= 180: # 2 seconds (60 frames/sec)
            game_controller['frame_counter'] = 0
            game_controller['state'] = 2
            
        # Make Curator object visible in state 2
        if 'Curator' in scene.objects:
            curator_obj = scene.objects['Curator']
            curator_obj.visible = True
            
            # Play animation only once
            if not game_controller['curator_anim_played']:
                try:
                    # Method 1: Use actuators if configured
                    conts = curator_obj.controllers
                    for c in conts:
                        for act in c.actuators:
                            if act.name == "CuratorAnim" or "CuratorAnim" in act.name:
                                c.activate(act)
                                print("Debug: Activating CuratorAnim animation via actuator")
                    
                    # Method 2: Use playAction
                    try:
                        curator_obj.playAction('CuratorAnim', 1, 120, layer=0, play_mode=bge.logic.KX_ACTION_MODE_PLAY)
                        curator_obj.playAction('Curator_MatAction', 1, 13, layer=1, play_mode=bge.logic.KX_ACTION_MODE_LOOP)
                        print("Debug: Playing CuratorAnim animation with playAction")
                    except:
                        print("Debug: playAction method not available")
                    
                    game_controller['curator_anim_played'] = True
                except Exception as e:
                    print(f"Error playing animation: {e}")            
    
    elif state == 2:
        # Show titles
        if 'Text_Title_ES' in scene.objects:
            scene.objects['Text_Title_ES'].visible = False
        if 'Text_Title_ES_2' in scene.objects:
            scene.objects['Text_Title_ES_2'].visible = False  
                      
        if 'Text_Title_EN' in scene.objects:
            scene.objects['Text_Title_EN'].visible = True
        if 'Text_Title_EN_2' in scene.objects:
            scene.objects['Text_Title_EN_2'].visible = True    
        
        if game_controller['frame_counter'] >= 180: # 2 seconds
            game_controller['frame_counter'] = 0
            game_controller['state'] = 3
            
            # Hide Curator when exiting state 2
            if 'Curator' in scene.objects:
                scene.objects['Curator'].visible = False
            
            if 'Text_Title_EN' in scene.objects:
                scene.objects['Text_Title_EN'].visible = False
            if 'Text_Title_EN_2' in scene.objects:
                scene.objects['Text_Title_EN_2'].visible = False
                
            if 'Filter_Dark' in scene.objects:
                scene.objects['Filter_Dark'].visible = True
            
            # Show language selection text (line 2 according to file)
            # Send message after setting index
            game_controller['current_line_index'] = 2
            game_controller.sendMessage('info_text', '2')
            print("Debug: Sending message for line 2 (language selection).")
                
    elif state == 3:
        # State 3: Language selection
        # BLF text is shown here (line 2 of file - index 1 in array)
        
        # Keyboard detection (maintain compatibility)
        if key_1_pressed:
            logic.globalDict['language'] = 'es'
            game_controller['state'] = 4  # Now goes to state 4 (new menu state)
            print("Debug: Language set to Spanish (key 1). Transition to State 4 (Menu).")
        elif key_2_pressed:
            logic.globalDict['language'] = 'en'
            game_controller['state'] = 4  # Now goes to state 4 (new menu state)
            print("Debug: Language set to English (key 2). Transition to State 4 (Menu).")
        
        # Handle language button actions (process only once)
        if 'button_action' in game_controller:
            action = game_controller['button_action']
            
            if action == 'select_es':
                logic.globalDict['language'] = 'es'
                game_controller['state'] = 4
                print("Debug: Language set to Spanish (button). Transition to State 4 (Menu).")
            elif action == 'select_en':
                logic.globalDict['language'] = 'en'
                game_controller['state'] = 4
                print("Debug: Language set to English (button). Transition to State 4 (Menu).")
            
            # CLEAR IMMEDIATELY after processing
            del game_controller['button_action']

    elif state == 4:
        # New state: Main menu with buttons
        # BLF text was already cleared during transition to this state
        # Interaction is handled in intro_buttons.py
        pass

    elif state == 5:
        # State 5: Game information (previously state 4 in original)
        # IMPORTANT: Only send message if we just entered the state
        if prev_state != 5:
            # Just entered state 5, show first line (3)
            # IMPORTANT: Ensure current_line_index is 3
            game_controller['current_line_index'] = 3
            game_controller.sendMessage('info_text', '3')
            print(f"Debug: State 5 - Showing line 3 in language: {logic.globalDict.get('language', 'es')}")
        
        # Advance with Space key
        if space_pressed:
            _advance_info_text(game_controller, scene)
        
        # Handle forward button (if pressed)
        if 'button_action' in game_controller and game_controller['button_action'] == 'forward':
            _advance_info_text(game_controller, scene)
            # CLEAR IMMEDIATELY after processing
            del game_controller['button_action']

    elif state == 6:
        # State 6: Load game - LOADING LOGIC
        # Timer for automatic load
        if not game_controller.get('load_triggered', False):
            if 'load_timer' in game_controller:
                game_controller['load_timer'] += 1/60.0  # Assuming 60 FPS
                
                if game_controller['load_timer'] >= game_controller.get('load_delay', 0.5):
                    print("Debug: Delay completed, activating automatic load...")
                    _send_load_game_message(game_controller)
                    game_controller['load_triggered'] = True
        
        # Also allow manual load with Space
        if space_pressed and not game_controller.get('load_triggered', False):
            print("Debug: Space pressed, activating manual load...")
            _send_load_game_message(game_controller)
        
        # Handle forward button
        if 'button_action' in game_controller and game_controller['button_action'] == 'forward':
            if not game_controller.get('load_triggered', False):
                print("Debug: Forward button pressed, activating load...")
                _send_load_game_message(game_controller)
            # CLEAR IMMEDIATELY after processing
            del game_controller['button_action']
    
    elif state == 7:
        # State 7: Loading in progress - only show message
        # Increment safety timer
        if 'safety_timer' in game_controller:
            game_controller['safety_timer'] += 1/60.0
        
        # If too much time passes without changing, retry
        if game_controller.get('safety_timer', 0) > 5.0:  # 5 seconds max
            print("Debug: Timeout - resending load_game message...")
            _send_load_game_message(game_controller, force=True)
            game_controller['safety_timer'] = 0.0
    
    # --- BUTTON ACTION HANDLING ---
    # First, handle actions when in confirmation mode
    if state == 4 and game_controller.get('reset_confirmation', False):
        if 'button_action' in game_controller:
            action = game_controller['button_action']
            
            if action == 'accept_reset':
                # Accept reset - delete save and start from scratch
                delete_saved_game()  # Only deletes the file
                game_controller['reset_confirmation'] = False
                game_controller['state'] = 3  # Go to language selection
                # Show language selection text (line 2)
                game_controller['current_line_index'] = 2
                game_controller.sendMessage('info_text', '2')
                show_buttons(scene, False, False)
                show_confirmation_buttons(scene, False)
                show_forward_button(scene, False)  # Hide forward button
                show_language_buttons(scene, True)  # Show language buttons
                print("Debug: Reset accepted - Transition to State 3 (language selection)")
                # CLEAR IMMEDIATELY after processing
                del game_controller['button_action']
                
            elif action == 'cancel_reset':
                # Cancel reset - return to main menu with original buttons
                game_controller['reset_confirmation'] = False
                has_save = check_saved_game()  # Check if save still exists
                if has_save:
                    show_buttons(scene, False, True)  # Show Continue and Reset
                else:
                    show_buttons(scene, True, False)  # Show only Start
                show_confirmation_buttons(scene, False)  # Hide Accept/Cancel
                show_forward_button(scene, False)  # Hide forward button
                # Clear confirmation message
                clear_blf_text()
                print("Debug: Reset cancelled - Returning to main menu")
                # CLEAR IMMEDIATELY after processing
                del game_controller['button_action']
            
            else:
                # Clear any other unhandled action
                print(f"Debug: Unhandled action in reset confirmation: {action}")
                del game_controller['button_action']
    
    # Then, handle normal main menu actions (when NOT in confirmation)
    elif state == 4 and 'button_action' in game_controller:
        action = game_controller['button_action']
        
        if action == 'start':
            # Start game from scratch - only delete existing file
            delete_saved_game()  # Ensure no old save
            game_controller['state'] = 5  # Go to game information
            game_controller['current_line_index'] = 3  # Start at line 3 (controls)
            # Message will be sent automatically when entering state 5
            show_buttons(scene, False, False)
            show_confirmation_buttons(scene, False)
            show_forward_button(scene, True)  # Show forward button
            print("Debug: Start button pressed - Transition to State 5 (line 3)")
            # CLEAR IMMEDIATELY after processing
            del game_controller['button_action']
            
        elif action == 'continue':
            # Continue saved game - only send load signal
            print("Debug: Continue button pressed - Sending load signal...")
            game_controller['state'] = 6  # Go to load state
            show_buttons(scene, False, False)
            show_confirmation_buttons(scene, False)
            show_forward_button(scene, True)  # Show forward button
            # CLEAR IMMEDIATELY after processing
            del game_controller['button_action']
                
        elif action == 'reset':
            # Show reset confirmation
            game_controller['reset_confirmation'] = True
            show_buttons(scene, False, False)
            show_confirmation_buttons(scene, True)
            show_forward_button(scene, False)  # Hide forward button
            
            # Show confirmation message
            language = logic.globalDict.get('language', 'es')
            if language == 'es':
                message = "Estas seguro? \nEsta accion borrara todo tu progreso y reiniciara el juego"
            else:
                message = "Are you sure? \nThis will delete all your progress and restart the game"
            
            # Send custom message for confirmation text
            game_controller.sendMessage('info_text', message)
            print("Debug: Showing reset confirmation message")
            # CLEAR IMMEDIATELY after processing
            del game_controller['button_action']
        
        # Other actions should not occur in state 4
        else:
            # Clear action for any other unhandled action
            print(f"Debug: Unhandled action in main menu: {action}")
            del game_controller['button_action']

def _advance_info_text(game_controller, scene):
    """Advances to the next information text (state 5)"""
    current_line_index = game_controller.get('current_line_index', 3)
    
    print(f"Debug: _advance_info_text - Current line: {current_line_index}")
    
    # If all lines (3-6) are shown, send load signal
    if current_line_index >= 6:
        # Line 6 already shown, send load signal
        print("Debug: Last line shown, sending load signal...")
        _send_load_game_message(game_controller)
        return
    
    # Show the next line
    next_line = current_line_index + 1
    game_controller.sendMessage('info_text', str(next_line))
    game_controller['current_line_index'] = next_line
    
    print(f"Debug: Showing line {next_line}.")
    
    # If we just showed line 6, prepare to load game on next click
    if next_line == 6:
        print("Debug: Last text shown. Next click will send load signal.")

def _send_load_game_message(game_controller, force=False):
    """Sends the message to switch to the main game"""
    if game_controller.get('game_loading_started', False) and not force:
        return  # Prevent multiple calls
    
    print("Debug: _send_load_game_message() - Sending 'load_game' message to switch to Main_Game.blend...")
    
    # Mark that loading has started
    game_controller['game_loading_started'] = True
    
    # Ensure language is in globalDict
    if 'language' not in logic.globalDict:
        logic.globalDict['language'] = 'es'  # Default value
    
    print(f"Debug: Language saved in globalDict: {logic.globalDict['language']}")
    
    # Hide all buttons
    scene = logic.getCurrentScene()
    show_buttons(scene, False, False)
    show_forward_button(scene, False)
    show_confirmation_buttons(scene, False)
    
    # Visual feedback
    language = logic.globalDict.get('language', 'es')
    if language == 'es':
        message = "Cargando juego principal..."
    else:
        message = "Loading main game..."
    
    # Send message to text system
    game_controller.sendMessage('info_text', message)
    
    # SEND THE MESSAGE THAT WILL ACTIVATE THE SCENE CHANGE
    # The message must match the Subject of the Message sensor in Game.Controller
    game_controller.sendMessage('load_game')
    
    # Change state to prevent multiple sends
    game_controller['state'] = 7  # "loading in progress" state
    
    print("Debug: 'load_game' message sent. Waiting for actuator activation...")
    print("Debug: The Message sensor with Subject 'load_game' should activate:")
    print("       1. Load Main_Game.blend")
    print("       2. The actual data loading will be done in save_system.py inside Main_Game.blend")