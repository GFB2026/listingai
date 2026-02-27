"""Market data enrichment for AI-generated content.

Matches listings to local market statistics by city, county, or zip code.
Market data is stored in Tenant.settings["market_data"]["areas"] as a list
of area objects, each with match criteria and stats.

Example tenant.settings:
{
    "market_data": {
        "areas": [
            {
                "name": "Fort Lauderdale Beach",
                "zip_codes": ["33308", "33304"],
                "cities": ["Fort Lauderdale"],
                "stats": {
                    "median_price": 485000,
                    "median_price_yoy": 4.2,
                    "median_dom": 52,
                    "months_supply": 5.8,
                    "avg_price_per_sqft": 385
                }
            }
        ]
    }
}
"""

import structlog

logger = structlog.get_logger()


def lookup(listing_data: dict, market_areas: list[dict]) -> dict | None:
    """Find market data matching a listing's location.

    Matches by (in priority order):
    1. zip code
    2. city name
    3. county name
    4. "default" fallback

    Args:
        listing_data: Dict with address_city, address_zip, county fields.
        market_areas: List of area dicts from tenant settings.

    Returns:
        Matched area dict, or None if no match.
    """
    if not market_areas:
        return None

    city = (listing_data.get("address_city") or "").strip().lower()
    zip_code = (listing_data.get("address_zip") or "").strip()
    county = (listing_data.get("county") or "").strip().lower()

    by_zip: dict[str, dict] = {}
    by_city: dict[str, dict] = {}
    by_county: dict[str, dict] = {}
    default = None

    for area in market_areas:
        if not isinstance(area, dict):
            continue
        for z in area.get("zip_codes", []):
            by_zip[str(z)] = area
        for c in area.get("cities", []):
            by_city[c.lower()] = area
        for cn in area.get("counties", []):
            by_county[cn.lower()] = area
        if area.get("name", "").lower() == "default":
            default = area

    if zip_code and zip_code in by_zip:
        return by_zip[zip_code]
    if city and city in by_city:
        return by_city[city]
    if county and county in by_county:
        return by_county[county]
    return default


def build_market_section(listing_data: dict, market_areas: list[dict]) -> str:
    """Build MARKET CONTEXT text block for prompt injection.

    Args:
        listing_data: Listing dict with location fields.
        market_areas: List of area dicts from tenant settings.

    Returns:
        Text block string, or empty string if no data available.
    """
    area = lookup(listing_data, market_areas)
    if not area:
        return ""

    parts = ["MARKET CONTEXT:"]
    name = area.get("name", "Local Market")
    parts.append(f"Area: {name}")

    stats = area.get("stats", {})
    if not stats:
        return ""

    if stats.get("median_price"):
        parts.append(f"Median Sale Price: ${stats['median_price']:,.0f}")
    if stats.get("median_price_yoy"):
        direction = "up" if stats["median_price_yoy"] > 0 else "down"
        yoy = abs(stats['median_price_yoy'])
        parts.append(
            f"Price Trend: {direction} {yoy:.1f}%"
            " year-over-year"
        )
    if stats.get("median_dom"):
        parts.append(f"Median Days on Market: {stats['median_dom']}")
    if stats.get("active_inventory"):
        parts.append(f"Active Inventory: {stats['active_inventory']:,} listings")
    if stats.get("months_supply"):
        ms = stats["months_supply"]
        if ms < 4:
            market_type = "seller's market"
        elif ms > 6:
            market_type = "buyer's market"
        else:
            market_type = "balanced market"
        parts.append(f"Months of Supply: {ms:.1f} ({market_type})")
    if stats.get("avg_price_per_sqft"):
        parts.append(f"Avg Price/Sqft: ${stats['avg_price_per_sqft']:,.0f}")
    if stats.get("sale_to_list_ratio"):
        parts.append(f"Sale-to-List Ratio: {stats['sale_to_list_ratio']:.1f}%")
    if stats.get("note"):
        parts.append(f"Note: {stats['note']}")

    return "\n".join(parts) if len(parts) > 2 else ""
