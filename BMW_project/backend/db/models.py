"""
SQLAlchemy models for the Battery Industry Data Pipeline.

Tables
------
- battery_facilities_full : one row per facility
- battery_industry_news   : one row per news article (FK → facility)
"""

from datetime import date
from sqlalchemy import (
    Column,
    Integer,
    String,
    Float,
    Boolean,
    Date,
    Text,
    ForeignKey,
    UniqueConstraint,
    create_engine,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    relationship,
    sessionmaker,
    Session,
)
from config import DATABASE_URL


# ── Base ─────────────────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    pass


# ── Battery Facilities ───────────────────────────────────────────────────────
class BatteryFacility(Base):
    __tablename__ = "battery_facilities_full"

    id = Column(Integer, primary_key=True, autoincrement=True)
    status = Column(String(100), nullable=True)  # Commercial, Paused, Proposed …
    supply_chain_segment = Column(String(100), nullable=False)
    company = Column(String(255), nullable=False)
    company_website = Column(String(500), nullable=True)
    naatbatt_member = Column(Boolean, default=False)
    hq_city = Column(String(200), nullable=True)
    hq_state = Column(String(200), nullable=True)
    facility_name = Column(String(300), nullable=True)
    product_facility_type = Column(String(300), nullable=True)
    product = Column(String(300), nullable=True)
    facility_address = Column(String(500), nullable=True)
    facility_city = Column(String(200), nullable=True)
    facility_state_or_province = Column(String(200), nullable=True)
    facility_country = Column(String(200), nullable=True)
    facility_zip = Column(String(20), nullable=True)
    facility_phone = Column(String(50), nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    confidence_score = Column(Integer, nullable=True)
    citations = Column(Text, nullable=True)          # JSON-encoded list of source names
    website_reachable = Column(Boolean, nullable=True)
    verification_status = Column(String(50), nullable=True)

    # Composite uniqueness for deduplication
    __table_args__ = (
        UniqueConstraint(
            "company",
            "facility_name",
            "facility_city",
            name="uq_company_facility",
        ),
    )

    # Relationship
    news = relationship(
        "BatteryIndustryNews",
        back_populates="facility",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<BatteryFacility(id={self.id}, company='{self.company}', "
            f"facility='{self.facility_name}', city='{self.facility_city}')>"
        )


# ── Battery Industry News ───────────────────────────────────────────────────
class BatteryIndustryNews(Base):
    __tablename__ = "battery_industry_news"

    news_id = Column(Integer, primary_key=True, autoincrement=True)
    company_id = Column(
        Integer,
        ForeignKey("battery_facilities_full.id", ondelete="CASCADE"),
        nullable=False,
    )
    headline = Column(String(500), nullable=False)
    summary = Column(Text, nullable=True)
    source_url = Column(String(1000), nullable=True)
    date_published = Column(Date, nullable=True)

    # Relationship
    facility = relationship("BatteryFacility", back_populates="news")

    def __repr__(self) -> str:
        return (
            f"<BatteryIndustryNews(news_id={self.news_id}, "
            f"headline='{self.headline[:40]}…')>"
        )


# ── Engine & Session ─────────────────────────────────────────────────────────
engine = create_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(bind=engine)


def migrate_db() -> None:
    """Add credibility columns to battery_facilities_full if they don't exist yet."""
    import sqlite3
    db_path = DATABASE_URL.replace("sqlite:///", "")
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    for col, typ in [
        ("confidence_score", "INTEGER"),
        ("citations", "TEXT"),
        ("website_reachable", "INTEGER"),
        ("verification_status", "TEXT"),
    ]:
        try:
            cur.execute(f"ALTER TABLE battery_facilities_full ADD COLUMN {col} {typ}")
        except Exception:
            pass  # column already exists
    conn.commit()
    conn.close()


def init_db() -> None:
    """Create all tables if they do not already exist."""
    Base.metadata.create_all(bind=engine)
    migrate_db()


def get_session() -> Session:
    """Return a new SQLAlchemy session."""
    return SessionLocal()
