"""Tests for the runnable examples, the n8n workflows and the skills' shell blocks.

Every HTTP call goes to a local mock (tests/mock_api.py): nothing reaches api.revana.si and no credit is spent.
Run from the repo root: python3 -m unittest discover -s tests
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from mock_api import MODELS, MockApi  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
GEN = "gen_0123456789abcdef0123"
QUOTE_404 = [(404, {"error": {"code": "not_found", "message": "Not found."}}, {})]


def running(status="running"):
    return (200, {"id": GEN, "object": "generation", "status": status, "cost_usd": None, "error": None}, {})


SUCCEEDED = (200, {"id": GEN, "object": "generation", "status": "succeeded", "cost_usd": 1.05, "error": None, "output": {"urls": ["x"]}}, {})
CREATED = (202, {"id": GEN, "object": "generation", "status": "queued", "quoted_usd": 1.05}, {})


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        # A no-op sleep first on PATH, so resends and polls don't wait.
        bin_dir = self.tmp / "bin"
        bin_dir.mkdir()
        (bin_dir / "sleep").write_text("#!/bin/sh\nexit 0\n")
        (bin_dir / "sleep").chmod(0o755)
        self.path = f"{bin_dir}{os.pathsep}{os.environ['PATH']}"

    def serve(self, routes):
        api = MockApi(routes)
        self.addCleanup(api.close)
        return api

    def env(self, api, **extra):
        return {**os.environ, "PATH": self.path, "REVANA_API_KEY": "sr_live_test", "REVANA_BASE_URL": api.url, **extra}


@unittest.skipUnless(shutil.which("jq") and shutil.which("curl"), "needs curl and jq")
class CurlExamples(Base):
    def run_script(self, api, name, *args, stdin="y\n", **env):
        return subprocess.run(
            ["bash", str(ROOT / "examples/curl" / name), *args],
            input=stdin, text=True, capture_output=True, cwd=self.tmp, env=self.env(api, **env), timeout=60,
        )

    def test_list_quote_when_the_server_has_none_and_a_resend_keeps_the_key(self):
        api = self.serve({
            ("POST", "/v1/generations/quote"): QUOTE_404,
            ("GET", "/v1/models"): [(200, MODELS, {})],
            ("POST", "/v1/generations"): [(503, {"error": {"code": "model_busy", "message": "busy"}}, {"Retry-After": "1"}), CREATED],
            ("GET", f"/v1/generations/{GEN}"): [running("queued"), running(), SUCCEEDED],
            ("GET", f"/v1/generations/{GEN}/content"): [(200, b"MP4", {})],
        })
        r = self.run_script(api, "text-to-video.sh", "a boat")
        self.assertEqual(r.returncode, 0, r.stderr)
        creates = api.find("POST", "/v1/generations")
        self.assertEqual(len(creates), 2)
        keys = {c["headers"]["Idempotency-Key"] for c in creates}
        self.assertEqual(len(keys), 1, "a resend must carry the same Idempotency-Key")
        self.assertEqual(creates[0]["body"]["max_cost_usd"], 1.05)  # 0.21 x 5, without float noise
        self.assertEqual(creates[0]["body"]["input"]["prompt"], "a boat")
        self.assertIn("priced by the list", r.stdout)
        self.assertEqual((self.tmp / f"{GEN}.mp4").read_bytes(), b"MP4")

    def test_server_quote_is_the_cap(self):
        api = self.serve({
            ("POST", "/v1/generations/quote"): [(200, {"object": "quote", "quoted_usd": 1.25, "reserved_usd": 1.25}, {})],
            ("POST", "/v1/generations"): [CREATED],
            ("GET", f"/v1/generations/{GEN}"): [SUCCEEDED],
            ("GET", f"/v1/generations/{GEN}/content"): [(200, b"MP4", {})],
        })
        r = self.run_script(api, "text-to-video.sh")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(api.find("POST", "/v1/generations")[0]["body"]["max_cost_usd"], 1.25)
        self.assertEqual(api.find("GET", "/v1/models"), [], "no list call when the server quotes")

    def test_a_refused_create_is_not_polled(self):
        api = self.serve({
            ("POST", "/v1/generations/quote"): QUOTE_404,
            ("GET", "/v1/models"): [(200, MODELS, {})],
            ("POST", "/v1/generations"): [(422, {"error": {"code": "max_cost_exceeded", "message": "too low", "request_id": "req_00000000000000000001"}}, {})],
        })
        r = self.run_script(api, "text-to-video.sh")
        self.assertEqual(r.returncode, 1)
        self.assertIn("max_cost_exceeded", r.stderr)
        self.assertIn("req_00000000000000000001", r.stderr)
        self.assertEqual(len(api.find("POST", "/v1/generations")), 1, "a 4xx is not resent")
        self.assertFalse([c for c in api.calls if c["path"].startswith("/v1/generations/gen_")])

    def test_a_failed_generation_stops(self):
        api = self.serve({
            ("POST", "/v1/generations/quote"): [(200, {"quoted_usd": 1.05}, {})],
            ("POST", "/v1/generations"): [CREATED],
            ("GET", f"/v1/generations/{GEN}"): [(200, {"id": GEN, "status": "failed", "error": {"code": "timeout", "retryable": True}}, {})],
        })
        r = self.run_script(api, "text-to-video.sh")
        self.assertEqual(r.returncode, 1)
        self.assertIn("timeout", r.stderr)

    def test_image_to_video_uploads_and_takes_a_cap_of_your_own(self):
        img = self.tmp / "photo.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
        api = self.serve({})
        api.routes.update({
            ("POST", "/v1/uploads"): [(201, {"upload_url": f"{api.url}/put/photo", "upload_headers": {"Content-Type": "image/png"}, "url": "https://files.example/photo.png"}, {})],
            ("PUT", "/put/photo"): [(200, {}, {})],
            ("POST", "/v1/generations/quote"): QUOTE_404,
            ("GET", "/v1/models"): [(200, MODELS, {})],
            ("POST", "/v1/generations"): [CREATED],
            ("GET", f"/v1/generations/{GEN}"): [SUCCEEDED],
            ("GET", f"/v1/generations/{GEN}/content"): [(200, b"MP4", {})],
        })
        r = self.run_script(api, "image-to-video.sh", str(img), MAX_COST="1.5")
        self.assertEqual(r.returncode, 0, r.stderr)
        create = api.find("POST", "/v1/generations")[0]["body"]
        self.assertEqual(create["input"]["image_url"], "https://files.example/photo.png")
        self.assertEqual(create["max_cost_usd"], 1.5)

    def test_image_to_video_warns_that_a_list_quote_is_a_floor(self):
        img = self.tmp / "photo.png"
        img.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 32)
        api = self.serve({})
        api.routes.update({
            ("POST", "/v1/uploads"): [(201, {"upload_url": f"{api.url}/put/photo", "upload_headers": {}, "url": "https://files.example/p.png"}, {})],
            ("PUT", "/put/photo"): [(200, {}, {})],
            ("POST", "/v1/generations/quote"): QUOTE_404,
            ("GET", "/v1/models"): [(200, MODELS, {})],
        })
        r = self.run_script(api, "image-to-video.sh", str(img), stdin="n\n")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("MAX_COST", r.stdout)
        self.assertEqual(api.find("POST", "/v1/generations"), [], "nothing is sent without a yes")


@unittest.skipUnless(shutil.which("node"), "needs node")
class NodeHelper(Base):
    def node(self, api, code):
        return subprocess.run(
            ["node", "--input-type=module", "-e", code],
            text=True, capture_output=True, cwd=ROOT / "examples/node", env=self.env(api), timeout=60,
        )

    def test_quote_falls_back_to_the_list_and_create_resends_with_the_same_key(self):
        api = self.serve({
            ("POST", "/v1/generations/quote"): QUOTE_404,
            ("GET", "/v1/models"): [(200, MODELS, {})],
            ("POST", "/v1/generations"): [(502, {"error": {"code": "server_error", "message": "x"}}, {"Retry-After": "0"}), CREATED],
        })
        r = self.node(api, """
            import { quote, create } from "./revana.mjs";
            const st = globalThis.setTimeout; globalThis.setTimeout = (f, ms, ...a) => st(f, ms >= 1000 ? 0 : ms, ...a);
            const q = await quote("wan-3.0", { prompt: "p", resolution: "720p", duration: 3, image_url: "https://x/y.png" });
            const g = await create("wan-3.0", { prompt: "p" }, q.usd);
            console.log(JSON.stringify({ q, id: g.id }));
        """)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out["q"]["usd"], 0.21)  # 0.07 x 3 is 0.21000000000000002
        self.assertEqual(out["q"]["by"], "list")
        self.assertTrue(out["q"]["floor"])
        keys = {c["headers"]["idempotency-key"] for c in api.find("POST", "/v1/generations")}
        self.assertEqual(len(keys), 1)
        self.assertEqual(len(api.find("POST", "/v1/generations")), 2)

    def test_server_quote_and_error_details(self):
        api = self.serve({
            ("POST", "/v1/generations/quote"): [(200, {"quoted_usd": 1.25, "reserved_usd": 1.3}, {})],
            ("POST", "/v1/generations"): [(402, {"error": {"code": "insufficient_credits", "message": "top up", "request_id": "req_0000000000000000000a"}}, {})],
        })
        r = self.node(api, """
            import { quote, create } from "./revana.mjs";
            const q = await quote("seedance-2.5", { prompt: "p" });
            try { await create("seedance-2.5", { prompt: "p" }, q.usd); }
            catch (e) { console.log(JSON.stringify({ q, status: e.status, code: e.code, requestId: e.requestId, message: e.message })); }
        """)
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out["q"]["usd"], 1.25)
        self.assertEqual(out["q"]["by"], "server")
        self.assertEqual((out["status"], out["code"], out["requestId"]), (402, "insufficient_credits", "req_0000000000000000000a"))
        self.assertEqual(len(api.find("POST", "/v1/generations")), 1, "a 402 is not resent")


class PythonHelper(Base):
    def py(self, api, code):
        return subprocess.run(
            [sys.executable, "-c", code], text=True, capture_output=True, cwd=ROOT / "examples/python", env=self.env(api), timeout=60,
        )

    def test_quote_falls_back_and_create_resends_with_the_same_key(self):
        api = self.serve({
            ("POST", "/v1/generations/quote"): QUOTE_404,
            ("GET", "/v1/models"): [(200, MODELS, {})],
            ("POST", "/v1/generations"): [(503, {"error": {"code": "model_busy", "message": "x"}}, {"Retry-After": "1"}), CREATED],
        })
        r = self.py(api, """
