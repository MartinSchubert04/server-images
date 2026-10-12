"""Generates ../themes/athanor.yaml, the Home Assistant port of the Portfolio-athanor design system.

Palettes and component rules come from that repo's DESIGN.md and src/index.css. Colors are written
as literal hex (not var() references) because Home Assistant only derives its --rgb-* companions
from literal values.

    python build_theme.py
"""

from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "themes" / "athanor.yaml"

VGA = '"PxPlus IBM VGA 8x16", "Cascadia Mono", Consolas, "Courier New", monospace'
DISPLAY = '"Jacquard 24", "PxPlus IBM VGA 8x16", serif'

PALETTES = {
    "srcery": dict(
        plate="#baa67f", plate_ground="#1c1b19",
        ink="#1c1b19", ink_deep="#121110", clay="#2a2824", clay_hi="#3c3a36", rule="#3c3a36",
        umber="#5c4c39", dim="#918175", tan="#baa67f", cream="#fce8c3", amber="#fbb829",
        amber_hi="#fed06e", amber_lo="#a8760f", blood="#f75341",
        glow="rgb(252 232 195 / 0.12)", shade="rgb(0 0 0 / 0.4)",
    ),
    "umber": dict(
        plate="#c9b994", plate_ground="#16120e",
        ink="#16120e", ink_deep="#0d0b08", clay="#231d16", clay_hi="#3a3126", rule="#3a3126",
        umber="#5c4c39", dim="#8d7d65", tan="#cfc1a3", cream="#e3d6b8", amber="#d49a3a",
        amber_hi="#e8bd6a", amber_lo="#8f6520", blood="#dd7357",
        glow="rgb(252 232 195 / 0.12)", shade="rgb(0 0 0 / 0.4)",
    ),
    "cinnabar": dict(
        plate="#d6ad94", plate_ground="#1c0e0c",
        ink="#1c0e0c", ink_deep="#120807", clay="#2c1613", clay_hi="#4a2420", rule="#4a2420",
        umber="#6e3428", dim="#a8857a", tan="#d8c4ac", cream="#ecd9c0", amber="#e2a24a",
        amber_hi="#f2be6e", amber_lo="#9a6a26", blood="#ff7a56",
        glow="rgb(252 232 195 / 0.12)", shade="rgb(0 0 0 / 0.4)",
        # This palette paints the bars in its own color
        bar=dict(ink="#6e1a14", rule="#6e1a14", cream="#f3e4cc", amber="#ffd27a"),
    ),
    "vellum": dict(
        plate="#ece1c6", plate_ground="#2b241c",
        ink="#ece1c6", ink_deep="#d3c6a3", clay="#f3ead3", clay_hi="#fbf5e6", rule="#b9aa86",
        umber="#b9aa86", dim="#6e5f4c", tan="#473c30", cream="#1f1914", amber="#7c5510",
        amber_hi="#a57a2a", amber_lo="#553a08", blood="#9a3522",
        glow="rgb(255 255 255 / 0.5)", shade="rgb(31 25 20 / 0.12)",
    ),
    "orpiment": dict(
        plate="#eddca8", plate_ground="#2a1d0a",
        ink="#eddca8", ink_deep="#d4bd80", clay="#f4e7bd", clay_hi="#fbf2d6", rule="#c9b27a",
        umber="#c9b27a", dim="#6a5737", tan="#473922", cream="#241a0c", amber="#7a4f06",
        amber_hi="#a3700f", amber_lo="#553604", blood="#9a3522",
        glow="rgb(255 255 255 / 0.5)", shade="rgb(36 26 12 / 0.12)",
        bar=dict(ink="#2a1d0a", rule="#2a1d0a", cream="#eddca8", amber="#e9c766"),
    ),
}

# Theme name -> (dark palette, light palette)
THEMES = {
    "Athanor": ("srcery", "vellum"),
    "Athanor Umber": ("umber", "vellum"),
    "Athanor Cinnabar": ("cinnabar", "orpiment"),
}

