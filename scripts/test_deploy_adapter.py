#!/usr/bin/env python3
"""
Deploy Adapter Verification — proves Vercel path without billed LLM build.
Tests the adapter logic directly at the scaffold/deploy layer under Python 3.9+.
Extracts class definitions from orchestrate.py via AST to avoid Python 3.10 union-type syntax.
"""

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

def extract_class_defs(filepath: Path, class_names: set[str]) -> str:
    """Extract class/function bodies from a Python file as source text."""
    source = filepath.read_text()
    tree = ast.parse(source)
    chunks = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.ClassDef, ast.FunctionDef)) and node.name in class_names:
            chunks.append(ast.get_source_segment(source, node))
    return "\n\n".join(chunks)


PASS = 0
FAIL = 0

def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}")
        if detail:
            print(f"    → {detail}")


print("\n═══ Deploy Adapter Verification ═══\n")

# Extract adapter classes from orchestrate.py and execute in a safe namespace
orch = ROOT / "scripts" / "orchestrate.py"
adapter_src = extract_class_defs(orch, {
    "DeployAdapter", "ShopifyAdapter", "VercelAdapter", "_resolve_adapter"
})

ns = {"__name__": "__deploy_adapter__"}
exec(compile(adapter_src, str(orch), "exec"), ns)

DeployAdapter = ns["DeployAdapter"]
ShopifyAdapter = ns["ShopifyAdapter"]
VercelAdapter = ns["VercelAdapter"]
_resolve_adapter = ns["_resolve_adapter"]

# ── Test 1: VercelAdapter produces clean Next.js app ──
vercel = VercelAdapter()
test("VercelAdapter.name == 'vercel'", vercel.name == "vercel")
test("VercelAdapter.should_inject_commerce is False", vercel.should_inject_commerce is False)
test("VercelAdapter.should_write_env is False", vercel.should_write_env is False)
test("VercelAdapter.should_generate_l7_pages is False", vercel.should_generate_l7_pages() is False)

# No Shopify nav defaults (no /collections)
nav_links = vercel.get_nav_default_links()
test("Vercel nav has no /collections", all(url != "/collections" for _, url in nav_links))
test("Vercel nav has Home", any(lbl == "Home" for lbl, _ in nav_links))

# No Shopify CTA default
cta = vercel.get_cta_url_default()
test("Vercel CTA default is '#' not /collections", cta == "#")

# No extra Shopify deps
test("VercelAdapter has no extra deps", len(vercel.get_package_extra_deps()) == 0)

# No Shopify image patterns in next.config
test("VercelAdapter next.config extras are empty", vercel.get_next_config_extras() == "")

# ── Test 2: ShopifyAdapter preserves current behavior ──
shopify = ShopifyAdapter()
test("ShopifyAdapter.name == 'shopify'", shopify.name == "shopify")
test("ShopifyAdapter.should_inject_commerce is True", shopify.should_inject_commerce is True)
test("ShopifyAdapter.should_write_env is True", shopify.should_write_env is True)
test("ShopifyAdapter.should_generate_l7_pages is True", shopify.should_generate_l7_pages() is True)

shopify_nav = shopify.get_nav_default_links()
test("Shopify nav has /collections", any(url == "/collections" for _, url in shopify_nav))
shopify_cta = shopify.get_cta_url_default()
test("Shopify CTA default is /collections", shopify_cta == "/collections")

shopify_next = shopify.get_next_config_extras()
test("Shopify next.config has cdn.shopify.com", "cdn.shopify.com" in shopify_next)

# ── Test 3: Adapter resolution ──
test("_resolve_adapter('vercel') returns VercelAdapter", isinstance(_resolve_adapter("vercel"), VercelAdapter))
test("_resolve_adapter('shopify') returns ShopifyAdapter", isinstance(_resolve_adapter("shopify"), ShopifyAdapter))

# ── Test 4: orchestrate.py has --target-platform flag ──
orch_text = orch.read_text()
test("orchestrate.py contains '--target-platform'", "--target-platform" in orch_text)
test("orchestrate.py contains VercelAdapter", "VercelAdapter" in orch_text)

# ── Test 5: build_log migration has target_platform column ──
migration_path = ROOT / "supabase" / "migrations" / "20260722000000_add_target_platform.sql"
test("target_platform migration exists", migration_path.exists())
if migration_path.exists():
    mig_text = migration_path.read_text()
    test("Migration adds target_platform column", "target_platform" in mig_text)
    test("Migration default is 'shopify'", "DEFAULT 'shopify'" in mig_text)

# ── Test 6: log_build accepts target_platform parameter ──
sys.path.insert(0, str(ROOT / "scripts"))
import lib.supabase_client as sc
test("log_build signature accepts target_platform", "target_platform" in sc.log_build.__code__.co_varnames)

