"""
sound_fx.py

Centralized sound effects system for UPBGE

This module provides a centralized system for managing sound effects playback,
including caching, volume control, looping, and pitch adjustment. It supports
message-based triggering and direct API calls.

Main Features:
    1. Centralized sound effect playback with caching
    2. Support for .ogg, .wav, and .mp3 formats
    3. Volume control, looping, and pitch adjustment
    4. Message-based command system for external control
    5. Sound preloading and cache management
    6. Forwarding of background music messages
    7. Debug mode for troubleshooting

Setup:
    Owner: 'Sound.FX.Controller'
    Logic Bricks: Always (True) connected to a Module/Python controller 'sound_fx.handle_message'
    Message (Tap) Sensor connected to a Module/Python controller 'sound_fx.handle_background_messages'
    Send messages with format: "sound_fx.play|filename.ogg|volume=0.7|loop=1|pitch=1.0"

Configurable Variables:
    SOUNDS_PATH (str): Path to sound files directory (default: '//Assets/Sounds/')
    DEFAULT_VOLUME (float): Default playback volume (default: 0.7)
    MAX_CACHE_SIZE (int): Maximum number of sounds in cache (default: 20)
    DEBUG (bool): Enable debug messages (default: False)

Notes:
    - Requires aud module for audio playback
    - Message system only processes messages starting with 'sound_fx.'
    - Background music messages are forwarded to sound_background module
    - Cache uses FIFO (First In First Out) when limit is exceeded

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
__description__ = "Centralized sound effects system with caching and message support"

# =============================================================================
# IMPORTS AND CONFIGURATION
# =============================================================================
import bge
from bge import logic
import aud
import os

SOUNDS_PATH = "//Assets/Sounds/"
DEFAULT_VOLUME = 0.7
MAX_CACHE_SIZE = 20  # Maximum number of sounds in cache
DEBUG = False  # True = show messages, False = silent

# =============================================================================
# SOUND FX MANAGER CLASS
# =============================================================================
class SoundFXManager:
    def __init__(self):
        self.device = None
        self.cache = {}
        self.initialized = False
        self.supported_formats = ['.ogg', '.wav', '.mp3']
        
    def _log(self, message, level="INFO"):
        """Show messages only if DEBUG is enabled"""
        if DEBUG:
            if level == "INFO":
                print(f"[SoundFX] {message}")
            elif level == "ERROR":
                print(f"[SoundFX] ERROR: {message}")
            elif level == "SUCCESS":
                print(f"[SoundFX] SUCCESS: {message}")
            elif level == "WARNING":
                print(f"[SoundFX] WARNING: {message}")
    
    def initialize(self):
        """Initialize sound system once"""
        if self.initialized:
            return True
            
        try:
            self.device = aud.Device()
            self.initialized = True
            self._log("Audio device created", "SUCCESS")
            return True
        except Exception as e:
            self._log(f"Error creating device: {e}", "ERROR")
            return False
    
    def _find_sound_file(self, sound_name):
        """Find sound file in different formats"""
        # If it already has extension, search as is
        if any(sound_name.lower().endswith(fmt) for fmt in self.supported_formats):
            path = logic.expandPath(f"{SOUNDS_PATH}{sound_name}")
            if os.path.exists(path):
                return path
        
        # Try different extensions
        for fmt in self.supported_formats:
            path = logic.expandPath(f"{SOUNDS_PATH}{sound_name}{fmt}")
            if os.path.exists(path):
                return path
        
        return None
    
    def load_sound(self, sound_name):
        """Load sound into cache"""
        if sound_name in self.cache:
            return self.cache[sound_name]
        
        # Find file
        file_path = self._find_sound_file(sound_name)
        if not file_path:
            self._log(f"File not found: {sound_name}", "ERROR")
            return None
        
        try:
            sound = aud.Sound.file(file_path)
            self.cache[sound_name] = sound
            
            # Clean cache if too large
            if len(self.cache) > MAX_CACHE_SIZE:
                # Remove first element (FIFO)
                first_key = next(iter(self.cache))
                del self.cache[first_key]
            
            self._log(f"Sound loaded: {sound_name}", "SUCCESS")
            return sound
        except Exception as e:
            self._log(f"Error loading {sound_name}: {e}", "ERROR")
            return None
    
    def play_sound(self, sound_name, volume=None, loop=False, pitch=1.0):
        """Play a sound effect"""
        if not self.initialized:
            if not self.initialize():
                return None
        
        sound = self.load_sound(sound_name)
        if not sound:
            return None
        
        try:
            handle = self.device.play(sound)
            if handle:
                # Configure parameters
                vol = volume if volume is not None else DEFAULT_VOLUME
                handle.volume = vol
                
                if loop:
                    handle.loop_count = -1  # Infinite loop
                else:
                    handle.loop_count = 0  # No loop
                
                # Attempt to adjust pitch if supported
                try:
                    handle.pitch = pitch
                except:
                    pass
                
                self._log(f"Playing {sound_name} (vol={vol})")
                return handle
        except Exception as e:
            self._log(f"Error playing {sound_name}: {e}", "ERROR")
        
        return None

# =============================================================================
# GLOBAL INSTANCE
# =============================================================================
_manager = None

def get_manager():
    """Get global sound manager instance"""
    global _manager
    if _manager is None:
        _manager = SoundFXManager()
    return _manager

# =============================================================================
# MESSAGE HANDLER (IMPROVED)
# =============================================================================
def handle_message(cont):
    """Process sound effect messages - ONLY messages starting with 'sound_fx.'"""
    msg_sensor = cont.sensors.get("Message")
    if not msg_sensor or not msg_sensor.positive:
        return
    
    manager = get_manager()
    
    for body in msg_sensor.bodies:
        # Only show in console messages intended for sound_fx
        if not body.startswith("sound_fx."):
            # Silently ignore unrelated messages
            continue
            
        # Only show if DEBUG is enabled
        if DEBUG:
            print(f"[SoundFX] Message received: {body}")
        
        # ONLY process messages starting with "sound_fx.play|"
        if body.startswith("sound_fx.play|"):
            # Format: "sound_fx.play|pick_up.ogg|volume=0.7|loop=0"
            parts = body.split("|")
            if len(parts) < 2:
                if DEBUG:
                    print(f"[SoundFX] Invalid format: {body}")
                continue
                
            sound_name = parts[1]
            volume = DEFAULT_VOLUME
            loop = False
            pitch = 1.0
            
            for part in parts[2:]:
                if "=" in part:
                    key, value = part.split("=", 1)
                    key = key.strip().lower()
                    
                    if key == "volume":
                        try:
                            volume = float(value)
                        except:
                            pass
                    elif key == "loop":
                        loop = value.lower() in ("1", "true", "yes", "on")
                    elif key == "pitch":
                        try:
                            pitch = float(value)
                        except:
                            pass
            
            manager.play_sound(sound_name, volume, loop, pitch)
            continue  # IMPORTANT! Continue to next message

def update(cont):
    """Periodic update (initialization)"""
    manager = get_manager()
    if not manager.initialized:
        manager.initialize()

# =============================================================================
# UTILITY FUNCTIONS FOR OTHER SCRIPTS
# =============================================================================
def play_sound_immediate(sound_name, volume=None, loop=False):
    """Play a sound immediately (without messages)"""
    manager = get_manager()
    return manager.play_sound(sound_name, volume, loop)

def preload_sound(sound_name):
    """Preload a sound into cache"""
    manager = get_manager()
    return manager.load_sound(sound_name) is not None

def clear_cache():
    """Clear sound cache"""
    manager = get_manager()
    manager.cache.clear()
    if DEBUG:
        print("[SoundFX] Cache cleared")
        
# =============================================================================
# BACKGROUND MUSIC MESSAGE FORWARDING
# =============================================================================
def handle_background_messages(cont):
    """Forward messages to background music system"""
    msg_sensor = cont.sensors.get("Message")
    if not msg_sensor or not msg_sensor.positive:
        return
    
    for body in msg_sensor.bodies:
        if isinstance(body, str) and body.startswith("sound_background."):
            try:
                from sound_background import get_manager
                manager = get_manager()
                if manager:
                    manager.add_message(body)
            except:
                pass