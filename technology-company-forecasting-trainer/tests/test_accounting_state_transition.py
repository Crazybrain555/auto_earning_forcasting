import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_generic_event_schema_and_dta_submodule_are_separate():
    generic=(ROOT/'references/module-discrete-accounting-events.md').read_text().lower()
    dta=(ROOT/'references/submodule-dta-valuation-allowance.md').read_text().lower()
    perimeter=(ROOT/'references/module-perimeter-and-accounting.md').read_text().lower()
    for needle in ['eligible amount','event-specific states','cash-flow','normalized']:
        assert needle in generic
    for needle in ['s0','s1','s2','s3','s4','jurisdiction','cash taxes']:
        assert needle in dta
    assert 'do not apply deferred-tax states' in perimeter

def test_interval_widening_is_local_and_properly_scored():
    output=(ROOT/'references/core-output-and-valuation.md').read_text().lower()
    loop=(ROOT/'references/historical-training-loop.md').read_text().lower()
    assert 'do not widen every row by a common percentage' in output
    assert 'wider is better only when it represents a supported uncertainty state' in output
    assert re.search(r'proper interval\s+score', output)
    assert 'intervals were not silently widened' in loop
    assert 'width must still be attributed' in loop
