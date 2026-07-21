# Deterministic multi-skill release

The durable trainer retains the historical-training loop and canonical method. The generated production system contains `technology-company-profit-forecasting`, three specialist skills and the non-skill contract kernel. It excludes Actuals retrieval, training-round machinery, curricula, case-specific training examples and benchmark archives.

The live coordinator is maintained as whole files under `assets/live_release/`; specialist and protocol sources live under `assets/skill_system/`. Generated top-level packages are never edited directly.

Run:

```bash
python3 scripts/build_skill_system.py \
  --trainer-skill-root <trainer-skill-root> \
  --output-parent <forecasting-skills-repo> \
  --self-test \
  --promote \
  --promotion-evidence <promotion-evidence.json>
```

The system builder first assembles and self-tests the live coordinator, then generates exact specialist/protocol copies from promotion-bound sources and validates unique stage ownership, modes and handoffs. Promotion evidence may select only the fixed `trainer_structural_contracts` suite. The inner live builder resolves that suite itself without a shell, ignores evidence-supplied executable arguments, uses the real return code and refuses trainer-tree mutation. Static company backtests remain diagnostics outside this structural gate; independent causal judgment is not collapsed into a pass ratio. A plain build is only a candidate. The release is the atomic git commit and push containing the trainer and every regenerated package.