# One accent: every named color of Home Assistant collapses onto a palette tone
NAMED = {
    "blood": ["red", "pink", "deep-orange"],
    "amber": ["orange", "amber", "yellow", "lime", "light-green", "green", "teal"],
    "tan": ["cyan", "light-blue", "blue", "indigo", "deep-purple", "purple"],
    "dim": ["brown", "grey", "light-grey", "dark-grey", "blue-grey"],
}

ACTIVE_DOMAINS = [
    "light", "switch", "input_boolean", "fan", "media_player", "automation", "script",
    "binary_sensor", "climate", "cover", "lock", "humidifier", "vacuum", "siren", "camera",
]

RADII = ["xs", "s", "sm", "small", "md", "lg", "xl", "2xl", "3xl", "4xl", "5xl", "6xl", "pill", "circle", "square"]

# The bitmap font is only sharp at multiples of 16px
FONT_SIZES = {"xs": 16, "s": 16, "m": 16, "l": 16, "xl": 16, "2xl": 32, "3xl": 32, "4xl": 32, "5xl": 48}

SHARED = {
    "ha-card-border-radius": "0px",
    "ha-card-border-width": "0px",
    "ha-card-box-shadow": "none",
    "ha-dialog-border-radius": "0px",
    "ha-badge-border-radius": "0px",
    "ha-button-border-radius": "0px",
    "ha-tile-icon-border-radius": "0px",
    "mdc-shape-small": "0px",
    "mdc-shape-medium": "0px",
    "mdc-shape-large": "0px",
    **{f"ha-border-radius-{r}": "0px" for r in RADII},
    "ha-font-family-body": VGA,
    "ha-font-family-heading": VGA,
    "ha-font-family-code": VGA,
    "ha-font-family-longform": VGA,
    "primary-font-family": VGA,
    "paper-font-common-base_-_font-family": VGA,
    "mdc-typography-font-family": VGA,
    "ha-font-smoothing": "none",
    **{f"ha-font-size-{k}": f"{v}px" for k, v in FONT_SIZES.items()},
    "ha-card-header-font-family": DISPLAY,
    "ha-card-header-font-size": "24px",
    "ha-heading-card-title-font-size": "48px",
    "ha-heading-card-title-line-height": "48px",
    "ha-heading-card-title-font-weight": "400",
    "ha-heading-card-subtitle-font-size": "16px",
    "ha-heading-card-subtitle-line-height": "24px",
    "ha-tile-info-primary-font-size": "16px",
    "ha-tile-info-primary-line-height": "24px",
    "ha-tile-info-primary-font-weight": "400",
    "ha-tile-info-secondary-font-size": "16px",
    "ha-tile-info-secondary-line-height": "24px",
    # Room for the 4px dithered shadow of each card
    "ha-section-grid-column-gap": "12px",
    "ha-section-grid-row-gap": "12px",
    # Icons a step smaller than stock (24px), still on the 4px grid
    "mdc-icon-size": "20px",
    "athanor-font-vga": VGA,
    # Three rows of dither thinning downwards, used as a mask so the band takes the palette's color
    "athanor-dither-band": "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='8' height='12' "
    "shape-rendering='crispEdges'%3E%3Cpath d='M0 0h2v2H0zM4 0h2v2H4zM2 2h2v2H2zM6 2h2v2H6zM0 4h2v2H0zM4 6h2v2H4zM2 8h2v2H2z'/%3E%3C/svg%3E\")",
    "athanor-font-display": DISPLAY,
}

