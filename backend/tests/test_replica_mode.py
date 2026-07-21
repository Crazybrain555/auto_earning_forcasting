from __future__ import annotations

import importlib.util
import json
import os
import signal
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app import jobs, replica


ROOT = Path(__file__).resolve().parents[2]


def _load_config_module():
    spec = importlib.util.spec_from_file_location(
        "replica_mode_config", ROOT / "backend" / "app" / "config.py"
    )
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


class ReplicaPathResolutionTests(unittest.TestCase):
    """A pull re-points replica/current at a new snapshot. If the backend
    resolved that symlink at startup it would keep serving the old snapshot
    (and keep a pruned directory alive), so the override must stay unresolved."""

    def test_overrides_keep_the_current_symlink_unresolved(self) -> None:
        module = _load_config_module()
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = root / "replica" / "snapshots" / "snap-a"
            (snapshot / "training-runs").mkdir(parents=True)
            (snapshot / "backend" / "jobs").mkdir(parents=True)
            current = root / "replica" / "current"
            current.symlink_to(Path("snapshots") / "snap-a")

            config_file = root / "backend" / "config.json"
            config_file.parent.mkdir(parents=True, exist_ok=True)
            config_file.write_text(
                json.dumps({"project_root": "..", "runs_root": "training-runs", "jobs_dir": "jobs"}),
                encoding="utf-8",
            )
            with patch.dict(
                os.environ,
                {
                    "FORECAST_BACKEND_CONFIG": str(config_file),
                    "FORECAST_RUNS_ROOT": str(current / "training-runs"),
                    "FORECAST_JOBS_DIR": str(current / "backend" / "jobs"),
                    "FORECAST_REPLICA_MODE": "1",
                },
                clear=False,
            ):
                loaded = module.load_config()

        self.assertIn("current", loaded["runs_root"])
        self.assertIn("current", loaded["jobs_dir"])
        self.assertNotIn("snap-a", loaded["runs_root"])
        self.assertNotIn("snap-a", loaded["jobs_dir"])
        self.assertTrue(loaded["replica_mode"])

    def test_replica_mode_is_off_without_the_explicit_flag(self) -> None:
        module = _load_config_module()
        env = {key: value for key, value in os.environ.items() if key != "FORECAST_REPLICA_MODE"}
        with patch.dict(os.environ, env, clear=True):
            loaded = module.load_config()
        self.assertFalse(loaded["replica_mode"])

    def test_database_override_keeps_the_symlink_too(self) -> None:
        """Behavioral: import db with FORECAST_DB_PATH through a symlink and
        assert the computed DB_PATH still goes through the link."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = root / "snapshots" / "snap-a"
            snapshot.mkdir(parents=True)
            (root / "current").symlink_to(Path("snapshots") / "snap-a")
            db_via_link = root / "current" / "forecast.db"
            result = subprocess.run(
                [sys.executable, "-c", "from backend.app import db; print(db.DB_PATH)"],
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                env={**os.environ, "FORECAST_DB_PATH": str(db_via_link)},
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("current", result.stdout)
        self.assertNotIn("snap-a", result.stdout)


class ReplicaJobExclusionTests(unittest.TestCase):
    """Pull and job launch are mutually exclusive so a snapshot swap can never
    land under a running agent (and vice versa)."""

    def test_start_job_refuses_while_a_pull_is_in_flight(self) -> None:
        with patch.dict(replica._STATE, {"pulling": True}):
            with self.assertRaises(RuntimeError):
                jobs.start_job("suggest_watch", "claude", {})

    def test_start_pull_refuses_while_a_job_is_running(self) -> None:
        with patch.dict(replica.CONFIG, {"replica_mode": True}), \
                patch.object(replica, "_CURRENT_OVERRIDE", None), \
                patch.object(jobs, "running_jobs", return_value=[{"id": "j1", "status": "running"}]):
            with self.assertRaises(RuntimeError):
                replica.start_pull()

    def test_pull_is_refused_when_pinned_to_one_snapshot(self) -> None:
        with patch.dict(replica.CONFIG, {"replica_mode": True}), \
                patch.object(replica, "_CURRENT_OVERRIDE", "/some/old/snapshot"):
            with self.assertRaises(PermissionError):
                replica.start_pull()


class ForeignJobRecordTests(unittest.TestCase):
    """Job records pulled from the production runner carry the runner's pids;
    the replica backend must never probe or signal them."""

    FOREIGN = {"id": "j-remote", "status": "running", "pid": 1, "host": "aws-runner", "engine": "codex"}

    def test_stop_refuses_records_from_another_host(self) -> None:
        with patch.dict(jobs.CONFIG, {"replica_mode": True}), \
                patch.object(jobs, "_load", return_value=dict(self.FOREIGN)):
            with self.assertRaises(PermissionError):
                jobs.stop_job("j-remote")

    def test_refresh_leaves_foreign_running_records_untouched(self) -> None:
        with patch.dict(jobs.CONFIG, {"replica_mode": True}):
            record = jobs._refresh(dict(self.FOREIGN))
        self.assertEqual(record["status"], "running")  # no pid probe, no rewrite

    def test_new_records_carry_this_host(self) -> None:
        source = (ROOT / "backend" / "app" / "jobs.py").read_text(encoding="utf-8")
        self.assertIn('"host": HOSTNAME,', source)


class PullProcessGroupTests(unittest.TestCase):
    def test_timeout_kills_the_whole_pull_process_tree(self) -> None:
        """A timed-out pull must not leave orphans that later swap
        replica/current behind the state machine's back."""
        with tempfile.TemporaryDirectory() as temp:
            pidfile = Path(temp) / "child.pid"
            script = Path(temp) / "fake_pull.sh"
            script.write_text(
                textwrap.dedent(
                    f"""\
                    #!/bin/bash
                    sleep 300 &
                    echo $! > "{pidfile}"
                    wait
                    """
                ),
                encoding="utf-8",
            )
            script.chmod(0o755)
            with patch.object(replica, "PULL_SCRIPT", script), \
                    patch.object(replica, "PULL_TIMEOUT_S", 1), \
                    patch.object(replica, "_KILL_GRACE_S", 2), \
                    patch.dict(replica._STATE, {}):
                replica._run_pull()
                state = replica.status()

            self.assertFalse(state["pulling"])
            self.assertIn("terminated", state["error"])
            if not pidfile.is_file():
                # Under load the shell may be SIGTERMed before it even forked
                # the child - then there is no orphan to verify. killpg covers
                # the fork window either way; skip the pid probe, not the test.
                return
            child_pid = int(pidfile.read_text(encoding="utf-8").strip())
            for _ in range(20):  # the group SIGTERM may take a moment to land
                try:
                    os.kill(child_pid, 0)
                except ProcessLookupError:
                    break
                time.sleep(0.1)
            else:
                os.kill(child_pid, signal.SIGKILL)
                self.fail("grandchild survived the pull timeout")

    def test_unexpected_exception_never_leaves_pulling_stuck(self) -> None:
        with patch.object(replica, "PULL_SCRIPT", Path("/nonexistent/pull.sh")), \
                patch.dict(replica._STATE, {}):
            replica._run_pull()
            state = replica.status()
        self.assertFalse(state["pulling"])
        self.assertTrue(state["error"])

    def test_pull_wrapper_holds_a_cross_process_lock(self) -> None:
        source = (ROOT / "deploy" / "forecast_runner" / "pull_and_prune.sh").read_text(encoding="utf-8")
        self.assertIn('mkdir "$lock_dir"', source)
        self.assertIn("kill -0", source)
        self.assertIn("trap 'rm -rf \"$lock_dir\"'", source)


