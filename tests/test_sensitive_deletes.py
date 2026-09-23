from datetime import date

from fastapi.testclient import TestClient

from backend.app.config import settings
from backend.app.database import SessionLocal
from backend.app.main import app
from backend.app.models import HomeworkItem, Paper, Subject


client = TestClient(app)


def test_sensitive_delete_endpoints_require_parent_pin():
    """日常读取和录入开放，但删除必须由服务端验证 PIN。"""
    db = SessionLocal()
    try:
        subject = db.query(Subject).first()
        homework = HomeworkItem(
            student_id=1,
            subject_id=subject.id,
            content="PIN 删除校验",
            date=date(2026, 9, 22),
        )
        paper = Paper(title="PIN 删除校验卷", student_name="同学", mistake_ids="[]")
        db.add_all([homework, paper])
        db.commit()
        db.refresh(homework)
        db.refresh(paper)

        assert client.delete(f"/api/homework/{homework.id}").status_code == 401
        assert client.delete(f"/api/paper/{paper.id}").status_code == 401

        headers = {"X-Parent-PIN": settings.DEFAULT_PIN}
        assert client.delete(f"/api/homework/{homework.id}", headers=headers).status_code == 200
        assert client.delete(f"/api/paper/{paper.id}", headers=headers).status_code == 200
    finally:
        db.close()
