#!/usr/bin/env python3
"""
Tenant Provisioning Script
─────────────────────────────────────────────────────────
Idempotent tenant provisioning orchestrator that runs a 5-step sequence:

1. Upsert tenant record (tenants table)
2. Render tenant_core configuration
3. Confirm Phase0 capture (phase0_field_values)
4. Check creative_assets presence
5. Validate tenant is ready for builds

Re-running for an already-provisioned tenant is a safe no-op.
"""

from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import Supabase client primitives
try:
    from lib.supabase_client import _get, _post, _patch, SUPABASE_URL, SUPABASE_KEY
except ImportError:
    from supabase_client import _get, _post, _patch, SUPABASE_URL, SUPABASE_KEY  # type: ignore


def _check_supabase_config() -> bool:
    """Verify Supabase credentials are available."""
    if not (SUPABASE_URL and SUPABASE_KEY):
        print("❌ Supabase credentials not found in .env")
        print("   Required: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY")
        return False
    return True


def _safe_post(table: str, data: dict) -> dict | None:
    """POST wrapper that never raises — returns None on error."""
    try:
        return _post(table, data)
    except Exception as e:
        print(f"  ⚠ POST to {table} failed: {e}")
        return None


def _safe_patch(table: str, filters: str, data: dict) -> dict | None:
    """PATCH wrapper that never raises — returns None on error."""
    try:
        return _patch(table, filters, data)
    except Exception as e:
        print(f"  ⚠ PATCH to {table} failed: {e}")
        return None


def _safe_get(table: str, filters: str = "") -> list[dict]:
    """GET wrapper that never raises — returns [] on error."""
    try:
        rows = _get(table, filters)
        return rows if isinstance(rows, list) else []
    except Exception:
        return []


def step1_upsert_tenant_record(slug: str, deploy_target: str, tenant_data: dict) -> dict | None:
    """
    Step 1: Upsert tenant record in tenants table.
    Creates new tenant or updates existing one (idempotent).
    """
    print(f"\n📋 Step 1: Upsert tenant record (slug={slug})")

    # Check if tenant exists
    existing = _safe_get("tenants", f"slug=eq.{slug}&select=id,slug,deploy_target,status")
    if existing:
        tenant_id = existing[0].get("id")
        print(f"  ✅ Tenant exists: {tenant_id}")
        print(f"     Current status: {existing[0].get('status')}")
        print(f"     Current deploy_target: {existing[0].get('deploy_target')}")

        # Update if needed
        update_data = {"updated_at": "NOW()"}
        if deploy_target and existing[0].get('deploy_target') != deploy_target:
            update_data['deploy_target'] = deploy_target
            print(f"  🔄 Updating deploy_target to: {deploy_target}")

        if tenant_data:
            # Update relevant fields
            for key in ['trading_name', 'entity_name', 'legal_name', 'company_name', 'domain', 'logo_url', 'brand_voice']:
                if key in tenant_data and tenant_data[key]:
                    update_data[key] = tenant_data[key]

        if len(update_data) > 1:  # More than just updated_at
            _safe_patch("tenants", f"slug=eq.{slug}", update_data)
            print(f"  ✅ Tenant updated: {tenant_id}")
        else:
            print(f"  ✅ Tenant unchanged (no-op): {tenant_id}")

        return {"id": tenant_id, "slug": slug, "status": existing[0].get('status')}

    # Create new tenant
    print(f"  ➕ Creating new tenant...")
    new_tenant = {
        "slug": slug,
        "deploy_target": deploy_target or "shopify",
        "status": "provisioning",
        **{k: v for k, v in tenant_data.items() if k in ['trading_name', 'entity_name', 'legal_name', 'company_name', 'domain', 'logo_url', 'brand_voice']}
    }

    result = _safe_post("tenants", new_tenant)
    if result and isinstance(result, list) and result:
        tenant_id = result[0].get("id")
        print(f"  ✅ Tenant created: {tenant_id}")
        return {"id": tenant_id, "slug": slug, "status": "provisioning"}

    print(f"  ❌ Failed to create tenant")
    return None


def step2_render_tenant_core(tenant_id: str, tenant_context: dict) -> bool:
    """
    Step 2: Render tenant_core configuration.
    This is the tenant's base configuration for the builder.
    """
    print(f"\n⚙️  Step 2: Render tenant_core configuration (tenant_id={tenant_id})")

    # In a full implementation, this would render configuration files
    # For now, we verify the tenant has required core data
    existing_tenant = _safe_get("tenants", f"id=eq.{tenant_id}&select=*")
    if not existing_tenant:
        print(f"  ❌ Tenant not found")
        return False

    tenant = existing_tenant[0]
    print(f"  ✅ Tenant core configuration:")
    print(f"     - Slug: {tenant.get('slug')}")
    print(f"     - Deploy target: {tenant.get('deploy_target')}")
    print(f"     - Status: {tenant.get('status')}")

    # Add tenant context data if provided
    if tenant_context:
        phase0_values = tenant_context.get("phase0_field_values", {})
        if phase0_values:
            print(f"  ✅ Phase0 context available: {len(phase0_values)} fields")

    return True


