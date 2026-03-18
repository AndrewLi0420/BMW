"""
Unit tests for the data extractor module.
"""

import json
import pytest
from pipeline.extractor import extract_facilities, extract_news, _extract_json


class TestExtractJson:
    """Test the raw JSON extraction helper."""

    def test_plain_json_array(self):
        raw = '[{"a": 1}, {"a": 2}]'
        result = _extract_json(raw)
        assert len(result) == 2

    def test_markdown_fenced_json(self):
        raw = '```json\n[{"a": 1}]\n```'
        result = _extract_json(raw)
        assert len(result) == 1

    def test_json_embedded_in_text(self):
        raw = 'Here are the results:\n[{"a": 1}]\nEnd of results.'
        result = _extract_json(raw)
        assert len(result) == 1

    def test_single_object(self):
        raw = '{"a": 1}'
        result = _extract_json(raw)
        assert len(result) == 1

    def test_invalid_json(self):
        raw = "This is not JSON at all."
        result = _extract_json(raw)
        assert result == []


MOCK_FACILITIES_JSON = json.dumps([
    {
        "status": "Commercial",
        "supply_chain_segment": "Cell Manufacturing",
        "company": "Tesla",
        "company_website": "https://tesla.com",
        "naatbatt_member": False,
        "hq_city": "Austin",
        "hq_state": "TX",
        "facility_name": "Gigafactory Nevada",
        "product_facility_type": "Cylindrical cells",
        "product": "NMC",
        "facility_address": "1 Electric Ave",
        "facility_city": "Sparks",
        "facility_state_or_province": "NV",
        "facility_country": "USA",
        "facility_zip": "89434",
        "facility_phone": None,
        "latitude": 39.5349,
        "longitude": -119.7527,
    },
    {
        "status": "Under Construction",
        "supply_chain_segment": "Cell Manufacturing",
        "company": "LG Energy Solution",
        "company_website": "https://lgensol.com",
        "naatbatt_member": False,
        "hq_city": "Seoul",
        "hq_state": None,
        "facility_name": "Holland Plant",
        "product_facility_type": "Pouch cells",
        "product": "NMC",
        "facility_address": None,
        "facility_city": "Holland",
        "facility_state_or_province": "MI",
        "facility_country": "USA",
        "facility_zip": "49423",
        "facility_phone": None,
        "latitude": 42.7876,
        "longitude": -86.1089,
    },
])

MOCK_FACILITIES_WITH_INVALID = json.dumps([
    {
        "status": "Commercial",
        "supply_chain_segment": "Cell Manufacturing",
        "company": "GoodCo",
        "facility_name": "Plant A",
        "facility_city": "Detroit",
    },
    {
        # Invalid: bad segment
        "supply_chain_segment": "INVALID_SEGMENT",
        "company": "BadCo",
    },
])


class TestExtractFacilities:
    def test_valid_records(self):
        result = extract_facilities(MOCK_FACILITIES_JSON)
        assert len(result) == 2
        assert result[0].company == "Tesla"
        assert result[1].company == "LG Energy Solution"

    def test_skips_invalid(self):
        result = extract_facilities(MOCK_FACILITIES_WITH_INVALID)
        assert len(result) == 1
        assert result[0].company == "GoodCo"


MOCK_NEWS_JSON = json.dumps([
    {
        "company_name": "Tesla",
        "headline": "Tesla Expands Battery Production",
        "summary": "Tesla announces expansion of Nevada facility.",
        "source_url": "https://reuters.com/article/123",
        "date_published": "2025-06-15",
    },
    {
        "company_name": "Tesla",
        "headline": "Tesla Q3 Earnings Beat Expectations",
        "summary": None,
        "source_url": None,
        "date_published": None,
    },
])


class TestExtractNews:
    def test_valid_records(self):
        result = extract_news(MOCK_NEWS_JSON)
        assert len(result) == 2
        assert result[0].headline == "Tesla Expands Battery Production"

    def test_date_parsed(self):
        result = extract_news(MOCK_NEWS_JSON)
        assert result[0].date_published is not None
        assert result[0].date_published.year == 2025
