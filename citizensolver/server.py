"""Browser workbench and loopback API, using the same calculation engine."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
from threading import Lock, Thread
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from .catalogue import DEFAULT_DATA
from .engine import ShipModel, MODEL_VERSION
from .market import HANGARS, read_market, sync_market
from .optimizer import Search, optimize
from .workbench import OBJECTIVES, ROADMAP, search_workbench

STATIC = Path(__file__).with_name("static")


def handler(catalogue, market=None, data_folder=DEFAULT_DATA):
    solve_lock, state_lock = Lock(), Lock()
    state = {"market": market or {"ships": {}, "downloaded_at": None}, "jobs": {}}

    def run(job, body, refresh=False):
        def progress(done, total, name):
            with state_lock:
                job["progress"] = {"done": done, "total": total, "ship": name}
        try:
            if refresh:
                result = sync_market(data_folder)
                with state_lock:
                    state["market"] = result
                result = {"downloaded_at": result["downloaded_at"], "count": len(result["ships"])}
            else:
                result = search_workbench(catalogue, body, progress, market=state["market"])
            with state_lock:
                job.update(status="complete", result=result)
        except Exception as exc:
            with state_lock:
                job.update(status="error", error=str(exc))
        finally:
            solve_lock.release()

    class Handler(BaseHTTPRequestHandler):
        def send_body(self, status, body, content_type):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self' 'unsafe-inline'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def reply(self, status, value):
            self.send_body(status, json.dumps(value, allow_nan=False, ensure_ascii=False).encode("utf-8"), "application/json; charset=utf-8")

        def do_GET(self):
            url = urlsplit(self.path)
            if url.path == "/api/health":
                self.reply(200, {"app": "CitizenSolver", "status": "ok", "model_version": MODEL_VERSION, "data": catalogue.manifest})
            elif url.path == "/api/ships":
                self.reply(200, catalogue.list_ships(parse_qs(url.query).get("role", [None])[0]))
            elif url.path == "/api/options":
                ships = catalogue.list_ships()
                self.reply(200, {"ships": ships, "roles": sorted({s["role"] for s in ships if s["role"]}),
                                 "objectives": OBJECTIVES, "roadmap": ROADMAP, "hangars": HANGARS,
                                 "data": catalogue.manifest, "market": state["market"]})
            elif url.path.startswith("/api/jobs/"):
                with state_lock:
                    job = state["jobs"].get(url.path.rsplit("/", 1)[-1])
                    self.reply(200 if job else 404, job or {"error": "Search not found"})
            elif url.path in {"/", "/app.js", "/priorities.js", "/style.css"}:
                name = "index.html" if url.path == "/" else url.path[1:]
                types = {"html": "text/html", "js": "text/javascript", "css": "text/css"}
                self.send_body(200, (STATIC / name).read_bytes(), types[name.rsplit(".", 1)[-1]] + "; charset=utf-8")
            else:
                self.reply(404, {"error": "Unknown endpoint"})

        def do_POST(self):
            if self.path not in {"/api/evaluate", "/api/optimize", "/api/search", "/api/market/refresh"}:
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
                if self.path in {"/api/search", "/api/market/refresh"}:
                    if not solve_lock.acquire(blocking=False):
                        self.reply(409, {"error": "A search or market refresh is already running"})
                        return
                    job = {"id": uuid4().hex, "status": "running", "progress": {"done": 0, "total": 0, "ship": "Preparing"}}
                    with state_lock:
                        while len(state["jobs"]) >= 4:
                            del state["jobs"][next(iter(state["jobs"]))]
                        state["jobs"][job["id"]] = job
                    Thread(target=run, args=(job, body, self.path.endswith("refresh")), daemon=True).start()
                    self.reply(202, {"id": job["id"]})
                    return
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


def serve(catalogue, port=8765, data_folder=DEFAULT_DATA):
    with ThreadingHTTPServer(("127.0.0.1", port), handler(catalogue, read_market(data_folder), data_folder)) as server:
        print(f"CitizenSolver: http://127.0.0.1:{server.server_port} (Ctrl+C to stop)", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
