#!/usr/bin/env python3
"""The ProjectContract emitter produces stable keys and a section_uid map.

Guards, in the order of the harm they'd hide:

1. Keys are STABLE and UNIQUE per page — the key depends only on
   (section_type, ordinal-within-page), never on first-text / variant /
   implementation / file. A copy edit must not re-key the contract.
2. A page with two sections of the same semantic type yields ``base`` and
   ``base-2`` (the ordinal collision rule).
3. An unmapped archetype is emitted honestly: semanticType=None (JSON null) and
   validationStatus="unratified" — never an invented value.
4. The semanticSectionId <-> section_uid map keys match
   ``<projectId>:<pageSlug>:<sectionKey>`` exactly.
5. Changing the fixture's tsx (a copy edit) does not change the emitted keys.

Run: cd web-builder && python3 scripts/test_project_contract_emit.py
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
LIB = SCRIPTS / "lib"
for _p in (SCRIPTS, LIB):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from project_contract_emit import emit_project_contract, stable_section_key  # noqa: E402


def _artifact(page_dir: Path, filename: str, uid: str, archetype: str, variant: str, tsx: str) -> None:
    page_dir.mkdir(parents=True, exist_ok=True)
    (page_dir / filename).write_text(json.dumps({
        "section_uid": uid,
        "archetype": archetype,
        "variant": variant,
        "tsx": tsx,
        "section_index": 0,
    }))


def _build_fixture(root: Path) -> Path:
    sa = root / "section-artifacts"
    hp = sa / "homepage"
    _artifact(hp, "01-hero.json", "uid-hero", "HERO", "centered",
              "interface HeroProps { headline?: string; }")
    _artifact(hp, "02-features.json", "uid-feat-a", "FEATURES", "icon-grid",
              "interface FeaturesProps { headline?: string; }")
    _artifact(hp, "03-features.json", "uid-feat-b", "FEATURES", "spec-table",
              "interface FeaturesProps { headline?: string; }")
    _artifact(hp, "04-how.json", "uid-how", "HOW-IT-WORKS", "numbered-steps",
              "interface HowItWorksProps { steps?: Step[]; }")
    ap = sa / "about"
    _artifact(ap, "01-hero.json", "uid-about-hero", "HERO", "page-header",
              "interface HeroProps { headline?: string; }")
    return sa


class ProjectContractEmitTest(unittest.TestCase):
    def _emit(self, root: Path, project_id: str = "champion-grip", name: str = "Champion Grip"):
        sa = root / "section-artifacts"
        out = root / "project-contract.json"
        return emit_project_contract(sa, None, out, project_id, name)

    def test_stable_key_first_then_collision(self):
        occ: dict = {}
        self.assertEqual(stable_section_key("FEATURE", occ), "feature")
        self.assertEqual(stable_section_key("FEATURE", occ), "feature-2")
        self.assertEqual(stable_section_key("FEATURE", occ), "feature-3")
        occ2: dict = {}
        self.assertEqual(stable_section_key("HERO", occ2), "hero")

    def test_contract_keys_stable_unique_and_colliding(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_fixture(root)
            contract = self._emit(root)
            homepage = next(p for p in contract["pages"] if p["slug"] == "homepage")
            keys = [s["key"] for s in homepage["sections"]]
            self.assertEqual(len(keys), len(set(keys)), "keys must be unique within a page")
            self.assertIn("feature", keys)
            self.assertIn("feature-2", keys)
            self.assertIn("hero", keys)
            self.assertIn("how-it-works", keys)

    def test_unmapped_archetype_is_unratified_not_invented(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_fixture(root)
            contract = self._emit(root)
            homepage = next(p for p in contract["pages"] if p["slug"] == "homepage")
            how = next(s for s in homepage["sections"] if s["archetype"] == "HOW-IT-WORKS")
            self.assertIsNone(how["semanticType"])
            self.assertIsNone(how["canonicalType"])
            self.assertEqual(how["validationStatus"], "unratified")
            self.assertTrue(how["key_provisional"])
            hero = next(s for s in homepage["sections"] if s["archetype"] == "HERO")
            self.assertEqual(hero["semanticType"], "HERO")
            self.assertEqual(hero["validationStatus"], "valid")

    def test_semantic_section_id_map_keys(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_fixture(root)
            contract = self._emit(root, project_id="champion-grip")
            map_path = root / "semantic-section-id-map.json"
            self.assertTrue(map_path.is_file())
            id_map = json.loads(map_path.read_text())
            expected = set()
            for page in contract["pages"]:
                for sec in page["sections"]:
                    expected.add(f"champion-grip:{page['slug']}:{sec['key']}")
            self.assertEqual(set(id_map.keys()), expected)
            hero_map = id_map["champion-grip:homepage:hero"]
            self.assertEqual(hero_map["section_uid"], "uid-hero")
            self.assertEqual(hero_map["archetype"], "HERO")

    def test_copy_edit_does_not_change_keys(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _build_fixture(root)
            contract1 = self._emit(root)
            keys1 = [(p["slug"], s["key"]) for p in contract1["pages"] for s in p["sections"]]
            sa = root / "section-artifacts"
            for art_path in sorted(sa.rglob("*.json")):
                art = json.loads(art_path.read_text())
                art["tsx"] = "interface EditedProps { headline?: string; } /* copy changed */"
                art_path.write_text(json.dumps(art))
            contract2 = self._emit(root)
            keys2 = [(p["slug"], s["key"]) for p in contract2["pages"] for s in p["sections"]]
            self.assertEqual(keys1, keys2)


if __name__ == "__main__":
    unittest.main()
