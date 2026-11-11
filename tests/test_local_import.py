import copy
import hashlib
from pathlib import Path
import tempfile
import unittest

from citizensolver.catalogue import Catalogue, write_json
from citizensolver.engine import weapon_stats
from citizensolver.local_import import import_local, sequence_entries
from helpers import fixture


class LocalImport(unittest.TestCase):
    def test_single_xml_entry_wrapper_matches_multiple_entry_shape(self):
        entry = {"delay": 200, "unit": "RPM", "repetitions": 1,
                 "weaponAction": {"SWeaponActionFireSingleParams": {}}}
        self.assertEqual(sequence_entries({"sequenceEntries": {"SWeaponSequenceEntryParams": entry}}),
                         sequence_entries({"sequenceEntries": [entry]}))

    def test_local_build_provenance_sequence_and_failed_activation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "active").mkdir()
            previous = fixture(root / "active")
            export, game, unpacked = root / "export", root / "LIVE", root / "unpacked"
            write_json(game / "build_manifest.id", {"Data": {"Branch": "sc-alpha-9.8.7", "RequestedP4ChangeNum": "123"}})
            (unpacked / "Data").mkdir(parents=True)
            (unpacked / "Data/Game2.dcb").write_bytes(b"synthetic extraction evidence")
            write_json(export / "ships.json", list(previous.ships.values()))
            items = copy.deepcopy(list(previous.items.values()))
            laser = next(i for i in items if i["ClassName"] == "laser")
            laser["UUID"] = "synthetic-weapon-id"
            laser["Weapon"]["Modes"][0].update(FireType="sequence", SequenceMode="Looping", RoundsPerMinute=900)
            raw = {"Raw": {"Entity": {"ClassName": "laser", "__ref": "synthetic-weapon-id", "Components": {
                "SCItemWeaponComponentParams": {"fireActions": {"SWeaponActionSequenceParams": {
                    "mode": "Looping", "sequenceEntries": [
                        {"delay": delay, "unit": "RPM", "repetitions": 1, "weaponAction": {
                            "SWeaponActionFireSingleParams": {"heatPerShot": 0, "launchParams": {
                                "SProjectileLauncher": {"ammoCost": 1, "pelletCount": 1, "projectileType": "Primary", "damageMultiplier": 1}}}}}
                        for delay in [600, 300]]}}}}}}}
            write_json(export / "items/laser.json", raw)
            write_json(export / "ship-items.json", [{"stdItem": i} for i in items])
            result = import_local(export, game, unpacked, "b" * 40, root / "active")
            loaded = Catalogue(root / "active")
            self.assertEqual(loaded.manifest["game_version"], "9.8.7-LIVE.123")
            self.assertEqual(result["game2_sha256"], hashlib.sha256(b"synthetic extraction evidence").hexdigest())
            self.assertIn("laser", result["sequence_record_sha256"])
            self.assertAlmostEqual(weapon_stats(loaded.items["laser"])["rounds_per_minute"], 400)
            original_manifest = (root / "active/manifest.json").read_bytes()
            raw["Raw"]["Entity"]["__ref"] = "wrong-weapon"
            write_json(export / "items/laser.json", raw)
            with self.assertRaisesRegex(ValueError, "identity mismatch"):
                import_local(export, game, unpacked, "b" * 40, root / "active")
            self.assertEqual((root / "active/manifest.json").read_bytes(), original_manifest)
