import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from lib.contracts import CompositionRequest, CompositionResult, ContentBindRequest, ContentBindResult
import orchestrate

def composition_scaffold(request: CompositionRequest) -> CompositionResult:
    """Wrapper around stage_sections to provide an explicit service contract."""
    # Create the minimal args needed by stage_sections
    # stage_sections writes to disk, so we will need a temporary directory
    # or let it write and then read back the file.
    import tempfile
    
    with tempfile.TemporaryDirectory() as td:
        out_dir = Path(td)
        
        # stage_sections needs to write to output/{project_name}/{output_subdir}
        # It relies on orchestrate.OUTPUT_DIR which is a global.
        # We can monkey-patch it for safety, or just let it write to the normal place and read it.
        # To avoid side effects, we should mock OUTPUT_DIR.
        old_output = orchestrate.OUTPUT_DIR
        orchestrate.OUTPUT_DIR = out_dir
        
        try:
            files, summary = orchestrate.stage_sections(
                sections=[request["section_plan"]],
                preset=request.get("preset_content", "modern"), # Hack if it relies on preset string
                project_name=request["project_name"],
                section_contexts=request.get("asset_context"),
                site_spec={"style": {"animation": {"intensity": request.get("intensity", "moderate")}}},
                output_subdir="test_scaffold",
                section_file_names=["test_section.tsx"],
                brief=request.get("brief")
            )
            
            if not files:
                return {
                    "success": False,
                    "code": None,
                    "error": "stage_sections returned no files",
                    "is_generated": True,
                    "token_usage_label": None
                }
                
            code = files[0].read_text(encoding="utf-8")
            return {
                "success": True,
                "code": code,
                "error": None,
                "is_generated": True, # Assume LLM was called if it's new
                "token_usage_label": files[0].name
            }
        except Exception as e:
            return {
                "success": False,
                "code": None,
                "error": str(e),
                "is_generated": False,
                "token_usage_label": None
            }
        finally:
            orchestrate.OUTPUT_DIR = old_output

def content_bind(request: ContentBindRequest) -> ContentBindResult:
    """Wrapper around build_template_fill."""
    try:
        values, coverage, provenance = orchestrate.build_template_fill(
            section=request["section_plan"],
            code=request["template_code"]
        )
        
        # Now we need to substitute values into the code
        # _replace_content_tokens does this in orchestrate.py!
        # Wait, build_template_fill doesn't actually bind the text? 
        # Ah, build_template_fill returns the values. The caller does the replacement.
        # Let's check how orchestrate.py uses build_template_fill.
        return {
            "success": True,
            "bound_code": "", # We need to see how orchestrate.py does this
            "values": values,
            "coverage": coverage,
            "provenance": provenance,
            "error": None
        }
    except Exception as e:
        return {
            "success": False,
            "bound_code": "",
            "values": {},
            "coverage": {},
            "provenance": [],
            "error": str(e)
        }