# Pixel clay, from .clay in the portfolio: staircase corners, hard bevels, dithered offset shadow.
# card-mod injects this next to every <ha-card>; :host(ha-card) covers the case where it lands inside it.
CARD_CSS = """
ha-card, :host(ha-card) {
  --athanor-steps: polygon(
    0 8px, 4px 8px, 4px 4px, 8px 4px, 8px 0,
    calc(100% - 8px) 0, calc(100% - 8px) 4px, calc(100% - 4px) 4px, calc(100% - 4px) 8px, 100% 8px,
    100% calc(100% - 8px), calc(100% - 4px) calc(100% - 8px), calc(100% - 4px) calc(100% - 4px),
    calc(100% - 8px) calc(100% - 4px), calc(100% - 8px) 100%,
    8px 100%, 8px calc(100% - 4px), 4px calc(100% - 4px), 4px calc(100% - 8px), 0 calc(100% - 8px)
  );
  --athanor-lift: 0px;
  position: relative;
  isolation: isolate;
  background: none !important;
  border: none !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  transform: translate(calc(var(--athanor-lift) * -1), calc(var(--athanor-lift) * -1));
  -webkit-font-smoothing: none;
  shape-rendering: crispEdges;
}
ha-card::before, ha-card::after, :host(ha-card)::before, :host(ha-card)::after {
  content: "";
  position: absolute;
  inset: 0;
  clip-path: var(--athanor-steps);
  pointer-events: none;
}
ha-card::before, :host(ha-card)::before {
  z-index: -2;
  background: repeating-conic-gradient(var(--athanor-umber) 0 25%, transparent 0 50%) 0 0 / 4px 4px;
  transform: translate(calc(4px + var(--athanor-lift)), calc(4px + var(--athanor-lift)));
}
ha-card::after, :host(ha-card)::after {
  z-index: -1;
  opacity: 1 !important;
  background: var(--athanor-clay) !important;
  box-shadow:
    inset 4px 4px 0 var(--athanor-clay-hi),
    inset -4px -4px 0 var(--athanor-ink-deep),
    inset 10px 10px 14px -6px var(--athanor-clay-glow),
    inset -10px -10px 14px -6px var(--athanor-clay-shade);
}
/* Headings are ink on the page, not clay */
:host(hui-heading-card) ha-card::before, :host(hui-heading-card) ha-card::after {
  display: none;
}
/* Under each section title, the dither band that breaks the sections of the portfolio */
:host(hui-heading-card) ha-card:has(.content.title)::after {
  display: block;
  inset: auto 0 -10px 0;
  height: 12px;
  clip-path: none;
  box-shadow: none;
  background: var(--athanor-umber) !important;
  -webkit-mask: var(--athanor-dither-band) repeat-x;
  mask: var(--athanor-dither-band) repeat-x;
}
:host(hui-heading-card) .content.title p {
  font-family: var(--athanor-font-display);
  letter-spacing: 0;
}
/* A section is named by its heading and nothing else */
:host(hui-heading-card) .content.title ha-icon {
  display: none;
}
ha-card ha-icon, ha-card ha-state-icon, ha-card ha-svg-icon, ha-card ha-icon-button {
  --mdc-icon-size: 20px;
}
/* A tile icon is a bare glyph in the state color, like a character of the terminal */
ha-tile-icon {
  --tile-icon-size: 32px;
  --mdc-icon-size: 20px;
  --tile-icon-opacity: 0;
  --tile-icon-hover-opacity: 0;
  --tile-icon-border-radius: 0;
}
/* Cards you press rise a pixel step on hover and sink into their shadow */
:host(hui-tile-card) ha-card:hover, :host(hui-button-card) ha-card:hover {
  --athanor-lift: 2px;
}
:host(hui-tile-card) ha-card:active, :host(hui-button-card) ha-card:active {
  --athanor-lift: -2px;
}
@media (prefers-reduced-motion: no-preference) {
  ha-card, ha-card::before {
    transition: transform 100ms steps(2, end);
  }
}
"""

# The sidebar is the top bar of the portfolio turned on its side: ink, a 2px rule, the brand in amber
SIDEBAR_CSS = """
:host {
  border-right: 2px solid var(--athanor-rule) !important;
  shape-rendering: crispEdges;
  image-rendering: pixelated;
}
/* The plate only hangs where there is wall for it: an open sidebar on a tall window */
@media (min-height: 1000px) {
  :host([expanded]) {
    background-image: var(--athanor-plate-side);
    background-repeat: no-repeat;
    background-position: center bottom 168px;
  }
}
/* The sidebar hardcodes Roboto */
* {
  font-family: var(--athanor-font-vga) !important;
  -webkit-font-smoothing: none;
}
.title {
  color: var(--athanor-amber);
  font-size: 0 !important;
}
.title::before {
  content: var(--athanor-brand, "@ home");
  font-size: 16px;
}
ha-icon, ha-svg-icon, ha-icon-button {
  --mdc-icon-size: 20px;
}
"""

