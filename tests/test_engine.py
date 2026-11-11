import copy
import math
import tempfile
import unittest

from citizensolver.catalogue import compatible, walk_ports
from citizensolver.engine import ModelError, ShipModel, weapon_stats
from citizensolver.optimizer import Search, optimize
from helpers import fixture, gun


class Weapons(unittest.TestCase):
    def test_energy_cycle_and_power(self):
        full = weapon_stats(gun(), duration=34)
        self.assertAlmostEqual(full["sustained_dps"], 1000 / 17)
        self.assertAlmostEqual(full["damage_over_duration"], 2000)
        low = weapon_stats(gun(), power_ratio=.5)
        self.assertEqual(low["shots_per_cycle"], 5)
        self.assertAlmostEqual(low["sustained_dps"], 500 / 12)
        self.assertEqual(low["burst_dps"], full["burst_dps"])

    def test_fractional_capacitor_load_rounds_and_recharges_at_allocated_power(self):
        weapon = gun()
        weapon["Weapon"]["Capacitor"].update(MaxAmmoLoad=23, MaxRegenPerSec=7, Cooldown=.2)
        low = weapon_stats(weapon, power_ratio=1 / 2.8)
        medium = weapon_stats(weapon, power_ratio=2 / 2.8)
        self.assertEqual(low["shots_per_cycle"], 8)
        self.assertEqual(medium["shots_per_cycle"], 16)
        self.assertAlmostEqual(low["recovery_seconds"], .2 + 8 / 2.5)
        self.assertAlmostEqual(medium["recovery_seconds"], .2 + 16 / 5)

    def test_ballistic_ammo_exhaustion(self):
        stats = weapon_stats(gun(energy=False, ammo=12), duration=120)
        self.assertEqual(stats["burst_dps"], 100)
        self.assertEqual(stats["damage_over_duration"], 1200)
        self.assertEqual(stats["duration_dps"], 10)

    def test_looping_sequence_uses_all_delays_not_first_inner_fire_rate(self):
        weapon = gun()
        mode = weapon["Weapon"]["Modes"][0]
        mode.update(FireType="sequence", SequenceMode="Looping", RoundsPerMinute=900,
                    SequenceEntries=[{"Delay": d, "Unit": "RPM", "Repetitions": n, "FireType": "single",
                                      "AmmoPerShot": 1, "PelletsPerShot": 1, "ProjectileType": "Primary",
                                      "DamageMultiplier": 1, "HeatPerShot": 0}
                                     for d, n in [(600, 1), (300, 2)]])
        result = weapon_stats(weapon)
        self.assertAlmostEqual(result["rounds_per_minute"], 360)
        self.assertAlmostEqual(result["burst_dps"], 600)
        mode["SequenceMode"] = "Automatically"
        self.assertAlmostEqual(weapon_stats(weapon)["rounds_per_minute"], 360)
        mode["SequenceEntries"][1]["Unit"] = "Seconds"
        mode["SequenceEntries"][1]["Delay"] = .2
        self.assertAlmostEqual(weapon_stats(weapon)["rounds_per_minute"], 360)
        mode["SequenceEntries"][1]["DamageMultiplier"] = 2
        with self.assertRaisesRegex(ModelError, "Mixed projectiles"):
            weapon_stats(weapon)
        del mode["SequenceEntries"]
        with self.assertRaisesRegex(ModelError, "Sequence timing"):
            weapon_stats(weapon)

    def test_distortion_not_hull_damage(self):
        stats = weapon_stats(gun(alpha=0, distortion=150))
        self.assertEqual(stats["burst_dps"], 0)
        self.assertEqual(stats["alpha"], 0)
        self.assertEqual(stats["distortion_burst_dps"], 150)

    def test_heat_cycle(self):
        weapon = gun(energy=False, ammo=1000)
        weapon["Weapon"]["Heat"] = {"ShotsToOverheat": 5, "OverheatFixTime": 10}
        stats = weapon_stats(weapon, duration=30)
        self.assertAlmostEqual(stats["sustained_dps"], 500 / 15)
        self.assertEqual(stats["damage_over_duration"], 1000)

    def test_heat_threshold_preserves_fractional_cycle_time(self):
        weapon = gun(energy=False, ammo=1000)
        weapon["Weapon"]["Heat"] = {"ShotsToOverheat": 5, "HeatPerShot": 3,
                                   "OverheatTemperature": 17, "OverheatFixTime": 10}
        stats = weapon_stats(weapon)
        self.assertAlmostEqual(stats["fire_seconds"], 17 / 3)
        self.assertEqual(stats["shots_per_cycle"], 6)
        self.assertAlmostEqual(stats["sustained_dps"], 600 / (17 / 3 + 10))
        # The final overheat shot is counted at the threshold; cooling adds no damage.
        at_overheat = weapon_stats(weapon, duration=17 / 3)
        during_cooling = weapon_stats(weapon, duration=8)
        self.assertEqual(at_overheat["damage_over_duration"], 600)
        self.assertEqual(during_cooling["damage_over_duration"], 600)

    def test_missing_ammo_is_not_infinite(self):
        with self.assertRaises(ModelError):
            weapon_stats(gun(energy=False, ammo=0))

    def test_charged_weapon_not_silently_treated_as_repeater(self):
        weapon = gun()
        weapon["Weapon"]["Modes"][0]["FireType"] = "charged"
        with self.assertRaises(ModelError):
            weapon_stats(weapon)


