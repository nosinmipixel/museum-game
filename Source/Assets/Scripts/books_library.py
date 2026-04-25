"""
books_library.py

Manages book content loading, pagination, and display with fixed text box height.

This script handles loading book data from JSON files, paginating text content
with fixed line limits, displaying book images, and managing book opening/closing
through the BookManager class.

Main Features:
    1. Load book data from JSON files with language support
    2. Paginate text with fixed maximum lines per page and character width
    3. Display book images per page with dynamic positioning
    4. BookManager class for state management (open/close, page navigation)
    5. Texture switching for book highlight/normal states
    6. HUD text integration with game_access architecture
    7. Background music context switching for library environment

Setup:
    Connect to Logic Bricks as Python controller with module 'books_library.main'
    or call 'books_library.init()' for initialization

Configurable Variables:
    BASE_TEXT_PATH (str): Path to JSON book files (default: '//Assets/Texts/')
    FALLBACK_LANG (str): Fallback language if current not available (default: 'es')
    MAX_LINES_PER_PAGE (int): Maximum lines per page (default: 18)
    MAX_WIDTH_CHARS (int): Maximum characters per line (default: 72)
    LINE_HEIGHT (float): Line height factor (default: 1.2)
    HUD_MAIN (str): Main HUD object name (default: 'Empty.Book.Main')
    HUD_POS_IN (str): Target position when HUD is visible (default: 'Empty.Hud.Pos')
    HUD_POS_OUT (str): Target position when HUD is hidden (default: 'Empty.Book.Pos.Out')
    IMAGE_OBJECTS_IN (str): Target position for visible images (default: 'Empty.Book.Image.In')
    IMAGE_OBJECTS_OUT (str): Target position for hidden images (default: 'Empty.Book.Image.Out')
    TEXTURE_NORMAL (str): Path to normal book texture (default: '//Assets/Textures/Book_Black.png')
    TEXTURE_HIGHLIGHT (str): Path to highlighted book texture (default: '//Assets/Textures/Book_White.png')
    TEXTURE_NODE_NAME (str): Name of texture node in material (default: 'Texture.Book')
    MATERIAL_SLOT (int): Material slot index (default: 0)

Notes:
    - Requires JSON files named 'books_library_{lang}.json' in BASE_TEXT_PATH
    - JSON structure requires fields: book_id, book_type, Título, Contenido
    - Book images should be named 'Book.image.{book_type}.{page_number}'
    - Compatible with new game_data.py / init_game.py architecture
    - Uses BLF module for text rendering with fixed height constraint

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
__description__ = "Manages book content loading, pagination, and display"

# =============================================================================
# IMPORTS
# =============================================================================
import os
import json
import bge
from bge import logic
import time

# NOTE: info_queue is imported in the section below with other optional imports

# =============================================================================
# DEBUG CONFIGURATION
# =============================================================================
_DEBUG_MODE = False  # Global variable to control debug messages

def set_debug_mode(enabled):
    """Activates or deactivates debug messages"""
    global _DEBUG_MODE
    _DEBUG_MODE = enabled

def debug_print(*args, **kwargs):
    """Prints messages only if debug mode is enabled"""
    if _DEBUG_MODE:
        print("[books_library]", *args, **kwargs)

# =============================================================================
# CONFIGURATION
# =============================================================================
BASE_TEXT_PATH = "//Assets/Texts/"
FALLBACK_LANG = "es"

# Pagination configuration WITH FIXED HEIGHT
MAX_LINES_PER_PAGE = 18  # Reduced for better fit (was 18)
MAX_WIDTH_CHARS = 72     # Reduced for margins
LINE_HEIGHT = 1.2        # Line height factor

# HUD objects
HUD_MAIN = "Empty.Book.Main"
HUD_POS_IN = "Empty.Hud.Pos"
HUD_POS_OUT = "Empty.Book.Pos.Out"

# Image configuration
IMAGE_OBJECTS_IN = "Empty.Book.Image.In"
IMAGE_OBJECTS_OUT = "Empty.Book.Image.Out"

# Material and texture configuration - DYNAMIC DETECTION
TEXTURE_NORMAL = "//Assets/Textures/Book_Black.png"
TEXTURE_HIGHLIGHT = "//Assets/Textures/Book_White.png"
TEXTURE_NODE_NAME = "Texture.Book"
MATERIAL_SLOT = 0  # Slot where the material is located

# Import game_access for new architecture
try:
    import game_access
    HAS_GAME_ACCESS = True
except ImportError:
    HAS_GAME_ACCESS = False

# Import info_queue for non-interruptible info messages
try:
    import info_queue
    HAS_INFO_QUEUE = True
except ImportError:
    HAS_INFO_QUEUE = False

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def _lang():
    """Gets the current language according to the new architecture"""
    try:
        if HAS_GAME_ACCESS:
            game = game_access.get_game()
            if game:
                return game.state.language
    except Exception:
        pass
    
    # Fallback for compatibility
    try:
        return logic.game_state.language
    except Exception:
        return FALLBACK_LANG

def _abs(rel):
    if not rel.startswith("//"): 
        rel = "//" + rel
    return logic.expandPath(rel)

# =============================================================================
# PAGINATION SYSTEM WITH FIXED HEIGHT
# =============================================================================
def _wrap_text_with_height_limit(text, max_width_chars=MAX_WIDTH_CHARS, max_lines=MAX_LINES_PER_PAGE):
    """Splits text into lines that fit within maximum width and height"""
    if not text:
        return []
    
    lines = []
    paragraphs = text.replace('\\n', '\n').split('\n')
    
    for paragraph in paragraphs:
        if not paragraph.strip():
            if len(lines) < max_lines:
                lines.append("")
            continue
            
        words = paragraph.split(" ")
        current_line = ""
        
        for word in words:
            test_line = current_line + word + " "
            
            # Check if we exceed maximum width
            if len(test_line.strip()) <= max_width_chars:
                current_line = test_line
            else:
                # Line complete, add if space available
                if current_line and len(lines) < max_lines:
                    lines.append(current_line.strip())
                    current_line = word + " "
                elif len(lines) >= max_lines:
                    # No more space, truncate with "..."
                    if lines:
                        last_line = lines[-1]
                        if len(last_line) > max_width_chars - 3:
                            lines[-1] = last_line[:max_width_chars-3] + "..."
                        else:
                            lines[-1] = last_line + "..."
                    return lines
        
        # Add last line of paragraph if space available
        if current_line and len(lines) < max_lines:
            lines.append(current_line.strip())
        elif len(lines) >= max_lines:
            # No space, truncate
            if lines:
                last_line = lines[-1]
                if len(last_line) > max_width_chars - 3:
                    lines[-1] = last_line[:max_width_chars-3] + "..."
                else:
                    lines[-1] = last_line + "..."
            return lines
    
    return lines

def _paginate_text_with_height(text, max_lines_per_page=MAX_LINES_PER_PAGE, max_width_chars=MAX_WIDTH_CHARS):
    """Splits text into pages respecting height limit"""
    all_lines = _wrap_text_with_height_limit(text, max_width_chars, max_lines_per_page * 100)  # Large initial height
    
    pages = []
    current_page = []
    
    for line in all_lines:
        if len(current_page) >= max_lines_per_page:
            pages.append(current_page)
            current_page = []
        
        # If line is empty and we're near the limit, start new page
        if not line.strip() and len(current_page) >= max_lines_per_page - 2:
            pages.append(current_page)
            current_page = [line]
        else:
            current_page.append(line)
    
    if current_page:
        # Ensure last page does not exceed limit
        if len(current_page) > max_lines_per_page:
            # Split last page if too long
            pages.append(current_page[:max_lines_per_page])
            remaining = current_page[max_lines_per_page:]
            if remaining:
                pages.append(remaining)
        else:
            pages.append(current_page)
    
    return pages

def _paginate_text(text, max_lines_per_page=MAX_LINES_PER_PAGE):
    """Wrapper for compatibility"""
    return _paginate_text_with_height(text, max_lines_per_page)

def _get_child_object(own):
    """Gets the first child object"""
    try:
        if own.children and len(own.children) > 0:
            return own.children[0]
    except Exception as e:
        debug_print("Error getting child:", e)
    return None

def _get_material_name(own):
    """Gets the name of the material assigned to the child object"""
    try:
        child = _get_child_object(own)
        if not child:
            return None
        
        import bpy
        blender_child = child.blenderObject
        
        if not blender_child.data.materials:
            return None
        
        if MATERIAL_SLOT >= len(blender_child.data.materials):
            return None
        
        current_material = blender_child.data.materials[MATERIAL_SLOT]
        if current_material:
            return current_material.name
        
    except Exception as e:
        debug_print(f"Error getting material name: {e}")
    
    return None

# =============================================================================
# TEXTURE SYSTEM WITH DYNAMIC DETECTION
# =============================================================================
def change_texture(cont, texture_path):
    """Changes the texture of the book's material (UPBGE 0.44 compatible)
       AUTOMATICALLY DETECTS MATERIAL BY NAME"""
    try:
        own = cont.owner
        child = _get_child_object(own)
        if not child:
            return False
        
        # 1. Get the name of the material assigned to the child
        import bpy
        blender_child = child.blenderObject
        
        # Check if there are materials in the slot
        if not blender_child.data.materials:
            debug_print(f"The child object has no materials assigned")
            return False
        
        # Get current material from slot 0
        if MATERIAL_SLOT >= len(blender_child.data.materials):
            debug_print(f"No material in slot {MATERIAL_SLOT}")
            return False
        
        # Get reference to current material
        current_material = blender_child.data.materials[MATERIAL_SLOT]
        if not current_material:
            debug_print(f"Material in slot {MATERIAL_SLOT} is None")
            return False
        
        material_name = current_material.name
        if _DEBUG_MODE:
            debug_print(f"Material detected: {material_name}")
        
        # Check if material starts with 'Book'
        if not material_name.startswith("Book"):
            debug_print(f"Warning: Material '{material_name}' does not start with 'Book'")
            # Still try to change texture
        
        # 2. Get material using bpy
        mat = bpy.data.materials.get(material_name)
        if not mat:
            debug_print(f"Material not found in bpy.data.materials: {material_name}")
            return False
        
        # 3. Ensure nodes are enabled
        if not mat.use_nodes:
            mat.use_nodes = True
            if _DEBUG_MODE:
                debug_print(f"Nodes enabled for material: {material_name}")
        
        # 4. Get material nodes
        nodes = mat.node_tree.nodes
        
        # 5. Find or create texture node
        texture_node = None
        
        # First search by exact name
        texture_node = nodes.get(TEXTURE_NODE_NAME)
        
        # If not exists, search for any image node
        if not texture_node:
            for node in nodes:
                if node.type == 'TEX_IMAGE':
                    texture_node = node
                    # Update name for future reference
                    texture_node.name = TEXTURE_NODE_NAME
                    texture_node.label = TEXTURE_NODE_NAME
                    if _DEBUG_MODE:
                        debug_print(f"Texture node found by type: {node.name}")
                    break
        
        # If still not exists, create a new one
        if not texture_node:
            texture_node = nodes.new(type='ShaderNodeTexImage')
            texture_node.name = TEXTURE_NODE_NAME
            texture_node.label = TEXTURE_NODE_NAME
            if _DEBUG_MODE:
                debug_print(f"Texture node created in material: {material_name}")
        
        # 6. Load and assign new texture
        try:
            # Use relative path
            if not texture_path.startswith("//"):
                texture_path = "//" + texture_path
            
            # Load image (check_existing=True to avoid reloading)
            image = bpy.data.images.load(texture_path, check_existing=True)
            texture_node.image = image
            if _DEBUG_MODE:
                debug_print(f"Texture changed in '{material_name}': {texture_path}")
            return True
            
        except Exception as e:
            debug_print(f"Error loading texture {texture_path}: {e}")
            return False
            
    except Exception as e:
        debug_print(f"Error in change_texture: {e}")
        return False

def _load_books_data():
    """Loads book data from JSON file"""
    lang = _lang()
    cache_key = f"_books_cache_{lang}"
    
    if hasattr(logic, cache_key):
        return getattr(logic, cache_key)
    
    tried = []
    for cand in (lang, FALLBACK_LANG):
        fname = f"books_library_{cand}.json"
        path = _abs(BASE_TEXT_PATH + fname)
        tried.append(path)
        
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                setattr(logic, cache_key, data)
                return data
            except Exception as e:
                debug_print(f"Error reading {path}: {e}")
    
    default_data = []
    setattr(logic, cache_key, default_data)
    return default_data

def _change_child_texture(own, cont, texture_path):
    """Changes texture in the CHILD object's material"""
    try:
        # Call global change_texture function
        success = change_texture(cont, texture_path)
        if success and _DEBUG_MODE:
            material_name = _get_material_name(own)
            debug_print(f"Texture changed successfully in '{material_name}': {texture_path}")
        return success
    except Exception as e:
        debug_print(f"Error in _change_child_texture: {e}")
        return False

