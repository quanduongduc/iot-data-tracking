from datetime import datetime
from .root_schema import RootSchema
from typing import Dict


class LocationResponse(RootSchema):
    id: int
    name: str
    is_active: bool


class LocationWeatherDataPayload(RootSchema):
    location: str


class LocationWeatherDataResponse(RootSchema):
    location_name: str
    data: Dict
