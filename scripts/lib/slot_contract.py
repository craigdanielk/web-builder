"""The fillable-slot contract of a section template.

`section_archetypes.slot_schema` is the column meant to carry this contract. It
is populated on 2 of the 74 rows that have `has_template = true`, and the two
that are populated disagree on shape (one is `{"slots": [...]}` keyed on
`name`, the other a bare list keyed on `slot`). So the contract cannot be read
from the column; it is derived here from the template body instead.

Two things have to be separated, and getting it wrong is worse than not filling
at all:

  * **slots** — `{headline}`, `{member_3_role}`. Placeholders for tenant copy.
  * **code**  — `variants={container}`, `key={j}`, `{i}`, `{item}`. Ordinary JS
    identifiers that happen to sit inside JSX braces. Substituting a slot value
    into one of these produces `variants={}` or `key={}`: not wrong copy, but a
    component that does not compile.

The discriminator is the template's own header declaration. 73 of 74 templates
declare their slots — 72 in a `// Tokens: {a}, {b}` line, 1 in a
`Slot placeholders (filled by tenant data):` block — and every undeclared body
token in the corpus except the one undeclared template's is a code identifier.
So: declared, or matching the `prefix_N_field` repeater shape, and never in
RESERVED_IDENTS.
"""
from __future__ import annotations

import re

#: `{token}` in a template body. Excludes `{obj.field}` (a member expression
#: inside a `.map` callback) via the leading `.` guard.
TOKEN_RE = re.compile(r'(?<![\w.])\{([a-z][a-z_0-9]*)\}(?![\w])')

#: `{prefix_N_field}` — one field of one entry of a repeated item array.
NUMBERED_RE = re.compile(r'^([a-z]+)_(\d+)_(.+)$')

#: `{prefix_N}` — a bare indexed slot with no field (`{filter_1}`,
#: `{product_image_2}`; the prefix may itself contain underscores).
BARE_NUMBERED_RE = re.compile(r'^([a-z][a-z_]*[a-z])_(\d+)$')

#: JS identifiers that appear in JSX braces and are code, never content. Every
#: one of these was observed in the live corpus: `i` in 35 templates, `index`
#: in 16, `item` and `container` in 8, `j` in 4.
RESERVED_IDENTS = frozenset({
    "i", "j", "k", "index", "idx", "item", "container", "children", "key",
    "col", "feat", "f", "img", "size", "current", "playing", "open", "false",
    "true", "null", "undefined", "feature", "step", "faq", "logo", "product",
    "testimonial", "stat", "member", "post", "plan", "badge", "review",
    "image", "room", "project", "goal", "metric", "spec", "tab", "color",
    "social", "link", "nav", "row", "column", "filter", "child", "value",
})

# ── Slot type inference ────────────────────────────────────────────────────
# The harvest stores copy as parallel `headings[]` / `body_text[]` / `ctas[]`
# lists, not as typed slots. The field name is the only signal available for
# deciding which list a slot draws from.
_TITLE_FIELDS = frozenset({
    "title", "name", "question", "label", "heading", "headline", "role",
    "value", "author", "step_title", "tier",
})
_BODY_FIELDS = frozenset({
    "description", "answer", "body", "text", "subtitle", "subheadline",
    "quote", "bio", "excerpt", "detail", "caption", "desc", "content",
    "sublabel", "benefit", "body_text", "editorial_text", "company_description",
    "section_description", "empty_message", "disclaimer", "pairing_reason",
})

