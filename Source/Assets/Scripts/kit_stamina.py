"""
kit_stamina.py

Manages stamina recovery kit interaction for player energy restoration.

This script handles the visual effects and interaction logic for stamina kits,
showing recovery effects when the player needs stamina and restoring stamina
when the player interacts with the kit.

Main Features:
    1. Display stamina effect when player needs stamina and is in range
    2. Restore player stamina (50% of maximum) on click
    3. Show info message when stamina is already full
    4. Play sound effect on successful stamina recovery
    5. Hide effects after interaction

Setup:
    Connect to Logic Bricks as Python controller with module 'kit_stamina.main'
    Required sensors: Mouse.Over, Mouse.Click, Near (exact names in Logic Bricks)
    Required child objects: Stamina.Effect.Over, Info.Effect.Over (optional)

Configurable Variables:
    EFFECT_HIDE_POSITION (list): Position to hide effects (default: [0, -500, 0])

Notes:
    - Requires game_access module for stamina data and modification
    - Restores 50% of maximum stamina by default
    - Info message line 32 is displayed when stamina is full
    - Sound effect 'pick_up.ogg' is played on successful stamina recovery
    - Effect objects are repositioned to hide position when not active
    - Based on kit_health.py but adapted for stamina system

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
__description__ = "Manages stamina recovery kit interaction for player energy restoration"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
from bge import logic

# =============================================================================
# CONFIGURATION
# =============================================================================
EFFECT_HIDE_POSITION = [0, -500, 0]

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def main():
    controller = logic.getCurrentController()
    owner = controller.owner
    scene = logic.getCurrentScene()
    
    # Sensors (must have exactly these names in Logic Bricks)
    sensor_over = controller.sensors.get('Mouse.Over')
    sensor_click = controller.sensors.get('Mouse.Click')
    sensor_near = controller.sensors.get('Near')
    
    # Visual effect objects
    effect_over = scene.objects.get('Stamina.Effect.Over')
    info_effect = scene.objects.get('Info.Effect.Over')
    
    if not effect_over:
        return
    
    # Check if player needs stamina
    needs_stamina = _needs_stamina()
    
    # === STAMINA VISUAL EFFECT ===
    # Show effect when: mouse over + in range + needs stamina
    if sensor_over and sensor_near and sensor_over.positive and sensor_near.positive and needs_stamina:
        effect_over.worldPosition = owner.worldPosition.copy()
        effect_over.visible = True
        
        # Show info message
        owner.sendMessage(
            "add_info_text",
            "info.show|info_text|32|field=info_text|text=Full energy",
            "Game.Controller"
        )        
        
    else:
        effect_over.worldPosition = EFFECT_HIDE_POSITION
        effect_over.visible = False
    
    # === ACTION ON CLICK ===
    # All three sensors must be positive simultaneously
    if sensor_over and sensor_click and sensor_near:
        if sensor_over.positive and sensor_click.positive and sensor_near.positive:
            if needs_stamina:
                # Restore player stamina
                _restore_stamina()
                
                # Hide visual effect
                effect_over.worldPosition = EFFECT_HIDE_POSITION
                effect_over.visible = False
                
                # Play pickup sound
                bge.logic.sendMessage("sound_fx.play", "sound_fx.play|pick_up.ogg")
            
            # Hide info effect on click
            if info_effect:
                info_effect.worldPosition = EFFECT_HIDE_POSITION
                info_effect.visible = False

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================
def _needs_stamina():
    """
    Checks if player needs stamina recovery
    Returns True if current stamina < max stamina
    """
    try:
        import game_access
        stamina = game_access.get_stamina()
        max_stamina = game_access.get_max_stamina()
        return stamina < max_stamina
    except Exception as e:
        print(f"[kit_stamina] Error reading stamina: {e}")
    return False

def _restore_stamina():
    """
    Restores player stamina
    Default restores 50% of maximum or until full
    """
    try:
        import game_access
        
        current = game_access.get_stamina()
        max_val = game_access.get_max_stamina()
        
        # Restore 50% of maximum
        restore_amount = min(max_val * 0.5, max_val - current)
        
        new_stamina = game_access.modify_stamina(restore_amount)
        
        print(f"*** STAMINA RESTORED: {new_stamina:.1f}/{max_val} ***")
        return True
        
    except Exception as e:
        print(f"[kit_stamina] Error restoring stamina: {e}")
    return False