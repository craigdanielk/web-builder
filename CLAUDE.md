# Web Builder — Repo Context

**Last re-measured: 2026-08-18.**

> **This file was rewritten on 2026-08-18.** The version it replaced was dated
> 2026-02-17 (v3.1.0) and described a February system: an LLM-first pipeline with
> a Claude scaffold call, a "content tokens not populated" active issue, a
> 1,034-component animation library, and a `--from-url` clone mode as the normal
> path. Every one of those is now false. It also carried a 700-line file map and
> a 20-entry changelog that had not been maintained since February. Both are git
> history now; a stale map is worse than no map, because agents navigate by it.

---

## What this file is for

**Only web-builder-local facts that are not documented better elsewhere.** This
file does not restate pipeline internals — it points at the two documents that
own them:

| Question | Read |
|---|---|
| What is inside the build? Stage map, `SectionArtifact`, the design-token chain, verified data shapes | **`../docs/PIPELINE_ARCHITECTURE.md`** — canonical |
| System shape: services, the chain, entry points, the data plane, standing rules, open defects | **`../CLAUDE.md`** — canonical |
| The evidence behind any claim in either | `../docs/census/*.md`. **A census wins over prose.** |

**You are the web-builder sub-agent.** This is a **submodule** — an
independently git-tracked repo with its own `main`. Commit here separately from
the parent, with explicit paths, and never push.

---

## Before your first command

```bash
cd web-builder && set -a && . ./.env && set +a     # zsh: ./.env, not . .env
python3 scripts/run_tests.py
```

