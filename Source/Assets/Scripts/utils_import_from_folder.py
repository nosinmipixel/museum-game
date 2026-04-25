"""
utils_import_from_folder.py

# Text block importer for UPBGE/Blender

This script imports text files from the '//Assets/Scripts/' folder into the current
.blend file, creating or updating text blocks accordingly. It is complementary
to utils_export_to_folder.py.

Main Features:
    1. Imports files from '//Assets/Scripts/' folder to current .blend file
    2. Updates existing text blocks with same name
    3. Creates new text blocks for files not in .blend
    4. Ignores .blend blocks without corresponding file (optional)
    5. Supports multiple file types (.py, .txt, .json, .xml, etc.)
    6. UTF-8 encoding for proper special character reading
    7. Provides options to remove missing blocks
    8. Detailed operation summary

Setup:
    Ensure '//Assets/Scripts/' folder exists in same directory as .blend file,
    then run this script from Text Editor (Alt+P)

Configurable Variables:
    IMPORT_MODE (str): 'update_only' or 'sync' (bidirectional sync)
    REMOVE_MISSING (bool): Remove blocks without corresponding file
    ALLOWED_EXTENSIONS (list): Allowed extensions (None = all text files)

Notes:
    - Requires .blend file to be saved before execution
    - Files must be in UTF-8 or compatible encoding
    - Filenames become text block names
    - Externally modified files overwrite internal ones
    - Recommended for development with external editors (VS Code, PyCharm)

License: GPL-3.0-only (View LICENSE.txt)
UPBGE Compatible: 0.36, 0.44
"""

# =============================================================================
# METADATA
# =============================================================================
__author__ = "nosinmipixel"
__version__ = "1.0"
__license__ = "GPL-3.0-only"
__upbge_compatible__ = ["0.36", "0.44"]
__description__ = "Imports text files from Assets/Scripts/ folder to .blend text blocks"

# =============================================================================
# IMPORTS
# =============================================================================
import bpy
import os

# =============================================================================
# MAIN IMPORT FUNCTION
# =============================================================================
def import_text_blocks_from_folder(import_mode='update_only', 
                                   remove_missing=False,
                                   allowed_extensions=None):
    """
    Import text files from '//Assets/Scripts/' folder to current .blend file
    
    Parameters:
    - import_mode: 'update_only' (only update existing) or 
                   'sync' (full sync - creates new)
    - remove_missing: If True, remove blocks from .blend without corresponding file
    - allowed_extensions: List of allowed extensions (e.g., ['.py', '.txt'])
                         None = all text files
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
    
    # Define source folder (//Assets/Scripts/)
    scripts_dir = os.path.join(blend_dir, "Assets/Scripts")
    
    print(f".blend file: {blend_name}")
    print(f"Location: {blend_dir}")
    print(f"Source folder: {scripts_dir}")
    print(f"Mode: {import_mode}")
    print("-" * 50)
    
    # Check if Scripts folder exists
    if not os.path.exists(scripts_dir):
        print(f"Folder '{scripts_dir}' does not exist")
        print("  Run export script first to create it")
        return False
    
    # Get list of files in Scripts folder
    try:
        all_files = os.listdir(scripts_dir)
    except Exception as e:
        print(f"Error reading folder: {str(e)}")
        return False
    
    # Filter by extensions if specified
    if allowed_extensions:
        text_files = [f for f in all_files 
                     if os.path.splitext(f)[1].lower() in allowed_extensions]
        print(f"Allowed extensions: {allowed_extensions}")
    else:
        # Filter only files (not folders) that are text files
        text_files = []
        for f in all_files:
            full_path = os.path.join(scripts_dir, f)
            if os.path.isfile(full_path):
                # Try to determine if it's a text file
                try:
                    with open(full_path, 'r', encoding='utf-8') as test_file:
                        test_file.read(1024)  # Read a little to verify
                    text_files.append(f)
                except UnicodeDecodeError:
                    print(f"  Ignored (not UTF-8 text): {f}")
                except Exception:
                    print(f"  Ignored (read error): {f}")
    
    if not text_files:
        print("No text files found in Assets/Scripts/ folder")
        return False
    
    print(f"Files found in Assets/Scripts/: {len(text_files)}")
    
    # Counters
    updated_count = 0
    created_count = 0
    skipped_count = 0
    removed_count = 0
    
    # 1. FIRST: Process files from folder
    for filename in text_files:
        file_path = os.path.join(scripts_dir, filename)
        
        # Read file content
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_content = f.read()
        except Exception as e:
            print(f"Error reading {filename}: {str(e)}")
            skipped_count += 1
            continue
        
        # Check if text block already exists with this name
        if filename in bpy.data.texts:
            # Update existing block
            text_block = bpy.data.texts[filename]
            text_block.clear()
            text_block.write(file_content)
            print(f"Updated: {filename}")
            updated_count += 1
        elif import_mode == 'sync':
            # Create new text block
            new_text = bpy.data.texts.new(filename)
            new_text.write(file_content)
            print(f"Created new: {filename}")
            created_count += 1
        else:
            print(f"Ignored (not in .blend): {filename}")
            skipped_count += 1
    
    # 2. SECOND: Remove blocks from .blend without corresponding file
    if remove_missing:
        # Create set of filenames (without path)
        file_names = set(text_files)
        
        # Find blocks in .blend without file
        for text_block in bpy.data.texts[:]:  # Copy list to modify
            if text_block.name not in file_names:
                print(f"Removed (no file): {text_block.name}")
                bpy.data.texts.remove(text_block)
                removed_count += 1
    
    # 3. Show summary
    print("\n" + "=" * 50)
    print("IMPORT SUMMARY")
    print("=" * 50)
    print(f"Files in folder: {len(text_files)}")
    print(f"\nBlocks in .blend before: {len(bpy.data.texts) - created_count + removed_count}")
    print(f"Blocks in .blend after: {len(bpy.data.texts)}")
    print(f"\nOperations performed:")
    print(f"  • Updated: {updated_count}")
    print(f"  • Created: {created_count}")
    print(f"  • Ignored: {skipped_count}")
    print(f"  • Removed: {removed_count}")
    
    if remove_missing:
        print(f"\nWARNING: {removed_count} blocks removed from .blend")
        print("  (without corresponding file in folder)")
    
    print(f"\nSource location: {scripts_dir}")
    
    success = (updated_count + created_count) > 0
    if success:
        print("\nImport completed successfully")
    else:
        print("\nNo changes were made")
    
    return success

# =============================================================================
# MAIN EXECUTION
# =============================================================================
if __name__ == "__main__":
    print("\n=== TEXT BLOCK IMPORTER ===")
    print("Importing from '//Assets/Scripts/' to .blend file...\n")
    
    # CONFIGURATION - MODIFY THESE VALUES AS NEEDED
    IMPORT_MODE = 'sync'  # 'update_only' or 'sync'
    REMOVE_MISSING = False  # True to remove blocks without file
    ALLOWED_EXTENSIONS = None  # None for all, or ['.py', '.txt'] to filter
    
    import_text_blocks_from_folder(
        import_mode=IMPORT_MODE,
        remove_missing=REMOVE_MISSING,
        allowed_extensions=ALLOWED_EXTENSIONS
    )