# Design conformance: close the loop that already exists

**Status:** proposed, not built
**Author:** drafted 2026-08-25, rewritten the same day after running the gate
**Scope:** three changes to `conformance-gate.js` / `design_conformance.py` / the preset. No new gate.

---

## What the first draft got wrong

The first version of this file proposed a new fourth gate and a five-block
hand-authored preset schema. Both were wrong:

- **The gate already exists.** `scripts/quality/conformance-gate.js` serves the
  built site on a local port, runs `design_conformance.py` against it, returns
  0/1/3, and writes `conformance.json` with `{layer, rule, measured, expected}`.
- **The rules are already measured, not declared.** Ten `dna_*` rules read the
  benchmark and compare it to computed styles off the real render. Hand-authoring
  declarations for things an extractor measures is how 44 preset files drift.

The correct work is smaller and is described below.

---

## The evidence

Run, 2026-08-25, against the cape-crypto tree at `viz/01-band-rhythm`:

```
node scripts/quality/conformance-gate.js \
  --build-dir <tenants>/cape-crypto/site \
  --benchmark benchmarks/enterprise-payments-bvnk.json \
  --output <out>

CONFORMANCE GATE: FAIL — 4 violation(s), 6 conform, 0 not measured, 65 routes
```

| Rule | Measured | Expected |
|---|---|---|
| `dna_type_scale` | off-scale sizes incl. **23px ×61**, 26px ×21, 11px ×13, 46px ×9 | the 11-step scale |
| `dna_font_families` | Instrument Sans ×13601, IBM Plex Mono ×202, Archivo ×389 | `["Poppins"]` |
| `dna_shadow_layers` | **5 layers ×2**, 1 layer ×8 | `<= 1 layers` |
| `dna_palette_size` | **37 unique** | `<= 20` |

**Calibration note, recorded deliberately.** The same tree was scored by a model
reading source against a rubric earlier that day and returned 72/100 — asserting
"sizes all on the token scale" and "no shadow at rest, single coherent language."
The gate measured both as violations. **Two of four findings were inverted by
eyeball review, in the flattering direction, and the two most quantifiable
defects were missed entirely.** This is the argument for the deterministic path,
and it should not need making twice.

---

## Change 1 — per-route attribution (highest leverage, do first)

**The defect.** `route` and `section` are `null` on every finding. The gate's own
header explains why: the `dna_*` rules are site-level aggregates, `evaluate()`
flattens `measured["per_page"]` into one `aggregate` and stamps `pages[0]` onto
every evidence record, so reporting a route would be inventing a fact. The gate
is being honest — the honesty is correct and the limitation is what costs.

**The cost, measured.** After the run above, locating the 5-layer shadow took
three greps and found one candidate (`support/blocks.tsx:139`, a *1*-layer
shadow — not it). The 23px ×61 is still unlocated. The site has no `clamp()` and
no `text-[23px]`, so the source is neither obvious nor greppable. **A finding
without a route is a manual hunt across 65 routes**, and that hunt is where the
tokens and the time actually go.

**The change.** `evaluate()` iterates `per_page` instead of flattening it, so
each violation carries the route it was measured on. `conformance-gate.js`
already has `route` and `section` in its violation shape and already carries
`routes_measured` / `affected_routes` — the consumer side needs nothing. This is
an upstream change in `aurelix-uiux-audit/lib/design_conformance.py`.

**Why first.** Every other improvement is worth less until findings are
addressable. Fixes go from "hunt the codebase" to "open one route" — which is
the whole ask: deterministic, fast, cheap.

**Test.** A rule that fails on exactly one route must report exactly that route.
Introduce a 3-layer shadow on `/fees` only; `dna_shadow_layers` must name
`/fees`. Remove it; the finding goes. Both runs reported.

---

## Change 2 — `deviations`, so the gate stops crying wolf

`dna_font_families` expects `["Poppins"]` and measures Archivo / Instrument Sans
/ IBM Plex Mono. That is **not a defect**. The benchmark resolves Circular (a
proprietary Lineto face that cannot be served) to Poppins via `font_match.py`,
and the operator deliberately replaced it. The gate has no way to know, so it
fails a build for a decision that was made on purpose.

A gate that fails on intent is a gate people learn to ignore. `26555da` in the
tenant repo is already titled *"the conformance gate stops crying wolf"* — this
is the same class of problem, one level up.