def _get_book_data(book_id, book_type):
    """Gets data for a specific book"""
    books_data = _load_books_data()
    
    try:
        book_id = int(book_id)
    except (ValueError, TypeError):
        return None
    
    for book in books_data:
        book_data_id = book.get("book_id")
        book_data_type = book.get("book_type", "")
        
        try:
            book_data_id = int(book_data_id)
        except (ValueError, TypeError):
            continue
            
        if book_data_id == book_id and book_data_type == book_type:
            return book
    
    return None

def _move_to_position(object_name, target_name):
    """Moves an object to the position of another object"""
    scene = logic.getCurrentScene()
    obj = scene.objects.get(object_name)
    target = scene.objects.get(target_name)
    
    if obj and target:
        if _DEBUG_MODE:
            debug_print(f"Moving {object_name} to {target_name}")
        obj.worldPosition = target.worldPosition.copy()
        obj.worldOrientation = target.worldOrientation.copy()
        if _DEBUG_MODE:
            debug_print(f"Success: {object_name} moved to {target_name}")
        return True
    else:
        debug_print(f"Failed to move {object_name}")
        return False

def _show_book_hud():
    """Shows the book HUD interface - Moves to Empty.Hud.Pos"""
    return _move_to_position(HUD_MAIN, HUD_POS_IN)

