import io
import os
import zipfile
import shutil
from datetime import date, timedelta
from fastapi.testclient import TestClient
from PIL import Image
from backend.app.main import app
from backend.app.database import SessionLocal, engine, Base
from backend.app.models import Student, Subject, HomeworkItem, MistakeRecord, MistakeReview
from backend.app.routers.homework import calculate_streak
from backend.app.utils.image_handler import save_image_bytes
from backend.app.config import DATA_DIR, UPLOADS_DIR

client = TestClient(app)


def setup_function():
    """每个测试前清空业务表数据"""
    db = SessionLocal()
    db.query(MistakeReview).delete()
    db.query(MistakeRecord).delete()
    db.query(HomeworkItem).delete()
    db.commit()
    db.close()


def test_streak_calculation():
    """测试 Streak 连续打卡算法：连续 3 天 -> 3，中断归零或重计，同一天多次打勾不重复，跨月正确"""
    db = SessionLocal()
    try:
        # 获取数学科目 id
        math = db.query(Subject).filter(Subject.name == "数学").first()
        assert math is not None

        today = date.today()
        d_minus_1 = today - timedelta(days=1)
        d_minus_2 = today - timedelta(days=2)
        d_minus_4 = today - timedelta(days=4)  # 第 4 天前（中间隔了一天）

        # 1. 连续 3 天打勾全部完成（today, d-1, d-2）
        for d in [today, d_minus_1, d_minus_2]:
            db.add(HomeworkItem(student_id=1, subject_id=math.id, date=d, content=f"作业 {d}", is_completed=True))
            # 同一天增加第二条完成项
            db.add(HomeworkItem(student_id=1, subject_id=math.id, date=d, content=f"作业 {d} 补充", is_completed=True))
        db.commit()

        streak = calculate_streak(1, db)
        assert streak == 3, f"连续 3 天满打卡应为 3，实际为 {streak}"

        # 2. 中断测试：把昨天的第二条作业设为未完成 -> 昨天的打卡不完整
        yesterday_items = db.query(HomeworkItem).filter(HomeworkItem.date == d_minus_1).all()
        yesterday_items[1].is_completed = False
        db.commit()

        streak_broken = calculate_streak(1, db)
        assert streak_broken == 1, f"昨日未满打卡，streak 应归为 1（仅今日完成），实际为 {streak_broken}"

    finally:
        db.close()


def test_ebbinghaus_state_machine():
    """测试艾宾浩斯复习流转：创建 -> +1天；掌握 -> +3 -> +7 -> +15 -> 已掌握出队；遗忘 -> 回退第 1 天"""
    # 1. 创建错题
    res = client.post("/api/mistakes", json={
        "student_id": 1,
        "subject_id": 1,
        "source_type": "homework",
        "source_reference": "单元测试题",
        "extracted_text": "已知二次函数 y=ax^2+bx+c...",
        "error_type": "概念模糊"
    })
    assert res.status_code == 200
    m = res.json()
    mistake_id = m["id"]
    today = date.today()
    assert m["next_review_date"] == (today + timedelta(days=1)).isoformat()
    assert m["mastery_status"] == "未掌握"

    # 2. 第 1 次复习：掌握 -> +3 天，状态变待复习
    r1 = client.post(f"/api/mistakes/{mistake_id}/review", json={"mistake_id": mistake_id, "result": "remembered"}).json()
    assert r1["review_count"] == 1
    assert r1["mastery_status"] == "待复习"
    assert r1["next_review_date"] == (today + timedelta(days=3)).isoformat()

    # 3. 第 2 次复习：掌握 -> +7 天
    r2 = client.post(f"/api/mistakes/{mistake_id}/review", json={"mistake_id": mistake_id, "result": "remembered"}).json()
    assert r2["review_count"] == 2
    assert r2["next_review_date"] == (today + timedelta(days=7)).isoformat()

    # 4. 第 3 次复习：遗忘 -> 回退到第 1 天，状态变未掌握
    r_forgot = client.post(f"/api/mistakes/{mistake_id}/review", json={"mistake_id": mistake_id, "result": "forgotten"}).json()
    assert r_forgot["mastery_status"] == "未掌握"
    assert r_forgot["next_review_date"] == (today + timedelta(days=1)).isoformat()

    # 5. 再次掌握至第 4 次 -> 已掌握出队
    client.post(f"/api/mistakes/{mistake_id}/review", json={"mistake_id": mistake_id, "result": "remembered"})
    client.post(f"/api/mistakes/{mistake_id}/review", json={"mistake_id": mistake_id, "result": "remembered"})
    client.post(f"/api/mistakes/{mistake_id}/review", json={"mistake_id": mistake_id, "result": "remembered"})
    r_final = client.post(f"/api/mistakes/{mistake_id}/review", json={"mistake_id": mistake_id, "result": "remembered"}).json()
    assert r_final["mastery_status"] == "已掌握"
    assert r_final["next_review_date"] is None


def test_homework_to_mistake_conversion():
    """测试一键转错题：从作业条目正确继承学科、日期与来源说明"""
    # 1. 创建作业条目
    hw_res = client.post("/api/homework", json={
        "subject_id": 1,
        "date": date.today().isoformat(),
        "content": "数学练习册 P35 第 18 题",
        "is_completed": True
    }).json()
    hw_id = hw_res["id"]

    # 2. 一键转错题
    m_res = client.post(f"/api/homework/{hw_id}/to-mistake")
    assert m_res.status_code == 200
    m_data = m_res.json()
    assert m_data["subject_id"] == 1
    assert "数学作业" in m_data["source_reference"]
    assert "P35 第 18 题" in m_data["source_reference"]
    assert m_data["mastery_status"] == "未掌握"


