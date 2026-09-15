"""Submit a YouTube playlist to the TranscriptBatch API and save the JSON export.

Stdlib only. Reads the API key from TRANSCRIPTBATCH_API_KEY.

Usage:
    python playlist_to_json.py "https://www.youtube.com/playlist?list=PLxxxx"
"""

import json
import sys
import time
import urllib.parse
import urllib.request
import uuid

BASE_URL = "https://transcriptapiyt.com"


def api_request(method, path, api_key, payload=None, idempotency_key=None, params=None):
    url = BASE_URL + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    data = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("Authorization", "Bearer " + api_key)
    request.add_header("Content-Type", "application/json")
    if idempotency_key:
        request.add_header("Idempotency-Key", idempotency_key)
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            content_type = response.headers.get("Content-Type", "")
            body = response.read()
            if "application/json" in content_type:
                return json.loads(body.decode())
            return body
    except urllib.error.HTTPError as error:
        detail = error.read().decode(errors="replace")
        raise SystemExit("API error %s: %s" % (error.code, detail))


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python playlist_to_json.py <playlist-url>")
    api_key = __import__("os").environ.get("TRANSCRIPTBATCH_API_KEY")
    if not api_key:
        raise SystemExit("Set TRANSCRIPTBATCH_API_KEY first.")

    created = api_request(
        "POST",
        "/api/v1/jobs",
        api_key,
        payload={"playlistUrl": sys.argv[1], "requestedLanguage": "en"},
        idempotency_key=str(uuid.uuid4()),
    )
    job_id = created["jobId"]
    print("Job created:", job_id)

    while True:
        status = api_request("GET", "/api/v1/jobs/" + job_id, api_key)
        state = status.get("state")
        print("State:", state)
        if state in ("completed", "failed"):
            break
        time.sleep(10)

    if status.get("state") != "completed":
        raise SystemExit("Job did not complete: %s" % json.dumps(status))

    export = api_request(
        "GET", "/api/v1/jobs/" + job_id + "/export", api_key, params={"format": "json"}
    )
    with open("transcripts.json", "wb") as f:
        f.write(export if isinstance(export, bytes) else json.dumps(export).encode())
    print("Saved transcripts.json")


if __name__ == "__main__":
    main()
