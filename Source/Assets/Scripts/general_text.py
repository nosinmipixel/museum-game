"""
general_text.py

Displays general texts from JSON and manages task list with checkboxes.

This script loads general text data from JSON files, handles task rendering
with checkboxes, and manages automatic clearing of text fields after a
configurable timeout.

Main Features:
    1. Load general texts from JSON by language (info_text, center_text, tasks_text)
    2. Render task list with checkboxes showing completion state
    3. Automatic clearing of text fields after configurable duration (5 seconds)
    4. Timer system for scheduled text clearing
    5. Support for info.show, info.clear, info.set commands
    6. Support for tasks.show, tasks.set, tasks.reset commands
    7. Integration with game_access for HUD text management

Setup:
    Connect to Logic Bricks as Python controller with module 'general_text.handle'
    Connect an Always sensor to 'general_text.update' for timer updates
    Required message sensor: 'Message.Gral.Texts'

Configurable Variables:
    BASE_TEXT_PATH (str): Path to JSON text files (default: '//Assets/Texts/')
    FALLBACK_LANG (str): Fallback language (default: 'es')
    PREFERRED_MESSAGE_SENSOR (str): Message sensor name (default: 'Message.Gral.Texts')
    TIMER_DURATION (float): Duration in seconds before auto-clearing (default: 5.0)
    AUTO_CLEAR_FIELDS (list): Fields that auto-clear (default: ['info_text', 'center_text'])
    DEBUG (bool): Enable debug logging (default: False)

Notes:
    - Requires game_access module for HUD text management
    - JSON file named 'general_text_{lang}.json' in BASE_TEXT_PATH
    - JSON structure requires info_text, center_text, tasks_text, and meta sections
    - Task state is stored in logic._tasks_state (should be moved to game.state long term)
    - Timer system requires update() function to be called each frame

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
__description__ = "Displays general texts from JSON and manages task list with checkboxes"

# =============================================================================
# IMPORTS
# =============================================================================
import os, json
import bge
from bge import logic
import game_access
import info_queue

# =============================================================================
# CONFIGURATION
# =============================================================================
BASE_TEXT_PATH = "//Assets/Texts/"
FALLBACK_LANG  = "es"
PREFERRED_MESSAGE_SENSOR = "Message.Gral.Texts"

# =============================================================================
# TIMER CONFIGURATION
# =============================================================================
TIMER_DURATION = 5.0  # seconds messages remain on screen
AUTO_CLEAR_FIELDS = ["info_text", "center_text"]  # fields that auto-clear

# =============================================================================
# DEBUG CONFIGURATION
# =============================================================================
DEBUG = False

def _log(*args):
    if DEBUG:
        print("[general]", *args)

# =============================================================================
# ADAPTED HELPER FUNCTIONS
# =============================================================================

def _get_game():
    """Gets current GameManager instance (new architecture)"""
    try:
        return game_access.get_game()
    except Exception:
        return None

def _lang():
    """Gets current language from new architecture"""
    try:
        game = _get_game()
        if game and hasattr(game.state, 'language'):
            return game.state.language
        # Fallback if something fails
        return FALLBACK_LANG
    except Exception:
        return FALLBACK_LANG

def _abs(rel):
    if not rel.startswith("//"): rel = "//" + rel
    return logic.expandPath(rel)

def _set_hud(field, text):
    """Updates HUDText fields in new architecture"""
    try:
        game = _get_game()
        if not game:
            _log("GameManager not available.")
            return
            
        hud = game.hud_text  # Access HUDText from GameManager
        
        if hasattr(hud, field):
            setattr(hud, field, text)
        else:
            _log(f"HUDText does not have field '{field}'.")
    except AttributeError:
        _log("HUDText not initialized in GameManager.")

# =============================================================================
# TIMER SYSTEM
# =============================================================================
# Timing and expiry for fields in AUTO_CLEAR_FIELDS is now delegated entirely
# to info_queue.  The helpers below are kept as thin stubs so that any
# existing callers (outside this module) continue to work without errors.
# info_queue.DEFAULT_DURATION mirrors TIMER_DURATION; change it there.

def _setup_timer(field):
    """No-op: timing is handled by info_queue.enqueue()."""
    pass

def _update_timers():
    """No-op: call info_queue.update() each frame instead."""
    pass

def _cancel_timer(field):
    """No-op: use info_queue.clear_field(field) for explicit cancellation."""
    pass

# =============================================================================
# JSON LOADING AND TASK RENDERING
# =============================================================================

def _load_json():
    lang = _lang()
    if not hasattr(logic, "_general_cache"):
        logic._general_cache = {}
    if lang in logic._general_cache:
        return logic._general_cache[lang]

    tried = []
    for cand in (lang, FALLBACK_LANG):
        fname = f"general_text_{cand}.json"
        path  = _abs(os.path.join(BASE_TEXT_PATH, fname))
        tried.append(path)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                # sane defaults
                data.setdefault("info_text", [])
                data.setdefault("center_text", [])
                data.setdefault("tasks_text", {"title":"", "items":[]})
                data.setdefault("meta", {
                    "checkbox_empty":"",
                    "checkbox_checked":"",
                    "fallback_empty":"[ ]",
                    "fallback_checked":"[x]"
                })
                logic._general_cache[cand] = data
                _log("JSON loaded:", path)
                return data
            except Exception as e:
                _log("Error reading", path, e)
    _log("Could not load general_text JSON. Tried:", tried)
    logic._general_cache[lang] = {
        "info_text": [], "center_text": [],
        "tasks_text": {"title":"", "items":[]},
        "meta": {"checkbox_empty":"", "checkbox_checked":"", "fallback_empty":"[ ]", "fallback_checked":"[x]"}
    }
    return logic._general_cache[lang]

def _glyph_supported(_s):
    # Heuristic: assume support; change if you want to test font.
    return True

def _render_tasks():
    data = _load_json()
    tasks = data["tasks_text"]
    meta  = data["meta"]
    empty = meta["checkbox_empty"] if _glyph_supported(meta["checkbox_empty"]) else meta["fallback_empty"]
    chk   = meta["checkbox_checked"] if _glyph_supported(meta["checkbox_checked"]) else meta["fallback_checked"]

    # State stored in logic._tasks_state as dict { "t1": bool, ... }
    # NOTE: Long term, this should be moved to game.state
    if not hasattr(logic, "_tasks_state"):
        logic._tasks_state = { item.get("id",""): False for item in tasks.get("items", []) }

    lines = []
    title = tasks.get("title","").strip()
    if title:
        lines.append(title)

    for it in tasks.get("items", []):
        tid   = it.get("id","")
        lab   = it.get("label","")
        text  = it.get("text","")
        if not tid:
            continue
        done  = bool(logic._tasks_state.get(tid, False))
        box   = chk if done else empty
        prefix = f"{lab}. " if lab else ""
        lines.append(f"{box} {prefix}{text}")

    return "\n".join(lines)

# =============================================================================
# COMMAND HANDLERS (MODIFIED WITH TIMERS)
# =============================================================================

def _handle_info_show(args):
    """
    info.show|<block>|<index>|field=<hudField>[|duration=<seconds>]
      block: info_text | center_text
      index: 0..n
    The message is enqueued via info_queue; it will wait if a dialog is active
    or if another message is already showing in that field.
    """
    if len(args) < 2:
        _log("Usage: info.show|<block>|<index>|field=<hudField>")
        return
    block = args[0]
    try:
        idx = int(args[1])
    except Exception:
        _log("Invalid index in info.show")
        return
    field    = "info_text"
    duration = None
    for t in args[2:]:
        if t.startswith("field="):
            _, field = t.split("=", 1)
        elif t.startswith("duration="):
            try:
                _, duration = t.split("=", 1)
                duration = float(duration)
            except Exception:
                duration = None

    data = _load_json()
    arr  = data.get(block, [])
    text = ""
    if isinstance(arr, list) and 0 <= idx < len(arr):
        text = arr[idx]
    else:
        _log(f"Block '{block}' or index {idx} invalid")

    if field in info_queue.QUEUED_FIELDS:
        info_queue.enqueue(field, text, duration)
    else:
        # Non-queued field: write directly (legacy behaviour)
        _set_hud(field, text)

def _handle_info_clear(args):
    """
    info.clear|field=info_text,center_text,tasks_text
    Flushes the queue for each listed field and clears the HUD immediately.
    """
    fields = None
    for t in args:
        if t.startswith("field="):
            _, fields = t.split("=", 1)
    if not fields:
        _log("info.clear requires field=...")
        return
    for f in [x.strip() for x in fields.split(",") if x.strip()]:
        if f in info_queue.QUEUED_FIELDS:
            info_queue.clear_field(f)
        else:
            _set_hud(f, "")

def _handle_info_set(args):
    """
    info.set|field=center_text|value=Literal text[|duration=<seconds>]
    Enqueues a literal text string (no JSON lookup required).
    """
    field    = None
    value    = ""
    duration = None
    for t in args:
        if t.startswith("field="):
            _, field = t.split("=", 1)
        elif t.startswith("value="):
            _, value = t.split("=", 1)
        elif t.startswith("duration="):
            try:
                _, duration = t.split("=", 1)
                duration = float(duration)
            except Exception:
                duration = None
    if not field:
        _log("info.set requires field=...")
        return
    if field in info_queue.QUEUED_FIELDS:
        info_queue.enqueue(field, value, duration)
    else:
        _set_hud(field, value)

def _handle_tasks_show():
    """
    tasks.show  -> renders and writes to HUDText.tasks_text
    """
    _set_hud("tasks_text", _render_tasks())

def _handle_tasks_set(args):
    """
    tasks.set|t1=1|t3=0|...
    """
    data = _load_json()
    if not hasattr(logic, "_tasks_state"):
        logic._tasks_state = { it.get("id",""): False for it in data["tasks_text"].get("items", []) }

    changed = False
    for t in args:
        if "=" in t:
            k,v = t.split("=",1)
            k = k.strip()
            if not k:
                continue
            logic._tasks_state[k] = (v.strip().lower() in ("1","true","yes","y"))
            changed = True
    if changed:
        _handle_tasks_show()

def _handle_tasks_reset():
    data = _load_json()
    logic._tasks_state = { it.get("id",""): False for it in data["tasks_text"].get("items", []) }
    _handle_tasks_show()

# =============================================================================
# TIMER UPDATE FUNCTION (CALL EACH FRAME)
# =============================================================================

def update():
    """
    Function to update the info queue. Must be called each frame.
    Connect to an Always sensor on Game.Controller.

    Delegates entirely to info_queue.update(), which handles both the
    expiry timer and the dialog-priority guard.
    """
    info_queue.update()

# =============================================================================
# ADAPTED MAIN ENTRY POINT
# =============================================================================

def handle():
    """
    Accepted messages (Body):
      - info.show|info_text|3|field=info_text
      - info.show|center_text|2|field=center_text
      - info.clear|field=info_text,center_text,tasks_text
      - info.set|field=center_text|value=Hello
      - tasks.show
      - tasks.set|t1=1|t3=1|t5=0
      - tasks.reset
    
    NOTE: Adapted to work with the new data architecture
    """
    cont = logic.getCurrentController()

    # Prioritize "Message.Gral.Texts" sensor
    msg = None
    s = cont.sensors.get(PREFERRED_MESSAGE_SENSOR)
    if s and s.positive:
        msg = s
    else:
        # fallback: sensor named "Message"
        s2 = cont.sensors.get("Message")
        if s2 and s2.positive:
            msg = s2
        else:
            # final fallback: first positive MessageSensor
            for sen in cont.sensors:
                if getattr(sen, "positive", False) and sen.__class__.__name__.endswith("MessageSensor"):
                    msg = sen
                    break

    if not (msg and msg.bodies):
        return

    body   = msg.bodies[0]
    tokens = [t.strip() for t in body.split("|") if t.strip()]
    if not tokens:
        return

    cmd = tokens[0].lower()
    args = tokens[1:]

    if cmd == "info.show":
        _handle_info_show(args); return
    if cmd == "info.clear":
        _handle_info_clear(args); return
    if cmd == "info.set":
        _handle_info_set(args); return
    if cmd == "tasks.show":
        _handle_tasks_show(); return
    if cmd == "tasks.set":
        _handle_tasks_set(args); return
    if cmd == "tasks.reset":
        _handle_tasks_reset(); return

    _log("Unknown command:", cmd)