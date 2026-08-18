#!/usr/bin/env bash
#
# determinism-check.sh — build <project> twice and prove the two trees differ
# only in fields the allowlist justifies.
#
#   ./scripts/quality/determinism-check.sh <project> [extra orchestrate args…]
#
# Example (the cape-crypto captures build):
#
#   ./scripts/quality/determinism-check.sh cape-crypto \
#     --preset cape-crypto --tenant cape-crypto \
#     --captures /path/to/capecrypto-20260803/captures \
#     --benchmark enterprise-payments-bvnk --max-pages 5
#
# The two builds go into scratch roots under $DETERMINISM_SCRATCH (default
# $TMPDIR/aurelix-determinism). They never touch web-builder/output/.
#
# Exit codes follow the repo gate contract — PASS, FAIL and NOT_MEASURED are
# three distinct outcomes and NOT_MEASURED is not a pass:
#   0  PASS            two builds differ only in allowlisted fields
#   1  FAIL            at least one unexplained difference (printed)
#   3  NOT_MEASURED    a build did not complete, so nothing was compared
#
# Determinism is the precondition for caching and for attributing any diff to a
# change: you cannot claim a change improved a build if two identical runs
# already differ.

set -u

# AURELIX-CAPABILITY — this file declares a capability under `--describe`.
#
# The marker above is what makes this file discoverable by
# `scripts/capability_register.py`; it is the explicit form used by instruments
# that cannot import the helper. Shell cannot import scripts/lib/capability.py,
# so the declaration is a JSON literal here and is validated by the compiler
# through `lib.capability.validate` when the register is compiled — same schema,
# same rules. `cannot_see` is not optional.
if [ "${1:-}" = "--describe" ]; then
  cat <<'CAPABILITY_JSON'
{
  "id": "aurelix.gate.determinism",
  "name": "Build determinism gate (build twice, diff the trees)",
  "kind": "gate",
  "invocation": "./scripts/quality/determinism-check.sh <project> [extra orchestrate args…]",
  "preconditions": [
    "orchestrate.py can build <project> non-interactively to completion, twice, with whatever extra args you pass through",
    "a writable scratch root — $DETERMINISM_SCRATCH, default $TMPDIR/aurelix-determinism. It never touches web-builder/output/",
    "an allowlist at $DETERMINISM_ALLOWLIST, default scripts/determinism-allowlist.json"
  ],
  "inputs": [
    "the two build trees it produces itself, under $DETERMINISM_SCRATCH/<project>/{a,b}",
    "determinism-allowlist.json — the justified-difference declarations",
    "the two build logs, a.log and b.log, used only to explain a NOT_MEASURED"
  ],
  "outputs": [
    "$DETERMINISM_SCRATCH/<project>/{a,b} — two full build trees, kept for inspection",
    "$DETERMINISM_SCRATCH/<project>/{a.log,b.log}",
    "stdout: every unexplained difference, named by FIELD path (/line_items[*]/build_trace/completed_at), not just by filename"
  ],
  "outcome": "whether two identical runs produce the same tree, which is the precondition for caching and for attributing any later diff to a change",
  "exit_contract": {
    "0": "PASS — the two trees differ only in fields the allowlist justifies",
    "1": "FAIL — at least one unexplained difference, or the two builds exited with different codes",
    "3": "NOT_MEASURED — no argument given, the scratch dir could not be created, or fewer than $DETERMINISM_MIN_FILES (default 20) files were produced, so there was nothing worth comparing"
  },
  "measures": [
    "JSON artifacts structurally, so a report names the field that moved rather than the file",
    "every non-JSON file byte-for-byte — a generated .tsx that changes between two identical runs is a defect, always",
    "the two builds' exit codes: two identical runs that end differently are non-deterministic whatever the trees look like",
    "it deliberately does NOT pin PYTHONHASHSEED, so a build that depends on the seed surfaces as a real defect"
  ],
  "cannot_see": [
    "whether the build is CORRECT. Two identically wrong builds pass — this gate measures reproducibility, nothing else, and it says so by comparing the trees even when both runs exited non-zero",
    "intermittent non-determinism: it samples exactly two runs, so anything that varies less often than one run in two can pass here and still be non-deterministic",
    "anything written outside --output-root. SKILLS_DIR, BRIEFS_DIR and every Supabase write live in neither scratch root and are compared by nothing",
    "the two differences it normalises away by construction: the output-root prefix and the loopback port digits of the preview server",
    "a difference that an allowlist entry wrongly justifies — the allowlist is a declaration, and a field listed there is invisible to this gate forever after",
    "anything at all when a build dies early: fewer than 20 files exits 3 rather than comparing two near-empty trees that would have read as a pass"
  ],
  "reachable_from": [],
  "cost": "two full builds back to back — minutes to tens of minutes, and roughly twice one build's disk"
}
CAPABILITY_JSON
  exit 0
