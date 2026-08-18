#!/usr/bin/env python3
"""Annotate the file-backed rows of animation_registry.json, and split the
catalogue into the library that exists and the wish-list that does not.

WHY THE SPLIT EXISTS
--------------------
`animation_registry.json` is a CATALOGUE of 1034 rows. It is not an inventory
of what this repo has. Measured 2026-08-18 by an `os.path.exists` sweep over
every row's `source_file`: **48 rows have a file on disk and 986 do not**, and
the tree those 986 name — `21st-dev-library/` — is absent from the filesystem
entirely. So 95.4% of the catalogue describes components that cannot be read,
copied, safety-analysed or injected.

"1,034 components" has been quoted in every plan and doc for months. It
overstates the real supply by 21x. Splitting the file is what stops that
number being quotable: the selector reads `animation_library.json` (what
exists), and `animation_wishlist.json` records what does not — with the sweep
that established it, and the date. Nothing is deleted; the catalogue stays
whole, and library + wish-list always sum back to it (asserted below and in
scripts/test_animation_selection.py).

WHY THIS IS A SCRIPT AND NOT A HAND-EDIT
----------------------------------------
`animation_registry.json` is 1034 rows and ~30 fields wide. Hand-editing it
is how `named_exports` and `line_count` drifted from the files in the first
place (e.g. `interactive/hover-glow.tsx` was rewritten in place — the row
still listed only the legacy alias `TubesBackground` and a line_count of 117
against a 126-line file). Everything this writes is derived by reading the
component file, except the mismatch adjudications, which are a reviewed
constant below with the evidence for each.

Run from web-builder/:
    python3 skills/animation-components/registry/annotate_backed_rows.py

Fields written on file-backed rows only:
  dependencies            real external imports parsed from the file
  dependencies_verified   True — the marker the invariant test keys on
  line_count              actual
  named_exports           actual
  has_default_export      actual
  id_describes_file       does the animation_id describe what the file does
  actual_export           the file's primary export, when it doesn't
  mismatch_note           why, when it doesn't
  duplicate_of            when another backed row points at a byte-identical file
"""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

COMPONENTS_DIR = Path(__file__).resolve().parent.parent
REGISTRY = COMPONENTS_DIR / "registry" / "animation_registry.json"
LIBRARY = COMPONENTS_DIR / "registry" / "animation_library.json"
WISHLIST = COMPONENTS_DIR / "registry" / "animation_wishlist.json"
UNIFIED = COMPONENTS_DIR / "component-registry.json"

# The exact sweep that splits the catalogue, recorded in the wish-list so the
# artefact carries its own evidence rather than pointing at a census.
SWEEP = (
    "for row in animation_registry.json['components']: "
    "os.path.exists(skills/animation-components/ + row['source_file'])"
)

# Local aliases and build-provided modules are not npm dependencies.
NOT_A_PACKAGE = {"react", "react-dom", "next"}


def strip_comments(source: str) -> str:
    """Blank out // and /* */ comments, preserving line structure.

    Not cosmetic: `interactive/hover-glow.tsx` documents the remote
    `await import("https://cdn.jsdelivr.net/...")` it replaced inside a
    comment block. Parsing imports over raw text harvested `https:` as an npm
    package name and would have written it into package.json.
    """
    source = re.sub(r"/\*[\s\S]*?\*/", lambda m: re.sub(r"[^\n]", " ", m.group(0)), source)
    return re.sub(r"//[^\n]*", lambda m: " " * len(m.group(0)), source)


def external_imports(source: str) -> list[str]:
    """Bare package specifiers imported by the file, excluding local aliases.

    `gsap/ScrollTrigger` resolves to the `gsap` package; `@gsap/react` is its
    own package, so only scoped names keep their second segment.
    """
    source = strip_comments(source)
    pkgs = set()
    for spec in re.findall(r"""^\s*import[^'"]*['"]([^'"]+)['"]""", source, re.M):
        pkgs.add(spec)
    for spec in re.findall(r"""(?:require|import)\(\s*['"]([^'"]+)['"]\s*\)""", source):
        pkgs.add(spec)
    out = set()
    for spec in pkgs:
        if spec.startswith(".") or spec.startswith("@/") or spec.startswith("/"):
            continue
        parts = spec.split("/")
        name = "/".join(parts[:2]) if spec.startswith("@") else parts[0]
        if name in NOT_A_PACKAGE:
            continue
        out.add(name)
    return sorted(out)


