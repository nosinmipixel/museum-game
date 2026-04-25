"""
game_data.py

Single source of truth for game data with stamina and cat pet system.

This script contains all core data classes for the game: PlayerStats, GameState,
HUDText, and the GameManager singleton. It manages player attributes, game
progression, inventory, tasks, and climate systems.

Main Features:
    1. PlayerStats management (health, stamina, skills)
    2. GameState tracking (budget, tasks, inventory, climate)
    3. HUD text container for display data
    4. Singleton GameManager for global access
    5. Inventory collection statistics by historical period
    6. Task completion tracking (storage, restoration, exhibition, quiz)
    7. Climate warning system with trend detection
    8. Cat pet system with food items and timer
    9. Save/load support via dictionary serialization

Setup:
    Access via GameManager.get() singleton pattern
    Import game_access module for simplified access functions

Configurable Variables:
    None (all values are initialized in class constructors)

Notes:
    - GameManager is stored in logic.game_manager for persistence
    - Inventory uses periods: pal, neo, bronze, iberian, roman
    - Tasks: quiz (7/10 correct), restoration (3/5), storage (10 items), 
      conservation (climate ok), exhibition (5 items)
    - Cat pet system: feeding cat makes it follow player for 3 minutes
    - Climate warning level: 0=ok, 1=decreasing, 2=increasing out of range
    - Audio settings distinguish between editor (False) and production (True)

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
__description__ = "Single source of truth for game data with stamina and cat pet system"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic

# =============================================================================
# PLAYER STATS CLASS
# =============================================================================
class PlayerStats:
    def __init__(self):
        self.health = 100
        self.max_health = 100
        self.is_alive = True
        self.skills = 1
        self.stamina = 100
        self.max_stamina = 100
        # Stamina properties
        self.stamina_drain_rate = 1.0       # 1% per minute (base)
        self.stamina_drain_doors = 50.0     # 50% per minute (doors open)
    
    def take_damage(self, amount):
        self.health -= amount
        if self.health <= 0:
            self.is_alive = False
    
    def to_dict(self):
        """Converts player data to dictionary"""
        return {
            'health': self.health,
            'max_health': self.max_health,
            'is_alive': self.is_alive,
            'skills': self.skills,
            'stamina': self.stamina,
            'max_stamina': self.max_stamina,
            'stamina_drain_rate': self.stamina_drain_rate,
            'stamina_drain_doors': self.stamina_drain_doors
        }
    
    def from_dict(self, data):
        """Loads player data from dictionary"""
        if not data:
            return
        for key, value in data.items():
            if hasattr(self, key):
                setattr(self, key, value)


# =============================================================================
# GAME STATE CLASS
# =============================================================================
class GameState:
    def __init__(self):
        # Basic game properties
        self.is_paused = False
        self.score = 0
        self.budget = 100000
        self.language = 'es'
        self.current_level = 1
        
        # Game states
        self.doors_opened = 0
        self.temp_ok = True
        self.hr_ok = True
        self.temp_raw = 21.0
        self.hr_raw = 50.0
        self.frame_counter = 0
        self.dialog_turn = 0
        
        # Climate trend properties
        self.temp_previous = 21.0      # Previous temperature value
        self.hr_previous = 50.0        # Previous humidity value
        self.temp_trending_up = False  # True if temperature is rising
        self.hr_trending_up = False    # True if humidity is rising
        self.climate_warning_level = 0 # 0=ok, 1=decreasing, 2=increasing
        
        # Dialog system
        self.dialog_active = False
        self.current_npc_id = 0
        
        # Task system
        self.npc_turn = 1
        self.task_quiz = False
        self.quiz_active = True
        self.task_restoration = False
        self.task_conservation = False
        self.task_exhibition = False
        self.task_storage = False
        self.task_quiz_total = 0
        self.task_restoration_total = 0
        self.task_total = 0
        
        # Timers
        self.timer_quiz = 0.0
        self.timer_npc11 = 0.0
        
        # Properties for NPC11 / Restoration
        self.restoration_active = False
        self.restoration_item_type = ""
        self.restoration_item_id = 0
        self.restoration_attempt = 0
        
        # Game completion properties
        self.game_completed = False
        self.game_completion_time = 0.0
        self.matrix_effect_active = False
        
        # Collection system
        self.collection_items_total = 0
        self.total_pal = 0
        self.total_neo = 0
        self.total_bronze = 0
        self.total_iberian = 0
        self.total_roman = 0
        self.inventoried_items = 0
        self.restored_items = 0
        self.exhibited_items = 0
        self.general_items_total = 0
        
        # Audio
        self.sound_background = True  #   NOTE: 'True' for Production; 'False' for Testing
        self.sound_main = True
        self.sound_volume = 1.0
        self.sound_context = "exploration"
        
        # Other
        self.spray_total = 100
        self.spray_cans = 0
        self.hud_pause_open = False
        self.scene_id = 1
        
        # Bugs eliminated counter
        self.bugs_total = 0
        
        # Inventory
        self.inventory = {
            "collection_items": {
                "pal": [], "neo": [], "bronze": [], 
                "iberian": [], "roman": []
            },
            "general_items_total": 0,
            "boxes": {},
            "exhibitions": {}
        }
        
        # Cat pet system properties
        self.cat_food_items = 0                    # Number of cans in inventory
        self.cat_pet_active = False                # Is cat temporarily a pet?
        self.cat_pet_timer = 0.0                  # Remaining time as pet (seconds)
        self.cat_pet_duration = 180.0              # Total duration (3 minutes = 180s)
        self.cat_original_position = None          # Original cat position (Empty.Cat.1)
        self.cat_food_hud_visible = False          # Control cat food HUD visibility
        self.cat_food_spawn_points = 3             # Number of configurable spawn points
        self.cat_food_just_picked = False          # True only on the frame food is picked
    
    def update_collection_stats(self):
        """Updates collection statistics from inventory"""
        inv = self.inventory["collection_items"]
        
        self.total_pal = len(inv.get("pal", []))
        self.total_neo = len(inv.get("neo", []))
        self.total_bronze = len(inv.get("bronze", []))
        self.total_iberian = len(inv.get("iberian", []))
        self.total_roman = len(inv.get("roman", []))
        
        self.collection_items_total = (
            self.total_pal + self.total_neo + self.total_bronze + 
            self.total_iberian + self.total_roman
        )
        
        inventoried = 0
        restored = 0
        exhibited = 0
        
        for period_items in inv.values():
            for item in period_items:
                if item.get("ubication", 0) > 0:
                    inventoried += 1
                if item.get("restored", 0) == 0:
                    restored += 1
                if item.get("exhibition", 0) > 0:
                    exhibited += 1
        
        self.inventoried_items = inventoried
        self.restored_items = restored
        self.exhibited_items = exhibited
        
        return inventoried, restored, exhibited
    
    def to_dict(self):
        """Converts state to dictionary for saving"""
        return {
            'is_paused': self.is_paused,
            'score': self.score,
            'budget': self.budget,
            'language': self.language,
            'current_level': self.current_level,
            'doors_opened': self.doors_opened,
            'temp_ok': self.temp_ok,
            'hr_ok': self.hr_ok,
            'temp_raw': self.temp_raw,
            'hr_raw': self.hr_raw,
            'frame_counter': self.frame_counter,
            # Climate trend properties
            'temp_previous': self.temp_previous,
            'hr_previous': self.hr_previous,
            'temp_trending_up': self.temp_trending_up,
            'hr_trending_up': self.hr_trending_up,
            'climate_warning_level': self.climate_warning_level,
            'dialog_turn': self.dialog_turn,
            'dialog_active': self.dialog_active,
            'current_npc_id': self.current_npc_id,
            'npc_turn': self.npc_turn,
            'task_quiz': self.task_quiz,
            'task_restoration': self.task_restoration,
            'task_conservation': self.task_conservation,
            'task_exhibition': self.task_exhibition,
            'task_storage': self.task_storage,
            'task_quiz_total': self.task_quiz_total,
            'task_restoration_total': self.task_restoration_total,
            'task_total': self.task_total,
            'timer_quiz': self.timer_quiz,
            'timer_npc11': self.timer_npc11,
            'restoration_active': self.restoration_active,
            'restoration_item_type': self.restoration_item_type,
            'restoration_item_id': self.restoration_item_id,
            'restoration_attempt': self.restoration_attempt,
            'game_completed': self.game_completed,
            'game_completion_time': self.game_completion_time,
            'matrix_effect_active': self.matrix_effect_active,
            'collection_items_total': self.collection_items_total,
            'total_pal': self.total_pal,
            'total_neo': self.total_neo,
            'total_bronze': self.total_bronze,
            'total_iberian': self.total_iberian,
            'total_roman': self.total_roman,
            'inventoried_items': self.inventoried_items,
            'restored_items': self.restored_items,
            'exhibited_items': self.exhibited_items,
            'general_items_total': self.general_items_total,
            'sound_main': self.sound_main,
            'sound_background': self.sound_background,
            'sound_context': self.sound_context,
            'spray_total': self.spray_total,
            'spray_cans': self.spray_cans,
            'hud_pause_open': self.hud_pause_open,
            'scene_id': self.scene_id,
            'bugs_total': self.bugs_total,
            'inventory': self.inventory,
            # Cat pet system properties
            'cat_food_items': self.cat_food_items,
            'cat_pet_active': self.cat_pet_active,
            'cat_pet_timer': self.cat_pet_timer,
            'cat_pet_duration': self.cat_pet_duration,
            'cat_original_position': self.cat_original_position,
            'cat_food_hud_visible': self.cat_food_hud_visible,
            'cat_food_spawn_points': self.cat_food_spawn_points
        }
    
    def from_dict(self, data):
        """Loads state from dictionary"""
        if not data:
            return
        
        for key, value in data.items():
            if hasattr(self, key):
                try:
                    setattr(self, key, value)
                except:
                    pass
        
        # Load climate trend properties
        if 'temp_previous' in data:
            self.temp_previous = data['temp_previous']
        if 'hr_previous' in data:
            self.hr_previous = data['hr_previous']
        if 'temp_trending_up' in data:
            self.temp_trending_up = data['temp_trending_up']
        if 'hr_trending_up' in data:
            self.hr_trending_up = data['hr_trending_up']
        if 'climate_warning_level' in data:
            self.climate_warning_level = data['climate_warning_level']
        
        if 'inventory' in data:
            self.inventory = data['inventory']
        
        if 'bugs_total' in data:
            self.bugs_total = data['bugs_total']
        
        if 'timer_npc11' in data:
            self.timer_npc11 = data['timer_npc11']
        
        if 'restoration_active' in data:
            self.restoration_active = data['restoration_active']
        
        if 'restoration_item_type' in data:
            self.restoration_item_type = data['restoration_item_type']
        
        if 'restoration_item_id' in data:
            self.restoration_item_id = data['restoration_item_id']
        
        if 'restoration_attempt' in data:
            self.restoration_attempt = data['restoration_attempt']
        
        if 'game_completed' in data:
            self.game_completed = data['game_completed']
        
        if 'game_completion_time' in data:
            self.game_completion_time = data['game_completion_time']
        
        if 'matrix_effect_active' in data:
            self.matrix_effect_active = data['matrix_effect_active']
        
        # Load cat pet system properties
        if 'cat_food_items' in data:
            self.cat_food_items = data['cat_food_items']
        if 'cat_pet_active' in data:
            self.cat_pet_active = data['cat_pet_active']
        if 'cat_pet_timer' in data:
            self.cat_pet_timer = data['cat_pet_timer']
        if 'cat_pet_duration' in data:
            self.cat_pet_duration = data['cat_pet_duration']
        if 'cat_original_position' in data:
            self.cat_original_position = data['cat_original_position']
        if 'cat_food_hud_visible' in data:
            self.cat_food_hud_visible = data['cat_food_hud_visible']
        if 'cat_food_spawn_points' in data:
            self.cat_food_spawn_points = data['cat_food_spawn_points']
        
        self.update_collection_stats()


# =============================================================================
# HUD TEXT CLASS
# =============================================================================
class HUDText:
    def __init__(self):
        self.budget_text = ""
        self.skills_text = ""
        self.hr_mus = ""
        self.temp_mus = ""
        self.player_text = ""
        self.char1_text = ""
        self.info_text = ""
        self.center_text = ""
        self.tasks_text = ""
        self.quiz_text = ""
        self.info_text_v2 = ""
        self.item_desc_text = ""
        self.book_text = ""
        self.exhibition_text = ""
        self.restor_text = ""


# =============================================================================
# GAME MANAGER SINGLETON CLASS
# =============================================================================
class GameManager:
    """Singleton that manages all game instances"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GameManager, cls).__new__(cls)
            cls._instance.__init__()
        return cls._instance
    
    def __init__(self):
        self.player = PlayerStats()
        self.state = GameState()
        self.hud_text = HUDText()
    
    @staticmethod
    def get():
        """Get GameManager instance"""
        if not hasattr(logic, 'game_manager'):
            logic.game_manager = GameManager()
        return logic.game_manager
    
    def save_data(self):
        """Data for saving"""
        return {
            'version': '2.0',
            'timestamp': logic.getRealTime(),
            'player': self.player.to_dict(),
            'state': self.state.to_dict(),
            'inventory': self.state.inventory
        }
    
    def load_data(self, data):
        """Load data from file"""
        try:
            version = data.get('version', '1.0')
            print(f"Loading data version {version}")
            
            if 'player' in data:
                self.player.from_dict(data['player'])
            
            if 'state' in data:
                self.state.from_dict(data['state'])
            
            if 'inventory' in data:
                self.state.inventory = data['inventory']
            
            self.state.update_collection_stats()
            
            self.hud_text.budget_text = f"Budget: {self.state.budget}"
            self.hud_text.skills_text = f"Skills: {self.player.skills}"
            
            if self.state.game_completed:
                logic.matrix_effect_active = True
                print("Game was already completed - Reactivating effects")
            
            print("Data loaded successfully into GameManager")
            return True
            
        except Exception as e:
            print(f"Error loading data into GameManager: {e}")
            return False
    
    def update_hud(self):
        """Updates all HUD texts"""
        self.hud_text.budget_text = f"Budget: {self.state.budget}"
        self.hud_text.skills_text = f"Skills: {self.player.skills}"
        
        inventoried, restored, exhibited = self.state.update_collection_stats()
        
        return self.hud_text
    
    def get_property(self, prop_name):
        """Gets any property by name"""
        if hasattr(self.player, prop_name):
            return getattr(self.player, prop_name)
        
        if hasattr(self.state, prop_name):
            return getattr(self.state, prop_name)
        
        if hasattr(self.hud_text, prop_name):
            return getattr(self.hud_text, prop_name)
        
        return None
    
    def set_property(self, prop_name, value):
        """Sets any property by name"""
        if hasattr(self.player, prop_name):
            setattr(self.player, prop_name, value)
            return True
        
        if hasattr(self.state, prop_name):
            setattr(self.state, prop_name, value)
            return True
        
        if hasattr(self.hud_text, prop_name):
            setattr(self.hud_text, prop_name, value)
            return True
        
        return False
    
    def check_tasks(self):
        """Checks task status"""
        inventoried, restored, exhibited = self.state.update_collection_stats()
        
        self.state.task_quiz = (self.state.task_quiz_total >= 7)
        self.state.task_restoration = (self.state.task_restoration_total >= 3)
        self.state.task_storage = (self.state.collection_items_total >= 10 and 
                                  self.state.inventoried_items >= 10)
        self.state.task_conservation = (self.state.temp_ok and self.state.hr_ok)
        self.state.task_exhibition = (exhibited >= 5)

