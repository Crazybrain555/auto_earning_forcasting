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

## Authentication when YouTube blocks anonymous access

YouTube challenges the *player* endpoint with “Sign in to confirm you're not a bot” when it
distrusts the egress IP. Search is not gated the same way, so `youtube_search_videos` usually
keeps working while metadata and subtitles fail. Switching `player_client` does not help — the
block is on the IP, not the client — and neither does `--impersonate`.

There are only two real remedies: **use an IP YouTube has not flagged**, or **present cookies**.

### Preferred: a cookie file from a throwaway account

yt-dlp's YouTube guidance is explicit that live browser cookies are the wrong source: YouTube
rotates the session while a YouTube tab is open, so `--cookies-from-browser` often hands over an
already-invalidated session. It also warns that using an account with yt-dlp risks that account
being banned, and recommends a throwaway.

Export the jar exactly as the yt-dlp wiki prescribes, using an account you are willing to lose:

1. Open a **private/incognito window** and log into YouTube.
2. In that same tab, navigate to `https://www.youtube.com/robots.txt`. It must be the only
   private tab open.
3. Export `youtube.com` cookies with the **“Get cookies.txt LOCALLY”** extension. Do not use the
   similarly named “Get cookies.txt” — it was removed from the Chrome Web Store as malware.
4. **Close the private window** so the session is never reopened and therefore never rotated.

Install the jar outside the repository, readable only by you:

```bash
mkdir -p ~/.config/youtube-transcript-mcp
mv ~/Downloads/www.youtube.com_cookies.txt ~/.config/youtube-transcript-mcp/cookies.txt
chmod 600 ~/.config/youtube-transcript-mcp/cookies.txt
```

The launcher picks that path up automatically — no shell configuration is needed. The server
passes only `--cookies <path>` to `yt-dlp`; it never reads, prints, copies, or re-exports the
contents.

> **Do not use a YouTube Premium account.** Premium sessions are *required* to supply a PO token
> for subtitles, so Premium cookies make caption tracks harder to fetch, not easier.

### Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `YOUTUBE_COOKIES_FILE` | `~/.config/youtube-transcript-mcp/cookies.txt` if present | Netscape cookie jar passed as `--cookies`. |
| `YOUTUBE_COOKIE_MODE` | `always` when a jar is configured, else `fallback` | `fallback` tries anonymous first and retries with cookies only on a sign-in challenge; `always` sends cookies on the first player request; `never` disables them entirely. |
| `YOUTUBE_COOKIES_FROM_BROWSER` | unset | Legacy `--cookies-from-browser chrome` mode. Mutually exclusive with `YOUTUBE_COOKIES_FILE`, and discouraged for the rotation reason above. |
| `YOUTUBE_MCP_SLEEP_REQUESTS` | `0.75` | `--sleep-requests` value. yt-dlp documents a ceiling near 300 videos/hour for guest sessions. |

Search always tries anonymously first regardless of mode, so a working search costs no account
exposure.

### When cookies stop working

Cookie jars expire. The server distinguishes the cases: a challenge *with* cookies attached
reports that the jar is likely expired, while a challenge without them points at the IP. Re-run
the export above to refresh. If a caption track goes missing rather than erroring, the server
reports whether YouTube withheld it for a PO token, which otherwise looks identical to a video
that simply has no captions.

## Checks

```bash
npm test
npm run typecheck
npm run build
```
