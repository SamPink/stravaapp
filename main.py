from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from fastapi.responses import HTMLResponse  # Import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# Database connection details
DATABASE_URL = "postgresql+psycopg2://avnadmin:AVNS_qlXpg4FGEvhj5CnQYFl@pg-33d239a3-superpig1999-942a.e.aivencloud.com:19130/defaultdb"

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

app = FastAPI(
    title="Virtual Training Assistant API",
    description="API for interacting with Strava training data",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Models
class StravaActivity(Base):
    __tablename__ = "strava_activities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    distance = Column(Float)
    moving_time = Column(Integer)
    type = Column(String)
    start_date = Column(DateTime)


# Pydantic Models
class ActivityCount(BaseModel):
    date: datetime.date
    count: int


class ActivityDetail(BaseModel):
    id: int
    name: str
    distance: float
    moving_time: int
    type: str
    start_date: datetime.datetime


class TotalDistance(BaseModel):
    total_distance: float


class AveragePace(BaseModel):
    average_pace: float


class WeeklyMileage(BaseModel):
    week: datetime.date
    weekly_distance_km: float


class BestEffort(BaseModel):
    id: int
    name: str
    distance: float
    moving_time: int
    type: str
    start_date: datetime.datetime


# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.get("/")
async def root():
    with open("index.html", "r") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)


@app.get("/activities/count/last_30_days", response_model=List[ActivityCount])
async def get_activity_count_last_30_days(db: Session = Depends(get_db)):
    results = (
        db.query(
            func.date(StravaActivity.start_date).label("date"),
            func.count().label("count"),
        )
        .filter(
            StravaActivity.start_date
            >= datetime.datetime.now() - datetime.timedelta(days=30)
        )
        .group_by(func.date(StravaActivity.start_date))
        .order_by(func.date(StravaActivity.start_date))
        .all()
    )
    return results


@app.get("/activities/last_n_days/{n}", response_model=List[ActivityDetail])
async def get_activities_last_n_days(n: int, db: Session = Depends(get_db)):
    results = (
        db.query(StravaActivity)
        .filter(
            StravaActivity.start_date
            >= datetime.datetime.now() - datetime.timedelta(days=n)
        )
        .order_by(StravaActivity.start_date.desc())
        .all()
    )
    return results


@app.get("/activities/total_distance/last_n_days/{n}", response_model=TotalDistance)
async def get_total_distance_last_n_days(n: int, db: Session = Depends(get_db)):
    result = (
        db.query(func.sum(StravaActivity.distance) / 1000)
        .filter(
            StravaActivity.start_date
            >= datetime.datetime.now() - datetime.timedelta(days=n)
        )
        .scalar()
    )
    return {"total_distance": result}


@app.get("/activities/average_pace/last_n_days/{n}", response_model=AveragePace)
async def get_average_pace_last_n_days(n: int, db: Session = Depends(get_db)):
    result = (
        db.query(func.avg(StravaActivity.distance / StravaActivity.moving_time * 3600))
        .filter(
            StravaActivity.type == "Run",
            StravaActivity.start_date
            >= datetime.datetime.now() - datetime.timedelta(days=n),
        )
        .scalar()
    )
    return {"average_pace": result}


@app.get("/activities/weekly_mileage_trend", response_model=List[WeeklyMileage])
async def get_weekly_mileage_trend(db: Session = Depends(get_db)):
    results = (
        db.query(
            func.date_trunc("week", StravaActivity.start_date).label("week"),
            func.sum(StravaActivity.distance) / 1000,
        )
        .filter(StravaActivity.type == "Run")
        .group_by(func.date_trunc("week", StravaActivity.start_date))
        .order_by(func.date_trunc("week", StravaActivity.start_date).desc())
        .limit(12)
        .all()
    )

    # Format the results to match the WeeklyMileage model
    formatted_results = [
        {"week": result[0], "weekly_distance_km": result[1]} for result in results
    ]

    return formatted_results


@app.get("/activities/details/{activity_id}", response_model=ActivityDetail)
async def get_activity_details(activity_id: int, db: Session = Depends(get_db)):
    result = db.query(StravaActivity).filter(StravaActivity.id == activity_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="Activity not found")
    return result


@app.get("/activities/best_efforts", response_model=List[BestEffort])
async def get_best_efforts(db: Session = Depends(get_db)):
    results = (
        db.query(StravaActivity)
        .filter(StravaActivity.type == "Run")
        .order_by(StravaActivity.distance.desc())
        .limit(5)
        .all()
    )
    return results


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
