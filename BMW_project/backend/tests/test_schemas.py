"""
Unit tests for Pydantic validation schemas.
"""

import pytest
from schemas import FacilitySchema, NewsSchema


class TestFacilitySchema:
    """Tests for FacilitySchema validation."""

    def _base_data(self, **overrides) -> dict:
        data = {
            "company": "Tesla",
            "supply_chain_segment": "Cell Manufacturing",
            "facility_name": "Gigafactory Nevada",
            "facility_city": "Sparks",
        }
        data.update(overrides)
        return data

    def test_valid_minimal(self):
        fac = FacilitySchema(**self._base_data())
        assert fac.company == "Tesla"

    def test_valid_full(self):
        fac = FacilitySchema(
            **self._base_data(
                status="Commercial",
                company_website="https://tesla.com",
                naatbatt_member=False,
                hq_city="Austin",
                hq_state="TX",
                product_facility_type="Cylindrical cells",
                product="NMC",
                facility_address="1 Electric Ave",
                facility_state_or_province="NV",
                facility_country="USA",
                facility_zip="89434",
                facility_phone="775-555-0100",
                latitude=39.5349,
                longitude=-119.7527,
            )
        )
        assert fac.latitude == 39.5349

    # ── Segment validation ───────────────────────────────────────────────
    def test_invalid_segment(self):
        with pytest.raises(ValueError, match="Invalid supply chain segment"):
            FacilitySchema(**self._base_data(supply_chain_segment="Made Up"))

    # ── Zip validation ───────────────────────────────────────────────────
    def test_valid_zip_5digit(self):
        fac = FacilitySchema(**self._base_data(facility_zip="89434"))
        assert fac.facility_zip == "89434"

    def test_valid_zip_plus4(self):
        fac = FacilitySchema(**self._base_data(facility_zip="89434-1234"))
        assert fac.facility_zip == "89434-1234"

    def test_invalid_zip(self):
        with pytest.raises(ValueError):
            FacilitySchema(**self._base_data(facility_zip="XXXXXXXXXXX!!!"))

    # ── Coordinate validation ────────────────────────────────────────────
    def test_latitude_out_of_range(self):
        with pytest.raises(ValueError, match="Latitude"):
            FacilitySchema(**self._base_data(latitude=95.0))

    def test_longitude_out_of_range(self):
        with pytest.raises(ValueError, match="Longitude"):
            FacilitySchema(**self._base_data(longitude=-200.0))

    def test_latitude_none(self):
        fac = FacilitySchema(**self._base_data(latitude=None))
        assert fac.latitude is None

    # ── URL validation ───────────────────────────────────────────────────
    def test_url_auto_scheme(self):
        fac = FacilitySchema(**self._base_data(company_website="tesla.com"))
        assert fac.company_website.startswith("https://")

    def test_invalid_url(self):
        with pytest.raises(ValueError):
            FacilitySchema(**self._base_data(company_website="not a url!!!"))


class TestNewsSchema:
    """Tests for NewsSchema validation."""

    def _base_data(self, **overrides) -> dict:
        data = {
            "company_name": "Tesla",
            "headline": "Tesla Opens New Battery Plant",
        }
        data.update(overrides)
        return data

    def test_valid_minimal(self):
        news = NewsSchema(**self._base_data())
        assert news.headline == "Tesla Opens New Battery Plant"

    def test_date_parsing_iso(self):
        news = NewsSchema(**self._base_data(date_published="2025-06-15"))
        assert news.date_published.year == 2025

    def test_date_parsing_us_format(self):
        news = NewsSchema(**self._base_data(date_published="06/15/2025"))
        assert news.date_published.month == 6

    def test_date_parsing_long_format(self):
        news = NewsSchema(**self._base_data(date_published="June 15, 2025"))
        assert news.date_published.day == 15

    def test_invalid_date(self):
        with pytest.raises(ValueError, match="Cannot parse date"):
            NewsSchema(**self._base_data(date_published="not-a-date"))

    def test_source_url_auto_scheme(self):
        news = NewsSchema(**self._base_data(source_url="reuters.com/article"))
        assert news.source_url.startswith("https://")
