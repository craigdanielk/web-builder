"""The conformance gate measures against the EFFECTIVE style, not the raw benchmark.

WHAT THIS GUARDS
----------------
Operator decision 2026-10-21: the expectation is the benchmark plus the
tenant's declared overrides (`style.tenant_overrides`). The gate compared
THURIS's page with the raw luxury-botanical-oils benchmark (cream #f7f4ef,
text #000000), so every declared override — the whole two-mode palette —
read as a violation and the build failed on the design it was told to ship.

`effective_benchmark()` applies exactly the fields `tenant_overrides` lists
(plus the declared light palette as `<role>@light` roles), records them under
`_effective.declared_deviations`, and leaves everything else measured.
Contrast adjustments made by the compiler are NOT folded in — only operator
declarations. The type scale is not overridden, so an off-scale heading is
still a finding.

Run: `python3 -m pytest scripts/test_effective_benchmark.py -v` from web-builder/.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.effective_benchmark import effective_benchmark  # noqa: E402

BENCH = {
    "_meta": {"market": "luxury-botanical-oils"},
    "palette_roles": {"bg_primary": "#f7f4ef", "text_primary": "#000000",
                      "accent": "#C1A36B", "_source": {"bg_primary": "prose"}},
    "type_scale": {"ratio": 1.143, "base_px": 14},
    "type_system": {"scale_px": [11, 14, 32]},
    "rhythm": {"section_py_px": 100},
    "font_system": {"families": ["Inter"]},
}

STYLE = {
    "palette": {"bg_primary": "#09070B", "text_primary": "#F4EEE4", "accent": "#C2A46C"},
    "palette_light": {"bg_primary": "#F4F0E8", "text_primary": "#241F1B"},
    "tenant_overrides": [
        {"field": "palette_roles.bg_primary", "value": "#09070B", "was": "#f7f4ef"},
        {"field": "palette_roles.text_primary", "value": "#F4EEE4", "was": "#000000"},
        {"field": "type_scale.base_px", "value": 17, "was": 14},
        {"field": "rhythm.section_py_px", "value": 140, "was": 100},
        {"field": "fonts.heading", "value": "Bodoni Moda", "was": "Inter"},
        {"field": "fonts.body", "value": "Inter", "was": "Inter"},
        {"field": "border_radius.card", "value": "0px", "was": "8px"},
        {"field": "border_radius.button", "value": "0px", "was": "8px"},
    ],
}


def test_declared_overrides_replace_the_measured_values():
    eff = effective_benchmark(BENCH, STYLE)
    roles = eff["palette_roles"]
    assert roles["bg_primary"] == "#09070B"
    assert roles["text_primary"] == "#F4EEE4"
    assert eff["type_scale"]["base_px"] == 17
    assert eff["rhythm"]["section_py_px"] == 140
    assert eff["font_system"]["families"] == ["Bodoni Moda", "Inter"]
    assert eff["card_system"]["radius_px"] == [0]
    assert eff["cta_buttons"]["radius_px"] == [0]


def test_light_palette_becomes_tone_qualified_roles():
    roles = effective_benchmark(BENCH, STYLE)["palette_roles"]
    assert roles["bg_primary@light"] == "#F4F0E8"
    assert roles["text_primary@light"] == "#241F1B"


def test_only_declarations_apply_not_compiler_adjustments():
    # style.palette.accent was contrast-adjusted (#C2A46C) but never declared.
    eff = effective_benchmark(BENCH, STYLE)
    assert eff["palette_roles"]["accent"] == "#C1A36B"
    assert eff["type_system"]["scale_px"] == [11, 14, 32]  # not overridden: still measured


def test_deviations_are_recorded_and_the_input_is_untouched():
    eff = effective_benchmark(BENCH, STYLE)
    rec = eff["_effective"]
    assert rec["basis"] == "benchmark + style.tenant_overrides"
    assert len(rec["declared_deviations"]) == len(STYLE["tenant_overrides"])
    assert rec["tones"] == ["base", "light"]
    assert BENCH["palette_roles"]["bg_primary"] == "#f7f4ef"


def test_no_overrides_means_the_benchmark_itself():
    eff = effective_benchmark(BENCH, {"palette": {"bg_primary": "#000000"}})
    assert eff["palette_roles"] == BENCH["palette_roles"]
    assert eff["_effective"]["declared_deviations"] == []


def test_gate_is_held_to_the_effective_benchmark_and_says_so(tmp_path):
    import importlib.util
    import json
    scripts = Path(__file__).resolve().parent
    spec = importlib.util.spec_from_file_location("orch_eff", scripts / "orchestrate.py")
    orch = importlib.util.module_from_spec(spec)
    sys.modules["orch_eff"] = orch
    spec.loader.exec_module(orch)
    orch.reset_build_failures()
    orch.reset_gate_results()
    bench = tmp_path / "bm.json"
    bench.write_text(json.dumps(BENCH), encoding="utf-8")
    (tmp_path / "bm.deviations.json").write_text('{"deviations": []}', encoding="utf-8")
    results = tmp_path / "runner-results.json"
    results.write_text(json.dumps({"results": [{"rule_id": "dna_card_radius", "layer": "L4",
                                                "state": "PASS"}],
                                   "urls_reached": ["http://127.0.0.1:1/"]}), encoding="utf-8")
    orch.run_conformance_gate(tmp_path / "site", benchmark=str(bench), results_json=results,
                              output_dir=tmp_path, style=STYLE)
    eff = json.loads((tmp_path / "effective-benchmark.json").read_text(encoding="utf-8"))
    assert eff["palette_roles"]["bg_primary"] == "#09070B"
    report = json.loads((tmp_path / "conformance.json").read_text(encoding="utf-8"))
    assert report["expectation"]["kind"] == "effective"
    assert len(report["expectation"]["declared_deviations"]) == len(STYLE["tenant_overrides"])
    assert report["benchmark"].endswith("effective-benchmark.json")
    # ratified waivers travel with the effective benchmark
    assert (tmp_path / "effective-benchmark.deviations.json").exists()
