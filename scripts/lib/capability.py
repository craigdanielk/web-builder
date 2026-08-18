#!/usr/bin/env python3
"""The capability declaration — canonical schema, and the Python-side `--describe`.

WHY THIS EXISTS
---------------
See `scripts/quality/lib/capability.js` for the full argument.  In short: a
document describing the instruments goes stale the first time a flag changes and
nothing fails when it does (`registry/capability-matrix.yaml` carries
`last_measured: '2026-05-09'` on every row and still ships).  So the declaration
lives beside the code and the register is compiled from it.

WHICH VALIDATOR IS AUTHORITATIVE
--------------------------------
This one.  `capability.js` mirrors these rules so a JS instrument fails fast at
its own call site, but `capability_register.py` re-validates EVERY declaration
it ingests through this module, whatever language produced it.  If the two ever
disagree, the compiler's verdict is the one that reaches the register — and
`test_capability_register.py` asserts the two field lists agree, so the drift
cannot go unnoticed.

USAGE
    from lib.capability import describe
    CAPABILITY = {"id": "aurelix.gate.compliance", ...}
    def main() -> int:
        if describe(CAPABILITY):
            return 0
        ...
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any, Iterable

# What an instrument IS.  The compiler rejects anything else.
KINDS: frozenset[str] = frozenset({
    "gate",       # three-state verdict on a build: PASS / FAIL / NOT_MEASURED
    "probe",      # measures and reports; renders no verdict
    "extractor",  # pulls facts out of a source (a site, a bundle, a store)
    "compiler",   # turns declared inputs into a derived artifact
    "adapter",    # targets one platform behind a shared interface
    "generator",  # creates content or assets
    "builder",    # assembles a registry, spec or manifest
    "fixer",      # mutates source to remediate a finding
    "migration",  # moves state from one shape to another
    "harness",    # runs other instruments
})

# Every field is required.  There is no optional half of this contract.
REQUIRED: tuple[str, ...] = (
    "id",              # stable dotted identity; the register's primary key
    "name",            # one human line
    "kind",            # from KINDS
    "invocation",      # the EXACT command line.  Evidence is matched against it
    "preconditions",   # what must already be true, in operator-actionable words
    "inputs",          # what it reads
    "outputs",         # what it writes
    "outcome",         # what you learn by running it
    "exit_contract",   # {code: meaning} — every code it can return
    "measures",        # what it can see
    "cannot_see",      # what it CANNOT see.  Never empty
    "reachable_from",  # call sites today; [] means nothing invokes it
    "cost",            # wall-clock and prerequisites, honestly
)

# Fields the compiler owns.  A declaration that sets one is refused: an
# instrument does not get to grade itself.
COMPILER_OWNED: frozenset[str] = frozenset({"status", "evidence", "source_file", "language"})

_LIST_FIELDS: tuple[str, ...] = ("preconditions", "inputs", "outputs", "measures", "cannot_see")
# `inputs` and `outputs` may legitimately be empty (a gate that only reads a
# directory it is handed, a probe that writes nothing).  The rest may not.
_MAY_BE_EMPTY: frozenset[str] = frozenset({"inputs", "outputs"})

_ID_RE = re.compile(r"^[a-z0-9]+(\.[a-z0-9][a-z0-9-]*)+$")


class CapabilityInvalid(ValueError):
    """A declaration that cannot enter the register, with every reason listed."""


def validate(spec: Any, where: str = "capability declaration") -> dict[str, Any]:
    """Return `spec` unchanged, or raise `CapabilityInvalid` listing every problem.

    Reports ALL problems at once.  A validator that stops at the first one turns
    a single fix into five round trips.
    """
    problems: list[str] = []
    if not isinstance(spec, dict):
        raise CapabilityInvalid(f"{where}: expected an object, got {type(spec).__name__}")

    for field in REQUIRED:
        if field not in spec:
            problems.append(f"missing required field `{field}`")
    for field in sorted(COMPILER_OWNED):
        if field in spec:
            problems.append(
                f"`{field}` is owned by the compiler and may not be declared — "
                f"an instrument does not grade itself"
            )

    kind = spec.get("kind")
    if kind is not None and kind not in KINDS:
        problems.append(f"kind {kind!r} is not one of: {', '.join(sorted(KINDS))}")

    ident = spec.get("id")
    if isinstance(ident, str) and not _ID_RE.match(ident):
        problems.append(
            f"id {ident!r} must be dotted lowercase, e.g. aurelix.gate.conformance"
        )

    for field in _LIST_FIELDS:
        if field not in spec:
            continue
        value = spec[field]
        if not isinstance(value, list):
            problems.append(f"`{field}` must be a list of strings")
            continue
        if any(not isinstance(s, str) or not s.strip() for s in value):
            problems.append(f"`{field}` contains an empty or non-string entry")
        if not value and field == "cannot_see":
            # WHY: it is the only field no static analysis can derive, and the only
            # one that stops the next person deleting a "redundant" gate.  An
            # instrument that believes it sees everything is wrong, so there is no
            # escape value.
            problems.append(
                "`cannot_see` may not be empty — every instrument is blind somewhere, "
                "and that blindness is why its neighbour is not redundant"
            )
        elif not value and field not in _MAY_BE_EMPTY:
            problems.append(f"`{field}` may not be empty")

    if "exit_contract" in spec:
        contract = spec["exit_contract"]
        if not isinstance(contract, dict):
            problems.append("`exit_contract` must be an object mapping exit code to meaning")
        elif not contract:
            problems.append("`exit_contract` may not be empty — every instrument returns something")
        else:
            for code, meaning in contract.items():
                if not re.fullmatch(r"\d+", str(code)):
                    problems.append(f"exit_contract key {code!r} is not an exit code")
                if not isinstance(meaning, str) or not meaning.strip():
                    problems.append(f"exit_contract[{code}] has no meaning")

    if "reachable_from" in spec and not isinstance(spec["reachable_from"], list):
        problems.append('`reachable_from` must be a list (use [] for "nothing invokes this")')

    for field in ("name", "invocation", "outcome", "cost"):
        if field in spec and (not isinstance(spec[field], str) or not spec[field].strip()):
            problems.append(f"`{field}` must be a non-empty string")

    if problems:
        raise CapabilityInvalid(f"{where} is invalid:\n  - " + "\n  - ".join(problems))
    return spec


def describe(spec: dict[str, Any], argv: Iterable[str] | None = None) -> bool:
    """Validate always; print and signal "stop here" only under `--describe`.

    Returns True when the caller should return immediately.
    """
    validate(spec, str(spec.get("id") or "capability declaration"))
    args = list(sys.argv[1:] if argv is None else argv)
    if "--describe" not in args:
        return False
    sys.stdout.write(json.dumps(spec, indent=2) + "\n")
    return True
