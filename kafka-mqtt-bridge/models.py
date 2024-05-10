from pydantic import BaseModel

from pydantic import BaseModel
from datetime import datetime


class MqttWeatherData(BaseModel):
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


class KafkaWeatherData(BaseModel):
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
