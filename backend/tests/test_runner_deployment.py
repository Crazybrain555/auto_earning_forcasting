from __future__ import annotations

import json
import importlib.util
import os
import re
import shutil
import sqlite3
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]


class PortableRunnerConfigurationTests(unittest.TestCase):
    def test_project_mcp_config_uses_project_relative_launchers(self) -> None:
        config = json.loads((ROOT / ".mcp.json").read_text(encoding="utf-8"))

        for name, spec in config["mcpServers"].items():
            self.assertEqual(spec["command"], "/bin/bash", name)
            self.assertEqual(len(spec["args"]), 1, name)
            self.assertTrue(
                spec["args"][0].startswith("scripts/mcp/"),
                f"{name} must resolve from the project root",
            )

    def test_codex_mcp_config_has_no_machine_specific_project_path(self) -> None:
        source = (ROOT / ".codex" / "config.toml").read_text(encoding="utf-8")

        self.assertNotIn("/Users/", source)
        self.assertIn('args = ["scripts/mcp/edgartools.sh"]', source)
        self.assertIn('args = ["scripts/mcp/arxiv.sh"]', source)
        self.assertIn('args = ["scripts/mcp/youtube-transcript.sh"]', source)

    def test_backend_launcher_uses_a_portable_python_command(self) -> None:
        source = (ROOT / "backend" / "run.sh").read_text(encoding="utf-8")

        self.assertNotIn("/opt/homebrew", source)
        self.assertIn('python_bin="${PYTHON_BIN:-python3}"', source)
        self.assertIn("--host 127.0.0.1", source)

    def test_engine_commands_resolve_from_the_runner_path(self) -> None:
        config = json.loads((ROOT / "backend" / "config.json").read_text(encoding="utf-8"))

        self.assertEqual(config["engines"]["claude"]["cmd"][0], "claude")
        self.assertEqual(config["engines"]["codex"]["cmd"][0], "codex")