# ── Test 7: deploy_env() — the adapter is the env authority (P2) ──
#
# Measured before the change: layer9_go_live.py populated env_vars ONLY from
# shopify_config.json (lines 45-53) and `if not env_vars: return 1` (63-65), so
# a correct Vercel build for a tenant with no storefront failed Layer 9 on the
# absence of a file that target never produces. stage_deploy's .env.local
# writer read the same file directly. Both now go through adapter.deploy_env().
print("\n── deploy_env() ──")

CFG = {"store_domain": "demo.myshopify.com", "storefront_access_token": "tok_abc"}

# Shopify: source and filters unchanged.
sh_env = shopify.deploy_env(shopify_config=CFG)
test("Shopify deploy_env source is shopify_config.json", sh_env["source"] == "shopify_config.json")
test("Shopify deploy_env reads the config", sh_env["reads_shopify_config"] is True)
test("Shopify values carry the store domain",
     sh_env["values"].get("SHOPIFY_STORE_DOMAIN") == "demo.myshopify.com")
test("Shopify values carry the storefront token",
     sh_env["values"].get("SHOPIFY_STOREFRONT_ACCESS_TOKEN") == "tok_abc")
test("Shopify declares the revalidation secret without valuing it",
     "SHOPIFY_REVALIDATION_SECRET" in sh_env["declared"]
     and "SHOPIFY_REVALIDATION_SECRET" in sh_env["unvalued"])

# The placeholder filter is carried over verbatim: Layer 4 writes a literal
# bracketed placeholder, and shipping it produced a site that 401s.
sh_ph = shopify.deploy_env(shopify_config={"store_domain": "d.myshopify.com",
                                           "storefront_access_token": "[REDACTED]"})
test("Shopify rejects a bracketed placeholder token",
     "SHOPIFY_STOREFRONT_ACCESS_TOKEN" not in sh_ph["values"])

# Shopify with no config at all: declared, unvalued, and it does not crash.
sh_none = shopify.deploy_env(shopify_config=None)
test("Shopify with no config values nothing", sh_none["values"] == {})
test("Shopify with no config still declares 3 names", len(sh_none["declared"]) == 3)

# Vercel: reaches env population with NO shopify_config.json in existence.
vc_env = vercel.deploy_env()
test("Vercel deploy_env returns a manifest with no config present",
     isinstance(vc_env, dict) and "values" in vc_env and "declared" in vc_env)
test("Vercel deploy_env never reads shopify_config.json",
     vc_env["reads_shopify_config"] is False)
test("Vercel deploy_env source is the platform declaration",
     vc_env["source"] == "platform_declaration")
test("Vercel declares no Shopify env name",
     not any(n.startswith("SHOPIFY_") for n in vc_env["declared"]))

# Handed a config anyway, the Vercel path must not leak it onto this target.
vc_leak = vercel.deploy_env(shopify_config=CFG)
test("Vercel ignores a shopify_config handed to it",
     vc_leak["values"] == {} and not any(
         "myshopify" in str(v) for v in vc_leak["values"].values()))
test("Vercel declares no Shopify name even when handed a config",
     not any(n.startswith("SHOPIFY_") for n in vc_leak["declared"]))

# The whole point: an empty Vercel manifest is not an error.
test("Vercel has no unvalued env to fail on", vc_leak["unvalued"] == [])

# Base adapter declares nothing and reads nothing.
base_env = DeployAdapter().deploy_env()
test("Base adapter declares no env", base_env["declared"] == [])
test("Base adapter reads no shopify_config", base_env["reads_shopify_config"] is False)

# declared_env_names is data-driven off DECLARED_ENV, so a module adds env in
# one place rather than a second reader growing somewhere else.
test("declared_env_names reads DECLARED_ENV",
     shopify.declared_env_names() == list(ShopifyAdapter.DECLARED_ENV["*"]))

# ── Test 8: layer9 no longer fails a Vercel target for a missing Shopify file ──
layer9 = (ROOT / "scripts" / "layer9_go_live.py").read_text()
test("layer9 gets its env from the adapter", "_deploy_env_manifest(" in layer9)
test("layer9 accepts --target-platform", "--target-platform" in layer9)
test("layer9 no longer reads store_domain directly",
     "config.get(\"store_domain\")" not in layer9)
test("layer9's empty-env return 1 is gated on declared env",
     'if manifest["declared"]:' in layer9)

# ── Test 9: stage_deploy's .env.local writer goes through the adapter ──
orch_src = orch.read_text()
test("stage_deploy calls adapter.deploy_env", "adapter.deploy_env(" in orch_src)
test("stage_deploy no longer builds SHOPIFY_STORE_DOMAIN by hand",
     'f\'SHOPIFY_STORE_DOMAIN={shopify_cfg.get("store_domain", "")}\'' not in orch_src)

print(f"\n{'═' * 60}")
print(f"  RESULTS: {PASS} passed, {FAIL} failed")
print(f"{'═' * 60}\n")

if FAIL > 0:
    sys.exit(1)
