from boto3.dynamodb.conditions import Key
import logging
from typing import List
from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import ORJSONResponse
from sqlalchemy import select
from .constanst import SHOW_DOCS_ENVIRONMENT
from .config import settings
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db_session
import aioboto3

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
):
    try:
        session = aioboto3.Session()
        async with session.resource("dynamodb") as dynamodb:
            dynamodb_table = await dynamodb.Table(settings.DYNAMODB_TABLE_NAME)
            result = await dynamodb_table.query(
                KeyConditionExpression=Key("location").eq(payload.location),
                ScanIndexForward=False,
            )
            weather_data = result["Items"]
            weather_data_response = [
                LocationWeatherDataResponse(
                    location_name=weather["location"],
                    data={
                        key: value
                        for key, value in weather.items()
                        if key != "location"
                    },
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
