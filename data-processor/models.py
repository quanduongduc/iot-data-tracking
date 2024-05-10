from pydantic import BaseModel

from pydantic import BaseModel
from datetime import datetime


class WeatherData(BaseModel):
    location: str
    Date: datetime
    Latitude: float
    Longitude: float
    cld: float
    dtr: float
    frs: float
    pet: float
    pre: float
    tmn: float
    tmp: float
    tmx: float
    vap: float
    wet: float


class StoreWeatherData(BaseModel):
    location: str
    Date: datetime
    Latitude: float
    Longitude: float
    cld: float
    dtr: float
    frs: float
    pet: float
    pre: float
    tmn: float
    tmp: float
    tmx: float
    vap: float
    wet: float


class PublishWeatherData(BaseModel):
    location: str
    Date: datetime
    Latitude: float
    Longitude: float
    cld: float
    dtr: float
    frs: float
    pet: float
    pre: float
    tmn: float
    tmp: float
    tmx: float
    vap: float
    wet: float
