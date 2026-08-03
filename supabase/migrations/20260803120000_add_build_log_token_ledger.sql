-- W-A/A6 — token accounting: record what a build actually cost in LLM tokens.
-- Shape: {calls, measured_calls, unmeasured_calls, input_tokens, output_tokens,
--         by_stage: {<stage>: {calls, input_tokens, output_tokens}}}
-- measured_calls vs unmeasured_calls is deliberate: the CLI path reports no
-- usage object, and an unmeasured call must stay distinguishable from a free one.
ALTER TABLE build_log ADD COLUMN IF NOT EXISTS token_ledger jsonb;
