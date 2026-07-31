import assert from "node:assert/strict";
import { createApiClient } from "./client.js";

const successfulClient = createApiClient({
  baseUrl: "http://example.test",
  accessToken: "test-token",
  fetchImpl: async (_url, options) => {
    assert.equal(options.headers.Authorization, "Bearer test-token");
    assert.ok(options.signal instanceof AbortSignal);
    return new Response(JSON.stringify({ status: "ok" }), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    });
  },
  timeoutMs: 100,
});

assert.deepEqual(await successfulClient.request("/health"), { status: "ok" });

const stalledClient = createApiClient({
  fetchImpl: async (_url, options) =>
    new Promise((_resolve, reject) => {
      options.signal.addEventListener(
        "abort",
        () => reject(new DOMException("Request timed out", "AbortError")),
        { once: true }
      );
    }),
  timeoutMs: 10,
});

await assert.rejects(stalledClient.request("/stalled"), { name: "AbortError" });

console.log("api client tests passed");
