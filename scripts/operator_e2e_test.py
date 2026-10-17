import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib.operational_adapter import execute_capability

def run_builder_operator():
    print("🚀 Starting Builder Operator E2E (Capabilities Only)")
    
    project_name = "demo-operator"
    industry = "ecommerce"
    brief = "A minimal test brief"
    
    # 1. reference.extract
    res = execute_capability("reference.extract", {"url": "https://example.com"})
    assert res["success"]
    
    # 2. store.setup
    res = execute_capability("store.setup", {"architecture": res["evidence"]["architecture"]})
    assert res["success"]
    
    # 3. reference.import
    res = execute_capability("reference.import", {"products_csv": "dummy"})
    assert res["success"]
    
    # 4. analysis.journey
    res = execute_capability("analysis.journey", {})
    assert res["success"]
    
    # 5. project.contract
    res = execute_capability("project.contract", {})
    assert res["success"]
    
    # 6. planning.manifest
    res = execute_capability("planning.manifest", {"project_name": project_name, "industry": industry})
    assert res["success"]
    
    # 7. planning.spec
    res = execute_capability("planning.spec", {"manifest": res["evidence"]["manifest"]})
    assert res["success"]
    site_spec = res["evidence"]["site_spec"]
    
    # 8. composition.scaffold
    section_plan = site_spec["sections"][0]
    res = execute_capability("composition.scaffold", {
        "project_name": project_name,
        "section_plan": section_plan,
        "preset_content": industry,
        "brief": brief
    })
    # Since it's an empty harvest, it's expected to omit if allow_generated is false, 
    # but we will just check it executes without blowing up.
    print("Scaffold Result:", res)
    
    # 9. content.bind
    if res["success"] and res["evidence"]["code"]:
        bind_res = execute_capability("content.bind", {
            "section_plan": section_plan,
            "template_code": res["evidence"]["code"]
        })
        print("Bind Result:", bind_res)
    
    # 10. runtime.verify
    res = execute_capability("runtime.verify", {})
    assert res["success"]
    
    print("\n✅ Builder Operator E2E Completed Successfully")

if __name__ == "__main__":
    run_builder_operator()
