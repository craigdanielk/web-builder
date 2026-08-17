"""Tests for the determinism check.

Run from web-builder/:  python3 -m pytest scripts/test_determinism.py -v

The end-to-end assertion the plan asks for —

    a = build("cape-crypto"); b = build("cape-crypto")
    assert tree_diff(a, b, allowlist) == []

— is `test_two_builds_differ_only_in_allowlisted_fields`. It runs two real
builds and is therefore opt-in: set AURELIX_DETERMINISM_E2E=1 and point
AURELIX_DETERMINISM_CAPTURES at a capture bundle. Everything above it tests the
differ itself against fixtures, so the guard cannot silently stop failing just
because a build is slow or a bundle has moved.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from lib.determinism_diff import (  # noqa: E402
    normalise_path,
    normalise_value,
    tree_diff,
)

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
WEB_BUILDER = os.path.dirname(SCRIPTS)
ALLOWLIST_PATH = os.path.join(SCRIPTS, "determinism-allowlist.json")


@pytest.fixture
def allowlist():
    with open(ALLOWLIST_PATH) as fh:
        return json.load(fh)


def _write(root, rel, content):
    path = os.path.join(root, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = "wb" if isinstance(content, bytes) else "w"
    with open(path, mode) as fh:
        fh.write(content)
    return path


def _pair(tmp_path):
    a = os.path.join(str(tmp_path), "a")
    b = os.path.join(str(tmp_path), "b")
    os.makedirs(a)
    os.makedirs(b)
    return a, b


# ── the differ ────────────────────────────────────────────────────────────────

def test_identical_trees_produce_no_differences(tmp_path, allowlist):
    a, b = _pair(tmp_path)
    for root in (a, b):
        _write(root, "p/sections/01-hero.tsx", "export default function Hero(){}")
        _write(root, "p/site-spec.json", json.dumps({"pages": ["home"]}))
    unexplained, allowed = tree_diff(a, b, allowlist)
    assert unexplained == []
    assert allowed == []


def test_a_changed_generated_component_fails(tmp_path, allowlist):
    """The whole point: a .tsx that moves between runs is never allowlistable."""
    a, b = _pair(tmp_path)
    _write(a, "p/sections/01-hero.tsx", "const headline = 'Buy Bitcoin'")
    _write(b, "p/sections/01-hero.tsx", "const headline = 'Sell Bitcoin'")
    unexplained, _ = tree_diff(a, b, allowlist)
    assert len(unexplained) == 1
    assert unexplained[0]["file"] == "p/sections/01-hero.tsx"


def test_an_unallowlisted_json_field_is_named_not_just_flagged(tmp_path, allowlist):
    a, b = _pair(tmp_path)
    _write(a, "p/site-spec.json", json.dumps({"style": {"accent": "#1a1a1a"}}))
    _write(b, "p/site-spec.json", json.dumps({"style": {"accent": "#2b2b2b"}}))
    unexplained, _ = tree_diff(a, b, allowlist)
    assert [d["path"] for d in unexplained] == ["/style/accent"]


def test_allowlisted_timestamp_is_permitted(tmp_path, allowlist):
    a, b = _pair(tmp_path)
    _write(a, "p/checkpoint.json", json.dumps({"timestamp": "2026-08-17T13:00:00"}))
    _write(b, "p/checkpoint.json", json.dumps({"timestamp": "2026-08-17T14:00:00"}))
    unexplained, allowed = tree_diff(a, b, allowlist)
    assert unexplained == []
    assert [d["path"] for d in allowed] == ["/timestamp"]


def test_allowlist_entry_inside_a_list_matches_every_index(tmp_path, allowlist):
    """`[*]` is a literal list marker, not an fnmatch character class."""
    a, b = _pair(tmp_path)
    items = lambda t: json.dumps(  # noqa: E731
        {"line_items": [{"build_trace": {"completed_at": t}} for _ in range(3)]})
    _write(a, "p/bill-of-sale.json", items("2026-08-17T13:00:00+00:00"))
    _write(b, "p/bill-of-sale.json", items("2026-08-17T14:00:00+00:00"))
    unexplained, allowed = tree_diff(a, b, allowlist)
    assert unexplained == []
    assert len(allowed) == 3


def test_a_field_next_to_an_allowlisted_one_still_fails(tmp_path, allowlist):
    """Allowlisting /timestamp must not shield the rest of the same file."""
    a, b = _pair(tmp_path)
    _write(a, "p/checkpoint.json", json.dumps({"timestamp": "t1", "stage": "deploy"}))
    _write(b, "p/checkpoint.json", json.dumps({"timestamp": "t2", "stage": "review"}))
    unexplained, _ = tree_diff(a, b, allowlist)
    assert [d["path"] for d in unexplained] == ["/stage"]


def test_every_allowlist_entry_carries_a_reason(allowlist):
    for entry in allowlist["fields"] + allowlist["ignore"]:
        assert entry.get("reason", "").strip(), entry
        assert len(entry["reason"]) > 30, (
            "a one-word reason is not a justification: %r" % entry)


def test_a_list_that_changed_length_is_reported(tmp_path, allowlist):
    a, b = _pair(tmp_path)
    _write(a, "p/omitted-sections.json", json.dumps({"omitted": ["a", "b"]}))
    _write(b, "p/omitted-sections.json", json.dumps({"omitted": ["a"]}))
    unexplained, _ = tree_diff(a, b, allowlist)
    assert unexplained[0]["kind"] == "LEN"


def test_a_file_present_in_only_one_build_fails(tmp_path, allowlist):
    a, b = _pair(tmp_path)
    _write(a, "p/sections/09-cta.tsx", "x")
    _write(b, "p/sections/01-hero.tsx", "y")
    unexplained, _ = tree_diff(a, b, allowlist)
    kinds = sorted(d["kind"] for d in unexplained)
    assert kinds == ["ONLY-IN-A", "ONLY-IN-B"]


def test_a_missing_root_is_not_measured_not_a_pass(tmp_path, allowlist):
    a, _b = _pair(tmp_path)
    with pytest.raises(FileNotFoundError):
        tree_diff(a, os.path.join(str(tmp_path), "does-not-exist"), allowlist)


# ── harness normalisation ─────────────────────────────────────────────────────

def test_output_root_is_normalised_but_the_rest_of_the_path_is_not(tmp_path, allowlist):
    a, b = _pair(tmp_path)
    _write(a, "p/report.json", json.dumps({"shot": a + "/p/render-home.png"}))
    _write(b, "p/report.json", json.dumps({"shot": b + "/p/render-home.png"}))
    unexplained, _ = tree_diff(a, b, allowlist)
    assert unexplained == []

    _write(b, "p/report.json", json.dumps({"shot": b + "/p/render-about.png"}))
    unexplained, _ = tree_diff(a, b, allowlist)
    assert [d["path"] for d in unexplained] == ["/shot"]


def test_loopback_port_is_normalised_but_the_route_is_not(tmp_path, allowlist):
    a, b = _pair(tmp_path)
    _write(a, "p/conformance.json", json.dumps({"urls": ["http://127.0.0.1:57207/about"]}))
    _write(b, "p/conformance.json", json.dumps({"urls": ["http://127.0.0.1:57628/about"]}))
    unexplained, _ = tree_diff(a, b, allowlist)
    assert unexplained == []

    _write(b, "p/conformance.json", json.dumps({"urls": ["http://127.0.0.1:57628/wealth"]}))
    unexplained, _ = tree_diff(a, b, allowlist)
    assert [d["path"] for d in unexplained] == ["/urls[*]"]


def test_normalise_helpers():
    assert normalise_path("/line_items[3]/build_trace/at") == \
        "/line_items[*]/build_trace/at"
    assert normalise_value("http://localhost:1234/x", ()) == "http://localhost:<PORT>/x"
    assert normalise_value("/tmp/a/site", ("/tmp/a",)) == "<OUTPUT_ROOT>/site"
    assert normalise_value(7, ()) == 7


# ── end to end ────────────────────────────────────────────────────────────────

E2E = os.environ.get("AURELIX_DETERMINISM_E2E") == "1"
CAPTURES = os.environ.get("AURELIX_DETERMINISM_CAPTURES", "")


@pytest.mark.skipif(not E2E or not os.path.isdir(CAPTURES),
                    reason="set AURELIX_DETERMINISM_E2E=1 and "
                           "AURELIX_DETERMINISM_CAPTURES=<bundle dir>")
def test_two_builds_differ_only_in_allowlisted_fields(tmp_path, allowlist):
    roots = []
    for name in ("a", "b"):
        root = os.path.join(str(tmp_path), name)
        os.makedirs(root)
        proc = subprocess.run(
            [sys.executable, "scripts/orchestrate.py", "cape-crypto",
             "--preset", "cape-crypto", "--tenant", "cape-crypto",
             "--captures", CAPTURES,
             "--benchmark", "enterprise-payments-bvnk",
             "--max-pages", "5", "--no-pause", "--output-root", root],
            cwd=WEB_BUILDER, capture_output=True, text=True)
        assert proc.returncode == 0, proc.stdout[-3000:]
        roots.append(root)

    unexplained, _ = tree_diff(roots[0], roots[1], allowlist)
    assert unexplained == [], "non-deterministic: %s" % json.dumps(unexplained, indent=2)
