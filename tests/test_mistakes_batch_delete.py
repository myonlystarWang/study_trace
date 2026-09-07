from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_single_and_batch_delete_mistakes():
    # 1. 创建两个临时测试错题
    res1 = client.post("/api/mistakes", json={
        "subject_id": 1,
        "source_type": "exercise",
        "source_reference": "测试批量删除01",
        "extracted_text": "临时待删错题A",
        "error_type": "计算错误"
    })
    assert res1.status_code == 200
    id1 = res1.json()["id"]

    res2 = client.post("/api/mistakes", json={
        "subject_id": 1,
        "source_type": "exercise",
        "source_reference": "测试批量删除02",
        "extracted_text": "临时待删错题B",
        "error_type": "思路卡壳"
    })
    assert res2.status_code == 200
    id2 = res2.json()["id"]

    # 2. 验证单条删除
    del_res1 = client.delete(f"/api/mistakes/{id1}")
    assert del_res1.status_code == 200
    assert del_res1.json()["status"] == "ok"

    # 再次查询已不存在
    get_res1 = client.get(f"/api/mistakes/{id1}")
    assert get_res1.status_code == 404

    # 3. 验证批量删除
    del_batch = client.post("/api/mistakes/batch-delete", json={"ids": [id2]})
    assert del_batch.status_code == 200
    assert del_batch.json()["deleted_count"] >= 1

    get_res2 = client.get(f"/api/mistakes/{id2}")
    assert get_res2.status_code == 404
