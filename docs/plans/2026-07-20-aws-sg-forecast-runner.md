# AWS Forecast Ops Runner Implementation Plan

> **For Codex:** Execute this plan task by task and verify each milestone before cutover.

**Goal:** Run the Forecast Ops Codex executor on a persistent cloud runner while Sites remains the production entry point and local machines remain development/test mirrors.

**Architecture:** Sites hosts the UI, API, D1 command/state store, and R2 artifacts. A replaceable trusted runner checks out the project, runs the localhost-only FastAPI execution service plus the Sites queue bridge, and launches `codex exec` using a ChatGPT device login created on that runner. Deployment-specific host, region, root path, and service names are parameters; the active values live only in `deploy/forecast_runner/README.md`.

**Tech Stack:** Sites Worker API, D1, R2, Node.js 22+, Python 3.13, uv, FastAPI, systemd system services running as an isolated user, Codex CLI, Git, rsync, project-scoped MCP servers.

---

### Task 1: Lock the portable runner contract

**Files:**
- Create: `backend/tests/test_runner_deployment.py`
- Modify: `.mcp.json`
- Modify: `.codex/config.toml`
- Modify: `backend/run.sh`
- Modify: `backend/config.json`

**Step 1: Write the failing tests**

Test that project MCP entries use project-relative script paths, the backend launcher contains no macOS-only Python path, engine commands resolve from `PATH`, and the backend remains bound to `127.0.0.1`.

**Step 2: Run the tests to verify RED**

Run: `python3 -m unittest backend.tests.test_runner_deployment -v`

Expected: failures identify `/Users/yuye`, `/opt/homebrew`, and missing runner assets.

**Step 3: Make the minimum portable changes**

Use relative project scripts in both MCP configurations, `${PYTHON_BIN:-python3}` in the launcher, and `codex`/`claude` commands resolved through the service `PATH`.

**Step 4: Run the focused tests to verify GREEN**

Run: `python3 -m unittest backend.tests.test_runner_deployment -v`

Expected: all runner portability tests pass.

### Task 2: Add deterministic service rendering

**Files:**
- Create: `deploy/forecast_runner/render_units.py`
- Create: `deploy/forecast_runner/systemd/forecast-ops-backend.service.in`
- Create: `deploy/forecast_runner/systemd/forecast-sites-bridge.service.in`
- Modify: `backend/tests/test_runner_deployment.py`

**Step 1: Write the failing tests**

Test rendering with an arbitrary runner root and env-file path. Assert that no placeholder remains, the backend listens only on localhost, the bridge starts after the backend, both services restart safely, and neither unit references AWS, Singapore, an IP address, or a personal home path.

**Step 2: Run the tests to verify RED**

Run: `python3 -m unittest backend.tests.test_runner_deployment -v`

Expected: renderer/templates are missing.

**Step 3: Implement the renderer and templates**

Render systemd units from explicit `--runner-root`, separate backend/bridge environment-file paths, `--runner-user`, and `--output-dir` arguments. Keep provider identity outside the service definitions and run both units as the dedicated account.

**Step 4: Run the focused tests to verify GREEN**

Run: `python3 -m unittest backend.tests.test_runner_deployment -v`

Expected: all tests pass.

### Task 3: Add a safe bootstrap and code/data transfer path

**Files:**
- Create: `deploy/forecast_runner/bootstrap.sh`
- Create: `deploy/forecast_runner/sync_to_runner.sh`
- Modify: `backend/tests/test_runner_deployment.py`

**Step 1: Write the failing tests**

Assert that synchronization excludes `.env*`, authentication files, caches, virtual environments, `node_modules`, build output, browser data, and live SQLite WAL/SHM files; assert that it does not use `--delete`; assert that bootstrap installs isolated dependencies and never changes system-global Codex or Node installations.

**Step 2: Run the tests to verify RED**

Run: `python3 -m unittest backend.tests.test_runner_deployment -v`

