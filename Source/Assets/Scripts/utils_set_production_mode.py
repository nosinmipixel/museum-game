"""
utils_set_production_mode.py

Set game variables to Production mode values.

This script modifies specific game variables to their Production mode values
and configures render properties for release builds.

Main Features:
    1. Sets sound_background to True in game_data.py
    2. Sets NPC_INIT_TIME to 120.0 in npc_logic.py
    3. Sets SPAWN_INTERVAL to 10.0 in storage_spawn.py
    4. Disables Debug Properties in Render Properties
    5. Disables Framerate and Profile in Render Properties
    6. Preserves code indentation and comments when modifying

Setup:
    Run active script (Alt+P) from Text Editor in UPBGE
    Or connect to Logic Bricks as Script/Module 'utils_set_production_mode.set_production_values'

Configurable Variables:
    variables_to_fix (list): List of variable configurations for production values
        - file (str): Target script filename
        - var_name (str): Variable name to modify
        - production_value (str): Value to set for production
        - test_values (list): Values considered as test mode
        - description (str): Human readable description

Notes:
    - Script must be run from within UPBGE environment
    - Changes are applied directly to scripts in memory
    - Save .blend file manually (Ctrl+S) to persist changes
    - Both render options are disabled for production builds

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
__description__ = "Set game variables and render properties to Production mode"

import bpy
import re


def set_render_properties():
    """Configure render properties for Production mode."""
    print("\nRENDER CONFIGURATION")
    print("-" * 50)
    
    # Disable Debug Properties for production
    bpy.context.scene.game.debug_properties = False
    print("Debug Properties: Disabled (Production)")
    
    # Disable Framerate and Profile for production
    bpy.context.scene.game.show_framerate_and_profile = False
    print("Framerate and Profile: Disabled (Production)")


def set_production_values():
    """Ensure values are in Production mode (search by variable name)."""
    
    variables_to_fix = [
        {
            "file": "game_data.py",
            "var_name": "self.sound_background",
            "production_value": "True",
            "test_values": ["False", "None"],
            "description": "Background sound"
        },
        {
            "file": "npc_logic.py",
            "var_name": "NPC_INIT_TIME",
            "production_value": "120.0",
            "test_values": ["5.0", "5000"],
            "description": "NPC startup time"
        },
        {
            "file": "storage_spawn.py",
            "var_name": "SPAWN_INTERVAL",
            "production_value": "10.0",
            "test_values": ["8.0", "8", "10"],
            "description": "Collectible spawn interval"
        }
    ]
    
    modified_count = 0
    error_count = 0
    
    print("\nVERIFYING PRODUCTION MODE (intelligent search)")
    print("=" * 60)
    
    available_scripts = [text.name for text in bpy.data.texts]
    print(f"Available scripts: {', '.join(available_scripts)}\n")
    
    for var_config in variables_to_fix:
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
                            
                            if current_value == var_config["production_value"]:
                                print(f"  OK {var_config['description']}: {var_config['var_name']} = {current_value} (Production active)")
                            elif current_value in var_config["test_values"]:
                                parts = line.split('=', 1)
                                if len(parts) == 2:
                                    indent = parts[0][:-len(parts[0].lstrip())]
                                    var_part = parts[0].strip()
                                    new_line = f"{indent}{var_part} = {var_config['production_value']}"
                                    
                                    if '#' in parts[1]:
                                        comment = parts[1].split('#', 1)[1]
                                        new_line += f"  # {comment}"
                                    
                                    lines[i-1] = new_line
                                    modified = True
                                    modified_count += 1
                                    print(f"  UPDATED {var_config['description']}: {current_value} -> {var_config['production_value']} (Production mode)")
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
        print(f"MODIFIED: {modified_count} file(s) updated to Production mode")
        print("REMINDER: Save .blend file (Ctrl+S) to persist changes")
    else:
        print("ALL GOOD: All values already in Production mode")
    
    if error_count > 0:
        print(f"ERRORS: {error_count} script(s) not found")
    
    print("=" * 60)


def check_production_mode():
    """Check current state without modifying anything."""
    
    variables_to_check = [
        {"file": "game_data.py", "var_name": "self.sound_background", "name": "Sound Background", "prod_value": "True"},
        {"file": "npc_logic.py", "var_name": "NPC_INIT_TIME", "name": "NPC Init Time", "prod_value": "120.0"},
        {"file": "storage_spawn.py", "var_name": "SPAWN_INTERVAL", "name": "Spawn Interval", "prod_value": "10.0"}
    ]
    
    print("\nCHECKING CURRENT STATE (read only)")
    print("-" * 50)
    
    all_production = True
    
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
                            if current_value == var_config["prod_value"]:
                                status = "OK"
                            else:
                                status = "MISSING"
                                all_production = False
                            print(f"[{status}] {var_config['name']}: {current_value}")
                        break
                break
        
        if not found:
            print(f"[ERROR] Script not found: {var_config['file']}")
            all_production = False
    
    return all_production


# =============================================================================
# MAIN
# =============================================================================
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == 'check':
        check_production_mode()
    else:
        print("APPLYING PRODUCTION MODE SETTINGS")
        print("#" * 60)
        set_render_properties()
        set_production_values()
        print("\nVerifying applied changes:")
        check_production_mode()