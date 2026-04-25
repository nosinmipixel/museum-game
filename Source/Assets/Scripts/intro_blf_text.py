"""
intro_blf_text.py

Manages introductory text display using BLF with file and custom message support.

This script handles text display for introductory screens, loading text from
language-specific files, supporting custom messages, and providing line-by-line
navigation with 1-indexed line numbers.

Main Features:
    1. Load text from language-specific files (info_1_text_{lang}.txt)
    2. Display custom messages (e.g., confirmation dialogs)
    3. Line-by-line text navigation with 1-indexed line numbers
    4. Auto-wrap text to fit screen width
    5. Center text positioning with proper line spacing
    6. Message sensor support for line selection and clearing
    7. One-time BLF draw handler registration

Setup:
    Connect to Logic Bricks as Python controller with module 'intro_blf_text.main'
    Optional: Connect init(cont) for initialization only
    Requires message sensor named 'message_info_text'

Configurable Variables:
    font_path (str): Path to font file (default: '//Fonts/MatrixSans-Regular.ttf')
    font_size (int): Dynamic font size (screen_height * 0.035)
    line_spacing (int): Dynamic line spacing (screen_height * 0.04)
    max_width_px (int): Dynamic max width (screen_width * 0.8)

Notes:
    - Text files should be named 'info_1_text_{lang}.txt' in //Texts/ folder
    - Line numbers are 1-indexed (line 1 typically clears the display)
    - Message 'clear_info_text' hides the text
    - Numeric messages set the line number to display
    - Non-numeric messages are treated as custom text
    - BLF draw handler is registered once and persists

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
__description__ = "Manages introductory text display using BLF with file and custom message support"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
import blf
import os

# =============================================================================
# BLF CONFIGURATION (Executed only once)
# =============================================================================
font_path = bge.logic.expandPath('//Fonts/MatrixSans-Regular.ttf')
blf_font_id = blf.load(font_path)

# =============================================================================
# STATE VARIABLES
# =============================================================================
show_text = True
custom_message = None
current_text_source = 'file'  # 'file' or 'custom'

# =============================================================================
# TEXT LOADING FUNCTIONS
# =============================================================================
def load_text_lines(file_name):
    """
    Loads text from a file and splits it into lines.
    Returns a list where each element is a line from the file.
    """
    try:
        file_path = bge.logic.expandPath(f"//Texts/{file_name}")
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read().split('\n')
    except Exception as e:
        print(f"Error loading text file: {e}")
        return [f"Error: File '{file_name}' not found."]

def wrap_and_split_line(line, font_id, max_width_px, font_size):
    """
    Splits a single line of text into multiple lines for drawing,
    respecting maximum width and manual line breaks ('\n').
    """
    lines = []
    
    if not line:
        return [""]
    
    # First, replace literal '\n' with actual newline character
    formatted_line = line.replace('\\n', '\n')
    
    # Now split the line by newline character
    segments = formatted_line.split('\n')
    
    for segment in segments:
        if not segment.strip():
            lines.append("")
            continue
        
        words = segment.split(' ')
        current_sub_line = ""

        for word in words:
            test_line = current_sub_line + word + " "
            blf.size(font_id, font_size)
            line_width, _ = blf.dimensions(blf_font_id, test_line)

            if line_width <= max_width_px:
                current_sub_line = test_line
            else:
                lines.append(current_sub_line.strip())
                current_sub_line = word + " "
        
        lines.append(current_sub_line.strip())

    return lines

# =============================================================================
# DRAW FUNCTION
# =============================================================================
def draw_info_text():
    """
    Draws specific text line on screen with appropriate formatting.
    """
    global show_text, custom_message, current_text_source
    
    if not show_text:
        return
    
    scene = bge.logic.getCurrentScene()
    game_controller = scene.objects.get('Game.Controller')
    
    if not game_controller:
        return
    
    # --- Drawing Preparation ---
    screen_width = bge.render.getWindowWidth()
    screen_height = bge.render.getWindowHeight()
    font_size = int(screen_height * 0.035)
    line_spacing = int(screen_height * 0.04)
    max_width_px = screen_width * 0.8
    
    # Determine which text to display
    text_to_display = ""
    
    if current_text_source == 'custom' and custom_message is not None:
        # Show custom message (for reset confirmation)
        text_to_display = custom_message
    elif current_text_source == 'file':
        # Show text from file according to current line
        original_lines = game_controller.get('info_lines', [])
        
        if not original_lines:
            return
        
        # Get current line index (1-indexed in system)
        current_line_index = game_controller.get('current_line_index', 1)
        
        # Convert to 0-indexed for array
        array_index = current_line_index - 1
        
        # Check bounds
        if array_index < 0 or array_index >= len(original_lines):
            return
            
        text_to_display = original_lines[array_index]
    else:
        return

    # If text is empty, don't draw anything (screen clearing)
    if not text_to_display.strip():
        show_text = False
        return

    # Split text into lines for drawing
    lines_to_draw = wrap_and_split_line(text_to_display, blf_font_id, max_width_px, font_size)

    blf.size(blf_font_id, font_size)
    blf.color(blf_font_id, 1.0, 1.0, 1.0, 1.0)
    
    total_height = len(lines_to_draw) * line_spacing
    start_y = (screen_height / 2) + (total_height / 2) - line_spacing
    
    for i, line in enumerate(lines_to_draw):
        line_width, _ = blf.dimensions(blf_font_id, line)
        
        pos_x = (screen_width / 2) - (line_width / 2)
        pos_y = start_y - (line_spacing * i)
        
        blf.position(blf_font_id, pos_x, pos_y, 0)
        blf.draw(blf_font_id, line)

# =============================================================================
# TEXT UPDATE FUNCTION
# =============================================================================
def update_text():
    """
    Function to load text from correct language file.
    """
    global custom_message, show_text, current_text_source
    
    cont = bge.logic.getCurrentController()
    game_controller = cont.owner
    
    # Check if we have a custom message (for confirmation)
    message_sensor = cont.sensors.get('message_info_text')
    
    if message_sensor and message_sensor.positive:
        for message in message_sensor.bodies:
            if message == 'clear_info_text':
                # Clear text - hide
                show_text = False
                custom_message = None
                current_text_source = 'file'
                return
            elif message.isdigit():
                # It's a line number from file (1-indexed)
                line_number = int(message)
                show_text = True
                custom_message = None
                current_text_source = 'file'
                
                # Save current index (1-indexed)
                game_controller['current_line_index'] = line_number
                
                # Get current language
                language = bge.logic.globalDict.get('language', 'es')
                file_name = f"info_1_text_{language}.txt"
                
                # Always load file to ensure correct language
                game_controller['info_lines'] = load_text_lines(file_name)
                
                # If line is 1 (empty), hide text
                if line_number == 1:
                    show_text = False
            else:
                # It's a custom message (for reset confirmation)
                show_text = True
                custom_message = message
                current_text_source = 'custom'

# =============================================================================
# MAIN ENTRY POINT
# =============================================================================
def main():
    # Ensure draw handler is configured only once
    if not hasattr(bge.logic, 'blf_handler_initialized'):
        bge.logic.blf_handler_initialized = True
        scene = bge.logic.getCurrentScene()
        scene.post_draw = [draw_info_text]
        print("BLF Draw Handler initialized")
    
    # Update text if message received
    update_text()

# =============================================================================
# OPTIONAL INITIALIZATION FUNCTION
# =============================================================================
def init(cont):
    """Optional handler initialization"""
    global show_text
    show_text = False  # Initially hidden
    print("BLF Text Handler initialized")