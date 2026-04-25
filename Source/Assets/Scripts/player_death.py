"""
player_death.py

Manages player death system including animations, visual effects, and restart flow.

This script handles the complete player death sequence: detecting death, playing
death animation, triggering Matrix effect, showing restart UI, and coordinating
the restart process with proper state management.

Main Features:
    1. Player death detection via health check (health <= 0)
    2. Death animation playback and maintenance
    3. Matrix effect trigger at death location
    4. Restart UI display with button interaction
    5. Coordinated restart with position restoration
    6. Reverse death animation playback on restart
    7. Sound effects for death and restart
    8. Background music context switching

Setup:
    Connect to Logic Bricks as Python controller with module 'player_death.main'
    Requires 'Player' object with health property
    Requires 'charA_metarig.001' rig with 'Player.Death' and 'Player.Idle' animations
    Requires 'Matrix.Effect.Tracked' object for visual effects
    Requires 'Button.Restart' and 'Empty.Button.Restart' for UI

Configurable Variables:
    DEBUG_MODE (bool): Enable debug logging (default: True)
    ANIMATION_DURATION (float): Death animation duration in seconds (default: 1.0)
    MATRIX_DURATION (float): Matrix effect duration in seconds (default: 0.5)
    RESTART_MATRIX_DURATION (float): Restart matrix effect duration (default: 0.5)

Notes:
    - Death states: NONE, START, ANIM, EFFECTS, UI, WAIT, RESTART
    - Requires game_access module for player health data
    - Uses sound_background module for music context switching
    - Restart can be triggered via button or external call
    - Player position is restored to [0, 0, 0.7] on restart
    - Death animation plays in reverse on restart for smooth transition

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
__description__ = "Manages player death system including animations and restart flow"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic
import math
from sound_background import set_background_context

# =============================================================================
# CONFIGURATION
# =============================================================================
DEBUG_MODE = True

# Death states
DEATH_STATE_NONE = 0      # Player alive
DEATH_STATE_START = 1     # Starting death
DEATH_STATE_ANIM = 2      # Death animation in progress
DEATH_STATE_EFFECTS = 3   # Visual effects
DEATH_STATE_UI = 4        # Showing death UI
DEATH_STATE_WAIT = 5      # Waiting for restart
DEATH_STATE_RESTART = 6   # Restart state

# Timings (in seconds)
ANIMATION_DURATION = 1.0    # Death animation duration
MATRIX_DURATION = 0.5       # Matrix effect duration
RESTART_MATRIX_DURATION = 0.5  # Restart matrix effect duration

# =============================================================================
# DEATH SYSTEM CLASS
# =============================================================================
class DeathSystem:
    """Death system - ONLY for the player"""
    
    # State variables (static for sharing between instances)
    current_state = DEATH_STATE_NONE
    state_start_time = 0
    death_detected = False
    restart_initiated = False  # Flag indicating restart was initiated FROM THE BUTTON
    
    # Single execution flags
    death_anim_started = False
    matrix_effect_played = False
    matrix_hidden = False
    ui_shown = False
    death_sound_played = False
    restart_sound_played = False
    restart_matrix_played = False
    player_position_restored = False  # Flag to know if position already restored
    
    # Reference to rig to maintain animation
    death_rig = None
    death_animation_active = False
    
    # Restart position for Matrix effect
    restart_position = None
    
    @staticmethod
    def log(message):
        """Basic logging"""
        if DEBUG_MODE:
            print(f"[PLAYER_DEATH] {message}")
    
    @staticmethod
    def check_player_dead():
        """Checks if player is dead"""
        try:
            from game_access import get_player
            player = get_player()
            if player and hasattr(player, 'health'):
                health = player.health
                is_dead = health <= 0
                
                # Only detect the first time
                if is_dead and not DeathSystem.death_detected:
                    DeathSystem.log(f"Player dead! Health: {health}")
                    DeathSystem.death_detected = True
                    return True
                elif not is_dead:
                    DeathSystem.death_detected = False
                
                return is_dead
        except Exception:
            pass
        return False
    
    @staticmethod
    def set_state(new_state):
        """Changes to new state and resets execution flags"""
        if DeathSystem.current_state != new_state:
            DeathSystem.current_state = new_state
            DeathSystem.state_start_time = logic.getFrameTime()
            
            # Reset execution flags for the new state
            if new_state == DEATH_STATE_ANIM:
                DeathSystem.death_anim_started = False
            elif new_state == DEATH_STATE_EFFECTS:
                DeathSystem.matrix_effect_played = False
                DeathSystem.matrix_hidden = False
            elif new_state == DEATH_STATE_UI:
                DeathSystem.ui_shown = False
            elif new_state == DEATH_STATE_RESTART:
                DeathSystem.restart_sound_played = False
                DeathSystem.restart_matrix_played = False
                DeathSystem.player_position_restored = False
                DeathSystem.restart_position = None
            
            # Log state change
            state_names = {
                DEATH_STATE_NONE: "Player alive",
                DEATH_STATE_START: "Starting death",
                DEATH_STATE_ANIM: "Death animation",
                DEATH_STATE_EFFECTS: "Matrix effects",
                DEATH_STATE_UI: "Showing UI",
                DEATH_STATE_WAIT: "Waiting for restart",
                DEATH_STATE_RESTART: "Restarting"
            }
            
            if new_state in state_names:
                DeathSystem.log(f"State: {state_names[new_state]}")
            
            return True
        return False
    
    @staticmethod
    def state_elapsed():
        """Time elapsed in current state"""
        return logic.getFrameTime() - DeathSystem.state_start_time
    
    @staticmethod
    def execute(owner):
        """Executes the death system according to current state"""
        
        # IMPORTANT: If restart was initiated from button, go directly to RESTART state
        if DeathSystem.restart_initiated and DeathSystem.current_state != DEATH_STATE_RESTART:
            DeathSystem.log("Restart initiated from external button")
            DeathSystem.set_state(DEATH_STATE_RESTART)
            DeathSystem.restart_initiated = False  # Reset flag
            return
        
        # If player is alive, reset if necessary
        if not DeathSystem.check_player_dead():
            if DeathSystem.current_state != DEATH_STATE_NONE:
                DeathSystem.reset_all()
            return
        
        # If player is dead and we are in NONE state, start
        if DeathSystem.current_state == DEATH_STATE_NONE:
            DeathSystem.set_state(DEATH_STATE_START)
            
            # Block player movement
            owner.worldLinearVelocity = [0, 0, 0]
            owner.worldAngularVelocity = [0, 0, 0]
            owner['on_dialog'] = True
        
        # State START: brief pause before animation
        elif DeathSystem.current_state == DEATH_STATE_START:
            if DeathSystem.state_elapsed() > 0.2:
                DeathSystem.set_state(DEATH_STATE_ANIM)
        
        # State ANIM: start Death animation
        elif DeathSystem.current_state == DEATH_STATE_ANIM:
            if not DeathSystem.death_anim_started:
                DeathSystem.start_death_animation()
                DeathSystem.death_anim_started = True
                DeathSystem.death_animation_active = True
            
            if not DeathSystem.death_sound_played:
                DeathSystem.play_death_sound()
                DeathSystem.death_sound_played = True
            
            if DeathSystem.state_elapsed() > ANIMATION_DURATION:
                DeathSystem.set_state(DEATH_STATE_EFFECTS)
        
        # State EFFECTS: Matrix effect
        elif DeathSystem.current_state == DEATH_STATE_EFFECTS:
            if DeathSystem.death_animation_active:
                DeathSystem.maintain_death_animation()
            
            if not DeathSystem.matrix_effect_played:
                DeathSystem.trigger_matrix_effect_death()
                DeathSystem.matrix_effect_played = True
            
            # Only wait a minimum time, effect self-manages
            if DeathSystem.state_elapsed() > MATRIX_DURATION:
                DeathSystem.set_state(DEATH_STATE_UI)
        
        # State UI: show interface
        elif DeathSystem.current_state == DEATH_STATE_UI:
            if DeathSystem.death_animation_active:
                DeathSystem.maintain_death_animation()
            
            if not DeathSystem.ui_shown:
                DeathSystem.show_death_ui_once()
                DeathSystem.ui_shown = True
            
            if DeathSystem.state_elapsed() > 0.1:
                DeathSystem.set_state(DEATH_STATE_WAIT)
        
        # State WAIT: wait for restart
        elif DeathSystem.current_state == DEATH_STATE_WAIT:
            if DeathSystem.death_animation_active:
                DeathSystem.maintain_death_animation()
            
            # Check if restart button was pressed
            if DeathSystem.check_restart_button():
                DeathSystem.set_state(DEATH_STATE_RESTART)
        
        # State RESTART: handle restart effects
        elif DeathSystem.current_state == DEATH_STATE_RESTART:
            DeathSystem.process_restart_state()
    
    @staticmethod
    def process_restart_state():
        """Processes the restart state - CORRECTED FLOW"""
        
        # 1. FIRST: RESTORE PLAYER POSITION (only once)
        if not DeathSystem.player_position_restored:
            DeathSystem.restore_player_position()
            DeathSystem.player_position_restored = True
        
        # 2. Maintain animation during effect (if still active)
        if DeathSystem.death_animation_active:
            DeathSystem.maintain_death_animation()
        
        # 3. Wait a bit for position to be properly set
        if DeathSystem.state_elapsed() < 0.1:  # Wait 100ms for position stabilization
            return  # Keep waiting
        
        # 4. Activate appearance effect at new player position (only once)
        if not DeathSystem.restart_matrix_played and DeathSystem.restart_position:
            DeathSystem.trigger_restart_matrix_effect()
            DeathSystem.restart_matrix_played = True
        
        # 5. Play restart sound immediately after
        if not DeathSystem.restart_sound_played:
            DeathSystem.play_restart_sound()
            DeathSystem.restart_sound_played = True
        
        # 6. Wait for total effect duration (Matrix object self-manages)
        if DeathSystem.state_elapsed() < RESTART_MATRIX_DURATION:
            return  # Keep waiting
        
        # 7. Complete restart (Matrix effect will have auto-hidden)
        DeathSystem.complete_restart()
    
    @staticmethod
    def restore_player_position():
        """RESTORES player position BEFORE showing Matrix effect"""
        DeathSystem.log("Restoring player position...")
        
        try:
            scene = logic.getCurrentScene()
            player_obj = scene.objects.get("Player")
            
            if player_obj:
                # Define restart position
                DeathSystem.restart_position = [0, 0, 0.7]
                
                # Restore player position
                player_obj.worldPosition = DeathSystem.restart_position
                player_obj.worldOrientation = [0, 0, 0]
                
                # Reset properties
                try:
                    player_obj['on_dialog'] = False
                except:
                    try:
                        if hasattr(player_obj, 'on_dialog'):
                            player_obj.on_dialog = False
                    except:
                        pass
                
                # Reset velocity
                if hasattr(player_obj, 'worldLinearVelocity'):
                    player_obj.worldLinearVelocity = [0, 0, 0]
                    player_obj.worldAngularVelocity = [0, 0, 0]
                
                DeathSystem.log(f"Player position restored: {DeathSystem.restart_position}")
                return True
            else:
                DeathSystem.log("Player object not found")
                return False
                
        except Exception as e:
            DeathSystem.log(f"Error restoring player position: {e}")
            # Default position
            DeathSystem.restart_position = [0, 0, 0.7]
            return False
    
    @staticmethod
    def init_restart_from_button():
        """Method for button to initiate restart"""
        DeathSystem.log("Initiating restart from external button...")
        DeathSystem.restart_initiated = True
    
    @staticmethod
    def start_death_animation():
        """Starts Death animation"""
        DeathSystem.log("Starting Death animation...")
        
        try:
            scene = logic.getCurrentScene()
            rig_object = None
            
            # Find player rig
            rig_object = scene.objects.get("charA_metarig.001")
            if not rig_object:
                for obj in scene.objects:
                    if "charA_metarig" in obj.name:
                        rig_object = obj
                        break
            
            if rig_object:
                DeathSystem.death_rig = rig_object
                rig_object.stopAction(1)

                anim_name = "Player.Death"
                try:
                    rig_object.playAction(
                        anim_name,
                        1, 30,
                        layer=1,
                        priority=0,
                        blendin=5,
                        play_mode=logic.KX_ACTION_MODE_PLAY,
                        speed=1.0,
                    )
                    DeathSystem.log(f"Animation '{anim_name}' started")
                    return True
                except Exception as e:
                    DeathSystem.log(f"Error starting animation: {str(e)}")
                    return False
            else:
                DeathSystem.log("Player rig not found")
                return False
                
        except Exception as e:
            DeathSystem.log(f"General error in Death animation: {str(e)}")
        
        return False
    
    @staticmethod
    def maintain_death_animation():
        """Maintains Death animation active"""
        if DeathSystem.death_rig and DeathSystem.death_animation_active:
            try:
                anim_name = "Player.Death"
                DeathSystem.death_rig.playAction(
                    anim_name,
                    30, 30,
                    layer=1,
                    priority=0,
                    blendin=0,
                    play_mode=logic.KX_ACTION_MODE_PLAY,
                    speed=0.0,
                )
                return True
            except Exception as e:
                try:
                    DeathSystem.death_rig.playAction(
                        anim_name,
                        29, 30,
                        layer=1,
                        priority=0,
                        blendin=0,
                        play_mode=logic.KX_ACTION_MODE_LOOP,
                        speed=0.1,
                    )
                    return True
                except:
                    DeathSystem.log(f"Error maintaining animation: {str(e)}")
                    return False
        return False
    
    @staticmethod
    def play_death_sound():
        DeathSystem.log("Playing death sound...")
        try:
            # 1. FX sound
            bge.logic.sendMessage("sound_fx.play", "sound_fx.play|death.ogg")
            
            # 2. Change background music
            set_background_context("death")
            
            DeathSystem.log("Sounds configured")
            return True
        except Exception as e:
            DeathSystem.log(f"Error: {e}")
            return False

    @staticmethod
    def play_restart_sound():
        DeathSystem.log("Playing restart sound...")
        try:
            # 1. FX sound
            bge.logic.sendMessage("sound_fx.play", "sound_fx.play|restart.ogg")
            
            # 2. Return to normal music
            set_background_context("exploration")
            
            DeathSystem.log("Sounds configured")
            return True
        except Exception as e:
            DeathSystem.log(f"Error: {e}")
            return False
    
    @staticmethod
    def trigger_matrix_effect_death():
        """Activates Matrix effect for death - Simplified version"""
        DeathSystem.log("Activating Matrix effect for death...")
        
        try:
            scene = logic.getCurrentScene()
            owner = logic.getCurrentController().owner
            
            # Find Matrix.Effect.Tracked object
            matrix_obj = scene.objects.get("Matrix.Effect.Tracked")
            
            if matrix_obj and owner:
                # Position at player location
                pos = owner.worldPosition.copy()
                pos.z -= 0.8
                matrix_obj.worldPosition = pos
                
                # Send message to object to activate its internal animation
                matrix_obj.sendMessage('effect_disappear')
                
                DeathSystem.log("Death Matrix effect activated")
                return True
            else:
                DeathSystem.log("Matrix.Effect.Tracked or owner not found")
                return False
                
        except Exception as e:
            DeathSystem.log(f"Error activating death Matrix effect: {str(e)}")
            return False
    
    @staticmethod
    def trigger_restart_matrix_effect():
        """Activates appearance effect for restart"""
        DeathSystem.log("Activating appearance effect for restart...")
        
        try:
            # Get current player position (already restored)
            scene = logic.getCurrentScene()
            player_obj = scene.objects.get("Player")
            
            if not player_obj:
                DeathSystem.log("Player not found")
                return False
            
            # Find Matrix.Effect.Tracked object
            matrix_obj = scene.objects.get("Matrix.Effect.Tracked")
            
            if matrix_obj:
                # Position effect at player location
                player_pos = player_obj.worldPosition.copy()
                player_pos.z -= 0.8  # Adjust player height
                matrix_obj.worldPosition = player_pos
                
                # Send direct message to object to activate its internal animation
                matrix_obj.sendMessage('effect_disappear')
                
                DeathSystem.log(f"Appearance effect activated at position {player_pos}")
                return True
            else:
                DeathSystem.log("Matrix.Effect.Tracked object not found")
                return False
                
        except Exception as e:
            DeathSystem.log(f"Error in trigger_restart_matrix_effect: {e}")
            return False
    
    @staticmethod
    def show_death_ui_once():
        """Shows death UI"""
        DeathSystem.log("Showing death UI...")
        
        try:
            scene = logic.getCurrentScene()
            button = scene.objects.get("Button.Restart")
            target = scene.objects.get("Empty.Button.Restart")
            
            if button and target:
                button.worldPosition = target.worldPosition.copy()
                button.worldOrientation = target.worldOrientation.copy()
                button.visible = True
                button["clickable"] = True
                
                DeathSystem.log("Death UI shown")
                return True
                
        except Exception as e:
            DeathSystem.log(f"Error: {str(e)}")
        
        return False
    
    @staticmethod
    def check_restart_button():
        """Checks if restart button was pressed"""
        try:
            scene = logic.getCurrentScene()
            button = scene.objects.get("Button.Restart")
            
            if button and button.get("clicked", False):
                DeathSystem.log("Restart button pressed")
                return True
        except Exception as e:
            # Only log error if it's not the sensor error
            if "'SCA_AlwaysSensor' object has no attribute 'type'" not in str(e):
                DeathSystem.log(f"Error checking button: {str(e)}")
        
        return False
    
    @staticmethod
    def complete_restart():
        """Completes restart (health, animation, etc.)"""
        DeathSystem.log("Completing restart...")
        
        try:
            # 1. Restore health
            try:
                from game_access import get_player
                player = get_player()
                if player and hasattr(player, 'health'):
                    player.health = 100
                    DeathSystem.log("Health restored to 100")
            except Exception as e:
                DeathSystem.log(f"Error restoring health: {e}")
            
            # 2. Play Death animation in REVERSE and then Idle (IN PARALLEL)
            try:
                scene = logic.getCurrentScene()
                rig = scene.objects.get("charA_metarig.001")
                if not rig:
                    for obj in scene.objects:
                        if "charA_metarig" in obj.name:
                            rig = obj
                            break
                
                if rig:
                    # Layer 1: Death animation in REVERSE (plays once)
                    rig.playAction(
                        "Player.Death",
                        30,      # start_frame (last)
                        1,       # end_frame (first) - REVERSE
                        layer=1,
                        priority=0,
                        blendin=5,
                        play_mode=logic.KX_ACTION_MODE_PLAY,  # PLAY once
                        speed=-1.0,     # Negative for reverse
                    )
                    
                    # Layer 0: Idle animation (in loop, starts immediately)
                    rig.playAction(
                        "Player.Idle",
                        1,      # start_frame
                        13,     # end_frame
                        layer=0,
                        priority=1,     # Higher priority than Death
                        blendin=15,     # Long blend for smooth transition
                        play_mode=logic.KX_ACTION_MODE_LOOP,
                        speed=1.0,
                    )
                    
                    DeathSystem.log("Death reverse + Idle animations started")
                    
            except Exception as e:
                DeathSystem.log(f"Error restoring animation: {e}")
            
            # 3. Reset UI
            try:
                scene = logic.getCurrentScene()
                button = scene.objects.get("Button.Restart")
                if button:
                    button.visible = False
                    button["clickable"] = False
                    button["clicked"] = False
            except:
                pass
            
            # 4. Reset death system
            DeathSystem.reset_all()
            
            DeathSystem.log("Restart completed successfully")
            return True
            
        except Exception as e:
            DeathSystem.log(f"Error completing restart: {e}")
            DeathSystem.reset_all()
            return False
    
    @staticmethod
    def reset_all():
        """Resets the entire system to its initial state"""
        DeathSystem.current_state = DEATH_STATE_NONE
        DeathSystem.state_start_time = 0
        DeathSystem.death_detected = False
        DeathSystem.restart_initiated = False
        
        # Reset execution flags
        DeathSystem.death_anim_started = False
        DeathSystem.matrix_effect_played = False
        DeathSystem.matrix_hidden = False
        DeathSystem.ui_shown = False
        DeathSystem.death_animation_active = False
        DeathSystem.death_sound_played = False
        DeathSystem.restart_sound_played = False
        DeathSystem.restart_matrix_played = False
        DeathSystem.player_position_restored = False
        
        # Clear rig reference and position
        DeathSystem.death_rig = None
        DeathSystem.restart_position = None
        
        DeathSystem.log("Death system reset")

# =============================================================================
# MAIN FUNCTION FOR PLAYER
# =============================================================================
def main():
    """Main function for Player object"""
    controller = logic.getCurrentController()
    owner = controller.owner
    
    # Only execute if we are the Player
    if owner.name == "Player":
        DeathSystem.execute(owner)

# Execute
main()