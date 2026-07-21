#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

import { createYtDlpService } from "./service.js";

const service = createYtDlpService();
const server = new McpServer({
  name: "youtube-transcript-mcp-server",
  version: "1.0.0",
});

const responseFormatSchema = z
  .enum(["json", "markdown"])
  .default("json")
  .describe("Return JSON for programmatic use or concise Markdown for reading.");

const annotations = {
  readOnlyHint: true,
  destructiveHint: false,
  idempotentHint: true,
  openWorldHint: true,
} as const;

function asRecord(value: object): Record<string, unknown> {
  return Object.fromEntries(Object.entries(value));
}

function success(value: object, text?: string) {
  const structuredContent = asRecord(value);
  return {
    content: [{ type: "text" as const, text: text ?? JSON.stringify(value, null, 2) }],
    structuredContent,
  };
}

async function execute(action: () => Promise<ReturnType<typeof success>>) {
  try {
    return await action();
  } catch (error) {
    return {
      content: [{
        type: "text" as const,
        text: error instanceof Error ? error.message : String(error),
      }],
      isError: true,
    };
  }
}

server.registerTool(
  "youtube_search_videos",
  {
    title: "Search YouTube Videos",
    description: `Search public YouTube videos by keywords without downloading media.

Use this for broad discovery. Results include stable video URLs and basic metadata. To return only videos that have a requested public caption language, use youtube_search_captioned_videos instead.

Returns a paginated object with count, offset, videos, has_more, and next_offset.`,
    inputSchema: z.object({
      query: z.string().min(2).max(300).describe("YouTube search keywords."),
      max_results: z.number().int().min(1).max(20).default(10)
        .describe("Maximum videos to return (1-20)."),
      offset: z.number().int().min(0).max(80).default(0)
        .describe("Number of search results to skip."),
      response_format: responseFormatSchema,
    }).strict(),
    annotations,
  },
  async ({ query, max_results, offset, response_format }) => execute(async () => {
    const result = await service.searchVideos(query, max_results, offset);
    const markdown = [
      `# YouTube search: ${query}`,
      "",
      ...result.videos.map((video) =>
        `- [${video.title}](${video.url}) — ${video.channel ?? "unknown channel"}`),
      "",
      result.has_more ? `Next offset: ${result.next_offset}` : "No more fetched results.",
    ].join("\n");
    return success(result, response_format === "markdown" ? markdown : undefined);
  }),
);

server.registerTool(
  "youtube_search_captioned_videos",
  {
    title: "Search Captioned YouTube Videos",
    description: `Search YouTube and keep only videos with a public subtitle track matching a language.

This is the preferred discovery workflow for forecast research because it filters out videos with no usable captions. Manual creator captions are preferred; public automatic captions are accepted as fallback. It inspects several candidates, so keep limits small to reduce YouTube rate limiting.

Returns videos with subtitle_language and subtitle_source ('manual' or 'automatic').`,
    inputSchema: z.object({
      query: z.string().min(2).max(300).describe("YouTube search keywords."),
      language: z.string().min(2).max(20).default("en")
        .describe("Requested public caption language code, for example en or zh-Hans."),
      max_results: z.number().int().min(1).max(5).default(5)
        .describe("Maximum captioned videos to return (1-5)."),
      max_candidates: z.number().int().min(1).max(15).default(8)
        .describe("Maximum search candidates to inspect for captions (1-15)."),
      response_format: responseFormatSchema,
    }).strict(),
    annotations,
  },
  async ({ query, language, max_results, max_candidates, response_format }) => execute(async () => {
    const result = await service.searchCaptionedVideos(
      query,
      language,
      max_results,
      max_candidates,
    );
    const markdown = [
      `# Captioned YouTube search: ${query}`,
      "",
      ...result.videos.map((video) =>
        `- [${video.title}](${video.url}) — ${video.subtitle_language}, ${video.subtitle_source}`),
      "",
      `Inspected ${result.inspected}; found ${result.count}.`,
    ].join("\n");
    return success(result, response_format === "markdown" ? markdown : undefined);
  }),
);

