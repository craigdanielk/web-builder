#!/usr/bin/env python3
"""Gates C, D and E must have three outcomes: PASS (0) - FAIL (1) - NOT_MEASURED (3).

NOT_MEASURED is not PASS. A gate that reports success because it could not
measure anything is worse than no gate: it launders "I did not look" into
"I looked and it was fine".

Run: cd web-builder && python3 -m pytest scripts/test_gate_outcomes.py -v
"""

from __future__ import annotations

import http.server
import json
import os
import socketserver
import subprocess
import sys
import threading
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent
WEB_BUILDER_ROOT = SCRIPTS_DIR.parent

GATE_SCRIPTS = {
    "c": SCRIPTS_DIR / "verify_gate_c.py",
    "d": SCRIPTS_DIR / "verify_gate_d.py",
    "e": SCRIPTS_DIR / "verify_gate_e.py",
}

NOT_MEASURED_EXIT = 3


def run_gate(gate, args):
    """Invoke a gate as a subprocess. Returns (exit_code, combined_output)."""
    env = os.environ.copy()
    # These env defaults would silently supply the very input we are testing for.
    env.pop("GATE_D_URL", None)
    env.pop("GATE_E_URL", None)
    proc = subprocess.run(
        [sys.executable, str(GATE_SCRIPTS[gate])] + [str(a) for a in args],
        cwd=str(WEB_BUILDER_ROOT),
        capture_output=True,
        text=True,
        timeout=240,
        env=env,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


# --------------------------------------------------------------------------
# A local HTTP server, so the URL-driven gates can be exercised without a
# deployed site.
# --------------------------------------------------------------------------

class _Handler(http.server.BaseHTTPRequestHandler):
    status_code = 200
    body = b"<html><body><a href=\"/collections\">Collections</a></body></html>"

    def do_GET(self):  # noqa: N802 (stdlib naming)
        self.send_response(self.status_code)
        self.send_header("Content-Type", "text/html")
        self.send_header("Content-Length", str(len(self.body)))
        self.end_headers()
        self.wfile.write(self.body)

    def log_message(self, *args):
        pass


class _ThreadedServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


@pytest.fixture
def http_site():
    """Yield a factory: http_site(status) -> base URL of a server returning `status`."""
    servers = []

    def _start(status=200):
        handler = type("_H", (_Handler,), {"status_code": status})
        srv = _ThreadedServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=srv.serve_forever, daemon=True)
        thread.start()
        servers.append((srv, thread))
        return "http://127.0.0.1:%d" % srv.server_address[1]

    yield _start

    for srv, thread in servers:
        srv.shutdown()
        srv.server_close()
        thread.join(timeout=5)


def _make_buildable_app(tmp_path):
    """Minimal app dir Gate C accepts: package.json with a build script + app/page.tsx.

    The build script is a no-op node call so the test does not depend on npm
    install or a real Next.js toolchain — Gate C's assertion is "npm run build
    exits 0", and that is exactly what is being exercised.
    """
    app_dir = tmp_path / "site"
    (app_dir / "app").mkdir(parents=True)
    (app_dir / "package.json").write_text(
        json.dumps({"name": "gate-c-fixture", "version": "1.0.0", "private": True,
                    "scripts": {"build": "node -e \"process.exit(0)\""}}),
        encoding="utf-8",
    )
    (app_dir / "app" / "page.tsx").write_text(
        "export default function Page() { return <main>ok</main>; }\n", encoding="utf-8"
    )
    return app_dir


def _redirect_map(tmp_path):
    path = tmp_path / "redirects.csv"
    path.write_text("from_path,to_path\nold-page,/collections\n", encoding="utf-8")
    return path


# --------------------------------------------------------------------------
# NOT_MEASURED — the branch this task exists for
# --------------------------------------------------------------------------

@pytest.mark.parametrize("gate", ["c", "d", "e"])
def test_gate_reports_not_measured_when_it_cannot_measure(gate):
    code, out = run_gate(gate, [])  # no --site-dir / --url / --redirect-map
    assert code == NOT_MEASURED_EXIT, "gate %s exited %d, expected 3\n%s" % (gate, code, out)
    assert "NOT_MEASURED" in out, out
    assert "PASS" not in out, out


@pytest.mark.parametrize("gate,expected_input", [
    ("c", "--site-dir"),
    ("d", "--url"),
    ("e", "--url"),
])
def test_not_measured_message_names_the_missing_input(gate, expected_input):
    code, out = run_gate(gate, [])
    assert code == NOT_MEASURED_EXIT, out
    assert "VERIFY GATE %s: NOT_MEASURED" % gate.upper() in out, out
    assert expected_input in out, out


def test_gate_e_not_measured_when_redirect_map_does_not_exist(tmp_path):
    """A --redirect-map pointing at nothing measured nothing. It must not PASS."""
    code, out = run_gate("e", ["--redirect-map", tmp_path / "absent.csv"])
    assert code == NOT_MEASURED_EXIT, out
    assert "NOT_MEASURED" in out, out
    assert "PASS" not in out, out


# --------------------------------------------------------------------------
# FAIL
# --------------------------------------------------------------------------

def test_gate_c_can_fail(tmp_path):
    empty = tmp_path / "site"
    empty.mkdir()
    code, out = run_gate("c", ["--site-dir", empty])
    assert code == 1, out
    assert "FAIL" in out, out


def test_gate_d_can_fail(http_site):
    base = http_site(404)
    code, out = run_gate("d", ["--url", base, "--timeout", "5"])
    assert code == 1, out
    assert "PASS" not in out, out


def test_gate_e_can_fail(http_site):
    base = http_site(404)
    code, out = run_gate("e", ["--url", base, "--timeout", "5"])
    assert code == 1, out
    assert "FAIL" in out, out


# --------------------------------------------------------------------------
# PASS
# --------------------------------------------------------------------------

def test_gate_c_can_pass(tmp_path):
    app_dir = _make_buildable_app(tmp_path)
    code, out = run_gate("c", ["--site-dir", app_dir])
    assert code == 0, out
    assert "VERIFY GATE C: PASS" in out, out


def test_gate_d_can_pass(http_site):
    base = http_site(200)
    code, out = run_gate("d", ["--url", base, "--timeout", "5"])
    assert code == 0, out
    assert "VERIFY GATE D: PASS" in out, out


def test_gate_e_can_pass(http_site):
    base = http_site(200)
    code, out = run_gate("e", ["--url", base, "--timeout", "5"])
    assert code == 0, out
    assert "VERIFY GATE E: PASS" in out, out
