"""Tree diff for the determinism check.

Two builds of the same inputs must produce the same tree. This module compares
two output roots and reports every difference, classifying each as either
ALLOWED (it matches a justified entry in ``determinism-allowlist.json``) or
UNEXPLAINED.

Design notes:

* JSON files are compared structurally so a report names the *field* that moved
  (``/line_items[*]/build_trace/completed_at``), not just the filename. A gate
  that says "two files differ" is not actionable; one that names the field is.
* Every other file is compared byte-for-byte. There is no allowlist for
  non-JSON content: a generated ``.tsx`` that changes between two identical
  runs is a defect, always.
* The allowlist is matched against a *normalised* path in which list indices
  become ``[*]``, so one entry covers a repeated field without hiding a change
  in list length (length changes are reported separately as ``LEN``).

Two classes of difference are *normalised away* rather than allowlisted, because
they are artefacts of the harness rather than properties of the build:

* **The output root.** The two builds must go into two different directories, so
  every absolute path recorded in an artifact differs by construction. Both
  roots are rewritten to ``<OUTPUT_ROOT>``, which keeps the rest of the path
  under comparison — a screenshot moving from ``render-home.png`` to something
  else still fails.
* **The loopback port.** The pre-deploy preview server binds an OS-assigned
  ephemeral port, so ``http://127.0.0.1:57207/about`` and
  ``http://127.0.0.1:57628/about`` describe the same route. Only the port digits
  are rewritten to ``<PORT>``; the path is still compared, so a change in *which*
  routes were reached still fails.

Normalisations are counted and printed. A normalisation is a claim about the
harness; an allowlist entry is a claim about the build. Keeping them separate is
what stops "this path differs" from silently covering "this artifact changed".

Exit-code contract for the CLI entry point, per the repo's gate rule
(PASS / FAIL / NOT_MEASURED are three distinct outcomes):

* ``0`` — PASS: the only differences were allowlisted.
* ``1`` — FAIL: at least one unexplained difference.
* ``3`` — NOT_MEASURED: the comparison could not be performed (a root is
  missing, or a JSON artifact could not be parsed).
"""

from __future__ import annotations

import fnmatch
import json
import os
import re
import sys

_INDEX_RE = re.compile(r"\[\d+\]")
_LOOPBACK_PORT_RE = re.compile(r"\b(127\.0\.0\.1|localhost|\[::1\]):\d+")

#: Counts of harness normalisations applied during the last tree_diff() call.
NORMALISATIONS = {"output_root": 0, "loopback_port": 0}


def normalise_path(path: str) -> str:
    """`/items[3]/at` -> `/items[*]/at` so one allowlist entry covers a list."""
    return _INDEX_RE.sub("[*]", path)


def normalise_value(value, roots):
    """Rewrite harness artefacts (build root, ephemeral port) out of a value.

    Only strings are touched. *roots* is the pair of output roots being compared;
    both are rewritten to the same placeholder so the two builds become
    comparable without loosening what is actually compared.
    """
    if not isinstance(value, str):
        return value
    out = value
    for root in roots:
        if root and root in out:
            out = out.replace(root, "<OUTPUT_ROOT>")
            NORMALISATIONS["output_root"] += 1
    replaced, n = _LOOPBACK_PORT_RE.subn(lambda m: m.group(1) + ":<PORT>", out)
    if n:
        NORMALISATIONS["loopback_port"] += n
        out = replaced
    return out


def relative_files(root: str, ignore_globs):
    """Every file under *root*, as paths relative to root, minus ignored globs."""
    out = set()
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        if rel_dir == ".":
            rel_dir = ""
        # Prune ignored directories so we never walk node_modules or .next.
        keep = []
        for d in dirnames:
            rel = os.path.join(rel_dir, d) if rel_dir else d
            if not _matches_any(rel, ignore_globs) and not _matches_any(rel + "/", ignore_globs):
                keep.append(d)
        dirnames[:] = keep
        for f in filenames:
            rel = os.path.join(rel_dir, f) if rel_dir else f
            if _matches_any(rel, ignore_globs):
                continue
            out.add(rel)
    return out


