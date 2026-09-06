import io
import time
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi.testclient import TestClient
from PIL import Image

from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import Subject, Student, MistakeRecord, MistakeReview, Paper
from backend.app.utils.image_handler import save_image_bytes

client = TestClient(app)


def _clean_db():
    db = SessionLocal()
    db.query(MistakeReview).delete()
    db.query(Paper).delete()
    db.query(MistakeRecord).delete()
    db.commit()
    db.close()


def _create_dummy_image() -> str:
    """生成一张微型图片并保存，返回原图可访问 URL"""
    im = Image.new("RGB", (100, 100), color="blue")
    buf = io.BytesIO()
    im.save(buf, format="JPEG")
    _, rel_orig, _ = save_image_bytes(buf.getvalue(), filename="test_img.jpg")
    return rel_orig


def test_paper_candidates_presets():
    """验证四大候选预设过滤：本周新增、艾宾浩斯临界、高频未掌握，以及交集不去重"""
    _clean_db()
    db = SessionLocal()
    try:
        math_sub = db.query(Subject).filter(Subject.name == "数学").first()
        today = date.today()
        monday = today - timedelta(days=today.weekday())

        # 1. 本周新增 (本周一创建，未复习)
        r1 = MistakeRecord(
            student_id=1,
            subject_id=math_sub.id,
            extracted_text="本周新增错题",
            mastery_status="未掌握",
            review_count=0,
            next_review_date=today,
            created_at=datetime.combine(monday, datetime.min.time()) + timedelta(hours=2),
        )
        # 2. 艾宾浩斯临界题 (next_review_date <= today 且未掌握)
        r2 = MistakeRecord(
            student_id=1,
            subject_id=math_sub.id,
            extracted_text="艾宾浩斯临界题",
            mastery_status="待复习",
            review_count=1,
            next_review_date=today,
            created_at=datetime.now() - timedelta(days=20),
        )
        # 3. 高频未掌握 (review_count >= 2 且未掌握)
        r3 = MistakeRecord(
            student_id=1,
            subject_id=math_sub.id,
            extracted_text="高频未掌握题",
            mastery_status="未掌握",
            review_count=3,
            next_review_date=today + timedelta(days=5),
            created_at=datetime.now() - timedelta(days=30),
        )
        # 4. 双重命中题：同时满足艾宾浩斯(next<=today) 与 高频未掌握(review_count>=2)
        r4 = MistakeRecord(
            student_id=1,
            subject_id=math_sub.id,
            extracted_text="双重命中题",
            mastery_status="未掌握",
            review_count=2,
            next_review_date=today - timedelta(days=1),
            created_at=datetime.now() - timedelta(days=15),
        )
        # 5. 已掌握的题（不应被任何复习预设命中）
        r5 = MistakeRecord(
            student_id=1,
            subject_id=math_sub.id,
            extracted_text="已掌握题",
            mastery_status="已掌握",
            review_count=4,
            next_review_date=None,
            created_at=datetime.now() - timedelta(days=10),
        )

        db.add_all([r1, r2, r3, r4, r5])
        db.commit()

        # 测试 this_week 预设
        res_week = client.get("/api/paper/candidates?preset=this_week")
        assert res_week.status_code == 200
        week_ids = [item["id"] for item in res_week.json()]
        assert r1.id in week_ids

        # 测试 ebbinghaus 预设
        res_ebb = client.get("/api/paper/candidates?preset=ebbinghaus")
        assert res_ebb.status_code == 200
        ebb_ids = [item["id"] for item in res_ebb.json()]
        assert r2.id in ebb_ids
        assert r4.id in ebb_ids  # 双重命中包含在此
        assert r5.id not in ebb_ids

        # 测试 unmastered 预设
        res_unm = client.get("/api/paper/candidates?preset=unmastered")
        assert res_unm.status_code == 200
        unm_ids = [item["id"] for item in res_unm.json()]
        assert r3.id in unm_ids
        assert r4.id in unm_ids  # 双重命中也包含在此（不去重，后端完整返回）
        assert r5.id not in unm_ids

        # 测试全库自选
        res_all = client.get("/api/paper/candidates?preset=all")
        assert res_all.status_code == 200
        all_ids = [item["id"] for item in res_all.json()]
        assert len(all_ids) == 5
    finally:
        db.close()