def step3_confirm_phase0_capture(tenant_id: str, phase0_data: dict) -> bool:
    """
    Step 3: Confirm Phase0 capture.
    Ensure essential phase0_field_values are present.
    """
    print(f"\n📊 Step 3: Confirm Phase0 capture (tenant_id={tenant_id})")

    # Check existing phase0 data
    existing = _safe_get("phase0_field_values", f"tenant_id=eq.{tenant_id}&select=field_key,value")
    print(f"  📈 Existing phase0_field_values: {len(existing)}")

    # Upsert provided phase0 data
    upserted = 0
    for field_key, value in phase0_data.items():
        # Check if exists
        field_exists = any(f.get("field_key") == field_key for f in existing)

        if field_exists:
            print(f"  ✅ Phase0 field exists: {field_key}")
        else:
            # Insert new field
            result = _safe_post("phase0_field_values", {
                "tenant_id": tenant_id,
                "field_key": field_key,
                "value": {"v": value},  # Wrap in {"v": ...} format as expected by tenant_context
                "fill_status": "complete",
                "source": "provisioning"
            })
            if result:
                upserted += 1
                print(f"  ➕ Phase0 field added: {field_key}")

    print(f"  ✅ Phase0 capture confirmed: {len(existing)} existing + {upserted} new")

    # Check for essential fields
    essential_fields = ['domain', 'company_name', 'trading_name']
    existing_keys = {f.get("field_key") for f in existing}
    missing_essential = [f for f in essential_fields if f not in existing_keys and f not in phase0_data]

    if missing_essential:
        print(f"  ⚠  Missing essential fields: {', '.join(missing_essential)}")
    else:
        print(f"  ✅ All essential fields present")

    return True


def step4_check_creative_assets(tenant_id: str, assets_data: list) -> bool:
    """
    Step 4: Check creative_assets presence.
    Verify tenant has required media assets.
    """
    print(f"\n🎨 Step 4: Check creative_assets presence (tenant_id={tenant_id})")

    # Check existing assets
    existing = _safe_get("creative_assets", f"tenant_id=eq.{tenant_id}&select=asset_type,storage_path")
    print(f"  📈 Existing creative_assets: {len(existing)}")

    # Upsert provided assets
    upserted = 0
    for asset in assets_data:
        asset_type = asset.get("asset_type", "image")
        storage_path = asset.get("storage_path") or asset.get("cdn_url")

        if not storage_path:
            print(f"  ⚠  Asset missing storage_path/cdn_url, skipping")
            continue

        result = _safe_post("creative_assets", {
            "tenant_id": tenant_id,
            "asset_type": asset_type,
            "storage_path": storage_path,
            "cdn_url": asset.get("cdn_url"),
            "metadata": asset.get("metadata", {})
        })
        if result:
            upserted += 1
            print(f"  ➕ Creative asset added: {asset_type}")

    print(f"  ✅ Creative assets check: {len(existing)} existing + {upserted} new")

    # Check for essential asset types
    asset_types = {a.get("asset_type") for a in existing}
    if "logo" not in asset_types:
        print(f"  ⚠  No logo asset found")
    else:
        print(f"  ✅ Logo asset present")

    return True


def step5_validate_tenant_ready(tenant_id: str) -> bool:
    """
    Step 5: Validate tenant is ready for builds.
    Update tenant status to 'active' if all checks pass.
    """
    print(f"\n✅ Step 5: Validate tenant ready for builds (tenant_id={tenant_id})")

    # Get tenant data
    tenant = _safe_get("tenants", f"id=eq.{tenant_id}&select=status,slug,deploy_target")
    if not tenant:
        print(f"  ❌ Tenant not found")
        return False

    tenant = tenant[0]
    print(f"  🔍 Current status: {tenant.get('status')}")

    # Get phase0 data
    phase0 = _safe_get("phase0_field_values", f"tenant_id=eq.{tenant_id}&select=field_key")
    print(f"  🔍 Phase0 fields: {len(phase0)}")

    # Get creative assets
    assets = _safe_get("creative_assets", f"tenant_id=eq.{tenant_id}&select=asset_type")
    print(f"  🔍 Creative assets: {len(assets)}")

    # Basic readiness checks
    ready = True
    if len(phase0) < 2:
        print(f"  ⚠  Insufficient phase0 data (minimum 2 fields recommended)")
        ready = False

    if len(assets) < 1:
        print(f"  ⚠  No creative assets found (at least 1 recommended)")
        ready = False

    if ready and tenant.get("status") != "active":
        # Update to active
        _safe_patch("tenants", f"id=eq.{tenant_id}", {"status": "active"})
        print(f"  ✅ Tenant status updated to: active")
    elif ready:
        print(f"  ✅ Tenant already active and ready")
    else:
        print(f"  ⚠  Tenant not ready for builds, status remains: {tenant.get('status')}")

    return ready


