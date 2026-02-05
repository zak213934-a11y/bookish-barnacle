#!/usr/bin/env python3
"""
Advanced 90s Anime Aesthetic Prompt Generator v6.4
Optimized for Illustrious SDXL 2.0 (No LoRA version)
Generates highly detailed prompts with extensive customization
Based on Illustrious XL 2.0 tag recommendations and syntax

Now with external data files for easy expansion!
Add more entries to any .txt file in the data/ folder (one per line)
"""

import random
import os
import re
from typing import List, Optional, Tuple, Dict

# ============================================================
# PAIRING MODE (Scene coherence)
# ============================================================
# 'pure'  : fully random (v5 classic behavior)
# 'paired': random, but tries to keep time-of-day ↔ lighting ↔ weather ↔ location coherent
# 'spiky' : mostly paired, but with occasional intentional mismatches for fun surprises
PAIRING_MODE = os.environ.get("PAIRING_MODE", "paired").strip().lower()  # pure | paired | spiky
WILD_SPIKE_CHANCE = float(os.environ.get("WILD_SPIKE_CHANCE", "0.06"))  # only used when PAIRING_MODE == 'spiky'

def _should_pair() -> bool:
    return PAIRING_MODE in ("paired", "spiky")

# SPIKE BUDGET: avoid stacking many contradictions in one prompt
SPIKE_BUDGET = 0

def _reset_spike_budget():
    global SPIKE_BUDGET, WILD_SPIKE_CHANCE
    if PAIRING_MODE == "spiky":
        WILD_SPIKE_CHANCE = max(WILD_SPIKE_CHANCE, 0.03)
        SPIKE_BUDGET = 1
    else:
        SPIKE_BUDGET = 0

def _try_spike() -> bool:
    """Consume the single allowed spike."""
    global SPIKE_BUDGET
    if PAIRING_MODE != "spiky":
        return False
    if SPIKE_BUDGET <= 0:
        return False
    if random.random() < WILD_SPIKE_CHANCE:
        SPIKE_BUDGET -= 1
        return True
    return False

# Track the last scene anchors (optional; useful for future extensions)
LAST_TIME_KEY: str = ""   # key in TIME_OF_DAY (e.g. "night")
LAST_TIME_TAG: str = ""   # emitted tag string
LAST_SEASON_KEY: str = "" # "spring"|"summer"|"autumn"|"winter"|""


# ============================================================
# DATA LOADING SYSTEM
# ============================================================

def get_data_path() -> str:
    """Get the path to the data folder (same directory as this script)"""
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")

