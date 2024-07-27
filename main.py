from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

app = FastAPI(
    title="Virtual Training Assistant API",
    description="API for interacting with Strava training data",
    version="1.0.0",
)

# Database connection details
# postgres://avnadmin:AVNS_qlXpg4FGEvhj5CnQYFl@pg-33d239a3-superpig1999-942a.e.aivencloud.com:19130/defaultdb?sslmode=require
DATABASE_CONFIG = {
    "dbname": "defaultdb",
    "user": "avnadmin",
    "password": "AVNS_qlXpg4FGEvhj5CnQYFl",
    "host": "pg-33d239a3-superpig1999-942a.e.aivencloud.com",
    "port": "19130",
}


# Model for activity count
class ActivityCount(BaseModel):
    date: str
    count: int


# Model for activity details
class ActivityDetail(BaseModel):
    id: int
    name: str
    distance: float
    moving_time: int
    type: str
    start_date: datetime.datetime


# Model for total distance
class TotalDistance(BaseModel):
    total_distance: float


# Model for average pace
class AveragePace(BaseModel):
    average_pace: float


# Model for weekly mileage trend
class WeeklyMileage(BaseModel):
    week: str
    weekly_distance_km: float


# Model for best efforts
class BestEffort(BaseModel):
    id: int
    name: str
    distance: float
    moving_time: int
    type: str
    start_date: datetime.datetime


def get_db_connection():
    try:
        connection = psycopg2.connect(**DATABASE_CONFIG, cursor_factory=RealDictCursor)
        return connection
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/activities/count/last_30_days", response_model=List[ActivityCount])
async def get_activity_count_last_30_days():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                DATE(start_date) AS date,
                COUNT(*) AS count
            FROM
                strava_activities
            WHERE
                start_date >= NOW() - INTERVAL '30 days'
            GROUP BY
                DATE(start_date)
            ORDER BY
                DATE(start_date);
        """
        )
        results = cursor.fetchall()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()


@app.get("/activities/last_n_days/{n}", response_model=List[ActivityDetail])
async def get_activities_last_n_days(n: int):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                id,
                name,
                distance,
                moving_time,
                type,
                start_date
            FROM
                strava_activities
            WHERE
                start_date >= NOW() - INTERVAL %s || ' days'
            ORDER BY
                start_date DESC;
        """,
            (n,),
        )
        results = cursor.fetchall()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()


@app.get("/activities/total_distance/last_n_days/{n}", response_model=TotalDistance)
async def get_total_distance_last_n_days(n: int):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                SUM(distance) AS total_distance
            FROM
                strava_activities
            WHERE
                start_date >= NOW() - INTERVAL %s || ' days';
        """,
            (n,),
        )
        result = cursor.fetchone()
        return {"total_distance": result["total_distance"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()


@app.get("/activities/average_pace/last_n_days/{n}", response_model=AveragePace)
async def get_average_pace_last_n_days(n: int):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                AVG(distance / moving_time * 3600) AS average_pace
            FROM
                strava_activities
            WHERE
                type = 'Run' AND
                start_date >= NOW() - INTERVAL %s || ' days';
        """,
            (n,),
        )
        result = cursor.fetchone()
        return {"average_pace": result["average_pace"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()


@app.get("/activities/weekly_mileage_trend", response_model=List[WeeklyMileage])
async def get_weekly_mileage_trend():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                DATE_TRUNC('week', start_date) AS week,
                SUM(distance) / 1000 AS weekly_distance_km
            FROM
                strava_activities
            WHERE
                type = 'Run'
            GROUP BY
                week
            ORDER BY
                week DESC
            LIMIT 12;
        """
        )
        results = cursor.fetchall()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()


@app.get("/activities/details/{activity_id}", response_model=ActivityDetail)
async def get_activity_details(activity_id: int):
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                id,
                name,
                distance,
                moving_time,
                type,
                start_date
            FROM
                strava_activities
            WHERE
                id = %s;
        """,
            (activity_id,),
        )
        result = cursor.fetchone()
        if not result:
            raise HTTPException(status_code=404, detail="Activity not found")
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()


@app.get("/activities/best_efforts", response_model=List[BestEffort])
async def get_best_efforts():
    connection = get_db_connection()
    cursor = connection.cursor()
    try:
        cursor.execute(
            """
            SELECT
                id,
                name,
                distance,
                moving_time,
                type,
                start_date
            FROM
                strava_activities
            WHERE
                type = 'Run'
            ORDER BY
                distance DESC
            LIMIT 5;
        """
        )
        results = cursor.fetchall()
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        cursor.close()
        connection.close()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
