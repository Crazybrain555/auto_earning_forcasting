import assert from "node:assert/strict";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

test("stdio server exposes only the six public YouTube subtitle research tools", async () => {
  const cacheDir = await mkdtemp(path.join(tmpdir(), "youtube-mcp-server-test-"));
  const transport = new StdioClientTransport({
    command: process.execPath,
    args: ["--import", "tsx", "src/index.ts"],
    cwd: process.cwd(),
    env: {
      ...process.env,
      YOUTUBE_TRANSCRIPT_CACHE_DIR: cacheDir,
    },
  });
  const client = new Client({ name: "youtube-mcp-test-client", version: "1.0.0" });

  try {
    await client.connect(transport);
    const listed = await client.listTools();
    const names = listed.tools.map((tool) => tool.name).sort();
    assert.deepEqual(names, [
      "youtube_get_subtitles",
      "youtube_get_transcript",
      "youtube_get_video_metadata",
      "youtube_list_subtitle_languages",
      "youtube_search_captioned_videos",
      "youtube_search_videos",
    ]);
    assert.equal(names.includes("youtube_download_video"), false);
    assert.equal(names.includes("youtube_download_audio"), false);

    const invalid = await client.callTool({
      name: "youtube_get_video_metadata",
      arguments: { url: "https://example.com/not-youtube" },
    });
    assert.equal(invalid.isError, true);
    assert.match(JSON.stringify(invalid.content), /Invalid YouTube video URL/);
  } finally {
    await client.close();
    await rm(cacheDir, { recursive: true, force: true });
  }
});
