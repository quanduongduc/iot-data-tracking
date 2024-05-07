from sqlalchemy import Boolean, Column, DateTime, ForeignKey
from sqlalchemy.dialects.mysql import FLOAT, INTEGER, VARCHAR
from src.database import Base


class SourceLocation(Base):
    __tablename__ = "source_location"

    id = Column(INTEGER(unsigned=True), primary_key=True, index=True)
    name = Column(VARCHAR(255), index=True)
    is_active = Column(Boolean, default=False)


class WeatherData(Base):
    __tablename__ = "weather_data"

    id = Column(INTEGER(unsigned=True), primary_key=True, index=True, nullable=False)
    location_id = Column(
        INTEGER(unsigned=True), ForeignKey("source_location.id"), nullable=False
    )
    temperature = Column(FLOAT, nullable=False)  # tmp
    humidity = Column(FLOAT, nullable=False)  # vap
    wind_speed = Column(FLOAT, nullable=False)  # frs
    wind_direction = Column(FLOAT, nullable=False)  # dtr
    rain_fall = Column(FLOAT, nullable=False)  # pre
    date = Column(DateTime, nullable=False)  # Date
    latitude = Column(FLOAT, nullable=False)  # Latitude
    longitude = Column(FLOAT, nullable=False)  # Longitude
    cld = Column(FLOAT, nullable=False)
    pet = Column(FLOAT, nullable=False)
    tmn = Column(FLOAT, nullable=False)
    tmx = Column(FLOAT, nullable=False)
    wet = Column(FLOAT, nullable=False)
