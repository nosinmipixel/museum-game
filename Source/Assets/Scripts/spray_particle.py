"""
spray_particle.py

Spray particle system for UPBGE

This script manages a spray particle emission system that consumes spray resource
from the game state. It handles particle emission rates, random direction spread,
velocity variation, and resource consumption based on particles emitted.

Main Features:
    1. Particle emission with configurable rate (particles per second)
    2. Random spread angle for spray cone effect
    3. Variable particle velocity within configurable range
    4. Resource consumption based on particles emitted
    5. Activation delay before emission starts
    6. Automatic shutdown when spray resource is depleted
    7. Player state notification for audio/visual feedback

Setup:
    Owner: 'Empty.Spray'
    Logic Bricks: Always (True) and Keyboard sensors connected to a Python controller/module 'spray_particle.main'
    Requires particle objects named: Spray.Particle, Spray.Particle.002, Spray.Particle.003
    Requires Player object with 'player_attacking' property

Configurable Variables:
    DEBUG_ENABLED (bool): Enable debug messages (default: False)
    spray_delay (float): Delay before emission starts (default: 0.3)
    spray_particles_per_second (int): Emission rate (default: 20)
    spray_velocity_min (float): Minimum particle velocity (default: 8.0)
    spray_velocity_max (float): Maximum particle velocity (default: 12.0)
    spray_spread_angle (float): Spread cone angle in radians (default: 0.3)
    spray_particle_lifetime (int): Particle lifespan in frames (default: 15)
    spray_consumption_per_particle (float): Spray cost per particle (default: 0.5)

Notes:
    - Requires game_access module for game state management
    - Particle emission stops automatically when spray reaches zero
    - Notifies Player object when spray is depleted
    - Uses random selection from multiple particle templates
    - Particles inherit position from emitter object

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
__description__ = "Spray particle system with resource consumption and player feedback"

# =============================================================================
# IMPORTS AND CONFIGURATION
# =============================================================================
import bge
from bge import logic
import random
from mathutils import Vector
import game_access

DEBUG_ENABLED = False  # Set to False to disable ALL debug messages

def debug_print(message, debug_type="INFO"):
    """Centralized debug message function"""
    if DEBUG_ENABLED:
        print(f"[SPRAY SYSTEM - {debug_type}] {message}")

# =============================================================================
# SPRAY SYSTEM INITIALIZATION
# =============================================================================
def setup_spray_system():
    """Initialize spray particle system at startup"""
    cont = logic.getCurrentController()
    owner = cont.owner
    scene = logic.getCurrentScene()
    
    # Configurable properties
    if "spray_initialized" not in owner:
        owner["spray_initialized"] = True
        owner["spray_active"] = False
        owner["spray_delay"] = 0.3
        owner["spray_delay_timer"] = 0.0
        owner["spray_particles_per_second"] = 20
        owner["spray_velocity_min"] = 8.0
        owner["spray_velocity_max"] = 12.0
        owner["spray_spread_angle"] = 0.3
        owner["spray_particle_lifetime"] = 15
        owner["time_since_last_emission"] = 0.0
        owner["spray_emitting"] = False
        
        # Consumption based on emitted particles - FIX
        owner["spray_consumption_per_particle"] = 0.5  # Spray points per particle (ADJUSTABLE)
        owner["spray_emitted_this_frame"] = 0  # Emitted particles counter
        
        # NEW: State control to notify player
        owner["spray_was_available"] = True  # Previous spray state
        owner["player_notified_empty"] = False  # Whether player has been notified
        
        # Available particle objects list
        owner["available_particles"] = [
            "Spray.Particle",
            "Spray.Particle.002", 
            "Spray.Particle.003"
        ]
        
        debug_print("Spray system initialized", "INIT")

# =============================================================================
# SPRAY RESOURCE MANAGEMENT
# =============================================================================
def can_consume_spray(consumption_amount):
    """Check if enough spray is available using new architecture"""
    try:
        game = game_access.get_game()
        if game:
            return game.state.spray_total >= consumption_amount
    except Exception as e:
        debug_print(f"Error accessing GameManager: {e}", "WARNING")
    return False

def consume_spray(consumption_amount):
    """Consume specific amount of spray using new architecture"""
    try:
        game = game_access.get_game()
        if not game:
            return 0
            
        current_spray = game.state.spray_total
        
        if current_spray <= 0:
            return 0
        
        # Reduce spray
        new_spray = current_spray - consumption_amount
        
        # Do not allow negative values
        if new_spray < 0:
            new_spray = 0
            consumption_amount = current_spray  # Adjust actual consumption
        
        game.state.spray_total = new_spray
        debug_print(f"Spray consumed: {consumption_amount:.2f}, Remaining: {new_spray:.2f}", "CONSUMPTION")
        return consumption_amount  # Return actual consumption
        
    except Exception as e:
        debug_print(f"Error consuming spray: {e}", "ERROR")
        return 0

def update_player_spray_state(spray_available):
    """
    NEW FUNCTION: Update Player state so player_movement.py can react
    """
    try:
        scene = logic.getCurrentScene()
        player = scene.objects.get("Player")
        
        if player:
            # Update property on Player for player_movement.py to read
            player['spray_available'] = spray_available
            
            # If spray is depleted, force update in player_movement.py
            if not spray_available:
                # These properties are used by player_movement.py for sound/effects control
                if player.get('current_spray_sound') == 'spray.ogg':
                    # Force sound change in next player_movement.py frame
                    player['_spray_just_emptied'] = True
                    debug_print("Notifying player_movement that spray is depleted", "NOTIFICATION")
            else:
                # Reset flag when spray is available
                player['_spray_just_emptied'] = False
                
    except Exception as e:
        debug_print(f"Error updating player state: {e}", "ERROR")

# =============================================================================
# ACTIVATION DELAY HANDLING
# =============================================================================
def handle_activation_delay(owner, player_attacking):
    """Handle delay between attack signal and actual emission"""
    fps = logic.getLogicTicRate()
    delta_time = 1.0 / fps if fps > 0 else 0.016
    
    if player_attacking and not owner["spray_emitting"]:
        # Check if enough spray before starting delay
        if not can_consume_spray(owner["spray_consumption_per_particle"]):
            owner["spray_emitting"] = False
            owner["spray_delay_timer"] = 0.0
            debug_print("Insufficient spray to start emission", "DEPLETED")
            return
        
        # Increment delay timer
        owner["spray_delay_timer"] += delta_time
        debug_print(f"Delay timer: {owner['spray_delay_timer']:.2f}/{owner['spray_delay']}", "DELAY")
        
        # Check if delay time has passed
        if owner["spray_delay_timer"] >= owner["spray_delay"]:
            owner["spray_emitting"] = True
            owner["spray_delay_timer"] = 0.0
            debug_print("Particle system ACTIVATED after delay", "ACTIVATION")
    
    elif not player_attacking:
        # Reset everything when player stops attacking
        if owner["spray_emitting"]:
            debug_print("Particle system DEACTIVATED (player stopped attacking)", "DEACTIVATION")
        owner["spray_emitting"] = False
        owner["spray_delay_timer"] = 0.0
        owner["time_since_last_emission"] = 0.0

# =============================================================================
# PARTICLE EMISSION
# =============================================================================
def emit_particle(owner, scene):
    """Emit a single particle with random properties"""
    # Select random particle object
    particle_name = random.choice(owner["available_particles"])
    
    # Calculate random direction within spread angle
    base_direction = Vector((0, 0, -1))
    
    # Apply random rotation in X and Y
    spread = owner["spray_spread_angle"]
    rot_x = random.uniform(-spread, spread)
    rot_y = random.uniform(-spread, spread)
    
    # Rotate base direction
    from mathutils import Euler
    rotation = Euler((rot_x, rot_y, 0), 'XYZ')
    direction = base_direction.copy()
    direction.rotate(rotation)
    
    # Calculate random velocity
    velocity = random.uniform(
        owner["spray_velocity_min"], 
        owner["spray_velocity_max"]
    )
    
    # Final linear velocity
    linear_velocity = direction * velocity
    
    # Create the particle
    try:
        particle_obj = scene.addObject(particle_name, owner, owner["spray_particle_lifetime"])
        
        # Apply linear velocity
        particle_obj.setLinearVelocity(
            [linear_velocity.x, linear_velocity.y, linear_velocity.z], 
            True
        )
        
        # Optional: add random initial rotation
        particle_obj.setAngularVelocity([
            random.uniform(-1, 1),
            random.uniform(-1, 1), 
            random.uniform(-1, 1)
        ], True)
        
        debug_print(f"Particle emitted: {particle_name}, Velocity: {velocity:.2f}", "PARTICLE")
        
    except Exception as e:
        debug_print(f"Error creating particle: {e}", "ERROR")

# =============================================================================
# MAIN UPDATE FUNCTION
# =============================================================================
def update_spray():
    """Update particle system each frame using new architecture"""
    cont = logic.getCurrentController()
    owner = cont.owner
    scene = logic.getCurrentScene()
    
    # Reset emitted particles counter
    owner["spray_emitted_this_frame"] = 0
    
    fps = logic.getLogicTicRate()
    delta_time = 1.0 / fps if fps > 0 else 0.016
    
    # Get current spray state
    game = game_access.get_game()
    spray_available = game.state.spray_total > 0 if game else True
    
    # UPDATE PLAYER STATE EVERY FRAME
    update_player_spray_state(spray_available)
    
    # Check if player is attacking
    try:
        player = scene.objects["Player"]
        player_attacking = player.get("player_attacking", False)
        debug_print(f"Player attack state: {player_attacking}", "PLAYER")
    except:
        player_attacking = False
        debug_print("Player object not found", "WARNING")
    
    # DETECT WHEN SPRAY IS DEPLETED
    if owner["spray_was_available"] and not spray_available:
        debug_print("SPRAY DEPLETED! Stopping emission and notifying", "DEPLETED")
        owner["spray_emitting"] = False
        owner["spray_delay_timer"] = 0.0
        owner["time_since_last_emission"] = 0.0
        player_attacking = False  # Force deactivation
    
    # Save current state for comparison next frame
    owner["spray_was_available"] = spray_available
    
    # Check if spray is available BEFORE delay
    if not spray_available:
        if owner["spray_emitting"]:
            debug_print("Spray depleted. Emission stopped.", "DEPLETED")
        owner["spray_emitting"] = False
        owner["spray_delay_timer"] = 0.0
        owner["time_since_last_emission"] = 0.0
        player_attacking = False  # Force deactivation
        return  # Exit early if no spray
    
    # Handle activation delay
    handle_activation_delay(owner, player_attacking)
    
    # Calculate particles to emit (before consumption)
    if owner["spray_emitting"]:
        # Calculate how many particles to emit this frame
        time_per_particle = 1.0 / owner["spray_particles_per_second"]
        owner["time_since_last_emission"] += delta_time
        
        particles_to_emit = 0
        while owner["time_since_last_emission"] >= time_per_particle:
            particles_to_emit += 1
            owner["time_since_last_emission"] -= time_per_particle
        
        # Check if enough spray for all particles
        total_consumption_needed = particles_to_emit * owner["spray_consumption_per_particle"]
        
        if game and not can_consume_spray(total_consumption_needed):
            # Adjust particles based on available spray
            spray_available_amount = game.state.spray_total
            particles_to_emit = int(spray_available_amount / owner["spray_consumption_per_particle"])
            
            if particles_to_emit <= 0:
                owner["spray_emitting"] = False
                debug_print("Insufficient spray to emit particles", "DEPLETED")
                return
        
        # Consume spray for all particles
        if particles_to_emit > 0:
            actual_consumption = consume_spray(particles_to_emit * owner["spray_consumption_per_particle"])
            actual_particles = int(actual_consumption / owner["spray_consumption_per_particle"])
            
            debug_print(f"Particles to emit: {actual_particles}", "EMISSION")
            
            # Emit particles (only those we can afford)
            owner["spray_emitted_this_frame"] = actual_particles
            for _ in range(actual_particles):
                emit_particle(owner, scene)

# =============================================================================
# PUBLIC FUNCTIONS
# =============================================================================
def set_spray_consumption(consumption_per_particle):
    """Change the amount of spray consumed per particle"""
    cont = logic.getCurrentController()
    owner = cont.owner
    
    if consumption_per_particle <= 0:
        debug_print("Error: Consumption per particle must be greater than 0", "ERROR")
        return False
    
    owner["spray_consumption_per_particle"] = consumption_per_particle
    debug_print(f"Consumption per particle set to: {consumption_per_particle}", "ADJUSTMENT")
    return True

def debug_info(owner):
    """Display debug information in console (independent of DEBUG_ENABLED)"""
    if owner.get("show_debug_info", False):
        game = game_access.get_game()
        if game:
            print(f"[SPRAY INFO] Spray: {game.state.spray_total:.1f}, Emitting: {owner['spray_emitting']}, Particles/frame: {owner['spray_emitted_this_frame']}, Consumption/particle: {owner['spray_consumption_per_particle']:.2f}")

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main():
    setup_spray_system()
    update_spray()
    debug_info(logic.getCurrentController().owner)

# Execute
main()