from datetime import date, datetime
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import Subject, Student, ExamRecord, ExamScore, MistakeRecord, HomeworkItem
from backend.app.seed import seed_database

client = TestClient(app)


def _clean_m5_db():
    seed_database()
    db = SessionLocal()
    try:
        db.query(ExamScore).delete()
        db.query(ExamRecord).delete()
        db.query(MistakeRecord).delete()
        db.commit()
    finally:
        db.close()


def test_exam_crud_and_absent_calculation():
    """验证成绩录入、缺考分子分母跳过规则、更新及级联删除"""
    _clean_m5_db()
    db = SessionLocal()
    try:
        math_sub = db.query(Subject).filter(Subject.name == "数学").first()
        eng_sub = db.query(Subject).filter(Subject.name == "英语").first()
        geo_sub = db.query(Subject).filter(Subject.name == "地理").first()
        chi_sub = db.query(Subject).filter(Subject.name == "语文").first()

        # 录入：数学 110/120, 英语 115/120, 地理缺考 (None/100), 语文未考 (None/120, is_absent=False)
        payload = {
            "title": "初一单元质量检测",
            "exam_type": "单元测试",
            "exam_date": "2024-10-15",
            "class_rank": 3,
            "grade_rank": 12,
            "remarks": "地理缺考",
            "scores": [
                {"subject_id": math_sub.id, "score": 110.0, "full_score": 120.0, "is_absent": False},
                {"subject_id": eng_sub.id, "score": 115.0, "full_score": 120.0, "is_absent": False},
                {"subject_id": geo_sub.id, "score": None, "full_score": 100.0, "is_absent": True},
                {"subject_id": chi_sub.id, "score": None, "full_score": 120.0, "is_absent": False},
            ],
        }

        # 1. 创建测试：未考科目（语文）不会被误标为缺考，不写入明细
        res = client.post("/api/exams", json=payload)
        assert res.status_code == 200
        data = res.json()
        exam_id = data["id"]

        # 核心铁律：缺考科目不计入 total_score 与 total_full_score
        assert data["total_score"] == 225.0  # 110 + 115
        assert data["total_full_score"] == 240.0  # 120 + 120 (跳过地理 100)
        assert data["rate"] == round((225.0 / 240.0) * 100, 1)
        assert len(data["scores"]) == 3

        # 2. 列表查询测试
        res_list = client.get("/api/exams")
        assert res_list.status_code == 200
        items = res_list.json()
        assert len(items) == 1
        assert items[0]["id"] == exam_id
        assert items[0]["absent_count"] == 1

        # 3. 详情查询测试
        res_detail = client.get(f"/api/exams/{exam_id}")
        assert res_detail.status_code == 200
        assert res_detail.json()["title"] == "初一单元质量检测"

        # 4. 更新测试：地理补考，录入 85 分
        update_payload = {
            "title": "初一单元质量检测（补考后）",
            "scores": [
                {"subject_id": math_sub.id, "score": 110.0, "full_score": 120.0, "is_absent": False},
                {"subject_id": eng_sub.id, "score": 115.0, "full_score": 120.0, "is_absent": False},
                {"subject_id": geo_sub.id, "score": 85.0, "full_score": 100.0, "is_absent": False},
            ],
        }
        res_put = client.put(f"/api/exams/{exam_id}", json=update_payload)
        assert res_put.status_code == 200
        updated = res_put.json()
        assert updated["title"] == "初一单元质量检测（补考后）"
        assert updated["total_score"] == 310.0  # 110 + 115 + 85
        assert updated["total_full_score"] == 340.0  # 120 + 120 + 100

        # 5. 级联删除测试
        res_del = client.delete(f"/api/exams/{exam_id}")
        assert res_del.status_code == 200
        res_get_again = client.get(f"/api/exams/{exam_id}")
        assert res_get_again.status_code == 404
    finally:
        db.close()


def test_exam_trends_line_chart():
    """验证折线图走势接口与单次考试单点安全防御"""
    _clean_m5_db()
    db = SessionLocal()
    try:
        math_sub = db.query(Subject).filter(Subject.name == "数学").first()

        # 1. 仅有 1 次考试时测试单点输出，杜绝前端崩溃
        p1 = {
            "title": "第 1 次月考",
            "exam_date": "2024-10-01",
            "scores": [{"subject_id": math_sub.id, "score": 100.0, "full_score": 120.0}],
        }
        client.post("/api/exams", json=p1)

        res_single = client.get("/api/exams/charts/trends")
        assert res_single.status_code == 200
        data_single = res_single.json()
        assert len(data_single["items"]) == 1
        assert data_single["items"][0]["score"] == 100.0

        # 2. 录入第 2 次考试，测试单科过滤走势
        p2 = {
            "title": "第 2 次月考",
            "exam_date": "2024-11-01",
            "scores": [{"subject_id": math_sub.id, "score": 112.0, "full_score": 120.0}],
        }
        client.post("/api/exams", json=p2)

        res_math = client.get(f"/api/exams/charts/trends?subject_id={math_sub.id}")
        assert res_math.status_code == 200
        data_math = res_math.json()
        assert data_math["target"] == "数学"
        assert len(data_math["items"]) == 2
        assert data_math["items"][1]["score"] == 112.0
    finally:
        db.close()


