"""
Unit tests for the database models (uses an in-memory SQLite DB).
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from db.models import Base, BatteryFacility, BatteryIndustryNews


@pytest.fixture
def session():
    """Create a fresh in-memory database for each test."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    sess = Session()
    yield sess
    sess.close()


class TestBatteryFacility:
    def test_create_facility(self, session):
        fac = BatteryFacility(
            company="Tesla",
            supply_chain_segment="Cell Manufacturing",
            facility_name="Gigafactory",
            facility_city="Sparks",
        )
        session.add(fac)
        session.commit()
        assert fac.id is not None

    def test_deduplication_constraint(self, session):
        """Inserting the same (company, facility_name, facility_city) twice
        should raise an IntegrityError."""
        kwargs = dict(
            company="Tesla",
            supply_chain_segment="Cell Manufacturing",
            facility_name="Gigafactory",
            facility_city="Sparks",
        )
        session.add(BatteryFacility(**kwargs))
        session.commit()

        session.add(BatteryFacility(**kwargs))
        with pytest.raises(IntegrityError):
            session.commit()

    def test_different_facilities_ok(self, session):
        session.add(
            BatteryFacility(
                company="Tesla",
                supply_chain_segment="Cell Manufacturing",
                facility_name="Gigafactory 1",
                facility_city="Sparks",
            )
        )
        session.add(
            BatteryFacility(
                company="Tesla",
                supply_chain_segment="Cell Manufacturing",
                facility_name="Gigafactory 2",
                facility_city="Austin",
            )
        )
        session.commit()
        assert session.query(BatteryFacility).count() == 2


class TestBatteryIndustryNews:
    def test_create_news(self, session):
        fac = BatteryFacility(
            company="Tesla",
            supply_chain_segment="Cell Manufacturing",
            facility_name="Gigafactory",
            facility_city="Sparks",
        )
        session.add(fac)
        session.commit()

        news = BatteryIndustryNews(
            company_id=fac.id,
            headline="Tesla announces expansion",
            summary="Big news.",
        )
        session.add(news)
        session.commit()
        assert news.news_id is not None
        assert news.facility.company == "Tesla"

    def test_cascade_delete(self, session):
        fac = BatteryFacility(
            company="CATL",
            supply_chain_segment="Cell Manufacturing",
            facility_name="Plant A",
            facility_city="Detroit",
        )
        session.add(fac)
        session.commit()

        news = BatteryIndustryNews(
            company_id=fac.id,
            headline="CATL opens US plant",
        )
        session.add(news)
        session.commit()

        session.delete(fac)
        session.commit()
        assert session.query(BatteryIndustryNews).count() == 0