class RunnerServiceAssetTests(unittest.TestCase):
    def test_renderer_materializes_isolated_backend_and_bridge_units(self) -> None:
        renderer_path = ROOT / "deploy" / "forecast_runner" / "render_units.py"
        self.assertTrue(renderer_path.is_file(), "runner unit renderer must exist")
        spec = importlib.util.spec_from_file_location("forecast_runner_units", renderer_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader if spec else None)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp)
            rendered = module.render_units(
                runner_root=Path("/srv/forecast-one"),
                backend_env_file=Path("/run/forecast/backend.env"),
                bridge_env_file=Path("/run/forecast/bridge.env"),
                output_dir=output_dir,
            )

            self.assertEqual(
                {path.name for path in rendered},
                {
                    "forecast-ops-backend.service",
                    "forecast-sites-bridge.service",
                    "forecast-replica-backup.service",
                    "forecast-replica-backup.timer",
                },
            )
            backend = (output_dir / "forecast-ops-backend.service").read_text(encoding="utf-8")
            bridge = (output_dir / "forecast-sites-bridge.service").read_text(encoding="utf-8")
            backup = (output_dir / "forecast-replica-backup.service").read_text(encoding="utf-8")
            timer = (output_dir / "forecast-replica-backup.timer").read_text(encoding="utf-8")

        self.assertIn("WorkingDirectory=/srv/forecast-one", backend)
        self.assertIn("EnvironmentFile=/run/forecast/backend.env", backend)
        self.assertIn("ExecStart=/srv/forecast-one/backend/run.sh", backend)
        self.assertIn("--host 127.0.0.1", (ROOT / "backend" / "run.sh").read_text(encoding="utf-8"))
        self.assertIn("After=forecast-ops-backend.service", bridge)
        self.assertIn("Requires=forecast-ops-backend.service", bridge)
        self.assertIn("EnvironmentFile=/run/forecast/bridge.env", bridge)
        self.assertIn("ExecStart=/usr/bin/node scripts/bridge-local.mjs", bridge)
        self.assertIn("User=forecastops", backup)
        self.assertIn(
            "ExecStart=/srv/forecast-one/deploy/forecast_runner/scheduled_backup.sh /srv/forecast-one",
            backup,
        )
        self.assertIn("OnCalendar=", timer)
        self.assertIn("Persistent=true", timer)
        combined = backend + bridge + backup + timer
        self.assertNotIn("@RUNNER_ROOT@", combined)
        self.assertNotIn("@BACKEND_ENV_FILE@", combined)
        self.assertNotIn("@BRIDGE_ENV_FILE@", combined)
        self.assertNotIn("/Users/", combined)
        host_ips = [
            ip
            for ip in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", combined)
            if ip != "127.0.0.1"
        ]
        self.assertEqual(host_ips, [], "rendered units must not embed host addresses")
        self.assertNotIn("aws-sg", combined.lower())

    def test_sync_script_is_dry_run_by_default_and_excludes_secrets_and_builds(self) -> None:
        path = ROOT / "deploy" / "forecast_runner" / "sync_to_runner.sh"
        self.assertTrue(path.is_file(), "safe runner sync script must exist")
        source = path.read_text(encoding="utf-8")

        for excluded in (
            ".env*",
            ".venv",
            "node_modules",
            ".cache",
            ".pytest_cache",
            ".wrangler",
            "dist",
            "auth.json",
            ".claude/settings.local.json",
            ".claude/agents",
            ".git/sg-hook*",
            "pkcs11.txt",
            "validator_stderr.txt",
            "replica",
            "/training-runs",
            "/backend/jobs",
            "/backend/state",
            "*.db-wal",
            "*.db-shm",
            "ai-hardware-forecasting",
        ):
            self.assertIn(excluded, source)
        self.assertIn("--dry-run", source)
        self.assertIn("--apply", source)
        self.assertIn('rsync_path="${RUNNER_RSYNC_PATH:-rsync}"', source)
        self.assertIn("--include=.env.example", source)
        self.assertIn("--no-perms", source)
        self.assertLess(
            source.index("--include=.env.example"),
            source.index('"--exclude=.env*"'),
        )
        self.assertNotIn("--chmod=Du=rwx,Dg=rx,Do=,Fu=rw,Fg=r,Fo=,u+X", source)
        self.assertNotIn("--delete", source)

    def test_bootstrap_builds_project_scoped_runtime_from_pinned_inputs(self) -> None:
        path = ROOT / "deploy" / "forecast_runner" / "bootstrap.sh"
        self.assertTrue(path.is_file(), "runner bootstrap script must exist")
        source = path.read_text(encoding="utf-8")

        self.assertIn(".runtime", source)
        self.assertIn("uv==0.10.2", source)
        self.assertIn("pytest==9.0.3", source)
        self.assertIn("umask 0027", source)
        self.assertIn('chmod -R o-rwx "$runner_root"', source)
        self.assertIn("@openai/codex@0.144.6", source)
        self.assertIn("@anthropic-ai/claude-code@2.1.110", source)
        self.assertIn("uv sync --frozen", source)
        self.assertGreaterEqual(source.count("npm ci"), 2)
        self.assertNotIn("npm install -g", source)
        self.assertNotIn("sudo ", source)

    def test_replica_bundle_is_consistent_and_excludes_credentials(self) -> None:
        path = ROOT / "deploy" / "forecast_runner" / "create_replica_bundle.sh"
        self.assertTrue(path.is_file(), "runner replica bundle helper must exist")
        self.assertIsNotNone(shutil.which("sqlite3"), "sqlite3 CLI is required")
        self.assertIsNotNone(shutil.which("rsync"), "rsync is required")

        with tempfile.TemporaryDirectory() as temp:
            runner_root = Path(temp) / "runner"
            (runner_root / "training-runs" / "round-1").mkdir(parents=True)
            (runner_root / "training-runs" / "round-1" / "round.json").write_text(
                '{"status":"complete"}\n', encoding="utf-8"
            )
            (runner_root / "backend" / "state").mkdir(parents=True)
            (runner_root / "backend" / "state" / "watchlist.json").write_text(
                "[]\n", encoding="utf-8"
            )
            (runner_root / "backend" / "jobs").mkdir(parents=True)
            (runner_root / "backend" / "jobs" / "job-1.json").write_text(
                '{"status":"succeeded"}\n', encoding="utf-8"
            )
            with sqlite3.connect(runner_root / "backend" / "state" / "forecast.db") as conn:
                conn.execute("CREATE TABLE runs (id INTEGER PRIMARY KEY, security TEXT)")
                conn.execute("INSERT INTO runs (security) VALUES ('MU')")
            (runner_root / "backend" / "state" / "forecast.db-wal").write_text(
                "do-not-copy", encoding="utf-8"
            )
            (runner_root / ".env.production").write_text("SECRET=canary\n", encoding="utf-8")
            (runner_root / "codex-home").mkdir()
            (runner_root / "codex-home" / "auth.json").write_text(
                '{"token":"canary"}\n', encoding="utf-8"
            )

            result = subprocess.run(
                ["bash", str(path), str(runner_root)],
                check=True,
                capture_output=True,
                text=True,
            )
            metadata = dict(
                line.split("=", 1)
                for line in result.stdout.splitlines()
                if "=" in line
            )
            bundle = Path(metadata["BUNDLE_PATH"])
            self.assertTrue(bundle.is_file())
            self.assertRegex(metadata["SHA256"], r"^[0-9a-f]{64}$")

            with tarfile.open(bundle, "r:gz") as archive:
                names = {name.removeprefix("./") for name in archive.getnames()}
                self.assertIn("training-runs/round-1/round.json", names)
                self.assertIn("backend/state/forecast.db", names)
                self.assertIn("backend/state/watchlist.json", names)
                self.assertIn("backend/jobs/job-1.json", names)
                self.assertIn("manifest.json", names)
                self.assertIn("CHECKSUMS.sha256", names)
                self.assertNotIn("backend/state/forecast.db-wal", names)
                self.assertFalse(any("auth.json" in name for name in names))
                self.assertFalse(any(".env" in name for name in names))

                extracted = Path(temp) / "extracted"
                archive.extractall(extracted, filter="data")
            with sqlite3.connect(extracted / "backend" / "state" / "forecast.db") as conn:
                self.assertEqual(conn.execute("SELECT security FROM runs").fetchone()[0], "MU")

    def test_pull_replica_is_dry_run_by_default_and_switches_atomically(self) -> None:
        path = ROOT / "deploy" / "forecast_runner" / "pull_replica.sh"
        self.assertTrue(path.is_file(), "local pull-only replica command must exist")
        source = path.read_text(encoding="utf-8")

        self.assertIn('mode="--dry-run"', source)
        self.assertIn("--apply", source)
        self.assertIn("create_replica_bundle.sh", source)
        self.assertIn("env --chdir=", source)
        self.assertIn("CHECKSUMS.sha256", source)
        self.assertIn("PRAGMA integrity_check", source)
        self.assertIn("snapshots", source)
        self.assertIn("current", source)
        self.assertIn("ln -s", source)
        self.assertIn("os.replace", source)
        self.assertNotIn('mv -f "$next_link"', source)
        self.assertIn("cat '$bundle_path'", source)
        self.assertNotIn("\nscp ", source)
        self.assertNotIn("--delete", source)

        result = subprocess.run(
            ["bash", str(path)],
            check=True,
            capture_output=True,
            text=True,
            env={**os.environ, "RUNNER_HOST": "replica-test"},
        )
        self.assertIn("DRY RUN", result.stdout)
        self.assertIn("replica-test", result.stdout)

    def test_replica_backend_uses_explicit_local_data_overrides(self) -> None:
        launcher = ROOT / "backend" / "run-replica.sh"
        self.assertTrue(launcher.is_file(), "replica backend launcher must exist")
        launcher_source = launcher.read_text(encoding="utf-8")
        self.assertIn("replica/current", launcher_source)
        self.assertIn("FORECAST_RUNS_ROOT", launcher_source)
        self.assertIn("FORECAST_JOBS_DIR", launcher_source)
        self.assertIn("FORECAST_DB_PATH", launcher_source)

        config_path = ROOT / "backend" / "app" / "config.py"
        spec = importlib.util.spec_from_file_location("replica_backend_config", config_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader if spec else None)
        module = importlib.util.module_from_spec(spec)
        assert spec and spec.loader
        spec.loader.exec_module(module)

        with tempfile.TemporaryDirectory() as temp:
            temp_root = Path(temp)
            config_file = temp_root / "backend" / "config.json"
            config_file.parent.mkdir(parents=True)
            config_file.write_text(
                json.dumps({"project_root": "..", "runs_root": "training-runs", "jobs_dir": "jobs"}),
                encoding="utf-8",
            )
            runs = temp_root / "replica" / "training-runs"
            jobs = temp_root / "replica" / "backend" / "jobs"
            with patch.dict(
                os.environ,
                {
                    "FORECAST_BACKEND_CONFIG": str(config_file),
                    "FORECAST_RUNS_ROOT": str(runs),
                    "FORECAST_JOBS_DIR": str(jobs),
                },
                clear=False,
            ):
                loaded = module.load_config()
            # abspath, not resolve(): replica overrides must keep the
            # replica/current symlink so a pull is visible without a restart
            # (see test_replica_mode.ReplicaPathResolutionTests).
            self.assertEqual(loaded["runs_root"], os.path.abspath(runs))
            self.assertEqual(loaded["jobs_dir"], os.path.abspath(jobs))

        db_source = (ROOT / "backend" / "app" / "db.py").read_text(encoding="utf-8")
        self.assertIn("FORECAST_DB_PATH", db_source)


