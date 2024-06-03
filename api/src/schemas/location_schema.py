from datetime import datetime
from .root_schema import RootSchema


class LocationResponse(RootSchema):
    id: int
    name: str
    is_active: bool


class LocationWeatherDataPayload(RootSchema):
    location: str


class LocationWeatherDataResponse(RootSchema):
    location_id: str
    temperature: float
    date: datetime
    latitude: float
    longitude: float
    cld: float
    pet: float
    tmn: float
    tmx: float
    wet: float
    pre: float
    dtr: float
    frs: float
    vap: float