import json, time
time.sleep = lambda s: None
import revana_rest as r
q = r.quote("wan-3.0", {"prompt": "p", "resolution": "720p", "duration": 3})
g = r.create("wan-3.0", {"prompt": "p"}, q["usd"])
print(json.dumps({"q": q, "id": g["id"]}))
""")
        self.assertEqual(r.returncode, 0, r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out["q"]["usd"], 0.21)
        self.assertEqual(out["q"]["by"], "list")
        self.assertFalse(out["q"]["floor"])
        creates = api.find("POST", "/v1/generations")
        self.assertEqual(len(creates), 2)
        self.assertEqual(len({c["headers"]["Idempotency-Key"] for c in creates}), 1)

    def test_errors_carry_code_and_request_id_in_both_shapes(self):
        api = self.serve({
            ("POST", "/v1/generations"): [(400, {"error": "Customer generation requires max_cost_usd", "code": "invalid_request"}, {"X-Request-Id": "req_000000000000000000bb"})],
            ("POST", "/v1/generations/quote"): [(422, {"error": {"code": "invalid_input", "message": "no", "request_id": "req_000000000000000000cc"}}, {})],
        })
        r = self.py(api, """
import json
import revana_rest as r
out = []
for f in (lambda: r.create("m", {}, 1), lambda: r.quote("m", {})):
    try:
        f()
    except r.ApiError as e:
        out.append([e.status, e.code, e.request_id])
