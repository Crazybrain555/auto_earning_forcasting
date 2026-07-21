# Company profit forecasting skill system (git-managed)

Five invokable Claude Code / Codex skills share one method:

- `technology-company-profit-forecasting` — thin live coordinator, red team and publication.
- `company-evidence-research` — point-in-time evidence, reusable observations and conflicts.
- `company-operating-modeling` — industry economics, causal graph and operating equations.
- `company-financial-forecasting` — integrated statements, attributable profit, earnings power and value.
- `technology-company-forecasting-trainer` — sealed historical evaluation, capability-level learning and release.

`forecasting-system-contracts` is a shared non-skill protocol kernel. The same
three specialists serve live and sealed historical work; only the trainer sees
post-seal Actuals.

The method version is the git commit. One training round = train on Group A -> validate on two untouched Group B companies -> push if clean; on failure swap fold (retrain on B, re-check on A, compare closeness); if still inconsistent, revert and restart with a new training group. Full procedure: `technology-company-forecasting-trainer/references/historical-training-loop.md`.

Rules of the repo:

- `training-runs/` is gitignored: case workspaces, actuals and evaluations never enter the method tree.
- Never hand-edit the live coordinator, specialist or contract output directories. Their canonical sources are under the trainer's `assets/skill_system/` and are regenerated with `scripts/build_skill_system.py --self-test`.
- Record `git rev-parse HEAD` as `method_commit` in every run manifest.
- To publish, add a remote and push: `git remote add origin <url> && git push -u origin main`.