def _hide_book_hud():
    """Hides the book HUD interface - Moves to Empty.Book.Pos.Out"""
    return _move_to_position(HUD_MAIN, HUD_POS_OUT)

def send_message(cont):
    own = cont.owner
    debug_print(f"Sending message 'lock_background' to Lock.Main.Scene")
    
    # Simple format - only what's needed
    bge.logic.sendMessage("lock_background", "lock_background", "Lock.Main.Scene")
    debug_print("Message sent successfully")
    return True  

# =============================================================================
# INFORMATION SYSTEM
# =============================================================================
# Duration for book title display (seconds) - balance between readable and responsive
# This is a "grace period" after mouse exit before clearing the text
BOOK_TITLE_DURATION = 1.5

def _set_info_text_immediate(text):
    """Sets info text immediately to HUD (low-level)"""
    try:
        if HAS_GAME_ACCESS:
            game = game_access.get_game()
            if game and hasattr(game, 'hud_text'):
                game.hud_text.info_text = text
                return True
        else:
            scene = logic.getCurrentScene()
            game_controller = scene.objects.get("Game.Controller")
            if game_controller:
                hud_text = game_controller.get("hud_text", None)
                if hud_text:
                    hud_text.info_text = text
                    return True
    except Exception as e:
        debug_print("Error setting info text:", e)
    return False

