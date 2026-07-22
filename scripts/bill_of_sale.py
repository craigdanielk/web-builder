"""
Bill of Sale (BoS) — Build Manifest & Orchestration Model
──────────────────────────────────────────────────────────
A Bill of Sale is a formal JSON manifest of every build item (page → sections)
that the web-builder pipeline must produce.  Each **line item** represents one
coherent output unit (typically a page) and receives a **build_trace** after
the pipeline processes it.

Architecture
  BoS → read_line_items() → iterate → drive build → write_trace() → persist
                                                                    ↓
                                                          re-audit loop picks up
                                                          build_trace per item

Usage (CLI):
  python scripts/orchestrate.py <project> --bill-of-sale <path>

Usage (Python):
  bos = BillOfSale.load("path/to/bill-of-sale.json")
  for item in bos.line_items:
      trace = bos.build(item, ...)
      bos.write_trace(item.item_id, trace)
  bos.save()
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


# ─── Data Model ───────────────────────────────────────────────────────────────

@dataclass
class LineItem:
    """One unit of build work (typically one page + its sections)."""
    item_id: str
    type: str                     # "page" | "section"
    page_type: str                # "homepage" | "collection-template" | …
    position: int = 0
    archetype: str = ""
    variant: str = ""
    content_direction: str = ""
    sections: list[dict] = field(default_factory=list)  # nested sections (for page type)
    build_trace: dict | None = None


@dataclass
class BuildTrace:
    """Record of what happened when a line item was built."""
    status: str                    # "pending" | "in_progress" | "completed" | "failed" | "skipped"
    files: list[str] = field(default_factory=list)
    verified_against: str = ""
    started_at: str = ""
    completed_at: str = ""
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    bos_line_items_count: int = 0

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "files": self.files,
            "verified_against": self.verified_against,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "errors": self.errors,
            "warnings": self.warnings,
            "bos_line_items_count": self.bos_line_items_count,
        }


@dataclass
class BillOfSale:
    """Top-level build manifest."""
    bill_of_sale_id: str = ""
    project_name: str = ""
    industry: str = ""
    generated_at: str = ""
    version: str = "1.0"
    line_items: list[LineItem] = field(default_factory=list)

    # ─── Factory ──────────────────────────────────────────────────────────────

    @classmethod
    def new(cls, project_name: str, industry: str = "") -> "BillOfSale":
        return cls(
            bill_of_sale_id=str(uuid.uuid4()),
            project_name=project_name,
            industry=industry,
            generated_at=datetime.now(timezone.utc).isoformat(),
            version="1.0",
            line_items=[],
        )

    @classmethod
    def from_manifest(cls, manifest: dict, project_name: str | None = None) -> "BillOfSale":
        """Build a BoS from a site-manifest dict (Layer 6 multi-page manifest).

        Each manifest page becomes one line_item.  Sections within that page are
        stored as the line item's nested ``sections`` list.
        """
        bos = cls.new(
            project_name=project_name or manifest.get("project", ""),
            industry=manifest.get("industry", ""),
        )
        for page in manifest.get("pages", []):
            page_id = page.get("id", "")
            page_type = page.get("page_type", "homepage")
            page_sections = page.get("sections", [])
            item = LineItem(
                item_id=f"{page_id}-{page_type}",
                type="page",
                page_type=page_type,
                sections=page_sections,
                build_trace=None,
            )
            bos.line_items.append(item)
        return bos

    @classmethod
    def from_sections(
        cls,
        sections: list[dict],
        project_name: str,
        industry: str = "",
    ) -> "BillOfSale":
        """Build a BoS from a flat section list (single-page pipeline).

        Each section becomes one line_item so every section gets its own
        build_trace.  A synthetic "page" line_item wraps all sections when
        the caller needs page-level granularity.
        """
        bos = cls.new(project_name, industry)
        # Page-level item
        page_item = LineItem(
            item_id=f"{project_name}-page",
            type="page",
            page_type="homepage",
            sections=sections,
            build_trace=None,
        )
        bos.line_items.append(page_item)
        # Per-section items
        for i, sec in enumerate(sections):
            arch = sec.get("archetype", "FEATURES")
            var = sec.get("variant", "default")
            bos.line_items.append(LineItem(
                item_id=f"{project_name}-section-{i + 1:02d}-{arch.lower()}",
                type="section",
                page_type="homepage",
                position=i + 1,
                archetype=arch,
                variant=var,
                content_direction=sec.get("content", "") or sec.get("content_direction", ""),
                build_trace=None,
            ))
        return bos

    # ─── I/O ──────────────────────────────────────────────────────────────────

    @classmethod
    def load(cls, path: str | Path) -> "BillOfSale":
        """Load a Bill of Sale from a JSON file."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        items = [LineItem(**it) for it in data.get("line_items", [])]
        return cls(
            bill_of_sale_id=data.get("bill_of_sale_id", ""),
            project_name=data.get("project_name", ""),
            industry=data.get("industry", ""),
            generated_at=data.get("generated_at", ""),
            version=data.get("version", "1.0"),
            line_items=items,
        )

    def save(self, path: str | Path | None = None) -> str:
        """Write the BoS (including build_traces) back to JSON.  Returns the path used."""
        if path is None:
            path = f"bill-of-sale-{self.project_name}.json"
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "bill_of_sale_id": self.bill_of_sale_id,
            "project_name": self.project_name,
            "industry": self.industry,
            "generated_at": self.generated_at,
            "version": self.version,
            "line_items": [asdict(it) for it in self.line_items],
        }
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        return str(path)

    # ─── Build Trace Management ───────────────────────────────────────────────

    def get_item(self, item_id: str) -> LineItem | None:
        """Look up a line item by its item_id."""
        for item in self.line_items:
            if item.item_id == item_id:
                return item
        return None

    def write_trace(
        self,
        item_id: str,
        trace: BuildTrace,
    ) -> None:
        """Write (or update) the build_trace for a single line item in place.

        The in-memory dict is updated immediately; call ``.save()`` to persist.
        """
        item = self.get_item(item_id)
        if item is None:
            raise KeyError(f"Line item '{item_id}' not found in Bill of Sale")
        item.build_trace = trace.to_dict()

    def mark_started(self, item_id: str) -> None:
        """Mark a line item as in_progress and record the start timestamp."""
        self.write_trace(item_id, BuildTrace(
            status="in_progress",
            started_at=datetime.now(timezone.utc).isoformat(),
        ))

    def mark_completed(
        self,
        item_id: str,
        files: list[str],
        verified_against: str = "",
        errors: list[str] | None = None,
        warnings: list[str] | None = None,
    ) -> None:
        """Mark a line item as completed with its output files and any issues."""
        self.write_trace(item_id, BuildTrace(
            status="completed",
            files=files,
            verified_against=verified_against,
            started_at="",  # preserved below
            completed_at=datetime.now(timezone.utc).isoformat(),
            errors=errors or [],
            warnings=warnings or [],
            bos_line_items_count=len(self.line_items),
        ))
        # Carry forward the start timestamp from the in-progress trace if available
        item = self.get_item(item_id)
        if item and item.build_trace:
            prev = item.build_trace
            prev["completed_at"] = datetime.now(timezone.utc).isoformat()
            prev["bos_line_items_count"] = len(self.line_items)

    def mark_failed(
        self,
        item_id: str,
        errors: list[str],
    ) -> None:
        """Mark a line item as failed with error details."""
        self.write_trace(item_id, BuildTrace(
            status="failed",
            errors=errors,
            completed_at=datetime.now(timezone.utc).isoformat(),
        ))

    def completed_line_items(self) -> list[LineItem]:
        """Return all line items that have a completed build_trace."""
        return [
            it for it in self.line_items
            if it.build_trace and it.build_trace.get("status") == "completed"
        ]

    @property
    def total_count(self) -> int:
        return len(self.line_items)

    @property
    def completed_count(self) -> int:
        return len(self.completed_line_items())