#: Fields whose value is structured data, not page prose: a price, a date, an
#: icon name, a rating. The harvest carries `headings[]` / `body_text[]` /
#: `ctas[]` / images and nothing else, so it cannot source these. Filling them
#: from the heading list is what produced `icon: 'Lowest trading fees in South
#: Africa'` — a heading standing in for an icon name. They resolve to empty and
#: are recorded as unfilled.
_DATA_FIELDS = frozenset({
    "price", "date", "icon", "icon_path", "rating", "average_rating",
    "total_reviews", "count", "product_count", "suffix", "tag", "sold",
    "period", "email", "phone", "address", "company", "category",
    "one_time_price", "subscribe_price", "subscribe_savings",
    "subscribe_frequency", "bundle_discount", "subtotal_value",
    "highlight_stat", "copyright_text",
})
_IMAGE_FIELDS = frozenset({
    "image_url", "image", "src", "logo", "avatar", "logo_url", "image_src",
    "bg_image_url", "photo", "thumbnail",
})
_ALT_FIELDS = frozenset({"image_alt", "alt", "bg_image_alt", "logo_alt", "photo_alt"})
_URL_FIELDS = frozenset({"url", "href", "link", "cta_url", "video_url"})

#: Button labels. Sourced from the harvest's `ctas[]`, not from headings — a
#: CTA is a distinct supply from a section heading, and typing it as generic
#: text made the derived contract disagree with what the fill actually does.
_CTA_FIELDS = frozenset({
    "cta_text", "primary_cta_text", "secondary_cta_text", "button_text",
    "cta_button_text", "form_cta_text", "checkout_text", "cta",
})


#: Field name for an indexed slot that has none of its own (`{filter_1}`).
#: Deliberately unspellable as a real token so it cannot collide.
BARE_FIELD = "__bare__"


def infer_type(field: str) -> str:
    """The kind of value a slot wants.

    Returns one of: alt / image / url / text-long / text-short / data /
    unclassified. The last two are deliberately *unfillable* from a harvest
    that carries only headings, body text, CTAs and images — a field this
    function cannot identify gets left empty and recorded rather than filled
    with whatever list came to hand. The alternative, a catch-all that falls
    back to the heading list, is how `post[].date` and `feature[].icon` would
    come to hold section headings.
    """
    if field == BARE_FIELD:
        return "text-short"  # `{filter_1}` renders as a short label
    if field in _ALT_FIELDS or field.endswith("_alt"):
        return "alt"
    if field in _IMAGE_FIELDS or field.endswith("_image_url") or field.endswith("_image"):
        return "image"
    if field in _CTA_FIELDS:
        return "cta"
    if field in _URL_FIELDS or field.endswith("_url") or field.endswith("_href"):
        return "url"
    if field in _DATA_FIELDS or field.endswith("_price") or field.endswith("_icon"):
        return "data"
    if field in _BODY_FIELDS or field.endswith("_description"):
        return "text-long"
    if field in _TITLE_FIELDS:
        return "text-short"
    return "unclassified"


def _singular(name: str) -> str:
    """`breadcrumbs` -> `breadcrumb`. Declarations name repeaters in the plural
    while the body spells individual slots in the singular."""
    if name.endswith("ies") and len(name) > 4:
        return name[:-3] + "y"
    if name.endswith("s") and not name.endswith("ss"):
        return name[:-1]
    return name


def declared_slots(code: str) -> set[str]:
    """Slot names the template declares in its own header comment.

    Handles both dialects in the corpus. A declared repeater contributes every
    spelling the body might use: `{faqs[].question}` yields `faqs[].question`,
    the base `faqs`, its singular `faq`, and the bare field `question` — FAQ /
    accordion declares the repeater form but renders `{question}`.
    """
    names: set[str] = set()

    def add(tok: str) -> None:
        names.add(tok)
        base = re.split(r'[\[.]', tok)[0]
        names.add(base)
        names.add(_singular(base))
        if "[]." in tok or "." in tok:
            names.add(tok.split(".")[-1])

    for line in code.splitlines():
        stripped = line.strip()
        if stripped.startswith("// Tokens:"):
            for tok in re.findall(r'\{([^{}]+)\}', stripped[len("// Tokens:"):]):
                add(tok)
    block = re.search(r'Slot placeholders[^\n]*\n(.*?)\*/', code, re.S)
    if block:
        for tok in re.findall(r'\{([a-z][a-z_0-9]*)\}', block.group(1)):
            add(tok)
    return names


