[![es](https://img.shields.io/badge/lang-es-yellow.svg)](CONTRIBUTING.es.md)
# 💻 Introduction
This game is developed using UPBGE (https://upbge.org)
Initial development was performed with UPBGE version 0.44. However, all development has been migrated to the older version UPBGE 0.36 to achieve better performance.
This game uses Python scripts and Logic Bricks. The Logic Nodes system is **NOT** used.

# 💻 File Structure
There are two main `.blend` files:
`Intro_Game.blend` contains the game's introductory scene. This is the file that must be used to build the executable. Functions:
- Provide usage instructions and basic context to the player.
- Handle initial language selection.
- Start a new game.
- Load or reset a saved game.
- Launch the main game file `Main_Game.blend`.

`Main_Game.blend` contains the main game scene, which is loaded via `Intro_Game.blend`.

The `Assets` folder contains the rest of the game elements grouped by type:
- `Fonts`
- `Models`
- `Scripts`
- `Sounds`
- `Texts`
- `Textures`

Except for the scripts, all other elements are linked to the main `.blend` files. This linking is established directly within the program or through the scripts.

# 🛠️ Scripts. General Aspects
Functional Python scripts are embedded directly within the `.blend` file itself.
The files located in the project's `/Scripts` folder are copies of these embedded files.
Therefore, to verify any changes in the game, the files embedded in the `.blend` must be updated. This can be done by directly modifying the script within the `.blend` or by importing the modified files from the `/Source/Assets/Scripts` folder. This import can be performed using the script: `utils_import_to_folder.py`.

At the beginning of this project, scripts were linked within the `.blend` file itself. However, this option was discarded because change tracking was less predictable and sometimes failed (conflicts). This manual control allows changes to be applied in either direction regardless of the workflow: Folder > `.blend` or `.blend` > Folder.

Depending on this workflow, scripts left on one side or the other (folder or file) can be considered backups as long as they are not manually synchronized via the import (`utils_import_to_folder.py`) or export (`utils_export_to_folder.py`) utilities.

**Script Types:**
- The main game scripts are attached to the object named `Game.Controller`. These scripts handle window/inventory systems, text rendering via BLF, audio, dialogs, etc.
- In addition to the main scripts, there are scripts attached to other objects that control their behavior. For example, NPCs, books, exhibition objects, etc.
- Finally, there are utility scripts that allow file operations such as importing or exporting scripts from within the `.blend` itself.

# 📁 Script Catalog by Functional Category
`*Technical documentation of the project's code architecture*`
https://img.shields.io/badge/Python-3.10+-blue
https://img.shields.io/badge/Blender-3.6+-orange
https://img.shields.io/badge/Status-In%20Development-yellow

| Functional Category | Script | Description |
| --- | --- | --- |
| **Core & Global** | `game_data.py` | Single source of truth for game data (stats, state, inventory). |
|  | `game_access.py` | Simplified access layer to GameManager for game state. |
|  | `game_init.py` | Game initialization with welcome messages and info. |
|  | `init_game.py` | Unified initialization of engine, languages, and game loading. |
|  | `save_system.py` | Save and load progress system using JSON files. |
|  | `game_achievements.py` | Achievement management, collectible progress, and rewards. |
|  | `game_displace_objects.py` | Handles inventory card movement between slots. |
| **User Interface (UI) & HUD** | `BLF_module.py` | Text rendering engine, progress bars, and visual effects. |
|  | `info_queue.py` | Priority queue for informative HUD messages. |
|  | `general_text.py` | General text management and to-do lists with checkboxes. |
|  | `format_hud_data.py` | HUD data formatting and overlay transition management. |
|  | `intro_blf_text.py` | Introductory text display with multilingual support. |
|  | `intro_sequence.py` | State machine for the game intro sequence. |
|  | `intro_buttons.py` | Button interaction in the intro menu. |
|  | `pause_window.py` | Pause menu and settings interface management. |
|  | `pause_buttons.py` | Button interaction within the pause menu. |
|  | `death_button.py` | Restart button functionality on the death screen. |
|  | `resize_backgrounds.py` | UI element scaling based on screen resolution. |
|  | `button_fx.py` | Visual effects system for inventory buttons (V1 & V2). |
|  | `exhibition_button.py` | Close button management for the exhibition interface. |
|  | `exhibition_objects.py` | Interaction with exhibition objects and info display. |
|  | `message_area_info.py` | Info messages triggered by collision zones in the area. |
|  | `input_toggle_inventory.py` | Inventory toggling management via keyboard input. |
|  | `container_object.py` | Container interaction and V2 inventory opening. |
| **NPCs & Enemy System** | `npc_logic.py` | Sequential activation system and logic for base NPCs. |
|  | `npc_dialog.py` | Interactive dialog system for general NPCs. |
|  | `npc_librarian.py` | Dialog and animation control for the Librarian NPC. |
|  | `npc_security_guard.py` | Interaction and dialogs for the Security Guard NPC. |
|  | `npc_restoration_logic.py` | Restoration NPC logic and work queue management. |
|  | `npc_restoration_dialog.py` | Specific dialog system for the restoration process. |
|  | `npc_cat.py` | Cat NPC behavior (patrol, combat, and pet mode). |
|  | `npc_mouse.py` | Mouse enemy behavior (navigation and attack). |
|  | `npc_cockroach.py` | Cockroach enemy behavior (damage and movement). |
|  | `npc_car.py` | Movement and physics control for the Car NPC. |
|  | `npc_pest_spawn.py` | Pest spawn manager (mice & cockroaches) by waves. |
|  | `npc_cat_food.py` | Food item management for the cat feeding system. |
| **Inventory & Collectibles System** | `inventory_module.py` | Display and stats management for Inventory V1. |
|  | `inventory_view2.py` | Detailed interface for item management (V2) and restoration. |
|  | `book_buttons.py` | Interaction with book interface buttons. |
|  | `books_library.py` | Content loading, pagination, and book management. |
|  | `storage_objects.py` | World collectible objects management and persistence. |
|  | `storage_spawn.py` | Collectible object spawn system at designated points. |
|  | `spray_can.py` | Spray can interaction for resource refills. |
|  | `spray_can_spawn.py` | Random spray can spawn control in the scene. |
|  | `spray_particle.py` | Particle system for spray usage effect. |
| **Game Mechanics & Environment** | `player_movement.py` | Movement mechanics, spray combat, and stamina system. |
|  | `player_death.py` | Player death sequence management and restart. |
|  | `kit_health.py` | Health kit interaction for player healing. |
|  | `kit_stamina.py` | Stamina kit interaction for energy recovery. |
|  | `matrix_effect.py` | "Matrix"-style visual particle effect for special events. |
|  | `matrix_rain_screen.py` | Full-screen binary character rain effect. |
|  | `door.py` | Door interaction (animation, proximity, and weather). |
|  | `door_street.py` | Proximity-controlled automatic street doors. |
|  | `camera.py` | Orthographic camera control with smooth player tracking. |
|  | `temperature_controller.py` | Temperature and humidity simulation based on environment. |
|  | `suspend_collections.py` | Collection logic suspension during UI interactions. |
| **Sound & Weather Management** | `sound_background.py` | Background music system with context/zone management. |
|  | `sound_fx.py` | Centralized sound effects playback system. |
|  | `sound_context.py` | Musical context switching based on collision zones. |
| **Quiz & Challenge Systems** | `quiz_module.py` | Question, answer, and feedback management for quizzes. |
|  | `quiz_button_logic.py` | Button interaction and response for the quiz system. |
|  | `quiz_button_restoration.py` | Specific button interaction for the restoration quiz. |
|  | `timer_controller.py` | Timer control for the quiz system. |
| **Utilities & Dev Tools** | `utils_export_to_folder.py` | Blender text blocks exporter to physical files. |
|  | `utils_import_from_folder.py` | Text files importer to Blender text blocks. |
|  | `utils_set_test_mode.py` | Variable configuration for test/debug mode. |
|  | `utils_set_production_mode.py` | Variable configuration for production/release mode. |
|  | `end_game_test.py` | Test script to verify game ending. |

## 📁 Node Graph of Script Relationships

See the full architectural diagram in [`architecture-diagram.md`](architecture-diagram.md).

## 🚀 Workflow

### ➕ Adding New Assets

1. Prepare your asset (3D model, texture, sound, etc.).
2. Place it in the corresponding folder inside `Source/Assets/` (e.g., `Source/Assets/Models/`).
3. Link the asset to the corresponding `.blend` file (e.g., `Main_Game.blend`).

### ➕ Adding New Scripts

1. Create your script directly within the `.blend` file using an existing template or the button to create new text blocks.
2. Using the `utils_export_to_folder.py` export tool will create a copy in the `Source/Assets/Scripts/` folder.
3. Ensure the script is compatible with the Python version of UPBGE you are using.

## 📏 Code Standards

- **Python:** Use Python 3.x compatible with UPBGE.
- **Naming:** Maintain clear and descriptive naming conventions for variables and functions.
- **Structure:** Try to follow the existing script structure to maintain consistency.
- **Comments:** Document complex functions to facilitate understanding.

## 📦 Building the Executable

To build a game executable, ensure you have the compatible UPBGE version installed (0.36 or 0.44 is recommended depending on the case).

- The executable must be built from the `Intro_Game.blend` file.
- Ensure the export add-on is enabled in Blender preferences (`Edit > Preferences > Add-ons`).
- Once enabled, you can create the executable: `File > Export > Save as game runtime`.

## 🧪 Testing & Verification

- Before submitting any changes, verify that the game launches correctly.
- Ensure new assets or scripts do not break existing functionality (especially inventory and dialog systems).
- Verify that script changes have been correctly imported into the `.blend` file.

## 🤝 Contribution Process

1. **Fork & Clone:** Fork the repository and clone it to your local machine.
2. **Branch:** Create a branch for your feature or fix (`git checkout -b feature/your-feature-name`).
3. **Commit:** Make atomic and descriptive commits.
4. **Push:** Push your changes to your branch on GitHub.
5. **Pull Request:** Create a Pull Request detailing the changes made.

