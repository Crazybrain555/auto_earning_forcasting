# YouTube Public-Subtitle Research MCP Implementation Plan

> **For Codex:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add one project-scoped, read-only YouTube research MCP that both Codex and Claude can use to search videos and retrieve only publicly available subtitle data.

**Architecture:** Run a small project-owned TypeScript MCP server over stdio through one repository wrapper. The server shells out safely to `yt-dlp` without a command shell and registers only YouTube search, metadata, subtitle-language discovery, timestamped subtitle, and clean-transcript tools—there is no video/audio tool to expose accidentally. Codex and Claude point at the same wrapper. Start anonymously; enable the user's own Chrome cookies only if YouTube blocks the machine as a bot.

**Tech Stack:** TypeScript, official MCP TypeScript SDK v1, Zod, Bash, Node.js, `yt-dlp`, Deno, Codex project MCP config, Claude project MCP config.

---

### Task 1: Inspect available upstream MCPs and define the safe surface

**Files:**
- Create: `docs/plans/2026-07-20-youtube-research-mcp.md`

1. Query npm for the current package version, dependency metadata, and repository.
2. Inspect the package's live MCP tool list, schemas, and runtime behavior.
3. If the upstream package cannot enforce a pure-subtitle boundary or its documented limits do not work, implement a focused local server instead of exposing media tools.

### Task 2: Install and validate runtime dependencies

**Files:**
- No repository files modified.

1. Check for `yt-dlp`, Deno, Node.js, and npx.
2. Install missing `yt-dlp` and Deno runtimes with Homebrew.
3. Run `yt-dlp --list-subs` against a known public, captioned YouTube video without cookies.
4. If YouTube returns a bot challenge, retry at low volume using the user's own Chrome browser cookies and avoid exporting or printing cookie data.

### Task 3: Build the pure-subtitle MCP and shared launcher

**Files:**
- Create: `scripts/mcp/youtube-transcript-mcp/package.json`
- Create: `scripts/mcp/youtube-transcript-mcp/package-lock.json`
- Create: `scripts/mcp/youtube-transcript-mcp/tsconfig.json`
- Create: `scripts/mcp/youtube-transcript-mcp/src/index.ts`
- Create: `scripts/mcp/youtube-transcript-mcp/src/ytdlp.ts`
- Create: `scripts/mcp/youtube-transcript-mcp/test/ytdlp.test.ts`
- Create: `scripts/mcp/youtube-transcript-mcp/README.md`
- Create: `scripts/mcp/youtube-transcript.sh`

1. Write failing unit tests for URL validation, subtitle selection, safe yt-dlp arguments, transcript cleanup, and search pagination.
2. Implement only the minimum service code needed to pass those tests.
3. Register six focused MCP tools using modern `registerTool`, strict Zod schemas, structured results, and accurate annotations.
4. Keep subtitle files inside the repository's ignored `.cache/youtube-transcripts` directory and never accept an arbitrary output path.
5. Add a strict Bash launcher and add Chrome cookie access only if the anonymous integration test proves it is required.
6. Run unit tests, TypeScript build, `bash -n`, and start the server through an MCP client.

### Task 4: Configure both MCP clients

**Files:**
- Modify: `.mcp.json`
- Modify: `.codex/config.toml`
- Modify: `.claude/settings.json`
- Modify: `.claude/settings.local.json`

1. Point Claude and Codex at the same launcher.
2. In Codex, expose only the exact search, metadata, and subtitle tools.
3. In Claude, allow the same exact subtitle-safe tools; the server itself contains no video/audio operation.
4. Parse both JSON files and the TOML file to catch syntax errors.

### Task 5: Document forecast-research behavior

**Files:**
- Modify: `AGENTS.md`
- Modify: `CLAUDE.md`

1. Document the search-to-subtitle workflow.
2. State that video/audio downloads and speech-to-text fallback are out of scope.
3. Prefer creator-provided captions, then automatic public captions; skip videos with no public subtitle track.
4. Require timestamps and corroboration for exact figures or names found in automatic captions.

### Task 6: End-to-end verification

**Files:**
- Verify all files above.

1. Confirm Codex and Claude both discover the shared MCP.
2. Call search or metadata, list subtitle languages, and fetch a transcript from a known public video.
3. Verify the result is text/subtitle data only and includes useful timestamps or subtitle structure.
4. Confirm Codex does not expose media-download tools and Claude denies them.
5. Review `git diff` and `git status` without modifying unrelated user work.
