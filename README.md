# yt-uploader — GitHub Actions YouTube upload infrastructure

Each upload runs on a **fresh GitHub-hosted runner with a different public IP**,
so the five channels never share an upload IP. No server, no RDP — just
cron-triggered jobs.

## Repo secrets (Settings → Secrets and variables → Actions)

| Secret | Content |
|---|---|
| `YT_CLIENTS_JSON` | `{"<label>": {"client_id": "...", "client_secret": "..."}, ...}` — one OAuth Desktop client per channel, each from that channel's **own GCP project** |
| `YT_TOKENS_JSON` | `{"<label>": {"refresh_token": "..."}, ...}` — one refresh token per channel, minted under its own project with the `https://www.googleapis.com/auth/youtube` scope |

Labels: `hidden-history-files`, `oldgold`, `story-atlas`, `past-present`, `tech-atlas`.

## Workflows

- **Upload video to YouTube** (`upload.yml`) — `workflow_dispatch` inputs: `label`,
  `video_url` (direct MP4 download, e.g. R2 signed URL), `title`, `description`,
  `tags`, `thumbnail_url`, `privacy` (default `unlisted`). Downloads, uploads with
  resumable chunks, sets the thumbnail, prints `RESULT_VIDEO_ID=<id>` (masked in logs).
- **Publish video** (`publish.yml`) — inputs: `label`, `video_id`, `privacy`
  (default `public`). Flips visibility; prints `ALREADY_PUBLIC` if nothing to do.

One job per channel at a time (`concurrency` groups); extra dispatches queue.

## Dispatching (from the production machine)

```bash
curl -X POST \
  -H "Authorization: Bearer $GH_PAT" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/OWNER/yt-uploader/actions/workflows/upload.yml/dispatches \
  -d '{"ref":"main","inputs":{"label":"oldgold","video_url":"https://...","title":"...","description":"...","tags":"a,b","thumbnail_url":"https://...","privacy":"unlisted"}}'
```

Poll the run via the Actions API and grep its logs for `RESULT_VIDEO_ID=`.

## Why this is safe

- Every channel has its **own GCP project + OAuth client + Gmail**. A strike on one
  cannot cascade through a shared project.
- Secrets are encrypted; workflow runs each get a fresh Azure IP.
- Repo is public (unlimited free Actions minutes); video IDs are masked in logs.
