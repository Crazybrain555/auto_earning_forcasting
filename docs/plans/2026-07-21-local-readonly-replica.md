# Local Read-Only Production Replica Plan

**Goal:** Keep the AWS/Sites production path single-writer while giving the Mac a one-command, versioned production-data replica for comfortable localhost debugging.

**Authority boundary:** Git remains canonical for code. Sites/AWS remains canonical for production state and artifacts during the current transition. The Mac replica is pull-only and disposable; local test writes never flow back to production.

## Contract

1. The Runner creates an online-consistent bundle without stopping production:
   - `training-runs/`
   - `backend/state/` with SQLite copied through `.backup`
   - `backend/jobs/`
   - a manifest and SHA-256 checksums.
2. Secrets, `.env*`, Codex authentication, caches, virtual environments, dependencies, and unrelated services never enter the bundle.
3. The Mac command is dry-run by default. `--apply` downloads into `replica/snapshots/<snapshot-id>/`, verifies the archive, file checksums, and SQLite integrity, then atomically updates `replica/current`.
4. Existing snapshots are retained. Pulling never writes to AWS except for a short-lived export bundle that is deleted after successful download.
5. `backend/run-replica.sh` runs the normal localhost backend against `replica/current`; all mutations stay inside that disposable replica.
6. After full D1/R2 migration, preserve the local command contract and replace only the export source.

## Verification

- Unit-test the real bundle helper against a temporary SQLite database and secret canaries.
- Test the local command's default dry-run behavior and static pull-only/atomic-switch invariants.
- Test backend path overrides used by replica mode.
- Run the full backend suite, Site suite, shell syntax checks, and `git diff --check`.
