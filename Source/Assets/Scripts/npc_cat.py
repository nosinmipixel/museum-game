"""
npc_cat.py

Manages NPC cat behavior including patrol, interaction, combat, and pet mode.

This script handles a cat NPC that can patrol between waypoints, interact with
the player, fight enemies, and enter a pet mode where it follows the player.

Main Features:
    1. Patrol between two waypoints with random pauses and grooming animations
    2. Combat system with chasing and attacking enemy objects
    3. Pet mode activation via feeding (consumes cat food items)
    4. Player following behavior in pet mode
    5. Intelligent navigation with wall-following obstacle avoidance + wall collision escape
    6. Combat abandonment detection (stuck without progress or line-of-sight blocked)
    7. Mouse over highlighting with material change
    8. Sound effects (meow, angry, purr, attack)
    9. Synchronization with game_state for pet timer persistence
    10. Swirl effect on attack (visual feedback)

Setup:
    Connect to Logic Bricks as Python controller with module 'npc_cat.main'
    Required sensors: Near.Actv, Near.Player, Near.Enemy, Collision.Enemy,
                      Near.Pet, Ray.Col, Mouse.Over, Mouse.Click, Collision.Col
    Required child objects: metarig (armature), cat_main (mesh)
    Optional: Swirl.Effect object for attack visual effect

Configurable Variables:
    DEBUG_MODE (bool): Enable debug logging (default: True)
    ANIM_IDLE, ANIM_GROOMING, ANIM_WALKING, ANIM_RUNNING, ANIM_ATTACK (str)
    STATE_* constants for state machine
    PET_COMBAT_* constants for pet combat sub-state
    walk_speed (float): Patrol walking speed (default: 0.03)
    run_speed (float): Combat running speed (default: 0.15)
    pet_follow_distance (float): Distance to maintain from player (default: 1.5)
    pet_duration (float): Pet mode duration in seconds (default: 180.0)
    combat_abandon_timeout (float): Seconds without progress to abandon combat (default: 1.0)

Notes:
    - Requires game_access module for cat food and game state
    - Cat food items are consumed when activating pet mode
    - Pet timer persists in game_state.cat_pet_timer
    - Material highlighting uses White_Backface_Culling and Black_Backface_Culling
    - Ray.Col sensor used for obstacle detection during navigation
    - Collision.Col sensor forces small knockback (does NOT cancel combat)
    - Line-of-sight raycast prevents chasing enemies through walls
    - Swirl.Effect object is moved to cat position on attack and then hidden off-camera

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
__description__ = "Manages NPC cat behavior including patrol, combat, and pet mode"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
import random
import math
import traceback
from bge import logic, events
from mathutils import Vector
import game_access

# =============================================================================
# CONFIGURATION
# =============================================================================
DEBUG_MODE = True

# Animation constants
ANIM_IDLE     = "Cat.Idle"
ANIM_GROOMING = "Cat.Grooming"
ANIM_WALKING  = "Cat.Walking"
ANIM_RUNNING  = "Cat.Running"
ANIM_ATTACK   = "Cat.Attack"

# NPC states
STATE_INACTIVE   = 0
STATE_PATROLLING = 1
STATE_INTERACT   = 2
STATE_CHASING    = 3
STATE_ATTACKING  = 4
STATE_PET        = 5

# Pet combat sub-states
PET_COMBAT_NONE     = 0
PET_COMBAT_CHASING  = 1
PET_COMBAT_ATTACKING = 2

# Material names
MATERIAL_HIGHLIGHT = "White_Backface_Culling"
MATERIAL_NORMAL    = "Black_Backface_Culling"

STATE_NAMES = {
    STATE_INACTIVE:   "INACTIVE",
    STATE_PATROLLING: "PATROLLING",
    STATE_INTERACT:   "INTERACT",
    STATE_CHASING:    "CHASING",
    STATE_ATTACKING:  "ATTACKING",
    STATE_PET:        "PET"
}

# UPBGE 0.44 constants
ACTION_MODE_PLAY = 0
ACTION_MODE_LOOP = 2
BLEND_FRAMES     = 5

# =============================================================================
# DEBUG FUNCTIONS
# =============================================================================
def debug_log(*args, **kwargs):
    if DEBUG_MODE:
        print("[DEBUG][NPC_Cat]", *args, **kwargs)

def debug_error(*args, **kwargs):
    print("[NPC_Cat Error]", *args, **kwargs)

def debug_state_change(old_state, new_state):
    if DEBUG_MODE:
        old_name = STATE_NAMES.get(old_state, f"UNKNOWN({old_state})")
        new_name = STATE_NAMES.get(new_state, f"UNKNOWN({new_state})")
        print(f"[DEBUG][NPC_Cat] State: {old_name} -> {new_name}")

# =============================================================================
# NPC CAT CLASS
# =============================================================================
class NPC_Cat:
    def __init__(self, cont):
        debug_log("Initializing NPC Cat with pet system...")
        self.cont  = cont
        self.own   = cont.owner
        self.scene = logic.getCurrentScene()
        self.dt    = 1.0 / logic.getLogicTicRate()

        # -- Metarig (direct child of own) ------------------------------------
        self.metarig = None
        for child in self.own.children:
            if "metarig" in child.name.lower():
                self.metarig = child
                debug_log(f"metarig found: {child.name}")
                break

        if not self.metarig:
            debug_error("metarig not found")

        # -- Cat_main (child of metarig) -------------------------------------
        self.cat_main = None
        if self.metarig:
            for child in self.metarig.children:
                if "cat_main" in child.name.lower():
                    self.cat_main = child
                    debug_log(f"cat_main found: {child.name}")
                    break

        if not self.cat_main:
            debug_log("Searching for cat_main recursively...")
            def find_cat_main(obj):
                if "cat_main" in obj.name.lower():
                    return obj
                for child in obj.children:
                    result = find_cat_main(child)
                    if result:
                        return result
                return None
            self.cat_main = find_cat_main(self.own)
            if self.cat_main:
                debug_log(f"cat_main found recursively: {self.cat_main.name}")
            else:
                debug_error("cat_main NOT FOUND")

        # -- Patrol empties --------------------------------------------------
        self.empty_a = self.scene.objects.get("Empty.Cat.1")
        self.empty_b = self.scene.objects.get("Empty.Cat.2")

        # -- Movement / combat configuration ---------------------------------
        self.walk_speed      = 0.03
        self.run_speed       = 0.15
        self.patrol_pause_min  = 2
        self.patrol_pause_max  = 5
        self.attack_damage   = 5
        self.attack_interval = 0.8
        self.attack_cooldown = 0

        # -- Main state ------------------------------------------------------
        self.current_state    = STATE_INACTIVE
        self.target_empty     = self.empty_b
        self.is_moving_to_a   = False
        self.pause_timer      = 0
        self.next_pause_time  = 0
        self.grooming_timer   = 0
        self.transition_timer = 0
        self.current_enemy    = None
        self.current_animation = None
        self.current_speed    = 0.0
        self.micro_pause_timer = 0
        self.interact_timer   = 0
        self.interact_anim    = ANIM_IDLE
        self.interact_change_time = random.uniform(3, 5)
        self.meow_cooldown    = 0
        self.meow_interval_range  = (4.0, 8.0)
        self.angry_cooldown   = 0
        self.angry_interval_range = (2.0, 5.0)
        self.alertness        = 0.0
        self.comfort          = 0.5
        self.was_in_combat    = False
        self.was_activated    = False
        self.player_far_timer = 0
        self.player_far_threshold = 2.0
        self.frame_count      = 0

        # -- Pet system ------------------------------------------------------
        self.pet_mode           = False
        self.pet_timer          = 0.0
        self.pet_duration       = 180.0
        self.pet_follow_distance = 1.5
        self.pet_min_distance   = 1.0
        self.pet_max_distance   = 2.0
        self.returning_to_patrol = False
        self.patrol_return_target = None
        self.ray_sensor         = None
        self.original_position  = None
        self.pet_follow_player  = None

        # Pet combat sub-state (PET_COMBAT_*)
        self.pet_combat_state   = PET_COMBAT_NONE

        # -- Combat abandonment (stuck without progress or line-of-sight) ---
        self.combat_abandon_timeout   = 1.0  # seconds without progress -> give up
        self.pet_abandon_distance     = 6.0  # player distance threshold (pet mode)
        self.pet_abandon_timeout_far  = 2.5  # seconds if player is far (pet mode)
        self._combat_no_progress_timer = 0.0
        self._combat_check_interval   = 1.0  # how often to measure distance
        self._combat_check_accum      = 0.0
        self._combat_last_dist        = None
        self._combat_progress_min     = 0.3  # minimum progress per interval (units)
        self._enemy_not_visible_timer = 0.0  # time enemy has been out of sight

        # -- Navigation system with wall-following (improved v4) ------------
        self.nav_evading        = False
        self.nav_evade_side     = 1       # +1 right / -1 left
        self.nav_evade_timer    = 0.0
        self.nav_evade_timeout  = 3.0
        self.nav_stuck_timer    = 0.0
        self.nav_last_pos       = None
        # MODIFICATION: Reduce stuck threshold to 0.4 seconds (before 1.0)
        self.nav_stuck_threshold = 0.4     # seconds (before 1.0)
        self._evasion_hold_timer = 0.0     # hysteresis
        self._last_move_dir     = Vector([1, 0, 0])  # for smoothing
        # MODIFICATION: Minimum time to maintain evasion direction
        self._evade_side_lock_timer = 0.0
        self._evade_side_lock_duration = 0.5  # segundos

        # -- Mouse over system ----------------------------------------------
        self.mouse_over_active  = False
        self.was_mouse_over     = False
        self.mouse_over_cooldown = 0
        self.last_mouse_click_time = 0
        self._initialized_mouse_over = False

        # -- Swirl effect ----------------------------------------------------
        self.swirl_effect = self.scene.objects.get("Swirl.Effect")
        if self.swirl_effect:
            # Save original position (just in case, although y=-500 will be used
            self.swirl_original_pos = self.swirl_effect.worldPosition.copy()
            self.swirl_effect_active = False
            self.swirl_effect_timer = 0.0
            # Estimated animation duration (17 frames at 30 fps ≈ 0.567 s)
            self.swirl_anim_duration = 0.6
            # Hide at init
            self.swirl_effect.worldPosition = Vector((0.0, -500.0, 0.0))
            debug_log("Swirl.Effect found and initialized")
        else:
            debug_log("Swirl.Effect not found in scene")

        if self.empty_a:
            self.original_position = self.empty_a.worldPosition.copy()

        self.schedule_next_pause()

        if self.empty_a:
            self.own.worldPosition = self.empty_a.worldPosition.copy()
            if self.empty_b:
                self.rotate_towards(self.empty_b.worldPosition, turn_speed=1.0)

        self.set_visibility(False)
        debug_log("NPC Cat initialized successfully")

    # =========================================================================
    # VISIBILITY
    # =========================================================================
    def set_visibility(self, visible):
        if self.own:
            self.own.setVisible(visible, True)
        if self.metarig:
            self.metarig.setVisible(visible, True)

    # =========================================================================
    # MATERIAL SYSTEM
    # =========================================================================
    def get_mesh_child(self):
        return self.cat_main

    def change_mesh_material(self, material_name):
        mesh = self.get_mesh_child()
        if not mesh:
            debug_error("change_mesh_material: cat_main is None")
            return False
        try:
            import bpy
            mat = bpy.data.materials.get(material_name)
            if mat is None:
                debug_error(f"Material '{material_name}' not found")
                return False
            blender_obj    = mesh.blenderObject
            materials_list = blender_obj.data.materials
            while len(materials_list) < 2:
                materials_list.append(None)
            if len(materials_list) > 1:
                materials_list[1] = mat
                return True
            return False
        except Exception as e:
            debug_error(f"Error changing material: {e}")
            traceback.print_exc()
            return False

    def handle_mouse_over(self):
        mouse_over_sensor  = self.cont.sensors.get("Mouse.Over")
        near_player_sensor = self.cont.sensors.get("Near.Player")
        if not mouse_over_sensor:
            return

        mouse_over_now  = mouse_over_sensor.positive
        player_in_range = near_player_sensor and near_player_sensor.positive

        if not self._initialized_mouse_over:
            self._initialized_mouse_over = True
            self.was_mouse_over = mouse_over_now
            return

        if self.pet_mode:
            if self.mouse_over_active:
                self.change_mesh_material(MATERIAL_NORMAL)
                self.mouse_over_active = False
            self.was_mouse_over = mouse_over_now
            return

        if not player_in_range:
            if self.mouse_over_active:
                self.change_mesh_material(MATERIAL_NORMAL)
                self.mouse_over_active = False
            self.was_mouse_over = mouse_over_now
            return

        if mouse_over_now and not self.was_mouse_over:
            if self.change_mesh_material(MATERIAL_HIGHLIGHT):
                self.mouse_over_active = True
        elif not mouse_over_now and self.was_mouse_over:
            if self.change_mesh_material(MATERIAL_NORMAL):
                self.mouse_over_active = False

        self.was_mouse_over = mouse_over_now

    # =========================================================================
    # ANIMATION AND MOVEMENT
    # =========================================================================
    def play_animation(self, animation, play_mode=ACTION_MODE_LOOP, speed=1.0):
        if not self.metarig:
            return
        # If it's the same animation and it keeps playing, do nothing
        if self.current_animation == animation and self.metarig.isPlayingAction():
            return
        # If it's the same animation but it has stopped (by mistake), restart
        if self.current_animation == animation and not self.metarig.isPlayingAction():
            debug_log(f"Restarting animation {animation} because it stopped unexpectedly")
        try:
            # Custom animation speeds
            # Walking: minimum range 2.5, maximum 4.0
            walking_speed = max(2.5, min(4.0, 2.5 * (self.current_speed / max(self.walk_speed, 0.001))))
            anim_map = {
                ANIM_IDLE:     (1, 10, 1.0),
                ANIM_GROOMING: (1, 30, 0.7 if self.was_in_combat else 0.5),
                ANIM_WALKING:  (1, 20, walking_speed),
                ANIM_RUNNING:  (1, 30, 2.0),
                ANIM_ATTACK:   (1, 25, 1.0),
            }
            if animation in anim_map:
                start, end, spd = anim_map[animation]
                spd *= random.uniform(0.97, 1.03)
                self.metarig.playAction(
                    animation, start, end,
                    play_mode=play_mode,
                    speed=spd,
                    blendin=BLEND_FRAMES
                )
                self.current_animation = animation
        except Exception as e:
            debug_error(f"Animation error {animation}: {e}")

    def stop_animation(self):
        if self.metarig and self.current_animation:
            self.metarig.stopAction()
            self.current_animation = None

    def rotate_towards(self, target_pos, turn_speed=0.1):
        direction = target_pos - self.own.worldPosition
        direction.z = 0
        if direction.length > 0.1:
            direction.normalize()
            target_angle  = math.atan2(direction.y, direction.x) + math.pi / 2
            current_angle = self.own.worldOrientation.to_euler().z
            diff      = (target_angle - current_angle + math.pi) % (2 * math.pi) - math.pi
            new_angle = current_angle + diff * turn_speed
            self.own.worldOrientation = [0, 0, new_angle]

    def move_towards(self, target_pos, speed):
        """Standard straight-line movement towards target with speed smoothing.
        Returns True when arrived."""
        direction = target_pos - self.own.worldPosition
        direction.z = 0
        distance = direction.length
        if distance <= 0.05:
            self.own.worldPosition = target_pos.copy()
            self.current_speed = 0
            return True
        ease_factor  = min(1.0, distance / 1.5)
        target_speed = speed * max(0.2, ease_factor)
        self.current_speed += (target_speed - self.current_speed) * 0.08
        direction.normalize()
        self.own.worldPosition += direction * self.current_speed
        return False

    def schedule_next_pause(self):
        self.next_pause_time = random.uniform(self.patrol_pause_min, self.patrol_pause_max)
        self.pause_timer     = 0

    # =========================================================================
    # LINE-OF-SIGHT & ENEMY VISIBILITY
    # =========================================================================
    def _raycast_to_target(self, target, ignore_self=True, ignore_target=True, property_filter="col"):
        """
        Perform a raycast from the cat to a target object.
        Returns (hit_object, hit_position, hit_normal) or (None, None, None) if no obstacle.
        """
        start = self.own.worldPosition.copy()
        end = target.worldPosition.copy()
        # Lift ray slightly above ground to avoid ground collisions
        start.z += 0.5
        end.z += 0.5

        prop_name = property_filter
        result = self.own.rayCast(end, start, 0, prop_name, 0, 0, 0)
        hit_obj, hit_pos, hit_norm = result

        if hit_obj is None:
            return (None, None, None)

        if ignore_target and hit_obj == target:
            return (None, None, None)

        return (hit_obj, hit_pos, hit_norm)

    def is_enemy_visible(self, enemy):
        """Check if there is a direct line-of-sight to the enemy (no 'col' property in between)."""
        if not enemy or enemy.invalid:
            return False
        hit_obj, _, _ = self._raycast_to_target(enemy, ignore_self=True, ignore_target=True, property_filter="col")
        return hit_obj is None

    def get_visible_enemy(self):
        """Return the nearest enemy that is both in Near.Enemy range and has line-of-sight."""
        near_sensor = self.cont.sensors.get("Near.Enemy")
        if not near_sensor or not near_sensor.positive:
            return None
        hit_list = near_sensor.hitObjectList
        if not hit_list:
            return None

        my_pos = self.own.worldPosition
        best_enemy = None
        best_dist_sq = float('inf')
        for obj in hit_list:
            if obj.invalid:
                continue
            if not self.is_enemy_visible(obj):
                continue
            dist_sq = (obj.worldPosition - my_pos).length_squared
            if dist_sq < best_dist_sq:
                best_dist_sq = dist_sq
                best_enemy = obj
        return best_enemy

    # =========================================================================
    # PET SYSTEM
    # =========================================================================
    def activate_pet_mode(self):
        if self.pet_mode:
            return
        self.pet_mode           = True
        self.pet_timer          = self.pet_duration
        self.returning_to_patrol = False
        self.pet_combat_state   = PET_COMBAT_NONE
        self.current_state      = STATE_PET
        debug_log("Pet mode ACTIVATED")

        game_access.consume_cat_food(1)
        game_access.set_cat_food_hud_visible(False)

        game = game_access.get_game()
        if game and game.state:
            game.state.cat_pet_active = True
            game.state.cat_pet_timer  = self.pet_timer

        bge.logic.sendMessage("sound_fx.play", "sound_fx.play|cat_purr.ogg")

        if self.empty_a:
            self.patrol_return_target = self.empty_a

    def deactivate_pet_mode(self):
        if not self.pet_mode:
            return
        self.pet_mode         = False
        self.pet_timer        = 0.0
        self.pet_combat_state = PET_COMBAT_NONE
        self.returning_to_patrol    = True
        self.patrol_return_target   = self.empty_a
        self.current_enemy    = None
        self.nav_evading      = False
        self.nav_evade_timer  = 0.0
        self.nav_stuck_timer  = 0.0
        debug_log("Pet mode DEACTIVATED")

        game = game_access.get_game()
        if game and game.state:
            game.state.cat_pet_active = False
            game.state.cat_pet_timer  = 0.0

    def check_ray_obstacle(self):
        if self.ray_sensor is None:
            self.ray_sensor = self.cont.sensors.get("Ray.Col")
        return self.ray_sensor and self.ray_sensor.positive

    def evade_obstacle(self):
        """Simple evasion for pet follow and return to patrol (uses speed-based animation)."""
        forward = Vector([0, 1, 0])
        forward = self.own.worldOrientation @ forward
        forward.z = 0
        if forward.length > 0.01:
            forward.normalize()
        side = Vector([self.nav_evade_side, 0, 0])
        side = self.own.worldOrientation @ side
        side.z = 0
        if side.length > 0.01:
            side.normalize()
        move_dir = forward * 0.5 + side * 0.5
        if move_dir.length > 0.01:
            move_dir.normalize()
        target_speed = self.walk_speed
        self.current_speed += (target_speed - self.current_speed) * 0.1
        self.own.worldPosition += move_dir * self.current_speed
        if move_dir.length > 0.01:
            target_angle = math.atan2(move_dir.y, move_dir.x) + math.pi/2
            current_angle = self.own.worldOrientation.to_euler().z
            diff = (target_angle - current_angle + math.pi) % (2*math.pi) - math.pi
            self.own.worldOrientation = [0, 0, current_angle + diff * 0.2]
        # Selection of animation based on real speed
        if self.current_speed > self.walk_speed * 1.2:
            self.play_animation(ANIM_RUNNING, ACTION_MODE_LOOP)
        elif self.current_speed > 0.01:
            self.play_animation(ANIM_WALKING, ACTION_MODE_LOOP)
        else:
            self.play_animation(ANIM_IDLE, ACTION_MODE_LOOP)

    # -------------------------------------------------------------------------
    # INTELLIGENT NAVIGATION WITH WALL-FOLLOWING
    # -------------------------------------------------------------------------
    def _probe_side(self, side_sign):
        """Fires a lateral Ray to check if that side is free.
        Returns True if the side is clear."""
        side_vec = Vector([side_sign, 0, 0])
        side_vec = self.own.worldOrientation @ side_vec
        side_vec.z = 0
        if side_vec.length < 0.01:
            return True
        side_vec.normalize()
        # MODIFICATION: Increase lateral sounding distance to 3.0 (previously 1.2)
        probe_end = self.own.worldPosition + side_vec * 3.0
        result = self.own.rayCast(probe_end, self.own.worldPosition,
                                  3.5, "col", 0, 0, 0)
        return result[0] is None

    def _choose_evade_side(self, target_pos):
        """Chooses the evasion side that minimizes angle toward target."""
        # MODIFICATION: Maintain the evasion side for a minimum time
        if self.nav_evading and self._evade_side_lock_timer > 0:
            self._evade_side_lock_timer -= self.dt
            return self.nav_evade_side

        right_free = self._probe_side(1)
        left_free  = self._probe_side(-1)

        if right_free and not left_free:
            chosen = 1
        elif left_free and not right_free:
            chosen = -1
        else:
            to_target = target_pos - self.own.worldPosition
            to_target.z = 0
            right_vec = Vector([1, 0, 0])
            right_vec = self.own.worldOrientation @ right_vec
            right_vec.z = 0

            if to_target.length > 0.01 and right_vec.length > 0.01:
                dot = to_target.normalized().dot(right_vec.normalized())
                chosen = 1 if dot >= 0 else -1
            else:
                chosen = random.choice([1, -1])

        # Reset steering lock
        self._evade_side_lock_timer = self._evade_side_lock_duration
        return chosen

    def navigate_towards(self, target_pos, speed):
        """
        Intelligent navigation: uses raycast to target to decide if obstacle blocks the way.
        If obstacle found, activates wall-following (blend lateral + forward).
        If path clear, moves directly using move_towards.
        Returns True when target reached (only if direct movement and arrived).
        """
        my_pos = self.own.worldPosition
        to_target = target_pos - my_pos
        to_target.z = 0
        distance = to_target.length

        # -- If very close, consider arrived (to allow attack state) --------
        if distance < 0.8:
            return False

        # -- Stuck detection ------------------------------------------------
        if self.nav_last_pos is not None:
            moved = (my_pos - self.nav_last_pos).length
            if moved < 0.02:
                self.nav_stuck_timer += self.dt
            else:
                self.nav_stuck_timer = 0.0
        self.nav_last_pos = my_pos.copy()
        stuck = self.nav_stuck_timer >= self.nav_stuck_threshold

        # -- Raycast to target to check for obstacles -----------------------
        start = my_pos.copy()
        end = target_pos.copy()
        start.z += 0.5
        end.z += 0.5
        hit_obj, _, _ = self.own.rayCast(end, start, 0, "col", 0, 0, 0)
        obstacle = hit_obj is not None

        # Also check forward sensor for very close walls (optional)
        ray_sensor = self.cont.sensors.get("Ray.Col")
        front_wall = ray_sensor and ray_sensor.positive
        # MODIFICACIÓN: Usar también check_ray_obstacle() para mayor sensibilidad
        front_ray_obstacle = self.check_ray_obstacle()

        # Hysteresis: keep evading a bit after obstacle disappears
        if obstacle or front_wall or front_ray_obstacle:
            self._evasion_hold_timer = 0.2
        else:
            if self._evasion_hold_timer > 0:
                self._evasion_hold_timer -= self.dt
                obstacle = True

        # -- Direct movement if path clear and not stuck -------------------
        if not obstacle and not stuck:
            if self.nav_evading:
                debug_log("Path clear -> direct movement")
                self.nav_evading = False
                self.nav_evade_timer = 0.0
                self.nav_stuck_timer = 0.0
                self._evade_side_lock_timer = 0.0
            self.rotate_towards(target_pos, turn_speed=0.15)
            return self.move_towards(target_pos, speed)

        # -- Activate evasion mode ------------------------------------------
        if not self.nav_evading or stuck:
            self.nav_evade_side = self._choose_evade_side(target_pos)
            self.nav_evading = True
            self.nav_evade_timer = 0.0
            self.nav_stuck_timer = 0.0
            debug_log(f"Evasion activated, side {'right' if self.nav_evade_side==1 else 'left'}")

        self.nav_evade_timer += self.dt
        if self.nav_evade_timer >= self.nav_evade_timeout:
            self.nav_evade_side = -self.nav_evade_side
            self.nav_evade_timer = 0.0
            self._evade_side_lock_timer = 0.0  # reset lock on forced switch
            debug_log("Evasion timeout, switching side")

        # -- Compute movement direction (blend lateral + forward) ----------
        if distance < 0.01:
            forward_dir = self.own.worldOrientation.col[1]
        else:
            forward_dir = to_target.normalized()

        side_vec = Vector([self.nav_evade_side, 0, 0])
        side_vec = self.own.worldOrientation @ side_vec
        side_vec.z = 0
        if side_vec.length < 0.01:
            side_vec = Vector([self.nav_evade_side, 0, 0])
        else:
            side_vec.normalize()

        blend_ratio = 0.6
        move_dir = side_vec * blend_ratio + forward_dir * (1 - blend_ratio)
        if move_dir.length > 0.01:
            move_dir.normalize()
        else:
            move_dir = forward_dir

        self._last_move_dir = move_dir

        # -- Smooth speed control -------------------------------------------
        ease_factor = min(1.0, distance / 1.5)
        target_speed = speed * max(0.3, ease_factor)
        self.current_speed += (target_speed - self.current_speed) * 0.1

        # -- Move the cat ---------------------------------------------------
        self.own.worldPosition += move_dir * self.current_speed

        # -- Rotate towards movement direction -----------------------------
        if move_dir.length > 0.01:
            target_angle = math.atan2(move_dir.y, move_dir.x) + math.pi/2
            current_angle = self.own.worldOrientation.to_euler().z
            diff = (target_angle - current_angle + math.pi) % (2*math.pi) - math.pi
            self.own.worldOrientation = [0, 0, current_angle + diff * 0.2]

        return False

    def _reset_combat_state(self):
        """Clears all combat and navigation state at once."""
        self.current_enemy    = None
        self.pet_combat_state = PET_COMBAT_NONE
        self.nav_evading      = False
        self.nav_evade_timer  = 0.0
        self.nav_stuck_timer  = 0.0
        self._combat_no_progress_timer = 0.0
        self._combat_check_accum       = 0.0
        self._combat_last_dist         = None
        self._enemy_not_visible_timer  = 0.0
        self._evade_side_lock_timer    = 0.0

    def _check_combat_abandon(self, is_pet_mode=False):
        """Checks if the cat should give up on the current enemy."""
        if not self.current_enemy or self.current_enemy.invalid:
            return False

        visible = self.is_enemy_visible(self.current_enemy)
        if not visible:
            self._enemy_not_visible_timer += self.dt
            timeout = self.combat_abandon_timeout
            if is_pet_mode and self.pet_follow_player and not self.pet_follow_player.invalid:
                dist_player = (self.own.worldPosition - self.pet_follow_player.worldPosition).length
                if dist_player > self.pet_abandon_distance:
                    timeout = self.pet_abandon_timeout_far
            if self._enemy_not_visible_timer >= timeout:
                debug_log(f"Combat abandonment: enemy not visible for {self._enemy_not_visible_timer:.1f}s")
                self._reset_combat_state()
                return True
        else:
            self._enemy_not_visible_timer = 0.0

        current_dist = (self.own.worldPosition - self.current_enemy.worldPosition).length
        self._combat_check_accum += self.dt
        if self._combat_check_accum >= self._combat_check_interval:
            self._combat_check_accum = 0.0
            if self._combat_last_dist is None:
                self._combat_last_dist = current_dist
            else:
                progress = self._combat_last_dist - current_dist
                if progress >= self._combat_progress_min:
                    self._combat_no_progress_timer = 0.0
                    debug_log(f"Combat progress: -{progress:.2f}u")
                else:
                    self._combat_no_progress_timer += self._combat_check_interval
                    debug_log(f"No progress ({progress:.2f}u) -> abandon timer: {self._combat_no_progress_timer:.1f}s")
                self._combat_last_dist = current_dist

        timeout = self.combat_abandon_timeout
        if is_pet_mode and self.pet_follow_player and not self.pet_follow_player.invalid:
            dist_player = (self.own.worldPosition - self.pet_follow_player.worldPosition).length
            if dist_player > self.pet_abandon_distance:
                timeout = self.pet_abandon_timeout_far

        if self._combat_no_progress_timer >= timeout:
            debug_log(f"Combat abandonment due to lack of progress after {self._combat_no_progress_timer:.1f}s")
            self._reset_combat_state()
            return True

        return False

    # -------------------------------------------------------------------------
    # SWIRL EFFECT METHODS
    # -------------------------------------------------------------------------
    def activate_swirl_effect(self):
        """Activa el efecto de remolino en la posición actual del gato."""
        if not self.swirl_effect:
            return
        
        # Move to the cat's position (slightly elevated for better visibility)
        effect_pos = self.own.worldPosition.copy()
        effect_pos.z += 0.3  # levantar un poco del suelo
        self.swirl_effect.worldPosition = effect_pos
        
        # Play animation (once only) - syntax corrected for UPBGE
        try:
            # Stop any previous animation
            if hasattr(self.swirl_effect, 'isPlayingAction') and self.swirl_effect.isPlayingAction():
                self.swirl_effect.stopAction()
            
            # Correct method for UPBGE 0.36/0.44
            # playAction(name, start_frame, end_frame, layer=0, priority=0, blendin=0, play_mode=0, speed=1.0)
            self.swirl_effect.playAction(
                "Swirl_EffectAction",  # name of the action Swirl_EffectAction, Uncollected_EffectAction.002
                1,                     # start_frame
                17,                    # end_frame
                0,                     # layer
                0,                     # priority
                0,                     # blendin
                0,                     # play_mode (0 = play once)
                1.0                    # speed
            )
        except Exception as e:
            debug_error(f"Error playing swirl animation: {e}")
            traceback.print_exc()
        
        # Activate timer
        self.swirl_effect_active = True
        self.swirl_effect_timer = self.swirl_anim_duration
        
        # Ensure the object is visible
        self.swirl_effect.setVisible(True)
        debug_log("Swirl effect activated at cat position")

    def update_swirl_effect(self):
        """Actualiza el temporizador del efecto y lo oculta al terminar."""
        if not self.swirl_effect or not self.swirl_effect_active:
            return
        
        self.swirl_effect_timer -= self.dt
        if self.swirl_effect_timer <= 0:
            # Hide off-camera (Y-axis = -500)
            self.swirl_effect.worldPosition = Vector((0.0, -500.0, 0.0))
            self.swirl_effect_active = False
            # Stop animation if it is still playing
            if hasattr(self.swirl_effect, 'isPlayingAction') and self.swirl_effect.isPlayingAction():
                self.swirl_effect.stopAction()
            debug_log("Swirl effect hidden")

    # -------------------------------------------------------------------------
    # PET BEHAVIOR
    # -------------------------------------------------------------------------
    def update_pet_behavior(self):
        if not self.pet_mode:
            return

        self.pet_timer -= self.dt

        game = game_access.get_game()
        if game and game.state and game.state.cat_pet_active:
            game.state.cat_pet_timer = self.pet_timer

        if self.pet_timer <= 0:
            self.deactivate_pet_mode()
            return

        self.set_visibility(True)

        # Wall collision gentle knockback (only if stuck)
        wall_coll = self.cont.sensors.get("Collision.Col")
        if wall_coll and wall_coll.positive:
            if self.nav_stuck_timer > 0.2:
                back_dir = -self.own.worldOrientation.col[1]
                if back_dir.length > 0.01:
                    back_dir.normalize()
                    self.own.worldPosition += back_dir * 0.08

        # Enemy collision
        enemy_coll = self.cont.sensors.get("Collision.Enemy")
        if enemy_coll and enemy_coll.positive:
            hit = enemy_coll.hitObject
            if hit and not hit.invalid and "enemy" in hit.getPropertyNames():
                self.current_enemy = hit
                self.pet_combat_state = PET_COMBAT_ATTACKING
                debug_log("[PET] Collision with enemy -> ATTACKING")

        if self.pet_combat_state == PET_COMBAT_ATTACKING:
            self._pet_state_attacking()
            return
        if self.pet_combat_state == PET_COMBAT_CHASING:
            self._pet_state_chasing()
            return

        visible_enemy = self.get_visible_enemy()
        if visible_enemy:
            if visible_enemy != self.current_enemy:
                self._combat_no_progress_timer = 0.0
                self._combat_check_accum = 0.0
                self._combat_last_dist = None
                self._enemy_not_visible_timer = 0.0
            self.current_enemy = visible_enemy
            self.pet_combat_state = PET_COMBAT_CHASING
            debug_log("[PET] Visible enemy -> CHASING")
            self._pet_state_chasing()
            return

        self._pet_follow_player()

    def _pet_state_attacking(self):
        self.set_visibility(True)
        self.alertness = min(1.0, self.alertness + 0.3 * self.dt)
        self.was_in_combat = True
        self.play_animation(ANIM_ATTACK, ACTION_MODE_PLAY)
        self.attack_cooldown -= self.dt

        if self.current_enemy and not self.current_enemy.invalid:
            if self.is_enemy_visible(self.current_enemy):
                if self.attack_cooldown <= 0:
                    # Play attack sound
                    bge.logic.sendMessage("sound_fx.play", "sound_fx.play|cat_attack.ogg")
                    # Activate swirl effect
                    self.activate_swirl_effect()
                    props = self.current_enemy.getPropertyNames()
                    if "life" in props:
                        self.current_enemy["life"] -= self.attack_damage
                        self.attack_cooldown = self.attack_interval
                        if self.current_enemy["life"] <= 0:
                            debug_log("[PET] Enemy eliminated")
                            self.current_enemy.endObject()
                            self.current_enemy = None
                            self.pet_combat_state = PET_COMBAT_NONE
                            self.transition_timer = 1.0
                    else:
                        self.current_enemy.endObject()
                        self.current_enemy = None
                        self.pet_combat_state = PET_COMBAT_NONE
                        self.transition_timer = 0.5
            else:
                debug_log("[PET] Enemy not visible during attack -> chase")
                self.pet_combat_state = PET_COMBAT_CHASING
                return
        else:
            self.current_enemy = None
            self.pet_combat_state = PET_COMBAT_NONE

        if self.transition_timer > 0:
            self.transition_timer -= self.dt
            self.play_animation(ANIM_IDLE, ACTION_MODE_LOOP)
            if self.transition_timer <= 0:
                self.current_enemy = None
                self.pet_combat_state = PET_COMBAT_NONE

    def _pet_state_chasing(self):
        self.set_visibility(True)
        self.alertness = min(1.0, self.alertness + 0.1 * self.dt)
        self.was_in_combat = True

        if not self.current_enemy or self.current_enemy.invalid:
            visible = self.get_visible_enemy()
            if visible:
                if visible != self.current_enemy:
                    self.nav_evading = False
                    self.nav_evade_timer = 0.0
                    self.nav_stuck_timer = 0.0
                    self._combat_no_progress_timer = 0.0
                    self._combat_check_accum = 0.0
                    self._combat_last_dist = None
                    self._enemy_not_visible_timer = 0.0
                self.current_enemy = visible
            else:
                debug_log("[PET] No visible enemies -> follow player")
                self._reset_combat_state()
                return

        if not self.is_enemy_visible(self.current_enemy):
            debug_log("[PET] Enemy not visible, abandoning chase")
            self._reset_combat_state()
            return

        if self._check_combat_abandon(is_pet_mode=True):
            debug_log("[PET] Abandon combat, resuming follow")
            return

        enemy_pos = self.current_enemy.worldPosition
        self.navigate_towards(enemy_pos, self.run_speed)
        self.play_animation(ANIM_RUNNING, ACTION_MODE_LOOP)

        self.angry_cooldown -= self.dt
        if self.angry_cooldown <= 0:
            bge.logic.sendMessage("sound_fx.play", "sound_fx.play|cat_angry.ogg")
            self.angry_cooldown = random.uniform(*self.angry_interval_range)

    def _pet_follow_player(self):
        """Follow the player in pet mode. The animation is selected based on the actual speed."""
        pet_sensor = self.cont.sensors.get("Near.Pet")
        if pet_sensor and pet_sensor.positive:
            for obj in pet_sensor.hitObjectList:
                if obj.get("player", False) or obj.name == "Player":
                    self.pet_follow_player = obj
                    break

        player_obj = self.pet_follow_player
        if not player_obj or player_obj.invalid:
            self.current_speed = 0
            self.play_animation(ANIM_IDLE, ACTION_MODE_LOOP)
            return

        distance = (self.own.worldPosition - player_obj.worldPosition).length

        # MODIFICATION: Use navigate_towards instead of evade_obstacle when there is an obstacle
        if self.check_ray_obstacle():
            self.navigate_towards(player_obj.worldPosition, self.walk_speed)
            return

        # Decide movement based on distance
        if distance > self.pet_max_distance:
            if distance > 4.0:
                self.rotate_towards(player_obj.worldPosition, turn_speed=0.2)
                self.move_towards(player_obj.worldPosition, self.run_speed)
            else:
                self.rotate_towards(player_obj.worldPosition, turn_speed=0.15)
                self.move_towards(player_obj.worldPosition, self.walk_speed)
        elif distance < self.pet_min_distance:
            direction = self.own.worldPosition - player_obj.worldPosition
            direction.z = 0
            if direction.length > 0.1:
                direction.normalize()
                self.own.worldPosition += direction * self.walk_speed * 0.5
                self.rotate_towards(self.own.worldPosition + direction, turn_speed=0.15)
        else:
            # Maintain zero speed if within range
            self.current_speed = 0

        # Animation selection based on actual speed
        if self.current_speed > self.walk_speed * 1.2:
            self.play_animation(ANIM_RUNNING, ACTION_MODE_LOOP)
        elif self.current_speed > 0.01:
            self.play_animation(ANIM_WALKING, ACTION_MODE_LOOP)
        else:
            self.play_animation(ANIM_IDLE, ACTION_MODE_LOOP)

    def update_return_to_patrol(self):
        if not self.returning_to_patrol:
            return
        if not self.patrol_return_target:
            self.returning_to_patrol = False
            self.current_state = STATE_PATROLLING
            return

        distance = (self.own.worldPosition - self.patrol_return_target.worldPosition).length

        # MODIFICATION: Also use navigate_towards for the return when there is an obstacle
        if self.check_ray_obstacle():
            self.navigate_towards(self.patrol_return_target.worldPosition, self.walk_speed)
            return

        self.rotate_towards(self.patrol_return_target.worldPosition, turn_speed=0.08)
        self.set_visibility(True)

        if distance < 0.5:
            self.returning_to_patrol = False
            self.current_state = STATE_PATROLLING
            self.target_empty = self.empty_b
            self.own.worldPosition = self.patrol_return_target.worldPosition.copy()
        else:
            self.move_towards(self.patrol_return_target.worldPosition, self.walk_speed)
            # During the return trip, always use walking (low speed)
            self.play_animation(ANIM_WALKING, ACTION_MODE_LOOP)

    # =========================================================================
    # STATE MACHINE WITH PRIORITIES
    # =========================================================================
    def determine_next_state(self):
        if self.pet_mode:
            return STATE_PET

        visible_enemy = self.get_visible_enemy()
        if visible_enemy:
            if self.current_enemy and not self.current_enemy.invalid and self.current_enemy == visible_enemy:
                return self.current_state if self.current_state in (STATE_CHASING, STATE_ATTACKING) else STATE_CHASING
            else:
                self.current_enemy = visible_enemy
                return STATE_CHASING

        near_player = self.cont.sensors.get("Near.Player")
        if near_player and near_player.positive and self.was_activated:
            return STATE_INTERACT

        actv = self.cont.sensors.get("Near.Actv")
        if actv and actv.positive:
            self.was_activated = True
            self.player_far_timer = 0
            return STATE_PATROLLING

        self.was_activated = False
        return STATE_INACTIVE

    def update_state(self):
        new_state = self.determine_next_state()
        if new_state != self.current_state and self.transition_timer <= 0:
            debug_state_change(self.current_state, new_state)
            self.current_state = new_state

        if self.current_state == STATE_INACTIVE:
            self.player_far_timer += self.dt
            if self.player_far_timer >= self.player_far_threshold:
                self.was_activated = False

        return self.current_state

    def update_mood(self):
        self.alertness = max(0, self.alertness - 0.02 * self.dt)
        if self.alertness < 0.05:
            self.was_in_combat = False
        self.comfort += (0.5 - self.comfort) * 0.01 * self.dt

    def state_inactive(self):
        self.set_visibility(False)
        self.stop_animation()
        self.current_enemy = None
        self.nav_evading = False
        self.nav_evade_timer = 0.0
        self.nav_stuck_timer = 0.0

    def state_patrolling(self):
        self.set_visibility(True)
        if not self.empty_a or not self.empty_b:
            return
        if self.empty_a.invalid or self.empty_b.invalid:
            self.current_state = STATE_INACTIVE
            return

        self.pause_timer += self.dt

        if self.micro_pause_timer > 0:
            self.micro_pause_timer -= self.dt
            self.play_animation(ANIM_IDLE, ACTION_MODE_LOOP)
            return

        if self.grooming_timer > 0:
            self.play_animation(ANIM_GROOMING, ACTION_MODE_LOOP)
            self.grooming_timer -= self.dt
            if self.grooming_timer <= 0:
                self.schedule_next_pause()
        elif self.pause_timer >= self.next_pause_time:
            self.grooming_timer = random.uniform(3.0, 7.0)
            self.play_animation(ANIM_GROOMING, ACTION_MODE_LOOP)
        else:
            if random.random() < 0.002:
                self.micro_pause_timer = random.uniform(0.5, 1.5)
                return
            self.rotate_towards(self.target_empty.worldPosition, turn_speed=0.08)
            patrol_speed = self.walk_speed * (1.0 + self.alertness * 0.4)
            arrived = self.move_towards(self.target_empty.worldPosition, patrol_speed)
            self.play_animation(ANIM_WALKING, ACTION_MODE_LOOP)
            if arrived:
                self.is_moving_to_a = not self.is_moving_to_a
                self.target_empty = self.empty_a if self.is_moving_to_a else self.empty_b

    def state_interact(self):
        self.set_visibility(True)
        self.comfort = min(1.0, self.comfort + 0.05 * self.dt)

        self.interact_timer += self.dt
        if self.interact_timer > self.interact_change_time:
            self.interact_timer = 0
            self.interact_change_time = random.uniform(3, 5)
            self.interact_anim = ANIM_GROOMING if self.interact_anim == ANIM_IDLE else ANIM_IDLE

        self.play_animation(self.interact_anim, ACTION_MODE_LOOP)

        if not self.pet_mode:
            self.meow_cooldown -= self.dt
            if self.meow_cooldown <= 0:
                bge.logic.sendMessage("sound_fx.play", "sound_fx.play|cat_meow.ogg|volume=0.2|loop=0")
                self.meow_cooldown = random.uniform(*self.meow_interval_range)

    def state_chasing(self):
        self.set_visibility(True)
        self.alertness = min(1.0, self.alertness + 0.1 * self.dt)
        self.was_in_combat = True

        # Verify that the enemy remains valid and visible
        if not self.current_enemy or self.current_enemy.invalid:
            visible = self.get_visible_enemy()
            if visible:
                self.current_enemy = visible
            else:
                self._reset_combat_state()
                self.current_state = STATE_PATROLLING
                return

        # If the enemy is not visible, abandon chasing
        if not self.is_enemy_visible(self.current_enemy):
            debug_log("Enemy not visible, returning to patrol")
            self.current_state = STATE_PATROLLING
            return

        # If it's very close, switch to attack
        dist_to_enemy = (self.own.worldPosition - self.current_enemy.worldPosition).length
        if dist_to_enemy < 0.8:
            self.current_state = STATE_ATTACKING
            return

        # Soft knockback only if stuck
        wall_coll = self.cont.sensors.get("Collision.Col")
        if wall_coll and wall_coll.positive:
            if self.nav_stuck_timer > 0.2:
                back_dir = -self.own.worldOrientation.col[1]
                if back_dir.length > 0.01:
                    back_dir.normalize()
                    self.own.worldPosition += back_dir * 0.08

        # Abandonment due to lack of progress
        if self._check_combat_abandon(is_pet_mode=False):
            self.current_state = STATE_PATROLLING
            return

        enemy_pos = self.current_enemy.worldPosition
        self.navigate_towards(enemy_pos, self.run_speed)
        self.play_animation(ANIM_RUNNING, ACTION_MODE_LOOP)

        self.angry_cooldown -= self.dt
        if self.angry_cooldown <= 0:
            bge.logic.sendMessage("sound_fx.play", "sound_fx.play|cat_angry.ogg")
            self.angry_cooldown = random.uniform(*self.angry_interval_range)

    def state_attacking(self):
        self.set_visibility(True)
        self.alertness = min(1.0, self.alertness + 0.3 * self.dt)
        self.was_in_combat = True

        # Handle transition (for example, after killing an enemy)
        if self.transition_timer > 0:
            self.transition_timer -= self.dt
            self.play_animation(ANIM_IDLE, ACTION_MODE_LOOP)
            if self.transition_timer <= 0:
                self.current_enemy = None
                self.current_state = STATE_PATROLLING
                debug_log("Attack transition finished, returning to patrol")
            return

        # If there is no enemy or he is incapacitated, leave immediately
        if not self.current_enemy or self.current_enemy.invalid:
            self.current_enemy = None
            self.current_state = STATE_PATROLLING
            debug_log("No enemy, exiting attack state")
            return

        # Check visibility
        if not self.is_enemy_visible(self.current_enemy):
            debug_log("Enemy not visible during attack -> chasing")
            self.current_state = STATE_CHASING
            return

        # Play attack animation
        self.play_animation(ANIM_ATTACK, ACTION_MODE_PLAY)
        self.attack_cooldown -= self.dt

        # Perform attack if available
        if self.attack_cooldown <= 0:
            # Attack sound
            bge.logic.sendMessage("sound_fx.play", "sound_fx.play|cat_attack.ogg")
            # Activate swirl effect
            self.activate_swirl_effect()
            props = self.current_enemy.getPropertyNames()
            if "life" in props:
                self.current_enemy["life"] -= self.attack_damage
                self.attack_cooldown = self.attack_interval
                if self.current_enemy["life"] <= 0:
                    debug_log("Enemy eliminated, starting transition to patrol")
                    self.current_enemy.endObject()
                    self.current_enemy = None
                    self.transition_timer = 1.0
            else:
                # Enemy without life, eliminate it immediately
                debug_log("Enemy eliminated (no life property), starting transition")
                self.current_enemy.endObject()
                self.current_enemy = None
                self.transition_timer = 0.5

    # =========================================================================
    # MAIN LOOP
    # =========================================================================
    def update(self):
        try:
            self.update_mood()

            game = game_access.get_game()
            if game and game.state:
                if game.state.cat_pet_active and not self.pet_mode:
                    self.pet_mode = True
                    self.pet_timer = game.state.cat_pet_timer
                    self.pet_combat_state = PET_COMBAT_NONE
                    self.current_state = STATE_PET
                elif not game.state.cat_pet_active and self.pet_mode:
                    self.deactivate_pet_mode()

            if self.pet_mode:
                self.update_pet_behavior()
                # Update swirl effect even in pet mode
                self.update_swirl_effect()
                return

            if self.returning_to_patrol:
                self.update_return_to_patrol()
                self.update_swirl_effect()
                return

            self.update_state()

            state_handlers = {
                STATE_INACTIVE:   self.state_inactive,
                STATE_PATROLLING: self.state_patrolling,
                STATE_INTERACT:   self.state_interact,
                STATE_CHASING:    self.state_chasing,
                STATE_ATTACKING:  self.state_attacking,
            }
            handler = state_handlers.get(self.current_state)
            if handler:
                handler()

            # Update swirl effect (if active)
            self.update_swirl_effect()

            self.frame_count += 1

        except Exception as e:
            debug_error(f"Error in update: {e}")
            traceback.print_exc()

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main(cont):
    try:
        if "npc_cat" not in cont.owner:
            cont.owner["npc_cat"] = NPC_Cat(cont)

        npc = cont.owner["npc_cat"]

        npc.handle_mouse_over()

        mouse_click = cont.sensors.get("Mouse.Click")
        mouse_over  = cont.sensors.get("Mouse.Over")

        click_on_cat = (
            mouse_click and mouse_click.positive and
            mouse_over  and mouse_over.positive
        )

        if click_on_cat:
            debug_log("Mouse.Click detected ON the cat")
            game_flag  = game_access.get_game()
            just_picked = False
            if game_flag and game_flag.state:
                just_picked = getattr(game_flag.state, "cat_food_just_picked", False)
                game_flag.state.cat_food_just_picked = False

            if just_picked:
                debug_log("Click ignored: food just picked")
            else:
                current_time = bge.logic.getRealTime()
                if current_time - npc.last_mouse_click_time >= 0.3:
                    npc.last_mouse_click_time = current_time

                    cat_food = game_access.get_cat_food_items()

                    if cat_food <= 0:
                        message = "info.show|info_text|34|field=info_text"
                        npc.own.sendMessage("add_info_text", message, "Game.Controller")
                    else:
                        message = "info.show|info_text|35|field=info_text"
                        npc.own.sendMessage("add_info_text", message, "Game.Controller")
                        npc.activate_pet_mode()

        npc.update()

    except Exception as e:
        debug_error(f"Error in main: {e}")
        traceback.print_exc()