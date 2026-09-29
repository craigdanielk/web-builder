#!/usr/bin/env bash
# Higgsfield CLI wrapper for agent use. bash (NOT zsh: zsh won't word-split flag bundles).
#   hf.sh preflight                      -> binary, auth, credits, recent spend by model
#   hf.sh cost  <model> [params...]      -> credit quote (needs the same media flags as the real run)
#   hf.sh run   <out.json> <model> [params...]   -> create --wait --json, recovers if --wait drops
#   hf.sh fetch <job.json|job-id> <out-file>     -> download result_url
#   hf.sh ledger [N]                     -> spend today grouped by model (detects foreign consumers)
# Lessons: use ~/.npm-global/bin/higgsfield (>=1.1.x; /opt/homebrew 0.1.x is stale); run OUTSIDE the
# agent sandbox (keychain/network); Seedance 2.5 start/end images need --mode omni_reference;
# 2.5 max 1080p, 2.0 supports 4k; --wait can lose the connection while the job completes server-side.
set -uo pipefail
H="${HF_BIN:-$HOME/.npm-global/bin/higgsfield}"
PY="${HF_PY:-python3}"
cmd="${1:-}"; shift || true
case "$cmd" in
  preflight)
    "$H" --version; "$H" account status 2>&1 | grep -iv token || { echo "NOT AUTHENTICATED: run '$H auth login' (browser OAuth; keep localhost callback ports free)"; exit 2; }
    "$0" ledger 100 ;;
  cost) m="$1"; shift; "$H" generate cost "$m" "$@" ;;
  run)
    out="$1"; m="$2"; shift 2
    "$H" generate create "$m" "$@" --wait --wait-timeout 30m --wait-interval 10s --json > "$out" 2>&1
    if ! grep -q '"status": *"completed"' "$out"; then
      echo "[hf] wait did not report completion; recovering from job list" >&2
      "$H" generate list --json > "$out.list" 2>/dev/null
      "$PY" - "$out.list" "$m" "$out" <<'PYX'
import json,sys
d=json.load(open(sys.argv[1])); items=d if isinstance(d,list) else (d.get('items') or d.get('jobs') or [])
for j in items:
    if j.get('job_type')==sys.argv[2]:
        json.dump(j,open(sys.argv[3],'w'),indent=2); print(f"[hf] recovered {j.get('id')} status={j.get('status')}"); break
PYX
    fi
    grep -oE '"(status|result_url)": *"[^"]*"' "$out" | head -2 ;;
  fetch)
    src="$1"; dst="$2"
    if [ -f "$src" ]; then u=$(grep -oE '"(result_url|url)": *"https[^"]*"' "$src" | head -1 | sed 's/.*"\(https[^"]*\)"/\1/');
    else "$H" generate get "$src" --json > /tmp/hf_job.json; u=$(grep -oE '"(result_url|url)": *"https[^"]*"' /tmp/hf_job.json | head -1 | sed 's/.*"\(https[^"]*\)"/\1/'); fi
    [ -n "$u" ] || { echo "[hf] no result url"; exit 3; }
    curl -sfL -o "$dst" "$u" && echo "[hf] $dst $(du -h "$dst" | cut -f1)" ;;
  ledger)
    "$H" account transactions --json --size "${1:-100}" > /tmp/hf_tx.json
    "$PY" - <<'PYX'
import json,collections,datetime
d=json.load(open('/tmp/hf_tx.json')); items=d if isinstance(d,list) else (d.get('items') or d.get('transactions') or [])
today=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d'); agg=collections.defaultdict(lambda:[0,0.0])
for t in items:
    if t['created_at'].startswith(today): a=agg[t['display_name']]; a[0]+=1; a[1]+=t['credits']
for m,(n,c) in sorted(agg.items(),key=lambda x:x[1][1]): print(f"  {m:24s} jobs={n:3d} credits={c:8.1f}")
print("  (any model you did not run = another consumer on this account)")
PYX
    ;;
  *) sed -n '2,12p' "$0"; exit 1 ;;
esac
