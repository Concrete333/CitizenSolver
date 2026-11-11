import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from citizensolver.engine import ShipModel
from citizensolver.equipment import normalize_equipment, offers_for, sync_equipment
from citizensolver.insights import stealth_profile, handling_profile
from citizensolver.optimizer import Search, optimize
from citizensolver.workbench import search_workbench
from tests.helpers import fixture


class EquipmentAndInsights(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.catalogue = fixture(self.temp.name)
        self.ship = self.catalogue.ship('TEST_Ship')

    def test_exact_identity_npc_price_and_report_provenance(self):
        items = [{'id': 1, 'uuid': 'ABC', 'name': 'Same name'}, {'id': 2, 'uuid': 'DEF', 'name': 'Same name'}]
        row = {'id_item': 1, 'price_buy': 200, 'terminal_name': 'NPC shop', 'terminal_is_player_owned': 0,
               'game_version': 'old-patch', 'date_modified': 123}
        prices = [row, {**row, 'id_item': 2, 'terminal_is_player_owned': 1}, {**row, 'price_buy': 0},
                  {**row, 'price_buy': float('nan')}, {**row, 'terminal_is_player_owned': None}]
        normalized = normalize_equipment(items, prices)
        self.assertEqual(list(normalized), ['abc'])
        self.assertEqual(len(normalized['abc']['offers']), 1)
        self.assertEqual(normalized['abc']['offers'][0]['game_version'], 'old-patch')
        self.assertFalse(offers_for({'UUID': 'DEF', 'Name': 'Same name'}, {'items': normalized}))
        self.assertTrue(offers_for({'UUID': 'ABC'}, {'items': normalized}))

    def test_failed_refresh_keeps_previous_cache(self):
        path = Path(self.temp.name) / 'equipment-market.json'
        path.write_text('{"old":true}')
        with patch('citizensolver.equipment.get_json', return_value={'status': 'ok', 'data': []}):
            with self.assertRaises(ValueError):
                sync_equipment(self.temp.name)
        self.assertEqual(path.read_text(), '{"old":true}')

    def test_shop_mode_retains_stock_and_excludes_unlisted_upgrades(self):
        market = {'downloaded_at': 'today', 'items': {}}
        report = optimize(self.catalogue, self.ship, Search(equipment_mode='shop'), market)
        self.assertTrue(report['results'])
        self.assertTrue(all(not r['swaps'] for r in report['results']))
        self.catalogue.items['quiet']['UUID'] = 'quiet-id'
        market['items']['quiet-id'] = {'offers': [{'shop': 'Test shop'}]}
        report = optimize(self.catalogue, self.ship, Search(equipment_mode='shop', locks={'p1':'quiet'}), market)
        self.assertTrue(all(r['swaps']['p1'] == 'quiet' for r in report['results']))
        with self.assertRaisesRegex(ValueError, 'NPC seller'):
            optimize(self.catalogue, self.ship, Search(equipment_mode='shop', locks={'p0':'cannon'}), market)
        with self.assertRaisesRegex(ValueError, 'Refresh'):
            optimize(self.catalogue, self.ship, Search(equipment_mode='shop'))

    def test_seed_and_locks_survive_grouped_and_individual_search(self):
        request = Search(goal='damage', seed_swaps={'p1':'quiet'}, locks={'p0':'laser'}, passes=2)
        results = optimize(self.catalogue, self.ship, request)['results']
        self.assertTrue(results)
        self.assertTrue(all(next(i for i in r['loadout'] if i['port']=='p0')['id']=='laser' for r in results))
        with self.assertRaisesRegex(ValueError, 'Unknown port'):
            optimize(self.catalogue, self.ship, Search(locks={'unknown':'laser'}))
        with self.assertRaisesRegex(ValueError, 'one ship'):
            search_workbench(self.catalogue, {'scope':'class','search':{'locks':{'p0':'laser'}}})

    def test_cross_section_multiplier_once_and_unknown_is_not_stealthy(self):
        self.ship['Armor']['SignalMultipliers']['CrossSection'] = .5
        s = stealth_profile(self.ship, 10, 20)
        self.assertEqual(s['axes'], {'X':250,'Y':100,'Z':500})
        self.assertAlmostEqual(s['ranking_signal'], 850/3)
        self.assertEqual(s['ranking_signal'], stealth_profile(self.ship, 5, 10)['ranking_signal'])
        self.ship['CrossSection'].pop('Y')
        self.assertIsNone(stealth_profile(self.ship, 10, 20)['ranking_signal'])
        self.assertFalse(optimize(self.catalogue, self.ship, Search(goal='custom',weights={'stealth':100}))['results'])

    def test_handling_rewards_braking_and_requires_acceleration(self):
        rates = {'Pitch':50,'Yaw':40,'Roll':120}
        a = handling_profile(self.ship, rates, {}, {'Scm':200})
        self.ship['FlightCharacteristics']['Acceleration']['Raw']['Retro'] = 80
        b = handling_profile(self.ship, rates, {}, {'Scm':200})
        self.assertGreater(b['score'], a['score'])
        self.assertLess(b['scm_to_zero_seconds'], a['scm_to_zero_seconds'])
        other = copy.deepcopy(self.ship)
        other.update(ClassName='TEST_WeakBrakes', Name='Weak brakes')
        other['FlightCharacteristics']['Acceleration']['Raw']['Retro'] = 5
        self.catalogue.ships[other['ClassName']] = other
        comparison = search_workbench(self.catalogue, {'scope':'class', 'goal':'handling'})
        self.assertEqual(comparison['results'][0]['ship']['id'], 'TEST_Ship')
        self.ship['FlightCharacteristics'].pop('Acceleration')
        self.assertIsNone(ShipModel(self.catalogue, self.ship).evaluate()['metrics']['maneuverability_score'])
        self.assertFalse(optimize(self.catalogue, self.ship, Search(goal='handling'))['results'])
