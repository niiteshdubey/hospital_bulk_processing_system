from fastapi import FastAPI
from .api import router
from .constants import APP_TITLE, APP_DESCRIPTION
import logging


logging.basicConfig(
    level=logging.INFO,  
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("hospital-bulk-processor")


app = FastAPI(
    title=APP_TITLE,
    description=APP_DESCRIPTION
)

app.include_router(router)

@app.on_event("startup")
async def on_startup():
    logger.info("Hospital Bulk Processing API has started up!")

@app.on_event("shutdown")
async def on_shutdown():
    logger.info("API server is shutting down.")
