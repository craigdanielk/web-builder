from typing import TypedDict, List, Dict, Any, Optional

class CompositionRequest(TypedDict):
    """Explicit request to scaffold or compose a section template."""
    project_name: str
    section_plan: Dict[str, Any]      # The single section's plan (e.g. from site_spec.json)
    preset_content: str               # The raw preset styles/brand data
    instructions: str                 # The instructions template (gsap/framer)
    animation_context: Optional[str]  # Sourced from animation analysis
    asset_context: Optional[str]      # Sourced from extraction data
    brief: Optional[str]              # Project brief
    intensity: str                    # e.g., 'moderate'

class CompositionResult(TypedDict):
    """Result of a composition request."""
    success: bool
    code: Optional[str]
    error: Optional[str]
    is_generated: bool                # True if the LLM was called
    token_usage_label: Optional[str]

class ContentBindRequest(TypedDict):
    """Request to bind harvested or generated content into a scaffolded template."""
    section_plan: Dict[str, Any]      # The single section's plan (containing harvested content)
    template_code: str                # The raw TSX code with {slots}

class ContentBindResult(TypedDict):
    """Result of binding content into a template."""
    success: bool
    bound_code: str
    values: Dict[str, str]            # slot -> harvested string
    coverage: Dict[str, Any]          # filled/empty counts
    provenance: List[Dict[str, Any]]  # slot provenance records
    error: Optional[str]
