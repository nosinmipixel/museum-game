"""
quiz_module.py

Module for handling QUIZ functionality in game

This module manages quiz interactions including question display, answer handling,
sound feedback, background music, and HUD updates for both normal and restoration quizzes.

Main Features:
    1. Loads quiz data from JSON files with language support
    2. Displays questions and multiple-choice options on HUD
    3. Handles answer selection and provides visual/audio feedback
    4. Supports restoration quiz mode with special formatting
    5. Manages background music context switching for quizzes
    6. Synchronizes quiz statistics with game state

Setup:
    Connect in Logic Bricks as Python controller/module 'quiz_module.handle'
    Send messages to module with format: "quiz.show|quiz_id|question_text=HUD_field|options_text=HUD_field"

Configurable Variables:
    BASE_TEXT_PATH (str): Path to text files directory (default: '//Assets/Texts/')
    FALLBACK_LANG (str): Default language if selected not available (default: 'es')
    SOUND_SUCCESS (str): Filename for correct answer sound (default: 'quiz_success.ogg')
    SOUND_WRONG (str): Filename for incorrect answer sound (default: 'quiz_wrong.ogg')

Notes:
    - Requires game_access module for state and HUD management
    - Requires sound_background module for background music control
    - Quiz JSON files should follow format: quiz_{lang}.json
    - General text JSON file should be named: general_text_{lang}.json

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
__description__ = "Quiz module with sound support, music context switching, and restoration mode"

# =============================================================================
# IMPORTS AND INITIALIZATION
# =============================================================================
import os, json
import bge
from bge import logic
import game_access

BASE_TEXT_PATH = "//Assets/Texts/"
FALLBACK_LANG  = "es"

# Sound configuration for result feedback (filenames only)
SOUND_SUCCESS = "quiz_success.ogg"
SOUND_WRONG = "quiz_wrong.ogg"

# Global injection for external access
logic.globalDict["quiz_module"] = globals() 

# =============================================================================
# BASIC UTILITY FUNCTIONS
# =============================================================================
def _lang():
    """Get current language using game_access"""
    try:
        state = game_access.get_state()
        if state and hasattr(state, 'language'):
            return state.language
    except Exception:
        pass
    return "es"

def _abs(rel):
    if not rel.startswith("//"): rel = "//" + rel
    return logic.expandPath(rel)

def _log(*args):
    print("[quiz]", *args)

def _set_hud(field, text):
    """Set text on HUD using game_access"""
    try:
        game = game_access.get_game()
        if game and hasattr(game, 'hud_text'):
            hud = game.hud_text
            if hasattr(hud, field):
                setattr(hud, field, text)
            else:
                _log(f"HUDText does not have field '{field}'")
        else:
            _log("HUDText not available through game_access")
    except Exception as e:
        _log(f"Error setting HUD: {e}")

def _play_result_sound(is_correct):
    """Play success or failure sound using centralized sound system"""
    try:
        sound_name = SOUND_SUCCESS if is_correct else SOUND_WRONG
        
        # Send message to centralized sound system
        # Format: sound_fx.play|filename.ogg|volume=0.7
        bge.logic.sendMessage(
            "sound_fx.play",
            f"sound_fx.play|{sound_name}|volume=0.7"
        )
        _log(f"Result sound requested: {sound_name}")
    except Exception as e:
        _log(f"Error requesting result sound: {e}")

# =============================================================================
# BACKGROUND MUSIC MANAGEMENT
# =============================================================================
def _push_quiz_music():
    """Activate background music for QUIZ mode (both normal and restoration)"""
    try:
        import sound_background
        success = sound_background.push_background_context("quiz")
        if success:
            _log("Quiz music activated")
        return success
    except Exception as e:
        _log(f"Error activating quiz music: {e}")
        return False

def _pop_quiz_music():
    """Restore previous background music"""
    try:
        import sound_background
        success = sound_background.pop_background_context()
        if success:
            _log("Music restored")
        return success
    except Exception as e:
        _log(f"Error restoring music: {e}")
        return False

def _is_quiz_field(field_name):
    """Determine if HUD field is related to QUIZ functionality"""
    quiz_fields = ["quiz_text", "restor_text", "options_text", "question_text", "center_text"]
    return field_name in quiz_fields

# =============================================================================
# JSON LOADING FUNCTIONS
# =============================================================================
def _load_quiz_json(lang):
    if not hasattr(logic, "_quiz_cache"):
        logic._quiz_cache = {}
    if lang in logic._quiz_cache:
        return logic._quiz_cache[lang]

    tried = []
    for cand in (lang, FALLBACK_LANG):
        fname = f"quiz_{cand}.json"
        path  = _abs(os.path.join(BASE_TEXT_PATH, fname))
        tried.append(path)
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "quizzes" not in data: data["quizzes"] = {}
                if "meta" not in data: data["meta"] = {"icon_ok":"?","icon_ko":":("}
                logic._quiz_cache[cand] = data
                _log("JSON loaded:", path)
                return data
            except Exception as e:
                _log("Error reading", path, e)
    _log("Could not load quiz JSON. Attempted:", tried)
    logic._quiz_cache[lang] = {"quizzes":{}, "meta":{"icon_ok":"?","icon_ko":":("}}
    return logic._quiz_cache[lang]

def _load_general_text_json():
    """Load //Assets/Texts/general_text_<lang>.json to get center_text[2]/[3]"""
    try:
        lang = _lang()
        tried = []
        for cand in (lang, FALLBACK_LANG):
            path = _abs(f"{BASE_TEXT_PATH}general_text_{cand}.json")
            tried.append(path)
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
        _log("Could not load general_text JSON. Attempted:", tried)
    except Exception as e:
        _log("Failed to load general_text JSON:", e)
    # Minimal fallback:
    return {"center_text": ["", "", "? Correct!", ":("]}

