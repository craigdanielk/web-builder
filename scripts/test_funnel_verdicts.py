#!/usr/bin/env python3
"""funnel-verdicts — every (rule × route) cell is accounted, and every rule can fail.

WHY THIS EXISTS
---------------
The funnel rules are the first gate in this repo that grades the site's INTENT
rather than its code, and a gate about intent is the easiest kind to write so
that it can only say yes. Two properties are therefore asserted here per rule,
not per file:

  1. **Every rule has all three states reachable.** For each of the eight rules
     there is a fixture route that PASSes it, one that FAILs it, and one for
     which it is NOT_MEASURED with a reason. A rule that could not fail would be
     caught by the missing FAIL fixture; a rule that vacuously passes where it
     cannot apply would be caught by the missing NOT_MEASURED fixture.
  2. **Accounting.** pass + fail + not_measured == rules × routes, and every FAIL
     cell is either routed to a section slot or present in `unrouted` with a
     reason from the closed vocabulary. This is K1's discipline
     (`scripts/test_findings_verdicts.py`) applied to the funnel lane, because
     the two lanes merge into one verdict stream and a lane that quietly drops a
     FAIL is worse than a lane that reports nothing.

Two further assertions guard the merge itself: the output must be page-scoped by
`orchestrate._findings_are_page_scoped`'s own definition (a wrong shape is a
SILENT no-op in the build, not a failure), and this file's `slugify_route` /
`page_keys` must agree with K1's copies of them on a table of inputs — the two
lanes restate those functions rather than import each other, so the test is what
stops the copies drifting.

Run: python3 scripts/test_funnel_verdicts.py     (exit 0 = green)
"""

import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EVALUATOR = ROOT / "scripts" / "quality" / "funnel-verdicts.py"
K1 = ROOT / "scripts" / "quality" / "findings-to-verdicts.py"
RULES = ROOT / "skills" / "funnel-rules.json"

PASSED = 0
FAILED = 0


