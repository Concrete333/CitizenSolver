"""Locally cached public FleetYards reference prices and landing size classes."""
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from .catalogue import DEFAULT_DATA, get_json, write_json

HANGARS = ("Small", "Medium", "Large", "Extra Large")
# Dock classes smaller than Small also fit a Small hangar. These are source
# classifications, not the unrelated numeric ship-size field in scunpacked.
DOCK_TO_HANGAR = {"extra_extra_small": "Small", "extra_small": "Small", "small": "Small",
                  "medium": "Medium", "large": "Large", "extra_large": "Extra Large"}


def positive(value):
    return value if type(value) in (int, float) and math.isfinite(value) and value > 0 else None


def normalize(rows):
    records = {}
    for row in rows:
        identity = row.get("scIdentifier")
        if not identity:
            continue
        locations = [{"name": p.get("location"), "price": positive(p.get("price")),
                      "updated_at": p.get("updatedAt")} for p in (row.get("availability") or {}).get("soldAt", [])]
        prices = [p["price"] for p in locations if p["price"] is not None]
        dock = (row.get("metrics") or {}).get("dockSize")
        records[identity.casefold()] = {
            "usd": positive(row.get("pledgePrice")), "auec": min(prices) if prices else None,
            "in_game_listing": bool(prices), "locations": locations,
            "hangar": DOCK_TO_HANGAR.get(dock), "dock_class": dock,
            "hangar_basis": "FleetYards dock class; smaller classes grouped into Small. Landing configuration and location restrictions still apply.",
            "source": "FleetYards", "url": (row.get("links") or {}).get("self") or "https://fleetyards.net",
            "updated_at": row.get("lastUpdatedAt"), "pledge_on_sale": row.get("onSale"),
        }
    return records


def sync_market(folder=DEFAULT_DATA):
    rows, page = [], 1
    while True:
        response = get_json(f"https://api.fleetyards.net/v1/models?perPage=240&page={page}")
        rows.extend(response["items"])
        if page >= response["meta"]["pagination"]["totalPages"]:
            break
        page += 1
        if page > 20:
            raise ValueError("Unexpected market pagination")
    records = normalize(rows)
    if not records:
        raise ValueError("Empty market response; previous cache retained")
    result = {"source": "https://api.fleetyards.net/v1/models", "downloaded_at": datetime.now(timezone.utc).isoformat(),
              "ships": records}
    write_json(Path(folder) / "market.json", result)
    return result


def read_market(folder=DEFAULT_DATA):
    path = Path(folder) / "market.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"ships": {}, "downloaded_at": None}


def limits(body):
    for key in ("max_usd", "max_auec"):
        value = body.get(key)
        if value is not None and (type(value) not in (int, float) or not math.isfinite(value) or value < 0):
            raise ValueError("Budgets must be finite nonnegative numbers")
    if body.get("hangar") not in (None, "", *HANGARS):
        raise ValueError("Unknown hangar size")
    if type(body.get("require_ingame", False)) is not bool:
        raise ValueError("In-game availability must be true or false")


def exclusion(record, body):
    for currency in ("usd", "auec"):
        ceiling = body.get("max_" + currency)
        if ceiling is not None:
            if record.get(currency) is None:
                return f"No recorded {currency.upper()} price"
            if record[currency] > ceiling:
                return f"Over the {currency.upper()} budget"
    if body.get("require_ingame") and not record.get("in_game_listing"):
        return "No recorded in-game shop listing"
    maximum = body.get("hangar")
    if maximum:
        if record.get("hangar") not in HANGARS:
            return "Hangar fit is not known"
        if HANGARS.index(record["hangar"]) > HANGARS.index(maximum):
            return "Requires a larger hangar"
    return None
