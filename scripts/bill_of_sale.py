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
    """One unit of build work (typically one page + its sections).

    Two provenances are supported on the same model:
      * pipeline-native items  (from_manifest / from_sections) — page/section units;
      * DAG bill items         (from_dag) — one audit finding per line item, carrying
        a ``disposition`` (built-fresh / gen+wire / carried-into-unified-app / …) and
        a ``verified_against`` rule_id that the re-audit loop re-checks to prove the
        finding closed.
    """
    item_id: str
    type: str                     # "page" | "section" | "finding"
    page_type: str                # "homepage" | "collection-template" | …
    position: int = 0
    archetype: str = ""
    variant: str = ""
    content_direction: str = ""
    sections: list[dict] = field(default_factory=list)  # nested sections (for page type)
    build_trace: dict | None = None
    # ── DAG bill provenance (uiux-bill-of-sale-dag-v1) ────────────────────────
    disposition: str = ""         # built-fresh | gen+wire | carried-into-unified-app | …
    verified_against: str = ""    # rule_id the re-audit re-checks to prove closure
    page: str = ""                # property/page the finding lives on (e.g. "exchange")
    section: str = ""             # build_role / build_target the fix lands in
    fix_locus: str = ""           # source_code | content | config | …


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
        """Load a Bill of Sale from a JSON file.

        Schema-aware: an external ``uiux-bill-of-sale-dag-v1`` bill (line items
        keyed by ``id`` + ``disposition``, e.g. the tenant audit Bill of Sale) is
        routed to :meth:`from_dag`; the pipeline-native format (line items keyed by
        ``item_id``) is loaded directly.  This lets ``--bill-of-sale`` consume the
        real audit bill without a converter step.
        """
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        if cls._is_dag_schema(data):
            return cls.from_dag(data, project_name=str(path))
        items = [LineItem(**it) for it in data.get("line_items", [])]
        return cls(
            bill_of_sale_id=data.get("bill_of_sale_id", ""),
            project_name=data.get("project_name", ""),
            industry=data.get("industry", ""),
            generated_at=data.get("generated_at", ""),
            version=data.get("version", "1.0"),
            line_items=items,
        )

    @staticmethod
    def _is_dag_schema(data: dict) -> bool:
        """Detect the external DAG bill schema (uiux-bill-of-sale-dag-v1)."""
        schema = str((data.get("meta") or {}).get("schema", ""))
        if schema.startswith("uiux-bill-of-sale-dag"):
            return True
        # Fallback heuristic: DAG items are keyed by ``id`` + ``disposition``,
        # never by the pipeline-native ``item_id``.
        items = data.get("line_items", [])
        if items and isinstance(items[0], dict):
            first = items[0]
            return "item_id" not in first and ("disposition" in first or "id" in first)
        return False

    @classmethod
    def from_dag(cls, data: dict, project_name: str | None = None) -> "BillOfSale":
        """Build a BoS from an external ``uiux-bill-of-sale-dag-v1`` bill.

        Each DAG ``line_item`` (one audit finding) becomes one :class:`LineItem`
        keyed by its stable ``id`` (e.g. ``BOS-034``).  Its ``disposition`` and
        ``verified_against`` rule_id are preserved so the build orchestration can
        drive the right deliverable and the re-audit loop can re-check closure.

        The mapping is deterministic — the same bill always yields the same set of
        line items in the same order — which underpins idempotent trace writeback.
        """
        meta = data.get("meta") or {}
        bos = cls.new(
            project_name=project_name or meta.get("tenant", "") or "",
            industry=meta.get("industry", ""),
        )
        bos.version = str(meta.get("schema", "uiux-bill-of-sale-dag-v1"))
        for di in data.get("line_items", []):
            finding = di.get("finding") or {}
            bt = di.get("build_trace") or {}
            rule_id = (
                bt.get("verified_against")
                or finding.get("rule_id")
                or di.get("id", "")
            )
            bos.line_items.append(LineItem(
                item_id=di.get("id", ""),
                type="finding",
                page_type=di.get("build_target", "") or di.get("stack", ""),
                content_direction=(di.get("fix") or {}).get("action", "") if isinstance(di.get("fix"), dict) else "",
                disposition=di.get("disposition", ""),
                verified_against=rule_id,
                page=di.get("property", "") or (di.get("page") or ""),
                section=di.get("build_role", "") or (di.get("section") or "") or di.get("build_target", ""),
                fix_locus=di.get("fix_locus", ""),
                build_trace=None,
            ))
        return bos

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