Expected: scripts are missing.

**Step 3: Implement minimal scripts**

Synchronize the exact source and Git worktrees into a newly created runner directory without deleting remote siblings. Build fresh Linux environments from lockfiles. Transfer runtime secrets separately into mode-0600 backend and bridge environment files; never expose bridge/ingest secrets to the backend or spawned Codex processes. Copy a consistent SQLite backup rather than live WAL/SHM files.

**Step 4: Run the focused tests to verify GREEN**

Run: `python3 -m unittest backend.tests.test_runner_deployment -v`

Expected: all tests pass.

### Task 4: Document replaceable deployment topology

**Files:**
- Modify: `README.md`
- Modify: `backend/README.md`
- Modify: `sites/forecast-ops-console/README.md`
- Create: `deploy/forecast_runner/README.md`
- Modify: `backend/tests/test_runner_deployment.py`

**Step 1: Write the failing documentation checks**

Assert that the root README names Sites as the production entry/data plane, describes a replaceable cloud runner, documents one-way production-to-local backup semantics, and keeps the current AWS Singapore profile in one replaceable section.

**Step 2: Run the tests to verify RED**

Run: `python3 -m unittest backend.tests.test_runner_deployment -v`

Expected: required architecture wording is absent.

**Step 3: Update documentation**

Document ownership boundaries, deployment parameters, secret handling, Git/MCP parity, migration, health checks, failover, and how to change runner providers without rewriting product architecture.

**Step 4: Run the focused tests to verify GREEN**

Run: `python3 -m unittest backend.tests.test_runner_deployment -v`

Expected: all tests pass.

### Task 5: Provision the isolated AWS runner

**External paths:**
- Create: the active profile's `RUNNER_ROOT`
- Create: the active profile's `BACKEND_ENV_FILE`
- Create: the active profile's `BRIDGE_ENV_FILE`
- Create: `/etc/systemd/system/forecast-ops-backend.service`
- Create: `/etc/systemd/system/forecast-sites-bridge.service`

**Step 1: Capture read-only preflight evidence**

Record OS, disk, Python/Node/Codex/Git versions, authentication status without tokens, current user services, and the absence of the target directory.

**Step 2: Transfer code and consistent data**

Run the safe sync in apply mode, separately install the mode-0600 backend and bridge environment files, and transfer a SQLite `.backup` plus `training-runs`, job records, and UI state. The backend file must not contain bridge/ingest credentials. Do not transfer caches, browser cookies, local auth files, or macOS binaries.

**Step 3: Build the isolated runtime**

Create Python 3.13 environments, install locked project dependencies, install Node dependencies from lockfiles, install a project-scoped Codex CLI matching the validated local version, and build project MCP servers.

**Step 4: Render and start services**

Install system-level units that run as the dedicated account from the active profile, reload systemd, start the backend, verify localhost health, then start the bridge. Leave existing OpenClaw units untouched.

### Task 6: Verify cutover and stop the old local bridge

**Step 1: Run local regression suites**

Run backend unit tests, Site tests/build/lint, and `git diff --check`.

**Step 2: Run remote smoke tests**

Verify Codex login status, MCP discovery, backend health, bridge heartbeat, queue drain, state/artifact synchronization, and service restart recovery.

**Step 3: Verify production from Sites**

Submit one idempotent, non-destructive control operation through Sites and confirm the AWS runner—not the Mac—leases and completes it. Confirm the public UI no longer depends on local power state.

**Step 4: Disable the macOS bridge only after cutover**

Unload the existing macOS LaunchAgent without deleting its plist, preserving an easy rollback. Confirm AWS remains online for at least one full heartbeat window.

**Step 5: Record deployment state**

Update the marked active profile only in `deploy/forecast_runner/README.md`. Record source commits/dirty-state hashes, validation evidence, service names, and rollback procedure without copying host parameters or secrets into a second location.
