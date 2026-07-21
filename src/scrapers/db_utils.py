from collections.abc import Mapping
from typing import Any

from src.config.database import SessionLocal
from src.models.Listing import Listing, ListingType


def _get_value(item: Any, *keys: str, default: Any = None) -> Any:
    if isinstance(item, Mapping):
        for key in keys:
            if key in item and item[key] is not None:
                return item[key]
    else:
        for key in keys:
            value = getattr(item, key, None)
            if value is not None:
                return value
    return default


def _normalize_listing_type(value: Any) -> ListingType:
    if isinstance(value, ListingType):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == ListingType.internship.value:
            return ListingType.internship
    return ListingType.job


def save_listings_to_db(listings: list[Any], default_source: str = "lever") -> int:
    db = SessionLocal()
    saved_count = 0
    try:
        for item in listings:
            company_name = _get_value(item, "company_name", "company")
            role_title = _get_value(item, "role_title", "title")
            jd_text = _get_value(item, "jd_text", "description", default="")
            location = _get_value(item, "location", default="")
            application_url = _get_value(item, "application_url", "url")
            listing_type = _normalize_listing_type(_get_value(item, "listing_type", default=ListingType.job))
            source = _get_value(item, "source", default=default_source)

            if not company_name or not role_title or not application_url:
                continue

            existing = db.query(Listing).filter(Listing.application_url == application_url).first()
            if existing:
                existing.company_name = company_name
                existing.role_title = role_title
                existing.jd_text = jd_text
                existing.location = location
                existing.listing_type = listing_type
                existing.source = source
            else:
                db.add(
                    Listing(
                        company_name=company_name,
                        role_title=role_title,
                        jd_text=jd_text,
                        location=location,
                        application_url=application_url,
                        listing_type=listing_type,
                        source=source,
                    )
                )
            saved_count += 1

        db.commit()
        return saved_count
    finally:
        db.close()