class ScheduledBackupAndWatchdogTests(unittest.TestCase):
    def test_scheduled_backup_wrapper_prunes_old_bundles(self) -> None:
        path = ROOT / "deploy" / "forecast_runner" / "scheduled_backup.sh"
        self.assertTrue(path.is_file(), "scheduled backup wrapper must exist")
        self.assertTrue(os.access(path, os.X_OK), "scheduled backup wrapper must be executable")
        source = path.read_text(encoding="utf-8")
        self.assertIn("create_replica_bundle.sh", source)
        self.assertIn("FORECAST_BACKUP_KEEP", source)
        self.assertIn("replica-export-", source)
        self.assertNotIn("--delete", source)

    def test_local_pull_wrapper_never_prunes_the_current_snapshot(self) -> None:
        path = ROOT / "deploy" / "forecast_runner" / "pull_and_prune.sh"
        self.assertTrue(path.is_file(), "local pull-and-prune wrapper must exist")
        self.assertTrue(os.access(path, os.X_OK), "pull-and-prune wrapper must be executable")
        source = path.read_text(encoding="utf-8")
        self.assertIn('pull_replica.sh" --apply', source)
        self.assertIn("FORECAST_REPLICA_KEEP", source)
        self.assertIn("current", source)
        self.assertIn("continue", source)

    def test_watchdog_checks_bridge_snapshot_and_replica_freshness(self) -> None:
        path = ROOT / "deploy" / "forecast_runner" / "watchdog.py"
        self.assertTrue(path.is_file(), "watchdog must exist")
        source = path.read_text(encoding="utf-8")
        for marker in ("/api/bridge/status", "/api/snapshot", "generated_at", "manifest.json"):
            self.assertIn(marker, source)


