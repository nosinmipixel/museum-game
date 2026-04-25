"""
matrix_effect.py

Manages Matrix rain particle effect for game completion and special events.

This script handles the Matrix-style falling character effect with particle
emission, material transitions, and physics movement.

Main Features:
    1. Particle emission from a source object with configurable rate
    2. Material transition from white to green over particle lifetime
    3. Manual or Bullet physics movement for particles
    4. Automatic particle removal after lifetime expires
    5. Singleton controller for effect activation at specific positions
    6. Configurable effect duration and emission parameters

Setup:
    Connect to Logic Bricks as Python controller with module 'matrix_effect.main'
    Requires Matrix.Effect.0 and Matrix.Effect.1 particle objects in scene
    Requires Effect.White and Effect.Green materials

Configurable Variables:
    MATRIX_DEBUG_LEVEL (int): Debug level (0-3, default: 0)

Notes:
    - Effect duration defaults to 2.0 seconds when activated at position
    - Particle emission rate: 25 particles per second by default
    - Particle lifetime: 1.0 second by default
    - Material transition occurs at 30% of particle lifetime
    - Particles can use manual movement or Bullet physics
    - Singleton pattern ensures only one active effect controller

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
__description__ = "Manages Matrix rain particle effect for game completion and special events"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic
import random
from mathutils import Vector

# =============================================================================
# DEBUG CONFIGURATION
# =============================================================================
MATRIX_DEBUG_LEVEL = 0  # Increased for more information

def debug_log(level, message, particle=None):
    if MATRIX_DEBUG_LEVEL >= level:
        if particle:
            print(f"[MATRIX-DEBUG-L{level}] {particle.name}: {message}")
        else:
            print(f"[MATRIX-DEBUG-L{level}] {message}")

# =============================================================================
# MATRIX EFFECT CONTROLLER (SINGLETON)
# =============================================================================
class MatrixEffectController:
    _instance = None
    
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = MatrixEffectController()
        return cls._instance
    
    def __init__(self):
        self.owner = None
        self.initialized = False
        self.effect_active = False
        self.target_position = None
        self.effect_duration = 2.0
        self.effect_timer = 0.0
        
    def setup(self, owner):
        """Configures the Matrix particle system"""
        debug_log(1, f"Configuring MatrixEffectController with object: {owner.name}")
        self.owner = owner
        
        if "matrix_initialized" not in owner:
            owner["matrix_initialized"] = True
            owner["spray_active"] = False  # Inactive by default
            owner["matrix_velocity"] = 1.0
            owner["matrix_particles_per_second"] = 25
            owner["matrix_particle_lifetime"] = 1.0
            owner["matrix_time_since_last_emission"] = 0.0
            owner["matrix_emitting"] = False
            owner["matrix_particles"] = ["Matrix.Effect.0", "Matrix.Effect.1"]
            owner["matrix_materials"] = ["Effect.White", "Effect.Green"]
            debug_log(1, f"Matrix system initialized in {owner.name}")
        
        self.initialized = True
    
    def activate_at_position(self, position, duration=2.0):
        """Activates the effect at a specific position for a given duration - IMPROVED"""
        if not self.initialized or not self.owner:
            debug_log(1, f"Cannot activate: initialized={self.initialized}, owner={self.owner is not None}")
            return False
        
        debug_log(1, f"Activating Matrix effect at position: {position} for {duration}s")
        
        # IMPROVEMENT: Ensure object is visible and positioned correctly
        self.owner.worldPosition = position
        self.owner.setVisible(True)
        self.owner["spray_active"] = True
        self.effect_active = True
        self.effect_duration = duration
        self.effect_timer = 0.0
        
        # IMPROVEMENT: Force immediate first emission
        self.owner["matrix_time_since_last_emission"] = 1.0  # Force emission
        
        debug_log(1, f"Matrix effect ACTIVATED - Position: {position}, Duration: {duration}s")
        return True
    
    def deactivate(self):
        """Deactivates the effect - IMPROVED"""
        debug_log(1, f"Deactivating Matrix effect")
        if self.owner:
            self.owner["spray_active"] = False
            # IMPROVEMENT: Do not hide immediately, let existing particles finish
            debug_log(1, f"spray_active set to {self.owner['spray_active']}")
        self.effect_active = False
        self.effect_timer = 0.0
    
    def update(self):
        """Updates the effect timer"""
        if not self.effect_active:
            return
        
        self.effect_timer += 1.0 / logic.getLogicTicRate()
        
        if self.effect_timer >= self.effect_duration:
            debug_log(1, f"Effect time completed ({self.effect_timer:.1f}s >= {self.effect_duration}s)")
            self.deactivate()

# =============================================================================
# PARTICLE SYSTEM
# =============================================================================
def setup_matrix_effect():
    """Configures the Matrix particle system at startup"""
    cont = logic.getCurrentController()
    owner = cont.owner
    
    debug_log(1, f"Starting setup_matrix_effect for {owner.name}")
    
    # Verify we have a valid object
    if not owner:
        debug_log(1, "ERROR: No owner object")
        return
    
    # Initialize controller
    controller = MatrixEffectController.get_instance()
    controller.setup(owner)
    
    debug_log(1, f"Matrix system configured in {owner.name}")

def update_matrix_effect():
    """Updates the Matrix particle system each frame"""
    cont = logic.getCurrentController()
    owner = cont.owner
    
    # Update controller
    controller = MatrixEffectController.get_instance()
    controller.update()
    
    # Existing emission system
    if owner.get("spray_active", False) and not owner["matrix_emitting"]:
        owner["matrix_emitting"] = True
        debug_log(2, "Matrix system: Emission STARTED")
    elif not owner.get("spray_active", False) and owner["matrix_emitting"]:
        owner["matrix_emitting"] = False
        owner["matrix_time_since_last_emission"] = 0.0
        debug_log(2, "Matrix system: Emission STOPPED")
    
    if owner["matrix_emitting"]:
        emit_matrix_particles(owner, logic.getCurrentScene())
    
    update_particle_materials()
    update_particle_physics()

def emit_matrix_particles(owner, scene):
    """Emits Matrix particles when the system is active"""
    fps = logic.getLogicTicRate()
    delta_time = 1.0 / fps if fps > 0 else 0.016
    
    # Calculate how many particles to emit this frame
    time_per_particle = 1.0 / owner["matrix_particles_per_second"]
    owner["matrix_time_since_last_emission"] += delta_time
    
    particles_to_emit = 0
    while owner["matrix_time_since_last_emission"] >= time_per_particle:
        particles_to_emit += 1
        owner["matrix_time_since_last_emission"] -= time_per_particle
    
    # Emit particles
    for _ in range(particles_to_emit):
        emit_matrix_particle(owner, scene)
    
    # Emission debug
    if particles_to_emit > 0 and MATRIX_DEBUG_LEVEL >= 3:
        debug_log(3, f"Emitted {particles_to_emit} particles")

def emit_matrix_particle(owner, scene):
    """Emits a single Matrix particle"""
    # Select random particle object
    particle_name = random.choice(owner["matrix_particles"])
    
    # Get spawn point
    spawn_point = get_emission_point(owner)
    
    # Create particle
    try:
        particle_obj = scene.addObject(particle_name, owner, 0)  # Lifetime 0 = no auto-remove
        
        # Position at spawn point
        particle_obj.worldPosition = spawn_point
        
        # CORRECTED PHYSICS CONFIGURATION
        setup_particle_physics(particle_obj, owner)
        
        # Configure properties for material transition
        current_time = logic.getRealTime()
        particle_obj["matrix_birth_time"] = current_time
        particle_obj["matrix_lifetime"] = owner["matrix_particle_lifetime"]
        particle_obj["matrix_initial_velocity"] = owner["matrix_velocity"]
        particle_obj["matrix_transition_progress"] = 0.0
        particle_obj["current_material_index"] = 0
        particle_obj["matrix_should_remove"] = False
        
        debug_log(3, f"Particle created at {spawn_point}", particle_obj)
        
        # Apply initial material
        apply_material_to_particle(particle_obj, owner["matrix_materials"][0])
        
    except Exception as e:
        debug_log(1, f"Error creating particle: {e}")

def setup_particle_physics(particle, owner):
    """Forces manual movement"""
    particle["matrix_manual_movement"] = True
    particle["matrix_velocity_vector"] = Vector((
        random.uniform(-0.05, 0.05),
        random.uniform(-0.05, 0.05), 
        owner["matrix_velocity"]
    ))
    
def update_particle_physics():
    """Updates movement of all particles each frame"""
    scene = logic.getCurrentScene()
    delta_time = 1.0 / logic.getLogicTicRate() if logic.getLogicTicRate() > 0 else 0.016
    
    for obj in scene.objects:
        if "Matrix.Effect." in obj.name and "matrix_birth_time" in obj:
            update_single_particle_physics(obj, delta_time)

def update_single_particle_physics(particle, delta_time):
    """Updates physics of a single particle"""
    try:
        # OPTION 1: Manual movement for particles without Bullet physics
        if particle.get("matrix_manual_movement", False):
            velocity = particle.get("matrix_velocity_vector", Vector((0, 0, 1)))
            current_pos = particle.worldPosition
            new_pos = current_pos + velocity * delta_time
            particle.worldPosition = new_pos
            
            # Occasional position debug
            if MATRIX_DEBUG_LEVEL >= 3 and random.random() < 0.01:  # 1% probability per frame
                debug_log(3, f"Manual position: {current_pos.z:.2f} -> {new_pos.z:.2f}", particle)
        
        # OPTION 2: For particles with Bullet physics, verify they are moving
        elif particle.getPhysicsId() > 0 and MATRIX_DEBUG_LEVEL >= 3:
            current_vel = particle.getLinearVelocity()
            if random.random() < 0.005:  # 0.5% probability per frame
                debug_log(3, f"Bullet velocity: Z={current_vel[2]:.2f}", particle)
                
    except Exception as e:
        debug_log(1, f"Error in particle physics: {e}", particle)

def get_emission_point(owner):
    """Gets a random emission point"""
    try:
        scale = owner.worldScale
        pos = owner.worldPosition
        
        x = pos.x + random.uniform(-scale.x/2, scale.x/2)
        y = pos.y + random.uniform(-scale.y/2, scale.y/2)
        z = pos.z - scale.z/2  # Emit from the bottom
        
        return Vector((x, y, z))
        
    except Exception as e:
        debug_log(1, f"Error getting emission point: {e}")
        return owner.worldPosition.copy()

def apply_material_to_particle(particle, material_name):
    """Applies a material to the particle"""
    try:
        import bpy
        mat = bpy.data.materials.get(material_name)
        if not mat:
            debug_log(1, f"Material not found: {material_name}", particle)
            return False
        
        if hasattr(particle, 'blenderObject') and particle.blenderObject:
            blender_obj = particle.blenderObject
            if len(blender_obj.data.materials) == 0:
                blender_obj.data.materials.append(mat)
            else:
                blender_obj.data.materials[0] = mat
            debug_log(3, f"Material applied: {material_name}", particle)
            return True
        debug_log(1, f"Cannot access blenderObject", particle)
        return False
        
    except Exception as e:
        debug_log(1, f"ERROR applying material: {e}", particle)
        return False

def update_particle_materials():
    """Updates materials of all particles"""
    scene = logic.getCurrentScene()
    current_time = logic.getRealTime()
    
    matrix_particles = []
    for obj in scene.objects:
        if "Matrix.Effect." in obj.name and "matrix_birth_time" in obj:
            matrix_particles.append(obj)
    
    stats = {'total': len(matrix_particles), 'white': 0, 'green': 0, 'transitions': 0, 'removed': 0}
    
    for particle in matrix_particles:
        transition_occurred, should_remove = update_single_particle_material(particle, current_time)
        
        if transition_occurred:
            stats['transitions'] += 1
        
        current_index = particle.get("current_material_index", -1)
        if current_index == 0:
            stats['white'] += 1
        elif current_index == 1:
            stats['green'] += 1
        
        if should_remove:
            try:
                particle.endObject()
                stats['removed'] += 1
            except Exception as e:
                debug_log(1, f"Error removing particle: {e}", particle)
    
    # Statistics debug
    if MATRIX_DEBUG_LEVEL >= 2 and current_time % 3.0 < 0.1:
        debug_log(2, f"Particles: {stats['total']} (W:{stats['white']} G:{stats['green']}) Trans:{stats['transitions']} Rem:{stats['removed']}")

def update_single_particle_material(particle, current_time):
    """Updates material of a single particle"""
    try:
        birth_time = particle["matrix_birth_time"]
        lifetime = particle["matrix_lifetime"]
        age = current_time - birth_time
        
        if age > lifetime:
            return False, True
        
        life_progress = age / lifetime if lifetime > 0 else 0
        transition_threshold = 0.3
        
        if life_progress > transition_threshold:
            target_material_index = 1
        else:
            target_material_index = 0
        
        current_index = particle.get("current_material_index", -1)
        if current_index != target_material_index:
            material_name = logic.getCurrentController().owner["matrix_materials"][target_material_index]
            success = apply_material_to_particle(particle, material_name)
            if success:
                particle["current_material_index"] = target_material_index
                debug_log(3, f"Material transition: {current_index} -> {target_material_index}", particle)
                return True, False
        return False, False
        
    except Exception as e:
        debug_log(1, f"ERROR updating material: {e}", particle)
        return False, False

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main():
    cont = logic.getCurrentController()
    owner = cont.owner
    
    if "matrix_initialized" not in owner:
        setup_matrix_effect()
    
    update_matrix_effect()

# Execute
main()