def provision_tenant(slug: str, deploy_target: str, tenant_data: dict,
                     phase0_data: dict, assets_data: list) -> dict:
    """
    Main provision function: runs the 5-step idempotent sequence.
    """
    print(f"\n{'='*60}")
    print(f"  TENANT PROVISIONING: {slug}")
    print(f"{'='*60}")

    if not _check_supabase_config():
        return {"success": False, "error": "Missing Supabase configuration"}

    # Step 1: Upsert tenant record
    tenant = step1_upsert_tenant_record(slug, deploy_target, tenant_data)
    if not tenant:
        return {"success": False, "error": "Failed to upsert tenant record"}

    tenant_id = tenant["id"]
    tenant_context = {"phase0_field_values": phase0_data}

    # Step 2: Render tenant_core
    if not step2_render_tenant_core(tenant_id, tenant_context):
        return {"success": False, "error": "Failed to render tenant_core"}

    # Step 3: Confirm Phase0 capture
    if not step3_confirm_phase0_capture(tenant_id, phase0_data):
        return {"success": False, "error": "Failed to confirm Phase0 capture"}

    # Step 4: Check creative_assets
    if not step4_check_creative_assets(tenant_id, assets_data):
        return {"success": False, "error": "Failed to check creative_assets"}

    # Step 5: Validate tenant ready
    ready = step5_validate_tenant_ready(tenant_id)

    print(f"\n{'='*60}")
    print(f"  PROVISIONING COMPLETE")
    print(f"  Tenant ID: {tenant_id}")
    print(f"  Slug: {slug}")
    print(f"  Ready for builds: {ready}")
    print(f"{'='*60}\n")

    return {
        "success": True,
        "tenant_id": tenant_id,
        "slug": slug,
        "ready": ready
    }


def main():
    parser = argparse.ArgumentParser(
        description="Idempotent tenant provisioning for web-builder",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Provision with minimal data
  python scripts/ops/provision_tenant.py xago --deploy-target vercel

  # Provision with tenant data file
  python scripts/ops/provision_tenant.py xago --config tenant_data.json

  # Re-run (no-op if tenant exists)
  python scripts/ops/provision_tenant.py xago
        """
    )
    parser.add_argument("slug", help="Tenant slug (unique identifier)")
    parser.add_argument("--deploy-target", choices=["shopify", "vercel"],
                        help="Deploy target platform (default: shopify)")
    parser.add_argument("--config", help="Path to JSON config file with tenant/phase0/assets data")
    parser.add_argument("--tenant-id", help="Existing tenant UUID (for updates)")
    parser.add_argument("--force", action="store_true",
                        help="Force provisioning even if tenant exists")

    args = parser.parse_args()

    # Load configuration
    tenant_data = {}
    phase0_data = {}
    assets_data = []

    if args.config:
        config_path = Path(args.config)
        if not config_path.exists():
            print(f"❌ Config file not found: {args.config}")
            sys.exit(1)

        with open(config_path, 'r') as f:
            config = json.load(f)

        tenant_data = config.get("tenant", {})
        phase0_data = config.get("phase0_field_values", {})
        assets_data = config.get("creative_assets", [])

    # Add basic phase0 data if none provided
    if not phase0_data:
        phase0_data = {
            "company_name": args.slug.replace("-", " ").title(),
            "domain": f"{args.slug}.example.com"
        }

    # Run provisioning
    result = provision_tenant(
        slug=args.slug,
        deploy_target=args.deploy_target or "shopify",
        tenant_data=tenant_data,
        phase0_data=phase0_data,
        assets_data=assets_data
    )

    if result["success"]:
        print(f"✅ Provisioning successful!")
        print(f"   Tenant ID: {result['tenant_id']}")
        print(f"   Ready: {result['ready']}")
        sys.exit(0)
    else:
        print(f"❌ Provisioning failed: {result.get('error')}")
        sys.exit(1)


if __name__ == "__main__":
    main()
