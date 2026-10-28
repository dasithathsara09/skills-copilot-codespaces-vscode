from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base, get_db
from app.main import app

DB_PATH = Path("test.db")
TEST_DATABASE_URL = f"sqlite:///{DB_PATH.resolve()}"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    if DB_PATH.exists():
        DB_PATH.unlink()


def auth_headers(username="tester", pw="test-pass-123"):
    register_res = client.post("/auth/register", json={"username": username, "password": pw})
    assert register_res.status_code in {201, 400}

    token_res = client.post(
        "/auth/token",
        data={"username": username, "password": pw},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert token_res.status_code == 200
    token = token_res.json()["access_token"]
    return {"Authorization": "Bearer " + token}


def test_record_crud_and_dashboard():
    headers = auth_headers()

    payload = {
        "name": "Revenue Q1",
        "category": "Finance",
        "value": 1500.5,
        "recorded_on": "2026-10-01",
        "notes": "Initial import",
    }
    create_res = client.post("/records", json=payload, headers=headers)
    assert create_res.status_code == 201
    record_id = create_res.json()["id"]

    list_res = client.get("/records?search=Revenue&category=Finance", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1

    update_res = client.put(f"/records/{record_id}", json={"value": 1700.0}, headers=headers)
    assert update_res.status_code == 200
    assert update_res.json()["value"] == 1700.0

    dashboard_res = client.get("/dashboard", headers=headers)
    assert dashboard_res.status_code == 200
    dashboard_data = dashboard_res.json()
    assert dashboard_data["total_records"] == 1
    assert dashboard_data["distribution"][0]["category"] == "Finance"

    export_res = client.get("/records/export/csv", headers=headers)
    assert export_res.status_code == 200
    assert "Revenue Q1" in export_res.text

    report_res = client.get("/reports/summary", headers=headers)
    assert report_res.status_code == 200
    assert "Generated report" in report_res.json()["summary"]

    delete_res = client.delete(f"/records/{record_id}", headers=headers)
    assert delete_res.status_code == 204


def test_csv_import():
    headers = auth_headers(username="import-user")
    csv_content = "name,category,value,recorded_on,notes\nA,Ops,10,2026-10-01,n1\nB,Ops,20,2026-10-02,n2\n"

    import_res = client.post(
        "/records/import",
        headers=headers,
        files={"file": ("records.csv", csv_content, "text/csv")},
    )
    assert import_res.status_code == 201
    assert import_res.json()["imported"] == 2

    list_res = client.get("/records?category=Ops", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 2
