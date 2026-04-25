"""
npc_dialog.py

Simplified dialog system for NPCs 1-10

This script manages NPC dialog interactions including proximity detection,
keyboard/mouse input handling, quiz integration, animations, sound effects,
and dialog state management.

Main Features:
    1. Proximity-based dialog activation with E key or mouse click
    2. Multi-step dialog flow with NPC and player dialogue lines
    3. Integration with quiz system for NPC questions
    4. Mouse-over visual feedback with material switching
    5. Character animations (Idle, Talking) with skeleton rig
    6. Voice sound playback during NPC dialogue
    7. Dialog state machine with automatic timer advancement
    8. Object movement (quiz buttons, display objects) for visual feedback

Setup:
    Owners: NPC objects (e.g. npc1, npc2, etc.)
    Logic Bricks: Always, Message and Near Sensors connected to Python controller/module 'npc_dialog.main'
    NPC object requires properties:
        - npc_id (int): NPC identifier (1-10)
        - scene_id (int): Current dialogue scene (1-30)
        - what_object (str): Associated world object name
        - what_quiz (str): Quiz ID for questions

Configurable Variables:
    DEBUG_NPC (bool): Enable debug messages (default: False)
    dialog_type: "LARGE" for 3-step, "SHORT" for 2-step dialogues

Notes:
    - Requires game_access module for game state management
    - Dialog text loaded from JSON files: dialogs_{lang}.json
    - Sound files expected in //Assets/Sounds/npc{npc_id}.ogg
    - Quiz buttons are moved to/from positions using Empty.Quiz.Pos.N
    - Uses aud module for audio playback

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
__description__ = "NPC dialog system with quiz integration and animations"

# =============================================================================
# IMPORTS AND CONFIGURATION
# =============================================================================
import bge
from bge import logic
from bge import events
import json
import time
import aud
import game_access

DEBUG_NPC = False

# =============================================================================
# NPC DIALOG SYSTEM CLASS
# =============================================================================
class NPCDialogSystem:
    def __init__(self, owner):
        self.owner = owner
        self.npc_id = owner.get('npc_id', 1)
        
        # SPECIFIC VALUES FOR NPCS 1-10
        self.scene_id = owner.get('scene_id', 1)
        self.object_name = owner.get('what_object', '') 
        self.quiz_id = owner.get('what_quiz', 'q001')
        
        # QUIZ OBJECT MAPPING (ONLY FOR NPCS 1-10)
        self.quiz_elements = [
            {"button": "Button.Quiz.False.1", "pos_in": "Empty.Quiz.Pos.1", "answer_id": 1},
            {"button": "Button.Quiz.False.2", "pos_in": "Empty.Quiz.Pos.2", "answer_id": 2},
            {"button": "Button.Quiz.True",    "pos_in": "Empty.Quiz.Pos.3", "answer_id": 3}, 
        ]
        
        self.pos_out_name = "Empty.Quiz.Out"
        
        # Debug system
        self.debug_level = 2 if DEBUG_NPC else 0
        
        self._log(1, f"INITIALIZING NPC {self.npc_id} - {owner.name}")
        
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
        self._quiz_answered = False
        
        # Load dialog data
        self.dialog_data = self.load_dialog_data()
        
    def _log(self, level, *args):
        """Logging system controlled by level"""
        if self.debug_level >= level:
            print(f"[NPC{self.npc_id}-{level}]", *args)

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
                    # Search recursively
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
                    if animation_name == 'Talking':
                        end_frame = 30
                    elif animation_name == 'Idle':
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
        """Load dialog JSON"""
        try:
            state = game_access.get_state()
            lang = state.language if state and hasattr(state, 'language') else 'es'
            
            path = logic.expandPath(f"//Assets/Texts/dialogs_{lang}.json")
            with open(path, 'r', encoding='utf-8') as f:
                dialog_data = json.load(f)
                
                self._log(1, f"Dialogs loaded - language: {lang}, scene_id: {self.scene_id}")
                return dialog_data
        except Exception as e:
            self._log(1, f"ERROR loading dialogs: {e}")
            return {"names": {}, "dialogs": {}}
    
    def get_dialog_type(self):
        """Determine flow type based on scene_id"""
        # For normal NPCs (1-10)
        first_scene_for_npc = (self.npc_id - 1) * 3 + 1
        return "LARGE" if self.scene_id == first_scene_for_npc else "SHORT"

    def get_dialog_path(self, speaker, step):
        """Build correct path for dialog"""
        scene_key = f"scene{self.scene_id}"
        speaker_key = speaker if speaker == "player" else f"npc{self.npc_id}"
        path = f"dialogs.{scene_key}.{speaker_key}.{step}"
        
        # Debug if enabled
        if DEBUG_NPC and step == 1:
            self._log(1, f"Using scene_id={self.scene_id} for dialog")
        
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
        """Set speaker states"""
        is_player = speaker == "player"
        is_npc = speaker == "npc"
        
        self.set_property("Player", "player_talking", is_player)
        self.set_property(self.owner.name, "npc_talking", is_npc)
        
        if speaker == "none":
            self.set_property("Player", "player_talking", False)
            self.set_property(self.owner.name, "npc_talking", False)

    # =========================================================================
    # QUIZ BUTTON RESET SYSTEM
    # =========================================================================
    
    def force_reset_all_quiz_buttons(self):
        """Force reset ALL quiz buttons"""
        scn = logic.getCurrentScene()
        for element in self.quiz_elements:
            obj = scn.objects.get(element["button"])
            if obj:
                # Reset state properties
                obj["_button_clicked"] = False
                obj["_button_state"] = "idle"
                obj["_warmup_timer"] = 0.0
                
                # Reset visual properties
                try:
                    obj.color = [1.0, 1.0, 1.0, 1.0]
                    self._log(3, f"Color reset on {obj.name}")
                except Exception as e:
                    self._log(2, f"Could not reset color on {obj.name}: {e}")
                
                # Restore scale if exists
                try:
                    if "_base_scale" in obj:
                        obj.localScale = list(obj["_base_scale"])
                        self._log(3, f"Scale reset on {obj.name}")
                except Exception as e:
                    self._log(2, f"Could not reset scale on {obj.name}: {e}")
                    
        self._log(1, f"All quiz buttons reset for NPC {self.npc_id}")

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

        # Sync scene_id with object
        current_obj_scene = self.owner.get('scene_id', 1)
        if current_obj_scene != self.scene_id:
            self.scene_id = current_obj_scene
            self._log(1, f"Scene_id synced: {self.scene_id}")
        
        # Block re-entry if dialog already ended
        if self.owner.get('_dialog_ended', False):
            self.player_was_close = False
            self.player_nearby = False
            return False

        distance = (self.owner.worldPosition - player.worldPosition).length
        previous_nearby = self.player_nearby
        
        # Update proximity state
        self.player_nearby = (distance < 5.0)
        
        # Handle animations based on proximity
        if self.player_nearby and not previous_nearby:
            if self.current_state == "IDLE" and not self.idle_animation_active:
                self.play_animation('Idle', 1, 13)
                self.idle_animation_active = True
                self._log(2, f"Idle animation activated ({distance:.1f} units)")
        
        elif not self.player_nearby and previous_nearby:
            if self.idle_animation_active and self.current_animation == 'Idle':
                self.stop_animation()
                self._log(2, f"Idle animation deactivated ({distance:.1f} units)")
        
        # Check if close enough to start dialog
        on_dialog = player.get('on_dialog', False)
        
        if distance < 2.0 and not on_dialog:
            if not self.player_was_close:
                self.scene_id = self.owner.get('scene_id', 1)
                self._log(1, f"Starting dialog - NPC {self.npc_id}, Scene {self.scene_id}")
                self.start_dialog_sequence()
                self.player_was_close = True
            return True
        else:
            self.player_was_close = False
            return False

    # =========================================================================
    # OBJECT MOVEMENT LOGIC
    # =========================================================================
    
    def _move_quiz_buttons_to_in(self):
        """Move three quiz buttons to visible positions"""
        scn = logic.getCurrentScene()
        for element in self.quiz_elements:
            obj = scn.objects.get(element["button"])
            pos_in = scn.objects.get(element["pos_in"])
            if obj and pos_in:
                obj.worldPosition = pos_in.worldPosition.copy()
                obj.visible = True
                obj["answer_id"] = element["answer_id"]
    
    def _move_quiz_buttons_to_out(self):
        """Move three quiz buttons to hidden position"""
        scn = logic.getCurrentScene()
        pos_out = scn.objects.get(self.pos_out_name)
        if not pos_out:
            return
        for element in self.quiz_elements:
            obj = scn.objects.get(element["button"])
            if obj:
                obj.worldPosition = pos_out.worldPosition.copy() 
                obj.visible = False
    
    def _move_main_object_to_in(self):
        """Move main object to visible position"""
        scn = logic.getCurrentScene()
        obj = scn.objects.get(self.object_name)
        if not obj:
            return
            
        pos_in = scn.objects.get("Object.Pos.In")
        if not pos_in:
            pos_in = scn.objects.get("Empty.Pos.In")
            
        if obj and pos_in:
            obj.worldPosition = pos_in.worldPosition.copy()
            obj.visible = True
    
    def _move_main_object_to_out(self):
        """Move main object to hidden position"""
        scn = logic.getCurrentScene()
        obj = scn.objects.get(self.object_name)
        if not obj:
            return
            
        pos_out = scn.objects.get("Object.Pos.Out")
        if not pos_out:
            pos_out = scn.objects.get("Empty.Pos.Out")
            
        if obj and pos_out:
            obj.worldPosition = pos_out.worldPosition.copy()
            obj.visible = False

    # =========================================================================
    # QUIZ OBJECT SYSTEM
    # =========================================================================
    
    def _get_quiz_object_name(self):
        """Get QUIZ object name using 'Quiz' prefix"""
        if not self.object_name:
            return ""
        
        # Convert Object.Pal.1 -> Quiz.Pal.1
        parts = self.object_name.split('.')
        if len(parts) >= 3 and parts[0] == "Object":
            return f"Quiz.{parts[1]}.{parts[2]}"
        return self.object_name
    
    def _move_quiz_object_to_in(self):
        """Move QUIZ object to visible position"""
        quiz_obj_name = self._get_quiz_object_name()
        if not quiz_obj_name:
            return
            
        scn = logic.getCurrentScene()
        obj = scn.objects.get(quiz_obj_name)
        if not obj:
            self._log(1, f"QUIZ object not found: {quiz_obj_name}")
            return
            
        pos_in = scn.objects.get("Object.Pos.In")
        if not pos_in:
            pos_in = scn.objects.get("Empty.Pos.In")
            
        if obj and pos_in:
            obj.worldPosition = pos_in.worldPosition.copy()
            obj.visible = True
            self._log(2, f"QUIZ object moved to IN: {quiz_obj_name}")
    
    def _move_quiz_object_to_out(self):
        """Move QUIZ object to hidden position"""
        quiz_obj_name = self._get_quiz_object_name()
        if not quiz_obj_name:
            return
            
        scn = logic.getCurrentScene()
        obj = scn.objects.get(quiz_obj_name)
        if not obj:
            self._log(1, f"QUIZ object not found: {quiz_obj_name}")
            return
            
        pos_out = scn.objects.get("Object.Pos.Out")
        if not pos_out:
            pos_out = scn.objects.get("Empty.Pos.Out")
            
        if obj and pos_out:
            obj.worldPosition = pos_out.worldPosition.copy()
            obj.visible = False
            self._log(2, f"QUIZ object moved to OUT: {quiz_obj_name}")

    # =========================================================================
    # COMPLETE DIALOG SYSTEM
    # =========================================================================
    
    def start_dialog_sequence(self):
        """Start dialog sequence for NPCs 1-10"""
        # Get CURRENT values from object
        self.scene_id = self.owner.get('scene_id', 1)
        self.quiz_id = self.owner.get('what_quiz', 'q001')
        
        self._log(1, f"Dialog started for NPC {self.npc_id}, scene {self.scene_id}, quiz {self.quiz_id}")
        
        # Reset flags
        self._quiz_result_processed = False
        self.owner['_dialog_ended'] = False
        
        game_access.set_dialog_active(True)
        game_access.set_current_npc_id(self.npc_id)
        
        # Reset quiz buttons
        self.force_reset_all_quiz_buttons()
        
        self.set_property("Player", "on_dialog", True)
        self.set_property(self.owner.name, "npc_talking", False)
        self.set_property(self.owner.name, "quiz_on", False)
        self.set_property(self.owner.name, "quiz_reply", False)
        self.set_property("Player", "player_talking", False)
        
        # Activate animation if nearby
        if self.player_nearby and self.current_animation != 'Idle':
            self.play_animation('Idle', 1, 13)
            self.idle_animation_active = True
        
        self.send_message('add_info_text', 'info.show|info_text|2|field=info_text')
        
        try:
            time.sleep(0.25)
        except:
            pass
        
        self.current_state = "STARTING"
        self.dialog_step = 1
        self.e_key_enabled = True
        self.cleaning_previous = False
        self._log(1, f"State: STARTING - Scene {self.scene_id}, waiting for E")
    
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
        """Start second NPC dialog"""
        self.set_property(self.owner.name, "npc_talking", True)
        self.set_property("Player", "player_talking", False)
        
        self.play_animation('Talking', 1, 30)
        self.play_talking_sound()
        
        self.send_message('add_text', f'char1_text|{self.get_dialog_path(f"npc{self.npc_id}", 2)}')
        
        # Move quiz object only in LARGE dialogs
        if self.get_dialog_type() == "LARGE":
            self._move_quiz_object_to_in()
            
        self.cleaning_previous = True
        self.text_to_clean = "player_text"
        self.dialog_step = 4
        
        self.current_state = "WAITING_INPUT"
        self.e_key_enabled = True
        self._log(1, "State: WAITING_INPUT - Showing NPC dialog step 2")
    
    def start_quiz(self):
        """Start QUIZ for NPCs 1-10"""
        self.force_reset_all_quiz_buttons()
        
        dialog_type = self.get_dialog_type()
        
        if dialog_type == "LARGE":
            quiz_step = 3
        else:
            quiz_step = 2
        
        if dialog_type == "SHORT":
            self.send_message('add_text', f'char1_text|{self.get_dialog_path(f"npc{self.npc_id}", quiz_step)}')
            self.cleaning_previous = True
            self.text_to_clean = "player_text"
            self._move_quiz_object_to_in()
        else:
            self.send_message('add_text', f'char1_text|{self.get_dialog_path(f"npc{self.npc_id}", quiz_step)}')
        
        time.sleep(0.10)
        self._move_quiz_buttons_to_in()
        self.set_speaker_states("none")
        
        self.play_animation('Idle', 1, 13)
        self.stop_talking_sound()
                
        self.send_message('add_text_quiz', f'quiz.show|{self.quiz_id}|options_text=quiz_text')
        self._quiz_answered = False
        self.set_property(self.owner.name, "quiz_on", True)
        self.set_property(self.owner.name, "quiz_reply", False)
        
        self.e_key_enabled = False
        self.current_state = "WAITING_INPUT"
        self.dialog_step = 5
        self._log(1, f"QUIZ started - type: {dialog_type}")
    
    def handle_quiz_input(self):
        """Handle QUIZ input"""
        # If already answered in this cycle, don't allow another answer
        if getattr(self, '_quiz_answered', False):
            return False

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
        self.send_message('add_text_quiz', f'quiz.answer|{self.quiz_id}|choice={choice}|options_text=quiz_text|result_text=center_text')
            
        self.set_property(self.owner.name, "quiz_reply", True)
        self.set_property(self.owner.name, "quiz_on", False)

        # Hide buttons IMMEDIATELY
        self._move_quiz_buttons_to_out()
        self._quiz_answered = True
        
        self.e_key_enabled = True
        self.cleaning_previous = False
        self.dialog_step = 6
        self._log(1, f"Quiz processed: choice={choice}")
        
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
        
        # NORMAL NPCS (1-10)
        self.send_message('add_text_quiz', 'quiz_text|empty')
        self._move_quiz_buttons_to_out()
        self._move_quiz_object_to_out()
        
        dialog_type = self.get_dialog_type()
        
        if quiz_success:
            # SUCCESS
            if dialog_type == "LARGE":
                success_step = 6
            else:
                success_step = 4
            
            dialog_path = self.get_dialog_path(f"npc{self.npc_id}", success_step)
            self.send_message('add_text', f'char1_text|{dialog_path}')
            
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
                dialog_path = self.get_dialog_path(f"npc{self.npc_id}", fail_step)
                self.send_message('add_text', f'char1_text|{dialog_path}')
                
                self.play_animation('Talking', 1, 30)
                self.play_talking_sound()
                self.set_speaker_states("npc")
                
                self.dialog_step = 7
                self.e_key_enabled = True
                self.cleaning_previous = False
            else:
                fail_step = 3
                dialog_path = self.get_dialog_path(f"npc{self.npc_id}", fail_step)
                self.send_message('add_text', f'char1_text|{dialog_path}')
                
                self.play_animation('Talking', 1, 30)
                self.play_talking_sound()
                self.set_speaker_states("npc")
                
                self.dialog_step = 8
                self.e_key_enabled = True
                self.cleaning_previous = False
        
        self._log(1, f"NPC {self.npc_id} - Result processed: {'SUCCESS' if quiz_success else 'FAILURE'}")
    
    def show_second_failure_paragraph(self):
        """Second failure paragraph - LARGE only"""
        dialog_type = self.get_dialog_type()
        
        if dialog_type != "LARGE":
            if DEBUG_NPC:
                print(f"[NPC{self.npc_id}] show_second_failure_paragraph on SHORT - skipping")
            self.end_dialog()
            return
        
        dialog_path = self.get_dialog_path(f"npc{self.npc_id}", 5)
        self.send_message('add_text', f'char1_text|{dialog_path}')
        
        self.play_animation('Talking', 1, 30)
        self.play_talking_sound()
        
        self.dialog_step = 8
        self.e_key_enabled = True
        self.cleaning_previous = False
        
        self._log(1, f"NPC {self.npc_id} - Second failure paragraph shown")
    
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
                return True
        
        # DETECTION of 3D button response
        if self.dialog_step == 5:
            quiz_on = self.owner.get('quiz_on', False)
            quiz_reply = self.owner.get('quiz_reply', False)
            
            if not quiz_on and quiz_reply:
                self._log(1, "Advance by 3D button click detected")
                self.dialog_step = 6
                self.e_key_enabled = True
                self.cleaning_previous = False
                self.start_timer_jump()
                return True
        
        # Handle QUIZ input (keyboard)
        if self.handle_quiz_input():
            return True

        # Detection for E key and click
        e_key_pressed = self.e_key_enabled and self._is_e_key_pressed()
        mouse_click_pressed = self.check_mouse_click_direct()
        timer_triggered = self.timer_trigger and not self.cleaning_previous
        
        if not (e_key_pressed or mouse_click_pressed or timer_triggered):
            return False
        
        if self.timer_trigger:
            self.timer_trigger = False
        
        # SIMPLIFIED ADVANCE LOGIC
        if self.dialog_step == 2:
            self.start_player_dialog()
            return True
        
        elif self.dialog_step == 3:
            if self.get_dialog_type() == "LARGE":
                self.start_npc_second_dialog()
            else:
                self.start_quiz()
            return True
        
        elif self.dialog_step == 4:
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
                if self.get_dialog_type() == "LARGE":
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
        """End dialog completely - WITH COMPLETE RESET"""
        self.stop_timer()
        
        # Use individual functions
        game_access.set_dialog_active(False)
        game_access.set_current_npc_id(0)
        self._log(1, f"Dialog end for NPC {self.npc_id}")
        
        # Clean mouse over material
        if self.mouse_over_active or self.was_mouse_over:
            self.change_mesh_material('Black_Backface_Culling')
            self.mouse_over_active = False
            self.was_mouse_over = False
        
        # Clear all texts
        self.send_message('add_text', 'char1_text|empty')
        self.send_message('add_text', 'player_text|empty')
        
        # Clear quiz text
        self.send_message('add_text_quiz', 'quiz_text|empty')
        self._move_quiz_object_to_out()
        self._move_quiz_buttons_to_out()
        
        self.send_message('add_info_text', 'info.clear|field=info_text')
        
        # FINAL RESET: Clear button states
        self.force_reset_all_quiz_buttons()
        
        # CRITICAL: Reset NPC properties
        self.set_property("Player", "on_dialog", False)
        self.set_property("Player", "player_talking", False)
        self.set_property(self.owner.name, "npc_talking", False)
        
        # PROPERTIES THAT MUST BE RESET
        self.set_property(self.owner.name, "quiz_on", False)
        self.set_property(self.owner.name, "quiz_reply", False)
        
        # IMPORTANT: Mark that dialog ended
        self.owner['_dialog_ended'] = True
        
        # Stop animation completely
        self.stop_animation()
        self.stop_talking_sound()
        
        # Reset internal state
        self.current_state = "IDLE"
        self.dialog_step = 1
        self.e_key_enabled = True
        self.cleaning_previous = False
        self.timer_trigger = False
        
        self._log(1, "Dialog ended completely")
    
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

# =============================================================================
# GLOBAL INSTANCES AND MAIN FUNCTION
# =============================================================================
_dialog_systems = {}

def main(cont):
    owner = cont.owner
    obj_key = owner.name
    
    if obj_key not in _dialog_systems:
        try:
            _dialog_systems[obj_key] = NPCDialogSystem(owner)
        except Exception as e:
            print(f"Initialization error on {obj_key}: {e}")
            return
    
    try:
        _dialog_systems[obj_key].update()
    except Exception as e:
        print(f"Error on {obj_key}: {e}")