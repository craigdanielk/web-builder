// Shared `claude` CLI wrapper (subscription auth, no API key) — mirrors the
// Python _call_claude_cli path in orchestrate.py so the JS audit/extraction
// tooling runs subscription-only, matching the generation half of the pipeline.
// This removes the split-brain LLM auth (JS = Anthropic API SDK, Python = CLI)
// that blocked the --from-url audit-driven flow at stage 0a.
const { execFileSync } = require('child_process');
const os = require('os');
const fs = require('fs');
const path = require('path');

const _MODEL_ALIAS = { 'claude-sonnet-4-5-20250929': 'sonnet', 'sonnet': 'sonnet', 'opus': 'opus', 'haiku': 'haiku' };

/**
 * Generate text via `claude -p` headless mode. Runs in an isolated temp cwd
 * with all tools denied so it only returns text. Synchronous (mirrors the
 * blocking Python path); callers may drop their `await`.
 * @param {string} prompt
 * @param {string} model - CLI alias or full model id (mapped to an alias)
 * @returns {string}
 */
function callClaudeCli(prompt, model = 'sonnet') {
  const alias = _MODEL_ALIAS[model] || 'sonnet';
  const td = fs.mkdtempSync(path.join(os.tmpdir(), 'wb-claude-js-'));
  try {
    const out = execFileSync(
      'claude',
      ['-p', prompt, '--model', alias, '--output-format', 'text', '--allowedTools', 'NoTool'],
      { cwd: td, encoding: 'utf-8', maxBuffer: 64 * 1024 * 1024, timeout: 360000 }
    );
    return (out || '').trim();
  } finally {
    try { fs.rmSync(td, { recursive: true, force: true }); } catch (_e) { /* best-effort cleanup */ }
  }
}

module.exports = { callClaudeCli };
