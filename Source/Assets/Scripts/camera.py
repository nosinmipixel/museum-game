"""
camera.py

Manages fixed orthographic camera movement with smooth following behavior.

This script implements a camera that follows the player with configurable
smoothing effects during movement start, movement, and stop phases.

Main Features:
    1. Fixed camera rotation (isometric perspective)
    2. Relative positioning relative to player
    3. Smooth camera following with easing curves
    4. Different smoothing for movement start and stop
    5. Delta time independent movement
    6. Automatic initialization on first frame

Setup:
    Connect to Logic Bricks as Python controller with module 'camera.main'
    or call the main() function directly

Configurable Variables:
    RELATIVE_DISTANCE (list): XYZ offset from player to camera (default: [8.4, -8.4, 9.90])
    CAMERA_ROTATION (list): Camera rotation in degrees (default: [52.0, 0.0, 45.0])
    SMOOTH_FACTOR (float): Base smoothing factor (0.0 = no smoothing, 1.0 = very smooth)
    MIN_MOVEMENT (float): Minimum movement to consider player moving (default: 0.01)
    START_SMOOTH_TIME (float): Smoothing time when starting to move in seconds (default: 0.5)
    STOP_SMOOTH_TIME (float): Smoothing time when stopping movement in seconds (default: 0.8)

Notes:
    - Requires objects named 'Player' and 'Camera' in the scene
    - Camera rotation is set only once at initialization
    - Uses linear interpolation (LERP) for position smoothing
    - Quadratic easing curves for more natural start/stop transitions
    - Delta time is calculated from logic tic rate for frame rate independence

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
__description__ = "Manages fixed orthographic camera movement with smooth following"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
import math

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main():
    """Main script for fixed orthographic camera movement with smoothing."""
    
    # Get reference to current scene
    scene = bge.logic.getCurrentScene()
    
    # Get references to objects
    player = scene.objects.get("Player")
    camera = scene.objects.get("Camera")
    
    if not player or not camera:
        return
    
    # Camera configuration (adjustable values)
    # Relative distance from camera to player
    RELATIVE_DISTANCE = [8.4, -8.4, 9.90]
    
    # Camera rotation angle (in degrees)
    CAMERA_ROTATION = [52.0, 0.0, 45.0]
    
    # Smoothing configuration (adjustable values)
    SMOOTH_FACTOR = 0.1  # Smoothing factor (0.0 = no smoothing, 1.0 = very smooth)
    MIN_MOVEMENT = 0.01  # Minimum movement to consider player moving
    START_SMOOTH_TIME = 0.5  # Smoothing time when starting (seconds)
    STOP_SMOOTH_TIME = 0.8   # Smoothing time when stopping (seconds)
    
    # Get delta time for current frame
    delta_time = 1.0 / bge.logic.getLogicTicRate() if bge.logic.getLogicTicRate() > 0 else 0.016
    
    # Initialize state variables if they don't exist
    if not hasattr(bge.logic, 'camera_initialized'):
        bge.logic.camera_initialized = False
        bge.logic.last_player_pos = [0, 0, 0]
        bge.logic.target_camera_pos = [0, 0, 0]
        bge.logic.current_camera_pos = [0, 0, 0]
        bge.logic.player_moving = False
        bge.logic.smooth_timer = 0.0
        bge.logic.smooth_phase = 'idle'  # 'idle', 'starting', 'moving', 'stopping'
    
    # Set camera rotation (only once at start)
    if not bge.logic.camera_initialized:
        # Convert angles from degrees to radians
        rotation_rad = [
            math.radians(CAMERA_ROTATION[0]),
            math.radians(CAMERA_ROTATION[1]),
            math.radians(CAMERA_ROTATION[2])
        ]
        
        # Set initial camera rotation
        camera.worldOrientation = [0, 0, 0]  # Reset orientation
        camera.applyRotation(rotation_rad, True)  # Apply rotation
        
        # Initialize camera position
        player_pos = player.worldPosition
        initial_camera_pos = [
            player_pos[0] + RELATIVE_DISTANCE[0],
            player_pos[1] + RELATIVE_DISTANCE[1],
            player_pos[2] + RELATIVE_DISTANCE[2]
        ]
        
        bge.logic.current_camera_pos = list(initial_camera_pos)
        bge.logic.target_camera_pos = list(initial_camera_pos)
        camera.worldPosition = initial_camera_pos
        
        # Mark as initialized
        bge.logic.camera_initialized = True
        print("Camera initialized with rotation:", CAMERA_ROTATION)
    
    # Get current player position
    current_player_pos = player.worldPosition
    
    # Calculate distance player has moved
    movement_distance = math.sqrt(
        (current_player_pos[0] - bge.logic.last_player_pos[0]) ** 2 +
        (current_player_pos[1] - bge.logic.last_player_pos[1]) ** 2 +
        (current_player_pos[2] - bge.logic.last_player_pos[2]) ** 2
    )
    
    # Determine if player is moving
    is_moving_now = movement_distance > MIN_MOVEMENT
    
    # Update movement state and smoothing timer
    if is_moving_now and not bge.logic.player_moving:
        # Player started moving
        bge.logic.player_moving = True
        bge.logic.smooth_phase = 'starting'
        bge.logic.smooth_timer = 0.0
    elif not is_moving_now and bge.logic.player_moving:
        # Player stopped moving
        bge.logic.player_moving = False
        bge.logic.smooth_phase = 'stopping'
        bge.logic.smooth_timer = 0.0
    elif bge.logic.smooth_phase == 'starting' or bge.logic.smooth_phase == 'stopping':
        # Update timer during smoothing phases
        bge.logic.smooth_timer += delta_time
    
    # Calculate target camera position
    target_position = [
        current_player_pos[0] + RELATIVE_DISTANCE[0],
        current_player_pos[1] + RELATIVE_DISTANCE[1],
        current_player_pos[2] + RELATIVE_DISTANCE[2]
    ]
    
    # Update target position
    bge.logic.target_camera_pos = target_position
    
    # Calculate smoothing factor based on current state
    current_smooth_factor = SMOOTH_FACTOR
    
    if bge.logic.smooth_phase == 'starting':
        # Progressive smoothing when starting
        progress = min(bge.logic.smooth_timer / START_SMOOTH_TIME, 1.0)
        # Quadratic interpolation for smoother start
        ease_in = progress * progress
        current_smooth_factor = SMOOTH_FACTOR * (1.0 - ease_in * 0.7)
        
        if progress >= 1.0:
            bge.logic.smooth_phase = 'moving'
            
    elif bge.logic.smooth_phase == 'stopping':
        # Progressive smoothing when stopping
        progress = min(bge.logic.smooth_timer / STOP_SMOOTH_TIME, 1.0)
        # Inverse quadratic interpolation for smoother stop
        ease_out = 1.0 - (1.0 - progress) * (1.0 - progress)
        current_smooth_factor = SMOOTH_FACTOR * (1.0 + ease_out * 2.0)
        
        if progress >= 1.0:
            bge.logic.smooth_phase = 'idle'
    
    # Apply smooth interpolation to camera position
    # Only if in a phase that requires smoothing
    if bge.logic.smooth_phase != 'idle':
        for i in range(3):
            # Smoothed linear interpolation (LERP)
            bge.logic.current_camera_pos[i] = (
                bge.logic.current_camera_pos[i] * (1.0 - current_smooth_factor) +
                bge.logic.target_camera_pos[i] * current_smooth_factor
            )
    else:
        # No smoothing, follow target directly
        bge.logic.current_camera_pos = list(bge.logic.target_camera_pos)
    
    # Set new camera position
    camera.worldPosition = bge.logic.current_camera_pos
    
    # Save current player position for next frame
    bge.logic.last_player_pos = list(current_player_pos)

# Execute the function
if __name__ == "__main__":
    main()