class Compatibility(unittest.TestCase):
    def test_size_type_and_bespoke_restrictions(self):
        port = {"MinSize": 1, "MaxSize": 1, "CompatibleTypes": [{"Type": "WeaponGun", "SubTypes": ["Gun"]}], "RequiredTags": ["Meteor"]}
        ordinary = gun()
        self.assertFalse(compatible(port, ordinary))
        bespoke = {**ordinary, "Tags": ["$Meteor"], "RequiredTags": ["Meteor"]}
        self.assertTrue(compatible(port, bespoke))
        self.assertFalse(compatible({**port, "RequiredTags": []}, bespoke))
        self.assertFalse(compatible(port, {**bespoke, "Size": 2}))
        self.assertFalse(compatible(port, {**bespoke, "Type": "WeaponGun.Rocket"}))

    def test_editable_gun_inside_locked_gimbal(self):
        ports = [{"Editable": False, "EditableChildren": False, "Loadout": [{"Editable": True}]}]
        self.assertEqual([editable for _, editable in walk_ports(ports)], [False, True])


class Models(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.catalogue = fixture(self.temp.name)
        self.ship = self.catalogue.ship("TEST_Ship")
        self.model = ShipModel(self.catalogue, self.ship)

    def test_stock_and_explicit_replay(self):
        r = self.model.evaluate()
        self.assertTrue(r["feasible"], r["violations"])
        replay = self.model.evaluate(pips=r["power"]["allocation"])
        self.assertEqual(r["metrics"], replay["metrics"])

    def test_invalid_swaps_and_pips(self):
        with self.assertRaises(ValueError):
            self.model.evaluate({"p0": "cooler"})
        with self.assertRaises(ValueError):
            self.model.evaluate({"not-a-port": "laser"})
        with self.assertRaises(ValueError):
            self.model.evaluate(pips={"weapons": 500})

    def test_locked_component_cannot_be_swapped(self):
        self.ship["Loadout"][0]["Editable"] = False
        self.catalogue._options.clear()
        with self.assertRaises(ValueError):
            ShipModel(self.catalogue, self.ship).evaluate({"p0": "cannon"})

    def test_underpowered_ship_is_not_feasible(self):
        self.catalogue.items["plant"]["ResourceNetwork"]["Generation"]["Power"] = 1
        r = self.model.evaluate()
        self.assertFalse(r["feasible"])
        self.assertTrue(any("Power demand" in text for text in r["violations"]))

    def test_mixed_guns_share_power_and_signatures_follow_pips(self):
        ballistic = self.catalogue.items["cannon"]
        ballistic["ResourceNetwork"]["Usage"]["Power"] = {"Minimum": .8, "Maximum": .8}
        port = copy.deepcopy(self.ship["Loadout"][0])
        port.update(PortId="ballistic", ClassName="cannon", HardpointName="ballistic", Path=["ballistic"])
        self.ship["Loadout"].append(port)
        self.ship["Weaponry"]["FixedWeapons"]["Weapons"].append({"ClassName": "cannon"})
        shield = self.catalogue.items["shield"]
        shield["ResourceNetwork"]["Usage"]["Coolant"] = {"Minimum": .7, "Maximum": 3}
        shield["ResourceNetwork"]["States"] = [{"Name": "Online", "PowerRanges": [
            {"Start": 1, "Modifier": .7, "RegisterRange": 1}]}]
        model = ShipModel(self.catalogue, self.ship)
        low = model.evaluate(profile="stealth")
        laser = next(w for w in low["weapons"] if w["id"] == "laser")
        self.assertAlmostEqual(laser["power_ratio"], 1 / 2.8)
        self.assertEqual(laser["shots_per_cycle"], 4)
        self.assertAlmostEqual(low["cooling"]["demand"], 4.7)
        self.assertAlmostEqual(low["metrics"]["ir"], 47)
        full = model.evaluate(pips={**low["power"]["allocation"], "weapons": 3})
        # Only 1.8 of the extra two allocated pips are consumed by the guns.
        self.assertAlmostEqual(full["metrics"]["em"] - low["metrics"]["em"], 1000 * 1.8 / 12 + 200 * 2 / 3)
        self.assertAlmostEqual(full["cooling"]["demand"], 6.5)

    def test_manned_guns_do_not_count_as_pilot_damage(self):
        p = copy.deepcopy(self.ship["Loadout"][0])
        p.update(PortId="turretgun", Path=["turret", "gun"])
        self.ship["Loadout"].append(p)
        self.ship["Weaponry"]["Turrets"] = [{"HardpointName": "turret", "IsPilotSlaveable": False}]
        model = ShipModel(self.catalogue, self.ship)
        self.assertEqual(len(model.evaluate()["weapons"]), 1)

    def test_long_engagement_prefers_recharge_to_tiny_magazine(self):
        result = optimize(self.catalogue, self.ship, Search(goal="pve", duration=300, limit=1))
        self.assertTrue(result["results"])
        guns = result["results"][0]["weapons"]
        self.assertEqual(guns[0]["id"], "laser")

    def test_damage_floor_and_hard_constraints(self):
        result = optimize(self.catalogue, self.ship, Search(goal="stealth", damage_floor=.9))
        floor = result["search"]["best_feasible_duration_dps_found"] * .9
        self.assertTrue(all(r["metrics"]["duration_dps"] >= floor - 1e-8 for r in result["results"]))
        impossible = optimize(self.catalogue, self.ship, Search(min_shield=100000))
        self.assertEqual(impossible["results"], [])
        too_far = optimize(self.catalogue, self.ship, Search(min_range=3000))
        self.assertEqual(too_far["results"], [])

    def test_bounded_and_deterministic_search(self):
        request = Search(max_evaluations=10)
        a = optimize(self.catalogue, self.ship, request)
        b = optimize(self.catalogue, self.ship, request)
        self.assertLessEqual(a["search"]["evaluations"], 10)
        self.assertTrue(a["search"]["evaluation_limit_reached"])
        self.assertEqual(a["results"], b["results"])

    def test_invalid_search_inputs(self):
        for values in ({"beam": 0}, {"duration": math.nan}, {"damage_floor": 2}, {"goal": "unknown"}, {"min_dps": -1}):
            with self.assertRaises(ValueError):
                Search(**values)
