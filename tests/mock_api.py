"""A scripted stand-in for api.revana.si, for the example tests. Nothing here talks to the real API."""
import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

MODELS = {
    "object": "list",
    "data": [
        {"id": "seedance-2.5", "kind": "video", "price": {"unit": "per_second", "usd": {"480p": 0.09, "720p": 0.21, "1080p": 0.52}}},
        {"id": "wan-3.0", "kind": "video", "price": {"unit": "per_second", "usd": {"720p": 0.07}}},
        {"id": "nano-banana-pro", "kind": "image", "price": {"unit": "per_image", "usd": {"1K": 0.04, "2K": 0.04, "4K": 0.08}}},
    ],
}


class MockApi:
    """routes: {(METHOD, path): [(status, body, headers), ...]}; each call takes the next answer, the last repeats."""

    def __init__(self, routes):
        self.routes = {k: list(v) for k, v in routes.items()}
        self.calls = []
        mock = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _answer(self):
                n = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(n) if n else b""
                try:
                    body = json.loads(raw) if raw else None
                except ValueError:
                    body = raw
                path = self.path.split("?")[0]
                mock.calls.append({"method": self.command, "path": path, "headers": dict(self.headers), "body": body})
                answers = mock.routes.get((self.command, path))
                if not answers:
                    status, out, headers = 404, {"error": {"code": "not_found", "message": "Not found."}}, {}
                else:
                    status, out, headers = answers.pop(0) if len(answers) > 1 else answers[0]
                data = out if isinstance(out, bytes) else json.dumps(out).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/octet-stream" if isinstance(out, bytes) else "application/json")
                self.send_header("Content-Length", str(len(data)))
                for k, v in (headers or {}).items():
                    self.send_header(k, v)
                self.end_headers()
                self.wfile.write(data)

            do_GET = do_POST = do_PUT = _answer

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.server.server_address[1]}"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    def close(self):
        self.server.shutdown()
        self.server.server_close()

    def find(self, method, path):
        return [c for c in self.calls if c["method"] == method and c["path"] == path]