def test_paper_compose_endpoint_and_assets():
    """验证组装接口生成顺序编号、原图 URL 可访问性、留白高度、学生姓名及 papers 表落库"""
    _clean_db()
    db = SessionLocal()
    try:
        math_sub = db.query(Subject).filter(Subject.name == "数学").first()
        img_url = _create_dummy_image()

        r1 = MistakeRecord(
            student_id=1,
            subject_id=math_sub.id,
            extracted_text="几何大题测试",
            original_image_path=img_url,
            mastery_status="未掌握",
        )
        r2 = MistakeRecord(
            student_id=1,
            subject_id=math_sub.id,
            extracted_text="代数计算测试",
            original_image_path=None,
            mastery_status="未掌握",
        )
        db.add_all([r1, r2])
        db.commit()

        # 调 compose 接口
        payload = {
            "mistake_ids": [r1.id, r2.id],
            "title": "单元自测周末卷",
            "subtitle": "用时45分钟",
            "sort_by": "order",
            "space_level": "standard",
            "style_mode": "grid",
            "show_error_type": True,
        }
        res = client.post("/api/paper/compose", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["paper_id"] > 0
        assert data["title"] == "单元自测周末卷"
        assert data["student_name"] == "初一同学"
        assert data["total_questions"] == 2
        assert len(data["questions"]) == 2

        q1 = data["questions"][0]
        assert q1["order_num"] == 1
        assert q1["original_image_path"] == img_url
        assert q1["space_mm"] == 45  # standard 默认 45mm >= 40mm

        # 验证原图 HTTP GET 契约
        img_res = client.get(q1["original_image_path"])
        assert img_res.status_code == 200
        assert "image" in img_res.headers.get("content-type", "")

        # 验证 papers 表真实落盘
        paper_in_db = db.query(Paper).filter(Paper.id == data["paper_id"]).first()
        assert paper_in_db is not None
        assert paper_in_db.title == "单元自测周末卷"
    finally:
        db.close()


def test_paper_estimate_pages_rough():
    """验证粗略页数估算公式：max(1, round(total/4) + ceil(img/6))"""
    _clean_db()
    db = SessionLocal()
    try:
        math_sub = db.query(Subject).filter(Subject.name == "数学").first()
        img_url = _create_dummy_image()

        # 构造 20 道题，其中 6 道带图
        records = []
        for i in range(20):
            has_img = i < 6
            rec = MistakeRecord(
                student_id=1,
                subject_id=math_sub.id,
                extracted_text=f"题目 {i + 1}",
                original_image_path=img_url if has_img else None,
                mastery_status="未掌握",
            )
            records.append(rec)
        db.add_all(records)
        db.commit()

        # 20 题 6 图 -> round(20/4)=5 + ceil(6/6)=1 -> 6 页
        res = client.post("/api/paper/compose", json={"mistake_ids": [r.id for r in records]})
        assert res.status_code == 200
        assert res.json()["estimated_pages"] == 6

        # 0 题 -> 1 页
        res_empty = client.post("/api/paper/compose", json={"mistake_ids": []})
        assert res_empty.status_code == 200
        assert res_empty.json()["estimated_pages"] == 1

        # 100 题无图 -> round(100/4) = 25 页
        bulk_100 = [
            MistakeRecord(
                student_id=1,
                subject_id=math_sub.id,
                extracted_text=f"估算页数题 {i}",
                mastery_status="未掌握",
            )
            for i in range(100)
        ]
        db.add_all(bulk_100)
        db.commit()
        res_100 = client.post(
            "/api/paper/compose", json={"mistake_ids": [r.id for r in bulk_100]}
        )
        assert res_100.status_code == 200
        assert res_100.json()["estimated_pages"] == 25
    finally:
        db.close()


def test_paper_oversized_heuristic():
    """验证后端超长题启发式标记：字数>800 或 宽敞留白+字数>400"""
    _clean_db()
    db = SessionLocal()
    try:
        math_sub = db.query(Subject).filter(Subject.name == "数学").first()

        # 1. 文本长度边界测试：
        # 超长阅读 (800 字整，达到 >= 800 阈值)
        long_text = "这是测试长文本！" * 100  # 恰好 800 字（>=800 阈值）
        r_long = MistakeRecord(
            student_id=1,
            subject_id=math_sub.id,
            extracted_text=long_text,
            mastery_status="未掌握",
        )
        # 中等长度 (440 字，spacious 下超限，standard 下不超限)
        medium_text = "这是中等长度文。" * 55  # 恰好 440 字
        r_med = MistakeRecord(
            student_id=1,
            subject_id=math_sub.id,
            extracted_text=medium_text,
            mastery_status="未掌握",
        )
        # 短文本 (18 字)
        r_short = MistakeRecord(
            student_id=1,
            subject_id=math_sub.id,
            extracted_text="这是一道普通的短题目，仅有几十个字。",
            mastery_status="未掌握",
        )

        # 2. 图文结合超长启发式测试：
        dummy_img = _create_dummy_image()
        # 504 字 + 带图 -> standard 下即标记 oversized (>= 500)
        r_img_long = MistakeRecord(
            student_id=1,
            subject_id=math_sub.id,
            extracted_text="五百字带图长文本" * 63,  # 504 字
            original_image_path=dummy_img,
            mastery_status="未掌握",
        )
        # 256 字 + 带图 -> spacious 下标记 oversized (>= 250)，standard 下不标记
        r_img_med = MistakeRecord(
            student_id=1,
            subject_id=math_sub.id,
            extracted_text="二百五十字符文本" * 32,  # 256 字
            original_image_path=dummy_img,
            mastery_status="未掌握",
        )

        db.add_all([r_long, r_med, r_short, r_img_long, r_img_med])
        db.commit()

        # 1. 标准留白下：r_long(>=800) 与 r_img_long(>=500+图) 标记 oversized，其余不标记
        res_std = client.post(
            "/api/paper/compose",
            json={
                "mistake_ids": [r_long.id, r_med.id, r_short.id, r_img_long.id, r_img_med.id],
                "space_level": "standard",
            },
        )
        assert res_std.status_code == 200
        qs_std = res_std.json()["questions"]
        assert qs_std[0]["is_oversized"] is True
        assert qs_std[1]["is_oversized"] is False
        assert qs_std[2]["is_oversized"] is False
        assert qs_std[3]["is_oversized"] is True
        assert qs_std[4]["is_oversized"] is False
        assert len(res_std.json()["warnings"]) >= 2

        # 2. 宽敞留白下：r_long, r_med, r_img_long, r_img_med 均标记 oversized
        res_spa = client.post(
            "/api/paper/compose",
            json={
                "mistake_ids": [r_long.id, r_med.id, r_short.id, r_img_long.id, r_img_med.id],
                "space_level": "spacious",
            },
        )
        assert res_spa.status_code == 200
        qs_spa = res_spa.json()["questions"]
        assert qs_spa[0]["is_oversized"] is True
        assert qs_spa[1]["is_oversized"] is True
        assert qs_spa[2]["is_oversized"] is False
        assert qs_spa[3]["is_oversized"] is True
        assert qs_spa[4]["is_oversized"] is True
    finally:
        db.close()


def test_paper_empty_and_extreme_amounts():
    """验证 0 题、1 题、100 题极限数据下的接口稳定性和响应速度 (<500ms)"""
    _clean_db()
    db = SessionLocal()
    try:
        math_sub = db.query(Subject).filter(Subject.name == "数学").first()

        # 0 题测试
        res_0 = client.post("/api/paper/compose", json={"mistake_ids": []})
        assert res_0.status_code == 200
        assert res_0.json()["total_questions"] == 0
        assert res_0.json()["estimated_pages"] == 1

        # 1 题测试
        r1 = MistakeRecord(
            student_id=1,
            subject_id=math_sub.id,
            extracted_text="单题测试",
            mastery_status="未掌握",
        )
        db.add(r1)
        db.commit()
        res_1 = client.post("/api/paper/compose", json={"mistake_ids": [r1.id]})
        assert res_1.status_code == 200
        assert res_1.json()["total_questions"] == 1

        # 100 题批量压测
        bulk_records = [
            MistakeRecord(
                student_id=1,
                subject_id=math_sub.id,
                extracted_text=f"批量第 {i} 题",
                mastery_status="未掌握",
            )
            for i in range(100)
        ]
        db.add_all(bulk_records)
        db.commit()

        start_time = time.time()
        res_100 = client.post(
            "/api/paper/compose", json={"mistake_ids": [r.id for r in bulk_records]}
        )
        elapsed_ms = (time.time() - start_time) * 1000

        assert res_100.status_code == 200
        assert res_100.json()["total_questions"] == 100
        assert elapsed_ms < 500  # 要求响应时间小于 500ms
    finally:
        db.close()


def test_paper_batch_review_transaction():
    """验证批量打卡单事务推进艾宾浩斯复习周期与部分失败容错"""
    _clean_db()
    db = SessionLocal()
    try:
        math_sub = db.query(Subject).filter(Subject.name == "数学").first()
        today = date.today()

        records = [
            MistakeRecord(
                student_id=1,
                subject_id=math_sub.id,
                extracted_text=f"测试题 {i}",
                mastery_status="未掌握",
                review_count=0,
                next_review_date=today,
            )
            for i in range(5)
        ]
        db.add_all(records)
        db.commit()

        compose_res = client.post(
            "/api/paper/compose", json={"mistake_ids": [r.id for r in records]}
        )
        paper_id = compose_res.json()["paper_id"]

        # 构造打卡入参：其中包含 2 个不存在的非法 ID
        reviews = [
            {"mistake_id": records[0].id, "result": "remembered"},
            {"mistake_id": records[1].id, "result": "remembered"},
            {"mistake_id": records[2].id, "result": "forgotten"},
            {"mistake_id": 999991, "result": "remembered"},  # 不存在
            {"mistake_id": 999992, "result": "forgotten"},   # 不存在
        ]

        batch_res = client.post(f"/api/paper/{paper_id}/batch_review", json={"reviews": reviews})
        assert batch_res.status_code == 200
        body = batch_res.json()

        # 断言成功 3 题，失败 2 题
        assert len(body["success"]) == 3
        assert len(body["failed"]) == 2
        assert body["failed"][0]["mistake_id"] == 999991

        # 断言艾宾浩斯流转：
        # records[0]: review_count 0 -> 1, next_review_date = today + 3
        db.refresh(records[0])
        assert records[0].review_count == 1
        assert records[0].next_review_date == today + timedelta(days=3)
        assert records[0].mastery_status == "待复习"

        # records[2]: forgotten -> review_count 0, next_review_date = today + 1
        db.refresh(records[2])
        assert records[2].next_review_date == today + timedelta(days=1)
        assert records[2].mastery_status == "未掌握"

        # 断言试卷状态变更为 reviewed
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        assert paper.status == "reviewed"
    finally:
        db.close()


def test_paper_recovery_by_id():
    """验证通过 paper_id 精确恢复试卷快照"""
    _clean_db()
    db = SessionLocal()
    try:
        math_sub = db.query(Subject).filter(Subject.name == "数学").first()
        records = [
            MistakeRecord(student_id=1, subject_id=math_sub.id, extracted_text=f"恢复题 {i}")
            for i in range(3)
        ]
        db.add_all(records)
        db.commit()

        orig = client.post(
            "/api/paper/compose",
            json={"mistake_ids": [r.id for r in records], "title": "期中复习卷"},
        ).json()

        paper_id = orig["paper_id"]
        res = client.get(f"/api/paper/{paper_id}")
        assert res.status_code == 200
        recovered = res.json()

        assert recovered["paper_id"] == paper_id
        assert recovered["title"] == "期中复习卷"
        assert recovered["total_questions"] == 3
        assert recovered["student_name"] == orig["student_name"]
        assert len(recovered["questions"]) == 3
        assert recovered["questions"][0]["order_num"] == 1
    finally:
        db.close()


def test_print_css_rules_exist():
    """纯文本断言前端 print.css 必须包含核心排版与防截断规范"""
    css_path = Path("frontend/src/assets/print.css").resolve()
    assert css_path.exists(), "frontend/src/assets/print.css 文件不存在"

    content = css_path.read_text(encoding="utf-8")

    # 1. 断言 @page 与 @bottom-center 页码计数器
    assert "@page" in content
    assert "@bottom-center" in content
    assert "counter(page)" in content
    assert "counter(pages)" in content

    # 2. 断言防截断规范与父级 block
    assert "break-inside: avoid" in content
    assert ".is-oversized" in content
    assert "break-inside: auto" in content
    assert "display: block !important" in content

    # 3. 断言颜色与底纹强制输出
    assert "print-color-adjust: exact" in content or "-webkit-print-color-adjust: exact" in content

    # 4. 断言打印态清除与视口清除
    assert "min-height: 0 !important" in content
    assert ".van-tabbar" in content
    assert "display: none !important" in content

    # 5. 断言屏幕态解除 500px 宽度限制
    assert ".app-container--wide" in content
    assert "max-width: none !important" in content


def test_paper_history_endpoint():
    """验证 GET /api/paper/history 正常响应（杜绝 /{paper_id} 422 路由截胡回归）"""
    _clean_db()
    db = SessionLocal()
    try:
        math_sub = db.query(Subject).filter(Subject.name == "数学").first()
        r = MistakeRecord(student_id=1, subject_id=math_sub.id, extracted_text="历史测试题")
        db.add(r)
        db.commit()

        # 生成 2 份试卷
        res1 = client.post("/api/paper/compose", json={"mistake_ids": [r.id], "title": "第一卷"})
        res2 = client.post("/api/paper/compose", json={"mistake_ids": [r.id], "title": "第二卷"})
        p2_id = res2.json()["paper_id"]

        # 标记 p2 为 printed
        client.post(f"/api/paper/{p2_id}/mark_printed")

        # 核心防回归断言：GET /api/paper/history 必须返回 200 列表，严禁被 /{paper_id} 截胡返回 422
        res_hist = client.get("/api/paper/history")
        assert res_hist.status_code == 200
        items = res_hist.json()
        assert isinstance(items, list)
        assert len(items) == 2
        assert items[0]["title"] == "第二卷"
        assert items[0]["status"] == "printed"
        assert items[1]["title"] == "第一卷"
        assert items[1]["status"] == "draft"

        # 测试 status 过滤
        res_filtered = client.get("/api/paper/history?status=printed")
        assert res_filtered.status_code == 200
        assert len(res_filtered.json()) == 1
        assert res_filtered.json()[0]["id"] == p2_id

        # 测试 limit 限制
        res_limit = client.get("/api/paper/history?limit=1")
        assert res_limit.status_code == 200
        assert len(res_limit.json()) == 1
    finally:
        db.close()


def test_paper_get_not_found():
    """验证 GET /api/paper/{paper_id} 不存在时正确返回 404"""
    res = client.get("/api/paper/999999")
    assert res.status_code == 404
    assert "不存在" in res.json()["detail"]


def test_paper_sort_modes():
    """验证 sort_by=order, subject, random 排序行为与非核心科综合兜底"""
    _clean_db()
    db = SessionLocal()
    try:
        math_sub = db.query(Subject).filter(Subject.name == "数学").first()
        eng_sub = db.query(Subject).filter(Subject.name == "英语").first()
        # 查找或创建一个非核心 7 科的辅助科目（如美术）
        art_sub = db.query(Subject).filter(Subject.name == "美术").first()
        if not art_sub:
            art_sub = Subject(name="美术", full_score=100.0, sort_order=9)
            db.add(art_sub)
            db.commit()

        r_math = MistakeRecord(student_id=1, subject_id=math_sub.id, extracted_text="数学题")
        r_eng = MistakeRecord(student_id=1, subject_id=eng_sub.id, extracted_text="英语题")
        r_art = MistakeRecord(student_id=1, subject_id=art_sub.id, extracted_text="美术题")
        db.add_all([r_math, r_eng, r_art])
        db.commit()

        input_ids = [r_art.id, r_eng.id, r_math.id]

        # 1. sort_by="order"：严格保持输入顺序
        res_order = client.post(
            "/api/paper/compose", json={"mistake_ids": input_ids, "sort_by": "order"}
        )
        assert res_order.status_code == 200
        q_order_ids = [q["id"] for q in res_order.json()["questions"]]
        assert q_order_ids == input_ids

        # 2. sort_by="subject"：核心 7 科按 sort_order 升序排前（数学=1，英语=3），非核心科排在最后并归入"综合"
        res_sub = client.post(
            "/api/paper/compose", json={"mistake_ids": input_ids, "sort_by": "subject"}
        )
        assert res_sub.status_code == 200
        qs_sub = res_sub.json()["questions"]
        assert [q["id"] for q in qs_sub] == [r_math.id, r_eng.id, r_art.id]
        assert qs_sub[0]["subject_name"] == "数学"
        assert qs_sub[1]["subject_name"] == "英语"
        assert qs_sub[2]["subject_name"] == "综合"

        # 3. sort_by="random"：包含全部题目且结果落库固定
        res_rnd = client.post(
            "/api/paper/compose", json={"mistake_ids": input_ids, "sort_by": "random"}
        )
        assert res_rnd.status_code == 200
        rnd_ids = [q["id"] for q in res_rnd.json()["questions"]]
        assert set(rnd_ids) == set(input_ids)
        # 通过 paper_id 恢复查验顺序是否持久化不变
        p_id = res_rnd.json()["paper_id"]
        res_get = client.get(f"/api/paper/{p_id}")
        assert [q["id"] for q in res_get.json()["questions"]] == rnd_ids
    finally:
        db.close()


def test_paper_mark_printed():
    """验证 POST /api/paper/{paper_id}/mark_printed 状态流转契约与防误逆转"""
    _clean_db()
    db = SessionLocal()
    try:
        math_sub = db.query(Subject).filter(Subject.name == "数学").first()
        r = MistakeRecord(student_id=1, subject_id=math_sub.id, extracted_text="打印状态题")
        db.add(r)
        db.commit()

        # 1. 新建试卷状态为 draft
        compose_res = client.post("/api/paper/compose", json={"mistake_ids": [r.id]})
        paper_id = compose_res.json()["paper_id"]
        assert compose_res.json()["status"] == "draft"

        # 2. 调起打印回写为 printed
        mark_res = client.post(f"/api/paper/{paper_id}/mark_printed")
        assert mark_res.status_code == 200
        assert mark_res.json()["status"] == "printed"

        # 3. 打卡后变为 reviewed
        review_res = client.post(
            f"/api/paper/{paper_id}/batch_review",
            json={"reviews": [{"mistake_id": r.id, "result": "remembered"}]},
        )
        assert review_res.status_code == 200
        paper = db.query(Paper).filter(Paper.id == paper_id).first()
        assert paper.status == "reviewed"

        # 4. 已打卡试卷若重复打印，不能逆转为 printed，保持 reviewed
        re_mark = client.post(f"/api/paper/{paper_id}/mark_printed")
        assert re_mark.status_code == 200
        assert re_mark.json()["status"] == "reviewed"

        # 5. 不存在的试卷返回 404
        not_found_res = client.post("/api/paper/999999/mark_printed")
        assert not_found_res.status_code == 404
    finally:
        db.close()


def test_paper_include_all_subjects():
    """验证 candidates 接口 include_all_subjects 过滤与非 7 科'综合'大题兜底"""
    _clean_db()
    db = SessionLocal()
    try:
        math_sub = db.query(Subject).filter(Subject.name == "数学").first()
        # 确保存在一个非核心 7 科的辅助科目（如信息科技）
        it_sub = db.query(Subject).filter(Subject.name == "信息科技").first()
        if not it_sub:
            it_sub = Subject(name="信息科技", full_score=100.0, sort_order=8)
            db.add(it_sub)
            db.commit()

        r_math = MistakeRecord(student_id=1, subject_id=math_sub.id, extracted_text="数学错题")
        r_it = MistakeRecord(student_id=1, subject_id=it_sub.id, extracted_text="信息科技错题")
        db.add_all([r_math, r_it])
        db.commit()

        # 1. 默认 include_all_subjects=False：仅返回 7 科内题目，信息科技被过滤
        res_default = client.get("/api/paper/candidates")
        assert res_default.status_code == 200
        default_ids = [item["id"] for item in res_default.json()]
        assert r_math.id in default_ids
        assert r_it.id not in default_ids

        # 2. 显式 include_all_subjects=True：全量返回，包含信息科技
        res_all = client.get("/api/paper/candidates?include_all_subjects=true")
        assert res_all.status_code == 200
        all_ids = [item["id"] for item in res_all.json()]
        assert r_math.id in all_ids
        assert r_it.id in all_ids

        # 3. 组卷时信息科技大题显示为'综合'
        res_compose = client.post(
            "/api/paper/compose", json={"mistake_ids": [r_it.id], "sort_by": "subject"}
        )
        assert res_compose.status_code == 200
        assert res_compose.json()["questions"][0]["subject_name"] == "综合"
    finally:
        db.close()

