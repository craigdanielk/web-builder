#!/usr/bin/env python3
"""The CVR loop driver — one bounded pass from a build to a better build.

Task K3 of docs/superpowers/plans/2026-08-17-close-the-gaps.md.

WHAT THIS IS

  build → audit the BUILT site → K1 + K2 → merged copy-findings.json →
  rebuild with --copy-findings → diff report

K1 (`scripts/quality/findings-to-verdicts.py`) and K2
(`scripts/quality/funnel-verdicts.py`) both already emit `copy_findings` in the
one page-scoped shape `orchestrate._findings_are_page_scoped()` recognises.
Nothing drove them. This drives them, once — `--max-iterations` defaults to 1
because this is a pass, not a daemon.

WHY THE AUDIT MUST HIT THE BUILT SITE

K1's real run compiled 562 findings into ONE verdict. Not a defect in K1: that
bundle audited the SOURCE site, so its axe selectors name the source theme's
classes, which match nothing the build owns. The selector lane can only fire
against an audit of the built site. So this loop serves the built site itself:
`--deploy` leaves a production `next build` and an installed node_modules in
`<build>/site`, and the loop starts its own `npm run start` on a free port,
audits `http://localhost:<port>` with `--axe --store-html`, and kills the
server. orchestrate.py's own render audit starts and kills a server inside its
own process; there is nothing left running for us to reuse.

If that cannot be done here — no built site, no axe.min.js, no Playwright
browser, server refuses to come up — the audit lane is recorded NOT_MEASURED
**with a reason** and the loop CONTINUES. K2's funnel lane needs no server and
must still run. Findings are never invented to fill the gap; the absence is
named in the report.

COMPLIANCE IS FATAL

Cape Crypto is a licensed FSP whose disclaimer #3 sits one word from a
prohibited term. A build that exits non-zero, or whose compliance gate FAILs,
ABORTS the loop with that build's own exit code. There is no "partial report"
that swallows a failed build — the report is written, it records which build
aborted and why, and the process exits with the build's code.

`orchestrate.record_gate_result` only PRINTS; GATE_RESULTS is never serialised
(grep: 4 hits, all in-memory). So the compliance verdict is read off the build's
captured stdout — `GATE compliance: FAIL` / `BUILD FAILURE [compliance]` — and
cross-checked against the exit code. Both are recorded.

DETERMINISM, AND THE CONTROL FIELD

The build is deterministic at 0 LLM calls, so two builds from the same inputs
are byte-identical and any diff in this report is attributable to the verdicts
file alone. That is asserted, not assumed: every non-verdict input (captures
bundle, benchmark, preset, brief, funnel rules, extraction store) is digested
before build A and again before build B, and
`control.non_verdict_inputs_unchanged` records whether they agreed. A false
there invalidates the diff and is reported as such.

EXITS
  0   the pass completed (FAIL verdicts are findings, not loop failures)
  1   an accounting failure inside the loop
  3   NOT_MEASURED — nothing could be measured at all
  64  usage
  *   on abort: the aborting build's own exit code, verbatim

THE SEAM
`--orchestrate-cmd` replaces the build command and `--audit-cmd` the audit
command (both shlex-split, argv appended). The tests drive the loop's control
flow against stub scripts; no test runs a real build.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shlex
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # web-builder/
REPO_ROOT = ROOT.parent                                # services/aurelix-ag/
AUDIT_REPO = REPO_ROOT / "aurelix-uiux-audit"

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_NOT_MEASURED = 3
EXIT_USAGE = 64

# Printed by orchestrate.record_gate_result / record_build_failure. The gate
# results are in-memory only, so stdout is the only channel that carries them.
COMPLIANCE_FAIL_MARKERS = (
    "GATE compliance: FAIL",
    "BUILD FAILURE [compliance]",
)
COMPLIANCE_NOT_MEASURED_MARKER = "GATE compliance: NOT_MEASURED"
COMPLIANCE_PASS_MARKER = "GATE compliance: PASS"
BUILD_FAILURE_MARKER = "BUILD FAILURE ["

# Where axe.min.js may live. Not vendored — the audit engine refuses to pin a
# copy, and so do we. Absent → the selector lane is NOT_MEASURED, named.
AXE_CANDIDATES = (
    ROOT / "scripts" / "quality" / "node_modules" / "axe-core" / "axe.min.js",
    AUDIT_REPO / "node_modules" / "axe-core" / "axe.min.js",
    Path("/opt/homebrew/lib/node_modules/pa11y/node_modules/axe-core/axe.min.js"),
)

SERVER_START_TIMEOUT_S = 60


# ─────────────────────────────────────────────────────────────────────────────
# digests — the control field
# ─────────────────────────────────────────────────────────────────────────────

def _digest_path(path: Path) -> str:
    """Content digest of a file, or of a directory tree (paths + bytes).

    Missing → "absent". A directory is walked in sorted order so the digest is
    stable across filesystems.
    """
    if not path.exists():
        return "absent"
    h = hashlib.sha256()
    if path.is_file():
        h.update(path.read_bytes())
        return h.hexdigest()
    for p in sorted(path.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(path)).encode())
            h.update(p.read_bytes())
    return h.hexdigest()


def non_verdict_input_digests(cfg: dict) -> dict:
    """Digest every build input that is NOT the verdicts file.

    If these agree across the two builds, the only thing that changed is
    --copy-findings, and the diff in this report is attributable to it.
    """
    out = {}
    for label, path in cfg.items():
        if path is None:
            out[label] = "not-passed"
        else:
            out[label] = _digest_path(Path(path))
    return out


# ─────────────────────────────────────────────────────────────────────────────
# the build
# ─────────────────────────────────────────────────────────────────────────────

def build_argv(base_cmd: list[str], project: str, output_root: Path,
               args: argparse.Namespace, copy_findings: Path | None) -> list[str]:
    """The orchestrate.py invocation. --deploy is the local production build
    that leaves a servable site; it is never a Vercel publish (--publish is
    deliberately not passed, ever, from here)."""
    argv = list(base_cmd) + [project, "--output-root", str(output_root)]
    if args.tenant:
        argv += ["--tenant", args.tenant]
    if args.captures:
        argv += ["--captures", str(args.captures)]
    if args.routes:
        argv += ["--routes", args.routes]
    if args.benchmark:
        argv += ["--benchmark", args.benchmark]
    if args.preset:
        argv += ["--preset", args.preset]
    if args.target_platform:
        argv += ["--target-platform", args.target_platform]
    if args.deploy:
        argv += ["--deploy"]
    if copy_findings is not None:
        argv += ["--copy-findings", str(copy_findings)]
    return argv


def run_build(label: str, argv: list[str], log_path: Path, timeout: int) -> dict:
    """Run one build, capture its stdout, read the compliance verdict off it."""
    log_path.parent.mkdir(parents=True, exist_ok=True)
    print(f"\n─── BUILD {label} ───")
    print("  " + " ".join(shlex.quote(a) for a in argv))
    started = time.time()
    try:
        proc = subprocess.run(argv, cwd=str(ROOT), capture_output=True,
                              text=True, timeout=timeout)
        out, err, rc, timed_out = proc.stdout, proc.stderr, proc.returncode, False
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout if isinstance(exc.stdout, str) else (exc.stdout or b"").decode(
            "utf-8", "replace")
        err = exc.stderr if isinstance(exc.stderr, str) else (exc.stderr or b"").decode(
            "utf-8", "replace")
        rc, timed_out = 124, True
    elapsed = round(time.time() - started, 1)
    log_path.write_text(out + ("\n--- STDERR ---\n" + err if err else ""),
                        encoding="utf-8")

    failed_stages = sorted({
        line.split(BUILD_FAILURE_MARKER, 1)[1].split("]", 1)[0]
        for line in out.splitlines() if BUILD_FAILURE_MARKER in line
    })

    compliance = "not_reported"
    if any(m in out for m in COMPLIANCE_FAIL_MARKERS):
        compliance = "fail"
    elif COMPLIANCE_NOT_MEASURED_MARKER in out:
        compliance = "not_measured"
    elif COMPLIANCE_PASS_MARKER in out:
        compliance = "pass"

    result = {
        "label": label,
        "argv": argv,
        "exit_code": rc,
        "timed_out": timed_out,
        "elapsed_s": elapsed,
        "compliance_gate": compliance,
        "recorded_failure_stages": failed_stages,
        "log": str(log_path),
    }
    print(f"  exit {rc} · compliance {compliance}"
          + (f" · failures {failed_stages}" if failed_stages else "")
          + f" · {elapsed}s · log {log_path}")
    return result


def build_is_fatal(result: dict, tolerated: frozenset = frozenset()) -> tuple[bool, str]:
    """A non-zero build, or a compliance FAIL, aborts the loop. Fatally.

    Both are checked, not just the exit code: a compliance FAIL records a build
    failure and so already implies exit 1, but naming the compliance channel is
    what makes the abort reason readable in the report instead of a bare 1 — and
    if that link ever breaks, the gate line alone still aborts.

    `tolerated` is the explicit, operator-named set of OTHER recorded-failure
    stages the loop is allowed to proceed past — it exists because a pre-existing
    failure in a gate this task does not own (a `dna_type_scale` conformance
    violation, say) would otherwise make the loop unmeasurable. It is narrow by
    construction: an exit is only tolerable when EVERY recorded failure stage was
    named, and `compliance` can never be named (refused at usage). A tolerated
    exit is recorded in the report, never silently.
    """
    if result["compliance_gate"] == "fail":
        return True, "compliance gate FAILed"
    if result["exit_code"] == 0:
        return False, ""
    stages = set(result.get("recorded_failure_stages") or [])
    if stages and stages <= set(tolerated):
        result["tolerated_failure_stages"] = sorted(stages)
        return False, ""
    return True, f"build exited {result['exit_code']}" + (
        f" with recorded failure(s) {sorted(stages)}" if stages else "")


# ─────────────────────────────────────────────────────────────────────────────
# the audit of the built site
# ─────────────────────────────────────────────────────────────────────────────

def free_port() -> int:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def resolve_axe_js(explicit: str | None) -> tuple[str | None, str]:
    if explicit:
        p = Path(explicit)
        if p.is_file():
            return str(p), "explicit"
        return None, f"--axe-js {explicit} is not a file"
    env = os.environ.get("AXE_JS")
    if env and Path(env).is_file():
        return env, "AXE_JS"
    for cand in AXE_CANDIDATES:
        if cand.is_file():
            return str(cand), "discovered"
    npx = Path.home() / ".npm" / "_npx"
    if npx.is_dir():
        for cand in sorted(npx.glob("*/node_modules/axe-core/axe.min.js")):
            return str(cand), "npx-cache"
    return None, "axe.min.js not found (not vendored; set AXE_JS)"


def serve_site(site_dir: Path,
               serve_cmd: list[str] | None = None) -> tuple[subprocess.Popen | None, int, str]:
    """Start the production server against the built site. Returns (proc, port, reason).

    `serve_cmd` is the third seam: `npm run start --` by default, `--port <n>`
    appended. The preconditions below are checked whatever the command, because
    a server started against a directory with no `.next` would serve a 404 to
    every route and the audit would report a site of empty pages as measured.
    """
    if not (site_dir / "package.json").is_file():
        return None, 0, f"no package.json at {site_dir}"
    if not (site_dir / ".next").is_dir():
        return None, 0, (f"no production build at {site_dir}/.next — "
                         "the build was not run with --deploy")
    if not (site_dir / "node_modules").is_dir():
        return None, 0, f"no node_modules at {site_dir} — dependencies never installed"
    port = free_port()
    proc = subprocess.Popen(
        list(serve_cmd or ["npm", "run", "start", "--"]) + ["--port", str(port)],
        cwd=str(site_dir), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(SERVER_START_TIMEOUT_S):
        time.sleep(1)
        if proc.poll() is not None:
            return None, port, f"server exited {proc.returncode} before accepting"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect(("127.0.0.1", port))
            s.close()
            return proc, port, ""
        except OSError:
            continue
    proc.kill()
    proc.wait(timeout=5)
    return None, port, f"server did not accept within {SERVER_START_TIMEOUT_S}s"


def built_routes(build_dir: Path) -> list[str]:
    """The routes this build actually emitted, from site-manifest.json.

    MEASURED 2026-08-17, and the reason this function exists: the built
    cape-crypto site's nav hrefs are absolute `https://capecrypto.com/...`, so a
    same-origin crawl of the served site reaches exactly ONE page — the seed —
    and `coverage.reached_count` came back 1 of 5 routes. Handing the audit the
    routes the build declares is not a convenience; without it four fifths of
    the site is silently unaudited and the loop would report a 1-page audit as
    if it had covered the site.
    """
    doc = _read_json(build_dir / "site-manifest.json")
    routes = []
    for page in ((doc or {}).get("pages") or []):
        route = str(page.get("route") or "/")
        if "[" in route:            # a dynamic segment has no concrete URL
            continue
        if route not in routes:
            routes.append(route)
    return routes


def audit_built_site(label: str, audit_cmd: list[str], build_dir: Path,
                     out_dir: Path, max_pages: int, axe_js: str | None,
                     timeout: int, serve_cmd: list[str] | None = None) -> dict:
    """Serve the built site and audit it. NOT_MEASURED-with-reason on any
    infrastructure absence; never a fabricated finding."""
    lane = {"label": label, "state": "not_measured", "reason": "",
            "audit_result": None, "axe": "off", "routes_audited": None,
            "mode": None}
    site_dir = build_dir / "site"
    proc, port, reason = serve_site(site_dir, serve_cmd)
    if proc is None:
        lane["reason"] = reason
        print(f"  ⊘ AUDIT {label}: NOT_MEASURED — {reason}")
        return lane
    base_url = f"http://127.0.0.1:{port}"
    routes = built_routes(build_dir)
    if routes:
        # `urls` audits exactly what was built. `site` would crawl, and the
        # built nav does not point at the built site (see built_routes).
        lane["mode"], lane["routes_audited"] = "urls", routes
        argv = list(audit_cmd) + ["urls"]
        for route in routes[:max_pages]:
            argv += ["--url", base_url + ("" if route == "/" else route)]
        argv += ["--output-dir", str(out_dir),
                 "--store-html", "--no-psi", "--no-handoff"]
    else:
        lane["mode"] = "site-crawl"
        lane["reason"] = ("no site-manifest routes — fell back to a same-origin "
                          "crawl, which reaches only the pages the built nav links to")
        argv = list(audit_cmd) + ["site", base_url,
                                  "--max-pages", str(max_pages),
                                  "--output-dir", str(out_dir),
                                  "--store-html", "--no-psi", "--no-handoff"]
    if axe_js:
        argv += ["--axe", "--axe-js", axe_js]
        lane["axe"] = "on"
    else:
        lane["axe"] = "off"
    print(f"\n─── AUDIT {label} ({base_url}, axe={lane['axe']}) ───")
    print("  " + " ".join(shlex.quote(a) for a in argv))
    try:
        res = subprocess.run(argv, cwd=str(AUDIT_REPO), capture_output=True,
                             text=True, timeout=timeout)
        rc, tail = res.returncode, (res.stdout or "")[-2000:] + (res.stderr or "")[-2000:]
    except subprocess.TimeoutExpired:
        rc, tail = 124, f"audit exceeded {timeout}s"
    finally:
        proc.kill()
        proc.wait(timeout=10)
    lane["exit_code"] = rc
    report = out_dir / "audit_result.yaml"
    if not report.is_file():
        lane["reason"] = f"audit exited {rc} and wrote no audit_result.yaml"
        lane["tail"] = tail[-600:]
        print(f"  ⊘ AUDIT {label}: NOT_MEASURED — {lane['reason']}")
        return lane
    lane["state"] = "measured"
    lane["audit_result"] = str(report)
    # Coverage is read back off the report rather than assumed from the argv: a
    # requested route that 404s is reached-but-empty, and the count is the only
    # honest statement about how much of the site was measured.
    try:
        import yaml as _yaml
        doc = _yaml.safe_load(report.read_text(encoding="utf-8")) or {}
        cov = doc.get("coverage") or {}
        lane["coverage"] = {"requested": cov.get("requested_count"),
                            "reached": cov.get("reached_count"),
                            "unreached": cov.get("unreached") or []}
        lane["finding_count"] = len(doc.get("findings") or [])
        lane["axe_findings"] = (doc.get("axe") or {}).get("finding_count")
    except Exception as exc:
        lane["coverage"] = {"error": f"{type(exc).__name__}: {exc}"}
    if lane["axe"] == "off":
        lane["reason"] = ("axe off — the selector lane cannot fire, so only the "
                          "page-rule lane can produce verdicts")
    print(f"  ✓ AUDIT {label}: {report}")
    return lane


# ─────────────────────────────────────────────────────────────────────────────
# K1 + K2
# ─────────────────────────────────────────────────────────────────────────────

def run_k1(audit_result: Path, build_dir: Path, out_dir: Path) -> dict:
    """K1: audit_result.yaml → copy-findings.json + unroutable-findings.json."""
    out_dir.mkdir(parents=True, exist_ok=True)
    argv = [sys.executable, str(ROOT / "scripts" / "quality" / "findings-to-verdicts.py"),
            str(audit_result), "--site-spec", str(build_dir / "site-spec.json"),
            "--out-dir", str(out_dir)]
    res = subprocess.run(argv, cwd=str(ROOT), capture_output=True, text=True)
    lane = {"tool": "findings-to-verdicts.py", "exit_code": res.returncode,
            "state": "not_measured", "reason": "", "copy_findings": {}, "summary": {}}
    cf = out_dir / "copy-findings.json"
    ur = out_dir / "unroutable-findings.json"
    if res.returncode == EXIT_NOT_MEASURED:
        lane["reason"] = "K1 exit 3 — the audit report carried no findings[]"
        return lane
    if res.returncode != EXIT_OK or not cf.is_file():
        lane["reason"] = (f"K1 exited {res.returncode}: "
                          f"{(res.stderr or res.stdout or '').strip()[-300:]}")
        return lane
    lane["state"] = "measured"
    lane["copy_findings"] = json.loads(cf.read_text())
    if ur.is_file():
        lane["summary"] = json.loads(ur.read_text()).get("summary", {})
    lane["copy_findings_path"] = str(cf)
    lane["unroutable_path"] = str(ur)
    return lane


def run_k2(build_dir: Path, out_dir: Path, rules: Path | None) -> dict:
    """K2: build dir → funnel-verdicts.json."""
    out_dir.mkdir(parents=True, exist_ok=True)
    argv = [sys.executable, str(ROOT / "scripts" / "quality" / "funnel-verdicts.py"),
            str(build_dir), "--out-dir", str(out_dir)]
    if rules:
        argv += ["--rules", str(rules)]
    res = subprocess.run(argv, cwd=str(ROOT), capture_output=True, text=True)
    lane = {"tool": "funnel-verdicts.py", "exit_code": res.returncode,
            "state": "not_measured", "reason": "", "copy_findings": {}, "summary": {},
            "unrouted": []}
    path = out_dir / "funnel-verdicts.json"
    if res.returncode == EXIT_NOT_MEASURED:
        lane["reason"] = "K2 exit 3 — no built sections, so there is no funnel to grade"
        return lane
    if res.returncode != EXIT_OK or not path.is_file():
        lane["reason"] = (f"K2 exited {res.returncode}: "
                          f"{(res.stderr or res.stdout or '').strip()[-300:]}")
        return lane
    doc = json.loads(path.read_text())
    lane["state"] = "measured"
    lane["copy_findings"] = doc.get("copy_findings", {})
    lane["summary"] = doc.get("summary", {})
    lane["unrouted"] = doc.get("unrouted", [])
    lane["rule_verdicts"] = doc.get("rule_verdicts", [])
    lane["path"] = str(path)
    return lane


def merge_verdicts(audit_cf: dict, funnel_cf: dict) -> dict:
    """Merge the two page-scoped verdict streams.

    K2 documented that its copy_findings is indistinguishable from K1's, so the
    merge is a dict update — but at the SLOT level, not the page level: a
    page-level `update()` would silently drop every slot K1 found on a page K2
    also touched. Slot-key collisions are counted and named, and the audit
    verdict wins the slot (a rule_id the build's own funnel evaluator invented
    should not displace a measured audit finding). The loser is retained under
    `displaced` so nothing lands on the floor.
    """
    merged: dict = {}
    collisions: list[dict] = []
    for page_id, slots in audit_cf.items():
        merged.setdefault(page_id, {}).update(slots)
    for page_id, slots in funnel_cf.items():
        page = merged.setdefault(page_id, {})
        for slot_key, entry in slots.items():
            if slot_key in page:
                collisions.append({
                    "page_id": page_id, "slot_key": slot_key,
                    "kept": page[slot_key].get("rule_id"),
                    "displaced": entry.get("rule_id"),
                })
                continue
            page[slot_key] = entry
    ordered = {p: {s: merged[p][s] for s in sorted(merged[p])}
               for p in sorted(merged)}
    audit_slots = {(p, s) for p, ss in audit_cf.items() for s in ss}
    funnel_slots = {(p, s) for p, ss in funnel_cf.items() for s in ss}
    merged_slots = {(p, s) for p, ss in ordered.items() for s in ss}
    accounting = {
        "audit_slots": len(audit_slots),
        "funnel_slots": len(funnel_slots),
        "merged_slots": len(merged_slots),
        "collisions": len(collisions),
        "consistent": len(merged_slots) + len(collisions) == len(audit_slots) + len(funnel_slots),
    }
    return {"copy_findings": ordered, "collisions": collisions,
            "accounting": accounting}


def validate_consumed_shape(copy_findings: dict) -> None:
    """The merged file must still be detected as page-scoped by the consumer.

    orchestrate._findings_are_page_scoped(): non-empty mapping, every top-level
    value a non-empty mapping whose values are all mappings. A merge that broke
    that would be read as flat — silently addressing the wrong slots.
    """
    if not copy_findings:
        return
    if not isinstance(copy_findings, dict):
        raise ValueError("merged copy_findings is not a mapping")
    for page_id, slots in copy_findings.items():
        if not isinstance(slots, dict) or not slots:
            raise ValueError(f"page {page_id!r} is not a non-empty mapping")
        for slot_key, entry in slots.items():
            if not isinstance(entry, dict):
                raise ValueError(f"{page_id}/{slot_key} is not a mapping")


# ─────────────────────────────────────────────────────────────────────────────
# the diff
# ─────────────────────────────────────────────────────────────────────────────

def section_inventory(build_dir: Path) -> dict:
    """Per-section digests, keyed by path relative to section-artifacts/.

    The unit of "revised". The layout is `section-artifacts/<page_id>/NN-*.json`
    — nested, as K2's own loader assumes — so this walks the tree; a flat glob
    here would count zero sections on every real build.
    """
    inv = {}
    art_dir = build_dir / "section-artifacts"
    if art_dir.is_dir():
        for p in sorted(art_dir.rglob("*.json")):
            inv[str(p.relative_to(art_dir))] = _digest_path(p)
    return inv


def emitted_inventory(build_dir: Path) -> dict:
    """Per-emitted-file digests under sections/ — the rendered TSX."""
    inv = {}
    sec_dir = build_dir / "sections"
    if sec_dir.is_dir():
        for p in sorted(sec_dir.rglob("*")):
            if p.is_file():
                inv[str(p.relative_to(sec_dir))] = _digest_path(p)
    return inv


def diff_inventories(before: dict, after: dict) -> dict:
    keys = set(before) | set(after)
    changed = sorted(k for k in keys
                     if k in before and k in after and before[k] != after[k])
    return {
        "before_count": len(before),
        "after_count": len(after),
        "changed": changed,
        "added": sorted(set(after) - set(before)),
        "removed": sorted(set(before) - set(after)),
    }


def finding_keys(unroutable_path: Path | None, copy_findings: dict) -> set:
    """Every finding key K1 accounted for — placed plus unroutable."""
    keys = set()
    for slots in copy_findings.values():
        for entry in slots.values():
            keys.update(entry.get("contributing_findings") or [])
    if unroutable_path and Path(unroutable_path).is_file():
        doc = json.loads(Path(unroutable_path).read_text())
        for row in doc.get("findings", []):
            if row.get("finding_key"):
                keys.add(row["finding_key"])
    return keys


VERDICT_LOADED_MARKER = "Loaded copy findings for"


def verdict_effect(build_b: dict, build_a_dir: Path, build_b_dir: Path,
                   section_diff: dict, verdict_slots: int) -> dict:
    """Did the verdicts actually reach anything? Three states, never a shrug.

    MEASURED 2026-08-17 and the reason this exists: the loop's first real run
    ended `2 verdict slots, 0 sections changed`, which reads as "the loop did
    nothing" and is not what happened. `--copy-findings` is consumed at ONE site
    inside orchestrate.py's LLM section-generation branch — it selects the
    finding, sets `_copy_status = "revised"`, and appends to `_copy_trace`, all
    of which also produce `copy-manifest*.json`. A fully template-resolved build
    makes 0 LLM calls and never enters that branch, so the file is loaded, the
    count is printed, and nothing downstream reads it. Neither build wrote a
    copy-manifest, which is the positive evidence for that reading.

    So: `applied` when sections changed; `loaded-but-inert` when the build
    confirms the load and no artefact of consumption exists; `not-loaded` when
    the build never reported reading the file.
    """
    loaded = VERDICT_LOADED_MARKER in Path(build_b["log"]).read_text(
        encoding="utf-8", errors="replace")
    manifests = sorted(
        str(p.name) for d in (build_a_dir, build_b_dir) if d.is_dir()
        for p in d.glob("copy-manifest*.json"))
    changed = len(section_diff.get("changed") or [])
    if changed:
        state, reason = "applied", f"{changed} section artifact(s) changed"
    elif not loaded:
        state, reason = "not-loaded", ("the build never reported reading the "
                                       "verdicts file")
    else:
        state = "loaded-but-inert"
        reason = (f"the build loaded {verdict_slots} verdict slot(s) and no "
                  "section changed. --copy-findings is consumed only in the LLM "
                  "section-generation branch; this build resolved every section "
                  "from a template and made 0 LLM calls, so the branch never "
                  "ran. No copy-manifest*.json was written by either build, "
                  "which is the positive evidence for that.")
    return {"state": state, "reason": reason,
            "verdicts_loaded_by_build": loaded,
            "copy_manifests_found": manifests,
            "verdict_slots": verdict_slots,
            "sections_changed": changed}


def funnel_fail_cells(lane: dict) -> set:
    return {(c["rule_id"], c["page_id"]) for c in lane.get("rule_verdicts", [])
            if c.get("state") == "FAIL"}


# ─────────────────────────────────────────────────────────────────────────────
# the loop
# ─────────────────────────────────────────────────────────────────────────────

def run_iteration(n: int, args: argparse.Namespace, orchestrate_cmd: list[str],
                  audit_cmd: list[str], serve_cmd: list[str], scratch: Path,
                  digest_cfg: dict) -> tuple[dict, int | None]:
    """One bounded pass. Returns (iteration report, abort exit code or None)."""
    it: dict = {"iteration": n, "not_measured_lanes": []}

    def not_measured(lane: str, reason: str) -> None:
        it["not_measured_lanes"].append({"lane": lane, "reason": reason})

    root_a = scratch / f"pass{n}-a"
    root_b = scratch / f"pass{n}-b"
    verdicts = scratch / f"pass{n}-verdicts"
    build_a_dir = root_a / args.project
    build_b_dir = root_b / args.project

    # ── 1. BUILD A ─────────────────────────────────────────────────────────
    it["control_digests_before_a"] = non_verdict_input_digests(digest_cfg)
    it["build_a"] = run_build(f"{n}A", build_argv(orchestrate_cmd, args.project,
                                                 root_a, args, None),
                              scratch / "logs" / f"build-{n}a.log",
                              args.build_timeout)
    fatal, why = build_is_fatal(it["build_a"], args.tolerate_build_failure)
    if fatal:
        it["aborted"] = {"at": "build_a", "why": why,
                         "exit_code": it["build_a"]["exit_code"]}
        return it, it["build_a"]["exit_code"]
    it["build_a"]["asset_coverage"] = _read_json(build_a_dir / "asset-coverage.json")
    it["build_a"]["sections"] = len(section_inventory(build_a_dir))

    # ── 2. AUDIT THE BUILT SITE ────────────────────────────────────────────
    axe_js, axe_source = resolve_axe_js(args.axe_js)
    it["axe"] = {"path": axe_js, "source": axe_source if axe_js else None,
                 "reason": None if axe_js else axe_source}
    if not axe_js:
        not_measured("axe-selector-lane", axe_source)
    if args.audit_built:
        it["audit_a"] = audit_built_site(
            f"{n}A", audit_cmd, build_a_dir, verdicts / "audit-a",
            args.audit_max_pages, axe_js, args.audit_timeout, serve_cmd)
    else:
        it["audit_a"] = {"label": f"{n}A", "state": "not_measured",
                         "reason": "--no-audit-built was passed"}
    if it["audit_a"]["state"] != "measured":
        not_measured("audit-built-site", it["audit_a"]["reason"])

    # ── 3. COMPILE VERDICTS ────────────────────────────────────────────────
    if it["audit_a"]["state"] == "measured":
        it["k1"] = run_k1(Path(it["audit_a"]["audit_result"]), build_a_dir,
                          verdicts / "k1")
        if it["k1"]["state"] != "measured":
            not_measured("k1-audit-verdicts", it["k1"]["reason"])
    else:
        it["k1"] = {"tool": "findings-to-verdicts.py", "state": "not_measured",
                    "reason": "no built-site audit to compile",
                    "copy_findings": {}, "summary": {}}
        not_measured("k1-audit-verdicts", it["k1"]["reason"])

    it["k2_before"] = run_k2(build_a_dir, verdicts / "k2-before", args.rules)
    if it["k2_before"]["state"] != "measured":
        not_measured("k2-funnel-verdicts", it["k2_before"]["reason"])

    if it["k1"]["state"] != "measured" and it["k2_before"]["state"] != "measured":
        it["merged"] = {"accounting": {"merged_slots": 0}, "collisions": []}
        it["nothing_measured"] = True
        return it, None

    merged = merge_verdicts(it["k1"].get("copy_findings", {}),
                            it["k2_before"].get("copy_findings", {}))
    validate_consumed_shape(merged["copy_findings"])
    if not merged["accounting"]["consistent"]:
        it["merged"] = merged
        it["accounting_failure"] = merged["accounting"]
        return it, EXIT_FAILED
    verdicts.mkdir(parents=True, exist_ok=True)
    merged_path = verdicts / "merged-copy-findings.json"
    merged_path.write_text(
        json.dumps(merged["copy_findings"], indent=2, sort_keys=True) + "\n",
        encoding="utf-8")
    merged["path"] = str(merged_path)
    merged["per_source"] = {
        "audit_slots": merged["accounting"]["audit_slots"],
        "funnel_slots": merged["accounting"]["funnel_slots"],
        "audit_findings_placed": it["k1"].get("summary", {}).get("verdict_findings"),
        "audit_findings_unroutable": it["k1"].get("summary", {}).get("unroutable_findings"),
        "audit_findings_input": it["k1"].get("summary", {}).get("input_findings"),
        "funnel_fail_cells": it["k2_before"].get("summary", {}).get("fail"),
        "funnel_routed_fail_cells": it["k2_before"].get("summary", {}).get("routed_fail_cells"),
        "funnel_unrouted_fail_records": it["k2_before"].get("summary", {}).get(
            "unrouted_fail_records"),
    }
    it["merged"] = merged
    print(f"\n  merged verdicts: {merged['accounting']['merged_slots']} slot(s) "
          f"({merged['accounting']['audit_slots']} audit + "
          f"{merged['accounting']['funnel_slots']} funnel, "
          f"{merged['accounting']['collisions']} collision(s)) → {merged_path}")

    if not merged["copy_findings"]:
        it["not_rebuilt"] = "no verdicts were produced; a rebuild would be identical"
        not_measured("rebuild", it["not_rebuilt"])
        return it, None

    # ── 4. REBUILD WITH THE VERDICTS ───────────────────────────────────────
    it["control_digests_before_b"] = non_verdict_input_digests(digest_cfg)
    it["control"] = {
        "non_verdict_inputs_unchanged":
            it["control_digests_before_a"] == it["control_digests_before_b"],
        "changed_inputs": sorted(
            k for k in it["control_digests_before_a"]
            if it["control_digests_before_a"][k] != it["control_digests_before_b"].get(k)),
        "note": ("the build is deterministic at 0 LLM calls, so with these "
                 "digests equal every diff below is attributable to the "
                 "verdicts file alone"),
    }
    it["build_b"] = run_build(f"{n}B", build_argv(orchestrate_cmd, args.project,
                                                 root_b, args, merged_path),
                              scratch / "logs" / f"build-{n}b.log",
                              args.build_timeout)
    fatal, why = build_is_fatal(it["build_b"], args.tolerate_build_failure)
    if fatal:
        it["aborted"] = {"at": "build_b", "why": why,
                         "exit_code": it["build_b"]["exit_code"]}
        return it, it["build_b"]["exit_code"]
    it["build_b"]["asset_coverage"] = _read_json(build_b_dir / "asset-coverage.json")
    it["build_b"]["sections"] = len(section_inventory(build_b_dir))

    # ── 5. DIFF ────────────────────────────────────────────────────────────
    it["section_diff"] = diff_inventories(section_inventory(build_a_dir),
                                          section_inventory(build_b_dir))
    it["emitted_diff"] = diff_inventories(emitted_inventory(build_a_dir),
                                          emitted_inventory(build_b_dir))
    it["sections_revised"] = {
        "verdict_slots": sorted(f"{p}/{s}" for p, ss in
                                merged["copy_findings"].items() for s in ss),
        "artifacts_changed": it["section_diff"]["changed"],
        "emitted_changed": it["emitted_diff"]["changed"],
    }
    it["verdict_effect"] = verdict_effect(
        it["build_b"], build_a_dir, build_b_dir, it["section_diff"],
        merged["accounting"]["merged_slots"])
    if it["verdict_effect"]["state"] != "applied":
        not_measured("verdict-application", it["verdict_effect"]["reason"])

    it["k2_after"] = run_k2(build_b_dir, verdicts / "k2-after", args.rules)
    if it["k2_after"]["state"] != "measured":
        not_measured("k2-funnel-verdicts-after", it["k2_after"]["reason"])
    else:
        before, after = funnel_fail_cells(it["k2_before"]), funnel_fail_cells(it["k2_after"])
        it["funnel_fail_fate"] = {
            "before": sorted(f"{r}@{p}" for r, p in before),
            "after": sorted(f"{r}@{p}" for r, p in after),
            "closed": sorted(f"{r}@{p}" for r, p in before - after),
            "still_failing": sorted(f"{r}@{p}" for r, p in before & after),
            "new": sorted(f"{r}@{p}" for r, p in after - before),
            "note": ("a verdict flips ONE section from reproduce-verbatim to "
                     "revise-from-source; it cannot CREATE a section. A "
                     "route-scoped FAIL ('this route ends in a FAQ', 'no trust "
                     "section was built') is therefore not addressable by this "
                     "loop and its persistence is not a loop failure."),
        }

    # ── findings closed/remaining — needs a second audit ───────────────────
    if args.audit_built and it["audit_a"]["state"] == "measured":
        it["audit_b"] = audit_built_site(
            f"{n}B", audit_cmd, build_b_dir, verdicts / "audit-b",
            args.audit_max_pages, axe_js, args.audit_timeout, serve_cmd)
    else:
        it["audit_b"] = {"state": "not_measured",
                         "reason": "build A was not audited, so there is nothing to compare"}
    if it["audit_b"]["state"] == "measured":
        it["k1_after"] = run_k1(Path(it["audit_b"]["audit_result"]), build_b_dir,
                                verdicts / "k1-after")
        if it["k1_after"]["state"] == "measured":
            kb = finding_keys(it["k1"].get("unroutable_path"), it["k1"]["copy_findings"])
            ka = finding_keys(it["k1_after"].get("unroutable_path"),
                              it["k1_after"]["copy_findings"])
            it["findings_fate"] = {
                "before": len(kb), "after": len(ka),
                "closed": len(kb - ka), "remaining": len(kb & ka), "new": len(ka - kb),
                "closed_keys": sorted(kb - ka)[:50],
                "new_keys": sorted(ka - kb)[:50],
            }
        else:
            not_measured("findings-closed-remaining", it["k1_after"]["reason"])
    else:
        not_measured("findings-closed-remaining", it["audit_b"]["reason"])

    return it, None


def _read_json(path: Path):
    if path.is_file():
        try:
            return json.loads(path.read_text())
        except (ValueError, OSError):
            return None
    return None


def _strip(it: dict) -> dict:
    """Drop the bulky in-memory payloads from the report; the files hold them."""
    out = dict(it)
    for lane in ("k1", "k1_after", "k2_before", "k2_after"):
        if lane in out and isinstance(out[lane], dict):
            out[lane] = {k: v for k, v in out[lane].items()
                         if k not in ("copy_findings", "rule_verdicts")}
    if "merged" in out and isinstance(out["merged"], dict):
        out["merged"] = {k: v for k, v in out["merged"].items()
                         if k != "copy_findings"}
    return out


def parse_args(argv: list[str]) -> argparse.Namespace:
    class P(argparse.ArgumentParser):
        def error(self, message):
            self.print_usage(sys.stderr)
            sys.stderr.write(f"{self.prog}: error: {message}\n")
            raise SystemExit(EXIT_USAGE)

    p = P(description="Run the CVR loop: build → audit → verdicts → rebuild → diff.")
    p.add_argument("project")
    p.add_argument("--tenant")
    p.add_argument("--captures")
    p.add_argument("--routes")
    p.add_argument("--benchmark")
    p.add_argument("--preset")
    p.add_argument("--target-platform", choices=("shopify", "vercel"))
    p.add_argument("--output-root", required=True,
                   help="Scratch root. NEVER output/<project>/ — another session reads it.")
    p.add_argument("--max-iterations", type=int, default=1,
                   help="Bounded. This is a pass, not a daemon. Default 1.")
    p.add_argument("--audit-built", dest="audit_built", action="store_true", default=True,
                   help="Serve and audit the built site (default). This is what "
                        "lights K1's selector lane.")
    p.add_argument("--no-audit-built", dest="audit_built", action="store_false")
    p.add_argument("--deploy", dest="deploy", action="store_true", default=True,
                   help="Local production build (default) — required to serve the "
                        "site. Never a Vercel publish.")
    p.add_argument("--no-deploy", dest="deploy", action="store_false")
    p.add_argument("--axe-js", help="axe.min.js path (else AXE_JS, else discovered)")
    p.add_argument("--rules", help="funnel-rules.json override")
    p.add_argument("--tolerate-build-failure", action="append", default=[],
                   metavar="STAGE",
                   help="Proceed past a recorded build failure in STAGE (repeatable). "
                        "For a pre-existing failure in a gate outside this loop's "
                        "scope. `compliance` is refused: a compliance FAIL is always "
                        "fatal. Every use is recorded in the report.")
    p.add_argument("--audit-max-pages", type=int, default=6)
    p.add_argument("--build-timeout", type=int, default=3600)
    p.add_argument("--audit-timeout", type=int, default=1800)
    p.add_argument("--orchestrate-cmd",
                   default=f"{shlex.quote(sys.executable)} "
                           f"{shlex.quote(str(ROOT / 'scripts' / 'orchestrate.py'))}",
                   help="SEAM: the build command (shlex-split, argv appended).")
    p.add_argument("--audit-cmd",
                   default=f"{shlex.quote(sys.executable)} "
                           f"{shlex.quote(str(AUDIT_REPO / 'run_ui_ux_audit.py'))}",
                   help="SEAM: the audit command (shlex-split, argv appended).")
    p.add_argument("--serve-cmd", default="npm run start --",
                   help="SEAM: the command that serves the built site "
                        "(shlex-split, --port N appended).")
    p.add_argument("--report", help="Report path (default <output-root>/cvr-loop-report.json)")
    return p.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(sys.argv[1:] if argv is None else argv)
    except SystemExit as exc:
        return int(exc.code) if exc.code is not None else EXIT_USAGE

    if "compliance" in args.tolerate_build_failure:
        print("--tolerate-build-failure compliance is refused: a compliance FAIL is "
              "always fatal", file=sys.stderr)
        return EXIT_USAGE
    args.tolerate_build_failure = frozenset(args.tolerate_build_failure)
    if args.max_iterations < 1:
        print("--max-iterations must be >= 1", file=sys.stderr)
        return EXIT_USAGE
    scratch = Path(args.output_root).resolve()
    guard = (ROOT / "output").resolve()
    if scratch == guard or guard in scratch.parents:
        print(f"refusing to write under {guard} — pass a scratch --output-root",
              file=sys.stderr)
        return EXIT_USAGE
    scratch.mkdir(parents=True, exist_ok=True)

    orchestrate_cmd = shlex.split(args.orchestrate_cmd)
    audit_cmd = shlex.split(args.audit_cmd)
    serve_cmd = shlex.split(args.serve_cmd)
    if not orchestrate_cmd or not audit_cmd or not serve_cmd:
        print("--orchestrate-cmd / --audit-cmd / --serve-cmd must be non-empty",
              file=sys.stderr)
        return EXIT_USAGE

    digest_cfg = {
        "captures": args.captures,
        "benchmark": (str(ROOT / "benchmarks" / f"{args.benchmark}.json")
                      if args.benchmark else None),
        "preset": (str(ROOT / "skills" / "presets" / f"{args.preset}.md")
                   if args.preset else None),
        "funnel_rules": str(Path(args.rules) if args.rules
                            else ROOT / "skills" / "funnel-rules.json"),
        "section_templates": str(ROOT / "section-templates"),
        "extractions": str(ROOT / "output" / "extractions"),
    }

    report = {
        "schema": "aurelix.cvr_loop.v1",
        "project": args.project,
        "tenant": args.tenant,
        "output_root": str(scratch),
        "max_iterations": args.max_iterations,
        "tolerated_build_failure_stages": sorted(args.tolerate_build_failure),
        "argv": (sys.argv[1:] if argv is None else argv),
        "iterations": [],
    }
    report_path = Path(args.report) if args.report else scratch / "cvr-loop-report.json"

    def write_report(outcome: str, exit_code: int) -> None:
        report["outcome"] = outcome
        report["exit_code"] = exit_code
        report["not_measured_lanes"] = [
            dict(row, iteration=it["iteration"])
            for it in report["iterations"] for row in it.get("not_measured_lanes", [])
        ]
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
                               encoding="utf-8")
        print(f"\n  report → {report_path}")

    if shutil.which(orchestrate_cmd[0]) is None and not Path(orchestrate_cmd[0]).exists():
        print(f"build command not executable: {orchestrate_cmd[0]}", file=sys.stderr)
        return EXIT_USAGE

    for n in range(1, args.max_iterations + 1):
        it, abort = run_iteration(n, args, orchestrate_cmd, audit_cmd, serve_cmd,
                                  scratch, digest_cfg)
        report["iterations"].append(_strip(it))
        if abort is not None:
            if it.get("accounting_failure"):
                write_report("accounting-failure", EXIT_FAILED)
                print("✖ ACCOUNTING FAILURE in the verdict merge", file=sys.stderr)
                return EXIT_FAILED
            ab = it.get("aborted", {})
            # An abort can never be exit 0. If a build reported a compliance
            # FAIL and still exited 0 — the exact honesty gap this loop exists
            # not to reproduce — the loop reports EXIT_FAILED, not the build's 0.
            if abort == 0:
                abort = EXIT_FAILED
                ab["exit_code_substituted"] = (
                    "the build exited 0 while reporting a fatal gate; "
                    "the loop refuses to pass that through")
                it["aborted"] = ab
                report["iterations"][-1] = _strip(it)
            write_report(f"aborted-at-{ab.get('at', 'unknown')}", abort)
            print(f"\n✖ LOOP ABORTED at {ab.get('at')}: {ab.get('why')} "
                  f"→ exit {abort}", file=sys.stderr)
            return abort
        if it.get("nothing_measured"):
            write_report("not-measured", EXIT_NOT_MEASURED)
            print("\n⊘ NOTHING COULD BE MEASURED — no audit lane and no funnel lane",
                  file=sys.stderr)
            return EXIT_NOT_MEASURED

    write_report("completed", EXIT_OK)
    last = report["iterations"][-1]
    print("\n═══ CVR LOOP COMPLETE ═══")
    print(f"  merged verdicts : {last.get('merged', {}).get('accounting', {}).get('merged_slots', 0)} slot(s)")
    if "section_diff" in last:
        print(f"  sections        : {last['section_diff']['before_count']} → "
              f"{last['section_diff']['after_count']}, "
              f"{len(last['section_diff']['changed'])} changed")
    if "funnel_fail_fate" in last:
        f = last["funnel_fail_fate"]
        print(f"  funnel FAILs    : {len(f['before'])} → {len(f['after'])} "
              f"({len(f['closed'])} closed, {len(f['still_failing'])} still failing, "
              f"{len(f['new'])} new)")
    if "verdict_effect" in last:
        print(f"  verdict effect  : {last['verdict_effect']['state']}")
    if "findings_fate" in last:
        f = last["findings_fate"]
        print(f"  audit findings  : {f['before']} → {f['after']} "
              f"({f['closed']} closed, {f['remaining']} remaining, {f['new']} new)")
    for row in report["not_measured_lanes"]:
        print(f"  ⊘ {row['lane']}: {row['reason']}")
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
