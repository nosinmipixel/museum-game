"""
sound_background.py

Background music system with state stack

This module manages background music playback with a context stack system,
allowing temporary music changes (e.g., for quizzes, combat) that can be
reverted to previous contexts. Supports multiple music tracks per context,
fade effects, and zone-based music switching.

Main Features:
    1. Context-based music management with push/pop stack system
    2. Supports multiple music tracks per context with cycling
    3. Fade in/out effects for smooth transitions
    4. Zone-based music switching using proximity triggers
    5. Integration with game state for sound muting
    6. Message-based command system for external control
    7. Debug mode for troubleshooting

Setup:
    Logic Bricks: Connect an Always sensor (True Level) to a Python Module 
    controller: sound_background.main. Owner: 'Game.Controller'.
    Should be called every frame for continuous audio management

Configurable Variables:
    _DEBUG_MODE (bool): Global debug flag (default: False)
    max_stack_size (int): Maximum context stack depth (default: 10)
    switch_check_distance (float): Distance for zone-based music (default: 5.0)
    fade_speed (float): Speed of volume fade transitions (default: 2.0)
    target_volume (float): Target volume level (default: 0.1)

Notes:
    - Requires aud module for audio playback
    - Music files must be .ogg format in '//Assets/Sounds/' folder
    - Filenames must start with 'background_' followed by context name
    - Examples: background_exploration_01.ogg, background_quiz_01.ogg
    - Integrates with game_access for mute state from game settings

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
__description__ = "Background music system with context stack and fade effects"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic
import aud
import os
import game_access

# =============================================================================
# GLOBAL DEBUG SYSTEM
# =============================================================================

_DEBUG_MODE = False  # Global variable for controlling debug messages

def set_debug_mode(enabled):
    """Enable or disable debug messages globally"""
    global _DEBUG_MODE
    _DEBUG_MODE = enabled

def debug_print(*args, **kwargs):
    """Print messages only if debug mode is enabled"""
    if _DEBUG_MODE:
        print(*args, **kwargs)

# =============================================================================
# MAIN SOUND BACKGROUND MANAGER CLASS
# =============================================================================

class SoundBackgroundManager:
    def __init__(self):
        self.device = None
        self.sound_handles = {}
        self.current_context = "exploration"
        self.default_context = "exploration"
        self.track_index = 0
        self.initialized = False
        self.game = None
        
        # Stack system for states
        self.context_stack = []  # List of previous contexts
        self.max_stack_size = 10
        
        # Message system
        self.message_buffer = []
        
        # Switch system
        self.active_switches = {}  # {context: owner_object}
        self.switch_check_distance = 5.0
        self.player_position = None
        
        # Audio system
        self.current_handle = None
        self.target_volume = 0.1
        self.current_volume = 0.0
        self.fade_speed = 2.0
        
        # Tracking
        self.last_update_time = 0
        self.last_switch_check = 0
        
        debug_print("[SoundBG] Stack system initialized")
    
    def init(self):
        """Initialize the audio system"""
        if self.initialized:
            return True
        
        debug_print("[SoundBG] Initializing...")
        
        try:
            # Create audio device
            self.device = aud.Device()
            
            # Load sounds
            self.load_sounds()
            
            # Start with default context
            self.push_context(self.default_context, source="init")
            
            self.initialized = True
            debug_print(f"[SoundBG] Initialization complete")
            return True
            
        except Exception as e:
            debug_print(f"[SoundBG] ERROR during initialization: {e}")
            return False
    
    def load_sounds(self):
        """Load all background sounds"""
        sounds_path = logic.expandPath("//Assets/Sounds/")
        
        # Possible contexts
        self.sound_handles = {
            "exploration": [],
            "calm": [],
            "death": [],
            "fight": [],
            "library": [],
            "quiz": [],
            "start": [],
            "endgame": [],            
            "storage": []
        }
        
        if not os.path.exists(sounds_path):
            debug_print(f"[SoundBG] ERROR: Folder not found: {sounds_path}")
            return
        
        debug_print("[SoundBG] Loading background sounds...")
        
        for filename in os.listdir(sounds_path):
            if not filename.lower().endswith('.ogg'):
                continue
            
            filename_lower = filename.lower()
            
            # Only files starting with 'background_'
            if filename_lower.startswith('background_'):
                # Extract context
                name_parts = filename_lower.replace('.ogg', '').split('_')
                
                if len(name_parts) >= 2:
                    context = name_parts[1]
                    
                    if context in self.sound_handles:
                        full_path = os.path.join(sounds_path, filename)
                        
                        try:
                            sound = aud.Sound.file(full_path)
                            self.sound_handles[context].append({
                                'name': filename,
                                'sound': sound,
                                'path': full_path
                            })
                        except:
                            pass
        
        # Verify we have sounds
        for context in self.sound_handles:
            if self.sound_handles[context]:
                debug_print(f"[SoundBG] {context}: {len(self.sound_handles[context])} tracks")
        
    def should_play(self):
        """Determine if music should play"""
        # Get game instance if not already
        if not self.game:
            try:
                self.game = game_access.get_game()
            except Exception as e:
                debug_print(f"[SoundBG] Error getting GameManager: {e}")
                return True  # Fallback: play music
        
        if not self.game or not hasattr(self.game, 'state'):
            return True  # Fallback: play music
        
        try:
            # Access properties correctly
            state = self.game.state
            
            # Get values with defaults
            sound_main_enabled = getattr(state, 'sound_main', True)
            sound_background_enabled = getattr(state, 'sound_background', True)
            
            # Play only if both are enabled
            return bool(sound_main_enabled and sound_background_enabled)
            
        except Exception as e:
            debug_print(f"[SoundBG] Error checking sound state: {e}")
            return True  # Fallback: play music
    
    def push_context(self, context, source="unknown"):
        """Push a new context to the stack and play it"""
        
        # Check if we have music for this context
        if context not in self.sound_handles or not self.sound_handles[context]:
            debug_print(f"[SoundBG] No music for context: {context}")
            return False
        
        # If already in this context, do nothing
        if self.context_stack and self.context_stack[-1] == context:
            return True
        
        debug_print(f"[SoundBG] Pushing context: {context} (source: {source})")
        debug_print(f"[SoundBG]   Stack before: {self.context_stack}")
        
        # Save current context to stack (if not empty)
        if self.context_stack:
            self.context_stack.append(context)
        else:
            self.context_stack = [context]
        
        # Limit stack size
        if len(self.context_stack) > self.max_stack_size:
            self.context_stack = self.context_stack[-self.max_stack_size:]
        
        # Play new context
        self._play_context(context)
        
        debug_print(f"[SoundBG]   Stack after: {self.context_stack}")
        return True
    
    def pop_context(self):
        """Pop current context from stack and return to previous"""
        if len(self.context_stack) <= 1:
            debug_print(f"[SoundBG] Cannot pop, stack has only 1 item")
            return False
        
        debug_print(f"[SoundBG] Popping context: {self.context_stack[-1]}")
        debug_print(f"[SoundBG]   Stack before: {self.context_stack}")
        
        # Remove current context
        self.context_stack.pop()
        
        # Get previous context
        previous_context = self.context_stack[-1]
        
        # Play previous context
        self._play_context(previous_context)
        
        debug_print(f"[SoundBG]   Stack after: {self.context_stack}")
        return True
    
    def set_context(self, context, temporary=False):
        """
        Set a context
        
        Args:
            context: Context to set
            temporary: If True, save previous state to allow returning
        """
        if temporary:
            # For temporary context, use push
            return self.push_context(context, source="temporary")
        else:
            # For permanent context, replace entire stack
            self.context_stack = [context]
            return self._play_context(context)
    
    def _play_context(self, context):
        """Play music for specified context (internal)"""
        
        if context not in self.sound_handles or not self.sound_handles[context]:
            debug_print(f"[SoundBG] ERROR: No music for context: {context}")
            return False
        
        # Stop current music if playing
        if self.current_handle:
            try:
                self.current_handle.stop()
            except:
                pass
        
        # Select track
        tracks = self.sound_handles[context]
        if self.track_index >= len(tracks):
            self.track_index = 0
        
        track = tracks[self.track_index]
        
        try:
            # Play new track
            self.current_handle = self.device.play(track['sound'])
            if self.current_handle:
                # Set volume
                self.current_handle.volume = 0.0
                self.current_volume = 0.0
                self.target_volume = 0.1
                
                # Update current context
                self.current_context = context
                
                # Next track for next time
                self.track_index = (self.track_index + 1) % len(tracks)
                
                debug_print(f"[SoundBG] Now playing: {context} ({track['name']})")
                return True
                
        except Exception as e:
            debug_print(f"[SoundBG] ERROR playing: {e}")
        
        return False
    
    def stop_music(self):
        """Stop current music"""
        if self.current_handle:
            try:
                self.current_handle.stop()
            except:
                pass
            self.current_handle = None
    
    def fade_out(self):
        """Start fade out"""
        self.target_volume = 0.0
    
    def fade_in(self):
        """Start fade in"""
        self.target_volume = 0.1
    
    def update_fade(self, dt):
        """Update fade effect"""
        if not self.current_handle:
            return
        
        change = self.fade_speed * dt
        
        if self.current_volume < self.target_volume:
            self.current_volume = min(self.target_volume, self.current_volume + change)
        else:
            self.current_volume = max(self.target_volume, self.current_volume - change)
        
        try:
            self.current_handle.volume = self.current_volume
        except:
            pass
        
        # If volume reaches 0, stop
        if self.target_volume == 0 and self.current_volume < 0.01:
            self.stop_music()
    
    def add_message(self, message):
        """Add a message to the buffer"""
        if isinstance(message, str):
            self.message_buffer.append(message)
            return True
        return False
    
    def process_messages(self):
        """Process all messages in the buffer"""
        while self.message_buffer:
            message = self.message_buffer.pop(0)
            
            if not isinstance(message, str):
                continue
            
            debug_print(f"[SoundBG] Message: {message}")
            
            if message.startswith("sound_background.set_context|"):
                # Format: sound_background.set_context|quiz|temporary
                parts = message.split("|")
                if len(parts) >= 2:
                    context = parts[1]
                    temporary = len(parts) >= 3 and parts[2].lower() == "temporary"
                    self.set_context(context, temporary=temporary)
            
            elif message.startswith("sound_background.push_context|"):
                parts = message.split("|")
                if len(parts) >= 2:
                    context = parts[1]
                    self.push_context(context, source="message")
            
            elif message == "sound_background.pop_context":
                self.pop_context()
            
            elif message == "sound_background.stop":
                self.stop_music()
            
            elif message == "sound_background.fade_out":
                self.fade_out()
            
            elif message == "sound_background.fade_in":
                self.fade_in()
            
            elif message == "sound_background.reset_stack":
                self.context_stack = [self.default_context]
                self._play_context(self.default_context)
    
    def add_switch(self, context, owner):
        """Add an active zone switch"""
        if context in self.sound_handles:
            self.active_switches[context] = owner
            debug_print(f"[SoundBG] Switch activated: {owner.name} -> {context}")
            
            # Switches are temporary (can return to previous state)
            self.push_context(context, source="switch")
    
    def remove_switch(self, context):
        """Remove a zone switch"""
        if context in self.active_switches:
            del self.active_switches[context]
            debug_print(f"[SoundBG] Switch deactivated: {context}")
            
            # If this switch was the current context, return to previous
            if self.context_stack and self.context_stack[-1] == context:
                self.pop_context()
    
    def update_switches(self):
        """Update zone switch state"""
        if not self.player_position:
            return
        
        current_time = logic.getRealTime()
        
        if current_time - self.last_switch_check < 0.5:
            return
        
        self.last_switch_check = current_time
        
        # Check each active switch
        switches_to_remove = []
        
        for context, owner in list(self.active_switches.items()):
            if not owner:
                switches_to_remove.append(context)
                continue
            
            try:
                if hasattr(owner, 'worldPosition'):
                    distance = (self.player_position - owner.worldPosition).length
                    
                    if distance > self.switch_check_distance:
                        switches_to_remove.append(context)
                else:
                    switches_to_remove.append(context)
            except:
                switches_to_remove.append(context)
        
        # Remove switches
        for context in switches_to_remove:
            self.remove_switch(context)
    
    def update_player_position(self, position):
        """Update player position"""
        self.player_position = position
    
    def update(self):
        """Main update loop"""
        
        if not self.initialized:
            if not self.init():
                return
        
        # Check if music should play
        if not self.should_play():
            if self.current_handle:
                self.stop_music()
            return
        
        # If should play but no music is playing, start it
        if self.should_play() and not self.current_handle and self.context_stack:
            self._play_context(self.context_stack[-1])
        
        # Calculate delta time
        current_time = logic.getFrameTime()
        dt = current_time - self.last_update_time
        if dt <= 0 or dt > 0.5:
            dt = 0.016
        self.last_update_time = current_time
        
        # Process messages
        self.process_messages()
        
        # Update switches
        self.update_switches()
        
        # Update fade
        self.update_fade(dt)
        
        # Check if music ended
        if self.current_handle:
            try:
                if hasattr(self.current_handle, 'status'):
                    if not self.current_handle.status:
                        # Play next track from same context
                        self._play_context(self.current_context)
            except:
                pass

# =============================================================================
# GLOBAL INSTANCE
# =============================================================================

_sound_bg_manager = None

def get_manager():
    global _sound_bg_manager
    if _sound_bg_manager is None:
        _sound_bg_manager = SoundBackgroundManager()
    return _sound_bg_manager

def main():
    manager = get_manager()
    manager.update()

# =============================================================================
# PUBLIC FUNCTIONS
# =============================================================================

def set_debug(enabled):
    """Enable or disable debug messages globally"""
    set_debug_mode(enabled)

def push_background_context(context):
    """Push a new temporary context to the stack"""
    try:
        manager = get_manager()
        if manager:
            return manager.add_message(f"sound_background.push_context|{context}")
    except:
        pass
    return False

def pop_background_context():
    """Return to previous context"""
    try:
        manager = get_manager()
        if manager:
            return manager.add_message("sound_background.pop_context")
    except:
        pass
    return False

def set_background_context(context, temporary=False):
    """Set a context (temporary or permanent)"""
    try:
        manager = get_manager()
        if manager:
            temp_flag = "temporary" if temporary else ""
            return manager.add_message(f"sound_background.set_context|{context}|{temp_flag}")
    except:
        pass
    return False

def get_current_context():
    """Get current context"""
    try:
        manager = get_manager()
        if manager:
            return manager.current_context
    except:
        pass
    return ""

# Legacy functions (for compatibility)
def add_switch_context(context, owner):
    try:
        manager = get_manager()
        if manager:
            manager.add_switch(context, owner)
            return True
    except:
        pass
    return False

def update_player_position(position):
    try:
        manager = get_manager()
        if manager:
            manager.update_player_position(position)
            return True
    except:
        pass
    return False