# Debug print. Only uncomment in production
#        print(f"Tasks - Storage: {self.state.task_storage}, "
#              f"Restoration: {self.state.task_restoration_total}/3, "
#              f"Exhibition: {exhibited}/5, Quiz: {self.state.task_quiz_total}/7")
        
        return (self.state.task_storage, self.state.task_restoration, 
                self.state.task_exhibition, self.state.task_conservation, 
                self.state.task_quiz)
    
    def sync_to_controller(self, controller):
        """Synchronizes data with Game Controller"""
        try:
            controller['task_storage'] = self.state.task_storage
            controller['task_restoration'] = self.state.task_restoration
            controller['task_exhibition'] = self.state.task_exhibition
            controller['task_conservation'] = self.state.task_conservation
            controller['task_quiz'] = self.state.task_quiz
            controller['task_restoration_total'] = self.state.task_restoration_total
            controller['task_quiz_total'] = self.state.task_quiz_total
            controller['timer_npc11'] = getattr(self.state, 'timer_npc11', 0.0)
            controller['restoration_active'] = getattr(self.state, 'restoration_active', False)
            controller['restoration_item_type'] = getattr(self.state, 'restoration_item_type', "")
            controller['restoration_item_id'] = getattr(self.state, 'restoration_item_id', 0)
            controller['restoration_attempt'] = getattr(self.state, 'restoration_attempt', 0)
            controller['game_completed'] = getattr(self.state, 'game_completed', False)
            return True
        except:
            return False