def _set_info_text(text):
    """
    Sets information text in HUD with smart display management.
    The text is shown immediately and will persist for at least BOOK_TITLE_DURATION
    seconds, even if mouse exits (grace period for reading).
    """
    if not text:
        return False

    # Store the current text globally for tracking
    logic._current_book_title = text
    logic._book_title_show_time = time.time()

    # Set text immediately
    success = _set_info_text_immediate(text)

    if _DEBUG_MODE and success:
        debug_print(f"Info text set: '{text}' (will persist for {BOOK_TITLE_DURATION}s)")

    return success

def _clear_info_text():
    """
    Clears information text in HUD.
    NOTE: With the grace period system, this only clears if enough time has passed.
    """
    # Check if we should respect the grace period
    show_time = getattr(logic, '_book_title_show_time', 0)
    current_time = time.time()
    elapsed = current_time - show_time

    # Only clear if grace period has elapsed
    if elapsed >= BOOK_TITLE_DURATION:
        _set_info_text_immediate("")
        if _DEBUG_MODE:
            debug_print(f"Info text cleared after {elapsed:.1f}s")
        return True
    else:
        # Still in grace period, don't clear yet
        remaining = BOOK_TITLE_DURATION - elapsed
        if _DEBUG_MODE:
            debug_print(f"Grace period active: {remaining:.1f}s remaining, not clearing yet")
        return False

