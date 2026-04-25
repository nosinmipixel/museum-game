"""
dialog_text.py

Manages dialog text display, JSON loading, placeholder resolution, and speech balloon visibility.

This script handles loading dialog data from JSON files, resolving placeholders
with game state values, displaying text in HUD fields, and controlling speech
balloon visibility based on who is speaking.

Main Features:
    1. Multi-language JSON dialog loading with caching
    2. Placeholder resolution ({player_name}, {npc1_name}, {budget}, etc.)
    3. Keypath-based dialog lookup (dialogs.npc1.greeting)
    4. HUD text field management via game_access
    5. Speech balloon visibility control (Main/L/R for neutral/player/NPC)
    6. NPC name prefix stripping from dialog text
    7. Message sensor parsing with command support
    8. Debug level control via messages

Setup:
    Connect to Logic Bricks as Python controller with module 'dialog_text.set_dialog_text'
    Requires a Message sensor named 'Message.JSON' (configurable)

Configurable Variables:
    BASE_TEXT_PATH (str): Path to JSON dialog files (default: '//Assets/Texts/')
    FALLBACK_LANG (str): Fallback language if current not available (default: 'es')
    DEFAULT_MSG_SENSOR (str): Default message sensor name (default: 'Message.JSON')
    BALLOON_MAIN_NAME (str): Main balloon object name (default: 'Balloon.Main')
    BALLOON_L_NAME (str): Left (player) balloon object name (default: 'Balloon.L')
    BALLOON_R_NAME (str): Right (NPC) balloon object name (default: 'Balloon.R')
    BALLOON_POS_VISIBLE (str): Position anchor for visible balloons (default: 'Pos.Info.Balloon')
    BALLOON_POS_HIDDEN (str): Position anchor for hidden balloons (default: 'Pos.Info.Balloon.Out')
    PLAYER_OBJ_NAME (str): Player object name (default: 'Player')

Notes:
    - Requires game_access module for state and HUD text access
    - JSON files should be named 'dialogs_{lang}.json' in BASE_TEXT_PATH
    - JSON structure requires 'names' and 'dialogs' keys
    - Supports dialog.debug, dialog.test, dialog.clear, dialog.set commands
    - Speech balloons require specific object names in the scene
    - NPC name is stored in Game.Controller's 'npc_name' property

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
__description__ = "Manages dialog text display, JSON loading, and speech balloon visibility"

# =============================================================================
# IMPORTS
# =============================================================================
import os
import json
import bge
from bge import logic
import game_access
import info_queue

# =============================================================================
# CONFIGURATION
# =============================================================================
BASE_TEXT_PATH = "//Assets/Texts/"
FALLBACK_LANG = "es"
DEFAULT_MSG_SENSOR = "Message.JSON"

# Balloon object names
BALLOON_MAIN_NAME = "Balloon.Main"
BALLOON_L_NAME    = "Balloon.L"
BALLOON_R_NAME    = "Balloon.R"
BALLOON_POS_VISIBLE = "Pos.Info.Balloon"
BALLOON_POS_HIDDEN  = "Pos.Info.Balloon.Out"
PLAYER_OBJ_NAME   = "Player"

# =============================================================================
# DEBUG / LOG
# =============================================================================
if not hasattr(logic, "_dialog_debug"):
    logic._dialog_debug = 0

def _log(level, *args):
    if getattr(logic, "_dialog_debug", 1) >= level:
        print("[dialog]", *args)

def _set_debug_level(level):
    try:
        lvl = int(level)
    except Exception:
        lvl = 1
    logic._dialog_debug = max(0, min(lvl, 3))
    _log(1, f"DEBUG level set to {logic._dialog_debug}")

# =============================================================================
# JSON LOADING / CACHE
# =============================================================================
def _get_lang():
    """Gets language using game_access"""
    try:
        state = game_access.get_state()
        if state and hasattr(state, 'language'):
            lang = state.language
            _log(2, "Current language:", lang)
            return lang
    except Exception:
        _log(1, "Could not get language; using 'es'")
    return "es"

def _abs_path(rel):
    if not rel.startswith("//"):
        rel = "//" + rel
    path = logic.expandPath(rel)
    _log(3, "expandPath:", rel, "->", path)
    return path

def _load_dialogs_json(lang):
    if not hasattr(logic, "_dialog_cache"):
        logic._dialog_cache = {}

    if lang in logic._dialog_cache:
        _log(2, f"Using cached dialog JSON for '{lang}'")
        return logic._dialog_cache[lang]

    tried = []
    for cand_lang in (lang, FALLBACK_LANG):
        fname = f"dialogs_{cand_lang}.json"
        path_rel = os.path.join(BASE_TEXT_PATH, fname)
        path = _abs_path(path_rel)
        tried.append(path)
        _log(2, f"Attempting to load: {path}")
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "names" not in data: data["names"] = {}
                if "dialogs" not in data: data["dialogs"] = {}
                logic._dialog_cache[cand_lang] = data
                _log(1, f"JSON loaded OK: {path}")
                return data
            except Exception as e:
                _log(1, f"ERROR reading JSON '{path}': {e}")
        else:
            _log(2, f"Does not exist: {path}")

    _log(1, "Could not load dialog JSON. Tried:", tried)
    logic._dialog_cache[lang] = {"names": {}, "dialogs": {}}
    return logic._dialog_cache[lang]

# =============================================================================
# PLACEHOLDER RESOLUTION
# =============================================================================
def _resolve_placeholders(text, names_map, extra=None):
    if not isinstance(text, str):
        text = str(text)

    fmt = {}
    # Build {player_name}, {npc1_name}, ...
    for key, value in names_map.items():
        fmt[f"{key}_name"] = value

    # Common game variables
    try:
        state = game_access.get_state()
        if state:
            fmt.setdefault("budget", getattr(state, "budget", ""))
            fmt.setdefault("score", getattr(state, "score", ""))
            fmt.setdefault("level", getattr(state, "current_level", ""))
            fmt.setdefault("language", getattr(state, "language", ""))
    except Exception:
        pass

    # Message extras (k=v)
    if isinstance(extra, dict):
        fmt.update(extra)

    if logic._dialog_debug >= 3:
        _log(3, "Available placeholders:", fmt)

    class _SafeDict(dict):
        def __missing__(self, k):
            return "{" + k + "}"

    out = text.format_map(_SafeDict(fmt))
    _log(2, "Resolved text:", out)
    return out

# =============================================================================
# KEYPATH LOOKUP
# =============================================================================
def _get_by_keypath(data, keypath):
    parts = keypath.split(".")
    node = data
    for p in parts:
        if isinstance(node, dict):
            if p in node:
                node = node[p]
                _log(3, f"dict['{p}'] -> type {type(node).__name__}")
            else:
                _log(1, f"Key not found in dict: '{p}' (path: {keypath})")
                return ""
        elif isinstance(node, list):
            try:
                idx = int(p)
            except ValueError:
                _log(1, f"Not a list index: '{p}' (path: {keypath})")
                return ""
            if 0 <= idx < len(node):
                node = node[idx]
                _log(3, f"list[{idx}] -> type {type(node).__name__}")
            else:
                _log(1, f"Index out of range: {idx} (len={len(node)}) (path: {keypath})")
                return ""
        else:
            _log(1, f"Unexpected type in path: {type(node).__name__} (key '{p}')")
            return ""
    return node if isinstance(node, str) else str(node)

# =============================================================================
# HUD TEXT - USING game_access
# =============================================================================
def _set_hud_field(field_name, value):
    """Sets a field in HUD using game_access"""
    try:
        game = game_access.get_game()
        if game and hasattr(game, 'hud_text'):
            hud_text = game.hud_text
            if hasattr(hud_text, field_name):
                setattr(hud_text, field_name, value)
                _log(2, f"HUDText.{field_name} <- '{value}'")
            else:
                _log(1, f"HUDText does not have field '{field_name}'")
        else:
            _log(1, "HUDText not available via game_access")
    except Exception as e:
        _log(1, f"Error setting HUD: {e}")

# =============================================================================
# VISUALS / FLAGS / MOVEMENT
# =============================================================================
def _obj_by_name(name):
    try:
        return logic.getCurrentScene().objects.get(name)
    except Exception:
        return None

def _set_visible(name, visible):
    o = _obj_by_name(name)
    if o is not None:
        try:
            o.visible = bool(visible)
        except Exception:
            pass

def _get_bool_prop(name, prop, default=False):
    o = _obj_by_name(name)
    if o is not None:
        try:
            return bool(o.get(prop, default))
        except Exception:
            pass
    return default

def _move_to_anchor(obj_name: str, anchor_name: str):
    try:
        scene = logic.getCurrentScene()
        obj   = scene.objects.get(obj_name)
        anch  = scene.objects.get(anchor_name)
        if not obj or not anch:
            return
        obj.worldPosition    = anch.worldPosition.copy()
        obj.worldOrientation = anch.worldOrientation.copy()
        obj.worldScale       = anch.worldScale.copy()
    except Exception:
        pass

def _update_balloon_visibility():
    player_talking = _get_bool_prop(PLAYER_OBJ_NAME, "player_talking", False)
    
    # Check if any NPC has npc_talking = True
    npc_talking = False
    try:
        for obj in logic.getCurrentScene().objects:
            if "npc_talking" in obj and obj.get("npc_talking", False):
                npc_talking = True
                break
    except Exception:
        pass
    
    _log(2, f"Balloon visibility - player_talking: {player_talking}, npc_talking: {npc_talking}")

    # ------------------------------------------------------------------
    # DIALOG / INFO-QUEUE SYNCHRONISATION
    # Centralized dialog blocking using info_queue.set_dialog_blocking()
    # This ensures info messages are:
    #   - Queued (not displayed) when dialog starts
    #   - Resumed when dialog ends
    #   - Cleared from HUD when dialog starts (to prevent overlap)
    # ------------------------------------------------------------------
    dialog_now = bool(game_access.get_dialog_active())
    dialog_prev = getattr(logic, "_dialog_was_active", None)

    if dialog_prev is None:
        # First call — just record current state, no edge to process
        logic._dialog_was_active = dialog_now
        # Initialize blocking state to match current dialog state
        info_queue.set_dialog_blocking(dialog_now)
    elif dialog_now != dialog_prev:
        logic._dialog_was_active = dialog_now

        if dialog_now:
            # DIALOG STARTED: Block info messages and clear HUD fields
            _log(2, "Dialog started: blocking info messages, clearing HUD")
            info_queue.set_dialog_blocking(True)

            # Clear info fields immediately to prevent text overlap
            # Use clear_field to properly reset the queue state (not just HUD)
            try:
                for f in info_queue.QUEUED_FIELDS:
                    info_queue.clear_field(f)
            except Exception as e:
                _log(1, f"Error clearing info fields: {e}")
        else:
            # DIALOG ENDED: Resume info queue processing
            _log(2, "Dialog ended: resuming info messages")
            info_queue.set_dialog_blocking(False)
    # ------------------------------------------------------------------

    if player_talking:
        _set_visible(BALLOON_MAIN_NAME, False)
        _set_visible(BALLOON_R_NAME, False)
        _set_visible(BALLOON_L_NAME, True)
        _move_to_anchor(BALLOON_L_NAME, BALLOON_POS_VISIBLE)
        _move_to_anchor(BALLOON_R_NAME, BALLOON_POS_HIDDEN)
        _log(2, "Showing Balloon.L (Player speaking)")
        
    elif npc_talking:
        _set_visible(BALLOON_MAIN_NAME, False)
        _set_visible(BALLOON_L_NAME, False)
        _set_visible(BALLOON_R_NAME, True)
        _move_to_anchor(BALLOON_R_NAME, BALLOON_POS_VISIBLE)
        _move_to_anchor(BALLOON_L_NAME, BALLOON_POS_HIDDEN)
        _log(2, "Showing Balloon.R (NPC speaking)")
        
    else:
        _set_visible(BALLOON_MAIN_NAME, True)
        _set_visible(BALLOON_L_NAME, False)
        _set_visible(BALLOON_R_NAME, False)
        _move_to_anchor(BALLOON_L_NAME, BALLOON_POS_HIDDEN)
        _move_to_anchor(BALLOON_R_NAME, BALLOON_POS_HIDDEN)
        _log(2, "Showing Balloon.Main (neutral state)")

# =============================================================================
# SPEAKER / NAME HANDLING
# =============================================================================
def _infer_speaker_from_keypath(keypath: str):
    try:
        parts = keypath.split(".")
        if len(parts) >= 3 and parts[0] == "dialogs":
            return parts[2]
    except Exception:
        pass
    return ""

def _strip_name_prefix(text: str, display_name: str) -> str:
    if not text or not display_name:
        return text or ""
    out = []
    needle = display_name + ":"
    for line in text.split("\n"):
        s = line.lstrip()
        if s.startswith(needle):
            rest = s[len(needle):]
            if rest.startswith(" "):
                rest = rest[1:]
            prefix_spaces = line[:len(line) - len(s)]
            out.append(prefix_spaces + rest)
        else:
            out.append(line)
    return "\n".join(out)

# =============================================================================
# MESSAGING / PARSING
# =============================================================================
def _get_positive_message_sensor(cont):
    s = cont.sensors.get(DEFAULT_MSG_SENSOR)
    if s and s.positive:
        return s
    for sen in cont.sensors:
        if getattr(sen, "positive", False) and sen.__class__.__name__.endswith("MessageSensor"):
            _log(2, f"Using message sensor: '{sen.name}'")
            return sen
    return None

def _parse_body(body):
    parts = [x.strip() for x in body.split("|") if x.strip() or x == ""]
    _log(2, "Message received:", parts)
    if not parts:
        return None

    cmd0 = parts[0].lower() if parts[0] else ""

    if cmd0 == "dialog.debug":
        lvl = 2
        for t in parts[1:]:
            if t.startswith("level="):
                _, v = t.split("=", 1)
                lvl = v
        _set_debug_level(lvl)
        return {"cmd": "debug"}

    if cmd0 == "dialog.test":
        key = None
        extras = {}
        for t in parts[1:]:
            if t.startswith("key="):
                _, key = t.split("=", 1)
            elif "=" in t:
                k, v = t.split("=", 1)
                extras[k] = v
        return {"cmd": "test", "key": key, "extras": extras}

    if cmd0 == "dialog.clear":
        field = None
        for t in parts[1:]:
            if t.startswith("field="):
                _, field = t.split("=", 1)
        return {"cmd": "clear", "field": field}

    if cmd0 == "dialog.set":
        field = None
        value = ""
        extras = {}
        for t in parts[1:]:
            if t.startswith("field="):
                _, field = t.split("=", 1)
            elif t.startswith("value="):
                _, value = t.split("=", 1)
            elif "=" in t:
                k, v = t.split("=", 1)
                extras[k] = v
        return {"cmd": "set_literal", "field": field, "value": value, "extras": extras}

    # normal mode: <hud_field>|<optional keypath>|k=v...
    field = parts[0]
    keypath = parts[1] if len(parts) >= 2 else ""
    extras = {}
    for t in parts[2:]:
        if "=" in t:
            k, v = t.split("=", 1)
            extras[k] = v
    return {"cmd": "set", "field": field, "key": keypath, "extras": extras}

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def set_dialog_text():
    cont = logic.getCurrentController()
    sen = _get_positive_message_sensor(cont)
    if not (sen and sen.bodies):
        _log(3, "No positive message this frame.")
        return

    body = sen.bodies[0]
    _log(2, "Body:", body)
    parsed = _parse_body(body)
    if not parsed:
        _log(1, "Empty or malformed message.")
        return

    # Clear info fields BEFORE processing any dialog message
    # This ensures no info text overlaps with dialog text
    try:
        for f in info_queue.QUEUED_FIELDS:
            info_queue._set_hud(f, "")
    except Exception:
        pass

    cmd = parsed["cmd"]

    if cmd == "debug":
        return

    if cmd == "clear":
        field = parsed.get("field")
        if not field:
            _log(1, "dialog.clear requires field=...")
            return
        _set_hud_field(field, "")
        # Clear header if it was NPC
        try:
            gc = logic.getCurrentScene().objects.get("Game.Controller")
            if gc and field == "char1_text":
                gc["npc_name"] = ""
        except Exception:
            pass
        _update_balloon_visibility()
        return

    if cmd == "set_literal":
        field = parsed.get("field")
        if field is None:
            _log(1, "dialog.set requires field=...")
            return
        value  = parsed.get("value","")
        extras = parsed.get("extras", {}) or {}

        # Allow setting header if explicitly provided
        speaker = (extras.get("speaker","") or "").lower()
        try:
            gc = logic.getCurrentScene().objects.get("Game.Controller")
            if gc:
                if speaker.startswith("npc"):
                    disp = (extras.get("name","") or "").strip()
                    gc["npc_name"] = disp
                elif field == "player_text":
                    gc["npc_name"] = ""
        except Exception:
            pass

        _set_hud_field(field, value)
        _update_balloon_visibility()
        return

    # Load JSON (with fallback) for 'test' and 'set'
    lang = _get_lang()
    data = _load_dialogs_json(lang)

    if cmd == "test":
        key = parsed.get("key", "")
        if not key:
            _log(1, "dialog.test without 'key='.")
            return
        text_raw = _get_by_keypath(data, key)
        names = data.get("names", {})
        final = _resolve_placeholders(text_raw, names, parsed.get("extras", {}))

        spid  = _infer_speaker_from_keypath(key)
        disp  = names.get(spid, "") if spid.startswith("npc") else ""
        clean = _strip_name_prefix(final, disp) if disp else final
        _log(1, f"[TEST] key='{key}' -> '{final}' | speaker='{spid}' name='{disp}' | clean='{clean}'")
        return

    if cmd == "set":
        field  = parsed.get("field", "")
        key    = parsed.get("key", "")
        extras = parsed.get("extras", {}) or {}

        # if no path or 'empty' => clear
        if not key or key.lower() == "empty":
            _set_hud_field(field, "")
            try:
                gc = logic.getCurrentScene().objects.get("Game.Controller")
                if gc and field == "char1_text":
                    gc["npc_name"] = ""
            except Exception:
                pass
            _update_balloon_visibility()
            return

        if not key.startswith("dialogs"):
            _log(1, f"key must start with 'dialogs': '{key}'")
            return

        text_raw = _get_by_keypath(data, key)
        if text_raw == "":
            _log(1, f"Key not found or empty: {key}")
            _set_hud_field(field, "")
            _update_balloon_visibility()
            return

        names = data.get("names", {})
        final = _resolve_placeholders(text_raw, names, extras)

        spid = _infer_speaker_from_keypath(key)
        try:
            gc = logic.getCurrentScene().objects.get("Game.Controller")
        except Exception:
            gc = None

        if spid.startswith("npc"):
            disp = names.get(spid, "")
            if gc is not None:
                try:
                    gc["npc_name"] = disp
                except Exception:
                    pass
            final = _strip_name_prefix(final, disp)
        else:
            if gc is not None:
                try:
                    gc["npc_name"] = ""
                except Exception:
                    pass

        _set_hud_field(field, final)
        _update_balloon_visibility()
        return

def set_idle():
    """Force neutral state at startup"""
    _update_balloon_visibility()