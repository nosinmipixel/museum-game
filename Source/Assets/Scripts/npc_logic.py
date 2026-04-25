"""
npc_logic.py

NPC logic system for NPCs 1-10

Main Features:
    1. Turn-based NPC activation system (NPCs appear in sequence)
    2. Safe state machine with transition queue to prevent race conditions
    3. Player proximity detection with dialog and animation ranges
    4. Smooth rotation toward player with corrected angle calculation
    5. Idle animation playback when player is nearby
    6. Disappear effect with matrix effect trigger
    7. Phone notification system for NPC appearance
    8. Timer-based appearance (initial delay + interval between appearances)
    9. PERIODIC REMINDER when NPC is active but not interacted with

Setup:
    Connect in Logic Bricks as Python controller/module 'npc_logic.main'
    NPC object requires sensors Always (True) and:
        - Near_Dialog (proximity for dialog activation)
        - Near_Anim (proximity for animation activation)
    NPC object requires properties:
        - remaining_events (int): Number of attempts left (default: 3)
        - active (bool): Whether NPC is currently active

Configurable Variables:
    DEBUG_VERBOSITY (int): 0=silent, 1=info, 2=detailed, 3=very detailed
    NPC_INIT_TIME (float): Initial delay before first NPC appears (default: 60.0)
    NPC_INTERVAL_TIME (float): Delay between subsequent NPCs (default: 60.0)
    SUPPRESS_ALL_LOGS (bool): Disable all logging (default: False)
    rotation_speed (float): Rotation speed toward player (default: 5.0)
    REMINDER_INTERVAL (float): Seconds between reminder messages when NPC is active (default: 45.0)
    REMINDER_MESSAGE_KEY (str): Message key for reminder text (default: "info.show|info_text|36|field=info_text")

Notes:
    - Requires game_access module for game state management
    - Only processes NPCs with IDs 1-10
    - Uses cached player reference with TTL to avoid performance issues
    - Dialog detection uses game_access state for dialog_active and current_npc_id
    - Effect disappear triggered via message or direct object reference

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
__description__ = "NPC logic system with turn-based activation and rotation"

# =============================================================================
# IMPORTS AND CONFIGURATION
# =============================================================================
import bge
from bge import logic
import time
import math
import game_access

DEBUG_VERBOSITY = 0  # 2 = Detailed
NPC_INIT_TIME = 60.0   # Production: 60 (1 min); Testing: 5; Disabled: 5000
NPC_INTERVAL_TIME = 60.0   # Production: 60 (1 min); Testing: 3.0
SUPPRESS_ALL_LOGS = False

# ===== REMINDER SYSTEM CONFIGURATION =====
REMINDER_INTERVAL = 45.0  # Seconds between reminder messages when NPC is active
REMINDER_MESSAGE_KEY = "info.show|info_text|36|field=info_text"  # Message key for reminder (line 36)

def debug_print(level, message):
    """Print messages according to verbosity level"""
    if not SUPPRESS_ALL_LOGS and level <= DEBUG_VERBOSITY:
        print(f"[NPC-LOGIC-FIXED] {message}")

# =============================================================================
# STATE TRANSITION QUEUE
# =============================================================================
class StateTransitionQueue:
    """Queue for atomic state transitions - UPBGE VERSION"""
    def __init__(self):
        self.pending_transitions = []
        self.processing = False
        self._frame_counter = 0
        
    def add_transition(self, event_type, data=None):
        """Add a transition to the queue"""
        self._frame_counter += 1
        self.pending_transitions.append({
            'type': event_type,
            'data': data,
            'frame': self._frame_counter
        })
        debug_print(3, f"Transition queued: {event_type}")
        
    def process_all(self):
        """Process all pending transitions atomically"""
        if self.processing or not self.pending_transitions:
            return []
            
        self.processing = True
        transitions_to_process = []
        try:
            # Take all pending transitions
            transitions_to_process = self.pending_transitions[:]
            self.pending_transitions = []
        finally:
            self.processing = False
            
        return transitions_to_process

# =============================================================================
# NPC LOGIC SYSTEM CLASS
# =============================================================================
class NPCLogicSystem:
    def __init__(self, owner):
        self.owner = owner
        
        # Extract npc_id safely
        try:
            self.npc_id = int(owner.name.replace('npc', ''))
        except:
            self.npc_id = 0
            
        # VALIDATION: Only NPCs 1-10
        if self.npc_id < 1 or self.npc_id > 10:
            debug_print(1, f"NPC {self.npc_id} out of range 1-10 - Disabled")
            self.valid_npc = False
            return
        self.valid_npc = True
        
        # TRANSITION QUEUE SYSTEM
        self.transition_queue = StateTransitionQueue()
        
        # RE-ENTRY PROTECTION
        self._update_in_progress = False
        self._state_change_in_progress = False
        self._current_frame = 0
        self._state_version = 0
        
        self.current_state = "WAITING"
        self.notification_step = 0
        self.notification_timer = 0
        
        # DIALOG CONTROL WITH PROTECTION
        self.dialog_started = False
        self.dialog_start_time = 0
        self.min_dialog_duration = 1.0
        
        # ROTATION SYSTEM
        self.rotation_speed = 5.0
        
        # CENTRALIZED SENSOR STATE
        self._sensor_state = {
            'dialog_range': False,
            'anim_range': False,
            'dialog_prev': False,
            'anim_prev': False
        }
        
        # PLAYER CACHE WITH EXPIRATION
        self._cached_player = None
        self._cache_valid_until_frame = 0
        self._cache_ttl_frames = 5
        
        # REMINDER SYSTEM
        self._last_reminder_time = 0
        self._reminder_sent_in_current_state = False
        
        # REFERENCES
        self.pos_in = None
        self.pos_out = None
        self.initial_position = None
        self.effect_matrix = None
        
        # INITIALIZE
        self.emergency_init()
        
        debug_print(1, f"NPC {self.npc_id} initialized - Fixed system without race conditions")
    
    # ===== REMINDER SYSTEM =====
    
    def _send_reminder_message(self):
        """Send reminder message to Game.Controller"""
        try:
            self.owner.sendMessage(
                "add_info_text",
                REMINDER_MESSAGE_KEY,
                "Game.Controller"
            )
            debug_print(1, f"NPC {self.npc_id}: Reminder sent (key: {REMINDER_MESSAGE_KEY})")
            return True
        except Exception as e:
            debug_print(1, f"NPC {self.npc_id}: Error sending reminder: {e}")
            return False
    
    def _should_send_reminder(self, current_time):
        """
        Check if reminder should be sent to player.
        Only sends if:
        1. NPC is active and visible
        2. Not currently in dialog/interaction
        3. Enough time has passed since last reminder
        """
        # Only send reminders when NPC is in a state where player can interact
        reminder_states = ["READY", "SHOWING_NOTIFICATION"]
        
        if self.current_state not in reminder_states:
            return False
        
        # Don't send reminders if dialog is active or starting
        if self.dialog_started:
            return False
        
        # Check if enough time has passed
        if current_time - self._last_reminder_time >= REMINDER_INTERVAL:
            return True
        
        return False
    
    def _update_reminder(self, current_time):
        """Update reminder system - called periodically"""
        if self._should_send_reminder(current_time):
            self._send_reminder_message()
            self._last_reminder_time = current_time
            self._reminder_sent_in_current_state = True
    
    # PROTECTED METHODS
    
    def change_state(self, new_state, reason=""):
        """Change state safely and atomically"""
        if self._state_change_in_progress:
            # Queue change to avoid re-entry
            self.transition_queue.add_transition('STATE_CHANGE', {
                'new_state': new_state,
                'reason': reason
            })
            return False
            
        self._state_change_in_progress = True
        try:
            old_state = self.current_state
            
            # Reset reminder tracking on state change
            if old_state != new_state:
                self._reminder_sent_in_current_state = False
                # Don't reset _last_reminder_time to preserve interval across states
            
            self.current_state = new_state
            self._state_version += 1
            
            debug_print(2, f"NPC {self.npc_id}: {old_state} -> {new_state} ({reason})")
            return True
        finally:
            self._state_change_in_progress = False
    
    def invalidate_player_cache(self):
        """Completely clear player cache"""
        self._cached_player = None
        self._cache_valid_until_frame = 0
    
    def get_player_reference(self, force_refresh=False):
        """Get player reference with protected cache - UPBGE VERSION"""
        self._current_frame += 1
        
        # Check if cache has expired
        cache_expired = self._current_frame > self._cache_valid_until_frame
        
        if force_refresh or cache_expired or self._cached_player is None:
            try:
                scene = logic.getCurrentScene()
                player = scene.objects.get("Player")
                
                if player:
                    # In UPBGE, verify object still exists
                    try:
                        # Try to access a property to verify validity
                        _ = player.name
                        self._cached_player = player
                        self._cache_valid_until_frame = self._current_frame + self._cache_ttl_frames
                        debug_print(3, f"NPC {self.npc_id}: Player cache updated")
                    except:
                        self.invalidate_player_cache()
                else:
                    self.invalidate_player_cache()
            except Exception as e:
                debug_print(3, f"NPC {self.npc_id}: Error finding player: {e}")
                self.invalidate_player_cache()
        
        # Return cache if available
        return self._cached_player
    
    # ===== SAFE SENSOR MANAGEMENT =====
    
    def process_sensor_transitions(self, near_dialog, near_anim):
        """Process sensors and queue transitions - UPBGE VERSION"""
        # In UPBGE, sensors have .positive attribute
        if near_dialog:
            current_dialog = near_dialog.positive
            prev_dialog = self._sensor_state['dialog_prev']
            self._sensor_state['dialog_range'] = current_dialog
            
            if current_dialog and not prev_dialog:
                # Player ENTERED range
                self.transition_queue.add_transition('PLAYER_ENTERED_DIALOG', {
                    'sensor': 'dialog',
                    'time': time.time()
                })
                debug_print(2, f"NPC {self.npc_id}: Transition ENTER dialog")
            
            elif not current_dialog and prev_dialog:
                # Player EXITED range
                self.transition_queue.add_transition('PLAYER_EXITED_DIALOG')
                debug_print(2, f"NPC {self.npc_id}: Transition EXIT dialog")
            
            self._sensor_state['dialog_prev'] = current_dialog
        
        if near_anim:
            current_anim = near_anim.positive
            prev_anim = self._sensor_state['anim_prev']
            self._sensor_state['anim_range'] = current_anim
            
            if current_anim and not prev_anim:
                self.transition_queue.add_transition('PLAYER_ENTERED_ANIM_RANGE')
                debug_print(2, f"NPC {self.npc_id}: Transition ENTER animation")
            
            elif not current_anim and prev_anim:
                self.transition_queue.add_transition('PLAYER_EXITED_ANIM_RANGE')
                debug_print(2, f"NPC {self.npc_id}: Transition EXIT animation")
            
            self._sensor_state['anim_prev'] = current_anim
    
    def apply_transition(self, transition):
        """Apply transition atomically"""
        event_type = transition['type']
        data = transition.get('data', {})
        
        if event_type == 'PLAYER_ENTERED_DIALOG':
            debug_print(2, f"NPC {self.npc_id}: Applying PLAYER_ENTERED_DIALOG")
            # Player will be detected by get_player_reference()
            
        elif event_type == 'PLAYER_EXITED_DIALOG':
            debug_print(2, f"NPC {self.npc_id}: Applying PLAYER_EXITED_DIALOG")
            # Nothing special, sensor already updated state
            
        elif event_type == 'STATE_CHANGE':
            new_state = data.get('new_state', self.current_state)
            reason = data.get('reason', 'unknown')
            self.change_state(new_state, reason)
            
        elif event_type == 'RETRY_INTERACTION_FINISHED':
            debug_print(2, f"NPC {self.npc_id}: Retrying handle_interaction_finished")
            self.handle_interaction_finished()
    
    def emergency_init(self):
        """Atomic initialization of all properties"""
        if not self.valid_npc:
            return
            
        try:
            scene = logic.getCurrentScene()
            
            # ATOMIC PROPERTY INITIALIZATION
            default_properties = {
                'remaining_events': 3,
                'quiz_success': False,
                'active': False,
                'quiz_reply': False,
                '_initialized': True,
                '_dialog_ended': False,
                'scene_id': (self.npc_id - 1) * 3 + 1,
                '_base_scene_id': (self.npc_id - 1) * 3 + 1
            }
            
            for prop, value in default_properties.items():
                if prop not in self.owner:
                    self.owner[prop] = value
            
            # OBJECT REFERENCES
            self.pos_in = scene.objects.get("Empty.NPC.In")
            self.pos_out = scene.objects.get("Empty.NPC.Out")
            self.effect_matrix = scene.objects.get("Matrix.Effect.Tracked")
            
            # INITIAL POSITION
            self.initial_position = self.owner.worldPosition.copy()
            
            # ACTIVATE ONLY NPC1 AT START
            state = game_access.get_state()
            if state and state.npc_turn == self.npc_id:
                if not self.has_been_any_interaction():
                    self.owner['active'] = True
                    debug_print(1, f"NPC {self.npc_id}: ACTIVATED at start")
            
            # ENSURE INITIAL STATE
            self.owner.setVisible(False)
            self.owner.worldPosition = self.initial_position.copy()
            
            # Initialize reminder timer
            self._last_reminder_time = time.time()
            
            debug_print(1, f"NPC {self.npc_id}: Fully initialized")
            
        except Exception as e:
            debug_print(1, f"Error in NPC {self.npc_id} initialization: {e}")
    
    def is_my_turn(self):
        """Check if it's this NPC's turn safely"""
        if not self.valid_npc:
            return False
            
        state = game_access.get_state()
        if not state:
            return False
            
        current_turn = state.npc_turn
        is_active = self.owner.get('active', True)
        
        return current_turn == self.npc_id and is_active
    
    def has_been_any_interaction(self):
        """Check if there has been any previous interaction"""
        try:
            scene = logic.getCurrentScene()
            for i in range(1, 11):
                npc_name = f'npc{i}'
                npc = scene.objects.get(npc_name)
                if npc and npc.get('remaining_events', 3) < 3:
                    return True
        except Exception as e:
            debug_print(3, f"Error checking interactions: {e}")
        return False
    
    def should_appear(self):
        """Determine if NPC should appear now"""
        if not self.valid_npc:
            return False
            
        state = game_access.get_state()
        if not state:
            return False
        
        # Check if quiz is active
        if not getattr(state, 'quiz_active', True):
            return False
        
        # Check turn and state
        if not self.is_my_turn():
            return False
        
        if self.current_state != "WAITING":
            return False
        
        timer_quiz = getattr(state, 'timer_quiz', 0.0)
        has_interaction = self.has_been_any_interaction()
        
        if has_interaction:
            return timer_quiz >= NPC_INTERVAL_TIME
        else:
            return timer_quiz >= NPC_INIT_TIME
    
    # PROTECTED METHODS
    
    def handle_interaction_finished(self):
        """Handle end of interaction atomically - WITH EFFECT"""
        if self._state_change_in_progress:
            debug_print(2, f"NPC {self.npc_id}: handle_interaction_finished already in progress - queuing")
            self.transition_queue.add_transition('RETRY_INTERACTION_FINISHED')
            return
            
        self._state_change_in_progress = True
        try:
            debug_print(1, f"NPC {self.npc_id}: Processing final result (ATOMIC)")
            
            # DISAPPEAR EFFECT - ACTIVATE BEFORE ANYTHING ELSE
            self.trigger_effect_disappear()
            
            # ATOMIC PROPERTY READING
            quiz_success = self.owner.get('quiz_success', False)
            remaining_events = self.owner.get('remaining_events', 3)
            
            # ATOMIC PROPERTY RESET
            reset_properties = {
                'quiz_reply': False,
                'quiz_on': False,
                '_dialog_ended': False
            }
            
            for prop, value in reset_properties.items():
                self.owner[prop] = value
            
            # CACHE CLEANUP
            self.invalidate_player_cache()
            self._sensor_state['dialog_range'] = False
            self._sensor_state['anim_range'] = False
            
            # RESULT LOGIC
            if quiz_success:
                # SUCCESS
                self.owner['active'] = False
                self.owner['remaining_events'] = 0
                
                debug_print(1, f"NPC {self.npc_id}: QUIZ SUCCESSFUL - Deactivated")
                
                self.move_to_out()
                self.owner.setVisible(False)
                
                # ADVANCE TURN AFTER DEACTIVATION
                self.advance_turn()
                
            else:
                # FAILURE
                remaining_events -= 1
                self.owner['remaining_events'] = remaining_events
                
                debug_print(1, f"NPC {self.npc_id}: FAILURE - Attempts remaining: {remaining_events}")
                
                if remaining_events <= 0:
                    self.owner['active'] = False
                    debug_print(1, f"NPC {self.npc_id}: No attempts left")
                    
                    self.move_to_out()
                    self.owner.setVisible(False)
                    self.advance_turn()
                else:
                    # KEEP ACTIVE FOR NEW ATTEMPT
                    debug_print(1, f"NPC {self.npc_id}: Preparing new attempt")
                    
                    # Update scene_id safely
                    attempts_used = 3 - remaining_events
                    base_scene = self.owner.get('_base_scene_id', (self.npc_id - 1) * 3 + 1)
                    new_scene_id = base_scene + attempts_used
                    self.owner['scene_id'] = new_scene_id
                    
                    debug_print(1, f"  New scene_id: {new_scene_id}")
                    
                    self.move_to_out()
                    self.owner.setVisible(False)
                    # DO NOT advance turn - same NPC reappears
            
            # RESET TIMER
            self.reset_timer_quiz()
            
            # RESET INTERNAL STATE
            self.change_state("WAITING", "interaction finished")
            self.dialog_started = False
            self.notification_step = 0
            
            # Reset reminder timer for next appearance
            self._last_reminder_time = time.time()
            self._reminder_sent_in_current_state = False
            
            debug_print(1, f"NPC {self.npc_id}: Interaction finished atomically")
            
        except Exception as e:
            debug_print(1, f"Error in handle_interaction_finished NPC {self.npc_id}: {e}")
        finally:
            self._state_change_in_progress = False
    
    def trigger_effect_disappear(self):
        """Trigger disappear effect - ENHANCED VERSION"""
        try:
            debug_print(2, f"NPC {self.npc_id}: Triggering disappear effect")
            
            # OPTION 1: Use cached reference
            if self.effect_matrix:
                # Position effect at NPC location
                self.effect_matrix.worldPosition = self.owner.worldPosition.copy()
                debug_print(2, f"  Effect positioned at {self.owner.worldPosition}")
                
                # Send direct message to object
                self.effect_matrix.sendMessage('effect_disappear')
                debug_print(2, f"  Message 'effect_disappear' sent to object")
            
            # OPTION 2: Global message (fallback)
            try:
                bge.logic.sendMessage("effect_disappear")
                debug_print(2, f"  Global message 'effect_disappear' sent")
            except:
                pass
                
            # OPTION 3: Dynamically find object (additional fallback)
            if not self.effect_matrix:
                try:
                    scene = logic.getCurrentScene()
                    effect_obj = scene.objects.get("Matrix.Effect.Tracked")
                    if effect_obj:
                        effect_obj.worldPosition = self.owner.worldPosition.copy()
                        effect_obj.sendMessage('effect_disappear')
                        debug_print(2, f"  Effect found and activated dynamically")
                except:
                    pass
                    
            return True
            
        except Exception as e:
            debug_print(1, f"Error in trigger_effect_disappear NPC {self.npc_id}: {e}")
            return False
    
    # NEW METHOD: DETECT DIALOG START IMMEDIATELY
    def is_dialog_starting(self):
        """Detect if dialog is starting RIGHT NOW"""
        state = game_access.get_state()
        if not state:
            return False
        
        dialog_active = getattr(state, 'dialog_active', False)
        current_npc = getattr(state, 'current_npc_id', 0)
        
        # If dialog is active and for this NPC
        if dialog_active and current_npc == self.npc_id:
            # And we haven't marked it as started yet
            if not self.dialog_started:
                return True
        
        return False
    
    def is_dialog_finished(self):
        """Robustly detect if dialog has ended"""
        if not self.dialog_started:
            return False
        
        state = game_access.get_state()
        if not state:
            return False
        
        dialog_active = getattr(state, 'dialog_active', False)
        current_npc = getattr(state, 'current_npc_id', 0)
        
        # Check player state
        player_on_dialog = False
        player_ref = self.get_player_reference()
        if player_ref:
            player_on_dialog = player_ref.get('on_dialog', False)
        
        # ROBUST DIALOG END CONDITION
        dialog_ended = (
            (not dialog_active and current_npc != self.npc_id) or
            (not player_on_dialog and self.dialog_started and 
             time.time() - self.dialog_start_time > self.min_dialog_duration)
        )
        
        return dialog_ended
    
    def update(self, near_dialog=None, near_anim=None):
        """Main update protected against race conditions - WITH CORRECTED ROTATION"""
        
        # 1. BASIC VALIDATION
        if not self.valid_npc:
            return
            
        if self._update_in_progress:
            debug_print(3, f"NPC {self.npc_id}: Update already in progress - skipping")
            return
            
        self._update_in_progress = True
        current_time = time.time()
        
        try:
            # 2. ACTIVE CHECK
            is_active = self.owner.get('active', True)
            if not is_active:
                if self.owner.visible:
                    self.owner.setVisible(False)
                return
            
            # 3. PROCESS SENSORS AND TRANSITIONS
            self.process_sensor_transitions(near_dialog, near_anim)
            
            # Apply queued transitions
            transitions = self.transition_queue.process_all()
            for transition in transitions:
                self.apply_transition(transition)
            
            # 4. DIALOG START DETECTION (CRITICAL - BEFORE ROTATION)
            # DETECT IF DIALOG IS STARTING NOW
            if self.is_dialog_starting():
                self.dialog_started = True
                self.dialog_start_time = current_time
                debug_print(1, f"NPC {self.npc_id}: DIALOG STARTED IMMEDIATELY")
                
                # CHANGE TO INTERACTING IMMEDIATELY
                if self.current_state != "INTERACTING":
                    self.change_state("INTERACTING", "dialog started")
                    debug_print(1, f"NPC {self.npc_id}: INTERACTING STATE IMMEDIATE")
            
            # 5. CONDITIONAL UPDATES
            # CRITICAL CHANGE: Rotate ALWAYS when:
            # 1. NPC is in READY or INTERACTING state, OR
            # 2. Dialog has started (dialog_started = True)
            should_rotate = (
                self.current_state in ["READY", "INTERACTING"] or
                self.dialog_started
            )
            
            if should_rotate:
                # Only rotate if player is in range (per sensor)
                if self._sensor_state['dialog_range']:
                    self.rotate_to_player()
                
                # Only animate if player is in range (per sensor)
                if self._sensor_state['anim_range']:
                    self.update_animation()
            
            # 6. REMINDER SYSTEM UPDATE
            self._update_reminder(current_time)
            
            # 7. STATE MACHINE
            if self.current_state == "WAITING":
                if self.should_appear():
                    # RESET BEFORE APPEARING
                    reset_props = ['quiz_reply', 'quiz_success', '_dialog_ended']
                    for prop in reset_props:
                        self.owner[prop] = False
                    
                    self.invalidate_player_cache()
                    self._sensor_state['dialog_range'] = False
                    self._sensor_state['anim_range'] = False
                    
                    # Reset reminder timer when appearing
                    self._last_reminder_time = current_time
                    self._reminder_sent_in_current_state = False
                    
                    self.change_state("MOVING_IN", "must appear")
                    debug_print(1, f"NPC {self.npc_id} MOVING TO IN")
            
            elif self.current_state == "MOVING_IN":
                self.move_to_in()
                self.change_state("SHOWING_NOTIFICATION", "movement completed")
                
            elif self.current_state == "SHOWING_NOTIFICATION":
                self.show_phone_notification()
                
            elif self.current_state == "READY":
                # SAFE DIALOG START DETECTION (backup)
                state = game_access.get_state()
                if state:
                    dialog_active = getattr(state, 'dialog_active', False)
                    current_npc = getattr(state, 'current_npc_id', 0)
                    
                    if dialog_active and current_npc == self.npc_id:
                        if not self.dialog_started:
                            self.dialog_started = True
                            self.dialog_start_time = current_time
                            debug_print(1, f"NPC {self.npc_id}: Dialog detected (backup)")
                        
                        # REMOVED 0.5s WAIT - Change immediately
                        if self.current_state != "INTERACTING":
                            self.change_state("INTERACTING", "dialog confirmed immediate")
                            debug_print(1, f"NPC {self.npc_id}: INTERACTION CONFIRMED IMMEDIATE")
                
            elif self.current_state == "INTERACTING":
                # ROBUST DIALOG END DETECTION
                if self.is_dialog_finished():
                    debug_print(1, f"NPC {self.npc_id}: DIALOG END DETECTED")
                    self.handle_interaction_finished()
                        
        except Exception as e:
            debug_print(1, f"Error in update NPC {self.npc_id}: {e}")
        finally:
            self._update_in_progress = False
    
    # EXISTING METHODS (modified to be safe)
    
    def move_to_in(self):
        """Move NPC to entry position"""
        if self.pos_in:
            self.owner.worldPosition = self.pos_in.worldPosition.copy()
            debug_print(1, f"NPC {self.npc_id}: Moved to IN")
    
    def move_to_out(self):
        """Move NPC to exit position"""
        if self.pos_out: 
            self.owner.worldPosition = self.pos_out.worldPosition.copy()
            debug_print(1, f"NPC {self.npc_id}: Moved to OUT")
    
    def rotate_to_player(self):
        """Rotate NPC toward player - Safe version"""
        try:
            player = self.get_player_reference()
            if not player:
                debug_print(3, f"NPC {self.npc_id}: No player to rotate toward")
                return False
            
            # Rotation calculations
            npc_pos = self.owner.worldPosition.copy()
            player_pos = player.worldPosition.copy()
            
            direction = player_pos - npc_pos
            direction.z = 0
            
            if direction.length < 0.1:
                debug_print(3, f"NPC {self.npc_id}: Player too close, not rotating")
                return True
            
            direction.normalize()
            target_angle = math.atan2(-direction.x, direction.y)
            
            current_rotation = self.owner.worldOrientation.to_euler()
            current_angle = current_rotation.z
            
            angle_diff = target_angle - current_angle
            
            # Normalize difference
            while angle_diff > math.pi:
                angle_diff -= 2 * math.pi
            while angle_diff < -math.pi:
                angle_diff += 2 * math.pi
            
            # DEBUG: Show rotation information
            debug_print(3, f"NPC {self.npc_id}: Rotation - Current: {math.degrees(current_angle):.1f} deg, "
                         f"Target: {math.degrees(target_angle):.1f} deg, "
                         f"Diff: {math.degrees(angle_diff):.1f} deg")
            
            if abs(angle_diff) < 0.01:
                debug_print(3, f"NPC {self.npc_id}: Already facing player")
                return True
            
            # In UPBGE, use fixed or estimated frame rate
            try:
                tic_rate = logic.getLogicTicRate()
                if tic_rate <= 0:
                    tic_rate = 60.0
            except:
                tic_rate = 60.0
                
            rotation_step = self.rotation_speed * 2.0 * (1.0 / tic_rate)
            
            if abs(angle_diff) < rotation_step:
                new_angle = target_angle
                debug_print(3, f"NPC {self.npc_id}: Final rotation reached")
            else:
                new_angle = current_angle + (rotation_step if angle_diff > 0 else -rotation_step)
                debug_print(3, f"NPC {self.npc_id}: Rotating {math.degrees(rotation_step):.1f} deg")
            
            new_rotation = current_rotation.copy()
            new_rotation.z = new_angle
            self.owner.worldOrientation = new_rotation.to_matrix()
            
            return True
            
        except Exception as e:
            debug_print(2, f"Rotation error NPC {self.npc_id}: {e}")
            return False
    
    def update_animation(self):
        """Update Idle animation"""
        if self.current_state in ["READY", "INTERACTING"] or self.dialog_started:
            try:
                children = self.owner.children
                if children and len(children) > 0:
                    skeleton = children[0]
                    if not skeleton.isPlayingAction(0):
                        try:
                            skeleton.playAction(
                                'Idle', 
                                1, 
                                13, 
                                layer=0, 
                                play_mode=bge.logic.KX_ACTION_MODE_LOOP,
                                blendin=5,
                                priority=1
                            )
                            debug_print(3, f"NPC {self.npc_id}: Idle animation started")
                        except Exception as e:
                            debug_print(3, f"Error playing animation: {e}")
            except Exception as e:
                debug_print(3, f"Error in update_animation: {e}")
    
    def advance_turn(self):
        """Advance to next active NPC"""
        state = game_access.get_state()
        if not state:
            return
            
        current_turn = state.npc_turn
        scene = logic.getCurrentScene()
        
        debug_print(1, f"NPC {self.npc_id}: Finding next NPC from NPC{current_turn}")
        
        found_next = False
        for offset in range(1, 11):
            next_turn = (current_turn + offset - 1) % 10
            if next_turn == 0:
                next_turn = 10
            
            if next_turn == self.npc_id:
                continue
                
            next_npc = scene.objects.get(f'npc{next_turn}')
            
            if next_npc:
                remaining_events = next_npc.get('remaining_events', 3)
                
                if remaining_events > 0:
                    next_npc['active'] = True
                    state.npc_turn = next_turn
                    
                    base_scene = (next_turn - 1) * 3 + 1
                    next_npc['scene_id'] = base_scene
                    
                    debug_print(1, f"Turn advanced: NPC{current_turn} -> NPC{next_turn}")
                    found_next = True
                    break
        
        if not found_next:
            debug_print(1, "No next NPC with remaining attempts found")
            state.quiz_active = False
    
    def reset_timer_quiz(self):
        """Reset quiz timer"""
        state = game_access.get_state()
        if state:
            state.timer_quiz = 0.0
            debug_print(1, f"NPC {self.npc_id}: timer_quiz reset")
    
    def show_phone_notification(self):
        """Show phone notification"""
        current_time = time.time()
        
        if self.notification_step == 0:
            self.owner.setVisible(True)
            self.play_phone_sound()
            self.send_dialog_message('dialogs.scene100.npc13.0')
            self.notification_step = 1
            self.notification_timer = current_time
            
        elif self.notification_step == 1:
            if current_time - self.notification_timer >= 10.0:
                self.send_dialog_message('dialogs.scene100.npc13.1')
                self.notification_step = 2
                self.notification_timer = current_time
                
        elif self.notification_step == 2:
            if current_time - self.notification_timer >= 3.0:
                self.send_dialog_message('dialogs.scene100.npc13.2')
                self.notification_step = 3
                self.notification_timer = current_time
                
        elif self.notification_step == 3:
            if current_time - self.notification_timer >= 3.0:
                self.send_dialog_message('empty')
                self.notification_step = 0
                self.change_state("READY", "notification completed")
                
                # Reset reminder timer when entering READY state
                self._last_reminder_time = current_time
    
    def play_phone_sound(self):
        """Play phone ring sound"""
        try:
            bge.logic.sendMessage("sound_fx.play", "sound_fx.play|telephone_ring.ogg|volume=0.6")
        except Exception:
            pass
    
    def send_dialog_message(self, message_key):
        """Send message to display dialog"""
        try:
            controller = logic.getCurrentScene().objects.get("Game.Controller")
            if controller:
                controller.sendMessage('add_text', f'char1_text|{message_key}')
                return True
        except Exception:
            pass
        return False

    def send_effect_message(self, message_key):
        """Send message to display effect"""
        try:
            effect_matrix = logic.getCurrentScene().objects.get("Matrix.Effect.Tracked")
            if effect_matrix:
                effect_matrix.sendMessage('effect_disappear')
                return True
        except Exception:
            pass
        return False
 
    def effect_disappear(self):
        """Disappear effect - COMPATIBILITY METHOD"""
        # This method is kept for compatibility with existing code
        return self.trigger_effect_disappear()

# =============================================================================
# PROTECTED GLOBAL INSTANCES
# =============================================================================
_npc_systems = {}
_init_lock = False

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main(cont):
    global _init_lock
    
    owner = cont.owner
    
    # SAFE INITIALIZATION
    if owner.name not in _npc_systems:
        # Protect initialization against race conditions
        if _init_lock:
            return
        _init_lock = True
        try:
            _npc_systems[owner.name] = NPCLogicSystem(owner)
            debug_print(1, f"System created for {owner.name}")
        except Exception as e:
            debug_print(1, f"Error creating system for {owner.name}: {e}")
        finally:
            _init_lock = False
    
    # FORCE INITIALIZATION IF NEEDED
    if not owner.get('_initialized', False):
        if owner.name in _npc_systems:
            try:
                _npc_systems[owner.name].emergency_init()
            except Exception as e:
                debug_print(1, f"Error in emergency_init for {owner.name}: {e}")
    
    # GET SENSORS
    near_dialog = cont.sensors.get("Near_Dialog")
    near_anim = cont.sensors.get("Near_Anim")
    
    # EXECUTE UPDATE
    if owner.name in _npc_systems:
        system = _npc_systems[owner.name]
        
        # Only update if active
        if owner.get('active', True):
            try:
                system.update(near_dialog, near_anim)
            except Exception as e:
                debug_print(1, f"Error in update for {owner.name}: {e}")
        else:
            if owner.visible:
                owner.setVisible(False)
    else:
        debug_print(2, f"System not found for {owner.name}")