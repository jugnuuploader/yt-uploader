#!/usr/bin/env python3
"""Upload a video file to YouTube via Data API v3 using per-channel OAuth tokens.

Reads credentials from env (GitHub Secrets):
  YT_CLIENTS_JSON  - {"<label>": {"client_id":..., "client_secret":...}, ...}
  YT_TOKENS_JSON   - {"<label>": {"refresh_token":...}, ...}

Prints RESULT_VIDEO_ID=<id> on success (caller masks it in logs).
"""
import argparse, json, os, sys

import requests
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

TOKEN_URL = "https://oauth2.googleapis.com/token"


def get_service(label):
    clients = json.loads(os.environ["YT_CLIENTS_JSON"])
    tokens = json.loads(os.environ["YT_TOKENS_JSON"])
    if label not in clients or label not in tokens:
        raise RuntimeError("no credentials for label '%s'" % label)
    c = clients[label]
    creds = Credentials(
        token=None,
        refresh_token=tokens[label]["refresh_token"],
        client_id=c["client_id"],
        client_secret=c["client_secret"],
        token_uri=TOKEN_URL,
        scopes=["https://www.googleapis.com/auth/youtube"],
    )
    creds.refresh(Request())
    return build("youtube", "v3", credentials=creds)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--label", required=True)
    p.add_argument("--video", required=True)
    p.add_argument("--title", required=True)
    p.add_argument("--description", default="")
    p.add_argument("--tags", default="")
    p.add_argument("--thumbnail", default="")
    p.add_argument("--privacy", default="unlisted",
                   choices=["private", "unlisted", "public"])
    a = p.parse_args()

    yt = get_service(a.label)
    body = {
        "snippet": {
            "title": a.title,
            "description": a.description,
            "tags": [t.strip() for t in a.tags.split(",") if t.strip()],
            "categoryId": "27",
        },
        "status": {
            "privacyStatus": a.privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(a.video, chunksize=8 * 1024 * 1024, resumable=True)
    req = yt.videos().insert(part="snippet,status", body=body, media_body=media)
    resp = None
    while resp is None:
        status, resp = req.next_chunk()
    vid = resp["id"]

    if a.thumbnail and os.path.exists(a.thumbnail):
        try:
            yt.thumbnails().set(videoId=vid, media_body=MediaFileUpload(
                a.thumbnail, mimetype="image/png")).execute()
            print("thumbnail set OK", flush=True)
        except Exception as e:
            # Non-fatal: video is already uploaded. Thumbnail 429s are common;
            # the hourly health check retries missing thumbnails.
            print("THUMBNAIL_FAILED (non-fatal): %s" % str(e)[:200], flush=True)

    # Mask the ID in CI logs, then emit it for the poller.
    print("::add-mask::%s" % vid)
    print("RESULT_VIDEO_ID=%s" % vid, flush=True)


if __name__ == "__main__":
    main()
