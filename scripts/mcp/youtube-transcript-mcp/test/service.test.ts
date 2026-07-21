import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";
import test from "node:test";

import { createYtDlpService, type YtDlpRunner } from "../src/service.js";

test("searchVideos requests one extra result and returns a stable page", async () => {
  const calls: string[][] = [];
  const runner: YtDlpRunner = async (args) => {
    calls.push([...args]);
    return JSON.stringify({
      entries: [
        { id: "a", title: "A" },
        { id: "b", title: "B" },
        { id: "c", title: "C" },
        { id: "d", title: "D" },
      ],
    });
  };
  const service = createYtDlpService({ runner });

  const result = await service.searchVideos("AI chips", 2, 1);

  assert.deepEqual(result.videos.map((video) => video.id), ["b", "c"]);
  assert.equal(calls.length, 1);
  assert.equal(calls[0]?.includes("ytsearch4:AI chips"), true);
  assert.equal(calls[0]?.includes("--flat-playlist"), true);
});

test("getVideoMetadata returns focused metadata and subtitle availability", async () => {
  const runner: YtDlpRunner = async () => JSON.stringify({
    id: "video123",
    title: "AI Hardware Update",
    webpage_url: "https://www.youtube.com/watch?v=video123",
    channel: "Research Channel",
    duration: 900,
    view_count: 1234,
    formats: [{ format_id: "large-field-that-must-not-be-returned" }],
    subtitles: { en: [{ ext: "vtt", name: "English" }] },
    automatic_captions: { ja: [{ ext: "vtt", name: "Japanese" }] },
  });
  const service = createYtDlpService({ runner });

  const result = await service.getVideoMetadata(
    "https://www.youtube.com/watch?v=video123",
  );

  assert.equal(result.id, "video123");
  assert.deepEqual(result.manual_subtitle_languages, ["en"]);
  assert.deepEqual(result.automatic_subtitle_languages, ["ja"]);
  assert.equal(result.has_public_subtitles, true);
  assert.equal("formats" in result, false);
});

test("getSubtitleArtifact saves the full VTT in the fixed cache and truncates only MCP content", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "youtube-mcp-test-"));
  const cacheDir = path.join(root, "cache");
  const vtt = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nA sufficiently long subtitle line.\n";
  const calls: string[][] = [];
  const runner: YtDlpRunner = async (args) => {
    calls.push([...args]);
    if (args.includes("--dump-single-json")) {
      return JSON.stringify({
        id: "video123",
        title: "Example",
        webpage_url: "https://www.youtube.com/watch?v=video123",
        subtitles: { en: [{ ext: "vtt", name: "English" }] },
        automatic_captions: {},
      });
    }
    const outputIndex = args.indexOf("--output");
    assert.notEqual(outputIndex, -1);
    const outputTemplate = args[outputIndex + 1];
    assert.equal(typeof outputTemplate, "string");
    await writeFile(outputTemplate!.replace("%(ext)s", "en.vtt"), vtt, "utf8");
    return "";
  };
  const service = createYtDlpService({ runner, cacheDir, maxContentChars: 12 });

  try {
    const artifact = await service.getSubtitleArtifact(
      "https://www.youtube.com/watch?v=video123",
      "en",
      true,
    );

    assert.equal(artifact.source, "manual");
    assert.equal(artifact.content_truncated, true);
    assert.equal(artifact.content.length, 12);
    assert.equal(path.dirname(artifact.saved_path), cacheDir);
    assert.equal(await readFile(artifact.saved_path, "utf8"), vtt);
    const downloadArgs = calls.at(-1) ?? [];
    assert.equal(downloadArgs.includes("--skip-download"), true);
    assert.equal(downloadArgs.includes("--write-subs"), true);
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("getTranscriptArtifact saves clean text derived only from the public VTT", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "youtube-mcp-transcript-test-"));
  const cacheDir = path.join(root, "cache");
  const vtt = "WEBVTT\n\n00:00:00.000 --> 00:00:01.000\nHello &amp; welcome.\n";
  const runner: YtDlpRunner = async (args) => {
    if (args.includes("--dump-single-json")) {
      return JSON.stringify({
        id: "video123",
        title: "Example",
        webpage_url: "https://www.youtube.com/watch?v=video123",
        subtitles: { en: [{ ext: "vtt", name: "English" }] },
      });
    }
    const outputTemplate = args[args.indexOf("--output") + 1];
    assert.equal(typeof outputTemplate, "string");
    await writeFile(outputTemplate!.replace("%(ext)s", "en.vtt"), vtt, "utf8");
    return "";
  };
  const service = createYtDlpService({ runner, cacheDir, maxContentChars: 100 });

  try {
    const artifact = await service.getTranscriptArtifact(
      "https://www.youtube.com/watch?v=video123",
      "en",
      true,
    );

    assert.equal(artifact.content, "Hello & welcome.");
    assert.match(artifact.saved_path, /\.txt$/);
    assert.equal(await readFile(artifact.saved_path, "utf8"), "Hello & welcome.");
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("Chrome cookie mode adds only yt-dlp browser-cookie arguments", async () => {
  let received: readonly string[] = [];
  const runner: YtDlpRunner = async (args) => {
    received = args;
    return JSON.stringify({ entries: [] });
  };
  const service = createYtDlpService({ runner, cookiesFromBrowser: "chrome" });

  await service.searchVideos("semiconductors", 1, 0);

  const cookieIndex = received.indexOf("--cookies-from-browser");
  assert.notEqual(cookieIndex, -1);
  assert.equal(received[cookieIndex + 1], "chrome");
  assert.throws(
    () => createYtDlpService({ runner, cookiesFromBrowser: "../../browser-profile" }),
    /Only the Chrome browser cookie source is supported/,
  );
});

test("searchCaptionedVideos returns only candidates with the requested public caption", async () => {
  const runner: YtDlpRunner = async (args) => {
    const target = args.at(-1) ?? "";
    if (target.startsWith("ytsearch")) {
      return JSON.stringify({
        entries: [
          { id: "with-captions", title: "Captioned" },
          { id: "without-captions", title: "Silent" },
        ],
      });
    }
    if (target.includes("with-captions")) {
      return JSON.stringify({
        id: "with-captions",
        title: "Captioned",
        webpage_url: target,
        subtitles: { en: [{ ext: "vtt", name: "English" }] },
      });
    }
    return JSON.stringify({
      id: "without-captions",
      title: "Silent",
      webpage_url: target,
      subtitles: {},
      automatic_captions: {},
    });
  };
  const service = createYtDlpService({ runner });

  const result = await service.searchCaptionedVideos("AI earnings", "en", 3, 5);

  assert.equal(result.count, 1);
  assert.equal(result.videos[0]?.id, "with-captions");
  assert.equal(result.videos[0]?.subtitle_source, "manual");
});
