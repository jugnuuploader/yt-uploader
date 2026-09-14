#!/usr/bin/env python3
"""Flip a video's visibility (e.g. unlisted -> public) via Data API v3.

Env: YT_CLIENTS_JSON, YT_TOKENS_JSON (same shape as yt_upload.py).
"""
import argparse, json, os

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_URL = "https://oauth2.googleapis.com/token"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--label", required=True)
    p.add_argument("--video-id", required=True)
    p.add_argument("--privacy", default="public",
                   choices=["private", "unlisted", "public"])
    a = p.parse_args()

    clients = json.loads(os.environ["YT_CLIENTS_JSON"])
    tokens = json.loads(os.environ["YT_TOKENS_JSON"])
    c = clients[a.label]
    creds = Credentials(
        token=None,
        refresh_token=tokens[a.label]["refresh_token"],
        client_id=c["client_id"],
        client_secret=c["client_secret"],
        token_uri=TOKEN_URL,
        scopes=["https://www.googleapis.com/auth/youtube"],
    )
    creds.refresh(Request())
    yt = build("youtube", "v3", credentials=creds)

    cur = yt.videos().list(part="status", id=a.video_id).execute()
    items = cur.get("items", [])
    if not items:
        raise RuntimeError("video not found: %s" % a.video_id)
    if items[0]["status"]["privacyStatus"] == a.privacy:
        print("ALREADY_%s" % a.privacy.upper())
        return
    yt.videos().update(
        part="status",
        body={"id": a.video_id,
              "status": {"privacyStatus": a.privacy,
                         "selfDeclaredMadeForKids": False}}).execute()
    print("FLIPPED_TO_%s" % a.privacy.upper())


if __name__ == "__main__":
    main()
