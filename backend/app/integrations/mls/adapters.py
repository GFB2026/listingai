import contextlib
from datetime import date


class PropertyAdapter:
    """Normalize RESO Property resource to internal listing format."""

    @staticmethod
    def normalize(reso_data: dict) -> dict:
        features = []

        # Extract features from RESO fields
        if reso_data.get("PoolPrivateYN"):
            features.append("Pool")
        if reso_data.get("WaterfrontYN"):
            features.append("Waterfront")
        if reso_data.get("ViewDescription"):
            view = reso_data["ViewDescription"]
            if isinstance(view, list):
                features.extend(view)
            else:
                features.append(view)
        if reso_data.get("Appliances"):
            appliances = reso_data["Appliances"]
            if isinstance(appliances, list):
                features.extend(appliances)
        if reso_data.get("GarageSpaces") and reso_data["GarageSpaces"] > 0:
            features.append(f"{reso_data['GarageSpaces']}-Car Garage")

        # Build address
        address_parts = [
            reso_data.get("StreetNumber", ""),
            reso_data.get("StreetDirPrefix", ""),
            reso_data.get("StreetName", ""),
            reso_data.get("StreetSuffix", ""),
            reso_data.get("UnitNumber", ""),
        ]
        address_street = " ".join(p for p in address_parts if p).strip()
        city = reso_data.get("City", "")
        state = reso_data.get("StateOrProvince", "")
        zip_code = reso_data.get("PostalCode", "")
        address_full = f"{address_street}, {city}, {state} {zip_code}".strip(", ")

        # Parse list date
        list_date = None
        if reso_data.get("ListingContractDate"):
            with contextlib.suppress(ValueError, TypeError):
                list_date = date.fromisoformat(reso_data["ListingContractDate"][:10])

        return {
            "mls_listing_id": reso_data.get("ListingKey") or reso_data.get("ListingId"),
            "status": _map_status(reso_data.get("StandardStatus", "")),
            "property_type": _map_property_type(reso_data.get("PropertyType", "")),
            "address_full": address_full,
            "address_street": address_street,
            "address_city": city,
            "address_state": state,
            "address_zip": zip_code,
            "price": reso_data.get("ListPrice"),
            "bedrooms": reso_data.get("BedroomsTotal"),
            "bathrooms": reso_data.get("BathroomsTotalDecimal") or reso_data.get("BathroomsFull"),
            "sqft": reso_data.get("LivingArea"),
            "lot_sqft": reso_data.get("LotSizeSquareFeet"),
            "year_built": reso_data.get("YearBuilt"),
            "description_original": reso_data.get("PublicRemarks"),
            "features": features,
            "latitude": reso_data.get("Latitude"),
            "longitude": reso_data.get("Longitude"),
            "list_date": list_date,
            "listing_agent_name": reso_data.get("ListAgentFullName"),
            "raw_mls_data": reso_data,
        }


class MediaAdapter:
    """Normalize RESO Media resource to internal photo format."""

    @staticmethod
    def normalize(reso_media: dict) -> dict:
        return {
            "url": reso_media.get("MediaURL"),
            "caption": reso_media.get("ShortDescription", ""),
            "order": reso_media.get("Order", 0),
            "media_type": reso_media.get("MediaCategory", "Photo"),
        }


def _map_status(reso_status: str) -> str:
    mapping = {
        "Active": "active",
        "Active Under Contract": "pending",
        "Pending": "pending",
        "Closed": "sold",
        "Withdrawn": "withdrawn",
        "Canceled": "withdrawn",
        "Expired": "withdrawn",
    }
    return mapping.get(reso_status, "active")


def _map_property_type(reso_type: str) -> str:
    mapping = {
        "Residential": "residential",
        "Condominium": "condo",
        "Townhouse": "townhouse",
        "Land": "land",
        "Commercial Sale": "commercial",
        "Multi Family": "multi_family",
    }
    return mapping.get(reso_type, "residential")
