from typing import List
from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import ORJSONResponse
from sqlalchemy import desc, func, select
from .constanst import SHOW_DOCS_ENVIRONMENT
from .config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db_session
from .models import SourceLocation, WeatherData
from .schemas.location_schema import (
    LocationResponse,
    LocationWeatherDataPayload,
    LocationWeatherDataResponse,
)
from fastapi import HTTPException

app_configs = {"title": "My Cool API"}
if settings.is_development not in SHOW_DOCS_ENVIRONMENT:
    app_configs["openapi_url"] = None

app_configs["default_response_class"] = ORJSONResponse
app = FastAPI(**app_configs)


app.get("/health")(lambda: {"status": "ok"})


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return ORJSONResponse(
        status_code=exc.status_code,
        content={"message": str(exc.detail)},
    )


@app.exception_handler(Exception)
async def exception_handler(request, exc):
    return ORJSONResponse(
        status_code=500,
        content={"message": str(exc)},
    )


router = APIRouter(prefix=f"/{settings.ENVIRONMENT.value.lower()}")


@router.get("/locations", response_model=List[LocationResponse])
async def get_locations(db_session: AsyncSession = Depends(get_db_session)):
    result = await db_session.execute(select(SourceLocation))
    locations = result.scalars().all()
    locations_response = [
        LocationResponse(
            id=location.id, name=location.name, is_active=location.is_active
        )
        for location in locations
    ]
    return locations_response


@router.get("/weather_data", response_model=List[LocationWeatherDataResponse])
async def get_location_data(
    payload: LocationWeatherDataPayload = Depends(),
    db_session: AsyncSession = Depends(get_db_session),
):
    start_date_result = await db_session.execute(
        select(WeatherData.date)
        .filter(WeatherData.location_id == payload.location_id)
        .group_by(WeatherData.date)
        .order_by(desc(WeatherData.date))
        .offset(payload.page)
        .limit(1)
    )
    start_date = start_date_result.scalar_one()

    result = await db_session.execute(
        select(WeatherData)
        .filter(
            WeatherData.location_id == payload.location_id,
            func.date(WeatherData.date) == func.date(start_date),
        )
        .order_by(desc(WeatherData.date))
    )
    weather_data = result.scalars().all()

    weather_data_response = [
        LocationWeatherDataResponse(
            id=weather.id,
            location_id=weather.location_id,
            temperature=weather.temperature,
            humidity=weather.humidity,
            wind_speed=weather.wind_speed,
            wind_direction=weather.wind_direction,
            rain_fall=weather.rain_fall,
            date=weather.date,
            latitude=weather.latitude,
            longitude=weather.longitude,
            cld=weather.cld,
            pet=weather.pet,
            tmn=weather.tmn,
            tmx=weather.tmx,
            wet=weather.wet,
        )
        for weather in weather_data
    ]
    return weather_data_response


app.include_router(router)
