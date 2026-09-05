import bcrypt
from backend.app.database import SessionLocal
from backend.app.models import Student, Subject, Setting
from backend.app.config import settings

DEFAULT_SUBJECTS = [
    {"name": "数学", "full_score": 120.0, "sort_order": 1},
    {"name": "语文", "full_score": 120.0, "sort_order": 2},
    {"name": "英语", "full_score": 120.0, "sort_order": 3},
    {"name": "道德与法治", "full_score": 100.0, "sort_order": 4},
    {"name": "历史", "full_score": 100.0, "sort_order": 5},
    {"name": "地理", "full_score": 100.0, "sort_order": 6},
    {"name": "生物", "full_score": 100.0, "sort_order": 7},
]


def seed_database():
    db = SessionLocal()
    try:
        # 1. 确保默认学生存在
        student = db.query(Student).filter(Student.id == 1).first()
        if not student:
            student = Student(id=1, name="初一同学", grade="初一")
            db.add(student)

        # 2. 确保预置初一 7 科存在
        for sub_data in DEFAULT_SUBJECTS:
            existing = db.query(Subject).filter(Subject.name == sub_data["name"]).first()
            if not existing:
                db.add(Subject(**sub_data))

        # 3. 确保默认 PIN 口令哈希存在
        pin_setting = db.query(Setting).filter(Setting.key == "parent_pin_hash").first()
        if not pin_setting:
            salt = bcrypt.gensalt()
            hashed = bcrypt.hashpw(settings.DEFAULT_PIN.encode("utf-8"), salt).decode("utf-8")
            db.add(Setting(key="parent_pin_hash", value=hashed))

        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
    print("Database seeded successfully!")
