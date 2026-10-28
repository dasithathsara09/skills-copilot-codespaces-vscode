from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RecordBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    category: str = Field(min_length=1, max_length=80)
    value: float
    recorded_on: date
    notes: str | None = None


class RecordCreate(RecordBase):
    pass


class RecordUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    category: str | None = Field(default=None, min_length=1, max_length=80)
    value: float | None = None
    recorded_on: date | None = None
    notes: str | None = None


class RecordOut(RecordBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DashboardResponse(BaseModel):
    total_records: int
    total_value: float
    average_value: float
    trend: list[dict[str, str | float | int]]
    distribution: list[dict[str, str | float | int]]


class ReportResponse(BaseModel):
    generated_at: datetime
    summary: str
    metrics: DashboardResponse
