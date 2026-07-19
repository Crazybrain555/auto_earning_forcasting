import json, py_compile, subprocess, sys, tempfile
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
        assert payload['release_is_git_commit'] is True
        assert not (out/'references/training-governance-and-promotion.md').exists()
        assert not (out/'references/companion-live-skill-contract.md').exists()
        assert not (out/'scripts/validate_revision_promotion.py').exists()
        assert not (out/'scripts/build_live_release.py').exists()
        assert not (out/'tests').exists()
        assert not (out/'assets/examples/sandisk_v73').exists()
        assert not (out/'assets/benchmarks').exists()
        assert not (out/'assets/live_release').exists()
        # scaffold_delivery runtime dependencies must survive the prune
        assert (out/'assets/templates/training_state_template.json').exists()
        assert (out/'assets/templates/mode_config_template.json').exists()
        text=(out/'SKILL.md').read_text().lower()
        assert 'historical_train' not in text
        assert 'pending_clean_holdout' not in text
        assert 'live_forecast' in text
        assert 'name: technology-company-profit-forecasting' in text
        assert 'technology-company-forecasting-trainer' in text
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
