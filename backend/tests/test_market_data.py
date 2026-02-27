"""Tests for market data enrichment service."""

from app.services.market_data import build_market_section, lookup


class TestLookup:
    def test_lookup_by_zip(self):
        areas = [{"name": "Beach", "zip_codes": ["33308"], "stats": {"median_price": 500000}}]
        result = lookup({"address_zip": "33308", "address_city": ""}, areas)
        assert result is not None
        assert result["name"] == "Beach"

    def test_lookup_by_city(self):
        areas = [{"name": "FTL", "cities": ["Fort Lauderdale"], "stats": {"median_price": 485000}}]
        result = lookup({"address_city": "Fort Lauderdale", "address_zip": ""}, areas)
        assert result is not None
        assert result["name"] == "FTL"

    def test_lookup_by_county(self):
        areas = [{"name": "Broward", "counties": ["Broward"], "stats": {"median_price": 450000}}]
        result = lookup({"address_city": "", "address_zip": "", "county": "Broward"}, areas)
        assert result is not None
        assert result["name"] == "Broward"

    def test_lookup_zip_takes_priority_over_city(self):
        areas = [
            {"name": "City Match", "cities": ["Fort Lauderdale"], "stats": {}},
            {"name": "Zip Match", "zip_codes": ["33308"], "stats": {}},
        ]
        result = lookup({"address_city": "Fort Lauderdale", "address_zip": "33308"}, areas)
        assert result["name"] == "Zip Match"

    def test_lookup_no_match(self):
        areas = [{"name": "Elsewhere", "zip_codes": ["99999"], "stats": {}}]
        result = lookup({"address_city": "Nowhere", "address_zip": "00000"}, areas)
        assert result is None

    def test_lookup_default_fallback(self):
        areas = [{"name": "default", "stats": {"median_price": 400000}}]
        result = lookup({"address_city": "Anywhere", "address_zip": ""}, areas)
        assert result is not None
        assert result["name"] == "default"

    def test_lookup_empty_areas(self):
        assert lookup({"address_zip": "33308"}, []) is None

    def test_lookup_case_insensitive_city(self):
        areas = [{"name": "FTL", "cities": ["fort lauderdale"], "stats": {}}]
        result = lookup({"address_city": "Fort Lauderdale", "address_zip": ""}, areas)
        assert result is not None


class TestBuildMarketSection:
    def test_full_stats(self):
        areas = [{
            "name": "Galt Ocean Mile",
            "zip_codes": ["33308"],
            "stats": {
                "median_price": 485000,
                "median_price_yoy": 4.2,
                "median_dom": 52,
                "months_supply": 5.8,
                "avg_price_per_sqft": 385,
                "sale_to_list_ratio": 96.5,
                "note": "Oceanfront condos trending up",
            },
        }]
        section = build_market_section({"address_zip": "33308"}, areas)
        assert "MARKET CONTEXT:" in section
        assert "$485,000" in section
        assert "4.2%" in section
        assert "52" in section
        assert "balanced market" in section
        assert "$385" in section
        assert "96.5%" in section
        assert "Oceanfront condos trending up" in section

    def test_no_match_returns_empty(self):
        areas = [{"name": "Elsewhere", "zip_codes": ["99999"], "stats": {"median_price": 300000}}]
        assert build_market_section({"address_zip": "00000"}, areas) == ""

    def test_empty_areas_returns_empty(self):
        assert build_market_section({"address_zip": "33308"}, []) == ""

    def test_sellers_market(self):
        areas = [{
            "name": "Hot",
            "zip_codes": ["11111"],
            "stats": {"median_price": 300000, "months_supply": 2.5},
        }]
        section = build_market_section({"address_zip": "11111"}, areas)
        assert "seller's market" in section

    def test_buyers_market(self):
        areas = [{
            "name": "Slow",
            "zip_codes": ["22222"],
            "stats": {"median_price": 200000, "months_supply": 8.0},
        }]
        section = build_market_section({"address_zip": "22222"}, areas)
        assert "buyer's market" in section

    def test_no_stats_returns_empty(self):
        areas = [{"name": "Empty", "zip_codes": ["33333"], "stats": {}}]
        assert build_market_section({"address_zip": "33333"}, areas) == ""

    def test_price_trend_down(self):
        areas = [{
            "name": "Declining",
            "zip_codes": ["44444"],
            "stats": {
                "median_price": 400000,
                "median_price_yoy": -2.3,
            },
        }]
        section = build_market_section({"address_zip": "44444"}, areas)
        assert "down 2.3%" in section