# Header and dialogs only need the icon treatment
CRISP_CSS = """
:host {
  shape-rendering: crispEdges;
}
ha-icon, ha-svg-icon, ha-icon-button, ha-state-icon {
  --mdc-icon-size: 20px;
}
"""


# Room at the bottom of a dashboard for the status line that athanor.js draws
ROOT_CSS = CRISP_CSS + """
hui-view-container {
  padding-bottom: var(--athanor-status-height, 0px);
}
"""


def mix(a: str, b: str, t: float) -> str:
    """Color at fraction t of the way from a to b."""
    ca, cb = (tuple(int(c[i : i + 2], 16) for i in (1, 3, 5)) for c in (a, b))
    return "#" + "".join(f"{round(x + (y - x) * t):02x}" for x, y in zip(ca, cb))


def luminance(c: str) -> float:
    r, g, b = (int(c[i : i + 2], 16) for i in (1, 3, 5))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def scale(family: str, hue: str, dark: str, light: str) -> dict:
    """The 05..95 ramp behind Home Assistant's semantic colors (buttons, links, alerts), re-inked."""
    down = {"05": 0.12, "10": 0.2, "20": 0.35, "30": 0.55, "40": 0.8, "50": 1.0}
    up = {"60": 0.25, "70": 0.45, "80": 0.62, "90": 0.8, "95": 0.9}
    return {
        **{f"ha-color-{family}-{k}": mix(dark, hue, t) for k, t in down.items()},
        **{f"ha-color-{family}-{k}": mix(hue, light, t) for k, t in up.items()},
    }


