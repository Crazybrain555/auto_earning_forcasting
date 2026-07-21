import json, py_compile, re, subprocess, sys, tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def build(out):
    return subprocess.run([sys.executable,str(ROOT/'scripts/build_live_release.py'),'--trainer-skill-root',str(ROOT),'--output-root',str(out)],capture_output=True,text=True)

def test_live_builder_strips_trainer_only_assets():
    with tempfile.TemporaryDirectory() as td:
        out=Path(td)/'technology-company-profit-forecasting'
        r=build(out)
        assert r.returncode==0, r.stdout+r.stderr
        payload=json.loads(r.stdout)
        assert payload['status']=='PASS'
        assert payload['release_is_git_commit'] is False
        assert payload['release_eligible'] is False
        assert not (out/'references/training-governance-and-promotion.md').exists()
        assert not (out/'references/companion-live-skill-contract.md').exists()
        assert not (out/'scripts/validate_revision_promotion.py').exists()
        assert not (out/'scripts/build_live_release.py').exists()
        assert not (out/'tests').exists()
        assert not (out/'assets/examples/sandisk_v73').exists()
        assert not (out/'assets/benchmarks').exists()
        assert not (out/'assets/live_release').exists()
        assert not (out/'assets/skill_system').exists()
        assert not (out/'assets/templates/method_reflection_template.md').exists()
        assert not (out/'assets/templates/training_state_template.json').exists()
        method = json.loads((out/'assets/method_system.json').read_text(encoding='utf-8'))
        assert set(method['profiles']) == {'live'}
        assert 'improvement_objective' not in method
        assert [stage['id'] for stage in method['stages']][-1] == 'publish_monitor_version'
        assert 'predictive_discipline' not in json.dumps(method)
        assert not (out/'assets/training_method_overlay.json').exists()
        sop = (out/'references/research-sop.md').read_text(encoding='utf-8').lower()
        assert 'historical training' not in sop
        assert 'how a method improvement is judged' not in sop
        assert 'sealed trainer evaluation' not in sop
        assert 'training_state.json' not in json.loads(
            (out/'assets/templates/run_manifest_template.json').read_text(encoding='utf-8')
        )['required_artifacts']
        for removed in (
            'references/historical-training-loop.md',
            'references/training-curriculum.md',
            'references/companion-live-skill-contract.md',
        ):
            assert removed not in json.dumps(method)
        # Single-purpose production has no second mode state.
        assert not (out/'assets/templates/mode_config_template.json').exists()
        profile = json.loads((out/'assets/profile.json').read_text(encoding='utf-8'))
        assert profile['profile'] == 'live'
        assert 'allowed_modes' not in profile
        text=(out/'SKILL.md').read_text().lower()
        assert 'historical_train' not in text
        assert 'pending_clean_holdout' not in text
        assert 'live_forecast' in text
        assert 'name: technology-company-profit-forecasting' in text
        assert 'technology-company-forecasting-trainer' not in text
        scaffold_text = (out/'scripts/scaffold_delivery.py').read_text(encoding='utf-8')
        assert scaffold_text == (
            ROOT/'assets/live_release/scripts/scaffold_delivery.py'
        ).read_text(encoding='utf-8')
        assert not (out/'scripts/validate_time_boundary.py').exists()
        assert not (out/'references/mode-router-and-time-boundary.md').exists()
        for script in (out/'scripts').glob('*.py'):
            py_compile.compile(str(script), doraise=True)

def test_live_builder_output_passes_live_self_test():
    with tempfile.TemporaryDirectory() as td:
        out=Path(td)/'technology-company-profit-forecasting'
        r=build(out)
        assert r.returncode==0, r.stdout+r.stderr
        st=subprocess.run([sys.executable,str(out/'scripts/package_self_test.py'),str(out)],capture_output=True,text=True)
        assert st.returncode==0, st.stdout+st.stderr
        assert 'PASS: live package self-test' in st.stdout


