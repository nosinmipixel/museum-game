"""
npc_restoration_logic.py

Restoration NPC logic with near sensors and Working animation

This script manages the Restoration NPC (NPC11) logic including sequential quiz
assignment, restoration queue management, player proximity detection via sensors,
rotation toward player, and animation state management.

Main Features:
    1. Sequential quiz assignment (q101 to q105) for restoration items
    2. Restoration queue with attempt tracking (max 3 attempts per item)
    3. Proximity detection using Near sensors for dialog and animation ranges
    4. Smooth rotation toward player when in dialog range
    5. Idle animation when objects need restoration, Working animation when none
    6. Phone notification system with multi-step messages
    7. Retry delay system with automatic reactivation
    8. Result capture and processing from restoration dialog

Setup:
    Connect in Logic Bricks as Python controller/module 'npc_restoration_logic.main'
    NPC object requires sensors:
        - Near_Dialog: property='player', Distance=2.0, Reset=4.0
        - Near_Anim: property='player', Distance=5.0, Reset=7.0
        - Message (for activation messages)

Configurable Variables:
    DEBUG (bool): Enable debug messages (default: False)
    DEBUG_VERBOSITY (int): 1=info, 2=detailed, 3=very detailed
    SUPPRESS_ALL_LOGS (bool): Disable all logging (default: False)
    RESTORATION_MAX_ATTEMPTS (int): Max attempts per item (default: 3)
    RETRY_DELAY (float): Seconds before retry (default: 5.0)
    ACTIVATION_DELAY (float): Delay before reactivation (default: 3.0)

Notes:
    - Requires game_access module for game state and inventory
    - Quiz IDs follow pattern: q101 (quiz 1), q102 (quiz 2), ... q105 (quiz 5)
    - Scene IDs: 31-33 (quiz 1), 34-36 (quiz 2), etc.
    - Message format for activation: "restoration_npc|activate|item_type=X|item_id=Y"

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
__description__ = "Restoration NPC logic with sequential quizzes and proximity sensors"

# =============================================================================
# IMPORTS AND CONFIGURATION
# =============================================================================
import bge
from bge import logic
import game_access
import math
import time

RESTORATION_MAX_ATTEMPTS = 3
RETRY_DELAY = 5.0
ACTIVATION_DELAY = 3.0

DEBUG = False
DEBUG_VERBOSITY = 1
SUPPRESS_ALL_LOGS = False

def debug_print(level, message):
    if SUPPRESS_ALL_LOGS:
        return
    if level <= DEBUG_VERBOSITY and DEBUG:
        print(f"[NPC11-L{level}] {message}")

# =============================================================================
# RESTORATION NPC LOGIC CLASS
# =============================================================================
class RestorationNPCLogic:
    def __init__(self, owner):
        self.owner = owner
        self.npc_id = 11
        
        # Sequential quiz system
        self.next_quiz_number = 1
        self.max_quiz_number = 5
        self.assigned_quizzes = {}
        
        # States and notification
        self.current_state = "WAITING"
        self.notification_step = 0
        self.notification_timer = 0
        self.has_notified = False
        
        # OPTIMIZATION: Proximity flags (controlled by Near sensors)
        self.player_in_dialog_range = False    # Near_Dialog (2.0m / 4.0m)
        self.player_in_anim_range = False      # Near_Anim (5.0m / 7.0m)
        self.cached_player = None              # Cached player reference
        
        # ANIMATION WORKING: Flag to control when to show Working
        self.showing_working_anim = False
        self.working_anim_started = False
        
        # OPTIMIZATION: Rotation cache
        self.last_player_pos = None
        self.rotation_update_threshold = 0.1   # Minimum squared distance for rotation update
        
        # Rotation (parameters preserved)
        self.rotation_speed = 5.0
        self.rotation_max_distance = 15.0
        self.rotation_min_distance = 0.5
        
        # Dialog
        self.dialog_started = False
        self.dialog_start_time = 0
        self.min_dialog_duration = 2.0
        
        # Restoration system
        self.restoration_queue = []
        self.current_restoration_item = None
        self.attempts = {}
        self.retry_timers = {}
        self.active_restoration = False
        self.last_notification_time = 0
        
        # Result capture system
        self.awaiting_retry = False
        self.captured_quiz_result = None
        self.quiz_result_processed = False
        
        # Interaction
        self.manual_interaction_allowed = False
        self.interaction_cooldown = 0
        
        # Properties
        self.owner["has_objects_to_restore"] = False
        self.owner["restoration_available"] = False
        self.owner["restoration_in_progress"] = False
        
        self.owner.setVisible(False)
        
        if not SUPPRESS_ALL_LOGS:
            debug_print(1, "Initialized with Near sensor optimization")

    # =========================================================================
    # NEAR SENSOR MANAGEMENT
    # =========================================================================
    
    def update_from_sensors(self, near_dialog, near_anim):
        """Update proximity flags based on Near sensors
        
        IMPORTANT: In UPBGE, Near sensors only have .positive attribute
        """
        # Variables to store previous state (to detect transitions)
        if not hasattr(self, '_prev_dialog_state'):
            self._prev_dialog_state = False
        if not hasattr(self, '_prev_anim_state'):
            self._prev_anim_state = False
        
        # Near_Dialog sensor (dialog and rotation range)
        if near_dialog:
            current_dialog_state = near_dialog.positive
            
            # Detect transitions using comparison with previous state
            if current_dialog_state and not self._prev_dialog_state:
                # Player ENTERED dialog range
                self.player_in_dialog_range = True
                # Find player among activated objects
                for obj in near_dialog.hitObjectList:
                    if hasattr(obj, 'get') and obj.get('player', False):
                        self.cached_player = obj
                        break
                if not SUPPRESS_ALL_LOGS:
                    debug_print(2, "Player entered dialog range (2.0m)")
            
            elif not current_dialog_state and self._prev_dialog_state:
                # Player EXITED dialog range
                self.player_in_dialog_range = False
                if not SUPPRESS_ALL_LOGS:
                    debug_print(2, "Player exited dialog range (4.0m)")
            
            # Update previous state
            self._prev_dialog_state = current_dialog_state
        
        # Near_Anim sensor (animation range)
        if near_anim:
            current_anim_state = near_anim.positive
            
            # Detect transitions using comparison with previous state
            if current_anim_state and not self._prev_anim_state:
                # Player ENTERED animation range
                self.player_in_anim_range = True
                if not self.cached_player:
                    # Find player among activated objects
                    for obj in near_anim.hitObjectList:
                        if hasattr(obj, 'get') and obj.get('player', False):
                            self.cached_player = obj
                            break
                if not SUPPRESS_ALL_LOGS:
                    debug_print(2, "Player entered animation range (5.0m)")
            
            elif not current_anim_state and self._prev_anim_state:
                # Player EXITED animation range
                self.player_in_anim_range = False
                if not SUPPRESS_ALL_LOGS:
                    debug_print(2, "Player exited animation range (7.0m)")
                
                # If also exited dialog range, clear cache
                if not self.player_in_dialog_range:
                    self.cached_player = None
                    self.last_player_pos = None
            
            # Update previous state
            self._prev_anim_state = current_anim_state

    def get_player_reference(self):
        """Get player reference (optimized with cache)
        
        Returns:
            KX_GameObject: Player reference or None
        """
        # 1. Try using sensor cache
        if self.cached_player:
            # Verify cached object still exists and is valid
            try:
                if self.cached_player.invalid:
                    self.cached_player = None
                else:
                    return self.cached_player
            except:
                self.cached_player = None
        
        # 2. Fallback: search in scene (only if no cache)
        try:
            scene = logic.getCurrentScene()
            player = scene.objects.get("Player")
            if player:
                self.cached_player = player
            return player
        except:
            return None

    # =========================================================================
    # QUIZ AND SCENE ID FUNCTIONS
    # =========================================================================
    
    def get_quiz_for_item(self, item_type, item_id):
        """Assign sequential quizzes from 1 to 5"""
        key = (item_type, item_id)
        
        if key in self.assigned_quizzes:
            quiz_num = self.assigned_quizzes[key]
            quiz_id = f"q10{quiz_num}"
            self.owner["what_quiz"] = quiz_id
            self.owner["current_quiz_num"] = quiz_num
            self.apply_scene_for_item_attempt(key)
            print(f"[NPC11] Reusing quiz {quiz_id} for {item_type}#{item_id}")
            return quiz_id
        
        quiz_num = self.next_quiz_number
        quiz_id = f"q10{quiz_num}"
        
        self.assigned_quizzes[key] = quiz_num
        self.owner["what_quiz"] = quiz_id
        self.owner["current_quiz_num"] = quiz_num
        self.owner["scene_id"] = self.get_scene_for_attempt(quiz_num, 0)
        
        self.next_quiz_number += 1
        if self.next_quiz_number > self.max_quiz_number:
            self.next_quiz_number = 1
        
        print(f"[NPC11] Assigned quiz {quiz_id} (scene {self.owner['scene_id']}) to {item_type}#{item_id}")
        return quiz_id

    def get_scene_for_quiz_number(self, quiz_num):
        """Get scene_id corresponding to quiz number"""
        if 1 <= quiz_num <= 5:
            base_scene = 30 + (quiz_num * 3) - 2
            return base_scene
        return 31

    def get_scene_for_attempt(self, quiz_num: int, attempt_index: int) -> int:
        """Return scene_id for a quiz and attempt"""
        base_scene = self.get_scene_for_quiz_number(quiz_num)
        if attempt_index < 0:
            attempt_index = 0
        if attempt_index > 2:
            attempt_index = 2
        return base_scene + attempt_index

    def _get_current_quiz_num(self) -> int:
        """Get quiz number (1..5) from NPC properties"""
        qn = self.owner.get("current_quiz_num", 0)
        if isinstance(qn, int) and qn:
            return qn
        quiz_id = self.owner.get("what_quiz", "q101")
        try:
            if isinstance(quiz_id, str) and quiz_id.startswith("q"):
                n = int(quiz_id[2:]) - 100
                return n if 1 <= n <= 99 else 0
        except:
            pass
        return 0

    def apply_scene_for_item_attempt(self, key):
        """Apply correct scene_id to NPC for current item and attempt"""
        try:
            quiz_num = self._get_current_quiz_num()
            if not quiz_num:
                return
            try:
                attempt_index = int(self.attempts.get(key, 0))
            except:
                attempt_index = 0
            scene_id = self.get_scene_for_attempt(quiz_num, attempt_index)
            self.owner["scene_id"] = scene_id
            if not SUPPRESS_ALL_LOGS:
                debug_print(1, f"scene_id updated to {scene_id} (quiz {quiz_num}, attempt {attempt_index+1})")
        except:
            pass
    
    def update_npc_scene_id(self, quiz_num):
        """Update NPC scene_id according to quiz number"""
        scene_id = self.get_scene_for_quiz_number(quiz_num)
        self.owner["scene_id"] = scene_id
        self.scene_id = scene_id
        
        if not SUPPRESS_ALL_LOGS:
            debug_print(1, f"scene_id updated to {scene_id} for quiz {quiz_num}")

    # =========================================================================
    # NEW RESULT CAPTURE AND MANAGEMENT METHODS
    # =========================================================================
    
    def capture_quiz_result(self):
        """Capture quiz result BEFORE resetting properties"""
        if self.quiz_result_processed:
            return False
        
        quiz_on = self.owner.get("quiz_on", False)
        quiz_replied = self.owner.get("quiz_reply", False)
        quiz_success = self.owner.get("quiz_success", False)
        
        if quiz_replied:
            self.captured_quiz_result = {
                'replied': True,
                'success': quiz_success,
                'quiz_on': quiz_on,
                'timestamp': time.time()
            }
            
            if not SUPPRESS_ALL_LOGS:
                result_text = "SUCCESS" if quiz_success else "FAILURE"
                debug_print(1, f"Quiz result captured: {result_text}")
            
            return True
        
        return False
    
    def update_scene_id_for_current_item(self):
        """Update scene_id based on current item and its attempts"""
        if not self.current_restoration_item:
            if not SUPPRESS_ALL_LOGS:
                debug_print(2, "No current item - scene_id not updated")
            return None
        
        key = self.current_restoration_item
        quiz_num = self._get_current_quiz_num()
        
        if not quiz_num:
            if not SUPPRESS_ALL_LOGS:
                debug_print(1, "quiz_num not available")
            return None
        
        current_attempts = self.attempts.get(key, 0)
        scene_id = self.get_scene_for_attempt(quiz_num, current_attempts)
        self.owner["scene_id"] = scene_id
        
        if not SUPPRESS_ALL_LOGS:
            debug_print(1, f"scene_id -> {scene_id} (quiz={quiz_num}, attempt={current_attempts+1}/3)")
        
        return scene_id
    
    def reset_dialog_flags(self):
        """Reset all dialog-related flags"""
        self.dialog_started = False
        self.dialog_start_time = 0
        self.quiz_result_processed = False
        self.captured_quiz_result = None
        self._ready_logged = False
        
        if not SUPPRESS_ALL_LOGS:
            debug_print(2, "Dialog flags reset")
    
    def prepare_for_next_attempt(self):
        """Prepare NPC for next attempt after failure"""
        if not self.current_restoration_item:
            return
        
        key = self.current_restoration_item
        current_attempts = self.attempts.get(key, 0)
        
        self.reset_dialog_flags()
        self.update_scene_id_for_current_item()
        
        self.current_state = "DELAYED"
        self.notification_timer = time.time() + RETRY_DELAY
        self.has_notified = False
        self.notification_step = 0
        self.manual_interaction_allowed = False
        self.awaiting_retry = True
        
        self.retry_timers[key] = {
            'retry_time': time.time() + RETRY_DELAY,
            'attempts': current_attempts
        }
        
        if not SUPPRESS_ALL_LOGS:
            debug_print(1, f"Prepared for retry {current_attempts + 1}/3 in {RETRY_DELAY}s")

    # =========================================================================
    # VERIFICATION AND QUEUE
    # =========================================================================
    
    def check_restoration_needed(self):
        """Check if there are objects that need restoration"""
        game = game_access.get_game()
        if not game:
            return False
        
        inventory = game.state.inventory
        collection_items = inventory.get("collection_items", {})
        
        for period, items in collection_items.items():
            for item in items:
                if item.get("restored", 0) == 0:
                    return True
        
        return False

    def get_next_restoration_item(self):
        """Get next object that needs restoration"""
        game = game_access.get_game()
        if not game:
            return None
        
        inventory = game.state.inventory
        collection_items = inventory.get("collection_items", {})
        
        for period, items in collection_items.items():
            for item in items:
                if item.get("restored", 0) == 0:
                    item_type = period
                    item_id = item.get("item_id")
                    key = (item_type, item_id)
                    
                    if key not in self.restoration_queue:
                        return key
        
        return None

    def add_to_restoration_queue(self, item_type, item_id):
        """Add object to restoration queue"""
        key = (item_type, item_id)
        
        if key in self.restoration_queue:
            if not SUPPRESS_ALL_LOGS:
                debug_print(2, f"Already in queue: {item_type}#{item_id}")
            return False
        
        game = game_access.get_game()
        if game:
            inventory = game.state.inventory
            collection_items = inventory.get("collection_items", {})
            
            item_found = False
            for item in collection_items.get(item_type, []):
                if item.get("item_id") == item_id and item.get("restored", 0) == 0:
                    item_found = True
                    break
            
            if not item_found:
                if not SUPPRESS_ALL_LOGS:
                    debug_print(1, f"No restoration needed: {item_type}#{item_id}")
                return False
        
        self.restoration_queue.append(key)
        self.attempts[key] = 0
        
        self.owner["has_objects_to_restore"] = True
        
        if not SUPPRESS_ALL_LOGS:
            debug_print(1, f"Added to queue: {item_type}#{item_id}")
        
        if not self.active_restoration:
            self.start_next_restoration()
        else:
            if not SUPPRESS_ALL_LOGS:
                debug_print(2, f"Waiting: {item_type}#{item_id}")
        
        return True

    # =========================================================================
    # RESTORATION START
    # =========================================================================
    
    def start_next_restoration(self):
        """Start restoration of next object"""
        if not self.restoration_queue:
            self.active_restoration = False
            self.current_restoration_item = None
            self.current_state = "WAITING"
            self.manual_interaction_allowed = False
            self.awaiting_retry = False
            
            self.owner["has_objects_to_restore"] = False
            self.owner["restoration_available"] = False
            self.owner["restoration_in_progress"] = False
            
            if not SUPPRESS_ALL_LOGS:
                debug_print(1, "Queue empty - WAITING")
            
            self.owner.setVisible(False)
            return
        
        self.current_restoration_item = self.restoration_queue[0]
        item_type, item_id = self.current_restoration_item
        
        key = (item_type, item_id)
        current_attempts = self.attempts.get(key, 0)
        is_retry = current_attempts > 0
        
        quiz_id = self.get_quiz_for_item(item_type, item_id)
        quiz_num = self.assigned_quizzes.get((item_type, item_id), 1)
        
        scene_id = self.get_scene_for_attempt(quiz_num, current_attempts)
        self.owner["scene_id"] = scene_id
        
        self.owner["restoration_item_type"] = item_type
        self.owner["restoration_item_id"] = item_id
        self.owner["what_quiz"] = quiz_id

        print(f"[NPC11] Starting restoration of: {item_type}#{item_id} with quiz {quiz_id}")
        print(f"[NPC11] Attempt {current_attempts + 1}/3 - Scene ID: {scene_id} - Is retry: {is_retry}")
        
        # Check if already restored
        game = game_access.get_game()
        if game:
            inventory = game.state.inventory
            collection_items = inventory.get("collection_items", {})
            
            already_restored = False
            for item in collection_items.get(item_type, []):
                if item.get("item_id") == item_id:
                    if item.get("restored", 0) != 0:
                        already_restored = True
                        if not SUPPRESS_ALL_LOGS:
                            debug_print(1, f"Already restored, skipping: {item_type}#{item_id}")
                    break
            
            if already_restored:
                self.remove_from_queue((item_type, item_id))
                self.start_next_restoration()
                return
        
        self.active_restoration = True
        self.has_notified = False
        self.notification_step = 0
        self.manual_interaction_allowed = False
        self._ready_logged = False
        
        if is_retry:
            self.current_state = "DELAYED"
            self.notification_timer = time.time() + ACTIVATION_DELAY
            self.awaiting_retry = True
            self.quiz_result_processed = False
            if not SUPPRESS_ALL_LOGS:
                debug_print(1, f"Retry {current_attempts + 1} - Notifications after delay")
        else:
            self.current_state = "READY"
            self.has_notified = True
            self.manual_interaction_allowed = True
            self.awaiting_retry = False
            self.quiz_result_processed = False
            if not SUPPRESS_ALL_LOGS:
                debug_print(1, "First attempt - Ready immediately (no notifications)")
        
        self.owner["restoration_in_progress"] = True
        
        self.owner.setVisible(True)
        
        if not SUPPRESS_ALL_LOGS:
            debug_print(1, f"Starting restoration for: {item_type}#{item_id}")

    # =========================================================================
    # NOTIFICATIONS
    # =========================================================================
    
    def play_phone_sound(self):
        """Play phone ring sound"""
        try:
            bge.logic.sendMessage("sound_fx.play", "sound_fx.play|telephone_ring.ogg|volume=0.6")
            if not SUPPRESS_ALL_LOGS:
                debug_print(2, "Phone sound")
        except:
            pass

    def send_dialog_message(self, message_key):
        """Send message to display dialog"""
        try:
            controller = logic.getCurrentScene().objects.get("Game.Controller")
            if controller:
                controller.sendMessage('add_text', f'char1_text|{message_key}')
                return True
        except:
            pass
        return False

    def show_phone_notification(self):
        """Show phone notification"""
        current_time = time.time()
        
        if self.notification_step == 0:
            self.play_phone_sound()
            self.send_dialog_message('dialogs.scene101.npc11.0')
            self.notification_step = 1
            self.notification_timer = current_time
            self.last_notification_time = current_time
            if not SUPPRESS_ALL_LOGS:
                debug_print(1, "Notification step 1")
            
        elif self.notification_step == 1:
            if current_time - self.notification_timer >= 10.0:
                self.send_dialog_message('dialogs.scene101.npc11.1')
                self.notification_step = 2
                self.notification_timer = current_time
                if not SUPPRESS_ALL_LOGS:
                    debug_print(1, "Notification step 2")
                
        elif self.notification_step == 2:
            if current_time - self.notification_timer >= 3.0:
                self.send_dialog_message('dialogs.scene101.npc11.2')
                self.notification_step = 3
                self.notification_timer = current_time
                if not SUPPRESS_ALL_LOGS:
                    debug_print(1, "Notification step 3")
                
        elif self.notification_step == 3:
            if current_time - self.notification_timer >= 3.0:
                self.send_dialog_message('dialogs.scene101.npc11.3')
                self.notification_step = 4
                self.notification_timer = current_time
                if not SUPPRESS_ALL_LOGS:
                    debug_print(1, "Notification step 4 (final)")
                
        elif self.notification_step == 4:
            if current_time - self.notification_timer >= 3.0:
                self.has_notified = True
                if not SUPPRESS_ALL_LOGS:
                    debug_print(1, "Notifications completed")

    # =========================================================================
    # ROTATION - OPTIMIZED WITH SENSORS
    # =========================================================================

    def rotate_to_player(self):
        """Rotate NPC toward player - CORRECTED VERSION FOR COMPLETE ROTATION
        
        Only executes if player_in_dialog_range=True (controlled by sensor)
        """
        try:
            # Quick check: is player in range?
            if not self.player_in_dialog_range:
                return False
            
            # Get player reference (cached by sensor)
            player = self.get_player_reference()
            if not player:
                return False
            
            # Check if NPC should rotate (correct state)
            if self.current_state not in ["READY", "INTERACTING"]:
                return False
            
            # Calculate direction toward player
            npc_pos = self.owner.worldPosition.copy()
            player_pos = player.worldPosition.copy()
            
            # Direction vector from NPC to player
            direction = player_pos - npc_pos
            direction.z = 0  # Keep on horizontal plane
            
            # If player is very close, don't rotate
            if direction.length < 0.1:
                return True
            
            # Normalize direction
            direction.normalize()
            
            # CORRECTION: Calculate target angle CORRECTLY
            # In Blender/UPBGE, Y axis is forward for objects
            # Angle is between NPC Y axis and direction to player
            target_angle = math.atan2(-direction.x, direction.y)
            
            # NEW: Convert to degrees for debugging (optional)
            target_angle_deg = math.degrees(target_angle)
            
            # Get current NPC rotation
            current_rotation = self.owner.worldOrientation.to_euler()
            current_angle = current_rotation.z
            
            # CORRECTION: Calculate angle difference CORRECTLY
            angle_diff = target_angle - current_angle
            
            # CRITICAL CORRECTION: Normalize difference between -pi and pi
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            
            # DEBUG: Show angle information
            debug_print(3, f"NPC {self.npc_id}: Current angle: {math.degrees(current_angle):.1f} deg, "
                         f"Target: {target_angle_deg:.1f} deg, Difference: {math.degrees(angle_diff):.1f} deg")
            
            # If already facing correct direction (small threshold)
            if abs(angle_diff) < 0.01:  # ~0.57 degrees
                return True
            
            # CORRECTION: Increase rotation speed for faster turning
            tic_rate = logic.getLogicTicRate()
            if tic_rate == 0:
                tic_rate = 60.0
            
            # INCREASE rotation speed
            rotation_step = self.rotation_speed * 2.0 * (1.0 / tic_rate)  # Double speed
            
            # Apply smoothed rotation
            if abs(angle_diff) < rotation_step:
                new_angle = target_angle
            else:
                # Rotate in shortest direction
                new_angle = current_angle + (rotation_step if angle_diff > 0 else -rotation_step)
            
            # Apply new rotation
            new_rotation = current_rotation.copy()
            new_rotation.z = new_angle
            self.owner.worldOrientation = new_rotation.to_matrix()
            
            # DEBUG: Verify rotation was applied
            new_current = self.owner.worldOrientation.to_euler().z
            new_diff = target_angle - new_current
            
            # Normalize new difference
            while new_diff > math.pi:
                new_diff -= 2 * math.pi
            while new_diff < -math.pi:
                new_diff += 2 * math.pi
                
            debug_print(3, f"NPC {self.npc_id}: New angle: {math.degrees(new_current):.1f} deg, "
                         f"New difference: {math.degrees(new_diff):.1f} deg")
            
            return True
            
        except Exception as e:
            debug_print(1, f"Rotation error NPC {self.npc_id}: {e}")
            return False

    # =========================================================================
    # ANIMATIONS - ENHANCED VERSION WITH WORKING
    # =========================================================================

    def update_animation(self):
        """Update animation based on state and player proximity
        
        - If there are objects to restore: uses Idle animation when player is nearby
        - If NO objects to restore: uses Working animation when player is nearby
        """
        # Only update animation if player is in range
        if not self.player_in_anim_range:
            # If player leaves range, reset Working flag
            self.showing_working_anim = False
            self.working_anim_started = False
            return
        
        try:
            # Get skeleton (first child)
            children = self.owner.children
            if not children or len(children) == 0:
                return
            skeleton = children[0]
            
            # Check if there ARE objects to restore
            has_objects = self.check_restoration_needed()
            
            # CASE 1: There ARE objects to restore - Use Idle animation
            if has_objects:
                # Reset Working flag
                self.showing_working_anim = False
                self.working_anim_started = False
                
                # Only show Idle in READY or INTERACTING states
                if self.current_state in ["READY", "INTERACTING"]:
                    if not skeleton.isPlayingAction(0):
                        try:
                            skeleton.playAction(
                                'Restorer.Idle', 
                                1, 
                                13, 
                                layer=0, 
                                play_mode=bge.logic.KX_ACTION_MODE_LOOP,
                                blendin=5,
                                priority=1
                            )
                            if not SUPPRESS_ALL_LOGS:
                                debug_print(3, "Idle animation started (with objects)")
                        except Exception as e:
                            debug_print(1, f"Error playing Idle: {e}")
            
            # CASE 2: There are NO objects to restore - Use Working animation
            else:
                # Mark that we are showing Working
                if not self.showing_working_anim:
                    self.showing_working_anim = True
                    self.working_anim_started = False
                
                # Start Working animation if not already playing
                if not self.working_anim_started or not skeleton.isPlayingAction(0):
                    try:
                        skeleton.playAction(
                            'Restorer.Working',
                            1,
                            13,
                            layer=0,
                            play_mode=bge.logic.KX_ACTION_MODE_LOOP,
                            blendin=5,
                            priority=1
                        )
                        self.working_anim_started = True
                        if not SUPPRESS_ALL_LOGS:
                            debug_print(2, "Working animation started (no objects)")
                    except Exception as e:
                        debug_print(1, f"Error playing Working: {e}")
                        
        except Exception as e:
            debug_print(1, f"Error in update_animation(): {e}")

    # =========================================================================
    # RESULT HANDLING
    # =========================================================================
    
    def handle_quiz_result(self, success):
        """Process restoration quiz result"""
        if not self.current_restoration_item:
            if not SUPPRESS_ALL_LOGS:
                debug_print(1, "handle_quiz_result without current item")
            return
        
        item_type, item_id = self.current_restoration_item
        key = (item_type, item_id)
        
        if not SUPPRESS_ALL_LOGS:
            result_text = "SUCCESS" if success else "FAILURE"
            debug_print(1, f"Processing result: {item_type}#{item_id} -> {result_text}")
        
        if success:
            # CORRECT ANSWER
            if not SUPPRESS_ALL_LOGS:
                debug_print(1, f"Restoration successful!")
            
            self.mark_object_restored(item_type, item_id, success=True)
            self.remove_from_queue(key)
            self.awaiting_retry = False
            self.reset_dialog_flags()
            
            if self.restoration_queue:
                if not SUPPRESS_ALL_LOGS:
                    debug_print(1, f"Next object in queue")
                self.start_next_restoration()
            else:
                self.current_state = "WAITING"
                self.active_restoration = False
                self.current_restoration_item = None
                self.owner.setVisible(False)
                self.owner["has_objects_to_restore"] = False
                self.owner["restoration_available"] = False
                self.owner["restoration_in_progress"] = False
                
                if not SUPPRESS_ALL_LOGS:
                    debug_print(1, "All restorations completed - NPC hidden")
        
        else:
            # INCORRECT ANSWER
            if key not in self.attempts:
                self.attempts[key] = 0
            self.attempts[key] += 1
            current_attempts = self.attempts[key]
            
            if not SUPPRESS_ALL_LOGS:
                debug_print(1, f"Attempt {current_attempts}/{RESTORATION_MAX_ATTEMPTS} failed")
            
            if current_attempts >= RESTORATION_MAX_ATTEMPTS:
                # MAX ATTEMPTS REACHED
                if not SUPPRESS_ALL_LOGS:
                    debug_print(1, f"Max attempts reached - marking as restored without success")
                
                self.mark_object_restored(item_type, item_id, success=False)
                self.remove_from_queue(key)
                self.awaiting_retry = False
                self.reset_dialog_flags()
                
                if self.restoration_queue:
                    if not SUPPRESS_ALL_LOGS:
                        debug_print(1, f"Next object in queue")
                    self.start_next_restoration()
                else:
                    self.current_state = "WAITING"
                    self.active_restoration = False
                    self.current_restoration_item = None
                    self.owner.setVisible(False)
                    self.owner["has_objects_to_restore"] = False
                    self.owner["restoration_available"] = False
                    self.owner["restoration_in_progress"] = False
                    
                    if not SUPPRESS_ALL_LOGS:
                        debug_print(1, "Queue empty - NPC hidden")
            
            else:
                # SCHEDULE RETRY
                if not SUPPRESS_ALL_LOGS:
                    debug_print(1, f"Retry {current_attempts + 1}/{RESTORATION_MAX_ATTEMPTS} scheduled")
                
                self.prepare_for_next_attempt()
        
        self.quiz_result_processed = True

    def mark_object_restored(self, item_type, item_id, success=True):
        """Mark object as restored in inventory"""
        try:
            game = game_access.get_game()
            if not game:
                return
                    
            inventory = game.state.inventory
            collection_items = inventory.get("collection_items", {})
            
            item_updated = False
            for item in collection_items.get(item_type, []):
                if item.get("item_id") == item_id:
                    item["restored"] = 1
                    item_updated = True
                    
                    if not SUPPRESS_ALL_LOGS:
                        if success:
                            print(f"[NPC11] Object restored SUCCESSFULLY: {item_type}#{item_id}")
                        else:
                            print(f"[NPC11] Object restored WITHOUT SUCCESS (attempts exhausted): {item_type}#{item_id}")
                    
                    self.sync_object_properties(item_type, item_id, 1)
                    break
            
            if item_updated:
                game.state.update_collection_stats()
                
                try:
                    scn = logic.getCurrentScene()
                    gc = scn.objects.get("Game.Controller")
                    if gc:
                        gc.sendMessage("achievement", 
                                     f"action=restoration_complete|item_type={item_type}|item_id={item_id}|success={1 if success else 0}")
                    
                        game_access.sync_to_controller(gc)
                except Exception as e:
                    if not SUPPRESS_ALL_LOGS:
                        debug_print(1, f"Error syncing: {e}")
                        
        except Exception as e:
            if not SUPPRESS_ALL_LOGS:
                debug_print(1, f"Error marking as restored: {e}")

    def sync_object_properties(self, item_type, item_id, restored_value):
        """Synchronize object properties between world and card"""
        try:
            scene = logic.getCurrentScene()
            
            world_obj_name = f"Object.World.{item_type.capitalize() if item_type != 'bronze' else 'Bronze'}.{item_id}"
            world_obj = scene.objects.get(world_obj_name)
            
            if world_obj:
                world_obj["restored"] = restored_value
                if not SUPPRESS_ALL_LOGS:
                    print(f"[NPC11] Synced World object: {world_obj_name} -> restored={restored_value}")
            
            card_obj_name = f"Object.{item_type.capitalize() if item_type != 'bronze' else 'Bronze'}.{item_id}"
            card_obj = scene.objects.get(card_obj_name)
            
            if card_obj:
                card_obj["restored"] = restored_value
                if not SUPPRESS_ALL_LOGS:
                    print(f"[NPC11] Synced Card object: {card_obj_name} -> restored={restored_value}")
            
            for obj in scene.objects:
                try:
                    if (obj.get("item_type", "") == item_type and 
                        obj.get("item_id", 0) == item_id):
                        obj["restored"] = restored_value
                        if not SUPPRESS_ALL_LOGS:
                            print(f"[NPC11] Synced generic object: {obj.name}")
                except:
                    pass
                
            return True
        except Exception as e:
            if not SUPPRESS_ALL_LOGS:
                print(f"[NPC11] Error syncing objects: {e}")
            return False

    def increment_restoration_total(self):
        """Increment successful restoration counter"""
        try:
            game = game_access.get_game()
            if game:
                current_total = getattr(game.state, 'task_restoration_total', 0)
                game.state.task_restoration_total = current_total + 1
                
                if not SUPPRESS_ALL_LOGS:
                    debug_print(1, f"Restorations: {game.state.task_restoration_total}/3")
                
                if game.state.task_restoration_total >= 3:
                    game.state.task_restoration = True
                    if not SUPPRESS_ALL_LOGS:
                        debug_print(1, "RESTORATION task completed!")
                
                try:
                    gc = logic.getCurrentScene().objects.get("Game.Controller")
                    if gc:
                        gc['task_restoration_total'] = game.state.task_restoration_total
                        gc['task_restoration'] = game.state.task_restoration
                except:
                    pass
                    
        except:
            pass

    def remove_from_queue(self, key):
        """Remove object from restoration queue"""
        if key in self.restoration_queue:
            self.restoration_queue.remove(key)
            if not SUPPRESS_ALL_LOGS:
                debug_print(1, f"Removed from queue: {key}")
        
        if self.current_restoration_item == key:
            self.current_restoration_item = None
            if not SUPPRESS_ALL_LOGS:
                debug_print(1, f"Reset current_restoration_item")
        
        if key in self.attempts:
            del self.attempts[key]
        
        if key in self.retry_timers:
            del self.retry_timers[key]
        
        if not self.restoration_queue:
            self.owner["has_objects_to_restore"] = False
            self.owner["restoration_available"] = False
            if not SUPPRESS_ALL_LOGS:
                debug_print(1, f"Queue empty - Properties updated to False")
        else:
            self.owner["has_objects_to_restore"] = True
            if not SUPPRESS_ALL_LOGS:
                debug_print(1, f"{len(self.restoration_queue)} objects in queue")

    def update_retry_timers(self):
        """Update retry timers"""
        current_time = time.time()
        items_to_retry = []
        
        for key, timer_info in list(self.retry_timers.items()):
            if current_time >= timer_info['retry_time']:
                items_to_retry.append(key)
                del self.retry_timers[key]
        
        for key in items_to_retry:
            item_type, item_id = key
            if not SUPPRESS_ALL_LOGS:
                debug_print(1, f"Retrying: {item_type}#{item_id}")
            
            if key not in self.restoration_queue:
                self.restoration_queue.insert(0, key)
                self.owner["has_objects_to_restore"] = True
            
            if not self.active_restoration:
                self.current_restoration_item = key
                self.apply_scene_for_item_attempt(key)
                
                current_attempts = self.attempts.get(key, 0)
                current_scene = self.owner.get("scene_id", 31)
                if not SUPPRESS_ALL_LOGS:
                    debug_print(1, f"Retry {current_attempts + 1}: scene_id={current_scene}")
                
                self.active_restoration = True
                self.current_state = "DELAYED"
                self.notification_timer = current_time + 1.0
                self.has_notified = False
                self.notification_step = 0
                self.awaiting_retry = True
                self.owner.setVisible(True)
                self.owner["restoration_in_progress"] = True

    def handle_interaction_finished(self):
        """Handle interaction completion"""
        if not SUPPRESS_ALL_LOGS:
            debug_print(1, "Ending interaction")
        
        if self.awaiting_retry:
            if not SUPPRESS_ALL_LOGS:
                debug_print(1, "Retry pending - interaction suspended")
            return
        
        self.update_scene_id_for_current_item()
        
        self.owner["quiz_on"] = False
        self.owner["quiz_reply"] = False
        
        self.verify_state_consistency()
        
        if self.restoration_queue:
            self.current_state = "WAITING"
            self.dialog_started = False
            self.has_notified = False
            self.manual_interaction_allowed = False
            
            self.owner["restoration_available"] = False
            self.owner["restoration_in_progress"] = False
            
            if not SUPPRESS_ALL_LOGS:
                debug_print(1, f"Ready for next object ({len(self.restoration_queue)} in queue)")
        
        else:
            self.current_state = "WAITING"
            self.dialog_started = False
            self.has_notified = False
            self.manual_interaction_allowed = False
            
            self.owner["has_objects_to_restore"] = False
            self.owner["restoration_available"] = False
            self.owner["restoration_in_progress"] = False
            
            self.owner.setVisible(False)
            
            if not SUPPRESS_ALL_LOGS:
                debug_print(1, "All interactions completed - NPC hidden")

    def process_message(self, body):
        """Process incoming messages for this NPC"""
        try:
            if "restoration_npc|activate" in body:
                parts = body.split("|")
                params = {}
                for part in parts[1:]:
                    if "=" in part:
                        key, value = part.split("=")
                        params[key] = value
                
                if "item_type" in params and "item_id" in params:
                    item_type = params["item_type"]
                    try:
                        item_id = int(params["item_id"])
                    except:
                        return
                    
                    if not SUPPRESS_ALL_LOGS:
                        debug_print(1, f"Message received: activate {item_type}#{item_id}")
                    
                    self.add_to_restoration_queue(item_type, item_id)
                    
        except Exception as e:
            if not SUPPRESS_ALL_LOGS:
                debug_print(1, f"Error processing message: {e}")

    def verify_state_consistency(self):
        """Verify state consistency"""
        if not self.restoration_queue and not self.current_restoration_item:
            if self.current_state not in ["WAITING"]:
                if not SUPPRESS_ALL_LOGS:
                    debug_print(1, f"Inconsistency detected: state={self.current_state}, but no objects")
                self.current_state = "WAITING"
                self.owner.setVisible(False)

    # =========================================================================
    # MAIN UPDATE - OPTIMIZED
    # =========================================================================
    
    def update(self):
        """Update per frame - OPTIMIZED VERSION WITH SENSORS"""
        try:
            # 1. Check pending objects
            if self.check_restoration_needed() and not self.restoration_queue and not self.active_restoration:
                next_item = self.get_next_restoration_item()
                if next_item:
                    item_type, item_id = next_item
                    self.add_to_restoration_queue(item_type, item_id)
            
            # 2. Update retry timers
            if self.retry_timers:
                self.update_retry_timers()
            
            # 3. OPTIMIZATION: Only rotate if player in range (sensor)
            if self.current_state in ["READY", "INTERACTING"]:
                self.rotate_to_player()  # Has internal verification with sensor
            
            # 4. OPTIMIZATION: Update animation (now handles Working automatically)
            self.update_animation()  # Has internal verification with sensor
            
            # 5. Interaction cooldown management
            if self.interaction_cooldown > 0:
                self.interaction_cooldown -= 1
            
            # 6. Main state machine
            if self.current_state == "WAITING":
                pass
            
            elif self.current_state == "DELAYED":
                if not SUPPRESS_ALL_LOGS:
                    if not hasattr(self, '_delayed_logged') or not self._delayed_logged:
                        key = self.current_restoration_item
                        current_attempts = self.attempts.get(key, 0) if key else 0
                        debug_print(2, f"DELAYED - Waiting for retry {current_attempts + 1}/3")
                        self._delayed_logged = True
                
                current_time = time.time()
                if current_time >= self.notification_timer:
                    self.current_state = "SHOWING_NOTIFICATION"
                    self._delayed_logged = False
                    if not SUPPRESS_ALL_LOGS:
                        debug_print(1, "-> SHOWING_NOTIFICATION")
            
            elif self.current_state == "SHOWING_NOTIFICATION":
                if not SUPPRESS_ALL_LOGS:
                    if not hasattr(self, '_notif_logged') or not self._notif_logged:
                        debug_print(2, f"SHOWING_NOTIFICATION - Step {self.notification_step}/4")
                        self._notif_logged = True
                
                self.show_phone_notification()
                
                if self.has_notified:
                    self.current_state = "READY"
                    self.manual_interaction_allowed = True
                    self._notif_logged = False
                    if not SUPPRESS_ALL_LOGS:
                        debug_print(1, "-> READY (after notifications)")
            
            elif self.current_state == "READY":
                if not SUPPRESS_ALL_LOGS:
                    if not hasattr(self, '_ready_logged') or not self._ready_logged:
                        key = self.current_restoration_item
                        current_attempts = self.attempts.get(key, 0) if key else 0
                        attempt_type = "Retry" if current_attempts > 0 else "First attempt"
                        debug_print(2, f"READY - {attempt_type} (attempt {current_attempts + 1}/3)")
                        self._ready_logged = True
                
                if not self.current_restoration_item:
                    self.current_state = "WAITING"
                    self.owner["restoration_available"] = False
                    self._ready_logged = False
                    if not SUPPRESS_ALL_LOGS:
                        debug_print(1, "READY without object - Forcing WAITING")
                    return
                
                # Detect dialog start
                if self.current_restoration_item:
                    game = game_access.get_game()
                    if game:
                        state = game.state
                        dialog_active = getattr(state, 'dialog_active', False)
                        current_npc = getattr(state, 'current_npc_id', 0)
                        
                        if dialog_active and current_npc == self.npc_id:
                            if not self.dialog_started:
                                self.dialog_started = True
                                self.dialog_start_time = time.time()
                                self.current_state = "INTERACTING"
                                self._ready_logged = False
                                
                                self.awaiting_retry = False
                                self.quiz_result_processed = False
                                
                                if not SUPPRESS_ALL_LOGS:
                                    debug_print(1, f"Flags reset: awaiting_retry=False, quiz_result_processed=False")
                                
                                key = self.current_restoration_item
                                current_attempts = self.attempts.get(key, 0) if key else 0
                                if current_attempts > 0 and not SUPPRESS_ALL_LOGS:
                                    debug_print(1, f"Dialog started (Retry {current_attempts})")
                                else:
                                    debug_print(1, "Dialog started (First attempt)")
            
            elif self.current_state == "INTERACTING":
                game = game_access.get_game()
                if not game:
                    return
                
                state = game.state
                dialog_active = getattr(state, 'dialog_active', False)
                current_npc = getattr(state, 'current_npc_id', 0)
                
                player = self.get_player_reference()
                player_on_dialog = player and player.get('on_dialog', False) if player else False
                
                current_time = time.time()
                dialog_minimum_elapsed = current_time - self.dialog_start_time >= self.min_dialog_duration
                
                dialog_ended_for_this_npc = (
                    (state and not dialog_active and dialog_minimum_elapsed) or
                    (not player_on_dialog and dialog_minimum_elapsed)
                )
                
                other_npc_talking = (dialog_active and current_npc != self.npc_id)
                
                if dialog_ended_for_this_npc or other_npc_talking:
                    if not SUPPRESS_ALL_LOGS:
                        key = self.current_restoration_item
                        current_attempts = self.attempts.get(key, 0) if key else 0
                        debug_print(1, f"Dialog end detected (Attempt {current_attempts + 1})")
                    
                    quiz_captured = self.capture_quiz_result()
                    
                    if quiz_captured and self.captured_quiz_result:
                        result = self.captured_quiz_result
                        
                        if not SUPPRESS_ALL_LOGS:
                            result_text = "SUCCESS" if result['success'] else "FAILURE"
                            debug_print(1, f"Quiz: {result_text}")
                        
                        self.handle_quiz_result(result['success'])
                        self.captured_quiz_result = None
                        
                        self.owner["quiz_reply"] = False
                        self.owner["quiz_on"] = False
                        
                        if not SUPPRESS_ALL_LOGS:
                            debug_print(2, "Quiz properties reset")
                    
                    if not self.awaiting_retry:
                        if not SUPPRESS_ALL_LOGS:
                            debug_print(1, "-> Ending interaction (no retry)")
                        self.handle_interaction_finished()
                    else:
                        if not SUPPRESS_ALL_LOGS:
                            debug_print(1, f"Retry scheduled - keeping DELAYED state")
            
            # 8. Update final properties
            if not self.current_restoration_item and not self.restoration_queue:
                if self.owner.visible and self.current_state not in ["INTERACTING", "SHOWING_NOTIFICATION", "DELAYED"]:
                    self.owner.setVisible(False)
                    self.current_state = "WAITING"
                    self.awaiting_retry = False
                    self.owner["has_objects_to_restore"] = False
                    self.owner["restoration_available"] = False
                    self.owner["restoration_in_progress"] = False
            else:
                self.owner["has_objects_to_restore"] = True
                
                if self.current_state == "READY":
                    self.owner["restoration_available"] = True
                elif self.current_state == "INTERACTING":
                    self.owner["restoration_available"] = True
                else:
                    self.owner["restoration_available"] = False
                
                if self.current_state in ["DELAYED", "SHOWING_NOTIFICATION", "INTERACTING"]:
                    self.owner["restoration_in_progress"] = True
                elif self.current_state == "READY":
                    self.owner["restoration_in_progress"] = True
                else:
                    self.owner["restoration_in_progress"] = False
            
               
        except Exception as e:
            if not SUPPRESS_ALL_LOGS:
                debug_print(1, f"Error in update(): {e}")

# =============================================================================
# GLOBAL INSTANCE AND MAIN FUNCTION
# =============================================================================
_restoration_npc_instance = None

def main(cont):
    """Main function - OPTIMIZED VERSION WITH SENSORS
    
    IMPORTANT: Requires sensors configured in Blender:
    - Near_Dialog: property='player', Distance=2.0, Reset=4.0
    - Near_Anim: property='player', Distance=5.0, Reset=7.0
    """
    global _restoration_npc_instance
    owner = cont.owner
    
    if owner.get("npc_id", 0) != 11:
        return
    
    # Initialize instance
    if _restoration_npc_instance is None:
        _restoration_npc_instance = RestorationNPCLogic(owner)
    
    # OPTIMIZATION: Process Near sensors FIRST
    near_dialog = cont.sensors.get("Near_Dialog")
    near_anim = cont.sensors.get("Near_Anim")
    
    if near_dialog or near_anim:
        _restoration_npc_instance.update_from_sensors(near_dialog, near_anim)
    
    # Process messages
    msg_sensor = cont.sensors.get("Message")
    
    if msg_sensor and msg_sensor.positive:
        for body in msg_sensor.bodies:
            if "restoration_npc" in body:
                _restoration_npc_instance.process_message(body)
            elif "restoration_system" in body:
                _restoration_npc_instance.process_message(body.replace("restoration_system", "restoration_npc"))
    
    # Main update
    _restoration_npc_instance.update()