# ─── DAG disposition → build lane mapping ─────────────────────────────────────
#
# Deterministic, side-effect-free mapping from a line item's *disposition* to the
# build lane + action that drives its deliverable.  Same disposition → same lane,
# always — this is what keeps the trace writeback idempotent.

DISPOSITION_ACTIONS: dict[str, tuple[str, str]] = {
    "built-fresh":               ("build", "build-fresh-section"),
    "built-fresh+wired":         ("build", "build-fresh-and-wire"),
    "gen+wire":                  ("build", "generate-and-wire"),
    "carried-into-unified-app":  ("carry", "carry-into-unified-app"),
    "auto-resolved-by-rebuild":  ("auto", "auto-resolved-by-rebuild"),
    "retained":                  ("retain", "retain-existing"),
    "foundation":                ("foundation", "foundation-scaffold"),
    "copy-findings":             ("copy", "route-to-copy-gate"),
    "copy":                      ("copy", "route-to-copy-gate"),
}

# Lane → the trace status recorded at the orchestration layer.  A full billed build
# fills real statuses/commits later; at the orchestration layer we record intent.
_LANE_STATUS: dict[str, str] = {
    "copy": "routed-to-copy-gate",
}


def map_disposition(disposition: str) -> tuple[str, str]:
    """Map a disposition string to ``(lane, action)`` deterministically.

    Unknown dispositions fall back to the ``build`` lane so nothing is silently
    dropped from the audit — the finding still gets a trace and stays visible.
    """
    return DISPOSITION_ACTIONS.get((disposition or "").strip(), ("build", "build-deliverable"))


def build_dag_trace(item: LineItem, commit: str | None = None,
                    files: list[str] | None = None) -> dict:
    """Produce the deterministic build_trace dict for one DAG line item.

    Keyed by ``id`` and ``verified_against`` so the re-audit loop can re-check the
    exact rule that raised the finding.  Re-running over the same bill reproduces
    an identical dict — no timestamps, no randomness — so the writeback is a pure
    replace-in-place, never an append.
    """
    lane, action = map_disposition(item.disposition)
    status = _LANE_STATUS.get(lane, "planned")
    return {
        "id": item.item_id,
        "disposition": item.disposition,
        "lane": lane,
        "build_action": action,
        "status": status,
        "page": item.page,
        "section": item.section,
        "fix_locus": item.fix_locus,
        "files": list(files or []),
        "commit": commit,
        "verified_against": item.verified_against,
    }


def write_build_trace_artifact(output_dir: Path, traces: list[dict]) -> str:
    """Write ``output_dir/build-trace.json`` idempotently (replace-in-place).

    The artifact is rebuilt from scratch each call and keyed by line-item id, so a
    re-run over the same Bill of Sale leaves the trace count equal to the line-item
    count (N, never 2N).  Returns the path written.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    # De-dupe by id defensively — last write wins, so the count can never exceed
    # the number of distinct line items even if a caller passes duplicates.
    by_id: dict[str, dict] = {}
    for t in traces:
        by_id[t.get("id", "")] = t
    out = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(by_id),
        "traces": list(by_id.values()),
    }
    path = output_dir / "build-trace.json"
    path.write_text(json.dumps(out, indent=2, default=str), encoding="utf-8")
    return str(path)


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
