from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from src.constanst import SHOW_DOCS_ENVIRONMENT
from src.config import settings

app_configs = {"title": "My Cool API"}
if settings.is_development not in SHOW_DOCS_ENVIRONMENT:
    app_configs["openapi_url"] = None  # set url for docs as null
    
app_configs["default_response_class"] = ORJSONResponse  # set default response class as ORJSONResponse
app = FastAPI(**app_configs)


app.get("/")(lambda: {"message": "Hello World!"})