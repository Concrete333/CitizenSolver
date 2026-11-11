from contextlib import redirect_stdout, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
from threading import Thread
from http.server import ThreadingHTTPServer
import unittest
from unittest.mock import patch
from urllib.request import Request, urlopen
from urllib.error import HTTPError

from citizensolver.catalogue import Catalogue, sync, write_json
from citizensolver.cli import main
from citizensolver.server import handler
from helpers import fixture, REVISION


class Interfaces(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.catalogue = fixture(self.temp.name)

    def cli(self, *args):
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(out):
            code = main(["--data", self.temp.name, *args])
        return code, out.getvalue()

    def test_save_replay_and_revision_check(self):
        file = Path(self.temp.name) / "build.json"
        code, _ = self.cli("optimize", "TEST_Ship", "--limit", "1", "--out", str(file))
        self.assertEqual(code, 0)
        saved = json.loads(file.read_text(encoding="utf-8"))
        code, text = self.cli("evaluate", "TEST_Ship", "--build", str(file), "--json")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(text)["metrics"], saved["results"][0]["metrics"])
        saved["results"][0]["data"]["revision"] = "b" * 40
        write_json(file, saved)
        code, text = self.cli("evaluate", "TEST_Ship", "--build", str(file))
        self.assertEqual(code, 2)
        self.assertIn("different data revision", text)

    def test_ambiguous_names_require_id(self):
        self.catalogue.ships["TEST_Other"] = {**self.catalogue.ships["TEST_Ship"], "ClassName": "TEST_Other"}
        with self.assertRaises(ValueError):
            self.catalogue.ship("Ship")
        self.assertEqual(self.catalogue.ship("TEST_Ship")["ClassName"], "TEST_Ship")

    def test_failed_sync_preserves_active_revision(self):
        with patch("citizensolver.catalogue.get_json", return_value=[]):
            with self.assertRaises(ValueError):
                sync(self.temp.name, revision="b" * 40)
        self.assertEqual(Catalogue(self.temp.name).manifest["revision"], REVISION)

    def test_snapshot_checksums_detect_corruption(self):
        manifest = sync(self.temp.name, revision=REVISION, version="synthetic")
        self.assertEqual(len(manifest["sha256"]), 2)
        path = Path(self.temp.name) / REVISION / "ships.json"
        path.write_text("[]", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "checksum"):
            Catalogue(self.temp.name)

    def test_http_health_evaluate_optimize_and_errors(self):
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler(self.catalogue, data_folder=self.temp.name))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base + "/api/health", timeout=10) as r:
                self.assertEqual(json.load(r)["status"], "ok")
            with urlopen(base + "/api/components?ship=TEST_Ship", timeout=10) as r:
                components = json.load(r)
                self.assertEqual(components["revision"], REVISION)
                plant = next(p for p in components["ports"] if p["port"] == "p1")
                self.assertIn("quiet", [c["id"] for c in plant["choices"]])
            with urlopen(base + "/editor.js", timeout=10) as r:
                self.assertIn("text/javascript", r.headers["Content-Type"])
            req = Request(base + "/api/evaluate", data=json.dumps({"ship":"TEST_Ship", "revision":"stale"}).encode(), headers={"Content-Type":"application/json"})
            with self.assertRaises(HTTPError) as ctx:
                urlopen(req, timeout=10)
            self.assertEqual(ctx.exception.code, 400)
            self.assertIn("Game data changed", ctx.exception.read().decode())
            ctx.exception.close()
            for endpoint in ("evaluate", "optimize"):
                req = Request(base + "/api/" + endpoint, data=json.dumps({"ship": "TEST_Ship"}).encode(), headers={"Content-Type": "application/json"})
                with urlopen(req, timeout=10) as r:
                    value = json.load(r)
                    self.assertTrue(value.get("feasible") or value.get("results"))
            req = Request(base + "/api/evaluate", data=b'{"ship":"bad"}', headers={"Content-Type": "application/json"})
            with self.assertRaises(HTTPError) as ctx:
                urlopen(req, timeout=10)
            self.assertEqual(ctx.exception.code, 400)
            ctx.exception.close()
            req = Request(base + "/api/evaluate", data=b'{}', headers={"Content-Type": "application/json", "Origin": "https://example.org"})
            with self.assertRaises(HTTPError) as ctx:
                urlopen(req, timeout=10)
            self.assertEqual(ctx.exception.code, 403)
            ctx.exception.close()
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
