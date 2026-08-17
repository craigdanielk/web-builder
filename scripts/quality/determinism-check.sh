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
