import { spawn } from "node:child_process";
import { accessSync, constants, statSync } from "node:fs";
import {
  mkdir,
  mkdtemp,
  readFile,
  readdir,
  rename,
  rm,
  writeFile,
} from "node:fs/promises";
import { homedir, tmpdir } from "node:os";
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
  type SelectedSubtitleTrack,
  type SubtitleInventory,
  type SubtitleSource,
} from "./ytdlp.js";

export interface YtDlpResult {
  stdout: string;
  stderr: string;
}

/**
 * Runners may return stdout alone. The record form additionally carries stderr,
 * which is required to diagnose the yt-dlp runs that exit 0 but write no subtitles.
 */
export type YtDlpRunner = (args: readonly string[]) => Promise<string | YtDlpResult>;

/**
 * How the server may spend the configured YouTube account cookies:
 * - "fallback": anonymous first, retry once with cookies when YouTube demands sign-in
 * - "always": send cookies on every player request (right when the egress IP is known-blocked)
 * - "never": never send cookies, even if a cookie source is configured
 */
export type CookieMode = "fallback" | "always" | "never";

export interface YtDlpServiceOptions {
  runner?: YtDlpRunner;
  cacheDir?: string;
  maxContentChars?: number;
  cookiesFromBrowser?: string;
  cookiesFile?: string;
  cookieMode?: CookieMode;
  sleepRequests?: number;
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

function normalizeResult(value: string | YtDlpResult): YtDlpResult {
  return typeof value === "string" ? { stdout: value, stderr: "" } : value;
}

/**
 * yt-dlp exits 0 when it silently drops a caption track, so a missing VTT is ambiguous.
 * The PO-token case is the misleading one: YouTube withholds the track and yt-dlp reports
 * it at debug level for its default clients, which otherwise reads as "no captions exist".
 */
function describeMissingSubtitle(track: SelectedSubtitleTrack, output: string): string {
  if (/po token/i.test(output)) {
    return `YouTube demanded a PO token for the '${track.language}' (${track.source}) caption track, so yt-dlp discarded it. The track exists; this is a YouTube-side restriction. Note that YouTube Premium sessions always require a PO token for subtitles, so a non-Premium cookie source usually avoids this.`;
  }
  if (/no subtitles for the requested languages/i.test(output)) {
    return `yt-dlp found no '${track.language}' subtitles even though the track was listed. Re-check with youtube_list_subtitle_languages; the track may have been withdrawn since.`;
  }
  return `yt-dlp did not produce a VTT file for '${track.language}' (${track.source}).`;
}

/**
 * Resolves and sanity-checks a Netscape cookie jar path. yt-dlp's YouTube guidance
 * mandates a file exported from a throwaway account's private-window session rather
 * than live browser cookies, which YouTube rotates while a YouTube tab stays open.
 */
function resolveCookiesFile(candidate: string): string {
  const resolved = candidate.startsWith("~/")
    ? path.join(homedir(), candidate.slice(2))
    : path.resolve(candidate);

  let stats;
  try {
    stats = statSync(resolved);
  } catch {
    throw new Error(`YOUTUBE_COOKIES_FILE does not exist: ${resolved}`);
  }
  if (!stats.isFile()) {
    throw new Error(`YOUTUBE_COOKIES_FILE is not a regular file: ${resolved}`);
  }
  try {
    accessSync(resolved, constants.R_OK);
  } catch {
    throw new Error(`YOUTUBE_COOKIES_FILE is not readable: ${resolved}`);
  }
  if ((stats.mode & 0o077) !== 0) {
    console.error(
      `youtube-transcript MCP: ${resolved} is group/world readable. Run 'chmod 600' on it.`,
    );
  }
  return resolved;
}

function parseCookieMode(value: string | undefined): CookieMode {
  if (value === undefined || value === "") return "fallback";
  if (value === "fallback" || value === "always" || value === "never") return value;
  throw new Error(
    `Invalid YOUTUBE_COOKIE_MODE '${value}'. Use 'fallback', 'always', or 'never'.`,
  );
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

export function isSignInChallenge(output: string): boolean {
  return /sign in to confirm you.?re not a bot|confirm your age|this video is only available to/i
    .test(output);
}

export class YtDlpError extends Error {
  readonly signInChallenge: boolean;

  constructor(message: string, signInChallenge: boolean) {
    super(message);
    this.name = "YtDlpError";
    this.signInChallenge = signInChallenge;
  }
}

function actionableYtDlpError(output: string, cookiesAttempted: boolean): YtDlpError {
  if (isSignInChallenge(output)) {
    return new YtDlpError(
      cookiesAttempted
        ? "YouTube rejected the request even with the configured cookies. The cookie file is most likely expired — re-export it (see the MCP README), or the egress IP has been blocked outright."
        : "YouTube blocked anonymous access from this egress IP. Configure YOUTUBE_COOKIES_FILE (see the MCP README) or route this host through an IP YouTube has not flagged.",
      true,
    );
  }
  if (/requested format is not available|no subtitles/i.test(output)) {
    return new YtDlpError(
      "The requested public subtitle track is not available for this video.",
      false,
    );
  }
  const concise = output.trim().split("\n").slice(-6).join("\n");
  return new YtDlpError(`yt-dlp failed: ${concise || "unknown error"}`, false);
}

export async function runYtDlpCommand(args: readonly string[]): Promise<YtDlpResult> {
  const configuredTimeout = Number.parseInt(process.env.YOUTUBE_MCP_TIMEOUT_MS ?? "180000", 10);
  const timeoutMs = Number.isFinite(configuredTimeout) && configuredTimeout > 0
    ? configuredTimeout
    : 180_000;
  const cookiesAttempted = args.includes("--cookies") || args.includes("--cookies-from-browser");

  return new Promise<YtDlpResult>((resolve, reject) => {
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
        if (code === 0) resolve({ stdout, stderr });
        else reject(actionableYtDlpError(`${stderr}\n${stdout}`, cookiesAttempted));
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
  const configuredCookiesFile = options.cookiesFile ?? process.env.YOUTUBE_COOKIES_FILE;
  if (configuredCookiesFile && cookiesFromBrowser) {
    throw new Error("Set either YOUTUBE_COOKIES_FILE or YOUTUBE_COOKIES_FROM_BROWSER, not both.");
  }
  const cookiesFile = configuredCookiesFile ? resolveCookiesFile(configuredCookiesFile) : undefined;
  const cookieMode = options.cookieMode ?? parseCookieMode(process.env.YOUTUBE_COOKIE_MODE);
  const cookiesUsable = Boolean(cookiesFile ?? cookiesFromBrowser) && cookieMode !== "never";

  const configuredSleep = Number.parseFloat(process.env.YOUTUBE_MCP_SLEEP_REQUESTS ?? "0.75");
  const sleepRequests = options.sleepRequests
    ?? (Number.isFinite(configuredSleep) && configuredSleep >= 0 ? configuredSleep : 0.75);

  const cookieArgs = (): string[] => {
    if (cookiesFile) return ["--cookies", cookiesFile];
    if (cookiesFromBrowser) return ["--cookies-from-browser", "chrome"];
    return [];
  };

  const commonArgs = (useCookies: boolean): string[] => [
    "--ignore-config",
    "--js-runtimes",
    "deno",
    ...(sleepRequests > 0 ? ["--sleep-requests", String(sleepRequests)] : []),
    ...(useCookies ? cookieArgs() : []),
  ];

  /**
   * Runs one yt-dlp invocation, spending account cookies only as the mode allows.
   * "always" sends them on the first player attempt, because when the egress IP is
   * already blocked the anonymous attempt is a guaranteed round trip to a sign-in
   * challenge. Search stays anonymous-first in every mode: the search endpoint is not
   * gated like the player endpoint, so cookies there would add account exposure for
   * nothing.
   */
  const run = async (
    buildArgs: (useCookies: boolean) => string[],
    kind: "search" | "player",
  ): Promise<YtDlpResult> => {
    const cookiesFirst = cookiesUsable && cookieMode === "always" && kind === "player";
    try {
      return normalizeResult(await runner(buildArgs(cookiesFirst)));
    } catch (error) {
      const challenged = error instanceof YtDlpError && error.signInChallenge;
      if (!challenged || cookiesFirst || !cookiesUsable) throw error;
      return normalizeResult(await runner(buildArgs(true)));
    }
  };

  const getRawMetadata = async (url: string): Promise<UnknownRecord> => {
    if (!validateYouTubeUrl(url)) {
      throw new Error("Invalid YouTube video URL. Use a youtube.com or youtu.be video URL.");
    }
    const { stdout } = await run((useCookies) => [
      ...commonArgs(useCookies),
      "--no-playlist",
      "--skip-download",
      "--dump-single-json",
      url,
    ], "player");
    return parseJsonRecord(stdout);
  };

  const searchVideos = async (
    query: string,
    maxResults: number,
    offset: number,
  ): Promise<SearchResult> => {
    const fetchCount = Math.min(100, offset + maxResults + 1);
    const { stdout } = await run((useCookies) => [
      ...commonArgs(useCookies),
      "--flat-playlist",
      "--skip-download",
      "--dump-single-json",
      `ytsearch${fetchCount}:${query}`,
    ], "search");
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
      // --verbose costs no extra request but is the only way to see a PO-token track drop,
      // which yt-dlp otherwise logs at debug level for its default clients.
      const { stdout, stderr } = await run(
        (useCookies) => buildSubtitleDownloadArgs(url, selected, outputTemplate, [
          ...commonArgs(useCookies),
          "--verbose",
        ]),
        "player",
      );

      const subtitleFile = (await readdir(tempDir)).sort().find((name) => name.endsWith(".vtt"));
      if (!subtitleFile) {
        throw new Error(describeMissingSubtitle(selected, `${stderr}\n${stdout}`));
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
