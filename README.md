# yt-uploader — GitHub Actions YouTube upload infrastructure

Each upload runs on a **fresh GitHub-hosted runner with a different public IP**,
so the five channels never share an upload IP. No server, no RDP — just
cron-triggered jobs.

## Repo secrets (Settings → Secrets and variables → Actions)

| Secret | Content |
|---|---|
| `YT_CLIENTS_JSON` | `{"<label>": {"client_id": "...", "client_secret": "..."}, ...}` — one OAuth Desktop client per channel, each from that channel's **own GCP project** |
| `YT_TOKENS_JSON` | `{"<label>": {"refresh_token": "..."}, ...}` — one refresh token per channel, minted under its own project with the `https://www.googleapis.com/auth/youtube` scope |
| `YT_URL_KEY` | Fernet key (base64, 44 chars) used to encrypt download URLs — the repo is **public**, so raw MP4/thumbnail URLs must never appear as workflow inputs |

Labels: `hidden-history-files`, `oldgold`, `story-atlas`, `past-present`, `tech-atlas`.

## Workflows

- **Upload video to YouTube** (`upload.yml`) — `workflow_dispatch` inputs: `label`,
  `video_url_enc` (Fernet-encrypted direct MP4 download URL), `title`, `description`,
  `tags`, `thumbnail_url_enc` (Fernet-encrypted thumbnail PNG URL, optional),
  `privacy` (default `unlisted`). The workflow decrypts the URLs in an early step
  (never echoed or logged), downloads, uploads with resumable chunks, sets the
  thumbnail, prints `RESULT_VIDEO_ID=<id>` (masked in logs).
- **Publish video** (`publish.yml`) — inputs: `label`, `video_id`, `privacy`
  (default `public`). Flips visibility; prints `ALREADY_PUBLIC` if nothing to do.

One job per channel at a time (`concurrency` groups); extra dispatches queue.

## Dispatching (from the production machine)

`video_url` / `thumbnail_url` are **never sent in the clear** — encrypt them with
the `YT_URL_KEY` Fernet key first (the key lives in the production machine's
secrets store, same place as the GitHub PAT):

```python
from cryptography.fernet import Fernet
f = Fernet(YT_URL_KEY.encode())          # YT_URL_KEY from the secrets store
video_url_enc = f.encrypt(b"https://direct-link/video.mp4").decode()
thumb_url_enc = f.encrypt(b"https://direct-link/thumb.png").decode()
```

```bash
curl -X POST \
  -H "Authorization: Bearer $GH_PAT" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/jugnuuploader/yt-uploader/actions/workflows/upload.yml/dispatches \
  -d "$(jq -n --arg v "$video_url_enc" --arg t "$thumb_url_enc" '{
        ref: "main",
        inputs: {
          label: "tech-atlas",
          video_url_enc: $v,
          title: "...",
          description: "...",
          tags: "a,b",
          thumbnail_url_enc: $t,
          privacy: "unlisted"
        }
      }')"
```

Poll the run via the Actions API and grep its logs for `RESULT_VIDEO_ID=`.

## Why this is safe

- Every channel has its **own GCP project + OAuth client + Gmail**. A strike on one
  cannot cascade through a shared project.
- Secrets are encrypted; workflow runs each get a fresh Azure IP.
- Repo is public (unlimited free Actions minutes); video IDs are masked in logs.
