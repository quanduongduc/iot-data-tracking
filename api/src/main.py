from boto3.dynamodb.conditions import Key
import logging
from typing import List
from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import ORJSONResponse
from sqlalchemy import select
from .constanst import SHOW_DOCS_ENVIRONMENT
from .config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db_session, get_dynamodb_table
from .models import SourceLocation
from .schemas.location_schema import (
    LocationResponse,
    LocationWeatherDataPayload,
    LocationWeatherDataResponse,
)
from fastapi import HTTPException
from botocore.exceptions import BotoCoreError, ClientError


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
    dynamodb_table=Depends(get_dynamodb_table),
):
    try:
        start_date_result = await dynamodb_table.query(
            KeyConditionExpression=Key('location_id').eq(payload.location_id),
            ScanIndexForward=False,
            Limit=1,
            ExclusiveStartKey={'page': payload.page}
        )
        start_date = start_date_result['Items'][0]['date']

        result = await dynamodb_table.query(
            KeyConditionExpression=Key('location_id').eq(payload.location_id) & Key('date').eq(start_date),
            ScanIndexForward=False
        )
        weather_data = result['Items']

        weather_data_response = [
            LocationWeatherDataResponse(
                id=weather['id'],
                location_id=weather['location_id'],
                temperature=weather['temperature'],
                humidity=weather['humidity'],
                wind_speed=weather['wind_speed'],
                wind_direction=weather['wind_direction'],
                rain_fall=weather['rain_fall'],
                date=weather['date'],
                latitude=weather['latitude'],
                longitude=weather['longitude'],
                cld=weather['cld'],
                pet=weather['pet'],
                tmn=weather['tmn'],
                tmx=weather['tmx'],
                wet=weather['wet'],
            )
            for weather in weather_data
        ]
        return weather_data_response
    except BotoCoreError as e:
        logging.error(f"BotoCoreError occurred: {e}")
        raise
    except ClientError as e:
        logging.error(f"ClientError occurred: {e}")
        raise


app.include_router(router)
