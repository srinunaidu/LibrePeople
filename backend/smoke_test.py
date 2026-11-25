"""Local smoke test using SQLite (no Oracle needed). Validates auth + employee flow."""
import os

os.environ["DATABASE_URL"] = "sqlite:///./smoke_test.db"
os.environ["SECRET_KEY"] = "local-test-secret-key-not-for-production-0123456789"
os.environ["MIGRATE_ON_STARTUP"] = "false"  # the suite builds its own schema
os.environ["BACKEND_CORS_ORIGINS"] = "*"

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.core.database import Base, engine  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.models.user import User  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402

Base.metadata.create_all(bind=engine)

# create admin
db = SessionLocal()
if not db.query(User).filter(User.username == "admin").first():
    db.add(User(username="admin", email="admin@k.local",
                hashed_password=get_password_hash("secret123"),
                role="SuperAdmin", is_active=True))
    db.commit()
db.close()

client = TestClient(app)

print("1. health:", client.get("/health").json())

r = client.post("/api/v1/auth/login", json={"username": "admin", "password": "secret123"})
print("2. login status:", r.status_code, "role:", r.json().get("role"))
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

r = client.post("/api/v1/departments/", json={"name": "Operations", "code": "OPS"}, headers=headers)
print("3. create department:", r.status_code, r.json())

r = client.post("/api/v1/employees/", headers=headers, json={
    "employee_id": "EMP001", "first_name": "Srinu", "last_name": "Naidu",
    "email": "srinu@example.com", "hire_date": "2026-10-18",
    "job_id": 1, "department_id": 1, "status": "Active", "salary": 50000,
})
print("4. create employee:", r.status_code, r.json())

r = client.get("/api/v1/employees/", headers=headers)
print("5. list employees:", r.status_code, r.json())

r = client.get("/api/v1/employees/", headers={"Authorization": "Bearer bad"})
print("6. unauthorized test (expect 403):", r.status_code)

print("\nSMOKE TEST COMPLETE")
