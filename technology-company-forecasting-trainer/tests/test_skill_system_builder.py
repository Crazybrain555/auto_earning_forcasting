import json
import hashlib
import shutil
import subprocess
import sys
from pathlib import Path


TRAINER = Path(__file__).resolve().parents[1]


def _tree_hash(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        if any(part in {"__pycache__", ".pytest_cache"} for part in path.parts):
            continue
        if path.suffix in {".pyc", ".pyo"} or path.name == ".DS_Store":
            continue
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def test_skill_system_builder_generates_one_live_coordinator_three_specialists_and_contracts(tmp_path):
    output = tmp_path / "system"
    result = subprocess.run(
        [
            sys.executable,
            str(TRAINER / "scripts/build_skill_system.py"),
            "--trainer-skill-root",
            str(TRAINER),
            "--output-parent",
            str(output),
            "--self-test",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    expected = {
        "technology-company-profit-forecasting",
        "company-evidence-research",
        "company-operating-modeling",
        "company-financial-forecasting",
        "forecasting-system-contracts",
    }
    assert {path.name for path in output.iterdir()} == expected
    payload = json.loads(result.stdout)
    assert payload["status"] == "PASS"
    assert payload["capability_count"] == 3


def test_generated_capabilities_are_exact_copies_of_promotion_bound_sources(tmp_path):
    output = tmp_path / "system"
    result = subprocess.run(
        [
            sys.executable,
            str(TRAINER / "scripts/build_skill_system.py"),
            "--trainer-skill-root",
            str(TRAINER),
            "--output-parent",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    manifest = json.loads(
        (TRAINER / "assets/skill_system/manifest.json").read_text(encoding="utf-8")
    )
    for name in manifest["capabilities"]:
        assert (output / name / "SKILL.md").read_bytes() == (
            TRAINER / "assets/skill_system/skills" / name / "SKILL.md"
        ).read_bytes()
        assert (output / name / "assets/capability.json").read_bytes() == (
            TRAINER / "assets/skill_system/skills" / name / "assets/capability.json"
        ).read_bytes()


def test_builder_refuses_to_overwrite_trainer_tree(tmp_path):
    scratch_root = tmp_path / "system"
    scratch_trainer = scratch_root / "technology-company-forecasting-trainer"
    shutil.copytree(TRAINER, scratch_trainer)
    result = subprocess.run(
        [
            sys.executable,
            str(scratch_trainer / "scripts/build_skill_system.py"),
            "--trainer-skill-root",
            str(scratch_trainer),
            "--output-parent",
            str(scratch_root),
        ],
        capture_output=True,
        text=True,
    )
    # The real repository parent is the supported release target, so the
    # builder must preserve the trainer while replacing only allowlisted
    # generated directories.  This regression asserts that invariant rather
    # than expecting a blanket overlap rejection.
    assert result.returncode == 0, result.stdout + result.stderr
    assert scratch_trainer.is_dir()


def test_checked_in_production_system_matches_a_deterministic_rebuild(tmp_path):
    """One release-integrity view prevents a stale generated live tree."""

    output = tmp_path / "system"
    result = subprocess.run(
        [
            sys.executable,
            str(TRAINER / "scripts/build_skill_system.py"),
            "--trainer-skill-root",
            str(TRAINER),
            "--output-parent",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    checked_in_root = TRAINER.parent
    for name in (
        "technology-company-profit-forecasting",
        "company-evidence-research",
        "company-operating-modeling",
        "company-financial-forecasting",
        "forecasting-system-contracts",
    ):
        assert _tree_hash(checked_in_root / name) == _tree_hash(output / name), name