`.env` holds exactly two keys, `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.
**There is no root `.env`.** `orchestrate.py` never calls `load_dotenv`, and
`lib/supabase_client.py` only fills keys **not already** in `os.environ` — so an
ambient `SUPABASE_URL` from your shell profile silently wins over the file and
points you at a project where `section_archetypes` looks empty. It has **74
rows**. This has cost multiple sessions an hour each.

---

## The node

```
python3 scripts/orchestrate.py <project> [flags]
```

28 declared flags plus the positional `<project>`
(`grep -c "parser.add_argument" scripts/orchestrate.py` → 29, 2026-08-18). The
flag contract, the ratified benchmark and the required-vs-optional table live in
`../CLAUDE.md` §6. **`--deploy` is a local production build + `npm run start`,
never a Vercel publish** — it exists to gate the render audit.

`orchestrate.py` is **one node inside `../run_pipeline.py`**, not the system.
The chain can now express a real build (`build_orchestrate_cmd()` forwards
`--tenant`, `--target-platform`, `--captures`, `--routes`, `--benchmark` and
more), so hand-driving the node is a choice rather than the only option.

### Exit codes

```
EXIT_OK = 0 · EXIT_FAILED = 1 · EXIT_REVIEW_NEEDED = 2
EXIT_NOT_MEASURED = 3 · EXIT_USAGE = 64
```

`resolve_build_outcome()` evaluates: recorded build failures → 1; deploy not
requested → 0; render audit passed → 0; review needed → 2; audit never ran → 3;
fallthrough → 1. **NOT_MEASURED ≠ PASS.**

---

## Repo layout — the directories that matter

Verified on disk 2026-08-18. Counts are commands, not memory.

| Path | What | Measured |
|---|---|---|
| `scripts/orchestrate.py` | the node | **12,261 lines** |
| `scripts/lib/` | the Python libraries the node imports | **24 modules** |
| `scripts/quality/` | Node.js extraction, harvest, gates, probes | `compile-gate.js`, `conformance-gate.js`, `render-audit.js`, `lib/html-page-harvest.js` |
| `scripts/test_*.py` | the tests, beside the code | **54 files** |
| `scripts/run_tests.py` | the whole suite, one command, three-state | **54/54 passed · 0 failed · 0 not measured** |
| `section-templates/` | local React templates | **15 `.tsx`** across 25 archetype dirs + `manifest.json` |
| `benchmarks/` | the design authority | 4 files + generated `index.json` + `corpora/` |
| `rails-templates/` | emitted application rails (`cms/`) | migrations, `src/lib`, middleware, `MANIFEST.json` |
| `skills/presets/` | operator-authored presets | 44 `.md` |
| `skills/animation-components/registry/` | the animation store | see below |
| `output/` | all build output, gitignored | `output/extractions/` is the crawl **input** store |

**There is no `tests/` directory. Do not create one.**

### Templates: 15 local, and the build used all of them

The claim *"4 of 74 templates read the design tokens"* — which this file carried
until 2026-08-18 — is **retired**. It came from a grep that over-reports (it
flags button padding and prose inside comments).

Measured 2026-08-18: **15 local templates**
(`find section-templates -name '*.tsx' | wc -l`). The unconverted tier is the
*database*, and the gap there is body depth, not literals — DB median 52.5 lines
vs local median 213.5. `../docs/PIPELINE_ARCHITECTURE.md` §11.7.

**The local/Supabase resolution split of the last build is `[UNVERIFIED]`.** No
artifact records it: `section-artifacts/*/*.json` (21 files on the last
cape-crypto build) carry no `template_source`, and `bill-of-sale.json`'s 5 line
items carry none either. **Reading the split off a console line is not
evidence** — persist it into an artifact before quoting a number.

### The animation store: 48 backed, not 1,034

`os.path.exists` over every catalogue row's `source_file`, this checkout,
2026-08-18:

| File | Rows | Role |
|---|---:|---|
| `registry/animation_registry.json` | 1034 | the CATALOGUE. **Not** an inventory |
| `registry/animation_library.json` | **48** | the LIBRARY — file-backed. **The only rows selection may read** |
| `registry/animation_wishlist.json` | 986 | rows whose `source_file` does not exist |

The 986 name paths under `21st-dev-library/`, and that tree is absent from the
filesystem entirely — `ls skills/animation-components/` has no such directory and
a repo-wide `find` returns nothing. They cannot be re-derived from anything
present. Only **5** of the 48 backed rows carry `section_archetypes`.
`registry/annotate_backed_rows.py` is the store's only producer and emits all
three files.

`animation_registry.json.components` is an **ARRAY**; look up by the
`animation_id` field. `animation_id` is namespaced by **author**
(`codehagen__`, `shadcn__`), not by taxonomy — infer role from the role
*directory*, never the id prefix.

---

## Local conventions

**Build isolation.** Each project lives in `output/<project>/site/` with its own
`package.json` and `node_modules`. Never read another project's output directory.

**Roots are separate.** `--output-root` re-roots outputs; `--extractions-root`
re-roots the crawl input store. Neither moves the other, and setting only
`--output-root` prints where inputs are still being read from. Moving outputs
alone once silently took asset resolution from 5 extracted to 0 — and the build
exited 0.

**A template must declare `// Tokens: {a} {b}`** (or a `Slot placeholders`
block). A prose `Slots:` header is **not** a declaration — `declared_slots()`
does not read it, and the slot contract then falls back to a permissive brace
sweep that has rewritten `key={copy}` to `key=`. Name locals **camelCase**; the
token pattern is `[a-z][a-z_0-9]*`.

**Capture filenames use Python's builtin `hash()`**, salted per process. Key off
`record["url"]`, never the filename.

**Atomic writes.** Quality scripts write `path + '.tmp-' + Date.now()` then
rename.

---

## Working rules

- **Commit locally, explicit paths, never `git add -A`. Never push, no PRs.**
- Commit messages to a file, then `git commit -F <file>`. **The harness evaluates
  heredocs** — a quoted heredoc is not safe here.
- **A test that cannot fail is not a test.** Mutate the guarded code, watch the
  test fail, restore, report both runs.
- **Sourced or empty, never invented.** Cape Crypto is an FSCA-licensed FSP;
  a fabricated statistic is a regulatory liability, not a styling defect.
- **Do not add a gate that can only say yes.** Three outcomes, always:
  PASS · FAIL · NOT_MEASURED.
- **Verify at the artifact or the rendered DOM, never a log line.**
- Local `python3` is 3.9.6; CI runs 3.11/3.12.

## When this file changes

Update it when something **web-builder-local** changes: the directory layout, a
measured count above, a local convention, a trap. **Do not** add pipeline-internal
detail here — that belongs in `../docs/PIPELINE_ARCHITECTURE.md`, and a second
copy is how the two drift. Re-run the command before restating any number.
