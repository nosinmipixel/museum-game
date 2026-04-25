"""
matrix_rain_screen.py

Manages Matrix-style falling character effect for full screen display.

This script creates and manages a Matrix-inspired rain effect with falling
binary digits (0 and 1) that cascade down the screen with varying colors
(bright, medium, dim, trail) and speeds.

Main Features:
    1. Full screen column-based character rain effect
    2. Configurable number of columns (default: 100)
    3. Dynamic character generation (0 or 1) with change probability
    4. Gradient color system (bright head, dimming tail)
    5. Adjustable speed per column (1.5 to 4.0)
    6. Importable module for integration with BLF_module
    7. Independent or integrated operation modes
    8. Negative Z-index to render behind HUD

Setup:
    For integrated mode: Import and call init_matrix_effect(), then
    call draw_matrix_effect() from post_draw handler
    For standalone mode: Connect to Logic Bricks with module 'matrix_rain_screen.main'

Configurable Variables:
    NUM_COLUMNS (int): Number of character columns (default: 100)
    MIN_SPEED (float): Minimum falling speed (default: 1.5)
    MAX_SPEED (float): Maximum falling speed (default: 4.0)
    INITIAL_LENGTH (int): Initial character chain length (default: 20)
    MAX_LENGTH (int): Maximum character chain length (default: 30)
    CHANGE_PROBABILITY (float): Probability to change a character (default: 0.03)
    Z_OFFSET (int): Z-index offset (default: -10)

Notes:
    - Requires MatrixSans-Regular.ttf font in //Assets/Fonts/ folder
    - Colors are pre-configured for optimal HUD visibility
    - Uses BLF for text rendering
    - Global state stored in _matrix_state for import access
    - Can be called from BLF_module for integrated game completion effect

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
__description__ = "Manages Matrix-style falling character effect for full screen display"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
import blf
import random
import math
from bge import logic

# =============================================================================
# CONFIGURATION
# =============================================================================
FONT_PATH = bge.logic.expandPath('//Assets/Fonts/MatrixSans-Regular.ttf')

COLOR_BRIGHT = (0.0, 1.0, 0.2, 0.9)      # Bright green (more opaque to not cover HUD)
COLOR_MEDIUM = (0.0, 0.8, 0.1, 0.6)      # Medium green
COLOR_DIM = (0.0, 0.6, 0.05, 0.3)        # Dim green
COLOR_TRAIL = (0.0, 0.3, 0.02, 0.15)     # Very faint trail

NUM_COLUMNS = 100                         # More columns for full screen
MIN_SPEED = 1.5
MAX_SPEED = 4.0
INITIAL_LENGTH = 20
MAX_LENGTH = 30
CHANGE_PROBABILITY = 0.03

# Negative Z-index to render behind HUD
Z_OFFSET = -10

# Global state (for access from other modules)
_matrix_state = {
    'columns': [],
    'font_id': None,
    'initialized': False,
    'last_time': 0
}

# =============================================================================
# INITIALIZATION FUNCTIONS
# =============================================================================
def init_matrix_effect():
    """Initializes the Matrix effect (called from BLF_module)"""
    if not _matrix_state['initialized']:
        _matrix_state['font_id'] = blf.load(FONT_PATH)
        _matrix_state['columns'] = []
        _matrix_state['last_time'] = logic.getRealTime()
        _matrix_state['initialized'] = True
        print("[MATRIX] Effect initialized for import")

def create_all_matrix_columns(screen_width, screen_height):
    """Creates all columns - FULL SCREEN (no clipping)"""
    if not _matrix_state['initialized']:
        init_matrix_effect()
    
    _matrix_state['columns'] = []
    
    for col_index in range(NUM_COLUMNS):
        col_width = screen_width / NUM_COLUMNS
        x_pos = (col_index * col_width) + (col_width / 2)
        
        # Random initial distribution across full screen
        initial_y = screen_height - random.uniform(0, screen_height)
        
        column = {
            'x': x_pos,
            'current_y': initial_y,
            'min_y': 0,  # Reaches all the way down
            'speed': random.uniform(MIN_SPEED, MAX_SPEED),
            'chars': [],
            'char_timer': random.uniform(0, 0.05),
            'char_index': 0,
            'brightness': random.uniform(0.8, 1.0),
            'age': 0.0
        }
        
        # Generate initial sequence
        for _ in range(INITIAL_LENGTH):
            column['chars'].append(str(random.randint(0, 1)))
        
        _matrix_state['columns'].append(column)
    
    # Also save in logic for compatibility
    logic.matrix_columns = _matrix_state['columns']
    
    print(f"[MATRIX] Created {len(_matrix_state['columns'])} columns for full screen")

def get_columns():
    """Returns current columns (for access from BLF_module)"""
    return _matrix_state['columns']

def update_matrix_columns(dt, screen_height):
    """Updates all columns"""
    columns = _matrix_state['columns']
    if not columns:
        return
    
    for column in columns:
        # Move downward
        column['current_y'] -= column['speed'] * dt * 60
        
        # Update characters
        column['char_timer'] += dt
        if column['char_timer'] > 0.05:
            column['char_timer'] = 0
            column['char_index'] = (column['char_index'] + 1) % len(column['chars'])
            
            if random.random() < CHANGE_PROBABILITY and len(column['chars']) > 0:
                idx = random.randint(0, len(column['chars']) - 1)
                column['chars'][idx] = str(random.randint(0, 1))
            
            if random.random() < 0.01 and len(column['chars']) < MAX_LENGTH:
                column['chars'].insert(0, str(random.randint(0, 1)))
        
        # Reset when exiting bottom
        if column['current_y'] < 0:
            column['current_y'] = screen_height
            column['speed'] = random.uniform(MIN_SPEED, MAX_SPEED)

def draw_matrix_effect():
    """Draws the Matrix effect (called from BLF_module)"""
    columns = _matrix_state['columns']
    if not columns:
        return
    
    screen_width = bge.render.getWindowWidth()
    screen_height = bge.render.getWindowHeight()
    font_id = _matrix_state['font_id']
    
    # Configure font
    text_size = int(screen_height * 0.022)  # Slightly smaller
    blf.size(font_id, text_size)
    
    char_height = text_size * 1.2
    
    for column in columns:
        chars = column['chars']
        
        # Calculate how many characters are visible (all that fit)
        max_visible = int((column['current_y'] - 0) / char_height) + 10
        visible_chars = min(len(chars), max_visible)
        
        for i in range(visible_chars):
            if i >= len(chars):
                break
            
            char_y = column['current_y'] - (i * char_height)
            
            if char_y < 0 or char_y > screen_height:
                continue
            
            # Determine color
            if i == 0:
                color = COLOR_BRIGHT
                char = str(random.randint(0, 1))
            elif i == 1:
                color = COLOR_MEDIUM
                char = chars[(column['char_index'] + i) % len(chars)]
            elif i < 5:
                color = COLOR_DIM
                char = chars[(column['char_index'] + i) % len(chars)]
            else:
                color = COLOR_TRAIL
                char = chars[(column['char_index'] + i) % len(chars)]
            
            # Adjust brightness
            r, g, b, a = color
            r *= column['brightness']
            g *= column['brightness']
            b *= column['brightness']
            
            # Draw with negative Z offset (behind)
            blf.color(font_id, r, g, b, a)
            
            char_width, _ = blf.dimensions(font_id, char)
            char_x = column['x'] - (char_width / 2)
            
            blf.position(font_id, char_x, char_y, Z_OFFSET)
            blf.draw(font_id, char)

# =============================================================================
# MAIN FUNCTION FOR STANDALONE USE
# =============================================================================
def main():
    """Main function for use with Always sensor (standalone mode)"""
    try:
        # Initialize if necessary
        if not _matrix_state['initialized']:
            init_matrix_effect()
        
        screen_width = bge.render.getWindowWidth()
        screen_height = bge.render.getWindowHeight()
        
        # Create columns if they don't exist
        if not _matrix_state['columns']:
            create_all_matrix_columns(screen_width, screen_height)
        
        # Calculate delta time
        current_time = logic.getRealTime()
        dt = current_time - _matrix_state['last_time']
        _matrix_state['last_time'] = current_time
        
        # Update
        update_matrix_columns(dt, screen_height)
        
        # Register in post_draw if not registered (standalone mode)
        scene = logic.getCurrentScene()
        if not hasattr(logic, 'matrix_handler_added'):
            if not hasattr(scene, 'post_draw'):
                scene.post_draw = []
            
            # Verify not already added
            draw_func = lambda: draw_matrix_effect()
            if draw_func not in scene.post_draw:
                scene.post_draw.append(draw_func)
                logic.matrix_handler_added = True
                print("[MATRIX] Draw handler registered (standalone mode)")
        
    except Exception as e:
        print(f"[MATRIX] Error: {e}")

# If executed directly as main script
if __name__ == "__main__":
    main()