"""
exhibition_objects.py

Manages interaction with museum exhibition objects with optimized image handling.

This script handles visual interaction (hover, click) and functionality
for exhibition objects, including displaying object information and images
when clicked, with proper state management to prevent conflicts.

Main Features:
    1. Sensor-based mouse detection for hover and click
    2. Visual effects (scale, tint) for idle, hover, and click states
    3. Optimized image display via parent-child hierarchy
    4. Multi-language text loading from JSON files
    5. Exhibition state management with blocking of concurrent interactions
    6. Scale animation for hover effect
    7. Diagnostic function for debugging image objects

Setup:
    Connect to Logic Bricks as Python controller with module 'exhibition_objects.main'
    Required sensors: Mouse.Over, Mouse.Click
    Required properties: 'id' (unique identifier for the object)

Configurable Variables:
    DEBUG (bool): Enable debug logging (default: True)
    FALLBACK_LANG (str): Fallback language if current not available (default: 'es')
    HOVER_SCALE (float): Scale factor when mouse is over (default: 1.2)
    NORMAL_SCALE (float): Normal object scale (default: 1.0)
    ANIM_SPEED (float): Animation speed for scaling (default: 10.0)
    IDLE_TINT (tuple): RGBA color for idle state (default: (1.00, 1.00, 1.00, 1.0))
    HOVER_TINT (tuple): RGBA color for hover state (default: (2.00, 2.00, 2.00, 1.0))
    CLICK_TINT (tuple): RGBA color for click state (default: (0.85, 0.85, 0.85, 1.0))
    DISABLED_TINT (tuple): RGBA color for disabled state (default: (0.55, 0.55, 0.55, 1.0))
    REQUIRED_CONSECUTIVE_FRAMES (int): Frames needed for stable hover detection (default: 2)
    EXHIBITION_MAIN (str): Main exhibition HUD object (default: 'Empty.Exhibition.Main')
    HUD_POS_IN (str): Position when HUD is visible (default: 'Empty.Hud.Pos')
    EXHIBITION_POS_OUT (str): Position when HUD is hidden (default: 'Empty.Exhibition.Out')
    IMAGE_PARENT_EMPTY (str): Empty containing all exhibition images (default: 'Empty.Img.Exhib')
    IMAGE_OBJECT_PREFIX (str): Prefix for image objects (default: 'Img.')
    MOUSE_OVER_SENSOR_NAME (str): Mouse over sensor name (default: 'Mouse.Over')
    MOUSE_CLICK_SENSOR_NAME (str): Mouse click sensor name (default: 'Mouse.Click')

Notes:
    - Requires game_access module for HUD text management
    - JSON file named 'objects_exhibition_{lang}.json' in //Assets/Texts/ folder
    - Images should be children of Empty.Img.Exhib for efficient hiding/showing
    - Interaction is blocked when exhibition is already open
    - Click effects automatically restore after 0.1 seconds
    - Uses frame stabilization to prevent flickering on hover

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
__description__ = "Manages interaction with museum exhibition objects"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic
import json
import os

# Import game_access for new architecture
try:
    import game_access
    HAS_GAME_ACCESS = True
except ImportError:
    HAS_GAME_ACCESS = False

# =============================================================================
# LOGGING
# =============================================================================
def _log(*args):
    print("[exhibition_objects]", *args)

# =============================================================================
# CONFIGURATION
# =============================================================================
DEBUG = True
FALLBACK_LANG = "es"

# Visual effects for objects
HOVER_SCALE = 1.2
NORMAL_SCALE = 1.0
ANIM_SPEED = 10.0

# Visual effects configuration (tinting)
IDLE_TINT     = (1.00, 1.00, 1.00, 1.0)
HOVER_TINT    = (2.00, 2.00, 2.00, 1.0)
CLICK_TINT    = (0.85, 0.85, 0.85, 1.0)
DISABLED_TINT = (0.55, 0.55, 0.55, 1.0)

# Stabilization system
REQUIRED_CONSECUTIVE_FRAMES = 2

# HUD positioning
EXHIBITION_MAIN = "Empty.Exhibition.Main"
HUD_POS_IN = "Empty.Hud.Pos"
EXHIBITION_POS_OUT = "Empty.Exhibition.Out"

# Optimization: Search images as children of this empty
IMAGE_PARENT_EMPTY = "Empty.Img.Exhib"
IMAGE_OBJECT_PREFIX = "Img."

# Mouse sensor names
MOUSE_OVER_SENSOR_NAME = "Mouse.Over"
MOUSE_CLICK_SENSOR_NAME = "Mouse.Click"

# =============================================================================
# TINTING SYSTEM
# =============================================================================
def _tint_branch(root, rgba):
    """Applies tint to an object and all its children"""
    if not root:
        return
    
    r, g, b, a = rgba
    
    try:
        root.color = [r, g, b, a]
    except:
        pass
    
    try:
        for ch in root.childrenRecursive:
            try:
                ch.color = [r, g, b, a]
            except:
                pass
    except:
        pass

def _apply_tint(owner, rgba):
    """Applies tint to the object and saves the state"""
    _tint_branch(owner, rgba)
    owner["_current_tint"] = rgba

def _apply_hover_effects(owner):
    """Applies visual effects when mouse is over the object"""
    if not owner.get("_mouse_over", False):
        owner["_mouse_over"] = True
        owner["_tint_state"] = "hover"
        
        if "_original_scale" not in owner:
            owner["_original_scale"] = tuple(owner.localScale)
        
        _apply_tint(owner, HOVER_TINT)

def _apply_click_effect(owner):
    """Applies momentary click effect"""
    owner["_tint_state"] = "click"
    _apply_tint(owner, CLICK_TINT)
    
    if "_click_restore_time" not in owner:
        owner["_click_restore_time"] = logic.getRealTime() + 0.1
        
    bge.logic.sendMessage("sound_fx.play", "sound_fx.play|clic.ogg")
    
    _log(f"Click effect applied to {owner.name}")

def _reset_visual_effects(owner):
    """Restores visual effects to normal state"""
    if owner.get("_mouse_over", False):
        owner["_mouse_over"] = False
        owner["_tint_state"] = "idle"
        _apply_tint(owner, IDLE_TINT)
        _log(f"Hover effects restored on {owner.name}")

def _handle_click_restoration(owner):
    """Handles restoration of click effect to hover"""
    if "_click_restore_time" in owner:
        current_time = logic.getRealTime()
        if current_time >= owner["_click_restore_time"]:
            if owner.get("_mouse_over", False):
                owner["_tint_state"] = "hover"
                _apply_tint(owner, HOVER_TINT)
                _log(f"Tint restored to hover after click")
            del owner["_click_restore_time"]

def _handle_mouse_over_stable(owner, current_mouse_over):
    """Handles mouse over effects with stabilization"""
    if "_mouse_over_counter" not in owner:
        owner["_mouse_over_counter"] = 0
    if "_mouse_out_counter" not in owner:
        owner["_mouse_out_counter"] = 0
    
    previous_mouse_over = owner.get("_mouse_over", False)
    
    if current_mouse_over:
        owner["_mouse_out_counter"] = 0
        if not previous_mouse_over:
            owner["_mouse_over_counter"] += 1
            if owner["_mouse_over_counter"] >= REQUIRED_CONSECUTIVE_FRAMES:
                _apply_hover_effects(owner)
                owner["_mouse_over_counter"] = 0
    else:
        owner["_mouse_over_counter"] = 0
        if previous_mouse_over:
            owner["_mouse_out_counter"] += 1
            if owner["_mouse_out_counter"] >= REQUIRED_CONSECUTIVE_FRAMES:
                _reset_visual_effects(owner)
                owner["_mouse_out_counter"] = 0

# =============================================================================
# JSON LOADING FUNCTION
# =============================================================================
def _get_lang():
    """Gets current game language"""
    try:
        if HAS_GAME_ACCESS:
            game = game_access.get_game()
            if game:
                return game.state.language
    except Exception:
        pass
    
    try:
        return logic.game_state.language
    except Exception:
        return FALLBACK_LANG

def _load_exhibition_data():
    """Loads exhibition objects data from JSON"""
    lang = _get_lang()
    json_path = logic.expandPath(f"//Assets/Texts/objects_exhibition_{lang}.json")
    
    if not os.path.exists(json_path) and lang != FALLBACK_LANG:
        json_path = logic.expandPath(f"//Assets/Texts/objects_exhibition_{FALLBACK_LANG}.json")
    
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if DEBUG: _log(f"JSON loaded: {len(data)} objects")
        return data
    except Exception as e:
        if DEBUG: _log(f"Error loading JSON: {e}")
        return []

# =============================================================================
# HUD POSITIONING SYSTEM
# =============================================================================
def _move_to_position(object_name, target_name):
    """Moves an object to the position of another object"""
    scene = logic.getCurrentScene()
    obj = scene.objects.get(object_name)
    target = scene.objects.get(target_name)
    
    if obj and target:
        if DEBUG: _log(f"Moving {object_name} to {target_name}")
        obj.worldPosition = target.worldPosition.copy()
        obj.worldOrientation = target.worldOrientation.copy()
        return True
    else:
        if DEBUG: _log(f"Could not move {object_name}")
        return False

def _show_exhibition_hud():
    """Shows the exhibition HUD interface"""
    return _move_to_position(EXHIBITION_MAIN, HUD_POS_IN)

def _hide_exhibition_hud():
    """Hides the exhibition HUD interface"""
    return _move_to_position(EXHIBITION_MAIN, EXHIBITION_POS_OUT)

# =============================================================================
# OPTIMIZED VISIBILITY SYSTEM (child-based search)
# =============================================================================

def _get_image_parent():
    """Gets Empty.Img.Exhib object that groups all images"""
    scene = logic.getCurrentScene()
    return scene.objects.get(IMAGE_PARENT_EMPTY)

def _hide_all_exhibition_images():
    """Hides all Img.* objects that are children of Empty.Img.Exhib"""
    img_parent = _get_image_parent()
    if not img_parent:
        if DEBUG: _log(f"Could not find {IMAGE_PARENT_EMPTY}")
        return False
    
    hidden_count = 0
    for child in img_parent.children:
        if child.name.startswith(IMAGE_OBJECT_PREFIX):
            try:
                child.visible = False
                hidden_count += 1
            except:
                pass
    
    if DEBUG and hidden_count > 0:
        _log(f"Hidden {hidden_count} image objects (children of {IMAGE_PARENT_EMPTY})")
    return hidden_count > 0

def _show_exhibition_image(obj_id):
    """Shows the image object corresponding to the given ID, searching as child of Empty.Img.Exhib"""
    img_parent = _get_image_parent()
    if not img_parent:
        if DEBUG: _log(f"Could not find {IMAGE_PARENT_EMPTY}")
        return False
    
    image_obj_name = f"{IMAGE_OBJECT_PREFIX}{obj_id}"
    
    # Search directly among children of the parent empty
    for child in img_parent.children:
        if child.name == image_obj_name:
            try:
                child.visible = True
                if DEBUG: _log(f"Showing image: {image_obj_name} (child of {IMAGE_PARENT_EMPTY})")
                return True
            except Exception as e:
                if DEBUG: _log(f"Error showing {image_obj_name}: {e}")
                return False
    
    if DEBUG: _log(f"Image object not found as child of {IMAGE_PARENT_EMPTY}: {image_obj_name}")
    return False

# =============================================================================
# TEXT HANDLING
# =============================================================================
def _get_exhibition_text(obj_id):
    """Gets exhibition object text by ID"""
    data = _load_exhibition_data()
    
    for item in data:
        if item.get("id") == obj_id:
            lines = []
            desc = item.get("descripcion", "")
            if desc:
                lines.append(desc)
            
            periodo = item.get("periodo", "")
            if periodo:
                lines.append("")
                lines.append(periodo)
            
            lugar = item.get("lugar_recuperacion", "")
            if lugar:
                lines.append("")
                lines.append(lugar)
            
            dimensiones = item.get("dimensiones", "")
            if dimensiones:
                lines.append("")
                lines.append(f"Dimensions: {dimensiones}")
            
            return "\n".join(lines)
    
    return f"Information not available for object ID: {obj_id}"

def _update_exhibition_display(obj_id):
    """Updates display with object text"""
    if DEBUG: _log(f"Updating display for object ID: {obj_id}")
    
    exhibition_text = _get_exhibition_text(obj_id)
    
    try:
        if HAS_GAME_ACCESS:
            game = game_access.get_game()
            if game and hasattr(game, 'hud_text'):
                game.hud_text.exhibition_text = exhibition_text
                if DEBUG: _log(f"Text updated for ID {obj_id} (new architecture)")
            else:
                if DEBUG: _log("game.hud_text not available")
        else:
            scene = logic.getCurrentScene()
            game_controller = scene.objects.get("Game.Controller")
            if game_controller:
                hud_text = game_controller.get("hud_text", None)
                if hud_text:
                    hud_text.exhibition_text = exhibition_text
                    if DEBUG: _log(f"Text updated for ID {obj_id} (compatibility)")
                else:
                    if DEBUG: _log("hud_text not found")
            else:
                if DEBUG: _log("Game.Controller not found")
    except Exception as e:
        if DEBUG: _log("Error updating display:", e)

def _clear_exhibition_hud_text():
    """Clears exhibition text from HUD"""
    try:
        if HAS_GAME_ACCESS:
            game = game_access.get_game()
            if game and hasattr(game, 'hud_text'):
                game.hud_text.exhibition_text = ""
                if DEBUG: _log("Text cleared (new architecture)")
        else:
            scene = logic.getCurrentScene()
            game_controller = scene.objects.get("Game.Controller")
            if game_controller:
                hud_text = game_controller.get("hud_text", None)
                if hud_text:
                    hud_text.exhibition_text = ""
                    if DEBUG: _log("Text cleared (compatibility)")
                else:
                    if DEBUG: _log("hud_text not available")
            else:
                if DEBUG: _log("Game.Controller not found")
    except Exception as e:
        if DEBUG: _log("Error clearing text:", e)

# =============================================================================
# SCALE ANIMATION
# =============================================================================
def _animate_scale(cont, target_scale):
    """Animates object scale towards a target value"""
    own = cont.owner
    
    if "_base_scale" not in own:
        own["_base_scale"] = tuple(own.localScale)
    
    base_scale = own["_base_scale"]
    current_scale = own.localScale
    
    target_scaled = [
        base_scale[0] * target_scale,
        base_scale[1] * target_scale,
        base_scale[2] * target_scale
    ]
    
    new_scale = [
        current_scale[0] + (target_scaled[0] - current_scale[0]) * ANIM_SPEED * 0.02,
        current_scale[1] + (target_scaled[1] - current_scale[1]) * ANIM_SPEED * 0.02,
        current_scale[2] + (target_scaled[2] - current_scale[2]) * ANIM_SPEED * 0.02
    ]
    
    own.localScale = new_scale

# =============================================================================
# MOUSE DETECTION USING SENSORS
# =============================================================================
def _update_mouse_sensors(cont):
    """Updates mouse state based on sensors"""
    mouse_over = False
    mouse_click = False
    
    mouse_over_sensor = cont.sensors.get(MOUSE_OVER_SENSOR_NAME)
    if mouse_over_sensor and mouse_over_sensor.positive:
        mouse_over = True
        
        mouse_click_sensor = cont.sensors.get(MOUSE_CLICK_SENSOR_NAME)
        if mouse_click_sensor and mouse_click_sensor.positive:
            mouse_click = True
    
    return mouse_over, mouse_click

# =============================================================================
# OPTIMIZED CLEANUP FUNCTION
# =============================================================================
def cleanup_exhibition():
    """Cleans up all exhibition resources"""
    try:
        if DEBUG: _log("Cleaning up exhibition resources")
        
        # 1. Hide all images (searching as children)
        _hide_all_exhibition_images()
        
        # 2. Clear exhibition text
        _clear_exhibition_hud_text()
        
        # 3. Clear global flags
        keys_to_remove = ["exhibition_open", "current_exhibition_id"]
        for key in keys_to_remove:
            if key in logic.globalDict:
                del logic.globalDict[key]
        
        return True
        
    except Exception as e:
        if DEBUG: _log(f"Error in cleanup_exhibition: {e}")
        return False

# =============================================================================
# OPTIMIZED DIAGNOSTIC FUNCTION
# =============================================================================
def diagnose_exhibition_objects():
    """Diagnoses available image objects (checking hierarchy)"""
    scene = logic.getCurrentScene()
    
    print("\n" + "="*60)
    print("EXHIBITION OBJECTS DIAGNOSTIC (ATLAS)")
    print("="*60)
    
    # Check the parent Empty object for images
    img_parent = _get_image_parent()
    if img_parent:
        print(f"\nParent empty: {IMAGE_PARENT_EMPTY} found")
        print(f"  - Visible: {img_parent.visible}")
        print(f"  - Direct children: {len(img_parent.children)}")
        
        # List children with Img. prefix
        img_children = [child for child in img_parent.children if child.name.startswith(IMAGE_OBJECT_PREFIX)]
        print(f"  - Children with '{IMAGE_OBJECT_PREFIX}' prefix: {len(img_children)}")
        
        if img_children:
            print("\n  List of available images:")
            for child in sorted(img_children, key=lambda x: x.name):
                visible_status = "VISIBLE" if child.visible else "hidden"
                print(f"    - {child.name}: {visible_status}")
    else:
        print(f"\nParent empty {IMAGE_PARENT_EMPTY} NOT found")
    
    # Check Empty.Exhibition.Main object
    exhibition_main = scene.objects.get(EXHIBITION_MAIN)
    if exhibition_main:
        print(f"\nMain empty: {EXHIBITION_MAIN} found")
        
        # Verify that IMAGE_PARENT_EMPTY is child of EXHIBITION_MAIN
        if img_parent and img_parent.parent == exhibition_main:
            print(f"  {IMAGE_PARENT_EMPTY} is direct child of {EXHIBITION_MAIN}")
        elif img_parent:
            parent_name = img_parent.parent.name if img_parent.parent else "none"
            print(f"  Warning: {IMAGE_PARENT_EMPTY} is NOT child of {EXHIBITION_MAIN} (parent: {parent_name})")
    else:
        print(f"\nMain empty {EXHIBITION_MAIN} NOT found")
    
    print("="*60 + "\n")
    
    return img_parent is not None

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main(cont):
    """Main function for exhibition objects"""
    own = cont.owner
    
    # NEW VERIFICATION - SOLUTION POINT 1
    # If exhibition is open, completely ignore interaction
    # This prevents clicking on objects behind the UI
    if logic.globalDict.get("exhibition_open", False):
        # Restore visual effects if they were active
        if own.get("_mouse_over", False):
            _reset_visual_effects(own)
        return
    # END NEW VERIFICATION
    
    if "id" not in own:
        if DEBUG: _log(f"Object {own.name} does not have 'id' property")
        return
    
    obj_id = own["id"]
    
    # Check if there is an open modal that blocks interaction
    if getattr(logic, "hud_pause_open", False) or \
       getattr(logic, "hud_inventory_open", False) or \
       getattr(logic, "hud_inventory_v2_open", False):
        if own.get("_mouse_over", False):
            _reset_visual_effects(own)
        return
    
    # Initialize visual effects if they don't exist
    if "_mouse_over" not in own:
        own["_mouse_over"] = False
    if "_tint_state" not in own:
        own["_tint_state"] = "idle"
        _apply_tint(own, IDLE_TINT)
    
    _handle_click_restoration(own)
    
    mouse_over, mouse_click = _update_mouse_sensors(cont)
    _handle_mouse_over_stable(own, mouse_over)
    
    # Scale animation
    if own.get("_mouse_over", False):
        _animate_scale(cont, HOVER_SCALE)
    else:
        _animate_scale(cont, NORMAL_SCALE)
    
    # Handle click
    if mouse_over and mouse_click:
        _apply_click_effect(own)
        
        if DEBUG: _log(f"CLICK on exhibition object ID: {obj_id}")
        
        if logic.globalDict.get("exhibition_open", False):
            if DEBUG: _log("Exhibition already open")
            return
        
        if _show_exhibition_hud():
            if DEBUG: _log("Exhibition HUD displayed")
            
            # Optimized: hide all images (searching as children)
            _hide_all_exhibition_images()
            
            # Optimized: show ONLY the image corresponding to the ID (searching as child)
            image_shown = _show_exhibition_image(obj_id)
            
            if image_shown:
                if DEBUG: _log("Image displayed successfully")
            else:
                if DEBUG: _log("Could not display specific image")
                if DEBUG:
                    print("\nAUTOMATIC DIAGNOSTIC:")
                    diagnose_exhibition_objects()
            
            _update_exhibition_display(obj_id)
            
            logic.globalDict["exhibition_open"] = True
            logic.globalDict["current_exhibition_id"] = obj_id
        else:
            if DEBUG: _log("Could not display exhibition HUD")

# =============================================================================
# INITIALIZATION
# =============================================================================
def init(cont):
    """Initializes the exhibition object"""
    own = cont.owner
    
    own["_base_scale"] = tuple(own.localScale)
    own["_mouse_over"] = False
    own["_tint_state"] = "idle"
    _apply_tint(own, IDLE_TINT)
    
    if DEBUG: _log(f"Object initialized: {own.name} (ID: {own.get('id', 'No ID')})")