"""Activate a complete ScDataDumper export from a locally installed game build."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
import re

from .catalogue import Catalogue, DEFAULT_DATA, write_json


def sequence_entries(sequence):
    entries = []
    raw = sequence.get("sequenceEntries") or []
    if isinstance(raw, dict):
        raw = raw.get("SWeaponSequenceEntryParams", raw)
        if isinstance(raw, dict):
            raw = [raw]
    for entry in raw:
        entry = entry.get("SWeaponSequenceEntryParams", entry)
        actions = entry.get("weaponAction") or {}
        action = actions.get("SWeaponActionFireSingleParams")
        if not isinstance(action, dict):
            entries.append({"FireType": "unsupported"})
            continue
        launcher = (action.get("launchParams") or {}).get("SProjectileLauncher") or {}
        entries.append({"Delay": entry.get("delay"), "Unit": entry.get("unit"),
                        "Repetitions": entry.get("repetitions"), "FireType": "single",
                        "AmmoPerShot": launcher.get("ammoCost", 1),
                        "PelletsPerShot": launcher.get("pelletCount", 1),
                        "ProjectileType": launcher.get("projectileType"),
                        "DamageMultiplier": launcher.get("damageMultiplier", 1),
                        "HeatPerShot": action.get("heatPerShot", 0)})
    return entries


def import_local(export_folder, game_folder, unpacked_folder, exporter_revision, folder=DEFAULT_DATA):
    """Import our own extraction, preserving its build stamp, hashes and sequence timing.

    Run the documented extraction/export against game_folder before calling this.
    Supplying a manifest cannot establish that arbitrary JSON came from that build.
    """
    export_folder, game_folder, unpacked_folder, folder = map(Path, (export_folder, game_folder, unpacked_folder, folder))
    build_bytes = (game_folder / "build_manifest.id").read_bytes()
    build = json.loads(build_bytes)["Data"]
    branch, change, channel = build["Branch"], build["RequestedP4ChangeNum"], game_folder.name.upper()
    if not re.fullmatch(r"sc-alpha-\d+\.\d+\.\d+", branch) or not str(change).isdigit() or channel not in {"LIVE", "PTU", "EPTU"}:
        raise ValueError("Cannot establish the installed game's version/channel")
    if not re.fullmatch(r"[0-9a-f]{40}", exporter_revision):
        raise ValueError("Record the exact ScDataDumper commit")
    dcb = unpacked_folder / "Data" / "Game2.dcb"
    with dcb.open("rb") as stream:
        dcb_hash = hashlib.file_digest(stream, "sha256").hexdigest()
    ships = json.loads((export_folder / "ships.json").read_text(encoding="utf-8"))
    items = json.loads((export_folder / "ship-items.json").read_text(encoding="utf-8"))
    if not isinstance(ships, list) or not isinstance(items, list) or not ships or not items:
        raise ValueError("A complete nonempty ship and component export is required")
    sequence_hashes = {}
    for row in items:
        item = row.get("stdItem") or {}
        modes = [m for m in (item.get("Weapon") or {}).get("Modes", []) if m.get("FireType") == "sequence"]
        if not modes:
            continue
        name = item["ClassName"]
        if not re.fullmatch(r"[\w-]+", name):
            raise ValueError("Invalid component class name")
        raw_bytes = (export_folder / "items" / (name.lower() + ".json")).read_bytes()
        entity = json.loads(raw_bytes)["Raw"]["Entity"]
        if entity["ClassName"] != name or entity["__ref"] != item["UUID"]:
            raise ValueError(f"Raw record identity mismatch: {name}")
        actions = entity.get("Components", {}).get("SCItemWeaponComponentParams", {}).get("fireActions", {})
        sequences = actions.get("SWeaponActionSequenceParams", [])
        if isinstance(sequences, dict):
            sequences = [sequences]
        if len(sequences) != len(modes):
            raise ValueError(f"Cannot map sequence modes to raw actions: {name}")
        for mode, sequence in zip(modes, sequences):
            mode["SequenceMode"] = sequence.get("mode")
            mode["SequenceEntries"] = sequence_entries(sequence)
        sequence_hashes[name] = hashlib.sha256(raw_bytes).hexdigest()
    contents = {"ships.json": ships, "ship-items.json": items}
    encoded = {name: (json.dumps(data, ensure_ascii=False, allow_nan=False, indent=2) + "\n").encode("utf-8")
               for name, data in contents.items()}
    hashes = {name: hashlib.sha256(data).hexdigest() for name, data in encoded.items()}
    version = f"{branch.removeprefix('sc-alpha-')}-{channel}.{change}"
    revision = hashlib.sha1(json.dumps([version, dcb_hash, hashes], sort_keys=True).encode()).hexdigest()
    manifest = {"source": "Local Star Citizen client / ScDataDumper", "revision": revision,
                "game_version": version, "downloaded_at": datetime.now(timezone.utc).isoformat(),
                "sha256": hashes, "build_manifest": build,
                "build_manifest_sha256": hashlib.sha256(build_bytes).hexdigest(),
                "game2_sha256": dcb_hash, "exporter_revision": exporter_revision,
                "sequence_record_sha256": sequence_hashes}
    snapshot = folder / revision
    snapshot.mkdir(parents=True, exist_ok=True)
    for name, data in encoded.items():
        (snapshot / name).write_bytes(data)
    Catalogue(snapshot, manifest=manifest)
    write_json(snapshot / "manifest.json", manifest)
    write_json(folder / "manifest.json", manifest)
    return manifest