def parse_exports(source: str) -> tuple[bool, list[str]]:
    source = strip_comments(source)
    named = set(re.findall(r"^\s*export\s+(?:async\s+)?(?:function|const|class)\s+(\w+)", source, re.M))
    for block in re.findall(r"^\s*export\s*\{([^}]*)\}", source, re.M):
        for piece in block.split(","):
            piece = piece.strip()
            if not piece:
                continue
            named.add(piece.split(" as ")[-1].strip() if " as " in piece else piece)
    has_default = bool(re.search(r"^\s*export\s+default\b", source, re.M))
    named.discard("default")
    return has_default, sorted(named)


# ---------------------------------------------------------------------------
# Reviewed adjudications: animation_ids that do not describe their file.
# Each was read in full on 2026-08-17; the note is the evidence.
# ---------------------------------------------------------------------------
MISDESCRIBED = {
    "scroll__horizontal_scroll": (
        "Example",
        "file is a self-contained demo page: a hardcoded 7-card carousel of "
        "Unsplash URLs titled 'Title 1'..'Title 7' between two 'Scroll down' / "
        "'Scroll up' panels. Not a reusable horizontal-scroll wrapper.",
    ),
    "scroll__scroll_progress": (
        "Component",
        "exported `Component` is a demo of five coloured panels with the copy "
        "'Scroll down to see the progress bar'. The reusable piece in the file "
        "is the un-exported `ScrollProgress`, whose container is "
        "`overflow-y-auto h-full` — a scroll viewport, not a section wrapper.",
    ),
    "interactive__accordion_expand": (
        "FAQs",
        "file is a complete hardcoded FAQ <section> with placeholder body copy "
        "('Accusantium quisquam. Illo, omnis?', a 30-day refund policy). It has "
        "no accordion behaviour and takes no props. Injecting it would put "
        "invented copy on the page.",
    ),
    "entrance__slide_in_left": (
        "SlideTabs",
        "file is an interactive tab bar with hardcoded labels "
        "Home/Pricing/Features/Docs/Blog and a sliding cursor. No slide-in "
        "entrance animation, and it takes no props.",
    ),
    "entrance__slide_in_right": (
        "SlideTabs",
        "byte-identical to entrance/slide-in-left.tsx — same tab bar, same "
        "export name. Neither direction exists in the file.",
    ),
    "continuous__floating": (
        "CircularMenu",
        "file is a click-to-expand circular image menu with a plus button. "
        "Nothing floats continuously.",
    ),
    "text__text_scramble": (
        "ShaderCanvas",
        "file is a three.js full-screen GLSL RGB-glitch/scanline shader canvas. "
        "No text, no scramble.",
    ),
    "scroll__pin_and_reveal": (
        "StickyFeatureSection",
        "file is a hardcoded sticky feature section taking no props — a section, "
        "not a pin-and-reveal wrapper.",
    ),
    "entrance__scale_up": (
        "BlurReveal",
        "file is a blur+rise reveal (filter blur 10px -> 0, y 20% -> 0), the "
        "same effect as entrance/blur-fade.tsx and the same export name. There "
        "is no scale in it.",
    ),
}


# The date the sweep's RESULT was last reviewed. A reviewed constant, like
# MISDESCRIBED — deliberately not a wall-clock stamp, because this producer's
# defining property is that re-running it reproduces its outputs byte for byte
# (proved in the census; asserted by test_animation_selection.py). A timestamp
# would break that and turn a verifiable artefact into an unverifiable one.
# Bump it when the finding changes, not when the file is rewritten.
SWEEP_DATE = "2026-08-18"