class TestLookupCascadePriority:
    """Thorough cascade priority tests: zip > city > county > default."""

    ALL_AREAS = [
        {"name": "default", "stats": {"median_price": 100000}},
        {"name": "County Match", "counties": ["Broward"], "stats": {"median_price": 200000}},
        {"name": "City Match", "cities": ["Fort Lauderdale"], "stats": {"median_price": 300000}},
        {"name": "Zip Match", "zip_codes": ["33308"], "stats": {"median_price": 400000}},
    ]

    def test_zip_beats_everything(self):
        result = lookup(
            {"address_zip": "33308", "address_city": "Fort Lauderdale", "county": "Broward"},
            self.ALL_AREAS,
        )
        assert result["name"] == "Zip Match"

    def test_city_beats_county_and_default(self):
        result = lookup(
            {"address_zip": "99999", "address_city": "Fort Lauderdale", "county": "Broward"},
            self.ALL_AREAS,
        )
        assert result["name"] == "City Match"

    def test_county_beats_default(self):
        result = lookup(
            {"address_zip": "99999", "address_city": "Unknown City", "county": "Broward"},
            self.ALL_AREAS,
        )
        assert result["name"] == "County Match"

    def test_default_when_nothing_matches(self):
        result = lookup(
            {"address_zip": "99999", "address_city": "Unknown City", "county": "Unknown County"},
            self.ALL_AREAS,
        )
        assert result["name"] == "default"

    def test_no_county_field_still_works(self):
        """Listings without county field should gracefully fall through."""
        result = lookup(
            {"address_zip": "99999", "address_city": "Unknown City"},
            self.ALL_AREAS,
        )
        assert result["name"] == "default"

    def test_none_values_handled(self):
        """None values in listing fields should not crash."""
        result = lookup(
            {"address_zip": None, "address_city": None, "county": None},
            self.ALL_AREAS,
        )
        assert result["name"] == "default"


class TestGetMarketDataConvenience:
    """Test the tenant settings -> lookup integration pattern."""

    def test_full_flow_tenant_settings_to_market_section(self):
        """Simulate the full flow: tenant settings -> extract areas -> lookup -> build section."""
        tenant_settings = {
            "market_data": {
                "areas": [
                    {
                        "name": "Beach Zone",
                        "zip_codes": ["33308"],
                        "stats": {
                            "median_price": 485000,
                            "median_dom": 52,
                            "months_supply": 3.5,
                        },
                    },
                    {
                        "name": "default",
                        "stats": {"median_price": 400000},
                    },
                ]
            }
        }
        # Extract areas the same way ai_service.py does
        market_data = tenant_settings.get("market_data", {})
        market_areas = market_data.get("areas") if isinstance(market_data, dict) else None

        # Listing matches by zip
        listing_data = {"address_zip": "33308", "address_city": "Fort Lauderdale"}
        section = build_market_section(listing_data, market_areas)
        assert "MARKET CONTEXT:" in section
        assert "$485,000" in section
        assert "seller's market" in section  # months_supply 3.5 < 4

    def test_tenant_with_no_market_data_key(self):
        """Tenant settings without market_data key -> empty result."""
        tenant_settings = {"branding": {"logo": "logo.png"}}
        market_data = tenant_settings.get("market_data", {})
        market_areas = market_data.get("areas") if isinstance(market_data, dict) else None
        assert market_areas is None

    def test_tenant_with_empty_market_data(self):
        """Tenant settings with empty market_data -> empty result."""
        tenant_settings = {"market_data": {}}
        market_data = tenant_settings.get("market_data", {})
        market_areas = market_data.get("areas") if isinstance(market_data, dict) else None
        assert market_areas is None
