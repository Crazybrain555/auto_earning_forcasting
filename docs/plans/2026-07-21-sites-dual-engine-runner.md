# Sites Dual-Engine Runner Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Let the hosted Forecast Ops console select and safely execute either Claude Code or Codex on the AWS Runner, matching the local console.

**Architecture:** Keep the existing named-command queue and fixed localhost mappings. Preserve only an allowlisted `claude|codex` engine value through the Site read API, command normalization and Runner bridge; keep prompts, commands, paths and headers server-owned. Install both CLIs in the Runner-scoped runtime, authenticate them independently on the Runner, and advertise an engine only when its executable is actually present.

**Tech Stack:** Sites Worker/Vinext, TypeScript, Node test runner, FastAPI/Python, Claude Code CLI, Codex CLI, systemd.

---

### Task 1: Define the hosted dual-engine contract

**Files:**
- Modify: `sites/forecast-ops-console/tests/remote-api.test.mjs`
- Modify: `sites/forecast-ops-console/tests/command-queue.test.mjs`
- Modify: `sites/forecast-ops-console/tests/bridge-actions.test.mjs`
- Modify: `sites/forecast-ops-console/tests/interactive-parity.test.mjs`

1. Assert `/api/engines` exposes both available allowlisted engines.
2. Assert `job.start` preserves `claude` or `codex`, rejects unknown engines and still strips raw execution fields.
3. Run the focused Node tests and confirm they fail because the current implementation filters or rewrites Claude.
4. Update the Site API, queue normalizer, bootstrap policy and bridge mapping minimally.
5. Re-run the focused tests and confirm they pass.

### Task 2: Make Runner availability truthful

**Files:**
- Modify: `backend/tests/test_dual_engine_dashboard.py`
- Modify: `backend/app/jobs.py`
- Modify: `backend/tests/test_runner_deployment.py`
- Modify: `deploy/forecast_runner/bootstrap.sh`

1. Assert a configured engine whose executable is absent is reported unavailable.
2. Assert bootstrap pins both Codex and Claude Code.
3. Run the focused Python tests and confirm failure under the old configuration-only status logic.
4. Add executable detection and the project-scoped Claude installation.
5. Re-run focused and full backend tests.

### Task 3: Provision and authenticate Claude on AWS

**Files:**
- Modify: `deploy/forecast_runner/README.md`
- Modify: `backend/README.md`
- Modify: `sites/forecast-ops-console/README.md`

1. Synchronize only the reviewed implementation files to the Runner.
2. Install the pinned Claude Code package under `.runtime/tools`.
3. Complete a Runner-specific Claude subscription login; do not copy Mac credentials.
4. Run a bounded non-interactive `claude -p` smoke test in the dedicated workspace.
5. Restart the backend and verify `/api/engines` reports both engines available.

### Task 4: Validate and publish the Site

**Files:**
- Modify: Site source files listed above.

1. Run the full Site test/build and lint.
2. Run the full AWS backend suite and verify the bridge remains online.
3. Commit and push the exact validated Site source.
4. Package, save and deploy a new Site version.
5. Verify the deployed snapshot exposes Claude and Codex and that no test command remains queued.