def test_exam_radar_dynamic_indicators_and_absent():
    """验证雷达图动态轴过滤（缺考不入轴防拉垮）、缺考提示与少于 3 科 fallback"""
    _clean_m5_db()
    db = SessionLocal()
    try:
        math_sub = db.query(Subject).filter(Subject.name == "数学").first()
        chn_sub = db.query(Subject).filter(Subject.name == "语文").first()
        eng_sub = db.query(Subject).filter(Subject.name == "英语").first()
        geo_sub = db.query(Subject).filter(Subject.name == "地理").first()

        # 4 科考试，其中地理缺考
        p = {
            "title": "4 科期中模拟考",
            "exam_date": "2024-11-10",
            "scores": [
                {"subject_id": math_sub.id, "score": 110.0, "full_score": 120.0},
                {"subject_id": chn_sub.id, "score": 100.0, "full_score": 120.0},
                {"subject_id": eng_sub.id, "score": 115.0, "full_score": 120.0},
                {"subject_id": geo_sub.id, "score": None, "full_score": 100.0, "is_absent": True},
            ],
        }
        res_post = client.post("/api/exams", json=p)
        exam_id = res_post.json()["id"]

        # 测试雷达图接口
        res_radar = client.get(f"/api/exams/charts/radar?exam_id={exam_id}")
        assert res_radar.status_code == 200
        radar = res_radar.json()

        # 核心断言：缺考的地理不进入 indicators 维度轴，避免拉至 0 点
        indicator_names = [ind["name"] for ind in radar["indicators"]]
        assert "数学" in indicator_names
        assert "语文" in indicator_names
        assert "英语" in indicator_names
        assert "地理" not in indicator_names
        assert len(radar["values"]) == 3

        # 核心断言：地理记录在 absent_subjects 中显式提示
        assert "地理" in radar["absent_subjects"]
        assert radar["message"] is None

        # 测试少于 3 科时的友好 fallback 提示
        p_few = {
            "title": "单科数学测验",
            "exam_date": "2024-11-20",
            "scores": [{"subject_id": math_sub.id, "score": 118.0, "full_score": 120.0}],
        }
        res_few = client.post("/api/exams", json=p_few)
        few_id = res_few.json()["id"]

        res_radar_few = client.get(f"/api/exams/charts/radar?exam_id={few_id}")
        assert res_radar_few.status_code == 200
        assert "不足 3 门" in res_radar_few.json()["message"]
    finally:
        db.close()


def test_subject_weakness_diagnostics():
    """验证薄弱学科极简规则判定：得分率 < 60% 或 错题本未掌握错题 >= 3"""
    _clean_m5_db()
    db = SessionLocal()
    try:
        math_sub = db.query(Subject).filter(Subject.name == "数学").first()
        geo_sub = db.query(Subject).filter(Subject.name == "地理").first()

        # 1. 地理考了 55 分（< 60%）
        p = {
            "title": "月考",
            "exam_date": "2024-10-10",
            "scores": [
                {"subject_id": math_sub.id, "score": 110.0, "full_score": 120.0},
                {"subject_id": geo_sub.id, "score": 55.0, "full_score": 100.0},
            ],
        }
        client.post("/api/exams", json=p)

        # 2. 为数学录入 4 道未掌握错题（虽考试及格但错题堆积）
        math_mistakes = [
            MistakeRecord(student_id=1, subject_id=math_sub.id, extracted_text=f"数学错题{i}", mastery_status="未掌握")
            for i in range(4)
        ]
        db.add_all(math_mistakes)
        db.commit()

        # 诊断接口
        res = client.get("/api/exams/diagnostics/weaknesses")
        assert res.status_code == 200
        weaknesses = res.json()

        geo_item = next((item for item in weaknesses if item["subject_name"] == "地理"), None)
        math_item = next((item for item in weaknesses if item["subject_name"] == "数学"), None)

        assert geo_item is not None and geo_item["is_weak"] is True
        assert "不及格" in geo_item["reason"]

        assert math_item is not None and math_item["is_weak"] is True
        assert "4 道未掌握" in math_item["reason"]
    finally:
        db.close()


def test_monthly_analytics_aggregation():
    """验证家长深度月度学情看板聚合统计与作业遗漏学科分布"""
    _clean_m5_db()
    db = SessionLocal()
    try:
        math_sub = db.query(Subject).filter(Subject.name == "数学").first()
        eng_sub = db.query(Subject).filter(Subject.name == "英语").first()

        # 构造 2024-10 月数据：
        # 10-01: 数学(完成), 英语(完成) -> 100%
        # 10-02: 数学(完成), 英语(未完成) -> 50%
        hw1 = HomeworkItem(student_id=1, subject_id=math_sub.id, date=date(2024, 10, 1), content="t1", is_completed=True)
        hw2 = HomeworkItem(student_id=1, subject_id=eng_sub.id, date=date(2024, 10, 1), content="t2", is_completed=True)
        hw3 = HomeworkItem(student_id=1, subject_id=math_sub.id, date=date(2024, 10, 2), content="t3", is_completed=True)
        hw4 = HomeworkItem(student_id=1, subject_id=eng_sub.id, date=date(2024, 10, 2), content="t4", is_completed=False)

        db.add_all([hw1, hw2, hw3, hw4])
        db.commit()

        res = client.get("/api/exams/analytics/monthly?year=2024&month=10")
        assert res.status_code == 200
        data = res.json()

        assert data["year"] == 2024
        assert data["month"] == 10
        assert data["total_days"] == 31
        assert data["recorded_days"] == 2
        assert data["perfect_days"] == 1
        assert len(data["daily_trends"]) == 31

        # 检查学科缺卡频次分布：英语缺卡 1 次
        missing_dist = data["subject_missing_distribution"]
        assert len(missing_dist) == 1
        assert missing_dist[0]["subject_name"] == "英语"
        assert missing_dist[0]["missing_count"] == 1
    finally:
        db.close()