server.registerTool(
  "youtube_get_video_metadata",
  {
    title: "Get YouTube Video Metadata",
    description: `Get focused metadata for one public YouTube video without downloading media.

Returns title, channel, duration, dates, engagement counts, description, and the manual/automatic public subtitle language lists. Large technical format arrays are intentionally omitted.`,
    inputSchema: z.object({
      url: z.string().url().max(500).describe("A youtube.com or youtu.be video URL."),
      response_format: responseFormatSchema,
    }).strict(),
    annotations,
  },
  async ({ url, response_format }) => execute(async () => {
    const result = await service.getVideoMetadata(url);
    const markdown = [
      `# ${result.title}`,
      "",
      `- Channel: ${result.channel ?? "unknown"}`,
      `- Duration: ${result.duration_seconds ?? "unknown"} seconds`,
      `- Manual captions: ${result.manual_subtitle_languages.join(", ") || "none"}`,
      `- Automatic captions: ${result.automatic_subtitle_languages.join(", ") || "none"}`,
    ].join("\n");
    return success(result, response_format === "markdown" ? markdown : undefined);
  }),
);

server.registerTool(
  "youtube_list_subtitle_languages",
  {
    title: "List Public YouTube Subtitle Languages",
    description: `List creator-provided and automatic public caption tracks for one YouTube video.

Call this before fetching a specific language. It clearly separates manual tracks from automatic captions and returns available subtitle formats. Videos with neither list are intentionally skipped by this project workflow.`,
    inputSchema: z.object({
      url: z.string().url().max(500).describe("A youtube.com or youtu.be video URL."),
      response_format: responseFormatSchema,
    }).strict(),
    annotations,
  },
  async ({ url, response_format }) => execute(async () => {
    const result = await service.listSubtitleLanguages(url);
    const markdown = [
      `# Subtitle languages: ${result.title}`,
      "",
      `- Manual: ${result.manual.map((track) => track.language).join(", ") || "none"}`,
      `- Automatic: ${result.automatic.map((track) => track.language).join(", ") || "none"}`,
    ].join("\n");
    return success(result, response_format === "markdown" ? markdown : undefined);
  }),
);

server.registerTool(
  "youtube_get_subtitles",
  {
    title: "Get Timestamped YouTube Subtitles",
    description: `Fetch one public YouTube subtitle track as timestamped WebVTT; never downloads video or audio.

The complete VTT is saved in the project's fixed ignored subtitle cache. The response includes its path and up to the configured MCP character limit. Manual captions are preferred by default, with public automatic captions as fallback.`,
    inputSchema: z.object({
      url: z.string().url().max(500).describe("A youtube.com or youtu.be video URL."),
      language: z.string().min(2).max(20).default("en")
        .describe("Requested caption language code."),
      prefer_manual: z.boolean().default(true)
        .describe("Prefer creator-provided captions before automatic captions."),
    }).strict(),
    annotations: { ...annotations, readOnlyHint: false },
  },
  async ({ url, language, prefer_manual }) => execute(async () => {
    const result = await service.getSubtitleArtifact(url, language, prefer_manual);
    return success(result, result.content);
  }),
);

server.registerTool(
  "youtube_get_transcript",
  {
    title: "Get Clean YouTube Transcript",
    description: `Fetch public YouTube captions and derive a clean plain-text transcript; never uses speech recognition and never downloads media.

The full text is saved in the project's fixed ignored subtitle cache. Use youtube_get_subtitles instead when exact timestamps matter. Manual captions are preferred by default, with public automatic captions as fallback.`,
    inputSchema: z.object({
      url: z.string().url().max(500).describe("A youtube.com or youtu.be video URL."),
      language: z.string().min(2).max(20).default("en")
        .describe("Requested caption language code."),
      prefer_manual: z.boolean().default(true)
        .describe("Prefer creator-provided captions before automatic captions."),
    }).strict(),
    annotations: { ...annotations, readOnlyHint: false },
  },
  async ({ url, language, prefer_manual }) => execute(async () => {
    const result = await service.getTranscriptArtifact(url, language, prefer_manual);
    return success(result, result.content);
  }),
);

const transport = new StdioServerTransport();
await server.connect(transport);
console.error("youtube-transcript-mcp-server running on stdio");
