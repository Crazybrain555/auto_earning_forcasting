export type SubtitleSource = "manual" | "automatic";

export interface SubtitleTrack {
  language: string;
  name: string;
  formats: string[];
}

export interface SubtitleInventory {
  video_id: string;
  title: string;
  url?: string;
  manual: SubtitleTrack[];
  automatic: SubtitleTrack[];
}

export interface SelectedSubtitleTrack {
  language: string;
  source: SubtitleSource;
}

export interface SearchVideo {
  id: string;
  title: string;
  url: string;
  channel?: string;
  duration_seconds?: number;
  upload_date?: string;
}

export interface SearchResult {
  count: number;
  offset: number;
  videos: SearchVideo[];
  has_more: boolean;
  next_offset?: number;
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

export function validateYouTubeUrl(value: string): boolean {
  try {
    const parsed = new URL(value);
    if (parsed.protocol !== "https:" && parsed.protocol !== "http:") return false;

    const hostname = parsed.hostname.toLowerCase();
    if (hostname === "youtu.be" || hostname === "www.youtu.be") {
      return parsed.pathname.split("/").filter(Boolean).length === 1;
    }

    const allowedHosts = new Set([
      "youtube.com",
      "www.youtube.com",
      "m.youtube.com",
      "music.youtube.com",
      "youtube-nocookie.com",
      "www.youtube-nocookie.com",
    ]);
    if (!allowedHosts.has(hostname)) return false;

    if (parsed.pathname === "/watch") return Boolean(parsed.searchParams.get("v"));
    return /^\/(shorts|live|embed)\/[^/]+\/?$/.test(parsed.pathname);
  } catch {
    return false;
  }
}

function parseTrackMap(value: unknown): SubtitleTrack[] {
  if (!isRecord(value)) return [];

  return Object.entries(value).map(([language, rawFormats]) => {
    const formatItems = Array.isArray(rawFormats) ? rawFormats : [];
    const formats = formatItems
      .map((item) => (isRecord(item) ? optionalString(item.ext) : undefined))
      .filter((extension): extension is string => Boolean(extension));
    const namedItem = formatItems.find(
      (item) => isRecord(item) && typeof item.name === "string" && item.name.length > 0,
    );
    const name = isRecord(namedItem) ? optionalString(namedItem.name) ?? language : language;
    return { language, name, formats: [...new Set(formats)] };
  });
}

export function parseSubtitleInventory(value: unknown): SubtitleInventory {
  const record = isRecord(value) ? value : {};
  return {
    video_id: optionalString(record.id) ?? "",
    title: optionalString(record.title) ?? "",
    ...(optionalString(record.webpage_url) ? { url: optionalString(record.webpage_url) } : {}),
    manual: parseTrackMap(record.subtitles),
    automatic: parseTrackMap(record.automatic_captions),
  };
}

export function selectSubtitleTrack(
  inventory: SubtitleInventory,
  language: string,
  preferManual: boolean,
): SelectedSubtitleTrack | undefined {
  const ordered: Array<[SubtitleSource, SubtitleTrack[]]> = preferManual
    ? [["manual", inventory.manual], ["automatic", inventory.automatic]]
    : [["automatic", inventory.automatic], ["manual", inventory.manual]];
  const desired = language.toLowerCase();

  for (const [source, tracks] of ordered) {
    const exact = tracks.find((track) => track.language.toLowerCase() === desired);
    if (exact) return { language: exact.language, source };
  }
  for (const [source, tracks] of ordered) {
    const compatible = tracks.find((track) => {
      const candidate = track.language.toLowerCase();
      return candidate.startsWith(`${desired}-`) || desired.startsWith(`${candidate}-`);
    });
    if (compatible) return { language: compatible.language, source };
  }
  return undefined;
}

export function buildSubtitleDownloadArgs(
  url: string,
  track: SelectedSubtitleTrack,
  outputTemplate: string,
): string[] {
  return [
    "--ignore-config",
    "--no-playlist",
    "--skip-download",
    track.source === "manual" ? "--write-subs" : "--write-auto-subs",
    "--sub-langs",
    track.language,
    "--sub-format",
    "vtt",
    "--output",
    outputTemplate,
    "--js-runtimes",
    "deno",
    url,
  ];
}

function decodeHtmlEntities(value: string): string {
  const named: Record<string, string> = {
    amp: "&",
    apos: "'",
    gt: ">",
    lt: "<",
    nbsp: " ",
    quot: '"',
  };
  return value.replace(/&(#x[0-9a-f]+|#\d+|[a-z]+);/gi, (match, entity: string) => {
    if (entity.startsWith("#x")) {
      return String.fromCodePoint(Number.parseInt(entity.slice(2), 16));
    }
    if (entity.startsWith("#")) {
      return String.fromCodePoint(Number.parseInt(entity.slice(1), 10));
    }
    return named[entity.toLowerCase()] ?? match;
  });
}

export function cleanVttTranscript(vtt: string): string {
  const output: string[] = [];
  for (const rawLine of vtt.replace(/\r/g, "").split("\n")) {
    const trimmed = rawLine.trim();
    if (
      !trimmed ||
      trimmed === "WEBVTT" ||
      /^(Kind|Language):/i.test(trimmed) ||
      /^(NOTE|STYLE|REGION)(\s|$)/.test(trimmed) ||
      /-->/.test(trimmed) ||
      /^\d+$/.test(trimmed)
    ) {
      continue;
    }

    const text = decodeHtmlEntities(trimmed.replace(/<[^>]+>/g, ""))
      .replace(/\s+/g, " ")
      .trim();
    if (text && output.at(-1) !== text) output.push(text);
  }
  return output.join("\n");
}

export function parseSearchResults(value: unknown, offset: number, limit: number): SearchResult {
  const record = isRecord(value) ? value : {};
  const entries = Array.isArray(record.entries) ? record.entries : [];
  const videos = entries
    .slice(offset, offset + limit)
    .filter(isRecord)
    .map((entry): SearchVideo | undefined => {
      const id = optionalString(entry.id);
      const title = optionalString(entry.title);
      if (!id || !title) return undefined;
      const rawUrl = optionalString(entry.webpage_url) ?? optionalString(entry.url);
      const url = rawUrl?.startsWith("http")
        ? rawUrl
        : `https://www.youtube.com/watch?v=${encodeURIComponent(id)}`;
      return {
        id,
        title,
        url,
        ...(optionalString(entry.channel) || optionalString(entry.uploader)
          ? { channel: optionalString(entry.channel) ?? optionalString(entry.uploader) }
          : {}),
        ...(optionalNumber(entry.duration) !== undefined
          ? { duration_seconds: optionalNumber(entry.duration) }
          : {}),
        ...(optionalString(entry.upload_date) ? { upload_date: optionalString(entry.upload_date) } : {}),
      };
    })
    .filter((video): video is SearchVideo => Boolean(video));
  const hasMore = entries.length > offset + limit;
  return {
    count: videos.length,
    offset,
    videos,
    has_more: hasMore,
    ...(hasMore ? { next_offset: offset + limit } : {}),
  };
}

export function safeCacheBasename(
  videoId: string,
  language: string,
  source: SubtitleSource,
  extension: string,
): string {
  const safePart = (value: string): string =>
    value.replace(/[^A-Za-z0-9_-]+/g, "_").replace(/^_+|_+$/g, "").slice(0, 80) || "unknown";
  const safeExtension = extension.replace(/[^A-Za-z0-9]/g, "").slice(0, 10) || "txt";
  return `${safePart(videoId)}.${safePart(language)}.${source}.${safeExtension}`;
}