# =============================================================================
# QUIZ CORE FUNCTIONS
# =============================================================================
def _fmt_options(options, show_icons=False, chosen_idx=-1, icon_ok="?", icon_ko=":(", is_restoration=False):
    """
    Format quiz options.
    is_restoration: If True, use '|||' separator between answers
    """
    lines = []
    if not show_icons:
        for opt in options:
            lines.append(opt["label"])
    else:
        for i, opt in enumerate(options):
            if i == chosen_idx:
                mark = icon_ok if opt.get("correct", False) else icon_ko
                lines.append(f"{opt['label']} {mark}")
            else:
                lines.append(opt["label"])
    
    # For restoration quizzes, use special separator
    if is_restoration:
        return "|||".join(lines)
    else:
        return "\n".join(lines)

def _get_quiz(data, qid):
    q = data["quizzes"].get(qid)
    if not q:
        _log(f"Question '{qid}' not found in JSON.")
        _log(f"   Available quizzes: {list(data['quizzes'].keys())[:10]}...")
        # Force reload
        force_reload_quiz()
        # Search again
        data = _load_quiz_json(_lang())
        q = data["quizzes"].get(qid)
        if not q:
            _log(f"Question '{qid}' not found even after reload.")
            return None
    return q

def _handle_show(args, options_field_default="quiz_text"):
    lang = _lang()
    data = _load_quiz_json(lang)
    qid = None
    q_field = None
    o_field = options_field_default
    r_field = None
    
    # Detect if this is a restoration quiz
    is_restoration = (o_field == "restor_text")
    
    # Activate background music for ALL quizzes (normal and restoration)
    _push_quiz_music()
    
    for tok in args:
        if "=" in tok:
            k, v = tok.split("=", 1)
            if k == "question_text": 
                q_field = v
            elif k == "options_text": 
                o_field = v
                is_restoration = (v == "restor_text")
            elif k == "result_text": r_field = v
        else:
            if qid is None:
                qid = tok
    
    if not qid:
        _log("Missing qid in show.")
        return
    
    if r_field:
        _set_hud(r_field, "")
    else:
        _set_hud("center_text", "")
    
    q = _get_quiz(data, qid)
    if not q: return
    
    # Use the new is_restoration parameter
    opts_text = _fmt_options(q["options"], show_icons=False, is_restoration=is_restoration)
    
    # For restoration: Do NOT show question here, it's already in the upper dialog
    # Only show options
    if q_field and not is_restoration:
        num = q.get("number", "")
        prefix = f"({num}) " if num else ""
        _set_hud(q_field, f"{prefix}{q['question']}")
    elif is_restoration:
        _log(f"Restoration: Question shown in upper dialog, not in {q_field}")
    
    _set_hud(o_field, opts_text)