# ─── Convenience helpers used by orchestrate.py ───────────────────────────────

def ensure_bill_of_sale(
    project_name: str,
    industry: str,
    output_dir: Path,
    manifest: dict | None = None,
    sections: list[dict] | None = None,
) -> BillOfSale:
    """Load an existing BoS from the output directory or create one from the manifest/sections.

    The BoS is persisted as ``output_dir / bill-of-sale.json`` so successive
    pipeline stages can read/write build_traces without re-parsing.
    """
    bos_path = output_dir / "bill-of-sale.json"
    if bos_path.exists():
        try:
            bos = BillOfSale.load(bos_path)
            # Update project_name / industry in case they changed
            bos.project_name = project_name
            bos.industry = industry
            return bos
        except (json.JSONDecodeError, KeyError):
            pass  # Corrupted — recreate

    if manifest:
        bos = BillOfSale.from_manifest(manifest, project_name)
    elif sections:
        bos = BillOfSale.from_sections(sections, project_name, industry)
    else:
        bos = BillOfSale.new(project_name, industry)

    bos.project_name = project_name
    bos.industry = industry
    bos.save(bos_path)
    return bos


def load_build_traces(output_dir: Path) -> list[dict]:
    """Load all completed build_traces from the BoS in output_dir.

    Used by the re-audit loop to consume build results after a pipeline run.
    Returns a list of build_trace dicts, one per completed line item.
    """
    bos_path = output_dir / "bill-of-sale.json"
    if not bos_path.exists():
        return []
    try:
        bos = BillOfSale.load(bos_path)
        return [
            item.build_trace
            for item in bos.line_items
            if item.build_trace
        ]
    except (json.JSONDecodeError, KeyError, OSError):
        return []
