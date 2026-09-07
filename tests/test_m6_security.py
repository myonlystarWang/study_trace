import io
import zipfile
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.config import settings

client = TestClient(app)


def test_m6_ports_and_origins_config():
    """验证 M6 决议：端口配置为 28000 (prod) / 28001 (dev)，CORS 收紧包含正式域名"""
    assert settings.PORT == 28000
    assert settings.DEV_PORT == 28001
    assert "https://study.raddishlab.tech" in settings.ALLOWED_ORIGINS
    assert "http://127.0.0.1:28000" in settings.ALLOWED_ORIGINS
    assert "http://127.0.0.1:28001" in settings.ALLOWED_ORIGINS
    assert settings.SECRET_KEY != ""


def test_m6_children_endpoints_stay_passwordless():
    """验证孩子端日常打卡与错题查看保持免密，无摩擦打卡体验"""
    # 1. 孩子查询作业列表：无需任何 Header / PIN，直接 200
    res_hw = client.get("/api/homework?date=2026-09-07")
    assert res_hw.status_code == 200
    assert "items" in res_hw.json()

    # 2. 孩子查询错题列表：无需任何 Header / PIN，直接 200
    res_mis = client.get("/api/mistakes")
    assert res_mis.status_code == 200
    assert isinstance(res_mis.json(), list)


def test_m6_backup_export_requires_pin():
    """验证阶段 0 安全加固：/api/backup/export 强制接入家长 PIN 门禁"""
    # 1. 匿名无 PIN 请求：必须返回 401 Unauthorized
    res_anon = client.get("/api/backup/export")
    assert res_anon.status_code == 401
    assert "需要家长管理口令" in res_anon.json()["detail"]

    # 2. 错误 PIN 请求：返回 400 Bad Request
    res_wrong = client.get("/api/backup/export", headers={"X-Parent-PIN": "000000"})
    assert res_wrong.status_code == 400
    assert "口令错误" in res_wrong.json()["detail"]

    # 3. 正确 Header PIN 请求：返回 200 OK 且为有效 zip
    res_ok = client.get("/api/backup/export", headers={"X-Parent-PIN": settings.DEFAULT_PIN})
    assert res_ok.status_code == 200
    assert res_ok.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(res_ok.content)) as z:
        names = z.namelist()
        assert "manifest.json" in names

    # 4. 正确 Query PIN 请求：返回 200 OK
    res_query_ok = client.get(f"/api/backup/export?pin={settings.DEFAULT_PIN}")
    assert res_query_ok.status_code == 200


def test_m6_backup_import_requires_pin():
    """验证阶段 0 安全加固：/api/backup/import 强制接入家长 PIN 门禁"""
    # 匿名无 PIN 请求：必须返回 401 Unauthorized
    fake_zip = io.BytesIO(b"fake zip content")
    res_anon = client.post(
        "/api/backup/import",
        files={"file": ("test.zip", fake_zip, "application/zip")}
    )
    assert res_anon.status_code == 401
    assert "需要家长管理口令" in res_anon.json()["detail"]


def test_m6_pin_status_and_default_detection():
    """验证阶段 0：能够正确检测初始默认 PIN (888888) 并通过接口告知前端"""
    res_status = client.get("/api/settings/pin-status")
    assert res_status.status_code == 200
    assert "is_default_pin" in res_status.json()

    # 校验默认 PIN 返回 is_default_pin: True
    res_verify = client.post("/api/settings/verify-pin", json={"pin": settings.DEFAULT_PIN})
    assert res_verify.status_code == 200
    data = res_verify.json()
    assert data["status"] == "ok"
    assert data["is_default_pin"] is True
