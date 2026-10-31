"""Tiny Revana REST helper for the examples: standard library only, Python 3.8+.

The official package (`pip install revana`) does the same and more; see sdk_example.py.
"""
import json
import math
import mimetypes
import os
import ssl
import sys
import time
import urllib.error
import urllib.request
import uuid

API = os.environ.get("REVANA_BASE_URL", "https://api.revana.si")


def _ssl_context():
    # python.org builds on macOS ship without CA certificates; use certifi when it is installed.
    try:
        import certifi

        return ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        return ssl.create_default_context()


_CTX = _ssl_context()


def _key():
    k = os.environ.get("REVANA_API_KEY")
    if not k:
        sys.exit("Set REVANA_API_KEY first (create a key at https://revana.si/dashboard).")
    return k


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def _open(req, follow=True):
    opener = urllib.request.build_opener(urllib.request.HTTPSHandler(context=_CTX), *([] if follow else [_NoRedirect]))
    try:
        return opener.open(req, timeout=120)
    except urllib.error.URLError as e:
        if "CERTIFICATE_VERIFY_FAILED" in str(e):
            sys.exit("SSL certificates missing: run 'pip install certifi' (or macOS 'Install Certificates.command').")
        raise


class ApiError(RuntimeError):
    """A refused call: status, code, request_id (quote it when asking for help) and retry_after (seconds or None)."""

    def __init__(self, status, code, message, request_id=None, retry_after=None):
        super().__init__(f"{status} {code}: {message}" + (f" (request {request_id})" if request_id else ""))
        self.status, self.code, self.request_id, self.retry_after = status, code, request_id, retry_after


def api(method, path, body=None, idempotency_key=None, auth=True):
    headers = {"User-Agent": "revana-examples/1.0"}
    if auth:
        headers["Authorization"] = "Bearer " + _key()
    data = None
    if body is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body).encode()
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key
    req = urllib.request.Request(API + path, data=data, headers=headers, method=method)
    try:
        with _open(req) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        try:
            data = json.loads(e.read() or b"{}")
        except ValueError:
            data = {}
        err = data.get("error")
        if not isinstance(err, dict):  # the older {"error": "...", "code": "..."} shape
            err = {"message": err, "code": data.get("code")}
        retry_after = e.headers.get("Retry-After")
        raise ApiError(
            e.code,
            err.get("code") or "error",
            err.get("message") or e.reason,
            err.get("request_id") or data.get("request_id") or e.headers.get("X-Request-Id"),
            int(retry_after) if retry_after and retry_after.isdigit() else None,
        ) from None


def models():
    """Every model you can generate with now, with options and live prices. No key needed."""
    return api("GET", "/v1/models", auth=False)["data"]


def quote(model_id, inp):
    """Price one generation: {"usd", "by": "server" | "list", ...}.

    The server's free quote (POST /v1/generations/quote) prices the exact request. API versions from before the
    2026-10-31 deploy answer it 404; then the live list prices it (list_quote). "floor": True means the list can be
    low (a start image costs more on some models, Seedance 2.5 among them).
    """
    try:
        q = api("POST", "/v1/generations/quote", {"model": model_id, "input": inp})
        return {"model": model_id, "usd": q["quoted_usd"], "reserved_usd": q.get("reserved_usd"), "by": "server", "setting": "server quote"}
    except ApiError as e:
        if e.status != 404:
            raise
    return list_quote(model_id, inp)


def list_quote(model_id, inp):
    """Price one generation from the live list: per_second x duration, per_image, or per_job.

    price.usd is a number or a map keyed by resolution ("720p"), "<res>+audio", quality, or "<aspect>-<quality>".
    If no key matches, the dearest listed setting is used so the quote never comes in low.
    """
    m = next((x for x in models() if x["id"] == model_id), None)
    if m is None:
        raise RuntimeError(f'No model "{model_id}" in /v1/models')
    unit, usd = m["price"]["unit"], m["price"]["usd"]
    setting = "flat"
    if isinstance(usd, (int, float)):
        each = usd
    else:
        res, q, ar = inp.get("resolution"), inp.get("quality"), inp.get("aspect_ratio")
        tries = [res and inp.get("audio") and f"{res}+audio", res, q, ar and q and f"{ar}-{q}"]
        setting = next((k for k in tries if k and k in usd), None)
        if setting:
            each = usd[setting]
        else:
            k, each = max(usd.items(), key=lambda kv: kv[1])
            setting = f"{k} (dearest listed)"
    seconds = inp.get("duration", 5) if unit == "per_second" else 1
    usd_total = math.ceil(round(each * seconds * 100, 6) - 1e-9) / 100  # up to a whole cent
    floor = unit == "per_second" and bool(inp.get("image_url"))
    return {"model": m["id"], "unit": unit, "setting": setting, "each": each, "usd": usd_total, "by": "list", "floor": floor}