def split_catalogue(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Partition every catalogue row by whether its source_file exists.

    This is the whole split: no heuristic, no allowlist, no framework filter —
    one `os.path.exists` per row. A row is in the library iff the file it
    names can be opened.
    """
    backed, unresolved = [], []
    for row in rows:
        sf = row.get("source_file")
        if sf and (COMPONENTS_DIR / sf).exists():
            backed.append(row)
        else:
            unresolved.append(row)
    return backed, unresolved


def write_split(rows: list[dict]) -> tuple[int, int]:
    """Emit the library the selector reads and the wish-list it must not."""
    backed, unresolved = split_catalogue(rows)

    LIBRARY.write_text(
        json.dumps(
            {
                "role": "the components that exist on disk — the ONLY rows animation "
                        "selection may read",
                "produced_by": "registry/annotate_backed_rows.py",
                "swept": SWEEP_DATE,
                "sweep": SWEEP,
                "backed_components": len(backed),
                "catalogue_components": len(rows),
                "components": backed,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    # The wish-list names each absent row rather than copying it whole: the row
    # itself is not deleted, it stays in animation_registry.json. What is
    # recorded here is the FINDING — this id, this path, this missing root.
    missing_roots: dict[str, int] = {}
    entries = []
    for row in unresolved:
        sf = row.get("source_file") or ""
        root = sf.split("/")[0] if sf else "<no source_file>"
        missing_roots[root] = missing_roots.get(root, 0) + 1
        entries.append(
            {
                "animation_id": row.get("animation_id"),
                "source_file": sf,
                "missing_root": root,
                "framework": row.get("framework") or row.get("engine") or "",
                "section_archetypes": row.get("section_archetypes") or [],
            }
        )

    WISHLIST.write_text(
        json.dumps(
            {
                "role": "UNRESOLVED — catalogue rows naming a file that does not exist. "
                        "Not deleted, not silently filtered: recorded, so a component "
                        "count can never quote them as supply.",
                "produced_by": "registry/annotate_backed_rows.py",
                "swept": SWEEP_DATE,
                "sweep": SWEEP,
                "evidence": (
                    "Every path below was tested with os.path.exists and did not "
                    "exist. The tree they overwhelmingly name, 21st-dev-library/, is "
                    "absent from this filesystem entirely (`ls -d 21st-dev-library` "
                    "and `find / -maxdepth 6 -name 21st-dev-library` both return "
                    "nothing), so these rows are not merely unvendored — they cannot "
                    "be re-derived from anything present."
                ),
                "unresolved_components": len(entries),
                "backed_components": len(backed),
                "catalogue_components": len(rows),
                "missing_by_root": dict(sorted(missing_roots.items())),
                "components": entries,
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    assert len(backed) + len(entries) == len(rows), "split lost or invented a row"
    return len(backed), len(entries)


def main() -> int:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    rows = data["components"]
    unified = json.loads(UNIFIED.read_text(encoding="utf-8"))["components"]
    by_source = {v["source_file"]: v for v in unified.values() if v.get("source_file")}

    # Byte-identical files across backed rows: two animation_ids, one component.
    digests: dict[str, list[str]] = {}
    for row in rows:
        sf = row.get("source_file")
        if not sf:
            continue
        p = COMPONENTS_DIR / sf
        if not p.exists():
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        digests.setdefault(h, []).append(row["animation_id"])

    dupe_of: dict[str, str] = {}
    for ids in digests.values():
        if len(ids) > 1:
            canonical = sorted(ids)[0]
            for other in sorted(ids)[1:]:
                dupe_of[other] = canonical

    touched = 0
    for row in rows:
        sf = row.get("source_file")
        if not sf:
            continue
        path = COMPONENTS_DIR / sf
        if not path.exists():
            # Never annotate a row with no file on disk. A row that advertises
            # verified dependencies for a component that cannot be copied would
            # make the build install npm packages for nothing.
            continue
        source = path.read_text(encoding="utf-8")
        has_default, named = parse_exports(source)
        aid = row["animation_id"]

        row["dependencies"] = external_imports(source)
        row["dependencies_verified"] = True
        row["line_count"] = len(source.splitlines())
        row["named_exports"] = named
        row["has_default_export"] = has_default

        if aid in MISDESCRIBED:
            actual, note = MISDESCRIBED[aid]
            row["id_describes_file"] = False
            row["actual_export"] = actual
            row["mismatch_note"] = note
        else:
            row["id_describes_file"] = True
            row.pop("actual_export", None)
            row.pop("mismatch_note", None)
            unified_row = by_source.get(sf)
            if unified_row:
                row["actual_export"] = unified_row["export_name"]

        if aid in dupe_of:
            row["duplicate_of"] = dupe_of[aid]
        else:
            row.pop("duplicate_of", None)
        touched += 1

    backed_n, unresolved_n = write_split(rows)

    # The catalogue header said `total_components: 1034` and nothing else, so
    # every reader that quoted a count quoted the catalogue. It now states the
    # split in the same place, and the honest number is named `backed_components`.
    data["backed_components"] = backed_n
    data["unresolved_components"] = unresolved_n
    data["split_swept"] = SWEEP_DATE
    REGISTRY.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    print(f"annotated {touched} file-backed rows")
    print(f"misdescribed: {sum(1 for r in rows if r.get('id_describes_file') is False)}")
    print(f"byte-identical duplicates: {sorted(dupe_of.items())}")
    print(
        f"split: {backed_n} backed (animation_library.json) + "
        f"{unresolved_n} unresolved (animation_wishlist.json) = "
        f"{data['total_components']} catalogue rows"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
