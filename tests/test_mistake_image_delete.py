"""错题图片管理接口测试：删图、清空、共享文件不误删。

覆盖用户诉求：拍照留下的图片（常含手写订正笔迹）必须能删掉，
且删除要连带清理磁盘文件，但不能误删仍被其它记录引用的共享文件。
"""
import io

from fastapi.testclient import TestClient
from PIL import Image

from backend.app.config import DATA_DIR
from backend.app.main import app
from backend.app.database import SessionLocal
from backend.app.models import MistakeRecord

client = TestClient(app)

SUBJECT_ID = 1


def _upload(color: str) -> dict:
    """通过上传接口拿到一份真实图片的 URL 三元组。不同 color → 不同 sha256。"""
    im = Image.new("RGB", (120, 90), color=color)
    buf = io.BytesIO()
    im.save(buf, format="JPEG", quality=90)
    res = client.post(
        "/api/mistakes/upload",
        files={"file": ("probe.jpg", buf.getvalue(), "image/jpeg")},
    )
    assert res.status_code == 200, res.text
    return res.json()


def _abs(rel_url: str):
    return DATA_DIR / rel_url.lstrip("/")


def _create(**overrides) -> int:
    payload = {
        "subject_id": SUBJECT_ID,
        "source_type": "exercise",
        "extracted_text": "图片管理接口测试题",
        "error_type": "计算错误",
    }
    payload.update(overrides)
    res = client.post("/api/mistakes", json=payload)
    assert res.status_code == 200, res.text
    return res.json()["id"]


def test_delete_question_image_clears_fields_and_files():
    """删除题干图：字段置空 + originals/thumbnails 两份文件都被清理"""
    up = _upload("green")
    mid = _create(
        original_image_path=up["original_url"],
        thumbnail_path=up["thumbnail_url"],
    )
    assert _abs(up["original_url"]).exists()
    assert _abs(up["thumbnail_url"]).exists()

    res = client.delete(f"/api/mistakes/{mid}/image/question")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["kind"] == "question"
    assert body["files_deleted"] >= 1

    detail = client.get(f"/api/mistakes/{mid}").json()
    assert detail["original_image_path"] is None
    assert detail["thumbnail_path"] is None
    # 磁盘文件同步消失，不留孤儿
    assert not _abs(up["original_url"]).exists()
    assert not _abs(up["thumbnail_url"]).exists()

    client.delete(f"/api/mistakes/{mid}")


def test_delete_diagram_image_only_touches_diagram():
    """删除配图不应影响同一题的题干图"""
    photo = _upload("yellow")
    diagram = _upload("purple")
    mid = _create(
        original_image_path=photo["original_url"],
        thumbnail_path=photo["thumbnail_url"],
        cropped_diagram_path=diagram["original_url"],
    )

    res = client.delete(f"/api/mistakes/{mid}/image/diagram")
    assert res.status_code == 200

    detail = client.get(f"/api/mistakes/{mid}").json()
    assert detail["cropped_diagram_path"] is None
    assert detail["original_image_path"] == photo["original_url"]
    assert detail["thumbnail_path"] == photo["thumbnail_url"]
    assert _abs(photo["original_url"]).exists()
    assert not _abs(diagram["original_url"]).exists()

    client.delete(f"/api/mistakes/{mid}")


def test_shared_image_not_purged_while_still_referenced():
    """两条记录引用同一张图时，删其中一条不能把文件删掉"""
    up = _upload("orange")
    mid_a = _create(
        original_image_path=up["original_url"],
        thumbnail_path=up["thumbnail_url"],
        source_reference="共享图A",
    )
    mid_b = _create(
        original_image_path=up["original_url"],
        thumbnail_path=up["thumbnail_url"],
        source_reference="共享图B",
    )

    res = client.delete(f"/api/mistakes/{mid_a}/image/question")
    assert res.status_code == 200
    assert res.json()["files_deleted"] == 0
    assert _abs(up["original_url"]).exists(), "文件仍被 B 引用，不能被删除"

    # 删掉最后一条引用后，文件才应被回收
    res_b = client.delete(f"/api/mistakes/{mid_b}/image/question")
    assert res_b.status_code == 200
    assert res_b.json()["files_deleted"] >= 1
    assert not _abs(up["original_url"]).exists()

    client.delete(f"/api/mistakes/{mid_a}")
    client.delete(f"/api/mistakes/{mid_b}")


def test_put_null_clears_image_fields():
    """PUT 显式传 null 应清空图片字段（旧实现会因 is not None 判断被吞掉）"""
    up = _upload("cyan")
    mid = _create(
        original_image_path=up["original_url"],
        thumbnail_path=up["thumbnail_url"],
        cropped_diagram_path=up["original_url"],
    )

    res = client.put(
        f"/api/mistakes/{mid}",
        json={"extracted_text": "改过文字", "cropped_diagram_path": None},
    )
    assert res.status_code == 200
    detail = client.get(f"/api/mistakes/{mid}").json()
    assert detail["cropped_diagram_path"] is None
    assert detail["extracted_text"] == "改过文字"
    # 文本字段不因未传而被误清空
    db = SessionLocal()
    try:
        rec = db.query(MistakeRecord).filter(MistakeRecord.id == mid).first()
        assert rec.answer is None
    finally:
        db.close()

    client.delete(f"/api/mistakes/{mid}/image/question")
    client.delete(f"/api/mistakes/{mid}")


def test_delete_image_rejects_unknown_kind():
    mid = _create()
    res = client.delete(f"/api/mistakes/{mid}/image/whatever")
    assert res.status_code == 400
    assert "question" in res.json()["detail"]
    client.delete(f"/api/mistakes/{mid}")
