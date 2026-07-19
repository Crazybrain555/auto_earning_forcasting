from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def test_recurring_contract_module_is_wired():
    skill=(ROOT/'SKILL.md').read_text().lower()
    router=(ROOT/'references/mechanism-router.md').read_text().lower()
    module=(ROOT/'references/module-recurring-contract-revenue.md').read_text().lower()
    for needle in ['beginning eligible recurring base','renewal probability','expansion','recognition fraction','rpo','never add']:
        assert needle in module
    assert 'module-recurring-contract-revenue.md' in router
    assert 'recurring-contract state and recognition' in skill

def test_coverage_thresholds_are_diagnostics_not_universal_hard_gates():
    text=(ROOT/'references/module-recurring-contract-revenue.md').read_text().lower()
    for needle in ['explained_revenue_share','sensitivity_weighted_residual','80%','10%','warning thresholds','not universal hard gates']:
        assert needle in text
    assert 'guidance is an output constraint' in text
