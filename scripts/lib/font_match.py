"""Resolve a measured font family to one that will actually load.

A benchmark captures the reference's real typeface. That typeface is usually
proprietary — robinhood.com renders in Capsule Sans Text, which no build can
serve. The pipeline's previous answer was a 24-name membership set in
`orchestrate.py`: a miss emitted `font-family: 'Capsule Sans Text', system-ui`
with no import, so the browser silently fell back to system-ui. The site
declared a typeface it never loaded and nothing reported it — the same
degrade-toward-looking-fine failure as an accent averaged to white.

This module replaces that with a substitution that is chosen and RECORDED.
Two rules:

    A substitution is never silent. Every result carries the measured name,
    the served name, the reason, and a confidence. Callers are expected to
    surface it, the way a contrast adjustment is surfaced.

    A font is never invented. The served name always comes from CATALOG,
    which is a curated list of families that `next/font/google` can serve.
    When nothing in the catalog is a defensible match the result is
    UNMATCHED and the caller must decide, rather than being handed a guess.

Matching is by classification, not by metric similarity — we have a name and
a weight, not outlines. That is honest about what a name can tell you: a
`geometric-sans` match means "same genre", not "same face".
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

#: Families `next/font/google` can serve, grouped by the genre a name can
#: actually signal. Order within a genre is preference: the first entry is the
#: safest general-purpose choice for that genre.
#: Must remain a SUPERSET of the font list this replaced in `orchestrate.py`.
#: That set gated `next/font/google` imports, so dropping a name from here
#: silently downgrades any preset naming it to system-ui.
CATALOG: dict[str, tuple[str, ...]] = {
    "geometric-sans": ("Poppins", "Outfit", "Urbanist", "Sora",
                       "Montserrat", "Raleway"),
    "neo-grotesque-sans": ("Inter", "Manrope", "Work Sans", "Archivo", "Roboto"),
    "humanist-sans": ("Source Sans 3", "Open Sans", "Lato", "Nunito",
                      "Source Sans Pro"),
    "grotesk-display": ("Space Grotesk", "Plus Jakarta Sans", "DM Sans", "Geist"),
    "transitional-serif": ("Libre Baskerville", "Merriweather"),
    "didone-serif": ("Playfair Display", "Cormorant Garamond"),
    "mono": ("Geist Mono", "Space Mono", "IBM Plex Mono"),
}

#: Every servable name, flattened. Membership here means "no substitution
#: needed" — the measured font IS the served font.
SERVABLE: frozenset[str] = frozenset(n for names in CATALOG.values() for n in names)

#: Genre signals carried in a family NAME. This is the whole basis of a
#: heuristic match, and its limits are the point: a name says genre at best.
_SIGNALS: tuple[tuple[str, str], ...] = (
    (r"\bmono(space)?\b|\bcode\b", "mono"),
    (r"\bgrotesk\b|\bgrotesque\b", "grotesk-display"),
    (r"\bdisplay\b|\bheadline\b", "grotesk-display"),
    (r"\bgaramond\b|\bdidot\b|\bbodoni\b|\bplantijn\b", "didone-serif"),
    (r"\bserif\b|\btimes\b|\bgeorgia\b|\bbaskerville\b|\bcaslon\b", "transitional-serif"),
    (r"\bgeometric\b|\bfutura\b|\bavenir\b|\bcircular\b|\bpoppins\b", "geometric-sans"),
    (r"\bhumanist\b|\bfrutiger\b|\bmyriad\b", "humanist-sans"),
    (r"\bneue\b|\bhelvetica\b|\bakzidenz\b|\binter\b|\bgraphik\b", "neo-grotesque-sans"),
    (r"\bsans\b", "neo-grotesque-sans"),
)

#: Genres that a serif measurement must never be substituted across, and vice
#: versa. Substituting a serif reference with a sans is not a near miss, it is
#: a different design.
_SERIF_GENRES = frozenset({"transitional-serif", "didone-serif"})

UNMATCHED = "UNMATCHED"


@dataclass(frozen=True)
class FontMatch:
    """The record of a substitution. Never discard this — it is the evidence."""

    measured: str
    served: str | None
    genre: str | None
    reason: str
    confidence: str  # "exact" | "genre" | "unmatched"

    @property
    def substituted(self) -> bool:
        return self.served is not None and self.served != self.measured

    def as_dict(self) -> dict[str, Any]:
        return {
            "measured": self.measured,
            "served": self.served,
            "genre": self.genre,
            "reason": self.reason,
            "confidence": self.confidence,
            "substituted": self.substituted,
        }


def classify(family: str) -> str | None:
    """Genre a family NAME signals, or None when the name says nothing."""
    name = family.lower()
    for pattern, genre in _SIGNALS:
        if re.search(pattern, name):
            return genre
    return None


def match_font(family: str, *, prefer: str | None = None) -> FontMatch:
    """Resolve `family` to a servable font, or to UNMATCHED.

    `prefer` names a genre to use when the family name signals nothing, which
    is how a caller passes knowledge the name cannot carry (for example, a
    benchmark that measured a serif reference).
    """
    measured = (family or "").strip().strip("'\"")
    if not measured:
        return FontMatch("", None, None, "no family measured", UNMATCHED)

    canonical = {n.lower(): n for n in SERVABLE}
    if measured.lower() in canonical:
        served = canonical[measured.lower()]
        return FontMatch(measured, served, classify(served),
                         "measured family is directly servable", "exact")

    genre = classify(measured) or prefer
    if genre is None:
        return FontMatch(
            measured, None, None,
            f"{measured!r} signals no genre and no preference was supplied; "
            "a served font must be chosen deliberately rather than guessed",
            UNMATCHED)

    if prefer and genre != prefer:
        # A name signal and a caller preference that disagree across the
        # serif/sans divide is not a tie to break silently.
        if (genre in _SERIF_GENRES) != (prefer in _SERIF_GENRES):
            return FontMatch(
                measured, None, genre,
                f"{measured!r} reads as {genre} but caller expected {prefer}; "
                "serif/sans disagreement is not resolvable from a name",
                UNMATCHED)

    served = CATALOG[genre][0]
    return FontMatch(
        measured, served, genre,
        f"{measured!r} is not servable; matched on genre {genre} "
        f"(name signal), served the genre's default",
        "genre")
