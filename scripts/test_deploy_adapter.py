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

print(f"\n{'═' * 60}")
print(f"  RESULTS: {PASS} passed, {FAIL} failed")
print(f"{'═' * 60}\n")

if FAIL > 0:
    sys.exit(1)
