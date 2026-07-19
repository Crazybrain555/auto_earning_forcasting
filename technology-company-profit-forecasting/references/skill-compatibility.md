# Codex and Claude compatibility

Both Skills follow the common Agent Skills shape: a directory whose name equals the SKILL.md frontmatter `name`, with YAML `name` and `description`, plus optional `scripts/`, `references/`, and `assets/`. Frontmatter constraints: lowercase letters, digits, and hyphens, name <= 64 characters, description <= 1024 characters, written in third person with explicit use-when and do-not-use-when guidance.

For Claude Code, install by copying the skill directory to `~/.claude/skills/<name>/` (personal) or `<project>/.claude/skills/<name>/` (project), or install the package root as a plugin (`.claude-plugin/plugin.json` plus `skills/`). The trainer and the production Skill carry different names, so both can be installed at the same level simultaneously; identical names at the same level would collide, which is why the split names are mandatory.

For Codex, `agents/openai.yaml` supplies UI metadata and `.codex-plugin/plugin.json` sits at the package root; install by copying the skill directory to `.agents/skills/<name>/`.

Keep critical workflow rules in `SKILL.md`; load detailed references only when relevant. Scripts are invoked relative to the skill directory (`${CLAUDE_SKILL_DIR}` in Claude Code), never relative to the user's project root.
