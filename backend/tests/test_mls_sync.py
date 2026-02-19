from app.integrations.mls.adapters import PropertyAdapter, MediaAdapter


class TestPropertyAdapter:
    def test_normalize_full_record(self):
        reso_data = {
            "ListingKey": "12345",
            "ListingId": "MLS12345",
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
            "PublicRemarks": "Beautiful ocean view condo",
            "PoolPrivateYN": True,
            "WaterfrontYN": True,
            "Latitude": 26.1901,
            "Longitude": -80.0965,
            "ListAgentFullName": "Dennis Test",
            "ListingContractDate": "2025-01-15",
        }

        result = PropertyAdapter.normalize(reso_data)

        assert result["mls_listing_id"] == "12345"
        assert result["status"] == "active"
        assert result["property_type"] == "condo"
        assert result["address_city"] == "Fort Lauderdale"
        assert result["price"] == 1500000
        assert result["bedrooms"] == 3
        assert result["bathrooms"] == 2.5
        assert "Pool" in result["features"]
        assert "Waterfront" in result["features"]

    def test_normalize_minimal_record(self):
        reso_data = {
            "ListingKey": "99999",
            "StandardStatus": "Pending",
            "PropertyType": "Residential",
            "City": "Pompano Beach",
            "StateOrProvince": "FL",
            "ListPrice": 400000,
        }

        result = PropertyAdapter.normalize(reso_data)

        assert result["mls_listing_id"] == "99999"
        assert result["status"] == "pending"
        assert result["property_type"] == "residential"
        assert result["price"] == 400000


class TestMediaAdapter:
    def test_normalize_media(self):
        reso_media = {
            "MediaURL": "https://example.com/photo.jpg",
            "ShortDescription": "Front view",
            "Order": 1,
            "MediaCategory": "Photo",
        }

        result = MediaAdapter.normalize(reso_media)

        assert result["url"] == "https://example.com/photo.jpg"
        assert result["caption"] == "Front view"
        assert result["order"] == 1