def _force_clear_info_text():
    """Force immediate clear (used when opening a book)"""
    _set_info_text_immediate("")
    logic._current_book_title = None
    logic._book_title_show_time = 0
    if _DEBUG_MODE:
        debug_print("Info text force cleared")

def _update_book_display():
    """Updates the book text display"""
    if not logic.book_manager.is_open:
        return
    
    page_text = logic.book_manager.get_current_page_text()
    page_info = logic.book_manager.get_page_info()
    
    try:
        if HAS_GAME_ACCESS:
            game = game_access.get_game()
            if game and hasattr(game, 'hud_text'):
                game.hud_text.book_text = page_text
                game.hud_text.info_text = f"Page {page_info}"
                if _DEBUG_MODE:
                    debug_print(f"Text updated: Page {page_info} ({len(page_text.split(chr(10)))} lines)")
        else:
            scene = logic.getCurrentScene()
            game_controller = scene.objects.get("Game.Controller")
            if game_controller:
                hud_text = game_controller.get("hud_text", None)
                if hud_text:
                    hud_text.book_text = page_text
                    hud_text.info_text = f"Page {page_info}"
                    if _DEBUG_MODE:
                        debug_print(f"Text updated: Page {page_info}")
                
    except Exception as e:
        debug_print("Error updating display:", e)

