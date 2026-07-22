# Copy Fidelity Node — Reproduce-from-Source (v1.0.0)

**Created:** 2026-07-22
**Status:** Active
**Depends On:** `universal-asset-intelligence-pipeline` (completed) — this closes its
weakest row (Text content), by moving copy from *generate-from-brief* to
*reproduce-from-source*, the same model images already use.

---

## Problem Statement

The Universal Asset Intelligence Pipeline defines one chain — **Extract → Map →
Insert → Fallback** — meant to run identically across every signal type. It does,
except for **copy**, which is graded "A" under the *wrong success criterion*:

| Signal | Map | Insert | Fallback | Real behaviour |
|--------|-----|--------|----------|----------------|
| Images | categories | **download real asset** | CSS gradient | **reproduce source** |
| Text content | brief + context | prompts | Claude generates | **invent from brief** |

`extract-reference.js` already harvests real per-section copy —
`{ headings[], body_text[20], ctas[10] }` — into `extraction-data.json` /
`site-spec.json`. But the generator consumes **only `headings[0]`** as a scaffold
hint (`orchestrate.py:1358, 1385`); `body_text` and `ctas` are referenced
**nowhere**. The rich harvest is dropped and sections are LLM-invented around an
archetype + one heading, then sanitized to generic placeholders ("Free Shipping",
"Verified Buyer").

Net defect: **the pipeline reproduces images but invents copy.** This node makes
it reproduce copy too — making the pipeline actually universal, as it already
claims to be.

## Design Principle — same cadence as media assets

> Pull the real copy **verbatim first**. Only change it when a **weakness is
> identified**, and the change is **derived from the source copy + the specific
> finding** — never invented fresh. Identical to media: self-host the real asset;
> only resize/reformat on an identified deficiency; never substitute a stock image.

```
Extract source copy (headings / body_text / ctas)          [EXISTS — extract-reference.js]
  → Map 1:1 to the rebuilt section's content slots
    → Insert VERBATIM into section_spec_json (LLM reproduces, MUST NOT paraphrase)
      → Weakness gate: revise a slot ONLY if flagged (audit finding / empty / broken)
        → Revision is anchored to source copy + the finding (rewrite, not replace)
          → Fallback (generate) ONLY when no source copy exists for that slot
            → NEVER silently invent over harvested copy
```

## Behaviour Contract

1. **Verbatim by default.** Every generated section slot that has a matching
   harvested string renders that string unchanged. The section-generation prompt
   receives the real `headings` / `body_text` / `ctas` and is instructed:
   *"Reproduce this copy exactly. Do not paraphrase, shorten, or embellish."*
2. **Weakness-gated revision.** A slot is revised **only** when an explicit signal
   says it's deficient:
   - an **audit / Bill-of-Sale finding** targets it (e.g. Xago BOS-001 missing H1,
     BOS-012 meta length, "proposition never quantified"); or
   - the harvested slot is **empty / boilerplate / broken**.
   The revision prompt is given *the source copy AND the finding*, and must
   **rewrite from** the source — evidence-linked to the finding's `rule_id`.
3. **Fallback = generate**, used only for slots with **no source copy** (net-new
   sections the rebuild adds, e.g. a SIGNUP-FORM that didn't exist on source, or
   Cell-2/3/4 where source access yields nothing). Generated copy is **marked as
   generated** in the output manifest, never conflated with reproduced copy.
4. **Cell-aware source** (ties to the deploy matrix):
   - Cell 1 (migrate, no access) — copy from crawl/extraction (Xago's path).
   - Cell 2 (migrate, repo access) — copy from real source content if richer.
   - Cell 3/4 (stay) — source copy is already canonical; node validates + revises
     flagged slots in place.

## Current-State grade correction

Re-grade **Text content** from a false **A** to **C** (extract ✓, map ✗ points at
brief not harvest, insert ✗ headings[0] only, fallback = invent) — same real grade
as Images before their download rung was wired. This node brings it to **A** under
the *correct* criterion (reproduce-from-source).

## Phases

### Phase 1 — Wire the harvest into generation (the missing "integrate from source" rung)
- Thread `content.{headings, body_text, ctas}` from `site-spec.json` into the
  `section_spec_json` block already sent to the section-gen LLM (`orchestrate.py`
  ~1345–1372).
- Add the verbatim-reproduction instruction to `templates/section-prompt.md`.
- Make sanitization **defer** to any token/slot already filled from harvested copy
  (skip the generic-default backfill when real copy is present).

### Phase 2 — Weakness gate
- Accept a per-section findings input (Bill-of-Sale line items keyed by
  page/section + `rule_id`). For each flagged slot, switch that slot from
  reproduce → revise-from-source, passing source copy + finding to the LLM.
- Emit a `copy_trace` per revised slot (`source_text`, `revised_text`,
  `finding_id`) for audit re-run / `build_trace`.

### Phase 3 — Promote to a named canonical node
- Surface as an explicit pipeline stage (e.g. Stage 2a: Copy Resolution) in
  `INTERFACE.md` stage list, with its own fallback ladder and a validation suite
  (harvested-slot coverage %, verbatim-match %, generated-slot count).
- Output a copy manifest (`reproduced` / `revised` / `generated` per slot) mirroring
  the asset manifest, so copy is inventoried exactly like media.

## Success Criteria
- A rebuilt page renders the source's **real** headlines, body, and CTAs verbatim
  where they exist; no generic placeholder copy over harvested content.
- Every revised string is traceable to a finding and derived from source copy.
- Generated (net-new) copy is explicitly flagged, never silently mixed in.
- Xago present-build reads as **Xago's own site** (real proposition, quantified per
  the audit), passing the content-fidelity re-audit (BOS L1/L4 items).