**The change.** One block in the preset, and only this one:

```yaml
deviations:
  - rule: dna_font_families
    benchmark_value: ["Poppins"]
    build_value: ["Archivo", "Instrument Sans", "IBM Plex Mono"]
    reason: "Circular cannot be licensed or served; Poppins is font_match's
             geometric-sans resolution, not an operator choice. Archivo carries
             the display voice the reproduction lacked."
    decided_by: Craig
    decided_on: 2026-08-24
```

`evaluate()` reads it and downgrades a matching violation to `waived`, counted
and printed separately — never silently dropped. An entry missing `reason`,
`decided_by` or `decided_on` is a usage error, not a warning. A `build_value`
that no longer matches what is measured re-raises the violation, so a waiver
cannot rot into a blanket exemption.

**This is the only hand-authored block in this plan.** It exists because intent
is the one thing an extractor cannot measure.

---

## Change 3 — symmetric extraction, to close the measured gap

The three remaining findings from the earlier review are not covered by any of
the ten rules: **icon stroke weight cardinality** (1.5 vs 1.6), **structural
repetition** (the same section opener on 10 of 11 bands), and **role binding**
(gold declared keyline-only, shipped as a button fill).

The first draft proposed declaring these by hand. They should be **derived**.

**The asymmetry today.** The gate compares a build against the benchmark *JSON*,
which is a lossy summary of an extraction. `cta_buttons` records `radius_px` and
no fill colour — so "gold as a button fill" is invisible to it, no matter how
many rules are added.

**The change.** Diff extraction against extraction, not extraction against
summary:

```
extractReference(reference_url) → corpus_ref      # persist it
extractReference(http://127.0.0.1:PORT) → corpus_build
diff(corpus_build, corpus_ref) → violations
```

`extractReference(url, outputDir)` already takes any URL — pointing it at
localhost is free. `capture-benchmark-pages.js` already persists corpora to
`benchmarks/corpora/<market-slug>/`, and the census records that both prior
corpora were lost to a scratchpad path, which is the direct reason
`enterprise-payments-bvnk.json` carries `corpus_absent_consequence: "every
number in this file is an assertion with no evidence behind it that this
repository can replay."`

**Persisting the reference corpus is therefore prerequisite work that is already
owed**, independent of this plan.

Three rules fall out of the diff as arithmetic, with no declaration anywhere:

| New rule | Derivation |
|---|---|
| `dna_stroke_cardinality` | distinct `stroke-width` values on icon SVGs; build cardinality > reference cardinality → FAIL |
| `dna_opener_repetition` | element-type frequency of the first child of each band, both sides; build share exceeds reference share → FAIL |
| `dna_token_role` | for each colour, the set of CSS properties it lands on; a colour appearing as `background-color` where the reference only ever uses it on `border-color` → FAIL |

`dna_token_role` is the one that catches gold-as-a-fill, and it needs no
`role_bindings` block: the reference already demonstrates the role, and the
demonstration is the rule.

**Ordering.** `dna_token_role` needs the corpus. The other two can read the
build's own distribution against a cardinality floor and ship earlier if the
corpus capture slips.

---

## What is deliberately not in this plan

- **No new gate.** `conformance-gate.js` is the gate. Three changes, same exit
  contract, same three states.
- **No new preset schema.** One `deviations` block. Everything else is measured.
- **No rubric and no model judgment in the loop.** The 72 is in this file as a
  calibration record, not as an input.
- **The `signature` obligation is dropped from this plan.** It is real — a build
  can pass every measured rule and still be forgettable — but it is not
  measurable from a reference and does not belong in a deterministic gate. It
  needs its own plan, or it stays a human call at review.

---

## Sequence

1. Per-route attribution in `evaluate()`. Re-run against cape-crypto; every
   finding above should name a route.
2. Fix what the routes point at. Mechanical once addressable.
3. `deviations` waiver path; `dna_font_families` moves to `waived`.
4. Persist the reference corpus (owed regardless).
5. `dna_stroke_cardinality`, `dna_opener_repetition`, then `dna_token_role`.
6. Run the full rule set against the 13 deployed builds **without wiring the
   exit code**. Record the distribution before enforcing. A floor nothing clears
   is miscalibrated, not strict.

Each new rule ships with a mutation test — introduce the defect, watch the rule
fail, remove it, watch it pass, report both runs. A test that cannot fail is not
a test.
