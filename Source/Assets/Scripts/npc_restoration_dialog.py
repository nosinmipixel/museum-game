"""
npc_restoration_dialog.py

Specific dialog system for NPC11 (Restoration NPC)

This script manages dialog interactions with the Restoration NPC (NPC11),
including quiz handling for restoration questions, button organization based
on correct answers, and integration with the restoration system.

Main Features:
    1. Proximity-based dialog activation with E key or mouse click
    2. Multi-step dialog flow with NPC and player dialogue lines
    3. Dynamic button positioning - correct answer button moves to correct position
    4. Quiz system for restoration questions with 3 answer choices
    5. Mouse-over visual feedback with material switching
    6. Character animations (Restorer.Talking, Restorer.Idle) with skeleton rig
    7. Voice sound playback during NPC dialogue
    8. Dialog state machine with automatic timer advancement

Setup:
    Connect in Logic Bricks as Python controller/module 'npc_restoration_dialog.main'
    NPC object requires properties:
        - npc_id (int): Must be 11
        - scene_id (int): Current dialogue scene (31-45)
        - what_quiz (str): Quiz ID for restoration questions
    Sensors required:
        - Near_Dialog (proximity for dialog activation)
        - Near_Anim (proximity for animation activation)

Configurable Variables:
    DEBUG_NPC11 (bool): Enable debug messages (default: False)
    dialog_type: "LARGE" for 3-step, "SHORT" for 2-step dialogues

Notes:
    - Requires game_access module for game state management
    - Dialog text loaded from JSON files: dialogs_{lang}.json
    - Sound files expected in //Assets/Sounds/npc11.ogg
    - Restoration buttons are dynamically positioned based on correct answer
    - Uses separate message subjects: add_text_restor, restor.show, restor.answer

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
__description__ = "NPC11 Restoration dialog system with dynamic quiz button positioning"

# =============================================================================
# IMPORTS AND CONFIGURATION
# =============================================================================
import bge
from bge import logic
from bge import events
import json
import os
import time
import aud
import game_access

DEBUG_NPC11 = False

# =============================================================================
# NPC11 DIALOG SYSTEM CLASS
# =============================================================================
class NPC11DialogSystem:
    def __init__(self, owner):
        self.owner = owner
        self.npc_id = 11  # Fixed for NPC11
        self.scene_id = owner.get('scene_id', 31)
        self.object_name = owner.get('what_object', '')
        self.quiz_id = owner.get('what_quiz', 'q101')
        
        # Restoration object mapping
        self.restoration_elements = [
            {"button": "Button.Restor.False.1", "pos_in": "Empty.Restor.Pos.1", "answer_id": 1},
            {"button": "Button.Restor.False.2", "pos_in": "Empty.Restor.Pos.2", "answer_id": 2},
            {"button": "Button.Restor.True",    "pos_in": "Empty.Restor.Pos.3", "answer_id": 3}, 
        ]
        
        self.restor_pos_out_name = "Empty.Restor.Out"
        
        # Debug system
        self.debug_level = 2 if DEBUG_NPC11 else 0
        
        self._log(1, f"INITIALIZING NPC11 (RESTORATION) - {owner.name}")
        
        # Dialog states
        self.current_state = "IDLE"
        self.dialog_step = 1
        self.cleaning_previous = False
        self.text_to_clean = ""
        
        # Detection control
        self.player_was_close = False
        self.e_key_enabled = True
        
        # Timer control
        self.timer_trigger = False
        self.timer_start_time = 0
        self.timer_active = False
        self.timer_duration = 3.0
        
        # Animation reference
        self.skeleton = None
        self.current_animation = None
        self.setup_animations()
        
        # Sound system
        self.sound_device = None
        self.sound_talking = None
        self.sound_handle = None
        self.setup_sound_system()
        
        # Mouse over control
        self.mouse_over_active = False
        self.was_mouse_over = False
        
        # Proximity control for animations
        self.player_nearby = False
        self.idle_animation_active = False
        
        # Load dialog data using game_access
        self.dialog_data = self.load_dialog_data()
        
    def _log(self, level, *args):
        """Logging system controlled by level"""
        if self.debug_level >= level:
            print(f"[NPC11-{level}]", *args)

    # =========================================================================
    # INPUT SYSTEM
    # =========================================================================
    
    def _is_key_just_pressed(self, keycode):
        """Simple key press detection"""
        keyboard = logic.keyboard
        if not keyboard:
            return False
            
        try:
            key_input = keyboard.inputs.get(keycode)
            if key_input and key_input.activated:
                return True
        except:
            try:
                return keyboard.events.get(keycode, 0) == logic.KX_INPUT_JUST_ACTIVATED
            except:
                pass
                
        return False
    
    def _is_e_key_pressed(self):
        """E key detection"""
        return self._is_key_just_pressed(events.EKEY)
    
    def _is_quiz_key_pressed(self, key_number):
        """1, 2, 3 key detection"""
        key_map = {1: events.ONEKEY, 2: events.TWOKEY, 3: events.THREEKEY}
        if key_number not in key_map:
            return False
        return self._is_key_just_pressed(key_map[key_number])
    
    def _is_mouse_over_direct(self):
        """Mouse over detection"""
        scn = logic.getCurrentScene()
        camera = scn.objects.get("Camera")
        if not camera:
            return False
        
        mouse = logic.mouse
        if not mouse:
            return False
            
        mx, my = mouse.position
        hit_obj = camera.getScreenRay(mx, my, 1000.0, "")
        
        if hit_obj == self.owner:
            return True
        
        try:
            parent = hit_obj.parent
            while parent:
                if parent == self.owner:
                    return True
                parent = parent.parent
        except:
            pass
        
        return False
    
    def _is_mouse_clicked_direct(self):
        """Mouse click detection"""
        mouse = logic.mouse
        if not mouse:
            return False
            
        try:
            mouse_input = mouse.inputs.get(events.LEFTMOUSE)
            if mouse_input and mouse_input.activated:
                return True
        except:
            try:
                return mouse.events.get(events.LEFTMOUSE, 0) == logic.KX_INPUT_JUST_ACTIVATED
            except:
                pass
                
        return False
    
    def check_mouse_click_direct(self):
        """Check valid mouse click"""
        if not self.e_key_enabled:
            return False
        
        if self.player_was_close and self.e_key_enabled:
            mouse_over = self._is_mouse_over_direct()
            mouse_click = self._is_mouse_clicked_direct()
            
            if mouse_over and mouse_click:
                self._log(2, "Direct click detected")
                return True
        
        return False

    # =========================================================================
    # BASIC SYSTEM FUNCTIONS
    # =========================================================================
    
    def setup_sound_system(self):
        """Initialize sound system"""
        try:
            self.sound_device = aud.Device()
            def _load_sound(rel_path):
                if not rel_path.startswith("//"):
                    rel_path = "//" + rel_path
                return aud.Sound.file(bge.logic.expandPath(rel_path))
            
            sound_path = f"Assets/Sounds/npc{self.npc_id}.ogg"
            self.sound_talking = _load_sound(sound_path)
            self._log(1, f"Sound system initialized")
            
        except Exception as e:
            self._log(1, f"Error initializing sound system: {e}")
            self.sound_device = None
            self.sound_talking = None
    
    def play_talking_sound(self):
        """Play NPC talking sound"""
        try:
            if self.sound_device and self.sound_talking:
                if self.sound_handle and self.sound_handle.status:
                    self.sound_handle.stop()
                
                self.sound_handle = self.sound_device.play(self.sound_talking)
                if self.sound_handle:
                    try: 
                        self.sound_handle.loop_count = 0
                        self.sound_handle.volume = 1.0
                    except Exception: 
                        pass
                self._log(2, f"Talking sound played")
        except Exception as e:
            self._log(1, f"Error playing talking sound: {e}")
    
    def stop_talking_sound(self):
        """Stop NPC talking sound"""
        try:
            if self.sound_handle and self.sound_handle.status:
                self.sound_handle.stop()
                self.sound_handle = None
                self._log(2, f"Talking sound stopped")
        except Exception as e:
            self._log(1, f"Error stopping talking sound: {e}")
    
    def setup_animations(self):
        """Setup skeleton animation references"""
        try:
            children = self.owner.children
            if children and len(children) > 0:
                self.skeleton = children[0]
                
                if hasattr(self.skeleton, 'playAction'):
                    self._log(1, f"Skeleton found: {self.skeleton.name}")
                else:
                    for child in children:
                        if hasattr(child, 'playAction'):
                            self.skeleton = child
                            self._log(1, f"Skeleton found (recursive): {self.skeleton.name}")
                            break
                        for subchild in child.childrenRecursive:
                            if hasattr(subchild, 'playAction'):
                                self.skeleton = subchild
                                self._log(1, f"Skeleton found (sub-child): {self.skeleton.name}")
                                break
                        if self.skeleton:
                            break
            else:
                self._log(1, f"WARNING: No skeleton found for {self.owner.name}")
                    
        except Exception as e:
            self._log(1, f"ERROR setting up animations: {e}")
    
    def play_animation(self, animation_name, start_frame=1, end_frame=0, layer=0):
        """Play animation on skeleton"""
        if self.current_animation == animation_name:
            return
            
        if self.skeleton and animation_name:
            try:
                if end_frame == 0:
                    if animation_name == 'Restorer.Talking':
                        end_frame = 30
                    elif animation_name == 'Restorer.Idle':
                        end_frame = 13
                
                self.skeleton.playAction(
                    animation_name, 
                    start_frame, 
                    end_frame, 
                    layer=layer, 
                    play_mode=bge.logic.KX_ACTION_MODE_LOOP,
                    blendin=5,
                    priority=1
                )
                self.current_animation = animation_name
                self._log(2, f"Animation '{animation_name}' played")
            except Exception as e:
                self._log(1, f"ERROR playing animation '{animation_name}': {e}")
    
    def stop_animation(self):
        """Stop current animation"""
        if self.skeleton:
            try:
                self.skeleton.stopAction(0)
                self.current_animation = None
                self.idle_animation_active = False
                self._log(2, "Animation stopped")
            except Exception as e:
                self._log(1, f"ERROR stopping animation: {e}")
    
    def load_dialog_data(self):
        """Load dialog JSON using game_access"""
        try:
            state = game_access.get_state()
            lang = state.language if state and hasattr(state, 'language') else 'es'
            
            path = logic.expandPath(f"//Assets/Texts/dialogs_{lang}.json")
            with open(path, 'r', encoding='utf-8') as f:
                dialog_data = json.load(f)
                
                # Verification for NPC11 dialogs
                if DEBUG_NPC11:
                    print(f"[NPC11] Dialogs loaded for scenes 31-45")
                    for scene in range(31, 46):
                        scene_key = f"scene{scene}"
                        if scene_key not in dialog_data.get("dialogs", {}):
                            print(f"[NPC11] Warning: {scene_key} not found in dialogs")
                
                self._log(1, f"Dialogs loaded - language: {lang}, scene_id: {self.scene_id}")
                return dialog_data
        except Exception as e:
            self._log(1, f"ERROR loading dialogs: {e}")
            return {"names": {}, "dialogs": {}}
    
    def get_dialog_type(self):
        """Determine flow type based on scene_id"""
        base_scenes = {31, 34, 37, 40, 43}
        return "LARGE" if self.scene_id in base_scenes else "SHORT"
    
    def get_dialog_path(self, speaker, step):
        """Build correct path for dialog"""
        scene_key = f"scene{self.scene_id}"
        speaker_key = speaker if speaker == "player" else f"npc{self.npc_id}"
        path = f"dialogs.{scene_key}.{speaker_key}.{step}"
        
        if DEBUG_NPC11:
            print(f"[NPC11-DIALOG] Dialog path: {path}")
        
        return path
    
    def send_message(self, subject, body):
        """Send message with correct Subject and Body"""
        controller = logic.getCurrentScene().objects.get("Game.Controller")
        if controller:
            controller.sendMessage(subject, body)
            self._log(2, f"Message sent: {subject} > {body}")
            return True
        return False
    
    def set_property(self, obj_name, prop, value):
        """Set property on object"""
        obj = logic.getCurrentScene().objects.get(obj_name)
        if obj:
            obj[prop] = value
            return True
        return False
    
    def clean_previous_text(self):
        """Clean previously prepared text"""
        if self.cleaning_previous and self.text_to_clean:
            self.send_message('add_text', f'{self.text_to_clean}|empty')
            self.cleaning_previous = False
            self.text_to_clean = ""
            self._log(2, f"Previous text cleaned")
            return True
        return False
        
    def set_speaker_states(self, speaker):
        """Configure speaker states"""
        is_player = speaker == "player"
        is_npc = speaker == "npc"
        
        self.set_property("Player", "player_talking", is_player)
        self.set_property(self.owner.name, "npc_talking", is_npc)
        
        if speaker == "none":
            self.set_property("Player", "player_talking", False)
            self.set_property(self.owner.name, "npc_talking", False)

    # =========================================================================
    # BUTTON RESET SYSTEM
    # =========================================================================
    
    def _reset_restoration_buttons(self):
        """Reset restoration buttons"""
        scn = logic.getCurrentScene()
        
        for element in self.restoration_elements:
            obj = scn.objects.get(element["button"])
            if obj:
                # Reset state properties
                obj["_button_clicked"] = False
                obj["_button_state"] = "idle"
                obj["_warmup_timer"] = 0.0
                
                # Reset visual properties
                try:
                    obj.color = [1.0, 1.0, 1.0, 1.0]
                except Exception as e:
                    pass
                
                # Restore scale
                try:
                    if "_base_scale" in obj:
                        obj.localScale = list(obj["_base_scale"])
                except Exception as e:
                    pass
        
        if DEBUG_NPC11:
            self._log(1, f"Restoration buttons reset")

    # =========================================================================
    # MOUSE OVER SYSTEM
    # =========================================================================
    
    def get_mesh_child(self):
        """Get child mesh object"""
        try:
            if self.owner.children and len(self.owner.children) > 0:
                skeleton = self.owner.children[0]
                if skeleton.children and len(skeleton.children) > 0:
                    mesh = skeleton.children[0]
                    return mesh
        except Exception as e:
            self._log(1, f"Error getting mesh child: {e}")
        return None
    
    def change_mesh_material(self, material_name):
        """Change material on child mesh"""
        mesh = self.get_mesh_child()
        if not mesh:
            return False
        
        try:
            import bpy
            mat = bpy.data.materials.get(material_name)
            if mat is None:
                return False

            materials_list = mesh.blenderObject.data.materials
            while len(materials_list) < 2:
                materials_list.append(None)
            
            if len(materials_list) > 1:
                materials_list[1] = mat
                return True
            else:
                return False
                
        except Exception as e:
            return False
    
    def handle_mouse_over(self):
        """Handle mouse over/out events"""
        current_mouse_over = self._is_mouse_over_direct()
        previous_mouse_over = self.was_mouse_over
        
        # MOUSE_OVER
        if current_mouse_over and not previous_mouse_over and self.player_was_close:
            if self.change_mesh_material('White_Backface_Culling'):
                self.mouse_over_active = True
                self.was_mouse_over = True
        
        # MOUSE_EXITED
        elif not current_mouse_over and previous_mouse_over:
            if self.change_mesh_material('Black_Backface_Culling'):
                self.mouse_over_active = False
                self.was_mouse_over = False
        
        # Exit proximity range
        elif not self.player_was_close and previous_mouse_over:
            if self.change_mesh_material('Black_Backface_Culling'):
                self.mouse_over_active = False
                self.was_mouse_over = False

    # =========================================================================
    # PROXIMITY AND ANIMATION SYSTEM
    # =========================================================================
    
    def check_player_proximity(self):
        """Check if player is close to activate animations"""
        player = logic.getCurrentScene().objects.get("Player")
        if not player:
            return False
            
        distance = (self.owner.worldPosition - player.worldPosition).length
        previous_nearby = self.player_nearby
        
        # Update proximity state
        self.player_nearby = (distance < 5.0)
        
        # Check restoration NPC sync properties
        restoration_available = self.owner.get("restoration_available", False)
        has_objects_to_restore = self.owner.get("has_objects_to_restore", False)
        restoration_in_progress = self.owner.get("restoration_in_progress", False)
        
        # BLOCK dialog if:
        # 1. No objects to restore
        # 2. NPC not available for interaction
        # 3. NPC in progress but not ready
        if not has_objects_to_restore:
            self.player_was_close = False
            self.player_nearby = False
            
            # Reset animation if no work
            if self.idle_animation_active:
                self.stop_animation()
                self.idle_animation_active = False
            
            return False
        
        # Handle animations based on proximity
        if self.player_nearby and not previous_nearby:
            # Player entered 5 unit range
            # Only activate animation if there are objects to restore
            has_objects = self.owner.get("has_objects_to_restore", False)
            if not has_objects:
                # No objects, don't activate animation
                self._log(2, "NPC11: No objects - No animation")
                return False
            
            if self.current_state == "IDLE" and not self.idle_animation_active:
                self.play_animation('Idle', 1, 13)
                self.idle_animation_active = True
            
        elif not self.player_nearby and previous_nearby:
            # Player left 5 unit range
            if self.idle_animation_active and self.current_animation == 'Idle':
                self.stop_animation()
        
        # Check if close enough to start dialog
        on_dialog = player.get('on_dialog', False)
        
        if distance < 2.0 and not on_dialog:
            # Extra check before starting dialog
            restoration_available = self.owner.get("restoration_available", False)
            has_objects = self.owner.get("has_objects_to_restore", False)
            
            if not restoration_available or not has_objects:
                self.player_was_close = False
                return False
            
            if not self.player_was_close:
                self._log(1, f"Starting dialog - Scene {self.scene_id}")
                self.start_dialog_sequence()
                self.player_was_close = True
            return True
        else:
            self.player_was_close = False
            return False

    # =========================================================================
    # CORRECT BUTTON POSITIONING
    # =========================================================================
    
    def _get_correct_answer_position(self, quiz_id):
        """Get correct answer position (1, 2, or 3) for restoration quiz"""
        try:
            # Load quiz JSON
            import json
            state = game_access.get_state()
            lang = state.language if state and hasattr(state, 'language') else 'es'
            path = logic.expandPath(f"//Assets/Texts/quiz_{lang}.json")
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            quiz = data.get("quizzes", {}).get(quiz_id, {})
            options = quiz.get("options", [])
            
            if not options:
                self._log(1, f"Quiz {quiz_id} has no options")
                return 3
            
            # Find correct option
            for i, option in enumerate(options):
                if option.get("correct", False):
                    self._log(2, f"Quiz {quiz_id}: correct answer at position {i+1}")
                    return i + 1  # Position 1, 2, or 3
            
            # If no correct option found
            self._log(1, f"No correct option found in {quiz_id}, using position 3")
            return 3
            
        except Exception as e:
            self._log(1, f"Error getting correct position: {e}, using position 3")
            return 3

    # =========================================================================
    # RESTORATION BUTTON SYSTEM
    # =========================================================================
    
    def _move_restoration_buttons_to_in(self):
        """Move restoration buttons REORGANIZING them according to correct answer"""
        scn = logic.getCurrentScene()
        
        # 1. Get base positions
        pos_objects = {
            1: scn.objects.get("Empty.Restor.Pos.1"),
            2: scn.objects.get("Empty.Restor.Pos.2"),
            3: scn.objects.get("Empty.Restor.Pos.3")
        }
        
        # Verify all positions exist
        for pos_num, pos_obj in pos_objects.items():
            if not pos_obj:
                self._log(1, f"Position {pos_num} not found: Empty.Restor.Pos.{pos_num}")
                return
        
        # 2. Determine which option is correct in THIS quiz
        quiz_id = self.owner.get("what_quiz", "q101")
        correct_position = self._get_correct_answer_position(quiz_id)
        
        self._log(1, f"Quiz {quiz_id}: correct answer at position {correct_position}")
        
        # 3. Get button references
        button_true = scn.objects.get("Button.Restor.True")
        button_false1 = scn.objects.get("Button.Restor.False.1")
        button_false2 = scn.objects.get("Button.Restor.False.2")
        
        if not button_true or not button_false1 or not button_false2:
            self._log(1, f"Buttons not found:")
            if not button_true: self._log(1, "  - Button.Restor.True")
            if not button_false1: self._log(1, "  - Button.Restor.False.1")
            if not button_false2: self._log(1, "  - Button.Restor.False.2")
            return
        
        # 4. Determine positions for false buttons (the two positions that are NOT correct)
        false_positions = [1, 2, 3]
        false_positions.remove(correct_position)
        
        # Position for first false button
        false_pos_1 = false_positions[0]
        # Position for second false button
        false_pos_2 = false_positions[1]
        
        # 5. REORGANIZE: Place Button.Restor.True at correct position
        button_true.worldPosition = pos_objects[correct_position].worldPosition.copy()
        button_true.visible = True
        button_true["answer_id"] = correct_position
        button_true["is_correct"] = True
        
        # 6. Place Button.Restor.False.1 at first false position
        button_false1.worldPosition = pos_objects[false_pos_1].worldPosition.copy()
        button_false1.visible = True
        button_false1["answer_id"] = false_pos_1
        button_false1["is_correct"] = False
        
        # 7. Place Button.Restor.False.2 at second false position
        button_false2.worldPosition = pos_objects[false_pos_2].worldPosition.copy()
        button_false2.visible = True
        button_false2["answer_id"] = false_pos_2
        button_false2["is_correct"] = False
        
        self._log(1, f"Buttons REORGANIZED for quiz {quiz_id}:")
        self._log(1, f"  Position {correct_position}: Button.Restor.True (answer_id={correct_position}, correct)")
        self._log(1, f"  Position {false_pos_1}: Button.Restor.False.1 (answer_id={false_pos_1}, incorrect)")
        self._log(1, f"  Position {false_pos_2}: Button.Restor.False.2 (answer_id={false_pos_2}, incorrect)")
    
    def _move_restoration_buttons_to_out(self):
        """Move restoration buttons off screen"""
        scn = logic.getCurrentScene()
        pos_out = scn.objects.get(self.restor_pos_out_name)
        
        if not pos_out:
            if DEBUG_NPC11:
                self._log(1, f"OUT position not found: {self.restor_pos_out_name}")
            return
        
        for element in self.restoration_elements:
            obj = scn.objects.get(element["button"])
            if obj:
                obj.worldPosition = pos_out.worldPosition.copy()
                obj.visible = False
                
                if DEBUG_NPC11:
                    self._log(2, f"Button {obj.name} moved to OUT")

    # =========================================================================
    # COMPLETE DIALOG SYSTEM
    # =========================================================================
    
    def start_dialog_sequence(self):
        """Start dialog sequence - SPECIFIC VERSION FOR NPC11"""
        updated_scene_id = self.owner.get("scene_id", 31)
        self.scene_id = updated_scene_id
        self.quiz_id = self.owner.get('what_quiz', 'q101')
        
        key = (self.owner.get("restoration_item_type", ""), 
               self.owner.get("restoration_item_id", 0))
        
        print(f"[NPC11-DIALOG] Dialog started:")
        print(f"  scene_id: {self.scene_id}")
        print(f"  quiz_id: {self.quiz_id}")
        print(f"  object: {key[0]}#{key[1]}")
        
        self._quiz_result_processed = False
        
        game_access.set_dialog_active(True)
        game_access.set_current_npc_id(self.npc_id)
        self._log(1, f"Dialog started for NPC {self.npc_id}, scene {self.scene_id}")
        
        self._reset_restoration_buttons()
        
        self.set_property("Player", "on_dialog", True)
        self.set_property(self.owner.name, "npc_talking", False)
        self.set_property(self.owner.name, "quiz_on", False)
        self.set_property(self.owner.name, "quiz_reply", False)
        self.set_property("Player", "player_talking", False)
        
        if self.skeleton and not self.skeleton.isPlayingAction(0):
            self.play_animation('Idle', 1, 13)
            self.idle_animation_active = True
        
        self.send_message('add_info_text', 'info.show|info_text|2|field=info_text')
        
        try:
            import time
            time.sleep(0.25)
        except:
            pass
        
        self.current_state = "STARTING"
        self.dialog_step = 1
        self.e_key_enabled = True
        self.cleaning_previous = False
        self._log(1, "State: STARTING - Showing info, waiting for E")
    
    def handle_starting_state(self):
        """Handle initial state"""
        if not self.e_key_enabled:
            return False
        
        e_key_pressed = self._is_e_key_pressed()
        mouse_click_pressed = self.check_mouse_click_direct()
        
        if e_key_pressed or mouse_click_pressed:
            self._log(1, "E key or click pressed - starting dialog")
            self.start_first_dialog()
            return True
        return False
    
    def start_first_dialog(self):
        """Start first dialog after pressing E"""
        self.send_message('add_info_text', 'info.clear|field=info_text')
        self.send_message('add_text', f'char1_text|{self.get_dialog_path(f"npc{self.npc_id}", 1)}')
        self.set_speaker_states("npc")
        
        self.play_animation('Talking', 1, 30)
        self.play_talking_sound()
        
        self.current_state = "WAITING_INPUT"
        self.dialog_step = 2
        self.e_key_enabled = True
        self.cleaning_previous = False
        self._log(1, "State: WAITING_INPUT - Showing NPC dialog step 1, waiting for E")
    
    def start_player_dialog(self):
        """Start player dialog"""
        self.set_property("Player", "player_talking", True)
        self.set_property(self.owner.name, "npc_talking", False)
        
        self.play_animation('Idle', 1, 13)
        self.stop_talking_sound()
        
        self.send_message('add_text', f'player_text|{self.get_dialog_path("player", 1)}')
        
        self.cleaning_previous = True
        self.text_to_clean = "char1_text"
        
        self.current_state = "WAITING_INPUT"
        self.dialog_step = 3
        self.e_key_enabled = True
        self._log(1, "State: WAITING_INPUT - Showing Player dialog")
    
    def start_npc_second_dialog(self):
        """Start second NPC dialog (quiz question for NPC11)"""
        self.set_property(self.owner.name, "npc_talking", True)
        self.set_property("Player", "player_talking", False)
        
        self.play_animation('Talking', 1, 30)
        self.play_talking_sound()
        
        dialog_type = self.get_dialog_type()
        
        # LARGE: npc11[2] is context, npc11[3] is question
        # SHORT: npc11[2] is direct question
        if dialog_type == "LARGE":
            # Show step 2 (context) before question
            dialog_path = f'char1_text|{self.get_dialog_path(f"npc{self.npc_id}", 2)}'
            self.send_message('add_text', dialog_path)
            
            print(f"[NPC11-DIALOG] LARGE step 2 (context): dialogs.scene{self.scene_id}.npc11.2")
            print(f"  Waiting for player E...")
            
            # Clean previous text but DO NOT process input until next frame
            self.cleaning_previous = True
            self.text_to_clean = "player_text"
            self.dialog_step = 4  # Next: show question (step 3)
        else:
            # SHORT: Show direct question (step 2)
            dialog_path = f'char1_text|{self.get_dialog_path(f"npc{self.npc_id}", 2)}'
            self.send_message('add_text', dialog_path)
            
            print(f"[NPC11-DIALOG] SHORT step 2 (question): dialogs.scene{self.scene_id}.npc11.2")
            print(f"  Waiting for player E...")
            
            # Clean previous text
            self.cleaning_previous = True
            self.text_to_clean = "player_text"
            self.start_quiz()
        
        self.current_state = "WAITING_INPUT"
        self.e_key_enabled = True
        self._log(1, "State: WAITING_INPUT - Showing NPC dialog step 2")
    
    def setup_restoration_quiz(self):
        """Setup restoration quiz - DOES NOT show question, only buttons"""
        quiz_id = self.owner.get("what_quiz", "q101")
        scene_id = self.scene_id
        dialog_type = self.get_dialog_type()
        
        print(f"\n[NPC11-QUIZ] SETTING UP QUIZ")
        print(f"  Quiz ID: {quiz_id}, Scene: {scene_id}, Type: {dialog_type}")
        print(f"  Question already shown in start_npc_second_dialog()")
        
        try:
            import time
            time.sleep(0.10)
        except:
            pass
        
        self._move_restoration_buttons_to_in()
        self.set_speaker_states("none")
        
        self.play_animation('Idle', 1, 13)
        self.stop_talking_sound()
        
        # Show only options
        self.send_message('add_text_restor', f'restor.show|{quiz_id}|options_text=restor_text')
        self.set_property(self.owner.name, "quiz_on", True)
        self.set_property(self.owner.name, "quiz_reply", False)
        
        self.e_key_enabled = False
        self.current_state = "WAITING_INPUT"
        self.dialog_step = 5
        
        print(f"  Quiz configured\n")
    
    def start_quiz(self):
        """Start restoration quiz"""
        self.setup_restoration_quiz()
    
    def handle_quiz_input(self):
        """Handle QUIZ input"""
        quiz_on = self.owner.get('quiz_on', False)
        quiz_reply = self.owner.get('quiz_reply', False)
        
        if quiz_on and not quiz_reply and self.dialog_step == 5:
            for key_num in [1, 2, 3]:
                if self._is_quiz_key_pressed(key_num):
                    self.process_quiz_answer(key_num)
                    return True
        
        return False
    
    def process_quiz_answer(self, choice):
        """Process QUIZ answer"""
        self.send_message('add_text_restor', f'restor.answer|{self.quiz_id}|choice={choice}|options_text=restor_text|result_text=center_text')
            
        self.set_property(self.owner.name, "quiz_reply", True)
        self.set_property(self.owner.name, "quiz_on", False)
        
        is_correct = choice == 3
        self.set_property(self.owner.name, "quiz_success", is_correct)
        
        self.e_key_enabled = True
        self.cleaning_previous = False
        self.dialog_step = 6
        self._log(1, f"Quiz processed: {'SUCCESS' if is_correct else 'FAILURE'}")
        
        self.start_timer_jump()
    
    def start_timer_jump(self):
        """Start timer for automatic advancement"""
        self.timer_active = True
        self.timer_start_time = time.time()
        self.timer_trigger = False
        self._log(2, "Timer started (3 seconds)")
    
    def update_timer(self):
        """Update timer - must be called each frame"""
        if self.timer_active:
            current_time = time.time()
            elapsed_time = current_time - self.timer_start_time
            
            if elapsed_time >= self.timer_duration:
                self.timer_trigger = True
                self.timer_active = False
                self._log(2, "Timer completed - automatic advance triggered")
    
    def stop_timer(self):
        """Stop timer"""
        self.timer_active = False
        self.timer_trigger = False
        self._log(2, "Timer stopped")
    
    def handle_quiz_result(self):
        """Handle QUIZ result"""
        self.stop_timer()
        quiz_success = self.owner.get('quiz_success', False)
        
        self.send_message('add_text_restor', 'restor_text|empty')
        self._move_restoration_buttons_to_out()
        
        dialog_type = self.get_dialog_type()
        
        print(f"\n[NPC11-RESULT] PROCESSING RESULT")
        print(f"  Scene: {self.scene_id}, Type: {dialog_type}, Success: {quiz_success}")
        
        if quiz_success:
            # SUCCESS
            if dialog_type == "LARGE":
                success_step = 6
            else:
                success_step = 4
            
            dialog_path = self.get_dialog_path(f"npc{self.npc_id}", success_step)
            self.send_message('add_text', f'char1_text|{dialog_path}')
            
            print(f"  Success step {success_step}: {dialog_path}")
            
            self.play_animation('Talking', 1, 30)
            self.play_talking_sound()
            self.set_speaker_states("npc")
            
            self.dialog_step = 7
            self.e_key_enabled = True
            self.cleaning_previous = False
        
        else:
            # FAILURE
            if dialog_type == "LARGE":
                fail_step = 4
            else:
                fail_step = 3
            
            dialog_path = self.get_dialog_path(f"npc{self.npc_id}", fail_step)
            self.send_message('add_text', f'char1_text|{dialog_path}')
            
            print(f"  Failure step {fail_step}: {dialog_path}")
            
            self.play_animation('Talking', 1, 30)
            self.play_talking_sound()
            self.set_speaker_states("npc")
            
            if dialog_type == "LARGE":
                self.dialog_step = 7
            else:
                self.dialog_step = 8
            
            self.e_key_enabled = True
            self.cleaning_previous = False
        
        print(f"  Next dialog_step: {self.dialog_step}\n")
    
    def show_second_failure_paragraph(self):
        """Second failure paragraph - LARGE only"""
        dialog_type = self.get_dialog_type()
        
        if dialog_type != "LARGE":
            if DEBUG_NPC11:
                print(f"[NPC11] show_second_failure_paragraph on SHORT - skipping")
            self.end_dialog()
            return
        
        # LARGE: Show step 5 (second paragraph)
        dialog_path = self.get_dialog_path(f"npc{self.npc_id}", 5)
        self.send_message('add_text', f'char1_text|{dialog_path}')
        
        if DEBUG_NPC11:
            print(f"[NPC11] Second failure paragraph: {dialog_path}")
        
        self.play_animation('Talking', 1, 30)
        self.play_talking_sound()
        
        self.dialog_step = 8
        self.e_key_enabled = True
        self.cleaning_previous = False
    
    def handle_final_dialog(self):
        """Handle final dialog after result"""
        quiz_success = self.owner.get('quiz_success', False)
        
        if quiz_success:
            self.send_message('add_text', 'char1_text|empty')
            self.end_dialog()
        else:
            self.end_dialog()
    
    def handle_waiting_input_state(self):
        """Handle waiting input state"""
        if self.timer_active:
            self.update_timer()
        
        # FIRST: Clean previous text if needed
        if self.cleaning_previous:
            if self.clean_previous_text():
                # Text cleaned - DO NOT process more input this frame
                return True
        
        # Detection of 3D button response
        is_quiz_answered_externally = False
        
        quiz_on = self.owner.get('quiz_on', False)
        quiz_reply = self.owner.get('quiz_reply', False)
        
        if self.dialog_step == 5 and quiz_on == False and quiz_reply == True:
            is_quiz_answered_externally = True
        
        if is_quiz_answered_externally:
            self._log(1, "Advance by 3D button click")
            self.dialog_step = 6
            self.e_key_enabled = True
            self.cleaning_previous = False
            self.start_timer_jump()
            return True

        if self.handle_quiz_input():
            return True

        # Only process input if there is REAL user E key or click
        e_key_pressed = self.e_key_enabled and self._is_e_key_pressed()
        mouse_click_pressed = self.check_mouse_click_direct()
        timer_triggered = self.timer_trigger and not self.cleaning_previous
        
        # IMPORTANT: If NO user input, DO NOT advance
        if not (e_key_pressed or mouse_click_pressed or timer_triggered):
            return False
        
        # If we reach here, there is REAL user input
        if self.timer_trigger:
            self.timer_trigger = False
        
        dialog_type = self.get_dialog_type()
        
        print(f"[NPC11-INPUT] Input detected at dialog_step={self.dialog_step}")
        
        if self.dialog_step == 2:
            print(f"[NPC11-INPUT] -> Calling start_player_dialog()")
            self.start_player_dialog()
            return True
        
        elif self.dialog_step == 3:
            print(f"[NPC11-INPUT] -> Calling start_npc_second_dialog()")
            self.start_npc_second_dialog()
            return True
        
        elif self.dialog_step == 4:
            # Only for LARGE: show question (step 3)
            if dialog_type == "LARGE":
                print(f"[NPC11-INPUT] -> Showing question (npc11[3])")
                
                self.set_property(self.owner.name, "npc_talking", True)
                self.play_animation('Talking', 1, 30)
                self.play_talking_sound()
                
                dialog_path = f'char1_text|{self.get_dialog_path(f"npc{self.npc_id}", 3)}'
                self.send_message('add_text', dialog_path)
                
                print(f"[NPC11-DIALOG] LARGE step 3 (QUESTION): dialogs.scene{self.scene_id}.npc11.3")
                
                self.cleaning_previous = False
                self.e_key_enabled = True
                self.start_quiz()
                return True
        
        elif self.dialog_step == 5:
            print(f"[NPC11-INPUT] -> Starting quiz")
            self.start_quiz()
            return True
        
        elif self.dialog_step == 6:
            self.handle_quiz_result()
            return True
        
        elif self.dialog_step == 7:
            if self.owner.get('quiz_success', False):
                self.handle_final_dialog()
                return True
            else:
                if dialog_type == "LARGE":
                    self.show_second_failure_paragraph()
                    return True
                else:
                    self.end_dialog()
                    return True
        
        elif self.dialog_step == 8:
            self.end_dialog()
            return True
        
        if self.dialog_step >= 9:
            return self.handle_final_steps()
            
        return False
    
    def handle_final_steps(self):
        """Handle final dialog steps (9+)"""
        if self.dialog_step >= 9:
            self.end_dialog()
            return True
        return False
    
    def end_dialog(self):
        """End dialog completely - SPECIFIC VERSION FOR NPC11"""
        self.stop_timer()
        
        game_access.set_dialog_active(False)
        game_access.set_current_npc_id(0)
        self._log(1, f"Dialog end for NPC {self.npc_id}")
        
        if self.mouse_over_active or self.was_mouse_over:
            self.change_mesh_material('Black_Backface_Culling')
            self.mouse_over_active = False
            self.was_mouse_over = False
        
        self.send_message('add_text', 'char1_text|empty')
        self.send_message('add_text', 'player_text|empty')
        
        # Clear restoration quiz text
        self.send_message('add_text_restor', 'restor_text|empty')
        self._move_restoration_buttons_to_out()
        
        self.send_message('add_info_text', 'info.clear|field=info_text')
        
        # FINAL RESET: Clear button states
        self._reset_restoration_buttons()
        
        self.set_property("Player", "on_dialog", False)
        self.set_property("Player", "player_talking", False)
        self.set_property(self.owner.name, "npc_talking", False)
        
        # CRITICAL: For NPC11, DO NOT reset quiz_on or quiz_reply
        #    These properties are needed in npc_restoration_logic.py
        self._log(1, f"NPC11: quiz_on/quiz_reply properties NOT reset (handled by npc_restoration_logic.py)")
        
        # Stop animation completely
        self.stop_animation()
        self.stop_talking_sound()
        
        self.current_state = "IDLE"
        self.dialog_step = 1
        self.e_key_enabled = True
        self.cleaning_previous = False
        self.timer_trigger = False
        
        self._log(1, "Dialog ended")
    
    def update(self):
        """Update per frame"""
        try:
            # Handle mouse over
            self.handle_mouse_over()
            
            if self.current_state == "IDLE":
                # Check player proximity
                self.check_player_proximity()
            elif self.current_state == "STARTING":
                self.handle_starting_state()
            elif self.current_state == "WAITING_INPUT":
                self.handle_waiting_input_state()
                
        except Exception as e:
            self._log(1, f"Dialog error: {e}")
            
    def debug_info(self):
        """Display debug information"""
        self._log(1, f"=== DEBUG NPC{self.npc_id} ===")
        self._log(1, f"State: {self.current_state}")
        self._log(1, f"Step: {self.dialog_step}")
        self._log(1, f"Quiz ID: {self.quiz_id}")
        self._log(1, f"Scene ID: {self.scene_id}")
        self._log(1, f"Quiz on: {self.owner.get('quiz_on', False)}")
        self._log(1, f"Quiz reply: {self.owner.get('quiz_reply', False)}")
        self._log(1, f"Quiz success: {self.owner.get('quiz_success', False)}")
        self._log(1, f"=====================")

# =============================================================================
# GLOBAL INSTANCES AND MAIN FUNCTION
# =============================================================================
_dialog_systems = {}

def main(cont):
    owner = cont.owner
    obj_key = owner.name
    
    if obj_key not in _dialog_systems:
        try:
            _dialog_systems[obj_key] = NPC11DialogSystem(owner)
        except Exception as e:
            print(f"Initialization error on {obj_key}: {e}")
            return
    
    try:
        _dialog_systems[obj_key].update()
    except Exception as e:
        print(f"Error on {obj_key}: {e}")