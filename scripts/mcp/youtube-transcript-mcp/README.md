# YouTube public-subtitle MCP

Project-scoped MCP server for YouTube research. It can search public videos, inspect focused metadata, identify public caption tracks, save timestamped WebVTT, and derive clean text from those captions.

It intentionally has no video download, audio download, or speech-to-text tool.

## Runtime setup

Prerequisites:

- Node.js 20 or newer
- `yt-dlp`
- Deno, used by `yt-dlp` for YouTube JavaScript challenges

Install the pinned Node dependencies and build:

```bash
cd scripts/mcp/youtube-transcript-mcp
npm ci
npm run build
```

The shared launcher is `scripts/mcp/youtube-transcript.sh`. It stores complete `.vtt` and `.txt` files under the repository's ignored `.cache/youtube-transcripts/` directory.

## Tools

- `youtube_search_videos`
- `youtube_search_captioned_videos`
- `youtube_get_video_metadata`
- `youtube_list_subtitle_languages`
- `youtube_get_subtitles`
- `youtube_get_transcript`

`youtube_get_subtitles` preserves timestamps. `youtube_get_transcript` removes subtitle timing/markup for reading, but does not transcribe audio.

## Optional Chrome authentication

Anonymous YouTube access may be challenged with “Sign in to confirm you're not a bot.” After explicit user authorization, set:

```bash
export YOUTUBE_COOKIES_FROM_BROWSER=chrome
```

The server passes only `--cookies-from-browser chrome` to `yt-dlp`. It never exports, prints, or stores browser cookies. Browser-cookie access is sensitive: use it only with the account owner's approval, keep request volumes low, and consider a dedicated Chrome profile for research.

## Checks

```bash
npm test
npm run typecheck
npm run build
```
