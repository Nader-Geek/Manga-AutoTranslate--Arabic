# -*- coding: utf-8 -*-
"""Font per bubble tone for chapter.json (the engine's 16 tones, same idea as its --font-<tone>).

Only fonts shipped in fonts/ are used (all checked to cover the Arabic letters). The mapping is
written into each text's computed.fontFamily/fontWeight; the font FILES are not put in the zip.
"""
from typing import Dict, Tuple

DEFAULT = ("Vazirmatn", "700")
TONE_FONTS: Dict[str, Tuple[str, str]] = {
    "normal": ("Vazirmatn", "700"),
    "shout": ("Lalezar", "400"), "comedy_shout": ("Lalezar", "400"),
    "monster": ("Lalezar", "400"), "black": ("Lalezar", "400"), "sfx": ("Lalezar", "400"),
    "whisper": ("Gandom", "400"),
    "thought": ("Gandom", "400"), "sun_thought": ("Gandom", "400"),
    "square_thought": ("Samim", "700"),
    "free_text": ("Sahel", "700"),
    "system": ("Samim", "700"), "broadcast": ("Samim", "700"),
    "cry": ("Shabnam", "700"),
    "fear": ("Nahid", "400"),
    "letter": ("Amiri", "400"), "narrator": ("Amiri", "400"),
}


def font_for(tone: str, kind: str = "", enabled: bool = True) -> Tuple[str, str]:
    if not enabled:
        return DEFAULT
    if kind == "sfx":
        return TONE_FONTS["sfx"]
    if kind == "narration" and tone in ("normal", ""):
        return TONE_FONTS["narrator"]
    return TONE_FONTS.get(tone or "normal", DEFAULT)
