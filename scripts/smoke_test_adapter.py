import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.operational_adapter import execute_capability
import json

def test(cap_id: str, inputs: dict, expected_status="passed"):
    res = execute_capability(cap_id, inputs)
    if res["status"] != expected_status:
        print(f"❌ {cap_id} failed. Expected {expected_status}, got {res['status']}. Error: {res.get('error')}")
        sys.exit(1)
    else:
        print(f"✅ {cap_id} {res['status']}")
    return res

def run_smoke_tests():
    print("🚀 Starting Independent Smoke Tests for Operational Adapter\n")
    
    # 1. project.start
    start_res = test("project.start", {"project_name": "smoke-test-project"})
    site_dir = start_res["state_delta"]["site_dir"]
    
    # Provide a dummy package.json for layer9 verification and npm run build
    (Path(site_dir) / "package.json").write_text('{"name": "smoke-test", "scripts": {"build": "mkdir -p .next && echo dummy-build-id > .next/BUILD_ID"}}')
    
    # 2. media.generate
    test("media.generate", {"project_name": "smoke-test-project"})
    
    # 3. site.build
    test("site.build", {"site_dir": site_dir})
    
    # 4. site.deploy
    test("site.deploy", {"site_dir": site_dir})
    
    # 5. runtime.verify (Should succeed because site.build generated a dummy .next artifact)
    test("runtime.verify", {"site_dir": site_dir})
    
    # 6. runtime.verify (Should fail because bad url)
    test("runtime.verify", {"url": "http://this-does-not-exist.localdomain"}, expected_status="failed")

    # 7. runtime.verify (Should fail because no inputs)
    test("runtime.verify", {}, expected_status="failed")
    
    # 8. Check planning.manifest (Existing wrapper)
    test("planning.manifest", {"project_name": "smoke-test-project", "industry": "ecommerce"})

    print("\n✅ All independent smoke tests passed.")

if __name__ == "__main__":
    run_smoke_tests()