def load_list(filename: str) -> List[str]:
    """
    Load a list from a text file (one item per line)
    Ignores empty lines and lines starting with #
    """
    filepath = os.path.join(get_data_path(), filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            items = []
            for line in f:
                line = line.strip()
                # Allow inline comments: 'tag  # comment'
                if '#' in line and not line.lstrip().startswith('#'):
                    line = line.split('#', 1)[0].strip()
                # Skip empty lines and full-line comments
                if line and not line.startswith('#'):
                    items.append(line)
            return items if items else ["default"]
    except FileNotFoundError:
        print(f"Warning: {filename} not found, using defaults")
        return ["default"]

def load_dict(filename: str) -> Dict[str, str]:
    """
    Load a dictionary from a text file (key=value format, one per line)
    Ignores empty lines and lines starting with #
    """
    filepath = os.path.join(get_data_path(), filename)
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            result = {}
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    result[key.strip()] = value.strip()
            return result
    except FileNotFoundError:
        print(f"Warning: {filename} not found, using defaults")
        return {}

# ============================================================
# LOAD ALL DATA FROM FILES
# ============================================================

# Colors
CLOTHING_COLORS = load_list("colors_clothing.txt")
UNDERWEAR_COLORS = load_list("colors_underwear.txt")

# Underwear details
UNDERWEAR_PATTERNS = load_list("underwear_patterns.txt")
UNDERWEAR_STYLES = load_list("underwear_styles.txt")
MATERIAL_TYPES = load_list("materials.txt")

# Hair
HAIR_COLORS = load_list("hair_colors.txt")
HAIR_STYLES = load_list("hair_styles.txt")
HAIR_STYLES_ECCHI = load_list("hair_styles_ecchi.txt")
HAIR_ACCESSORIES = load_list("hair_accessories.txt")
HAIR_COLOR_MODIFIERS = load_list("hair_modifiers.txt")

# Eyes
EYE_COLORS = load_list("eye_colors.txt")
EYE_STYLES = load_list("eye_styles.txt")
EYE_QUALITY = load_list("eye_quality.txt")

# Face
FACE_QUALITY = load_list("face_quality.txt")

# Body
BODY_TYPES = load_list("body_types.txt")
BODY_TYPES_ECCHI = load_list("body_types_ecchi.txt")
BREAST_SIZES = load_list("breast_sizes.txt")
BREAST_SIZES_ECCHI = load_list("breast_sizes_ecchi.txt")
BODY_DETAILS = load_list("body_details.txt")
BODY_DETAILS_ECCHI = load_list("body_details_ecchi.txt")

# Skin
SKIN_TONES = load_list("skin_tones.txt")
SKIN_DETAILS = load_list("skin_details.txt")
SKIN_DETAILS_ECCHI = load_list("skin_details_ecchi.txt")

# Character info
AGE_MATURITY = load_list("age_maturity.txt")
AGE_MATURITY_ECCHI = load_list("age_maturity_ecchi.txt")
NATIONALITY_ETHNICITY = load_list("nationality_ethnicity.txt")

# Subjects
SUBJECTS = load_list("subjects.txt")

# Makeup
MAKEUP = load_list("makeup.txt")
MAKEUP_ECCHI = load_list("makeup_ecchi.txt")

# Jewelry
JEWELRY = load_list("jewelry.txt")
JEWELRY_ECCHI = load_list("jewelry_ecchi.txt")

# Expressions
EXPRESSIONS_PEACEFUL = load_list("expressions_peaceful.txt")
EXPRESSIONS_HAPPY = load_list("expressions_happy.txt")
EXPRESSIONS_SHY = load_list("expressions_shy.txt")
EXPRESSIONS_SERIOUS = load_list("expressions_serious.txt")
EXPRESSIONS_SAD = load_list("expressions_sad.txt")
EXPRESSIONS_SURPRISED = load_list("expressions_surprised.txt")
EXPRESSIONS_CONFIDENT = load_list("expressions_confident.txt")
EXPRESSIONS_MYSTERIOUS = load_list("expressions_mysterious.txt")
EXPRESSIONS_ANGRY = load_list("expressions_angry.txt")
EXPRESSIONS_OTHER = load_list("expressions_other.txt")
EXPRESSIONS_ECCHI = load_list("expressions_ecchi.txt")

# Combined expressions
EXPRESSIONS_DETAILED = (
    EXPRESSIONS_PEACEFUL + EXPRESSIONS_HAPPY + EXPRESSIONS_SHY +
    EXPRESSIONS_SERIOUS + EXPRESSIONS_SAD + EXPRESSIONS_SURPRISED +
    EXPRESSIONS_CONFIDENT + EXPRESSIONS_MYSTERIOUS + EXPRESSIONS_OTHER
)

# Hand positions
HAND_POSITIONS = load_list("hand_positions.txt")
HAND_POSITIONS_ECCHI = load_list("hand_positions_ecchi.txt")

# Poses
POSES_SITTING = load_list("poses_sitting.txt")
POSES_LYING = load_list("poses_lying.txt")
POSES_STANDING = load_list("poses_standing.txt")
POSES_RELAXED = load_list("poses_relaxed.txt")
POSES_PLAYFUL = load_list("poses_playful.txt")
POSES_ECCHI = load_list("poses_ecchi.txt")
ALL_POSES = POSES_SITTING + POSES_LYING + POSES_STANDING + POSES_RELAXED + POSES_PLAYFUL

# Pose variations
POSE_VARIATIONS = load_list("pose_variations.txt")

# Clothing
CASUAL_CLOTHING = load_list("clothing_casual.txt")
SCHOOL_UNIFORMS = load_list("clothing_school.txt")
BUSINESS_CLOTHING = load_list("clothing_business.txt")
STREETWEAR = load_list("clothing_streetwear.txt")
FANTASY_CLOTHING = load_list("clothing_fantasy.txt")
MEDIEVAL_CLOTHING = load_list("clothing_medieval.txt")
SCIFI_CLOTHING = load_list("clothing_scifi.txt")
CYBERPUNK_CLOTHING = load_list("clothing_cyberpunk.txt")
NOIR_CLOTHING = load_list("clothing_noir.txt")
SLEEPWEAR = load_list("clothing_sleepwear.txt")
ELEGANT_CLOTHING = load_list("clothing_elegant.txt")
ATHLETIC_CLOTHING = load_list("clothing_athletic.txt")
TORN_CLOTHING = load_list("clothing_torn.txt")

# Ecchi clothing
ECCHI_SWIMWEAR = load_list("ecchi_swimwear.txt")
ECCHI_LINGERIE = load_list("ecchi_lingerie.txt")
ECCHI_UNDERWEAR = load_list("ecchi_underwear.txt")
ECCHI_REVEALING = load_list("ecchi_revealing.txt")
ECCHI_SLEEPWEAR = load_list("ecchi_sleepwear.txt")
ECCHI_SPECIALTY = load_list("ecchi_specialty.txt")
ECCHI_TOWEL = load_list("ecchi_towel.txt")

# Underwear categories
UNDERWEAR_CASUAL = load_list("underwear_casual.txt")
UNDERWEAR_CUTE = load_list("underwear_cute.txt")
UNDERWEAR_SEXY = load_list("underwear_sexy.txt")
UNDERWEAR_ELEGANT = load_list("underwear_elegant.txt")
UNDERWEAR_ATHLETIC = load_list("underwear_athletic.txt")
UNDERWEAR_SCIFI = load_list("underwear_scifi.txt")
UNDERWEAR_FANTASY = load_list("underwear_fantasy.txt")
UNDERWEAR_THEMED = load_list("underwear_themed.txt")
UNDERWEAR_SHEER = load_list("underwear_sheer.txt")
UNDERWEAR_VINTAGE = load_list("underwear_vintage.txt")

# Combined clothing
ALL_ECCHI_CLOTHING = (
    ECCHI_SWIMWEAR + ECCHI_LINGERIE + ECCHI_UNDERWEAR +
    ECCHI_REVEALING + ECCHI_SLEEPWEAR + ECCHI_SPECIALTY + ECCHI_TOWEL
)

ALL_UNDERWEAR = (
    UNDERWEAR_CASUAL + UNDERWEAR_CUTE + UNDERWEAR_SEXY +
    UNDERWEAR_ELEGANT + UNDERWEAR_ATHLETIC + UNDERWEAR_VINTAGE
)

# Legwear and footwear
LEGWEAR = load_list("legwear.txt")
LEGWEAR_ECCHI = load_list("legwear_ecchi.txt")
FOOTWEAR = load_list("footwear.txt")

# Accessories
ACCESSORIES = load_list("accessories.txt")
ACCESSORIES_ECCHI = load_list("accessories_ecchi.txt")

# Locations
LOCATIONS_COZY = load_list("locations_cozy.txt")
LOCATIONS_URBAN_DAY = load_list("locations_urban_day.txt")
LOCATIONS_URBAN_NIGHT = load_list("locations_urban_night.txt")
LOCATIONS_CYBERPUNK = load_list("locations_cyberpunk.txt")
LOCATIONS_FANTASY = load_list("locations_fantasy.txt")
LOCATIONS_NATURE = load_list("locations_nature.txt")
LOCATIONS_SCHOOL = load_list("locations_school.txt")
LOCATIONS_HISTORICAL = load_list("locations_historical.txt")
LOCATIONS_MODERN = load_list("locations_modern.txt")
LOCATIONS_ECCHI = load_list("locations_ecchi.txt")

# Weather and atmosphere
WEATHER = load_list("weather.txt")
SKY_DETAILS = load_list("sky_details.txt")  # optional extra sky variety

# Time-of-day variants (optional; if files exist they override the default TIME_OF_DAY strings)
TIME_VARIANTS = {
    "dawn": load_list("time_dawn.txt"),
    "morning": load_list("time_morning.txt"),
    "noon": load_list("time_noon.txt"),
    "afternoon": load_list("time_afternoon.txt"),
    "golden_hour": load_list("time_golden_hour.txt"),
    "dusk": load_list("time_dusk.txt"),
    "night": load_list("time_night.txt"),
    "midnight": load_list("time_midnight.txt"),
}

ATMOSPHERIC_EFFECTS = load_list("atmospheric_effects.txt")
ATMOSPHERIC_ECCHI = load_list("atmospheric_ecchi.txt")

# Lighting
LIGHTING_NATURAL = load_list("lighting_natural.txt")
LIGHTING_ARTIFICIAL = load_list("lighting_artificial.txt")
LIGHTING_DRAMATIC = load_list("lighting_dramatic.txt")
LIGHTING_ECCHI = load_list("lighting_ecchi.txt")

# Camera
CAMERA_ANGLES = load_list("camera_angles.txt")
CAMERA_ANGLES_ECCHI = load_list("camera_angles_ecchi.txt")
CAMERA_DISTANCE = load_list("camera_distance.txt")
FRAMING_ECCHI = load_list("framing_ecchi.txt")

# Style
STYLE_ENHANCERS_STANDARD = load_list("style_enhancers_standard.txt")
STYLE_ENHANCERS_ECCHI = load_list("style_enhancers_ecchi.txt")
STYLE_ENHANCERS_DRAMATIC = load_list("style_enhancers_dramatic.txt")
MOODS = load_list("moods.txt")
RETRO_90S_FLAVOR = load_list("retro_90s_flavor.txt")
STYLE_MODIFIERS = load_list("style_modifiers.txt")
ARTISTIC_STYLES = load_list("artistic_styles.txt")
RENDERING_STYLES = load_list("rendering_styles.txt")

# Quality
QUALITY_BOOSTERS = load_list("quality_boosters.txt")

# Illustrious token packs (optional)
QUALITY_SCAFFOLD_ILLUSTRIOUS = load_list("quality_scaffold_illustrious.txt")
OPTICS_BOKEH = load_list("optics_bokeh.txt")

# Load artistic style elements for generation
FILM_GRAIN_OPTIONS = load_list("artistic_film_grain.txt")
SHADING_OPTIONS = load_list("artistic_shading.txt")
LINEWORK_OPTIONS = load_list("artistic_linework.txt")
SHADOW_OPTIONS = load_list("artistic_shadows.txt")
CONTRAST_OPTIONS = load_list("artistic_contrast.txt")
ERA_OPTIONS = load_list("artistic_era.txt")

# ============================================================
# QUALITY PRESETS (kept as dict for structure)
# ============================================================

QUALITY_PRESETS = {
    "ultra": "masterpiece, best quality, absurdres, newest, very aesthetic, incredibly detailed",
    "high": "masterpiece, best quality, absurdres, newest, very aesthetic",
    "standard": "masterpiece, best quality, absurdres, newest",
    "artistic": "masterpiece, best quality, absurdres, very aesthetic, artistic",
}

def _has_real_list(lst: List[str]) -> bool:
    """True if a loaded list is present and not the default placeholder."""
    return bool(lst) and lst != ["default"]


def _pick_quality_scaffold(quality_preset: str) -> str:
    """Pick a single Illustrious-friendly quality scaffold without bloating prompts."""
    base = QUALITY_PRESETS.get(quality_preset, QUALITY_PRESETS["ultra"])
    if not _has_real_list(QUALITY_SCAFFOLD_ILLUSTRIOUS):
        return base

    p = {
        "ultra": 0.70,
        "high": 0.60,
        "standard": 0.45,
        "artistic": 0.25,
    }.get(quality_preset, 0.55)

    if random.random() < p:
        scaff = [s for s in QUALITY_SCAFFOLD_ILLUSTRIOUS if s and s != "default"]
        if not scaff:
            return base
        if quality_preset == "artistic":
            # Prefer shorter scaffolds in artistic mode
            short = [s for s in scaff if s.count(",") <= 3]
            if short:
                return random.choice(short)
        return random.choice(scaff)

    return base


# ============================================================
# CAMERA DISTANCE DETAILED (kept as dict for structure)
# ============================================================

CAMERA_DISTANCE_DETAILED = {
    "face_closeup": [
        "extreme close-up, face focus",
        "close-up, face only",
        "close-up, portrait",
    ],
    "portrait": [
        "portrait, head and shoulders",
        "bust shot, upper chest visible",
        "close-up, upper body",
    ],
    "half_body": [
        "cowboy shot, thighs up",
        "medium shot, waist up",
        "upper body shot",
    ],
    "full_body": [
        "full body",
        "full body shot",
        "whole body visible",
        "knee shot",
    ],
    "wide_scene": [
        "wide shot, full body with environment",
        "very wide shot, figure in scene",
        "establishing shot",
    ],
}

# Time of day
TIME_OF_DAY = {
    "dawn": "dawn, early morning light, soft pink sky, golden hour beginning",
    "morning": "morning, bright daylight, fresh atmosphere, clear sky",
    "noon": "midday, bright sunlight, harsh shadows, clear blue sky",
    "afternoon": "afternoon, warm sunlight, long shadows, golden tones",
    "golden_hour": "golden hour, warm orange light, long shadows, magical atmosphere",
    "dusk": "dusk, twilight, purple sky, fading light",
    "night": "night, darkness, artificial lights, nighttime atmosphere",
    "midnight": "midnight, deep darkness, moonlight, stars visible",
}

# Cached list of time keys (used by pairing/spike logic)
_TIME_KEYS = list(TIME_OF_DAY.keys())



def _time_tag(time_key: str) -> str:
    """Return a time-of-day tag string. Uses data/time_*.txt variants if present."""
    variants = TIME_VARIANTS.get(time_key) if 'TIME_VARIANTS' in globals() else None
    if variants and variants != ["default"]:
        return random.choice(variants)
    return TIME_OF_DAY.get(time_key, TIME_OF_DAY["night"])


def _is_outdoor(location_type: str, location_tag: str) -> bool:
    """Heuristic: decide if scene is outdoor to control sky/weather density."""
    # Bucket hints
    if location_type in ("nature", "urban_day", "urban_night", "cyberpunk"):
        # these are often outdoors, but not always
        likely_outdoor = True
    elif location_type in ("cozy", "ecchi"):
        likely_outdoor = False
    else:
        likely_outdoor = location_type in ("historical", "fantasy")

    t = (location_tag or "").lower()
    outdoor_kw = ["street", "alley", "rooftop", "park", "beach", "shore", "pier", "forest", "mountain", "river", "lake", "field", "garden", "courtyard", "balcony", "bridge", "station platform", "festival", "market", "sidewalk", "crosswalk", "stairs outside", "sky", "outdoors"]
    indoor_kw = ["bedroom", "bathroom", "shower", "bathtub", "room", "apartment", "living room", "kitchen", "cafe", "classroom", "library", "hallway", "locker", "changing room", "hotel", "office", "train car", "subway car", "elevator"]

    if any(k in t for k in indoor_kw):
        return False
    if any(k in t for k in outdoor_kw):
        return True
    return likely_outdoor


def _coherent_sky(sky_list: List[str], time_key: str, location_type: str) -> Optional[str]:
    """Pick a sky descriptor; more likely outdoors, filtered by time-of-day keywords."""
    if not sky_list:
        return None
    # Only add sky for outdoor-ish scenes (or occasionally if indoor with windows)
    # Probability is handled by caller.
    hints = []
    if time_key in ("night", "midnight"):
        hints += ["night", "star", "moon", "milky"]
    elif time_key in ("dawn",):
        hints += ["dawn", "sunrise", "pink", "peach", "horizon"]
    elif time_key in ("morning",):
        hints += ["morning", "blue", "clear", "fresh"]
    elif time_key in ("noon",):
        hints += ["noon", "midday", "blue", "bright", "summer", "heat"]
    elif time_key in ("afternoon",):
        hints += ["afternoon", "warm", "haze", "azure"]
    elif time_key in ("golden_hour", "dusk"):
        hints += ["sunset", "twilight", "orange", "purple", "afterglow", "lavender"]

    cand = _filter_by_keywords(sky_list, include=hints)
    if cand:
        return random.choice(cand)
    return random.choice(sky_list)


def _weather_probability(is_ecchi: bool, location_type: str, is_outdoor: bool) -> float:
    """Higher weather probability outdoors; keep indoor ecchi lighter."""
    if is_outdoor:
        return 0.75 if not is_ecchi else 0.55
    # indoor
    return 0.10 if is_ecchi else 0.25


def _pick_time_key(is_ecchi: bool, location_type: str) -> str:
    # Ecchi and cozy scenes lean evening/night a bit; outdoor scenic can stay broad.
    if not _should_pair():
        return random.choice(_TIME_KEYS)
    if is_ecchi or location_type in ("cozy", "ecchi"):
        weights = [
            ("dusk", 14), ("night", 22), ("midnight", 14),
            ("golden_hour", 10), ("afternoon", 8),
            ("morning", 6), ("dawn", 6), ("noon", 4)
        ]
    elif location_type in ("urban_night", "cyberpunk"):
        weights = [
            ("night", 24), ("dusk", 14), ("midnight", 14),
            ("golden_hour", 10), ("afternoon", 8),
            ("morning", 6), ("dawn", 4), ("noon", 4)
        ]
    else:
        weights = [
            ("morning", 14), ("afternoon", 14), ("golden_hour", 14),
            ("dawn", 10), ("dusk", 10),
            ("noon", 10), ("night", 10), ("midnight", 6)
        ]
    return weighted_choice(weights)
def _spike_override(time_key: str, location_type: str) -> Tuple[str, str]:
    # Create intentional but "still plausible" mismatches sometimes.
    if not _try_spike():
        return time_key, location_type

    # Spike types
    spike = random.choice(["swap_time", "swap_location"])

    if spike == "swap_time":
        # Flip to an opposing time (night <-> noon, dawn <-> midnight, etc.)
        opposites = {
            "night": "noon",
            "midnight": "morning",
            "dusk": "noon",
            "golden_hour": "midnight",
            "dawn": "night",
            "morning": "midnight",
            "noon": "night",
            "afternoon": "midnight",
        }
        return opposites.get(time_key, random.choice(_TIME_KEYS)), location_type

    # swap_location
    # Push location to a contrasting bucket
    contrast = ["fantasy", "cyberpunk", "urban_night", "urban_day", "nature", "historical", "school", "cozy", "modern", "ecchi"]
    if location_type in contrast:
        contrast.remove(location_type)
    return time_key, random.choice(contrast) if contrast else location_type
def _coherent_location_type(preset_locations: List[str], time_key: str) -> str:
    # Pick a location bucket that fits the time-of-day, but keep genre intent.
    if not _should_pair():
        return random.choice(preset_locations)

    nightish = time_key in ("night", "midnight")
    duskish = time_key in ("dusk",)
    dawnish = time_key in ("dawn",)
    noonish = time_key in ("noon",)

    # Prefer buckets that exist in the preset
    preferred = []
    if nightish:
        preferred += ["urban_night", "cyberpunk", "modern", "cozy", "ecchi", "historical", "school"]
    elif duskish:
        preferred += ["urban_day", "urban_night", "modern", "nature", "school", "cozy", "historical"]
    elif dawnish:
        preferred += ["nature", "urban_day", "school", "cozy", "historical"]
    elif noonish:
        preferred += ["urban_day", "nature", "school", "modern"]
    else:
        preferred += ["urban_day", "modern", "school", "nature", "cozy", "historical", "fantasy"]

    viable = [p for p in preferred if p in preset_locations]
    if viable:
        return random.choice(viable)

    return random.choice(preset_locations)
def _filter_by_keywords(items: List[str], include: Optional[List[str]] = None, exclude: Optional[List[str]] = None) -> List[str]:
    """Filter a list of strings by keyword rules to improve scene coherence.

    Matching is intentionally forgiving:
    - Case-insensitive.
    - Also matches after removing spaces/hyphens/underscores, so keywords like
      "streetlight" will match entries like "street light".

    - If include is provided: keep items that contain ANY include keyword.
    - If exclude is provided: drop items that contain ANY exclude keyword.

    This is *not* censorship: it only improves scene coherence in pairing mode.
    """
    if not items:
        return []

    inc_raw = [k for k in (include or []) if k]
    exc_raw = [k for k in (exclude or []) if k]

    inc = [str(k).lower() for k in inc_raw]
    exc = [str(k).lower() for k in exc_raw]

    def _compact(s: str) -> str:
        return re.sub(r"[\s\-_]+", "", s.lower())

    inc_c = [_compact(k) for k in inc]
    exc_c = [_compact(k) for k in exc]

    out: List[str] = []
    for s in items:
        if not s:
            continue
        t = str(s)
        tl = t.lower()
        tc = _compact(t)

        if inc:
            ok = any(k in tl for k in inc) or any(kc and kc in tc for kc in inc_c)
            if not ok:
                continue
        if exc:
            bad = any(k in tl for k in exc) or any(kc and kc in tc for kc in exc_c)
            if bad:
                continue

        out.append(s)
    return out
def _coherent_lighting(preset_lighting: List[str], time_key: str, location_type: str, is_ecchi: bool) -> str:
    if not preset_lighting:
        return "default"
    if not _should_pair():
        return random.choice(preset_lighting)

    # Build a hint list for keyword filtering
    hints = []
    if time_key in ("night", "midnight"):
        hints += ["night", "moon", "starlight", "moonlight", "neon", "streetlight", "lamp", "artificial", "fluorescent", "volumetric", "light shafts"]
    elif time_key in ("dusk", "golden_hour"):
        hints += ["sunset", "golden", "warm", "rim", "twilight", "evening", "sunbeam", "rays", "light shafts", "god rays", "volumetric"]
    elif time_key in ("dawn", "morning"):
        hints += ["morning", "early", "soft", "window", "sunlight", "daylight", "sunbeam", "rays", "dappled", "god rays"]
    elif time_key == "noon":
        hints += ["midday", "harsh", "bright", "sunlight", "daylight", "sunbeam", "sun rays", "light shafts", "volumetric sunlight"]
    else:
        hints += ["daylight", "sunlight", "ambient", "window"]

    # Location nudges
    if location_type in ("urban_night", "cyberpunk"):
        hints += ["neon", "streetlight", "sign", "artificial", "glow"]
    if location_type in ("cozy", "ecchi"):
        hints += ["lamp", "bedside", "warm", "indoor", "soft"]
    if location_type in ("nature", "fantasy", "historical"):
        hints += ["sunlight", "ambient", "soft", "dramatic", "dappled", "sunbeam", "rays"]

    # Ecchi can still be moody indoors
    if is_ecchi:
        hints += ["soft", "warm", "dramatic"]

    cand = _filter_by_keywords(preset_lighting, include=hints)
    if cand:
        return random.choice(cand)

    # If no keyword match, just pick from the preset
    return random.choice(preset_lighting)

def _pick_optics(distance_preset: str, is_ecchi: bool) -> Optional[str]:
    """Optional bokeh/DoF optics tag. Keeps output compact (0-1 optics line)."""
    if not _has_real_list(OPTICS_BOKEH):
        return None

    dp = (distance_preset or "random").strip().lower()
    prob_map = {
        "face_closeup": 0.46,
        "portrait": 0.44,
        "half_body": 0.38,
        "full_body": 0.26,
        "wide_scene": 0.16,
        "random": 0.30,
    }
    p = prob_map.get(dp, 0.28)
    if is_ecchi:
        p = min(0.50, p + 0.05)

    if random.random() > p:
        return None

    # Prefer shorter entries (avoid bloat): mostly 1 token, sometimes 2
    candidates = [s for s in OPTICS_BOKEH if s and s != "default"]
    if not candidates:
        return None

    short = [s for s in candidates if s.count(",") <= 1]
    pool = short if short else candidates
    return random.choice(pool)


def _pick_light_effect(time_key: str, is_outdoor: bool, is_ecchi: bool, existing_text: str = "") -> Optional[str]:
    """Occasional sunbeam/volumetric accent (0-1 extra tag)."""
    # Keep ecchi indoor scenes lighter
    base = 0.22 if is_outdoor else 0.10
    if is_ecchi:
        base -= 0.05
    base = max(0.04, base)

    if random.random() > base:
        return None

    k = (time_key or "").lower()
    if k in ("night", "midnight"):
        include = ["volumetric", "light shafts", "god rays", "moonlight", "starlight"]
    else:
        include = ["sunbeam", "sunbeams", "sun rays", "god rays", "crepuscular", "light shafts", "volumetric"]

    # Pull from lighting lists that already exist (we expanded them in data)
    pool = (LIGHTING_NATURAL or []) + (LIGHTING_DRAMATIC or [])
    cand = _filter_by_keywords(pool, include=include)
    if not cand:
        return None

    ex = (existing_text or "").lower()
    # Avoid repeats
    cand2 = [c for c in cand if c.lower() not in ex]
    if not cand2:
        return None

    # Prefer explicit effects
    explicit = [c for c in cand2 if any(w in c.lower() for w in ["sunbeam", "volumetric", "god rays", "light shafts", "crepuscular"])]
    return random.choice(explicit if explicit else cand2)


def _coherent_weather(weather_list: List[str], time_key: str, location_type: str, is_ecchi: bool, is_outdoor: bool) -> Optional[str]:
    if not weather_list:
        return None

    # ecchi indoor scenes should rarely force weather unless spiking
    base_prob = _weather_probability(is_ecchi, location_type, is_outdoor)
    if not _should_pair():
        return random.choice(weather_list) if random.random() < base_prob else None

    if random.random() > base_prob:
        return None

    hints = []
    if time_key in ("night", "midnight"):
        hints += ["night", "fog", "mist", "clear night", "star", "moon", "cloud"]
    elif time_key in ("dusk", "golden_hour"):
        hints += ["sunset", "twilight", "clearing", "partly cloudy", "cloud"]
    elif time_key in ("dawn", "morning"):
        hints += ["morning", "mist", "fog", "clear", "pale", "sunny"]
    elif time_key == "noon":
        hints += ["sunny", "clear", "harsh", "heat", "blue"]
    else:
        hints += ["partly", "cloud", "clear", "breeze"]

    # Location nudges
    if location_type in ("cyberpunk", "urban_night"):
        hints += ["rain", "drizzle", "wet", "fog", "mist", "storm"]
    if location_type == "nature":
        hints += ["breeze", "clear", "cloud", "mist", "rain"]
    if location_type == "fantasy":
        hints += ["mist", "fog", "storm", "clearing", "rainbow"]

    cand = _filter_by_keywords(weather_list, include=hints)
    if cand:
        return random.choice(cand)

    return random.choice(weather_list)

# Track last scene time key so other modules can align (e.g., mood/atmosphere)
def _coherent_atmosphere(atmo_list: List[str], time_key: str, location_type: str, is_ecchi: bool) -> Optional[str]:
    """
    Pick atmosphere/mood-ish tags in a time-aware way.
    Works with your large wildcard lists (ATMOSPHERIC_EFFECTS / ATMOSPHERIC_ECCHI).
    """
    if not atmo_list:
        return None
    if not _should_pair():
        return random.choice(atmo_list)

    hints = []
    # time hints
    if time_key in ("night", "midnight"):
        hints += ["night", "late night", "moon", "neon", "city lights", "quiet", "noir", "fog", "mist"]
    elif time_key in ("dusk", "golden_hour"):
        hints += ["sunset", "golden", "twilight", "evening", "warm", "long shadows", "nostalgia"]
    elif time_key in ("dawn", "morning"):
        hints += ["morning", "spring morning", "early", "fresh", "soft", "calm"]
    elif time_key == "noon":
        hints += ["midday", "noon", "bright", "summer", "heat"]
    else:
        hints += ["afternoon", "daytime", "warm", "breeze"]

    # location hints
    if location_type in ("cyberpunk", "urban_night"):
        hints += ["neon", "rain", "wet", "city pop", "noir", "alley"]
    if location_type in ("cozy", "ecchi"):
        hints += ["cozy", "quiet room", "soft", "intimate", "bedroom"]
    if location_type == "nature":
        hints += ["breeze", "forest", "sunlight", "mist", "fresh"]
    if location_type == "school":
        hints += ["after school", "classroom", "rooftop"]
    if location_type == "fantasy":
        hints += ["mystic", "mist", "enchanted", "dreamy"]

    cand = _filter_by_keywords(atmo_list, include=hints)
    if cand:
        return random.choice(cand)

    return random.choice(atmo_list)
def _pick_season_from_weather(weather_tag: Optional[str]) -> str:
    """Heuristic season inference; safe defaults."""
    if not weather_tag:
        return ""
    w = weather_tag.lower()
    if any(k in w for k in ["snow", "blizzard", "sleet", "freezing", "ice", "frost", "cold snap"]):
        return "winter"
    if any(k in w for k in ["heat wave", "desert heat", "heat shimmer", "humid", "monsoon", "summer"]):
        return "summer"
    if any(k in w for k in ["autumn", "fall", "leaf", "harvest"]):
        return "autumn"
    if any(k in w for k in ["spring", "pollen", "cherry blossom"]):
        return "spring"
    # Rain/mist are ambiguous; leave blank
    return ""

# ------------------------------------------------------------
# MUTUAL EXCLUSION / ARBITRATION PASSES (post-process tags)
# ------------------------------------------------------------


# Weighted subjects
SUBJECTS_WEIGHTED = [
    ("1girl, solo", 70),
    ("2girls", 20),
    ("2girls, yuri", 10),
]

# ============================================================
# CLOTHING AND LOCATION DICTIONARIES
# ============================================================

ALL_CLOTHING = {
    "casual": CASUAL_CLOTHING,
    "school": SCHOOL_UNIFORMS,
    "business": BUSINESS_CLOTHING,
    "streetwear": STREETWEAR,
    "fantasy": FANTASY_CLOTHING,
    "medieval": MEDIEVAL_CLOTHING,
    "scifi": SCIFI_CLOTHING,
    "cyberpunk": CYBERPUNK_CLOTHING,
    "noir": NOIR_CLOTHING,
    "sleepwear": SLEEPWEAR,
    "elegant": ELEGANT_CLOTHING,
    "athletic": ATHLETIC_CLOTHING,
    "torn": TORN_CLOTHING,
    "ecchi": ALL_ECCHI_CLOTHING,
    "underwear_all": ALL_UNDERWEAR,
    "underwear_casual": UNDERWEAR_CASUAL,
    "underwear_cute": UNDERWEAR_CUTE,
    "underwear_sexy": UNDERWEAR_SEXY,
    "underwear_elegant": UNDERWEAR_ELEGANT,
    "underwear_athletic": UNDERWEAR_ATHLETIC,
    "underwear_scifi": UNDERWEAR_SCIFI,
    "underwear_fantasy": UNDERWEAR_FANTASY,
    "underwear_themed": UNDERWEAR_THEMED,
    "underwear_sheer": UNDERWEAR_SHEER,
    "underwear_vintage": UNDERWEAR_VINTAGE,
}

ALL_LOCATIONS = {
    "cozy": LOCATIONS_COZY,
    "urban_day": LOCATIONS_URBAN_DAY,
    "urban_night": LOCATIONS_URBAN_NIGHT,
    "cyberpunk": LOCATIONS_CYBERPUNK,
    "fantasy": LOCATIONS_FANTASY,
    "nature": LOCATIONS_NATURE,
    "school": LOCATIONS_SCHOOL,
    "historical": LOCATIONS_HISTORICAL,
    "modern": LOCATIONS_MODERN,
    "ecchi": LOCATIONS_ECCHI,
}

# ============================================================
# GENRE PRESETS
# ============================================================

GENRE_WEIGHTS = {
    # Standard genres
    "cozy_slice_of_life": {
        "clothing_types": ["casual", "sleepwear", "school"],
        "locations": ["cozy", "school", "nature"],
        "poses": POSES_SITTING + POSES_LYING + POSES_RELAXED,
        "lighting": LIGHTING_NATURAL,
        "mood": "peaceful",
    },
    "urban_contemporary": {
        "clothing_types": ["casual", "streetwear", "business", "athletic"],
        "locations": ["urban_day", "urban_night", "modern"],
        "poses": POSES_STANDING + POSES_SITTING + POSES_RELAXED,
        "lighting": LIGHTING_NATURAL + LIGHTING_ARTIFICIAL,
        "mood": "urban",
    },
    "cyberpunk_noir": {
        "clothing_types": ["cyberpunk", "noir", "streetwear", "scifi"],
        "locations": ["cyberpunk", "urban_night"],
        "poses": POSES_STANDING + POSES_SITTING,
        "lighting": LIGHTING_ARTIFICIAL + LIGHTING_DRAMATIC,
        "mood": "dark",
    },
    "scifi_future": {
        "clothing_types": ["scifi", "cyberpunk"],
        "locations": ["cyberpunk", "modern"],
        "poses": POSES_STANDING + POSES_SITTING + POSES_RELAXED,
        "lighting": LIGHTING_ARTIFICIAL + LIGHTING_DRAMATIC,
        "mood": "futuristic",
    },
    "fantasy_adventure": {
        "clothing_types": ["fantasy", "elegant", "medieval"],
        "locations": ["fantasy", "nature", "historical"],
        "poses": POSES_STANDING + POSES_SITTING,
        "lighting": LIGHTING_DRAMATIC + LIGHTING_NATURAL,
        "mood": "epic",
    },
    "medieval_fantasy": {
        "clothing_types": ["medieval", "fantasy"],
        "locations": ["fantasy", "historical", "nature"],
        "poses": POSES_STANDING + POSES_SITTING + POSES_LYING,
        "lighting": LIGHTING_NATURAL + LIGHTING_DRAMATIC,
        "mood": "medieval",
    },
    "neo_noir": {
        "clothing_types": ["noir", "business", "elegant"],
        "locations": ["urban_night", "modern"],
        "poses": POSES_STANDING + POSES_SITTING,
        "lighting": LIGHTING_DRAMATIC,
        "mood": "noir",
    },
    "nature_scenic": {
        "clothing_types": ["casual", "elegant", "athletic"],
        "locations": ["nature"],
        "poses": POSES_STANDING + POSES_SITTING + POSES_RELAXED + POSES_PLAYFUL,
        "lighting": LIGHTING_NATURAL,
        "mood": "peaceful",
    },
    "action_torn": {
        "clothing_types": ["torn", "fantasy", "scifi", "cyberpunk"],
        "locations": ["urban_day", "urban_night", "fantasy", "cyberpunk"],
        "poses": POSES_STANDING + POSES_SITTING,
        "lighting": LIGHTING_DRAMATIC + LIGHTING_ARTIFICIAL,
        "mood": "intense",
    },
    # Ecchi genres
    "ecchi_standard": {
        "clothing_types": ["ecchi", "underwear_sexy", "underwear_cute"],
        "locations": ["ecchi", "cozy"],
        "poses": POSES_ECCHI,
        "lighting": LIGHTING_ECCHI,
        "is_ecchi": True,
        "mood": "intimate",
    },
    "ecchi_scifi": {
        "clothing_types": ["underwear_scifi", "scifi", "cyberpunk"],
        "locations": ["cyberpunk", "modern"],
        "poses": POSES_ECCHI,
        "lighting": LIGHTING_ECCHI + LIGHTING_ARTIFICIAL,
        "is_ecchi": True,
        "mood": "futuristic",
    },
    "ecchi_fantasy": {
        "clothing_types": ["underwear_fantasy", "medieval", "fantasy"],
        "locations": ["fantasy", "historical"],
        "poses": POSES_ECCHI,
        "lighting": LIGHTING_ECCHI + LIGHTING_NATURAL + LIGHTING_DRAMATIC,
        "is_ecchi": True,
        "mood": "mystical",
    },
    "ecchi_cute": {
        "clothing_types": ["underwear_cute", "ecchi"],
        "locations": ["cozy", "school"],
        "poses": POSES_ECCHI,
        "lighting": LIGHTING_ECCHI + LIGHTING_NATURAL,
        "is_ecchi": True,
        "mood": "cute",
    },
    "ecchi_athletic": {
        "clothing_types": ["underwear_athletic", "athletic", "ecchi"],
        "locations": ["ecchi", "school", "modern"],
        "poses": POSES_ECCHI,
        "lighting": LIGHTING_ECCHI + LIGHTING_NATURAL,
        "is_ecchi": True,
        "mood": "sporty",
    },
    "ecchi_elegant": {
        "clothing_types": ["underwear_elegant", "underwear_sexy", "elegant"],
        "locations": ["modern", "ecchi", "cozy"],
        "poses": POSES_ECCHI,
        "lighting": LIGHTING_ECCHI + LIGHTING_DRAMATIC,
        "is_ecchi": True,
        "mood": "luxurious",
    },
    "ecchi_sheer": {
        "clothing_types": ["underwear_sheer", "underwear_sexy"],
        "locations": ["ecchi", "cozy", "modern"],
        "poses": POSES_ECCHI,
        "lighting": LIGHTING_ECCHI + LIGHTING_DRAMATIC,
        "is_ecchi": True,
        "mood": "revealing",
    },
    "ecchi_vintage": {
        "clothing_types": ["underwear_vintage", "elegant", "noir"],
        "locations": ["historical", "cozy", "modern"],
        "poses": POSES_ECCHI,
        "lighting": LIGHTING_ECCHI + LIGHTING_NATURAL,
        "is_ecchi": True,
        "mood": "nostalgic",
    },
    "ecchi_themed": {
        "clothing_types": ["underwear_themed", "ecchi"],
        "locations": ["ecchi", "cozy", "modern"],
        "poses": POSES_ECCHI,
        "lighting": LIGHTING_ECCHI + LIGHTING_NATURAL,
        "is_ecchi": True,
        "mood": "playful",
    },
    "ecchi_torn": {
        "clothing_types": ["torn", "ecchi", "underwear_sexy"],
        "locations": ["ecchi", "urban_night", "fantasy"],
        "poses": POSES_ECCHI,
        "lighting": LIGHTING_ECCHI + LIGHTING_DRAMATIC,
        "is_ecchi": True,
        "mood": "intense",
    },
    "ecchi_nature": {
        "clothing_types": ["ecchi", "underwear_casual", "athletic"],
        "locations": ["nature", "ecchi"],
        "poses": POSES_ECCHI,
        "lighting": LIGHTING_ECCHI + LIGHTING_NATURAL,
        "is_ecchi": True,
        "mood": "natural",
    },
    "ecchi_random": {
        "clothing_types": [
            "ecchi", "underwear_all", "underwear_casual", "underwear_cute",
            "underwear_sexy", "underwear_elegant", "underwear_athletic",
            "underwear_scifi", "underwear_fantasy", "underwear_themed",
            "underwear_sheer", "underwear_vintage"
        ],
        "locations": list(ALL_LOCATIONS.keys()),
        "poses": POSES_ECCHI,
        "lighting": LIGHTING_ECCHI + LIGHTING_NATURAL + LIGHTING_ARTIFICIAL + LIGHTING_DRAMATIC,
        "is_ecchi": True,
        "mood": "varied",
    },
    "underwear_only": {
        "clothing_types": ["underwear_all"],
        "locations": ["ecchi", "cozy"],
        "poses": POSES_ECCHI,
        "lighting": LIGHTING_ECCHI,
        "is_ecchi": True,
        "mood": "intimate",
    },
    "random": {
        "clothing_types": list(ALL_CLOTHING.keys()),
        "locations": list(ALL_LOCATIONS.keys()),
        "poses": ALL_POSES,
        "lighting": LIGHTING_NATURAL + LIGHTING_ARTIFICIAL + LIGHTING_DRAMATIC,
        "mood": "varied",
    },
}

# ============================================================
# HELPER FUNCTIONS
# ============================================================

def weighted_choice(items_with_weights: List[Tuple[str, int]]) -> str:
    """Select item based on weights"""
    total = sum(weight for _, weight in items_with_weights)
    r = random.randint(1, total)
    running = 0
    for item, weight in items_with_weights:
        running += weight
        if r <= running:
            return item
    return items_with_weights[-1][0]

def clean_prompt(prompt: str) -> str:
    """Clean up prompt formatting and remove duplicates"""
    # Split into parts
    parts = [part.strip() for part in prompt.split(",") if part.strip()]
    
    # Remove exact duplicates while preserving order
    seen = set()
    unique_parts = []
    for part in parts:
        part_lower = part.lower()
        if part_lower not in seen:
            seen.add(part_lower)
            unique_parts.append(part)
    
    # Rejoin
    prompt = ", ".join(unique_parts)
    
    # Remove double spaces
    while "  " in prompt:
        prompt = prompt.replace("  ", " ")
    
    return prompt

def get_coherent_expression(mood: str, is_ecchi: bool = False) -> str:
    """Get expression that matches the mood"""
    mood_expressions = {
        "peaceful": EXPRESSIONS_PEACEFUL,
        "urban": EXPRESSIONS_CONFIDENT + EXPRESSIONS_OTHER,
        "dark": EXPRESSIONS_SERIOUS + EXPRESSIONS_MYSTERIOUS,
        "futuristic": EXPRESSIONS_SERIOUS + EXPRESSIONS_CONFIDENT,
        "epic": EXPRESSIONS_SERIOUS + EXPRESSIONS_CONFIDENT,
        "medieval": EXPRESSIONS_PEACEFUL + EXPRESSIONS_SERIOUS,
        "noir": EXPRESSIONS_MYSTERIOUS + EXPRESSIONS_SERIOUS,
        "intense": EXPRESSIONS_SERIOUS + EXPRESSIONS_ANGRY,
        "intimate": EXPRESSIONS_ECCHI if is_ecchi else EXPRESSIONS_SHY,
        "cute": EXPRESSIONS_HAPPY + EXPRESSIONS_SHY,
        "sporty": EXPRESSIONS_HAPPY + EXPRESSIONS_CONFIDENT,
        "luxurious": EXPRESSIONS_CONFIDENT + EXPRESSIONS_MYSTERIOUS,
        "mystical": EXPRESSIONS_PEACEFUL + EXPRESSIONS_MYSTERIOUS,
        "playful": EXPRESSIONS_HAPPY + EXPRESSIONS_SHY,
        "natural": EXPRESSIONS_PEACEFUL + EXPRESSIONS_HAPPY,
        "nostalgic": EXPRESSIONS_SAD + EXPRESSIONS_PEACEFUL,
        "revealing": EXPRESSIONS_SHY + EXPRESSIONS_CONFIDENT,
        "varied": EXPRESSIONS_DETAILED,
    }
    
    if is_ecchi:
        return random.choice(EXPRESSIONS_ECCHI)
    
    expressions = mood_expressions.get(mood, EXPRESSIONS_DETAILED)
    return random.choice(expressions)

def get_artistic_style() -> str:
    """Generate varied artistic style string from loaded files"""
    film_grain = random.choice(FILM_GRAIN_OPTIONS) if FILM_GRAIN_OPTIONS else "film grain"
    shading = random.choice(SHADING_OPTIONS) if SHADING_OPTIONS else "cel shading"
    linework = random.choice(LINEWORK_OPTIONS) if LINEWORK_OPTIONS else "detailed linework"
    shadows = random.choice(SHADOW_OPTIONS) if SHADOW_OPTIONS else "soft shadows"
    contrast = random.choice(CONTRAST_OPTIONS) if CONTRAST_OPTIONS else "high contrast"
    era = random.choice(ERA_OPTIONS) if ERA_OPTIONS else "modern anime style"

    elements = [film_grain, shading, linework, shadows, contrast, era]

    # Controlled retro flavor: only when the chosen era implies 80s/90s/retro, and only add 0-1 extra tag
    era_l = era.lower()
    if RETRO_90S_FLAVOR and ("80" in era_l or "90" in era_l or "retro" in era_l or "vhs" in era_l or "ova" in era_l):
        if random.random() < 0.35:
            elements.append(random.choice(RETRO_90S_FLAVOR))

    return ", ".join(elements)

# ============================================================
# MAIN GENERATION FUNCTIONS
# ============================================================

def generate_character(is_ecchi: bool = False, force_1girl: bool = False) -> str:
    """Generate detailed character description"""
    parts = []
    
    # Subject
    if force_1girl:
        parts.append("1girl, solo")
    else:
        parts.append(weighted_choice(SUBJECTS_WEIGHTED))
    
    # Age/Maturity (occasional)
    if is_ecchi:
        if random.random() > 0.4:
            parts.append(random.choice(AGE_MATURITY_ECCHI))
    else:
        if random.random() > 0.5:
            parts.append(random.choice(AGE_MATURITY))
    
    # Ethnicity/Skin (occasional variety)
    if random.random() > 0.6:
        parts.append(random.choice(NATIONALITY_ETHNICITY))
    elif random.random() > 0.5:
        parts.append(random.choice(SKIN_TONES))
    
    # Face quality
    if random.random() > 0.3:
        parts.append(random.choice(FACE_QUALITY))
    
    # Body type
    if is_ecchi:
        parts.append(random.choice(BODY_TYPES_ECCHI))
        parts.append(random.choice(BREAST_SIZES_ECCHI))
        if random.random() > 0.3:
            parts.append(random.choice(BODY_DETAILS_ECCHI))
    else:
        if random.random() > 0.5:
            parts.append(random.choice(BODY_TYPES))
        if random.random() > 0.5:
            parts.append(random.choice(BREAST_SIZES))
        if random.random() > 0.7:
            parts.append(random.choice(BODY_DETAILS))
    
    # Skin details
    if is_ecchi:
        if random.random() > 0.5:
            parts.append(random.choice(SKIN_DETAILS_ECCHI))
    else:
        if random.random() > 0.7:
            parts.append(random.choice(SKIN_DETAILS))
    
    # Makeup
    if is_ecchi:
        if random.random() > 0.6:
            parts.append(random.choice(MAKEUP_ECCHI))
    else:
        if random.random() > 0.7:
            parts.append(random.choice(MAKEUP))
    
    # Eyes
    eye_color = random.choice(EYE_COLORS)
    eye_quality = random.choice(EYE_QUALITY)
    parts.append(f"{eye_color}, {eye_quality}")
    
    # Hair color with optional modifier for variety
    hair_color = random.choice(HAIR_COLORS)
    if random.random() > 0.7:
        hair_modifier = random.choice(HAIR_COLOR_MODIFIERS)
        parts.append(f"{hair_color}, {hair_modifier}")
    else:
        parts.append(hair_color)
    
    # Hair style
    if is_ecchi:
        parts.append(random.choice(HAIR_STYLES_ECCHI))
    else:
        parts.append(random.choice(HAIR_STYLES))
    
    # Hair accessory (occasional)
    if random.random() > 0.7:
        parts.append(random.choice(HAIR_ACCESSORIES))
    
    return ", ".join(parts)

def generate_outfit(genre: str = "random", context: str = "") -> str:
    """Generate outfit based on genre with color variations"""
    preset = GENRE_WEIGHTS.get(genre, GENRE_WEIGHTS["random"])
    is_ecchi = preset.get("is_ecchi", False)
    
    clothing_type = random.choice(preset["clothing_types"])
    clothing_list = ALL_CLOTHING.get(clothing_type, CASUAL_CLOTHING)
    outfit = random.choice(clothing_list)
    

    ctx = (context or "").lower()
    bath_ctx = any(k in ctx for k in ["bath", "bathtub", "onsen", "bathhouse", "shower", "steam"])
    if is_ecchi and bath_ctx:
        # Bias toward towels/robes/lingerie for bath/onsen contexts; avoid heavy streetwear/uniforms
        bath_pool = ECCHI_TOWEL + ECCHI_SLEEPWEAR + ECCHI_LINGERIE + ECCHI_UNDERWEAR
        outfit = random.choice(bath_pool) if bath_pool else outfit

    parts = []
    
    # Add color variation sometimes
    if random.random() > 0.6 and not any(c in outfit.lower() for c in ["white", "black", "red", "blue", "pink", "purple", "green", "yellow", "orange", "grey", "brown"]):
        color = random.choice(CLOTHING_COLORS)
        parts.append(f"{color} {outfit}")
    else:
        parts.append(outfit)
    
    # Add pattern OR material occasionally for ecchi (one slot to avoid prompt bloat)
    if is_ecchi and random.random() > 0.7:
        # Prefer fabric-like materials for Illustrious XL tag vocab; avoid fetish/modern plastics most of the time
        if MATERIAL_TYPES and random.random() < 0.55:
            safe = []
            for m in MATERIAL_TYPES:
                ml = (m or "").lower()
                if not ml:
                    continue
                if any(bad in ml for bad in ["latex", "vinyl", "pvc"]):
                    continue
                safe.append(m)
            pool = safe if safe else MATERIAL_TYPES
            parts.append(random.choice(pool))
        else:
            parts.append(random.choice(UNDERWEAR_PATTERNS))


    # Optional 'sheer' material spice (helps visibility of the sheer option)
    if is_ecchi and ("underwear_sheer" in clothing_type or random.random() > 0.88):
        if not any(w in " ".join(parts).lower() for w in ["sheer", "transparent", "see-through", "mesh"]):
            parts.append(random.choice(["sheer", "mesh", "transparent lace", "see-through fabric"]))
    
    # Legwear with color
    if is_ecchi:
        if random.random() > 0.5:
            legwear = random.choice(LEGWEAR_ECCHI)
            if random.random() > 0.6:
                color = random.choice(["white", "black", "nude", "pink", "red"])
                parts.append(f"{color} {legwear}")
            else:
                parts.append(legwear)
    else:
        if random.random() > 0.5:
            parts.append(random.choice(LEGWEAR))
    
    # Footwear (less for ecchi)
    if is_ecchi:
        if random.random() > 0.7:
            parts.append(random.choice(FOOTWEAR))
    else:
        if random.random() > 0.4:
            parts.append(random.choice(FOOTWEAR))
    
    # Accessories / Jewelry (slot-based so it doesn't always add both)
    # Goal: allow neither, one, or both — with "both" rarer to reduce repetition/bloat.
    if is_ecchi:
        r = random.random()
        if r < 0.45:
            pass  # neither
        elif r < 0.90:
            # one of them
            if random.random() < 0.65:
                parts.append(random.choice(ACCESSORIES_ECCHI))
            else:
                parts.append(random.choice(JEWELRY_ECCHI))
        else:
            # both (rare)
            parts.append(random.choice(ACCESSORIES_ECCHI))
            parts.append(random.choice(JEWELRY_ECCHI))
    else:
        r = random.random()
        if r < 0.55:
            pass  # neither
        elif r < 0.93:
            if random.random() < 0.65:
                parts.append(random.choice(ACCESSORIES))
            else:
                parts.append(random.choice(JEWELRY))
        else:
            parts.append(random.choice(ACCESSORIES))
            parts.append(random.choice(JEWELRY))
    
    return ", ".join(parts)

def generate_pose(genre: str = "random") -> str:
    """Generate pose with optional hand position"""
    preset = GENRE_WEIGHTS.get(genre, GENRE_WEIGHTS["random"])
    is_ecchi = preset.get("is_ecchi", False)
    
    pose = random.choice(preset["poses"])
    parts = [pose]
    
    # Hand position
    if is_ecchi:
        if random.random() > 0.5:
            parts.append(random.choice(HAND_POSITIONS_ECCHI))
    else:
        if random.random() > 0.6:
            parts.append(random.choice(HAND_POSITIONS))
    
    return ", ".join(parts)


def generate_mood() -> str:
    """Generate mood/atmosphere descriptor(s) (separate from visual effects)."""
    if not MOODS:
        return ""
    # Keep it subtle: 0-2 tags
    r = random.random()
    if r < 0.35:
        return ""
    count = 1 if r < 0.85 else 2
    picks = random.sample(MOODS, k=min(count, len(MOODS)))
    return ", ".join(picks)

def generate_scene(genre: str = "random", distance_preset: str = "random") -> str:
    """Generate scene with camera, time-of-day, location, lighting, weather, atmosphere.
    Uses PAIRING_MODE:
      - pure  : fully random
      - paired: coherent time-of-day ↔ lighting ↔ weather ↔ location
      - spiky : mostly coherent, with occasional fun mismatches
    """
    preset = GENRE_WEIGHTS.get(genre, GENRE_WEIGHTS["random"])
    is_ecchi = preset.get("is_ecchi", False)

    parts = []

    # Camera distance/framing (primary - comes first)
    if distance_preset != "random" and distance_preset in CAMERA_DISTANCE_DETAILED:
        parts.append(random.choice(CAMERA_DISTANCE_DETAILED[distance_preset]))
    else:
        parts.append(random.choice(FRAMING_ECCHI) if is_ecchi else random.choice(CAMERA_DISTANCE))

    # Camera angle (secondary)
    # Use external camera angle pools for better variance (no prompt bloat vs previous hardcoded list)
    angle_pool = CAMERA_ANGLES_ECCHI if (is_ecchi and CAMERA_ANGLES_ECCHI) else CAMERA_ANGLES
    if angle_pool:
        parts.append(random.choice(angle_pool))
    else:
        angle_options = ["from front", "from side", "three-quarter view", "profile", "straight-on"]
        if is_ecchi:
            angle_options = ["from front", "from side", "three-quarter view", "over shoulder", "looking up at viewer"]
        parts.append(random.choice(angle_options))

    # --- Time-of-day ↔ location ↔ lighting ↔ weather coherence ---
    # Decide a location bucket, then time, then pick coherent location + lighting + weather.
    preset_locations = preset.get("locations", list(ALL_LOCATIONS.keys()))
    location_type_raw = random.choice(preset_locations)
    time_key = _pick_time_key(is_ecchi=is_ecchi, location_type=location_type_raw)

    # In spiky mode, sometimes intentionally mismatch the time/location bucket
    time_key, location_type_raw = _spike_override(time_key=time_key, location_type=location_type_raw)
    global LAST_TIME_KEY
    LAST_TIME_KEY = time_key

    # Coherent bucket selection (paired/spiky only)
    location_type = _coherent_location_type(preset_locations, time_key) if _should_pair() else location_type_raw
    location = random.choice(ALL_LOCATIONS.get(location_type, LOCATIONS_COZY))
    time_tag = _time_tag(time_key)
    parts.append(time_tag)  # time tag is explicit and useful

    # Optional sky detail (boosts sky variety; mainly outdoors)
    sky_prob = 0.70 if _is_outdoor(location_type, location) else 0.18
    if random.random() < sky_prob:
        sky = _coherent_sky(SKY_DETAILS, time_key, location_type)
        if sky:
            parts.append(sky)

    global LAST_TIME_TAG, LAST_SEASON_KEY
    LAST_TIME_TAG = time_tag
    parts.append(location)

    # Lighting coherent to time + location
    lighting = _coherent_lighting(preset.get("lighting", LIGHTING_NATURAL), time_key, location_type, is_ecchi)
    parts.append(lighting)

    # Optics (bokeh / depth cues) - keep to 0-1 entry to avoid bloat
    optics = _pick_optics(distance_preset, is_ecchi)
    if optics:
        parts.append(optics)

    # Occasional sunbeam/volumetric accent (kept compact)
    effect = _pick_light_effect(time_key, is_outdoor=_is_outdoor(location_type, location), is_ecchi=is_ecchi, existing_text=", ".join(parts))
    if effect:
        parts.append(effect)

    # Weather (rare for ecchi indoor unless lucky/spiky)
    is_outdoor = _is_outdoor(location_type, location)

    weather = _coherent_weather(WEATHER, time_key, location_type, is_ecchi, is_outdoor)
    if weather:
        parts.append(weather)
        if not LAST_SEASON_KEY:
            LAST_SEASON_KEY = _pick_season_from_weather(weather)

    # Atmospheric effects (time-aware in paired/spiky mode)
    # In spiky mode, we allow occasional contradiction by sampling from the full list unfiltered.
    atmo_list = ATMOSPHERIC_ECCHI if is_ecchi else ATMOSPHERIC_EFFECTS
    if atmo_list and (random.random() > (0.55 if is_ecchi else 0.70)):
        if _try_spike():
            parts.append(random.choice(atmo_list))
        else:
            chosen_atmo = _coherent_atmosphere(atmo_list, time_key, location_type, is_ecchi)
            if chosen_atmo:
                parts.append(chosen_atmo)

    return ", ".join(parts)
def generate_style(is_ecchi: bool = False, context: str = "") -> str:
    """Generate style elements"""
    parts = []

    # Illustrious enhancer (standard/ecchi) with dramatic variants when scene hints call for it
    if random.random() > 0.4:
        if is_ecchi:
            parts.append(random.choice(STYLE_ENHANCERS_ECCHI))
        else:
            ctx = (context or "").lower()
            dramatic_hint = any(k in ctx for k in [
                "night", "midnight", "twilight", "dusk", "storm", "thunder", "rainy",
                "neon", "noir", "spotlight", "moonlight", "dark", "dramatic"
            ])
            if STYLE_ENHANCERS_DRAMATIC:
                # Prefer dramatic enhancers when the scene is already dramatic; otherwise keep it rare
                use_dramatic = (dramatic_hint and random.random() < 0.65) or (not dramatic_hint and random.random() < 0.12)
                pool = STYLE_ENHANCERS_DRAMATIC if use_dramatic else STYLE_ENHANCERS_STANDARD
            else:
                pool = STYLE_ENHANCERS_STANDARD
            parts.append(random.choice(pool))
    
    # Style modifier
    if random.random() > 0.4:
        parts.append(random.choice(STYLE_MODIFIERS))
    
    # Artistic style
    if random.random() > 0.3:
        parts.append(random.choice(ARTISTIC_STYLES))
    
    # Rendering style
    if random.random() > 0.5:
        parts.append(random.choice(RENDERING_STYLES))
    
    # Dynamic artistic style
    parts.append(get_artistic_style())
    
    return ", ".join(parts)

def generate_prompt(
    genre: str = "random",
    seed: Optional[int] = None,
    extra_words: str = "",
    distance_preset: str = "random",
    force_1girl: bool = False,
    quality_preset: str = "ultra"
) -> str:
    """
    Generate complete prompt optimized for Illustrious SDXL 2.0
    
    Recommended order for Illustrious:
    1. Quality tags (masterpiece, best quality, etc.)
    2. Style enhancers (official art, illustration, etc.)
    3. Subject count (1girl, solo)
    4. Character details (body, face, hair, eyes)
    5. Clothing/outfit
    6. Expression
    7. Pose
    8. Camera/framing
    9. Location/background
    10. Lighting
    11. Atmosphere
    12. Artistic style
    """
    if seed is not None:
        random.seed(seed)
    _reset_spike_budget()
    
    # Handle ecchi_random
    actual_genre = genre
    if genre == "ecchi_random":
        ecchi_genres = [
            "ecchi_standard", "ecchi_scifi", "ecchi_fantasy",
            "ecchi_cute", "ecchi_athletic", "ecchi_elegant",
            "ecchi_sheer", "ecchi_vintage", "ecchi_themed",
            "ecchi_nature", "ecchi_torn",
        ]
        actual_genre = random.choice(ecchi_genres)
    
    preset = GENRE_WEIGHTS.get(actual_genre, GENRE_WEIGHTS["random"])
    is_ecchi = preset.get("is_ecchi", False)
    mood = preset.get("mood", "varied")
    
    # Build prompt parts
    prompt_parts = []
    
    # 1. Quality tags (most important at start for Illustrious)
    quality = _pick_quality_scaffold(quality_preset)
    prompt_parts.append(quality)

    # Add random quality booster (reduced if scaffold already contains many quality tokens)
    booster_prob = 0.55
    if _has_real_list(QUALITY_SCAFFOLD_ILLUSTRIOUS) and ("amazing quality" in quality.lower() or "extremely aesthetic" in quality.lower() or "very aesthetic" in quality.lower()):
        booster_prob = 0.30
    if random.random() < booster_prob:
        prompt_parts.append(random.choice(QUALITY_BOOSTERS))
    
    # 2. Style enhancer at start
    if is_ecchi:
        prompt_parts.append(random.choice(STYLE_ENHANCERS_ECCHI))
    else:
        prompt_parts.append(random.choice(STYLE_ENHANCERS_STANDARD))
    
    # 3-4. Character (includes subject count and all physical details)
    prompt_parts.append(generate_character(is_ecchi, force_1girl))

    # 6. Expression (mood-coherent)
    expr_part = get_coherent_expression(mood, is_ecchi)
    if expr_part:
        prompt_parts.append(expr_part)

    # 7. Pose
    pose_part = generate_pose(actual_genre)
    if pose_part:
        prompt_parts.append(pose_part)

    
    # 7.5 Mood
    mood_part = generate_mood()
    if mood_part:
        prompt_parts.append(mood_part)

    # 8-11. Scene (camera, location, lighting, atmosphere)
    scene_part = generate_scene(actual_genre, distance_preset)
    if scene_part:
        prompt_parts.append(scene_part)

    # 5. Outfit (context-aware; may bias toward towels/robes for bath/onsen scenes)
    outfit_part = generate_outfit(actual_genre, context=f"{pose_part} {scene_part}")
    # Insert outfit right after character to keep prompt structure stable
    # Character is appended at index 2 (quality, style enhancer, character)
    insert_at = 3 if len(prompt_parts) >= 3 else len(prompt_parts)
    prompt_parts.insert(insert_at, outfit_part)

    
    # 12. Style
    prompt_parts.append(generate_style(is_ecchi, context=f"{mood_part} {scene_part}"))
    
    # Extra words if provided
    if extra_words and extra_words.strip():
        prompt_parts.append(extra_words.strip())
    
    # Combine and clean
    prompt = ", ".join(prompt_parts)
    return clean_prompt(prompt)

# ============================================================
# INTERACTIVE MODE
# ============================================================

def interactive_mode():
    """Run the generator in interactive mode"""
    print("╔" + "═" * 62 + "╗")
    print("║" + " " * 5 + "ANIME PROMPT GENERATOR v6.4 (Illustrious SDXL 2.0)" + " " * 6 + "║")
    print("║" + " " * 10 + "External Data Files Edition - Easy to Expand!" + " " * 6 + "║")
    print("╚" + "═" * 62 + "╝")
    print()
    
    # Genre selection
    print("🎨 SELECT GENRE:")
    print()
    print("  ─── STANDARD GENRES ───")
    print("  1)  Cozy Slice of Life  - Peaceful cafes, bedrooms, warm lighting")
    print("  2)  Urban Contemporary  - Modern streets, rooftops, city vibes")
    print("  3)  Cyberpunk Noir      - Neon streets, tech wear, rain-slicked")
    print("  4)  Sci-Fi Future       - Space suits, androids, futuristic")
    print("  5)  Fantasy Adventure   - Castles, magic, medieval settings")
    print("  6)  Medieval Fantasy    - Taverns, corsets, knights, princesses")
    print("  7)  Neo Noir            - Detective aesthetic, dramatic shadows")
    print("  8)  Nature Scenic       - Beaches, forests, mountains, outdoors")
    print("  9)  Action Torn         - Battle damaged, ripped clothes")
    print()
    print("  ─── ECCHI GENRES (Themed underwear + matching environments) ───")
    print("  10) Ecchi Standard      - Swimwear, lingerie, bedroom settings")
    print("  11) Ecchi Sci-Fi        - Holographic/neon/chrome underwear, cyber settings")
    print("  12) Ecchi Fantasy       - Chainmail/elven/dragon lingerie, castle settings")
    print("  13) Ecchi Cute          - Kawaii/frilly/ribbon underwear, cozy settings")
    print("  14) Ecchi Athletic      - Sports bras, gym shorts, locker room settings")
    print("  15) Ecchi Elegant       - Silk/satin/luxury lingerie, upscale settings")
    print("  16) Ecchi Sheer         - See-through/transparent underwear, intimate")
    print("  17) Ecchi Vintage       - Retro/pinup underwear, historical settings")
    print("  18) Ecchi Themed        - Costume underwear (maid, nurse, etc)")
    print("  19) Ecchi Nature        - Casual underwear, outdoor settings")
    print("  20) Ecchi Torn          - Battle damaged, revealing tears")
    print("  21) Ecchi Random        - Random from ALL ecchi presets above!")
    print()
    print("  ─── UNDERWEAR ONLY ───")
    print("  22) Underwear Only      - All underwear types, intimate settings")
    print()
    print("  23) Random (All)        - Mix of everything (surprise me!)")
    print()
    
    genre_map = {
        "1": "cozy_slice_of_life",
        "2": "urban_contemporary",
        "3": "cyberpunk_noir",
        "4": "scifi_future",
        "5": "fantasy_adventure",
        "6": "medieval_fantasy",
        "7": "neo_noir",
        "8": "nature_scenic",
        "9": "action_torn",
        "10": "ecchi_standard",
        "11": "ecchi_scifi",
        "12": "ecchi_fantasy",
        "13": "ecchi_cute",
        "14": "ecchi_athletic",
        "15": "ecchi_elegant",
        "16": "ecchi_sheer",
        "17": "ecchi_vintage",
        "18": "ecchi_themed",
        "19": "ecchi_nature",
        "20": "ecchi_torn",
        "21": "ecchi_random",
        "22": "underwear_only",
        "23": "random"
    }
    
    while True:
        choice = input("Enter choice (1-23): ").strip()
        if choice in genre_map:
            genre = genre_map[choice]
            break
        print("❌ Invalid choice. Please enter 1-23.")
    
    print()
    
    # Number of prompts
    while True:
        try:
            count_input = input("📊 How many prompts to generate? (default: 1): ").strip()
            count = int(count_input) if count_input else 1
            if count > 0:
                break
            print("❌ Please enter a positive number.")
        except ValueError:
            print("❌ Please enter a valid number.")
    
    print()
    
    # Quality preset
    print("✨ QUALITY PRESET:")
    print("   1) Ultra (default)   - Maximum quality tags")
    print("   2) High              - Standard high quality")
    print("   3) Standard          - Basic quality")
    print("   4) Artistic          - Focus on artistic style")
    print()
    
    quality_map = {
        "1": "ultra", "2": "high", "3": "standard", "4": "artistic", "": "ultra"
    }
    quality_input = input("   Select quality (1-4, default: 1): ").strip()
    quality_preset = quality_map.get(quality_input, "ultra")
    
    print()
    
    # Camera distance option
    print("📷 CAMERA DISTANCE / FRAMING:")
    print("   1) Face Close-up    - Extreme close-up, face only")
    print("   2) Portrait         - Head and shoulders, upper body")
    print("   3) Half Body        - Cowboy shot, waist up")
    print("   4) Full Body        - Whole body visible")
    print("   5) Wide Scene       - Full body with environment")
    print("   6) Random (default) - Mix of all distances")
    print()
    
    distance_map = {
        "1": "face_closeup",
        "2": "portrait",
        "3": "half_body",
        "4": "full_body",
        "5": "wide_scene",
        "6": "random",
        "": "random"
    }
    
    distance_input = input("   Select distance (1-6, default: 6): ").strip()
    distance_preset = distance_map.get(distance_input, "random")
    
    print()
    
    # 1girl only option
    print("👤 CHARACTER COUNT:")
    print("   Force single character (1girl, solo) for all prompts?")
    print("   Y = Always use '1girl, solo' (no 2girls)")
    print("   N = Allow random character count (mostly 1girl, sometimes 2girls)")
    print()
    force_1girl_input = input("   Force 1girl only? (Y/n, default: N): ").strip().lower()
    force_1girl = force_1girl_input == 'y'
    
    print()
    
    # Extra words option
    print("📝 EXTRA WORDS (optional):")
    print("   Add custom tags/words to append to EVERY prompt in batch.")
    print("   Examples: 'rain, umbrella' or 'holding flowers' or 'looking at viewer'")
    print()
    extra_words = input("   Enter extra words (leave blank to skip): ").strip()
    
    print()
    
    # Seed option
    seed_input = input("🎲 Use a seed for reproducible results? (leave blank for random): ").strip()
    seed = int(seed_input) if seed_input else None
    
    print()
    
    # Save option
    save_file = input("💾 Save to file? (leave blank to skip, or enter filename): ").strip()
    
    print()
    print("=" * 64)
    print("🚀 GENERATING PROMPTS...")
    print(f"   Quality preset: {quality_preset}")
    if distance_preset != "random":
        print(f"   Camera distance: {distance_preset}")
    if force_1girl:
        print("   Forcing 1girl, solo")
    print("   No LoRA tags (clean prompts)")
    print("=" * 64)
    print()
    
    return genre, count, seed, save_file if save_file else None, extra_words, distance_preset, force_1girl, quality_preset

# ============================================================
# MAIN EXECUTION
# ============================================================

def main():
    genre, count, seed, save_file, extra_words, distance_preset, force_1girl, quality_preset = interactive_mode()
    
    # Generate prompts
    prompts = []
    for i in range(count):
        current_seed = seed + i if seed is not None else None
        
        prompt = generate_prompt(
            genre=genre,
            seed=current_seed,
            extra_words=extra_words,
            distance_preset=distance_preset,
            force_1girl=force_1girl,
            quality_preset=quality_preset
        )
        
        # Show progress for large batches
        if count > 10 and i % 10 == 0 and i > 0:
            print(f"Generated {i}/{count} prompts...")
        
        prompts.append(prompt)
    
    print()
    
    # Display prompts to console
    if not save_file:
        print("=" * 64)
        print("GENERATED PROMPTS:")
        print("=" * 64)
        print()
        for i, prompt in enumerate(prompts, 1):
            print(f"PROMPT #{i}:")
            print(prompt)
            print()
    
    # Save to file if requested
    if save_file:
        if not save_file.endswith('.txt'):
            save_file = save_file + '.txt'
        
        with open(save_file, 'w', encoding='utf-8') as f:
            for prompt in prompts:
                f.write(prompt + '\n')
        
        print(f"✓ Saved {len(prompts)} prompt(s) to {save_file}")
        print(f"  Format: One prompt per line (ready for batch automation!)")
        print(f"  Quality preset: {quality_preset}")
        if extra_words:
            print(f"  Extra words appended: '{extra_words}'")
    
    print()
    print("=" * 64)
    print("✨ Generation complete! ✨")
    print("=" * 64)
    print()
    print("💡 TIP: These prompts are optimized for Illustrious SDXL 2.0")
    print("   Recommended settings:")
    print("   - CFG Scale: 5-7")
    print("   - Steps: 25-35")
    print("   - Sampler: DPM++ 2M Karras or Euler a")
    print()
    print("📁 To expand this generator, edit the .txt files in the 'data' folder!")
    print("   Each file contains one entry per line. Add as many as you like!")
    print()
    
    # Pause if no file saved
    if not save_file:
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