def test(name, condition, detail=""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print(f"  ✓ {name}")
    else:
        FAILED += 1
        print(f"  ✗ {name}")
        if detail:
            print(f"      {detail}")


def load_module(path, name):
    """Import a dashed-name module by path (its siblings are dashed too)."""
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


FV = load_module(EVALUATOR, "funnel_verdicts")


# ---------------------------------------------------------------------------
# Fixture builder — a synthetic build dir in the real on-disk shape
# ---------------------------------------------------------------------------

def sec(archetype, variant="v", uid=None, index=None, **slots):
    """One section artifact spec. slots are `name=(source, value)` pairs."""
    return {"archetype": archetype, "variant": variant, "uid": uid,
            "index": index, "slots": slots}


def make_build(root: Path, pages: list[dict]) -> Path:
    """Write site-manifest.json + section-artifacts/<page>/NN-<arch>.json.

    `pages` entries: {id, route, nav: [url], sections: [sec(...)], build: bool}.
    `build: False` writes the manifest page but NO artifact directory — a route
    that planned sections and built none, which is the real NOT_MEASURED case
    (23 of cape-crypto's 44 planned sections were omitted).
    """
    root.mkdir(parents=True, exist_ok=True)
    manifest = {"project": "fixture", "pages": []}
    for page in pages:
        manifest["pages"].append({
            "id": page["id"],
            "route": page.get("route", "/" + page["id"]),
            "page_type": page.get("page_type", "content"),
            "sections": [],  # deliberately empty: the PLAN is never graded
            "nav": {"links": [{"label": u, "href": u}
                              for u in page.get("nav", [])]},
        })
        if page.get("build", True):
            page_dir = root / "section-artifacts" / page["id"]
            page_dir.mkdir(parents=True, exist_ok=True)
            for i, s in enumerate(page["sections"], start=1):
                artifact = {
                    "tsx": "// fixture",
                    "archetype": s["archetype"],
                    "variant": s["variant"],
                    "origin": "local_template",
                    "assets": [],
                    "animation": None,
                    "provenance": [
                        {"slot": name, "value": value, "source": source}
                        for name, (source, value) in sorted(s["slots"].items())
                    ],
                }
                if s["uid"] is not None:
                    artifact["section_uid"] = s["uid"]
                if s["index"] is not None:
                    artifact["section_index"] = s["index"]
                name = s["archetype"].lower().replace("-", "_")
                (page_dir / f"{i:02d}-{name}.json").write_text(
                    json.dumps(artifact, indent=1), encoding="utf-8")
    (root / "site-manifest.json").write_text(json.dumps(manifest, indent=1),
                                             encoding="utf-8")
    return root


def run_eval(build_dir: Path, out_dir: Path, rules: Path = RULES):
    return subprocess.run(
        [sys.executable, str(EVALUATOR), str(build_dir),
         "--out-dir", str(out_dir), "--rules", str(rules)],
        capture_output=True, text=True, cwd=str(ROOT))


def evaluate(build_dir: Path, rules: Path = RULES) -> dict:
    doc = FV.load_rules(rules)
    return FV.evaluate(doc, FV.load_build(build_dir))


def cell(result: dict, rule_id: str, page_id: str) -> dict:
    hits = [c for c in result["rule_verdicts"]
            if c["rule_id"] == rule_id and c["page_id"] == page_id]
    assert len(hits) == 1, f"{rule_id}/{page_id}: {len(hits)} cells, expected 1"
    return hits[0]


HARVESTED = "harvested"
EMPTY = "empty"
NAV = ["https://x.example.com/signup"]

# One fixture build per rule: three routes named `pass`, `fail`, `nm`, each
# constructed for that rule's three states. Every route is also graded by the
# other seven rules, which is why the accounting assertion runs on each build.
PER_RULE_FIXTURES = {
    "funnel_route_closes_with_conversion": {
        "pass": [sec("HERO"), sec("CTA", uid="p1",
                                  cta_text=(HARVESTED, "Go"),
                                  cta_url=(HARVESTED, NAV[0]))],
        "fail": [sec("HERO"), sec("FAQ")],
        "nm": None,  # no artifact dir -> route built no sections
    },
    "funnel_route_offers_an_action": {
        "pass": [sec("HERO", primary_cta_url=(HARVESTED, NAV[0]),
                     primary_cta_text=(HARVESTED, "Go"))],
        "fail": [sec("HERO", primary_cta_url=(EMPTY, ""),
                     primary_cta_text=(EMPTY, ""))],
        "nm": None,
    },
    "funnel_route_opens_with_hero": {
        "pass": [sec("HERO"), sec("FAQ")],
        "fail": [sec("FEATURES"), sec("FAQ")],
        "nm": None,
    },
    "funnel_conversion_has_a_sourced_action": {
        "pass": [sec("HERO"), sec("CTA", uid="p2", cta_text=(HARVESTED, "Go"),
                                  cta_url=(HARVESTED, NAV[0]))],
        "fail": [sec("HERO"), sec("CTA", uid="f2", cta_text=(EMPTY, ""),
                                  cta_url=(EMPTY, ""))],
        "nm": [sec("HERO"), sec("FAQ")],  # no conversion section
    },
    "funnel_conversion_destination_reachable_from_nav": {
        "pass": [sec("HERO"), sec("CTA", uid="p3", cta_text=(HARVESTED, "Go"),
                                  cta_url=(HARVESTED, NAV[0]))],
        "fail": [sec("HERO"), sec("CTA", uid="f3", cta_text=(HARVESTED, "Go"),
                                  cta_url=(HARVESTED,
                                           "https://elsewhere.example.com/x"))],
        # a conversion section exists but carries no sourced destination
        "nm": [sec("HERO"), sec("CTA", uid="n3", cta_text=(HARVESTED, "Go"),
                                cta_url=(EMPTY, ""))],
    },
    "funnel_trust_precedes_first_conversion": {
        "pass": [sec("HERO"), sec("TRUST-BADGES"),
                 sec("CTA", uid="p4", cta_text=(HARVESTED, "Go"),
                     cta_url=(HARVESTED, NAV[0]))],
        "fail": [sec("HERO"), sec("CTA", uid="f4", cta_text=(HARVESTED, "Go"),
                                  cta_url=(HARVESTED, NAV[0])),
                 sec("TRUST-BADGES")],
        "nm": [sec("HERO"), sec("TRUST-BADGES")],
    },
    "funnel_first_conversion_within_reach": {
        "pass": [sec("HERO"), sec("FEATURES"),
                 sec("CTA", uid="p5", cta_text=(HARVESTED, "Go"),
                     cta_url=(HARVESTED, NAV[0]))],
        "fail": [sec("HERO"), sec("FEATURES"), sec("FAQ"), sec("ABOUT"),
                 sec("CTA", uid="f5", cta_text=(HARVESTED, "Go"),
                     cta_url=(HARVESTED, NAV[0]))],
        "nm": [sec("HERO"), sec("FEATURES")],
    },
    "funnel_no_adjacent_conversion_pair": {
        "pass": [sec("HERO"),
                 sec("CTA", uid="p6a", cta_text=(HARVESTED, "Go"),
                     cta_url=(HARVESTED, NAV[0])),
                 sec("FEATURES"),
                 sec("CTA", uid="p6b", cta_text=(HARVESTED, "Go"),
                     cta_url=(HARVESTED, NAV[0]))],
        "fail": [sec("HERO"),
                 sec("CTA", uid="f6a", cta_text=(HARVESTED, "Go"),
                     cta_url=(HARVESTED, NAV[0])),
                 sec("CTA", uid="f6b", cta_text=(HARVESTED, "Go"),
                     cta_url=(HARVESTED, NAV[0]))],
        # exactly one conversion section: adjacency is undefined, not true
        "nm": [sec("HERO"), sec("CTA", uid="n6", cta_text=(HARVESTED, "Go"),
                                cta_url=(HARVESTED, NAV[0]))],
    },
}

EXPECTED_STATE = {"pass": "PASS", "fail": "FAIL", "nm": "NOT_MEASURED"}


def build_for_rule(tmp: Path, rule_id: str) -> Path:
    spec = PER_RULE_FIXTURES[rule_id]
    pages = []
    for name in ("pass", "fail", "nm"):
        sections = spec[name]
        pages.append({"id": name, "route": f"/{name}", "nav": NAV,
                      "sections": sections or [], "build": sections is not None})
    return make_build(tmp / rule_id.replace("_", "-"), pages)


# ---------------------------------------------------------------------------

def test_every_rule_reaches_every_state():
    print("\nEvery rule: one route PASSes it, one FAILs it, one cannot measure it")
    doc = FV.load_rules(RULES)
    declared = [r["id"] for r in doc["rules"]]
    test("every declared rule has a three-state fixture",
         sorted(declared) == sorted(PER_RULE_FIXTURES),
         f"declared={sorted(declared)} fixtures={sorted(PER_RULE_FIXTURES)}")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for rule_id in declared:
            result = evaluate(build_for_rule(tmp, rule_id))
            for page, want in EXPECTED_STATE.items():
                got = cell(result, rule_id, page)
                test(f"{rule_id} · {page} route is {want}",
                     got["state"] == want,
                     f"got {got['state']}: {got['detail']}")
                if want == "NOT_MEASURED":
                    test(f"{rule_id} · NOT_MEASURED carries a reason",
                         bool(got["detail"].strip()))


def test_accounting_invariant_holds_on_every_fixture():
    print("\nAccounting — every cell accounted, every FAIL routed or counted")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for rule_id in PER_RULE_FIXTURES:
            result = evaluate(build_for_rule(tmp, rule_id))
            s = result["summary"]
            test(f"{rule_id}: pass+fail+nm == cells",
                 s["pass"] + s["fail"] + s["not_measured"] == s["cells"],
                 json.dumps(s, sort_keys=True))
            test(f"{rule_id}: cells == rules x routes",
                 s["cells"] == s["rules"] * s["routes"],
                 f"{s['cells']} != {s['rules']}*{s['routes']}")
            test(f"{rule_id}: check_accounting is silent",
                 FV.check_accounting(result) == "",
                 FV.check_accounting(result))
            fails = {(c["rule_id"], c["page_id"])
                     for c in result["rule_verdicts"] if c["state"] == "FAIL"}
            counted = {(r["rule_id"], r["page_id"]) for r in result["unrouted"]}
            routed = {(c["rule_id"], c["page_id"])
                      for c in result["rule_verdicts"]
                      if c["state"] == "FAIL" and c["sections_named"]}
            test(f"{rule_id}: no FAIL on the floor",
                 not (fails - (counted | routed)),
                 f"orphans: {sorted(fails - (counted | routed))}")
            test(f"{rule_id}: every unrouted reason is declared",
                 all(r["reason"] in FV.UNROUTED_REASONS
                     for r in result["unrouted"]),
                 json.dumps([r["reason"] for r in result["unrouted"]]))


def test_section_scoped_fails_land_on_the_offender():
    print("\nA section-scoped FAIL names the offending section, and only it")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        result = evaluate(build_for_rule(
            Path(td), "funnel_conversion_has_a_sourced_action"))
        verdicts = result["copy_findings"]
        test("the failing route carries a verdict", "fail" in verdicts,
             json.dumps(sorted(verdicts)))
        test("the verdict lands on the offending section's uid",
             list(verdicts.get("fail", {})) == ["f2"],
             json.dumps(verdicts.get("fail", {}), sort_keys=True))
        test("the passing route carries no verdict", "pass" not in verdicts,
             json.dumps(sorted(verdicts)))
        entry = verdicts.get("fail", {}).get("f2", {})
        test("the verdict's rule_id is the funnel rule",
             entry.get("rule_id") == "funnel_conversion_has_a_sourced_action",
             json.dumps(entry, sort_keys=True))
        test("the verdict carries a remedy hint",
             bool(str(entry.get("remedy_hint") or "").strip()))
        # A route-scoped FAIL must NOT produce a verdict: revising a FAQ's copy
        # cannot add the CTA the route is missing.
        result2 = evaluate(build_for_rule(
            tmp, "funnel_route_closes_with_conversion"))
        test("a route-scoped FAIL produces no verdict slot",
             result2["summary"]["verdict_slots"] == 0,
             json.dumps(result2["copy_findings"], sort_keys=True))
        test("a route-scoped FAIL is counted as route-scoped-rule",
             any(r["reason"] == "route-scoped-rule"
                 for r in result2["unrouted"]),
             json.dumps(result2["unrouted"], sort_keys=True))


def test_unaddressable_section_is_counted_not_guessed():
    print("\nA section with no uid and no index is counted, never guessed at")
    with tempfile.TemporaryDirectory() as td:
        build = make_build(Path(td) / "b", [{
            "id": "anon", "route": "/anon", "nav": NAV,
            "sections": [sec("HERO"),
                         sec("CTA", cta_text=(EMPTY, ""), cta_url=(EMPTY, ""))],
        }])
        result = evaluate(build)
        got = cell(result, "funnel_conversion_has_a_sourced_action", "anon")
        test("the cell still FAILs", got["state"] == "FAIL", got["detail"])
        test("no verdict is invented for an unaddressable section",
             result["summary"]["verdict_slots"] == 0,
             json.dumps(result["copy_findings"], sort_keys=True))
        test("it is counted as section-has-no-slot-key",
             any(r["reason"] == "section-has-no-slot-key"
                 for r in result["unrouted"]),
             json.dumps(result["unrouted"], sort_keys=True))


def test_the_plan_is_never_graded():
    print("\nThe manifest's planned sections are never what is graded")
    with tempfile.TemporaryDirectory() as td:
        build = make_build(Path(td) / "b", [{
            "id": "homepage", "route": "/", "nav": NAV,
            "sections": [sec("HERO"), sec("FAQ")],
        }])
        # Plant a perfect PLAN on the manifest. If the evaluator read it, the
        # route would close with a CTA and the rule would pass.
        manifest = json.loads((build / "site-manifest.json").read_text())
        manifest["pages"][0]["sections"] = [
            {"position": 1, "archetype": "HERO", "variant": "v"},
            {"position": 2, "archetype": "FAQ", "variant": "v"},
            {"position": 3, "archetype": "CTA", "variant": "v"},
        ]
        (build / "site-manifest.json").write_text(json.dumps(manifest, indent=1))
        result = evaluate(build)
        got = cell(result, "funnel_route_closes_with_conversion", "homepage")
        test("a planned-but-unbuilt CTA does not earn a PASS",
             got["state"] == "FAIL", f"{got['state']}: {got['detail']}")
        test("the detail names the section that actually closes the route",
             "FAQ" in got["detail"], got["detail"])


def test_determinism_byte_identical():
    print("\nDeterminism — two runs, byte-identical")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        build = build_for_rule(tmp, "funnel_trust_precedes_first_conversion")
        r1 = run_eval(build, tmp / "o1")
        r2 = run_eval(build, tmp / "o2")
        test("both runs exit 0", r1.returncode == 0 and r2.returncode == 0,
             f"{r1.returncode}/{r2.returncode}: {r1.stderr[-300:]}")
        a = (tmp / "o1" / "funnel-verdicts.json").read_bytes()
        b = (tmp / "o2" / "funnel-verdicts.json").read_bytes()
        test("funnel-verdicts.json is byte-identical across runs", a == b,
             f"{len(a)} vs {len(b)} bytes")
        test("nothing timestamp-shaped is serialised",
             b"generated_at" not in a and b"timestamp" not in a)


def test_merges_into_the_consumers_own_shape():
    print("\nThe verdict stream merges — asserted against orchestrate.py itself")
    spec = importlib.util.spec_from_file_location(
        "orch_funnel", ROOT / "scripts" / "orchestrate.py")
    orch = importlib.util.module_from_spec(spec)
    sys.modules["orch_funnel"] = orch
    spec.loader.exec_module(orch)
    with tempfile.TemporaryDirectory() as td:
        result = evaluate(build_for_rule(
            Path(td), "funnel_conversion_has_a_sourced_action"))
        stream = result["copy_findings"]
        test("the consumer detects the output as page-scoped",
             orch._findings_are_page_scoped(stream),
             json.dumps(stream, sort_keys=True))
        entry = orch.resolve_page_entry(stream, {"id": "fail", "route": "/fail"})
        test("the consumer's page lookup resolves the funnel page",
             isinstance(entry, dict) and "f2" in entry,
             json.dumps(entry, sort_keys=True) if entry else "no entry")
        slot = orch.section_identity({"section_uid": "f2", "index": 1}, 1)
        test("the consumer's slot key matches the emitted slot key",
             str(slot) in (entry or {}), f"section_identity -> {slot!r}")
        FV.validate_consumed_shape(stream)
        test("validate_consumed_shape accepts the real output", True)


def test_slug_vocabulary_agrees_with_k1():
    print("\nThe restated route vocabulary agrees with K1's copy of it")
    k1 = load_module(K1, "k1_findings_to_verdicts")
    cases = ["/", "", "/wealth", "/wealth/", "wealth", "/a/b",
             "https://x.example.com/merchants/", "/x?y=1#z", None,
             "/Contact-Us"]
    mismatch = [c for c in cases
                if FV.slugify_route(c) != k1.slugify_route(c)]
    test("slugify_route agrees with K1 on every case", not mismatch,
         f"mismatched: {mismatch}")
    pages = [{"id": "homepage", "route": "/", "page_type": "homepage"},
             {"page_type": "content-page", "route": "/wealth"},
             {"id": "about", "route": "/about", "page_type": "about"}]
    bad = [p for p in pages if FV.page_keys(p) != k1.page_keys(p)]
    test("page_keys agrees with K1 on every case", not bad, f"mismatched: {bad}")


def test_nav_prefix_matching_has_a_boundary():
    print("\nNav reachability is a path prefix, not a string prefix")
    nav = ["https://x.example.com/hc/en-za", "https://x.example.com/sign"]
    test("an exact nav link is reachable",
         FV.url_reachable("https://x.example.com/hc/en-za", nav))
    test("a deeper path under a nav link is reachable",
         FV.url_reachable("https://x.example.com/hc/en-za/requests/new", nav))
    test("a fragment does not defeat the match",
         FV.url_reachable("https://x.example.com/hc/en-za#top", nav))
    test("a sibling that merely shares a prefix is NOT reachable",
         not FV.url_reachable("https://x.example.com/signup", nav))
    test("an unrelated host is not reachable",
         not FV.url_reachable("https://other.example.com/hc/en-za", nav))
    test("an empty target is not reachable", not FV.url_reachable("", nav))
    test("no nav at all reaches nothing",
         not FV.url_reachable("https://x.example.com/a", []))


def test_exit_codes_and_rule_file_validation():
    print("\nExit codes: 3 NOT_MEASURED · 64 usage · 1 bad rule file")
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        empty = make_build(tmp / "empty", [{"id": "a", "route": "/a", "nav": [],
                                           "sections": [], "build": False}])
        r = run_eval(empty, tmp / "o")
        test("exit 3 when no section was built", r.returncode == 3,
             f"exit {r.returncode}: {r.stderr[-300:]}")
        test("exit 3 says it is not a pass", "not a pass" in r.stderr,
             r.stderr[-200:])
        test("exit 3 writes no verdict file",
             not (tmp / "o" / "funnel-verdicts.json").exists())

        r = run_eval(tmp / "nope", tmp / "o2")
        test("exit 64 on a missing build dir", r.returncode == 64,
             f"exit {r.returncode}")

        good = build_for_rule(tmp, "funnel_route_opens_with_hero")
        r = run_eval(good, tmp / "o3", rules=tmp / "no-rules.json")
        test("exit 64 on a missing rule file", r.returncode == 64,
             f"exit {r.returncode}")

        doc = json.loads(RULES.read_text())
        for label, mutate in (
            ("unknown assertion.kind",
             lambda d: d["rules"][0]["assertion"].__setitem__("kind", "vibes")),
            ("unknown applies_to.kind",
             lambda d: d["rules"][0]["applies_to"].__setitem__("kind", "always")),
            ("rule id outside funnel_*",
             lambda d: d["rules"][0].__setitem__("id", "cta_presence")),
            ("undeclared family",
             lambda d: d["rules"][0]["assertion"].__setitem__("family", "vibes")),
            ("missing remedy_hint",
             lambda d: d["rules"][0].__setitem__("remedy_hint", "")),
        ):
            bad = json.loads(json.dumps(doc))
            mutate(bad)
            path = tmp / f"bad-{label.replace(' ', '-')}.json"
            path.write_text(json.dumps(bad))
            r = run_eval(good, tmp / "o4", rules=path)
            test(f"exit 1 on {label}", r.returncode == 1,
                 f"exit {r.returncode}: {r.stderr[-200:]}")


def test_the_committed_build_if_present():
    print("\nThe committed cape-crypto build (read-only; skipped if absent)")
    build = ROOT / "output" / "cape-crypto"
    if not (build / "section-artifacts").is_dir():
        test("no committed build to measure — NOT_MEASURED, not a pass", True,
             "section-artifacts/ absent")
        return
    result = evaluate(build)
    s = result["summary"]
    test("40 cells (8 rules x 5 routes)", s["cells"] == 40, json.dumps(s["by_rule"]))
    test("accounting holds on the real build",
         FV.check_accounting(result) == "", FV.check_accounting(result))
    test("the real build FAILs at least one rule — the gate is not vacuous",
         s["fail"] > 0, json.dumps(s, sort_keys=True))
    test("the real build has NOT_MEASURED cells reported, not hidden",
         s["not_measured"] > 0, json.dumps(s, sort_keys=True))
    homepage = cell(result, "funnel_route_closes_with_conversion", "homepage")
    test("the homepage's missing closing CTA is FAILed",
         homepage["state"] == "FAIL", homepage["detail"])


def main():
    print("=" * 70)
    print("  funnel-verdicts — three states per rule, every cell accounted")
    print("=" * 70)
    test_every_rule_reaches_every_state()
    test_accounting_invariant_holds_on_every_fixture()
    test_section_scoped_fails_land_on_the_offender()
    test_unaddressable_section_is_counted_not_guessed()
    test_the_plan_is_never_graded()
    test_determinism_byte_identical()
    test_merges_into_the_consumers_own_shape()
    test_slug_vocabulary_agrees_with_k1()
    test_nav_prefix_matching_has_a_boundary()
    test_exit_codes_and_rule_file_validation()
    test_the_committed_build_if_present()
    print("\n" + "=" * 70)
    print(f"  {PASSED} passed, {FAILED} failed")
    print("=" * 70)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