# =============================================================================
# BOOK MANAGER CLASS
# =============================================================================
class BookManager:
    """Manages the state of opened books"""
    
    def __init__(self):
        self.current_book = None
        self.current_page = 0
        self.total_pages = 0
        self.pages = []
        self.is_open = False
        self.current_book_type = ""
        self.book_opening_time = 0
    
    def open_book(self, book_id, book_type):
        """Opens a book - RETURNS WHETHER OPENING WAS SUCCESSFUL"""
        if logic.globalDict.get("book_closing", False):
            debug_print("Opening book blocked - closing in progress")
            return False
        
        # Prevent rapid double click
        current_time = time.time()
        if current_time - self.book_opening_time < 0.3:
            debug_print("Double click detected - ignoring")
            return False
        
        self.book_opening_time = current_time
        
        book_data = _get_book_data(book_id, book_type)
        if not book_data:
            debug_print(f"Data not found for book id={book_id}, type={book_type}")
            return False
        
        self.current_book = book_data
        self.current_page = 0
        self.current_book_type = book_type
        
        title = book_data.get("Título", "Untitled")
        content = book_data.get("Contenido", "")
        full_text = f"{title}\n\n{content}"
        
        # Use new pagination system with fixed height
        self.pages = _paginate_text_with_height(full_text, MAX_LINES_PER_PAGE, MAX_WIDTH_CHARS)
        self.total_pages = len(self.pages)
        self.is_open = True
        
        debug_print(f"Book opened: '{title}' - {self.total_pages} pages, type: {book_type}")
        debug_print(f"   * Maximum: {MAX_LINES_PER_PAGE} lines per page")
        debug_print(f"   * Maximum width: {MAX_WIDTH_CHARS} characters")
        
        # Verify lines per page for debug
        for i, page in enumerate(self.pages):
            if _DEBUG_MODE:
                debug_print(f"   * Page {i+1}: {len(page)} lines")
                if len(page) > MAX_LINES_PER_PAGE:
                    debug_print(f"     WARNING: Page {i+1} has {len(page)} lines (max: {MAX_LINES_PER_PAGE})")
        
        # Count available images
        scene = logic.getCurrentScene()
        image_count = 0
        for obj in scene.objects:
            if obj.name.startswith(f"Book.image.{book_type}."):
                image_count += 1
        
        if _DEBUG_MODE:
            debug_print(f"Images available for {book_type}: {image_count}")
        
        # Switch to library music
        try:
            from sound_background import push_background_context
            push_background_context("library")
            if _DEBUG_MODE:
                debug_print("Library music activated")
        except ImportError:
            pass
        
        return True
    
    def close_book(self):
        """Closes the current book"""
        if _DEBUG_MODE:
            debug_print("Starting book closing...")
        
        # Play click sound
        bge.logic.sendMessage("sound_fx.play", "sound_fx.play|mouse-click.ogg")    
        
        # Clear HUD text
        self._clear_hud_text()
        
        # Hide all images
        self._hide_all_images()
        
        # Reset internal state
        self.current_book = None
        self.current_page = 0
        self.total_pages = 0
        self.pages = []
        self.current_book_type = ""
        self.is_open = False
        
        if _DEBUG_MODE:
            debug_print("Book closed completely")
        
        # Return to previous music
        try:
            from sound_background import pop_background_context
            pop_background_context()
            if _DEBUG_MODE:
                debug_print("Returning to previous music")
        except ImportError:
            pass
        
        # Hide HUD
        _hide_book_hud()

    def _clear_hud_text(self):
        """Clears book text from HUD"""
        try:
            if HAS_GAME_ACCESS:
                game = game_access.get_game()
                if game and hasattr(game, 'hud_text'):
                    game.hud_text.book_text = ""
                    game.hud_text.info_text = ""
                    if _DEBUG_MODE:
                        debug_print("HUD text cleared")
            else:
                scene = logic.getCurrentScene()
                game_controller = scene.objects.get("Game.Controller")
                if game_controller:
                    hud_text = game_controller.get("hud_text", None)
                    if hud_text:
                        hud_text.book_text = ""
                        hud_text.info_text = ""
                        if _DEBUG_MODE:
                            debug_print("HUD text cleared")
        except Exception as e:
            debug_print("Error clearing HUD text:", e)

    def next_page(self):
        """Advances to the next page"""
        if self.is_open and self.current_page < self.total_pages - 1:
            self.current_page += 1
            if _DEBUG_MODE:
                debug_print(f"Advancing to page {self.current_page + 1}/{self.total_pages}")
            self._update_image_display()
            return True
        else:
            if _DEBUG_MODE:
                debug_print(f"Cannot advance: page {self.current_page + 1}/{self.total_pages}")
            return False
    
    def prev_page(self):
        """Goes back to the previous page"""
        if self.is_open and self.current_page > 0:
            self.current_page -= 1
            if _DEBUG_MODE:
                debug_print(f"Going back to page {self.current_page + 1}/{self.total_pages}")
            self._update_image_display()
            return True
        else:
            if _DEBUG_MODE:
                debug_print(f"Cannot go back: page {self.current_page + 1}/{self.total_pages}")
            return False
    
    def get_current_page_text(self):
        """Gets the text of the current page"""
        if not self.is_open or not self.pages or self.current_page >= len(self.pages):
            return ""
        
        # Ensure we don't exceed maximum lines
        page_lines = self.pages[self.current_page]
        if len(page_lines) > MAX_LINES_PER_PAGE:
            page_lines = page_lines[:MAX_LINES_PER_PAGE]
            if _DEBUG_MODE:
                debug_print(f"Page {self.current_page + 1} truncated to {MAX_LINES_PER_PAGE} lines")
        
        return "\n".join(page_lines)
    
    def get_page_info(self):
        """Gets information about the current page"""
        if not self.is_open:
            return "0/0"
        return f"{self.current_page + 1}/{self.total_pages}"
    
    def _update_image_display(self):
        """Shows the image corresponding to the current page"""
        if not self.current_book_type:
            if _DEBUG_MODE:
                debug_print("No current book type")
            return
        
        scene = logic.getCurrentScene()
        
        show_marker = None
        main_hud = scene.objects.get(HUD_MAIN)
        if main_hud:
            for child in main_hud.childrenRecursive:
                if child.name == IMAGE_OBJECTS_IN or "Image" in child.name:
                    show_marker = child
                    break
        
        if not show_marker:
            show_marker = scene.objects.get(IMAGE_OBJECTS_IN)
        
        if not show_marker:
            debug_print(f"Image marker not found: {IMAGE_OBJECTS_IN}")
            return
        
        show_pos = show_marker.worldPosition.copy()
        show_orient = show_marker.worldOrientation.copy()
        
        hide_pos = scene.objects.get(IMAGE_OBJECTS_OUT)
        if hide_pos:
            for obj in scene.objects:
                if obj.name.startswith("Book.image."):
                    obj.worldPosition = hide_pos.worldPosition.copy()
                    obj.worldOrientation = hide_pos.worldOrientation.copy()
                    obj.visible = False
        
        if _DEBUG_MODE:
            debug_print(f"Looking for image: {self.current_book_type}, page {self.current_page + 1}")
        
        page_num = self.current_page + 1
        
        possible_names = [
            f"Book.image.{self.current_book_type}.{page_num}",
            f"Book.image.{self.current_book_type}{page_num}",
            f"Book.image.{self.current_book_type}_{page_num}",
            f"Book.Image.{self.current_book_type}.{page_num}",
        ]
        
        image_shown = False
        for image_name in possible_names:
            image_obj = scene.objects.get(image_name)
            if image_obj:
                image_obj.worldPosition = show_pos
                image_obj.worldOrientation = show_orient
                image_obj.visible = True
                if _DEBUG_MODE:
                    debug_print(f"Image {image_name} displayed")
                image_shown = True
                break
        
        # If no image found, show debug log
        if not image_shown and _DEBUG_MODE:
            debug_print(f"No image found for page {page_num}")
    
    def _hide_all_images(self):
        """Hides all book images"""
        scene = logic.getCurrentScene()
        target_pos = scene.objects.get(IMAGE_OBJECTS_OUT)
        
        if not target_pos:
            debug_print(f"Exit position not found: {IMAGE_OBJECTS_OUT}")
            return
        
        moved_count = 0
        for obj in scene.objects:
            if obj.name.startswith("Book.image."):
                obj.worldPosition = target_pos.worldPosition.copy()
                obj.worldOrientation = target_pos.worldOrientation.copy()
                obj.visible = False
                moved_count += 1
        
        if _DEBUG_MODE and moved_count > 0:
            debug_print(f"{moved_count} images hidden")

