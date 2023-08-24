import datetime
import json
import os
from typing import List

import aioredis
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBasic, HTTPBasicCredentials
import motor.motor_asyncio
from pydantic import BaseModel

app = FastAPI()
security = HTTPBasic()
load_dotenv()

# Secret Key for JWT
SECRET_KEY = os.environ.get("SECRET_KEY")
ALGORITHM = os.environ.get("ALGORITHM")

# MongoDB Configuration
MONGO_HOST = os.environ.get("MONGO_HOST")
MONGO_PORT = os.environ.get("MONGO_PORT")
MONGO_USER = os.environ.get("MONGO_USER")
MONGO_PASSWORD = os.environ.get("MONGO_PASSWORD")
MONGO_URL = F"mongodb://{MONGO_USER}:{MONGO_PASSWORD}@{MONGO_HOST}:{MONGO_PORT}"
MONGO_DB = os.environ.get("MONGO_DB")
MONGO_COL = os.environ.get("MONGO_COL")

# Redis Configuration
REDIS_HOST = os.environ.get("REDIS_HOST")
REDIS_PORT = int(os.environ.get("REDIS_PORT"))
REDIS_DB = int(os.environ.get("REDIS_DB"))
REDIS_URL = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
REDIS_KEY_PREFIX = "Sensor"
REDIS_LAST_READINGS_COUNT = 10

dummy_user_db = {
    "user": "password"
}

# MongoDB Connection
client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_URL)
db = client[MONGO_DB]
collection = db[MONGO_COL]


# Redis Connection
pool = aioredis.ConnectionPool.from_url(REDIS_URL, max_connections=10)
redis = aioredis.Redis(connection_pool=pool)


class SensorReading(BaseModel):
    sensor_id: int
    timestamp: datetime.datetime
    temperature: int


def get_current_user(credentials: HTTPBasicCredentials = Depends(security)):
    if credentials.username not in dummy_user_db:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )
    if credentials.password != dummy_user_db[credentials.username]:
        raise HTTPException(
            status_code=403,
            detail="Check your password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username


@app.get("/readings/")
async def get_readings(sensor_id: int, start: str, end: str, user: str = Depends(get_current_user)):
    """Advisable to use pagination for this end point"""
    if not (sensor_id and start and end):
        raise HTTPException(
            status_code=400,
            detail="Check parameters"
        )
    try:
        start_time = datetime.datetime.fromisoformat(start)
        end_time = datetime.datetime.fromisoformat(end)
    except Exception as err:
        raise HTTPException(
            status_code=400,
            detail="Check parameters"
        )
    query = {"sensor_id": sensor_id, "timestamp": {
        "$gte": start_time, "$lte": end_time}}
    print(query)
    project = {'_id': 0}
    readings = await collection.find({"sensor_id": sensor_id}, projection=project).to_list(None)
    if not readings:
        raise HTTPException(
            status_code=404,
            detail="Not found"
        )
    return readings


@app.get("/readings/{sensor_id}")
async def get_latest_sensor_readings(sensor_id: int, user: str = Depends(get_current_user)):
    if not (sensor_id):
        raise HTTPException(
            status_code=400,
            detail="Check parameters"
        )
    redis_key = f"{REDIS_KEY_PREFIX}:{sensor_id}"
    try:
        latest_readings = await redis.lrange(redis_key, -REDIS_LAST_READINGS_COUNT, -1)
        if not latest_readings:
            raise HTTPException(
                status_code=404,
                detail="Not found"
            )

    except Exception:
        raise HTTPException(
            status_code=404,
            detail="Not found"
        )
    result = []
    for reading in latest_readings:
        result.append(SensorReading(**json.loads(reading)))
    return result
