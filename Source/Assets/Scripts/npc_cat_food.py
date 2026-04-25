"""
npc_cat_food.py

Manages Cat.Food object (food can) for cat feeding system.

This script handles the cat food can object including spawning, visual effects,
mouse interaction, collection, and respawn logic.

Main Features:
    1. Spawn cat food can at random spawn points when conditions are met
    2. Scale animation on mouse hover (scale up to 1.2x)
    3. Mouse click collection with inventory update
    4. Automatic respawn after cooldown when inventory is empty
    5. Integration with game_state for inventory tracking
    6. Visual effect (Matrix.Effect) on collection
    7. Hide/disable logic when collected or inventory full

Setup:
    Connect to Logic Bricks as Python controller with module 'npc_cat_food.main'
    Required sensors: Mouse.Click, Mouse.Over, Near
    Required child objects: Matrix.Effect.Tracked (optional)

Configurable Variables:
    DEBUG_MODE (bool): Enable debug logging (default: False)
    _SCALE_MULTIPLIER (float): Scale multiplier on hover (default: 1.2)
    _RESPAWN_FRAMES (int): Frames to wait before respawn (default: 300)

Notes:
    - Requires game_access module for cat food inventory management
    - Spawn points must be named 'Empty.Cat.Food.{n}' (n from 1 to max_points)
    - Max spawn points configured via game_access.set_cat_food_spawn_points()
    - Cat food will not spawn if player already has inventory items
    - Cat food will not spawn if another active can exists in scene
    - Matrix.Effect.Tracked object is triggered on collection

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
__description__ = "Manages Cat.Food object (food can) for cat feeding system"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic
from mathutils import Vector
import random
import game_access

# =============================================================================
# DEBUG CONFIGURATION
# =============================================================================
DEBUG_MODE = False

# =============================================================================
# PRE-CALCULATED CONSTANTS (avoids object creation each frame)
# =============================================================================
_SCALE_MULTIPLIER   = 1.2
_SCALE_THRESHOLD    = 0.001
_HIDDEN_Y           = -500
_RESPAWN_FRAMES     = 300
_DEBUG_INTERVAL     = 60

# =============================================================================
# UTILITIES
# =============================================================================

def debug_log(message):
    """Zero-cost logging when DEBUG_MODE=False (avoids f-string construction)."""
    if DEBUG_MODE:
        print(f"[CAT_FOOD] {message}")


def _vectors_equal(v1, v2, threshold=_SCALE_THRESHOLD):
    """Fast vector comparison with threshold."""
    return (abs(v1.x - v2.x) < threshold and
            abs(v1.y - v2.y) < threshold and
            abs(v1.z - v2.z) < threshold)


def _hide_owner(owner):
    """Centralizes hide logic to avoid code duplication."""
    owner.worldPosition.y = _HIDDEN_Y
    owner.visible         = False
    owner["active"]       = False


# =============================================================================
# SPAWN
# =============================================================================

def get_spawn_point():
    """
    Gets random spawn point.
    Caches empty list to avoid iterating scene.objects repeatedly.
    """
    scene        = logic.getCurrentScene()
    max_points   = game_access.get_cat_food_spawn_points()
    spawn_points = []

    for i in range(1, max_points + 1):
        empty_name = f"Empty.Cat.Food.{i}"
        # scene.objects.get() is O(1) — name lookup, not iteration
        empty_obj = scene.objects.get(empty_name)
        if empty_obj:
            spawn_points.append(empty_obj)

    return random.choice(spawn_points) if spawn_points else None


# =============================================================================
# INITIALIZATION
# =============================================================================

def initialize_food(owner):
    """
    Initializes food object.
    Optimized: uses name lookup instead of iterating scene.objects.
    """
    if DEBUG_MODE:
        debug_log("Initializing cat food can")

    scene = logic.getCurrentScene()

    # ---- Check if another active can already exists -------------------------
    # OPTIMIZATION: instead of iterating ALL scene objects,
    # we look directly by name. If the engine has multiple instances,
    # only the relevant one is checked.
    for obj in scene.objects:
        if obj is owner:
            continue
        if obj.name.startswith("Cat.Food") and obj.get("active", False):
            if DEBUG_MODE:
                debug_log("Another ACTIVE can already in scene - Hiding this one")
            _hide_owner(owner)
            owner["initialized"] = True
            return False

    # ---- Check inventory ---------------------------------------------------
    # Single call; reuse the value
    cat_food_items = game_access.get_cat_food_items()
    if cat_food_items > 0:
        if DEBUG_MODE:
            debug_log(f"Player has {cat_food_items} can(s) - No spawn")
        _hide_owner(owner)
        owner["initialized"] = True
        return False

    # ---- Spawn at random point --------------------------------------------
    spawn_point = get_spawn_point()
    if not spawn_point:
        if DEBUG_MODE:
            debug_log("No Empty.Cat.Found — can not visible")
        _hide_owner(owner)
        owner["initialized"] = True
        return False

    owner.worldPosition    = spawn_point.worldPosition.copy()
    owner.worldOrientation = spawn_point.worldOrientation.copy()
    if DEBUG_MODE:
        debug_log(f"Positioned at: {spawn_point.name}")

    # ---- Initial state -----------------------------------------------------
    owner.visible = True

    # Original scale captured ONCE and explicitly copied
    original_scale = owner.worldScale.copy()

    owner["active"]           = True
    owner["initialized"]      = True
    owner["collected"]        = False
    owner["respawn_timer"]    = 0
    owner["scale_anim_active"] = False
    owner["original_scale"]   = original_scale.copy()
    owner["current_scale"]    = original_scale.copy()
    # Initial target = original scale (pre-calculated Vector)
    owner["scale_target"]     = original_scale.copy()
    owner["scale_speed"]      = 0.3
    # Flag to know if mouse was over AND near in previous frame
    owner["mouse_was_over"]   = False

    if DEBUG_MODE:
        debug_log("Cat.Food initialized and visible")
    return True


# =============================================================================
# SCALE ANIMATION
# =============================================================================

def handle_scale_animation(owner):
    """
    Handles scale animation (lerp toward target).
    Only executes if animation is active — zero cost when inactive.
    """
    if not owner["scale_anim_active"]:
        return

    target_scale  = owner["scale_target"]
    current_scale = owner["current_scale"]
    speed         = owner["scale_speed"]

    # Lerp component by component
    dx = (target_scale.x - current_scale.x) * speed
    dy = (target_scale.y - current_scale.y) * speed
    dz = (target_scale.z - current_scale.z) * speed

    new_x = current_scale.x + dx
    new_y = current_scale.y + dy
    new_z = current_scale.z + dz

    # Snap to target if close enough
    reached = True
    if abs(new_x - target_scale.x) > _SCALE_THRESHOLD:
        reached = False
    else:
        new_x = target_scale.x

    if abs(new_y - target_scale.y) > _SCALE_THRESHOLD:
        reached = False
    else:
        new_y = target_scale.y

    if abs(new_z - target_scale.z) > _SCALE_THRESHOLD:
        reached = False
    else:
        new_z = target_scale.z

    # OPTIMIZATION: reuse stored Vector instead of creating a new one
    new_scale   = owner["current_scale"]   # reference to existing Vector
    new_scale.x = new_x
    new_scale.y = new_y
    new_scale.z = new_z

    owner.worldScale           = new_scale
    # current_scale already points to the same object, no need to reassign
    owner["scale_anim_active"] = not reached


# =============================================================================
# MOUSE INTERACTION
# =============================================================================

def handle_mouse_interaction(cont, owner):
    """
    Handles mouse interaction with the can (mouse over and click).
    Optimized: minimal object creation and external calls.
    """
    mouse_click = cont.sensors.get("Mouse.Click")
    mouse_over  = cont.sensors.get("Mouse.Over")
    near_player = cont.sensors.get("Near")

    # Quick exit if object is not active / visible
    if not owner["active"] or not owner.visible:
        return False

    over_positive = mouse_over and mouse_over.positive
    near_valid    = near_player and near_player.positive

    # ---- Scale animation on Mouse Over + Near (only if can be picked up) ----
    # The can should only scale when the player is close enough to pick it up.
    # Therefore, both conditions must be true.
    should_scale = over_positive and near_valid
    mouse_was_over = owner["mouse_was_over"]

    if should_scale != mouse_was_over:          # state change
        original_scale = owner["original_scale"]

        if should_scale:
            # Scale to 1.2x
            m = _SCALE_MULTIPLIER
            target = owner["scale_target"]       # reuse existing Vector
            target.x = original_scale.x * m
            target.y = original_scale.y * m
            target.z = original_scale.z * m
            if DEBUG_MODE:
                debug_log("Mouse Over + Near - Scaling to 1.2x")
        else:
            # Return to original scale
            target = owner["scale_target"]
            target.x = original_scale.x
            target.y = original_scale.y
            target.z = original_scale.z
            if DEBUG_MODE:
                debug_log("Mouse Out or Player left range - Scaling to original scale")

        owner["scale_anim_active"] = True
        owner["mouse_was_over"]    = should_scale

    # ---- Click to collect can --------------------------------------------
    # Single call to get_cat_food_items() per frame
    cat_food_items = game_access.get_cat_food_items()
    if cat_food_items > 0:
        return False

    click_valid = mouse_click and mouse_click.positive

    if not (click_valid and over_positive and near_valid):
        return False

    if DEBUG_MODE:
        debug_log("Valid click detected")

    # Verify that the object in Near is the player
    player = None
    for obj in near_player.hitObjectList:
        if obj.get("player", False) or obj.name == "Player":
            player = obj
            break

    if not player:
        if DEBUG_MODE:
            debug_log("Player not found in Near sensor")
        return False

    # Save position before hiding (for Matrix.Effect)
    food_position = owner.worldPosition.copy()

    # Update inventory
    new_count = game_access.add_cat_food(1)
    if DEBUG_MODE:
        debug_log(f"Can added to inventory: total={new_count}")

    # Mark collected in GameState
    game = game_access.get_game()
    if game and game.state:
        game.state.cat_food_just_picked = True
        if DEBUG_MODE:
            debug_log(f"GameState: cat_food_items={game.state.cat_food_items}")

    # HUD and sound
    game_access.set_cat_food_hud_visible(True)
    bge.logic.sendMessage("sound_fx.play", "sound_fx.play|pop.ogg")

    # Matrix.Effect
    scene = logic.getCurrentScene()
    matrix_effect = scene.objects.get("Matrix.Effect.Tracked")
    if matrix_effect:
        matrix_effect.worldPosition = food_position
        matrix_effect.sendMessage('effect_disappear')
        if DEBUG_MODE:
            debug_log("Matrix.Effect positioned")

    # Hide can
    _hide_owner(owner)
    owner["collected"]         = True
    owner["respawn_timer"]     = 0
    owner["scale_anim_active"] = False
    owner["mouse_was_over"]    = False

    # Reset current scale to original without creating new Vector
    original_scale          = owner["original_scale"]
    current_scale           = owner["current_scale"]
    current_scale.x         = original_scale.x
    current_scale.y         = original_scale.y
    current_scale.z         = original_scale.z
    owner.worldScale        = current_scale

    if DEBUG_MODE:
        debug_log("Can collected and object hidden")
    return True


# =============================================================================
# MAIN LOOP
# =============================================================================

def main(cont):
    """Main script for Cat.Food — executed each frame by BGE."""
    owner = cont.owner

    # ---- Periodic debug (zero cost if DEBUG_MODE=False) -------------------
    if DEBUG_MODE:
        frame_count = owner.get("frame_count", 0)
        if frame_count % _DEBUG_INTERVAL == 0:
            print("=" * 60)
            print(f"[CAT_FOOD] Cat.Food.main() — Frame {frame_count}")
            print(f"[CAT_FOOD] Position:    {owner.worldPosition}")
            print(f"[CAT_FOOD] Visible:     {owner.visible}")
            print(f"[CAT_FOOD] active=      {owner.get('active', 'N/A')}")
            print(f"[CAT_FOOD] initialized= {owner.get('initialized', 'N/A')}")
            print(f"[CAT_FOOD] collected=   {owner.get('collected', 'N/A')}")
        owner["frame_count"] = frame_count + 1

    # ---- Initialization (only first frame) -------------------------------
    if "initialized" not in owner:
        if DEBUG_MODE:
            debug_log("First initialization")
        initialize_food(owner)
        return

    # ---- Respawn logic (only if inactive and collected) ------------------
    if not owner["active"]:
        if owner.get("collected", False):
            respawn_timer  = owner["respawn_timer"]
            # Only check inventory if timer has expired
            if respawn_timer >= _RESPAWN_FRAMES:
                if game_access.get_cat_food_items() == 0:
                    if DEBUG_MODE:
                        debug_log("Conditions met — Respawn can")
                    owner["collected"]      = False
                    owner["respawn_timer"]  = 0
                    initialize_food(owner)
                    return
                # If player still has the can, reset timer
                # to wait another _RESPAWN_FRAMES after dropping it
                owner["respawn_timer"] = 0
            else:
                owner["respawn_timer"] = respawn_timer + 1
        return

    # ---- Scale animation ------------------------------------------------
    handle_scale_animation(owner)

    # ---- Sensor interaction ---------------------------------------------
    handle_mouse_interaction(cont, owner)