"""Tests for MLS property/media adapters — normalize RESO data to internal format."""
from app.integrations.mls.adapters import MediaAdapter, PropertyAdapter


class TestPropertyAdapter:
    def test_basic_normalize(self):
        reso = {
            "ListingKey": "LK-001",
            "StandardStatus": "Active",
            "PropertyType": "Condominium",
            "StreetNumber": "4250",
            "StreetName": "Galt Ocean",
            "StreetSuffix": "Dr",
            "City": "Fort Lauderdale",
            "StateOrProvince": "FL",
            "PostalCode": "33308",
            "ListPrice": 1500000,
            "BedroomsTotal": 3,
            "BathroomsTotalDecimal": 2.5,
            "LivingArea": 2200,
            "YearBuilt": 2020,
        }
        result = PropertyAdapter.normalize(reso)
        assert result["mls_listing_id"] == "LK-001"
        assert result["status"] == "active"
        assert result["property_type"] == "condo"
        assert result["price"] == 1500000
        assert "Fort Lauderdale" in result["address_full"]

    def test_view_description_list(self):
        reso = {"ListingKey": "LK-002", "ViewDescription": ["Ocean", "Bay"]}
        result = PropertyAdapter.normalize(reso)
        assert "Ocean" in result["features"]
        assert "Bay" in result["features"]

    def test_view_description_string(self):
        reso = {"ListingKey": "LK-003", "ViewDescription": "Ocean"}
        result = PropertyAdapter.normalize(reso)
        assert "Ocean" in result["features"]

    def test_appliances_list(self):
        reso = {"ListingKey": "LK-004", "Appliances": ["Dishwasher", "Microwave"]}
        result = PropertyAdapter.normalize(reso)
        assert "Dishwasher" in result["features"]
        assert "Microwave" in result["features"]

    def test_garage_spaces(self):
        reso = {"ListingKey": "LK-005", "GarageSpaces": 2}
        result = PropertyAdapter.normalize(reso)
        assert "2-Car Garage" in result["features"]

    def test_garage_spaces_zero_excluded(self):
        reso = {"ListingKey": "LK-006", "GarageSpaces": 0}
        result = PropertyAdapter.normalize(reso)
        assert not any("Garage" in f for f in result["features"])

    def test_list_date_valid(self):
        reso = {"ListingKey": "LK-007", "ListingContractDate": "2025-06-15"}
        result = PropertyAdapter.normalize(reso)
        assert result["list_date"].isoformat() == "2025-06-15"

    def test_list_date_invalid(self):
        reso = {"ListingKey": "LK-008", "ListingContractDate": "not-a-date"}
        result = PropertyAdapter.normalize(reso)
        assert result["list_date"] is None

    def test_list_date_truncated_datetime(self):
        reso = {"ListingKey": "LK-009", "ListingContractDate": "2025-06-15T10:30:00Z"}
        result = PropertyAdapter.normalize(reso)
        assert result["list_date"].isoformat() == "2025-06-15"

    def test_pool_and_waterfront_features(self):
        reso = {"ListingKey": "LK-010", "PoolPrivateYN": True, "WaterfrontYN": True}
        result = PropertyAdapter.normalize(reso)
        assert "Pool" in result["features"]
        assert "Waterfront" in result["features"]

    def test_listing_id_fallback(self):
        """Uses ListingId when ListingKey is absent."""
        reso = {"ListingId": "ALT-001"}
        result = PropertyAdapter.normalize(reso)
        assert result["mls_listing_id"] == "ALT-001"

    def test_status_mapping(self):
        for reso_status, expected in [
            ("Active Under Contract", "pending"),
            ("Pending", "pending"),
            ("Closed", "sold"),
            ("Withdrawn", "withdrawn"),
            ("Unknown", "active"),
        ]:
            reso = {"ListingKey": "X", "StandardStatus": reso_status}
            assert PropertyAdapter.normalize(reso)["status"] == expected


class TestMediaAdapter:
    def test_normalize(self):
        media = {
            "MediaURL": "https://photos.example.com/1.jpg",
            "ShortDescription": "Front view",
            "Order": 1,
            "MediaCategory": "Photo",
        }
        result = MediaAdapter.normalize(media)
        assert result["url"] == "https://photos.example.com/1.jpg"
        assert result["caption"] == "Front view"
        assert result["order"] == 1

    def test_defaults(self):
        result = MediaAdapter.normalize({})
        assert result["url"] is None
        assert result["caption"] == ""
        assert result["order"] == 0
        assert result["media_type"] == "Photo"