def schema_slot_names(slot_schema) -> set[str]:
    """Slot names out of a populated `slot_schema` column.

    The two populated rows disagree on shape — CTA/dark-band is
    `{"slots": [{"name": ...}]}`, TEAM/headshot-grid-square is a bare list of
    `{"slot": ...}` — so both are accepted. Absent or unrecognised shapes give
    an empty set and the comment declaration is used instead.
    """
    if isinstance(slot_schema, dict):
        slot_schema = slot_schema.get("slots")
    if not isinstance(slot_schema, list):
        return set()
    names = set()
    for entry in slot_schema:
        if isinstance(entry, dict):
            name = entry.get("name") or entry.get("slot")
            if isinstance(name, str) and name:
                names.add(name.strip("{}"))
    return names


def strip_comments(code: str) -> str:
    """Template body with `//` lines and `/* */` blocks removed.

    The header comment declares the contract; a token inside it is a
    declaration, not an occurrence, and substituting into it destroys the
    record of what the template asked for.
    """
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.S)
    return "\n".join(
        line for line in code.splitlines() if not line.lstrip().startswith("//")
    )


def _is_slot(token: str, declared: set[str], numbered, no_declaration: bool) -> bool:
    """Is this brace token a fillable slot, or a JS identifier?

    Every clause below exists because a real template in the corpus needs it:

      declared          — the common case, 72 templates.
      numbered          — `{member_3_role}`, `{product_image_2}`.
      no_declaration    — CTA/dark-band declares nothing in a comment (its
                          contract is in `slot_schema`); fall back to "not
                          reserved" rather than filling none of it.
      prefix sharing    — CART-DRAWER declares `{subtotal_label}` and renders
                          `{subtotal_value}`; HERO/page-header declares
                          `{breadcrumbs[].label}` and renders
                          `{breadcrumb_current}`. A token sharing its first
                          segment with a declared name is content.
    """
    if token in RESERVED_IDENTS:
        return False
    if numbered or no_declaration or token in declared:
        return True
    head = token.split("_")[0]
    for d in declared:
        if "_" not in d and "[" not in d:
            continue
        base = d.split("_")[0].split("[")[0]
        if head in (base, _singular(base)):
            return True
    return False


def template_contract(code: str, slot_schema=None) -> dict:
    """The fillable-slot contract of one template.

    Returns::

        {
          "scalars": {name: {"type": ...}},
          "arrays":  {prefix: {"arity": int, "indices": [...],
                               "fields": [...], "field_types": {...}}},
          "code_idents": [...],   # brace tokens rejected as JS, for audit
        }

    `arity` is what the template *hardcodes* — TEAM/headshot-grid-square
    structurally declares 8 member rows. It is the ceiling, not the count to
    render: the count comes from the harvest, and rows beyond it are dropped.
    """
    body = strip_comments(code)
    declared = declared_slots(code)
    declared |= schema_slot_names(slot_schema)
    no_declaration = not declared

    scalars: dict[str, dict] = {}
    arrays: dict[str, dict] = {}
    code_idents: set[str] = set()

    for token in sorted(set(TOKEN_RE.findall(body))):
        numbered = NUMBERED_RE.match(token) or BARE_NUMBERED_RE.match(token)
        if not _is_slot(token, declared, numbered, no_declaration):
            code_idents.add(token)
            continue
        if numbered:
            prefix = numbered.group(1)
            idx = int(numbered.group(2))
            # A bare `{filter_1}` has no field name. The sentinel must not
            # collide with a real one — `"value"` does (`{stat_1_value}`).
            field = numbered.group(3) if numbered.lastindex >= 3 else BARE_FIELD
            entry = arrays.setdefault(
                prefix, {"indices": set(), "fields": set(), "field_types": {}}
            )
            entry["indices"].add(idx)
            entry["fields"].add(field)
            entry["field_types"][field] = infer_type(field)
        else:
            scalars[token] = {"type": infer_type(token)}

    for prefix, entry in arrays.items():
        entry["arity"] = max(entry["indices"])
        entry["indices"] = sorted(entry["indices"])
        entry["fields"] = sorted(entry["fields"])

    return {
        "scalars": scalars,
        "arrays": arrays,
        "code_idents": sorted(code_idents),
    }