# =============================================================================
# GLOBAL INSTANCES
# =============================================================================
# Global instance of book manager
if not hasattr(logic, "book_manager"):
    logic.book_manager = BookManager()

# Initialize globalDict if it doesn't exist
if not hasattr(logic, "globalDict"):
    logic.globalDict = {}

# =============================================================================
# MAIN FUNCTION - FIXED HEIGHT VERSION
# =============================================================================
def main():
    cont = logic.getCurrentController()
    own = cont.owner
    
    # 1. MOUSE SENSORS (event-driven, efficient)
    mouse_over_sensor = cont.sensors.get("Mouse.Over")
    mouse_click_sensor = cont.sensors.get("Mouse.Click")
    
    # Variable to track if mouse is over the book
    current_mouse_over = False
    if mouse_over_sensor and mouse_over_sensor.positive:
        current_mouse_over = True
    
    # Mouse Over/Out handling
    previous_mouse_over = own.get("_was_mouse_over", False)
    
    # MOUSE ENTERED
    if current_mouse_over and not previous_mouse_over:
        if _change_child_texture(own, cont, TEXTURE_HIGHLIGHT):
            own["_was_mouse_over"] = True
            own["_highlight_active"] = True

            if _DEBUG_MODE:
                debug_print(f"Mouse ENTERED book")

            # Show book title on hover (with duplicate prevention)
            book_id = own.get("book_id", 0)
            book_type = own.get("book_type", "")
            book_data = _get_book_data(book_id, book_type)

            if book_data:
                title = book_data.get("Título", "Book")

                # Prevent re-showing the same title if already showing
                # This uses the object's last_shown_title tracking
                last_title = own.get("_last_shown_title", None)
                last_time = own.get("_last_shown_time", 0)
                current_time = time.time()

                # Only show if different title or enough time has passed (1 second)
                if title != last_title or (current_time - last_time) > 1.0:
                    _set_info_text(title)
                    own["_last_shown_title"] = title
                    own["_last_shown_time"] = current_time
                    if _DEBUG_MODE:
                        debug_print(f"Showing title: {title}")
                else:
                    if _DEBUG_MODE:
                        debug_print(f"Skipping duplicate title: {title}")
    
    # MOUSE EXITED
    elif not current_mouse_over and previous_mouse_over:
        if _change_child_texture(own, cont, TEXTURE_NORMAL):
            own["_was_mouse_over"] = False
            own["_highlight_active"] = False
            own["_mouse_exit_time"] = time.time()

            if _DEBUG_MODE:
                debug_print(f"Mouse EXITED book - grace period started")
    
    # 2. CLICK ONLY IF MOUSE IS OVER THE BOOK
    if mouse_click_sensor and mouse_click_sensor.positive:
        # Only process click if mouse is OVER the book
        if current_mouse_over:
            _handle_mouse_click_event(cont, own)
        elif _DEBUG_MODE:
            debug_print("Click ignored - mouse not over book")
    
    # 3. ALWAYS SENSOR (cleanup and timer management)
    always_sensor = cont.sensors.get("Always")

    if always_sensor and always_sensor.positive:
        # Handle book display when open
        if logic.book_manager.is_open:
            _update_book_display()

        # Handle grace period timer for info text clearing
        # Check continuously if we need to clear (works on any frame, not just transition)
        exit_time = own.get("_mouse_exit_time", 0)
        if exit_time > 0 and not current_mouse_over:
            elapsed = time.time() - exit_time
            if elapsed >= BOOK_TITLE_DURATION:
                # Grace period elapsed, safe to clear
                _set_info_text_immediate("")
                own["_mouse_exit_time"] = 0  # Reset
                if _DEBUG_MODE:
                    debug_print(f"Grace period complete ({elapsed:.1f}s), text cleared")

        # Legacy cleanup
        if own.get("_needs_image_update", False):
            own["_needs_image_update"] = False