def confirm(question):
    """Ask before spending. --yes on the command line skips the question."""
    if "--yes" in sys.argv:
        return True
    if not sys.stdin.isatty():
        print("Not a terminal: pass --yes to confirm the spend.", file=sys.stderr)
        return False
    return input(f"{question} [y/N] ").strip().lower() in ("y", "yes")


def create(model, inp, max_cost_usd, idempotency_key=None, tries=4):
    """Start one generation.

    Its Idempotency-Key is made once, here: a resend after no answer, a 429 or a 5xx carries the same key, so it
    returns the generation already started instead of making (and charging for) a second one. After a generation
    has failed, call create again: that makes a new key (the old one keeps answering the failure).
    """
    body = {"model": model, "input": inp, "max_cost_usd": max_cost_usd}
    key = idempotency_key or str(uuid.uuid4())
    for n in range(1, tries + 1):
        try:
            return api("POST", "/v1/generations", body, key)
        except (ApiError, urllib.error.URLError, OSError) as e:
            status = getattr(e, "status", None)
            if (status is not None and status != 429 and status < 500) or n == tries:
                raise
            wait_s = getattr(e, "retry_after", None) or 5 * n
            print(f"  create: {e}; resending with the same key in {wait_s}s", file=sys.stderr)
            time.sleep(wait_s)


def max_cost_arg():
    """--max-cost=<usd> on the command line: a cap of your own instead of the quote."""
    v = next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--max-cost=")), None)
    try:
        return float(v) if v and float(v) > 0 else None
    except ValueError:
        return None


def wait(gen_id, every_s=5, log=True):
    """Poll until succeeded (returned) or failed (raised)."""
    while True:
        g = api("GET", f"/v1/generations/{gen_id}")
        if g["status"] == "succeeded":
            return g
        if g["status"] == "failed":
            e = g.get("error") or {}
            raise RuntimeError(f"{gen_id} failed: {e.get('code')}: {e.get('message')} (retryable: {e.get('retryable')})")
        if log:
            print(f"  {gen_id} {g['status']}", file=sys.stderr)
        time.sleep(every_s)


def download(gen_id, path, n=1):
    """Save file n (1-based). The key goes only to api.revana.si, not to the file host it redirects to."""
    url = f"{API}/v1/generations/{gen_id}/content" + (f"/{n}" if n > 1 else "")
    req = urllib.request.Request(url, headers={"Authorization": "Bearer " + _key(), "User-Agent": "revana-examples/1.0"})
    try:
        r = _open(req, follow=False)
    except urllib.error.HTTPError as e:
        if e.code not in (301, 302, 303, 307, 308):
            raise
        r = _open(urllib.request.Request(e.headers["Location"], headers={"User-Agent": "revana-examples/1.0"}))
    with r, open(path, "wb") as f:
        f.write(r.read())
    return path


def upload(path):
    """Upload a local file (free) and get a public link, good for 14 days, to pass as image_url etc."""
    ctype = mimetypes.guess_type(path)[0]
    if not ctype:
        raise RuntimeError(f"Unknown file type: {path}")
    with open(path, "rb") as f:
        data = f.read()
    up = api("POST", "/v1/uploads", {"content_type": ctype, "bytes": len(data), "filename": os.path.basename(path)})
    put = urllib.request.Request(up["upload_url"], data=data, headers=up["upload_headers"], method=up.get("upload_method", "PUT"))
    _open(put).close()
    return up["url"]