def _handle_answer(args, options_field_default="quiz_text"):
    lang = _lang()
    data = _load_quiz_json(lang)
    qid = None
    choice = None
    q_field = None
    o_field = options_field_default
    r_field = "center_text"
    
    # Detect if this is a restoration quiz
    is_restoration = (o_field == "restor_text")
    
    for tok in args:
        if "=" in tok:
            k, v = tok.split("=", 1)
            if k == "choice": choice = int(v)
            elif k == "question_text": q_field = v
            elif k == "options_text": 
                o_field = v
                is_restoration = (v == "restor_text")
            elif k == "result_text": r_field = v
        else:
            if qid is None:
                qid = tok
    
    if not qid or choice not in (1, 2, 3):
        _log("Invalid parameters in answer.")
        return
    
    q = _get_quiz(data, qid)
    if not q: return
    
    idx = choice - 1
    is_correct = False
    try:
        is_correct = bool(q["options"][idx].get("correct", False))
    except Exception:
        pass
    
    meta = data.get("meta", {})
    
    # Use the new is_restoration parameter
    opts_text = _fmt_options(
        q["options"], 
        show_icons=True, 
        chosen_idx=idx,
        icon_ok=meta.get("icon_ok", "?"), 
        icon_ko=meta.get("icon_ko", ":("),
        is_restoration=is_restoration
    )
    
    if q_field:
        num = q.get("number", "")
        prefix = f"({num}) " if num else ""
        _set_hud(q_field, f"{prefix}{q['question']}")
    
    _set_hud(o_field, opts_text)
    
    gen = _load_general_text_json()
    ct = gen.get("center_text", [])
    txt_ok = ct[2] if len(ct) > 2 else "? Correct!"
    txt_ko = ct[3] if len(ct) > 3 else ":("
    _set_hud(r_field, txt_ok if is_correct else txt_ko)

# =============================================================================
# 3D BUTTON HANDLER
# =============================================================================
def handle_quiz_choice_by_id(choice):
    """
    Called from quiz_button_logic.py or quiz_button_restoration.py when a button is clicked.
    CORRECTED VERSION: Only sets basic properties for NPC11, does not process result
    """
    _log(f"Answer received via click: {choice}")
    
    # 1. Find the NPC object that owns the Quiz
    active_quiz_owner = None
    quiz_id_active = None
    quiz_options_field = "quiz_text"
    
    for obj in logic.getCurrentScene().objects:
        if obj.get("quiz_on", False):
            active_quiz_owner = obj
            quiz_id_active = obj.get("what_quiz", None)
            # Detection for restoration (NPC11)
            is_restoration = (obj.get("npc_id", 0) == 11)
            quiz_options_field = "restor_text" if is_restoration else "quiz_text"
            _log(f"NPC with active QUIZ found: {obj.name} (NPC{obj.get('npc_id', '?')})")
            break
    
    if not active_quiz_owner or not quiz_id_active:
        _log(f"No NPC with active QUIZ found")
        return
    
    # 2. Determine if this is a restoration quiz (NPC11)
    is_restoration = (active_quiz_owner.get("npc_id", 0) == 11)
    
    # 3. Process visual response
    args = [
        quiz_id_active,
        f"choice={choice}",
        f"options_text={quiz_options_field}",
        "result_text=center_text" 
    ]
    
    if is_restoration:
        _handle_answer(args, options_field_default="restor_text")
    else:
        _handle_answer(args, options_field_default=quiz_options_field)

    # 4. Determine if the answer is correct
    is_correct = False
    try:
        lang = _lang()
        data = _load_quiz_json(lang)
        q = _get_quiz(data, quiz_id_active)
        if q:
            idx = choice - 1
            is_correct = bool(q["options"][idx].get("correct", False))
    except Exception:
        pass
    
    # 5. Play result sound using centralized system
    _play_result_sound(is_correct)

    # 6. CRITICAL: For restoration (NPC11), DO NOT set properties here
    #    Because quiz_button_restoration.py already does it correctly
    if active_quiz_owner:
        npc_id = active_quiz_owner.get("npc_id", 0)
        
        if npc_id == 11:
            # This is NPC11 (restoration) - DO NOT TOUCH properties
            _log(f"NPC11 detected - properties handled by quiz_button_restoration.py")
        else:
            # Normal NPC (quiz) - set properties normally
            try:
                active_quiz_owner["quiz_reply"] = True       
                active_quiz_owner["quiz_on"] = False          
                active_quiz_owner["quiz_success"] = is_correct 
                
                _log(f"Quiz properties updated in {active_quiz_owner.name}")
                
            except Exception as e:
                _log(f"Error updating properties: {e}")

    # 7. Update game statistics (only for normal quizzes, not restoration)
    if is_correct and not is_restoration:
        try:
            state = game_access.get_state()
            if state:
                # Increment correct quiz counter
                state.task_quiz_total = getattr(state, 'task_quiz_total', 0) + 1
                _log(f"Quiz correct. Total: {state.task_quiz_total}")
                
                # Check if 70% (7 out of 10) is reached
                if state.task_quiz_total >= 7:
                    # Mark QUIZ task as completed (task_quiz = True)
                    state.task_quiz = True
                    _log(f"QUIZ task completed (>=7/10) - task_quiz=True")
                
                # Synchronize with Game.Controller
                try:
                    gc = logic.getCurrentScene().objects.get("Game.Controller")
                    if gc:
                        gc['task_quiz_total'] = state.task_quiz_total
                        gc['task_quiz'] = state.task_quiz
                        # Keep quiz_active as True
                        gc['quiz_active'] = True
                        _log(f"Synchronized: task_quiz_total={state.task_quiz_total}, task_quiz={state.task_quiz}")
                except Exception as e:
                    _log(f"Error synchronizing with Game.Controller: {e}")
                    
        except Exception as e:
            _log(f"Error updating statistics: {e}")

