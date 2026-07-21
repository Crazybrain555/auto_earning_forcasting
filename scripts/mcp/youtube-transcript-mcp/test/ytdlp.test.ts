import assert from "node:assert/strict";
import test from "node:test";

import {
  buildSubtitleDownloadArgs,
  cleanVttTranscript,
  parseSearchResults,
  parseSubtitleInventory,
  safeCacheBasename,
  selectSubtitleTrack,
  validateYouTubeUrl,
} from "../src/ytdlp.js";

test("validateYouTubeUrl accepts YouTube video URLs and rejects lookalike hosts", () => {
  assert.equal(validateYouTubeUrl("https://www.youtube.com/watch?v=aircAruvnKk"), true);
  assert.equal(validateYouTubeUrl("https://youtu.be/aircAruvnKk"), true);
  assert.equal(validateYouTubeUrl("https://youtube.com.evil.example/watch?v=aircAruvnKk"), false);
  assert.equal(validateYouTubeUrl("https://example.com/video"), false);
});

test("parseSubtitleInventory distinguishes manual and automatic caption tracks", () => {
  const inventory = parseSubtitleInventory({
    id: "video123",
    title: "Example",
    webpage_url: "https://www.youtube.com/watch?v=video123",
    subtitles: {
      en: [{ ext: "vtt", name: "English" }],
    },
    automatic_captions: {
      en: [{ ext: "vtt", name: "English (auto-generated)" }],
      "zh-Hans": [{ ext: "vtt", name: "Chinese (Simplified)" }],
    },
  });

  assert.deepEqual(inventory.manual.map((track) => track.language), ["en"]);
  assert.deepEqual(inventory.automatic.map((track) => track.language), ["en", "zh-Hans"]);
});

test("selectSubtitleTrack prefers a manual exact match before automatic captions", () => {
  const inventory = parseSubtitleInventory({
    id: "video123",
    title: "Example",
    subtitles: { en: [{ ext: "vtt", name: "English" }] },
    automatic_captions: { en: [{ ext: "vtt", name: "English (auto-generated)" }] },
  });

  assert.deepEqual(selectSubtitleTrack(inventory, "en", true), {
    language: "en",
    source: "manual",
  });
  assert.deepEqual(selectSubtitleTrack(inventory, "en", false), {
    language: "en",
    source: "automatic",
  });
});

test("buildSubtitleDownloadArgs always skips media and selects only one subtitle source", () => {
  const manualArgs = buildSubtitleDownloadArgs(
    "https://www.youtube.com/watch?v=video123",
    { language: "en", source: "manual" },
    "/tmp/subtitle.%(ext)s",
  );
  const automaticArgs = buildSubtitleDownloadArgs(
    "https://www.youtube.com/watch?v=video123",
    { language: "en", source: "automatic" },
    "/tmp/subtitle.%(ext)s",
  );

  assert.equal(manualArgs.includes("--skip-download"), true);
  assert.equal(manualArgs.includes("--write-subs"), true);
  assert.equal(manualArgs.includes("--write-auto-subs"), false);
  assert.equal(automaticArgs.includes("--skip-download"), true);
  assert.equal(automaticArgs.includes("--write-auto-subs"), true);
  assert.equal(automaticArgs.includes("--write-subs"), false);
  assert.equal(manualArgs.some((arg) => /audio|video-format|extract-audio/.test(arg)), false);
});

test("cleanVttTranscript removes timing markup and consecutive duplicate text", () => {
  const vtt = `WEBVTT\n\n00:00:00.000 --> 00:00:01.000\n<v Speaker>Hello &amp; welcome</v>\n\n00:00:01.000 --> 00:00:02.000\nHello &amp; welcome\n\n00:00:02.000 --> 00:00:03.000\nToday we begin.\n`;

  assert.equal(cleanVttTranscript(vtt), "Hello & welcome\nToday we begin.");
});

test("parseSearchResults paginates flat yt-dlp search output", () => {
  const result = parseSearchResults(
    {
      entries: [
        { id: "a", title: "A", url: "https://www.youtube.com/watch?v=a" },
        { id: "b", title: "B", url: "https://www.youtube.com/watch?v=b" },
        { id: "c", title: "C", url: "https://www.youtube.com/watch?v=c" },
        { id: "d", title: "D", url: "https://www.youtube.com/watch?v=d" },
      ],
    },
    1,
    2,
  );

  assert.deepEqual(result.videos.map((video) => video.id), ["b", "c"]);
  assert.equal(result.has_more, true);
  assert.equal(result.next_offset, 3);
});

test("safeCacheBasename cannot create nested or parent paths", () => {
  const name = safeCacheBasename("../video/id", "../../en-US", "manual", "vtt");
  assert.equal(name.includes("/"), false);
  assert.equal(name.includes(".."), false);
  assert.match(name, /\.vtt$/);
});