def test_live_builder_is_positive_ownership_not_copy_then_forget_to_prune(tmp_path):
    import shutil

    scratch = tmp_path / "trainer"
    output = tmp_path / "live"
    shutil.copytree(ROOT, scratch, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    unowned = scratch / "references" / "unowned-experiment.md"
    unowned.write_text("This file has no production owner.\n", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(scratch / "scripts/build_live_release.py"),
            "--trainer-skill-root",
            str(scratch),
            "--output-root",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert not (output / "references" / "unowned-experiment.md").exists()


def test_live_runtime_surface_has_no_trainer_policy_or_user_time_gate(tmp_path):
    """One package-boundary test owns production/Trainer runtime separation.

    This is intentionally a surface test, not another forecasting validator:
    a production package must be unable to express the historical sandbox.
    Source/retrieval/vintage/publication dates remain ordinary model inputs.
    """

    out = tmp_path / "technology-company-profit-forecasting"
    result = build(out)
    assert result.returncode == 0, result.stdout + result.stderr

    ownership = json.loads(
        (ROOT / "assets" / "runtime_ownership.json").read_text(encoding="utf-8")
    )
    assert ownership["schema_version"] == "forecast-runtime-ownership/v1"
    assert ownership["profiles"]["live"]
    assert ownership["profiles"]["trainer"]

    forbidden = re.compile(
        r"historical_train|sealed_historical|cutoff|actuals|training_[a-z_]"
        r"|validate_time_boundary",
        re.I,
    )
    runtime_paths = [
        *sorted((out / "scripts").glob("*.py")),
        out / "assets" / "profile.json",
        out / "assets" / "templates" / "run_manifest_template.json",
        out / "assets" / "templates" / "forecast_snapshot_template.json",
        out / "assets" / "schemas" / "run_manifest.schema.json",
        out / "assets" / "schemas" / "forecast_snapshot.schema.json",
    ]
    violations = [
        f"{path.relative_to(out)}: {forbidden.search(path.read_text(encoding='utf-8')).group(0)}"
        for path in runtime_paths
        if forbidden.search(path.read_text(encoding="utf-8"))
    ]
    assert not violations, "production runtime owns Trainer policy: " + "; ".join(violations)

    workspace = tmp_path / "live-run"
    rejected = subprocess.run(
        [
            sys.executable,
            str(out / "scripts" / "scaffold_delivery.py"),
            "--workspace",
            str(workspace),
            "--entity",
            "TEST",
            "--as-of",
            "2020-01-31",
        ],
        capture_output=True,
        text=True,
    )
    assert rejected.returncode != 0
    assert "unrecognized arguments" in (rejected.stdout + rejected.stderr)

    started = __import__("datetime").datetime.now(__import__("datetime").timezone.utc)
    created = subprocess.run(
        [
            sys.executable,
            str(out / "scripts" / "scaffold_delivery.py"),
            "--workspace",
            str(workspace),
            "--entity",
            "TEST",
        ],
        capture_output=True,
        text=True,
    )
    assert created.returncode == 0, created.stdout + created.stderr
    manifest = json.loads((workspace / "run_manifest.json").read_text(encoding="utf-8"))
    snapshot_at = __import__("datetime").datetime.fromisoformat(
        manifest["as_of"].replace("Z", "+00:00")
    )
    assert snapshot_at >= started


def test_live_references_do_not_embed_trainer_time_sandbox(tmp_path):
    out = tmp_path / "technology-company-profit-forecasting"
    result = build(out)
    assert result.returncode == 0, result.stdout + result.stderr

    forbidden = {
        "historical training": re.compile(r"\bhistorical[ _-]train(?:ing)?\b", re.I),
        "historical backtest": re.compile(r"\bhistorical backtest\b", re.I),
        "trainer ownership": re.compile(r"\btrainer(?:'s)?\b", re.I),
        "historical cutoff": re.compile(r"\bhistorical (?:mode|work|cutoff)\b", re.I),
        "cutoff field": re.compile(r"\bas_of_cutoff\b", re.I),
        "post-cutoff": re.compile(r"\bpost[ _-]cutoff\b", re.I),
        "time-boundary workflow": re.compile(r"\btime[ _-]boundary\b", re.I),
        "training comparison": re.compile(r"\btraining (?:comparison|error|seal)\b", re.I),
        "method-change regression": re.compile(r"\bwhen changing the method\b", re.I),
    }
    violations = []
    for path in sorted((out / "references").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for label, pattern in forbidden.items():
            if pattern.search(text):
                violations.append(f"{path.name}: {label}")

    registry = json.loads(
        (ROOT / "assets" / "artifact_registry.json").read_text(encoding="utf-8")
    )
    trainer_only_artifacts = {
        artifact["path"]
        for artifact in registry["artifacts"]
        if artifact.get("profiles") == ["trainer"]
    }
    for path in sorted((out / "references").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        for artifact_path in trainer_only_artifacts:
            if artifact_path in text:
                violations.append(f"{path.name}: trainer-only artifact {artifact_path}")

    live_skill = (out / "SKILL.md").read_text(encoding="utf-8")
    if re.search(r"\bhistorical eligibility cutoff\b", live_skill, re.I):
        violations.append("SKILL.md: historical eligibility policy")
    assert not violations, "production references contain Trainer controls: " + "; ".join(violations)


def test_specialists_are_mode_agnostic_capabilities():
    specialist_root = ROOT / "assets" / "skill_system" / "skills"
    forbidden = re.compile(
        r"trainer|sealed_historical|historical_train|post[_ -]?cutoff|target actuals",
        re.I,
    )
    for specialist in specialist_root.iterdir():
        if not specialist.is_dir():
            continue
        skill_text = (specialist / "SKILL.md").read_text(encoding="utf-8")
        profile = json.loads((specialist / "assets/capability.json").read_text())
        assert not forbidden.search(skill_text)
        assert "allowed_modes" not in profile
        assert "forbidden_inputs_by_mode" not in profile


def test_live_builder_refuses_overlapping_paths():
    import shutil
    with tempfile.TemporaryDirectory() as td:
        scratch = Path(td) / "trainer-copy"
        shutil.copytree(ROOT, scratch, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        def build_with(out):
            return subprocess.run([sys.executable, str(scratch / "scripts/build_live_release.py"),
                                    "--trainer-skill-root", str(scratch), "--output-root", str(out)],
                                   capture_output=True, text=True)
        # out == src
        r = build_with(scratch)
        assert r.returncode != 0 and "overlap" in r.stdout, r.stdout + r.stderr
        assert (scratch / "SKILL.md").exists()
        # out inside src
        r = build_with(scratch / "sub" / "live")
        assert r.returncode != 0 and "overlap" in r.stdout, r.stdout + r.stderr
        assert (scratch / "SKILL.md").exists()
        # src inside out
        r = build_with(Path(td))
        assert r.returncode != 0 and "overlap" in r.stdout, r.stdout + r.stderr
        assert (scratch / "SKILL.md").exists()


def test_live_scaffold_has_no_user_selectable_mode_or_cutoff(tmp_path):
    out = tmp_path / "technology-company-profit-forecasting"
    result = build(out)
    assert result.returncode == 0, result.stdout + result.stderr
    workspace = tmp_path / "run"
    forbidden = subprocess.run(
        [
            sys.executable,
            str(out / "scripts/scaffold_delivery.py"),
            "--workspace",
            str(workspace),
            "--entity",
            "TEST",
            "--as-of",
            "2026-07-20",
            "--mode",
            "historical_train",
        ],
        capture_output=True,
        text=True,
    )
    assert forbidden.returncode != 0

    allowed = subprocess.run(
        [
            sys.executable,
            str(out / "scripts/scaffold_delivery.py"),
            "--workspace",
            str(workspace),
            "--entity",
            "TEST",
        ],
        capture_output=True,
        text=True,
    )
    assert allowed.returncode == 0, allowed.stdout + allowed.stderr
    assert not (workspace / "training_state.json").exists()
    manifest = json.loads((workspace / "run_manifest.json").read_text(encoding="utf-8"))
    assert "training_state.json" not in manifest["required_artifacts"]
    assert isinstance(manifest["accounting_basis"], dict)
    snapshot = json.loads((workspace / "forecast_snapshot.json").read_text(encoding="utf-8"))
    assert snapshot["accounting_basis_id"] == manifest["accounting_basis"]["forecast_basis_id"]
    assert "run_mode" not in manifest
    assert "baseline_skill_version" not in manifest
    assert not (workspace / "mode_config.json").exists()
    fact_header = (workspace / "financial_fact_ledger.csv").read_text(encoding="utf-8-sig").splitlines()[0]
    assert "as_of_cutoff" not in fact_header.split(",")


def test_live_validator_and_schema_do_not_implement_mode_routing(tmp_path):
    out = tmp_path / "technology-company-profit-forecasting"
    result = build(out)
    assert result.returncode == 0, result.stdout + result.stderr
    validator = (out / "scripts/validate_delivery.py").read_text(encoding="utf-8")
    manifest_schema = json.loads(
        (out / "assets/schemas/run_manifest.schema.json").read_text(encoding="utf-8")
    )
    snapshot_schema = json.loads(
        (out / "assets/schemas/forecast_snapshot.schema.json").read_text(encoding="utf-8")
    )
    assert "require_allowed_mode" not in validator
    assert "run_mode" not in manifest_schema["properties"]
    assert "run_mode" not in snapshot_schema["properties"]
    assert not (out / "scripts" / "validate_time_boundary.py").exists()


def test_live_skill_documents_the_full_strict_profit_chain():
    method = json.loads((ROOT / "assets/method_system.json").read_text(encoding="utf-8"))
    checks = set(
        method["mandatory_decision_schedules"]["integrated_three_statement_minimum"]
        ["required_checks"]
    )
    assert {
        "revenue_to_operating_profit",
        "operating_profit_to_pretax_profit",
        "pretax_tax_nci_to_gaap_attributable_net_income",
    } <= checks
    profile = json.loads((ROOT / "assets/profile.json").read_text(encoding="utf-8"))
    assert "equation_contract.py" in profile["runtime_scripts"]
