import { spawn } from "node:child_process";
import {
  mkdir,
  mkdtemp,
  readFile,
  readdir,
  rename,
  rm,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import path from "node:path";

import {
  buildSubtitleDownloadArgs,
  cleanVttTranscript,
  parseSearchResults,
  parseSubtitleInventory,
  safeCacheBasename,
  selectSubtitleTrack,
  validateYouTubeUrl,
  type SearchResult,
  type SearchVideo,
  type SubtitleInventory,
  type SubtitleSource,
} from "./ytdlp.js";

export type YtDlpRunner = (args: readonly string[]) => Promise<string>;

export interface YtDlpServiceOptions {
  runner?: YtDlpRunner;
  cacheDir?: string;
  maxContentChars?: number;
  cookiesFromBrowser?: string;
}

export interface VideoMetadata {
  id: string;
  title: string;
  url?: string;
  channel?: string;
  channel_id?: string;
  duration_seconds?: number;
  upload_date?: string;
  view_count?: number;
  like_count?: number;
  description?: string;
  live_status?: string;
  manual_subtitle_languages: string[];
  automatic_subtitle_languages: string[];
  has_public_subtitles: boolean;
}

export interface SubtitleArtifact {
  video_id: string;
  title: string;
  url?: string;
  language: string;
  source: SubtitleSource;
  format: "vtt";
  saved_path: string;
  character_count: number;
  content: string;
  content_truncated: boolean;
}

export interface TranscriptArtifact {
  video_id: string;
  title: string;
  url?: string;
  language: string;
  source: SubtitleSource;
  format: "txt";
  saved_path: string;
  character_count: number;
  content: string;
  content_truncated: boolean;
}

export interface CaptionedSearchVideo extends SearchVideo {
  subtitle_language: string;
  subtitle_source: SubtitleSource;
}

export interface CaptionedSearchResult {
  count: number;
  inspected: number;
  videos: CaptionedSearchVideo[];
  skipped_errors: Array<{ id: string; error: string }>;
}

export interface YtDlpService {
  searchVideos(query: string, maxResults: number, offset: number): Promise<SearchResult>;
  getVideoMetadata(url: string): Promise<VideoMetadata>;
  listSubtitleLanguages(url: string): Promise<SubtitleInventory>;
  getSubtitleArtifact(
    url: string,
    language: string,
    preferManual: boolean,
  ): Promise<SubtitleArtifact>;
  getTranscriptArtifact(
    url: string,
    language: string,
    preferManual: boolean,
  ): Promise<TranscriptArtifact>;
  searchCaptionedVideos(
    query: string,
    language: string,
    maxResults: number,
    maxCandidates: number,
  ): Promise<CaptionedSearchResult>;
}

type UnknownRecord = Record<string, unknown>;

function isRecord(value: unknown): value is UnknownRecord {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function optionalString(value: unknown): string | undefined {
  return typeof value === "string" && value.length > 0 ? value : undefined;
}

function optionalNumber(value: unknown): number | undefined {
  return typeof value === "number" && Number.isFinite(value) ? value : undefined;
}

function parseJsonRecord(stdout: string): UnknownRecord {
  let parsed: unknown;
  try {
    parsed = JSON.parse(stdout);
  } catch {
    throw new Error("yt-dlp returned invalid JSON. Update yt-dlp and retry.");
  }
  if (!isRecord(parsed)) throw new Error("yt-dlp returned an unexpected JSON value.");
  return parsed;
}

function actionableYtDlpError(stderr: string): Error {
  if (/sign in to confirm you.?re not a bot/i.test(stderr)) {
    return new Error(
      "YouTube blocked anonymous access. With explicit permission, enable the project's Chrome cookie mode and retry.",
    );
  }
  if (/requested format is not available|no subtitles/i.test(stderr)) {
    return new Error("The requested public subtitle track is not available for this video.");
  }
  const concise = stderr.trim().split("\n").slice(-6).join("\n");
  return new Error(`yt-dlp failed: ${concise || "unknown error"}`);
}

export async function runYtDlpCommand(args: readonly string[]): Promise<string> {
  const configuredTimeout = Number.parseInt(process.env.YOUTUBE_MCP_TIMEOUT_MS ?? "180000", 10);
  const timeoutMs = Number.isFinite(configuredTimeout) && configuredTimeout > 0
    ? configuredTimeout
    : 180_000;

  return new Promise<string>((resolve, reject) => {
    const child = spawn("yt-dlp", [...args], {
      shell: false,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    let settled = false;
    const finish = (action: () => void): void => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      action();
    };
    const appendWithLimit = (current: string, chunk: Buffer): string => {
      const next = current + chunk.toString("utf8");
      if (next.length > 20_000_000) {
        child.kill("SIGTERM");
        finish(() => reject(new Error("yt-dlp output exceeded the 20 MB safety limit.")));
      }
      return next;
    };
    const timer = setTimeout(() => {
      child.kill("SIGTERM");
      finish(() => reject(new Error(`yt-dlp timed out after ${timeoutMs} ms.`)));
    }, timeoutMs);

    child.stdout.on("data", (chunk: Buffer) => {
      stdout = appendWithLimit(stdout, chunk);
    });
    child.stderr.on("data", (chunk: Buffer) => {
      stderr = appendWithLimit(stderr, chunk);
    });
    child.on("error", (error) => {
      finish(() => {
        if ((error as NodeJS.ErrnoException).code === "ENOENT") {
          reject(new Error("yt-dlp is not installed or is not on PATH."));
        } else {
          reject(error);
        }
      });
    });
    child.on("close", (code) => {
      finish(() => {
        if (code === 0) resolve(stdout);
        else reject(actionableYtDlpError(`${stderr}\n${stdout}`));
      });
    });
  });
}

function metadataFromRecord(record: UnknownRecord): VideoMetadata {
  const inventory = parseSubtitleInventory(record);
  return {
    id: optionalString(record.id) ?? "",
    title: optionalString(record.title) ?? "",
    ...(optionalString(record.webpage_url) ? { url: optionalString(record.webpage_url) } : {}),
    ...(optionalString(record.channel) || optionalString(record.uploader)
      ? { channel: optionalString(record.channel) ?? optionalString(record.uploader) }
      : {}),
    ...(optionalString(record.channel_id) ? { channel_id: optionalString(record.channel_id) } : {}),
    ...(optionalNumber(record.duration) !== undefined
      ? { duration_seconds: optionalNumber(record.duration) }
      : {}),
    ...(optionalString(record.upload_date) ? { upload_date: optionalString(record.upload_date) } : {}),
    ...(optionalNumber(record.view_count) !== undefined
      ? { view_count: optionalNumber(record.view_count) }
      : {}),
    ...(optionalNumber(record.like_count) !== undefined
      ? { like_count: optionalNumber(record.like_count) }
      : {}),
    ...(optionalString(record.description)
      ? { description: optionalString(record.description)?.slice(0, 10_000) }
      : {}),
    ...(optionalString(record.live_status) ? { live_status: optionalString(record.live_status) } : {}),
    manual_subtitle_languages: inventory.manual.map((track) => track.language),
    automatic_subtitle_languages: inventory.automatic.map((track) => track.language),
    has_public_subtitles: inventory.manual.length > 0 || inventory.automatic.length > 0,
  };
}

export function createYtDlpService(options: YtDlpServiceOptions = {}): YtDlpService {
  const runner = options.runner ?? runYtDlpCommand;
  const cacheDir = options.cacheDir
    ?? process.env.YOUTUBE_TRANSCRIPT_CACHE_DIR
    ?? path.resolve(process.cwd(), ".cache", "youtube-transcripts");
  const configuredMax = Number.parseInt(
    process.env.YOUTUBE_MCP_MAX_CONTENT_CHARS ?? "200000",
    10,
  );
  const maxContentChars = options.maxContentChars
    ?? (Number.isFinite(configuredMax) && configuredMax > 0 ? configuredMax : 200_000);
  const cookiesFromBrowser = options.cookiesFromBrowser
    ?? process.env.YOUTUBE_COOKIES_FROM_BROWSER;
  if (cookiesFromBrowser && cookiesFromBrowser !== "chrome") {
    throw new Error("Only the Chrome browser cookie source is supported by this project MCP.");
  }

  const commonArgs = (): string[] => [
    "--ignore-config",
    "--js-runtimes",
    "deno",
    ...(cookiesFromBrowser ? ["--cookies-from-browser", "chrome"] : []),
  ];

  const getRawMetadata = async (url: string): Promise<UnknownRecord> => {
    if (!validateYouTubeUrl(url)) {
      throw new Error("Invalid YouTube video URL. Use a youtube.com or youtu.be video URL.");
    }
    const stdout = await runner([
      ...commonArgs(),
      "--no-playlist",
      "--skip-download",
      "--dump-single-json",
      url,
    ]);
    return parseJsonRecord(stdout);
  };

  const searchVideos = async (
    query: string,
    maxResults: number,
    offset: number,
  ): Promise<SearchResult> => {
    const fetchCount = Math.min(100, offset + maxResults + 1);
    const stdout = await runner([
      ...commonArgs(),
      "--flat-playlist",
      "--skip-download",
      "--dump-single-json",
      `ytsearch${fetchCount}:${query}`,
    ]);
    return parseSearchResults(parseJsonRecord(stdout), offset, maxResults);
  };

  const listSubtitleLanguages = async (url: string): Promise<SubtitleInventory> =>
    parseSubtitleInventory(await getRawMetadata(url));

  const getSubtitleArtifact = async (
    url: string,
    language: string,
    preferManual: boolean,
  ): Promise<SubtitleArtifact> => {
    const inventory = await listSubtitleLanguages(url);
    const selected = selectSubtitleTrack(inventory, language, preferManual);
    if (!selected) {
      throw new Error(
        `No public subtitle track matching '${language}'. Call youtube_list_subtitle_languages first.`,
      );
    }

    const tempDir = await mkdtemp(path.join(tmpdir(), "youtube-transcript-mcp-"));
    try {
      const outputTemplate = path.join(tempDir, "subtitle.%(ext)s");
      const baseArgs = buildSubtitleDownloadArgs(url, selected, outputTemplate);
      const downloadArgs = cookiesFromBrowser
        ? [
            ...baseArgs.slice(0, -1),
            "--cookies-from-browser",
            "chrome",
            baseArgs.at(-1)!,
          ]
        : baseArgs;
      await runner(downloadArgs);

      const subtitleFile = (await readdir(tempDir)).sort().find((name) => name.endsWith(".vtt"));
      if (!subtitleFile) {
        throw new Error(
          `yt-dlp did not produce a VTT file for '${selected.language}' (${selected.source}).`,
        );
      }
      const fullContent = await readFile(path.join(tempDir, subtitleFile), "utf8");
      await mkdir(cacheDir, { recursive: true });
      const savedPath = path.join(
        cacheDir,
        safeCacheBasename(inventory.video_id, selected.language, selected.source, "vtt"),
      );
      const atomicPath = `${savedPath}.${process.pid}.tmp`;
      await writeFile(atomicPath, fullContent, "utf8");
      await rename(atomicPath, savedPath);

      return {
        video_id: inventory.video_id,
        title: inventory.title,
        ...(inventory.url ? { url: inventory.url } : {}),
        language: selected.language,
        source: selected.source,
        format: "vtt",
        saved_path: savedPath,
        character_count: fullContent.length,
        content: fullContent.slice(0, maxContentChars),
        content_truncated: fullContent.length > maxContentChars,
      };
    } finally {
      await rm(tempDir, { recursive: true, force: true });
    }
  };

  const searchCaptionedVideos = async (
    query: string,
    language: string,
    maxResults: number,
    maxCandidates: number,
  ): Promise<CaptionedSearchResult> => {
    const search = await searchVideos(query, maxCandidates, 0);
    const videos: CaptionedSearchVideo[] = [];
    const skippedErrors: Array<{ id: string; error: string }> = [];

    for (const candidate of search.videos) {
      if (videos.length >= maxResults) break;
      try {
        const inventory = await listSubtitleLanguages(candidate.url);
        const selected = selectSubtitleTrack(inventory, language, true);
        if (selected) {
          videos.push({
            ...candidate,
            subtitle_language: selected.language,
            subtitle_source: selected.source,
          });
        }
      } catch (error) {
        skippedErrors.push({
          id: candidate.id,
          error: error instanceof Error ? error.message : String(error),
        });
      }
    }

    return {
      count: videos.length,
      inspected: Math.min(search.videos.length, maxCandidates),
      videos,
      skipped_errors: skippedErrors,
    };
  };

  const getTranscriptArtifact = async (
    url: string,
    language: string,
    preferManual: boolean,
  ): Promise<TranscriptArtifact> => {
    const subtitle = await getSubtitleArtifact(url, language, preferManual);
    const fullVtt = await readFile(subtitle.saved_path, "utf8");
    const fullContent = cleanVttTranscript(fullVtt);
    const savedPath = path.join(
      cacheDir,
      safeCacheBasename(subtitle.video_id, subtitle.language, subtitle.source, "txt"),
    );
    const atomicPath = `${savedPath}.${process.pid}.tmp`;
    await writeFile(atomicPath, fullContent, "utf8");
    await rename(atomicPath, savedPath);
    return {
      video_id: subtitle.video_id,
      title: subtitle.title,
      ...(subtitle.url ? { url: subtitle.url } : {}),
      language: subtitle.language,
      source: subtitle.source,
      format: "txt",
      saved_path: savedPath,
      character_count: fullContent.length,
      content: fullContent.slice(0, maxContentChars),
      content_truncated: fullContent.length > maxContentChars,
    };
  };

  return {
    searchVideos,
    getVideoMetadata: async (url: string): Promise<VideoMetadata> =>
      metadataFromRecord(await getRawMetadata(url)),
    listSubtitleLanguages,
    getSubtitleArtifact,
    getTranscriptArtifact,
    searchCaptionedVideos,
  };
}
