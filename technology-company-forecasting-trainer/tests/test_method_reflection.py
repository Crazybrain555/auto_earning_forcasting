"""Training reflection must look outward, not only at its own error table."""
import subprocess
import sys
import tempfile
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
VALIDATOR = SKILL / "scripts/validate_method_reflection.py"

GOOD = """# Method reflection - round-2

## Rule 1: technology-inflection expansion floor

- `error_observed`: CDNS@2018-02-26 FY+2 revenue under-forecast 16%, same direction on TSM.
- `internal_attribution`: PARAM - growth reverted to pre-inflection average.
- `external_sources`:
  - https://example.com/measuring-the-moat - fade is default, persistence needs a barrier
  - youtube:2kDTybPftG4 - ASML episode: generational lead sustains expansion
- `outside_view`: practitioners require an explicit fade assumption argued either way.
- `agreement`: confirms
- `rule_adopted`: when a named transition drives measurable demand, FY+2 base expansion
  may not fall below trailing organic rate; fails when the transition is unnamed.
- `why_not_alternatives`: a flat uplift was rejected - it tunes a number, not a mechanism.
"""

THIN = """# Method reflection - round-2

## Rule 1: bump FY+2 growth

- `error_observed`: under-forecast on two cases.
- `internal_attribution`: PARAM.
- `external_sources`:
  - https://example.com/only-one
- `outside_view`: unclear.
- `agreement`: confirms
- `rule_adopted`: raise FY+2 growth.
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
  - https://example.com/a - documented barriers can sustain spreads
  - https://example.com/b - mechanical fade misses compounders
- `outside_view`: practitioners argue fade both ways.
- `agreement`: contradicts
- `rule_adopted`: fade every high-ROIC company mechanically.
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


def test_single_source_is_not_enough():
    r = run(THIN)
    assert r.returncode == 2
    assert "external source reference" in r.stdout


def test_contradicted_rule_needs_an_argument():
    r = run(CONTRADICTED)
    assert r.returncode == 2
    assert "contradicts" in r.stdout


def test_well_reflected_rule_passes():
    r = run(GOOD)
    assert r.returncode == 0, r.stdout
    assert "external corroboration" in r.stdout