class LocalBackendHardeningTests(unittest.TestCase):
    def test_backend_rejects_foreign_host_headers(self) -> None:
        source = (ROOT / "backend" / "app" / "main.py").read_text(encoding="utf-8")
        self.assertIn("TrustedHostMiddleware", source)
        self.assertIn('allowed_hosts=["localhost", "127.0.0.1", "testserver"]', source)


class ReplicaPullGuardTests(unittest.TestCase):
    def test_pull_is_refused_outside_replica_mode(self) -> None:
        with patch.dict(replica.CONFIG, {"replica_mode": False}):
            self.assertFalse(replica.enabled())
            with self.assertRaises(PermissionError):
                replica.start_pull()

    def test_pull_is_single_flight(self) -> None:
        with patch.dict(replica.CONFIG, {"replica_mode": True}), \
                patch.dict(replica._STATE, {"pulling": True}):
            with self.assertRaises(RuntimeError):
                replica.start_pull()

    def test_missing_pull_script_is_reported(self) -> None:
        with patch.dict(replica.CONFIG, {"replica_mode": True}), \
                patch.object(replica, "PULL_SCRIPT", Path("/nonexistent/pull_and_prune.sh")):
            with self.assertRaises(FileNotFoundError):
                replica.start_pull()

    def test_status_reports_snapshot_identity(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            current = Path(temp)
            (current / "manifest.json").write_text(
                json.dumps({
                    "snapshot_id": "20260721T023831Z-1",
                    "created_at": "2026-07-21T02:38:31Z",
                    "root_commit": "abc1234",
                    "site_commit": "def5678",
                    "size_bytes_before_manifest": 999,
                }),
                encoding="utf-8",
            )
            with patch.object(replica, "REPLICA_CURRENT", current), \
                    patch.dict(replica.CONFIG, {"replica_mode": True}):
                status = replica.status()

        self.assertTrue(status["mode"])
        self.assertFalse(status["pulling"])
        self.assertEqual(status["snapshot"]["snapshot_id"], "20260721T023831Z-1")
        self.assertEqual(status["snapshot"]["root_commit"], "abc1234")
        self.assertNotIn("size_bytes_before_manifest", status["snapshot"])

    def test_status_survives_a_missing_replica(self) -> None:
        with patch.object(replica, "REPLICA_CURRENT", Path("/nonexistent/replica/current")):
            self.assertIsNone(replica.status()["snapshot"])


class ReplicaControlsAreLocalOnlyTests(unittest.TestCase):
    def test_controls_ship_only_with_the_local_dashboard(self) -> None:
        controls = ROOT / "webapp" / "replica-controls.js"
        self.assertTrue(controls.is_file())
        self.assertIn("replica-controls.js", (ROOT / "webapp" / "index.html").read_text(encoding="utf-8"))

        sync = (
            ROOT / "sites" / "forecast-ops-console" / "scripts" / "sync-console-assets.mjs"
        )
        self.assertTrue(sync.is_file(), "the console asset sync script moved; update this guard")
        self.assertNotIn(
            "replica-controls",
            sync.read_text(encoding="utf-8"),
            "the hosted console must never receive the replica pull control",
        )


if __name__ == "__main__":
    unittest.main()