def _matches_any(path, globs):
    return any(fnmatch.fnmatch(path, g) for g in globs)


def _normalise_doc(obj, roots):
    if isinstance(obj, dict):
        return dict((k, _normalise_doc(v, roots)) for k, v in obj.items())
    if isinstance(obj, list):
        return [_normalise_doc(v, roots) for v in obj]
    return normalise_value(obj, roots)


def _walk_json(a, b, path, out):
    if type(a) is not type(b):
        out.append((path, "TYPE", type(a).__name__, type(b).__name__))
        return
    if isinstance(a, dict):
        for k in sorted(set(a) | set(b)):
            if k not in a:
                out.append((path + "/" + str(k), "ONLY-B", None, _short(b[k])))
            elif k not in b:
                out.append((path + "/" + str(k), "ONLY-A", _short(a[k]), None))
            else:
                _walk_json(a[k], b[k], path + "/" + str(k), out)
    elif isinstance(a, list):
        if len(a) != len(b):
            out.append((path, "LEN", len(a), len(b)))
            return
        for i, (x, y) in enumerate(zip(a, b)):
            _walk_json(x, y, path + "[" + str(i) + "]", out)
    else:
        if a != b:
            out.append((path, "VALUE", _short(a), _short(b)))


def _short(v, limit=160):
    s = repr(v)
    return s if len(s) <= limit else s[:limit] + "…"


#: fnmatch reads "[*]" as a character class matching a literal asterisk, but in
#: a normalised JSON path "[*]" is a literal three-character list marker. Swap it
#: for a sentinel in both pattern and subject so fnmatch's wildcard "*" still
#: works everywhere else.
_LIST_SENTINEL = "\x00LIST\x00"


def _path_matches(norm_path, pattern):
    return fnmatch.fnmatch(norm_path.replace("[*]", _LIST_SENTINEL),
                           pattern.replace("[*]", _LIST_SENTINEL))


def _is_allowed(rel_file, norm_path, entries):
    for e in entries:
        if not fnmatch.fnmatch(rel_file, e.get("file", "*")):
            continue
        if _path_matches(norm_path, e["path"]):
            return e
    return None


def tree_diff(root_a, root_b, allowlist):
    """Compare two build roots.

    Returns ``(unexplained, allowed)``: two lists of difference dicts. A caller
    that gets an empty ``unexplained`` may treat the build as deterministic.

    Raises ``FileNotFoundError`` if either root is missing and ``ValueError``
    if a JSON artifact cannot be parsed — both are NOT_MEASURED conditions, not
    passes.
    """
    for root in (root_a, root_b):
        if not os.path.isdir(root):
            raise FileNotFoundError(root)

    ignore_globs = [i["path"] for i in allowlist.get("ignore", [])]
    entries = allowlist.get("fields", [])
    roots = (os.path.abspath(root_a), os.path.abspath(root_b))
    NORMALISATIONS["output_root"] = 0
    NORMALISATIONS["loopback_port"] = 0

    files_a = relative_files(root_a, ignore_globs)
    files_b = relative_files(root_b, ignore_globs)

    unexplained = []
    allowed = []

    for rel in sorted(files_a - files_b):
        unexplained.append({"file": rel, "path": "", "kind": "ONLY-IN-A",
                            "a": "present", "b": "absent"})
    for rel in sorted(files_b - files_a):
        unexplained.append({"file": rel, "path": "", "kind": "ONLY-IN-B",
                            "a": "absent", "b": "present"})

    for rel in sorted(files_a & files_b):
        pa, pb = os.path.join(root_a, rel), os.path.join(root_b, rel)
        with open(pa, "rb") as fh:
            raw_a = fh.read()
        with open(pb, "rb") as fh:
            raw_b = fh.read()
        if raw_a == raw_b:
            continue

        if rel.endswith(".json"):
            try:
                doc_a = json.loads(raw_a.decode("utf-8"))
                doc_b = json.loads(raw_b.decode("utf-8"))
            except (ValueError, UnicodeDecodeError) as exc:
                raise ValueError("%s: %s" % (rel, exc))
            doc_a = _normalise_doc(doc_a, roots)
            doc_b = _normalise_doc(doc_b, roots)
            leaves = []
            _walk_json(doc_a, doc_b, "", leaves)
            if not leaves:
                # No leaf differs after normalisation. Either the whole diff was
                # a harness artefact (fine), or key order / formatting moved —
                # which is still non-determinism in a committed artifact, so
                # check that explicitly rather than assuming the benign case.
                if json.dumps(doc_a) != json.dumps(doc_b):
                    unexplained.append({"file": rel, "path": "<key-order>",
                                        "kind": "BYTES",
                                        "a": "n bytes=%d" % len(raw_a),
                                        "b": "n bytes=%d" % len(raw_b)})
                continue
            for path, kind, va, vb in leaves:
                norm = normalise_path(path)
                rec = {"file": rel, "path": norm, "kind": kind,
                       "a": va, "b": vb}
                hit = _is_allowed(rel, norm, entries)
                if hit:
                    rec["reason"] = hit.get("reason", "")
                    allowed.append(rec)
                else:
                    unexplained.append(rec)
        else:
            # Text files get the same harness normalisation as JSON: a generated
            # .env.local or .tsx that embeds the build root is not a difference.
            try:
                txt_a = normalise_value(raw_a.decode("utf-8"), roots)
                txt_b = normalise_value(raw_b.decode("utf-8"), roots)
                if txt_a == txt_b:
                    continue
                raw_a, raw_b = txt_a.encode("utf-8"), txt_b.encode("utf-8")
            except UnicodeDecodeError:
                pass  # genuinely binary (screenshots); compare bytes as-is
            unexplained.append({"file": rel, "path": "<bytes>", "kind": "BYTES",
                                "a": _first_diff_line(raw_a, raw_b, "a"),
                                "b": _first_diff_line(raw_a, raw_b, "b")})

    return unexplained, allowed


