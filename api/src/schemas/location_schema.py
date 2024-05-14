from datetime import datetime
from .root_schema import RootSchema


class LocationResponse(RootSchema):
    id: int
    name: str
    is_active: bool


class LocationWeatherDataPayload(RootSchema):
    location_id: int
    page: int = 0


class LocationWeatherDataResponse(RootSchema):
    id: int
    location_id: int
    temperature: float
    humidity: float
    wind_speed: float
    wind_direction: float
    rain_fall: float
    date: datetime
    latitude: float
    longitude: float
    cld: float
    pet: float
    tmn: float
    tmx: float
    wet: float
