// Tiny Revana REST helper for the examples: plain fetch, no dependencies, Node 18+.
// The official SDK (`npm i revana`) does the same and more; see sdk.mjs.
import { readFile, writeFile } from "node:fs/promises";
import { randomUUID } from "node:crypto";
import { basename, extname } from "node:path";
import { createInterface } from "node:readline/promises";

export const API = process.env.REVANA_BASE_URL ?? "https://api.revana.si";

function key() {
  const k = process.env.REVANA_API_KEY;
  if (!k) {
    console.error("Set REVANA_API_KEY first (create a key at https://revana.si/dashboard).");
    process.exit(1);
  }
  return k;
}

/** A refused call: err.status, err.code and err.requestId (quote it when asking for help) are set. */
export async function api(method, path, { body, idempotencyKey, auth = true } = {}) {
  const headers = {};
  if (auth) headers.authorization = `Bearer ${key()}`;
  if (body !== undefined) headers["content-type"] = "application/json";
  if (idempotencyKey) headers["idempotency-key"] = idempotencyKey;
  const res = await fetch(API + path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const e = typeof data.error === "object" && data.error ? data.error : { message: data.error, code: data.code };
    const requestId = e.request_id ?? data.request_id ?? res.headers.get("x-request-id") ?? undefined;
    const err = new Error(`${res.status} ${e.code ?? "error"}: ${e.message ?? res.statusText}${requestId ? ` (request ${requestId})` : ""}`);
    Object.assign(err, { status: res.status, code: e.code, requestId, retryAfter: Number(res.headers.get("retry-after")) || undefined });
    throw err;
  }
  return data;
}

/** Every model you can generate with now, with options and live prices. No key needed. */
export async function models() {
  return (await api("GET", "/v1/models", { auth: false })).data;
}

/**
 * Price one generation. The server's free quote (POST /v1/generations/quote) prices the exact request; API versions
 * from before the 2026-10-31 deploy answer it 404, and then the live list prices it (listQuote). Returns
 * { usd, by: "server" | "list", ... }; `floor: true` when the list can be low (a start image costs more on some models).
 */
export async function quote(modelId, input) {
  try {
    const q = await api("POST", "/v1/generations/quote", { body: { model: modelId, input } });
    return { model: modelId, usd: q.quoted_usd, reserved_usd: q.reserved_usd, by: "server", setting: "server quote" };
  } catch (err) {
    if (err.status !== 404) throw err;
  }
  return listQuote(modelId, input);
}

/**
 * Price one generation from the live list: per_second x duration, per_image, or per_job.
 * price.usd is a number or a map keyed by resolution ("720p"), "<res>+audio", quality, or "<aspect>-<quality>".
 * If no key matches, the dearest listed setting is used so the quote never comes in low.
 */
export async function listQuote(modelId, input) {
  const m = (await models()).find((x) => x.id === modelId);
  if (!m) throw new Error(`No model "${modelId}" in /v1/models`);
  const { unit, usd } = m.price;
  let each;
  let setting = "flat";
  if (typeof usd === "number") each = usd;
  else {
    const res = input.resolution;
    const tries = [
      input.audio && res && `${res}+audio`,
      res,
      input.quality,
      input.aspect_ratio && input.quality && `${input.aspect_ratio}-${input.quality}`,
    ].filter(Boolean);
    setting = tries.find((k) => k in usd);
    if (setting) each = usd[setting];
    else {
      const [k, v] = Object.entries(usd).sort((a, b) => b[1] - a[1])[0];
      setting = `${k} (dearest listed)`;
      each = v;
    }
  }
  const seconds = unit === "per_second" ? (input.duration ?? 5) : 1;
  const usdTotal = Math.ceil(Math.round(each * seconds * 1e6) / 1e4 - 1e-9) / 100; // up to a whole cent
  return { model: m.id, unit, setting, each, seconds, usd: usdTotal, by: "list", floor: unit === "per_second" && !!input.image_url };
}

/** Ask before spending. --yes on the command line skips the question. */
export async function confirm(question) {
  if (process.argv.includes("--yes")) return true;
  if (!process.stdin.isTTY) {
    console.error("Not a terminal: pass --yes to confirm the spend.");
    return false;
  }
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  const answer = await rl.question(`${question} [y/N] `);
  rl.close();
  return /^y(es)?$/i.test(answer.trim());
}

/**
 * Start one generation. Its Idempotency-Key is made once, here: a resend after no answer, a 429 or a 5xx carries the
 * same key, so it returns the generation already started instead of making (and charging for) a second one.
 * After a generation has failed, call create again: that makes a new key (the old one keeps answering the failure).
 */
export async function create(model, input, maxCostUsd, idempotencyKey = randomUUID(), { tries = 4 } = {}) {
  for (let n = 1; ; n++) {
    try {
      return await api("POST", "/v1/generations", { body: { model, input, max_cost_usd: maxCostUsd }, idempotencyKey });
    } catch (err) {
      const again = err.status === undefined || err.status === 429 || err.status >= 500;
      if (!again || n >= tries) throw err;
      const s = err.retryAfter ?? 5 * n;
      process.stderr.write(`  create: ${err.message}; resending with the same key in ${s}s\n`);
      await new Promise((r) => setTimeout(r, s * 1000));
    }
  }
}

/** --max-cost <usd> on the command line: a cap of your own instead of the quote. */
export function maxCostArg() {
  const i = process.argv.indexOf("--max-cost");
  const v = i > 0 ? Number(process.argv[i + 1]) : NaN;
  return Number.isFinite(v) && v > 0 ? v : undefined;
}

/** Poll until succeeded (returned) or failed (thrown). */
export async function wait(id, { everyMs = 5000, log = true } = {}) {
  for (;;) {
    const g = await api("GET", `/v1/generations/${id}`);
    if (g.status === "succeeded") return g;
    if (g.status === "failed") throw new Error(`${id} failed: ${g.error?.code}: ${g.error?.message} (retryable: ${g.error?.retryable})`);
    if (log) process.stderr.write(`  ${id} ${g.status}${g.message ? `: ${g.message}` : ""}\n`);
    await new Promise((r) => setTimeout(r, everyMs));
  }
}

/** Save file n (1-based) of a finished generation. fetch drops the key on the redirect to the file host. */
export async function download(id, file, n = 1) {
  const res = await fetch(`${API}/v1/generations/${id}/content${n > 1 ? `/${n}` : ""}`, {
    headers: { authorization: `Bearer ${key()}` },
  });
  if (!res.ok) throw new Error(`download ${res.status}`);
  await writeFile(file, Buffer.from(await res.arrayBuffer()));
  return file;
}

const TYPES = { ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".mp4": "video/mp4", ".mov": "video/quicktime", ".mp3": "audio/mpeg", ".wav": "audio/wav" };

/** Upload a local file (free) and get a public link, good for 14 days, to pass as image_url etc. */
export async function upload(path) {
  const type = TYPES[extname(path).toLowerCase()];
  if (!type) throw new Error(`Unknown file type: ${path}`);
  const bytes = await readFile(path);
  const up = await api("POST", "/v1/uploads", { body: { content_type: type, bytes: bytes.length, filename: basename(path) } });
  const put = await fetch(up.upload_url, { method: up.upload_method ?? "PUT", headers: up.upload_headers, body: bytes });
  if (!put.ok) throw new Error(`upload PUT ${put.status}`);
  return up.url;
}
