"""Recorded NPC component sellers, joined to game items by UUID, never by name."""
from datetime import datetime, timezone
import math
from pathlib import Path

from .catalogue import DEFAULT_DATA, get_json, write_json

API = "https://api.uexcorp.uk/2.0/"
CATEGORIES = {"Coolers", "Power Plants", "Shield Generators", "Flight Blade", "Radar", "Life Support Generator"}


def read_equipment(folder=DEFAULT_DATA):
    path = Path(folder) / "equipment-market.json"
    if not path.exists():
        return {"source": "UEX", "downloaded_at": None, "items": {}}
    import json
    return json.loads(path.read_text(encoding="utf-8"))


def normalize_equipment(items, prices):
    by_id = {i["id"]: i for i in items if i.get("uuid")}
    result = {}
    for row in prices:
        item = by_id.get(row.get("id_item"))
        price = row.get("price_buy")
        if (not item or type(price) not in (int, float) or not math.isfinite(price) or price <= 0
                or row.get("terminal_is_player_owned") != 0 or not row.get("terminal_name")):
            continue
        key = item["uuid"].casefold()
        offer = {"shop": row["terminal_name"], "system": row.get("star_system_name"),
                 "price": price, "game_version": row.get("game_version"),
                 "reported_at": row.get("date_modified"), "source_id": row.get("id")}
        result.setdefault(key, {"name": item.get("name"), "offers": []})["offers"].append(offer)
    for item in result.values():
        item["offers"].sort(key=lambda r: (r["price"], r["shop"]))
    return result


def sync_equipment(folder=DEFAULT_DATA):
    def read(route):
        response = get_json(API + route)
        if response.get("status") != "ok" or not isinstance(response.get("data"), list):
            raise ValueError("UEX component records could not be read; previous cache retained")
        return response["data"]
    categories = read("categories")
    ids = [c["id"] for c in categories if c.get("name") in CATEGORIES
           or (c.get("section") == "Vehicle Weapons" and c.get("name") == "Guns")]
    if not ids:
        raise ValueError("No supported component categories in UEX")
    items, prices = [], []
    for category in ids:
        items.extend(read(f"items?id_category={category}"))
        prices.extend(read(f"items_prices?id_category={category}"))
    normalized = normalize_equipment(items, prices)
    if not normalized:
        raise ValueError("No NPC purchase listings returned; previous cache retained")
    result = {"source": "UEX", "source_url": "https://uexcorp.space/api/documentation/",
              "downloaded_at": datetime.now(timezone.utc).isoformat(), "items": normalized,
              "note": "Recorded NPC listings, not live stock. Individual report patches and dates may be older than the active game build."}
    write_json(Path(folder) / "equipment-market.json", result)
    return result


def offers_for(item, market):
    return market.get("items", {}).get(str(item.get("UUID", "")).casefold(), {}).get("offers", [])


def annotate_equipment(result, catalogue, market):
    for row in result.get("loadout", []):
        offers = offers_for(catalogue.items[row["id"]], market)
        row["purchase"] = {"status": "stock" if not row["changed"] else "listed" if offers else "unknown",
                           "offers": offers}
    result["equipment_source"] = {k: v for k, v in market.items() if k != "items"}
    return result
