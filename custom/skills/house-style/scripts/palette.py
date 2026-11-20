"""The house palette, a repo's override from `.house-style.json`, and text measuring.

Shared by banner.py, diagram.py and report.py. Standard library only.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

OVERRIDE_FILE = ".house-style.json"
FONT = "Inter, ui-sans-serif, -apple-system, Segoe UI, Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

# Neutral ink. `line` is the hairline, `stroke` a connector, `surface` a tile.
LIGHT = {
    "paper": "#FDFDFB",
    "ink": "#0E0E10",
    "muted": "#6F6F6B",
    "faint": "#A3A39D",
    "line": "#E5E4DE",
    "stroke": "#BFBEB7",
    "surface": "#FFFFFF",
    "accent": "#1F6F5C",
}
# The accent is lifted for the dark ground: at print lightness it disappears on near-black.
DARK = {
    "paper": "#0E0E10",
    "ink": "#FDFDFB",
    "muted": "#A3A39D",
    "faint": "#6F6F6B",
    "line": "#54545A",
    "stroke": "#54545A",
    "surface": "#18181B",
    "accent": "#5FBFA6",
}
# Which `.house-style.json` key sets which colour of which theme.
OVERRIDE_KEYS = {
    "accent": ("light", "accent"),
    "accent_dark": ("dark", "accent"),
    "paper": ("light", "paper"),
    "ink": ("light", "ink"),
    "paper_dark": ("dark", "paper"),
    "ink_dark": ("dark", "ink"),
}
# `font` is read here; `visual` (logo, logo_dark, mark, fade, fade_dark, ramp, font_file, references,
# extraPhrases) is checked here and
# read by starter.py and check_visual.js.
OTHER_KEYS = {"font", "visual"}
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def find_override(start: Path) -> Path | None:
    """The nearest `.house-style.json` at or above `start`, stopping at a git root."""
    for folder in [start.resolve(), *start.resolve().parents]:
        candidate = folder / OVERRIDE_FILE
        if candidate.is_file():
            return candidate
        if (folder / ".git").exists():
            return None
    return None


def load(root: Path | None = None) -> dict:
    """{"light": {...}, "dark": {...}, "font": str}, with the repo's override applied."""
    themes = {"light": dict(LIGHT), "dark": dict(DARK), "font": FONT}
    path = find_override(root or Path.cwd())
    if path is None:
        return themes
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        sys.exit(f"{path}: not valid JSON ({exc})")
    if not isinstance(data, dict):
        sys.exit(f"{path}: expected a JSON object")
    unknown = set(data) - set(OVERRIDE_KEYS) - OTHER_KEYS
    if unknown:
        sys.exit(
            f"{path}: unknown keys {sorted(unknown)}; "
            f"allowed: {sorted(OVERRIDE_KEYS)}, {sorted(OTHER_KEYS)}"
        )
    for key, (theme, colour) in OVERRIDE_KEYS.items():
        if key not in data:
            continue
        value = data[key]
        if not isinstance(value, str) or not HEX.match(value):
            sys.exit(f"{path}: {key} must be a #RRGGBB colour, got {value!r}")
        themes[theme][colour] = value.upper()
    if "visual" in data:
        check_visual(path, data["visual"])
    if "font" in data:
        if not isinstance(data["font"], str) or not data["font"].strip():
            sys.exit(f"{path}: font must be a non-empty string")
        themes["font"] = f"{data['font']}, {FONT}"
    return themes


VISUAL_KEYS = {"logo": str, "logo_dark": str, "mark": str, "fade": list, "fade_dark": list, "ramp": str,
               "font_file": str, "references": list, "extraPhrases": list}
FADE_STOP = re.compile(r"^#[0-9A-Fa-f]{6} (100|[1-9]?[0-9])%$")


def check_visual(path: Path, visual: object) -> None:
    """The `visual` key: the logo, the brand mark, reference shots and extra phrases."""
    if not isinstance(visual, dict):
        sys.exit(f"{path}: visual must be a JSON object")
    unknown = set(visual) - set(VISUAL_KEYS)
    if unknown:
        sys.exit(f"{path}: unknown visual keys {sorted(unknown)}; allowed: {sorted(VISUAL_KEYS)}")
    for key, kind in VISUAL_KEYS.items():
        if key in visual and not isinstance(visual[key], kind):
            sys.exit(f"{path}: visual.{key} must be a {kind.__name__}")
    for key in ("fade", "fade_dark"):
        fade = visual.get(key)
        if fade is not None and not (2 <= len(fade) <= 3 and all(isinstance(x, str) and FADE_STOP.match(x) for x in fade)):
            sys.exit(f'{path}: visual.{key} takes 2 or 3 stops like "#1F6F5C 0%"')
    ramp = visual.get("ramp")
    if ramp is not None and not HEX.match(ramp):
        sys.exit(f"{path}: visual.ramp must be a #RRGGBB colour, got {ramp!r}")


# Rough advance widths for Inter, in em. Good enough to catch overflow before rendering;
# the rendered image is still what decides.
_NARROW = set("iljtf.,:;'|!()[] ")
_WIDE = set("mwMW@%")


def text_width(text: str, size: float, bold: bool = False, spacing: float = 0.0) -> float:
    em = 0.0
    for ch in text:
        if ch in _NARROW:
            em += 0.3
        elif ch in _WIDE:
            em += 0.86
        elif ch.isupper() or ch.isdigit():
            em += 0.68
        else:
            em += 0.56
    width = em * size * (1.06 if bold else 1.0) + spacing * len(text)
    return width


def esc(text: str) -> str:
    return (
        text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )


def mono_width(text: str, size: float) -> float:
    return 0.6 * size * len(text)


def balanced(text: str, size: float, max_width: float, bold: bool = False) -> list[str]:
    """Wrap into as few lines as fit, then even out a two-line split so no word is left alone."""
    lines = wrap(text, size, max_width, bold)
    if len(lines) != 2:
        return lines
    words = text.split()
    splits = [(" ".join(words[:i]), " ".join(words[i:])) for i in range(1, len(words))]
    return list(min(splits, key=lambda pair: max(text_width(part, size, bold) for part in pair)))


def wrap(text: str, size: float, max_width: float, bold: bool = False) -> list[str]:
    """Greedy word wrap by estimated width."""
    lines: list[str] = []
    current = ""
    for word in text.split():
        trial = f"{current} {word}".strip()
        if current and text_width(trial, size, bold) > max_width:
            lines.append(current)
            current = word
        else:
            current = trial
    if current:
        lines.append(current)
    return lines
