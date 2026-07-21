"""Training reflection must look outward, not only at its own error table."""
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL / "scripts/validate_method_reflection.py"

GOOD = """# Method reflection - round-2

## Rule 1: symmetric persistence challenger

- `error_observed`: CDNS@2018-02-26 FY+2 revenue under-forecast 16%, same direction on TSM.
- `internal_attribution`: PARAM - growth reverted to pre-inflection average.
- `external_sources`:
  - `source_id`: M1 | `category`: original_author_practitioner | `independence_cluster`: mauboussin |
    `originality`: original_author | `location`: https://www.morganstanley.com/im/publication/insights/articles/article_measuringthemoat.pdf |
    `method_claim`: fade is conditional on competitive barriers |
    `misuse_boundary`: this does not prove the case company has a moat
  - `source_id`: M2 | `category`: academic_primary | `independence_cluster`: fama-french |
    `originality`: original_academic | `location`: https://doi.org/10.1086/209638 |
    `method_claim`: profitability mean reverts nonlinearly in a broad sample |
    `misuse_boundary`: the population estimate is not a company fade parameter
- `outside_view`: practitioners require an explicit fade assumption argued either way.
- `agreement`: confirms
- `rule_adopted`: when a named transition drives measurable demand, compare the causal
  forecast symmetrically with trailing organic growth and the matched reference class;
  the rule fails when the transition or company departure cannot be evidenced.
- `why_not_alternatives`: a flat uplift was rejected - it tunes a number, not a mechanism.
- `support_status`: provisional
- `validation_plan`: test on two untouched holdout firms with opposite cycle states;
  compare revenue, operating-profit and net-income error plus signed bias.
- `challenger_baselines`: trailing organic growth and guidance-bias-adjusted growth.
- `generative_change`: replace the duplicated forecast override with one causal-stage equation.
- `assurance_angle`: causal transfer and generalization; retire the overlapping phrase-presence check.
- `complexity_delta`: remove one override and one duplicate test; add no artifact or validator branch.
- `independent_review_plan`: freeze cases and sources, then give them to an isolated reviewer before the builder responds.
- `ablation_plan`: rerun without the transition floor to isolate whether the rule moved the target error.
- `rollback_condition`: revert if holdouts gain directional over-forecast bias or the target error does not improve.
"""

THIN = """# Method reflection - round-2

## Rule 1: bump FY+2 growth

- `error_observed`: under-forecast on two cases.
- `internal_attribution`: PARAM.
- `external_sources`:
  - `source_id`: M1 | `category`: blog | `independence_cluster`: one |
    `originality`: commentary | `location`: https://example.com/only-one |
    `method_claim`: raise growth | `misuse_boundary`: none
- `outside_view`: unclear.
- `agreement`: confirms
- `rule_adopted`: raise FY+2 growth.
- `support_status`: provisional
- `validation_plan`: test later.
"""

INTERNAL_ONLY = """# Method reflection - round-2

## Rule 1: bump FY+2 growth

- `error_observed`: under-forecast on two cases.
- `internal_attribution`: PARAM - reverted to average.
- `rule_adopted`: raise FY+2 growth.
"""

CONTRADICTED = """# Method reflection - round-2

## Rule 1: always fade high ROIC

- `error_observed`: over-forecast on one case.
- `internal_attribution`: STRUCTURE.
- `external_sources`:
  - `source_id`: M1 | `category`: practitioner_original | `independence_cluster`: c1 |
    `originality`: original | `location`: https://example.com/a |
    `method_claim`: documented barriers can sustain spreads | `misuse_boundary`: not company proof
  - `source_id`: M2 | `category`: academic_primary | `independence_cluster`: c2 |
    `originality`: original | `location`: https://example.com/b |
    `method_claim`: profitability mean reverts | `misuse_boundary`: not a fixed company parameter
- `outside_view`: practitioners argue fade both ways.
- `agreement`: contradicts
- `rule_adopted`: fade every high-ROIC company mechanically.
- `support_status`: provisional
- `validation_plan`: test on holdout firms.
"""

DUPLICATED = """# Method reflection - round-2

## Rule 1: raise growth

- `error_observed`: two under-forecasts.
- `internal_attribution`: PARAM.
- `external_sources`:
  - `source_id`: M1 | `category`: blog | `independence_cluster`: same-wire |
    `originality`: commentary | `location`: https://example.com/a |
    `method_claim`: growth stays high | `misuse_boundary`: none
  - `source_id`: M2 | `category`: podcast | `independence_cluster`: same-wire |
    `originality`: commentary | `location`: https://example.com/b |
    `method_claim`: growth stays high | `misuse_boundary`: none
- `outside_view`: commentary agrees.
- `agreement`: confirms
- `rule_adopted`: raise growth.
- `why_not_alternatives`: none.
- `support_status`: provisional
- `validation_plan`: test on one holdout.
"""


