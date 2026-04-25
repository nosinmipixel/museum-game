"""
info_queue.py

Priority queue for HUD info messages with dialog-blocking support.

Manages a FIFO queue of info messages for fields like 'info_text' and
'center_text'. Messages are held while a dialog is active (dialog_active=True)
and are displayed sequentially, never overlapping.

Main Features:
    1. FIFO queue per HUD field — new messages wait until the current one expires
    2. Dialog priority — info messages are suppressed (queued) while dialog_active
    3. Transparent integration — general_text calls enqueue() instead of _set_hud()
    4. update() drives the queue each frame (connect to Always sensor)
    5. clear_field() flushes queue and clears HUD for explicit clears
    6. Optional per-message duration override (falls back to DEFAULT_DURATION)

Setup:
    Import and call enqueue() from general_text instead of writing to HUD directly.
    Connect update() to an Always sensor on Game.Controller (same as general_text.update).

Public API:
    enqueue(field, text, duration=None)   -- add message to queue
    clear_field(field)                    -- flush queue + clear HUD immediately
    update()                              -- tick; call every frame
    is_dialog_active()                    -- True while dialog blocks info

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
__description__ = "Priority queue for HUD info messages with dialog-blocking support"

# =============================================================================
# IMPORTS
# =============================================================================
from bge import logic
import game_access

# =============================================================================
# CONFIGURATION
# =============================================================================
DEFAULT_DURATION = 5.0      # seconds a message stays on screen if no override
QUEUED_FIELDS    = ["info_text", "center_text"]   # fields managed by this queue
DEBUG            = False

# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _log(*args):
    if DEBUG:
        print("[info_queue]", *args)

def _set_hud(field, text):
    """Write directly to HUDText via game_access."""
    try:
        game = game_access.get_game()
        if game and hasattr(game, "hud_text"):
            hud = game.hud_text
            if hasattr(hud, field):
                setattr(hud, field, text)
            else:
                _log(f"HUDText has no field '{field}'")
        else:
            _log("HUDText not available")
    except Exception as e:
        _log("_set_hud error:", e)

def _get_state_store():
    """
    Returns a dict stored in logic that holds per-field queue state.
    Structure:
        logic._iq[field] = {
            "queue":        [(text, duration), ...],  # FIFO
            "current_text": str,
            "expire_time":  float or None,
            "active":       bool,
        }
    """
    if not hasattr(logic, "_iq"):
        logic._iq = {}
    return logic._iq

def _ensure_field(field):
    store = _get_state_store()
    if field not in store:
        store[field] = {
            "queue":        [],
            "current_text": "",
            "expire_time":  None,
            "active":       False,
        }
    return store[field]

# =============================================================================
# DIALOG GUARD - CENTRALIZED DIALOG BLOCKING
# =============================================================================

# Module-level dialog blocking state (more reliable than querying game_access)
_dialog_blocking = False
_last_dialog_state = False

def set_dialog_blocking(blocking: bool):
    """
    Centralized control for dialog blocking state.
    Call this from dialog_text.py when dialog starts/ends.

    When blocking=True:
        - Current info messages are paused (preserved)
        - New messages are queued but not displayed
    When blocking=False:
        - Queued messages resume display
    """
    global _dialog_blocking, _last_dialog_state

    was_blocking = _dialog_blocking
    _dialog_blocking = bool(blocking)

    _log(f"Dialog blocking: {was_blocking} -> {_dialog_blocking}")

    # On transition from blocking to not blocking, resume queue processing
    if was_blocking and not _dialog_blocking:
        _log("Dialog ended - resuming info queue processing")
        for field in QUEUED_FIELDS:
            _try_pop(field)

def is_dialog_active():
    """
    Returns True if a character dialog is currently running.
    Uses module-level state for reliability (avoids race conditions).
    Falls back to game_access if module state not set.
    """
    global _dialog_blocking

    # Primary: use module-level state (most reliable)
    if _dialog_blocking:
        return True

    # Fallback: query game_access (for compatibility)
    try:
        return bool(game_access.get_dialog_active())
    except Exception:
        return False

def pause_current_messages():
    """
    Pause all currently active info messages.
    Called when dialog starts - preserves message state.
    """
    store = _get_state_store()
    for field in QUEUED_FIELDS:
        slot = store.get(field)
        if slot and slot.get("active"):
            # Mark as paused (don't clear HUD yet)
            slot["_paused_by_dialog"] = True
            _log(f"Paused message in '{field}': '{slot['current_text'][:40]}'")

def resume_paused_messages():
    """
    Resume paused messages after dialog ends.
    Messages continue from where they left off.
    """
    store = _get_state_store()
    for field in QUEUED_FIELDS:
        slot = store.get(field)
        if slot and slot.get("_paused_by_dialog"):
            slot["_paused_by_dialog"] = False
            _log(f"Resumed message in '{field}': '{slot['current_text'][:40]}'")

# =============================================================================
# PUBLIC API
# =============================================================================

def enqueue(field, text, duration=None):
    """
    Add an info message to the queue for *field*.

    If the field has nothing showing and no dialog is active, the message
    is displayed immediately. Otherwise it is appended to the queue and
    will appear as soon as the slot is free and dialog is over.

    Deduplication: Duplicate messages (same text as last queued or currently
    showing) are silently ignored to prevent spam.

    Args:
        field (str):    HUDText field name (e.g. 'info_text', 'center_text').
        text  (str):    Text to display.
        duration (float|None): Override display duration; uses DEFAULT_DURATION if None.
    """
    if not text:
        return

    dur = duration if (duration is not None and duration > 0) else DEFAULT_DURATION
    slot = _ensure_field(field)

    # DEDUPLICATION: Prevent duplicate messages
    # Check if identical to currently showing message
    if slot["active"] and slot["current_text"] == text:
        _log(f"enqueue '{field}': DUPLICATE (currently showing) - ignored")
        return

    # Check if identical to last message in queue
    if slot["queue"]:
        last_text, _ = slot["queue"][-1]
        if last_text == text:
            _log(f"enqueue '{field}': DUPLICATE (last in queue) - ignored")
            return

    slot["queue"].append((text, dur))
    _log(f"enqueue '{field}': '{text[:40]}' ({dur}s) — queue len={len(slot['queue'])}")
    # Try to pop immediately (will no-op if something is already showing or dialog blocking)
    _try_pop(field)

def clear_field(field):
    """
    Immediately clear the HUD field and flush its entire queue.
    Equivalent to info.clear from general_text, but queue-aware.
    """
    slot = _ensure_field(field)
    slot["queue"].clear()
    slot["current_text"] = ""
    slot["expire_time"]  = None
    slot["active"]       = False
    slot["_paused_by_dialog"] = False
    _set_hud(field, "")
    _log(f"clear_field '{field}' — queue flushed")

# =============================================================================
# INTERNAL QUEUE LOGIC
# =============================================================================

def _try_pop(field):
    """
    If the field slot is free AND no dialog is blocking, pop the next
    message from the queue and push it to the HUD.
    """
    slot = _ensure_field(field)

    # Slot already occupied
    if slot["active"]:
        return

    # Dialog blocks info messages - check both module state and game_access
    if is_dialog_active():
        _log(f"_try_pop '{field}': blocked by dialog_active")
        return

    # Nothing waiting
    if not slot["queue"]:
        return

    text, dur = slot["queue"].pop(0)
    slot["current_text"] = text
    slot["expire_time"]  = logic.getRealTime() + dur
    slot["active"]       = True
    slot["_paused_by_dialog"] = False  # Reset pause flag
    _set_hud(field, text)
    _log(f"_try_pop '{field}': showing '{text[:40]}' for {dur}s "
         f"(remaining in queue: {len(slot['queue'])})")

def _tick_field(field):
    """Check expiry for one field and advance queue if expired."""
    slot = _ensure_field(field)
    if not slot["active"]:
        # Even if idle, try to pop in case dialog just ended
        _try_pop(field)
        return

    now = logic.getRealTime()
    if slot["expire_time"] is not None and now >= slot["expire_time"]:
        # Current message expired
        slot["current_text"] = ""
        slot["expire_time"]  = None
        slot["active"]       = False
        _set_hud(field, "")
        _log(f"_tick_field '{field}': message expired, clearing HUD")
        # Immediately try the next one
        _try_pop(field)

# =============================================================================
# FRAME UPDATE (call every frame via Always sensor)
# =============================================================================

def update():
    """
    Advance all managed field queues. Must be called once per frame.
    Connect to an Always sensor on Game.Controller alongside general_text.update.
    """
    for field in QUEUED_FIELDS:
        _tick_field(field)