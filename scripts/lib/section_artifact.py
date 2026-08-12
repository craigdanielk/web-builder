"""The section artifact contract.

Every stage after fill consumes a SectionArtifact and returns a SectionArtifact.
That is deliberate: a stage defined over a contract cannot be gated on which CLI
flag was passed, which is how template lookup and animation injection each spent
months unreachable on the path we actually run.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

VALID_ORIGINS = {"local_template", "supabase_template", "llm"}
VALID_SOURCES = {"harvested", "phase0", "empty"}
VALID_INTENSITIES = {"subtle", "moderate", "expressive", "dramatic"}


@dataclass
class SectionArtifact:
    tsx: str
    archetype: str
    variant: str
    section_uid: str
    intensity: str
    origin: str
    provenance: list = field(default_factory=list)
    assets: list = field(default_factory=list)
    animation: dict = None

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def from_dict(d: dict) -> SectionArtifact:
        return SectionArtifact(
            tsx=d["tsx"],
            archetype=d["archetype"],
            variant=d["variant"],
            section_uid=d["section_uid"],
            intensity=d["intensity"],
            origin=d["origin"],
            provenance=list(d.get("provenance") or []),
            assets=list(d.get("assets") or []),
            animation=d.get("animation"),
        )


def validate(a: SectionArtifact) -> list:
    """Return human-readable violations. Empty list means valid."""
    problems = []
    if not a.tsx.strip():
        problems.append("tsx is empty")
    if not a.section_uid:
        problems.append("section_uid is empty")
    if a.origin not in VALID_ORIGINS:
        problems.append("origin %r is not one of %s" % (a.origin, sorted(VALID_ORIGINS)))
    if a.intensity not in VALID_INTENSITIES:
        problems.append("intensity %r is not one of %s" % (a.intensity, sorted(VALID_INTENSITIES)))
    for row in a.provenance:
        src = row.get("source")
        if src not in VALID_SOURCES:
            problems.append(
                "provenance source %r is not one of %s — fabricated content is a "
                "regulatory liability" % (src, sorted(VALID_SOURCES))
            )
    return problems
