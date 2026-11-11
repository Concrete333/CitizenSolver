import copy
import json
import tempfile
import time
import unittest
from http.server import ThreadingHTTPServer
from threading import Thread
from urllib.request import Request, urlopen

from citizensolver.engine import ShipModel
from citizensolver.market import exclusion, limits, normalize
from citizensolver.optimizer import Search, optimize
from citizensolver.server import handler
from citizensolver.workbench import search_workbench
from tests.helpers import fixture


class Workbench(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.catalogue = fixture(self.temp.name)
        self.ship = self.catalogue.ship("TEST_Ship")
        self.ship.update(Cargo=6, Health=1000, Armor={**self.ship["Armor"], "Health": 100})

    def test_weights_reject_invalid_budgets(self):
        for weights in ({"firepower": 101}, {"stealth": -5, "firepower": 105}, {"unknown": 100}, {"firepower": float('nan')}, {}, {"hull": True}):
            with self.subTest(weights=weights), self.assertRaises(ValueError):
                Search(goal="custom", weights=weights)

    def test_custom_priority_changes_the_selected_build(self):
        loud = copy.deepcopy(self.catalogue.items["laser"])
        loud.update(ClassName="loud", Name="Loud gun", Emission={"Em": {"Maximum": 50000}, "Ir": 1000})
        loud["Weapon"]["Modes"][0]["AlphaEnergy"] = 10000
        self.catalogue.items["loud"] = loud
        self.catalogue.by_type["WeaponGun"].append(loud)
        damage = optimize(self.catalogue, self.ship, Search(goal="custom", weights={"firepower": 100}, limit=1))
        stealth = optimize(self.catalogue, self.ship, Search(goal="custom", weights={"stealth": 100}, limit=1))
        self.assertGreater(damage["results"][0]["metrics"]["duration_dps"], stealth["results"][0]["metrics"]["duration_dps"])
        self.assertGreater(damage["results"][0]["metrics"]["em"], stealth["results"][0]["metrics"]["em"])

    def test_unknown_prioritized_stat_excludes_build(self):
        self.ship.pop("Cargo")
        r = optimize(self.catalogue, self.ship, Search(goal="custom", weights={"cargo":100}, limit=1))
        self.assertEqual(r["results"], [])

    def test_unarmed_ship_can_be_evaluated_for_noncombat_goal(self):
        self.ship["Loadout"] = [p for p in self.ship["Loadout"] if p["PortId"] != "p0"]
        self.ship["Weaponry"] = {}
        model = ShipModel(self.catalogue, self.ship)
        evaluated = model.evaluate()
        self.assertEqual(evaluated["metrics"]["duration_dps"], 0)
        self.assertNotIn("weapons", evaluated["power"]["allocation"])
        self.assertTrue(optimize(self.catalogue, self.ship, Search(goal="shields"))["results"])

    def test_market_identity_and_missing_prices_are_not_free(self):
        records = normalize([{"scIdentifier":"TEST_Ship", "pledgePrice":100, "price":25,
                              "metrics":{"size":"small", "dockSize":"large"},
                              "availability":{"soldAt":[{"location":"Shop", "price":12345}]}}])
        record = records["test_ship"]
        self.assertEqual(record["hangar"], "Large")
        self.assertEqual(record["auec"], 12345)
        self.assertIn("larger", exclusion(record,{"hangar":"Medium"}))
        self.assertIsNone(exclusion(record,{"hangar":"Extra Large", "max_usd":100, "max_auec":12345}))
        self.assertIsNotNone(exclusion(record,{"max_usd":100,"max_auec":10000}))
        self.assertIsNotNone(exclusion({}, {"max_auec":1000000}))
        no_listing = normalize([{"scIdentifier":"x","price":25}])["x"]
        self.assertIsNone(no_listing["auec"])
        self.assertIsNotNone(exclusion(no_listing, {"require_ingame":True}))
        with self.assertRaises(ValueError):
            limits({"max_usd":float('nan')})

    def test_filters_apply_to_specific_ship_and_class(self):
        market = {"ships":{"test_ship":{"usd":100,"auec":1000,"hangar":"Small","in_game_listing":True}}}
        for scope in ("ship", "class"):
            result = search_workbench(self.catalogue, {"scope":scope,"ship":"TEST_Ship","goal":"cargo","max_usd":99}, market=market)
            self.assertEqual(result["results"], [])
            self.assertEqual(result["ships_eligible"], 0)
            self.assertIn("budget", result["skipped"][0]["reason"])

    def test_cargo_compares_ship_capacity_not_ore_or_generic_size(self):
        with self.assertRaisesRegex(ValueError, "combat constraints"):
            search_workbench(self.catalogue, {"scope":"class","goal":"cargo","search":{"min_range":1000}})
        other = copy.deepcopy(self.ship)
        other.update(ClassName="TEST_Hauler",Name="Test Hauler",Cargo=100,Size=1)
        self.ship["Size"] = 9
        self.catalogue.ships[other["ClassName"]] = other
        market = {"ships":{"test_ship":{"hangar":"Small"},"test_hauler":{"hangar":"Large"}}}
        result = search_workbench(self.catalogue, {"scope":"class","goal":"cargo"}, market=market)
        self.assertEqual(result["results"][0]["ship"]["id"], "TEST_Hauler")
        limited = search_workbench(self.catalogue, {"scope":"class","goal":"cargo","hangar":"Small"}, market=market)
        self.assertEqual([r["ship"]["id"] for r in limited["results"]], ["TEST_Ship"])

    def test_browser_assets_and_background_search(self):
        server = ThreadingHTTPServer(("127.0.0.1",0), handler(self.catalogue, data_folder=self.temp.name))
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        try:
            with urlopen(base + "/") as response:
                self.assertIn(b'Find my fits', response.read())
            with urlopen(base + "/api/options") as response:
                self.assertIn("hangars", json.load(response))
            request = Request(base + "/api/search", data=json.dumps({"scope":"ship","ship":"TEST_Ship","goal":"cargo"}).encode(),headers={"Content-Type":"application/json"})
            with urlopen(request) as response:
                self.assertEqual(response.status,202)
                job = json.load(response)
            deadline = time.monotonic()+5
            while time.monotonic() < deadline:
                with urlopen(base + "/api/jobs/" + job["id"]) as response:
                    state = json.load(response)
                if state["status"] != "running":
                    break
                time.sleep(.01)
            self.assertEqual(state["status"], "complete")
            self.assertEqual(state["result"]["results"][0]["metrics"]["cargo_scu"], 6)
        finally:
            server.shutdown(); thread.join(timeout=5); server.server_close()


if __name__ == "__main__":
    unittest.main()
