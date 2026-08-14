#!/usr/bin/env python3
"""
Captures wiring — a capture bundle is a complete source, not a crawl accessory.

WHY THIS EXISTS
---------------
`--captures` and `--routes` were read only inside orchestrate.py's `--from-url`
branch. Passed without it they were accepted and silently ignored: the build
harvested nothing, every section was omitted for having no sourced content, and
pre-flight blocked the deploy. The failure was honest but the flag was a lie,
and the wasted cycle read as a template defect.

`build-site-spec.js` also hard-required `extraction-data.json` and
`mapped-sections.json` — products of a live crawl — even when a capture bundle
carrying full HTML was supplied. That is what forced `--from-url`, and with it
a SECOND crawl of a site the audit had already crawled.

`buildPages()` depends on captures alone. The extraction data feeds the style
block, which the benchmark compiler supplies for any tenant with a benchmark.
So a captures-only spec is reachable, and these tests hold that line.

Run: python3 scripts/test_captures_wiring.py
"""

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
BUILD_SITE_SPEC = ROOT / "scripts" / "quality" / "build-site-spec.js"

PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}")
        if detail:
            print(f"      {detail}")


def _page_html(title, heading, body, cta="Sign up"):
    """A capture body with enough structure for harvestPage to find blocks."""
    return (
        "<!DOCTYPE html><html lang=\"en\"><head><title>" + title + "</title></head>"
        "<body>"
        "<nav><a href=\"/\">Home</a><a href=\"/wealth\">Wealth</a></nav>"
        "<section><h1>" + heading + "</h1><p>" + body + "</p>"
        "<a href=\"/signup\">" + cta + "</a></section>"
        "<section><h2>Why us</h2><p>" + body + "</p>"
        "<ul><li><h3>One</h3><p>First point of substance here.</p></li>"
        "<li><h3>Two</h3><p>Second point of substance here.</p></li></ul>"
        "</section>"
        "</body></html>"
    )


def make_bundle(dirpath: Path):
    """A minimal but valid audit capture bundle: two routes, real HTML."""
    records = [
        {
            "url": "https://example.test/",
            "http_status": 200,
            "html": _page_html("Home", "Buy Bitcoin Today", "Lowest fees in the country."),
        },
        {
            "url": "https://example.test/wealth",
            "http_status": 200,
            "html": _page_html("Wealth", "Managed Portfolios", "Built for advisers and their clients."),
        },
    ]
    (dirpath / "captures_manifest.json").write_text(json.dumps(records), encoding="utf-8")
    return dirpath


def run_site_spec(args, cwd):
    return subprocess.run(
        ["node", str(BUILD_SITE_SPEC)] + args,
        capture_output=True, text=True, cwd=str(cwd), timeout=120,
    )


def test_captures_only_spec():
    """A capture bundle alone produces a multi-page spec — no crawl artefacts."""
    print("\nbuild-site-spec.js: captures without extraction data")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        bundle = tmp / "bundle"
        bundle.mkdir(parents=True)
        make_bundle(bundle)
        out = tmp / "out"
        # An extraction dir that does not exist — this is the whole point.
        missing_extraction = tmp / "no-such-extraction"

        result = run_site_spec(
            [str(missing_extraction), "example", "--out", str(out),
             "--captures", str(bundle)],
            cwd=ROOT,
        )

        test(
            "exits 0 with a capture bundle and no extraction data",
            result.returncode == 0,
            f"exit={result.returncode} stderr={(result.stderr or '')[:300]}",
        )

        spec_path = out / "site-spec.json"
        test("writes site-spec.json", spec_path.exists(), f"missing at {spec_path}")
        if not spec_path.exists():
            return

        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        pages = spec.get("pages") or []
        test(
            "harvests one page per captured route",
            len(pages) == 2,
            f"got {len(pages)} page(s): {[p.get('page_id') for p in pages]}",
        )
        test(
            "pages carry sections harvested from the captured HTML",
            bool(pages) and all((p.get("sections") or []) for p in pages),
            f"section counts: {[len(p.get('sections') or []) for p in pages]}",
        )
        test(
            "records that style was not measured, rather than inventing tokens",
            (spec.get("style") or {}).get("source") in ("captures_only", "NOT_MEASURED", None),
            f"style.source={(spec.get('style') or {}).get('source')!r}",
        )


