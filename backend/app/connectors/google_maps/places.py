from typing import Any

import httpx

from app.config import settings

PLACES_BASE_URL = "https://places.googleapis.com/v1"


class GoogleMapsConfigurationError(RuntimeError):
    pass


async def _client() -> httpx.AsyncClient:
    if not settings.google_maps_api_key:
        raise GoogleMapsConfigurationError("GOOGLE_MAPS_API_KEY is not configured")
    return httpx.AsyncClient(
        timeout=20.0,
        headers={"X-Goog-Api-Key": settings.google_maps_api_key},
    )


async def search_places(
    text_query: str,
    *,
    max_result_count: int = 10,
    language_code: str | None = None,
    region_code: str | None = None,
) -> list[dict[str, Any]]:
    """Search places with Places API (New) Text Search."""
    if not text_query.strip():
        return []
    body: dict[str, Any] = {
        "textQuery": text_query,
        "maxResultCount": max(1, min(max_result_count, 20)),
    }
    if language_code:
        body["languageCode"] = language_code
    if region_code:
        body["regionCode"] = region_code
    async with await _client() as client:
        response = await client.post(
            f"{PLACES_BASE_URL}/places:searchText",
            headers={"X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.googleMapsUri,places.location"},
            json=body,
        )
        response.raise_for_status()
        return response.json().get("places", [])


async def get_place_details(place_id: str) -> dict[str, Any]:
    """Fetch the selected fields for one place ID."""
    if not place_id:
        raise ValueError("place_id is required")
    async with await _client() as client:
        response = await client.get(
            f"{PLACES_BASE_URL}/places/{place_id}",
            headers={
                "X-Goog-FieldMask": (
                    "id,displayName,formattedAddress,googleMapsUri,location,regularOpeningHours,"
                    "nationalPhoneNumber,websiteUri,rating,userRatingCount"
                )
            },
        )
        response.raise_for_status()
        return response.json()
