"""
utils_export_to_folder.py

Text block exporter for UPBGE/Blender

This script exports all Text Editor blocks from a UPBGE/Blender .blend file
to physical files in the '//Assets/Scripts/' folder relative to the current .blend file.

Main Features:
    1. Exports all text blocks from current .blend to physical files
    2. Saves to '//Assets/Scripts/' folder relative to .blend
    3. Overwrites existing files automatically
    4. Preserves original text block names
    5. Full support for Python scripts (.py) and any text files
    6. UTF-8 encoding for special characters
    7. Creates destination folder automatically if missing
    8. Provides detailed operation summary

Setup:
    Save the .blend file first, then run this script from Text Editor (Alt+P)

Configurable Variables:
    scripts_dir (str): Destination folder (default: '//Assets/Scripts/')

Notes:
    - Requires .blend file to be saved before execution
    - Only exports Text Editor blocks, not other resources
    - Ideal for version control or backup of embedded scripts
    - Compatible with UPBGE 0.36, 0.44

License: GPL-3.0-only (View LICENSE.txt)
UPBGE Compatible: 0.36, 0.44
"""

# =============================================================================
# METADATA
# =============================================================================
__author__ = "nosinmipixel"
__version__ = "1.1"
__license__ = "GPL-3.0-only"
__upbge_compatible__ = ["0.36", "0.44"]
__description__ = "Exports text blocks from .blend to physical files"

# =============================================================================
# IMPORTS
# =============================================================================
import bpy
import os

# =============================================================================
# MAIN EXPORT FUNCTION
# =============================================================================
def save_text_blocks_to_folder():
    """
    Save all text blocks from current .blend file
    to '//Assets/Scripts/' folder (relative to .blend file)
    """
    # Check if .blend file is saved
    blend_file_path = bpy.data.filepath
    
    if not blend_file_path:
        print("ERROR: You must save the .blend file first")
        print("       Use File > Save or Ctrl+S")
        return False
    
    # Get directory path of .blend file
    blend_dir = os.path.dirname(blend_file_path)
    blend_name = os.path.basename(blend_file_path)
    
    # Define destination folder (//Assets/Scripts/)
    scripts_dir = os.path.join(blend_dir, "Assets/Scripts")
    
    print(f".blend file: {blend_name}")
    print(f"Location: {blend_dir}")
    print(f"Destination folder: {scripts_dir}")
    print("-" * 50)
    
    # Check if there are text blocks
    if len(bpy.data.texts) == 0:
        print("No text blocks in this .blend file")
        return False
    
    # Create folder if it doesn't exist (no error if already exists)
    os.makedirs(scripts_dir, exist_ok=True)
    
    if os.path.exists(scripts_dir):
        print(f"Folder '{scripts_dir}' ready")
    else:
        print(f"Could not create folder '{scripts_dir}'")
        return False
    
    # Counters
    saved_count = 0
    error_count = 0
    python_scripts = 0
    
    # Iterate over all text blocks
    for text_block in bpy.data.texts:
        # Define full output file path
        output_path = os.path.join(scripts_dir, text_block.name)
        
        # Count Python scripts
        if text_block.name.endswith('.py'):
            python_scripts += 1
        
        try:
            # Check if file already exists
            file_exists = os.path.exists(output_path)
            
            # Write text block content to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(text_block.as_string())
            
            status = "Overwritten" if file_exists else "Created"
            print(f"{status}: {text_block.name}")
            saved_count += 1
            
        except PermissionError:
            print(f"Permission error: {text_block.name} (file open in another program?)")
            error_count += 1
        except Exception as e:
            print(f"Error saving {text_block.name}: {str(e)}")
            error_count += 1
    
    # Show summary
    print("\n" + "=" * 50)
    print("EXPORT SUMMARY")
    print("=" * 50)
    print(f"Total blocks in .blend: {len(bpy.data.texts)}")
    print(f"  • Python scripts (.py): {python_scripts}")
    print(f"  • Other types: {len(bpy.data.texts) - python_scripts}")
    print(f"\nFiles saved: {saved_count}")
    print(f"Errors: {error_count}")
    print(f"\nLocation: {scripts_dir}")
    
    if saved_count > 0:
        print("\nExport completed successfully")
        return True
    else:
        print("\nNo files could be exported")
        return False

# =============================================================================
# MAIN EXECUTION
# =============================================================================
if __name__ == "__main__":
    print("\n=== TEXT BLOCK EXPORTER ===")
    print("Exporting to '//Assets/Scripts/' folder...\n")
    save_text_blocks_to_folder()