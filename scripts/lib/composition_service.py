from typing import Dict, Any, Optional
import tempfile
from pathlib import Path
import orchestrate
from lib.contracts import CompositionRequest, CompositionResult, ContentBindRequest, ContentBindResult

def composition_scaffold(request: CompositionRequest) -> CompositionResult:
    """Application-service seam for composition.scaffold"""
    old_output_dir = orchestrate.OUTPUT_DIR
    try:
        with tempfile.TemporaryDirectory() as td:
            orchestrate.OUTPUT_DIR = Path(td)
            files, summary = orchestrate.stage_sections(
                sections=[request["section_plan"]],
                preset=request.get("preset_content", "ecommerce"),
                project_name=request["project_name"],
                section_contexts=request.get("asset_context"),
                site_spec={"style": {"animation": {"intensity": request.get("intensity", "moderate")}}},
                output_subdir="isolated_scaffold",
                section_file_names=["section.tsx"],
                brief=request.get("brief")
            )
            
            if files:
                code = files[0].read_text(encoding="utf-8")
                return {
                    "success": True,
                    "code": code,
                    "is_generated": summary and summary.get("generated_strings_total", 0) > 0,
                    "error": None,
                    "token_usage_label": files[0].name
                }
            else:
                return {
                    "success": False,
                    "code": None,
                    "is_generated": False,
                    "error": "stage_sections omitted the section",
                    "token_usage_label": None
                }
    except Exception as e:
        return {
            "success": False,
            "code": None,
            "is_generated": False,
            "error": str(e),
            "token_usage_label": None
        }
    finally:
        orchestrate.OUTPUT_DIR = old_output_dir

def content_bind(request: ContentBindRequest) -> ContentBindResult:
    """Application-service seam for content.bind"""
    try:
        val, cov, prov = orchestrate.build_template_fill(
            request["section_plan"], 
            request["template_code"]
        )
        bound = orchestrate.apply_template_fill(request["template_code"], val, cov)
        return {
            "success": True,
            "bound_code": bound,
            "values": val,
            "coverage": cov,
            "provenance": prov,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "bound_code": request["template_code"],
            "values": {},
            "coverage": {},
            "provenance": [],
            "error": str(e)
        }
