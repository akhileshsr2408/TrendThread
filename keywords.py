"""Keyword lists. Add or remove names freely; each is searched as "<name> fabric"."""

# Based on the South India textile report. Slash entries are split into separate keywords.
COLORS = [
    "crimson red", "emerald green", "royal blue", "mustard yellow", "magenta",
    "ivory", "cream", "maroon", "burgundy", "purple", "violet",
    "black", "teal", "aqua", "dusty rose",
]

FABRICS = [
    "pure cotton", "mulberry silk", "silk cotton", "mercerized cotton", "georgette",
    "chiffon", "crepe", "linen", "tissue", "viscose", "rayon", "khadi", "organza",
]

# Anchor = reference term included in every batch (mid-popularity works best).
CATEGORIES = {
    "colors": {"label": "Colors", "names": COLORS, "anchor": "green"},
    "fabrics": {"label": "Fabrics", "names": FABRICS, "anchor": "satin"},
}


def term(name):
    return f"{name} fabric"


# ---- Regions (Google Trends geo codes) ----
# Region key -> (label, [geo codes]). To add a state later, add a line (e.g. Kerala = IN-KL).
REGIONS = {
    "tn": ("Tamil Nadu", ["IN-TN"]),
    "ka": ("Karnataka", ["IN-KA"]),
}
SOUTH_LABEL = "Tamil Nadu + Karnataka"   # key "south" = average of the regions above
GEOS = [g for _, geos in REGIONS.values() for g in geos]