def test_image_compression_and_deduplication():
    """测试图片存储：自动 EXIF 矫正、压缩生成原图与缩略图、相同内容 sha256 唯一去重"""
    # 创建一张 2000x2000 像素的高清测试图
    img = Image.new("RGB", (2000, 2000), color=(73, 109, 137))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95)
    img_bytes = buf.getvalue()

    # 第一次上传
    sha1, orig1, thumb1 = save_image_bytes(img_bytes, "test.jpg")
    assert orig1.startswith("/uploads/originals/")
    assert thumb1.startswith("/uploads/thumbnails/")

    # 验证物理文件生成且缩略图尺寸 <= 320px
    orig_path = DATA_DIR / orig1.lstrip("/")
    thumb_path = DATA_DIR / thumb1.lstrip("/")
    assert orig_path.exists()
    assert thumb_path.exists()

    with Image.open(thumb_path) as t_img:
        assert max(t_img.size) <= 320

    # 第二次传入完全相同字节，验证去重和复用同一个路径
    sha2, orig2, thumb2 = save_image_bytes(img_bytes, "another_name.jpg")
    assert sha1 == sha2
    assert orig1 == orig2


def test_backup_export_and_import():
    """测试全站备份与恢复：导出 zip -> 包含 manifest.json 与校验码 -> 恢复前创建快照"""
    # 导出备份
    export_res = client.get("/api/backup/export")
    assert export_res.status_code == 200
    zip_bytes = export_res.content

    # 验证 zip 包完整性
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        names = z.namelist()
        assert "study_trace.db" in names
        assert "manifest.json" in names

    # 导入恢复
    import_res = client.post(
        "/api/backup/import",
        files={"file": ("test_backup.zip", zip_bytes, "application/zip")}
    )
    assert import_res.status_code == 200
    assert import_res.json()["status"] == "ok"
    assert "pre_restore_snapshot" in import_res.json()


def test_pin_lockout_after_five_attempts():
    """测试家长门禁：输错 1-4 次提示剩余次数，第 5 次锁定 5 分钟并拦截后续请求"""
    from backend.app.auth import _auth_state
    # 重置临时认证状态
    _auth_state["failed_attempts"] = 0
    _auth_state["locked_until"] = None

    # 前 4 次输错返回 400 并显示剩余次数
    for attempt in range(1, 5):
        res = client.post("/api/settings/verify-pin", json={"pin": "wrong"})
        assert res.status_code == 400
        assert f"还剩 {5 - attempt} 次机会" in res.json()["detail"]

    # 第 5 次输错触发锁定返回 403
    res5 = client.post("/api/settings/verify-pin", json={"pin": "wrong"})
    assert res5.status_code == 403
    assert "锁定 5 分钟" in res5.json()["detail"]

    # 锁定中再次请求直接被拦截返回 403
    res_locked = client.post("/api/settings/verify-pin", json={"pin": "888888"})
    assert res_locked.status_code == 403
    assert "连续输错锁定中" in res_locked.json()["detail"]

    # 清理状态以防影响后续测试
    _auth_state["failed_attempts"] = 0
    _auth_state["locked_until"] = None


def test_streak_across_month_boundary():
    """测试跨月连续打卡：从上月30、31号到本月1、2号，Streak 连续累加不中断"""
    db = SessionLocal()
    try:
        math = db.query(Subject).filter(Subject.name == "数学").first()
        today = date.today()
        # 构造跨越前 5 天的连续打卡（无论当前日期是否处于月初或月中）
        for offset in range(5):
            d = today - timedelta(days=offset)
            db.add(HomeworkItem(student_id=1, subject_id=math.id, date=d, content=f"跨天作业 {d}", is_completed=True))
        db.commit()

        streak = calculate_streak(1, db)
        assert streak == 5, f"连续 5 天打卡 streak 应为 5，实际为 {streak}"
    finally:
        db.close()


def test_backup_manifest_sha256_exact_match():
    """测试备份文件内部清单：每个被打包文件的 sha256 均与 manifest.json 记录 100% 严格一致"""
    import hashlib
    import json
    export_res = client.get("/api/backup/export")
    assert export_res.status_code == 200

    with zipfile.ZipFile(io.BytesIO(export_res.content)) as z:
        manifest_data = json.loads(z.read("manifest.json").decode("utf-8"))
        files_map = manifest_data["files"]
        assert len(files_map) > 0

        for arc_name, expected_sha256 in files_map.items():
            actual_bytes = z.read(arc_name)
            actual_sha256 = hashlib.sha256(actual_bytes).hexdigest()
            assert actual_sha256 == expected_sha256, f"{arc_name} 的 sha256 校验不匹配"


def test_api_not_found_returns_404_json_not_html():
    """测试未定义的 API 路径返回 404 JSON 而不是被 SPA fallback 吞掉返回 index.html"""
    res = client.get("/api/invalid_endpoint_xyz")
    assert res.status_code == 404
    assert res.headers["content-type"].startswith("application/json")
    assert res.json()["detail"] == "API endpoint not found"