def _handle_mouse_click_event(cont, own):
    """Handles Mouse Click event (only when mouse is over the book)"""
    if logic.globalDict.get("book_closing", False):
        if _DEBUG_MODE:
            debug_print("Book interaction blocked")
        logic.globalDict["book_closing"] = False
        if _DEBUG_MODE:
            debug_print("book_closing flag cleared")
        return
    
    # Check if there are open modals blocking interaction
    if getattr(logic, "hud_pause_open", False) or \
       getattr(logic, "hud_inventory_open", False) or \
       getattr(logic, "hud_inventory_v2_open", False):
        return
    
    book_id = own.get("book_id", 0)
    book_type = own.get("book_type", "")
    
    if _DEBUG_MODE:
        debug_print(f"VALID click on book: id={book_id}, type={book_type}")
    
    # Open the book
    if logic.book_manager.open_book(book_id, book_type):
        if _DEBUG_MODE:
            debug_print("Showing book HUD")

        # Clear the hover title text IMMEDIATELY before showing book content
        # This prevents the title from overlapping with the book content
        _force_clear_info_text()
        own["_mouse_exit_time"] = 0  # Cancel any pending grace period

        # Move HUD
        if _show_book_hud():
            # Show image of first page IMMEDIATELY
            logic.book_manager._update_image_display()

            # Send message to lock main scene
            message_sent = send_message(cont)
            debug_print(f"Send result: {'SUCCESS' if message_sent else 'FAILED'}")

            if _DEBUG_MODE:
                debug_print("First page image displayed immediately")

        # Update text IMMEDIATELY
        _update_book_display()

        if _DEBUG_MODE:
            debug_print("Book fully opened - text and image displayed")

# =============================================================================
# INITIALIZATION
# =============================================================================
def init():
    """Initialization of the book system"""
    debug_print("Library system initialized - FIXED TEXT HEIGHT")
    debug_print(f"   * Configuration: {MAX_LINES_PER_PAGE} max lines, {MAX_WIDTH_CHARS} max characters")
    
    # Ensure HUD is hidden at startup
    _hide_book_hud()
    
    # Initialize texture states
    scene = logic.getCurrentScene()
    book_count = 0
    
    for obj in scene.objects:
        if "book_id" in obj:
            obj["_was_mouse_over"] = False
            obj["_highlight_active"] = False
            obj["_needs_image_update"] = False
            
            # Ensure initial texture is normal
            try:
                cont = logic.getCurrentController()
                _change_child_texture(obj, cont, TEXTURE_NORMAL)
                book_count += 1
            except Exception as e:
                debug_print(f"Error initializing book {obj.get('book_id', 'N/A')}: {e}")
    
    debug_print(f"{book_count} books initialized")
    
    # Initialize flags
    logic.globalDict["book_closing"] = False

# =============================================================================
# PUBLIC FUNCTIONS
# =============================================================================
def set_debug(enabled):
    """Activates or deactivates debug messages globally"""
    set_debug_mode(enabled)
    # Also update legacy flag for compatibility
    logic.globalDict["debug_books"] = enabled

# Call initialization
init()