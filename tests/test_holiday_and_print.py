import pytest
from datetime import date
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.utils.holidays import get_break_span, get_holiday_context, is_workday


@pytest.fixture
def client():
    return TestClient(app)


def test_holiday_span_detection():
    # 2026年国庆节假期：10-01 至 10-07
    span = get_break_span(date(2026, 10, 1))
    assert span is not None
    assert span["span_start"] == date(2026, 10, 1)
    assert span["span_end"] == date(2026, 10, 7)
    assert span["last_workday"] == date(2026, 9, 30)
    assert span["is_statutory"] is True
    assert "国庆" in span["holiday_name"]

    # 2026年9月30日为节前最后一个工作日
    assert is_workday(date(2026, 9, 30)) is True


def test_holiday_info_endpoint(client):
    res = client.get("/api/homework/holiday-info?date=2026-10-01")
    assert res.status_code == 200
    data = res.json()
    assert data["is_workday"] is False
    assert data["current_break"] is not None
    assert data["current_break"]["span_start"] == "2026-10-01"
    assert data["current_break"]["span_end"] == "2026-10-07"


def test_multi_day_homework_query(client):
    # 查询跨度日期作业
    res = client.get("/api/homework?start_date=2026-10-01&end_date=2026-10-07")
    assert res.status_code == 200
    data = res.json()
    assert data.get("is_multi_day") is True
    assert data["start_date"] == "2026-10-01"
    assert data["end_date"] == "2026-10-07"
    assert "items" in data
    assert "rollover_items" in data