def _first_diff_line(raw_a, raw_b, which):
    la = raw_a.decode("utf-8", "replace").splitlines()
    lb = raw_b.decode("utf-8", "replace").splitlines()
    for i in range(max(len(la), len(lb))):
        x = la[i] if i < len(la) else "<eof>"
        y = lb[i] if i < len(lb) else "<eof>"
        if x != y:
            return "L%d: %s" % (i + 1, (x if which == "a" else y)[:160])
    return "<identical lines, trailing bytes differ>"


def load_allowlist(path):
    with open(path) as fh:
        return json.load(fh)


def main(argv):
    if len(argv) < 3:
        sys.stderr.write(
            "usage: determinism_diff.py <root-a> <root-b> [allowlist.json]\n")
        return 3
    root_a, root_b = argv[1], argv[2]
    allow_path = argv[3] if len(argv) > 3 else os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "determinism-allowlist.json")
    try:
        allowlist = load_allowlist(allow_path)
    except (IOError, OSError, ValueError) as exc:
        sys.stderr.write("NOT_MEASURED: cannot read allowlist %s: %s\n"
                         % (allow_path, exc))
        return 3
    try:
        unexplained, allowed = tree_diff(root_a, root_b, allowlist)
    except FileNotFoundError as exc:
        sys.stderr.write("NOT_MEASURED: build root missing: %s\n" % exc)
        return 3
    except ValueError as exc:
        sys.stderr.write("NOT_MEASURED: unparseable JSON artifact: %s\n" % exc)
        return 3

    print("  harness normalisations: output-root %d · loopback-port %d"
          % (NORMALISATIONS["output_root"], NORMALISATIONS["loopback_port"]))
    print("  allowlisted differences: %d" % len(allowed))
    for rec in allowed:
        print("    · %s %s — %s" % (rec["file"], rec["path"], rec.get("reason", "")))
    if unexplained:
        print("")
        print("  UNEXPLAINED differences: %d" % len(unexplained))
        for rec in unexplained:
            print("    ✗ %s %s [%s]" % (rec["file"], rec["path"], rec["kind"]))
            print("        a: %s" % rec["a"])
            print("        b: %s" % rec["b"])
        print("")
        print("DETERMINISM: FAIL")
        return 1
    print("")
    print("DETERMINISM: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
