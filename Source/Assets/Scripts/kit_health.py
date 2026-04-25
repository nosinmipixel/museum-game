"""
kit_health.py

Manages health kit interaction for player healing and information display.

This script handles the visual effects and interaction logic for health kits,
showing healing effects when the player needs health and information effects
when the player is already at full health.

Main Features:
    1. Display healing effect when player needs health and is in range
    2. Display info effect when player has full health (no healing needed)
    3. Heal player to full health on click when health is missing
    4. Show warning message when clicking on health kit at full health
    5. Play sound effect on successful healing
    6. Hide effects after interaction

Setup:
    Connect to Logic Bricks as Python controller with module 'kit_health.main'
    Required sensors: Mouse.Over, Mouse.Click, Near
    Required child objects: Health.Effect.Over, Info.Effect.Over (optional)

Configurable Variables:
    EFFECT_HIDE_POSITION (list): Position to hide effects (default: [0, -500, 0])

Notes:
    - Requires game_access module for player health data
    - Health kit only heals when player health < max_health
    - Info message line 30 is displayed when player is at full health
    - Sound effect 'pick_up.ogg' is played on successful healing
    - Effect objects are repositioned to hide position when not active

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
__description__ = "Manages health kit interaction for player healing and information display"

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

    sensor_over  = controller.sensors['Mouse.Over']
    sensor_click = controller.sensors['Mouse.Click']
    sensor_near  = controller.sensors['Near']

    effect_health = scene.objects.get('Health.Effect.Over')
    effect_info   = scene.objects.get('Info.Effect.Over')

    # Safety: at least one must exist to continue
    if not effect_health and not effect_info:
        return

    needs_healing = _needs_healing()
    is_in_range   = sensor_over.positive and sensor_near.positive

    # ------------------------------------------------------------------ #
    # Health effect: visible ONLY if needs healing and in range
    # ------------------------------------------------------------------ #
    if effect_health:
        if is_in_range and needs_healing:
            effect_health.worldPosition = owner.worldPosition.copy()
            effect_health.visible = True
        else:
            effect_health.worldPosition = EFFECT_HIDE_POSITION
            effect_health.visible = False

    # ------------------------------------------------------------------ #
    # Info effect: visible ONLY if DOES NOT need healing and in range
    # (full health -> kit only informs, does not heal)
    # ------------------------------------------------------------------ #
    if effect_info:
        if is_in_range and not needs_healing:          # condition added
            effect_info.worldPosition = owner.worldPosition.copy()
            effect_info.visible = True
        else:
            effect_info.worldPosition = EFFECT_HIDE_POSITION
            effect_info.visible = False

    # ------------------------------------------------------------------ #
    # Action on click
    # ------------------------------------------------------------------ #
    if is_in_range and sensor_click.positive:
        if needs_healing:
            _heal_player()
            bge.logic.sendMessage("sound_fx.play", "sound_fx.play|pick_up.ogg")

            # Hide health effect after healing
            if effect_health:
                effect_health.worldPosition = EFFECT_HIDE_POSITION
                effect_health.visible = False
        else:
            # Full health: show warning
            owner.sendMessage(
                "add_info_text",
                "info.show|info_text|30|field=info_text",
                "Game.Controller"
            )

            # Hide info effect after click
            if effect_info:
                effect_info.worldPosition = EFFECT_HIDE_POSITION
                effect_info.visible = False

# ------------------------------------------------------------------ #
# Helper functions
# ------------------------------------------------------------------ #
def _needs_healing():
    try:
        import game_access
        player = game_access.get_player()
        if player:
            return player.health < player.max_health
    except Exception as e:
        print(f"[kit] Error reading health: {e}")
    return False

def _heal_player():
    try:
        import game_access
        player = game_access.get_player()
        if player:
            player.health    = player.max_health
            player.is_alive  = True
            print(f"*** PLAYER HEALED ({player.health}/{player.max_health}) ***")
            return True
    except Exception as e:
        print(f"[kit] Error healing: {e}")
    return False