"""A source-declared item field (`data-field="price"`) fills the same-named slot.

WHAT THIS GUARDS
----------------
`{products[].price}` classifies as `data`, which a harvest of headings, body
text, CTAs and images can never supply — so every price came back empty
("no-harvest-supply") although the operator-authored source carries it. The
harvest now records `item.fields` for elements the source explicitly marks
`data-field="<name>"`, and the fill reads `fields[<slot field>]` first. Only a
declared name ever fills a slot; nothing is inferred from a value's shape.

Run: `python3 -m pytest scripts/test_declared_item_fields.py -v` from web-builder/.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from orchestrate import build_template_fill  # noqa: E402

CODE = ("// Tokens: {section_title} {products[].name} {products[].price} {products[].badge}\n"
        "const rows = [\n  /* repeat:products */\n"
        '  { name: "{products[].name}", price: "{products[].price}", badge: "{products[].badge}" },\n'
        "  /* /repeat */\n];\n<h2>{section_title}</h2>")


def _item(name, fields):
    return {"heading": name, "body": "", "cta": None, "image": None, "headings": [name],
            "body_text": [], "ctas": [], "images": [], "fields": fields}


SECTION = {
    "archetype": "PRODUCT-SHOWCASE", "section_uid": "u3",
    "content": {
        "headings": ["Three essences.", "Frankincense", "Neroli"], "body_text": [],
        "section_headings": ["Three essences."], "section_body_text": [], "ctas": [],
        "items": [_item("Frankincense", {"price": "AED 395"}), _item("Neroli", {"price": "AED 445"})],
        "item_count": 2,
    },
}


def test_declared_field_fills_its_slot_and_undeclared_stays_empty():
    _, _, prov = build_template_fill(SECTION, CODE)
    prices = {p["slot"]: (p["value"], p["source"]) for p in prov if p["slot"].endswith(".price")}
    assert prices == {"products[1].price": ("AED 395", "harvested"),
                      "products[2].price": ("AED 445", "harvested")}, prices
    badges = [p for p in prov if p["slot"].endswith(".badge")]
    assert badges and all(p["source"] == "empty" for p in badges), badges
