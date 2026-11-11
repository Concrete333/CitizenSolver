"""Loopback-only development API. No data downloads or disk writes via HTTP."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Lock
from urllib.parse import parse_qs, urlsplit

from .engine import ShipModel, MODEL_VERSION
from .optimizer import Search, optimize


def handler(catalogue):
    solve_lock = Lock()

    class Handler(BaseHTTPRequestHandler):
        def reply(self, status, value):
            body = json.dumps(value, allow_nan=False, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path == "/api/health":
                self.reply(200, {"status": "ok", "model_version": MODEL_VERSION, "data": catalogue.manifest})
            elif url.path == "/api/ships":
                self.reply(200, catalogue.list_ships(parse_qs(url.query).get("role", [None])[0]))
            elif url.path == "/":
                self.reply(200, {"app": "CitizenSolver", "ui": "planned", "get": ["/api/health", "/api/ships"],
                                 "post": ["/api/evaluate", "/api/optimize"], "documentation": "docs/api.md"})
            else:
                self.reply(404, {"error": "Unknown endpoint"})

        def do_POST(self):
            if self.path not in {"/api/evaluate", "/api/optimize"}:
                self.reply(404, {"error": "Unknown endpoint"})
                return
            if self.headers.get("Origin") and self.headers["Origin"] != f"http://127.0.0.1:{self.server.server_port}":
                self.reply(403, {"error": "This development API accepts same-origin requests only"})
                return
            if self.headers.get_content_type() != "application/json":
                self.reply(415, {"error": "Use application/json"})
                return
            try:
                size = int(self.headers.get("Content-Length", "0"))
                if not 0 < size <= 65536:
                    raise ValueError("Request body must be 1..65536 bytes")
                self.connection.settimeout(10)
                body = json.loads(self.rfile.read(size))
                if not isinstance(body, dict):
                    raise ValueError("Expected a JSON object")
                ship = catalogue.ship(body["ship"])
                if self.path == "/api/evaluate":
                    result = ShipModel(catalogue, ship).evaluate(body.get("swaps"), pips=body.get("pips"),
                        profile=body.get("profile", "damage"), duration=body.get("duration", 120))
                else:
                    request = Search(**body.get("search", {}))
                    if not solve_lock.acquire(blocking=False):
                        self.reply(409, {"error": "A search is already running"})
                        return
                    try:
                        result = optimize(catalogue, ship, request)
                    finally:
                        solve_lock.release()
                self.reply(200, result)
            except (ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
                self.reply(400, {"error": str(exc)})

    return Handler


def serve(catalogue, port=8765):
    with ThreadingHTTPServer(("127.0.0.1", port), handler(catalogue)) as server:
        print(f"CitizenSolver local API: http://127.0.0.1:{server.server_port} (Ctrl+C to stop)", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