# =============================================================================
# RELOAD AND VERIFICATION FUNCTIONS
# =============================================================================
def force_reload_quiz(lang=None):
    """Force reload of quiz JSON, clearing cache"""
    if hasattr(logic, "_quiz_cache"):
        if lang:
            if lang in logic._quiz_cache:
                del logic._quiz_cache[lang]
        else:
            logic._quiz_cache.clear()
    
    _log(f"Quiz cache cleared, forcing reload")
    return _load_quiz_json(_lang() if not lang else lang)

def verify_quiz_structure(qid):
    """Verify that the quiz structure is consistent"""
    lang = _lang()
    data = _load_quiz_json(lang)
    q = data["quizzes"].get(qid)
    
    if not q:
        _log(f"Quiz '{qid}' not found")
        return False
    
    options = q.get("options", [])
    if len(options) != 3:
        _log(f"Quiz '{qid}' has {len(options)} options (should be 3)")
        return False
    
    correct_count = sum(1 for opt in options if opt.get("correct", False))
    if correct_count != 1:
        _log(f"Quiz '{qid}' has {correct_count} correct answers (should be 1)")
        return False
    
    # Find which option is correct
    for i, opt in enumerate(options):
        if opt.get("correct", False):
            _log(f"Quiz '{qid}': Correct option is {i+1}")
            _log(f"   Text: {opt.get('label', 'No text')}")
            break
    
    return True

# =============================================================================
# MAIN HANDLER FUNCTION
# =============================================================================
def handle():
    cont = logic.getCurrentController()
    msg = None
    s = cont.sensors.get("Message")
    if s and s.positive:
        msg = s
    else:
        for sen in cont.sensors:
            if getattr(sen, "positive", False) and sen.__class__.__name__.endswith("MessageSensor"):
                msg = sen
                break
    if not (msg and msg.bodies):
        return

    body   = msg.bodies[0]
    tokens = [t.strip() for t in body.split("|") if t.strip() or t == ""]
    if not tokens:
        return

    cmd = tokens[0].lower()

    # --- Utilities: clear/set (multi-field) ---
    if cmd == "quiz.clear":
        fields = None
        for t in tokens[1:]:
            if t.startswith("field="):
                _, fields = t.split("=",1)
        if not fields:
            _log("quiz.clear requires field=...")
            return
        
        # Restore previous music when clearing QUIZ
        fields_list = [f.strip() for f in fields.split(",") if f.strip()]
        
        # If any quiz field is being cleared, restore music
        if any(_is_quiz_field(field) for field in fields_list):
            _pop_quiz_music()
        
        for f in fields_list:
            _set_hud(f, "")
        return

    if cmd == "quiz.set":
        field = None
        value = ""
        for t in tokens[1:]:
            if t.startswith("field="):
                _, field = t.split("=",1)
            elif t.startswith("value="):
                _, value = t.split("=",1)
        if not field:
            _log("quiz.set requires field=...")
            return
        _set_hud(field, value)
        return

    # --- Core commands ---
    if cmd == "quiz.show":
        _handle_show(tokens[1:])
        return

    if cmd == "quiz.answer":
        _handle_answer(tokens[1:])
        return

    # --- Restoration commands ---
    if cmd == "restor.show":
        _log(f"Restoration show command received: {tokens}")
        _handle_show(tokens[1:], options_field_default="restor_text")
        return

    if cmd == "restor.answer":
        _log(f"Restoration answer command received: {tokens}")
        _handle_answer(tokens[1:], options_field_default="restor_text")
        return

    # --- Shortcut: "<hudField>|<qid>|..." and reset with 'empty' ---
    options_field = tokens[0]

    if len(tokens) >= 2 and tokens[1].lower() == "empty":
        # Restore previous music when emptying QUIZ
        if _is_quiz_field(options_field):
            _pop_quiz_music()
        
        _set_hud(options_field, "")
        _set_hud("center_text", "")
        return

    if len(tokens) >= 2:
        qid  = tokens[1]
        rest = tokens[2:] if len(tokens) > 2 else []
        has_options = any(t.startswith("options_text=") for t in rest)
        args = [qid] + (rest if has_options else rest + [f"options_text={options_field}"])
        _handle_show(args, options_field_default=options_field)
    else:
        _log("Invalid shortcut. Expected '<hudField>|<qid>|...' or '<hudField>|empty'.")