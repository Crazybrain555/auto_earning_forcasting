# Site interaction fast-path implementation plan

## Objective

Make ordinary dashboard interactions feel immediate without weakening the local
execution boundary, while keeping long-running forecast and training jobs
truthful about their submitted, queued, running, and terminal states.

## Product contract

| Interaction class | Examples | User-visible behavior |
| --- | --- | --- |
| Local UI | navigation, filters, drawers | Apply synchronously; no network status |
| Reversible write | watchlist add/remove, clear suggestions, pause/resume, version activate/delete/restore, soft-delete case/round/job | Apply an optimistic projection immediately, send one idempotent command, stay silent on normal success, roll back and show a useful error on failure |
| Saved configuration | round plan save | Keep the edited value on screen, show a small saving state, then saved or error |
| Long-running work | forecast, training, planning, AI suggestions | Show “已提交” as soon as the command is accepted; show “运行中” only after the job record says it is running; continue normal background reconciliation |
| Interrupting work | stop a running job | Show “停止中” immediately, then reconcile to stopped or restore the prior state on failure |

Infrastructure words such as “本地桥”, “命令队列”, and “等待桥” must not
appear in ordinary action feedback. Genuine job scheduling may still expose
the job's own queued state and position on the Jobs page.

## Root cause

The hosted fetch adapter currently converts every write into a synchronous
120-second wait for a D1 command to finish. The runner processes one command
per 15-second full snapshot cycle and acknowledges most commands only after
collecting and publishing the snapshot. The shared UI then reloads data after
the write, so ordinary reversible actions inherit infrastructure latency and
show infrastructure-specific messages.

## Implementation

### 1. Test the interaction contract first

Files:

- `sites/forecast-ops-console/tests/action-feedback.test.mjs`
- `sites/forecast-ops-console/tests/remote-bootstrap.test.mjs`
- `sites/forecast-ops-console/tests/local-bridge.test.mjs`
- `webapp/tests/interaction-state.test.cjs` (new)

Add failing tests that require:

- no generic queue/bridge toast for ordinary commands;
- an optimistic operation applies before the network promise settles;
- failure rolls the operation back and reports an accessible error;
- long jobs use accepted/running language rather than claiming premature
  completion;
- the browser adapter returns a stable accepted response quickly for long-job
  submission while retaining command identity for reconciliation;
- command execution and command acknowledgement happen before snapshot
  collection;
- the daemon drains consecutive commands without a 15-second sleep between
  them and coalesces snapshot work.

### 2. Add a small shared interaction state layer

Files:

- `webapp/interaction-state.js` (new)
- `webapp/index.html`
- `webapp/app.js`
- `webapp/style.css`
- generated hosted copies under
  `sites/forecast-ops-console/public/console/`

Implement a browser-global helper with:

- operation identity and interaction class;
- optimistic apply/rollback/commit hooks;
- button state helpers for saving/submitted/stopping;
- a pending overlay map so a stale snapshot cannot immediately reverse a
  just-applied optimistic action;
- bounded reconciliation and session persistence for in-flight accepted
  commands;
- centralized accessible failure feedback.

Use the helper across all ordinary writes, not only deletion. Keep job state
separate: accepted is not running.

### 3. Make the hosted command adapter category-aware

Files:

- `sites/forecast-ops-console/public/console/remote-bootstrap.js`
- `sites/forecast-ops-console/app/lib/command-api.ts` if command metadata is
  required by the hosted response

For ordinary writes, return once the Sites API has durably accepted the
idempotent command and expose the command id to the interaction layer. Poll
completion in the background and dispatch success/failure events. For job
starts and stops, return an explicit accepted result immediately; the normal
job/snapshot polling remains the authority for running and terminal status.

Never reinterpret accepted as succeeded. Preserve duplicate protection and
surface asynchronous command failure so optimistic UI can roll back.

### 4. Split fast command execution from snapshot publication

Files:

- `sites/forecast-ops-console/scripts/bridge-local.mjs`
- `sites/forecast-ops-console/tests/local-bridge.test.mjs`

Refactor the daemon into:

- a fast command cycle: heartbeat as needed, lease, renew, execute localhost,
  complete immediately, and continue draining;
- a snapshot cycle: collect, publish model-hiding safety snapshot when needed,
  synchronize model artifacts within the existing budget, publish the final
  snapshot;
- a coordinator that marks snapshots dirty after commands, coalesces bursts,
  and runs periodic refreshes independently.

Keep `--once` deterministic for operations and tests. Preserve lease-loss,
idempotency, sanitization, artifact-size, and model visibility safety
guarantees.

### 5. Verify

Run from the isolated root worktree:

```bash
node --test webapp/tests/*.test.cjs
```

Run from the isolated Site worktree:

```bash
npm test
npm run lint
npm run build
```

Also run focused latency/order tests showing that command acknowledgement does
not await snapshot collection and that back-to-back commands are drained
without the old interval.

### 6. Release

1. Commit and push the root UI branch.
2. Sync the shared console assets into the Site repository.
3. Commit and push the Site/runner branch.
4. Confirm there is no running forecast/training job before changing the
   runner bridge.
5. Deploy the bridge-only change and verify its service health and command
   drain logs.
6. Push the exact Site commit to the existing Sites source repository, package
   it, save a new version, deploy publicly, and poll to a terminal success.
7. Verify the production asset version, bridge health, and read-only pages.
8. Update `HANDOFF.md` with the shipped behavior, commits, deployment version,
   verification commands, and remaining operational notes.