def test_routes_filter_applies():
    """--routes selects from the bundle; an unmatched route yields no page."""
    print("\nbuild-site-spec.js: --routes filters captures-only harvest")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        bundle = tmp / "bundle"
        bundle.mkdir(parents=True)
        make_bundle(bundle)
        out = tmp / "out"

        result = run_site_spec(
            [str(tmp / "no-such-extraction"), "example", "--out", str(out),
             "--captures", str(bundle), "--routes", "/wealth"],
            cwd=ROOT,
        )
        if result.returncode != 0:
            test("exits 0 with --routes", False,
                 f"exit={result.returncode} stderr={(result.stderr or '')[:300]}")
            return

        spec = json.loads((out / "site-spec.json").read_text(encoding="utf-8"))
        pages = spec.get("pages") or []
        test(
            "keeps only the requested route",
            len(pages) == 1,
            f"got {[p.get('page_id') for p in pages]}",
        )


class _Args:
    """Stand-in for argparse.Namespace with only the fields under test."""

    def __init__(self, from_url=None, captures=None, routes=None):
        self.from_url = from_url
        self.captures = captures
        self.routes = routes


def _orchestrate():
    import importlib.util
    sys.path.insert(0, str(ROOT / "scripts"))
    spec = importlib.util.spec_from_file_location("orch", ROOT / "scripts" / "orchestrate.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["orch"] = mod
    spec.loader.exec_module(mod)
    return mod


def test_source_mode_resolution():
    """--captures selects the captures source whether or not --from-url is given."""
    print("\norchestrate.py: resolve_source_mode")
    orch = _orchestrate()
    resolve = getattr(orch, "resolve_source_mode", None)
    if resolve is None:
        test("resolve_source_mode exists", False, "orchestrate.py has no resolve_source_mode")
        return

    with tempfile.TemporaryDirectory() as tmp:
        bundle = Path(tmp) / "bundle"
        bundle.mkdir(parents=True)
        make_bundle(bundle)

        mode, cdir, routes = resolve(_Args(captures=str(bundle), routes="/,/wealth"))
        test("captures alone resolves to the captures source", mode == "captures",
             f"mode={mode!r}")
        test("captures directory is resolved to a real path",
             cdir is not None and Path(cdir).exists(), f"cdir={cdir!r}")
        test("routes survive resolution", routes == "/,/wealth", f"routes={routes!r}")

        mode_url, _, _ = resolve(_Args(from_url="https://example.test", captures=str(bundle)))
        test("captures still win when --from-url is also given",
             mode_url == "captures", f"mode={mode_url!r}")

        mode_plain, cdir_plain, _ = resolve(_Args())
        test("no captures and no url resolves to the preset source",
             mode_plain == "preset" and cdir_plain is None,
             f"mode={mode_plain!r} cdir={cdir_plain!r}")

        mode_only_url, _, _ = resolve(_Args(from_url="https://example.test"))
        test("--from-url alone still resolves to the url source",
             mode_only_url == "url", f"mode={mode_only_url!r}")


def test_missing_captures_dir_refuses():
    """A named bundle that is not there must refuse, naming the path."""
    print("\norchestrate.py: a missing bundle refuses")
    orch = _orchestrate()
    resolve = getattr(orch, "resolve_source_mode", None)
    if resolve is None:
        test("resolve_source_mode exists", False, "orchestrate.py has no resolve_source_mode")
        return

    missing = "/tmp/definitely-not-a-capture-bundle-38f1"
    try:
        resolve(_Args(captures=missing))
        test("refuses a missing capture bundle", False, "returned instead of raising")
    except SystemExit:
        test("refuses a missing capture bundle", True)
    except Exception as exc:  # noqa: BLE001 - any explicit refusal naming the path
        test("refuses a missing capture bundle", missing in str(exc),
             f"raised {type(exc).__name__}: {exc}")


def main():
    print("=" * 62)
    print("  Captures wiring — a bundle is a source, not a crawl accessory")
    print("=" * 62)
    test_captures_only_spec()
    test_routes_filter_applies()
    test_source_mode_resolution()
    test_missing_captures_dir_refuses()
    print("\n" + "=" * 62)
    print(f"  {PASS} passed, {FAIL} failed")
    print("=" * 62)
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
