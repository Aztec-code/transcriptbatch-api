// Submit a YouTube playlist to the TranscriptBatch API and save the JSON export.
//
// Native fetch only, needs Node 18+. Reads the API key from TRANSCRIPTBATCH_API_KEY.
//
// Usage:
//   node playlist_to_json.mjs "https://www.youtube.com/playlist?list=PLxxxx"

import { randomUUID } from "node:crypto";
import { writeFile } from "node:fs/promises";

const BASE_URL = "https://transcriptapiyt.com";
const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

async function apiRequest(method, path, apiKey, { payload, idempotencyKey, params } = {}) {
  const url = new URL(BASE_URL + path);
  for (const [key, value] of Object.entries(params ?? {})) url.searchParams.set(key, value);
  const response = await fetch(url, {
    method,
    headers: {
      Authorization: "Bearer " + apiKey,
      "Content-Type": "application/json",
      ...(idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}),
    },
    body: payload ? JSON.stringify(payload) : undefined,
  });
  if (!response.ok) throw new Error(`API error ${response.status}: ${await response.text()}`);
  return response.headers.get("content-type")?.includes("application/json")
    ? response.json()
    : Buffer.from(await response.arrayBuffer());
}

const playlistUrl = process.argv[2];
const apiKey = process.env.TRANSCRIPTBATCH_API_KEY;
if (!playlistUrl) throw new Error("Usage: node playlist_to_json.mjs <playlist-url>");
if (!apiKey) throw new Error("Set TRANSCRIPTBATCH_API_KEY first.");

const created = await apiRequest("POST", "/api/v1/jobs", apiKey, {
  payload: { playlistUrl, requestedLanguage: "en" },
  idempotencyKey: randomUUID(),
});
console.log("Job created:", created.jobId);

let status;
for (;;) {
  status = await apiRequest("GET", `/api/v1/jobs/${created.jobId}`, apiKey);
  console.log("State:", status.state);
  if (status.state === "completed" || status.state === "failed") break;
  await sleep(10000);
}
if (status.state !== "completed") throw new Error("Job did not complete.");

const data = await apiRequest("GET", `/api/v1/jobs/${created.jobId}/export`, apiKey, {
  params: { format: "json" },
});
await writeFile("transcripts.json", typeof data === "string" || Buffer.isBuffer(data) ? data : JSON.stringify(data));
console.log("Saved transcripts.json");
