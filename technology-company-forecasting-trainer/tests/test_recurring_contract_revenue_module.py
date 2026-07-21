from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_recurring_contract_module_is_wired():
    skill=(ROOT/'SKILL.md').read_text().lower()
    router=(ROOT/'references/mechanism-router.md').read_text().lower()
    module=(ROOT/'references/module-recurring-contract-revenue.md').read_text().lower()
    for needle in [
        'beginning eligible arr', 'churn arr', 'new-logo arr', 'recognition factor',
        'rpo', 'never add', 'unit support cost', 'capitalized-development',
    ]:
        assert needle in module
    assert 'module-recurring-contract-revenue.md' in router
    assert 'references/mechanism-router.md' in skill

def test_coverage_diagnostics_do_not_become_optimization_targets():
    text=' '.join((ROOT/'references/module-recurring-contract-revenue.md').read_text().lower().split())
    for needle in [
        'explained_revenue_share',
        'sensitivity_weighted_residual',
        'diagnostics, not target ratios',
        'do not manufacture rows',
    ]:
        assert needle in text
    assert '80%' not in text
    assert '10% unexplained' not in text
    assert 'guidance is an output constraint' in text
