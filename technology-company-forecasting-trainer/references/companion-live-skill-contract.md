# Companion production Skill contract

The production forecasting Skill is `technology-company-profit-forecasting`; the training Skill is `technology-company-forecasting-trainer`. The two names are distinct so both can be installed side by side (Claude Code: `~/.claude/skills/` or `<project>/.claude/skills/`; Codex: `.agents/skills/`) without colliding. Keep both skills in one git repository; the method version of any run is the repository commit.

Routing rule: ordinary current-company forecasts, models, and valuations run under the production Skill. Historical training rounds, error diagnosis, method revisions, validation and regression re-runs, and release builds run under this trainer. If one side receives the other's request, hand off by naming the companion Skill instead of improvising.

Release rule: a revision that passes validation (see `references/historical-training-loop.md`) is released by regenerating the production skill with `scripts/build_live_release.py --self-test`, then committing and pushing both skills together. A revision that fails is reverted with git. Never hand-edit the installed production Skill outside this flow, and never leave the trainer and production skills describing different methods in the same commit.