def mode_vars(name: str) -> dict:
    p = PALETTES[name]
    # Darkest and lightest tone of the palette, whichever way round it is
    dark, light = sorted([p["ink_deep"], p["cream"], p["clay_hi"]], key=luminance)[:: 2]
    bar = {**p, **p.get("bar", {})}
    v = {
        "primary-color": p["amber"],
        "light-primary-color": p["amber_hi"],
        "dark-primary-color": p["amber_lo"],
        "accent-color": p["amber"],
        "text-primary-color": p["ink"],
        # Text that sits on the accent, such as the count of a sidebar badge
        "text-accent-color": p["ink"],
        "primary-background-color": p["ink"],
        "secondary-background-color": p["clay"],
        "clear-background-color": p["ink"],
        "lovelace-background": p["ink"],
        "card-background-color": p["clay"],
        "ha-card-background": p["clay"],
        "ha-card-header-color": p["cream"],
        "divider-color": p["rule"],
        "outline-color": p["rule"],
        "primary-text-color": p["cream"],
        "secondary-text-color": p["dim"],
        "disabled-text-color": p["umber"],
        "ha-heading-card-title-color": p["cream"],
        "ha-heading-card-subtitle-color": p["dim"],
        "app-header-background-color": bar["ink"],
        "app-header-text-color": bar["cream"],
        "app-header-selection-text-color": bar["amber"],
        "app-header-border-bottom": f"2px solid {p['rule']}",
        # View tabs are the nav links of the portfolio's top bar: tan, the current one in amber
        "app-header-selection-bar-color": bar["amber"],
        "ha-tab-active-text-color": bar["amber"],
        "ha-tab-indicator-color": bar["amber"],
        "ha-tab-track-color": "transparent",
        "sidebar-background-color": p["ink"],
        "sidebar-text-color": p["tan"],
        "sidebar-icon-color": p["dim"],
        "sidebar-selected-text-color": p["amber"],
        "sidebar-selected-icon-color": p["amber"],
        "state-icon-color": p["tan"],
        "state-inactive-color": p["dim"],
        "state-unavailable-color": p["umber"],
        "state-active-color": p["amber"],
        **{f"state-{d}-active-color": p["amber"] for d in ACTIVE_DOMAINS},
        "success-color": p["tan"],
        "warning-color": p["amber"],
        "error-color": p["blood"],
        "info-color": p["dim"],
        **{f"{c}-color": p[tone] for tone, colors in NAMED.items() for c in colors},
        **scale("primary", p["amber"], dark, light),
        **scale("orange", p["amber"], dark, light),
        **scale("red", p["blood"], dark, light),
        **scale("green", p["tan"], dark, light),
        **{f"ha-color-neutral-{k}": mix(dark, light, int(k) / 100) for k in
           ["00", "05", "10", "20", "30", "40", "50", "60", "70", "80", "90", "95"]},
        "ha-color-text-link": p["amber"],
        "graph-color-1": p["amber"],
        "graph-color-2": p["tan"],
        "graph-color-3": p["cream"],
        "graph-color-4": p["dim"],
        "graph-color-5": p["blood"],
        "switch-checked-button-color": p["amber_hi"],
        "switch-checked-track-color": p["amber_lo"],
        "switch-unchecked-button-color": p["tan"],
        "switch-unchecked-track-color": p["clay_hi"],
        "slider-color": p["amber"],
        "slider-track-color": p["clay_hi"],
        "input-fill-color": p["ink_deep"],
        "input-ink-color": p["cream"],
        "input-label-ink-color": p["dim"],
        "input-idle-line-color": p["rule"],
        "input-hover-line-color": p["amber"],
        "input-dropdown-icon-color": p["dim"],
        "mdc-theme-primary": p["amber"],
        "mdc-theme-secondary": p["amber"],
        "mdc-theme-background": p["ink"],
        "mdc-theme-surface": p["clay"],
        "mdc-theme-on-surface": p["cream"],
        "mdc-theme-on-primary": p["ink"],
        "mdc-theme-on-secondary": p["ink"],
        "table-row-background-color": p["ink"],
        "table-row-alternative-background-color": p["clay"],
        "table-header-background-color": p["clay"],
        "code-editor-background-color": p["ink_deep"],
        "codemirror-keyword": p["amber"],
        "codemirror-property": p["tan"],
        "codemirror-atom": p["amber_hi"],
        "codemirror-string": p["cream"],
        "codemirror-number": p["amber_hi"],
        "codemirror-comment": p["dim"],
        "codemirror-meta": p["dim"],
        "scrollbar-thumb-color": p["clay_hi"],
        # Tokens read by the card-mod CSS
        "athanor-ink": p["ink"],
        "athanor-ink-deep": p["ink_deep"],
        "athanor-clay": p["clay"],
        "athanor-clay-hi": p["clay_hi"],
        "athanor-rule": p["rule"],
        "athanor-umber": p["umber"],
        "athanor-dim": p["dim"],
        "athanor-tan": p["tan"],
        "athanor-cream": p["cream"],
        "athanor-amber": p["amber"],
        "athanor-blood": p["blood"],
        "athanor-clay-glow": p["glow"],
        "athanor-clay-shade": p["shade"],
        "athanor-plate": p["plate"],
        "athanor-plate-ground": p["plate_ground"],
        "athanor-plate-side": f"url('/local/athanor/plates/side-{name}.png?v=2')",
    }
    return v


def q(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def emit(d: dict, indent: int) -> list[str]:
    pad = " " * indent
    return [f"{pad}{k}: {q(v)}" for k, v in d.items()]


def block(key: str, css: str, indent: int) -> list[str]:
    pad = " " * indent
    return [f"{pad}{key}: |"] + [f"{pad}  {line}".rstrip() for line in css.strip().splitlines()]


lines = ["# Generated by home-assistant-init/athanor/build_theme.py. Edit that file, not this one."]
for theme, (dark, light) in THEMES.items():
    lines += ["", f"{theme}:"]
    lines += [f"  card-mod-theme: {q(theme)}"]
    lines += block("card-mod-card", CARD_CSS, 2)
    lines += block("card-mod-sidebar", SIDEBAR_CSS, 2)
    lines += block("card-mod-root", ROOT_CSS, 2)
    lines += block("card-mod-more-info", CRISP_CSS, 2)
    lines += emit(SHARED, 2)
    lines += ["  modes:", "    dark:"] + emit(mode_vars(dark), 6)
    lines += ["    light:"] + emit(mode_vars(light), 6)

OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
print(f"{OUT} ({len(lines)} lines)")
