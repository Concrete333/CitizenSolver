"""Pinned, locally cached public game data. No calls to erkul."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from datetime import datetime, timezone
from urllib.request import Request, urlopen

SOURCE = "StarCitizenWiki/scunpacked-data"
DEFAULT_REVISION = "1340c8303709904165e2da0fa7060bce0624260b"
DEFAULT_VERSION = "4.10.2-LIVE.12881860"
DEFAULT_DATA = Path(__file__).resolve().parent.parent / "data"
SWAPPABLE = {"WeaponGun", "Shield", "PowerPlant", "Cooler", "Radar", "FlightController"}


def get_json(url):
    req = Request(url, headers={"User-Agent": "CitizenSolver/0.1"})
    with urlopen(req, timeout=45) as response:
        return json.load(response)


def write_json(path, value):
    """Replace a complete JSON file atomically; leave existing files intact on failure."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, allow_nan=False, indent=2)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def sync(folder=DEFAULT_DATA, revision=DEFAULT_REVISION, version=None):
    """Two bulk reads per immutable snapshot, plus an optional ref resolution."""
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        if revision != "latest":
            raise ValueError("Use a full commit SHA or 'latest'.")
        commit = get_json(f"https://api.github.com/repos/{SOURCE}/commits/master")
        revision = commit["sha"]
        version = commit["commit"]["message"].splitlines()[0]
    version = version or (DEFAULT_VERSION if revision == DEFAULT_REVISION else "unidentified build")
    folder = Path(folder)
    snapshot = folder / revision
    snapshot.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name in ("ships.json", "ship-items.json"):
        path = snapshot / name
        if path.exists():
            contents = json.loads(path.read_text(encoding="utf-8"))
        else:
            contents = get_json(f"https://raw.githubusercontent.com/{SOURCE}/{revision}/{name}")
            if not isinstance(contents, list) or not contents:
                raise ValueError(f"Unexpected or empty {name}; previous snapshot is still active.")
            write_json(path, contents)
        hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    # Parse before activation; incomplete downloads never replace the active manifest.
    manifest = {"source": SOURCE, "revision": revision, "game_version": version,
                "downloaded_at": datetime.now(timezone.utc).isoformat(), "sha256": hashes}
    Catalogue(snapshot, manifest=manifest)
    write_json(snapshot / "manifest.json", manifest)
    write_json(folder / "manifest.json", manifest)
    return manifest


def kind(item):
    return item.get("Type", "").split(".")[0]


def tags(value):
    if isinstance(value, str):
        value = value.split()
    return {x.lstrip("$").casefold() for x in value or []}


def walk_ports(ports):
    for port in ports:
        # The export stamps each port individually. A locked mount can hold an
        # explicitly editable gun; EditableChildren is not an inherited lock.
        yield port, port.get("Editable", False)
        yield from walk_ports(port.get("Loadout", []))


def compatible(port, item):
    size = item.get("Size")
    if size is None or not port.get("MinSize", 0) <= size <= port.get("MaxSize", -1):
        return False
    item_type, _, subtype = item.get("Type", "").partition(".")
    if not any(t.get("Type") == item_type and
               (not t.get("SubTypes") or subtype in t["SubTypes"])
               for t in port.get("CompatibleTypes", [])):
        return False
    requirements = tags(port.get("RequiredTags"))
    item_tags = tags(item.get("Tags")) | tags(item.get("RequiredTags"))
    if not requirements <= item_tags:
        return False
    if not tags(item.get("RequiredTags")) <= requirements | tags(port.get("PortTags")):
        return False
    return not bool(tags(port.get("ExcludedTags")) & item_tags)


class Catalogue:
    def __init__(self, folder=DEFAULT_DATA, *, manifest=None):
        folder = Path(folder)
        self.manifest = manifest or json.loads((folder / "manifest.json").read_text(encoding="utf-8"))
        if manifest is None:
            revision = self.manifest["revision"]
            if not re.fullmatch(r"[0-9a-f]{40}", revision):
                raise ValueError("Invalid snapshot revision")
            folder = folder / revision
        for filename, digest in self.manifest.get("sha256", {}).items():
            if filename not in {"ships.json", "ship-items.json"}:
                raise ValueError("Unexpected snapshot filename")
            if hashlib.sha256((folder / filename).read_bytes()).hexdigest() != digest:
                raise ValueError(f"Snapshot checksum mismatch: {filename}")
        ships = json.loads((folder / "ships.json").read_text(encoding="utf-8"))
        raw_items = json.loads((folder / "ship-items.json").read_text(encoding="utf-8"))
        if not isinstance(ships, list) or not isinstance(raw_items, list) or not ships or not raw_items:
            raise ValueError("Catalogue must contain nonempty ship and component lists")
        self.ships = {s["ClassName"]: s for s in ships}
        self.items = {x["stdItem"]["ClassName"]: x["stdItem"] for x in raw_items if x.get("stdItem")}
        self.by_type = {k: [i for i in self.items.values() if kind(i) == k] for k in SWAPPABLE}
        self._options = {}

    def ship(self, query):
        exact = [s for key, s in self.ships.items() if key.casefold() == query.casefold()]
        if exact:
            return exact[0]
        matches = [s for s in self.ships.values() if query.casefold() in s["Name"].casefold()]
        # An exact, canonical class spelling wins over temporary variants sharing a display name.
        canonical = [s for s in matches if s["ClassName"].replace("_", " ").casefold() == query.casefold()]
        if len(canonical) == 1:
            return canonical[0]
        if len(matches) != 1:
            names = ", ".join(s["ClassName"] for s in matches[:12])
            raise ValueError(f"Ship is unknown or ambiguous: {query}. Use a class id. Matches: {names}")
        return matches[0]

    def options(self, ship, port, editable):
        key = (ship["ClassName"], port["PortId"])
        if key not in self._options:
            stock = port.get("ClassName")
            options = [stock] if stock in self.items else []
            if editable and kind(port) in SWAPPABLE:
                for item in self.by_type[kind(port)]:
                    name = item["ClassName"]
                    if name != stock and compatible(port, item) and item.get("Name", "").strip() not in {"", "<= PLACEHOLDER =>"}:
                        if not re.search(r"(?:_temp|_test|_npc|_pu_ai)(?:_|$)", name, re.I):
                            options.append(name)
            self._options[key] = tuple(sorted(options))
        return self._options[key]

    def list_ships(self, role=None):
        return sorted([{"id": s["ClassName"], "name": s["Name"], "role": s.get("Role"),
                        "crew": s.get("Crew"), "size": s.get("Size")}
                       for s in self.ships.values() if s.get("IsSpaceship") and
                       (not role or role.casefold() == s.get("Role", "").casefold()) and
                       not re.search(r"(?:_temp|_test|_npc|_display)(?:_|$)", s["ClassName"], re.I)],
                      key=lambda s: (s["name"], s["id"]))
