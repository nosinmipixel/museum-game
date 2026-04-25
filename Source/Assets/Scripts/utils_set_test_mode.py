"""
utils_set_test_mode.py

Set game variables to Test mode values.

This script modifies specific game variables to their Test mode values
and configures render properties for debugging and testing builds.

Main Features:
    1. Sets sound_background to False in game_data.py
    2. Sets NPC_INIT_TIME to 5.0 in npc_logic.py
    3. Sets SPAWN_INTERVAL to 8.0 in storage_spawn.py
    4. Enables Debug Properties in Render Properties
    5. Enables Framerate and Profile in Render Properties
    6. Preserves code indentation and comments when modifying

Setup:
    Run active script (Alt+P) from Text Editor in UPBGE
    Or connect to Logic Bricks as Script/Module 'utils_set_test_mode.set_test_values'

Configurable Variables:
    variables_to_set_test (list): List of variable configurations for test values
        - file (str): Target script filename
        - var_name (str): Variable name to modify
        - test_value (str): Value to set for test mode
        - production_values (list): Values considered as production mode
        - description (str): Human readable description

Notes:
    - Script must be run from within UPBGE environment
    - Changes are applied directly to scripts in memory
    - Save .blend file manually (Ctrl+S) to persist changes
    - Both render options are enabled for test/debug builds
    - NPC_INIT_TIME set to 5.0 seconds for faster testing
    - SPAWN_INTERVAL set to 8.0 seconds for quicker spawns

License: GPL-3.0-only (View LICENSE.txt)
UPBGE Compatible: 0.36, 0.44
"""

# =============================================================================
# METADATA
# =============================================================================
__author__ = "nosinmipixel"
__version__ = "1.0.0"
__license__ = "GPL-3.0-only"
__upbge_compatible__ = ["0.36", "0.44"]
__description__ = "Set game variables and render properties to Test mode"

import bpy
import re


def set_render_properties():
    """Configure render properties for Test mode."""
    print("\nRENDER CONFIGURATION")
    print("-" * 50)
    
    # Enable Debug Properties for testing
    bpy.context.scene.game.debug_properties = True
    print("Debug Properties: Enabled (Test mode)")
    
    # Enable Framerate and Profile for testing
    bpy.context.scene.game.show_framerate_and_profile = True
    print("Framerate and Profile: Enabled (Test mode)")


def set_test_values():
    """Ensure values are in Test mode (search by variable name)."""
    
    variables_to_set_test = [
        {
            "file": "game_data.py",
            "var_name": "self.sound_background",
            "test_value": "False",
            "production_values": ["True"],
            "description": "Background sound (TEST: Disabled)"
        },
        {
            "file": "npc_logic.py",
            "var_name": "NPC_INIT_TIME",
            "test_value": "5.0",
            "production_values": ["120.0", "5000"],
            "description": "NPC startup time (TEST: Fast)"
        },
        {
            "file": "storage_spawn.py",
            "var_name": "SPAWN_INTERVAL",
            "test_value": "8.0",
            "production_values": ["10.0"],
            "description": "Collectible spawn interval (TEST: Faster)"
        }
    ]
    
    modified_count = 0
    error_count = 0
    
    print("\nACTIVATING TEST MODE")
    print("=" * 60)
    
    available_scripts = [text.name for text in bpy.data.texts]
    print(f"Available scripts: {', '.join(available_scripts)}\n")
    
    for var_config in variables_to_set_test:
        target_file = var_config["file"]
        found = False
        
        for text in bpy.data.texts:
            if text.name == target_file:
                found = True
                content = text.as_string()
                lines = content.split('\n')
                
                print(f"Processing: {target_file}")
                
                modified = False
                var_pattern = re.compile(r'{}\s*='.format(re.escape(var_config["var_name"])))
                
                for i, line in enumerate(lines, 1):
                    if var_pattern.search(line):
                        current_value_match = re.search(r'=\s*([^#\n]+)', line)
                        if current_value_match:
                            current_value = current_value_match.group(1).strip()
                            
                            if current_value == var_config["test_value"]:
                                print(f"  OK {var_config['description']}: {current_value} (Test already active)")
                            elif current_value in var_config["production_values"]:
                                parts = line.split('=', 1)
                                if len(parts) == 2:
                                    indent = parts[0][:-len(parts[0].lstrip())]
                                    var_part = parts[0].strip()
                                    new_line = f"{indent}{var_part} = {var_config['test_value']}"
                                    
                                    if '#' in parts[1]:
                                        comment = parts[1].split('#', 1)[1]
                                        new_line += f"  # {comment}"
                                    
                                    lines[i-1] = new_line
                                    modified = True
                                    modified_count += 1
                                    print(f"  UPDATED {var_config['description']}: {current_value} -> {var_config['test_value']} (Test mode activated)")
                                else:
                                    print(f"  WARNING Cannot parse line: {line}")
                            else:
                                print(f"  WARNING {var_config['description']}: Unexpected value '{current_value}' - Not modified")
                        break
                
                if modified:
                    new_content = '\n'.join(lines)
                    text.from_string(new_content)
                    print(f"  SAVED Changes to {target_file}")
                
                break
        
        if not found:
            error_count += 1
            print(f"ERROR Script not found: {target_file}")
    
    print("\n" + "=" * 60)
    if modified_count > 0:
        print(f"TEST MODE ACTIVATED: {modified_count} file(s) updated")
        print("Test values applied:")
        print("   - Background sound: Disabled (False)")
        print("   - NPC Init Time: 5.0 seconds")
        print("   - Spawn Interval: 8.0 seconds")
        print("REMINDER: Save .blend file (Ctrl+S) to persist changes")
    else:
        print("ALL GOOD: All values already in Test mode")
    
    if error_count > 0:
        print(f"ERRORS: {error_count} script(s) not found")
    
    print("=" * 60)


def check_test_mode():
    """Check current state of test mode without modifying."""
    
    variables_to_check = [
        {"file": "game_data.py", "var_name": "self.sound_background", "name": "Sound Background", "test_value": "False"},
        {"file": "npc_logic.py", "var_name": "NPC_INIT_TIME", "name": "NPC Init Time", "test_value": "5.0"},
        {"file": "storage_spawn.py", "var_name": "SPAWN_INTERVAL", "name": "Spawn Interval", "test_value": "8.0"}
    ]
    
    print("\nCHECKING TEST MODE STATE (read only)")
    print("-" * 50)
    
    all_test = True
    
    for var_config in variables_to_check:
        found = False
        for text in bpy.data.texts:
            if text.name == var_config["file"]:
                found = True
                content = text.as_string()
                lines = content.split('\n')
                
                var_pattern = re.compile(r'{}\s*='.format(re.escape(var_config["var_name"])))
                
                for line in lines:
                    if var_pattern.search(line):
                        value_match = re.search(r'=\s*([^#\n]+)', line)
                        if value_match:
                            current_value = value_match.group(1).strip()
                            if current_value == var_config["test_value"]:
                                status = "OK"
                            else:
                                status = "MISSING"
                                all_test = False
                            print(f"[{status}] {var_config['name']}: {current_value}")
                        break
                break
        
        if not found:
            print(f"[ERROR] Script not found: {var_config['file']}")
            all_test = False
    
    return all_test


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'check':
        check_test_mode()
    else:
        print("APPLYING TEST MODE SETTINGS")
        print("#" * 60)
        set_render_properties()
        set_test_values()
        print("\nVerifying applied changes:")
        check_test_mode()