print(json.dumps(out))
""")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [[400, "invalid_request", "req_000000000000000000bb"], [422, "invalid_input", "req_000000000000000000cc"]])


@unittest.skipUnless(shutil.which("node"), "needs node")
class N8nWorkflows(unittest.TestCase):
    FILES = ["n8n/seedance-2.5-video-generator.json", "n8n/product-ugc-ad-seedance-2.5.json"]

    def nodes(self, f):
        return {n["name"]: n for n in json.loads((ROOT / f).read_text())["nodes"]}

    def run_quote(self, f, settings):
        code = self.nodes(f)["Quote"]["parameters"]["jsCode"]
        harness = (
            "const settings = " + json.dumps(settings) + ";\n"
            "const models = " + json.dumps(MODELS) + ";\n"
            "const $ = () => ({ first: () => ({ json: settings }) });\n"
            "const $input = { first: () => ({ json: models }) };\n"
            "const $execution = { id: '42' };\n"
            "const run = () => { " + code + " };\n"
            "console.log(JSON.stringify([run()[0].json, run()[0].json]));\n"
        )
        r = subprocess.run(["node", "-e", harness], text=True, capture_output=True, timeout=30)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout)

    def test_each_run_makes_a_unique_key_used_by_create(self):
        for f in self.FILES:
            settings = {"model": "wan-3.0", "resolution": "720p", "duration": 3, "audio": True, "max_cost_usd": 2, "image_url": ""}
            a, b = self.run_quote(f, settings)
            self.assertTrue(a["idempotency_key"].startswith("n8n-42-"))
            self.assertNotEqual(a["idempotency_key"], b["idempotency_key"])
            self.assertEqual(a["quote_usd"], 0.21)
            self.assertEqual(a["cap_usd"], 0.21)
            create = self.nodes(f)["Create generation"]
            header = create["parameters"]["headerParameters"]["parameters"][0]
            self.assertEqual(header, {"name": "Idempotency-Key", "value": "={{ $json.idempotency_key }}"})
            self.assertIn("max_cost_usd: $json.cap_usd", create["parameters"]["jsonBody"])
            self.assertTrue(create.get("retryOnFail"))

    def test_a_start_image_is_capped_at_the_budget(self):
        settings = {"model": "seedance-2.5", "resolution": "720p", "duration": 5, "audio": True, "max_cost_usd": 2, "image_url": "https://x/y.png"}
        a, _ = self.run_quote(self.FILES[0], settings)
        self.assertEqual(a["quote_usd"], 1.05)
        self.assertEqual(a["cap_usd"], 2)


class Docs(unittest.TestCase):
    DOCS = [*ROOT.glob("skills/*/SKILL.md"), ROOT / "README.md", ROOT / "examples/README.md"]

    def test_no_inline_uuidgen_key(self):
        for f in [*self.DOCS, *ROOT.glob("examples/**/*.sh")]:
            self.assertNotRegex(f.read_text(), r"Idempotency-Key: \$\(uuidgen\)", str(f))

    def test_no_same_key_after_a_failure(self):
        for f in self.DOCS:
            text = f.read_text()
            self.assertNotRegex(text, r"retryable: true`?\)?[^.]*same Idempotency-Key", str(f))

    def test_shell_blocks_parse(self):
        for f in self.DOCS:
            for block in re.findall(r"```bash\n(.*?)```", f.read_text(), re.S):
                r = subprocess.run(["bash", "-n"], input=block, text=True, capture_output=True)
                self.assertEqual(r.returncode, 0, f"{f}: {r.stderr}")

    def test_lyrics_go_in_input_lyrics(self):
        text = (ROOT / "skills/revana-music/SKILL.md").read_text()
        self.assertIn("lyrics: $lyrics", text)
        self.assertNotRegex(text, r"lyrics, put them in `prompt`")

    def test_no_stale_seedance_720p_price(self):
        for f in self.DOCS:
            self.assertNotIn("$0.25/s", f.read_text(), str(f))


if __name__ == "__main__":
    unittest.main()
