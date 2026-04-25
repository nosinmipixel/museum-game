"""
BLF_module.py

Manages text rendering, HUD display, typewriter effects, and UI elements for UPBGE.

This module handles all on-screen text rendering using BLF, including dialog text,
HUD values, progress bars, book text, quiz displays, and matrix rain effects.
It provides dynamic positioning based on screen resolution and aspect ratio.

Main Features:
    1. Dynamic text positioning with aspect ratio compensation
    2. Typewriter text effect with sound synchronization
    3. Progress bars for health, spray, and stamina with color coding
    4. HUD value display with dynamic column layout
    5. Matrix rain visual effect integration
    6. Multi-language text wrapping with EM-based width limits
    7. Dialog system with NPC name detection and stripping
    8. Siren sound system for critical warnings

Setup:
    Connect to Logic Bricks as Python controller with module 'BLF_module.main'
    The draw_hud function is automatically registered to post_draw

Configurable Variables:
    BASE_WIDTH (int): Base width for coordinate adaptation (default: 1280)
    BASE_HEIGHT (int): Base height for coordinate adaptation (default: 720)
    TEXT_SCALES (dict): Font size scales for different text levels
    MAX_WIDTH_*_EM (float): Maximum text widths in EM units
    TYPEWRITER_CPS_DIALOG (float): Characters per second for dialog (default: 36.0)
    TYPEWRITER_CPS_INFO (float): Characters per second for info text (default: 42.0)
    PROGRESS_BARS_CONFIG (dict): Configuration for progress bars
    SIREN_SOUND (str): Sound file for warnings (default: 'warning-siren-fx.ogg')
    TYPING_SOUND (str): Sound file for typing effect (default: 'keyboard-typing.ogg')

Notes:
    - Font files required: 'MatrixSans-Regular.ttf' and 'PixelIcons-Regular.ttf' in //Fonts/
    - Requires game_access module for game state data
    - Optional: matrix_rain_screen module for Matrix effect
    - Optional: sound_fx module for sound effects
    - Progress bars blink when health or stamina is below 20%
    - Climate warning level 2 activates siren sound

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
__description__ = "Manages text rendering, HUD display, and UI elements"

# =============================================================================
# IMPORTS
# =============================================================================
import bge
import blf
import game_access
import math
from bge import logic

# =============================================================================
# CONDITIONAL IMPORT FOR MATRIX EFFECT
# =============================================================================
MATRIX_AVAILABLE = False
try:
    import matrix_rain_screen as matrix
    MATRIX_AVAILABLE = True
    print("[BLF] Matrix effect available")
except ImportError:
    print("[BLF] Matrix effect not available")
    MATRIX_AVAILABLE = False

# =============================================================================
# SCREEN GEOMETRY
# =============================================================================
# Font sizes and spacing: based on cam_h (16/9 view height)
# Positions relative to top edge: based on cam_top
# Absolute screen positions: based on screen_h
# Quizzes: adapt_pos() with aspect ratio correction formulas
# Text widths: normalized in ems for resolution consistency

BASE_WIDTH       = 1280
BASE_HEIGHT      = 720
ASPECT_RATIO_169 = 16.0 / 9.0

def get_camera_height():
    return bge.render.getWindowWidth() / ASPECT_RATIO_169

def get_camera_top():
    screen_h = bge.render.getWindowHeight()
    cam_h    = get_camera_height()
    return (screen_h + cam_h) / 2

def adapt_pos(origin_x, origin_y, base_w=BASE_WIDTH, base_h=BASE_HEIGHT):
    """
    Converts a position (x, y) designed for 16/9 base resolution
    to the current screen resolution, compensating for the vertical strip
    that Blender adds when changing aspect ratio.
    """
    screen_w = bge.render.getWindowWidth()
    screen_h = bge.render.getWindowHeight()
    
    scale_ratio = screen_w / base_w
    new_x       = origin_x * scale_ratio
    
    diff_height = screen_h - (base_h * scale_ratio)
    strip_inf   = diff_height / 2
    new_y       = origin_y * scale_ratio + strip_inf
    
    return new_x, new_y

def adapt_size(base_size, base_w=BASE_WIDTH):
    """
    Scales a pixel value (e.g., a fixed offset) using the same
    scale_ratio used by adapt_pos().
    """
    screen_w = bge.render.getWindowWidth()
    return base_size * (screen_w / base_w)

# =============================================================================
# NORMALIZED MAX TEXT WIDTHS (in ems)
# =============================================================================
MAX_WIDTH_INFO_EM        = 28.8
MAX_WIDTH_CENTER_EM      = 28.4
MAX_WIDTH_DESC_EM        = 48.0
MAX_WIDTH_BOOK_EM        = 46.1
MAX_WIDTH_EXHIBITION_EM  = 25.6
MAX_WIDTH_QUIZ_EM        = 28.8
MAX_WIDTH_RESTOR_EM      = 23.0

# =============================================================================
# TYPOGRAPHIC SCALES
# =============================================================================
TEXT_SCALES = {
    'xxl': 0.055,
    'xl':  0.050,
    'lg':  0.035,
    'md':  0.028,
    'sm':  0.028,
    'xs':  0.022,
    'xxs': 0.018,
}

def get_text_size(level='sm', cam_h=None):
    """
    Calculates font size in pixels based on cam_h
    (16/9 view height), not physical screen height.
    """
    if cam_h is None:
        cam_h = get_camera_height()
    scale = TEXT_SCALES.get(level, TEXT_SCALES['sm'])
    return int(cam_h * scale)

# =============================================================================
# PROGRESS BARS CONFIGURATION
# =============================================================================
PROGRESS_BARS_CONFIG = {
    'start_x': 0.02,
    'start_y': 0.05,
    'icon_scale': 0.035,
    'text_scale': 0.028,
    'bar_char_scale': 0.032,
    'column_gap': 0.18,
    'bar_length': 20,
    'colors': {
        'health_high': (0.0, 1.0, 0.0, 1.0),
        'health_medium': (1.0, 1.0, 0.0, 1.0),
        'health_low': (1.0, 0.5, 0.0, 1.0),
        'health_critical': (1.0, 0.0, 0.0, 1.0),
        'spray_high': (0.0, 0.5, 1.0, 1.0),
        'spray_medium': (0.5, 0.5, 1.0, 1.0),
        'spray_low': (1.0, 0.0, 0.0, 1.0),
        'stamina_high': (1.0, 0.65, 0.0, 1.0),      # Light orange
        'stamina_medium': (1.0, 0.5, 0.0, 1.0),     # Orange
        'stamina_low': (1.0, 0.3, 0.0, 1.0),        # Dark orange
        'stamina_critical': (1.0, 0.0, 0.0, 1.0),   # Red
        'text': (1.0, 1.0, 1.0, 1.0),
        'bar_bg': (0.3, 0.3, 0.3, 1.0),
    },
    'bar_char_full': '|',
    'bar_char_empty': '.',
    'blink_interval': 0.5,
}

_progress_bars_state = {
    'prev_health': 100,
    'prev_spray': 100,
    'prev_stamina': 100,
    'blink_state': True,
    'last_blink_time': 0,
}

# =============================================================================
# SOUND SYSTEM
# =============================================================================
try:
    import sound_fx
    SOUND_SYSTEM_AVAILABLE = True
    print("[BLF] Sound system available")
except ImportError:
    SOUND_SYSTEM_AVAILABLE = False
    print("[BLF] Sound system not available")

SIREN_SOUND = "warning-siren-fx.ogg"
SIREN_VOLUME = 0.20
TYPEWRITER_CPS_DIALOG = 36.0
TYPEWRITER_CPS_INFO   = 42.0
TYPING_SOUND = "keyboard-typing.ogg"
TYPING_VOLUME = 0.35
COMPLETE_KEYS = ("SPACEKEY", "RETKEY")
NPC_NAME_COLOR = (0.914, 0.902, 0.933, 1)
NPC_NAME_SIZE_SCALE = 0.026
NPC_NAME_RIGHT_MARGIN = 0.05
NPC_NAME_OVER_DY = 1.2

# =============================================================================
# TYPEWRITER STATE
# =============================================================================
def _tw_init():
    if not hasattr(logic, "_tw"):
        logic._tw = {
            "last_t": logic.getRealTime(),
            "fields": {f: {"full": "", "idx": 0, "acc": 0.0}
                      for f in ("player_text", "char1_text", "info_text", "desc_text")}
        }

def _tw_dt():
    now = logic.getRealTime()
    dt  = now - logic._tw.get("last_t", now)
    logic._tw["last_t"] = now
    return max(0.0, min(dt, 0.25))

def _tw_reset_field(field, new_text):
    st = logic._tw["fields"][field]
    st.update(full=new_text or "", idx=0, acc=0.0)

def _tw_update_and_get(field, target_text, cps):
    st = logic._tw["fields"][field]
    if (target_text or "") != st["full"]:
        _tw_reset_field(field, target_text)
    if not st["full"]:
        st["idx"] = 0
        st["acc"] = 0.0
        return ""
    st["acc"] += _tw_dt() * cps
    step = int(st["acc"])
    if step > 0:
        st["idx"] = min(len(st["full"]), st["idx"] + step)
        st["acc"] -= step
    return st["full"][:st["idx"]]

def _tw_any_active():
    return any(st["full"] and st["idx"] < len(st["full"])
               for st in logic._tw["fields"].values())

def _tw_complete_all():
    for st in logic._tw["fields"].values():
        if st["full"]:
            st["idx"] = len(st["full"])
            st["acc"] = 0.0

# =============================================================================
# SOUND MANAGEMENT
# =============================================================================
def _typing_sound_update():
    active = _tw_any_active()
    if not active or getattr(logic, "blf_hidden", False):
        if hasattr(logic, "typing_handle") and logic.typing_handle:
            try:
                logic.typing_handle.stop()
                logic.typing_handle = None
            except:
                logic.typing_handle = None
        return
    
    if SOUND_SYSTEM_AVAILABLE and active and not getattr(logic, "blf_hidden", False):
        if not hasattr(logic, "typing_handle") or not logic.typing_handle:
            try:
                logic.typing_handle = sound_fx.play_sound_immediate(
                    TYPING_SOUND,
                    volume=TYPING_VOLUME,
                    loop=True
                )
            except Exception as e:
                print(f"[BLF] Error playing typing sound: {e}")
                logic.typing_handle = None

def _handle_complete_shortcut():
    kb, ev = logic.keyboard, bge.events
    for name in COMPLETE_KEYS:
        code = getattr(ev, name, None)
        if code:
            try:
                key_input = kb.inputs.get(code)
                if key_input and key_input.activated:
                    _tw_complete_all()
                    if hasattr(logic, "typing_handle") and logic.typing_handle:
                        try:
                            logic.typing_handle.stop()
                            logic.typing_handle = None
                        except:
                            logic.typing_handle = None
                    break
            except (AttributeError, KeyError):
                if kb.events.get(code, 0) == logic.KX_INPUT_JUST_ACTIVATED:
                    _tw_complete_all()
                    if hasattr(logic, "typing_handle") and logic.typing_handle:
                        try:
                            logic.typing_handle.stop()
                            logic.typing_handle = None
                        except:
                            logic.typing_handle = None
                    break

# =============================================================================
# BLF SETUP
# =============================================================================
font_path_text  = logic.expandPath('//Assets/Fonts/MatrixSans-Regular.ttf')
font_path_icons = logic.expandPath('//Assets/Fonts/PixelIcons-Regular.ttf')
blf_font_id_text  = blf.load(font_path_text)
blf_font_id_icons = blf.load(font_path_icons)

COLOR_WHITE     = (1, 1, 1, 1)
COLOR_SILVER    = (0.596, 0.984, 0.596, 1)
COLOR_PALEGREEN = (0.863, 0.851, 0.890, 1)
COLOR_RED       = (1, 0, 0, 1)
COLOR_GREEN     = (0, 1, 0, 1)
COLOR_ORANGE    = (1, 0.5, 0, 1)  # Orange for "improving but out of range"

def wrap_text(text, font_id, max_width_px):
    lines = []
    segs = (text or "").replace('\n', '\n').split('\n')
    for seg in segs:
        if not seg:
            lines.append("")
            continue
        cur = ""
        words = [w for w in seg.split(" ") if w]
        for w in words:
            test = cur + w + " "
            if blf.dimensions(font_id, test.strip())[0] <= max_width_px:
                cur = test
            else:
                if cur:
                    lines.append(cur.strip())
                cur = w + " "
        if cur:
            lines.append(cur.strip())
    return lines

def _strip_npc_prefix(text, npc_name):
    if not text or not npc_name:
        return text or ""
    out_lines = []
    needle = npc_name + ":"
    for line in (text or "").split("\n"):
        s = line.lstrip()
        if s.startswith(needle):
            rem = s[len(needle):]
            if rem.startswith(" "):
                rem = rem[1:]
            out_lines.append(rem)
        else:
            out_lines.append(line)
    return "\n".join(out_lines)

# =============================================================================
# HUD VALUES CONFIGURATION
# =============================================================================
HUD_VALUES_CONFIG = {
    'margin_init_x': 0.02,
    'margin_init_y': 0.10,
    'hud_icon_scale': 0.04,
    'hud_text_scale': 0.026,
    'margin_x_text': 5,
    'margin_x_column_min': 0.11,
    'margin_x_column_max': 0.18,
    'margin_y_row': 0.04,
    'num_columns': 4,
    'num_rows': 2,
    'max_total_width': 0.70,
}

def _calculate_column_widths(values_data, screen_w, screen_h, cam_h):
    config      = HUD_VALUES_CONFIG
    icon_size   = int(cam_h * config['hud_icon_scale'])
    text_size   = int(cam_h * config['hud_text_scale'])
    margin_text = config['margin_x_text']
    column_widths = [0] * config['num_columns']
    
    blf.size(blf_font_id_icons, icon_size)
    blf.size(blf_font_id_text, text_size)
    
    for row in values_data:
        for col_idx, value_info in enumerate(row):
            if col_idx >= len(column_widths):
                continue
            icon_char, text, _, _, _ = value_info
            icon_width, _ = blf.dimensions(blf_font_id_icons, icon_char)
            text_width, _ = blf.dimensions(blf_font_id_text, text)
            total_width   = icon_width + margin_text + text_width
            column_widths[col_idx] = max(column_widths[col_idx], total_width)
    
    min_width = int(screen_w * config['margin_x_column_min'])
    max_width = int(screen_w * config['margin_x_column_max'])
    for i in range(len(column_widths)):
        column_widths[i] = max(min_width, min(column_widths[i], max_width))
    
    total_width_sum   = sum(column_widths)
    max_total_allowed = int(screen_w * config['max_total_width'])
    if total_width_sum > max_total_allowed:
        scale_factor = max_total_allowed / total_width_sum
        for i in range(len(column_widths)):
            column_widths[i] = int(column_widths[i] * scale_factor)
    
    return column_widths

def _draw_hud_values(cam_h, cam_top):
    if getattr(logic, "blf_hidden", False):
        if hasattr(logic, "siren_handle") and logic.siren_handle:
            try:
                logic.siren_handle.stop()
                logic.siren_handle = None
            except:
                logic.siren_handle = None
        return
    
    screen_w = bge.render.getWindowWidth()
    screen_h = bge.render.getWindowHeight()
    scene    = logic.getCurrentScene()
    game     = game_access.get_game()
    
    if not game:
        return
    
    state = game.state
    hud   = game.hud_text
    inventoried, restored, exhibited = state.update_collection_stats()
    total_items = state.collection_items_total
    gm = scene.objects.get('Game.Controller')
    
    if not gm:
        return
    
    config      = HUD_VALUES_CONFIG
    margin_x    = int(screen_w * config['margin_init_x'])
    margin_y    = int(cam_h * config['margin_init_y'])
    icon_size   = int(cam_h * config['hud_icon_scale'])
    text_size   = int(cam_h * config['hud_text_scale'])
    row_h       = int(cam_h * config['margin_y_row'])
    margin_text = config['margin_x_text']
    
    values = [
        ('p', f"Items: {total_items}", COLOR_WHITE, COLOR_WHITE, ""),
        ('o', f"Quiz: {getattr(state, 'task_quiz_total', 0)}/10", COLOR_WHITE, COLOR_WHITE, ""),
        ('r', f"Rest: {getattr(state, 'task_restoration_total', 0)}/5", COLOR_WHITE, COLOR_WHITE, ""),
        ('S', hud.hr_mus, None, None, ""),
    ]
    
    values_row2 = [
        ('M', hud.skills_text, COLOR_WHITE, COLOR_WHITE, ""),
        ('k', f"Bugs: {getattr(state, 'bugs_total', 0)}", COLOR_WHITE, COLOR_WHITE, ""),
        ('!', f"Exhib: {exhibited}/{total_items}", COLOR_WHITE, COLOR_WHITE, ""),
        ('R', hud.temp_mus, None, None, ""),
    ]
    
    # New color and siren logic based on trend
    temp_ok = state.temp_ok if state else True
    hr_ok = state.hr_ok if state else True
    climate_warning = getattr(state, 'climate_warning_level', 0)
    
    # Determine color by warning level
    # 0 = Green (OK), 1 = Orange (improving), 2 = Red (worsening)
    if climate_warning == 0:
        dynamic_color = COLOR_GREEN
        should_play_siren = False
    elif climate_warning == 1:
        dynamic_color = COLOR_ORANGE  # Decreasing but out of range
        should_play_siren = False      # No siren when improving
    else:  # climate_warning == 2
        dynamic_color = COLOR_RED     # Increasing and out of range
        should_play_siren = True       # Siren active
    
    # Apply dynamic color to climate values
    values[3]      = (values[3][0], values[3][1], dynamic_color, dynamic_color, values[3][4])
    values_row2[3] = (values_row2[3][0], values_row2[3][1], dynamic_color, dynamic_color, values_row2[3][4])
    
    all_values    = [values, values_row2]
    column_widths = _calculate_column_widths(all_values, screen_w, screen_h, cam_h)
    
    # Siren control based on trend
    if should_play_siren and not temp_ok:
        if SOUND_SYSTEM_AVAILABLE:
            if not hasattr(logic, "siren_handle") or not logic.siren_handle:
                try:
                    logic.siren_handle = sound_fx.play_sound_immediate(
                        SIREN_SOUND,
                        volume=SIREN_VOLUME,
                        loop=True
                    )
                except:
                    logic.siren_handle = None
        else:
            if hasattr(logic, "siren_handle") and logic.siren_handle:
                try:
                    logic.siren_handle.stop()
                    logic.siren_handle = None
                except:
                    logic.siren_handle = None
    else:
        # Stop siren when it shouldn't be playing
        if hasattr(logic, "siren_handle") and logic.siren_handle:
            try:
                logic.siren_handle.stop()
                logic.siren_handle = None
            except:
                logic.siren_handle = None
    
    for row_idx in range(config['num_rows']):
        current_row = values if row_idx == 0 else values_row2
        y_pos     = cam_top - margin_y - (row_h * row_idx)
        current_x = margin_x
        
        for col_idx in range(config['num_columns']):
            if col_idx >= len(current_row):
                current_x += column_widths[col_idx]
                continue
            
            icon_char, text, icon_color, text_color, _ = current_row[col_idx]
            col_width = column_widths[col_idx]
            
            blf.size(blf_font_id_icons, icon_size)
            icon_width, _ = blf.dimensions(blf_font_id_icons, icon_char)
            
            blf.size(blf_font_id_text, text_size)
            text_width, _ = blf.dimensions(blf_font_id_text, text)
            
            total_content_width = icon_width + margin_text + text_width
            extra_space = max(0, col_width - total_content_width)
            
            icon_x = current_x + (extra_space // 2)
            blf.color(blf_font_id_icons, *icon_color)
            blf.position(blf_font_id_icons, icon_x, y_pos, 0)
            blf.draw(blf_font_id_icons, icon_char)
            
            text_x = icon_x + icon_width + margin_text
            blf.color(blf_font_id_text, *text_color)
            blf.position(blf_font_id_text, text_x, y_pos, 0)
            blf.draw(blf_font_id_text, text)
            
            current_x += col_width

# =============================================================================
# PROGRESS BARS FUNCTIONS
# =============================================================================

def _get_bar_color(value, bar_type):
    """
    Gets the bar color based on type and value
    MUST BE DEFINED BEFORE _draw_single_bar
    """
    config = PROGRESS_BARS_CONFIG
    ratio  = value / 100.0
    
    if bar_type == 'health':
        if ratio >= 0.7:
            return config['colors']['health_high']
        elif ratio >= 0.4:
            return config['colors']['health_medium']
        elif ratio >= 0.2:
            return config['colors']['health_low']
        else:
            current_time = logic.getRealTime()
            if current_time - _progress_bars_state['last_blink_time'] > config['blink_interval']:
                _progress_bars_state['blink_state'] = not _progress_bars_state['blink_state']
                _progress_bars_state['last_blink_time'] = current_time
            if not _progress_bars_state['blink_state']:
                return config['colors']['bar_bg']
            return config['colors']['health_critical']
    
    elif bar_type == 'spray':
        if ratio >= 0.6:
            return config['colors']['spray_high']
        elif ratio >= 0.3:
            return config['colors']['spray_medium']
        else:
            return config['colors']['spray_low']
    
    # New: STAMINA
    elif bar_type == 'stamina':
        if ratio >= 0.7:
            return config['colors']['stamina_high']
        elif ratio >= 0.4:
            return config['colors']['stamina_medium']
        elif ratio >= 0.2:
            return config['colors']['stamina_low']
        else:
            current_time = logic.getRealTime()
            if current_time - _progress_bars_state['last_blink_time'] > config['blink_interval']:
                _progress_bars_state['blink_state'] = not _progress_bars_state['blink_state']
                _progress_bars_state['last_blink_time'] = current_time
            if not _progress_bars_state['blink_state']:
                return config['colors']['bar_bg']
            return config['colors']['stamina_critical']
    
    return config['colors']['text']

def _draw_single_bar(icon_char, value, x, y, screen_w, cam_h, bar_type):
    """
    Draws a single progress bar
    """
    config        = PROGRESS_BARS_CONFIG
    icon_size     = int(cam_h * config['icon_scale'])
    text_size     = int(cam_h * config['text_scale'])
    bar_char_size = int(cam_h * config['bar_char_scale'])
    
    blf.size(blf_font_id_icons, icon_size)
    blf.color(blf_font_id_icons, *config['colors']['text'])
    blf.position(blf_font_id_icons, x, y, 0)
    blf.draw(blf_font_id_icons, icon_char)
    
    icon_width, _ = blf.dimensions(blf_font_id_icons, icon_char)
    
    blf.size(blf_font_id_text, bar_char_size)
    char_width, _ = blf.dimensions(blf_font_id_text, '|')
    
    ratio        = value / 100.0
    filled_chars = int(ratio * config['bar_length'])
    bar_x        = x + icon_width + int(screen_w * 0.01)
    
    for i in range(config['bar_length']):
        char_x = bar_x + (i * char_width)
        if i < filled_chars:
            bar_color = _get_bar_color(value, bar_type)
            blf.color(blf_font_id_text, *bar_color)
            blf.position(blf_font_id_text, char_x, y, 0)
            blf.draw(blf_font_id_text, config['bar_char_full'])
        else:
            blf.color(blf_font_id_text, *config['colors']['bar_bg'])
            blf.position(blf_font_id_text, char_x, y, 0)
            blf.draw(blf_font_id_text, config['bar_char_empty'])
    
    bracket_x_start = bar_x - char_width
    bracket_x_end   = bar_x + (config['bar_length'] * char_width)
    
    blf.color(blf_font_id_text, *config['colors']['text'])
    blf.position(blf_font_id_text, bracket_x_start, y, 0)
    blf.draw(blf_font_id_text, '[')
    blf.position(blf_font_id_text, bracket_x_end, y, 0)
    blf.draw(blf_font_id_text, ']')
    
    num_text = f"{value:.1f}%"  # Change: 1 decimal
    blf.size(blf_font_id_text, text_size)
    blf.color(blf_font_id_text, *config['colors']['text'])
    num_x = bracket_x_end + int(char_width * 2)
    blf.position(blf_font_id_text, num_x, y, 0)
    blf.draw(blf_font_id_text, num_text)

def _draw_progress_bars(cam_h):
    """
    Draws all progress bars (Health, Spray, Stamina)
    """
    if getattr(logic, "blf_hidden", False):
        return
    
    screen_w = bge.render.getWindowWidth()
    screen_h = bge.render.getWindowHeight()
    game = game_access.get_game()
    
    if not game:
        return
    
    current_health = max(0, min(100, game.player.health))
    current_spray  = max(0, min(100, game.state.spray_total))
    # New: STAMINA
    current_stamina = max(0, min(100, game.player.stamina))
    
    _progress_bars_state['prev_health'] = current_health
    _progress_bars_state['prev_spray']  = current_spray
    _progress_bars_state['prev_stamina'] = current_stamina
    
    config     = PROGRESS_BARS_CONFIG
    start_x    = int(screen_w * config['start_x'])
    start_y    = int(screen_h * config['start_y'])
    column_gap = int(screen_w * config['column_gap'])
    
    # Draw three bars: Health, Spray, Stamina
    _draw_single_bar('t', current_health, start_x, start_y, screen_w, cam_h, 'health')
    _draw_single_bar('s', current_spray, start_x + column_gap, start_y, screen_w, cam_h, 'spray')
    # New STAMINA bar (to the right of spray)
    _draw_single_bar('u', current_stamina, start_x + (column_gap * 2), start_y, screen_w, cam_h, 'stamina')

# =============================================================================
# MAIN FUNCTION
# =============================================================================
def draw_hud():
    if getattr(logic, "hud_pause_open", False):
        _tw_init()
        _handle_complete_shortcut()
        _typing_sound_update()
        return
    
    _tw_init()
    _handle_complete_shortcut()
    
    screen_w = bge.render.getWindowWidth()
    screen_h = bge.render.getWindowHeight()
    cam_h    = get_camera_height()
    cam_top  = get_camera_top()
    
    current_time = logic.getRealTime()
    
    # ===== MATRIX EFFECT =====
    matrix_active = False
    if hasattr(logic, 'matrix_effect_active') and logic.matrix_effect_active:
        matrix_active = True
    if not matrix_active:
        try:
            game = game_access.get_game()
            if game and hasattr(game, 'state') and hasattr(game.state, 'matrix_effect_active'):
                if game.state.matrix_effect_active:
                    matrix_active = True
                    logic.matrix_effect_active = True
        except:
            pass
    
    if matrix_active and MATRIX_AVAILABLE:
        try:
            if not hasattr(logic, 'matrix_initialized'):
                matrix.init_matrix_effect()
                logic.matrix_initialized = True
            if not hasattr(logic, 'matrix_last_time'):
                logic.matrix_last_time = current_time
            dt = current_time - logic.matrix_last_time
            logic.matrix_last_time = current_time
            if not hasattr(logic, 'matrix_columns') or len(getattr(logic, 'matrix_columns', [])) == 0:
                matrix.create_all_matrix_columns(screen_w, screen_h)
                logic.matrix_columns = matrix.get_columns() if hasattr(matrix, 'get_columns') else []
            matrix.update_matrix_columns(dt, screen_h)
            matrix.draw_matrix_effect()
        except Exception as e:
            print(f"[BLF] Error drawing Matrix effect: {e}")
            logic.matrix_effect_active = False
    
    # ===== PROGRESS BARS =====
    _draw_progress_bars(cam_h)
    
    scene = logic.getCurrentScene()
    game  = game_access.get_game()
    
    if not game:
        return
    
    hud   = game.hud_text
    state = game.state
    gm    = scene.objects.get('Game.Controller')
    
    if not gm:
        return
    
    npc_name = gm.get("npc_name", "").strip()
    
    inv_open = (bool(getattr(logic, "hud_inventory_open", False)) or
                bool(getattr(logic, "hud_inventory_v2_open", False)) or
                bool(getattr(logic, "_force_inventory_open", False)))
    
    if not inv_open:
        if getattr(hud, "item_desc_text", ""):
            hud.item_desc_text = ""
            try:
                _tw_reset_field("desc_text", "")
            except:
                pass
        if getattr(hud, "info_text_v2", ""):
            hud.info_text_v2 = ""
            try:
                _tw_reset_field("info_text", "")
            except:
                pass
    
    # Font sizes (cam_h -> same visual size in any aspect)
    small    = get_text_size('sm', cam_h)
    big      = get_text_size('xl', cam_h)
    npc_size  = int(cam_h * NPC_NAME_SIZE_SCALE)
    
    # Maximum widths in ems (scale with font -> same characters/line)
    max_width_info       = MAX_WIDTH_INFO_EM       * small
    max_width_center     = MAX_WIDTH_CENTER_EM     * big
    max_width_desc       = MAX_WIDTH_DESC_EM       * small
    max_width_book       = MAX_WIDTH_BOOK_EM       * small
    max_width_exhibition = MAX_WIDTH_EXHIBITION_EM * small
    max_width_quiz       = MAX_WIDTH_QUIZ_EM       * small
    max_width_restor     = MAX_WIDTH_RESTOR_EM     * small
    
    # Spacings (cam_h -> proportional to camera view)
    margin_y_dialog         = cam_h * 0.10
    line_spacing_small      = int(cam_h * 0.035)
    margin_x                = screen_w * 0.05
    margin_y_hud            = cam_h * 0.10
    line_spacing_big        = int(cam_h * 0.060)
    line_spacing_book       = int(cam_h * 0.035)
    line_spacing_exhibition = int(cam_h * 0.025)
    line_spacing_within_ans = int(cam_h * 0.025)
    line_spacing_q          = int(cam_h * 0.100)
    
    # --------- 1) HUD VALUES ----------
    _draw_hud_values(cam_h, cam_top)
    
    # --------- 2) Player Dialog ----------
    blf.size(blf_font_id_text, small)
    blf.color(blf_font_id_text, *COLOR_SILVER)
    typed_player = _tw_update_and_get("player_text", hud.player_text, TYPEWRITER_CPS_DIALOG)
    pos_x_player = screen_w * 0.52
    for i, line in enumerate(wrap_text(typed_player, blf_font_id_text, max_width_info)):
        pos_y = cam_top - margin_y_dialog - (line_spacing_small * i)
        blf.position(blf_font_id_text, pos_x_player, pos_y, 0)
        blf.draw(blf_font_id_text, line)
    
    # --------- 3) NPC Name ----------
    if npc_name:
        blf.size(blf_font_id_text, npc_size)
        blf.color(blf_font_id_text, *NPC_NAME_COLOR)
        name_w, _ = blf.dimensions(blf_font_id_text, npc_name)
        base_y = cam_top - margin_y_dialog
        name_y = base_y + int(small * NPC_NAME_OVER_DY)
        name_x = screen_w - margin_x - name_w
        blf.position(blf_font_id_text, name_x, name_y, 0)
        blf.draw(blf_font_id_text, npc_name)
    
    # --------- 4) NPC Dialog ----------
    npc_text_clean = _strip_npc_prefix(hud.char1_text, npc_name)
    blf.size(blf_font_id_text, small)
    blf.color(blf_font_id_text, *COLOR_PALEGREEN)
    typed_char1 = _tw_update_and_get("char1_text", npc_text_clean, TYPEWRITER_CPS_DIALOG)
    for i, line in enumerate(wrap_text(typed_char1, blf_font_id_text, max_width_info)):
        w, _ = blf.dimensions(blf_font_id_text, line)
        pos_x = screen_w - margin_x - w
        pos_y = cam_top - margin_y_dialog - (line_spacing_small * i)
        blf.position(blf_font_id_text, pos_x, pos_y, 0)
        blf.draw(blf_font_id_text, line)
    
    # --------- 5) Center Text ----------
    blf.size(blf_font_id_text, big)
    blf.color(blf_font_id_text, *COLOR_WHITE)
    for i, line in enumerate(wrap_text(hud.center_text, blf_font_id_text, max_width_center)):
        lw, _ = blf.dimensions(blf_font_id_text, line)
        blf.position(blf_font_id_text,
                     (screen_w / 2) - (lw / 2),
                     (screen_h / 2) - (line_spacing_big * i), 0)
        blf.draw(blf_font_id_text, line)
    
    # --------- 6) Info ----------
    info_src = getattr(hud, "info_text_v2", "") or getattr(hud, "info_text", "")
    blf.size(blf_font_id_text, small)
    blf.color(blf_font_id_text, *COLOR_WHITE)
    typed_info = _tw_update_and_get("info_text", info_src, TYPEWRITER_CPS_INFO)
    for i, line in enumerate(wrap_text(typed_info, blf_font_id_text, max_width_info)):
        lw, _ = blf.dimensions(blf_font_id_text, line)
        blf.position(blf_font_id_text,
                     screen_w - margin_x - lw,
                     cam_top - margin_y_hud - (line_spacing_small * i), 0)
        blf.draw(blf_font_id_text, line)
    
    # --------- 7) Normal Quiz (adapt_pos) ----------
    blf.size(blf_font_id_text, small)
    blf.color(blf_font_id_text, *COLOR_WHITE)
    quiz_x, quiz_y_base = adapt_pos(832, 307)
    for i, line in enumerate(wrap_text(hud.quiz_text, blf_font_id_text, max_width_quiz)):
        blf.position(blf_font_id_text,
                     quiz_x,
                     quiz_y_base - (line_spacing_q * i), 0)
        blf.draw(blf_font_id_text, line)
    
    # --------- 8) Item Description ----------
    desc = getattr(hud, "item_desc_text", "")
    if desc:
        blf.size(blf_font_id_text, small)
        blf.color(blf_font_id_text, *COLOR_WHITE)
        line_h  = int(cam_h * 0.027)
        start_x = screen_w * 0.12
        start_y = screen_h * 0.26 + (line_h * 0.5)
        lines   = wrap_text(desc, blf_font_id_text, max_width_desc)
        for i, line in enumerate(lines):
            y = start_y + (line_h * (len(lines) - 1 - i))
            blf.position(blf_font_id_text, start_x, y, 0)
            blf.draw(blf_font_id_text, line)
    
    # --------- 9) Book Text ----------
    book_text = getattr(hud, "book_text", "")
    if book_text:
        blf.size(blf_font_id_text, small)
        blf.color(blf_font_id_text, *COLOR_WHITE)
        book_start_x  = screen_w * 0.23
        book_start_y  = cam_top - (cam_h * 0.28)
        max_book_lines = max(1, int((cam_h * 0.72) / line_spacing_book))
        lines = wrap_text(book_text, blf_font_id_text, max_width_book)
        for i, line in enumerate(lines):
            if i >= max_book_lines:
                break
            y = book_start_y - (line_spacing_book * i)
            blf.position(blf_font_id_text, book_start_x, y, 0)
            blf.draw(blf_font_id_text, line)
    
    # --------- 10) Exhibition Objects ----------
    exhibition_text = getattr(hud, "exhibition_text", "")
    if exhibition_text:
        blf.size(blf_font_id_text, small)
        blf.color(blf_font_id_text, *COLOR_WHITE)
        exhibition_start_x = screen_w * 0.44
        exhibition_start_y = screen_h * 0.60
        lines = wrap_text(exhibition_text, blf_font_id_text, max_width_exhibition)
        for i, line in enumerate(lines):
            if i >= 30:
                break
            y = exhibition_start_y - (line_spacing_exhibition * i)
            blf.position(blf_font_id_text, exhibition_start_x, y, 0)
            blf.draw(blf_font_id_text, line)
    
    # --------- 11) Restoration Quiz (adapt_pos) ----------
    restor_text = getattr(hud, "restor_text", "")
    if restor_text:
        blf.size(blf_font_id_text, small)
        blf.color(blf_font_id_text, *COLOR_WHITE)
        start_x, start_y = adapt_pos(768, 440)
        current_y = start_y
        answers   = restor_text.split("|||")
        for answer_idx, answer_text in enumerate(answers):
            answer_lines = wrap_text(answer_text.strip(), blf_font_id_text, max_width_restor)
            for line in answer_lines:
                blf.position(blf_font_id_text, start_x, current_y, 0)
                blf.draw(blf_font_id_text, line)
                current_y -= line_spacing_within_ans
            if answer_idx < len(answers) - 1:
                reduction = int(cam_h * 0.03) * (len(answer_lines) - 1)
                spacing   = max(int(cam_h * 0.15) - reduction, int(cam_h * 0.10))
                current_y -= spacing
    
    _typing_sound_update()

def main():
    try:
        sc = logic.getCurrentScene()
    except Exception as e:
        print(f"[BLF] Error getting scene: {e}")
        return

    if not hasattr(logic, 'draw_handler_added') or not logic.draw_handler_added:
        try:
            # In UPBGE 0.44 verify if draw_hud is already registered
            if draw_hud not in sc.post_draw:
                sc.post_draw.append(draw_hud)
            logic.draw_handler_added = True
            print("[BLF] draw_hud registered in post_draw")
        except Exception as e:
            print(f"[BLF] Error registering draw_hud: {e}")