"""Synthetic data only. Tests never read the user's downloaded catalogue."""
import json
from pathlib import Path
from citizensolver.catalogue import Catalogue


REVISION = "a" * 40


def item(name, typ, size=1, power=1, minimum=1, em=100, **extras):
    return {"ClassName": name, "Name": name, "Type": typ + ".Gun" if typ == "WeaponGun" else typ + ".UNDEFINED",
            "Size": size, "Emission": {"Em": {"Maximum": em}, "Ir": 0},
            "ResourceNetwork": {"Usage": {"Power": {"Minimum": minimum, "Maximum": power}}}, **extras}


def gun(name="laser", alpha=100, distortion=0, energy=True, ammo=100, size=1):
    g = item(name, "WeaponGun", size, power=2 if energy else .1, minimum=0 if energy else .1)
    g["Ammunition"] = {"Capacity": ammo if not energy else 0, "Speed": 1000, "Range": 2000}
    g["Weapon"] = {"EffectiveRange": 2000,
                   "Modes": [{"FireType": "single", "RoundsPerMinute": 60, "AmmoPerShot": 1,
                              "AlphaEnergy": alpha if energy else 0,
                              "AlphaPhysical": 0 if energy else alpha, "AlphaDistortion": distortion}]}
    if energy:
        g["Weapon"]["Capacitor"] = {"MaxAmmoLoad": 10, "MaxRegenPerSec": 2, "Cooldown": 2}
    return g


def fixture(folder):
    laser = gun()
    cannon = gun("cannon", alpha=180, energy=False, ammo=15)
    power = item("plant", "PowerPlant", power=0, minimum=0, em=1000)
    power["ResourceNetwork"]["Generation"] = {"Power": 12}
    quiet = item("quiet", "PowerPlant", power=0, minimum=0, em=200)
    quiet["ResourceNetwork"]["Generation"] = {"Power": 10}
    cooler = item("cooler", "Cooler")
    cooler["ResourceNetwork"]["Generation"] = {"Coolant": 100}
    cooler["Emission"]["Ir"] = 1000
    shield = item("shield", "Shield", power=3, Shield={"MaxShieldHealth": 1000, "MaxShieldRegen": 100})
    flight = item("flight", "FlightController", power=4,
                  Ifcs={"Pitch": 50, "Yaw": 40, "Roll": 120, "PitchBoosted": 60, "YawBoosted": 48, "RollBoosted": 144})
    items = [laser, cannon, power, quiet, cooler, shield, flight]
    fitted = [laser, power, cooler, shield, flight]
    ports = [{"PortId": f"p{n}", "HardpointName": f"slot{n}", "ClassName": i["ClassName"],
              "Type": i["Type"], "Editable": True, "MinSize": 1, "MaxSize": 1,
              "CompatibleTypes": [{"Type": i["Type"].split('.')[0]}], "Path": [f"slot{n}"]}
             for n, i in enumerate(fitted)]
    ship = {"ClassName": "TEST_Ship", "Name": "Test Ship", "Role": "Medium Fighter", "IsSpaceship": True,
            "Crew": 1, "Loadout": ports, "PowerPools": {"WeaponGun": {"Size": 4}},
            "Weaponry": {"FixedWeapons": {"Weapons": [{"ClassName": "laser"}]}},
            "Armor": {"SignalMultipliers": {"Electromagnetic": 1, "Infrared": 1}},
            "CrossSection": {"X": 500, "Y": 200, "Z": 1000}}
    ship["FlightCharacteristics"] = {"Acceleration": {"Raw": {"Main": 80, "Retro": 40}}}
    root = Path(folder)
    snapshot = root / REVISION
    snapshot.mkdir()
    (snapshot / "ships.json").write_text(json.dumps([ship]), encoding="utf-8")
    (snapshot / "ship-items.json").write_text(json.dumps([{"stdItem": i} for i in items]), encoding="utf-8")
    (root / "manifest.json").write_text(json.dumps({"revision": REVISION, "game_version": "synthetic", "source": "test"}), encoding="utf-8")
    return Catalogue(root)