def run(text, strict=True):
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "method_reflection.md"
        p.write_text(text, encoding="utf-8")
        cmd = [sys.executable, str(VALIDATOR), "--reflection", str(p)]
        if strict:
            cmd.append("--strict")
        return subprocess.run(cmd, capture_output=True, text=True)


def test_missing_file_fails():
    r = subprocess.run([sys.executable, str(VALIDATOR), "--reflection", "/nonexistent/x.md", "--strict"],
                       capture_output=True, text=True)
    assert r.returncode == 2 and "not found" in r.stdout


def test_internal_only_reflection_is_rejected():
    r = run(INTERNAL_ONLY)
    assert r.returncode == 2
    assert "external_sources" in r.stdout


def test_one_direct_original_method_source_can_support_a_bounded_reflection():
    single_source = GOOD.replace(
        "  - `source_id`: M2 | `category`: academic_primary | `independence_cluster`: fama-french |\n"
        "    `originality`: original_academic | `location`: https://doi.org/10.1086/209638 |\n"
        "    `method_claim`: profitability mean reverts nonlinearly in a broad sample |\n"
        "    `misuse_boundary`: the population estimate is not a company fade parameter\n",
        "",
    )
    r = run(single_source)
    assert r.returncode == 0, r.stdout


def test_conflict_interpretation_is_reviewer_judgment_not_a_keyword_gate():
    text = GOOD.replace("- `agreement`: confirms", "- `agreement`: contradicts").replace(
        "- `why_not_alternatives`: a flat uplift was rejected - it tunes a number, not a mechanism.\n",
        "",
    )
    r = run(text)
    assert r.returncode == 0, r.stdout


def test_duplicate_source_ids_are_rejected_without_counting_sources():
    text = GOOD.replace("`source_id`: M2", "`source_id`: M1")
    r = run(text)
    assert r.returncode == 2
    assert "source_id" in r.stdout.lower()


def test_source_authority_is_not_inferred_from_category_keywords():
    text = GOOD.replace("original_author_practitioner", "blog").replace(
        "academic_primary", "commentary"
    ).replace("original_author", "commentary").replace("original_academic", "commentary")
    r = run(text)
    assert r.returncode == 0, r.stdout


def test_every_source_needs_a_bounded_method_claim():
    text = GOOD.replace(
        "`misuse_boundary`: the population estimate is not a company fade parameter",
        "`not_a_boundary`: the population estimate is not a company fade parameter",
    )
    r = run(text)
    assert r.returncode == 2
    assert "misuse_boundary" in r.stdout


def test_rule_needs_support_status_and_validation_plan():
    text = GOOD.replace("- `support_status`: provisional\n", "")
    text = text.replace(
        "- `validation_plan`: test on two untouched holdout firms with opposite cycle states;\n  compare revenue, operating-profit and net-income error plus signed bias.\n",
        "",
    )
    r = run(text)
    assert r.returncode == 2
    assert "support_status" in r.stdout
    assert "validation_plan" in r.stdout


def test_process_first_fields_are_structurally_required():
    template = (
        SKILL / "assets/templates/method_reflection_template.md"
    ).read_text(encoding="utf-8")
    fields = (
        "generative_change",
        "assurance_angle",
        "complexity_delta",
        "independent_review_plan",
    )
    for field in fields:
        assert f"`{field}`" in template
        text = GOOD.replace(
            next(line for line in GOOD.splitlines(keepends=True) if f"`{field}`" in line),
            "",
        )
        result = run(text)
        assert result.returncode == 2
        assert field in result.stdout


def test_well_reflected_rule_passes():
    r = run(GOOD)
    assert r.returncode == 0, r.stdout
    assert "external method evidence" in r.stdout


def test_support_status_uses_controlled_honest_vocabulary():
    r = run(GOOD.replace("`support_status`: provisional", "`support_status`: proven forever"))
    assert r.returncode == 2
    assert "support_status" in r.stdout


def test_validation_plan_sufficiency_is_not_inferred_from_financial_keywords():
    text = GOOD.replace(
        "test on two untouched holdout firms with opposite cycle states;\n  compare revenue, operating-profit and net-income error plus signed bias.",
        "run the preregistered prospective comparison against the named simpler challenger;\n  an isolated reviewer will judge whether the observations and failure conditions are sufficient.",
    )
    r = run(text)
    assert r.returncode == 0, r.stdout


def test_every_rule_names_a_simpler_challenger():
    text = GOOD.replace(
        "- `challenger_baselines`: trailing organic growth and guidance-bias-adjusted growth.\n",
        "",
    )
    r = run(text)
    assert r.returncode == 2
    assert "challenger_baselines" in r.stdout
