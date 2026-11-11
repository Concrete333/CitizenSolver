"""Command line and JSON output for local use and future UI integration."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from .catalogue import Catalogue, DEFAULT_DATA, DEFAULT_REVISION, sync, write_json
from .engine import ShipModel, MODEL_VERSION
from .optimizer import GOALS, Search, compare, optimize


def search_arguments(parser):
    parser.add_argument("--goal", choices=GOALS, default="balanced")
    parser.add_argument("--duration", type=float, default=120, help="Engagement duration in seconds")
    parser.add_argument("--beam", type=int, default=6)
    parser.add_argument("--passes", type=int, default=2)
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--damage-floor", type=float, default=.9, help="For stealth/balanced: fraction of best finite-duration DPS found")
    parser.add_argument("--min-shield", type=float, default=0)
    parser.add_argument("--min-dps", type=float, default=0, help="Minimum finite-duration DPS")
    parser.add_argument("--min-pitch", type=float, default=0)
    parser.add_argument("--min-yaw", type=float, default=0)
    parser.add_argument("--min-range", type=float, default=0, help="Minimum rated range of every gun in meters")
    parser.add_argument("--min-velocity", type=float, default=0, help="Minimum projectile speed of every gun in m/s")
    parser.add_argument("--max-em", type=float)
    parser.add_argument("--max-ir", type=float)
    parser.add_argument("--max-evaluations", type=int, default=15000)


def parser():
    root = argparse.ArgumentParser(description="CitizenSolver — experimental local loadout optimizer")
    root.add_argument("--data", type=Path, default=DEFAULT_DATA)
    sub = root.add_subparsers(dest="command", required=True)
    download = sub.add_parser("sync", help="Download a pinned public game-data snapshot")
    download.add_argument("--revision", default=DEFAULT_REVISION, help="Commit SHA or latest")
    download.add_argument("--version", help="Build label for a custom SHA")
    listing = sub.add_parser("ships", help="List ship class ids")
    listing.add_argument("--role")
    components = sub.add_parser("components", help="List modeled ports and compatible components")
    components.add_argument("ship")
    evaluate = sub.add_parser("evaluate", help="Evaluate stock equipment or a saved build")
    evaluate.add_argument("ship")
    evaluate.add_argument("--build", type=Path)
    evaluate.add_argument("--profile", choices=("damage", "balanced", "stealth"), default="damage")
    evaluate.add_argument("--duration", type=float, default=120)
    solving = sub.add_parser("optimize", help="Search one ship's component combinations")
    solving.add_argument("ship")
    search_arguments(solving)
    comparison = sub.add_parser("compare", help="Optimize and rank ships in a role")
    comparison.add_argument("--role", default="Medium Fighter")
    comparison.add_argument("--ships", nargs="+", help="Optional exact subset of ship class ids")
    search_arguments(comparison)
    comparison.set_defaults(goal="pve")
    serving = sub.add_parser("serve", help="Run the local browser workbench and JSON API")
    serving.add_argument("--port", type=int, default=8765)
    for cmd in (listing, components, evaluate, solving, comparison):
        cmd.add_argument("--out", type=Path, help="Save the complete JSON result")
        cmd.add_argument("--json", action="store_true", help="Print full JSON instead of a concise summary")
    return root


def build_input(path, catalogue, ship):
    saved = json.loads(path.read_text(encoding="utf-8"))
    if "results" in saved:
        if not saved["results"]:
            raise ValueError("Saved search has no results")
        saved = saved["results"][0]
    if saved.get("ship", {}).get("id") != ship["ClassName"]:
        raise ValueError("Saved build belongs to a different ship")
    if saved.get("data", {}).get("revision") != catalogue.manifest["revision"]:
        raise ValueError("Saved build uses a different data revision; load that snapshot before replaying")
    if saved.get("model_version") != MODEL_VERSION:
        raise ValueError("Saved build uses a different calculation model")
    return saved


def summarize(result):
    if isinstance(result, list):
        return "\n".join(f"{s['id']} — {s['name']} ({s.get('role', '')})" for s in result)
    if "ports" in result:
        return "\n".join(f"{p['id']} | {p['name']} | {len(p['options'])} choices" for p in result["ports"])
    results = result.get("results", [result] if "metrics" in result else [])
    if not results:
        return result.get("message", "No candidates")
    lines = ["EXPERIMENTAL ESTIMATES — see docs/model.md; not a validated in-game optimum."]
    for index, r in enumerate(results, 1):
        m = r["metrics"]
        lines.append(f"\n{index}. {r['ship']['name']} — {r['scenario']['power_profile']} power")
        lines.append(f"   Alpha {m['alpha']:,.0f} | burst {m['burst_dps']:,.0f} | sustained {m['sustained_dps']:,.0f} | {r['scenario']['duration_seconds']:g}s DPS {m['duration_dps']:,.0f}")
        lines.append(f"   EM {m['em']:,.0f} | IR {m['ir'] or 0:,.0f} | shields {m['shield_hp']:,.0f} | rated pitch/yaw {m['pitch']}/{m['yaw']}")
        for item in r["loadout"]:
            if item["changed"]:
                lines.append(f"   {item['port']}: {item['name']}")
        lines.append("   Pips: " + ", ".join(f"{k}={v}" for k, v in r["power"]["allocation"].items()))
        if not r["feasible"]:
            lines.append("   INFEASIBLE: " + "; ".join(r["violations"]))
    if "search" in result:
        s = result["search"]
        lines.append(f"\n{s['evaluations']:,} configurations/profiles evaluated in {s['seconds']:.1f}s; global optimum not proven.")
    if result.get("skipped"):
        lines.append(f"\n{len(result['skipped'])} ships skipped; full reasons in JSON.")
    return "\n".join(lines)


def main(argv=None):
    # Redirected Windows streams otherwise use an ANSI code page that cannot
    # represent every ship name in the source catalogue.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = parser().parse_args(argv)
    try:
        if args.command == "sync":
            result = sync(args.data, args.revision, args.version)
            print(json.dumps(result, indent=2))
            return 0
        catalogue = Catalogue(args.data)
        if args.command == "serve":
            from .server import serve
            serve(catalogue, args.port, args.data)
            return 0
        if args.command == "ships":
            result = catalogue.list_ships(args.role)
        elif args.command == "components":
            ship = catalogue.ship(args.ship)
            model = ShipModel(catalogue, ship)
            result = {"ship": ship["ClassName"], "data": catalogue.manifest, "ports": [
                {"id": key, "name": item["Name"], "editable": model.ports[key][1],
                 "options": [{"id": name, "name": catalogue.items[name]["Name"]}
                             for name in catalogue.options(ship, *model.ports[key])]}
                for key, item in model.active.items()], "unsupported": model.excluded}
        elif args.command == "evaluate":
            ship = catalogue.ship(args.ship)
            saved = build_input(args.build, catalogue, ship) if args.build else None
            result = ShipModel(catalogue, ship).evaluate(
                saved["swaps"] if saved else {},
                profile=saved["scenario"]["power_profile"] if saved else args.profile,
                pips=saved["power"]["allocation"] if saved else None,
                duration=saved["scenario"]["duration_seconds"] if saved else args.duration)
        else:
            request = Search(**{k: getattr(args, k) for k in Search.__dataclass_fields__ if hasattr(args, k)})
            result = optimize(catalogue, catalogue.ship(args.ship), request) if args.command == "optimize" else compare(catalogue, args.role, request, args.ships)
        if args.out:
            write_json(args.out, result)
        if args.json:
            print(json.dumps(result, ensure_ascii=False, allow_nan=False, indent=2))
        else:
            print(summarize(result))
            if args.out:
                print(f"\nSaved: {args.out.resolve()}")
        return 0
    except (ValueError, OSError, KeyError) as exc:
        print(f"CitizenSolver: {exc}", file=sys.stderr)
        if isinstance(exc, FileNotFoundError):
            print("Download the catalogue first: python -m citizensolver sync", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
