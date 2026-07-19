# Deterministic companion live release

The durable trainer retains the historical-training loop and a full forecasting-method snapshot. The production artifact is emitted as the separate Skill `technology-company-profit-forecasting` and must exclude Actuals retrieval, training-round machinery, curricula, case-specific examples and benchmark archives.

The live profile is maintained as whole files under `assets/live_release/` (SKILL.md, openai.yaml, trigger_prompts.jsonl). When a promoted method change alters anything the production skill states, update the live SKILL.md there in the same commit; the builder assembles rather than rewrites.

Run:

```bash
python3 scripts/build_live_release.py \
  --trainer-skill-root <trainer-skill-root> \
  --output-root <live-skill-root>/technology-company-profit-forecasting \
  --self-test
```

The builder prunes trainer-only material, installs the live profile, verifies that no live SKILL.md pointer dangles and no trainer-only file survives, and runs the shared package self-test in its live profile. The release itself is the git commit and push that contains the rebuilt production skill.