class RunnerDocumentationTests(unittest.TestCase):
    def test_root_readme_describes_sites_primary_and_replaceable_runner(self) -> None:
        source = (ROOT / "README.md").read_text(encoding="utf-8")

        self.assertIn("Sites 是生产入口", source)
        self.assertIn("云端 Runner", source)
        self.assertIn("更换服务器", source)
        self.assertIn("Sites → 本地", source)
        self.assertNotIn("aws-sg", source)

    def test_runner_readme_keeps_provider_details_in_one_profile(self) -> None:
        path = ROOT / "deploy" / "forecast_runner" / "README.md"
        self.assertTrue(path.is_file(), "runner operator README must exist")
        source = path.read_text(encoding="utf-8")

        self.assertIn("RUNNER_HOST", source)
        self.assertIn("RUNNER_ROOT", source)
        self.assertIn("当前部署 profile", source)
        self.assertIn("ACTIVE-RUNNER-PROFILE:START", source)
        self.assertIn("RUNNER_PROVIDER=AWS", source)
        self.assertIn("RUNNER_REGION=Singapore (ap-southeast-1)", source)
        self.assertIn("aws-sg", source)
        self.assertIn("更换服务器", source)
        readme_ips = [
            ip
            for ip in re.findall(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", source)
            if ip != "127.0.0.1"
        ]
        self.assertEqual(readme_ips, [], "runner README must not record host addresses")


if __name__ == "__main__":
    unittest.main()
