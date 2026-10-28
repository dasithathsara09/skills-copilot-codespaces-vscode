import csv
from collections import defaultdict
from datetime import datetime
from io import StringIO

from fastapi import Depends, FastAPI, File, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session

from .auth import authenticate_user, create_access_token, get_current_user, hash_password
from .database import Base, engine, get_db
from .models import DataRecord, User
from .schemas import DashboardResponse, RecordCreate, RecordOut, RecordUpdate, ReportResponse, Token, UserCreate

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Analytics and Data Management API",
    description="JWT-protected REST API for dashboard analytics and data record management.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _build_metrics(records: list[DataRecord]) -> DashboardResponse:
    if not records:
        return DashboardResponse(
            total_records=0,
            total_value=0.0,
            average_value=0.0,
            trend=[],
            distribution=[],
        )

    total_value = sum(r.value for r in records)
    trend_map: dict[str, dict[str, float | int | str]] = defaultdict(lambda: {"count": 0, "value": 0.0})
    distribution_map: dict[str, dict[str, float | int | str]] = defaultdict(lambda: {"count": 0, "value": 0.0})

    for record in records:
        trend_key = record.recorded_on.isoformat()
        trend_map[trend_key]["count"] += 1
        trend_map[trend_key]["value"] += record.value

        distribution_map[record.category]["count"] += 1
        distribution_map[record.category]["value"] += record.value

    trend = [
        {"period": period, "count": int(values["count"]), "value": float(values["value"])}
        for period, values in sorted(trend_map.items())
    ]
    distribution = [
        {"category": category, "count": int(values["count"]), "value": float(values["value"])}
        for category, values in sorted(distribution_map.items())
    ]

    return DashboardResponse(
        total_records=len(records),
        total_value=round(total_value, 2),
        average_value=round(total_value / len(records), 2),
        trend=trend,
        distribution=distribution,
    )


@app.post("/auth/register", status_code=status.HTTP_201_CREATED)
def register(payload: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == payload.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    user = User(username=payload.username, password_hash=hash_password(payload.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "username": user.username}


@app.post("/auth/token", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect username or password")

    token = create_access_token({"sub": user.username})
    return Token(access_token=token)


@app.get("/records", response_model=list[RecordOut])
def list_records(
    search: str | None = Query(default=None),
    category: str | None = Query(default=None),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(DataRecord).filter(DataRecord.owner_id == current_user.id)
    if search:
        query = query.filter(DataRecord.name.ilike(f"%{search}%"))
    if category:
        query = query.filter(DataRecord.category == category)

    return query.order_by(DataRecord.recorded_on.desc()).offset(skip).limit(limit).all()


@app.post("/records", response_model=RecordOut, status_code=status.HTTP_201_CREATED)
def create_record(
    payload: RecordCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = DataRecord(**payload.model_dump(), owner_id=current_user.id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@app.get("/records/{record_id}", response_model=RecordOut)
def get_record(record_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    record = db.query(DataRecord).filter(DataRecord.id == record_id, DataRecord.owner_id == current_user.id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record


@app.put("/records/{record_id}", response_model=RecordOut)
def update_record(
    record_id: int,
    payload: RecordUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    record = db.query(DataRecord).filter(DataRecord.id == record_id, DataRecord.owner_id == current_user.id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(record, field, value)

    db.commit()
    db.refresh(record)
    return record


@app.delete("/records/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    record = db.query(DataRecord).filter(DataRecord.id == record_id, DataRecord.owner_id == current_user.id).first()
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")

    db.delete(record)
    db.commit()


@app.get("/dashboard", response_model=DashboardResponse)
def dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    records = db.query(DataRecord).filter(DataRecord.owner_id == current_user.id).all()
    return _build_metrics(records)


@app.post("/records/import", status_code=status.HTTP_201_CREATED)
async def import_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Only CSV files are supported")

    content = (await file.read()).decode("utf-8")
    reader = csv.DictReader(StringIO(content))
    required = {"name", "category", "value", "recorded_on", "notes"}
    if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
        raise HTTPException(status_code=400, detail="CSV must contain name, category, value, recorded_on, notes columns")

    created_count = 0
    for row in reader:
        record = DataRecord(
            name=row["name"],
            category=row["category"],
            value=float(row["value"]),
            recorded_on=datetime.strptime(row["recorded_on"], "%Y-%m-%d").date(),
            notes=row.get("notes"),
            owner_id=current_user.id,
        )
        db.add(record)
        created_count += 1

    db.commit()
    return {"imported": created_count}


@app.get("/records/export/csv")
def export_csv(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    records = db.query(DataRecord).filter(DataRecord.owner_id == current_user.id).order_by(DataRecord.recorded_on.asc()).all()

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "name", "category", "value", "recorded_on", "notes"])
    for record in records:
        writer.writerow([record.id, record.name, record.category, record.value, record.recorded_on.isoformat(), record.notes or ""])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=records.csv"},
    )


@app.get("/reports/summary", response_model=ReportResponse)
def report_summary(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    records = db.query(DataRecord).filter(DataRecord.owner_id == current_user.id).all()
    metrics = _build_metrics(records)
    summary = (
        f"Generated report with {metrics.total_records} records. "
        f"Total value is {metrics.total_value}, average value is {metrics.average_value}."
    )
    return ReportResponse(generated_at=datetime.utcnow(), summary=summary, metrics=metrics)


@app.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(func.count(User.id).select())
    return {"status": "ok"}