fi

if [ "$#" -lt 1 ]; then
  echo "usage: determinism-check.sh <project> [extra orchestrate args…]" >&2
  exit 3
fi

PROJECT="$1"
shift

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEB_BUILDER="$(cd "$HERE/../.." && pwd)"
ALLOWLIST="${DETERMINISM_ALLOWLIST:-$WEB_BUILDER/scripts/determinism-allowlist.json}"
SCRATCH="${DETERMINISM_SCRATCH:-${TMPDIR:-/tmp}/aurelix-determinism}"
PY="${PYTHON:-python3}"

ROOT_A="$SCRATCH/$PROJECT/a"
ROOT_B="$SCRATCH/$PROJECT/b"

rm -rf "$ROOT_A" "$ROOT_B"
mkdir -p "$ROOT_A" "$ROOT_B" || { echo "NOT_MEASURED: cannot create $SCRATCH" >&2; exit 3; }

run_build() {
  local root="$1"
  local log="$2"
  shift 2   # the rest of "$@" is the caller's orchestrate args
  # Deliberately NOT pinning PYTHONHASHSEED: if a build depends on the seed,
  # this check must surface that as a real defect, not paper over it.
  ( cd "$WEB_BUILDER" && "$PY" scripts/orchestrate.py "$PROJECT" \
      --output-root "$root" --no-pause "$@" ) > "$log" 2>&1
}

echo "▶ determinism: building $PROJECT twice into $SCRATCH/$PROJECT"

run_build "$ROOT_A" "$SCRATCH/$PROJECT/a.log" "$@"
RC_A=$?
run_build "$ROOT_B" "$SCRATCH/$PROJECT/b.log" "$@"
RC_B=$?

# The exit code is itself an output. Two identical runs that end differently are
# non-deterministic no matter what the trees look like.
if [ "$RC_A" -ne "$RC_B" ]; then
  echo "DETERMINISM: FAIL — the two builds exited differently ($RC_A vs $RC_B)" >&2
  exit 1
fi

# Both runs may legitimately exit non-zero — a fatal gate (conformance) failing
# on both is a real, reproducible verdict and the trees up to it are still worth
# comparing. But a build that died early produces near-empty trees that would
# compare equal and read as a pass, so require a non-trivial tree first.
MIN_FILES="${DETERMINISM_MIN_FILES:-20}"
N_A=$(find "$ROOT_A" -type f | wc -l | tr -d ' ')
if [ "$N_A" -lt "$MIN_FILES" ]; then
  echo "NOT_MEASURED: only $N_A file(s) produced (need >= $MIN_FILES) — the build" >&2
  echo "  did not get far enough to compare. See $SCRATCH/$PROJECT/a.log" >&2
  tail -30 "$SCRATCH/$PROJECT/a.log" >&2
  exit 3
fi
if [ "$RC_A" -ne 0 ]; then
  echo "  note: both builds exited $RC_A (reproducibly). Comparing what they produced."
fi

echo "▶ determinism: comparing trees against $ALLOWLIST"
"$PY" "$WEB_BUILDER/scripts/lib/determinism_diff.py" "$ROOT_A" "$ROOT_B" "$ALLOWLIST"
exit $?
